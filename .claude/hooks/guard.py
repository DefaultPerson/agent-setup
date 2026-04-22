#!/usr/bin/env python3
"""
Claude Code PreToolUse Hook
Blocks dangerous commands, protects credentials, logs all actions.
Cross-platform: supports both Unix and Windows.
"""

import json
import os
import sys
import re
import platform
from pathlib import Path
from datetime import datetime

IS_WINDOWS = platform.system() == "Windows"


def is_dangerous_delete_command(command: str) -> tuple[bool, str | None]:
    """
    Detection of dangerous delete commands.
    Cross-platform: Unix (rm) and Windows (del, rd, rmdir, Remove-Item).
    """
    normalized = ' '.join(command.lower().split())

    # === Unix patterns ===
    unix_rm_patterns = [
        r'\brm\s+.*-[a-z]*r[a-z]*f',
        r'\brm\s+.*-[a-z]*f[a-z]*r',
        r'\brm\s+--recursive\s+--force',
        r'\brm\s+--force\s+--recursive',
        r'\brm\s+-r\s+.*-f',
        r'\brm\s+-f\s+.*-r',
    ]

    unix_dangerous_paths = [
        r'\s/$',
        r'\s/\s',
        r'\s/\*',
        r'\s~/?(\s|$)',
        r'\s\$HOME',
        r'\s\.\.',
        r'\s\./?\s*$',
        r'\s/etc\b',
        r'\s/var\b',
        r'\s/usr\b',
        r'\s/home\b',
        r'\s/root\b',
    ]

    # === Windows patterns ===
    windows_del_patterns = [
        r'\bdel\s+/[sfq]',                 # del /s, del /f, del /q
        r'\brd\s+/[sq]',                   # rd /s, rd /q
        r'\brmdir\s+/[sq]',                # rmdir /s, rmdir /q
        r'remove-item\s+.*-recurse',       # PowerShell Remove-Item -Recurse
        r'\bri\s+.*-r',                    # PowerShell alias ri -r
    ]

    windows_dangerous_paths = [
        r'[a-z]:\\[\s\"\'\*]*$',           # C:\ or C:\*
        r'[a-z]:\\windows\b',              # C:\Windows
        r'[a-z]:\\program\s*files',        # C:\Program Files
        r'[a-z]:\\users\\[^\s\\]+\\?\s*$', # C:\Users\username
        r'[a-z]:\\users\\\*',              # C:\Users\*
        r'%systemroot%',
        r'%userprofile%',
        r'%programfiles%',
        r'\$env:systemroot',
        r'\$env:userprofile',
        r'\$home[\\/]?\s*$',               # PowerShell $HOME
    ]

    # Check Unix
    for pattern in unix_rm_patterns:
        if re.search(pattern, normalized):
            for path in unix_dangerous_paths:
                if re.search(path, normalized):
                    return True, "Dangerous delete: recursive force on system path"

    # Check Windows
    for pattern in windows_del_patterns:
        if re.search(pattern, normalized):
            for path in windows_dangerous_paths:
                if re.search(path, normalized):
                    return True, "Dangerous delete: recursive force on system path (Windows)"

    return False, None


