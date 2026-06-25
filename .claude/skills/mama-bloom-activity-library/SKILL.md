---
name: mama-bloom-activity-library
description: >
  ALWAYS use this skill when working on app/config.py's activity lists or
  MOOD_TO_* routing dicts, app/tools.py's get_daily_plan/mood_map, morning
  affirmations, evening whispers, or WEEKLY_MILESTONES. Also triggers when
  adding a new activity or debugging why the wrong activity was served. This
  is the authoritative source for the real (18-activity) library and every
  real routing rule — not the larger aspirational library once drafted (see
  docs/FEATURE_BACKLOG.md for unbuilt activity ideas).
---

# Mama Bloom — Activity Library & Routing Skill (matches the real config.py)

## Activity structure — every entry in `app/config.py` has these keys

```python
{
    "id": str, "name": str, "category": str, "stars": int,
    "duration_min": int, "duration_max": int,
    "trimester_min": int, "week_min": int, "week_max": int,
    "moods": list[str], "description": str, "prompt": str,
    "science_note": str, "baby_book": str,   # NOTE: a sentence string for breathing
                                              # activities, not a bool — check existing
                                              # entries before assuming the type
    "pillar": str,
}
```
Journaling and Baby Connect activities have a smaller key set (no `stars`,
`duration_min/max`, `trimester_min`, `science_note`, or `baby_book`) — check
the actual list (`BREATHING_ACTIVITIES`, `JOURNALING_ACTIVITIES`,
`BABY_CONNECT_ACTIVITIES`, `CREATIVE_ALTERNATES`, `MUSIC_ACTIVITY`) before
assuming every activity has every key.

## The real 18 activities (6 + 4 + 5 + 2 + 1)

**Breathing (6):** `box_breathing`, `extended_exhale`, `body_scan`, `pmr`
(week_min 14), `safe_place` ("Safe Place Imagery"), `loving_kindness`

**Journaling (4):** `free_mood_journal`, `gratitude_journal`,
`self_compassion` ("Self-Compassion Letter", `exclusive_with: "free_mood_journal"`),
`birth_wishes` (week_min 14)

**Baby Connect (5, week_min 18 except `evening_whisper` which is week_min 1):**
`daily_narration`, `story_time`, `humming_singing`, `conversation_with_baby`
(week_min 14), `evening_whisper`

**Creative Alternates (2, used pre-Week-18 instead of Baby Connect):**
`bilateral_drawing`, `symmetry_drawing`

**Music (1):** `calming_music` — served instead of a Baby Connect pick when
mood is `tired` or `uncomfortable`

There is no `first_letter`, `hope_letter`, `hard_day_letter`,
`weekly_milestone_letter`, or `labour_prep_affirmations` activity in the
real code — those were unbuilt ideas from an earlier draft. See
`docs/FEATURE_BACKLOG.md` if you're considering building one of them.

## The real mood vocabulary — two layers, don't confuse them

1. **Routing-layer moods** (keys in `MOOD_TO_BREATHING`/`MOOD_TO_JOURNALING`/
   `MOOD_TO_BABY_CONNECT` in `config.py` — 17 values): `anxious`,
   `overwhelmed`, `stressed`, `tired`, `uncomfortable`, `sad`, `lonely`,
   `happy`, `excited`, `guilty`, `restless`, `tense`, `panicked`,
   `frustrated`, `sleepless`, `fearful`, `self-critical`.
2. **UI-layer mood chips** (`fast_api_app.py`'s homepage buttons — only 6):
   Heavy, Okay, Good, Glowing, Tired, Uncomfortable.

These two vocabularies don't match 1:1, so `app/tools.py`'s
`get_daily_plan()` has a translation layer — **this exact mapping was a
real, previously-shipped bug** (4 of 6 homepage mood chips produced zero
activities because they didn't exist as keys in the `MOOD_TO_*` dicts).
Any change to either vocabulary must update this `mood_map` too:

```python
mood_map = {
    "heavy": "sad", "okay": "tired", "good": "happy", "glowing": "excited",
    "tired": "tired", "uncomfortable": "uncomfortable",
    "anxious": "anxious", "sad": "sad",
}
primary_mood = mood_map.get(primary_mood, "okay")
```

There's a regression test for exactly this (`tests/unit/test_tools.py::test_every_ui_mood_chip_produces_real_activities`)
— keep it green.

## Real routing rules — `get_daily_plan()` in `app/tools.py`

```python
def pick_activity(candidates, all_activities, yesterday_id):
    # 1. Prefer a candidate NOT used yesterday (variety rule)
    # 2. Fall back to repeating yesterday's pick if it's the only option
    #    (moods with only one routing candidate deliberately repeat)
    ...

# Journaling exclusivity: self_compassion and free_mood_journal never both
# appear two days running from each other
if yesterday_journaling == "self_compassion":
    journaling_candidates = [j for j in journaling_candidates if j != "self_compassion"]
if yesterday_journaling == "free_mood_journal":
    journaling_candidates = [j for j in journaling_candidates if j != "free_mood_journal"]

# Baby Connect: tired/uncomfortable -> calming_music ONLY.
# week < 18 -> creative alternates instead of voice-based Baby Connect activities.
# otherwise -> MOOD_TO_BABY_CONNECT candidates.
```

## Real `WEEKLY_MILESTONES` — 12 entries (weeks 4, 8, 12, 16, 18, 20, 22, 24, 28, 32, 36, 40)

`content_generator`/`get_daily_plan()` both fall back to "closest milestone
at or before the current week" if the exact week isn't a key — there's no
milestone defined for, e.g., week 30; it reuses week 28's text.

## Morning affirmations and evening whispers

- `MORNING_AFFIRMATIONS` (10 entries, rotated by `session_count % len(...)`)
  — but `get_morning_affirmation()` overrides this entirely for `week >= 28`
  with a single fixed labor-adjacent affirmation. There's no separate
  `LABOUR_PREP_AFFIRMATIONS` list — it's one hardcoded string.
- `get_evening_whisper()` rotates through a fixed 7-sentence list keyed by
  `datetime.date.today().weekday()` (day-of-week, not session count).

## Adding a new activity — checklist

1. Add the dict to the right list in `app/config.py` with the correct key
   set for that category (see "Activity structure" above).
2. Add its `id` to the relevant `MOOD_TO_*` dict(s) for every mood it should
   be eligible under.
3. If it has a `week_min`/`week_max` restriction, `pick_activity()` already
   enforces it — no extra code needed in `tools.py`.
4. Run `pytest tests/unit/test_tools.py` — the parametrized
   `test_every_ui_mood_chip_produces_real_activities` test will catch any
   mood that now has zero eligible activities.
