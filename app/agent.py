# Day 1: ADK 2.0 graph workflow - the heart of Mama Bloom
# Day 2: MCP Server integration in memory_saver node
# Day 3: Session memory and cross-session adaptive logic
# Day 4: Safety guardrail fires BEFORE any LLM call - no exceptions

import asyncio
import datetime
import os

from dotenv import load_dotenv
from google import genai
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import Edge, FunctionNode, Workflow, START
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


# ---------------------------------------------------------------------------
# NODE 1 – safety_screen
# ---------------------------------------------------------------------------


def safety_screen(state: dict) -> dict:
    # Day 4: Safety guardrail - ALWAYS runs first, ALWAYS before any LLM call
    description = state.get("description", "")
    state["clean_description"] = redact_pii(description)

    if detect_distress(state["clean_description"]):
        state["route"] = "crisis"
    else:
        state["route"] = "content"

    return state


# ---------------------------------------------------------------------------
# NODE 2a – crisis_response
# ---------------------------------------------------------------------------


def crisis_response(state: dict) -> dict:
    # Day 4: Human safety - NO LLM, NO delay, immediate response
    # This node NEVER calls Gemini under any circumstances
    state["output"] = CRISIS_MESSAGE
    state["is_crisis"] = True
    return state


# ---------------------------------------------------------------------------
# NODE 2b – activity_selector
# ---------------------------------------------------------------------------


async def activity_selector(state: dict) -> dict:
    # Day 1: ADK 2.0 LLM node - Gemini 2.0 Flash
    week: int = state.get("week", 12)
    mood: str = state.get("mood", "anxious")
    session_count: int = state.get("session_count", 0)

    # Step 1: retrieve yesterday's activities (variety rule)
    try:
        yesterday_activities = await get_yesterday_activities()
    except Exception:
        yesterday_activities = {}

    # Step 2: select today's activity plan
    daily_plan = get_daily_plan(week, mood, yesterday_activities)

    # Step 3: morning affirmation
    morning_affirmation = get_morning_affirmation(week, session_count)

    # Step 4 & 5: call Gemini for warm personalised intro (≤ 80 words)
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
                f"The mother is in week {week} of her pregnancy and is feeling {mood} today. "
                f"Write ONE warm, personalised introduction of maximum 80 words that "
                f"acknowledges her week and emotional state, then gently introduces "
                f"today's three activities: {breathing_name}, {journaling_name}, "
                f"and {baby_connect_name}. Be gentle, encouraging, and non-medical."
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

    # Step 6: store results in state
    state["daily_plan"] = daily_plan
    state["morning_affirmation"] = morning_affirmation
    state["gemini_intro"] = gemini_intro
    state["session_count"] = session_count
    return state


# ---------------------------------------------------------------------------
# NODE 3 – content_generator
# ---------------------------------------------------------------------------


def content_generator(state: dict) -> dict:
    # Day 1: Builds complete daily plan - pure Python, no LLM needed
    daily_plan = state.get("daily_plan", {})
    week: int = state.get("week", 12)

    # Evening whisper
    evening_whisper = get_evening_whisper()
    state["evening_whisper"] = evening_whisper

    # Week milestone — exact match first, then closest earlier week
    milestone = WEEKLY_MILESTONES.get(week)
    if milestone is None:
        sorted_weeks = sorted(WEEKLY_MILESTONES.keys())
        eligible = [w for w in sorted_weeks if w <= week]
        if eligible:
            milestone = WEEKLY_MILESTONES[eligible[-1]]
        else:
            milestone = WEEKLY_MILESTONES[sorted_weeks[0]]
    state["week_milestone"] = milestone

    # Unique session ID from timestamp
    state["session_id"] = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    state["daily_plan"] = daily_plan
    return state


# ---------------------------------------------------------------------------
# NODE 4 – memory_saver
# ---------------------------------------------------------------------------


