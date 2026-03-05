---
name: linkedin-compose
description: Production LinkedIn draft generation from SALES_INFO source of truth
---

# linkedin-compose

[LINKEDIN MODE ACTIVATED]

## Operating Goal
Generate publish-ready LinkedIn drafts with consistent conversion structure.

## Input
- `~/.claude/.js/projects/<project>/SALES_INFO.md`

## Output
- `~/.claude/.js/projects/<project>/channels/linkedin/drafts/<yyyymmdd-hhmm>.md`

## Execution Rules
1) Use `SALES_INFO.md` as single source of truth.
2) No interview flow.
3) Publish stays dry-run in console unless explicitly confirmed.

## Commands
```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PROJECT="${JUSTSELL_PROJECTS_DIR:-$CLAUDE_DIR/.js/projects}/<project>"
python3 scripts/generate_drafts.py linkedin --project "$PROJECT" --style bernays
```
