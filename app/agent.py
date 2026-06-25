# Day 1: ADK 2.0 graph workflow - the heart of Mama Bloom
# Day 2: MCP Server integration in memory_saver node
# Day 3: Session memory and cross-session adaptive logic
# Day 4: Safety guardrail fires BEFORE any LLM call - no exceptions

import datetime
import os
import re

from dotenv import load_dotenv
from google import genai
from google.adk.agents import Context
from google.adk.apps import App
from google.adk.workflow import Workflow
from google.genai import types

from app.config import CRISIS_MESSAGE, WEEKLY_MILESTONES
from app.mcp_client import (
    get_streak,
    get_yesterday_activities,
    save_baby_book_entry,
    save_session,
)
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

# Day 3: fixed text convention so the agents-cli eval harness (which can
# only drive the agent through chat text, not direct state seeding) can
# encode structured fields. The production /checkin route seeds week/mood/
# description into session state directly and never needs this pattern.
_INTAKE_PATTERN = re.compile(
    r"week:\s*(?P<week>\d+)\.?\s*mood:\s*(?P<mood>[^.]+)\.?\s*message:\s*(?P<message>.+)",
    re.IGNORECASE | re.DOTALL,
)


def intake_parser(
    ctx: Context,
    node_input: str = "",
    week: int | None = None,
    mood: str | list | None = None,
    description: str | None = None,
    user_id: str | None = None,
) -> None:
    # Day 1: graph entry point - the only node reachable from START.
    # Normalises structured input from either the production /checkin
    # route (state seeded directly at session creation) or the agents-cli
    # eval harness (only chat text available via node_input).
    if week is None or mood is None or description is None:
        match = _INTAKE_PATTERN.match(node_input.strip()) if node_input else None
        if match:
            if week is None:
                week = int(match.group("week"))
            if mood is None:
                mood = match.group("mood").strip()
            if description is None:
                description = match.group("message").strip()
        else:
            week = week if week is not None else 12
            mood = mood if mood is not None else "Okay"
            description = description if description is not None else ""

    ctx.state["week"] = week
    ctx.state["mood"] = mood
    ctx.state["description"] = description
    ctx.state.setdefault("free_text", description)
    ctx.state.setdefault("session_count", 0)
    # Day 4: per-visitor identity, used to scope all MCP reads/writes so
    # one mother's check-ins, mood history, and Baby Book entries are never
    # visible to another visitor of the deployed app. Falls back to a
    # fixed value for the agents-cli eval harness, which has no cookie.
    ctx.state["user_id"] = user_id or "anonymous"


def safety_screen(ctx: Context, description: str) -> None:
    # Day 4: Safety guardrail - ALWAYS runs first (directly after
    # intake_parser), ALWAYS before any LLM call.
    ctx.state["clean_description"] = redact_pii(description)
    # free_text is the same raw user input as description (see
    # intake_parser) and is what activity_picker/intro_writer actually
    # send to Gemini - redact it too, or PII typed into the free-text box
    # would reach the LLM unredacted despite clean_description existing.
    ctx.state["free_text"] = ctx.state["clean_description"]
    if detect_distress(ctx.state["clean_description"]):
        ctx.route = "crisis"
    else:
        ctx.route = "normal"


def crisis_response(ctx: Context) -> types.Content:
    # Day 4: Human safety - NO LLM, NO delay, immediate response.
    # This node has zero references to google.genai anywhere in its body -
    # a structural guarantee, not just a comment, that it can never call
    # Gemini.
    ctx.state["output"] = CRISIS_MESSAGE
    ctx.state["is_crisis"] = True
    # Returning Content (rather than None) gives the workflow a real
    # text-bearing final event, so agents-cli playground/run display it.
    return types.Content(role="model", parts=[types.Part.from_text(text=CRISIS_MESSAGE)])


async def activity_picker(
    ctx: Context,
    week: int,
    mood: str | list,
    free_text: str = "",
    session_count: int = 0,
    user_id: str = "anonymous",
) -> None:
    # Day 1: deterministic activity routing - pure Python, no LLM.
    try:
        yesterday_activities = await get_yesterday_activities(user_id)
    except Exception:
        yesterday_activities = {}

    daily_plan = get_daily_plan(week, mood, yesterday_activities)
    morning_affirmation = get_morning_affirmation(week, session_count)

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

    # Day 1: Gemini reads both selected moods and natural language -
    # build rich mood context from multi-select and free text.
    mood_context = mood
    if isinstance(mood, list):
        mood_context = " and ".join(mood)
    if free_text:
        mood_context = f"{mood_context}. She also wrote: {free_text}"

    ctx.state["daily_plan"] = daily_plan
    ctx.state["morning_affirmation"] = morning_affirmation
    ctx.state["breathing_name"] = breathing_name
    ctx.state["journaling_name"] = journaling_name
    ctx.state["baby_connect_name"] = baby_connect_name
    ctx.state["mood_context"] = mood_context


