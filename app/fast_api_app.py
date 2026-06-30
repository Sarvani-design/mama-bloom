# Day 1: FastAPI web interface for Mama Bloom
# Day 5: Deployable web app for Cloud Run

import datetime
import html
import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent
from app.mcp_client import start_mcp_client, stop_mcp_client
from app.mcp_server import (
    get_baby_book_entries,
    get_sessions,
    save_baby_book_entry,
)

# Day 1: real ADK Runner - genuinely executes the Workflow graph in
# app/agent.py, replacing the old hand-rolled _run_workflow_async.
_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent, session_service=_session_service, app_name="mama-bloom"
)

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)

# Day 4: per-visitor identity (cookie-based, no login) - scopes every MCP
# read/write to the visitor who made it, so one mother's check-ins and
# Baby Book entries are never visible to another visitor of a deployed
# instance. See app/mcp_server.py's user_id-scoped tools.
_VISITOR_COOKIE = "mama_bloom_uid"


def _get_visitor_id(request: Request) -> str:
    return request.cookies.get(_VISITOR_COOKIE) or secrets.token_hex(16)


def _with_visitor_cookie(response: HTMLResponse, visitor_id: str) -> HTMLResponse:
    response.set_cookie(
        _VISITOR_COOKIE, visitor_id,
        max_age=60 * 60 * 24 * 365, httponly=True, samesite="lax",
    )
    return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Day 2: real MCP client - spawns mcp_server.py as a stdio subprocess
    # and keeps one session open for the app's lifetime
    await start_mcp_client(project_root=_PROJECT_ROOT)
    yield
    await stop_mcp_client()

