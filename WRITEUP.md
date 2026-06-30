# Mama Bloom — Writeup

*This is the narrative submission piece for the Kaggle 5-Day AI Agents
Intensive Capstone ("Agents for Good" track). For setup instructions, the
full course-concept mapping, and the activity library reference, see
[README.md](README.md).*

---

## Problem

25 million pregnancies happen in India every year, and maternal anxiety is
the most common, least addressed risk among them. Elevated maternal
cortisol crosses the placenta and measurably disrupts fetal brain
development — specifically the hippocampus and amygdala, the regions
responsible for memory and emotional regulation. Despite this, there is no
personalised, daily, accessible emotional-support tool for most expecting
mothers. What exists instead is generic pregnancy content — week-by-week
newsletters, static symptom checklists — none of which adapts to how a
mother actually feels on a given day, and none of which is built to notice
when "feeling overwhelmed" crosses into something that needs a human, not
an activity suggestion.

## Solution

Mama Bloom is a mood-adaptive daily companion. Each day, a mother spends
about 25 minutes on a structured ritual: a self-compassion-framed morning
affirmation, one breathing exercise, one journaling prompt, and one
activity for connecting with her baby — each chosen for her specific
trimester, pregnancy week, and stated mood, while avoiding repeating
yesterday's picks. Over nine months, the journal and letter entries she
writes accumulate into a Baby Book. If she ever expresses distress, the
system detects it immediately and shows crisis support — real Indian
mental-health helplines — instead of any activity, instantly and without
involving the LLM at all.

## Why Agents — Not Just a Form

A static questionnaire or a content library could ask a mother her mood and
hand back a pre-written PDF. That's not sufficient here, for three reasons:

- **Personalisation requires judgment, not a lookup table.** "Week 20,
  anxious" has to resolve through mood × trimester × week ×
  yesterday's-activity-variety rules simultaneously, and the introduction
  she reads needs to feel like it actually noticed how she described her
  day — not a templated string with her week number swapped in.
- **Safety has to be a structural property of the architecture, not a
  prompt instruction.** Telling a single LLM call "don't ignore distress
  signals" can fail silently — model behavior under prompt instructions is
  probabilistic, and probabilistic is the wrong category for crisis
  routing. Mama Bloom's graph makes the safety guarantee structural
  instead: `safety_screen` is the only node reachable from `START`, and
  `crisis_response` has zero edges back into any LLM path, and zero
  references to the Gemini SDK anywhere in its body. The architecture
  enforces the guarantee; the model has no path to talk its way around it.
- **The agent has to remember, across sessions, without a human in the
  loop.** Building a Baby Book over nine months means the system reads its
  own check-in history every single day — via real MCP tool calls over the
  actual MCP protocol, not an in-memory variable — to decide what's next.
  That's autonomous, stateful behavior a one-shot form fundamentally can't
  provide.

So the mood-routing and crisis-safety logic are deliberately deterministic,
plain Python — verifiable, testable, and immune to model variance — while
the personalisation, warmth, and cross-session memory are exactly the parts
that need an agent. That's where Gemini and the MCP tool calls actually
live in the architecture.

## Architecture

`app/agent.py` builds a genuine `google.adk.workflow.Workflow` — the literal
`root_agent` executed by `agents-cli playground`, `agents-cli eval`, and the
production `/checkin` route via `Runner.run_async`.

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
   │ (no LLM)          │  Only node reachable from START via
   └────────┬──────────┘  intake_parser, so it always runs first.
            │
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
                        │ memory_saver         │  Real MCP client over
                        │                     │  stdio to mcp_server.py.
                        └────────────────────┘
```

See README's [Agent Architecture](README.md#agent-architecture--real-adk-20-workflow-graph)
section for the full node-by-node breakdown, and
[Known Limitations & Design Tradeoffs](README.md#known-limitations--design-tradeoffs)
for the specific, deliberate engineering reasons `crisis_response` and
`intro_writer` are shaped the way they are.

## The Journey

The earliest working version of Mama Bloom used a hand-rolled sequential
Python orchestrator — an `if/else` branch calling plain functions — built
to move fast in the hackathon's early days. It worked end to end, but the
"ADK 2.0 graph workflow" label on it wasn't actually earned: the real ADK
`Agent`/`App` objects sitting in the code were never the thing the running
app actually invoked. They were decoration over a hand-rolled dispatcher.

That gap mattered for a reason beyond scoring honesty. Once `app/agent.py`
became a real `google.adk.workflow.Workflow`, two things changed that
wouldn't have surfaced otherwise:

1. Reading the ADK source directly (`google/adk/workflow/_node_runner.py`)
   showed that an unhandled exception in *any* node aborts the entire rest
   of the graph — not just that node. That single fact is why the Gemini
   call lives in its own `intro_writer` node with a try/except and a
   templated fallback, rather than as a native `LlmAgent` whose error
   handling we hadn't verified. A real graph forced a real failure-mode
   conversation that a fake one never would have.
2. The MCP integration went through the same honesty check.
   `app/mcp_server.py`'s tools were originally just imported and called
   in-process — functionally identical output, but not actually exercising
   the MCP protocol "course concept" the submission claims. The migration
   to a genuine stdio `ClientSession`/`stdio_client` split (in
   `app/mcp_client.py`) surfaced a real integration detail along the way:
   FastMCP only populates `CallToolResult.structuredContent` when a tool's
   return type has a derivable JSON schema, which plain `dict`/`list`
   annotations don't qualify for — so `mcp_client.py` falls back to parsing
   the JSON text content instead. That's the kind of bug you only find by
   actually crossing a real process boundary.

Two genuine product bugs were also found and fixed purely as a result of
testing the real graph end to end rather than trusting the original
dispatcher's apparent correctness: a dead `config.py` import that silently
zeroed out the entire activity library, and a mood-routing gap where 4 of
the 6 homepage mood chips resolved to zero eligible activities. Neither was
visible until the real graph was actually exercised with real inputs.

The result is a submission where every architectural claim — the workflow
graph, the MCP server, the safety guardrail's structural enforcement — is
mechanically verifiable by reading the code and running
`pytest tests/unit tests/integration`, not just asserted in prose.


