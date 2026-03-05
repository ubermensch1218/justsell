---
name: instagram-cardnews
description: Production-grade Instagram cardnews orchestration (zero-touch default)
---

# instagram-cardnews

[CARDNEWS MODE ACTIVATED]

## Mode
- Default: zero-touch auto-run
- Strict: `JUSTSELL_STRICT_PIPELINE=1`

## Parallel Roles
- `marketing-director`
- `cardnews-copy-chief`
- `cardnews-designer`
- `cardnews-quality-auditor`

## Inputs
- `~/.claude/.js/projects/<project>/SALES_INFO.md`

## Required Artifacts
- `_agent_settings.md`
- `_parallel_roles.md`
- `_creative_brief.md`
- `_strategy_lock.md`

## Commands
```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PROJECT="${JUSTSELL_PROJECTS_DIR:-$CLAUDE_DIR/.js/projects}/<project>"

python3 scripts/generate_drafts.py instagram-cardnews --project "$PROJECT" --style bernays --format yaml
LATEST_SPEC="$(ls -1t "$PROJECT/channels/instagram/cardnews/"*.yaml "$PROJECT/channels/instagram/cardnews/"*.json 2>/dev/null | head -n 1)"
python3 scripts/validate_cardnews_spec.py --spec "$LATEST_SPEC"
python3 scripts/render_cardnews.py --spec "$LATEST_SPEC" --out "$PROJECT/channels/instagram/exports"
```
