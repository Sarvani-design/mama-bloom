---
name: mama-bloom-safety
description: >
  ALWAYS use this skill when writing or modifying app/tools.py's
  detect_distress/redact_pii, app/agent.py's safety_screen/crisis_response
  nodes, CONTEXT.md, app/config.py's CRISIS_MESSAGE/DISTRESS_KEYWORDS, or any
  code that runs before an LLM call in Mama Bloom. This is the security and
  safety source of truth — read it before any code that touches user input
  or the Gemini call path.
---

# Mama Bloom — Safety & Security Skill (matches the real codebase)

## The Iron Rule

```
safety_screen ALWAYS runs BEFORE any LLM call. No exceptions, no "for
testing" bypasses. In the real graph this is structural, not a convention:
safety_screen is the only node reachable from intake_parser (which is the
only node reachable from START), and crisis_response has zero edges back
into intro_writer (the only node that calls Gemini).
```

If you find yourself wiring a new edge where Gemini could be reached
without passing through `safety_screen` first — stop and fix the graph in
`app/agent.py`, don't patch around it.

## Canonical security rules live in `CONTEXT.md` — don't duplicate, defer to it

`CONTEXT.md` at the repo root is the actual, current source of truth for
security/privacy rules (data privacy, LLM safety, crisis safety, API keys,
medical disclaimer text). This skill should always point there rather than
keeping a second copy that can drift out of sync — re-read `CONTEXT.md`
before any change in this area, and update it (not this skill file) if a
rule changes.

## `app/tools.py` — the real safety functions

```python
def redact_pii(text: str) -> str:
    # Day 4: PII redaction - runs in safety_screen before any LLM call
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    phone_pattern = r"(\+?\b(?:\d{1,4}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b|\b\d{10}\b)"
    redacted_text = text
    redacted_emails, email_count = re.subn(email_pattern, "[REDACTED_EMAIL]", redacted_text)
    redacted_phones, phone_count = re.subn(phone_pattern, "[REDACTED_PHONE]", redacted_emails)
    if email_count > 0 or phone_count > 0:
        print("PII redacted before LLM call")   # log occurrence only, never the actual content
    return redacted_phones


def detect_distress(text: str) -> bool:
    # Day 4: Safety guardrail - pure Python, no LLM
    lowercased = text.lower()
    for keyword in DISTRESS_KEYWORDS:
        if keyword in lowercased:
            return True
    return False
```

Note the real redaction tokens are `[REDACTED_EMAIL]` / `[REDACTED_PHONE]`
(two distinct tokens), not a single generic `[REDACTED]`.

## `app/config.py` — the real `DISTRESS_KEYWORDS` and `CRISIS_MESSAGE`

```python
DISTRESS_KEYWORDS = [
    "can't do this", "cant do this", "want to disappear", "want to die",
    "hopeless", "no point", "end it", "ending it", "hurt myself",
    "don't want to be here", "dont want to be here", "give up",
    "can't go on", "cant go on", "not worth it", "better off without me",
    "nobody would care", "no one would care",
]

CRISIS_MESSAGE = (
    "We see you, and you are not alone. What you are feeling is real, and support is available right now. "
    "Please reach out: iCall (India): 9152987821, Vandrevala Foundation: 1860-2662-345 (available 24/7). "
    "You and your baby matter. Please talk to someone today. If you are in immediate danger, "
    "please call emergency services or go to your nearest hospital."
)
```

`CRISIS_MESSAGE` is a single string (not multi-line/markdown) — match this
exact text if it ever needs editing, and keep both helpline numbers
(`9152987821`, `1860-2662-345`) present.

**Validation checklist:**
- [ ] Contains `"9152987821"` (iCall)
- [ ] Contains `"1860-2662-345"` (Vandrevala Foundation)
- [ ] Does NOT recommend any activity
- [ ] `crisis_response` (app/agent.py) does NOT call Gemini to generate or modify it

## `app/agent.py` — the real `safety_screen` / `crisis_response` nodes

```python
def safety_screen(ctx: Context, description: str) -> None:
    ctx.state["clean_description"] = redact_pii(description)
    # free_text is the same raw input as description, and is what
    # activity_picker/intro_writer actually send to Gemini - redact it
    # too. A security review found this missing: redacting only
    # clean_description left a real PII-to-Gemini leak via free_text.
    ctx.state["free_text"] = ctx.state["clean_description"]
    if detect_distress(ctx.state["clean_description"]):
        ctx.route = "crisis"
    else:
        ctx.route = "normal"


def crisis_response(ctx: Context) -> types.Content:
    # Zero references to google.genai anywhere in this function body.
    ctx.state["output"] = CRISIS_MESSAGE
    ctx.state["is_crisis"] = True
    return types.Content(role="model", parts=[types.Part.from_text(text=CRISIS_MESSAGE)])
```

## Medical disclaimer — how it's actually enforced (structurally, not per-page)

`app/fast_api_app.py` defines `DISCLAIMER` once and `base_page()` appends
`<p class='disclaimer'>{DISCLAIMER}</p>` to **every** page's HTML — so the
"must appear on every page" rule is satisfied by construction (one shared
wrapper function), not by remembering to paste it onto each route handler.
If you add a new page, route it through `base_page()` and the disclaimer
is automatic; don't hand-roll a page that skips it.

## XSS / stored content — also part of the real safety surface

Anything persisted via `/save-entry` (journal/letter content) and
re-rendered later on `/babybook` is passed through `html.escape()` before
being placed in HTML — this was a real stored-XSS bug that was found and
fixed (mother-authored text used to render unescaped on every Baby Book
page load). Any new code that renders user-authored or LLM-generated text
into HTML must `html.escape()` it first; never trust LLM output as safe
HTML either (see the comment above the Gemini-intro rendering in
`fast_api_app.py`'s `/checkin` handler).

## `.gitignore` — already correctly configured, don't remove these entries

```gitignore
.env
data/sessions/
data/baby_book/
```

## API keys

```python
load_dotenv()                                     # app/agent.py, top of file
api_key = os.environ.get("GEMINI_API_KEY", "")     # never hardcoded
```

## Security checklist — run before every commit

- [ ] `GEMINI_API_KEY` read from `os.environ` — not hardcoded anywhere
- [ ] `.env` is in `.gitignore` and not staged (`git status` check)
- [ ] `safety_screen` is reachable from every input path before any Gemini call
- [ ] `crisis_response` contains zero `google.genai` references
- [ ] `CRISIS_MESSAGE` contains both helplines
- [ ] Medical disclaimer rendered via `base_page()`, not hand-pasted per route
- [ ] Any newly-rendered user-authored or LLM-generated text is `html.escape()`d
- [ ] `data/sessions/` and `data/baby_book/` are not exposed via any API endpoint
- [ ] `free_text`, not just `clean_description`, is redacted in `safety_screen` (it's what actually reaches the Gemini prompt)
- [ ] Any new MCP read/write route calls `_get_visitor_id(request)` and passes `user_id` through — see `mama-bloom-fastapi`/`mama-bloom-mcp-server` skills
