# Claude Code Setup

Universal setup for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — security hooks, notifications, status line, and productivity commands.

## Features

- **Security Guard** — blocks dangerous commands (`rm -rf /`, credential reads, privileged docker, etc.)
- **TTS Notifications** — cached voice alerts when Claude finishes or needs input
- **Desktop Notifications** — native OS notifications (Linux, macOS, Windows)
- **Status Line** — project, branch, model, context usage, rate limits
- **Slash Commands** — `/research`, `/ultrathink`, `/commit`, `/push-and-pr`, `/prime`, `/publish`, `/release`
- **Cross-platform** — Linux, macOS, Windows

## Setup

Paste into Claude Code — or follow the steps manually:

```
Prerequisites: Node.js 18+, uv (python package manager), ffmpeg or mpv (audio for TTS).

1. git clone https://github.com/DefaultPerson/claude-code-setup.git && cd claude-code-setup
2. cp -r .claude/hooks ~/.claude/hooks
3. cp -r .claude/commands ~/.claude/commands
4. cp .claude/settings.example.json ~/.claude/settings.json
   # Windows: cp .claude/settings.local.json.windows "$env:USERPROFILE/.claude/settings.json"
5. cp CLAUDE.md ~/.claude/CLAUDE.md (optional — author's coding style and rules)
6. Install recommended plugins from the README
7. Add shell aliases from the README to user's shell profile
8. Ask me for any preferences
9. Verify everything works
10. cd .. && rm -rf claude-code-setup (repo no longer needed after setup)
```

## Recommended Plugins

```bash
# Documentation lookup
claude /install-plugin context7@claude-plugins-official

# LSP for code analysis (requires language servers installed)
claude /install-plugin typescript-lsp@claude-plugins-official
claude /install-plugin pyright-lsp@claude-plugins-official
claude /install-plugin gopls-lsp@claude-plugins-official

# Context optimization — keeps raw tool output out of context window
# https://github.com/mksglu/context-mode
claude /install-plugin context-mode

# Browser automation for AI agents
# https://github.com/vercel-labs/agent-browser
claude /install-skill agent-browser@vercel-labs/agent-browser
```

## Shell Aliases

Add to `.bashrc` / `.zshrc`:

```bash
alias cc="claude" ccr="claude --resume" ccd="claude --dangerously-skip-permissions" ccdr="claude --dangerously-skip-permissions --resume"

# Tmux: tg (4 panes), tg -n 3, tg2 (side-by-side), ta (add pane)
tg() { local n=4; while getopts "n:" o; do case $o in n) n=$OPTARG;; esac; done; tmux new-session -d -s "g-$$"; for ((i=1;i<n;i++)); do tmux split-window -t "g-$$"; tmux select-layout -t "g-$$" tiled; done; tmux attach -t "g-$$"; }
tg2() { tmux new-session -d -s "s-$$"; tmux split-window -h -t "s-$$"; tmux attach -t "s-$$"; }
ta() { tmux split-window; tmux select-layout tiled; }
alias tg3='tg -n 3'
```

## Tips

> [!TIP]
> **Terminal as Editor Tab (VS Code)**: `Cmd/Ctrl+Shift+P` → "Terminal: Create New Terminal in Editor Area" — opens terminal as a tab next to your code, not in the bottom panel.

> [!TIP]
> **If something doesn't work — just ask Claude Code to fix it.** Describe the problem and Claude will diagnose and resolve it.

> [!TIP]
> **Create SKILLs for repetitive tasks.** Instead of doing any task manually, create a SKILL for it. First version gives junior-mid level results. Then iterate until it matches your quality — 100-1000x time savings.
