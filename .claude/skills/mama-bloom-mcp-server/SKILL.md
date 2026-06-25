---
name: mama-bloom-mcp-server
description: >
  ALWAYS use this skill when building or modifying app/mcp_server.py, app/
  mcp_client.py, any MCP tool (save_session, save_baby_book_entry,
  get_sessions, get_baby_book_entries, get_streak, get_yesterday_activities),
  the data/ storage directory, or the memory_saver node. Also triggers when
  debugging session persistence, streak counting, or the variety/memory
  logic. This documents the REAL stdio MCP client/server split — not an
  in-process stub.
---

# Mama Bloom — MCP Server & Client Skill (matches the real codebase)

## This is a genuine MCP client/server split, not an in-process call

`app/mcp_server.py` runs as an actual **stdio subprocess**
(`sys.executable -m app.mcp_server`, spawned from `app/mcp_client.py`'s
`start_mcp_client()`), and `app/mcp_client.py` talks to it over the real
MCP protocol via `mcp.client.stdio.stdio_client` + `ClientSession`. There is
no in-process function-call shortcut anywhere in this path — that was an
earlier, cosmetic version that has since been replaced. Don't reintroduce
a stub client that just calls the server's Python functions directly.

## `app/mcp_server.py` — real structure

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("mama-bloom-memory")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
BABY_BOOK_DIR = DATA_DIR / "baby_book"
```

Storage is **one JSON file per record** (not a single array file):
`data/sessions/session_<session_id>.json`,
`data/baby_book/entry_<entry_id>.json`. Both directories are in
`.gitignore` (`data/sessions/`, `data/baby_book/`) — real check-in/mood
data must never be committed.

## The real 6 tools — exact signatures (all `user_id`-scoped)

**Every tool takes `user_id` and either stores it (writes) or filters by it
(reads).** This isn't optional decoration — a security review found that
`get_sessions`/`get_baby_book_entries`/`get_streak`/`get_yesterday_activities`
originally had no ownership concept at all, so any visitor to a deployed
instance could read every other visitor's journal entries and mood history
via `/babybook`/`/calendar`. Never remove the `user_id` parameter or the
`if record.get("user_id") == user_id` filter from any of these — that
filter *is* the access-control boundary, not a nice-to-have.

```python
@mcp.tool()
async def save_session(user_id: str, week: int, mood: str, activities: list,
                        post_feeling: str, date: str, session_id: str) -> dict:
    ...   # writes user_id into the stored JSON record
    return {"saved": True, "total_sessions": count}

@mcp.tool()
async def save_baby_book_entry(user_id: str, entry_type: str, week: int, content: str,
                                date: str, entry_id: str) -> dict:
    ...   # writes user_id into the stored JSON record
    return {"saved": True, "total_entries": count}

@mcp.tool()
async def get_sessions(user_id: str, limit: int = 10) -> list: ...
    # filters to session.get("user_id") == user_id before sorting descending by date

@mcp.tool()
async def get_baby_book_entries(user_id: str) -> list: ...
    # filters to entry.get("user_id") == user_id before sorting ascending by date

@mcp.tool()
async def get_streak(user_id: str) -> dict:
    ...   # total_sessions/total_days/current_streak/total_letters all computed
    # only over this user_id's own records
    return {"current_streak": int, "total_days": int, "total_letters": int, "total_sessions": int}

@mcp.tool()
async def get_yesterday_activities(user_id: str) -> dict:
    # Used by the variety rule (never repeat same activity 2 days running).
    # Filters sessions to this user_id first, then reads the single most
    # recent one by date, maps its activity IDs back to
    # {"breathing": id, "journaling": id, "baby_connect": id} by checking
    # membership against BREATHING_ACTIVITIES / JOURNALING_ACTIVITIES /
    # (BABY_CONNECT_ACTIVITIES | CREATIVE_ALTERNATES) id sets.
    ...
