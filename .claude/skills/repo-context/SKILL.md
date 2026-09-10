---
name: repo-context
description: Load a compact snapshot of the current repository into context — structure, stack, docs, git state.
disable-model-invocation: true
allowed-tools: Bash(git *), Bash(ls *), Bash(head *), Bash(tail *), Bash(wc *), Bash(awk *), Bash(sort *), Bash(uniq *), Bash(echo *), Bash(true), Read, Glob, Grep
---

# Repo context

The snapshot below was collected before this prompt reached you. Treat it as ground truth and do not re-run these commands.

<!-- Every injected command must exit 0: a non-zero exit aborts the whole skill ("Shell command failed for pattern"). -->

## Snapshot

Root: !`git rev-parse --show-toplevel 2>&1 | head -1`

Git status:
```!
git status -sb 2>&1 | head -15
```

Tracked files (total, then per top-level directory):
```!
git ls-files 2>/dev/null | wc -l
git ls-files 2>/dev/null | awk -F/ 'NF>1{print $1}' | sort | uniq -c | sort -rn | head -25
```

File list (first 150):
```!
git ls-files 2>/dev/null | head -150
```

Stack markers present:
```!
ls -1d package.json pyproject.toml go.mod Cargo.toml requirements.txt uv.lock pnpm-lock.yaml Dockerfile docker-compose.yml compose.yaml Makefile .github/workflows 2>/dev/null || true
```

README (first 80 lines):
```!
head -80 README.md 2>/dev/null || echo "(no README.md)"
```

AGENTS.md (first 60 lines):
```!
head -60 AGENTS.md 2>/dev/null || echo "(no AGENTS.md)"
```

Recent activity:
```!
git log --oneline -15 2>&1 | head -15
git diff --stat HEAD~5..HEAD 2>/dev/null | tail -15
```

## Task

1. Use the snapshot for structure, stack and recent activity. CLAUDE.md is already loaded — don't re-read it.
2. Read **at most 5** key files: entry points, core models/schemas, main config. Pick them from the file list; skip lockfiles, generated and vendored code.
3. If the snapshot shows this is not a git repository, fall back to a top-level `ls` and the README.
4. Output the summary below — bullets, no walls of text.

## Output

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
- **Recent Work**: {last 5 commits, one line each}
- **Active Areas**: {most changed files/dirs}

### Key Files
- {path} — {purpose}
```
