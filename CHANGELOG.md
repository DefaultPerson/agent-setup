# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- **statusline.py** — session cost segment (`$N.NN`, muted gold, tail of line 2) from Claude Code's `cost.total_cost_usd` (API-equivalent estimate: token usage incl. cache × model list price). Guarded by `if cost_usd:` — hidden when absent/zero, so it no-ops on subscriptions that don't surface it.
- **CLAUDE.md** — `## Models` guidance: when running as Fable 5, default Workflow/subagent `model` to Opus — Fable agents are often redundant; keep Fable for the driving loop and delegate real work to Opus.
- **guard.py** — `test_guard.py` regression corpus (82 cases) built from real false positives harvested from session transcripts; run with `uv run --no-project .claude/hooks/test_guard.py`.
- **guard.py** — `ask` verdict tier via PreToolUse `permissionDecision` JSON: risky-but-legitimate commands (`git reset --hard`, `git push -f`, `git clean -f`, `curl | sh`, `rm -rf` of a top-level `$HOME` dir, `docker system prune -a`) now prompt for approval instead of hard-blocking (mapped to deny under Codex where no prompt exists).
- **guard.py** — `Read` tool protection wired in `settings.example.json` (private keys denied; `.ssh/config`, `known_hosts`, `*.pub` allowed) and `ask` on Edit/Write into `~/.ssh/`, deployed hook/settings files, `/etc/`.
- **statusline.py** — `effort` segment (e.g. `high`/`xhigh`); reads `effort.level` from status line JSON (Claude Code ≥ v2.1.119). Relevant since Opus 4.8 defaults to `high` and exposes `/effort xhigh`.
- **config.toml.sample** — documented Codex `tui.status_line` built-in items and `/hooks` trust workflow.
- **config.toml.sample** — enabled Codex theme-aware status line colors and added PR/branch/context progress items.
- **notification.py** — re-introduced `DESKTOP_NOTIFICATIONS` env toggle (default `1`); set to `0|false|no|off` to suppress notify-send/osascript/Toast while keeping audio.
- **settings.example.json / config.toml.sample** — `DESKTOP_NOTIFICATIONS=1` documented in env/shell_environment_policy.
- **.claude/skills/{commit,push-and-pr}/SKILL.md** — natural-language triggers (ru+en) for Claude Code; `commit` auto-chains to `push-and-pr` when user mentions push.
- **README.md** — Tip on disabling desktop notifications.
- **AGENTS.md** — added `NEVER add Co-Authored-By` rules for parity with CLAUDE.md.

### Changed

- **guard.py** — detection core rewritten from raw-substring regex to structure-aware shell analysis (heredoc stripping, quote-aware segment splitting, shlex tokenization, wrapper skipping for `sudo`/`env`/`timeout`/`xargs`, `bash -c`/`eval` recursion). Replay of 227 historical blocks: 219 were false positives (string literals, commit messages, grep patterns, `curl | python3 -c` JSON parsing, `/home` paths in unrelated parts of compound commands) — now 219 allow / 7 ask / 1 deny.
- **guard.py** — logging switched from rewrite-the-whole-JSON-array (`pre_tool_use.json`) to append-only `pre_tool_use.jsonl` with 5 MB rotation; input truncated to 500 chars.
- **.claude/skills/{commit,push-and-pr}/SKILL.md** — added `disallowed-tools: [Edit, Write, MultiEdit, NotebookEdit]` (Claude Code ≥ v2.1.152) so git skills can never mutate files; `allowed-tools: [Bash]` stays for auto-approved git/gh commands (the two fields are complementary — auto-approve vs remove-from-pool).
- **notification.py** — added short desktop notification and audio playback timeouts so Stop hooks cannot hang on `notify-send`/`ffplay`.
- **README.md** — Codex setup now includes `/hooks` review/trust step; status line note clarifies current Codex built-in-only customization.
- **README.md** — Slash Commands bullet renamed to "Skills + Slash Commands"; install step copies `.claude/skills` alongside commands.
- **.codex/skills/commit/SKILL.md** — added chain-to-push step; same triggers as Claude Code skill.
- **CLAUDE.md / AGENTS.md** — point cleanups: dropped outdated Opus 4.5/Sonnet 4 line, removed three duplicated bullets (`Structured answers; minimal output`, `Parallelize independent work`, `No sycophantic openers`).

