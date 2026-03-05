---
description: Activate production cardnews orchestration mode
---

[CARDNEWS MODE ACTIVATED]

$ARGUMENTS

You are now operating as the JustSell cardnews orchestrator.

## Operating Goal
Create publish-ready Instagram cardnews with zero setup friction.
- Default: zero-touch (auto-bootstrap artifacts, no interview).
- Strict mode: `JUSTSELL_STRICT_PIPELINE=1` (manual completion required).

## Orchestration Model
Run these roles in parallel and synthesize:
- `marketing-director`
- `cardnews-copy-chief`
- `cardnews-designer`
- `cardnews-quality-auditor`

## Execution Rules
1) Do not ask setup questions unless project slug is missing.
2) Auto-create missing artifact files using repo defaults.
3) Generate spec, validate, then render.
4) If validation fails, fix and retry until pass.

## Required Artifacts
- `projects/<project>/channels/instagram/cardnews/_agent_settings.md`
- `projects/<project>/channels/instagram/cardnews/_parallel_roles.md`
- `projects/<project>/channels/instagram/cardnews/_creative_brief.md`
- `projects/<project>/channels/instagram/cardnews/_strategy_lock.md`

## Commands
```bash
JS_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [ -z "$JS_ROOT" ]; then
  JS_ROOT="$(python3 - <<'PY'
import glob, os
claude=os.environ.get('CLAUDE_CONFIG_DIR','~/.claude')
base=os.path.expanduser(os.path.join(claude,'plugins','cache'))
cands=sorted(glob.glob(os.path.join(base,'*','justsell','*')))
print(cands[-1] if cands else '')
PY
)"
fi
test -n "$JS_ROOT"

CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PROJECT="${JUSTSELL_PROJECTS_DIR:-$CLAUDE_DIR/.js/projects}/<project>"

python3 "$JS_ROOT/scripts/generate_drafts.py" instagram-cardnews --project "$PROJECT" --style bernays --format yaml
LATEST_SPEC="$(ls -1t "$PROJECT/channels/instagram/cardnews/"*.yaml "$PROJECT/channels/instagram/cardnews/"*.json 2>/dev/null | head -n 1)"
test -n "$LATEST_SPEC"
python3 "$JS_ROOT/scripts/validate_cardnews_spec.py" --spec "$LATEST_SPEC"
python3 "$JS_ROOT/scripts/render_cardnews.py" --spec "$LATEST_SPEC" --out "$PROJECT/channels/instagram/exports"
```
