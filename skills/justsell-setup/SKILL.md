---
name: justsell-setup
description: Activate one-pass setup for JustSell local config
---

# justsell-setup

[SETUP MODE ACTIVATED]

## Operating Goal
Complete setup in one pass and persist defaults for every run.
- Config path: `~/.claude/.js/config.json`
- If `CLAUDE_CONFIG_DIR` is set, use that root.

## Execution Rules
1) Prefer non-disruptive updates (preserve existing user values).
2) Ask only when required keys/secrets are missing.
3) Keep publish behavior dry-run by default.

## Commands
```bash
python3 scripts/justsell_setup.py --wizard
```

## Next Run
```bash
python3 scripts/justsell_console.py
```
Open `http://127.0.0.1:5678/connect` for OAuth/account connect.
