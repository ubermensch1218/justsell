---
name: console-start
description: Activate JustSell console runtime (localhost 5678)
---

# console-start

[CONSOLE MODE ACTIVATED]

## Operating Goal
Start local console fast, with zero setup friction.
- Local-first storage under `~/.claude/.js/`
- Publish remains dry-run unless explicitly confirmed.

## Inputs
- Optional project slug/path.

## Outputs
- Dashboard: `http://127.0.0.1:5678/`
- Connect: `http://127.0.0.1:5678/connect`
- State: `~/.claude/.js/config.json`, `~/.claude/.js/console/`

## Commands
```bash
python3 scripts/justsell_console.py
```
