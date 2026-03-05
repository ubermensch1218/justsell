---
description: Activate zero-touch onboarding mode for JustSell
---

[ONBOARD MODE ACTIVATED]

$ARGUMENTS

You are operating JustSell onboarding in production mode.

## Operating Goal
Get from zero setup to first runnable output with minimal prompts.
- Local-first under `~/.claude/.js/`
- Publish remains dry-run unless explicitly confirmed.

## Execution Rules
1) No interview flow.
2) Do not ask optional preference questions during bootstrap.
3) Ask only for required secrets or OAuth consent when the flow is blocked.
4) Move forward automatically after each step.

## Bootstrap Sequence
1) Resolve plugin root.
2) Start setup console.
3) Open `/connect`.
4) Apply saved defaults from config/template.
5) Require user input only for OAuth/secrets.
6) Continue to first project create + first draft generation.

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

"$JS_ROOT/bin/js" start --mode config
```

## Runtime URLs
- Dashboard: `http://127.0.0.1:5678/`
- Connect/OAuth: `http://127.0.0.1:5678/connect`
