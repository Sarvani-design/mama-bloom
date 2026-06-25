---
name: mama-bloom-fastapi
description: >
  ALWAYS use this skill when building or modifying app/fast_api_app.py, any
  HTTP endpoint, the HTML/CSS, the Dockerfile, or Cloud Run deployment in
  Mama Bloom. Also triggers for UI text changes, disclaimer placement, or
  demo video prep. Documents the REAL hand-built-HTML FastAPI app — there
  are no Jinja2 templates in this codebase yet.
---

# Mama Bloom — FastAPI Web App & Deployment Skill (matches the real codebase)

## No Jinja2 templates exist yet — don't assume `templates/*.html`

`app/fast_api_app.py` builds every page as Python f-strings (a single `CSS`
string constant + `base_page()`/`activity_card()`/`nav_bar()` helper
functions), not `Jinja2Templates`. `jinja2` is listed in `pyproject.toml`
but currently unused — if a UI-restructuring pass introduces real
templates, that's a deliberate future migration, not the current state.
Don't write `templates.TemplateResponse(...)` calls against a `templates/`
directory that doesn't exist.

## Real routes (exact paths — note these differ from a hyphenated `/check-in` style)

```
GET  /              → home() — check-in form
POST /checkin        → checkin() — runs the real Runner against root_agent, renders daily plan or crisis page
GET  /write           → write_page() — journal/letter entry form
POST /save-entry      → save_entry() — persists to Baby Book via MCP
GET  /babybook        → babybook() — all Baby Book entries
GET  /calendar         → calendar_page() — 42-day mood calendar
POST /complete        → complete() — post-activity feeling check-in (logged, not yet wired to adaptive logic)
GET  /health          → health() — JSON health check
```

## The real `/checkin` handler — driven by a genuine ADK `Runner`, not `workflow.run(state)`

```python
_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent, session_service=_session_service, app_name="mama-bloom")

@app.post("/checkin", response_class=HTMLResponse)
async def checkin(week: int = Form(..., ge=1, le=42), mood: str = Form("Okay"),
                   free_text: str = Form(""), description: str = Form("")):
    session = await _session_service.create_session(
        app_name="mama-bloom", user_id=user_id,
        state={"week": week, "mood": mood_value, "description": free_text,
               "free_text": free_text, "session_count": 0},
    )
    placeholder = types.Content(role="user", parts=[types.Part.from_text(text="checkin")])
    async for _event in _runner.run_async(user_id=user_id, session_id=session.id, new_message=placeholder):
        pass   # drain; only the final session state matters for rendering
    final_session = await _session_service.get_session(app_name="mama-bloom", user_id=user_id, session_id=session.id)
    state = dict(final_session.state)
    if state.get("is_crisis"):
        # render crisis page — checks state["is_crisis"], not state["route"] == "crisis"
        ...
```

Crisis detection in the rendering code checks `state.get("is_crisis")` (a
bool set by `crisis_response`), not a `route` field — match this when
adding new branches.

## Medical disclaimer — enforced structurally via `base_page()`

```python
DISCLAIMER = (
    "Mama Bloom supports your emotional wellbeing during pregnancy. "
    "It is not a substitute for medical advice — always consult your "
    "doctor or midwife."
)

def base_page(content: str, title: str = "Mama Bloom") -> str:
    return (
        "<!DOCTYPE html>...<div class='container'>"
        f"{content}"
        f"<p class='disclaimer'>{DISCLAIMER}</p>"
        "</div>...</html>"
    )
```

Every route that returns `base_page(...)` automatically gets the
disclaimer — don't hand-write a page that bypasses `base_page()`.

## XSS — always `html.escape()` user-authored and LLM-generated text

`/babybook` and the Gemini intro card both `html.escape()` their content
before interpolating into HTML (a real stored-XSS bug was found and fixed
here). Any new route that renders mother-authored text (journal/letter
content) or Gemini output must do the same.

## Onboarding overlay (real, existing feature — don't reintroduce a duplicate)

`base_page()` already renders a 3-slide onboarding overlay (name + week +
preference chips) gated by `localStorage.getItem('mama_bloom_onboarded')`,
with JS in `onboarding_js` to pre-fill the week field from a returning
visitor's saved value. If a UI-restructuring pass wants to change
onboarding, modify this existing flow rather than adding a second one.

## Real Dockerfile

```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.8.13
WORKDIR /code
COPY ./pyproject.toml ./README.md ./uv.lock* ./
COPY ./app ./app
RUN uv sync --frozen
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]
```

No `Makefile` exists in this repo — run commands directly:

```bash
uvicorn app.fast_api_app:app --reload --port 8080
docker build -t mama-bloom . && docker run -p 8080:8080 --env-file .env mama-bloom
gcloud run deploy mama-bloom --source . --region us-east1 --allow-unauthenticated
```

## Demo video — what to actually show (route names corrected)

**Normal flow:** submit `/checkin` with a non-distress mood/description →
show the morning affirmation card, the Gemini intro card, the milestone
card, all three activity cards (breathing/journaling/baby connect), and the
streak bar.

**Safety flow:** submit `/checkin` with a distress phrase (e.g. "I feel
hopeless and can't do this anymore") → the response must show the crisis
box with both helpline numbers and **zero** activity cards, with no
visible delay (no LLM was called on this path).
