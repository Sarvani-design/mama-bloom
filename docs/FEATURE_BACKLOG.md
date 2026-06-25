# Feature Backlog — unbuilt ideas worth considering

These were pulled out of an earlier draft skill pack (`docs/legacy-skill-drafts/`)
that described a more ambitious version of Mama Bloom than what's currently
implemented. The drafted *architecture* in those files doesn't match the
real codebase (see `.claude/skills/` for the corrected, accurate skills) —
but a few of the *feature* ideas are legitimate, unbuilt candidates worth
scoping for the later UI-restructuring/new-features phase, not because the
draft said so, but on their own merits:

- **Triggered Baby Book letters** — a "First Letter to Baby" auto-prompted
  once in trimester 1, a "Hope Letter" once in trimester 2, a "Hard Day
  Letter" prompted specifically on heavy/sad-mood days, and a weekly
  (Day-7) milestone letter. Today, Baby Book entries are only created when
  the mother manually visits `/write` — these would be agent-initiated
  prompts instead.
- **Labour-prep affirmations** — a dedicated rotating affirmation set for
  week 28+, distinct from the single fixed string `get_morning_affirmation()`
  currently returns for that range.
- **Adaptive "still_hard" escalation** — track consecutive post-activity
  "still hard" check-ins (the `/complete` endpoint already collects this
  feeling but doesn't act on it yet) and respond with: 2 in a row → switch
  to a "low effort" daily plan (e.g. extended_exhale + gratitude_journal +
  evening_whisper); 3 in a row → a gentle resource nudge (not a crisis
  alert — distinct from the existing keyword-based crisis system).

None of these are scheduled — they're candidates to discuss when scoping
the UI-restructuring/new-features phase.