### Removed

- **.claude/commands/research.md** — superseded by Claude Code's native bundled `/deep-research` skill (multi-agent harness with adversarial fact-checking; ≥ v2.1.158). Codex keeps `.codex/skills/research/` — Codex has no native deep-research equivalent.
- **.claude/commands/commit.md, push-and-pr.md** — replaced by skills with same names; `/commit` and `/push-and-pr` still work via skill slash invocation.

## 2026-04-06

### Changed

- **Repo renamed** — `claude-code-setup` → `agent-setup` (platform-neutral naming)
- **README.md** — restructured into separate Claude Code and Codex CLI sections (Setup, Plugins, Aliases each)
- **README.md** — Codex plugins: replaced incorrect `codex plugin install` with links to plugins
- **README.md** — Codex aliases: fixed `--full-auto` (was `--approval-policy full-auto`), `codex resume --last` (was `codex exec resume --last`)
- **README.md** — removed tmux aliases (tg/tg2/tg3/ta)
- **README.md** — Tips section moved to end

## 2026-04-05

### Added

- **guard.py** — credential read protection: blocks reading `.ssh/*`, `.aws/credentials`, `*.pem`, `*.key`, `credentials.json`, `token.json`
- **notification.py** — Windows audio via `winmm.mciSendString` (MP3 without ffplay/mpv)
- **notification.py** — macOS click-to-focus: notification click activates terminal (iTerm2, Alacritty, kitty, WezTerm, Hyper)
- **notification.py** — 6 new completion phrases (Laura voice, ElevenLabs v3)
- **ultrathink.md** — Reasoning, Execution, Output sections with parallel agents instruction
- **commit.md, push-and-pr.md, publish.md, release.md** — inline `!` backtick context (pre-loads git status/branch/diff) + `allowed-tools` restriction
- **settings.example.json** — `attribution` config (empty = no Co-Authored-By)
- **README.md** — Recommended Plugins section, SKILL tip, LLM Quick Start prompt

### Changed

- **research.md** — `Task` tool → `Agent` tool with `run_in_background: true`
- **CLAUDE.md** — `Task agent (Explore)` → `Agent (subagent_type: Explore)` in tooling section
- **settings.example.json** — paths use `$HOME` instead of hardcoded placeholders (no `sed` needed)
- **settings.local.json.windows** — paths use `%USERPROFILE%` instead of relative
- **notification.py** — simplified: removed Russian messages, language selection, `DESKTOP_NOTIFICATIONS` env var
- **statusline.py** — uses new API fields (`context_window.used_percentage`, `rate_limits`, `session_name`) instead of transcript parsing
- **README.md** — restructured: removed ToC, Shell Aliases, Global Installation dupe, tg channel link; simplified Manual Setup

### Removed

- **guard.py** — `.env` write protection (was blocking legitimate workflows)
- **notification.py** — Russian messages, `TTS_LANGUAGE` env var, `DESKTOP_NOTIFICATIONS` env var
- **settings.example.json** — `CONTEXT7_API_KEY`, `TTS_LANGUAGE`, `DESKTOP_NOTIFICATIONS` env vars
- **.mcp.json.sample**, **.mcp.json.windows** — replaced by context7 plugin installation
- **CLAUDE.md** — removed `NEVER ADD Co-Authored-By` rules (replaced by `attribution` setting)

## 2026-03-11

### Fixed

- **guard.py** — fail-open → fail-close: broken input or exceptions now block instead of allowing
- **guard.py** — `.env` write protection for Edit/Write/MultiEdit was dead code (matcher only matched Bash)
- **settings.json** — added `Edit|Write|MultiEdit` matcher to PreToolUse hooks

### Added