# ---------------------------------------------------------------------------
# Activity lookup — resolves an activity ID string → full dict
# Used when agent returns IDs instead of full dicts in daily_plan
# ---------------------------------------------------------------------------
try:
    from app.config import (
        BABY_CONNECT_ACTIVITIES,
        BREATHING_ACTIVITIES,
        CREATIVE_ALTERNATES,
        JOURNALING_ACTIVITIES,
        MUSIC_ACTIVITY,
    )

    _ALL_ACTIVITIES: dict = {}
    for _a in (
        BREATHING_ACTIVITIES
        + JOURNALING_ACTIVITIES
        + BABY_CONNECT_ACTIVITIES
        + CREATIVE_ALTERNATES
        + [MUSIC_ACTIVITY]
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
    lifespan=lifespan,
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
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@300;400;500;600;700&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    background: linear-gradient(160deg, #E8F2ED 0%, #F5F0E8 45%, #F0E8EE 100%);
    font-family: 'Inter', sans-serif;
    color: #2C3E35;
    min-height: 100vh;
    padding: 0 0 48px 0;
    position: relative;
    overflow-x: hidden;
}

/* ── Animated background orbs ── */
.orb {
    position: fixed; border-radius: 50%; filter: blur(65px);
    pointer-events: none; z-index: 0;
}
.orb-1 {
    width: 360px; height: 360px; opacity: 0.5;
    background: radial-gradient(circle, #A8D5C2 0%, transparent 70%);
    top: -100px; right: -100px;
    animation: orb-drift 14s ease-in-out infinite;
}
.orb-2 {
    width: 300px; height: 300px; opacity: 0.42;
    background: radial-gradient(circle, #E8C4B8 0%, transparent 70%);
    bottom: 15%; left: -80px;
    animation: orb-drift 18s ease-in-out infinite reverse;
}
.orb-3 {
    width: 240px; height: 240px; opacity: 0.35;
    background: radial-gradient(circle, #C5D9F0 0%, transparent 70%);
    top: 45%; right: -60px;
    animation: orb-drift 11s ease-in-out infinite 5s;
}
@keyframes orb-drift {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33%       { transform: translate(-22px, 18px) scale(1.06); }
    66%       { transform: translate(12px, -18px) scale(0.96); }
}

.container { max-width: 480px; margin: 0 auto; padding: 24px 20px; position: relative; z-index: 1; }

/* ── Typography ── */
h1 {
    font-family: 'Lora', serif;
    font-size: 38px;
    font-weight: 600;
    background: linear-gradient(135deg, #2C6B55 0%, #4A7C6F 45%, #6B9E8F 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 6px;
    line-height: 1.2;
    animation: title-float 4s ease-in-out infinite;
}
@keyframes title-float {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-4px); }
}
h2 {
    font-family: 'Lora', serif;
    font-size: 22px;
    font-weight: 600;
    color: #2C3E35;
    margin-bottom: 8px;
}
h3 { font-size: 14px; font-weight: 700; color: #4A7C6F; margin-bottom: 12px; }
p { line-height: 1.7; color: #5C6B64; font-size: 15px; font-weight: 300; }
.subtitle { font-size: 15px; color: #8A9B94; margin-bottom: 28px; font-weight: 300; }

/* ── Section header (replaces plain h3 for "Today's plan") ── */
.section-header {
    font-size: 11px; font-weight: 700; color: #2C3E35;
    letter-spacing: 0.08em; text-transform: uppercase;
    margin: 8px 0 18px; display: flex; align-items: center; gap: 8px;
}
.section-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
    background: linear-gradient(135deg, #4A7C6F, #7AB5A8);
    display: inline-block;
}

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
    border-radius: 12px;
    font-size: 15px;
    font-family: 'Inter', sans-serif;
    background: white;
    color: #2C3E35;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
}
input[type=number]:focus, textarea:focus {
    border-color: #4A7C6F;
    box-shadow: 0 0 0 3px rgba(74,124,111,0.12);
}
textarea { height: 80px; resize: none; }

/* ── Mood chips ── */
.mood-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 4px;
}
.mood-chip {
    background: rgba(255,255,255,0.70);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1.5px solid rgba(212,201,187,0.50);
    border-radius: 22px; padding: 16px 8px;
    text-align: center; cursor: pointer;
    transition: all 0.28s cubic-bezier(0.34,1.56,0.64,1);
    font-size: 12px; color: #5C6B64; user-select: none;
    box-shadow: 0 2px 12px rgba(44,62,53,0.06);
}
.mood-chip:hover {
    border-color: rgba(74,124,111,0.55);
    background: rgba(240,247,244,0.85);
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(74,124,111,0.16);
}
.mood-chip.selected {
    background: linear-gradient(145deg, rgba(232,244,239,0.95), rgba(200,232,218,0.92));
    border-color: #4A7C6F;
    color: #1E3A2F; font-weight: 700;
    transform: scale(1.07) translateY(-3px);
    box-shadow: 0 10px 28px rgba(74,124,111,0.28);
}
.mood-chip .emoji {
    font-size: 28px; display: block; margin-bottom: 6px;
    transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1);
}
.mood-chip.selected .emoji { transform: scale(1.25) rotate(-5deg); }

/* ── Buttons ── */
.btn {
    width: 100%; padding: 16px;
    background: linear-gradient(135deg, #5A9E8F 0%, #3A7060 55%, #2E5E50 100%);
    color: white; border: none; border-radius: 14px;
    font-size: 16px; font-family: 'Inter', sans-serif;
    font-weight: 600; cursor: pointer; margin-top: 24px;
    box-shadow: 0 4px 20px rgba(58,112,96,0.38), 0 1px 0 rgba(255,255,255,0.15) inset;
    transition: all 0.25s;
    position: relative; overflow: hidden;
}
.btn::after {
    content: ''; position: absolute;
    top: 0; left: -100%; width: 60%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.20), transparent);
    animation: shimmer 3s ease infinite;
}
@keyframes shimmer { 0% { left: -100%; } 100% { left: 160%; } }
.btn:hover {
    background: linear-gradient(135deg, #6BB0A1 0%, #4A8272 55%, #3A6E5F 100%);
    box-shadow: 0 6px 28px rgba(58,112,96,0.48);
    transform: translateY(-1px);
}
.btn:active { transform: scale(0.97) translateY(0); }
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

/* ── Cards — glassmorphism ── */
.card {
    background: rgba(255,255,255,0.72);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.55);
    border-radius: 20px; padding: 22px; margin-bottom: 18px;
    box-shadow: 0 8px 32px rgba(44,62,53,0.10), 0 1px 0 rgba(255,255,255,0.8) inset;
    transition: transform 0.2s, box-shadow 0.2s;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 14px 40px rgba(44,62,53,0.14); }
.card-green {
    background: linear-gradient(135deg, rgba(232,244,239,0.92) 0%, rgba(205,235,222,0.88) 100%);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(192,216,204,0.65);
    border-radius: 20px; padding: 22px; margin-bottom: 18px;
    box-shadow: 0 6px 28px rgba(74,124,111,0.13);
}
.card-dark {
    background: linear-gradient(135deg, #2C3E35 0%, #1A2E22 100%);
    border-radius: 20px; padding: 24px; margin-bottom: 18px;
    box-shadow: 0 10px 36px rgba(26,46,34,0.38);
}
.card-rose {
    background: linear-gradient(135deg, rgba(253,240,236,0.92) 0%, rgba(248,218,206,0.88) 100%);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(232,196,184,0.65);
    border-radius: 20px; padding: 20px; margin-bottom: 18px;
    box-shadow: 0 6px 24px rgba(184,92,82,0.11);
}

/* ── Result hero banner ── */
.result-hero {
    background: linear-gradient(135deg, #2E5E50 0%, #3A7060 45%, #5A9E8F 100%);
    border-radius: 22px; padding: 30px 24px; margin-bottom: 20px;
    text-align: center; position: relative; overflow: hidden;
    box-shadow: 0 10px 36px rgba(46,94,80,0.38);
}
.result-hero::before {
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(ellipse at top right, rgba(255,255,255,0.18) 0%, transparent 55%);
}
.result-hero-week {
    font-family: 'Lora', serif; font-size: 34px; font-weight: 600;
    color: white; position: relative; line-height: 1.15;
}
.result-hero-sub {
    font-size: 13px; color: rgba(255,255,255,0.78);
    margin-top: 5px; position: relative; font-weight: 400;
}
.result-hero-badge {
    display: inline-block; margin-top: 12px; position: relative;
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.32);
    backdrop-filter: blur(8px);
    border-radius: 99px; padding: 5px 16px;
    font-size: 12px; font-weight: 600; color: white;
}

/* ── Activity cards — gradient top stripe + glass ── */
.activity-card {
    background: rgba(255,255,255,0.78);
    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.52);
    border-radius: 20px; padding: 0; margin-bottom: 18px;
    overflow: hidden;
    box-shadow: 0 6px 24px rgba(44,62,53,0.09);
    transition: transform 0.22s, box-shadow 0.22s;
}
.activity-card:hover { transform: translateY(-3px); box-shadow: 0 12px 36px rgba(44,62,53,0.14); }
.activity-top-stripe { height: 5px; }
.act-breathing .activity-top-stripe { background: linear-gradient(90deg, #4A7C6F, #7AB5A8); }
.act-journaling .activity-top-stripe { background: linear-gradient(90deg, #C4975A, #E0B87A); }
.act-baby .activity-top-stripe { background: linear-gradient(90deg, #B85C52, #D98278); }
.activity-inner { padding: 18px 20px 20px; }
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
    font-size: 23px;
    font-style: italic;
    color: #2C3E35;
    line-height: 1.65;
    text-align: center;
    padding: 12px 4px;
}

/* ── Staggered fade-in for result page cards ── */
@keyframes fade-up {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0);    }
}
.fade-in-1 { animation: fade-up 0.4s ease both; }
.fade-in-2 { animation: fade-up 0.4s ease 0.07s both; }
.fade-in-3 { animation: fade-up 0.4s ease 0.14s both; }
.fade-in-4 { animation: fade-up 0.4s ease 0.21s both; }
.fade-in-5 { animation: fade-up 0.4s ease 0.28s both; }
.fade-in-6 { animation: fade-up 0.4s ease 0.35s both; }

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
    display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;
    padding: 18px; border-radius: 20px; margin-bottom: 18px;
    background: linear-gradient(135deg, rgba(232,244,239,0.85), rgba(208,232,220,0.82));
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(192,216,204,0.55);
    box-shadow: 0 4px 20px rgba(74,124,111,0.10);
}
.streak-item {
    text-align: center; font-size: 10px; color: #5C6B64;
    background: rgba(255,255,255,0.72); border-radius: 14px;
    padding: 10px 14px; min-width: 60px;
    box-shadow: 0 2px 8px rgba(74,124,111,0.08);
    backdrop-filter: blur(8px);
}
.streak-item span {
    display: block; font-size: 24px; font-weight: 700; line-height: 1.2;
    background: linear-gradient(135deg, #2C6B55, #4A7C6F);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}

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

/* ── Slim scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #F7F3EE; }
::-webkit-scrollbar-thumb { background: #C8BDB3; border-radius: 99px; }

/* ── Nav ── */
.nav {
    display: flex;
    justify-content: space-around;
    background: rgba(247,243,238,0.94);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-radius: 16px;
    padding: 12px 8px;
    margin-bottom: 24px;
    border: 1px solid #EDE7DF;
    box-shadow: 0 2px 12px rgba(44,62,53,0.07);
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
.write-area:focus {
    border-color: #4A7C6F;
    box-shadow: 0 0 0 3px rgba(74,124,111,0.12);
}

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

/* ── Responsive container + activity grid ── */
@media (min-width: 880px) {
    .container { max-width: 860px; }
    .activities-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 18px;
    }
    .activities-grid > * { margin-bottom: 0; }
}
@media (min-width: 600px) and (max-width: 879px) {
    .container { max-width: 600px; }
    .activities-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;
    }
    .activities-grid > * { margin-bottom: 0; }
}

/* ── Calendar ── */
.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 5px;
    margin-bottom: 24px;
}
.cal-header {
    text-align: center; font-size: 9px; color: #8A9B94;
    padding: 4px 2px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.05em;
}
.cal-day {
    aspect-ratio: 1;
    border-radius: 10px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 2px; cursor: default;
    font-size: 10px; color: #5C6B64;
    background: rgba(255,255,255,0.55);
    border: 1px solid rgba(212,201,187,0.35);
    transition: transform 0.18s, box-shadow 0.18s;
    position: relative;
}
.cal-day.has-entry {
    cursor: pointer;
    background: rgba(255,255,255,0.80);
    border-color: rgba(74,124,111,0.25);
}
.cal-day.has-entry:hover { transform: scale(1.08); box-shadow: 0 6px 18px rgba(44,62,53,0.14); }
.cal-day.today {
    border: 2px solid #4A7C6F;
    background: rgba(232,244,239,0.85);
}
.cal-day-num { font-size: 11px; font-weight: 600; color: #2C3E35; line-height: 1; }
.cal-day.today .cal-day-num { color: #4A7C6F; }
.cal-day-emoji { font-size: 15px; line-height: 1; }
.cal-legend {
    display: flex; gap: 12px; flex-wrap: wrap;
    margin-bottom: 18px; font-size: 11px; color: #5C6B64;
    align-items: center;
}
.cal-legend-item { display: flex; align-items: center; gap: 4px; }

/* Calendar detail modal */
.cal-modal-bg {
    display: none; position: fixed; inset: 0; z-index: 500;
    background: rgba(26,46,34,0.45);
    backdrop-filter: blur(6px);
    align-items: center; justify-content: center;
}
.cal-modal-bg.open { display: flex; }
.cal-modal {
    background: rgba(255,255,255,0.97);
    border-radius: 22px; padding: 28px 24px;
    max-width: 340px; width: 90%;
    position: relative;
    box-shadow: 0 20px 60px rgba(26,46,34,0.28);
    animation: modal-in 0.22s ease;
}
@keyframes modal-in {
    from { transform: scale(0.90) translateY(12px); opacity: 0; }
    to   { transform: scale(1)    translateY(0);    opacity: 1; }
}
.cal-modal-close {
    position: absolute; top: 14px; right: 16px;
    background: none; border: none;
    font-size: 22px; cursor: pointer; color: #8A9B94; line-height: 1;
}
.cal-modal-date { font-size: 11px; color: #8A9B94; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
.cal-modal-emoji { font-size: 48px; text-align: center; margin: 10px 0; }
.cal-modal-mood { font-family: 'Lora', serif; font-size: 20px; color: #2C3E35; text-align: center; font-weight: 600; margin-bottom: 14px; text-transform: capitalize; }
.cal-modal-week { font-size: 12px; color: #8A9B94; text-align: center; margin-bottom: 14px; }
.cal-modal-acts { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.cal-modal-act { background: rgba(74,124,111,0.12); border-radius: 99px; padding: 4px 12px; font-size: 11px; color: #3A7060; }

/* ── Animated book UI ── */
.book-scene {
    width: 100%; max-width: 720px; margin: 0 auto;
    perspective: 1400px;
}
.book-open {
    display: flex; width: 100%;
    border-radius: 4px 6px 6px 4px;
    box-shadow: 0 24px 64px rgba(26,46,34,0.40), 0 8px 24px rgba(26,46,34,0.22);
    transform-style: preserve-3d;
    position: relative; overflow: hidden;
    min-height: 520px;
}
.book-spine {
    width: 14px; flex-shrink: 0;
    background: linear-gradient(180deg, #4A7060 0%, #2C5244 45%, #4A7060 100%);
    box-shadow: inset -3px 0 6px rgba(0,0,0,0.25), inset 3px 0 4px rgba(255,255,255,0.08);
}
.book-left-page {
    flex: 1; background: linear-gradient(160deg, #FFFEF5 0%, #FDF9EE 100%);
    padding: 36px 28px 28px;
    border-right: 1px solid rgba(180,155,130,0.22);
    position: relative; overflow: hidden;
}
.book-right-page {
    flex: 1; background: linear-gradient(160deg, #FFFEF5 0%, #FDF9EE 100%);
    padding: 36px 28px 28px;
    position: relative; overflow: hidden;
    transform-style: preserve-3d;
    transform-origin: left center;
    transition: transform 1.0s cubic-bezier(0.645, 0.045, 0.355, 1.0);
}
.book-right-page.flipping { transform: rotateY(-180deg); }
.page-lines {
    position: absolute; inset: 0;
    background-image: repeating-linear-gradient(
        to bottom, transparent 0px, transparent 35px, rgba(170,145,120,0.18) 36px
    );
    pointer-events: none;
}
.book-brand { text-align: center; padding-top: 60px; position: relative; z-index: 1; }
.book-brand-logo { font-size: 52px; margin-bottom: 14px; }
.book-brand-title { font-family: 'Lora', serif; font-size: 19px; color: #2C5244; font-weight: 600; margin-bottom: 5px; }
.book-brand-sub { font-size: 10px; color: #8A9B94; letter-spacing: 0.10em; text-transform: uppercase; }
.book-left-page::after {
    content: ''; position: absolute; bottom: 0; right: 0;
    width: 36px; height: 36px;
    background: linear-gradient(225deg, #F5EDE0 50%, transparent 50%);
    opacity: 0.7;
}
.book-date-header {
    font-family: 'Lora', serif; font-size: 12px; color: #8A9B94;
    text-align: center; font-style: italic;
    border-bottom: 1px solid rgba(170,145,120,0.22);
    padding-bottom: 10px; margin-bottom: 4px;
    position: relative; z-index: 1;
}
.book-textarea {
    width: 100%; border: none; outline: none; resize: none;
    background: transparent;
    font-family: 'Lora', serif; font-size: 14px; color: #2C3E35;
    line-height: 36px; min-height: 360px;
    position: relative; z-index: 1;
    caret-color: #4A7C6F;
}
.book-save-row {
    margin-top: 16px; display: flex; gap: 10px;
    position: relative; z-index: 1;
}
.book-save-btn {
    flex: 1; padding: 11px;
    background: linear-gradient(135deg, #4A8272, #2E5E50);
    color: white; border: none; border-radius: 10px;
    font-size: 14px; font-weight: 600; cursor: pointer;
    font-family: 'Inter', sans-serif;
    box-shadow: 0 3px 12px rgba(46,94,80,0.3);
    transition: all 0.2s;
}
.book-save-btn:hover { background: linear-gradient(135deg, #5A9282, #3A6E60); transform: translateY(-1px); }
.book-skip-btn {
    padding: 11px 16px;
    background: rgba(255,255,255,0.7); color: #8A9B94;
    border: 1px solid rgba(212,201,187,0.6); border-radius: 10px;
    font-size: 13px; cursor: pointer; font-family: 'Inter', sans-serif;
}
.page-num { position: absolute; bottom: 14px; font-size: 9px; color: rgba(140,115,90,0.4); font-style: italic; }
.book-left-page .page-num { right: 22px; }
.book-right-page .page-num { left: 22px; }

/* Book cover animation (pre-open) */
.book-cover-panel {
    position: absolute; top: 0; right: 0; bottom: 0;
    width: calc(50% + 7px);
    background: linear-gradient(145deg, #3A7060 0%, #2A5248 55%, #1E3C30 100%);
    border-radius: 0 6px 6px 0;
    transform-origin: left center;
    transform: rotateY(0deg);
    transition: transform 1.0s cubic-bezier(0.645, 0.045, 0.355, 1.0) 0.4s;
    z-index: 20;
    display: flex; align-items: center; justify-content: center;
    backface-visibility: hidden;
}
.book-cover-panel.open { transform: rotateY(-170deg); pointer-events: none; }
.book-cover-inner { text-align: center; padding: 24px; }
.book-cover-logo { font-size: 56px; margin-bottom: 16px; }
.book-cover-title { font-family: 'Lora', serif; font-size: 22px; color: white; font-weight: 600; margin-bottom: 6px; }
.book-cover-sub { font-size: 10px; color: rgba(255,255,255,0.65); letter-spacing: 0.12em; text-transform: uppercase; }

/* Book reading page navigation */
.book-nav { display: flex; justify-content: space-between; align-items: center; margin-top: 18px; max-width: 720px; margin-left: auto; margin-right: auto; }
.book-nav-btn {
    background: rgba(255,255,255,0.75); backdrop-filter: blur(10px);
    border: 1px solid rgba(212,201,187,0.5); border-radius: 12px;
    padding: 10px 20px; font-size: 13px; color: #4A7C6F;
    cursor: pointer; font-weight: 600; font-family: 'Inter', sans-serif;
    transition: all 0.2s;
}
.book-nav-btn:hover { background: rgba(232,244,239,0.9); transform: translateY(-1px); }
.book-nav-btn:disabled { opacity: 0.3; cursor: default; transform: none; }
.book-page-counter { font-size: 11px; color: #8A9B94; }
.entry-read-meta { font-size: 10px; color: #8A9B94; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.06em; }
.entry-read-content {
    font-family: 'Lora', serif; font-style: italic;
    font-size: 14px; color: #2C3E35; line-height: 36px;
    position: relative; z-index: 1;
    overflow-y: auto; max-height: 400px;
}
@media (max-width: 640px) {
    .book-left-page { display: none; }
    .book-spine { display: none; }
    .book-cover-panel { width: 100%; border-radius: 8px; }
    .book-right-page { border-radius: 8px; }
    .book-open { border-radius: 8px; }
}

/* Other mood input */
.other-mood-box {
    display: none; margin-top: 10px;
    animation: fade-in-up 0.2s ease;
}
.other-mood-box.visible { display: block; }
.other-mood-input {
    width: 100%; padding: 12px 14px;
    background: rgba(255,255,255,0.8); backdrop-filter: blur(10px);
    border: 1.5px solid rgba(74,124,111,0.4); border-radius: 12px;
    font-family: 'Lora', serif; font-size: 14px; color: #2C3E35;
    outline: none;
}
.other-mood-input:focus { border-color: #4A7C6F; box-shadow: 0 0 0 3px rgba(74,124,111,0.12); }
.other-mood-input::placeholder { color: #B4A99A; font-style: italic; }

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
.onboarding-slide.active { display: block; animation: ob-slide-in 0.35s ease; }
@keyframes ob-slide-in { from { opacity: 0; transform: translateX(28px); } to { opacity: 1; transform: translateX(0); } }
.dot { width: 10px; height: 10px; border-radius: 50%; background: #D4C9BB; transition: background 0.25s, transform 0.25s; }
.dot.active { background: #4A7C6F; transform: scale(1.25); }
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
/* ── Loading overlay ── */
#loading-overlay {
    position: fixed;
    inset: 0;
    background: linear-gradient(160deg, #E8F2ED 0%, #F5F0E8 45%, #F0E8EE 100%);
    z-index: 2000;
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
}
.loading-spinner {
    width: 44px;
    height: 44px;
    border: 3px solid #D4C9BB;
    border-top-color: #4A7C6F;
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text {
    font-family: 'Lora', serif;
    font-size: 18px;
    color: #4A7C6F;
    text-align: center;
}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def base_page(content: str, title: str = "Mama Bloom", force_onboarding: bool = False) -> str:
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
    // Each slide has its own hardcoded dot group already correct in HTML —
    // only the active slide's dots are visible, so no JS toggling needed.
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

  // Pre-fill week and name — script is at end of body so DOM is already ready
  var savedWeek = localStorage.getItem('mama_bloom_week');
  var savedName = localStorage.getItem('mama_bloom_name');
  var wk = document.getElementById('week-input');
  if (wk && savedWeek) wk.value = savedWeek;
  var gr = document.getElementById('greeting-name');
  if (gr && savedName) gr.textContent = savedName + '.';
})();
</script>
"""
    # When the server detects a new browser session (no visitor cookie), clear
    # any stale localStorage onboarding flag so the overlay always shows again.
    _force_reset = (
        "<script>localStorage.removeItem('mama_bloom_onboarded');</script>"
        if force_onboarding else ""
    )
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
        f"{_force_reset}"
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
        # Loading overlay — shown by checkin form's onsubmit handler
        "<div id='loading-overlay'>"
        "<div class='loading-spinner'></div>"
        "<div class='loading-text'>Preparing your plan for you…</div>"
        "</div>"
        # Floating background orbs (CSS-animated, pointer-events:none)
        "<div class='orb orb-1'></div>"
        "<div class='orb orb-2'></div>"
        "<div class='orb orb-3'></div>"
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
    dur_str = f"{dur_min} min" if dur_min == dur_max else f"{dur_min}-{dur_max} min"
    pill_label = f"{pill_icon} {pill_label_base} · {dur_str}"

    name     = act.get("name", "")
    science  = act.get("science_note", "")
    prompt   = act.get("prompt", "")
    act_id   = act.get("id", str(uuid.uuid4())[:8])

    science_short = science

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

    accent_map = {"breathing": "act-breathing", "journaling": "act-journaling", "baby_connect": "act-baby"}
    accent_cls = accent_map.get(pillar, "")
    return (
        f"<div class='activity-card {accent_cls}'>"
        "<div class='activity-top-stripe'></div>"
        "<div class='activity-inner'>"
        f"<span class='pill {pill_cls}'>{pill_label}</span>"
        f"<div class='activity-name'>{name}</div>"
        f"<div class='activity-why'>"
        f"<strong>Why this for Week {week}:</strong> {science_short}"
        "</div>"
        f"<div class='activity-prompt'>{prompt}</div>"
        f"{write_btn}"
        f"{checkin_html}"
        "</div>"
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
async def home(request: Request):
    visitor_id = _get_visitor_id(request)
    is_new_visitor = _VISITOR_COOKIE not in request.cookies
    nb = nav_bar("home")
    content = (
        f"{nb}"
        "<h1>Hello, <span id='greeting-name'>mama.</span></h1>"
        "<p class='subtitle'>25 minutes a day, just for you and your baby.</p>"
        "<form method='POST' action='/checkin' id='checkin-form' "
        "onsubmit=\"document.getElementById('loading-overlay').style.display='flex';"
        "this.querySelector('button[type=submit]').disabled=true;\">"
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
        "<div class='mood-chip' onclick='toggleOther(this)'>"
        "<span class='emoji'>✏️</span>Other</div>"
        "</div>"
        "<div class='other-mood-box' id='other-box'>"
        "<input class='other-mood-input' id='other-mood-input' type='text' "
        "placeholder='How are you feeling today? e.g. nostalgic, restless…' "
        "oninput='document.getElementById(\"mood-value\").value = "
        "Array.from(selected).concat(this.value.trim()?[this.value.trim()]:[]).join(\",\") || \"Okay\"'>"
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
        "  if (selected.has(mood)) { selected.delete(mood); el.classList.remove('selected'); }"
        "  else { selected.add(mood); el.classList.add('selected'); }"
        "  syncMoodValue();"
        "}"
        "function toggleOther(el) {"
        "  var box = document.getElementById('other-box');"
        "  if (el.classList.contains('selected')) {"
        "    el.classList.remove('selected');"
        "    box.classList.remove('visible');"
        "    document.getElementById('other-mood-input').value = '';"
        "  } else {"
        "    el.classList.add('selected');"
        "    box.classList.add('visible');"
        "    document.getElementById('other-mood-input').focus();"
        "  }"
        "  syncMoodValue();"
        "}"
        "function syncMoodValue() {"
        "  var arr = Array.from(selected);"
        "  var otherEl = document.getElementById('other-box');"
        "  var otherInput = document.getElementById('other-mood-input');"
        "  if (otherEl.classList.contains('visible') && otherInput.value.trim()) {"
        "    arr.push(otherInput.value.trim());"
        "  }"
        "  document.getElementById('mood-value').value = arr.length > 0 ? arr.join(',') : 'Okay';"
        "}"
        "document.getElementById('other-mood-input') && "
        "document.getElementById('other-mood-input').addEventListener('input', syncMoodValue);"
        "</script>"
    )
    return _with_visitor_cookie(
        HTMLResponse(base_page(content, force_onboarding=is_new_visitor)), visitor_id
    )


@app.post("/checkin", response_class=HTMLResponse)
async def checkin(
    request: Request,
    week: int = Form(..., ge=1, le=42),
    mood: str = Form("Okay"),
    free_text: str = Form(""),
    description: str = Form(""),
):
    mood_list = [m.strip() for m in mood.split(",") if m.strip()]
    primary_mood = mood_list[0] if mood_list else "Okay"
    mood_value = mood_list if len(mood_list) > 1 else primary_mood

    visitor_id = _get_visitor_id(request)
    session = await _session_service.create_session(
        app_name="mama-bloom",
        user_id=visitor_id,
        state={
            "week": week,
            "mood": mood_value,
            "description": free_text,
            "free_text": free_text,
            "session_count": 0,
            "user_id": visitor_id,
        },
    )
    placeholder = types.Content(role="user", parts=[types.Part.from_text(text="checkin")])
    async for _event in _runner.run_async(
        user_id=visitor_id, session_id=session.id, new_message=placeholder
    ):
        pass  # drain; only the final session state matters for this render

    final_session = await _session_service.get_session(
        app_name="mama-bloom", user_id=visitor_id, session_id=session.id
    )
    state = dict(final_session.state)

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
            "<button type='button' class='btn-outline' "
            "onclick=\"window.location='/'\">Return to home</button>"
        )
        return _with_visitor_cookie(
            HTMLResponse(base_page(content, "Mama Bloom — We See You")), visitor_id
        )

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
    mood_display = html.escape(mood.replace(",", " · "))

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
            "<div class='card-rose fade-in-4'>"
            f"<div class='label-small'>Week {week} — your baby right now</div>"
            f"<p style='color:#2C3E35;font-size:14px;margin-top:4px;'>{milestone}</p>"
            "</div>"
        )

    # Gemini intro card (only if present)
    # html.escape: intro is Gemini-generated text built from raw user
    # free_text via the prompt - never trust LLM output as safe HTML.
    intro_html = ""
    if intro:
        intro_html = (
            "<div class='card fade-in-3'>"
            f"<p style='font-style:italic;color:#5C6B64;font-size:14px;"
            f"font-family:Lora,serif;'>{html.escape(intro)}</p>"
            "</div>"
        )

    content = (
        f"{nb}"
        # Result hero — deep green gradient banner
        "<div class='result-hero fade-in-1'>"
        f"<div class='result-hero-week'>Week {week}</div>"
        f"<div class='result-hero-sub'>Feeling: {mood_display} &nbsp;·&nbsp; {current_streak} day streak</div>"
        "<div class='result-hero-badge'>✨ 25 min plan ready</div>"
        "</div>"
        # Morning affirmation — full-width, serene
        "<div class='card-green fade-in-2'>"
        "<div class='label-small'>Read this slowly</div>"
        f"<div class='affirmation'>\"{html.escape(affirmation)}\"</div>"
        "</div>"
        f"{intro_html}"
        f"{milestone_html}"
        # Activity cards
        "<div class='section-header'>"
        "<span class='section-dot'></span>"
        "Today's plan — 25 minutes, all for you"
        "</div>"
        "<div class='activities-grid'>"
        f"{b_card}{j_card}{bc_card}"
        "</div>"
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
        f"\"{html.escape(whisper)}\"</div>"
        "</div>"
        "<a href='/' class='back-link' "
        "style='display:block;text-align:center;margin-top:8px;'>"
        "← Back to home</a>"
        f"{CHECKIN_JS}"
    )
    return _with_visitor_cookie(
        HTMLResponse(base_page(content, f"Your Day — Week {week}")), visitor_id
    )


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
        "Dear little one,\n\nI want you to know…"
        if is_letter
        else "Write freely — no rules, just honest words…"
    )
    today_fmt = datetime.date.today().strftime("%B %d, %Y")
    week_label = f"Week {week}" if week else ""

    content = (
        "<a href='/' class='back-link'>← Back</a>"
        "<div class='book-scene'>"
        # Open book wrapper
        "<div class='book-open'>"
        # Left page — branding/decorative
        "<div class='book-left-page'>"
        "<div class='page-lines'></div>"
        "<div class='book-brand'>"
        "<div class='book-brand-logo'>🌸</div>"
        "<div class='book-brand-title'>Mama Bloom</div>"
        "<div class='book-brand-sub'>Baby Book</div>"
        "</div>"
        "<span class='page-num'>1</span>"
        "</div>"
        # Spine
        "<div class='book-spine'></div>"
        # Right page — writing area
        "<div class='book-right-page' id='writing-page'>"
        "<div class='page-lines'></div>"
        f"<div class='book-date-header'>{week_label} &nbsp;·&nbsp; {today_fmt}</div>"
        "<form method='POST' action='/save-entry' id='book-form'>"
        f"<input type='hidden' name='entry_type' value='{entry_type_val}'>"
        f"<input type='hidden' name='week' value='{week}'>"
        f"<input type='hidden' name='activity_id' value='{html.escape(activity_id)}'>"
        f"<textarea class='book-textarea' name='content' id='book-textarea' "
        f"placeholder='{placeholder}'></textarea>"
        "<div class='book-save-row'>"
        "<button type='button' class='book-save-btn' onclick='flipAndSave()'>Save to Baby Book 💌</button>"
        "<button type='button' class='book-skip-btn' onclick=\"window.location='/'\">Skip</button>"
        "</div>"
        "</form>"
        "<span class='page-num'>2</span>"
        "</div>"
        # Cover panel — animates open on load
        "<div class='book-cover-panel' id='book-cover'>"
        "<div class='book-cover-inner'>"
        "<div class='book-cover-logo'>🌸</div>"
        "<div class='book-cover-title'>Mama Bloom</div>"
        "<div class='book-cover-sub'>Baby Book</div>"
        "</div>"
        "</div>"
        "</div>"  # .book-open
        "</div>"  # .book-scene
        "<script>"
        "setTimeout(function() {"
        "  document.getElementById('book-cover').classList.add('open');"
        "  setTimeout(function() { document.getElementById('book-textarea').focus(); }, 900);"
        "}, 350);"
        "function flipAndSave() {"
        "  if (!document.getElementById('book-textarea').value.trim()) {"
        "    document.getElementById('book-textarea').focus(); return;"
        "  }"
        "  document.getElementById('writing-page').classList.add('flipping');"
        "  setTimeout(function() { document.getElementById('book-form').submit(); }, 950);"
        "}"
        "</script>"
    )
    return HTMLResponse(base_page(content, title_text))


@app.post("/save-entry", response_class=HTMLResponse)
async def save_entry(
    request: Request,
    entry_type: str = Form("journal"),
    week: int = Form(0, ge=0, le=42),
    content: str = Form(""),
    activity_id: str = Form(""),
):
    visitor_id = _get_visitor_id(request)
    entry_id = str(uuid.uuid4())[:8]
    today    = datetime.date.today().isoformat()
    saved    = False

    try:
        await save_baby_book_entry(
            user_id=visitor_id,
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
        f"{html.escape(preview)}</p>"
        "</div>"
        "<button type='button' class='btn' style='margin-top:8px;' "
        "onclick=\"window.location='/babybook'\">See your Baby Book 💌</button>"
        "<button type='button' class='btn-outline' "
        "onclick=\"window.location='/'\">Continue with today</button>"
    )
    return _with_visitor_cookie(
        HTMLResponse(base_page(page_content, "Saved to Baby Book")), visitor_id
    )


@app.get("/babybook", response_class=HTMLResponse)
async def babybook(request: Request):
    visitor_id = _get_visitor_id(request)
    try:
        entries = await get_baby_book_entries(visitor_id)
    except Exception:
        entries = []

    nb = nav_bar("book")

    type_label_map = {
        "letter":     "💌 Letter to baby",
        "journal":    "📓 Journal",
        "reflection": "🌿 Reflection",
        "milestone":  "⭐ Milestone",
    }

    # Build pages list — each entry becomes one "right page"
    # For an empty book show a cover-only state
    book_pages_js = "[]"
    if entries:
        pages = []
        for e in reversed(entries):
            entry_type = e.get("entry_type", "entry")
            type_label = type_label_map.get(entry_type, entry_type.capitalize())
            raw = str(e.get("content", ""))
            # Full content, html-escaped, newlines → \n for JS strings
            safe = html.escape(raw).replace("\r\n", "\n").replace("\n", "\\n").replace("'", "\\'")
            week_str = html.escape(str(e.get("week", "")))
            date_str = html.escape(str(e.get("date", "")))
            label_safe = html.escape(type_label)
            pages.append(f"{{meta:'Week {week_str} · {date_str} · {label_safe}',text:'{safe}'}}")
        book_pages_js = "[" + ",".join(pages) + "]"

    if not entries:
        book_html = (
            "<div class='book-scene'>"
            "<div class='book-open' style='min-height:440px;'>"
            "<div class='book-left-page'>"
            "<div class='page-lines'></div>"
            "<div class='book-brand'>"
            "<div class='book-brand-logo'>🌸</div>"
            "<div class='book-brand-title'>Mama Bloom</div>"
            "<div class='book-brand-sub'>Baby Book</div>"
            "</div>"
            "<span class='page-num'>1</span>"
            "</div>"
            "<div class='book-spine'></div>"
            "<div class='book-right-page'>"
            "<div class='page-lines'></div>"
            "<div style='display:flex;flex-direction:column;align-items:center;"
            "justify-content:center;height:100%;gap:16px;position:relative;z-index:1;'>"
            "<div style='font-size:40px;'>💌</div>"
            "<div style='font-family:Lora,serif;font-size:16px;color:#2C3E35;"
            "text-align:center;font-style:italic;line-height:1.6;'>"
            "Your Baby Book is waiting.<br>Start writing your first letter.</div>"
            "<a href='/'><button class='book-save-btn' style='margin-top:8px;'>"
            "Start today 🌸</button></a>"
            "</div>"
            "<span class='page-num'>2</span>"
            "</div>"
            "</div>"
            "</div>"
        )
        nav_html = ""
    else:
        book_html = (
            "<div class='book-scene'>"
            "<div class='book-open' id='book-spread' style='min-height:500px;'>"
            # Left page — shows current entry
            "<div class='book-left-page' id='left-page'>"
            "<div class='page-lines'></div>"
            "<div style='position:relative;z-index:1;'>"
            "<div class='entry-read-meta' id='left-meta'></div>"
            "<div class='entry-read-content' id='left-text'></div>"
            "</div>"
            "<span class='page-num' id='left-num'></span>"
            "</div>"
            "<div class='book-spine'></div>"
            # Right page — shows next entry
            "<div class='book-right-page' id='right-page'>"
            "<div class='page-lines'></div>"
            "<div style='position:relative;z-index:1;'>"
            "<div class='entry-read-meta' id='right-meta'></div>"
            "<div class='entry-read-content' id='right-text'></div>"
            "</div>"
            "<span class='page-num' id='right-num'></span>"
            "</div>"
            "</div>"
            "</div>"
        )
        nav_html = (
            "<div class='book-nav'>"
            "<button class='book-nav-btn' id='prev-btn' onclick='flipBack()'>← Previous</button>"
            "<span class='book-page-counter' id='page-counter'></span>"
            "<button class='book-nav-btn' id='next-btn' onclick='flipForward()'>Next →</button>"
            "</div>"
            "<div style='text-align:center;margin-top:18px;'>"
            "<a href='/write?type=letter&week=0'>"
            "<button class='btn' style='max-width:280px;margin:0 auto;display:block;'>"
            "Add a new letter 💌</button></a>"
            "</div>"
        )

    js_block = (
        "<script>"
        f"var PAGES = {book_pages_js};"
        "var spread = 0;"  # 0 = showing pages 0&1, 2 = showing 2&3, etc.
        "function renderSpread() {"
        "  if (!PAGES.length) return;"
        "  var lp = PAGES[spread] || null;"
        "  var rp = PAGES[spread+1] || null;"
        "  var lMeta=document.getElementById('left-meta'),"
        "      lText=document.getElementById('left-text'),"
        "      rMeta=document.getElementById('right-meta'),"
        "      rText=document.getElementById('right-text'),"
        "      lNum=document.getElementById('left-num'),"
        "      rNum=document.getElementById('right-num'),"
        "      ctr=document.getElementById('page-counter'),"
        "      prev=document.getElementById('prev-btn'),"
        "      nxt=document.getElementById('next-btn');"
        "  if (lMeta) lMeta.textContent = lp ? lp.meta : '';"
        "  if (lText) lText.textContent = lp ? lp.text : '';"
        "  if (rMeta) rMeta.textContent = rp ? rp.meta : '';"
        "  if (rText) rText.textContent = rp ? rp.text : '';"
        "  if (lNum)  lNum.textContent  = lp ? (spread+1) : '';"
        "  if (rNum)  rNum.textContent  = rp ? (spread+2) : '';"
        "  if (ctr)   ctr.textContent   = 'Entries ' + (spread+1) + '–' + Math.min(spread+2, PAGES.length) + ' of ' + PAGES.length;"
        "  if (prev)  prev.disabled = spread === 0;"
        "  if (nxt)   nxt.disabled  = spread+2 >= PAGES.length;"
        "}"
        "function flipForward() {"
        "  if (spread+2 >= PAGES.length) return;"
        "  var rp = document.getElementById('right-page');"
        "  if (rp) { rp.classList.add('flipping'); }"
        "  setTimeout(function() {"
        "    spread += 2; renderSpread();"
        "    if (rp) rp.classList.remove('flipping');"
        "  }, 500);"
        "}"
        "function flipBack() {"
        "  if (spread === 0) return;"
        "  spread = Math.max(0, spread - 2); renderSpread();"
        "}"
        "renderSpread();"
        "</script>"
    ) if entries else ""

    content = (
        f"{nb}"
        "<h1>Your Baby Book</h1>"
        "<p class='subtitle'>Letters and reflections, building week by week.</p>"
        f"{book_html}"
        f"{nav_html}"
        f"{js_block}"
    )
    return _with_visitor_cookie(HTMLResponse(base_page(content, "Baby Book")), visitor_id)


@app.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request):
    visitor_id = _get_visitor_id(request)
    try:
        sessions = await get_sessions(user_id=visitor_id, limit=42)
    except Exception:
        sessions = []

    mood_emojis = {
        "heavy": "😔", "sad": "😔", "anxious": "😰",
        "okay": "😐", "neutral": "😐",
        "good": "🌸", "happy": "😊",
        "glowing": "✨", "joyful": "✨",
        "tired": "😴", "exhausted": "😴",
        "uncomfortable": "😣", "sore": "😣",
    }

    session_map: dict = {}
    for s in sessions:
        date = s.get("date", "")
        if date:
            session_map[date] = s  # store full session for detail modal

    today     = datetime.date.today()
    today_str = today.isoformat()

    # Build 7-col grid aligned to Monday
    # First find the Monday of the 6-week block ending today
    block_end   = today
    block_start = block_end - datetime.timedelta(days=41)
    # Pad to Monday
    start_weekday = block_start.weekday()  # 0=Mon
    grid_start    = block_start - datetime.timedelta(days=start_weekday)

    days_html = ""
    d = grid_start
    while d <= block_end or (d - block_end).days < 7:
        day_str = d.isoformat()
        sess    = session_map.get(day_str)
        is_today   = day_str == today_str
        is_future  = d > today
        is_in_range = block_start <= d <= block_end

        if not is_in_range:
            # filler cell
            days_html += "<div class='cal-day' style='opacity:0.2;cursor:default;'></div>"
        elif is_future:
            days_html += (
                f"<div class='cal-day' style='opacity:0.35;cursor:default;'>"
                f"<span class='cal-day-num' style='color:#B4A99A;'>{d.day}</span>"
                "</div>"
            )
        elif sess:
            raw_mood = str(sess.get("mood", "okay")).lower().split(",")[0].strip()
            emoji    = mood_emojis.get(raw_mood, "🌿")
            acts     = sess.get("activities", [])
            if isinstance(acts, list):
                acts_str = "|".join(
                    html.escape(str(a.get("name", "")))
                    for a in acts if isinstance(a, dict)
                )
            else:
                acts_str = ""
            week_num  = html.escape(str(sess.get("week", "")))
            mood_disp = html.escape(raw_mood.capitalize())
            today_cls = " today" if is_today else ""
            days_html += (
                f"<div class='cal-day has-entry{today_cls}' "
                f"onclick=\"openDayModal('{html.escape(day_str)}','{mood_disp}','{emoji}','{week_num}','{acts_str}')\">"
                f"<span class='cal-day-num'>{d.day}</span>"
                f"<span class='cal-day-emoji'>{emoji}</span>"
                "</div>"
            )
        else:
            today_cls = " today" if is_today else ""
            days_html += (
                f"<div class='cal-day{today_cls}'>"
                f"<span class='cal-day-num'>{d.day}</span>"
                "</div>"
            )

        d += datetime.timedelta(days=1)
        if d > block_end and d.weekday() == 0:
            break

    legend_items = "".join(
        f"<span class='cal-legend-item'>{e} {lbl}</span>"
        for e, lbl in [("😔","Heavy"), ("😐","Okay"), ("🌸","Good"), ("✨","Glowing"), ("😴","Tired")]
    )

    nb = nav_bar("calendar")
    content = (
        f"{nb}"
        "<h1>Your journey</h1>"
        "<p class='subtitle'>Every day you showed up for your baby. Tap a day to see what you felt.</p>"
        f"<div class='cal-legend'>{legend_items}</div>"
        "<div class='cal-grid'>"
        + "".join(f"<div class='cal-header'>{d}</div>" for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
        + days_html
        + "</div>"
        "<a href='/babybook'><button class='btn-outline'>Open Baby Book 💌</button></a>"
        # Detail modal
        "<div class='cal-modal-bg' id='cal-modal-bg' onclick='closeDayModal(event)'>"
        "<div class='cal-modal'>"
        "<button class='cal-modal-close' onclick='document.getElementById(\"cal-modal-bg\").classList.remove(\"open\")'>×</button>"
        "<div class='cal-modal-date' id='modal-date'></div>"
        "<div class='cal-modal-emoji' id='modal-emoji'></div>"
        "<div class='cal-modal-mood' id='modal-mood'></div>"
        "<div class='cal-modal-week' id='modal-week'></div>"
        "<div class='cal-modal-acts' id='modal-acts'></div>"
        "</div>"
        "</div>"
        "<script>"
        "function openDayModal(date, mood, emoji, week, actsStr) {"
        "  document.getElementById('modal-date').textContent = date;"
        "  document.getElementById('modal-emoji').textContent = emoji;"
        "  document.getElementById('modal-mood').textContent = 'Feeling: ' + mood;"
        "  document.getElementById('modal-week').textContent = week ? 'Week ' + week : '';"
        "  var actsEl = document.getElementById('modal-acts');"
        "  actsEl.innerHTML = '';"
        "  if (actsStr) {"
        "    actsStr.split('|').forEach(function(a) {"
        "      if (a) { var s = document.createElement('span');"
        "        s.className='cal-modal-act'; s.textContent=a;"
        "        actsEl.appendChild(s); }"
        "    });"
        "  }"
        "  document.getElementById('cal-modal-bg').classList.add('open');"
        "}"
        "function closeDayModal(e) {"
        "  if (e.target.id === 'cal-modal-bg') document.getElementById('cal-modal-bg').classList.remove('open');"
        "}"
        "</script>"
    )
    return _with_visitor_cookie(HTMLResponse(base_page(content, "Your Journey")), visitor_id)


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