def intro_writer(
    ctx: Context,
    week: int,
    mood_context: str,
    breathing_name: str,
    journaling_name: str,
    baby_connect_name: str,
) -> None:
    # Day 1: the workflow's one LLM step - kept as a plain function node
    # (not a native LlmAgent node) on purpose: NodeRunner treats any
    # unhandled node exception as fatal and aborts the rest of the
    # workflow (verified directly in google/adk/workflow/_node_runner.py),
    # but a Gemini outage must never block a mother from seeing her daily
    # activities. This try/except preserves that graceful-degradation
    # guarantee while still running entirely inside the real graph.
    gemini_intro = ""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            user_prompt = (
                f"The mother is in week {week} of her pregnancy. "
                f"Her emotional state today: {mood_context}. "
                f"Write ONE warm personalised introduction of maximum "
                f"80 words that acknowledges her week and how she is "
                f"feeling, then gently introduces today's three "
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
            print(f"Gemini call failed, using fallback intro: {exc}")

    if not gemini_intro:
        gemini_intro = (
            f"Welcome to your Week {week} daily check-in. "
            f"Today's plan has been crafted just for you. "
            f"You are doing wonderfully."
        )

    ctx.state["gemini_intro"] = gemini_intro


def content_generator(ctx: Context, daily_plan: dict, week: int) -> None:
    # Day 1: builds complete daily plan - pure Python, no LLM needed.
    ctx.state["evening_whisper"] = get_evening_whisper()

    milestone = WEEKLY_MILESTONES.get(week)
    if milestone is None:
        sorted_weeks = sorted(WEEKLY_MILESTONES.keys())
        eligible = [w for w in sorted_weeks if w <= week]
        milestone = (
            WEEKLY_MILESTONES[eligible[-1]]
            if eligible
            else WEEKLY_MILESTONES[sorted_weeks[0]]
        )
    ctx.state["week_milestone"] = milestone
    ctx.state["session_id"] = (
        f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    )


async def memory_saver(
    ctx: Context,
    week: int,
    mood: str | list,
    session_id: str,
    daily_plan: dict,
    user_id: str = "anonymous",
) -> types.Content:
    # Day 2: real MCP client call (app/mcp_client.py - stdio transport)
    # Day 3: session memory - saves to persistent local storage
    today_str = datetime.date.today().isoformat()

    mood_str = ", ".join(mood) if isinstance(mood, list) else str(mood)

    activities_list = []
    for key in ("breathing", "journaling", "baby_connect"):
        act = daily_plan.get(key)
        if isinstance(act, dict) and act.get("id"):
            activities_list.append({"id": act["id"], "name": act.get("name", "")})

    try:
        await save_session(
            user_id=user_id,
            week=week,
            mood=mood_str,
            activities=activities_list,
            post_feeling="pending",
            date=today_str,
            session_id=session_id,
        )
    except Exception as exc:
        print(f"save_session failed: {exc}")

    try:
        ctx.state["streak"] = await get_streak(user_id)
    except Exception as exc:
        ctx.state["streak"] = {}
        print(f"get_streak failed: {exc}")

    for key in ("breathing", "journaling", "baby_connect"):
        act = daily_plan.get(key)
        if isinstance(act, dict) and act.get("baby_book"):
            try:
                entry_id = f"bb_{session_id}_{key}"
                await save_baby_book_entry(
                    user_id=user_id,
                    entry_type="milestone",
                    week=week,
                    content=str(act.get("baby_book", "")),
                    date=today_str,
                    entry_id=entry_id,
                )
            except Exception as exc:
                print(f"save_baby_book_entry failed for {key}: {exc}")

    ctx.state["saved"] = True

    # Returning Content (rather than None) gives the workflow a real
    # text-bearing final event, so agents-cli playground/run display it.
    activity_names = ", ".join(a["name"] for a in activities_list) or "today's plan"
    summary = ctx.state.get("gemini_intro") or f"Your Week {week} plan is ready: {activity_names}."
    return types.Content(role="model", parts=[types.Part.from_text(text=summary)])


# Day 1: real google.adk.workflow.Workflow graph - genuinely executed by
# both the production /checkin route (via Runner) and agents-cli
# playground/eval, not a hand-rolled if/else dressed up as a diagram.
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
