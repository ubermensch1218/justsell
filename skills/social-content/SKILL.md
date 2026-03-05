---
name: social-content
description: Production weekly content pack orchestration (Threads + Instagram)
---

# social-content

[SOCIAL PACK MODE ACTIVATED]

## Operating Goal
Produce one consistent weekly pack in a single run.
- Threads draft + Instagram cardnews set
- Source of truth: `~/.claude/.js/projects/<project>/SALES_INFO.md`

## Parallel Roles
- `marketing-director`
- `social-ops`
- `cardnews-copy-chief`
- `cardnews-quality-auditor`

## Execution Rules
1) No interview flow.
2) Generate drafts first, render second.
3) Keep publish action in console as dry-run default.

## Commands
```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PROJECT="${JUSTSELL_PROJECTS_DIR:-$CLAUDE_DIR/.js/projects}/<project>"
python3 scripts/generate_drafts.py threads --project "$PROJECT" --style bernays

python3 scripts/generate_drafts.py instagram-cardnews --project "$PROJECT" --style bernays --format yaml
LATEST_SPEC="$(ls -1t "$PROJECT/channels/instagram/cardnews/"*.yaml "$PROJECT/channels/instagram/cardnews/"*.json 2>/dev/null | head -n 1)"
python3 scripts/validate_cardnews_spec.py --spec "$LATEST_SPEC"
python3 scripts/render_cardnews.py --spec "$LATEST_SPEC" --out "$PROJECT/channels/instagram/exports"
```

## Console Review
```bash
python3 scripts/justsell_console.py
```
Open `http://127.0.0.1:5678/` and publish only with explicit confirmation.