- **guard.py** — git/gh destructive remote protection: `git push --force`, `git reset --hard`, `git clean -f`, `gh repo delete`, `gh release delete` (allows `--force-with-lease`)
- **`/commit`** — self-contained Conventional Commit command with inlined git rules
- **`/push-and-pr`** — push and PR workflow with main-branch detection (skips PR on main)
- **`/prime`** — general-purpose project context loader (structure, docs, stack, git activity)
- **`/publish`** — interactive repo publication to GitHub (description, topics, license, gh-pages)
- **`/release`** — create GitHub release with auto-generated changelog

### Changed

- **`/commit`** — acts immediately without confirmation
- **`/push-and-pr`** — acts immediately, asks to merge and delete branch after checks pass
- **notification.py** — simplified to cached-only mode: removed OpenAI/ElevenLabs/pyttsx3 dependencies, removed dynamic TTS generation, keeps cached MP3 playback and desktop notifications
- **settings.example.json** — added `Edit|Write|MultiEdit` guard matcher, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `TTS_LANGUAGE`, `DESKTOP_NOTIFICATIONS` env vars; removed stale PreCompact hook and `enabledMcpjsonServers`
- **settings.local.json.windows** — added `Edit|Write|MultiEdit` guard matcher, env vars; removed stale PreCompact hook and `enabledMcpjsonServers`
- **`/publish`** — added owner/visibility for existing repos, Dependabot, CI workflow, description override questions
- **README.md** — removed `.env` setup step (no longer needed)
- **README.md** — updated TTS notifications description (cached-only); removed stale Pre-Compact Hook and chrome-devtools references, updated slash commands list, added `.env` optional note
- **statusline.py** — new layout: `dir >> branch >> model >> [context bar] ~Xk left`, colored progress bar from transcript parsing, model in Claude orange, branch in magenta, removed session ID and percentage
- **research.md** — removed year binding from confidence ratings, removed Russian keywords and examples
- **CLAUDE.md** — replaced Russian example with English

### Removed

