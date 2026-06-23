# Day 1: FastAPI web interface for Mama Bloom
# Day 5: Deployable web app for Cloud Run

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.agent import _run_workflow_async
from app.mcp_server import get_baby_book_entries

app = FastAPI(title="Mama Bloom", description="Maternal wellbeing companion")

DISCLAIMER = (
    "Mama Bloom supports your emotional wellbeing during pregnancy. "
    "It is not a substitute for medical advice — always consult your "
    "doctor or midwife."
)

HOME_CSS = """
body {
    background: #FFF0F5;
    font-family: Georgia, serif;
    margin: 0;
    padding: 20px;
}
.container {
    max-width: 480px;
    margin: 0 auto;
    padding: 24px;
}
h1 {
    font-size: 32px;
    color: #2D4A3E;
    margin-bottom: 8px;
}
.subtitle {
    color: #666;
    font-size: 16px;
    margin-bottom: 32px;
}
label {
    display: block;
    color: #2D4A3E;
    font-size: 14px;
    margin-bottom: 6px;
    margin-top: 16px;
}
input, select, textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid #C8E6C9;
    border-radius: 8px;
    font-size: 16px;
    font-family: Georgia, serif;
    box-sizing: border-box;
    background: white;
}
textarea {
    height: 80px;
    resize: none;
}
.btn {
    width: 100%;
    padding: 14px;
    background: #4CAF50;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 18px;
    font-family: Georgia, serif;
    cursor: pointer;
    margin-top: 24px;
}
.disclaimer {
    font-size: 11px;
    color: #999;
    text-align: center;
    margin-top: 24px;
    line-height: 1.5;
}
.card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    border: 1px solid #E8F5E9;
}
.affirmation {
    font-size: 22px;
    color: #2D4A3E;
    font-style: italic;
    line-height: 1.6;
    text-align: center;
    padding: 24px;
}
.milestone {
    background: #E8F5E9;
    border-radius: 8px;
    padding: 16px;
    color: #2D4A3E;
    margin-bottom: 16px;
}
.activity-name {
    font-size: 18px;
    font-weight: bold;
    color: #2D4A3E;
}
.activity-duration {
    font-size: 12px;
    color: #999;
    margin-bottom: 8px;
}
.activity-prompt {
    color: #444;
    line-height: 1.6;
    margin-bottom: 8px;
}
.science-note {
    font-size: 11px;
    color: #aaa;
    font-style: italic;
}
.whisper {
    font-style: italic;
    color: #2D4A3E;
    font-size: 18px;
    text-align: center;
    padding: 16px;
}
.crisis-box {
    background: #FFF3F3;
    border: 2px solid #E57373;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
}
.crisis-number {
    font-size: 22px;
    font-weight: bold;
    color: #C62828;
    margin: 8px 0;
}
.label-small {
    font-size: 12px;
    color: #4CAF50;
    margin-bottom: 4px;
}
.streak {
    background: #F3E5F5;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
    color: #6A1B9A;
    font-size: 13px;
    margin-bottom: 16px;
}
"""


def base_page(content: str, title: str = "Mama Bloom") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{HOME_CSS}</style>
</head>
<body>
<div class="container">
{content}
<p class="disclaimer">{DISCLAIMER}</p>
</div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def home():
    content = """
    <h1>Hello, mama.</h1>
    <p class="subtitle">25 minutes a day, just for you and your baby.</p>
    <form method="POST" action="/checkin">
        <label>Which week are you in?</label>
        <input type="number" name="week" min="1" max="42"
               placeholder="e.g. 22" required>
        <label>How are you feeling today?</label>
        <select name="mood">
            <option value="Heavy">Heavy</option>
            <option value="Okay" selected>Okay</option>
            <option value="Good">Good</option>
            <option value="Glowing">Glowing</option>
            <option value="Tired">Tired</option>
            <option value="Uncomfortable">Uncomfortable</option>
        </select>
        <label>Anything on your mind? (optional)</label>
        <textarea name="description"
                  placeholder="How are you feeling today?"></textarea>
        <button type="submit" class="btn">Start today with Bloom 🌸</button>
    </form>
    """
    return HTMLResponse(base_page(content))


