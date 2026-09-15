# agent-setup

Universal setup for [Claude Code](https://code.claude.com/docs) and [OpenAI Codex CLI](https://developers.openai.com/codex/cli) — security hooks, notifications, status line, and skills.

## Features

- **Security Guard** — denies destructive and credential-leaking commands (`rm -rf ~`, `git push --force`, private key reads, archiving `~/.ssh`) with a reason instead of a prompt, so unattended runs don't stall; also catches a `pkill -f` that would kill the agent's own shell, and `systemctl stop|restart` of units listed in `GUARD_PROTECTED_UNITS`
- **TTS Notifications** — cached voice alerts when Claude finishes or needs input
- **Desktop Notifications** — native OS notifications (Linux, macOS, Windows)
- **Status Line** — project, branch, model, effort, rate limits with time to reset, context tokens, session cost
- **Skills** — `commit` («сделай коммит и пуш» chains into a PR), `push-and-pr`, `/publish`, `/repo-context`; for research use Claude Code's built-in `/deep-research`
- **Cross-platform** — Linux, macOS, Windows

---

## Setup

- [Claude Code setup](docs/claude-code.md)
- [Codex CLI setup](docs/codex.md)

---

## Recommendations

> [!TIP]
> **Disable desktop notifications** — set `DESKTOP_NOTIFICATIONS=0` in `~/.claude/settings.json` (`env` section); for Codex, export it in the shell that starts Codex (hooks get Codex's own environment, not `[shell_environment_policy]`). Audio TTS keeps working.

> [!TIP]
> **Remote monitoring and control** — use `herdr` with [herdrgram](https://github.com/DefaultPerson/herdrgram) to bridge your terminal multiplexer to Telegram, so you can watch and steer your AI coding agents from your phone while keeping full terminal access.

## License

MIT
