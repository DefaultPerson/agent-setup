# Codex CLI Setup

## Setup

Paste into Codex — or follow the steps manually:

```
Prerequisites: Node.js 18+, uv (python package manager), ffmpeg or mpv (audio for TTS).

1. git clone https://github.com/DefaultPerson/agent-setup.git && cd agent-setup
2. cp -r .codex/hooks ~/.codex/hooks
3. cp .codex/hooks.json ~/.codex/hooks.json
4. cp -r .codex/skills ~/.codex/skills
5. cp .codex/config.toml.sample ~/.codex/config.toml
6. cp AGENTS.md ~/.codex/AGENTS.md (optional — author's coding style and rules)
7. Edit ~/.codex/config.toml — set API keys, model preferences; add MCP servers with `codex mcp add`
8. Add shell aliases (see below)
9. Open `/hooks` in Codex and trust the PreToolUse + Stop hooks — again after any edit to hooks.json: trust is pinned to each hook's command, matcher and timeout, and a changed hook is skipped until re-trusted
10. Verify everything works (`codex doctor`)
11. Delete agent-setup (repo no longer needed after setup)
```

Update with `codex update`. If an npm update fails with `ENOTEMPTY`, or Codex then fails with `Missing optional dependency @openai/codex-<platform>`, delete `$(npm prefix -g)/lib/node_modules/@openai/{codex,.codex-*}` and reinstall with `npm i -g @openai/codex@latest`.

**Key differences from Claude Code:**
- Config: `config.toml` (TOML) instead of `settings.json`
- Instructions: `AGENTS.md` instead of `CLAUDE.md`
- Status line: built-in `/statusline` picker, theme-aware colors via `tui.status_line_use_colors`, and `tui.status_line` items — no Claude-style custom script hook yet
- Plugins: installed via interactive UI, not CLI command
- MCP: configured in `config.toml` `[mcp_servers]` section or via `codex mcp add`

## Recommended Plugins

- [agent-browser](https://github.com/vercel-labs/agent-browser) — browser automation for AI agents
- [frontend-design](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/frontend-design) — production-grade frontend generation

## Shell Aliases

Add to `.bashrc` / `.zshrc`:

```bash
alias cx="codex" cxr="codex resume" cxd="codex --yolo" cxdr="codex resume --yolo"
```
