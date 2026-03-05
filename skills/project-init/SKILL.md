---
name: project-init
description: Zero-touch project scaffold creation from template with validation
---

# project-init

[PROJECT INIT MODE ACTIVATED]

## Operating Goal
Create a new project scaffold and verify required files immediately.

## Input
- Project slug (example: `my-product`)

## Output
- `~/.claude/.js/projects/<project-slug>/`
- Required docs validated: `SALES_INFO.md`, `brand.md`, `product.md`, `CONVERSATION_POLICY.md`

## Execution Rules
1) Never overwrite an existing project directory.
2) Copy from `_template` then validate before proceeding.
3) Keep local-first pathing.

## Commands
```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PROJECTS_DIR="${JUSTSELL_PROJECTS_DIR:-$CLAUDE_DIR/.js/projects}"
PROJECT_SLUG="<project-slug>"
TARGET="$PROJECTS_DIR/$PROJECT_SLUG"

mkdir -p "$PROJECTS_DIR"
if [ -e "$TARGET" ]; then
  echo "Project already exists: $TARGET"
  exit 1
fi
cp -R projects/_template "$TARGET"
python3 scripts/validate_project.py "$TARGET"
```
