# Day 4: Safety functions and routing logic - pure Python, no LLM calls

import datetime
import re

from app.config import (
    BABY_CONNECT_ACTIVITIES,
    BREATHING_ACTIVITIES,
    CREATIVE_ALTERNATES,
    DISTRESS_KEYWORDS,
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


def get_daily_plan(week: int, mood: str, yesterday_activities: dict) -> dict:
    # Day 1: Activity routing logic for ADK 2.0 agent
    mood_key = mood.lower().strip()

    # Get preferred activity IDs based on user mood
    pref_breathing = MOOD_TO_BREATHING.get(mood_key, [])
    pref_journaling = MOOD_TO_JOURNALING.get(mood_key, [])
    pref_baby_connect = MOOD_TO_BABY_CONNECT.get(mood_key, [])

    # 1. Breathing activity selection
    breathing_candidates = [
        act
        for act in BREATHING_ACTIVITIES
        if act["id"] in pref_breathing
        and isinstance(act["week_min"], int)
        and isinstance(act["week_max"], int)
        and act["week_min"] <= week <= act["week_max"]
    ]
    if not breathing_candidates:
        breathing_candidates = [
            act
            for act in BREATHING_ACTIVITIES
            if isinstance(act["week_min"], int)
            and isinstance(act["week_max"], int)
            and act["week_min"] <= week <= act["week_max"]
        ]

    # Variety filter
    yesterday_breathing = yesterday_activities.get("breathing")
    filtered_breathing = [
        act for act in breathing_candidates if act["id"] != yesterday_breathing
    ]
    selected_breathing = (
        filtered_breathing[0]
        if filtered_breathing
        else (breathing_candidates[0] if breathing_candidates else None)
    )

    # 2. Journaling activity selection
    journaling_candidates = [
        act
        for act in JOURNALING_ACTIVITIES
        if act["id"] in pref_journaling
        and isinstance(act["week_min"], int)
        and week >= act["week_min"]
    ]
    if not journaling_candidates:
        journaling_candidates = [
            act
            for act in JOURNALING_ACTIVITIES
            if isinstance(act["week_min"], int) and week >= act["week_min"]
        ]

    # Variety filter
    yesterday_journaling = yesterday_activities.get("journaling")
    filtered_journaling = [
        act for act in journaling_candidates if act["id"] != yesterday_journaling
    ]
    selected_journaling = (
        filtered_journaling[0]
        if filtered_journaling
        else (journaling_candidates[0] if journaling_candidates else None)
    )

    # 3. Baby connect activity selection
    yesterday_baby_connect = yesterday_activities.get("baby_connect")
    if week < 18:
        # Pre-week 18: Swap to creative alternates
        candidates = [
            act
            for act in CREATIVE_ALTERNATES
            if isinstance(act["week_min"], int) and week >= act["week_min"]
        ]
        filtered_candidates = [
            act for act in candidates if act["id"] != yesterday_baby_connect
        ]
        selected_baby_connect = (
            filtered_candidates[0]
            if filtered_candidates
            else (candidates[0] if candidates else None)
        )
    else:
        # Week 18+: Spoken voice activities allowed
        candidates = [
            act
            for act in BABY_CONNECT_ACTIVITIES
            if act["id"] in pref_baby_connect
            and isinstance(act["week_min"], int)
            and week >= act["week_min"]
        ]
        if not candidates:
            candidates = [
                act
                for act in BABY_CONNECT_ACTIVITIES
                if isinstance(act["week_min"], int) and week >= act["week_min"]
            ]
        filtered_candidates = [
            act for act in candidates if act["id"] != yesterday_baby_connect
        ]
        selected_baby_connect = (
            filtered_candidates[0]
            if filtered_candidates
            else (candidates[0] if candidates else None)
        )

    # 4. Milestone & Trimester
    trimester = get_trimester(week)
    milestone = WEEKLY_MILESTONES.get(week)

    # 5. Calming music (tired/uncomfortable moods only)
    selected_music = None
    if mood_key in ["tired", "uncomfortable"]:
        selected_music = MUSIC_ACTIVITY

    return {
        "breathing": selected_breathing,
        "journaling": selected_journaling,
        "baby_connect": selected_baby_connect,
        "trimester": trimester,
        "week_milestone": milestone,
        "music": selected_music,
    }


def get_morning_affirmation(week: int, session_count: int) -> str:
    # Returns appropriate affirmation based on trimester
    if week >= 28:
        return "My body is wise and knows how to bring my baby into the world. I trust the process and breathe through each wave."

    idx = session_count % len(MORNING_AFFIRMATIONS)
    return MORNING_AFFIRMATIONS[idx]


def get_evening_whisper() -> str:
    sentences = [
        "Today I did my best, little one.",
        "You are so loved already.",
        "We made it through today together.",
        "I am learning, and that is enough.",
        "You are safe, and so am I.",
        "Thank you for growing so beautifully.",
        "Tomorrow we get to try again.",
    ]
    # Rotate by day of the week (0 = Monday, 6 = Sunday)
    day_index = datetime.date.today().weekday()
    return sentences[day_index]
