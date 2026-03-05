#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-${CLAUDE_HOME:-$HOME/.claude}}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

SKILLS_DIR="$CLAUDE_HOME/skills"
COMMANDS_DIR="$CLAUDE_HOME/commands"
JS_DIR="$CLAUDE_HOME/.js"
JS_BIN_DIR="$CLAUDE_HOME/.js/bin"

mkdir -p "$SKILLS_DIR" "$COMMANDS_DIR" "$JS_DIR/console" "$JS_BIN_DIR"

# Skills (symlink pack)
if [[ ! -e "$SKILLS_DIR/justsell" ]]; then
  ln -s "$ROOT/skills" "$SKILLS_DIR/justsell"
fi

# Commands (copy; safer than symlink for some environments)
for f in "$ROOT"/commands/*.md; do
  base="$(basename "$f")"
  cp -f "$f" "$COMMANDS_DIR/$base"
done

# Config seed (do not overwrite)
CONFIG_PATH="$JS_DIR/config.json"
if [[ ! -f "$CONFIG_PATH" ]]; then
  cat > "$CONFIG_PATH" <<'JSON'
{
  "version": 1,
  "settings": {
    "public_base_url": "",
    "threads_app_id": "",
    "threads_app_secret": "",
    "meta_app_id": "",
    "meta_app_secret": ""
  },
  "secrets": {},
  "meta": {
    "created_by": "justsell-marketing install.sh"
  }
}
JSON
  chmod 600 "$CONFIG_PATH" || true
fi

# Backfill shared cardnews defaults (do not overwrite existing user values).
export CONFIG_PATH
python3 - <<'PY'
import json, os
from pathlib import Path

cfg_path = Path(os.environ["CONFIG_PATH"]).expanduser()
obj = {}
try:
    if cfg_path.exists():
        obj = json.loads(cfg_path.read_text(encoding="utf-8"))
except Exception:
    obj = {}
if not isinstance(obj, dict):
    obj = {}
obj.setdefault("version", 1)
settings = obj.get("settings", {})
if not isinstance(settings, dict):
    settings = {}

cardnews = settings.get("cardnews", {})
if not isinstance(cardnews, dict):
    cardnews = {}

cardnews.setdefault("template", "channels/instagram/templates/cardnews.claude_code_like.yaml")

theme = cardnews.get("theme", {})
if not isinstance(theme, dict):
    theme = {}
theme.setdefault("accent_primary", "#2563EB")
theme.setdefault("accent_secondary", "#0F172A")
theme.setdefault("cover_fill", "#F3F8FF")
theme.setdefault("panel_fill", "#FFFFFF")
theme.setdefault("bg_kind", "solid")
theme.setdefault("bg_solid", "#FFFFFF")
theme.setdefault("bg_from", "")
theme.setdefault("bg_to", "")
cardnews["theme"] = theme

fonts = cardnews.get("fonts", {})
if not isinstance(fonts, dict):
    fonts = {}
fonts.setdefault("title_name", "Pretendard Bold")
fonts.setdefault("body_name", "Pretendard Regular")
fonts.setdefault("footer_name", "Pretendard Regular")
cardnews["fonts"] = fonts

settings["cardnews"] = cardnews
obj["settings"] = settings
cfg_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

# Optional local CLI shim (does not touch global PATH)
cp -f "$ROOT/bin/js" "$JS_BIN_DIR/js"
chmod +x "$JS_BIN_DIR/js" || true

echo "Installed:"
echo "- Skills:   $SKILLS_DIR/justsell -> $ROOT/skills"
echo "- Commands: $COMMANDS_DIR/justsell-*.md"
echo "- Storage:  $JS_DIR"
echo "- CLI:      $JS_BIN_DIR/js (add to PATH if you want: export PATH=\"$JS_BIN_DIR:$PATH\")"
