# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- **guard.py** — `pkill -f` / `pgrep -f` self-match rule: a full-match pattern (`-f`, `--full`, `-ef`, `-9f`, also after `sudo`/`timeout`, inside `bash -c`, `$(…)`, backticks, pipes and `ssh host '…'`) that matches the command line it is part of is denied, because the Bash tool's own `bash -c "<command>"` shell is in that pattern's way and dies with it (exit 144); `pgrep` is denied only when its output feeds a `kill`, and `[p]attern` or anchored patterns stay allowed.
- **guard.py** — `GUARD_PROTECTED_UNITS` (comma/whitespace separated unit names, with or without `.service`): `systemctl stop|restart|disable|kill|mask|try-restart|reload-or-restart` on a listed unit is denied, while `status`, `start`, `show`, `cat`, `list-units` and `daemon-reload` stay allowed.
- **.claude/skills/repo-context** — compact repository snapshot collected with `!` injections before the model runs; replaces `/prime`.
- **statusline.py** — time left until each rate-limit window resets, dim, after the percentages: `1%/76% (4h/48h)`; minutes under an hour (`40m`). Reads `rate_limits.*.resets_at`.
- **settings.example.json** — `statusLine.refreshInterval: 60`, so the reset countdown keeps ticking while the session is idle (otherwise the status line re-runs only on events).
- **statusline.py** — session cost segment (`$N.NN`, muted gold, tail of line 2) from Claude Code's `cost.total_cost_usd` (API-equivalent estimate: token usage incl. cache × model list price). Guarded by `if cost_usd:` — hidden when absent/zero, so it no-ops on subscriptions that don't surface it.
- **CLAUDE.md** — `## Models` guidance: when running as Fable 5, default Workflow/subagent `model` to Opus — Fable agents are often redundant; keep Fable for the driving loop and delegate real work to Opus.
- **guard.py** — `Read` tool protection wired in `settings.example.json` (private keys denied; `.ssh/config`, `known_hosts`, `*.pub` allowed).
- **statusline.py** — `effort` segment (e.g. `high`/`xhigh`); reads `effort.level` from status line JSON (Claude Code ≥ v2.1.119). Relevant since Opus 4.8 defaults to `high` and exposes `/effort xhigh`.
- **config.toml.sample** — documented Codex `tui.status_line` built-in items and `/hooks` trust workflow.
- **config.toml.sample** — enabled Codex theme-aware status line colors and added PR/branch/context progress items.
- **notification.py** — re-introduced `DESKTOP_NOTIFICATIONS` env toggle (default `1`); set to `0|false|no|off` to suppress notify-send/osascript/Toast while keeping audio.
- **settings.example.json** — `DESKTOP_NOTIFICATIONS=1` documented in `env`.
- **.claude/skills/{commit,push-and-pr}/SKILL.md** — natural-language triggers (ru+en) for Claude Code; `commit` auto-chains to `push-and-pr` when user mentions push.
- **README.md** — Tip on disabling desktop notifications.
- **AGENTS.md** — added `NEVER add Co-Authored-By` rules for parity with CLAUDE.md.

### Changed

