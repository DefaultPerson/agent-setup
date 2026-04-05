#!/usr/bin/env python3
"""Claude Code status line: dir >> branch >> model >> context% >> rate limits"""
import json
import os
import subprocess
import sys
from pathlib import Path


def get_branch(project_dir: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", project_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=1
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except:
        return ""


def format_bar(pct: float, width: int = 20) -> str:
    """Build colored progress bar: [####--------------]"""
    filled = round(pct / 100 * width)
    filled = max(0, min(filled, width))

    # Color by usage level (with ~15% overhead for system prompt/tools)
    total_pct = pct + 15
    if total_pct < 50:
        color = "\033[32m"  # green
    elif total_pct < 80:
        color = "\033[33m"  # yellow
    else:
        color = "\033[31m"  # red

    D = "\033[2m"   # dim
    R = "\033[0m"   # reset
    bar_filled = "#" * filled
    bar_empty = "-" * (width - filled)
    return f"{color}[{bar_filled}{D}{bar_empty}{R}{color}]{R}", color


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except:
        print("⚠ parse error")
        return

    # Debug: dump input to file (set DEBUG_STATUSLINE=1)
    if os.getenv("DEBUG_STATUSLINE"):
        debug_path = Path("/tmp/claude-statusline-debug.json")
        debug_path.write_text(json.dumps(data, indent=2, default=str))

    project_dir = data.get("workspace", {}).get("project_dir", "")
    model = data.get("model", {}).get("display_name", "?")
    session_name = data.get("session_name", "")
    branch = get_branch(project_dir)

    # Context info — prefer new API fields, fallback to context_window
    ctx_window = data.get("context_window", {})
    pct = ctx_window.get("used_percentage")
    remaining_pct = ctx_window.get("remaining_percentage")

    # Rate limits (Claude.ai Pro/Max only)
    rate_limits = data.get("rate_limits", {})
    five_hour = rate_limits.get("five_hour", {})
    seven_day = rate_limits.get("seven_day", {})

    # Project folder name
    folder = Path(project_dir).name if project_dir else ""

    # ANSI colors
    D = "\033[2m"   # dim
    R = "\033[0m"   # reset
    SEP = f" {D}>>{R} "
    CL = "\033[38;2;217;119;87m"  # claude orange

    parts = []

    if folder:
        parts.append(f"{D}{folder}{R}")

    if branch:
        parts.append(f"\033[35m{branch}{R}")

    parts.append(f"{CL}{model}{R}")

    # Rate limits — compact [5h/7d%]
    rl5 = five_hour.get("used_percentage")
    rl7 = seven_day.get("used_percentage")
    if rl5 is not None:
        worst = max(rl5, rl7 or 0)
        if worst < 50:
            rl_color = "\033[32m"
        elif worst < 80:
            rl_color = "\033[33m"
        else:
            rl_color = "\033[31m"
        rl_text = f"{rl5:.0f}/{rl7:.0f}%" if rl7 is not None else f"{rl5:.0f}%"
        parts.append(f"{rl_color}[{rl_text}]{R}")

    # Context bar
    if pct is not None:
        bar, color = format_bar(pct)
        if remaining_pct is not None:
            remaining_k = int(remaining_pct * ctx_window.get("context_window_size", 200_000) / 100 / 1000)
            parts.append(f"{bar} {color}{remaining_k}k{R}")
        else:
            parts.append(f"{bar} {color}{pct:.0f}%{R}")

    print(SEP.join(parts))

if __name__ == "__main__":
    main()
