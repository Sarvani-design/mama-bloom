# Day 4: Safety functions and routing logic - pure Python, no LLM calls

import datetime
import random
import re

from app.config import (
    BABY_CONNECT_ACTIVITIES,
    BREATHING_ACTIVITIES,
    CREATIVE_ALTERNATES,
    DISTRESS_KEYWORDS,
    EVENING_WHISPERS,
    FREE_TEXT_KEYWORD_OVERRIDES,
    JOURNALING_ACTIVITIES,
    MOOD_TO_BABY_CONNECT,
    MOOD_TO_BREATHING,
    MOOD_TO_JOURNALING,
    MORNING_AFFIRMATIONS,
    MUSIC_ACTIVITY,
    WEEKLY_MILESTONES,
)


def redact_pii(text: str) -> str:
    # Day 4: PII redaction - runs in safety_screen before any LLM call
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    # Match standard 10-digit numbers, numbers with spaces/hyphens, and international country codes
    phone_pattern = r"(\+?\b(?:\d{1,4}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b|\b\d{10}\b)"

    redacted_text = text
    redacted_emails, email_count = re.subn(
        email_pattern, "[REDACTED_EMAIL]", redacted_text
    )
    redacted_phones, phone_count = re.subn(
        phone_pattern, "[REDACTED_PHONE]", redacted_emails
    )

    if email_count > 0 or phone_count > 0:
        print("PII redacted before LLM call")
    return redacted_phones


def detect_distress(text: str) -> bool:
    # Day 4: Safety guardrail - pure Python, no LLM
    lowercased = text.lower()
    for keyword in DISTRESS_KEYWORDS:
        if keyword in lowercased:
            return True
    return False


def get_trimester(week: int) -> int:
    if week <= 13:
        return 1
    elif week <= 27:
        return 2
    else:
        return 3


def _find_activity_by_id(act_id: str) -> dict:
    """Look up a full activity dict by its id across all pools."""
    all_acts = (
        BREATHING_ACTIVITIES
        + JOURNALING_ACTIVITIES
        + BABY_CONNECT_ACTIVITIES
        + CREATIVE_ALTERNATES
        + [MUSIC_ACTIVITY]
    )
    return next((a for a in all_acts if a.get("id") == act_id), {})


def get_daily_plan(
    week: int,
    mood: str | list,
    yesterday_activities: dict,
    free_text: str = "",
) -> dict:
    # Day 1: Activity routing logic for ADK 2.0 agent
    # Accepts mood as single string or list for multi-select support

    # Normalise mood to a single primary mood string for routing
    if isinstance(mood, list) and len(mood) > 0:
        primary_mood = mood[0].lower()
    elif isinstance(mood, str):
        primary_mood = mood.lower()
    else:
        primary_mood = "okay"

    # Map UI mood-chip labels to the closest mood category that actually
    # has routing entries in config.py's MOOD_TO_* dicts.
    mood_map = {
        "heavy": "sad",
        "okay": "tired",
        "good": "happy",
        "glowing": "excited",
        "tired": "tired",
        "uncomfortable": "uncomfortable",
        "anxious": "anxious",
        "sad": "sad",
    }
    primary_mood = mood_map.get(primary_mood, "okay")

    trimester = get_trimester(week)

    # Get yesterday's activity IDs to enforce variety rule
    yesterday_breathing = yesterday_activities.get("breathing", "")
    yesterday_journaling = yesterday_activities.get("journaling", "")
    yesterday_baby = yesterday_activities.get("baby_connect", "")

    def pick_activity(candidates: list, all_activities: list, yesterday_id: str) -> dict:
        available = [
            a for a in all_activities
            if a["id"] in candidates
            and a["id"] != yesterday_id
            and week >= a.get("week_min", 0)
            and week <= a.get("week_max", 42)
        ]
        if not available:
            available = [
                a for a in all_activities
                if a["id"] in candidates
                and week >= a.get("week_min", 0)
                and week <= a.get("week_max", 42)
            ]
        return available[0] if available else {}

    # Select breathing activity
    breathing_candidates = MOOD_TO_BREATHING.get(
        primary_mood,
        MOOD_TO_BREATHING.get("okay", [])
    )
    breathing = pick_activity(
        breathing_candidates,
        BREATHING_ACTIVITIES,
        yesterday_breathing
    )

    # Select journaling activity
    # Enforce exclusive rule: self_compassion and free_mood_journal
    # never on same day
    journaling_candidates = MOOD_TO_JOURNALING.get(
        primary_mood,
        MOOD_TO_JOURNALING.get("okay", [])
    )
    if yesterday_journaling == "self_compassion":
        journaling_candidates = [
            j for j in journaling_candidates
            if j != "self_compassion"
        ]
    if yesterday_journaling == "free_mood_journal":
        journaling_candidates = [
            j for j in journaling_candidates
            if j != "free_mood_journal"
        ]
    journaling = pick_activity(
        journaling_candidates,
        JOURNALING_ACTIVITIES,
        yesterday_journaling
    )

    # Select baby connect activity
    # Tired or uncomfortable — music only
    if primary_mood in ("tired", "uncomfortable"):
        baby_connect = MUSIC_ACTIVITY
    elif week < 18:
        # Pre week 18 — use creative alternates
        baby_connect = pick_activity(
            [a["id"] for a in CREATIVE_ALTERNATES],
            CREATIVE_ALTERNATES,
            yesterday_baby
        )
    else:
        baby_candidates = MOOD_TO_BABY_CONNECT.get(
            primary_mood,
            MOOD_TO_BABY_CONNECT.get("okay", [])
        )
        baby_connect = pick_activity(
            baby_candidates,
            BABY_CONNECT_ACTIVITIES,
            yesterday_baby
        )

    # Get week milestone
    sorted_weeks = sorted(WEEKLY_MILESTONES.keys())
    eligible = [w for w in sorted_weeks if w <= week]
    milestone = (
        WEEKLY_MILESTONES[eligible[-1]]
        if eligible
        else WEEKLY_MILESTONES[sorted_weeks[0]]
    )

    result = {
        "breathing": breathing,
        "journaling": journaling,
        "baby_connect": baby_connect,
        "trimester": trimester,
        "week_milestone": milestone,
        "primary_mood": primary_mood,
    }

    # Research-based free-text keyword override (config.FREE_TEXT_KEYWORD_OVERRIDES).
    # Scans the mother's optional remarks for specific physical symptoms or emotional
    # signals and swaps the relevant activity to the research-recommended choice.
    # First matching keyword group wins; partial word match is intentional (e.g.,
    # "frustrat" catches both "frustrated" and "frustrating").
    if free_text:
        ft_lower = free_text.lower()
        for keywords, overrides in FREE_TEXT_KEYWORD_OVERRIDES:
            if any(kw in ft_lower for kw in keywords):
                for category, act_id in overrides.items():
                    act = _find_activity_by_id(act_id)
                    if act:
                        result[category] = act
                break

    return result

def get_morning_affirmation(week: int, session_count: int = 0) -> str:
    # Third-trimester mothers get a birth-preparation focused affirmation
    if week >= 28:
        t3_affirmations = [
            "My body is wise and knows how to bring my baby into the world. I trust the process and breathe through each wave.",
            "Millions of women before me have done this. My body holds that ancient knowing.",
            "I am strong, I am ready, and my baby and I will do this together.",
        ]
        return random.choice(t3_affirmations)
    return random.choice(MORNING_AFFIRMATIONS)


def get_evening_whisper() -> str:
    return random.choice(EVENING_WHISPERS)
