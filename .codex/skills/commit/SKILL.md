---
name: commit
description: >
  Commit the current changes as Conventional Commits; continues with push-and-pr
  when the user also asks to push or open a PR.
  Triggers: "commit", "/commit", "закоммить", "сделай коммит", "коммит и пуш", "commit and push"
---

Start from `git status` and `git diff --stat`; open individual diffs only where you need them.

- Conventional Commits: `<type>(<scope>)!: <summary>` — English, imperative, ≤72 chars.
- One purpose per commit: split unrelated changes into separate commits.
- Stage paths explicitly. Never `git add -A` or `git add .` — they sweep in untracked junk and secrets.
- Never commit secrets, `.env` files, dumps or build output.
- On the repository's default branch, create a feature branch first (`feat/…`, `fix/…`, `chore/…`) unless the user asked to commit there.

If the request also asks to push or open a PR ("и пуш", "and push", "сделай пр"), continue with the push-and-pr skill.