- **CLAUDE.md / AGENTS.md** — rewritten from 134 lines of XML-wrapped principles into 25 rules in four sections (Replies, Work, Irreversible steps, Models and scale) plus three aliases, each rule tied to a failure class found in a session audit (done-claims without a real check, dropped request items, `pkill -f` killing its own shell, deletions beyond authorization, live-infra changes without a rollback, parallel sessions in one checkout, over-sized agent fan-outs) or to an author convention; style matched to the Claude Code 2.1.270 system prompt (no em-dashes, one or two sentences per bullet) so the file's formatting doesn't leak into replies. Machine-specific rules live in `~/.claude/rules/*.md`, not in this file.
- **guard.py** — every deny reason handed to the model now ends with “Use the alternative named here or report the block; don't reach the same effect through another command form.”, appended once in `main()` (the JSONL log keeps the bare reason).
- **skills** — `commit`, `push-and-pr`, `publish` (Claude Code + Codex) rewritten from step-by-step procedures into intent + constraints: the PR base is the repository's default branch instead of an assumed `main`, files are staged explicitly (no `git add -A`), the full diff is no longer injected into context. `publish` is a Claude Code skill with `disable-model-invocation`.
- **settings.example.json** — one guard entry for `Bash|Edit|Write|MultiEdit|NotebookEdit|Read|Grep` with `timeout: 10` (was three entries without a timeout; `Grep` and `NotebookEdit` never reached the guard), timeouts on notification hooks, `permissions.defaultMode: "auto"`. The same file works on Windows: hooks run in Git Bash, where `$HOME` expands.
- **.codex/hooks/guard.py** — synced with `.claude/hooks/guard.py` (closed bypasses, no `ask`, fail-open); the June copy blocked every call on malformed input. `.codex/hooks.json` gets timeouts.
- **config.toml.sample** — for Codex 0.154: `model = "gpt-5.6-terra"` (`gpt-5.4` is gone from the model catalog); dropped `codex_hooks` (deprecated alias of `hooks`) and `multi_agent`, both on by default, and the no-op `notify` entry (`notification.py` does nothing without flags; completion alerts come from the Stop hook). The Context7 server used `headers`, which Codex does not read — replaced by a commented `env_http_headers` example. `DESKTOP_NOTIFICATIONS` is no longer set through `[shell_environment_policy]`: Codex runs hooks with its own process environment, so the toggle never reached `notification.py`.
- **CLAUDE.md** — Context7 section removed.
- **README.md** — setup copies skills only and uses one settings file on every OS; LSP plugins need their language servers on `PATH`; skills tip rewritten; Codex: setup copies skills, hooks must be re-trusted after any `hooks.json` edit, `codex update` and recovery from a broken npm update; the desktop-notification tip exports the variable instead.
- **guard.py** — no `ask` verdicts any more: every rule is `deny` with an actionable reason or `allow` + log. A hook `ask` in a `bypassPermissions` session can still prompt and stall an unattended run (observed: 46 h). Former asks → deny: `git push --force` (hint `--force-with-lease`), `--mirror`, deleting `main`/`master`, `git reset --hard` / `git clean -f` only when there is something to lose, `rm -r` of `.`/`..`/protected `$HOME` dirs; → allow: `push --delete` of feature branches, `docker system prune -a`, `gh release delete`, `curl | sh`, local cp/mv of key material.
- **guard.py** — closed bypasses: `$(…)` inside double quotes, heredoc or stdin piped into a shell, `find -delete` / `-exec rm`, `python -c` / `node -e` deletions, path traversal (`/tmp/../home`), Bash writes (`sed -i`, `tee`, `cp`, `mv`, `ln`, redirects) to the deployed guard or `authorized_keys`, worktree-wide `git checkout/restore .`, `git stash clear`, `push :ref`, combined `-fu`, archiving/uploading `~/.ssh`, `Grep` into secret paths. `.pem`/`.crt` count as secrets only when they contain `PRIVATE KEY`; the fork-bomb check no longer fires on quoted text.
- **guard.py** — fail-open: invalid stdin or an internal error now exits 0 (was exit 2, which blocked every tool call); `evaluate()` receives the hook's `cwd`.
- **test_guard.py** — regression corpus of 132 real false positives and bypasses (`uv run --no-project .claude/hooks/test_guard.py`); no case may expect `ask`. Replay of 16,033 logged calls: 0 ask, 2 new deny (both intended), the public-CA false deny fixed.
- **statusline.py** — context segment shows tokens in context instead of percentage (`[#------] 172k`, from `context_window.total_input_tokens`); bar color still follows `used_percentage`.
- **guard.py** — detection core rewritten from raw-substring regex to structure-aware shell analysis (heredoc stripping, quote-aware segment splitting, shlex tokenization, wrapper skipping for `sudo`/`env`/`timeout`/`xargs`, `bash -c`/`eval` recursion). Replay of 227 historical blocks: 219 were false positives (string literals, commit messages, grep patterns, `curl | python3 -c` JSON parsing, `/home` paths in unrelated parts of compound commands) — now allowed.
- **guard.py** — logging switched from rewrite-the-whole-JSON-array (`pre_tool_use.json`) to append-only `pre_tool_use.jsonl` with 5 MB rotation; input truncated to 500 chars.
- **.claude/skills/{commit,push-and-pr}/SKILL.md** — added `disallowed-tools: [Edit, Write, MultiEdit, NotebookEdit]` (Claude Code ≥ v2.1.152) so git skills can never mutate files; `allowed-tools: [Bash]` stays for auto-approved git/gh commands (the two fields are complementary — auto-approve vs remove-from-pool).
- **notification.py** — added short desktop notification and audio playback timeouts so Stop hooks cannot hang on `notify-send`/`ffplay`.
- **README.md** — Codex setup now includes `/hooks` review/trust step; status line note clarifies current Codex built-in-only customization.
- **.codex/skills/commit/SKILL.md** — added chain-to-push step; same triggers as Claude Code skill.
- **CLAUDE.md / AGENTS.md** — point cleanups: dropped outdated Opus 4.5/Sonnet 4 line, removed three duplicated bullets (`Structured answers; minimal output`, `Parallelize independent work`, `No sycophantic openers`).

