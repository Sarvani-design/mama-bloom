---
name: mama-bloom-adk-workflow
description: >
  ALWAYS use this skill when building or modifying any agent node, workflow graph,
  edge, or routing logic in the Mama Bloom project. Triggers on: any mention of
  "workflow", "node", "agent", "graph", "edge", "FunctionNode", "activity_selector",
  "safety_screen", "crisis_response", "content_generator", "memory_saver", or
  any ADK-related code in the mama-bloom/ directory. This skill enforces ADK 2.0
  graph Workflow API usage and PROHIBITS all ADK 1.x patterns. Read this before
  writing any agent code.
---

# Mama Bloom — ADK 2.0 Graph Workflow Skill

## CRITICAL: API Version Rules

### ✅ ALWAYS USE — ADK 2.0 Graph API
```python
from google.adk.workflow import Workflow, FunctionNode, Edge
```

### ❌ NEVER USE — ADK 1.x (will fail, will lose competition points)
```python
# FORBIDDEN — do not write any of these
from google.adk import SequentialAgent   # WRONG
from google.adk import LlmAgent          # WRONG
from google.adk import ParallelAgent     # WRONG
agent = SequentialAgent(...)             # WRONG
agent = LlmAgent(...)                    # WRONG
```

---

## The 4-Node Graph — Exact Architecture

```
Mother Input → safety_screen → [crisis_response | activity_selector] → content_generator → memory_saver
```

### Node 1: safety_screen (Pure Python — NO LLM EVER)
```python
# Day 4: Safety guardrail — always runs before any LLM call
def safety_screen_fn(state: dict) -> dict:
    """
    Pure Python. No Gemini. No external calls.
    Reads: state["description"]
    Writes: state["route"] = "crisis" | "content"
             state["description_clean"] = PII-redacted text
    """
    from mama_bloom.tools import detect_distress, redact_pii

    clean_text = redact_pii(state.get("description", ""))
    state["description_clean"] = clean_text

    if detect_distress(clean_text):
        state["route"] = "crisis"
    else:
        state["route"] = "content"

    return state
```

### Node 2a: crisis_response (Pure Python — NO LLM EVER)
```python
# Human safety — no LLM, no delay, immediate response
def crisis_response_fn(state: dict) -> dict:
    """
    Pure Python. Never calls Gemini under any circumstances.
    Reads: state["route"] == "crisis"
    Writes: state["output"] = CRISIS_MESSAGE
             state["done"] = True
    """
    from mama_bloom.config import CRISIS_MESSAGE
    state["output"] = CRISIS_MESSAGE
    state["llm_called"] = False
    state["done"] = True
    return state
```

### Node 2b: activity_selector (Gemini LLM node)
```python
# Day 1: ADK 2.0 LLM node — Gemini 2.0 Flash
def activity_selector_fn(state: dict) -> dict:
    """
    Calls Gemini 2.0 Flash ONLY after safety_screen clears.
    Reads: state["week"], state["mood"], state["description_clean"]
    Writes: state["selected_activities"] = [breathing_id, journaling_id, baby_connect_id]
             state["intro_message"] = warm 3-sentence personalised message (max 80 words)
    """
    import google.generativeai as genai
    import os
    from mama_bloom.tools import get_daily_plan
    from mama_bloom.config import ACTIVITY_SELECTOR_SYSTEM_PROMPT

    # Get activity plan from pure Python routing logic
    activities = get_daily_plan(
        week=state["week"],
        mood=state["mood"],
        yesterday=state.get("yesterday_activities", {})
    )
    state["selected_activities"] = activities

    # Gemini writes ONE warm personalised intro — max 80 words
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=ACTIVITY_SELECTOR_SYSTEM_PROMPT
    )
    prompt = (
        f"Write a warm 3-sentence welcome for a mother at Week {state['week']} "
        f"of pregnancy who is feeling {state['mood']} today. "
        f"Gently introduce: {', '.join(activities)}. Max 80 words."
    )
    response = model.generate_content(prompt)
    state["intro_message"] = response.text
    state["llm_called"] = True
    return state
```

### Node 3: content_generator (Pure Python)
```python
# Generates all content — no LLM needed for structured content
def content_generator_fn(state: dict) -> dict:
    """
    Pure Python. Builds full daily plan from selected activities.
    Reads: state["selected_activities"], state["week"], state["mood"]
    Writes: state["daily_plan"] = complete structured output dict
    """
    from mama_bloom.tools import (
        generate_activity_content, get_morning_affirmation,
        get_evening_whisper, get_milestone_for_week
    )

    week = state["week"]
    activities = state["selected_activities"]

    state["daily_plan"] = {
        "morning_affirmation": get_morning_affirmation(week),
        "intro_message": state.get("intro_message", ""),
        "activities": [generate_activity_content(a, week) for a in activities],
        "evening_whisper": get_evening_whisper(),
        "milestone": get_milestone_for_week(week),
        "session_id": state["session_id"],
        "week": week,
        "mood": state["mood"],
    }
    return state
```

