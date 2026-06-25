---
name: mama-bloom-safety
description: >
  ALWAYS use this skill when writing or modifying safety_screen, crisis_response,
  detect_distress, redact_pii, CRISIS_MESSAGE, distress keywords, PII handling,
  or any code that runs before an LLM call in Mama Bloom. Also triggers when
  editing CONTEXT.md, adding new user input fields, or modifying post-feeling
  adaptive logic. This skill is the security and safety source of truth for the
  project — read it before any code that touches user input or the LLM call path.
---

# Mama Bloom — Safety & Security Skill

## The Iron Rule

```
safety_screen ALWAYS runs BEFORE any LLM call.
No exceptions. No shortcuts. No "for testing" bypasses.
```

If you find yourself writing code where Gemini can be called
without passing through `safety_screen` first — STOP and fix the graph wiring.

---

## CONTEXT.md — Always Keep This File Current

The project root must contain `CONTEXT.md`. Antigravity reads it before every code change.
Keep it exactly as below — add to it, never remove from it:

```markdown
# MAMA BLOOM — SECURITY STANDARDS
# Antigravity: read this before every code change in this project.

## Data Privacy
- Never log or store the mother's personal name or exact location
- Health/mood data stored only locally via MCP filesystem server
- No health data sent to external APIs beyond the single Gemini API call
- MCP server data directory: ./data/ — never expose via API endpoints

## LLM Safety
- The safety_screen node MUST always run BEFORE any Gemini API call
- Gemini system prompt MUST include: "Never give medical advice"
- PII redaction (phone numbers, emails) runs in safety_screen
- Log when PII is redacted — never log the actual content

## Crisis Safety
- crisis_response node MUST never call Gemini under any circumstances
- Crisis message MUST contain both helpline numbers
- Safety check triggers on DISTRESS_KEYWORDS only — no LLM judgment

## Adaptive Safety
- "still_hard" x2 consecutive → low_effort_mode (no LLM escalation)
- "still_hard" x3 consecutive → gentle resource nudge (not a crisis alert)

## API Keys
- GEMINI_API_KEY always read from environment variable
- Never hardcode any key in any file
- .env must be in .gitignore

## Medical Disclaimer
- Must appear on first screen of the web app
- Must appear in footer of every page
- Text: "Mama Bloom supports your emotional wellbeing during pregnancy.
  It is not a substitute for medical advice — always consult your
  doctor or midwife."
```

---

## tools.py — Safety Functions (Complete Implementation)

### detect_distress
```python
# Day 4: Safety guardrail — keyword-based only, no LLM judgment
DISTRESS_KEYWORDS = [
    "can't do this", "cant do this",
    "want to disappear", "want to die",
    "hopeless", "no point", "end it",
    "ending it", "hurt myself",
    "don't want to be here", "dont want to be here",
    "give up", "can't go on", "cant go on",
    "not worth it", "better off without me",
    "nobody would care", "no one would care",
]

def detect_distress(text: str) -> bool:
    """
    # Day 4: Safety guardrail — pure keyword matching, no LLM.
    Returns True if ANY distress keyword found (case-insensitive).
    Never uses an LLM to judge distress — speed and reliability matter.
    """
    text_lower = text.lower()
    return any(kw in text_lower for kw in DISTRESS_KEYWORDS)
```

### redact_pii
```python
import re

def redact_pii(text: str) -> str:
    """
    # Day 4: PII redaction — runs in safety_screen before any LLM call.
    Removes phone numbers (Indian + international) and email addresses.
    Logs that redaction occurred — never logs the actual content.
    """
    original = text

    # Indian phone numbers (10-digit starting 6-9, with optional +91/0)
    text = re.sub(
        r'\b(\+91|0)?[6-9]\d{9}\b',
        '[REDACTED]', text
    )
    # International phone numbers (general pattern)
    text = re.sub(
        r'\b[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?'
        r'[-\s\.]?[0-9]{3,6}[-\s\.]?[0-9]{3,6}\b',
        '[REDACTED]', text
    )
    # Email addresses
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[REDACTED]', text
    )

    if text != original:
        print("PII redacted before LLM call")  # Log occurrence only — not content

    return text
```