async def memory_saver(state: dict) -> dict:
    # Day 2: MCP Server call
    # Day 3: Session memory - saves to persistent local storage
    week: int = state.get("week", 12)
    mood: str = state.get("mood", "")
    session_id: str = state.get("session_id", "")
    daily_plan: dict = state.get("daily_plan", {})
    today_str = datetime.date.today().isoformat()

    # Build flat list of today's activity IDs for storage
    activities_list = []
    for key in ("breathing", "journaling", "baby_connect"):
        act = daily_plan.get(key)
        if isinstance(act, dict) and act.get("id"):
            activities_list.append({"id": act["id"], "name": act.get("name", "")})

    # Step 1: save session
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

    # Step 2: get streak
    try:
        streak = await get_streak()
        state["streak"] = streak
    except Exception as exc:
        state["streak"] = {}
        print(f"get_streak failed: {exc}")

    # Step 3: baby book entries (activities flagged with baby_book=True)
    for key in ("breathing", "journaling", "baby_connect"):
        act = daily_plan.get(key)
        if isinstance(act, dict) and act.get("baby_book"):
            try:
                entry_id = f"bb_{session_id}_{key}"
                await save_baby_book_entry(
                    entry_type="milestone",
                    week=week,
                    content=act.get("baby_book", ""),
                    date=today_str,
                    entry_id=entry_id,
                )
            except Exception as exc:
                print(f"save_baby_book_entry failed for {key}: {exc}")

    # Step 4: mark saved
    state["saved"] = True
    return state


# ---------------------------------------------------------------------------
# ADK 2.0 Workflow graph
# ---------------------------------------------------------------------------

_safety_node = FunctionNode(func=safety_screen, name="safety_screen")
_crisis_node = FunctionNode(func=crisis_response, name="crisis_response")
_selector_node = FunctionNode(func=activity_selector, name="activity_selector")
_content_node = FunctionNode(func=content_generator, name="content_generator")
_memory_node = FunctionNode(func=memory_saver, name="memory_saver")

workflow = Workflow(
    name="mama_bloom",
    edges=[
        (START, _safety_node),
        # safety_screen → crisis_response when route == "crisis"
        Edge(from_node=_safety_node, to_node=_crisis_node, route="crisis"),
        # safety_screen → activity_selector when route == "content"
        Edge(from_node=_safety_node, to_node=_selector_node, route="content"),
        # activity_selector → content_generator (always)
        (_selector_node, _content_node),
        # content_generator → memory_saver (always)
        (_content_node, _memory_node),
    ],
)

# ADK App entrypoint — used by fast_api_app.py and agents-cli playground
# The playground expects `root_agent`; expose the workflow under that name
# via a thin Agent wrapper for CLI compatibility while keeping the Workflow
# as the canonical execution graph.
from google.adk.agents import Agent
from google.adk.apps import App

root_agent = Agent(
    name="mama_bloom_agent",
    model="gemini-2.0-flash",
    instruction=_SYSTEM_PROMPT,
)

app = App(
    root_agent=root_agent,
    name="mama-bloom",
)


# ---------------------------------------------------------------------------
# run_workflow — programmatic entry point
# ---------------------------------------------------------------------------


async def _run_workflow_async(
    week: int,
    mood: str,
    description: str,
    session_count: int = 0,
) -> dict:
    """Execute the Mama Bloom workflow and return the final state dict."""
    initial_state: dict = {
        "week": week,
        "mood": mood,
        "description": description,
        "session_count": session_count,
        "route": "",
    }

    session_service = InMemorySessionService()
    session = session_service.create_session(
        app_name="mama_bloom",
        user_id="local_user",
        state=initial_state,
    )

    runner = Runner(
        node=workflow,
        app_name="mama_bloom",
        session_service=session_service,
    )

    async for _event in runner.run_async(
        user_id="local_user",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=description or f"Week {week}, feeling {mood}")],
        ),
        state_delta=initial_state,
    ):
        pass  # consume events; final state lives in the session

    refreshed = session_service.get_session(
        app_name="mama_bloom",
        user_id="local_user",
        session_id=session.id,
    )
    return refreshed.state if refreshed else initial_state


def run_workflow(
    week: int,
    mood: str,
    description: str,
    session_count: int = 0,
) -> dict:
    """Synchronous wrapper around _run_workflow_async.

    Args:
        week: Current pregnancy week (1–42).
        mood: Mother's self-reported mood string.
        description: Free-text description that will be safety-screened.
        session_count: Number of prior sessions (used for affirmation rotation).

    Returns:
        Final state dict after all workflow nodes have executed.
    """
    return asyncio.run(
        _run_workflow_async(
            week=week,
            mood=mood,
            description=description,
            session_count=session_count,
        )
    )
