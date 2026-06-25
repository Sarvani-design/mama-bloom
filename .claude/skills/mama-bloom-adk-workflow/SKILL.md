---
name: mama-bloom-adk-workflow
description: >
  ALWAYS use this skill when building or modifying app/agent.py: any node
  function, the Workflow graph, edges, or conditional routing. Triggers on:
  "workflow", "node", "agent graph", "edge", "intake_parser", "safety_screen",
  "crisis_response", "activity_picker", "intro_writer", "content_generator",
  "memory_saver", "ctx.route", "ctx.state", or any ADK-related code in
  app/agent.py. This skill documents the REAL, currently-installed
  google.adk.workflow API — verified directly against the installed package,
  not assumed. Read this before writing any agent code.
---

# Mama Bloom — ADK 2.0 Workflow Skill (matches the real app/agent.py)

## The real API surface (verified via `inspect` against the installed package)

```python
import google.adk.workflow as w
# dir(w) -> ['BaseNode', 'DEFAULT_ROUTE', 'Edge', 'FunctionNode', 'JoinNode',
#            'Node', 'NodeTimeoutError', 'RetryConfig', 'START', 'Workflow', ...]
```

`Edge` and `FunctionNode` exist as classes, but **`Workflow` has no
`add_node()`/`add_edge()` builder methods** — it's a pydantic model
(`Workflow.__init__(self, /, **data)`). Don't write
`workflow.add_node(FunctionNode(...))` or
`workflow.add_edge(Edge(source=..., target=..., condition=...))` — that API
does not exist on this class and will fail. The real construction pattern is
a plain-function/dict-routing list passed to the `edges=` kwarg — see below.

## ✅ ALWAYS USE
```python
from google.adk.agents import Context
from google.adk.apps import App
from google.adk.workflow import Workflow
from google import genai          # current unified SDK
from google.genai import types
```

## ❌ NEVER USE
```python
from google.adk import SequentialAgent, LlmAgent, ParallelAgent   # not used anywhere in this codebase
import google.generativeai as genai                               # legacy SDK — use `from google import genai` instead
```

---

## The real 7-node graph — `app/agent.py`

```
Mother input (week, mood, description)
        │
        ▼
   intake_parser   (no LLM — normalises production /checkin state OR
        │           agents-cli eval's "Week: X. Mood: Y. Message: Z" text)
        ▼
   safety_screen   (no LLM — PII redaction + distress detection,
        │           sets ctx.route = "crisis" | "normal". Redacts BOTH
        │           clean_description AND free_text - intro_writer's
        │           Gemini prompt is built from free_text, so redacting
        │           only clean_description was a real PII-leak bug.)
        ├── crisis ──────────► crisis_response  (NO LLM EVER — terminal,
        │                       zero google.genai references anywhere
        │                       in its body; this is a structural
        │                       guarantee, not just a comment)
        └── normal ──────────► activity_picker  (no LLM — deterministic
                                 mood × trimester × variety routing)
                                       │
                                       ▼
                                 intro_writer    (the ONE Gemini call in
                                       │          the whole graph — see
                                       │          "Why intro_writer is a
                                       │          plain function node" below)
                                       ▼
                                 content_generator (no LLM)
                                       │
                                       ▼
                                 memory_saver    (real MCP client calls —
                                                  see mama-bloom-mcp-server skill)
```

Note: `activity_picker` and `intro_writer` are **separate nodes** — the
Gemini call is deliberately split out from activity routing, not fused
together. This matters for the graceful-degradation guarantee below.

## Real graph construction (the actual `edges=` pattern — copy this shape)

```python
workflow = Workflow(
    name="mama_bloom_workflow",
    edges=[
        ("START", intake_parser),
        (intake_parser, safety_screen),
        (safety_screen, {"crisis": crisis_response, "normal": activity_picker}),
        (activity_picker, intro_writer, content_generator, memory_saver),
    ],
)
root_agent = workflow
app = App(root_agent=root_agent, name="mama-bloom")
```

- A plain `(node_a, node_b)` tuple is an unconditional edge.
- A dict as the second element (`{"crisis": ..., "normal": ...}`) is
  conditional routing keyed by `ctx.route`, set inside the upstream node.
- A tuple of more than 2 nodes (`(activity_picker, intro_writer, content_generator, memory_saver)`)
  chains them sequentially.

## `user_id` flows through the whole graph — never bypass it

