---
name: content-creator
description: Production multi-channel copy generation from SALES_INFO source of truth
---

# content-creator

[CONTENT MODE ACTIVATED]

## Operating Goal
Generate conversion-focused copy for Threads and LinkedIn in one pass.

## Source of Truth
- `~/.claude/.js/projects/<project>/SALES_INFO.md`

## Output
- Threads: `~/.claude/.js/projects/<project>/channels/threads/drafts/<timestamp>.md`
- LinkedIn: `~/.claude/.js/projects/<project>/channels/linkedin/drafts/<timestamp>.md`

## Execution Rules
1) Facts, numbers, pricing, and claims must come from `SALES_INFO.md`.
2) No interview flow.
3) Publish stays dry-run unless explicitly confirmed.

## Commands
```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PROJECT="${JUSTSELL_PROJECTS_DIR:-$CLAUDE_DIR/.js/projects}/<project>"

python3 scripts/generate_drafts.py threads --project "$PROJECT" --style bernays
python3 scripts/generate_drafts.py linkedin --project "$PROJECT" --style bernays
```
