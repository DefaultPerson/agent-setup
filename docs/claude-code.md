# Claude Code Setup

## Setup

Paste into Claude Code — or follow the steps manually:

```
Prerequisites: uv (python package manager), ffmpeg or mpv (audio for TTS).

1. git clone https://github.com/DefaultPerson/agent-setup.git && cd agent-setup
2. cp -r .claude/hooks ~/.claude/hooks
3. cp -r .claude/skills ~/.claude/skills
4. cp .claude/settings.example.json ~/.claude/settings.json
   # Windows: hooks and the status line run in Git Bash (install Git for Windows); keep the $HOME paths as they are
5. cp CLAUDE.md ~/.claude/CLAUDE.md (optional — author's coding style and rules)
6. Install recommended plugins (see below)
7. Add shell aliases (see below)
8. Ask me for any preferences
9. Verify everything works
10. Delete agent-setup (repo no longer needed after setup)
```

## Recommended Plugins

LSP (`pyright-lsp`, `gopls-lsp`, `typescript-lsp`) and `frontend-design` are in the default marketplace — install via `/plugin`. An LSP plugin does nothing until its language server is on `PATH`: `pyright-langserver` (`uv tool install pyright`), `gopls` (`go install golang.org/x/tools/gopls@latest`), `typescript-language-server`.

```bash
# Browser automation for AI agents
# https://github.com/vercel-labs/agent-browser
/plugin marketplace add vercel-labs/agent-browser
/plugin install agent-browser@agent-browser

/reload-plugins
```

## Shell Aliases

Add to `.bashrc` / `.zshrc`:

```bash
alias cc="claude" ccr="claude --resume" ccd="claude --dangerously-skip-permissions" ccdr="claude --dangerously-skip-permissions --resume"
```

## TTS Volume

TTS notification volume is controlled independently of system volume via the `VOLUME` constant at **line 25** of `.claude/hooks/notification.py`:

```python
# Volume level: 0 (silent) to 1000 (max). Default 500 = 50%.
VOLUME = 400
```

Range: `0` (silent) to `1000` (max). Default `400` (~40%). Applies to both Windows MCI playback and `ffplay`/`mpv` fallbacks.
