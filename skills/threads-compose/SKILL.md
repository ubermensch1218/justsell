---
name: threads-compose
description: Production Threads draft generation from SALES_INFO source of truth
---

# threads-compose

[THREADS MODE ACTIVATED]

## Operating Goal
Generate high-signal Threads drafts for fast posting cadence.

## Input
- `~/.claude/.js/projects/<project>/SALES_INFO.md`

## Output
- `~/.claude/.js/projects/<project>/channels/threads/drafts/<yyyymmdd-hhmm>.md`

## Execution Rules
1) Use `SALES_INFO.md` as single source of truth.
2) No interview flow.
3) Publish stays dry-run in console unless explicitly confirmed.

## Commands
```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PROJECT="${JUSTSELL_PROJECTS_DIR:-$CLAUDE_DIR/.js/projects}/<project>"
python3 scripts/generate_drafts.py threads --project "$PROJECT" --style bernays
```