- **`/validation`** — removed validation command suite (example-validate, ultimate_validate_command)
- **utils/tts/** — removed ElevenLabs, OpenAI, and pyttsx3 TTS scripts (replaced by cached MP3 playback)
- **.env.example** — removed (all env vars now in settings.json)

## 2026-02-06

### Added

- **agent-browser skill** — replaced Chrome DevTools MCP with built-in agent-browser skill in tooling docs
- **Self-verification** — added post-change verification and edge-case checks to `<self_reflection>`

### Changed

- **CLAUDE.md** — added rule to prevent Co-Authored-By in commits
- **CLAUDE.md** — merged `coding-standards.md` and `tooling.md` inline (guaranteed context loading)
- **CLAUDE.md** — replaced Chrome DevTools MCP with agent-browser skill in tooling section
- **README.md** — moved from `docs/` to repository root
- **statusline.py** — replaced JSONL transcript parsing with native `context_window.used_percentage` API field (v2.1.6+)

### Removed

- **PreCompact hook** — removed from project settings (backup HTML generation)
- **pre_compact.py** — deleted hook script
- **Chrome DevTools MCP** — removed from tooling documentation (replaced by agent-browser)
- **enabledMcpjsonServers** — removed redundant empty array from project settings
- **docs/** — folder removed; content consolidated into CLAUDE.md and root README

## 2025-12-30

### Added

- **HTML Session Viewer** — `pre_compact.py` now generates standalone HTML with markdown rendering, syntax highlighting, and copy buttons per message
- **Theme Toggle** — session viewer supports dark/light theme switching with localStorage persistence (dark default)
- **Notification Stacking Prevention** — desktop notifications replace each other instead of accumulating:
  - Linux: `x-canonical-private-synchronous` and `x-dunst-stack-tag` hints
  - macOS: `terminal-notifier` with `-group` (if installed)
  - Windows: Toast `Tag` and `Group` properties
- **LSP Plugins Section** — README now documents TypeScript, Python (Pyright), Go (gopls) plugins

### Changed

- **CLAUDE.md** — optimized from 128 to 61 lines, merged `dev_guidelines` and `cursor_prefs`, removed redundant sections
- **README.md** — streamlined features list, updated Pre-Compact Hook description
- **.mcp.json.windows** — fixed context7 config to use `env` instead of `--api-key` arg
- **.claude/settings.local.json.windows** — added missing PreCompact and statusLine hooks
- **.env.example** — added `DESKTOP_NOTIFICATIONS` variable

### Removed

- **Persistent Memory** — removed `.claude/memory.md` and related CLAUDE.md section
- **Agents** — removed `sandbox.md` and `worktree-dev.md` (use built-in Task tool instead)
- **`/load-context`** — removed slash command

### Fixed

- **.claude/settings.example.json** — typo `youre` → `your`
- **pre_compact.py** — user messages rendered character-by-character when `content` was string instead of array

## 2025-12-29

### Added

- **Desktop Notifications** — cross-platform native notifications (Linux `notify-send`, macOS `osascript`, Windows PowerShell Toast)
- **`DESKTOP_NOTIFICATIONS`** — env variable to enable/disable (default: true)
- **`DEBUG_STATUSLINE`** — env variable to dump statusline input to `/tmp/claude-statusline-debug.json`
- **`tg2`** — tmux alias for 2 horizontal panes (side-by-side)
- **`tg3`** — tmux alias for 3 panes

### Changed

- **statusline.py** — context display changed from `~X%` to `X%+` format
- **notification.py** — integrated desktop notifications with TTS
- **Agents** — added required `description` field to frontmatter (sandbox, worktree-dev)
- **README.md** — updated tmux aliases section with tg2/tg3

### Removed

- **`/load-context`** — removed slash command (use memory.md directly)

## 2025-12-27

### Added

- **Sandbox Agent** — isolated development in separate git worktree for safe experimentation
- **Worktree-Dev Agent** — parallel feature development with automatic worktree management
- **`/load-context`** — slash command to load project context and memory on session start
- **`/validation`** — validation commands suite:
  - `/validation:example-validate` — comprehensive codebase validation
  - `/validation:ultimate_validate_command` — generate validation command for any project
- **`pre_compact.py`** — hook that auto-backups conversation transcript before compaction
- **`settings.example.json`** — template with placeholder paths for easy setup
- **`memory.md`** — persistent memory file that survives between sessions
- **Tips section in README** — VS Code terminal-as-tab tip
- **New TTS phrases** — "All done!", "Job complete!", "Task finished!", "Work complete!"

### Changed

- **README.md** — simplified structure, removed verbose install commands, listed all features
- **CLAUDE.md** — added memory management rules, context economy guidelines, orchestration patterns
- **`/research`** — improved with structured output to `research/` directory
- **notification.py** — refactored, cleaner code structure
- **statusline.py** — minor improvements
- **elevenlabs_tts.py** — better error handling
- **docs/tooling.md** — updated tooling reference
- **.env.example** — updated variables documentation
- **.gitignore** — added new exclusions for backups and cache
- **.mcp.json.sample / .mcp.json.windows** — simplified MCP server configs
- **TTS cache** — regenerated audio files with improved quality

### Removed

- **`speckit.validate.md`** — replaced by `/validation` commands
- **`.claude/settings.json`** — moved to template (`settings.example.json`)
- **Verbose README sections** — installation commands, file structure, hooks reference, env variables table

## 2025-12-26

### Added

- **Security Guard** (`guard.py`) — blocks dangerous bash commands (`rm -rf /`, `.env` writes, privileged docker)
- **TTS Notifications** (`notification.py`) — voice alerts via ElevenLabs, OpenAI, or pyttsx3
- **Status Line** (`statusline.py`) — shows project, branch, model, context usage
- **MCP Servers** — context7, chrome-devtools, memory, sequential-thinking
- **Windows support** — `.mcp.json.windows`, cross-platform guard hook
- **Shell aliases** — `cc`, `ccr`, `ccd`, `tg`, `ta`
- **CLAUDE.md** — project instructions for Claude Code
