---
description: JustSell entrypoint (OMC-style). Usage: /justsell:js init | /justsell:js console | /justsell:js cardnews
---

$ARGUMENTS

You are operating the `justsell` plugin.

Non-negotiable rules:
- Local-first: store all state under `~/.claude/.js/` (respect `CLAUDE_CONFIG_DIR`).
- Explicit publishing: default to dry-run unless the user explicitly confirms.
- No hardcoded URLs: use env vars or `config.json`.
- No emojis.

Interpret `$ARGUMENTS` as a subcommand:

Execution rule:
- When the user asks for `init`, `console`, or `cardnews`, run the bash commands (do not only describe them).

1) `init`
- Goal: wizard-like local setup (OMC-feel) that writes config under `~/.claude/.js/` and then completes OAuth in the console.
- Action:
  0) Resolve the plugin root (never assume the user's current repo contains `scripts/`):
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
  ```

  1) Run init (wizard + dashboard):
  ```bash
  "$JS_ROOT/bin/js" init
  ```
  - Note: Claude Code runs Bash without an interactive TTY, so the terminal wizard is skipped and you should use the `/connect` Setup section.

  2) In the dashboard, open `http://127.0.0.1:5678/connect` and complete OAuth:
  - Threads: click "Connect Threads (OAuth)"
  - Instagram: click "Connect Instagram (OAuth)"
  - Instagram account select: click "Discover accounts" then "Select" one `ig_user_id`
  - Optional: adjust template/colors/fonts in the Setup section if needed later

  3) Projects persist under `~/.claude/.js/projects/` (respects `CLAUDE_CONFIG_DIR` and `JUSTSELL_PROJECTS_DIR`).

2) `console`
- Start JustSellConsole at `http://127.0.0.1:5678/`:
```bash
"$JS_ROOT/bin/js" console
```

3) `cardnews`
- Generate + render Instagram cardnews for a project:
```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PROJECT="$CLAUDE_DIR/.js/projects/<project>"
"$JS_ROOT/bin/js" console
python3 "$JS_ROOT/scripts/generate_drafts.py" instagram-cardnews --project "$PROJECT" --style bernays --format yaml
python3 "$JS_ROOT/scripts/render_cardnews.py" --spec "$PROJECT/channels/instagram/cardnews/<spec>.yaml" --out "$PROJECT/channels/instagram/exports"
```

4) `oauth`
- Go to `http://127.0.0.1:5678/connect` and connect:
  - Threads OAuth
  - Instagram OAuth
  - Discover accounts and select exactly one `ig_user_id`

5) `comeback`
- Generate a comeback draft (Threads) for a project, then review in console before publishing:
  - Start console: `"$JS_ROOT/bin/js" console`
  - Pick any spec of the project, then in Publish panel click "Generate draft" with style `comeback`.

If `$ARGUMENTS` is empty or unknown:
- Ask the user which one: `init`, `console`, or `cardnews` (and which project slug for cardnews).
