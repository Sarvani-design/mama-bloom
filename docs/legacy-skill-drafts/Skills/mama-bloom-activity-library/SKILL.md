---
name: mama-bloom-activity-library
description: >
  ALWAYS use this skill when working on config.py, activity selection logic,
  routing rules, mood-to-activity mapping, trimester rules, the get_daily_plan
  function, morning affirmations, evening whispers, letter activities, or
  weekly milestones in Mama Bloom. Also triggers when adding new activities,
  changing mood options, or debugging why the wrong activity was served.
  This is the authoritative source for all 24 activities, their metadata,
  and every routing rule.
---

# Mama Bloom — Activity Library & Routing Skill

## Activity Structure — Every Activity Must Have These Keys

```python
{
    "id": str,              # unique snake_case
    "name": str,            # display name for UI
    "category": str,        # "breathing"|"journaling"|"baby_connect"|"creative"|"music"
    "stars": int,           # 3, 4, or 5
    "duration_min": int,
    "duration_max": int,
    "trimester_min": int,   # 1, 2, or 3
    "week_min": int,        # 0 = available from start
    "week_max": int,        # 42 = available until end
    "moods": list[str],     # moods this suits, or ["all"]
    "description": str,     # warm 2-sentence instruction
    "prompt": str,          # exact text shown to mother
    "science_note": str,    # one-sentence citation
    "baby_book": bool,
    "pillar": str,          # "breathing"|"journaling"|"baby_connect"
}
```

---

## 8 Valid Mood Values

```python
VALID_MOODS = [
    "anxious", "heavy", "sad",          # difficult moods
    "okay", "tired", "uncomfortable",   # neutral/physical
    "good", "glowing",                  # positive moods
]
```

---

## Phase 1 — 12 Activities (Build First, Verify Working)

### PILLAR 1: BREATHING (pick 1 per day)

| ID | Name | Weeks | Best Moods |
|----|------|-------|------------|
| `box_breathing` | Box Breathing 4-4-4-4 | 0–42 | anxious, heavy, okay, good, glowing, tired, uncomfortable |
| `extended_exhale` | Extended Exhale 4-7-8 | 0–42 | tired, uncomfortable, anxious, heavy |
| `body_scan` | Body Scan Relaxation | 0–42 | heavy, anxious, okay, good, uncomfortable |
| `morning_affirmation` | Morning Affirmation | 0–42 | all (fixed daily element) |

### PILLAR 2: JOURNALING (pick 1 per day)

| ID | Name | Weeks | Best Moods |
|----|------|-------|------------|
| `free_mood_journal` | Free Mood Journal | 0–42 | okay, good, glowing, anxious, heavy |
| `gratitude_journal` | Gratitude Journal | 0–42 | okay, good, glowing, tired, uncomfortable |
| `self_compassion` | Self-Compassion Check-In | 0–42 | heavy, sad, anxious, tired |

### PILLAR 3: BABY CONNECT (pick 1 per day)

| ID | Name | Weeks | Notes |
|----|------|-------|-------|
| `daily_narration` | Daily Narration | 18–42 | voice-based |
| `evening_whisper` | Evening Whisper | 0–42 | fixed closing element |
| `calming_music` | Calming Music | 0–42 | music-only on tired/uncomfortable |
| `first_letter` | First Letter to Baby | 0–13 | triggered once, T1 only |
| `weekly_milestone_letter` | Weekly Milestone Letter | 0–42 | Day 7 only |

---

## Phase 2 — 12 More Activities (After Phase 1 Verified)

