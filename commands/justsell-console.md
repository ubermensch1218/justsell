---
description: Activate JustSell console mode
---

[CONSOLE MODE ACTIVATED]

$ARGUMENTS

You are operating the JustSell local console runtime.

## Operating Goal
Bring up the console fast, with no extra questions.
- Local-first storage: `~/.claude/.js/`
- Publish remains dry-run unless explicitly confirmed.

## Execution Rules
1) Resolve plugin root.
2) Start console server.
3) Open dashboard URL.
4) Only explain OAuth/public URL if the user asks.

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

"$JS_ROOT/bin/js" start --mode console
```

## Runtime URLs
- Dashboard: `http://127.0.0.1:5678/`
- Connect/OAuth: `http://127.0.0.1:5678/connect`