```

Records written before this fix have no `"user_id"` key at all — that's
fine, they simply match no `user_id` going forward (effectively invisible
to everyone) rather than leaking into a new visitor's view.

`get_streak()`'s streak calculation only counts a streak if today OR
yesterday has a session — a gap of 2+ days resets `current_streak` to 0,
even if `total_days`/`total_sessions` keep accumulating.

## `app/mcp_client.py` — real stdio client + retry + the FastMCP quirk

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def start_mcp_client(project_root: str) -> None:
    global _session, _exit_stack
    _exit_stack = AsyncExitStack()
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "app.mcp_server"], cwd=project_root,
    )
    read, write = await _exit_stack.enter_async_context(stdio_client(params))
    _session = await _exit_stack.enter_async_context(ClientSession(read, write))
    await _session.initialize()
```

`start_mcp_client()`/`stop_mcp_client()` are called from
`app/fast_api_app.py`'s FastAPI `lifespan()` context manager — one MCP
session lives for the app's lifetime, not one per request.

**FastMCP quirk:** `CallToolResult.structuredContent` is only populated
when a tool's return type annotation has a derivable JSON schema; this
project's tools are annotated plain `dict`/`list`, so it's usually `None`.
`_unwrap()` falls back to parsing `result.content[0].text` as JSON:

```python
def _unwrap(result: CallToolResult) -> dict:
    if result.structuredContent is not None:
        return result.structuredContent
    return json.loads(result.content[0].text)
```

**Retry wrapper** — bounded retries live at the transport layer, not as an
ADK `RetryConfig` on `memory_saver`:

```python
_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 0.5

async def _call_tool_with_retry(name: str, arguments: dict) -> CallToolResult:
    last_exc = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return await _session.call_tool(name, arguments=arguments)
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(_RETRY_DELAY_SECONDS * attempt)
    raise last_exc
```

Why not an ADK-level retry: exhausting a workflow-level `RetryConfig`
surfaces as a fatal `ctx.error` that aborts the rest of the graph (see the
`mama-bloom-adk-workflow` skill's node-runner finding) — a flaky MCP write
would turn into a failed check-in. The bounded transport-layer retry
recovers from transient subprocess hiccups while `memory_saver`'s own
try/except remains the final graceful-degradation fallback if every retry
fails.

## How `memory_saver` (in `app/agent.py`) actually uses this

```python
async def memory_saver(ctx: Context, week: int, mood, session_id: str, daily_plan: dict,
                        user_id: str = "anonymous") -> types.Content:
    try:
        await save_session(user_id=user_id, week=week, mood=mood_str, activities=activities_list,
                            post_feeling="pending", date=today_str, session_id=session_id)
    except Exception as exc:
        print(f"save_session failed: {exc}")
    try:
        ctx.state["streak"] = await get_streak(user_id)
    except Exception as exc:
        ctx.state["streak"] = {}
    # For each activity with a truthy "baby_book" field, also call
    # save_baby_book_entry(user_id=user_id, entry_type="milestone", ...) —
    # wrapped in its own try/except per activity.
    ctx.state["saved"] = True
```

`user_id` itself comes from `ctx.state["user_id"]`, set by `intake_parser`
from `fast_api_app.py`'s per-visitor cookie (see `mama-bloom-fastapi`
skill) — see `mama-bloom-adk-workflow`'s "user_id flows through the whole
graph" section.

Every MCP call in `memory_saver` is individually try/except-wrapped — one
failed save must never prevent the others or fail the whole check-in.

## Data flow summary (real route names, real node names)

```
POST /checkin (fast_api_app.py)
  → Runner.run_async(root_agent, ...)
  → intake_parser → safety_screen
  → (crisis path: stops here, never touches MCP)
  → activity_picker
      → get_yesterday_activities()  [MCP tool, via mcp_client]
  → intro_writer → content_generator → memory_saver
      → save_session()              [MCP tool]
      → get_streak()                 [MCP tool]
      → save_baby_book_entry() per qualifying activity   [MCP tool]
```
