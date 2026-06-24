# 🌸 Mama Bloom — AI Maternal Wellbeing Companion

> A mood-adaptive AI agent that gives pregnant mothers a structured 
> 25-minute daily ritual of evidence-based emotional wellbeing 
> activities, personalised to their trimester, mood, and pregnancy 
> week — and builds a Baby Book over 9 months.

**Kaggle 5-Day AI Agents Intensive Capstone Project — Agents for Good Track**  
**Deadline: July 6, 2026**

---

## The Problem

25 million pregnancies occur in India every year. Maternal anxiety 
is the number one unaddressed risk — elevated cortisol crosses the 
placenta and directly disrupts fetal brain development, specifically 
the hippocampus and amygdala. No personalised, daily, accessible 
emotional support exists for most mothers.

---

## The Solution

Mama Bloom is a mood-adaptive AI agent that:

- Gives a pregnant mother a structured 25-minute daily ritual
- Personalises every session to her trimester, mood, and week
- Builds a Baby Book of letters and reflections over 9 months
- Detects distress and routes to crisis support instantly
- Never claims to treat or diagnose — supports wellbeing only

---

## What Makes It Different

- 100% secular — no religious content, universally inclusive
- Evidence-backed — 41 MBCP RCTs, NIH PMC citations, 
  Pennebaker, Kristin Neff self-compassion framework
- Mood-adaptive — not one-size-fits-all
- Safe — distress guardrail fires before any LLM call
- Builds something tangible — the Baby Book

---

## Medical Disclaimer

Mama Bloom supports your emotional wellbeing during pregnancy. 
It is not a substitute for medical advice — always consult your 
doctor or midwife.

---

## Agent Architecture — Real ADK 2.0 Workflow Graph

`app/agent.py` builds a genuine `google.adk.workflow.Workflow` — the literal
`root_agent` executed by `agents-cli playground`, `agents-cli eval`, and the
production `/checkin` route via `Runner.run_async`. It is not a hand-rolled
`if/else` dressed up as a diagram: the branching below is real conditional
routing (`ctx.route`), and every arrow is a real graph edge.

```
Mother input (week, mood, description)
            │
            ▼
   ┌──────────────────┐
   │ intake_parser     │  Normalises structured input from either the
   │ (no LLM)          │  production route (state seeded directly) or
   └────────┬──────────┘  agents-cli eval (chat-text convention).
            ▼
   ┌──────────────────┐
   │ safety_screen     │  PII redacted. Distress keywords checked.
   │ (no LLM)          │  Day 4 guardrail — only node reachable from
   └────────┬──────────┘  START via intake_parser, so it always runs
            │             before any LLM call.
   ┌────────┴─────────────────┐
   │ ctx.route == "crisis"    │ ctx.route == "normal"
   ▼                          ▼
┌──────────────────┐   ┌────────────────────┐
│ crisis_response   │   │ activity_picker     │  Deterministic mood ×
│ NO LLM EVER —     │   │ (no LLM)            │  trimester × variety
│ terminal node,     │   └──────────┬──────────┘  routing.
│ zero genai refs    │              ▼
└──────────────────┘   ┌────────────────────┐
                        │ intro_writer        │  Gemini 2.0 Flash, with a
                        │ (Gemini, try/except)│  graceful fallback — a
                        └──────────┬──────────┘  Gemini outage never blocks
                                   ▼              a mother's daily plan.
                        ┌────────────────────┐
                        │ content_generator    │  Pure Python.
                        └──────────┬──────────┘
                                   ▼
                        ┌────────────────────┐
                        │ memory_saver         │  Real MCP client
                        │                     │  (app/mcp_client.py) over
                        └────────────────────┘  stdio to mcp_server.py.
```

---

## Course Concepts Demonstrated