def is_dangerous_system_command(command: str) -> tuple[bool, str | None]:
    """
    Detection of dangerous system commands.
    Cross-platform: Unix and Windows/PowerShell.
    """
    normalized = ' '.join(command.lower().split())

    # === Unix dangerous patterns ===
    unix_patterns = [
        # Disk formatting and writing
        (r'\bmkfs\.', "filesystem formatting"),
        (r'\bdd\s+.*of=/dev/', "direct disk write"),
        (r'>\s*/dev/sd[a-z]', "write to block device"),
        (r'\bfdisk\b', "disk partitioning"),
        (r'\bparted\b', "disk partitioning"),

        # Download and execute
        (r'curl\s+.*\|\s*(ba)?sh', "curl pipe to shell"),
        (r'wget\s+.*\|\s*(ba)?sh', "wget pipe to shell"),
        (r'curl\s+.*\|\s*python', "curl pipe to python"),
        (r'wget\s+.*\|\s*python', "wget pipe to python"),

        # Dangerous chmod
        (r'\bchmod\s+777\s+/', "chmod 777 on system path"),
        (r'\bchmod\s+-R\s+777', "recursive chmod 777"),

        # System operations
        (r'\b:(){ :\|:& };:', "fork bomb"),
        (r'\brm\s+/etc/passwd', "remove passwd"),
        (r'\brm\s+/etc/shadow', "remove shadow"),
        (r'\bshutdown\b', "system shutdown"),
        (r'\breboot\b', "system reboot"),
        (r'\binit\s+0', "system halt"),

        # Network attacks
        (r'\bnc\s+-e\s+/bin/(ba)?sh', "reverse shell"),
        (r'\bbash\s+-i\s+>&\s+/dev/tcp/', "reverse shell"),

        # Git — destructive remote operations
        (r'\bgit\s+push\s+.*--force\b(?!-with-lease)', "git force push"),
        (r'\bgit\s+push\s+.*-f\b', "git force push"),
        (r'\bgit\s+reset\s+--hard', "git reset --hard"),
        (r'\bgit\s+clean\s+.*-[a-z]*f', "git clean -f"),

        # GitHub CLI — irreversible remote actions
        (r'\bgh\s+repo\s+delete\b', "gh repo delete"),
        (r'\bgh\s+release\s+delete\b', "gh release delete"),
    ]

    # === Windows dangerous patterns ===
    windows_patterns = [
        # Disk operations
        (r'\bformat\s+[a-z]:', "disk format"),
        (r'\bdiskpart\b', "disk partitioning"),
        (r'\bbcdboot\b', "boot configuration"),
        (r'\bbcdedit\b', "boot configuration edit"),

        # Registry attacks
        (r'\breg\s+delete\s+hk', "registry delete"),
        (r'remove-itemproperty.*registry', "PowerShell registry delete"),

        # User/system attacks
        (r'\bnet\s+user\s+.*\s+/delete', "user delete"),
        (r'\bnet\s+localgroup\s+administrators', "admin group modify"),

        # Download and execute (PowerShell)
        (r'iex\s*\(.*downloadstring', "PowerShell download & execute"),
        (r'invoke-expression.*net\.webclient', "PowerShell download & execute"),
        (r'powershell\s+.*-enc', "encoded PowerShell command"),
        (r'powershell\s+.*-e\s+[a-z0-9+/=]', "encoded PowerShell command"),

        # System operations
        (r'\bshutdown\s+/[srt]', "system shutdown"),
        (r'stop-computer', "PowerShell shutdown"),
        (r'restart-computer', "PowerShell restart"),

        # Service attacks
        (r'\bsc\s+delete\b', "service delete"),
        (r'stop-service.*-force', "force stop service"),
    ]

    for pattern, reason in unix_patterns:
        if re.search(pattern, normalized):
            return True, reason

    for pattern, reason in windows_patterns:
        if re.search(pattern, normalized):
            return True, reason

    return False, None


def is_credential_read(tool_name: str, tool_input: dict) -> tuple:
    """
    Blocks reading sensitive credential files.
    """
    credential_patterns = [
        (r'\.ssh[/\\]', "SSH key"),
        (r'\.aws[/\\](credentials|config)', "AWS credentials"),
        (r'\.gcloud[/\\]', "GCloud credentials"),
        (r'\.kube[/\\]config', "Kubernetes config"),
        (r'credentials\.json', "credentials file"),
        (r'\.pem$', "PEM certificate"),
        (r'\.key$', "private key"),
        (r'\.p12$', "PKCS12 certificate"),
        (r'\.pfx$', "PFX certificate"),
        (r'token\.json', "auth token"),
    ]

    if tool_name == 'Read':
        file_path = tool_input.get('file_path', '')
        for pattern, desc in credential_patterns:
            if re.search(pattern, file_path):
                return True, f"Reading {desc}: {file_path}"

    elif tool_name == 'Bash':
        command = tool_input.get('command', '')
        normalized = command.lower()
        read_cmds = r'\b(cat|head|tail|less|more|bat|type|get-content)\b'
        if re.search(read_cmds, normalized):
            for pattern, desc in credential_patterns:
                if re.search(pattern, normalized):
                    return True, f"Reading {desc} via shell"

    return False, None


