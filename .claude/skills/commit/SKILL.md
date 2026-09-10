---
name: commit
description: >
  Commit the current changes as Conventional Commits; continues with push-and-pr
  when the user also asks to push or open a PR.
  Triggers: "commit", "/commit", "закоммить", "сделай коммит", "коммит и пуш", "commit and push"
allowed-tools: [Bash]
disallowed-tools: [Edit, Write, MultiEdit, NotebookEdit]
---

## State

!`git status -sb 2>&1 | head -40`
!`git diff --stat HEAD 2>/dev/null | tail -25`
!`git log --oneline -8 2>/dev/null | cat`

Requested header (may be empty): $ARGUMENTS

## Conventions

- Conventional Commits: `<type>(<scope>)!: <summary>` — English, imperative, ≤72 chars.
- One purpose per commit: split unrelated changes into separate commits.
- Stage paths explicitly. Never `git add -A` or `git add .` — they sweep in untracked junk and secrets.
- Never commit secrets, `.env` files, dumps or build output.
- On the repository's default branch, create a feature branch first (`feat/…`, `fix/…`, `chore/…`) unless the user asked to commit there.

If the request also asks to push or open a PR ("и пуш", "and push", "сделай пр"), continue with the push-and-pr skill.
