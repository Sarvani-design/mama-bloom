# Video Shot-List — 5-Minute Submission Video

Maps to the rubric's suggested beats: Problem → Agents (why) → Architecture
→ Demo → The Build. Total budget: 5:00. Times below are targets, not hard
cuts — trim Architecture/Build first if running long; never cut Demo or the
safety-flow segment within it.

**Note:** record the Demo segment against whatever UI exists at recording
time. The UI-restructuring/new-features pass (tracked separately, scoped
later — see `docs/FEATURE_BACKLOG.md`) is intentionally not scheduled
before this video; don't block recording on it.

---

## 0:00–0:45 — Problem

- On screen: the stat — 25 million pregnancies/year in India, maternal
  anxiety as the leading unaddressed risk.
- Say: elevated maternal cortisol crosses the placenta and disrupts fetal
  hippocampus/amygdala development — and no personalised, daily,
  accessible emotional-support tool exists for most mothers today.
- Source for the framing: README's [The Problem](../README.md#the-problem)
  section and [Research Citations](../README.md#research-citations).

## 0:45–1:30 — Why Agents

- Say the three reasons, briefly, from `WRITEUP.md`'s "Why Agents" section:
  personalisation needs judgment (mood × trimester × week × variety,
  simultaneously), safety needs to be structural not a prompt instruction,
  and 9-month memory needs an agent that reads its own history without a
  human in the loop.
- On screen: pull the one-line version of each, or show the
  `safety_screen` → `crisis_response` structural-guarantee point visually
  (zero `google.genai` references in `crisis_response`'s body).

## 1:30–2:30 — Architecture

- Show the workflow diagram (`README.md`'s
  [Agent Architecture](../README.md#agent-architecture--real-adk-20-workflow-graph)
  ASCII graph, or a cleaner rendered version if one exists by recording
  time).
- Call out, specifically: `root_agent` is the literal graph executed by
  both `agents-cli playground`/`eval` and the production `/checkin` route —
  not a diagram describing something else running underneath.
- Mention the real MCP stdio client/server split (`app/mcp_client.py` ↔
  `app/mcp_server.py`) as the Day 2 concept, and the safety guardrail
  placement as the Day 4 concept.

## 2:30–4:00 — Demo (the most important 90 seconds)

**Scenario 1 — normal flow (~45s):** submit a check-in with a non-distress
mood/description (e.g. Week 20, "Good", "Feeling calm and a little excited
today"). Show, in order: the morning affirmation card, the Gemini intro
card, the week milestone card, all three activity cards (breathing /
journaling / baby connect), and the streak bar.

**Scenario 2 — safety flow (~45s):** submit a check-in with a distress
phrase (e.g. "I feel hopeless and can't do this anymore"). The response
must appear instantly, showing the crisis box with **both** helpline
numbers (iCall 9152987821, Vandrevala Foundation 1860-2662-345) and **zero**
activity cards. Narrate: no LLM was called on this path — say why that
matters (model latency/hallucination/outage can never gate crisis support).

## 4:00–5:00 — The Build

- Tools/tech: Google ADK 2.0 (`google.adk.workflow.Workflow`), Gemini 2.0
  Flash, MCP (FastMCP server + real stdio client), FastAPI, `agents-cli`
  (playground/eval), pytest (22 passing unit + integration tests).
- One honest beat from the Journey: the project's first working version
  was a hand-rolled `if/else` dispatcher with decorative ADK objects that
  the app never actually called — migrating to a real `Workflow` graph
  surfaced two real product bugs (a dead config import, a mood-routing gap
  affecting 4 of 6 mood chips) that the fake version had been silently
  hiding.
- Close on: every architectural claim in this submission is mechanically
  verifiable by reading the code and running
  `pytest tests/unit tests/integration`.
