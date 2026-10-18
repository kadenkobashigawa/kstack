#!/usr/bin/env python3
'''
stack — the deterministic half of stack-check: the parts of a Claude Code setup, their validity
findings, a frozen copy of them, and a digest of the recent sessions that worked in this repository.

Commands
--------
    check                         validity findings: frontmatter, dead skill links, and references
                                  that resolve nowhere
    freeze <dir>                  copy every part into <dir> under its absolute path, with
                                  FROZEN.txt naming each git repo's HEAD
    digest [--days N] [--project P] [--out F]
                                  the last N days (7) of this workspace's sessions, and of the
                                  lines other workspaces' sessions ran inside this repository:
                                  typed turns, slash commands, skills invoked, SKILL.md reads,
                                  commands run from a skills folder, and agents spawned

Methods
-------
    git :
        a git command's output, or '' when it fails.
    slug :
        a path with every character but letters and digits turned into '-'.
    skip_dir :
        whether a folder is git's own or a cache.
    files_in :
        every file under a folder, sorted, past git's folder and caches.
    memory_dir :
        the auto memory folder for this repository.
    parts :
        every part of the setup, and the skill links that point at nothing.
    cmd_check :
        the check command.
    cmd_freeze :
        the freeze command.
    sessions_dir :
        this workspace's session folder.
    repo_roots :
        every worktree of the repository, as real paths.
    inside :
        whether a working folder lies in one of those worktrees.
    text_of :
        the text of a message's content.
    rows :
        the kept entries of one session log.
    cmd_digest :
        the digest command.
    main :
        dispatch on the command named first.
'''

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path



HOME = Path.home() / '.claude'
TAG = b'Signature: 8a477f597d28d172789f06886806bc55'


# ── where the parts live ──────────────────────────────────────────────────────

def git(*args: str, cwd: Path | None = None) -> str:
    '''a git command's output, stripped, or '' when it fails.'''
    out = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ''


def slug(path: str) -> str:
    '''a path with every character but letters and digits turned into '-'.'''
    return re.sub(r'[^A-Za-z0-9]', '-', path)


def skip_dir(d: Path) -> bool:
    '''a folder that is git's own, or a cache by its signed tag or by being __pycache__.'''
    if d.name in ('.git', '__pycache__'):
        return True
    try:
        with open(d / 'CACHEDIR.TAG', 'rb') as f:
            return f.read(len(TAG)) == TAG
    except OSError:
        return False


def files_in(folder: Path) -> list[Path]:
    '''every file under a folder, sorted, past the folders `skip_dir` names.'''
    out = []
    for top, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not skip_dir(Path(top) / d))
        out += [Path(top) / f for f in sorted(files)]
    return out


def memory_dir(main: Path | None) -> Path | None:
    '''
    the auto memory folder for this repository.

    Parameters
    ----------
    main : Path or None
        the repository's main worktree, or None outside a repository.

    Returns
    -------
    Path
        the first `autoMemoryDirectory` set in the project's local settings, its shared
        settings or the user's, else the folder under `~/.claude/projects/` named for `main`
        (or for the checkout, or the working directory, without one).
    '''
    top = Path(git('rev-parse', '--show-toplevel') or os.getcwd())
    for s in (top / '.claude' / 'settings.local.json', top / '.claude' / 'settings.json',
              HOME / 'settings.json'):
        try:
            set_dir = json.loads(s.read_text()).get('autoMemoryDirectory')
        except (OSError, ValueError):
            continue
        if set_dir:
            return Path(set_dir).expanduser()
    return HOME / 'projects' / slug(str(main or top)) / 'memory'


