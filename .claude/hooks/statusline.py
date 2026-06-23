#!/usr/bin/env python3
"""Claude Code status line: dir >> branch >> model >> context% >> rate limits"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Force UTF-8 stdout so the accent rail (▌), arrow separator (›) and ⚠ marker
# don't crash print() on consoles whose default encoding isn't UTF-8
# (e.g. Windows cp1251); errors='replace' as a last-resort safety net.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Traffic-light colors — Claude-branded (warm earth)
GREEN = "\033[38;2;110;176;90m"    # leaf  #6eb05a
YELLOW = "\033[38;2;224;164;88m"   # amber #e0a458
RED = "\033[38;2;192;57;43m"       # brick #c0392b

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(s: str) -> int:
    """Length of string ignoring ANSI color codes (for width-aware layout)."""
    return len(ANSI_RE.sub("", s))


def get_branch(project_dir: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", project_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=1
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def format_bar(pct: float, width: int = 7) -> str:
    """Build colored progress bar: [####---]"""
    filled = round(pct / 100 * width)
    filled = max(0, min(filled, width))

    # Color by usage level (with ~15% overhead for system prompt/tools)
    total_pct = pct + 15
    if total_pct < 50:
        color = GREEN
    elif total_pct < 80:
        color = YELLOW
    else:
        color = RED

    D = "\033[2m"   # dim
    R = "\033[0m"   # reset
    bar_filled = "#" * filled
    bar_empty = "-" * (width - filled)
    return f"{color}[{bar_filled}{D}{bar_empty}{R}{color}]{R}", color


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception:
        print("⚠ parse error")
        return

    # Debug: dump input to file (set DEBUG_STATUSLINE=1)
    if os.getenv("DEBUG_STATUSLINE"):
        debug_path = Path(tempfile.gettempdir()) / "claude-statusline-debug.json"
        debug_path.write_text(json.dumps(data, indent=2, default=str))

    project_dir = data.get("workspace", {}).get("project_dir", "")
    model = data.get("model", {}).get("display_name", "?")
    session_name = data.get("session_name", "")
    branch = get_branch(project_dir)

    # Context info — prefer new API fields, fallback to context_window
    ctx_window = data.get("context_window", {})
    pct = ctx_window.get("used_percentage")

    # Rate limits (Claude.ai Pro/Max only)
    rate_limits = data.get("rate_limits", {})
    five_hour = rate_limits.get("five_hour", {})
    seven_day = rate_limits.get("seven_day", {})

    # Project folder name
    folder = Path(project_dir).name if project_dir else ""

    # ANSI colors — Claude-branded palette (warm earth)
    D = "\033[2m"   # dim
    R = "\033[0m"   # reset
    SEP = f" {D}›{R} "
    FOLDER = "\033[38;2;235;219;188m"  # manilla cream
    BRANCH = "\033[38;2;212;162;127m"  # kraft tan
    CL = "\033[38;2;217;119;87m"       # claude coral (model)
    EFFORT = "\033[38;2;156;142;126m"  # warm taupe

    # Line 1: dir > branch
    line1 = []

    if folder:
        line1.append(f"{FOLDER}{folder}{R}")

    if branch:
        line1.append(f"{BRANCH}{branch}{R}")

    # Line 2: model > effort > rate limits > context
    line2 = []

    model = model.split(" (")[0]  # "Opus 4.8 (1M context)" → "Opus 4.8"
    line2.append(f"{CL}{model}{R}")

    # Effort level (JSON field since v2.1.119); Opus 4.8 default=high, xhigh available
    effort = data.get("effort", {}).get("level")
    if effort:
        line2.append(f"{EFFORT}{effort}{R}")

    # Rate limits — compact [5h/7d%]
    rl5 = five_hour.get("used_percentage")
    rl7 = seven_day.get("used_percentage")
    if rl5 is not None:
        worst = max(rl5, rl7 or 0)
        if worst < 50:
            rl_color = GREEN
        elif worst < 80:
            rl_color = YELLOW
        else:
            rl_color = RED
        rl_text = f"{rl5:.0f}%/{rl7:.0f}%" if rl7 is not None else f"{rl5:.0f}%"
        line2.append(f"{rl_color}{rl_text}{R}")

    # Context bar — bar + used percentage, whole number (e.g. [####---] 57%)
    if pct is not None:
        bar, color = format_bar(pct)
        line2.append(f"{bar} {color}{pct:.0f}%{R}")

    # Accent marker (coral) on each line + adaptive: one line if it fits $COLUMNS, else two
    MARK = f"{CL}▌{R} "
    one_line = MARK + SEP.join(line1 + line2)
    cols = int(os.environ.get("COLUMNS") or 0)
    if cols and visible_len(one_line) > cols and line1:
        print(MARK + SEP.join(line1) + "\n" + MARK + SEP.join(line2))
    else:
        print(one_line)

if __name__ == "__main__":
    main()
