---
name: push-and-pr
description: >
  Push the current branch, open or update its pull request, and merge it when asked.
  Triggers: "push-and-pr", "/push-and-pr", "push and pr", "create pr", "сделай пр", "запушь"
allowed-tools: [Bash]
disallowed-tools: [Edit, Write, MultiEdit, NotebookEdit]
---

## State

!`git status -sb 2>&1 | head -20`

$ARGUMENTS

## Conventions

- Use `gh`. The base is the repository's default branch (`gh repo view --json defaultBranchRef`), never an assumed `main`.
- Rebase onto the base before pushing to keep history linear. Force-push only your own feature branch, and only with `--force-with-lease`.
- If the branch already has a PR, push to it instead of opening another one.
- PR title in Conventional Commit format, ≤72 chars; body sections: What, Why, How to test, Risks.
- Wait for checks only when the repository has them, and fix failures before merging.
- Merge only when the user asked for it: rebase-merge, delete the branch locally and on the remote, then update the local default branch with `git pull --rebase` — rebase-merge rewrites commit SHAs.
- On the default branch there is nothing to open a PR from: push directly only if the user asked to.