def parts() -> tuple[dict[str, list[Path]], list[Path]]:
    '''
    every part of the setup, and the skill links that point at nothing.

    Returns
    -------
    tuple
        a dict of label to files, each label one of `skill <folder>`, `agent <file>`,
        `instructions <file>`, `settings <file>` or `memory <file>`; and the dead skill links.

    Notes
    -----
    the parts are the user's and this checkout's skills and agents, the user's CLAUDE.md,
    settings and rules, this checkout's tracked CLAUDE.md and AGENTS.md files, CLAUDE.local.md,
    settings and rules, and the memory folder `memory_dir` names.
    '''
    top         = git('rev-parse', '--show-toplevel')
    common      = git('rev-parse', '--path-format=absolute', '--git-common-dir')
    main        = Path(common).parent if common else None
    found, dead = {}, []
    roots       = [HOME / 'skills'] + ([Path(top) / '.claude' / 'skills'] if top else [])
    for root in roots:
        for d in sorted(root.iterdir()) if root.is_dir() else []:
            if d.is_symlink() and not d.exists():
                dead.append(d)
            elif (d / 'SKILL.md').exists():
                found[f'skill {d}'] = files_in(d)
    for root in [HOME / 'agents'] + ([Path(top) / '.claude' / 'agents'] if top else []):
        for a in sorted(root.glob('*.md')) if root.is_dir() else []:
            found[f'agent {a}'] = [a]
    singles = [HOME / 'CLAUDE.md', HOME / 'settings.json', *sorted((HOME / 'rules').rglob('*.md'))]
    if top:
        t = Path(top)
        listed = git('ls-files', '*CLAUDE.md', '*AGENTS.md', cwd=t).splitlines()
        singles += [t / f for f in listed]
        singles += [t / 'CLAUDE.local.md', t / '.claude' / 'settings.json',
                    t / '.claude' / 'settings.local.json',
                    *sorted((t / '.claude' / 'rules').rglob('*.md'))]
    for s in singles:
        if s.is_file():
            found[f"{'settings' if s.suffix == '.json' else 'instructions'} {s}"] = [s]
    mem = memory_dir(main)
    for m in sorted(mem.glob('*.md')) if mem and mem.is_dir() else []:
        found[f'memory {m}'] = [m]
    return found, dead


# ── check ─────────────────────────────────────────────────────────────────────

def cmd_check(_argv: list[str]) -> int:
    '''
    the check command: print every validity finding, or that there are none.

    Parameters
    ----------
    _argv : list of str
        unused.

    Returns
    -------
    int
        0.

    Notes
    -----
    a finding is a dead skill link, a SKILL.md frontmatter with no name or no description, a
    skill's markdown naming a `references/` or `scripts/` path no skill holds, or a markdown link
    outside code that resolves to nothing.
    '''
    found, dead = parts()
    homes       = [Path(label.split(' ', 1)[1]) for label in found if label.startswith('skill ')]
    out         = [f'{d}: a skill link to {os.readlink(d)}, which does not exist' for d in dead]
    for home in homes:
        head = (home / 'SKILL.md').read_text(errors='replace').split('---')
        front = head[1] if len(head) > 2 else ''
        for key in ('name', 'description'):
            if not re.search(rf'^{key}:\s*\S', front, re.M):
                out.append(f'{home}/SKILL.md: frontmatter has no {key}')
        for f in found[f'skill {home}']:
            if f.suffix != '.md':
                continue
            text = f.read_text(errors='replace')
            for ref in set(re.findall(r'`((?:references|scripts)/[\w./-]+)`', text)):
                if not any((h / ref).exists() for h in [home, *homes]):
                    out.append(f'{f}: names {ref}, which no skill holds')
            prose = re.sub(r'`[^`\n]*`', '', re.sub(r'```.*?```', '', text, flags=re.S))
            for link in re.findall(r'\]\(([^)#\s]+)', prose):
                if link.startswith(('http', 'mailto:')):
                    continue
                target = Path(link).expanduser() if link[0] in '/~' else f.parent / link
                if not target.exists():
                    out.append(f'{f}: a link to {link}, which resolves to nothing')
    print('\n'.join(out) if out else 'no validity findings')
    return 0


# ── freeze ────────────────────────────────────────────────────────────────────

