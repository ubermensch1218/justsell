<INSTRUCTIONS>
# JustSell Plugin (Claude Code)

## Principles
1. Local-first: store all state under `~/.claude/.js/justsell/` (respect `CLAUDE_CONFIG_DIR`).
2. Explicit publishing: network publish actions must default to dry-run unless the user confirms.
3. No hardcoded URLs: use env vars or `config.json`.
4. No emojis in output (docs, UI, prompts).

## Primary entrypoints
- Setup: `justsell-setup`
- Console: `console-start`
- Cardnews: `instagram-cardnews`

</INSTRUCTIONS>
