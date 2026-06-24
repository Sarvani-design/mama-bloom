# Day 1: FastAPI web interface for Mama Bloom
# Day 5: Deployable web app for Cloud Run

import datetime
import uuid

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.agent import _run_workflow_async
from app.mcp_server import (
    get_baby_book_entries,
    get_sessions,
    save_baby_book_entry,
)

# ---------------------------------------------------------------------------
# Activity lookup — resolves an activity ID string → full dict
# Used when agent returns IDs instead of full dicts in daily_plan
# ---------------------------------------------------------------------------
try:
    from app.config import (
        BREATHING_ACTIVITIES,
        JOURNALING_ACTIVITIES,
        BABY_CONNECT_ACTIVITIES,
        CREATIVE_ALTERNATES,
        MUSIC_ACTIVITY,
        WEEKLY_REFLECTION,
        LETTER_ACTIVITIES,
    )

    _ALL_ACTIVITIES: dict = {}
    for _a in (
        BREATHING_ACTIVITIES
        + JOURNALING_ACTIVITIES
        + BABY_CONNECT_ACTIVITIES
        + CREATIVE_ALTERNATES
        + LETTER_ACTIVITIES
        + [MUSIC_ACTIVITY, WEEKLY_REFLECTION]
    ):
        _ALL_ACTIVITIES[_a["id"]] = _a
except Exception:
    _ALL_ACTIVITIES = {}


def _resolve_activity(val) -> dict:
    """Return full activity dict whether val is already a dict or an ID string."""
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val in _ALL_ACTIVITIES:
        return _ALL_ACTIVITIES[val]
    return {}


# ---------------------------------------------------------------------------
app = FastAPI(
    title="Mama Bloom",
    description="Maternal wellbeing companion",
)

DISCLAIMER = (
    "Mama Bloom supports your emotional wellbeing during pregnancy. "
    "It is not a substitute for medical advice — always consult your "
    "doctor or midwife."
)

# ---------------------------------------------------------------------------
# CSS — single source of truth
# ---------------------------------------------------------------------------
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;1,400&family=Inter:wght@400;500;600&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    background: #F7F3EE;
    font-family: 'Inter', sans-serif;
    color: #2C3E35;
    min-height: 100vh;
    padding: 0 0 48px 0;
}

.container { max-width: 480px; margin: 0 auto; padding: 24px 20px; }

