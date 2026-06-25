# Day 2: MCP Server - Day 3: Session memory and Baby Book storage

import datetime
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.config import (
    BABY_CONNECT_ACTIVITIES,
    BREATHING_ACTIVITIES,
    CREATIVE_ALTERNATES,
    JOURNALING_ACTIVITIES,
)

mcp = FastMCP("mama-bloom-memory")

# Paths configuration relative to workspace root
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
BABY_BOOK_DIR = DATA_DIR / "baby_book"

# Ensure directories exist
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
BABY_BOOK_DIR.mkdir(parents=True, exist_ok=True)


def parse_date(date_str: str) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(date_str[:10])
    except Exception:
        try:
            return datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except Exception:
            return None


@mcp.tool()
async def save_session(
    week: int,
    mood: str,
    activities: list,
    post_feeling: str,
    date: str,
    session_id: str,
) -> dict:
    # Day 3: Saves each check-in to persistent local storage
    session_data = {
        "week": week,
        "mood": mood,
        "activities": activities,
        "post_feeling": post_feeling,
        "date": date,
        "session_id": session_id,
    }

    file_path = SESSIONS_DIR / f"session_{session_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)

    # Count files
    count = len(list(SESSIONS_DIR.glob("session_*.json")))
    return {"saved": True, "total_sessions": count}


@mcp.tool()
async def save_baby_book_entry(
    entry_type: str,
    week: int,
    content: str,
    date: str,
    entry_id: str,
) -> dict:
    # Day 3: Baby Book persistence - builds over 9 months
    entry_data = {
        "entry_type": entry_type,
        "week": week,
        "content": content,
        "date": date,
        "entry_id": entry_id,
    }

    file_path = BABY_BOOK_DIR / f"entry_{entry_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(entry_data, f, indent=2, ensure_ascii=False)

    # Count files
    count = len(list(BABY_BOOK_DIR.glob("entry_*.json")))
    return {"saved": True, "total_entries": count}


@mcp.tool()
async def get_sessions(limit: int = 10) -> list:
    # Day 3: Retrieves mood history for adaptive logic
    sessions = []
    for file_path in SESSIONS_DIR.glob("session_*.json"):
        try:
            with open(file_path, encoding="utf-8") as f:
                sessions.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue

    # Sort descending by date
    sessions.sort(key=lambda s: s.get("date", ""), reverse=True)
    return sessions[:limit]


@mcp.tool()
async def get_baby_book_entries() -> list:
    # Day 3: Returns all Baby Book entries for display
    entries = []
    for file_path in BABY_BOOK_DIR.glob("entry_*.json"):
        try:
            with open(file_path, encoding="utf-8") as f:
                entries.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue

    # Sort ascending by date
    entries.sort(key=lambda e: e.get("date", ""))
    return entries


@mcp.tool()
async def get_streak() -> dict:
    # Day 3: Streak tracking for progress display
    # 1. Total sessions
    session_files = list(SESSIONS_DIR.glob("session_*.json"))
    total_sessions = len(session_files)

    # 2. Total letters
    entry_files = list(BABY_BOOK_DIR.glob("entry_*.json"))
    total_letters = 0
    for file_path in entry_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                entry = json.load(f)
                if entry.get("entry_type") == "letter":
                    total_letters += 1
        except (json.JSONDecodeError, OSError):
            continue

    # 3. Streak calculation
    dates = set()
    for file_path in session_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                s = json.load(f)
                d_parsed = parse_date(s.get("date", ""))
                if d_parsed:
                    dates.add(d_parsed)
        except (json.JSONDecodeError, OSError):
            continue

    total_days = len(dates)

    current_streak = 0
    if dates:
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        if today in dates:
            check_date = today
            while check_date in dates:
                current_streak += 1
                check_date -= datetime.timedelta(days=1)
        elif yesterday in dates:
            check_date = yesterday
            while check_date in dates:
                current_streak += 1
                check_date -= datetime.timedelta(days=1)

    return {
        "current_streak": current_streak,
        "total_days": total_days,
        "total_letters": total_letters,
        "total_sessions": total_sessions,
    }


@mcp.tool()
async def get_yesterday_activities() -> dict:
    # Day 3: Used by variety rule - never repeat same activity two days in a row
    session_files = list(SESSIONS_DIR.glob("session_*.json"))
    if not session_files:
        return {}

    sessions = []
    for file_path in session_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                sessions.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue

    if not sessions:
        return {}

    # Sort descending by date to get the most recent one
    sessions.sort(key=lambda s: s.get("date", ""), reverse=True)
    latest_session = sessions[0]

    activities = latest_session.get("activities", [])
    result = {}

    # We map activity IDs to categories to satisfy variety rule lookup
    breathing_ids = {a["id"] for a in BREATHING_ACTIVITIES}
    journaling_ids = {a["id"] for a in JOURNALING_ACTIVITIES}
    baby_connect_ids = {a["id"] for a in BABY_CONNECT_ACTIVITIES} | {
        a["id"] for a in CREATIVE_ALTERNATES
    }

    for act in activities:
        act_id = None
        if isinstance(act, dict):
            act_id = act.get("id")
        elif isinstance(act, str):
            act_id = act

        if not act_id:
            continue

        if act_id in breathing_ids:
            result["breathing"] = act_id
        elif act_id in journaling_ids:
            result["journaling"] = act_id
        elif act_id in baby_connect_ids:
            result["baby_connect"] = act_id

    return result


def run_mcp_server():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_mcp_server()
