---
allowed-tools: Bash(git *), Bash(find *), Bash(head *), Read, Glob, Grep
description: Load project context and output a structured summary.
---

Build comprehensive understanding of the codebase. Run all steps, then output a concise summary.

## Process

### 1. Project Structure

```bash
git ls-files | head -100
```

Show directory tree (depth 3, skip noise):
```bash
find . -maxdepth 3 -type f \
  -not -path '*/node_modules/*' \
  -not -path '*/.git/*' \
  -not -path '*/dist/*' \
  -not -path '*/build/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/.next/*' \
  | head -80
```

### 2. Core Documentation

Read whatever exists — skip what's missing:
- `README.md`, `CLAUDE.md`
- `docs/` directory (if present — scan for architecture, API, specs)
- Any other top-level docs (PRD, spec, CONTRIBUTING, ARCHITECTURE, etc.)

### 3. Stack Detection

Look for common config files to detect the stack:
- `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `requirements.txt`
- Build/lint configs (`tsconfig.json`, `ruff.toml`, `.eslintrc*`, etc.)
- Infra files (`Dockerfile`, `docker-compose.yml`, `.github/workflows/`)

### 4. Key Files

From the file tree, identify and read entry points, core schemas/models, and important service files.

### 5. Git Activity

```bash
git log --oneline -20
git branch -a
git diff --stat HEAD~5..HEAD 2>/dev/null
```

## Output Summary

```markdown
## Project Context

### Overview
- **Purpose**: {what this project does}
- **Tech Stack**: {languages, frameworks, key deps}

### Architecture
- **Structure**: {key directories, patterns}
- **Entry Points**: {main files}
- **Config**: {build tools, CI/CD, infra}

### Current State
- **Branch**: {current branch}
- **Recent Work**: {last 5 commits summary}
- **Active Areas**: {most changed files/dirs}

### Key Files
- {path} — {purpose}
- ...
```

Make the summary easy to scan — bullet points, clear headers, no walls of text.
