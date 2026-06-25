---
name: mama-bloom-fastapi
description: >
  ALWAYS use this skill when building or modifying fast_api_app.py, any HTTP
  endpoint (/check-in, /complete, /baby-book, /stats, /), the HTML UI, the
  CSS colour scheme, the Dockerfile, Cloud Run deployment, or the Makefile
  serve/deploy targets in Mama Bloom. Also triggers for any UI text changes,
  disclaimer placement, or demo video preparation. This skill covers the full
  web layer — FastAPI, HTML templates, and Cloud Run deployment.
---

# Mama Bloom — FastAPI Web App & Deployment Skill

## File: mama_bloom/fast_api_app.py

### Required Endpoints

```
GET  /              → Home page with check-in form
POST /check-in      → Runs ADK workflow, returns daily plan
GET  /baby-book     → All Baby Book entries
GET  /stats         → Streak, total sessions, total letters
POST /complete      → Mark activity done, save post-feeling
```

### Complete fast_api_app.py Structure

```python
# Day 5: FastAPI web app — demo interface for Mama Bloom
# Day 5: Cloud Run deployment — PORT env var for container

import os
import uuid
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from mama_bloom.agent import workflow
from mama_bloom.mcp_server import get_mcp_client
from mama_bloom.config import VALID_MOODS

app = FastAPI(title="Mama Bloom", description="Maternal Emotional Wellbeing Companion")
templates = Jinja2Templates(directory="templates")

MEDICAL_DISCLAIMER = (
    "Mama Bloom supports your emotional wellbeing during pregnancy. "
    "It is not a substitute for medical advice — always consult your "
    "doctor or midwife."
)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {
        "request": request,
        "disclaimer": MEDICAL_DISCLAIMER,
        "moods": VALID_MOODS,
    })

@app.post("/check-in", response_class=HTMLResponse)
async def check_in(
    request: Request,
    week: int = Form(...),
    mood: str = Form(...),
    description: str = Form(""),
):
    session_id = str(uuid.uuid4())
    state = {
        "week": week,
        "mood": mood,
        "description": description,
        "session_id": session_id,
        "session_date": __import__("datetime").date.today().isoformat(),
    }

    # Load yesterday's activities from MCP memory
    client = await get_mcp_client()
    state["yesterday_activities"] = await client.call_tool("get_yesterday_activities", {})

    # Run the ADK 2.0 workflow
    result = await workflow.run(state)

    # Crisis path — show crisis message, no activities
    if result.get("route") == "crisis":
        return templates.TemplateResponse("crisis.html", {
            "request": request,
            "message": result["output"],
            "disclaimer": MEDICAL_DISCLAIMER,
        })

    # Normal path — show daily plan
    return templates.TemplateResponse("daily_plan.html", {
        "request": request,
        "plan": result["daily_plan"],
        "session_id": session_id,
        "disclaimer": MEDICAL_DISCLAIMER,
    })

@app.post("/complete")
async def complete_activity(
    session_id: str = Form(...),
    post_feeling: str = Form(...),    # "settled"|"warm"|"same"|"still_hard"
    baby_book_content: str = Form(""),
    activity_id: str = Form(""),
):
    client = await get_mcp_client()

    # Save post-feeling to session
    sessions = await client.call_tool("get_sessions", {"limit": 1})
    if sessions:
        last = sessions[-1]
        await client.call_tool("save_session", {
            **last,
            "post_feeling": post_feeling,
        })

    # Save to Baby Book if content provided
    if baby_book_content.strip():
        import datetime
        await client.call_tool("save_baby_book_entry", {
            "entry_type": "letter",
            "week": sessions[-1]["week"] if sessions else 0,
            "content": baby_book_content,
            "date": datetime.date.today().isoformat(),
            "entry_id": str(uuid.uuid4()),
        })

    return {"status": "saved", "post_feeling": post_feeling}

@app.get("/baby-book", response_class=HTMLResponse)
async def baby_book(request: Request):
    client = await get_mcp_client()
    entries = await client.call_tool("get_baby_book_entries", {})
    return templates.TemplateResponse("baby_book.html", {
        "request": request,
        "entries": entries,
        "disclaimer": MEDICAL_DISCLAIMER,
    })

@app.get("/stats", response_class=HTMLResponse)
async def stats(request: Request):
    client = await get_mcp_client()
    streak_data = await client.call_tool("get_streak", {})
    return templates.TemplateResponse("stats.html", {
        "request": request,
        "streak": streak_data,
        "disclaimer": MEDICAL_DISCLAIMER,
    })

# Cloud Run entry point
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

---

## UI Design Specification

### Colour Scheme (CSS variables)
```css
:root {
    --bg-primary: #FFF0F5;        /* Warm pink background */
    --bg-card: #FFFFFF;
    --accent-green: #4CAF50;      /* Primary action colour */
    --accent-pink: #E91E8C;       /* Secondary accent */
    --text-dark: #2C2C2C;
    --text-soft: #6B6B6B;
    --border-light: #F0D6E4;
    --warning-bg: #FFF8E1;
    --crisis-bg: #FFF3F3;
}
```

### Home Page — Required Elements
```html
<!-- templates/home.html -->
<body style="background: var(--bg-primary)">

  <!-- Medical disclaimer — MUST be above the form -->
  <div class="disclaimer-box">
    ⚕️ {{ disclaimer }}
  </div>

  <h1>🌸 Mama Bloom</h1>
  <p>Your daily moment of calm during pregnancy.</p>

  <form action="/check-in" method="post">

    <label>How many weeks pregnant are you?</label>
    <input type="number" name="week" min="1" max="42" required>

    <label>How are you feeling today?</label>
    <select name="mood" required>
      <option value="">Choose your mood...</option>
      <option value="glowing">✨ Glowing</option>
      <option value="good">😊 Good</option>
      <option value="okay">😐 Okay</option>
      <option value="tired">😴 Tired</option>
      <option value="anxious">😰 Anxious</option>
      <option value="uncomfortable">😣 Uncomfortable</option>
      <option value="heavy">😔 Heavy</option>
      <option value="sad">😢 Sad</option>
    </select>

    <label>Anything on your mind? (optional)</label>
    <textarea name="description" rows="3"
      placeholder="How are you really feeling today?"></textarea>

    <button type="submit">Start Today with Bloom 🌸</button>

  </form>

  <!-- Footer disclaimer — MUST appear on every page -->
  <footer>
    <p>{{ disclaimer }}</p>
  </footer>
