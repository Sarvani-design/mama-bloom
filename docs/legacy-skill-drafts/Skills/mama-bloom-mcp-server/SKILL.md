---
name: mama-bloom-mcp-server
description: >
  ALWAYS use this skill when building or modifying mcp_server.py, any MCP
  tool (save_session, save_baby_book_entry, get_sessions, get_baby_book_entries,
  get_streak, get_yesterday_activities), the data/ storage directory, the
  memory_saver node, or any code that reads/writes session or Baby Book data
  in Mama Bloom. Also triggers when debugging session persistence, streak
  counting, or adaptive memory logic. This is the authoritative reference
  for all MCP server implementation — Day 2 and Day 3 course concepts.
---

# Mama Bloom — MCP Server Skill

## What the MCP Server Does

The MCP filesystem server is **not a checkbox** — it does real work:
1. Persists every session so mood history drives next-day activity selection
2. Tracks streaks for the stats dashboard
3. Stores Baby Book entries that accumulate across 9 months
4. Provides yesterday's activities so the variety rule prevents repetition
5. Enables the adaptive safety rules (consecutive "still_hard" detection)

---

## File: mama_bloom/mcp_server.py — Complete Structure

```python
# Day 2: MCP Server — filesystem-based session and Baby Book storage
# Day 3: Session memory — mood history enables adaptive activity selection

import json
import os
import uuid
from pathlib import Path
from datetime import date
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR", "./data"))
SESSIONS_FILE = DATA_DIR / "sessions.json"
BABY_BOOK_FILE = DATA_DIR / "baby_book.json"

def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SESSIONS_FILE.exists():
        SESSIONS_FILE.write_text("[]")
    if not BABY_BOOK_FILE.exists():
        BABY_BOOK_FILE.write_text("[]")

def _load_sessions() -> list:
    _ensure_data_dir()
    return json.loads(SESSIONS_FILE.read_text())

def _save_sessions(sessions: list):
    SESSIONS_FILE.write_text(json.dumps(sessions, indent=2))

def _load_baby_book() -> list:
    _ensure_data_dir()
    return json.loads(BABY_BOOK_FILE.read_text())

def _save_baby_book(entries: list):
    BABY_BOOK_FILE.write_text(json.dumps(entries, indent=2))

server = Server("mama-bloom-mcp")
```

---

## The 6 Required MCP Tools

### Tool 1: save_session
```python
@server.tool()
async def save_session(
    week: int,
    mood: str,
    activities: list,       # list of activity IDs served today
    post_feeling: str,      # "settled" | "warm" | "same" | "still_hard"
    date: str,              # ISO format: "2026-06-25"
    session_id: str,
) -> dict:
    """
    # Day 2: MCP Server — persists each session
    # Day 3: Session memory — enables adaptive logic on next day
    """
    sessions = _load_sessions()
    sessions.append({
        "session_id": session_id,
        "week": week,
        "mood": mood,
        "activities": activities,
        "post_feeling": post_feeling,
        "date": date,
    })
    _save_sessions(sessions)
    return {"saved": True, "total_sessions": len(sessions)}
```

### Tool 2: save_baby_book_entry
```python
@server.tool()
async def save_baby_book_entry(
    entry_type: str,    # "letter" | "reflection" | "milestone"
    week: int,
    content: str,       # what the mother wrote
    date: str,
    entry_id: str = None,
) -> dict:
    """
    # Day 2: MCP Server — Baby Book accumulates across 9 months
    Saves letters, weekly reflections, and milestone entries.
    """
    entries = _load_baby_book()
    entries.append({
        "entry_id": entry_id or str(uuid.uuid4()),
        "entry_type": entry_type,
        "week": week,
        "content": content,
        "date": date,
    })
    _save_baby_book(entries)
    return {"saved": True, "total_entries": len(entries)}
```

### Tool 3: get_sessions
```python
@server.tool()
async def get_sessions(limit: int = 10) -> list:
    """
    # Day 3: Session memory — last N sessions for adaptive routing
    Used by: memory_saver node to check consecutive still_hard count.
    Used by: activity_selector to get yesterday's activities.
    """
    sessions = _load_sessions()
    return sessions[-limit:] if len(sessions) > limit else sessions
```

### Tool 4: get_baby_book_entries
```python
@server.tool()
async def get_baby_book_entries() -> list:
    """
    # Day 3: Session memory — all Baby Book entries for PDF generation
    Returns full list sorted by date for Baby Book view.
    """
    entries = _load_baby_book()
    return sorted(entries, key=lambda e: e["date"])
```

