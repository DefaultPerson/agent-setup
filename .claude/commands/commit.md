---
allowed-tools: Bash(git *), Bash(gh *)
description: Create a Conventional Commit safely.
---

## Context

- Status: !`git status`
- Diff: !`git diff HEAD`
- Branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`

$ARGUMENTS

Arguments: [optional commit header]

## Git Rules

- **Conventional Commits**: `<type>[scope][!]: <short summary>`
- **Types**: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`, `build`, `ci`, `revert`
- English only, title ≤72 characters
- One commit — one purpose. Split different concerns into separate commits.
- **Never commit secrets**: tokens, keys, `.env`, database dumps, PII
- **Prefer feature branches** (`feat/<name>`, `fix/<name>`, `chore/<name>`) over committing to `main`

## Algorithm

1. **Guard**: `git status` — if clean, stop ("Nothing to commit"). If branch is `main` — ask user (AskUserQuestion): "You're on main. Commit directly or create a feature branch?" If user says branch — help create one and switch.
2. **Header**:
   - If argument provided — use it (validate format).
   - Otherwise — inspect changes, generate a Conventional Commit header.
   - Validate: matches `<type>[scope][!]: <summary>`, ≤72 chars, English.
3. **Stage & Commit**: `git add -A` → `git commit -m "<header>"` (add body/footer if multi-concern change warrants it).
4. **Output**: `Committed "<header>"` → suggest next: `/push-and-pr`.

Act immediately — no confirmation needed.
