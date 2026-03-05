---
name: reddit-compose
description: Production Reddit draft generation with subreddit-aware tone controls
---

# reddit-compose

[REDDIT MODE ACTIVATED]

## Operating Goal
Generate Reddit drafts aligned to product, brand, and subreddit tone.

## Input
- `~/.claude/.js/projects/<project>/SALES_INFO.md`
- `~/.claude/.js/projects/<project>/brand.md`

## Output
- `~/.claude/.js/projects/<project>/channels/reddit/drafts/<yyyymmdd-hhmmss>.md`

## Execution Rules
1) Use local project files only.
2) No interview flow.
3) Keep publish as dry-run until explicit confirmation.

## Commands
```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PROJECT="${JUSTSELL_PROJECTS_DIR:-$CLAUDE_DIR/.js/projects}/<project>"
python3 scripts/generate_reddit_drafts.py --project "$PROJECT" --style bernays
python3 scripts/generate_reddit_drafts.py --project "$PROJECT" --style bernays --subreddit r/webdev
python3 scripts/generate_reddit_drafts.py --project "$PROJECT" --style comeback
```
