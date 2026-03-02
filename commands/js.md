---
description: JustSell entrypoint (OMC-style). Usage: /js init | /js console | /js cardnews
---

$ARGUMENTS

You are operating the `justsell` plugin.

Non-negotiable rules:
- Local-first: store all state under `~/.claude/.js/justsell/` (respect `CLAUDE_CONFIG_DIR`).
- Explicit publishing: default to dry-run unless the user explicitly confirms.
- No hardcoded URLs: use env vars or `config.json`.
- No emojis.

Interpret `$ARGUMENTS` as a subcommand:

1) `init`
- Goal: wizard-like local setup (OMC-feel) that writes config under `~/.claude/.js/justsell/` and then completes OAuth in the console.
- Action:
  1) Run the setup wizard (writes `config.json`):
  ```bash
  python3 scripts/justsell_setup.py --wizard
  ```
  - If `config.json` already exists, the wizard asks: update / reset / cancel.
  - Uses `CLAUDE_CONFIG_DIR` (or `~/.claude`) automatically; never hardcode URLs.
  - If the wizard cannot run (no interactive terminal), start the console and use `/connect` Setup form instead.
  2) Start the console:
  ```bash
  python3 scripts/justsell_console.py
  ```
  3) Open `http://127.0.0.1:5678/connect` and complete OAuth:
  - Threads: click "Connect Threads (OAuth)"
  - Instagram: click "Connect Instagram (OAuth)"
  - Instagram account select: click "Discover accounts" then "Select" one `ig_user_id`
  - Optional: adjust template/colors/fonts in the Setup section if needed later

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

4) `oauth`
- Go to `http://127.0.0.1:5678/connect` and connect:
  - Threads OAuth
  - Instagram OAuth
  - Discover accounts and select exactly one `ig_user_id`

5) `comeback`
- Generate a comeback draft (Threads) for a project, then review in console before publishing:
  - Start console: `python3 scripts/justsell_console.py`
  - Pick any spec of the project, then in Publish panel click "Generate draft" with style `comeback`.

If `$ARGUMENTS` is empty or unknown:
- Ask the user which one: `init`, `console`, or `cardnews` (and which project slug for cardnews).
