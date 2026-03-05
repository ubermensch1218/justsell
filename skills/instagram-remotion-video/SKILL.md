---
name: instagram-remotion-video
description: Production remotion pipeline for Instagram video spec + render
---

# instagram-remotion-video

[REMOTION MODE ACTIVATED]

## Operating Goal
Generate and render publish-ready Instagram video assets with real recorded flow input.

## Input
- `~/.claude/.js/projects/<project>/SALES_INFO.md`

## Output
- Spec: `~/.claude/.js/projects/<project>/channels/instagram/remotion/<yyyymmdd-hhmm>.json`
- Video: `~/.claude/.js/projects/<project>/channels/instagram/videos/<spec-stem>.mp4`

## Commands
```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PROJECT="${JUSTSELL_PROJECTS_DIR:-$CLAUDE_DIR/.js/projects}/<project>"
FLOW_STEPS="$PROJECT/channels/instagram/remotion/_flow_steps.json"
FLOW_MANIFEST="$PROJECT/channels/instagram/remotion/_flow_manifest.json"
FLOW_VIDEO=""
FLOW_ARG=()

if [ ! -f "$FLOW_STEPS" ]; then
  echo "Missing flow steps: $FLOW_STEPS"
  echo "Copy template: templates/briefs/remotion_flow_steps.example.json"
  exit 1
fi
FLOW_VIDEO="$(python3 scripts/record_flow.py --project "$PROJECT" --steps "$FLOW_STEPS" --manifest-out "$FLOW_MANIFEST")"
test -n "$FLOW_VIDEO"
FLOW_ARG=(--flow-video "$FLOW_VIDEO")

python3 scripts/generate_remotion_spec.py \
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

python3 scripts/render_remotion_video.py \
  --spec "$LATEST_SPEC" \
  --out "$PROJECT/channels/instagram/videos"
```