def cmd_freeze(argv: list[str]) -> int:
    '''
    the freeze command: copy every part's files into a folder under their absolute paths.

    Parameters
    ----------
    argv : list of str
        the arguments after `freeze`; the first is the folder.

    Returns
    -------
    int
        0, or 2 when no folder is given.

    Notes
    -----
    `FROZEN.txt` in the folder names each git repository a copied file came from, with its HEAD.
    '''
    if not argv:
        print('usage: stack.py freeze <dir>')
        return 2
    dest         = Path(argv[0]).expanduser()
    found, _dead = parts()
    files        = sorted({f for fs in found.values() for f in fs})
    heads        = {}
    for f in files:
        out = dest / str(f).lstrip('/')
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
        top = git('rev-parse', '--show-toplevel', cwd=f.parent)
        if top and top not in heads:
            heads[top] = git('rev-parse', 'HEAD', cwd=Path(top))
    (dest / 'FROZEN.txt').write_text(''.join(f'{r} {h}\n' for r, h in sorted(heads.items())))
    print(f'froze {len(files)} file(s) from {len(found)} part(s) into {dest}')
    return 0


# ── digest ────────────────────────────────────────────────────────────────────

def sessions_dir(project: str | None = None) -> Path:
    '''
    this workspace's session folder.

    Parameters
    ----------
    project : str, optional
        the project root Claude Code names, which can be a link's path rather than the folder it
        resolves to.

    Returns
    -------
    Path
        the first existing folder under `~/.claude/projects/` named for `project`, the shell's
        `PWD` or the resolved working directory, each path with every character but letters and
        digits replaced by '-'; past 200 characters, the existing folder that begins with the first
        200. With none existing, the one named for the first of those paths.
    '''
    paths = [c for c in (project, os.environ.get('PWD'), os.getcwd()) if c]
    folders = []
    for path in dict.fromkeys(paths):
        name = slug(path)
        folder = HOME / 'projects' / name
        if len(name) > 200 and not folder.exists():
            match = sorted((HOME / 'projects').glob(name[:200] + '*'))
            folder = match[0] if match else folder
        if folder.exists():
            return folder
        folders.append(folder)
    return folders[0]


def repo_roots(project: str | None = None) -> list[str]:
    '''every worktree of the repository `project` (or the working directory) sits in, as real paths.'''
    listed = git('worktree', 'list', '--porcelain', cwd=Path(project) if project else None)
    roots = [os.path.realpath(ln[9:]) for ln in listed.splitlines() if ln.startswith('worktree ')]
    return roots or [os.path.realpath(project or os.getcwd())]


def inside(cwd: str, roots: list[str], memo: dict) -> bool:
    '''whether a working folder, resolved through links, lies in one of the worktrees.'''
    if not cwd:
        return False
    if cwd not in memo:
        real = os.path.realpath(cwd)
        memo[cwd] = any(real == r or real.startswith(r + os.sep) for r in roots)
    return memo[cwd]


def text_of(content) -> str:
    '''the text blocks of a message's content, joined by newlines; a string comes back as it is.'''
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(b.get('text', '') for b in content
                         if isinstance(b, dict) and b.get('type') == 'text')
    return ''


def rows(path: Path, since: str, seen: set[str], where=None):
    '''
    the kept entries of one session log.

    Parameters
    ----------
    path : Path
        the session's `.jsonl` log.
    since : str
        the ISO time before which entries are dropped.
    seen : set of str
        entry ids already kept from any log; each kept id is added, so a replayed entry is kept
        once.
    where : callable, optional
        given an entry, whether to keep it; every entry is kept without one.

    Yields
    ------
    tuple
        (line, timestamp, kind, text), kind being USER for a typed turn, SLASH for a slash
        command, SKILL for a skill invoked, AGENT for an agent spawned, READ for a SKILL.md read,
        or BASH for a command whose first line names a skills folder.

    Notes
    -----
    side chains, compact summaries, meta entries, tool results and system-written turns are
    dropped.
    '''
    with path.open('rb') as f:
        for n, raw in enumerate(f, 1):
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            if d.get('isSidechain') or d.get('isCompactSummary') or d.get('isMeta'):
                continue
            uid, ts = d.get('uuid'), d.get('timestamp') or ''
            if not uid or uid in seen or ts < since or (where and not where(d)):
                continue
            seen.add(uid)
            m = d.get('message') or {}
            if d.get('type') == 'user' and m.get('role') == 'user':
                c = m.get('content')
                results = [b for b in c if isinstance(b, dict)] if isinstance(c, list) else []
                if any(b.get('type') == 'tool_result' for b in results):
                    continue
                t = text_of(c).strip()
                cmd = re.search(r'<command-name>(.*?)</command-name>', t)
                if cmd:
                    args = re.search(r'<command-args>(.*?)</command-args>', t, re.S)
                    yield n, ts, 'SLASH', f"{cmd[1]} {args[1] if args else ''}".strip()
                elif t and not re.match(r'<(system-reminder|local-command|task-notification)', t):
                    yield n, ts, 'USER', t
            elif d.get('type') == 'assistant':
                for b in m.get('content') or []:
                    if not (isinstance(b, dict) and b.get('type') == 'tool_use'):
                        continue
                    name, i = b.get('name'), b.get('input') or {}
                    if name == 'Skill':
                        yield n, ts, 'SKILL', f"{i.get('skill')} {i.get('args', '')}".strip()
                    elif name in ('Agent', 'Task'):
                        yield n, ts, 'AGENT', (f"{i.get('subagent_type')} model={i.get('model')} "
                                               f"{i.get('description')!r}")
                    elif name == 'Read' and str(i.get('file_path', '')).endswith('SKILL.md'):
                        yield n, ts, 'READ', i['file_path']
                    elif name == 'Bash':
                        first = str(i.get('command', '')).splitlines()[:1]
                        if first and '/skills/' in first[0]:
                            yield n, ts, 'BASH', first[0]


