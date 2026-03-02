English | [한국어](README.ko.md) | [日本語](README.ja.md)

# justsell

Local-first marketing automation plugin for Claude Code.

Threads + Instagram cardnews + Reddit draft + Remotion video workflows, with local preview and explicit publish confirmation.

[Quick Start](#quick-start) | [Command Reference](#command-reference) | [Configuration](docs/CONFIG.md) | [Workflow](docs/WORKFLOW.md) | [Console Docs](apps/justsell_console/README.md)

---

## Quick Start

Step 1: Install
```bash
/plugin marketplace add https://github.com/ubermensch1218/justsell
/plugin install justsell
```

Step 2: Initialize setup
```bash
/justsell:js init
```

Step 3: Open console
```bash
/justsell:js console
```

Optional guided onboarding:
```bash
/justsell:onboard
```

---

## Why JustSell

- Local-first by default: state is stored under `~/.claude/.js/` (respects `CLAUDE_CONFIG_DIR`)
- Explicit publishing: network publish actions stay dry-run unless confirmed
- Per-project source-of-truth: content flows from `SALES_INFO.md` and channel policies
- Built-in rendering loops: generate drafts, render assets, review in console, then publish if approved

---

## Core Workflows

| Workflow | Entry Point | Result |
|----------|-------------|--------|
| Setup | `justsell-setup` / `/justsell:js init` | Writes local config and opens OAuth/setup flow |
| Console | `console-start` / `/justsell:js console` | Starts local dashboard at `http://127.0.0.1:5678/` |
| Cardnews | `instagram-cardnews` / `/justsell:js cardnews` | Generates cardnews spec and renders PNG files |
| Reddit draft | `skills/reddit-compose` or `python3 scripts/generate_reddit_drafts.py --project ...` | Generates subreddit-fit draft text with tone tripod |
| Remotion | `/justsell:js remotion` | Generates Remotion spec and renders MP4 video |
| Guided onboarding | `/justsell:onboard` | One-step-at-a-time onboarding for first run |

---

## Command Reference

| Command | Description |
|---------|-------------|
| `/justsell:js init` | Initialize local settings and open setup mode |
| `/justsell:js console` | Start JustSellConsole |
| `/justsell:js cardnews` | Generate and render Instagram cardnews |
| `/justsell:js remotion` | Generate and render Instagram Remotion video |
| `/justsell:onboard` | Interactive onboarding flow |

---

## Configuration

Default storage:
- Config/tokens: `~/.claude/.js/config.json`
- Console logs/events: `~/.claude/.js/console/`
- Projects: `~/.claude/.js/projects/`

Key docs:
- [Config schema](docs/CONFIG.md)
- [Workflow guide](docs/WORKFLOW.md)
- [Cardnews automation](docs/CARDNEWS_AUTOMATION.md)
- [Channel rules](docs/CHANNELS.md)

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_CONFIG_DIR` | `~/.claude` | Base Claude configuration directory |
| `CLAUDE_PLUGIN_ROOT` | auto-detected | Plugin root path for command wrappers |
| `JUSTSELL_HOME` | `$CLAUDE_CONFIG_DIR/.js` | JustSell state directory |
| `JUSTSELL_CONFIG_PATH` | `$JUSTSELL_HOME/config.json` | Config file override |
| `JUSTSELL_PROJECTS_DIR` | `$JUSTSELL_HOME/projects` | Project directory override |
| `JUSTSELL_CONSOLE_HOST` | `127.0.0.1` | Console bind host |
| `JUSTSELL_CONSOLE_PORT` | `5678` | Console bind port |
| `JUSTSELL_PUBLIC_BASE_URL` | unset | Public URL used for Instagram publish assets |
| `JUSTSELL_FONT_PATH` | unset | Fallback font for cardnews rendering |
| `JUSTSELL_THREADS_APP_ID` | unset | Threads OAuth app ID |
| `JUSTSELL_THREADS_APP_SECRET` | unset | Threads OAuth app secret |
| `JUSTSELL_THREADS_REDIRECT_URI` | `http://127.0.0.1:5678/oauth/threads/callback` | Threads OAuth callback |
| `JUSTSELL_META_APP_ID` | unset | Meta app ID for Instagram Graph API |
| `JUSTSELL_META_APP_SECRET` | unset | Meta app secret |
| `JUSTSELL_IG_REDIRECT_URI` | `http://127.0.0.1:5678/oauth/ig/callback` | Instagram OAuth callback |
| `JUSTSELL_GRAPH_API_VERSION` | `v20.0` | Graph API version |

---

## Troubleshooting

| Issue | Action |
|-------|--------|
| Console does not start | Run `/justsell:js console` and verify port `5678` is available |
| OAuth callback mismatch | Register exact callback URLs in app settings |
| Instagram publish requires public URL | Set `JUSTSELL_PUBLIC_BASE_URL` or `settings.public_base_url` |
| Font rendering looks wrong | Set `JUSTSELL_FONT_PATH` or `font.path` in spec |
| Plugin root cannot be resolved | Re-run `/justsell:js init` |

---

## License

MIT
