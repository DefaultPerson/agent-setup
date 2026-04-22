# agent-setup

Universal setup for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and [OpenAI Codex CLI](https://developers.openai.com/codex/cli) — security hooks, notifications, status line, and productivity commands.

## Features

- **Security Guard** — blocks dangerous commands (`rm -rf /`, credential reads, privileged docker, etc.)
- **TTS Notifications** — cached voice alerts when Claude finishes or needs input
- **Desktop Notifications** — native OS notifications (Linux, macOS, Windows)
- **Status Line** — project, branch, model, context usage, rate limits
- **Slash Commands** — `/research`, `/ultrathink`, `/commit`, `/push-and-pr`, `/prime`, `/publish`, `/release`
- **Cross-platform** — Linux, macOS, Windows

---

## Claude Code

### Setup

Paste into Claude Code — or follow the steps manually:

```
Prerequisites: Node.js 18+, uv (python package manager), ffmpeg or mpv (audio for TTS).

1. git clone https://github.com/DefaultPerson/agent-setup.git && cd agent-setup
2. cp -r .claude/hooks ~/.claude/hooks
3. cp -r .claude/commands ~/.claude/commands
4. cp .claude/settings.example.json ~/.claude/settings.json
   # Windows: cp .claude/settings.local.json.windows "$env:USERPROFILE/.claude/settings.json"
5. cp CLAUDE.md ~/.claude/CLAUDE.md (optional — author's coding style and rules)
6. Install recommended plugins (see below)
7. Add shell aliases (see below)
8. Ask me for any preferences
9. Verify everything works
10. Delete agent-setup (repo no longer needed after setup)
```

### Recommended Plugins

LSP, context7, frontend-design are available in the default marketplace — install via `/plugin` → search.

```bash
# Browser automation for AI agents
# https://github.com/vercel-labs/agent-browser
/plugin marketplace add vercel-labs/agent-browser
/plugin install agent-browser@agent-browser

/reload-plugins
```

### Shell Aliases

Add to `.bashrc` / `.zshrc`:

```bash
alias cc="claude" ccr="claude --resume" ccd="claude --dangerously-skip-permissions" ccdr="claude --dangerously-skip-permissions --resume"
```

### TTS Volume

TTS notification volume is controlled independently of system volume via the `VOLUME` constant at **line 25** of `.claude/hooks/notification.py`:

```python
# Volume level: 0 (silent) to 1000 (max). Default 500 = 50%.
VOLUME = 400
```

Range: `0` (silent) to `1000` (max). Default `400` (~40%). Applies to both Windows MCI playback and `ffplay`/`mpv` fallbacks.

---

## Codex CLI

### Setup

Paste into Codex — or follow the steps manually:

```
Prerequisites: Node.js 18+, uv (python package manager), ffmpeg or mpv (audio for TTS).

1. git clone https://github.com/DefaultPerson/agent-setup.git && cd agent-setup
2. cp -r .codex/hooks ~/.codex/hooks
3. cp .codex/hooks.json ~/.codex/hooks.json
4. cp .codex/config.toml.sample ~/.codex/config.toml
5. cp AGENTS.md ~/.codex/AGENTS.md (optional — author's coding style and rules)
6. Edit ~/.codex/config.toml — set API keys, model preferences
7. Add MCP servers (see below)
8. Add shell aliases (see below)
9. Verify everything works
10. Delete agent-setup (repo no longer needed after setup)
```

**Key differences from Claude Code:**
- Config: `config.toml` (TOML) instead of `settings.json`
- Instructions: `AGENTS.md` instead of `CLAUDE.md`
- Status line: built-in `/statusline` picker — no custom script needed
- Plugins: installed via interactive UI, not CLI command
- MCP: configured in `config.toml` `[mcp_servers]` section or via `codex mcp add`

### Recommended Plugins

- [agent-browser](https://github.com/vercel-labs/agent-browser) — browser automation for AI agents
- [context7](https://github.com/upstash/context7) — library documentation lookup
- [frontend-design](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/frontend-design) — production-grade frontend generation

### Shell Aliases

Add to `.bashrc` / `.zshrc`:

```bash
alias cx="codex" cxr="codex resume" cxd="codex --yolo" cxdr="codex resume --yolo"
```

---

## Tips

> [!TIP]
> **Terminal as Editor Tab (VS Code)**: `Cmd/Ctrl+Shift+P` → "Terminal: Create New Terminal in Editor Area" — opens terminal as a tab next to your code, not in the bottom panel.

> [!TIP]
> **If something doesn't work — just ask Claude Code/Codex to fix it.** Describe the problem and it will diagnose and resolve it.

> [!TIP]
> **Create SKILLs for repetitive tasks.** Instead of doing any task manually, create a SKILL for it. First version gives junior-mid level results. Then iterate until it matches your quality — 100-1000x time savings.

## License

MIT