def cmd_digest(argv: list[str]) -> int:
    '''
    the digest command: the recent sessions that worked in this repository, one line per kept
    entry.

    Parameters
    ----------
    argv : list of str
        the arguments after `digest`; `--days N` sets how far back (7 by default), `--project P`
        names the project root, and `--out F` writes the digest to F instead of printing it.

    Returns
    -------
    int
        0.

    Notes
    -----
    every log not written to within the window is left out; the current session is kept, since
    it holds the work just finished. reflect says "Do not glob across ~/.cursor/projects/*/. That
    crosses workspace boundaries and reads private chats from unrelated projects"; work on this
    repository is often done from another workspace's session, so other folders are read, and of
    them only the lines whose working folder lies in a worktree of this repository are kept.
    '''
    days        = float(argv[argv.index('--days') + 1]) if '--days' in argv else 7
    project     = argv[argv.index('--project') + 1] if '--project' in argv else None
    start       = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    since       = start.strftime('%Y-%m-%dT%H:%M:%S')
    folder      = sessions_dir(project)
    logs        = sorted((p for p in folder.glob('*.jsonl')
                          if p.stat().st_mtime >= start.timestamp()),
                         key=lambda p: p.stat().st_mtime)
    roots, memo = repo_roots(project), {}
    others      = sorted((p for f in (HOME / 'projects').glob('*') if f.is_dir() and f != folder
                          for p in f.glob('*.jsonl') if p.stat().st_mtime >= start.timestamp()),
                         key=lambda p: p.stat().st_mtime)
    lines, seen, count = [], set(), 0
    for p, where in [(p, None) for p in logs] + [
            (p, lambda d: inside(d.get('cwd') or '', roots, memo)) for p in others]:
        kept = [f'[{ts[:16]}] {p.stem[:8]} L{n} {kind}: {text}'
                for n, ts, kind, text in rows(p, since, seen, where)]
        if kept or where is None:
            lines += [f'######## SESSION {p.stem}'] + kept
            count += 1
    body = '\n'.join(lines) + '\n'
    if '--out' in argv:
        out = Path(argv[argv.index('--out') + 1]).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body)
        print(f'{count} session(s), {len(logs)} from {folder}, into {out}')
    else:
        sys.stdout.write(body)
    return 0


def main(argv: list[str]) -> int:
    '''
    dispatch on the command named first.

    Parameters
    ----------
    argv : list of str
        the command line after the script's name.

    Returns
    -------
    int
        the command's exit code, or 2, with this docstring printed, for an unknown command.
    '''
    commands = {'check': cmd_check, 'freeze': cmd_freeze, 'digest': cmd_digest}
    if not argv or argv[0] not in commands:
        print(__doc__)
        return 2
    return commands[argv[0]](argv[1:])


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