def is_docker_safe(command: str) -> bool:
    """
    Checks if command is a safe docker command.
    Docker commands are generally allowed, but some require attention.
    """
    normalized = command.strip().lower()

    # Dangerous docker commands to block
    dangerous_docker = [
        r'docker\s+run\s+.*--privileged',       # privileged containers
        r'docker\s+run\s+.*-v\s+/:/host',       # mounting root
        r'docker\s+run\s+.*--pid=host',         # host PID namespace
        r'docker\s+run\s+.*--network=host',     # might be ok, but be careful
        r'docker\s+system\s+prune\s+-a',        # will delete everything
    ]

    for pattern in dangerous_docker:
        if re.search(pattern, normalized):
            return False

    return True


def log_action(log_dir: Path, input_data: dict, blocked: bool = False, reason: str = None):
    """Log actions to JSON file."""
    log_path = log_dir / 'pre_tool_use.json'

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool_name": input_data.get('tool_name', ''),
        "blocked": blocked,
        "reason": reason,
        "tool_input": input_data.get('tool_input', {})
    }

    try:
        if log_path.exists():
            with open(log_path, 'r') as f:
                log_data = json.load(f)
        else:
            log_data = []
    except (json.JSONDecodeError, ValueError, OSError):
        log_data = []

    log_data.append(log_entry)

    # Keep only last 1000 entries
    if len(log_data) > 1000:
        log_data = log_data[-1000:]

    try:
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
    except (OSError, TypeError, ValueError):
        return


SECURITY_CRITICAL_TOOLS = {'Bash', 'Read'}


def main():
    tool_name = ''
    try:
        input_data = json.load(sys.stdin)

        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # Define log directory (platform-agnostic: Codex or Claude Code)
        codex_home = os.environ.get('CODEX_HOME')
        if codex_home:
            log_dir = Path(codex_home) / 'logs'
        else:
            log_dir = Path.home() / '.claude' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)

        # === Check credential file reads ===
        is_cred, cred_reason = is_credential_read(tool_name, tool_input)
        if is_cred:
            log_action(log_dir, input_data, blocked=True, reason=cred_reason)
            print(f"BLOCKED: {cred_reason}", file=sys.stderr)
            sys.exit(2)

        # === Check Bash commands ===
        if tool_name == 'Bash':
            command = tool_input.get('command', '')

            # Check dangerous delete commands (rm/del/rd)
            is_del, del_reason = is_dangerous_delete_command(command)
            if is_del:
                reason = del_reason or "Dangerous delete command detected"
                log_action(log_dir, input_data, blocked=True, reason=reason)
                print(f"BLOCKED: {reason}", file=sys.stderr)
                sys.exit(2)

            # Check system commands
            is_dangerous, danger_reason = is_dangerous_system_command(command)
            if is_dangerous:
                reason = f"Dangerous system command: {danger_reason}"
                log_action(log_dir, input_data, blocked=True, reason=reason)
                print(f"BLOCKED: {reason}", file=sys.stderr)
                sys.exit(2)

            # Check docker commands
            if 'docker' in command.lower() and not is_docker_safe(command):
                reason = "Potentially dangerous docker command"
                log_action(log_dir, input_data, blocked=True, reason=reason)
                print(f"BLOCKED: {reason}", file=sys.stderr)
                print("Privileged containers and root mounts are restricted", file=sys.stderr)
                sys.exit(2)

        # Log successful action
        log_action(log_dir, input_data, blocked=False)
        sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"guard.py: invalid stdin JSON: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        # Surface the error so it's not swallowed silently
        import traceback
        print(f"guard.py error on tool={tool_name!r}: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # Fail-close only for security-critical tools; fail-open otherwise
        if tool_name in SECURITY_CRITICAL_TOOLS:
            sys.exit(2)
        sys.exit(0)


if __name__ == '__main__':
    main()
