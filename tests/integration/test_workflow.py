"""Integration tests against the real ADK Workflow graph in app/agent.py.

Drives the workflow through a genuine google.adk.runners.Runner - the same
entrypoint agents-cli playground/eval and the production /checkin route use -
rather than calling internal functions directly. GEMINI_API_KEY is removed
so intro_writer deterministically falls back (proving the graceful-degradation
guarantee) instead of depending on network access.

start_mcp_client/stop_mcp_client are called within the same test coroutine
(not a split fixture) because the underlying anyio stdio transport requires
its task group to be entered and exited from the same asyncio Task - a
yield-based pytest fixture runs teardown as a separate task and trips that
restriction.
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent
from app.mcp_client import start_mcp_client, stop_mcp_client

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)


@asynccontextmanager
async def mcp_client_session():
    await start_mcp_client(project_root=_PROJECT_ROOT)
    try:
        yield
    finally:
        await stop_mcp_client()


async def _run_checkin(monkeypatch, *, week, mood, description, free_text=""):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent, session_service=session_service, app_name="test"
    )
    session = await session_service.create_session(
        app_name="test",
        user_id="test_user",
        state={
            "week": week,
            "mood": mood,
            "description": description,
            "free_text": free_text,
            "session_count": 0,
        },
    )
    placeholder = types.Content(role="user", parts=[types.Part.from_text(text="checkin")])
    async for _event in runner.run_async(
        user_id="test_user", session_id=session.id, new_message=placeholder
    ):
        pass
    final = await session_service.get_session(
        app_name="test", user_id="test_user", session_id=session.id
    )
    return dict(final.state)


def _cleanup_session_file(session_id: str) -> None:
    sessions_dir = Path(_PROJECT_ROOT) / "data" / "sessions"
    baby_book_dir = Path(_PROJECT_ROOT) / "data" / "baby_book"

    session_path = sessions_dir / f"session_{session_id}.json"
    if session_path.exists():
        session_path.unlink()

    # memory_saver also writes a baby_book entry for any activity with a
    # "baby_book" field (e.g. breathing activities) - clean those up too.
    for entry_path in baby_book_dir.glob(f"entry_bb_{session_id}_*.json"):
        entry_path.unlink()


@pytest.mark.asyncio
async def test_crisis_path_through_real_runner(monkeypatch):
    # Crisis path terminates before intro_writer/memory_saver, so it needs
    # no Gemini call and never touches the MCP client either - this is the
    # structural guarantee the README claims, proven end-to-end here.
    async with mcp_client_session():
        state = await _run_checkin(
            monkeypatch,
            week=28,
            mood="Heavy",
            description="I feel hopeless and can't do this anymore",
        )
    assert state["is_crisis"] is True
    assert "9152987821" in state["output"]
    assert "1860-2662-345" in state["output"]


@pytest.mark.asyncio
async def test_normal_path_through_real_runner_saves_via_mcp(monkeypatch):
    async with mcp_client_session():
        state = await _run_checkin(
            monkeypatch,
            week=20,
            mood="Good",
            description="Feeling okay today",
        )
    try:
        assert not state.get("is_crisis")
        assert state["daily_plan"]["breathing"]["id"]
        assert state["daily_plan"]["journaling"]["id"]
        assert state["daily_plan"]["baby_connect"]["id"]
        # intro_writer always produces a non-empty intro — either from Vertex AI
        # (which is now the fallback when no GEMINI_API_KEY is set) or from the
        # static fallback string, proving graceful degradation in both paths.
        assert state["gemini_intro"]
        assert state["saved"] is True

        session_path = (
            Path(_PROJECT_ROOT)
            / "data"
            / "sessions"
            / f"session_{state['session_id']}.json"
        )
        assert session_path.exists()
        saved = json.loads(session_path.read_text(encoding="utf-8"))
        assert saved["week"] == 20
        assert saved["mood"] == "Good"
    finally:
        _cleanup_session_file(state["session_id"])


@pytest.mark.asyncio
async def test_intake_parser_handles_chat_text_for_eval_harness(monkeypatch):
    # The agents-cli eval harness can only drive the agent through chat
    # text, not direct state seeding - this is the convention intake_parser
    # documents in tests/eval/datasets/README.md.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    async with mcp_client_session():
        session_service = InMemorySessionService()
        runner = Runner(
            agent=root_agent, session_service=session_service, app_name="test"
        )
        session = await session_service.create_session(app_name="test", user_id="u")
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="Week: 28. Mood: Heavy. Message: I feel hopeless and can't do this anymore"
            )],
        )
        async for _event in runner.run_async(
            user_id="u", session_id=session.id, new_message=message
        ):
            pass
        final = await session_service.get_session(
            app_name="test", user_id="u", session_id=session.id
        )
    state = dict(final.state)
    assert state["is_crisis"] is True
    assert state["week"] == 28
