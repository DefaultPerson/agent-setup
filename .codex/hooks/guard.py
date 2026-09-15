#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
PreToolUse guard hook (Claude Code / Codex).

Structure-aware command analysis instead of raw substring matching:
the command line is stripped of heredoc bodies, split into shell segments
(respecting quotes, command substitution and pipes), each segment is
tokenized with shlex, and rules run against the actual command position
and its arguments. String literals, commit messages, grep patterns and
quoted ssh remote payloads no longer trigger false positives.

Verdict tiers (this hook guards unattended, bypass-mode sessions):
  DENY  -> exit 2, message on stderr (hard block, fed back to the model;
           always paired with a high-confidence reason + safe alternative)
  ALLOW -> exit 0

There is deliberately NO interactive ASK verdict: a hook prompt stalls an
unattended session. Every rule resolves to DENY or ALLOW. `evaluate()` is
pure (no logging, no process exit); `main()` is the only place that logs and
exits, and it fails open on any error and converts any residual ASK to ALLOW.

Known, accepted limitations (availability over adversary-proofing):
  - quoted ssh/remote payloads are not analyzed (remote is user's domain)
  - an agent determined to bypass the hook can always write a script file;
    this hook protects against accidental footguns, not malice
"""

import json
import os
import re
import shlex
import subprocess
import sys
import platform
from datetime import datetime
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
IS_CODEX = bool(os.environ.get('CODEX_HOME')) or SCRIPT_ROOT.name == '.codex'
HOME = str(Path.home())

ALLOW, ASK, DENY = 0, 1, 2

# ---------------------------------------------------------------------------
# shell parsing
# ---------------------------------------------------------------------------

HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")


def strip_heredocs(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Drop heredoc bodies from the parsed text but return them separately.

    Returns (stripped_text, heredocs) where each heredoc is
    (opening_line, body_text). The body is exposed so a shell consuming it on
    stdin (bash <<EOF) can be evaluated recursively.
    """
    out, heredocs = [], []
    delim, strip_tabs, opening = None, False, None
    body: list[str] = []
    for line in text.split('\n'):
        if delim is not None:
            if line.rstrip() == delim or (strip_tabs and line.lstrip('\t').rstrip() == delim):
                heredocs.append((opening, '\n'.join(body)))
                delim, opening, body = None, None, []
            else:
                body.append(line)
            continue
        m = HEREDOC_RE.search(line)
        out.append(line)
        if m:
            delim = m.group(2)
            strip_tabs = '<<-' in line
            opening = line
            body = []
    if delim is not None:  # unterminated heredoc: treat the tail as the body
        heredocs.append((opening, '\n'.join(body)))
    return '\n'.join(out), heredocs


def strip_quoted(text: str) -> str:
    """Blank out single/double-quoted spans so raw patterns don't match text
    that lives inside a quoted argument (e.g. a commit message)."""
    out = []
    in_sq = in_dq = False
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if in_sq:
            if c == "'":
                in_sq = False
            i += 1
            continue
        if in_dq:
            if c == '\\' and i + 1 < n:
                i += 2
                continue
            if c == '"':
                in_dq = False
            i += 1
            continue
        if c == "'":
            in_sq = True
            out.append(' ')
            i += 1
            continue
        if c == '"':
            in_dq = True
            out.append(' ')
            i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def split_segments(text: str) -> list[tuple[str, bool]]:
    """Split into simple-command segments. Returns [(segment, piped_from_prev)].

    Splits on  ; & && || | newline ( ) ` $(  outside quotes. Single quotes are
    inert. Command substitution `$(...)` and backticks are tracked with a stack
    so their inner commands become their own segments even inside double quotes
    (the quoting state resets inside the substitution and is restored on close).
    """
    segs: list[tuple[str, bool]] = []
    cur: list[str] = []
    in_sq = in_dq = False
    piped = False
    subst: list[tuple[str, bool]] = []  # stack of ('(' | '`', saved in_dq)
    i, n = 0, len(text)

    def flush(next_piped: bool):
        nonlocal cur, piped
        s = ''.join(cur).strip()
        if s:
            segs.append((s, piped))
        cur = []
        piped = next_piped

    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ''
        if in_sq:
            cur.append(c)
            if c == "'":
                in_sq = False
            i += 1
            continue
        if c == '\\':
            cur.append(c)
            if nxt:
                cur.append(nxt)
            i += 2
            continue
        if c == "'" and not in_dq:
            in_sq = True
            cur.append(c)
            i += 1
            continue
        if c == '"':
            in_dq = not in_dq
            cur.append(c)
            i += 1
            continue
        if c == '`':
            if subst and subst[-1][0] == '`':
                flush(False)
                in_dq = subst.pop()[1]
            else:
                flush(False)
                subst.append(('`', in_dq))
                in_dq = False
            i += 1
            continue
        if c == '$' and nxt == '(':
            flush(False)
            subst.append(('(', in_dq))
            in_dq = False
            i += 2
            continue
        if c == ')' and subst and subst[-1][0] == '(':
            flush(False)
            in_dq = subst.pop()[1]
            i += 1
            continue
        if in_dq:
            cur.append(c)
            i += 1
            continue
        if c == '|':
            if nxt == '|':
                flush(False)
                i += 2
            else:
                flush(True)
                i += 1
            continue
        if c == '&':
            if nxt == '&':
                flush(False)
                i += 2
                continue
            if (cur and cur[-1] == '>') or nxt in '><0123456789':
                cur.append(c)
                i += 1
                continue
            flush(False)
            i += 1
            continue
        if c in ';\n()':
            flush(False)
            i += 1
            continue
        cur.append(c)
        i += 1
    flush(False)
    return segs


REDIR_OP_RE = re.compile(r'^\d*>>?$')
REDIR_INLINE_RE = re.compile(r'^(\d*>>?|&>>?)(.+)$')
REDIR_DUP_RE = re.compile(r'^\d*>&\d+-?$')


def extract_redirects(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Pull output-redirect targets out of the token list."""
    targets, out = [], []
    expect_target = False
    for t in tokens:
        if expect_target:
            targets.append(t)
            expect_target = False
            continue
        if REDIR_OP_RE.match(t) or t in ('&>', '&>>'):
            expect_target = True
            continue
        if REDIR_DUP_RE.match(t):
            continue
        m = REDIR_INLINE_RE.match(t)
        if m and not REDIR_DUP_RE.match(t):
            targets.append(m.group(2))
            continue
        if t.startswith('<'):
            continue  # input redirect / stripped heredoc marker
        out.append(t)
    return targets, out


ASSIGN_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')

WRAPPERS = {
    'sudo', 'doas', 'command', 'exec', 'nohup', 'nice', 'ionice',
    'stdbuf', 'timeout', 'time', 'watch', 'xargs', 'env', 'setsid',
}
WRAPPER_VALUE_FLAGS = {
    'sudo': {'-u', '-g', '-p', '-h'},
    'nice': {'-n'},
    'ionice': {'-c', '-n'},
    'timeout': {'-s', '-k', '--signal', '--kill-after'},
    'xargs': {'-I', '-d', '-n', '-P', '-L', '-a', '-E', '-s'},
    'env': {'-u', '-C', '-S'},
    'watch': {'-n', '-d'},
}


def resolve_command(tokens: list[str]) -> tuple[str | None, list[str]]:
    """Skip env assignments and wrapper commands; return (command, args)."""
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if ASSIGN_RE.match(t):
            i += 1
            continue
        name = os.path.basename(t)
        if name in WRAPPERS:
            value_flags = WRAPPER_VALUE_FLAGS.get(name, set())
            i += 1
            while i < len(tokens):
                tk = tokens[i]
                if tk in value_flags:
                    i += 2
                    continue
                if tk.startswith('-'):
                    i += 1
                    continue
                break
            if name == 'timeout' and i < len(tokens):
                i += 1  # duration
            continue
        return name, tokens[i + 1:]
    return None, []


def expand_path(p: str) -> str:
    if p == '~':
        return HOME
    if p.startswith('~/'):
        return HOME + p[1:]
    # ${HOME}, ${HOME:?}, ${HOME:?msg}, ${HOME:-default}, $HOME
    p = re.sub(r'\$\{HOME(?::[?+-][^}]*)?\}', HOME, p)
    p = p.replace('$HOME', HOME)
    return p


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------

SYSTEM_TOP = {
    'etc', 'usr', 'var', 'boot', 'bin', 'sbin', 'lib', 'lib64',
    'opt', 'srv', 'root', 'sys', 'proc', 'dev', 'run', 'nix',
}

HOME_PROTECTED_TOP = {'.ssh', '.config', '.local', 'projects'}


def _is_protected_home_top(name: str) -> bool:
    return name in HOME_PROTECTED_TOP or name.startswith('.claude')


def _resolve_dir(cwd: str | None) -> str | None:
    if not cwd:
        return None
    return os.path.normpath(expand_path(cwd))


def classify_rm_target(t: str, cwd: str | None = None) -> tuple[int, str | None]:
    if t in ('{}', '{}/'):
        return ALLOW, None
    raw = expand_path(t)

    if raw in ('.', './', '..', '../'):
        return DENY, f'rm -r {t}: current/parent directory — name the target explicitly'

    if raw == '*':
        base = _resolve_dir(cwd)
        if base is None:
            return ALLOW, None
        parts = [x for x in base.split('/') if x]
        if base == '/' or base == HOME or (parts and parts[0] in SYSTEM_TOP):
            return DENY, f'rm -r * in {base}: wildcard wipe of a sensitive directory'
        return ALLOW, None

    core = raw
    if core.endswith('/*'):
        core = core[:-1]
    elif core.endswith('*'):
        core = core[:-1]

    if not core.startswith('/'):
        if cwd:
            base = os.path.normpath(os.path.join(_resolve_dir(cwd), core))
        else:
            norm = os.path.normpath(core)
            if norm in ('.', '..') or norm.startswith('../'):
                return DENY, f'rm -r {t}: current/parent directory — name the target explicitly'
            return ALLOW, None
    else:
        base = os.path.normpath(core)

    if base in ('/', ''):
        return DENY, f'rm -r {t}: filesystem root'
    if base == HOME or (HOME + '/').startswith(base + '/'):
        return DENY, f'rm -r {t}: home directory (or its parent)'
    if base.startswith(HOME + '/'):
        rel = base[len(HOME) + 1:]
        if '/' not in rel and _is_protected_home_top(rel):
            return DENY, f'rm -r {t}: protected directory ~/{rel}'
        return ALLOW, None
    parts = [x for x in base.split('/') if x]
    if not parts:
        return DENY, f'rm -r {t}: filesystem root'
    top = parts[0]
    if top == 'tmp' or base.startswith('/var/tmp') or base.startswith('/dev/shm'):
        return ALLOW, None
    if top == 'home':
        if len(parts) <= 2:
            return DENY, f'rm -r {t}: user home root'
        return ALLOW, None
    if top in ('mnt', 'media'):
        return DENY, f'rm -r {t}: mounted volume'
    if top in SYSTEM_TOP:
        return DENY, f'rm -r {t}: system path'
    if len(parts) == 1:
        return DENY, f'rm -r {t}: top-level directory'
    return ALLOW, None


def check_rm(args: list[str], cwd: str | None = None) -> tuple[int, str | None]:
    recursive = False
    targets = []
    flags_done = False
    for a in args:
        if not flags_done and a == '--':
            flags_done = True
            continue
        if not flags_done and a.startswith('--'):
            if a == '--recursive':
                recursive = True
            continue
        if not flags_done and a.startswith('-') and len(a) > 1:
            if 'r' in a or 'R' in a:
                recursive = True
            continue
        targets.append(a)
    if not recursive:
        return ALLOW, None
    worst, reason = ALLOW, None
    for t in targets:
        v, r = classify_rm_target(t, cwd)
        if v > worst:
            worst, reason = v, r
    return worst, reason


def check_find(args: list[str], cwd: str | None = None) -> tuple[int, str | None]:
    has_delete = '-delete' in args
    has_exec_rm = False
    roots: list[str] = []
    seen_predicate = False
    i = 0
    while i < len(args):
        a = args[i]
        if a in ('-exec', '-execdir'):
            seen_predicate = True
            if i + 1 < len(args) and os.path.basename(args[i + 1]) == 'rm':
                has_exec_rm = True
            i += 1
            continue
        if a.startswith('-') or a in ('(', ')', '!', ','):
            seen_predicate = True
            i += 1
            continue
        if not seen_predicate:
            roots.append(a)
        i += 1
    if not (has_delete or has_exec_rm):
        return ALLOW, None
    if not roots:
        roots = ['.']
    worst, reason = ALLOW, None
    for r in roots:
        if r in ('.', './'):
            continue  # a filtered find under the current dir is the normal case
        v, rr = classify_rm_target(r, cwd)
        if v > worst:
            worst, reason = v, rr
    return worst, reason


INTERP_DEL_RE = re.compile(r'rmtree|rmSync|rm\s+-\w*[rf]')


def check_interpreter_delete(code: str, cwd: str | None = None) -> tuple[int, str | None]:
    """Classify literal paths passed to a delete call inside python -c / node -e."""
    if not INTERP_DEL_RE.search(code):
        return ALLOW, None
    worst, reason = ALLOW, None

    def bump(v, r):
        nonlocal worst, reason
        if v > worst:
            worst, reason = v, r

    for m in re.finditer(r'(?:rmtree|rmSync)\s*\(\s*[\'"]([^\'"]+)[\'"]', code):
        bump(*classify_rm_target(m.group(1), cwd))
    for m in re.finditer(r'rm\s+-\w*[rf]\w*\s+[\'"]?([^\'"\s]+)', code):
        bump(*classify_rm_target(m.group(1), cwd))
    return worst, reason


def check_chmod(args: list[str]) -> tuple[int, str | None]:
    recursive = any(
        a in ('-R', '--recursive')
        or (a.startswith('-') and not a.startswith('--') and 'R' in a)
        for a in args
    )
    positional = [a for a in args if not a.startswith('-')]
    if not positional or positional[0] not in ('777', '0777', 'a+rwx', 'ugo+rwx'):
        return ALLOW, None
    if recursive:
        return DENY, 'recursive chmod 777'
    for t in positional[1:]:
        p = expand_path(t)
        if p.startswith('/'):
            parts = [x for x in p.split('/') if x]
            if len(parts) <= 2 or parts[0] in SYSTEM_TOP:
                return DENY, f'chmod 777 on system path {t}'
    return ALLOW, None


def _git_worktree_dirty(cwd: str | None) -> tuple[int, str | None]:
    hint = 'commit or `git stash -u` first'
    if not cwd:
        return DENY, f'git reset --hard may discard uncommitted changes (cwd unknown) — {hint}'
    try:
        r = subprocess.run(['git', '-C', cwd, 'status', '--porcelain'],
                           capture_output=True, text=True, timeout=2)
    except Exception:
        return DENY, f'git reset --hard: cannot verify the worktree is clean — {hint}'
    if r.returncode != 0 or r.stdout.strip():
        return DENY, f'git reset --hard would discard uncommitted changes — {hint}'
    return ALLOW, None


def _git_clean_deletes(cwd: str | None, rest: list[str]) -> tuple[int, str | None]:
    hint = 'commit or `git stash -u` first'
    if not cwd:
        return DENY, f'git clean -f may delete untracked files (cwd unknown) — {hint}'
    flags = ['-n']
    for a in rest:
        if a.startswith('-') and not a.startswith('--'):
            for ch in a[1:]:
                if ch in 'dx':
                    flags.append('-' + ch)
    try:
        r = subprocess.run(['git', '-C', cwd, 'clean'] + flags,
                           capture_output=True, text=True, timeout=2)
    except Exception:
        return DENY, f'git clean -f: cannot verify what would be deleted — {hint}'
    if r.returncode != 0 or r.stdout.strip():
        return DENY, f'git clean -f would delete untracked files — {hint}'
    return ALLOW, None


def check_git(args: list[str], cwd: str | None = None) -> tuple[int, str | None]:
    i = 0
    while i < len(args) and args[i].startswith('-'):
        i += 2 if args[i] in ('-C', '-c') else 1
    if i >= len(args):
        return ALLOW, None
    sub, rest = args[i], args[i + 1:]

    if sub == 'push':
        has_lease = any(a == '--force-with-lease' or a.startswith('--force-with-lease=')
                        or a == '--force-if-includes' for a in rest)
        has_force = ('--force' in rest or '-f' in rest
                     or any(a.startswith('-') and not a.startswith('--') and 'f' in a[1:] for a in rest)
                     or any(re.match(r'^\+\w', a) for a in rest))
        if has_force and not has_lease:
            return DENY, 'git push --force rewrites remote history — use --force-with-lease'
        if has_lease:
            return ALLOW, None
        if '--mirror' in rest:
            return DENY, 'git push --mirror overwrites all remote refs — push explicit branches'
        deleted = []
        if '--delete' in rest or '-d' in rest:
            pos = [a for a in rest if not a.startswith('-')]
            deleted += pos[1:] if len(pos) > 1 else pos
        for a in rest:
            m = re.match(r'^:([\w./-]+)$', a)  # `push remote :ref` deletion syntax
            if m:
                deleted.append(m.group(1))
        for ref in deleted:
            if ref.split(':')[-1] in ('main', 'master'):
                return DENY, f'git push deleting protected branch {ref} — delete feature branches only'
        return ALLOW, None

    if sub == 'reset' and '--hard' in rest:
        return _git_worktree_dirty(cwd)

    if sub == 'clean':
        if any(a == '--force' or (a.startswith('-') and not a.startswith('--') and 'f' in a) for a in rest):
            return _git_clean_deletes(cwd, rest)

    if sub in ('checkout', 'restore'):
        pos = [a for a in rest if not a.startswith('-') and a != '--']
        if '.' in pos:
            return DENY, (f'git {sub} . discards all worktree changes — '
                          'name specific paths, or commit / `git stash -u` first')

    if sub == 'stash' and rest[:1] == ['clear']:
        return DENY, 'git stash clear drops every stash — use `git stash drop <id>` for one'

    return ALLOW, None


def check_gh(args: list[str]) -> tuple[int, str | None]:
    positional = [a for a in args if not a.startswith('-')]
    if positional[:2] == ['repo', 'delete']:
        return DENY, 'gh repo delete: irreversible remote deletion'
    return ALLOW, None


def check_docker(args: list[str]) -> tuple[int, str | None]:
    positional = [a for a in args if not a.startswith('-')]
    is_run = positional[:1] == ['run'] or positional[:2] == ['container', 'run']
    if not is_run:
        return ALLOW, None
    for j, a in enumerate(args):
        val = None
        if a in ('-v', '--volume') and j + 1 < len(args):
            val = args[j + 1]
        elif a.startswith('--volume='):
            val = a.split('=', 1)[1]
        if val and (val == '/' or val.startswith('/:')):
            return DENY, 'docker run mounting / into a container'
    return ALLOW, None


SSH_SAFE_BASENAMES = {
    'config', 'known_hosts', 'known_hosts.old', 'environment',
    # authorized_keys is a list of PUBLIC keys — safe to read (writing it is
    # blocked separately in check_write_path).
    'authorized_keys', 'authorized_keys2',
}


def _file_has_private_key(p: str) -> bool:
    try:
        with open(p, 'rb') as f:
            return b'PRIVATE KEY' in f.read(65536)
    except OSError:
        return False


def classify_credential_path(path: str) -> str | None:
    """Return a description if path points at secret material, else None."""
    if not path:
        return None
    p = expand_path(path).rstrip('/')
    if re.search(r'(?:^|/)\.ssh$', p):
        return 'the ~/.ssh directory'
    m = re.search(r'(?:^|[/\\])\.ssh[/\\](.+)$', p)
    if m:
        base = re.split(r'[/\\]', m.group(1))[-1]
        if base in SSH_SAFE_BASENAMES or base.endswith('.pub') or base == '':
            return None
        return 'SSH private key material'
    if re.search(r'\.aws[/\\]credentials$', p):
        return 'AWS credentials'
    if re.search(r'\.kube[/\\]config$', p):
        return 'Kubernetes credentials'
    if re.search(r'gcloud[/\\](credentials|legacy_credentials|access_tokens)', p):
        return 'GCloud credentials'
    if re.search(r'\.gnupg[/\\](private-keys|secring)', p):
        return 'GPG private keys'
    if re.search(r'/\.claude(?:-personal)?/\.credentials\.json$', p):
        return 'Claude credentials'
    if re.search(r'/\.config/gh/hosts\.yml$', p):
        return 'GitHub CLI credentials'
    if re.search(r'/\.docker/config\.json$', p):
        return 'Docker registry credentials'
    base = re.split(r'[/\\]', p)[-1]
    if base in ('credentials.json', 'token.json', '.netrc', '_netrc', '.pgpass'):
        return f'credential file {base}'
    if re.search(r'\.(key|p12|pfx)$', base):
        return 'private key / certificate file'
    if re.search(r'\.(pem|crt|cer)$', base):
        # a .pem/.crt/.cer is only secret if it actually holds a private key;
        # public CA certs with these extensions are safe to read.
        return 'private key file' if _file_has_private_key(p) else None
    return None


READERS = {
    'cat', 'head', 'tail', 'less', 'more', 'bat', 'batcat', 'strings',
    'xxd', 'od', 'hexdump', 'base64', 'grep', 'egrep', 'fgrep', 'rg',
    'awk', 'gawk', 'sed', 'cut', 'tac', 'nl', 'type', 'get-content', 'gc',
}
PATTERN_FIRST = {'grep', 'egrep', 'fgrep', 'rg', 'awk', 'gawk', 'sed'}
LOCAL_COPIERS = {'cp', 'mv', 'install'}
UPLOADERS = {'scp', 'rsync'}
COPIERS = LOCAL_COPIERS | UPLOADERS
EXFIL_ARCHIVERS = {'tar', 'gtar', 'bsdtar', 'zip'}


def check_credential_access(cmd: str, args: list[str]) -> tuple[int, str | None]:
    skip_first = cmd in PATTERN_FIRST
    for a in args:
        if a.startswith('-'):
            continue
        if skip_first:
            skip_first = False
            continue
        hit = classify_credential_path(a)
        if hit:
            if cmd in READERS:
                return DENY, f'Reading {hit}: {a}'
            if cmd in UPLOADERS:
                return DENY, f'Uploading {hit} to a remote: {a} — keep private keys local'
            # cp / mv / install: a local copy of credentials is allowed
            return ALLOW, None
    return ALLOW, None


def check_exfil(cmd: str, args: list[str]) -> tuple[int, str | None]:
    """Archiving / recursively copying the ~/.ssh directory looks like exfil."""
    archiver = cmd in EXFIL_ARCHIVERS
    recursive_copy = cmd == 'rsync' or (
        cmd == 'cp' and any(a.startswith('-') and not a.startswith('--') and ('r' in a or 'R' in a) or
                            a in ('--recursive', '--archive') for a in args))
    if not (archiver or recursive_copy):
        return ALLOW, None
    for a in args:
        if a.startswith('-'):
            continue
        if classify_credential_path(a) == 'the ~/.ssh directory':
            return DENY, f'archiving/exfiltrating ~/.ssh: {a}'
    return ALLOW, None


def check_upload(cmd: str, args: list[str]) -> tuple[int, str | None]:
    """curl/wget uploading credential material to a remote."""
    for j, a in enumerate(args):
        val = None
        if a in ('-T', '--upload-file'):
            val = args[j + 1] if j + 1 < len(args) else None
        elif a.startswith('--upload-file='):
            val = a.split('=', 1)[1]
        elif a in ('--data-binary', '--data', '--data-ascii', '-d'):
            nxt = args[j + 1] if j + 1 < len(args) else ''
            if nxt.startswith('@'):
                val = nxt[1:]
        elif a.startswith(('--data-binary=', '--data=', '--data-ascii=')):
            payload = a.split('=', 1)[1]
            if payload.startswith('@'):
                val = payload[1:]
        if val and classify_credential_path(val):
            return DENY, f'uploading credential material via {cmd}: {val} — keep secrets local'
    return ALLOW, None


REPO_GUARD = HOME + '/projects/misc/agent-setup/.claude/hooks/guard.py'
DEPLOYED_GUARDS = (HOME + '/.claude/hooks/guard.py', HOME + '/.claude-personal/hooks/guard.py')


def is_deployed_guard(p: str) -> bool:
    try:
        rp = os.path.realpath(p)
    except OSError:
        rp = p
    for c in DEPLOYED_GUARDS:
        if p == c:
            return True
        try:
            if rp == os.path.realpath(c):
                return True
        except OSError:
            pass
    return False


def is_allowed_install(cmd: str, args: list[str]) -> bool:
    """The one sanctioned way to deploy the guard: install -m 0644 <repo> <live>."""
    if cmd != 'install' or not any('0644' in a for a in args):
        return False
    skip_val = {'-m', '-o', '-g', '-t', '--mode', '--owner', '--group', '--target-directory'}
    pos, i = [], 0
    while i < len(args):
        a = args[i]
        if a in skip_val:
            i += 2
            continue
        if a.startswith('-'):
            i += 1
            continue
        pos.append(a)
        i += 1
    if len(pos) != 2:
        return False
    try:
        src = os.path.realpath(expand_path(pos[0]))
    except OSError:
        src = expand_path(pos[0])
    dst = os.path.normpath(expand_path(pos[1]))
    try:
        repo = os.path.realpath(REPO_GUARD)
    except OSError:
        repo = REPO_GUARD
    return src == repo and dst == HOME + '/.claude/hooks/guard.py'


def _check_settings_change(content, tool_name, edits) -> tuple[int, str | None]:
    """Guard the guard: block a settings edit that unhooks guard.py."""
    def bad_new(new):
        return 'disableAllHooks' in (new or '')

    if tool_name == 'Write' and content is not None:
        if 'disableAllHooks' in content:
            return DENY, 'settings change adds disableAllHooks — that turns the guard off'
        if ('"hooks"' in content or 'PreToolUse' in content) and 'guard.py' not in content:
            return DENY, 'settings change replaces hooks without guard.py — keep the guard installed'
        return ALLOW, None
    if tool_name == 'Edit' and isinstance(edits, dict):
        old, new = edits.get('old_string', ''), edits.get('new_string', '')
        if bad_new(new):
            return DENY, 'settings edit adds disableAllHooks — that turns the guard off'
        if 'guard.py' in old and 'guard.py' not in new:
            return DENY, 'settings edit removes guard.py from hooks — keep the guard installed'
        return ALLOW, None
    if tool_name == 'MultiEdit' and isinstance(edits, list):
        for e in edits:
            old, new = e.get('old_string', ''), e.get('new_string', '')
            if bad_new(new):
                return DENY, 'settings edit adds disableAllHooks — that turns the guard off'
            if 'guard.py' in old and 'guard.py' not in new:
                return DENY, 'settings edit removes guard.py from hooks — keep the guard installed'
        return ALLOW, None
    return ALLOW, None


SETTINGS_RE = re.compile(r'/\.claude(?:-personal)?/settings[^/]*\.json$')


def check_write_path(path: str, content=None, tool_name=None, edits=None,
                     cwd: str | None = None) -> tuple[int, str | None]:
    if not path:
        return ALLOW, None
    p = expand_path(path)
    if cwd and not p.startswith('/'):
        p = os.path.normpath(os.path.join(_resolve_dir(cwd), p))

    m = re.search(r'(?:^|[/\\])\.ssh[/\\](.+)$', p)
    if m:
        base = re.split(r'[/\\]', m.group(1))[-1]
        # Only the two genuinely dangerous writes are blocked; config backups,
        # known_hosts and .pub files under ~/.ssh are routine.
        if base in ('authorized_keys', 'authorized_keys2'):
            return DENY, f'writing SSH authorized_keys grants login access: {path}'
        if base.startswith('id_') and not base.endswith('.pub'):
            return DENY, f'overwriting an SSH private key: {path}'
        return ALLOW, None

    if is_deployed_guard(p):
        return DENY, ('editing the deployed guard hook — edit the copy in '
                      '~/projects/misc/agent-setup, run the tests, then install it')

    if SETTINGS_RE.search(p):
        return _check_settings_change(content, tool_name, edits)

    return ALLOW, None


def write_targets(cmd: str, args: list[str]) -> list[str]:
    """Destination paths that a writing command modifies."""
    if cmd == 'tee':
        return [a for a in args if not a.startswith('-') and a != '-']
    if cmd == 'sed':
        if not any(a == '-i' or a == '--in-place' or a.startswith('--in-place')
                   or (a.startswith('-i') and not a.startswith('--')) for a in args):
            return []
        pos = [a for a in args if not a.startswith('-')]
        uses_script_flag = any(a in ('-e', '-f', '--expression', '--file')
                               or a.startswith(('-e', '-f')) for a in args)
        return pos if uses_script_flag else pos[1:]
    if cmd in ('cp', 'mv', 'install'):
        pos = [a for a in args if not a.startswith('-')]
        return pos[-1:] if len(pos) >= 2 else []
    if cmd == 'ln':
        pos = [a for a in args if not a.startswith('-')]
        return pos[-1:] if pos else []
    return []


SHELLS = {'sh', 'bash', 'zsh', 'dash', 'ksh'}
DOWNLOADERS = {'curl', 'wget'}
PYTHON_RE = re.compile(r'^python[\d.]*$')


def shell_execs_stdin(args: list[str]) -> bool:
    if '-c' in args:
        return False
    for a in args:
        if a in ('-s', '-'):
            return True
        if not a.startswith('-'):
            return False  # script file argument
    return True


def python_execs_stdin(args: list[str]) -> bool:
    if '-c' in args or '-m' in args:
        return False
    for a in args:
        if a == '-':
            return True
        if not a.startswith('-'):
            return False
    return True


def echo_payload(args: list[str]) -> str | None:
    parts, started = [], False
    for a in args:
        if not started and re.fullmatch(r'-[neE]+', a):
            continue
        started = True
        parts.append(a)
    return ' '.join(parts) if parts else None


# --- process control: pkill/pgrep that matches the agent's own shell -------

# The Bash tool runs `bash -c "<command text>"`, so that shell's own argv holds
# the command text: a `pkill -f PATTERN` whose regex matches it kills the shell
# running it (tool exit 144, plain shell 143, over ssh 255).

PKILL_VALUE_SHORT = set('uUgGtPsFd')   # short options that consume a value
PKILL_VALUE_LONG = {
    '--signal', '--uid', '--euid', '--group', '--pgroup', '--terminal',
    '--parent', '--session', '--pidfile', '--delimiter', '--ns', '--nslist',
}
SSH_VALUE_SHORT = set('BbcDEeFIiJLlmOopQRSWw')

# pgrep output fed into a kill within the same command line
PGREP_TO_KILL_RE = re.compile(
    r'\bkill\b[^|;\n]*(?:\$\(|`)[^)`]*\bpgrep\b'  # kill $(pgrep -f x) / `pgrep -f x`
    r'|\bpgrep\b[^|]*\|[^|]*\bkill\b'              # pgrep -f x | xargs kill
)

SELF_PKILL_HINT = (
    "matches this command's own shell, so it would kill itself (exit 144). "
    'Stop by PID from a pid file or from a separate pgrep call, use systemctl '
    'or docker stop, or write the pattern as [p]attern with the plain name '
    'nowhere else in the command.'
)


def parse_pkill(args: list[str]) -> tuple[bool, str | None]:
    """Return (full_match, pattern) for a pkill/pgrep argument list."""
    full, i = False, 0
    while i < len(args):
        a = args[i]
        if a == '--':
            i += 1
            break
        if a.startswith('--'):
            name = a.split('=', 1)[0]
            if name == '--full':
                full = True
            elif name in PKILL_VALUE_LONG and '=' not in a:
                i += 1
            i += 1
            continue
        if a.startswith('-') and len(a) > 1:
            for j, ch in enumerate(a[1:]):
                if ch == 'f':
                    full = True
                elif ch in PKILL_VALUE_SHORT:
                    if j == len(a) - 2:
                        i += 1  # the value is the next token
                    break       # otherwise the rest of the cluster is the value
            i += 1
            continue
        return full, a
    return full, args[i] if i < len(args) else None


def check_self_pkill(cmd: str, args: list[str], top: str | None) -> tuple[int, str | None]:
    """DENY a full-match pkill (or a pgrep feeding a kill) that matches `top`."""
    if not top:
        return ALLOW, None
    full, pattern = parse_pkill(args)
    if not full or not pattern:
        return ALLOW, None
    try:  # POSIX ERE is a subset of Python's syntax; anything else -> allow
        if not re.search(pattern, top):
            return ALLOW, None
    except Exception:
        return ALLOW, None
    if cmd == 'pgrep' and not PGREP_TO_KILL_RE.search(top):
        return ALLOW, None
    return DENY, f"{cmd} -f '{pattern}' {SELF_PKILL_HINT}"


def scan_pkill_text(text: str, top: str | None) -> tuple[int, str | None]:
    """Look for a self-matching pkill/pgrep inside an unevaluated payload."""
    worst, reason = ALLOW, None
    for seg_text, _ in split_segments(text or ''):
        try:
            tokens = shlex.split(seg_text)
        except ValueError:
            continue
        _, tokens = extract_redirects(tokens)
        cmd, args = resolve_command(tokens)
        if cmd in ('pkill', 'pgrep'):
            v, r = check_self_pkill(cmd, args, top)
            if v > worst:
                worst, reason = v, r
    return worst, reason


def ssh_remote_command(args: list[str]) -> str:
    """The remote payload of an ssh invocation (everything after the host)."""
    pos, i = [], 0
    while i < len(args):
        a = args[i]
        if a.startswith('--'):
            i += 1
            continue
        if a.startswith('-') and len(a) > 1:
            if a[-1] in SSH_VALUE_SHORT:
                i += 1  # value lives in the next token
            i += 1
            continue
        pos.append(a)
        i += 1
    return ' '.join(pos[1:])


# --- systemd units protected on this machine ------------------------------

PROTECTED_UNIT_ACTIONS = {
    'stop', 'restart', 'disable', 'kill', 'mask', 'try-restart',
    'reload-or-restart',
}


def _unit_key(name: str) -> str:
    return name[:-8] if name.endswith('.service') else name


def protected_units() -> set[str]:
    """Unit names from $GUARD_PROTECTED_UNITS (comma/whitespace separated)."""
    raw = os.environ.get('GUARD_PROTECTED_UNITS', '')
    return {_unit_key(n) for n in re.split(r'[,\s]+', raw) if n}


def check_systemctl(args: list[str]) -> tuple[int, str | None]:
    positional = [a for a in args if not a.startswith('-')]
    sub = positional[0] if positional else ''
    if sub in ('poweroff', 'reboot', 'halt', 'kexec'):
        return DENY, f'systemctl {sub}'
    if sub in PROTECTED_UNIT_ACTIONS:
        guarded = protected_units()
        for unit in positional[1:]:
            if _unit_key(unit) in guarded:
                return DENY, (f"systemd unit '{unit}' is protected on this machine "
                              '(GUARD_PROTECTED_UNITS); report the problem instead '
                              'of stopping or restarting it.')
    return ALLOW, None


def check_command(cmd: str, args: list[str], cwd: str | None = None) -> tuple[int, str | None]:
    if cmd == 'rm':
        return check_rm(args, cwd)
    if cmd == 'find':
        return check_find(args, cwd)
    if cmd in ('shutdown', 'poweroff', 'halt', 'telinit', 'reboot'):
        return DENY, f'{cmd}: system power command'
    if cmd == 'init' and args and args[0] in ('0', '6'):
        return DENY, 'init 0/6: system halt/reboot'
    if cmd == 'systemctl':
        v, r = check_systemctl(args)
        if v != ALLOW:
            return v, r
    if cmd.startswith('mkfs'):
        return DENY, 'filesystem formatting'
    if cmd in ('fdisk', 'sfdisk', 'cfdisk', 'parted', 'wipefs'):
        if '-l' in args or '--list' in args:
            return ALLOW, None
        return DENY, f'{cmd}: disk partitioning'
    if cmd == 'dd':
        for a in args:
            if re.match(r'^of=/dev/(sd|hd|vd|nvme|mmcblk|md|dm-|disk)', a):
                return DENY, 'dd: direct write to a block device'
        return ALLOW, None
    if cmd == 'chmod':
        return check_chmod(args)
    if cmd == 'git':
        return check_git(args, cwd)
    if cmd == 'gh':
        return check_gh(args)
    if cmd == 'docker':
        return check_docker(args)
    if cmd in DOWNLOADERS:
        return check_upload(cmd, args)
    if cmd in ('nc', 'ncat', 'netcat') and '-e' in args:
        return DENY, f'{cmd} -e: reverse shell'
    if cmd in READERS or cmd in COPIERS:
        return check_credential_access(cmd, args)
    return ALLOW, None


# Severe patterns checked on raw text (tokenized words, quoted args blanked).
RAW_DENY = [
    (r':\(\)\s*\{', 'fork bomb'),
    (r'\bbash\s+-i\s+>&\s*/dev/tcp/', 'reverse shell'),
]

SEVERE_FALLBACK = [
    (r'\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+(--\S+\s+)*["\']?(/|/\*|~|\$HOME)["\']?\s*($|[;&|])',
     'rm -rf on root/home'),
    (r'\bmkfs\.', 'filesystem formatting'),
    (r'\bdd\s+[^|;]*of=/dev/(sd|hd|vd|nvme|mmcblk)', 'direct disk write'),
    (r':\(\)\s*\{', 'fork bomb'),
]


def severe_fallback(text: str) -> tuple[int, str | None]:
    for pat, why in SEVERE_FALLBACK:
        if re.search(pat, text):
            return DENY, why
    return ALLOW, None


# Legacy Windows checks (raw patterns; only run when actually on Windows).
WINDOWS_RAW = [
    (r'\b(del|erase)\s+/[sfq].*[a-z]:\\', 'recursive delete on drive root'),
    (r'\b(rd|rmdir)\s+/[sq].*[a-z]:\\', 'recursive delete on drive root'),
    (r'remove-item\s+.*-recurse.*(\$env:|[a-z]:\\(windows|users|program))', 'recursive delete on system path'),
    (r'\bformat\s+[a-z]:', 'disk format'),
    (r'\bdiskpart\b', 'disk partitioning'),
    (r'\bbcdedit\b|\bbcdboot\b', 'boot configuration'),
    (r'\breg\s+delete\s+hk', 'registry delete'),
    (r'\bnet\s+user\s+.*\s+/delete', 'user delete'),
    (r'iex\s*\(.*downloadstring', 'PowerShell download & execute'),
    (r'powershell\s+.*-enc\b', 'encoded PowerShell command'),
    (r'\bshutdown\s+/[srt]', 'system shutdown'),
    (r'stop-computer|restart-computer', 'PowerShell shutdown/restart'),
    (r'\bsc\s+delete\b', 'service delete'),
]


def check_windows_raw(text: str) -> tuple[int, str | None]:
    low = ' '.join(text.lower().split())
    for pat, why in WINDOWS_RAW:
        if re.search(pat, low):
            return DENY, why
    return ALLOW, None


def _heredoc_consumer_execs(opening_line: str) -> bool:
    """Does the command on this heredoc's opening line run the body as shell?"""
    segs = split_segments(opening_line)
    if not segs:
        return False
    try:
        tokens = shlex.split(segs[-1][0])
    except ValueError:
        return False
    _, tokens = extract_redirects(tokens)
    cmd, args = resolve_command(tokens)
    return cmd in SHELLS and shell_execs_stdin(args)


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------

def evaluate_bash(command: str, depth: int = 0, cwd: str | None = None,
                  top: str | None = None) -> tuple[int, str | None]:
    if not command or depth > 3:
        return ALLOW, None
    if top is None:
        top = command  # the text the Bash tool's own `bash -c` shell carries in argv
    text, heredocs = strip_heredocs(command)

    if IS_WINDOWS:
        v, r = check_windows_raw(text)
        if v != ALLOW:
            return v, r

    quoted_blanked = strip_quoted(text)
    for pat, why in RAW_DENY:
        if re.search(pat, quoted_blanked):
            return DENY, why

    worst, reason = ALLOW, None

    def bump(v, r):
        nonlocal worst, reason
        if v > worst:
            worst, reason = v, r

    # heredoc bodies consumed by a shell run as shell code
    for opening, body in heredocs:
        if opening and _heredoc_consumer_execs(opening):
            bump(*evaluate_bash(body, depth + 1, cwd, top))
    if worst == DENY:
        return DENY, reason

    prev_echo_payload = None
    for seg_text, piped in split_segments(text):
        if not piped:
            prev_echo_payload = None
        try:
            tokens = shlex.split(seg_text)
        except ValueError:
            bump(*severe_fallback(seg_text))
            prev_echo_payload = None
            continue
        redirect_targets, tokens = extract_redirects(tokens)
        cmd, args = resolve_command(tokens)

        for tgt in redirect_targets:
            if re.match(r'^/dev/(sd|hd|vd|nvme|mmcblk)', tgt):
                return DENY, 'write to a raw block device'
            bump(*check_write_path(tgt, cwd=cwd))

        if not cmd:
            prev_echo_payload = None
            continue

        cur_echo = echo_payload(args) if cmd in ('echo', 'printf') else None

        # inline code: bash -c '...' / eval '...'
        if cmd in SHELLS and '-c' in args:
            idx = args.index('-c')
            if idx + 1 < len(args):
                bump(*evaluate_bash(args[idx + 1], depth + 1, cwd, top))
        elif cmd == 'eval' and args:
            bump(*evaluate_bash(' '.join(args), depth + 1, cwd, top))

        # interpreter one-liners that delete files
        if PYTHON_RE.match(cmd) and '-c' in args:
            idx = args.index('-c')
            if idx + 1 < len(args):
                bump(*check_interpreter_delete(args[idx + 1], cwd))
        elif cmd in ('node', 'nodejs') and '-e' in args:
            idx = args.index('-e')
            if idx + 1 < len(args):
                bump(*check_interpreter_delete(args[idx + 1], cwd))

        # echo/printf '...' | sh  -> the echoed payload runs as shell
        if piped and prev_echo_payload is not None and cmd in SHELLS and shell_execs_stdin(args):
            bump(*evaluate_bash(prev_echo_payload, depth + 1, cwd, top))

        # bash write destinations (sed -i / tee / cp / mv / ln)
        if not is_allowed_install(cmd, args):
            for tgt in write_targets(cmd, args):
                bump(*check_write_path(tgt, cwd=cwd))

        # pkill -f / pgrep -f whose pattern matches this very command line
        if cmd in ('pkill', 'pgrep'):
            bump(*check_self_pkill(cmd, args, top))
        elif cmd == 'ssh':
            bump(*scan_pkill_text(ssh_remote_command(args), top))

        bump(*check_exfil(cmd, args))
        bump(*check_command(cmd, args, cwd))

        prev_echo_payload = cur_echo
        if worst == DENY:
            return DENY, reason

    return worst, reason


def evaluate(tool_name: str, tool_input: dict, cwd: str | None = None) -> tuple[int, str | None]:
    if not isinstance(tool_input, dict):
        return ALLOW, None
    if tool_name == 'Bash':
        return evaluate_bash(tool_input.get('command', ''), cwd=cwd)
    if tool_name in ('Read', 'Grep'):
        path = tool_input.get('file_path') or tool_input.get('path') or ''
        hit = classify_credential_path(path)
        if hit:
            return DENY, f'Reading {hit}: {path}'
        return ALLOW, None
    if tool_name in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
        path = tool_input.get('file_path', '') or tool_input.get('notebook_path', '')
        content = tool_input.get('content')
        edits = None
        if tool_name == 'Edit':
            edits = {'old_string': tool_input.get('old_string', ''),
                     'new_string': tool_input.get('new_string', '')}
        elif tool_name == 'MultiEdit':
            edits = tool_input.get('edits', [])
        return check_write_path(path, content=content, tool_name=tool_name, edits=edits, cwd=cwd)
    return ALLOW, None


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def resolve_log_dir() -> Path:
    candidates = []
    codex_home = os.environ.get('CODEX_HOME')
    if codex_home:
        candidates.append(Path(codex_home) / 'logs')
    if SCRIPT_ROOT.name == '.codex':
        candidates.append(SCRIPT_ROOT / 'log')
    config_dir = os.environ.get('CLAUDE_CONFIG_DIR')
    if config_dir:
        candidates.append(Path(config_dir) / 'logs')
    candidates.append(Path.home() / '.claude' / 'logs')
    candidates.append(Path('/tmp'))
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            if os.access(candidate, os.W_OK):
                return candidate
        except OSError:
            continue
    return Path('/tmp')


def log_action(log_dir: Path, tool_name: str, tool_input: dict, decision: str, reason: str | None):
    path = log_dir / 'pre_tool_use.jsonl'
    try:
        if path.exists() and path.stat().st_size > 5_000_000:
            path.replace(path.with_suffix('.jsonl.old'))
    except OSError:
        pass
    summary = ''
    if isinstance(tool_input, dict):
        summary = tool_input.get('command') or tool_input.get('file_path') or ''
    entry = {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'tool_name': tool_name,
        'decision': decision,
        'reason': reason,
        'input': str(summary)[:500],
    }
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except OSError:
        pass


# Appended to every deny reason handed to the model (the log keeps the bare
# reason); rules therefore never have to repeat it.
DENY_SUFFIX = (" Use the alternative named here or report the block; don't reach "
               'the same effect through another command form.')


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f'guard.py: invalid stdin JSON, allowing: {e}', file=sys.stderr)
        sys.exit(0)
    except Exception as e:  # any stdin/read failure -> fail open
        print(f'guard.py: cannot read stdin, allowing: {e}', file=sys.stderr)
        sys.exit(0)

    if not isinstance(input_data, dict):
        print('guard.py: unexpected stdin shape, allowing', file=sys.stderr)
        sys.exit(0)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {}) or {}
    cwd = input_data.get('cwd')
    log_dir = resolve_log_dir()

    try:
        verdict, reason = evaluate(tool_name, tool_input, cwd)
    except Exception as e:  # any internal error -> fail open (exit 0)
        import traceback
        traceback.print_exc(file=sys.stderr)
        log_action(log_dir, tool_name, tool_input, 'allow', f'error→allow: {type(e).__name__}')
        print(f'guard.py: internal error ({type(e).__name__}), allowing', file=sys.stderr)
        sys.exit(0)

    # Safety net: no ASK should ever surface in an unattended session.
    if verdict == ASK:
        log_action(log_dir, tool_name, tool_input, 'allow', f'ask→allow: {reason}')
        sys.exit(0)

    decision = {ALLOW: 'allow', DENY: 'deny'}.get(verdict, 'allow')
    log_action(log_dir, tool_name, tool_input, decision, reason)

    if verdict == DENY:
        print(f'BLOCKED: {reason}{DENY_SUFFIX}', file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