### Tool 5: get_streak
```python
@server.tool()
async def get_streak() -> dict:
    """
    # Day 3: Session memory — streak data for stats dashboard
    Returns current consecutive day streak.
    """
    sessions = _load_sessions()
    if not sessions:
        return {"current_streak": 0, "total_days": 0,
                "total_letters": 0, "total_sessions": 0}

    from datetime import datetime, timedelta
    total_sessions = len(sessions)

    # Count Baby Book letters
    baby_book = _load_baby_book()
    total_letters = sum(1 for e in baby_book if e["entry_type"] == "letter")

    # Calculate streak (consecutive days from today backwards)
    dates = sorted(set(s["date"] for s in sessions), reverse=True)
    streak = 0
    expected = date.today()
    for d in dates:
        session_date = datetime.fromisoformat(d).date()
        if session_date == expected or session_date == expected - timedelta(days=1):
            streak += 1
            expected = session_date - timedelta(days=1)
        else:
            break

    return {
        "current_streak": streak,
        "total_days": len(dates),
        "total_letters": total_letters,
        "total_sessions": total_sessions,
    }
```

### Tool 6: get_yesterday_activities
```python
@server.tool()
async def get_yesterday_activities() -> dict:
    """
    # Day 3: Session memory — variety rule: never repeat same activity 2 days running
    Returns last session's activities by pillar.
    """
    sessions = _load_sessions()
    if not sessions:
        return {"breathing": None, "journaling": None, "baby_connect": None}

    last = sessions[-1]
    activities = last.get("activities", [])

    from mama_bloom.config import ACTIVITY_LIBRARY
    result = {"breathing": None, "journaling": None, "baby_connect": None}
    for act_id in activities:
        act = ACTIVITY_LIBRARY.get(act_id, {})
        pillar = act.get("pillar")
        if pillar in result:
            result[pillar] = act_id

    return result
```

---

## MCP Client — How memory_saver Calls the Server

```python
# In mama_bloom/mcp_server.py — also expose a client helper
from mcp import ClientSession
from mcp.client.stdio import stdio_client

async def get_mcp_client():
    """
    # Day 2: MCP Client — used by memory_saver node
    Returns a ready-to-use MCP client session.
    """
    # In production: connect to running MCP server process
    # In development: use in-process for simplicity
    return _InProcessClient()

class _InProcessClient:
    """Thin wrapper for in-process MCP tool calls during development."""
    async def call_tool(self, tool_name: str, args: dict):
        tools = {
            "save_session": save_session,
            "save_baby_book_entry": save_baby_book_entry,
            "get_sessions": get_sessions,
            "get_baby_book_entries": get_baby_book_entries,
            "get_streak": get_streak,
            "get_yesterday_activities": get_yesterday_activities,
        }
        if tool_name not in tools:
            raise ValueError(f"Unknown MCP tool: {tool_name}")
        return await tools[tool_name](**args)
```

---

## MCP Server Entry Point

```python
# Bottom of mcp_server.py — runs as a subprocess
if __name__ == "__main__":
    import asyncio
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream,
                           server.create_initialization_options())
    asyncio.run(main())
```

---

## Data Directory Structure

```
data/
├── sessions.json        ← [{session_id, week, mood, activities, post_feeling, date}]
└── baby_book.json       ← [{entry_id, entry_type, week, content, date}]
```

**Security rules for data/:**
- Never expose `data/` via any API endpoint
- Never log session content (only log that data was saved)
- This directory is in `.gitignore`

---

## Makefile Targets for MCP

```makefile
# Start MCP server in background
mcp-server:
	python -m mama_bloom.mcp_server &

# Run playground (includes MCP)
playground:
	uvx google-agents-cli playground

# Serve FastAPI (MCP starts automatically)
serve:
	uvicorn mama_bloom.fast_api_app:app --reload --port 8080
```

---

## Session Data Flow Summary

```
check-in form submitted
    → FastAPI /check-in endpoint
    → workflow.run(initial_state)
    → safety_screen (reads description)
    → activity_selector (reads week, mood)
        → get_yesterday_activities() [MCP Tool 6]
    → content_generator (builds daily_plan)
    → memory_saver
        → save_session() [MCP Tool 1]
        → save_baby_book_entry() if letter day [MCP Tool 2]
    → response returned to FastAPI
    → UI shown to mother

activity marked Done
    → POST /complete
    → memory_saver updates post_feeling
        → save_session() updated [MCP Tool 1]
    → adaptive rule check
        → get_sessions(limit=3) [MCP Tool 3]
```