| ID | Pillar | Week Min | Notes |
|----|--------|----------|-------|
| `pmr` | breathing | 14 | Progressive Muscle Relaxation |
| `safe_place` | breathing | 0 | Safe Place Visualization |
| `loving_kindness` | breathing | 0 | Loving-Kindness Meditation |
| `birth_wishes` | journaling | 14 | good/glowing moods only |
| `labour_prep_affirmations` | breathing | 28 | replaces morning affirmation |
| `hope_letter` | baby_connect | 14–27 | triggered once, T2 only |
| `hard_day_letter` | baby_connect | 0 | triggered on heavy/sad mood |
| `story_time` | baby_connect | 18 | voice-based |
| `humming_singing` | baby_connect | 18 | voice-based |
| `conversation_with_baby` | baby_connect | 14 | voice-based |
| `bilateral_drawing` | baby_connect | 0 | pre-Week 18 creative alternate |
| `symmetry_drawing` | baby_connect | 0 | pre-Week 18 creative alternate |

---

## Routing Rules — get_daily_plan() in tools.py

```python
def get_daily_plan(week: int, mood: str, yesterday: dict = None) -> list[str]:
    """
    Returns [breathing_id, journaling_id, baby_connect_id]
    Applies all routing rules in order.
    """
    yesterday = yesterday or {}

    breathing = _pick_breathing(mood, week, yesterday.get("breathing"))
    journaling = _pick_journaling(mood, week, yesterday.get("journaling"))
    baby_connect = _pick_baby_connect(mood, week, yesterday.get("baby_connect"))

    return [breathing, journaling, baby_connect]
```

### Mood → Breathing Mapping
```python
MOOD_TO_BREATHING = {
    "anxious":       ["box_breathing", "safe_place", "loving_kindness"],
    "heavy":         ["box_breathing", "loving_kindness", "body_scan"],
    "sad":           ["loving_kindness", "body_scan", "safe_place"],
    "okay":          ["body_scan", "safe_place", "box_breathing"],
    "good":          ["safe_place", "loving_kindness", "body_scan"],
    "glowing":       ["safe_place", "body_scan", "loving_kindness"],
    "tired":         ["extended_exhale", "body_scan", "pmr"],
    "uncomfortable": ["extended_exhale", "pmr", "box_breathing"],
}
# Pick first available that was NOT used yesterday
```

### Mood → Journaling Mapping
```python
MOOD_TO_JOURNALING = {
    "anxious":       ["self_compassion", "gratitude_journal"],
    "heavy":         ["self_compassion", "free_mood_journal"],
    "sad":           ["self_compassion", "free_mood_journal"],
    "okay":          ["gratitude_journal", "free_mood_journal"],
    "good":          ["gratitude_journal", "free_mood_journal", "birth_wishes"],
    "glowing":       ["free_mood_journal", "birth_wishes", "gratitude_journal"],
    "tired":         ["gratitude_journal"],
    "uncomfortable": ["free_mood_journal", "gratitude_journal"],
}
# HARD RULE: self_compassion and free_mood_journal NEVER on same day
```

### Mood → Baby Connect Mapping
```python
MOOD_TO_BABY_CONNECT = {
    "anxious":       ["bilateral_drawing", "conversation_with_baby"],
    "heavy":         ["bilateral_drawing", "symmetry_drawing"],
    "sad":           ["conversation_with_baby", "daily_narration"],
    "okay":          ["daily_narration", "story_time", "humming_singing"],
    "good":          ["story_time", "humming_singing", "daily_narration"],
    "glowing":       ["humming_singing", "story_time", "daily_narration"],
    "tired":         ["calming_music"],
    "uncomfortable": ["calming_music"],
}
# Pre-Week 18: replace ALL voice activities with creative alternates
# tired/uncomfortable: calming_music ONLY — no other baby_connect
```

---

## Trimester Hard Rules — Apply These Before Serving Any Activity

```python
TRIMESTER_RULES = {
    "pmr":                      {"week_min": 14},
    "birth_wishes":             {"week_min": 14},
    "daily_narration":          {"week_min": 18},
    "story_time":               {"week_min": 18},
    "humming_singing":          {"week_min": 18},
    "conversation_with_baby":   {"week_min": 14},
    "labour_prep_affirmations": {"week_min": 28},
    "first_letter":             {"week_max": 13, "trigger": "once"},
    "hope_letter":              {"week_min": 14, "week_max": 27, "trigger": "once"},
    "hard_day_letter":          {"trigger": "mood", "moods": ["heavy", "sad"]},
    "weekly_milestone_letter":  {"trigger": "day_7"},
}

def is_activity_available(activity_id: str, week: int) -> bool:
    """Check trimester rules before serving any activity."""
    rules = TRIMESTER_RULES.get(activity_id, {})
    if "week_min" in rules and week < rules["week_min"]:
        return False
    if "week_max" in rules and week > rules["week_max"]:
        return False
    return True
```

