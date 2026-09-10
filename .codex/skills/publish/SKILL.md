---
name: publish
description: >
  Publish the repository to GitHub or update its GitHub setup — topics, license, Pages,
  Dependabot, CI, .gitignore, README scaffold. Use only when the user explicitly asks.
  Triggers: "publish", "/publish", "publish repo", "опубликуй репо"
---

Create the GitHub repository for this directory, or bring an existing one up to date, with `gh`. Start from `git remote get-url origin` and `gh repo view`.

Before changing anything, ask up front, showing current values for an existing repository: owner (personal account or one of `gh api user/orgs`), visibility, description (suggest one from the README), license, GitHub Pages (MkDocs Material), Dependabot, CI workflow, `.gitignore`, README scaffold.

Then apply only what was chosen:
- Take the repository name from the directory and topics from the detected stack and the README.
- Match CI, Dependabot ecosystems and `.gitignore` templates (`gh api gitignore/templates/<Name>`) to the stack actually in the repository. Scan untracked files for anything that should be ignored and confirm before adding it.
- Never overwrite a non-empty README; merge into an existing `.gitignore` only after asking.
- Commit and push what you generate.

Finish with the repository URL and a list of what changed.