Every node that touches MCP (`activity_picker`'s `get_yesterday_activities`,
`memory_saver`'s `save_session`/`get_streak`/`save_baby_book_entry`) takes a
`user_id: str = "anonymous"` parameter and passes it straight through.
`intake_parser` is the only node that *sets* it
(`ctx.state["user_id"] = user_id or "anonymous"`), seeded from
`fast_api_app.py`'s per-visitor cookie (see `mama-bloom-fastapi` skill) or
defaulted for the `agents-cli eval` harness, which has no cookie. This is a
real security boundary, not decoration — see `mama-bloom-mcp-server`'s
"Day 4" notes: without it, every visitor's check-ins and Baby Book entries
are visible to every other visitor. If you add a new node that reads or
writes MCP data, it must take and forward `user_id` too.

## Critical state-passing rule — the #1 mistake to avoid

**A node's return value becomes the next node's input/event output, NOT
automatic session state.** Only explicit `ctx.state[key] = value` writes
persist and become visible to downstream nodes (which receive them as
named keyword parameters, e.g. `def activity_picker(ctx: Context, week: int, mood: str, ...)`).
Returning a dict like `return {"week": week}` does **not** seed state —
you must write `ctx.state["week"] = week` explicitly. Every real node in
`app/agent.py` takes `ctx: Context` as its first parameter for exactly this
reason.

## Why `crisis_response` has zero LLM references

```python
def crisis_response(ctx: Context) -> types.Content:
    # NO LLM, NO delay, immediate response. Zero google.genai imports or
    # calls anywhere in this function body — a structural guarantee that
    # crisis messaging can never be subject to model hallucination,
    # latency, or an API outage.
    ctx.state["output"] = CRISIS_MESSAGE
    ctx.state["is_crisis"] = True
    return types.Content(role="model", parts=[types.Part.from_text(text=CRISIS_MESSAGE)])
```

`crisis_response` has **no edge back into any LLM path** — it's a terminal
node reachable only via `safety_screen`'s `"crisis"` route.

## Why `intro_writer` is a plain function node, not a native `LlmAgent`

Verified directly in `google/adk/workflow/_node_runner.py`: **any unhandled
exception in any node aborts the entire remaining workflow.** A Gemini
outage must never block a mother from seeing her daily activities, so
`intro_writer` wraps the Gemini call in try/except and falls back to a
templated intro string on any failure — while still running entirely
inside the real graph:

```python
def intro_writer(ctx: Context, week: int, mood_context: str, breathing_name: str,
                  journaling_name: str, baby_connect_name: str) -> None:
    gemini_intro = ""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT, max_output_tokens=150, temperature=0.8,
                ),
            )
            gemini_intro = response.text.strip() if response.text else ""
        except Exception as exc:
            print(f"Gemini call failed, using fallback intro: {exc}")
    if not gemini_intro:
        gemini_intro = f"Welcome to your Week {week} daily check-in. ..."
    ctx.state["gemini_intro"] = gemini_intro
```

Do not "upgrade" this to a native `LlmAgent` node without re-verifying the
node-runner exception-abort behavior first — that would remove the
graceful-degradation guarantee.

## `intake_parser` — two input conventions, one node

```python
_INTAKE_PATTERN = re.compile(
    r"week:\s*(?P<week>\d+)\.?\s*mood:\s*(?P<mood>[^.]+)\.?\s*message:\s*(?P<message>.+)",
    re.IGNORECASE | re.DOTALL,
)
```

- Production `/checkin` route seeds `week`/`mood`/`description` directly
  into session state at session creation — `intake_parser` just passes
  these through.
- `agents-cli eval` can only drive the agent through chat text, so
  `intake_parser` also recognises the fixed text convention
  `"Week: <int>. Mood: <text>. Message: <free text>"` (see
  `tests/eval/datasets/README.md`) and parses it when state hasn't already
  been seeded.

## Gemini model + API key — always this way

```python
api_key = os.environ.get("GEMINI_API_KEY", "")   # never hardcoded
client = genai.Client(api_key=api_key)
model="gemini-2.0-flash"                          # always this model
```

## Quick reference — what's actually in each file

| File | Contents |
|------|----------|
| `app/agent.py` | The real `Workflow` graph, all 7 node functions, `root_agent`, `app` |
| `app/tools.py` | `detect_distress`, `redact_pii`, `get_daily_plan`, `get_morning_affirmation`, `get_evening_whisper` |
| `app/config.py` | Activity library, `MOOD_TO_*` routing dicts, `CRISIS_MESSAGE`, `WEEKLY_MILESTONES` |
| `app/mcp_server.py` | `FastMCP` server, 6 real tools (see `mama-bloom-mcp-server` skill) |
| `app/mcp_client.py` | Real stdio MCP client (see `mama-bloom-mcp-server` skill) |
| `app/fast_api_app.py` | FastAPI routes, calls `Runner.run_async` against `root_agent` (see `mama-bloom-fastapi` skill) |
