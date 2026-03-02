#!/usr/bin/env bash
set -euo pipefail

CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-${CLAUDE_HOME:-$HOME/.claude}}"

rm -f "$CLAUDE_HOME/commands/justsell-console.md" || true
rm -f "$CLAUDE_HOME/commands/justsell-instagram-cardnews.md" || true

if [[ -L "$CLAUDE_HOME/skills/justsell" ]]; then
  rm "$CLAUDE_HOME/skills/justsell"
fi

echo "Uninstalled command files and skill-pack symlink."
echo "Kept local state under: $CLAUDE_HOME/.omc/justsell (delete manually if needed)."
