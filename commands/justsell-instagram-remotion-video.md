---
description: Activate Instagram remotion video mode
---

[REMOTION MODE ACTIVATED]

$ARGUMENTS

You are operating the JustSell remotion pipeline.

## Operating Goal
Generate and render publish-ready Instagram video assets with real recorded flow input.

## Execution Rules
1) Use local-first project path under `~/.claude/.js/projects/`.
2) Record input flow first (internal UI or product flow), then generate spec.
3) No external publish in this flow.

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
FLOW_STEPS="$PROJECT/channels/instagram/remotion/_flow_steps.json"
FLOW_ARG=()
FLOW_MANIFEST="$PROJECT/channels/instagram/remotion/_flow_manifest.json"

if [ ! -f "$FLOW_STEPS" ]; then
  echo "Missing flow steps: $FLOW_STEPS"
  echo "Copy template: $JS_ROOT/templates/briefs/remotion_flow_steps.example.json"
  exit 1
fi
FLOW_VIDEO="$(python3 "$JS_ROOT/scripts/record_flow.py" --project "$PROJECT" --steps "$FLOW_STEPS" --manifest-out "$FLOW_MANIFEST")"
test -n "$FLOW_VIDEO"
FLOW_ARG=(--flow-video "$FLOW_VIDEO")

python3 "$JS_ROOT/scripts/generate_remotion_spec.py" \
  --project "$PROJECT" \
  --style bernays \
  --video-seconds 22 \
  --video-format square \
  --channel-profile instagram-reel \
  --device-profile mobile \
  --flow-manifest "$FLOW_MANIFEST" \
  "${FLOW_ARG[@]}"

LATEST_SPEC="$(ls -1t "$PROJECT/channels/instagram/remotion/"*.json 2>/dev/null | head -n 1)"
test -n "$LATEST_SPEC"

python3 "$JS_ROOT/scripts/render_remotion_video.py" \
  --spec "$LATEST_SPEC" \
  --out "$PROJECT/channels/instagram/videos"
```
