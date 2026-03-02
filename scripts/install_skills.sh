#!/usr/bin/env bash
set -euo pipefail

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"

SKILLS_DIR="${JUSTSELL_SKILLS_DIR:-}"
if [[ -z "$SKILLS_DIR" ]]; then
  if [[ -d "$CLAUDE_HOME/skills" ]]; then
    SKILLS_DIR="$CLAUDE_HOME/skills"
  else
    SKILLS_DIR="$CODEX_HOME/skills"
  fi
fi

TARGET="$SKILLS_DIR/justsell"

mkdir -p "$SKILLS_DIR"

if [[ -e "$TARGET" ]]; then
  echo "Already exists: $TARGET"
  echo "Remove it first if you want to reinstall."
  exit 1
fi

ln -s "$(pwd)/skills" "$TARGET"
echo "Installed skill pack symlink:"
echo "  $TARGET -> $(pwd)/skills"