### Removed

- **CLAUDE.md / AGENTS.md** — `<self_reflection>` rubric (causes over-verification on Opus 5), `<answering_rules>` (expert role, TL;DR and the literal `<example>` block leaked into replies), `<coding_principles>` (43 lines the model applies without being told), the tables rule, the knowledge-cutoff rule, the Context7/`ultrathink` tooling notes and the tool list.
- **.claude/commands/** — `ultrathink` (the keyword works natively), `prime` (replaced by `repo-context`), `release` (never used); `publish` moved to skills. Same for `.codex/skills/{ultrathink,prime,release}`; `.codex/skills/research` is no longer needed.
- **settings.local.json.windows** — hooks on Windows run in Git Bash or PowerShell, and neither expands `%USERPROFILE%`: every guard call pointed at a missing file, exited 2 and blocked the tool.
- **settings.example.json** — `enableAllProjectMcpServers` (auto-approved MCP servers from any cloned repository) and `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`.
- **.claude/commands/research.md** — superseded by Claude Code's native bundled `/deep-research` skill (multi-agent harness with adversarial fact-checking; ≥ v2.1.158).
- **.claude/commands/commit.md, push-and-pr.md** — replaced by skills with same names; `/commit` and `/push-and-pr` still work via skill slash invocation.

### Fixed

- **statusline.py** — rate-limit segment disappeared entirely when the 5-hour window was absent (Claude Code drops a window once it resets, e.g. while idle); a missing window now renders as `-` (`-/76% (-/48h)`).
- **guard.py** — path rules on Windows. `HOME` (`C:\Users\x`) was passed to `re.sub` as a replacement template, so every path check raised `bad escape \U` and the hook failed open: `rm -rf /`, reading `~/.ssh` keys and unhooking guard.py from settings were all allowed. Past that crash, `os.path.normpath` produced backslash paths the POSIX rules never matched, so every `rm -r` (even `./build`) was denied as a top-level directory, while `C:\…` tool paths skipped the `~/.ssh` directory and settings checks. Paths are now normalized to one lowercase form before any check (`C:\x`, `C:/x` and Git Bash `/c/x` all become `/c/x`), `$USERPROFILE` expands like `$HOME`, and on Windows `rm -r` of a drive root, `Windows`, `Program Files`, `ProgramData` or another profile under `Users` is denied and `~/AppData` is protected. POSIX behavior is unchanged. `test_guard.py` pins a `/home/def` POSIX host so the corpus gives the same verdicts on any machine, and adds 28 simulated Windows cases.

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
