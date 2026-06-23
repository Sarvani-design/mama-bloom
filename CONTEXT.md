# MAMA BLOOM — SECURITY STANDARDS
# Read this before every code change in this project.

## Identity
This is Mama Bloom — a maternal emotional wellbeing companion for pregnant mothers.
It is NOT a medical app. It supports emotional wellbeing only.

## Non-negotiable rules
- The safety_screen node MUST always run BEFORE any Gemini API call. No exceptions.
- crisis_response node MUST never call Gemini under any circumstances.
- GEMINI_API_KEY must always be read from environment variable. Never hardcoded.
- .env must never be committed to git.
- Medical disclaimer must appear on every page of the web app.

## Medical disclaimer text
"Mama Bloom supports your emotional wellbeing during pregnancy.
It is not a substitute for medical advice — always consult your
doctor or midwife."

## Crisis message requirements
Crisis message MUST contain both helpline numbers:
- iCall: 9152987821
- Vandrevala Foundation: 1860-2662-345 (available 24/7)

## Data privacy
- Never log or store the mother's personal name or exact location
- Health and mood data stored only locally via MCP filesystem server
- No health data sent to external APIs beyond the single Gemini API call

## PII protection
- Phone numbers and email addresses must be redacted before any LLM call
- Log when PII is redacted — never log the actual content

## Code comments required
Every node must have a comment identifying which course day it demonstrates:
- Day 1: ADK 2.0 graph workflow
- Day 2: MCP Server
- Day 3: Session memory
- Day 4: Safety guardrail / PII redaction / evaluation
- Day 5: Cloud Run deployment