---

## Fixed Daily Elements (not in pillar rotation)

### Morning Affirmations — Pick 1, never repeat within a week
```python
MORNING_AFFIRMATIONS = [
    "I am doing something remarkable. It is okay that it is hard.",
    "My body knows more than I give it credit for.",
    "I do not have to have it all figured out to be a good mother.",
    "Today I give myself permission to feel whatever I feel.",
    "I am not behind. I am exactly where I need to be.",
    "Growing a person is not small. It is the largest thing.",
    "I can be uncertain and still be capable.",
    "My baby does not need a perfect mother. They need me.",
    "Some days are hard. Hard days are still days I showed up.",
    "I am allowed to rest. Rest is part of the work.",
    "Every breath I take is a breath we share.",
    "I trust my body even when it surprises me.",
    "I am becoming someone new. That takes time.",
    "What I feel matters. I matter.",
]

# Week 28+: replace with LABOUR_PREP_AFFIRMATIONS
LABOUR_PREP_AFFIRMATIONS = [
    "My body was made to do this.",
    "Each wave brings my baby closer to me.",
    "I can do hard things. I have done hard things.",
    "I trust the process even when it is intense.",
    "I am strong, and I am ready to meet you.",
]
```

### Evening Whispers — Rotate through list
```python
EVENING_WHISPERS = [
    "Today I did my best, little one.",
    "You are so loved already.",
    "We made it through today together.",
    "I am learning, and that is enough.",
    "You are safe, and so am I.",
    "Thank you for growing so beautifully.",
    "Tomorrow we get to try again.",
    "I thought about you all day today.",
]
```

---

## Weekly Milestones — Used in Letter Prompts

```python
WEEKLY_MILESTONES = {
    4:  "you are the size of a poppy seed and your heart has begun to beat",
    8:  "your fingers are forming and you can make tiny movements",
    12: "you can yawn, stretch, and open your fingers",
    16: "you can hear sounds from the outside world for the first time",
    18: "my voice is now the most familiar sound in your world",
    20: "we are halfway there, little one",
    22: "you can feel light through my belly",
    24: "your face is fully formed now",
    28: "you can dream. I wonder what you dream about.",
    32: "you are practicing breathing, getting ready",
    36: "you are nearly here. I can hardly wait.",
    40: "any day now. I am ready to meet you.",
}

def get_milestone_for_week(week: int) -> str:
    """Return closest milestone at or before current week."""
    milestones = sorted(WEEKLY_MILESTONES.keys())
    best = 4
    for m in milestones:
        if m <= week:
            best = m
    return WEEKLY_MILESTONES[best]
```

---

## Exclusion Rules

```python
# These two activities must NEVER appear on the same day
EXCLUSIVE_PAIRS = [
    ("self_compassion", "free_mood_journal"),
]

# Voice activities unavailable before Week 18
VOICE_ACTIVITIES = ["daily_narration", "story_time", "humming_singing"]

# Creative alternates for pre-Week 18 baby_connect slot
PRE_18_ALTERNATES = ["bilateral_drawing", "symmetry_drawing", "calming_music"]

# Music-only condition
MUSIC_ONLY_MOODS = ["tired", "uncomfortable"]
```

---

## Baby Book Flags

Activities that save to Baby Book (`"baby_book": True`):
- `first_letter` — once, T1
- `hope_letter` — once, T2
- `hard_day_letter` — on heavy/sad days
- `weekly_milestone_letter` — every Day 7
- `weekly_reflection` — every Day 7

All others: `"baby_book": False`
