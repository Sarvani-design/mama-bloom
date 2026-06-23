# 🌸 Mama Bloom — AI Maternal Wellbeing Companion

> A mood-adaptive AI agent that gives pregnant mothers a structured 
> 25-minute daily ritual of evidence-based emotional wellbeing 
> activities, personalised to their trimester, mood, and pregnancy 
> week — and builds a Baby Book over 9 months.

**Kaggle 5-Day AI Agents Intensive Capstone Project — Agents for Good Track**  
**Deadline: July 6, 2026**

---

## The Problem

25 million pregnancies occur in India every year. Maternal anxiety 
is the number one unaddressed risk — elevated cortisol crosses the 
placenta and directly disrupts fetal brain development, specifically 
the hippocampus and amygdala. No personalised, daily, accessible 
emotional support exists for most mothers.

---

## The Solution

Mama Bloom is a mood-adaptive AI agent that:

- Gives a pregnant mother a structured 25-minute daily ritual
- Personalises every session to her trimester, mood, and week
- Builds a Baby Book of letters and reflections over 9 months
- Detects distress and routes to crisis support instantly
- Never claims to treat or diagnose — supports wellbeing only

---

## What Makes It Different

- 100% secular — no religious content, universally inclusive
- Evidence-backed — 41 MBCP RCTs, NIH PMC citations, 
  Pennebaker, Kristin Neff self-compassion framework
- Mood-adaptive — not one-size-fits-all
- Safe — distress guardrail fires before any LLM call
- Builds something tangible — the Baby Book

---

## Medical Disclaimer

Mama Bloom supports your emotional wellbeing during pregnancy. 
It is not a substitute for medical advice — always consult your 
doctor or midwife.

---

## Agent Architecture — ADK 2.0 Graph
Mother Input: {week, mood, description}

│

▼

┌─────────────────┐

│ NODE 1          │ Pure Python. No LLM.

│ safety_screen   │ PII redacted. Distress checked.

└────────┬────────┘ # Day 4: Safety guardrail

│

┌────┴──────────────────┐

│ crisis                │ content

▼                       ▼

┌──────────────┐   ┌─────────────────────┐

│ NODE 2a      │   │ NODE 2b             │

│ crisis_      │   │ activity_selector   │

│ response     │   │ Gemini 2.0 Flash    │

│ NO LLM EVER  │   │ Warm intro + plan   │

└──────────────┘   └──────────┬──────────┘

│

▼

┌─────────────────────┐

│ NODE 3              │

│ content_generator   │

│ Pure Python         │

└──────────┬──────────┘

│

▼

┌─────────────────────┐

│ NODE 4              │

│ memory_saver        │

│ MCP Server call     │

└─────────────────────┘

---

## Course Concepts Demonstrated

| Day | Concept | Implementation |
|-----|---------|----------------|
| Day 1 | ADK 2.0 graph workflow | 4-node graph in agent.py |
| Day 2 | MCP Server | mcp_server.py with 6 tools |
| Day 3 | Session memory | Cross-session mood history |
| Day 4 | Security guardrails | safety_screen + PII redaction |
| Day 5 | Deployability | Dockerfile + Cloud Run ready |

---

## Activity Library

24 evidence-based activities across 3 daily pillars:

**Breathing (6 activities)**
Box Breathing, Extended Exhale, Body Scan, Progressive Muscle 
Relaxation, Safe Place Visualization, Loving-Kindness Meditation

**Journaling (4 activities)**
Free Mood Journal, Gratitude Journal, Self-Compassion Check-In, 
Birth Wishes Journal

**Baby Connect (5 activities + 2 creative + 1 music)**
Daily Narration, Story Time, Humming and Singing, Conversation 
with Baby, Evening Whisper, Bilateral Drawing, Symmetry Drawing, 
Calming Music

---

## Daily Experience

Every day the mother receives:

1. Morning affirmation — self-compassion framed, full screen
2. One breathing activity — mood adaptive
3. One journaling activity — alternating to avoid repetition
4. One baby connect activity — trimester appropriate
5. Evening whisper — one sentence spoken aloud to baby

Total time: approximately 25 minutes per day.

---

## Safety System

The safety_screen node runs before every LLM call. If distress 
keywords are detected, the agent immediately shows crisis support 
with real Indian helplines — no Gemini call, no delay, no 
activities shown.

Crisis helplines shown:
- iCall: 9152987821 (TISS — trained counselors)
- Vandrevala Foundation: 1860-2662-345 (24/7)

---

## Setup Instructions

### Prerequisites
- Python 3.11 or higher
- Node.js LTS
- Google Gemini API key from aistudio.google.com

### Installation

```bash
# Clone the repository
git clone https://github.com/Sarvani-design/mama-bloom.git
cd mama-bloom

# Install dependencies
uvx google-agents-cli setup
agents-cli install

# Create environment file
echo GEMINI_API_KEY=your-key-here > .env
```

### Run locally

```bash
.venv\Scripts\activate
uvicorn app.fast_api_app:app --reload --port 8080
```

Open browser at http://localhost:8080

### Run evaluation

```bash
agents-cli eval
```

---

## Project Structure
mama-bloom/

├── app/

│   ├── agent.py          # ADK 2.0 graph workflow

│   ├── config.py         # 24 activities + routing rules

│   ├── tools.py          # Safety functions + PII redaction

│   ├── mcp_server.py     # MCP server with 6 tools

│   └── fast_api_app.py   # FastAPI web interface

├── tests/eval/

│   ├── datasets/mama-bloom-eval.json  # 5 test scenarios

│   └── eval_config.yaml              # 6 LLM-as-judge metrics

├── CONTEXT.md            # Security standards

├── Dockerfile            # Cloud Run deployment

└── pyproject.toml        # Dependencies

---

## Research Citations

1. Mindfulness-Based Childbirth and Parenting — 41 RCTs showing 
   significant reduction in prenatal anxiety and stress hormones. 
   PMC10810490

2. Pennebaker expressive writing — 15 minutes 3 times per week 
   significantly reduces stress hormones and improves immune 
   function. PMC3830620

3. Kristin Neff self-compassion framework — stronger evidence than 
   affirmations alone for reducing anxiety and depression in the 
   perinatal period.

4. University of Florida fetal voice memory study — fetuses 
   recognise repeated voice patterns by Week 34. Voice builds 
   familiarity and maternal bonding simultaneously.

5. Maternal cortisol and fetal brain development — elevated 
   maternal cortisol crosses the placenta and disrupts development 
   of fetal hippocampus and amygdala. NIH PMC evidence base.

---

## Built With

- Google ADK 2.0 — agent graph workflow
- Google Antigravity CLI — agentic development environment
- Gemini 2.0 Flash — LLM for personalised responses
- FastAPI — web interface
- MCP filesystem server — session and Baby Book storage
- Python 3.11 — core language
- agents-cli — scaffold, eval, deploy toolchain

---

*Built with care for 25 million pregnant mothers in India.*