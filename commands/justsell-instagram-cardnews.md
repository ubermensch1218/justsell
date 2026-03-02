---
description: Generate Instagram cardnews spec (YAML/JSON) and render PNGs
---

$ARGUMENTS

You generate Instagram cardnews from `projects/<project>/SALES_INFO.md` and render PNG files.

Rules:
- Use Pretendard if available (download via `scripts/fetch_pretendard.sh`).
- Ensure slide number format is consistent (example: `01 / 05`).
- Keep styling consistent with the chosen template. Do not invent random typography.

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

python3 "$JS_ROOT/scripts/generate_drafts.py" instagram-cardnews --project "$PROJECT" --style bernays --format yaml
python3 "$JS_ROOT/scripts/render_cardnews.py" --spec "$PROJECT/channels/instagram/cardnews/<spec>.yaml" --out "$PROJECT/channels/instagram/exports"
```
