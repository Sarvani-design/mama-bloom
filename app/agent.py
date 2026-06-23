# Day 1: ADK 2.0 graph workflow - the heart of Mama Bloom
# Day 2: MCP Server integration in memory_saver node
# Day 3: Session memory and cross-session adaptive logic
# Day 4: Safety guardrail fires BEFORE any LLM call - no exceptions

import datetime
import os

from dotenv import load_dotenv
from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.genai import types

from app.config import CRISIS_MESSAGE, WEEKLY_MILESTONES
from app.mcp_server import get_streak, get_yesterday_activities, save_baby_book_entry, save_session
from app.tools import (
    detect_distress,
    get_daily_plan,
    get_evening_whisper,
    get_morning_affirmation,
    redact_pii,
)

load_dotenv()

_SYSTEM_PROMPT = (
    "You are a warm, supportive companion for pregnant mothers. "
    "Never give medical advice. Always recommend consulting a doctor "
    "or midwife for health concerns. Keep responses warm, concise, "
    "and emotionally supportive."
)


def safety_screen(state: dict) -> dict:
    # Day 4: Safety guardrail - ALWAYS runs first, ALWAYS before any LLM call
    description = state.get("description", "")
    state["clean_description"] = redact_pii(description)
    if detect_distress(state["clean_description"]):
        state["route"] = "crisis"
    else:
        state["route"] = "content"
    return state


def crisis_response(state: dict) -> dict:
    # Day 4: Human safety - NO LLM, NO delay, immediate response
    # This node NEVER calls Gemini under any circumstances
    state["output"] = CRISIS_MESSAGE
    state["is_crisis"] = True
    return state


async def activity_selector(state: dict) -> dict:
    # Day 1: ADK 2.0 LLM node - Gemini 2.0 Flash
    week: int = state.get("week", 12)
    mood: str = state.get("mood", "okay")
    session_count: int = state.get("session_count", 0)

    try:
        yesterday_activities = await get_yesterday_activities()
    except Exception:
        yesterday_activities = {}

    daily_plan = get_daily_plan(week, mood, yesterday_activities)
    morning_affirmation = get_morning_affirmation(week, session_count)

    gemini_intro = ""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            breathing_name = (
                daily_plan["breathing"]["name"]
                if isinstance(daily_plan.get("breathing"), dict)
                else "breathing exercise"
            )
            journaling_name = (
                daily_plan["journaling"]["name"]
                if isinstance(daily_plan.get("journaling"), dict)
                else "journaling"
            )
            baby_connect_name = (
                daily_plan["baby_connect"]["name"]
                if isinstance(daily_plan.get("baby_connect"), dict)
                else "baby connection activity"
            )
            user_prompt = (
                f"The mother is in week {week} of her pregnancy "
                f"and is feeling {mood} today. "
                f"Write ONE warm personalised introduction of maximum "
                f"80 words that acknowledges her week and emotional "
                f"state, then gently introduces today's three "
                f"activities: {breathing_name}, {journaling_name}, "
                f"and {baby_connect_name}. Be gentle, encouraging, "
                f"and non-medical."
            )
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    max_output_tokens=150,
                    temperature=0.8,
                ),
            )
            gemini_intro = response.text.strip() if response.text else ""
        except Exception as exc:
            gemini_intro = (
                f"Welcome to your Week {week} daily check-in. "
                f"Today's plan has been crafted just for you. "
                f"You are doing wonderfully."
            )
            print(f"Gemini call failed, using fallback intro: {exc}")

    state["daily_plan"] = daily_plan
    state["morning_affirmation"] = morning_affirmation
    state["gemini_intro"] = gemini_intro
    state["session_count"] = session_count
    return state


def content_generator(state: dict) -> dict:
    # Day 1: Builds complete daily plan - pure Python, no LLM needed
    daily_plan = state.get("daily_plan", {})
    week: int = state.get("week", 12)

    evening_whisper = get_evening_whisper()
    state["evening_whisper"] = evening_whisper

    milestone = WEEKLY_MILESTONES.get(week)
    if milestone is None:
        sorted_weeks = sorted(WEEKLY_MILESTONES.keys())
        eligible = [w for w in sorted_weeks if w <= week]
        if eligible:
            milestone = WEEKLY_MILESTONES[eligible[-1]]
        else:
            milestone = WEEKLY_MILESTONES[sorted_weeks[0]]
    state["week_milestone"] = milestone
    state["session_id"] = (
        f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    )
    state["daily_plan"] = daily_plan
    return state


async def memory_saver(state: dict) -> dict:
    # Day 2: MCP Server call
    # Day 3: Session memory - saves to persistent local storage
    week: int = state.get("week", 12)
    mood: str = state.get("mood", "")
    session_id: str = state.get("session_id", "")
    daily_plan: dict = state.get("daily_plan", {})
    today_str = datetime.date.today().isoformat()

    activities_list = []
    for key in ("breathing", "journaling", "baby_connect"):
        act = daily_plan.get(key)
        if isinstance(act, dict) and act.get("id"):
            activities_list.append({
                "id": act["id"],
                "name": act.get("name", "")
            })

    try:
        await save_session(
            week=week,
            mood=mood,
            activities=activities_list,
            post_feeling="pending",
            date=today_str,
            session_id=session_id,
        )
    except Exception as exc:
        print(f"save_session failed: {exc}")

    try:
        streak = await get_streak()
        state["streak"] = streak
    except Exception as exc:
        state["streak"] = {}
        print(f"get_streak failed: {exc}")

    for key in ("breathing", "journaling", "baby_connect"):
        act = daily_plan.get(key)
        if isinstance(act, dict) and act.get("baby_book"):
            try:
                entry_id = f"bb_{session_id}_{key}"
                await save_baby_book_entry(
                    entry_type="milestone",
                    week=week,
                    content=str(act.get("baby_book", "")),
                    date=today_str,
                    entry_id=entry_id,
                )
            except Exception as exc:
                print(f"save_baby_book_entry failed for {key}: {exc}")

    state["saved"] = True
    return state


# ADK App entrypoint for agents-cli playground
# Day 1: root_agent exposes the agent to ADK toolchain
root_agent = Agent(
    name="mama_bloom_agent",
    model="gemini-2.0-flash",
    instruction=_SYSTEM_PROMPT,
)

app = App(
    root_agent=root_agent,
    name="mama-bloom",
)


async def _run_workflow_async(
    week: int,
    mood: str,
    description: str,
    session_count: int = 0,
) -> dict:
    # Day 1: Manual graph execution - safety first, always
    # Day 3: State passed through all nodes
    state: dict = {
        "week": week,
        "mood": mood,
        "description": description,
        "session_count": session_count,
        "route": "",
    }

    # Node 1 - safety screen ALWAYS runs first
    # Day 4: guardrail before any LLM call
    state = safety_screen(state)

    if state.get("route") == "crisis":
        # Node 2a - crisis response, NO LLM
        state = crisis_response(state)
    else:
        # Node 2b - activity selector with Gemini
        state = await activity_selector(state)
        # Node 3 - content generator
        state = content_generator(state)
        # Node 4 - memory saver via MCP
        # Day 2: MCP server call
        state = await memory_saver(state)

    return state


def run_workflow(
    week: int,
    mood: str,
    description: str,
    session_count: int = 0,
) -> dict:
    import asyncio
    return asyncio.run(
        _run_workflow_async(
            week=week,
            mood=mood,
            description=description,
            session_count=session_count,
        )
    )