/* ── Typography ── */
h1 {
    font-family: 'Lora', serif;
    font-size: 30px;
    font-weight: 500;
    color: #2C3E35;
    margin-bottom: 6px;
    line-height: 1.25;
}
h2 {
    font-family: 'Lora', serif;
    font-size: 20px;
    font-weight: 500;
    color: #2C3E35;
    margin-bottom: 8px;
}
h3 { font-size: 14px; font-weight: 600; color: #4A7C6F; margin-bottom: 12px; }
p { line-height: 1.65; color: #5C6B64; font-size: 15px; }
.subtitle { font-size: 15px; color: #8A9B94; margin-bottom: 28px; }

/* ── Form elements ── */
.label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: #4A7C6F;
    margin-bottom: 8px;
    margin-top: 20px;
}
input[type=number], textarea {
    width: 100%;
    padding: 12px 14px;
    border: 1.5px solid #D4C9BB;
    border-radius: 10px;
    font-size: 15px;
    font-family: 'Inter', sans-serif;
    background: white;
    color: #2C3E35;
    outline: none;
    transition: border-color 0.2s;
}
input[type=number]:focus, textarea:focus { border-color: #4A7C6F; }
textarea { height: 80px; resize: none; }

/* ── Mood chips ── */
.mood-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 4px;
}
.mood-chip {
    background: white;
    border: 1.5px solid #D4C9BB;
    border-radius: 10px;
    padding: 10px 6px;
    text-align: center;
    cursor: pointer;
    transition: all 0.15s;
    font-size: 11px;
    color: #5C6B64;
    user-select: none;
}
.mood-chip:hover { border-color: #4A7C6F; background: #F0F7F4; }
.mood-chip.selected {
    border-color: #4A7C6F;
    background: #EDF4F0;
    color: #2C3E35;
    font-weight: 500;
}
.mood-chip .emoji { font-size: 22px; display: block; margin-bottom: 4px; }

/* ── Buttons ── */
.btn {
    width: 100%;
    padding: 14px;
    background: #4A7C6F;
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 16px;
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    cursor: pointer;
    margin-top: 24px;
    transition: background 0.2s;
}
.btn:hover { background: #3A6C5F; }
.btn-outline {
    width: 100%;
    padding: 12px;
    background: transparent;
    color: #4A7C6F;
    border: 1.5px solid #4A7C6F;
    border-radius: 10px;
    font-size: 14px;
    font-family: 'Inter', sans-serif;
    cursor: pointer;
    margin-top: 10px;
    transition: all 0.2s;
}
.btn-outline:hover { background: #EDF4F0; }
.btn-rose {
    display: block;
    width: 100%;
    padding: 10px;
    background: #B85C52;
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 13px;
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    cursor: pointer;
    margin-top: 10px;
    text-align: center;
    text-decoration: none;
}
.btn-rose:hover { background: #A04840; }
.btn-sm {
    padding: 8px 16px;
    background: #4A7C6F;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
}
.btn-sm:hover { background: #3A6C5F; }

/* ── Cards ── */
.card {
    background: white;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 14px;
    border: 1px solid #E8E0D8;
}
.card-green {
    background: #EDF4F0;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 14px;
    border: 1px solid #C0D8CC;
}
.card-dark {
    background: #2C3E35;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 14px;
}
.card-rose {
    background: #FDF0EC;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 14px;
    border: 1px solid #E8C4B8;
}

/* ── Activity cards ── */
.activity-card {
    background: white;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 14px;
    border: 1px solid #E8E0D8;
}
.activity-name {
    font-family: 'Lora', serif;
    font-size: 18px;
    font-weight: 500;
    color: #2C3E35;
    margin: 6px 0 10px;
}
.activity-why {
    font-size: 12px;
    color: #4A7C6F;
    background: #EDF4F0;
    border-radius: 8px;
    padding: 10px 12px;
    margin: 0 0 12px;
    line-height: 1.55;
}
.activity-why strong { font-weight: 600; }
.activity-prompt {
    font-size: 14px;
    color: #2C3E35;
    line-height: 1.75;
    margin-bottom: 4px;
    white-space: pre-wrap;
}
.activity-divider {
    border: none;
    border-top: 1px solid #F0EAE2;
    margin: 14px 0;
}

/* ── Post-activity check-in ── */
.checkin-row {
    display: flex;
    gap: 8px;
    margin-top: 12px;
}
.checkin-btn {
    flex: 1;
    padding: 8px 4px;
    border: 1.5px solid #D4C9BB;
    border-radius: 8px;
    background: white;
    font-size: 11px;
    color: #5C6B64;
    cursor: pointer;
    text-align: center;
    transition: all 0.15s;
    font-family: 'Inter', sans-serif;
}
.checkin-btn .ci-emoji { display: block; font-size: 18px; margin-bottom: 2px; }
.checkin-btn:hover { border-color: #4A7C6F; background: #EDF4F0; }
.checkin-done {
    font-size: 12px;
    color: #4A7C6F;
    font-weight: 500;
    text-align: center;
    padding: 8px;
    display: none;
}

/* ── Affirmation ── */
.affirmation {
    font-family: 'Lora', serif;
    font-size: 21px;
    font-style: italic;
    color: #2C3E35;
    line-height: 1.55;
    text-align: center;
    padding: 4px;
}

/* ── Pills ── */
.label-small {
    font-size: 11px;
    font-weight: 500;
    color: #4A7C6F;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 99px;
    font-size: 11px;
    font-weight: 500;
    margin-bottom: 2px;
}
.pill-green { background: #EDF4F0; color: #2C5F4A; }
.pill-rose  { background: #FDF0EC; color: #8B3A2E; }
.pill-amber { background: #FDF5E6; color: #7A5C1E; }

/* ── Streak bar ── */
.streak {
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
    padding: 14px;
    background: #EDF4F0;
    border-radius: 12px;
    margin-bottom: 14px;
    border: 1px solid #C0D8CC;
}
.streak-item { text-align: center; font-size: 11px; color: #5C6B64; }
.streak-item span { display: block; font-size: 22px; font-weight: 600; color: #2C3E35; line-height: 1.2; }

/* ── Disclaimer ── */
.disclaimer {
    font-size: 11px;
    color: #A09888;
    text-align: center;
    margin-top: 24px;
    line-height: 1.65;
    padding-top: 16px;
    border-top: 1px solid #E8E0D8;
}

/* ── Crisis ── */
.crisis-box {
    background: #FFF3F3;
    border: 2px solid #E57373;
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 16px;
}
.crisis-number {
    font-size: 20px;
    font-weight: 600;
    color: #C62828;
    margin: 10px 0;
    font-family: 'Lora', serif;
}

/* ── Nav ── */
.nav {
    display: flex;
    justify-content: space-around;
    background: white;
    border-radius: 14px;
    padding: 12px 8px;
    margin-bottom: 24px;
    border: 1px solid #E8E0D8;
    box-shadow: 0 1px 4px rgba(44,62,53,0.06);
}
.nav a {
    text-decoration: none;
    font-size: 11px;
    color: #8A9B94;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    transition: color 0.15s;
}
.nav a.active { color: #4A7C6F; font-weight: 600; }
.nav a:hover:not(.active) { color: #5C6B64; }
.nav-icon { font-size: 18px; }

/* ── Write page ── */
.write-area {
    width: 100%;
    min-height: 220px;
    padding: 16px;
    border: 1.5px solid #D4C9BB;
    border-radius: 10px;
    font-size: 15px;
    font-family: 'Lora', serif;
    background: white;
    color: #2C3E35;
    line-height: 1.85;
    resize: vertical;
    outline: none;
}
.write-area:focus { border-color: #4A7C6F; }

/* ── Baby book ── */
.confirm-circle {
    width: 64px; height: 64px;
    border-radius: 50%;
    background: #EDF4F0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    margin: 0 auto 16px;
}
.entry-card {
    background: white;
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 12px;
    border: 1px solid #E8E0D8;
}
.entry-meta { font-size: 11px; color: #8A9B94; margin-bottom: 6px; }
.entry-content {
    font-size: 14px;
    color: #2C3E35;
    line-height: 1.65;
    font-family: 'Lora', serif;
    font-style: italic;
}
.back-link {
    display: inline-block;
    color: #4A7C6F;
    font-size: 14px;
    text-decoration: none;
    margin-bottom: 20px;
}

/* ── Onboarding overlay ── */
.onboarding-overlay {
    position: fixed;
    inset: 0;
    background: #F7F3EE;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px 20px;
}
.onboarding-inner {
    max-width: 420px;
    width: 100%;
}
.onboarding-slide { display: none; }
.onboarding-slide.active { display: block; }
.onboarding-flower {
    font-size: 56px;
    text-align: center;
    margin-bottom: 20px;
    line-height: 1;
}
.onboarding-title {
    font-family: 'Lora', serif;
    font-size: 28px;
    font-weight: 500;
    color: #2C3E35;
    text-align: center;
    margin-bottom: 10px;
    line-height: 1.3;
}
.onboarding-body {
    font-size: 15px;
    color: #5C6B64;
    text-align: center;
    line-height: 1.7;
    margin-bottom: 28px;
}
.onboarding-dots {
    display: flex;
    justify-content: center;
    gap: 6px;
    margin-bottom: 20px;
}
.dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #D4C9BB;
    transition: background 0.2s;
}
.dot.active { background: #4A7C6F; }
.pref-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 20px;
}
.pref-chip {
    border: 1.5px solid #D4C9BB;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 13px;
    color: #5C6B64;
    cursor: pointer;
    text-align: left;
    background: white;
    transition: all 0.15s;
}
.pref-chip:hover { border-color: #4A7C6F; background: #EDF4F0; }
.pref-chip.selected {
    border-color: #4A7C6F;
    background: #EDF4F0;
    color: #2C3E35;
    font-weight: 500;
}
.pref-chip .pref-emoji { margin-right: 6px; }
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def base_page(content: str, title: str = "Mama Bloom") -> str:
    onboarding_js = """
<script>
(function() {
  // Show onboarding only on first visit
  if (!localStorage.getItem('mama_bloom_onboarded')) {
    document.getElementById('onboarding').style.display = 'flex';
  }

  var slide = 0;
  var totalSlides = 3;

  function showSlide(n) {
    document.querySelectorAll('.onboarding-slide').forEach(function(el, i) {
      el.classList.toggle('active', i === n);
    });
    document.querySelectorAll('.dot').forEach(function(el, i) {
      el.classList.toggle('active', i === n);
    });
    slide = n;
  }

  window.onboardingNext = function() {
    if (slide < totalSlides - 1) {
      showSlide(slide + 1);
    } else {
      finishOnboarding();
    }
  };

  window.finishOnboarding = function() {
    // Save name + week from slide 2
    var nameVal = document.getElementById('ob-name') ? document.getElementById('ob-name').value.trim() : '';
    var weekVal = document.getElementById('ob-week') ? document.getElementById('ob-week').value : '';
    if (nameVal) localStorage.setItem('mama_bloom_name', nameVal);
    if (weekVal) localStorage.setItem('mama_bloom_week', weekVal);
    localStorage.setItem('mama_bloom_onboarded', 'true');
    document.getElementById('onboarding').style.display = 'none';
    // Pre-fill week on home form if present
    var wk = document.getElementById('week-input');
    if (wk && weekVal) wk.value = weekVal;
  };

  window.togglePref = function(el) {
    el.classList.toggle('selected');
  };

  // Pre-fill week from localStorage on page load
  var savedWeek = localStorage.getItem('mama_bloom_week');
  var savedName = localStorage.getItem('mama_bloom_name');
  window.addEventListener('DOMContentLoaded', function() {
    var wk = document.getElementById('week-input');
    if (wk && savedWeek) wk.value = savedWeek;
    var gr = document.getElementById('greeting-name');
    if (gr && savedName) gr.textContent = savedName + '.';
  });
})();
</script>
"""
    return (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        f"<title>{title}</title>"
        f"<style>{CSS}</style>"
        "</head>"
        "<body>"
        # Onboarding overlay (hidden by default; JS shows on first visit)
        "<div id='onboarding' class='onboarding-overlay' style='display:none;'>"
        "<div class='onboarding-inner'>"
        # Slide 1 — Welcome
        "<div class='onboarding-slide active'>"
        "<div class='onboarding-flower'>🌸</div>"
        "<div class='onboarding-title'>Hello, mama.</div>"
        "<div class='onboarding-body'>"
        "Mama Bloom is your 25-minute daily ritual — breathing, journaling, and "
        "connecting with your baby — all shaped around how you feel today."
        "</div>"
        "<div class='onboarding-dots'>"
        "<div class='dot active'></div><div class='dot'></div><div class='dot'></div>"
        "</div>"
        "<button class='btn' onclick='onboardingNext()'>Let's begin 🌿</button>"
        "</div>"
        # Slide 2 — Name + week
        "<div class='onboarding-slide'>"
        "<div class='onboarding-flower'>🌱</div>"
        "<div class='onboarding-title'>Tell me about you</div>"
        "<div class='onboarding-body'>"
        "I'll use this to personalise everything for your pregnancy."
        "</div>"
        "<label class='label' style='text-align:left;'>Your name (optional)</label>"
        "<input type='text' id='ob-name' placeholder='e.g. Priya' "
        "style='width:100%;padding:12px 14px;border:1.5px solid #D4C9BB;"
        "border-radius:10px;font-size:15px;font-family:Inter,sans-serif;"
        "background:white;color:#2C3E35;outline:none;margin-bottom:4px;'>"
        "<label class='label' style='text-align:left;'>Which week are you in?</label>"
        "<input type='number' id='ob-week' min='1' max='42' placeholder='e.g. 22' "
        "style='width:100%;padding:12px 14px;border:1.5px solid #D4C9BB;"
        "border-radius:10px;font-size:15px;font-family:Inter,sans-serif;"
        "background:white;color:#2C3E35;outline:none;'>"
        "<div class='onboarding-dots' style='margin-top:20px;'>"
        "<div class='dot'></div><div class='dot active'></div><div class='dot'></div>"
        "</div>"
        "<button class='btn' onclick='onboardingNext()'>Continue</button>"
        "</div>"
        # Slide 3 — Preferences
        "<div class='onboarding-slide'>"
        "<div class='onboarding-flower'>💚</div>"
        "<div class='onboarding-title'>What feels right to you?</div>"
        "<div class='onboarding-body'>"
        "I'll lean toward these — you can always change your plan each day."
        "</div>"
        "<div class='pref-grid'>"
        "<div class='pref-chip' onclick='togglePref(this)'>"
        "<span class='pref-emoji'>🌬️</span>Breathing</div>"
        "<div class='pref-chip' onclick='togglePref(this)'>"
        "<span class='pref-emoji'>📓</span>Journaling</div>"
        "<div class='pref-chip' onclick='togglePref(this)'>"
        "<span class='pref-emoji'>💬</span>Talking to baby</div>"
        "<div class='pref-chip' onclick='togglePref(this)'>"
        "<span class='pref-emoji'>🎨</span>Creative activities</div>"
        "<div class='pref-chip' onclick='togglePref(this)'>"
        "<span class='pref-emoji'>🎵</span>Music</div>"
        "<div class='pref-chip' onclick='togglePref(this)'>"
        "<span class='pref-emoji'>🧘</span>Body relaxation</div>"
        "</div>"
        "<div class='onboarding-dots'>"
        "<div class='dot'></div><div class='dot'></div><div class='dot active'></div>"
        "</div>"
        "<button class='btn' onclick='finishOnboarding()'>Start my journey 🌸</button>"
        "</div>"
        "</div>"  # onboarding-inner
        "</div>"  # onboarding-overlay
        # Main page content
        "<div class='container'>"
        f"{content}"
        f"<p class='disclaimer'>{DISCLAIMER}</p>"
        "</div>"
        f"{onboarding_js}"
        "</body>"
        "</html>"
    )


def nav_bar(active: str = "home") -> str:
    tabs = [
        ("/", "🌸", "Today", "home"),
        ("/babybook", "💌", "Baby Book", "book"),
        ("/calendar", "📅", "Journey", "calendar"),
    ]
    links = ""
    for href, icon, label, key in tabs:
        cls = "active" if active == key else ""
        links += (
            f"<a href='{href}' class='{cls}'>"
            f"<span class='nav-icon'>{icon}</span>{label}</a>"
        )
    return f"<div class='nav'>{links}</div>"


def activity_card(act: dict, pillar: str, week: int) -> str:
    """Render a single activity card with pill, name, why-box, prompt, check-in."""
    if not act:
        return ""

    pill_map = {
        "breathing":   ("pill-green", "🌬️", "Breathing"),
        "journaling":  ("pill-rose",  "📓", "Journaling"),
        "baby_connect":("pill-amber", "💛", "Baby connect"),
    }
    pill_cls, pill_icon, pill_label_base = pill_map.get(pillar, ("pill-green", "🌿", "Activity"))

    dur_min = act.get("duration_min", 5)
    dur_max = act.get("duration_max", dur_min)
    dur_str = f"{dur_min} min" if dur_min == dur_max else f"{dur_min}–{dur_max} min"
    pill_label = f"{pill_icon} {pill_label_base} · {dur_str}"

    name     = act.get("name", "")
    science  = act.get("science_note", "")
    prompt   = act.get("prompt", "")
    act_id   = act.get("id", str(uuid.uuid4())[:8])

    # Science note trimmed to ≤120 chars for the why-box
    science_short = science[:120] + ("…" if len(science) > 120 else "")

    write_btn = ""
    if pillar == "journaling":
        write_btn = (
            f"<a href='/write?type=journal&activity_id={act_id}&week={week}' "
            f"class='btn-rose'>Open journal to write ✍️</a>"
        )

    # Post-activity check-in buttons — one per card, keyed by act_id
    checkin_id = f"ci_{act_id}"
    done_id    = f"done_{act_id}"
    checkin_html = (
        "<hr class='activity-divider'>"
        "<div style='font-size:11px;color:#8A9B94;margin-bottom:6px;'>"
        "How did that feel?</div>"
        f"<div class='checkin-row' id='{checkin_id}'>"
        f"<button class='checkin-btn' onclick=\"markCheckin('{act_id}','settled')\">"
        "<span class='ci-emoji'>😌</span>Settled</button>"
        f"<button class='checkin-btn' onclick=\"markCheckin('{act_id}','warm')\">"
        "<span class='ci-emoji'>🌸</span>Warm</button>"
        f"<button class='checkin-btn' onclick=\"markCheckin('{act_id}','same')\">"
        "<span class='ci-emoji'>😐</span>Same</button>"
        f"<button class='checkin-btn' onclick=\"markCheckin('{act_id}','still_hard')\">"
        "<span class='ci-emoji'>😔</span>Still hard</button>"
        "</div>"
        f"<div class='checkin-done' id='{done_id}'>Noted — thank you 💚</div>"
    )

    return (
        "<div class='activity-card'>"
        f"<span class='pill {pill_cls}'>{pill_label}</span>"
        f"<div class='activity-name'>{name}</div>"
        f"<div class='activity-why'>"
        f"<strong>Why this for Week {week}:</strong> {science_short}"
        "</div>"
        f"<div class='activity-prompt'>{prompt}</div>"
        f"{write_btn}"
        f"{checkin_html}"
        "</div>"
    )


CHECKIN_JS = """
<script>
function markCheckin(actId, feeling) {
  fetch('/complete', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({activity_id: actId, feeling: feeling})
  });
  document.getElementById('ci_' + actId).style.display = 'none';
  var done = document.getElementById('done_' + actId);
  done.style.display = 'block';
}
</script>
"""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home():
    nb = nav_bar("home")
    content = (
        f"{nb}"
        "<h1>Hello, <span id='greeting-name'>mama.</span></h1>"
        "<p class='subtitle'>25 minutes a day, just for you and your baby.</p>"
        "<form method='POST' action='/checkin' id='checkin-form'>"
        "<label class='label'>Which week are you in?</label>"
        "<input type='number' id='week-input' name='week' "
        "min='1' max='42' placeholder='e.g. 22' required>"
        "<label class='label'>How are you feeling today?</label>"
        "<p style='font-size:12px;color:#8A9B94;margin-bottom:10px;'>"
        "Select all that apply</p>"
        "<div class='mood-grid'>"
        "<div class='mood-chip' onclick='toggleMood(this,\"Heavy\")'>"
        "<span class='emoji'>😔</span>Heavy</div>"
        "<div class='mood-chip' onclick='toggleMood(this,\"Okay\")'>"
        "<span class='emoji'>😐</span>Okay</div>"
        "<div class='mood-chip' onclick='toggleMood(this,\"Good\")'>"
        "<span class='emoji'>🌸</span>Good</div>"
        "<div class='mood-chip' onclick='toggleMood(this,\"Glowing\")'>"
        "<span class='emoji'>✨</span>Glowing</div>"
        "<div class='mood-chip' onclick='toggleMood(this,\"Tired\")'>"
        "<span class='emoji'>😴</span>Tired</div>"
        "<div class='mood-chip' onclick='toggleMood(this,\"Uncomfortable\")'>"
        "<span class='emoji'>😣</span>Uncomfortable</div>"
        "</div>"
        "<input type='hidden' name='mood' id='mood-value' value='Okay'>"
        "<label class='label'>Tell Bloom how you are feeling (optional)</label>"
        "<textarea name='free_text' "
        "placeholder='My back is aching and I feel a bit emotional today...'>"
        "</textarea>"
        "<input type='hidden' name='description' id='desc-value' value=''>"
        "<button type='submit' class='btn'>See today's plan 🌿</button>"
        "</form>"
        "<script>"
        "const selected = new Set();"
        "function toggleMood(el, mood) {"
        "  if (selected.has(mood)) {"
        "    selected.delete(mood);"
        "    el.classList.remove('selected');"
        "  } else {"
        "    selected.add(mood);"
        "    el.classList.add('selected');"
        "  }"
        "  const arr = Array.from(selected);"
        "  document.getElementById('mood-value').value = "
        "    arr.length > 0 ? arr.join(',') : 'Okay';"
        "}"
        "</script>"
    )
    return HTMLResponse(base_page(content))


@app.post("/checkin", response_class=HTMLResponse)
async def checkin(
    week: int = Form(...),
    mood: str = Form("Okay"),
    free_text: str = Form(""),
    description: str = Form(""),
):
    mood_list = [m.strip() for m in mood.split(",") if m.strip()]
    primary_mood = mood_list[0] if mood_list else "Okay"

    state = await _run_workflow_async(
        week=week,
        mood=mood_list if len(mood_list) > 1 else primary_mood,
        description=free_text,
        free_text=free_text,
    )

    nb = nav_bar("home")

    # ── Crisis path ──────────────────────────────────────────────────────────
    if state.get("is_crisis"):
        content = (
            f"{nb}"
            "<h1>We see you.</h1>"
            "<div class='crisis-box'>"
            "<p style='color:#C62828;font-weight:500;margin-bottom:12px;'>"
            "You are not alone. What you are feeling is real, "
            "and support is available right now.</p>"
            "<p class='crisis-number'>📞 iCall: 9152987821</p>"
            "<p class='crisis-number'>📞 Vandrevala Foundation: 1860-2662-345</p>"
            "<p style='font-size:12px;color:#888;margin-top:8px;'>"
            "Available 24 hours, 7 days a week</p>"
            "</div>"
            "<p style='margin-bottom:20px;'>If you are in immediate danger, "
            "please call emergency services or go to your nearest hospital.</p>"
            "<a href='/'>"
            "<button class='btn-outline'>Return to home</button></a>"
        )
        return HTMLResponse(base_page(content, "Mama Bloom — We See You"))

    # ── Normal path ──────────────────────────────────────────────────────────
    affirmation  = state.get("morning_affirmation", "")
    intro        = state.get("gemini_intro", "")
    milestone    = state.get("week_milestone", "")
    daily_plan   = state.get("daily_plan", {})
    whisper      = state.get("evening_whisper", "")
    streak       = state.get("streak", {})
    total_sessions  = streak.get("total_sessions", 0)
    total_letters   = streak.get("total_letters", 0)
    current_streak  = streak.get("current_streak", 0)
    mood_display = mood.replace(",", " · ")

    # Resolve activity dicts (handles both ID strings and full dicts)
    b_act  = _resolve_activity(daily_plan.get("breathing", {}))
    j_act  = _resolve_activity(daily_plan.get("journaling", {}))
    bc_act = _resolve_activity(daily_plan.get("baby_connect", {}))

    b_card  = activity_card(b_act,  "breathing",    week)
    j_card  = activity_card(j_act,  "journaling",   week)
    bc_card = activity_card(bc_act, "baby_connect",  week)

    # Milestone card (only if milestone text exists)
    milestone_html = ""
    if milestone:
        milestone_html = (
            "<div class='card-rose'>"
            f"<div class='label-small'>Week {week} — your baby right now</div>"
            f"<p style='color:#2C3E35;font-size:14px;margin-top:4px;'>{milestone}</p>"
            "</div>"
        )

    # Gemini intro card (only if present)
    intro_html = ""
    if intro:
        intro_html = (
            "<div class='card'>"
            f"<p style='font-style:italic;color:#5C6B64;font-size:14px;"
            f"font-family:Lora,serif;'>{intro}</p>"
            "</div>"
        )

    content = (
        f"{nb}"
        # Morning affirmation — full-width, serene
        "<div class='card-green'>"
        "<div class='label-small'>Read this slowly</div>"
        f"<div class='affirmation'>\"{affirmation}\"</div>"
        "</div>"
        f"{intro_html}"
        f"{milestone_html}"
        # Mood context
        "<div style='margin-bottom:10px;'>"
        f"<span style='font-size:12px;color:#8A9B94;'>Feeling today: {mood_display}</span>"
        "</div>"
        # Activity cards
        "<h3>Today's plan — 25 minutes, all for you</h3>"
        f"{b_card}{j_card}{bc_card}"
        # Streak
        "<div class='streak'>"
        f"<div class='streak-item'><span>{current_streak}</span>day streak</div>"
        f"<div class='streak-item'><span>{total_sessions}</span>sessions</div>"
        f"<div class='streak-item'><span>{total_letters}</span>letters</div>"
        f"<div class='streak-item'><span>Wk {week}</span>pregnancy</div>"
        "</div>"
        # Evening whisper — dark card
        "<div class='card-dark'>"
        "<div class='label-small' style='color:#8A9B94;'>"
        "Before bed, say this to your baby 🌙</div>"
        f"<div class='affirmation' style='color:#F7F3EE;font-size:18px;'>"
        f"\"{whisper}\"</div>"
        "</div>"
        "<a href='/' class='back-link' "
        "style='display:block;text-align:center;margin-top:8px;'>"
        "← Back to home</a>"
        f"{CHECKIN_JS}"
    )
    return HTMLResponse(base_page(content, f"Your Day — Week {week}"))


@app.get("/write", response_class=HTMLResponse)
async def write_page(
    type: str = "journal",
    activity_id: str = "",
    week: int = 0,
):
    is_letter      = type == "letter"
    title_text     = "Letter to Baby" if is_letter else "Journal"
    entry_type_val = "letter" if is_letter else "journal"
    placeholder    = (
        "Dear little one,\n\n"
        if is_letter
        else "Write freely — no rules, just honest words...\n"
    )

    content = (
        "<a href='/' class='back-link'>← Back</a>"
        f"<h2>{title_text} — Week {week}</h2>"
        "<p style='margin-bottom:16px;font-size:13px;color:#8A9B94;'>"
        "This will be saved to your Baby Book.</p>"
        "<form method='POST' action='/save-entry'>"
        f"<input type='hidden' name='entry_type' value='{entry_type_val}'>"
        f"<input type='hidden' name='week' value='{week}'>"
        f"<input type='hidden' name='activity_id' value='{activity_id}'>"
        f"<textarea class='write-area' name='content' "
        f"placeholder='{placeholder}'></textarea>"
        "<button type='submit' class='btn'>Save to Baby Book 💌</button>"
        "<a href='/'>"
        "<button type='button' class='btn-outline'>Skip for today</button>"
        "</a>"
        "</form>"
    )
    return HTMLResponse(base_page(content, title_text))


@app.post("/save-entry", response_class=HTMLResponse)
async def save_entry(
    entry_type: str = Form("journal"),
    week: int = Form(0),
    content: str = Form(""),
    activity_id: str = Form(""),
):
    entry_id = str(uuid.uuid4())[:8]
    today    = datetime.date.today().isoformat()
    saved    = False

    try:
        await save_baby_book_entry(
            entry_type=entry_type,
            week=week,
            content=content,
            date=today,
            entry_id=entry_id,
        )
        saved = True
    except Exception:
        saved = False

    heading = "Saved to your Baby Book." if saved else "Almost there."
    subtext  = (
        "This is part of your baby's story. It is safe here."
        if saved
        else "Something went wrong — please try again."
    )
    preview = content[:140] + ("…" if len(content) > 140 else "")

    page_content = (
        "<div style='text-align:center;padding:40px 0 24px;'>"
        "<div class='confirm-circle'>💚</div>"
        f"<h2 style='margin-bottom:8px;'>{heading}</h2>"
        f"<p style='margin-bottom:24px;'>{subtext}</p>"
        "</div>"
        "<div class='card-green'>"
        f"<div class='label-small'>Week {week} · {today}</div>"
        "<p style='font-family:Lora,serif;font-style:italic;"
        f"font-size:14px;color:#2C3E35;margin-top:6px;line-height:1.65;'>"
        f"{preview}</p>"
        "</div>"
        "<a href='/babybook'>"
        "<button class='btn' style='margin-top:8px;'>See your Baby Book 💌</button>"
        "</a>"
        "<a href='/'>"
        "<button class='btn-outline'>Continue with today</button>"
        "</a>"
    )
    return HTMLResponse(base_page(page_content, "Saved to Baby Book"))


@app.get("/babybook", response_class=HTMLResponse)
async def babybook():
    try:
        entries = await get_baby_book_entries()
    except Exception:
        entries = []

    nb = nav_bar("book")

    if not entries:
        items = (
            "<div style='text-align:center;padding:48px 0;'>"
            "<div style='font-size:52px;margin-bottom:16px;'>💌</div>"
            "<h2 style='margin-bottom:10px;'>Your Baby Book is waiting.</h2>"
            "<p>Complete your first session and write your first letter "
            "to start building your baby's story.</p>"
            "<a href='/'><button class='btn' style='margin-top:24px;'>"
            "Start today 🌸</button></a>"
            "</div>"
        )
    else:
        type_label_map = {
            "letter":     "💌 Letter to baby",
            "journal":    "📓 Journal",
            "reflection": "🌿 Weekly reflection",
            "milestone":  "⭐ Milestone",
        }
        items = ""
        for e in reversed(entries):
            entry_type  = e.get("entry_type", "entry")
            type_label  = type_label_map.get(entry_type, entry_type.capitalize())
            raw         = str(e.get("content", ""))
            preview     = raw[:220] + ("…" if len(raw) > 220 else "")
            items += (
                "<div class='entry-card'>"
                "<div class='entry-meta'>"
                f"Week {e.get('week', '')} &nbsp;·&nbsp;"
                f"{e.get('date', '')} &nbsp;·&nbsp;"
                f"{type_label}</div>"
                f"<div class='entry-content'>{preview}</div>"
                "</div>"
            )

    content = (
        f"{nb}"
        "<h1>Your Baby Book</h1>"
        "<p class='subtitle'>Letters and reflections, building week by week.</p>"
        f"{items}"
    )
    return HTMLResponse(base_page(content, "Baby Book"))


@app.get("/calendar", response_class=HTMLResponse)
async def calendar_page():
    try:
        sessions = await get_sessions(limit=42)
    except Exception:
        sessions = []

    mood_colors = {
        "heavy":         "#FDF0EC",
        "sad":           "#FDF0EC",
        "okay":          "#EDF4F0",
        "good":          "#D4E8DC",
        "glowing":       "#C0DDD0",
        "tired":         "#FDF5E6",
        "uncomfortable": "#FDF5E6",
    }

    session_map: dict = {}
    for s in sessions:
        date = s.get("date", "")
        mood = s.get("mood", "okay").lower().split(",")[0].strip()
        if date:
            session_map[date] = mood

    today     = datetime.date.today()
    today_str = today.isoformat()
    days_html = ""

    for i in range(41, -1, -1):
        day     = today - datetime.timedelta(days=i)
        day_str = day.isoformat()
        mood    = session_map.get(day_str, "")
        color   = mood_colors.get(mood, "white")
        border  = (
            "2px solid #4A7C6F"
            if day_str == today_str
            else "1px solid #E8E0D8"
        )
        dot_html = (
            "<div style='width:6px;height:6px;border-radius:50%;"
            "background:#4A7C6F;margin:2px auto;'></div>"
            if mood else ""
        )
        days_html += (
            f"<div style='background:{color};border:{border};"
            "border-radius:6px;padding:4px 2px;"
            f"text-align:center;font-size:11px;color:#5C6B64;'>"
            f"{day.day}{dot_html}</div>"
        )

    legend = (
        "<div style='display:flex;gap:14px;flex-wrap:wrap;"
        "margin:12px 0 16px;font-size:11px;color:#5C6B64;'>"
        + "".join(
            f"<span style='display:flex;align-items:center;gap:4px;'>"
            f"<span style='width:10px;height:10px;border-radius:2px;"
            f"background:{c};display:inline-block;border:1px solid #D4C9BB;'></span>{l}</span>"
            for l, c in [
                ("Good", "#D4E8DC"), ("Okay", "#EDF4F0"),
                ("Heavy", "#FDF0EC"), ("Tired", "#FDF5E6"),
            ]
        )
        + "</div>"
    )

    nb = nav_bar("calendar")
    content = (
        f"{nb}"
        "<h1>Your journey</h1>"
        "<p class='subtitle'>Every day you showed up for your baby.</p>"
        f"{legend}"
        "<div style='display:grid;grid-template-columns:repeat(7,1fr);"
        "gap:4px;margin-bottom:24px;'>"
        + "".join(
            f"<div style='text-align:center;font-size:10px;"
            f"color:#8A9B94;padding:4px;'>{d}</div>"
            for d in ["M", "T", "W", "T", "F", "S", "S"]
        )
        + days_html
        + "</div>"
        "<a href='/babybook'>"
        "<button class='btn-outline'>Open Baby Book 💌</button></a>"
    )
    return HTMLResponse(base_page(content, "Your Journey"))


@app.post("/complete")
async def complete(request: Request):
    """Post-activity check-in — saves feeling, returns ok."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    # Future: pass feeling to memory_saver for adaptive logic
    return JSONResponse({"saved": True, "feeling": body.get("feeling", "")})


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "app": "mama-bloom"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)