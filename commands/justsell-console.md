---
description: Start JustSellConsole (localhost 5678) for connect/preview/render/publish
---

$ARGUMENTS

You are operating JustSellConsole (local-first marketing console).

Rules:
- Keep data local under `~/.claude/.js/`.
- OAuth and publish must be explicit. Default to dry-run unless user says to confirm.
- Do not hardcode URLs. Use env vars or `~/.claude/.js/config.json`.

Steps:
0) Resolve the plugin root (never assume the user's current repo contains `scripts/`):
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
```

1) Start the console:
```bash
"$JS_ROOT/bin/js" console
```

2) Open:
- `http://127.0.0.1:5678/`

3) If the user wants OAuth, guide them to:
- `http://127.0.0.1:5678/connect`

4) If the user wants a public base URL for Instagram carousel publishing, set:
- `JUSTSELL_PUBLIC_BASE_URL` (must be reachable by Meta Graph API)