@app.post("/checkin", response_class=HTMLResponse)
async def checkin(
    week: int = Form(...),
    mood: str = Form(...),
    description: str = Form(""),
):
    state = await _run_workflow_async(
        week=week,
        mood=mood,
        description=description
    )

    if state.get("is_crisis"):
        content = f"""
        <h1>We see you.</h1>
        <div class="crisis-box">
            <p>You are not alone. What you are feeling is real,
               and support is available right now.</p>
            <p class="crisis-number">iCall: 9152987821</p>
            <p class="crisis-number">
               Vandrevala Foundation: 1860-2662-345
            </p>
            <p style="font-size:13px;color:#666;">Available 24/7</p>
        </div>
        <p>If you are in immediate danger, please call emergency
           services or go to your nearest hospital.</p>
        <a href="/" style="color:#4CAF50;">Return to home</a>
        """
        return HTMLResponse(base_page(content, "Mama Bloom — We See You"))

    affirmation = state.get("morning_affirmation", "")
    intro = state.get("gemini_intro", "")
    milestone = state.get("week_milestone", "")
    daily_plan = state.get("daily_plan", {})
    whisper = state.get("evening_whisper", "")
    streak = state.get("streak", {})
    session_id = state.get("session_id", "")

    total_sessions = streak.get("total_sessions", 0)
    total_letters = streak.get("total_letters", 0)
    current_streak = streak.get("current_streak", 0)

    def activity_card(act: dict) -> str:
        if not act:
            return ""
        return f"""
        <div class="card">
            <div class="activity-name">{act.get("name", "")}</div>
            <div class="activity-duration">
                {act.get("duration_min", "")} min
            </div>
            <div class="activity-prompt">
                {act.get("prompt", "")}
            </div>
            <div class="science-note">
                {act.get("science_note", "")}
            </div>
        </div>"""

    breathing_card = activity_card(daily_plan.get("breathing", {}))
    journaling_card = activity_card(daily_plan.get("journaling", {}))
    baby_card = activity_card(daily_plan.get("baby_connect", {}))

    content = f"""
    <div class="label-small">READ THIS SLOWLY</div>
    <div class="affirmation">"{affirmation}"</div>

    <div class="card" style="font-style:italic;color:#666;">
        {intro}
    </div>

    <div class="milestone">
        Week {week}: {milestone}
    </div>

    <h3 style="color:#2D4A3E;font-size:16px;">
        Today's plan for you
    </h3>

    {breathing_card}
    {journaling_card}
    {baby_card}

    <div class="streak">
        {current_streak} day streak &nbsp;·&nbsp;
        {total_sessions} sessions &nbsp;·&nbsp;
        {total_letters} letters to baby
    </div>

    <div class="card">
        <div class="label-small">BEFORE BED, SAY THIS TO YOUR BABY</div>
        <div class="whisper">"{whisper}"</div>
    </div>

    <a href="/" style="color:#4CAF50;
                        display:block;
                        text-align:center;
                        margin-top:16px;">
        Back to home
    </a>

    <input type="hidden" id="session_id" value="{session_id}">
    """
    return HTMLResponse(base_page(content, f"Your Day — Week {week}"))


@app.post("/complete")
async def complete(request: Request):
    data = await request.json()
    return JSONResponse({"saved": True})


@app.get("/babybook", response_class=HTMLResponse)
async def babybook():
    try:
        entries = await get_baby_book_entries()
    except Exception:
        entries = []

    if not entries:
        items = (
            "<p style='color:#999;'>No entries yet. "
            "Complete your first session to begin your Baby Book.</p>"
        )
    else:
        items = ""
        for e in entries:
            items += f"""
            <div class="card">
                <div class="activity-duration">
                    Week {e.get("week", "")} ·
                    {e.get("date", "")} ·
                    {e.get("entry_type", "")}
                </div>
                <div class="activity-prompt">
                    {e.get("content", "")}
                </div>
            </div>"""

    content = f"""
    <h1>Your Baby Book</h1>
    <p class="subtitle">Letters and reflections,
       building week by week.</p>
    {items}
    <a href="/" style="color:#4CAF50;
                        display:block;
                        text-align:center;
                        margin-top:16px;">
        Back to home
    </a>
    """
    return HTMLResponse(base_page(content, "Baby Book"))


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "app": "mama-bloom"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)