### Node 4: memory_saver (MCP Server call)
```python
# Day 2: MCP Server — Day 3: Session memory
async def memory_saver_fn(state: dict) -> dict:
    """
    Calls MCP filesystem server to persist session data.
    Reads: state["daily_plan"], state["session_id"]
    Writes: state["saved"] = True
             state["total_sessions"] = int
             state["baby_book_entries"] = int
    """
    from mama_bloom.mcp_server import get_mcp_client
    import datetime

    client = get_mcp_client()
    result = await client.call_tool("save_session", {
        "week": state["week"],
        "mood": state["mood"],
        "activities": state["selected_activities"],
        "post_feeling": state.get("post_feeling", ""),
        "date": datetime.date.today().isoformat(),
        "session_id": state["session_id"],
    })
    state["saved"] = True
    state["total_sessions"] = result.get("total_sessions", 0)

    # Baby Book: weekly reflections and letters
    if state.get("is_day_7"):
        await client.call_tool("save_weekly_reflection_prompt", {
            "week": state["week"],
            "date": datetime.date.today().isoformat(),
        })

    return state
```

---

## Wiring the Graph — Complete agent.py Structure

```python
# Day 1: ADK 2.0 graph workflow — mama_bloom/agent.py
from google.adk.workflow import Workflow, FunctionNode, Edge
from mama_bloom.nodes import (
    safety_screen_fn, crisis_response_fn,
    activity_selector_fn, content_generator_fn, memory_saver_fn
)

def build_workflow() -> Workflow:
    workflow = Workflow(name="mama_bloom")

    # Add all nodes
    workflow.add_node(FunctionNode(name="safety_screen",   func=safety_screen_fn))
    workflow.add_node(FunctionNode(name="crisis_response", func=crisis_response_fn))
    workflow.add_node(FunctionNode(name="activity_selector", func=activity_selector_fn))
    workflow.add_node(FunctionNode(name="content_generator", func=content_generator_fn))
    workflow.add_node(FunctionNode(name="memory_saver",    func=memory_saver_fn))

    # Wire edges
    workflow.add_edge(Edge(
        source="safety_screen",
        target="crisis_response",
        condition=lambda state: state["route"] == "crisis"
    ))
    workflow.add_edge(Edge(
        source="safety_screen",
        target="activity_selector",
        condition=lambda state: state["route"] == "content"
    ))
    workflow.add_edge(Edge(source="activity_selector", target="content_generator"))
    workflow.add_edge(Edge(source="content_generator",  target="memory_saver"))

    return workflow

# Entry point
workflow = build_workflow()
```

---

## State Schema — Always Pass This Shape

```python
# Input state shape — everything the workflow needs
initial_state = {
    "week": int,               # 1–42, pregnancy week
    "mood": str,               # one of 8 mood values (see config)
    "description": str,        # mother's free text (will be PII-redacted)
    "session_id": str,         # uuid4
    "session_date": str,       # ISO date string
    # Optional — loaded from MCP memory
    "yesterday_activities": dict,   # {breathing: id, journaling: id, baby_connect: id}
    "still_hard_count": int,        # consecutive "still_hard" post-feelings
    "is_day_7": bool,               # True if this is day 7 of the week
    "post_feeling": str,            # set AFTER activity completion
}
```

---

## Code Comment Requirements

Every node function must include the course day comment:
```python
# Day 1: ADK 2.0 graph workflow         ← in activity_selector, content_generator
# Day 2: MCP Server                     ← in memory_saver
# Day 3: Session memory                 ← in memory_saver
# Day 4: Safety guardrail               ← in safety_screen
# Day 4: PII redaction                  ← in safety_screen
# Day 5: Cloud Run deployment           ← in fast_api_app.py
```

---

## System Prompt for activity_selector

Store in `config.py` as `ACTIVITY_SELECTOR_SYSTEM_PROMPT`:
```python
ACTIVITY_SELECTOR_SYSTEM_PROMPT = """
You are a warm, supportive companion for pregnant mothers.
Never give medical advice. Always recommend consulting a doctor or midwife
for health concerns. Keep responses warm, concise, and emotionally supportive.
Write only for the mother — never clinical, never cold.
"""
```

---

## Gemini Model — Always Use This

```python
MODEL_NAME = "gemini-2.0-flash"   # Always this. Never hardcode elsewhere.
```
API key always from environment:
```python
import os
api_key = os.environ["GEMINI_API_KEY"]   # Never hardcoded
```

---

## Quick Reference — What Goes Where

| File | Contents |
|------|----------|
| `agent.py` | Workflow graph, node wiring, edges, `build_workflow()` |
| `tools.py` | `detect_distress`, `redact_pii`, `get_daily_plan`, `generate_activity_content` |
| `config.py` | Activity library, routing rules, `CRISIS_MESSAGE`, system prompts |
| `mcp_server.py` | MCP server definition, 6 tool implementations |
| `fast_api_app.py` | FastAPI endpoints, calls `workflow.run(state)` |
