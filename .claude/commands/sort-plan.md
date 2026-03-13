---
description: Sort and reorganize a plan file by headers.
---

$ARGUMENTS

Arguments: <file path>

## Algorithm

1. **Validate**: Check file exists. If no argument — ask for path (AskUserQuestion).

2. **Backup**: `cp <file> <file>.bak`

3. **Sort**: Read the file, group content under its nearest header, sort sections alphabetically by header. Preserve every original line exactly as-is — no rewording, no reformatting. Keep frontmatter at the top.

4. **Write sorted version** to original path.

5. **Verify**: Write a temp script that compares `<file>.bak` and `<file>` — extract non-empty lines from both, sort, diff. Every line must be present. Run, show result, delete script. If mismatch — restore from backup, abort.

6. **Rewrite version**: Create `<file>.rewritten.<ext>` — rewrite the sorted plan for clarity (grammar, style, duplicates, section summaries). Keep all original items.

7. **Output**: Report paths of all 3 files and line counts.

Act immediately — no confirmation needed.