| Day | Concept | Implementation |
|-----|---------|----------------|
| Day 1 | ADK 2.0 graph workflow | Real `google.adk.workflow.Workflow` graph in `agent.py` — `root_agent` is the literal workflow, executed via `Runner.run_async` by both `/checkin` and `agents-cli playground`/`eval` |
| Day 2 | MCP Server | Real client/server split: `mcp_server.py` (FastMCP, 6 tools) run as a stdio subprocess, `mcp_client.py` talks to it over the actual MCP protocol via `ClientSession.call_tool` — not in-process function calls |
| Day 3 | Session memory | Cross-session mood history (`get_yesterday_activities`, `get_streak`) read back through the real MCP client |
| Day 4 | Security guardrails | `intake_parser` → `safety_screen` is the only path reachable from `START`, so PII redaction + distress routing structurally run before any LLM call; HTML-escaped output throughout `fast_api_app.py` |
| Day 5 | Deployability | Dockerfile + documented `docker build`/`gcloud run deploy` reproduction steps (see [Deployment](#deployment)) |

---

## Activity Library

18 evidence-based activities across 3 daily pillars:

**Breathing (6 activities)**
Box Breathing, Extended Exhale, Body Scan, Progressive Muscle 
Relaxation, Safe Place Visualization, Loving-Kindness Meditation

**Journaling (4 activities)**
Free Mood Journal, Gratitude Journal, Self-Compassion Check-In, 
Birth Wishes Journal

**Baby Connect (5 activities + 2 creative + 1 music)**
Daily Narration, Story Time, Humming and Singing, Conversation 
with Baby, Evening Whisper, Bilateral Drawing, Symmetry Drawing, 
Calming Music

---

## Daily Experience

Every day the mother receives:

1. Morning affirmation — self-compassion framed, full screen
2. One breathing activity — mood adaptive
3. One journaling activity — alternating to avoid repetition
4. One baby connect activity — trimester appropriate
5. Evening whisper — one sentence spoken aloud to baby

Total time: approximately 25 minutes per day.

---

## Safety System

The safety_screen node runs before every LLM call. If distress 
keywords are detected, the agent immediately shows crisis support 
with real Indian helplines — no Gemini call, no delay, no 
activities shown.

Crisis helplines shown:
- iCall: 9152987821 (TISS — trained counselors)
- Vandrevala Foundation: 1860-2662-345 (24/7)

---

## Setup Instructions

### Prerequisites
- Python 3.11 or higher
- Node.js LTS
- Google Gemini API key from aistudio.google.com

### Installation

```bash
# Clone the repository
git clone https://github.com/Sarvani-design/mama-bloom.git
cd mama-bloom

# Install dependencies
uvx google-agents-cli setup
agents-cli install

# Create environment file
echo GEMINI_API_KEY=your-key-here > .env
```

### Run locally

```bash
.venv\Scripts\activate
uvicorn app.fast_api_app:app --reload --port 8080
```

Open browser at http://localhost:8080

### Run tests

```bash
uv run pytest tests/unit tests/integration
```

Fast, deterministic, no API key or GCP project needed — these exercise the
real `app/tools.py` routing logic and the real ADK `Workflow` graph end to
end (the Gemini step's graceful-fallback path is exercised by removing
`GEMINI_API_KEY` from the test environment, so no network call is made).

### Run evaluation

```bash
# Requires a configured GCP project (for Vertex AI-backed inference/tracing):
#   export GOOGLE_CLOUD_PROJECT=<your-project-id>
agents-cli eval generate --dataset tests/eval/datasets/mama-bloom-eval.json --output artifacts/traces/
agents-cli eval grade --metrics safety_routing,activity_relevance,warmth_of_message,pii_protection,custom_response_quality,agent_turn_count --traces artifacts/traces/
```

See `tests/eval/datasets/README.md` for the dataset format and the
`intake_parser` text convention used to drive structured scenarios through
chat-shaped eval prompts.

---

## Deployment

Participants are not required to deploy to a live endpoint, but if you do,
here's how to reproduce it:

```bash
docker build -t mama-bloom .
docker run -p 8080:8080 --env-file .env mama-bloom
```

Or directly to Cloud Run:

```bash
gcloud run deploy mama-bloom --source . --region us-east1 --allow-unauthenticated
```

---

## Project Structure
mama-bloom/

├── app/

│   ├── agent.py          # Real google.adk.workflow.Workflow graph

│   ├── config.py         # 18 activities + routing rules

│   ├── tools.py          # Safety functions + PII redaction

│   ├── mcp_server.py     # MCP server with 6 tools (FastMCP, stdio)

│   ├── mcp_client.py     # Real MCP client (stdio ClientSession)

│   └── fast_api_app.py   # FastAPI web interface (Runner-driven /checkin)

├── tests/

│   ├── conftest.py                          # tmp_data_dir + mechanical-scenario fixtures

│   ├── unit/test_tools.py                   # deterministic safety/routing tests

│   ├── integration/test_workflow.py         # real Workflow/Runner end-to-end tests

│   └── eval/

│       ├── datasets/mama-bloom-eval.json           # 5 scenarios, agents-cli eval format

│       ├── datasets/mama-bloom-mechanical-cases.json  # same 5 scenarios, pytest format

│       └── eval_config.yaml                        # 6 LLM-as-judge metrics

├── CONTEXT.md            # Security standards

├── Dockerfile            # Cloud Run deployment

└── pyproject.toml        # Dependencies

---

## Project Journey

The earliest working version of Mama Bloom used a hand-rolled sequential
Python orchestrator (an `if/else` branch calling plain functions) to move
fast during the hackathon's early days. It worked, but the "ADK 2.0 graph
workflow" label on it wasn't quite earned — the real ADK `Agent`/`App`
objects in the code were never actually invoked by the running app.

We migrated `app/agent.py` to a genuine `google.adk.workflow.Workflow` with
real routing-map branching, and `app/mcp_server.py`'s tools to a real
stdio MCP client/server split, so that every claim in this README is
mechanically verifiable: `agents-cli playground`/`eval` now exercise the
exact same graph the production `/checkin` route runs, and `memory_saver`
talks to `mcp_server.py` over the actual MCP protocol instead of importing
its functions in-process.

## Known Limitations & Design Tradeoffs

- **`crisis_response` is deliberately deterministic, not agentic.** It is a
  terminal graph node with zero references to `google.genai` and no edge
  back into any LLM path. This is an intentional safety choice, not a
  missed opportunity for "more agentic" behavior — crisis messaging must be
  instant, predictable, and never subject to model hallucination, latency,
  or an API outage.
- **The Gemini intro step is a plain function node, not a native `LlmAgent`
  node.** We verified directly in `google/adk/workflow/_node_runner.py`
  that any unhandled exception in any workflow node aborts the entire
  remaining graph. A Gemini outage must never block a mother from seeing
  her daily activities, so `intro_writer` keeps the original try/except
  fallback behavior rather than delegating error handling to `LlmAgent`'s
  automatic flow. Every other part of the graph — branching, state-passing,
  the MCP client — is genuinely real ADK orchestration.
- **`agents-cli eval generate`/`grade` require a configured
  `GOOGLE_CLOUD_PROJECT`.** The mechanical safety/routing properties (crisis
  routing, PII redaction, activity rules) are covered separately by fast,
  network-free pytest tests in `tests/unit`/`tests/integration` that need no
  GCP project at all.

---

## Research Citations

1. Mindfulness-Based Childbirth and Parenting — 41 RCTs showing 
   significant reduction in prenatal anxiety and stress hormones. 
   PMC10810490

2. Pennebaker expressive writing — 15 minutes 3 times per week 
   significantly reduces stress hormones and improves immune 
   function. PMC3830620

3. Kristin Neff self-compassion framework — stronger evidence than 
   affirmations alone for reducing anxiety and depression in the 
   perinatal period.

4. University of Florida fetal voice memory study — fetuses 
   recognise repeated voice patterns by Week 34. Voice builds 
   familiarity and maternal bonding simultaneously.

5. Maternal cortisol and fetal brain development — elevated 
   maternal cortisol crosses the placenta and disrupts development 
   of fetal hippocampus and amygdala. NIH PMC evidence base.

---

## Built With

- Google ADK 2.0 — agent graph workflow
- Google Antigravity CLI — agentic development environment
- Gemini 2.0 Flash — LLM for personalised responses
- FastAPI — web interface
- MCP filesystem server — session and Baby Book storage
- Python 3.11 — core language
- agents-cli — scaffold, eval, deploy toolchain

---

*Built with care for 25 million pregnant mothers in India.*