</body>
```

### Daily Plan Page — Required Elements
```html
<!-- templates/daily_plan.html -->

<!-- Morning affirmation — large, full-width, prominent -->
<div class="affirmation-card">
  <p class="read-slowly">Read this slowly ✨</p>
  <h2>{{ plan.morning_affirmation }}</h2>
</div>

<!-- Intro message from Gemini -->
<div class="intro-message">{{ plan.intro_message }}</div>

<!-- Milestone card (if applicable) -->
{% if plan.milestone %}
<div class="milestone-card">
  💌 Week {{ plan.week }}: {{ plan.milestone }}
</div>
{% endif %}

<!-- Three activity cards -->
{% for activity in plan.activities %}
<div class="activity-card">
  <h3>{{ activity.name }}</h3>
  <span class="duration">{{ activity.duration_min }}–{{ activity.duration_max }} min</span>
  <p class="prompt">{{ activity.prompt }}</p>
  <p class="science">📚 {{ activity.science_note }}</p>
  <!-- Post-feeling check-in after Done -->
  <div class="post-feeling" style="display:none">
    <p>How do you feel now?</p>
    <button onclick="saveFeel('settled')">😌 Settled</button>
    <button onclick="saveFeel('warm')">🤗 Warm</button>
    <button onclick="saveFeel('same')">😐 Same</button>
    <button onclick="saveFeel('still_hard')">😔 Still hard</button>
  </div>
  <button onclick="markDone(this)">Done ✓</button>
</div>
{% endfor %}

<!-- Baby Book counter -->
<div class="baby-book-counter">
  📖 {{ streak.total_sessions }} sessions · {{ streak.total_letters }} letters
  · Week {{ plan.week }}
</div>

<!-- Evening Whisper — fixed at bottom -->
<div class="evening-whisper">
  <h3>🌙 Before bed, say this to your baby:</h3>
  <blockquote>{{ plan.evening_whisper }}</blockquote>
</div>

<footer><p>{{ disclaimer }}</p></footer>
```

---

## Dockerfile — Cloud Run Ready

```dockerfile
# Day 5: Cloud Run deployment
FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .

# Create data directory for MCP storage
RUN mkdir -p data

# Cloud Run uses PORT env variable
ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "mama_bloom.fast_api_app"]
```

---

## pyproject.toml — Dependencies

```toml
[project]
name = "mama-bloom"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "google-adk>=2.0.0",
    "google-generativeai>=0.8.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "jinja2>=3.1.0",
    "mcp>=1.0.0",
    "python-multipart>=0.0.12",
    "python-dotenv>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Makefile

```makefile
.PHONY: playground serve deploy generate-traces grade

playground:
	uvx google-agents-cli playground

serve:
	uvicorn mama_bloom.fast_api_app:app --reload --port 8080

deploy:
	gcloud run deploy mama-bloom \
	  --source . \
	  --region us-central1 \
	  --allow-unauthenticated \
	  --set-env-vars GEMINI_API_KEY=$$GEMINI_API_KEY

generate-traces:
	python tests/eval/generate_traces.py

grade:
	python tests/eval/grade.py
```

---

## Demo Video — The 60-Second Sequence Judges Need to See

Script this exactly in your video:

**Scenario 1 (0:00–0:45) — Normal flow:**
```
Input:  Week 22, mood: anxious
        "I'm feeling really overwhelmed and scared"

Show on screen:
  ✨ Morning Affirmation (full screen, warm typography)
  🌬️ Box Breathing — 5 min (prompt text visible)
  📓 Self-Compassion Check-In (3-step prompt visible)
  💬 Daily Narration (warm prompt to talk to baby)
  💌 "Week 22: your baby can feel light through your belly"
  📖 "3 sessions · 1 letter · Week 22"
```

**Scenario 2 (0:45–1:30) — Safety system:**
```
Input:  Week 28, mood: heavy
        "I feel hopeless and can't do this anymore"

Show on screen:
  CRISIS MESSAGE appears INSTANTLY
  Both helplines visible: iCall 9152987821
  Vandrevala 1860-2662-345
  NO activities shown
  NO Gemini response — pure Python
```

This two-scenario sequence proves: normal flow + safety guardrail.
It is the most important 90 seconds in the entire video.
