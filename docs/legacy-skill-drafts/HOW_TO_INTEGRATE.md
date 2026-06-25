# HOW TO ADD MAMA BLOOM SKILLS TO YOUR EXISTING PROJECT
# Step-by-step — safe to do on a running project, nothing will break

---

## WHAT THESE SKILLS DO

Each `.skill` folder contains a `SKILL.md` file.
Antigravity IDE reads these files automatically before generating or
modifying code in the relevant area of your project.

Think of them as "guardrails + memory" for Antigravity:
- It will never write ADK 1.x code again
- It will never put Gemini before the safety node
- It will always include medical disclaimers
- It will always use the correct activity routing rules

---

## STEP 1 — Copy the Skills Folder Into Your Project

From this download, you have a folder called `mama-bloom-skills/`.
It contains 6 subfolders, each with a `SKILL.md`.

Copy the entire folder into your existing project root:

```
your-project/
├── mama_bloom/          ← your existing code
├── tests/               ← your existing tests
├── README.md            ← your existing readme
├── .env                 ← your existing env file
│
└── mama-bloom-skills/   ← PASTE THIS FOLDER HERE  ← new
    ├── mama-bloom-adk-workflow/
    │   └── SKILL.md
    ├── mama-bloom-safety/
    │   └── SKILL.md
    ├── mama-bloom-activity-library/
    │   └── SKILL.md
    ├── mama-bloom-mcp-server/
    │   └── SKILL.md
    ├── mama-bloom-fastapi/
    │   └── SKILL.md
    └── mama-bloom-eval/
        └── SKILL.md
```

Nothing in your existing code changes. Nothing breaks.
This is purely additive — you're just adding files.

---

## STEP 2 — Install the Skills in Antigravity

In your Antigravity IDE terminal, run ONE of these:

### Option A — Install all 6 at once (recommended)
```bash
npx skills install ./mama-bloom-skills/mama-bloom-adk-workflow
npx skills install ./mama-bloom-skills/mama-bloom-safety
npx skills install ./mama-bloom-skills/mama-bloom-activity-library
npx skills install ./mama-bloom-skills/mama-bloom-mcp-server
npx skills install ./mama-bloom-skills/mama-bloom-fastapi
npx skills install ./mama-bloom-skills/mama-bloom-eval
```

### Option B — Install from the folder directly
```bash
for skill in mama-bloom-skills/*/; do
  npx skills install "./$skill"
done
```

### Verify installation
```bash
agents-cli info
```
You should see all 6 skills listed as active.

---

## STEP 3 — Verify Skills Are Working (2-minute test)

In Antigravity chat, type this:
```
"Fix the routing in agent.py so the activity_selector node runs"
```

If skills are working, Antigravity will:
✅ Read `mama-bloom-adk-workflow/SKILL.md` before touching agent.py
✅ Use only ADK 2.0 `FunctionNode` / `Edge` patterns
✅ Never write `SequentialAgent` or `LlmAgent`

If you see `SequentialAgent` in any output — skills are NOT installed.
Re-run Step 2.

---

## STEP 4 — Add CONTEXT.md to Your Project Root (if it doesn't exist)

Check if you already have one:
```bash
ls CONTEXT.md
```

If it exists — open it and add the Mama Bloom security rules at the top.
If it doesn't exist — create it:

```bash
cat > CONTEXT.md << 'EOF'
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
EOF
```

Antigravity reads CONTEXT.md automatically on every code change.

---

## STEP 5 — Which Skill Helps With What

When you're working in Antigravity and want help with a specific area,
just describe your task and the right skill triggers automatically.
But if you want to be explicit, here's the map:

