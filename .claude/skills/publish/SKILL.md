---
name: publish
description: Publish the current repository to GitHub, or review and update its GitHub setup.
disable-model-invocation: true
allowed-tools: Bash(git *), Bash(gh *), Bash(mkdir *), Bash(echo *)
---

## State

- Origin: !`git remote get-url origin 2>/dev/null || echo "no origin"`
- Branch: !`git branch --show-current 2>/dev/null || echo "not a git repository"`
- GitHub: !`gh repo view --json nameWithOwner,visibility,description --jq '"\(.nameWithOwner) (\(.visibility)) — \(.description)"' 2>/dev/null || echo "not on GitHub yet"`

## Goal

Create the GitHub repository for this directory, or bring an existing one up to date, with `gh`.

Before changing anything, ask up front — in as few AskUserQuestion calls as possible, showing current values for an existing repository: owner (personal account or one of `gh api user/orgs`), visibility, description (suggest one from the README), license, GitHub Pages (MkDocs Material), Dependabot, CI workflow, `.gitignore`, README scaffold.

Then apply only what was chosen:
- Take the repository name from the directory and topics from the detected stack and the README.
- Match CI, Dependabot ecosystems and `.gitignore` templates (`gh api gitignore/templates/<Name>`) to the stack actually in the repository. Scan untracked files for anything that should be ignored and confirm before adding it.
- Never overwrite a non-empty README; merge into an existing `.gitignore` only after asking.
- Commit and push what you generate.

Finish with the repository URL and a list of what changed.
