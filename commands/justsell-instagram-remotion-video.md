---
description: Generate Remotion promo video spec (JSON) and render MP4
---

$ARGUMENTS

You generate a Remotion promo video from `projects/<project>/SALES_INFO.md`.

Rules:
- Keep outputs local under `~/.claude/.js/`.
- Use channel profile + safe area + device font profile.
- Do not publish anything to external platforms in this flow.

Commands (example):
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

python3 "$JS_ROOT/scripts/generate_remotion_spec.py" \
  --project "$PROJECT" \
  --style bernays \
  --video-seconds 22 \
  --video-format auto \
  --channel-profile instagram-reel \
  --device-profile mobile

python3 "$JS_ROOT/scripts/render_remotion_video.py" \
  --spec "$PROJECT/channels/instagram/remotion/<spec>.json" \
  --out "$PROJECT/channels/instagram/videos"
```
