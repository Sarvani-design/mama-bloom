"""Deterministic safety/routing tests against the real app/tools.py logic.

No LLM, no network, no agents-cli — these must always be fast and green.
Parametrized from tests/eval/datasets/mama-bloom-mechanical-cases.json.
"""

import pytest

from app.tools import detect_distress, get_daily_plan, redact_pii


def _by_id(scenarios, scenario_id):
    return next(s for s in scenarios if s["id"] == scenario_id)


def test_redact_pii_removes_phone_number():
    text = "Call me at 9876543210 I need help"
    redacted = redact_pii(text)
    assert "9876543210" not in redacted
    assert "[REDACTED_PHONE]" in redacted


def test_redact_pii_removes_email():
    text = "Reach me at mother@example.com please"
    redacted = redact_pii(text)
    assert "mother@example.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted


def test_redact_pii_leaves_clean_text_unchanged():
    text = "I feel overwhelmed and scared"
    assert redact_pii(text) == text


@pytest.mark.parametrize(
    "scenario_id,expect_crisis",
    [
        ("test_1", False),
        ("test_2", False),
        ("test_3", False),
        ("test_4_safety", True),
        ("test_5_pii", False),
    ],
)
def test_safety_routing(mechanical_scenarios, scenario_id, expect_crisis):
    scenario = _by_id(mechanical_scenarios, scenario_id)
    description = scenario["input"]["description"]
    routed_to_crisis = detect_distress(redact_pii(description))
    assert routed_to_crisis is expect_crisis


def test_pii_scenario_phone_never_reaches_distress_check(mechanical_scenarios):
    scenario = _by_id(mechanical_scenarios, "test_5_pii")
    description = scenario["input"]["description"]
    clean = redact_pii(description)
    assert "9876543210" not in clean


def test_anxious_mood_picks_documented_breathing_activity(mechanical_scenarios):
    scenario = _by_id(mechanical_scenarios, "test_1")
    week = scenario["input"]["week"]
    mood = scenario["input"]["mood"]
    plan = get_daily_plan(week, mood, {})
    assert plan["breathing"]["id"] in scenario["expected"]["breathing_options"]


def test_tired_uncomfortable_mood_routes_to_calming_music(mechanical_scenarios):
    scenario = _by_id(mechanical_scenarios, "test_3")
    week = scenario["input"]["week"]
    mood = scenario["input"]["mood"]
    plan = get_daily_plan(week, mood, {})
    assert plan["baby_connect"]["id"] == scenario["expected"]["baby_connect"]


@pytest.mark.parametrize("mood", ["Heavy", "Okay", "Good", "Glowing", "Tired", "Uncomfortable"])
def test_every_ui_mood_chip_produces_real_activities(mood):
    """Regression test: all 6 homepage mood chips must resolve to real
    activities, not empty dicts (see config.py's MOOD_TO_* dicts vs.
    tools.py's mood_map translation)."""
    plan = get_daily_plan(20, mood, {})
    assert plan["breathing"].get("id")
    assert plan["journaling"].get("id")
    assert plan["baby_connect"].get("id")


def test_yesterday_variety_rule_avoids_repeat_breathing_activity():
    # "anxious" has 3 breathing candidates, so the variety rule has room
    # to actually exclude yesterday's pick (moods with only 1 candidate,
    # like "tired", deliberately fall back to repeating it).
    plan = get_daily_plan(20, "anxious", {"breathing": "box_breathing"})
    assert plan["breathing"].get("id") != "box_breathing"


def test_self_compassion_and_free_mood_journal_are_mutually_exclusive():
    plan_after_self_compassion = get_daily_plan(
        20, "Heavy", {"journaling": "self_compassion"}
    )
    assert plan_after_self_compassion["journaling"].get("id") != "self_compassion"

    plan_after_free_mood = get_daily_plan(
        20, "Heavy", {"journaling": "free_mood_journal"}
    )
    assert plan_after_free_mood["journaling"].get("id") != "free_mood_journal"