---

## config.py — Crisis Message (Exact Text Required)

```python
# Day 4: Crisis response content — both helplines mandatory
CRISIS_MESSAGE = """
We see you, and we want you to know: you are not alone.

What you are feeling is real, and support is available right now.

Please reach out:
📞 iCall (India): 9152987821
📞 Vandrevala Foundation: 1860-2662-345 (available 24/7)

You and your baby matter. Please talk to someone today.

If you are in immediate danger, please call emergency services
or go to your nearest hospital.

---
Mama Bloom supports your emotional wellbeing during pregnancy.
It is not a substitute for medical advice — always consult your
doctor or midwife.
"""
```

**Validation checklist for CRISIS_MESSAGE:**
- [ ] Contains "9152987821" (iCall)
- [ ] Contains "1860-2662-345" (Vandrevala Foundation)
- [ ] Contains "24/7" indicator
- [ ] Contains medical disclaimer
- [ ] Does NOT recommend any activity
- [ ] Does NOT call Gemini to generate it

---

## Adaptive Safety — Post-Feeling Logic (in tools.py)

```python
def check_adaptive_rules(sessions: list[dict]) -> dict:
    """
    # Day 3: Session memory — Day 4: Adaptive safety
    Reads recent sessions to detect consecutive "still_hard" post-feelings.
    Returns action dict the content_generator node uses.
    """
    recent = sessions[-3:] if len(sessions) >= 3 else sessions
    still_hard_streak = 0

    for session in reversed(recent):
        if session.get("post_feeling") == "still_hard":
            still_hard_streak += 1
        else:
            break

    if still_hard_streak >= 3:
        return {
            "mode": "gentle_resource_nudge",
            "message": (
                "You have had a few hard days. That is okay — "
                "pregnancy is genuinely difficult sometimes.\n"
                "If you would like to talk to someone:\n"
                "iCall: 9152987821\n"
                "Vandrevala Foundation: 1860-2662-345 (24/7)"
            )
        }
    elif still_hard_streak >= 2:
        return {
            "mode": "low_effort",
            "activities": {
                "breathing": "extended_exhale",
                "journaling": "gratitude_journal",
                "baby_connect": "evening_whisper",
            }
        }
    return {"mode": "normal"}
```

---

## Medical Disclaimer — Must Appear in 3 Places

### 1. FastAPI home page (above the form)
```html
<div class="disclaimer">
  <strong>⚕️ Please read:</strong>
  Mama Bloom supports your emotional wellbeing during pregnancy.
  It is not a substitute for medical advice — always consult your
  doctor or midwife.
</div>
```

### 2. FastAPI footer (every page)
```html
<footer>
  <p class="disclaimer-footer">
    Mama Bloom supports your emotional wellbeing during pregnancy.
    It is not a substitute for medical advice — always consult your doctor or midwife.
  </p>
</footer>
```

### 3. Alongside every crisis or resource message
Always append `CRISIS_MESSAGE` which already contains the disclaimer.

---

## .gitignore — Minimum Required Entries

```gitignore
# API keys — never commit
.env
.env.local
.env.*.local

# MCP data — health data stays local
data/
*.session.json

# Python
__pycache__/
*.pyc
.venv/
dist/
*.egg-info/
```

---

## .env — Template (commit this as .env.example, NOT .env)

```bash
# .env.example — copy to .env and fill in your values
GEMINI_API_KEY=your_key_here
MCP_DATA_DIR=./data
PORT=8080
```

---

## Security Checklist — Run Before Every Commit

- [ ] `GEMINI_API_KEY` read from `os.environ` — not hardcoded anywhere
- [ ] `.env` is in `.gitignore`
- [ ] `safety_screen` is the first node in the graph (no way to skip it)
- [ ] `crisis_response` contains zero Gemini calls
- [ ] `CRISIS_MESSAGE` contains both helplines
- [ ] Medical disclaimer in app header AND footer
- [ ] `redact_pii` called before any text reaches Gemini
- [ ] MCP `data/` directory not exposed as an API endpoint
- [ ] No mother's name or location stored anywhere
