---
description: JustSell entrypoint (OMC-style). Usage: /js init | /js console | /js cardnews
---

$ARGUMENTS

You are operating the `justsell` plugin.

Non-negotiable rules:
- Local-first: store all state under `~/.claude/.omc/justsell/` (respect `CLAUDE_CONFIG_DIR`).
- Explicit publishing: default to dry-run unless the user explicitly confirms.
- No hardcoded URLs: use env vars or `config.json`.
- No emojis.

Interpret `$ARGUMENTS` as a subcommand:

1) `init`
- Goal: configure defaults (template, key colors, fonts) and OAuth app IDs/secrets.
- Action:
  - Start the console and guide the user to `http://127.0.0.1:5678/connect`.
  - Use the Setup form to save:
    - Cardnews template + key colors + fonts
    - Threads/Meta OAuth app settings
    - (optional) `public_base_url` for Instagram publishing
  - Then perform OAuth connects:
    - Threads: click "Connect Threads (OAuth)"
    - Instagram: click "Connect Instagram (OAuth)"
    - Instagram account select: click "Discover accounts" then "Select" one `ig_user_id`.

2) `console`
- Start JustSellConsole at `http://127.0.0.1:5678/`:
```bash
python3 scripts/justsell_console.py
```

3) `cardnews`
- Generate + render Instagram cardnews for a project:
```bash
python3 scripts/generate_drafts.py instagram-cardnews --project projects/<project> --style bernays --format yaml
python3 scripts/render_cardnews.py --spec projects/<project>/channels/instagram/cardnews/<spec>.yaml --out projects/<project>/channels/instagram/exports
```

If `$ARGUMENTS` is empty or unknown:
- Ask the user which one: `init`, `console`, or `cardnews` (and which project slug for cardnews).

