---
description: Publish repository to GitHub with full setup.
---

Interactive repo publication workflow. Uses `gh` CLI for everything.

## Algorithm

1. **Detect state**: `git remote -v` — check if `origin` points to GitHub.
   - **New repo** (no origin): full creation flow (steps 2-13).
   - **Existing repo** (origin exists): update flow — go to step 2 to review/update settings.
   - **No git repo**: `git init` first.

2. **Ask questions** (AskUserQuestion, single batch — all repos):
   - **Owner**: personal account or organization? List available with `gh api user/orgs --jq '.[].login'` + personal account from `gh api user --jq .login`.
   - **Visibility**: public / private / Keep current (existing repos only)
   - **Description**: show auto-detected (from README.md or CLAUDE.md), ask to use or enter custom
   - **License**: MIT (Recommended for public) / Apache-2.0 / GPL-3.0 / Keep current / None
   - **GitHub Pages**: Yes (MkDocs Material) / No / Keep current
   - **Dependabot**: Enable dependency updates? Yes / No / Keep current
   - **CI workflow**: Set up GitHub Actions CI? Yes (auto-detect stack) / No / Keep current
   - **`.gitignore`**: Generate smart .gitignore? Yes (auto-detect stack + scan repo) / No / Keep current
   - **README.md**: Scaffold README if missing? Yes / No

3. **Auto-detect** (no user input needed):
   - **Repo name**: from current directory name
   - **Topics**: detect from stack files:
     - `package.json` → nodejs, javascript/typescript
     - `pyproject.toml` / `requirements.txt` → python
     - `go.mod` → golang
     - `Cargo.toml` → rust
     - `Dockerfile` → docker
     - Also infer from README content (keywords, frameworks)
   - For existing repos: fetch current values with `gh repo view --json description,repositoryTopics,visibility` and show diff

4. **Create or update repo**:
   - New: `gh repo create <owner>/<name> --public|--private --description "<desc>" --source . --push`
   - Existing: `gh repo edit --description "<desc>" --visibility public|private` (only if changed)

5. **Set topics**:
   ```bash
   gh repo edit --add-topic <tag1> --add-topic <tag2> ...
   ```

6. **License** (if selected/changed):
   - Fetch license text: `gh api licenses/<spdx-id> --jq .body > LICENSE`
   - Replace `[year]` and `[fullname]` placeholders
   - Commit and push

7. **GitHub Pages** (if selected/changed):
   - Create `mkdocs.yml` with Material theme, `docs/index.md` from README
   - Add GitHub Actions workflow `.github/workflows/docs.yml` for auto-deploy
   - Commit and push

8. **Dependabot** (if selected):
   - Create `.github/dependabot.yml` with update schedules based on detected ecosystem:
     - `npm` for package.json projects
     - `pip` for Python projects
     - `gomod` for Go projects
     - `cargo` for Rust projects
     - `github-actions` always included
   - Weekly schedule, auto-rebase, max 10 open PRs
   - Commit and push

9. **CI workflow** (if selected):
   - Create `.github/workflows/ci.yml` based on detected stack:
     - Node.js: install deps, lint, test, build
     - Python: install deps (uv/pip), lint (ruff), test (pytest)
     - Go: build, test, vet
     - Rust: check, test, clippy
   - Trigger on push to main and PRs
   - Use latest stable language versions
   - Commit and push

10. **`.gitignore`** (if selected):
    - **A) Stack-based templates** — reuse stack detection from step 3, fetch from GitHub API:
      - `package.json` → `Node`
      - `pyproject.toml` / `requirements.txt` / `setup.py` → `Python`
      - `go.mod` → `Go`
      - `Cargo.toml` → `Rust`
      - `composer.json` → `Composer`
      - `Gemfile` → `Ruby`
      - `*.sln` / `*.csproj` → `VisualStudio`
      - `build.gradle` / `pom.xml` → `Gradle` / `Maven`
      ```bash
      gh api gitignore/templates/Node --jq .source
      gh api gitignore/templates/Python --jq .source
      ```
    - **B) Common block** (always prepend — not available via API):
      ```gitignore
      # OS & Editor
      .DS_Store
      Thumbs.db
      *.swp
      *.swo
      *~
      .idea/
      .vscode/
      *.sublime-project
      *.sublime-workspace

      # Environment
      .env
      .env.*
      !.env.example

      # Build artifacts
      dist/
      build/
      out/
      ```
    - **C) Repo scan** — analyze actual repo contents for things that should be ignored:
      - Run `git ls-files --others --directory` to find untracked files/dirs
      - Check tracked files with `git ls-files` for items that shouldn't be in VCS
      - Look for: `node_modules/`, `__pycache__/`, `.venv/`, `venv/`, `.tox/`, `*.egg-info/`, `target/` (Rust), `vendor/` (Go), `.terraform/`, `*.sqlite3`, `coverage/`, `.nyc_output/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.next/`, `.nuxt/`, `.output/`, secrets (`*.key`, `*.pem`, `credentials.*`), heavy binaries, DB dumps
      - Show user what was found and confirm before adding
    - **D) Merge logic**:
      - No `.gitignore` exists → create from A + B + C
      - `.gitignore` exists → AskUserQuestion: Overwrite / Merge (append only new patterns) / Skip
    - Commit and push

11. **README.md** (if selected and missing or empty):
    - Generate from project metadata:
      ```markdown
      # {repo-name}

      {description from step 2}

      ## Installation

      {based on detected stack:}
      - Node.js: `npm install`
      - Python: `pip install -e .` / `uv pip install -e .`
      - Go: `go install ./...`
      - Rust: `cargo build`
      - Generic: manual instructions placeholder

      ## Usage

      <!-- TODO: Add usage examples -->

      ## License

      {license name, linked to LICENSE file}
      ```
    - If README.md exists and is non-empty: skip (never overwrite)
    - Commit and push

12. **Polish** (automatic):
    - If repo is public: suggest setting a social preview image

13. **Output**:
    ```
    Repo: https://github.com/<owner>/<name>
    Visibility: public/private
    Topics: tag1, tag2, tag3
    License: MIT
    Pages: enabled at https://<owner>.github.io/<name>
    Dependabot: enabled (npm, pip, github-actions)
    CI: enabled (.github/workflows/ci.yml)
    .gitignore: created (Node + Python + 3 patterns from repo scan)
    README: scaffolded / already exists
    Changes: [list of what was created/updated]
    ```