| You're working on... | Skill that activates |
|---------------------|---------------------|
| `agent.py` — nodes, edges, graph | `mama-bloom-adk-workflow` |
| `tools.py` — safety functions | `mama-bloom-safety` |
| `config.py` — activities, routing | `mama-bloom-activity-library` |
| `mcp_server.py` — session tools | `mama-bloom-mcp-server` |
| `fast_api_app.py` — UI, endpoints | `mama-bloom-fastapi` |
| `tests/eval/` — grading, traces | `mama-bloom-eval` |
| `CONTEXT.md` — security rules | `mama-bloom-safety` |
| `Dockerfile` / Cloud Run | `mama-bloom-fastapi` |

---

## STEP 6 — Safe Ways to Use Skills With Your Existing Code

### To fix a bug in existing code:
Tell Antigravity:
```
"The activity_selector is serving PMR at Week 10 — fix the trimester rule"
```
The `mama-bloom-activity-library` skill will activate and guide the fix correctly.

### To add a new activity:
Tell Antigravity:
```
"Add a new breathing activity called Gentle Sigh — moods: tired, uncomfortable,
week_min 0, 3 minutes, trimester_min 1"
```
Skill will ensure the correct dict structure with all required keys.

### To run evaluation:
```bash
make generate-traces   # generates trace files
make grade             # runs LLM-as-judge scoring
```

### To check safety system is intact:
```bash
python -c "
from mama_bloom.tools import detect_distress, redact_pii
assert detect_distress('I feel hopeless') == True
assert detect_distress('I feel great') == False
assert '[REDACTED]' in redact_pii('call me at 9876543210')
print('Safety system OK')
"
```

---

## STEP 7 — What NOT to Do

❌ Don't rename the `mama-bloom-skills/` folder — Antigravity looks for it by path
❌ Don't edit SKILL.md files unless you want to change the rules permanently
❌ Don't commit the `data/` folder — it has health data (already in .gitignore)
❌ Don't add `.env` to git — check with `git status` before every push

---

## STEP 8 — Your Project's .gitignore Check

Make sure these are in your `.gitignore`:
```gitignore
.env
data/
*.session.json
__pycache__/
.venv/
dist/
```

Run this to check nothing sensitive is staged:
```bash
git status
# .env and data/ should NOT appear in the output
```

---

## QUICK REFERENCE — Skill Trigger Phrases

If a skill isn't activating, try these exact phrases in Antigravity chat:

| Skill | Phrase to trigger it |
|-------|---------------------|
| ADK Workflow | "build the workflow graph" / "add a node" / "wire the edges" |
| Safety | "safety screen" / "crisis response" / "PII redaction" / "distress" |
| Activity Library | "activity routing" / "mood to activity" / "trimester rule" / "config.py" |
| MCP Server | "save session" / "baby book" / "memory saver" / "mcp_server.py" |
| FastAPI | "web app" / "endpoint" / "check-in form" / "deploy to Cloud Run" |
| Eval | "generate traces" / "LLM as judge" / "eval_config" / "grade" |

---

## FINAL CHECK — Competition Readiness

Run this checklist once skills are installed and your project is built:

```bash
# 1. Safety check
python -c "from mama_bloom.tools import detect_distress; assert detect_distress('I feel hopeless')"
echo "✅ Safety keywords working"

# 2. PII redaction check
python -c "from mama_bloom.tools import redact_pii; assert '[REDACTED]' in redact_pii('9876543210')"
echo "✅ PII redaction working"

# 3. API key not hardcoded check
grep -r "AIza" mama_bloom/ && echo "❌ HARDCODED KEY FOUND" || echo "✅ No hardcoded keys"

# 4. Medical disclaimer in app
grep -r "not a substitute for medical advice" mama_bloom/ && echo "✅ Disclaimer in code"

# 5. Both helplines in crisis message
grep "9152987821" mama_bloom/config.py && echo "✅ iCall present"
grep "1860-2662-345" mama_bloom/config.py && echo "✅ Vandrevala present"

# 6. Eval traces exist
ls tests/eval/traces/ && echo "✅ Traces generated"

# 7. .env not committed
git ls-files .env && echo "❌ .ENV IN GIT — REMOVE NOW" || echo "✅ .env not in git"
```

All 7 must pass before submission.
