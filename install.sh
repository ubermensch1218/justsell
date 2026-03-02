#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-${CLAUDE_HOME:-$HOME/.claude}}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

SKILLS_DIR="$CLAUDE_HOME/skills"
COMMANDS_DIR="$CLAUDE_HOME/commands"
JS_DIR="$CLAUDE_HOME/.js/justsell"
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

# Optional local CLI shim (does not touch global PATH)
cp -f "$ROOT/bin/js" "$JS_BIN_DIR/js"
chmod +x "$JS_BIN_DIR/js" || true

echo "Installed:"
echo "- Skills:   $SKILLS_DIR/justsell -> $ROOT/skills"
echo "- Commands: $COMMANDS_DIR/justsell-*.md"
echo "- Storage:  $JS_DIR"
echo "- CLI:      $JS_BIN_DIR/js (add to PATH if you want: export PATH=\"$JS_BIN_DIR:$PATH\")"
