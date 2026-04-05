---
allowed-tools: Bash(git *), Bash(gh *)
description: Create a GitHub release with auto-generated changelog.
---

## Context

- Branch: !`git branch --show-current`
- Last tag: !`git describe --tags --abbrev=0 2>/dev/null || echo "No tags"`
- Commits since tag: !`git log $(git describe --tags --abbrev=0 2>/dev/null || echo HEAD~20)..HEAD --oneline 2>/dev/null | head -20`
- CHANGELOG exists: !`test -f CHANGELOG.md && echo "Yes" || echo "No"`

$ARGUMENTS

Arguments: [optional version override]

## Algorithm

1. **Get release context**:
   ```bash
   LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
   ```
   - Show: last tag + date, commit count since, diff stats
   - If no tags — use full commit history (capped at 50)

2. **Detect versioning scheme**:
   - Semver (`v1.2.3` or `1.2.3`) → suggest bump (patch/minor/major based on commit types: feat→minor, fix→patch, `!`→major)
   - Calver (`2026.08.1`) → suggest next calver
   - No tags → ask user for preferred scheme
   - If `$ARGUMENTS` provided — use as version directly

3. **Ask questions** (AskUserQuestion):
   - **Version**: confirm suggested or enter custom
   - **Release notes style**: Technical (full changelog) / User-facing (features+fixes) / Both

4. **Generate release notes** from commits since last tag:

   Group by Conventional Commit type:

   | Type | Section | User-visible |
   |------|---------|-------------|
   | feat | Added | Yes |
   | fix | Fixed | Yes |
   | perf | Performance | Yes |
   | refactor | Changed | No |
   | docs | Documentation | No |
   | ci, test, chore, build | Internal | No |

   - **Technical**: all sections, commit messages as-is
   - **User-facing**: only Added + Fixed + Performance, rewrite as human-readable descriptions

5. **Update CHANGELOG.md** (if file exists):
   - Replace `[Unreleased]` header content with new version + date
   - Add fresh empty `[Unreleased]` section above
   - If no `[Unreleased]` section — prepend new version block after top header

6. **Create tag & release**:
   ```bash
   # Commit changelog if changed
   git add CHANGELOG.md && git commit -m "docs: release <version>"
   git push origin HEAD

   # Tag and release
   git tag -a <version> -m "Release <version>"
   git push origin <version>
   gh release create <version> --title "<version>" --notes-file /tmp/release-notes.md
   ```
   - If user wants to attach files — ask which files, then `gh release upload <version> <files...>`

7. **Output**:
   ```
   Release: <url>
   Tag: <version>
   Commits: <count> since <last-tag>
   CHANGELOG: updated / not found
   ```
