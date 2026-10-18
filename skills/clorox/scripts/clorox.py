#!/usr/bin/env python3
'''
clorox — one pass over a git project's leftovers. a proven leftover moves into the bin, anything
not proven stays where it is with the rule that kept it, and bin batches past 30 days are deleted.

Commands
--------
    sweep [--in PATH] [--out FILE]
                         move every proven leftover under PATH, in any worktree of the repository,
                         or in the whole repository by default, into the bin; print what moved
                         and what stayed
    empty [--days N]     delete bin batches older than N days (default 30)
    bin                  list what the bin holds for this project
    restore <id>         move one binned item back where it was

Methods
-------
    run :
        run a command with its output captured as text.
    main_root :
        the main worktree of the repository the current directory is in.
    scope_of :
        the worktree, and the part of it, a sweep is confined to.
    walk :
        os.walk that raises at the first folder it cannot read.
    deny_patterns :
        the file-name patterns the user's settings deny reading.
    holds_secret :
        whether a path, or anything under it, matches the deny list.
    is_cache :
        whether a folder is a signed cache or a __pycache__ of .pyc files only.
    same :
        whether two files or folders are identical byte for byte.
    untracked :
        every untracked or ignored path in one worktree.
    path_verdict :
        whether an untracked path is a proven leftover, or the rule that keeps it.
    worktree_list :
        every linked worktree git records.
    busy :
        the processes working in each of a list of paths.
    chatted :
        the worktrees a Claude Code session worked in within the last 5 days.
    unclean :
        why binning a worktree's folder would lose work.
    lost_commits :
        the commits a worktree holds that no branch, tag or remote holds.
    worktree_verdict :
        whether a linked worktree is finished, or the rule that keeps it.
    at_risk :
        the branches whose commits live only here.
    stamp :
        the current UTC time, as a batch folder's name.
    home :
        this project's folder in the bin.
    entries :
        the bin manifest's rows.
    put :
        move one item into a bin batch and record it.
    human :
        a byte count in human units.
    cmd_sweep :
        the sweep command.
    cmd_empty :
        the empty command.
    cmd_bin :
        the bin command.
    cmd_restore :
        the restore command.
    main :
        dispatch on the command named first.
'''

from __future__ import annotations

import datetime as dt
import filecmp
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path



BIN    = Path(os.environ.get('CLOROX_BIN', Path.home() / '.clorox'))
DAYS   = 30
TAG    = b'Signature: 8a477f597d28d172789f06886806bc55'
TWIN   = re.compile(r'^(?P<stem>.+) 2(?P<ext>\.[^/]*)?$')
RECENT = 5 * 86400
SECRET = 'holds a name your settings deny reading, or cannot be read'


# ── git and the disk ──────────────────────────────────────────────────────────

def run(*argv: str, cwd: Path | None = None,
        stdin: str | None = None) -> subprocess.CompletedProcess:
    '''run a command with its output captured as text; a failed exit comes back in returncode.'''
    return subprocess.run(argv, cwd=cwd, input=stdin, capture_output=True, text=True)


def main_root() -> Path:
    '''
    the main worktree of the repository the current directory is in.

    Returns
    -------
    Path
        the folder holding the repository's shared git directory, also from a linked worktree.

    Raises
    ------
    SystemExit
        when the current directory is not inside a git repository.
    '''
    out = run('git', 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if out.returncode:
        raise SystemExit('clorox: not inside a git repository')
    return Path(out.stdout.strip()).parent


def scope_of(root: Path, argv: list[str]) -> tuple[Path, str]:
    '''
    the worktree, and the part of it, a sweep is confined to.

    Parameters
    ----------
    root : Path
        the main worktree.
    argv : list of str
        the sweep's arguments; `--in PATH` names a file or folder in any worktree of the repository.

    Returns
    -------
    tuple
        the worktree holding PATH, main or linked, and PATH relative to it, '' for its root;
        `(root, '')`, the whole repository, without `--in`.

    Raises
    ------
    SystemExit
        when PATH lies outside the main worktree and every linked one.
    '''
    if '--in' not in argv:
        return root, ''
    target = Path(argv[argv.index('--in') + 1]).expanduser().resolve()
    folder = next((p for p in (target, *target.parents) if p.is_dir()), target)
    found  = run('git', '-C', str(folder), 'rev-parse', '--show-toplevel')
    top    = Path(found.stdout.strip()).resolve() if not found.returncode else None
    if top not in {root.resolve()} | {Path(w['path']).resolve() for w in worktree_list(root)}:
        raise SystemExit(f'clorox: {target} is outside {root} and its worktrees')
    rel = target.relative_to(top)
    return root if top == root.resolve() else top, '' if rel == Path('.') else str(rel)


def walk(folder: Path):
    '''
    os.walk that raises at the first folder it cannot read.

    Parameters
    ----------
    folder : Path
        the folder to walk.

    Returns
    -------
    iterator
        os.walk's (top, dirs, files) triples.

    Raises
    ------
    OSError
        while iterating, at the first folder that cannot be read.
    '''
    def fail(err: OSError) -> None:
        raise err
    return os.walk(folder, onerror=fail)


def deny_patterns(root: Path) -> list[str]:
    '''
    file-name patterns the user's settings deny reading, from every settings file that applies.

    Parameters
    ----------
    root : Path
        the main worktree, whose `.claude/settings.json` and `.claude/settings.local.json` apply
        when they exist.

    Returns
    -------
    list of str
        fnmatch patterns such as `.env`, `.env.*` and `*.pem`: the last path part of each
        `Read(...)` deny rule.

    Raises
    ------
    SystemExit
        when the user's settings file, or a project one that exists, cannot be read or parsed,
        since a secret could then be moved.
    '''
    files = [Path.home() / '.claude' / 'settings.json', root / '.claude' / 'settings.json',
             root / '.claude' / 'settings.local.json']
    patterns = []
    for i, f in enumerate(files):
        if i and not f.exists():
            continue
        try:
            deny = json.loads(f.read_text()).get('permissions', {}).get('deny', [])
        except (OSError, ValueError) as exc:
            raise SystemExit(f'clorox: cannot read the deny list in {f}: {exc}') from exc
        for rule in deny:
            m = re.fullmatch(r'Read\((.+)\)', rule)
            if m:
                patterns.append(re.sub(r'^(\./|\*\*/|~/)', '', m[1]).split('/')[-1])
    return sorted({p for p in patterns if p and p != '**'})


def holds_secret(path: Path, patterns: list[str]) -> bool:
    '''
    whether a path, or anything under it, matches the deny list.

    Parameters
    ----------
    path : Path
        the item about to be binned.
    patterns : list of str
        the deny list, from `deny_patterns`.

    Returns
    -------
    bool
        True on a match at any depth, and True when a folder under it cannot be read.
    '''
    if any(fnmatch.fnmatch(path.name, p) for p in patterns):
        return True
    if path.is_dir() and not path.is_symlink():
        try:
            for _top, dirs, files in walk(path):
                if any(fnmatch.fnmatch(n, p) for n in dirs + files for p in patterns):
                    return True
        except OSError:
            return True
    return False


# ── what counts as a leftover ─────────────────────────────────────────────────

def is_cache(path: Path) -> bool:
    '''a folder whose CACHEDIR.TAG opens with the signature, or a __pycache__ of .pyc files only.'''
    if path.is_symlink() or not path.is_dir():
        return False
    try:
        with open(path / 'CACHEDIR.TAG', 'rb') as f:
            if f.read(len(TAG)) == TAG:
                return True
    except OSError:
        pass
    if path.name != '__pycache__':
        return False
    try:
        found = list(os.scandir(path))
    except OSError:
        return False
    return bool(found) and all(e.is_file(follow_symlinks=False) and e.name.endswith('.pyc')
                               for e in found)


def same(a: Path, b: Path) -> bool:
    '''
    whether two files or folders are identical byte for byte at every depth.

    Parameters
    ----------
    a, b : Path
        the two items: an iCloud twin and its original.

    Returns
    -------
    bool
        True when both are files with equal bytes, or both are folders holding the same names
        with equal bytes in every file; a link anywhere, or a failed read, gives False.
    '''
    def listing(top_dir: Path) -> dict[str, Path | None]:
        out = {}
        for top, dirs, files in walk(top_dir):
            for n in dirs + files:
                p = Path(top) / n
                if p.is_symlink():
                    raise OSError(f'a link at {p}')
                out[str(p.relative_to(top_dir))] = p if p.is_file() else None
        return out

    try:
        if a.is_symlink() or b.is_symlink():
            return False
        if a.is_file() and b.is_file():
            return filecmp.cmp(a, b, shallow=False)
        if not (a.is_dir() and b.is_dir()):
            return False
        left, right = listing(a), listing(b)
        return left.keys() == right.keys() and all(
            left[k] is None and right[k] is None
            or left[k] is not None and right[k] is not None
            and filecmp.cmp(left[k], right[k], shallow=False) for k in left)
    except OSError:
        return False


def untracked(root: Path) -> list[str]:
    '''
    every untracked or ignored path git reports in one worktree, outermost only.

    Parameters
    ----------
    root : Path
        the worktree.

    Returns
    -------
    list of str
        paths relative to `root`, sorted, each without a trailing slash.

    Raises
    ------
    SystemExit
        when `git status` fails.
    '''
    out = run('git', '-C', str(root), 'status', '--porcelain=v1', '-z', '--ignored',
              '--untracked-files=normal')
    if out.returncode:
        raise SystemExit(f'clorox: git status failed: {out.stderr.strip()}')
    return sorted(e[3:].rstrip('/') for e in out.stdout.split('\0')
                  if len(e) > 3 and e[:2] in ('??', '!!'))


def path_verdict(root: Path, rel: str, patterns: list[str]) -> tuple[str, str]:
    '''
    whether an untracked path is a proven leftover, or the rule that keeps it.

    Parameters
    ----------
    root : Path
        the worktree the path is in.
    rel : str
        the path, relative to `root`.
    patterns : list of str
        the deny list, from `deny_patterns`.

    Returns
    -------
    tuple of str
        `(kind, '')` for a proven leftover, kind being `cache` or `twin` (an iCloud copy whose
        original exists and matches it); `('', reason)` for one that stays, including a leftover
        that holds a denied name, a twin judged under its original's name too.
    '''
    path = root / rel
    kind, why, original = '', 'not proven a leftover', None
    if is_cache(path):
        kind = 'cache'
    elif twin := TWIN.match(path.name):
        original = path.with_name(twin['stem'] + (twin['ext'] or ''))
        identical = original.exists() and not original.is_symlink() and same(path, original)
        kind, why = ('twin', '') if identical else ('', 'an iCloud twin with no identical original')
    if kind and (holds_secret(path, patterns) or original and holds_secret(original, patterns)):
        return '', SECRET
    return kind, '' if kind else why


# ── worktrees ─────────────────────────────────────────────────────────────────

def worktree_list(root: Path) -> list[dict]:
    '''
    every linked worktree git records, leaving out the main one.

    Parameters
    ----------
    root : Path
        the main worktree.

    Returns
    -------
    list of dict
        one per worktree: `path`, `head`, and the booleans `locked` and `prunable`.

    Raises
    ------
    SystemExit
        when `git worktree list` fails.
    '''
    out = run('git', '-C', str(root), 'worktree', 'list', '--porcelain')
    if out.returncode:
        raise SystemExit(f'clorox: git worktree list failed: {out.stderr.strip()}')
    items = []
    for block in out.stdout.strip().split('\n\n'):
        lines = block.splitlines()
        if not lines or not lines[0].startswith('worktree '):
            continue
        items.append({'path': lines[0][9:],
                      'head': next((ln[5:] for ln in lines if ln.startswith('HEAD ')), ''),
                      'locked': any(ln.startswith('locked') for ln in lines),
                      'prunable': any(ln.startswith('prunable') for ln in lines)})
    return [w for w in items if Path(w['path']) != root]


def busy(paths: list[str]) -> dict[str, list[int]] | None:
    '''
    the processes working in each of a list of paths.

    Parameters
    ----------
    paths : list of str
        the folders to check.

    Returns
    -------
    dict or None
        each path mapped to the sorted pids whose command line names it or whose working
        directory is inside it, this process left out; None when `ps` or `lsof` is not
        installed, `ps` fails or `lsof` prints nothing, since use is then unknown.
    '''
    try:
        ps = run('ps', '-axo', 'pid=,command=')
        lsof = run('lsof', '-a', '-d', 'cwd', '-F', 'pn')
    except OSError:
        return None
    if ps.returncode or not lsof.stdout:
        return None
    cmds = {}
    for line in ps.stdout.splitlines():
        pid, _, cmd = line.strip().partition(' ')
        if pid.isdigit() and int(pid) != os.getpid():
            cmds[int(pid)] = cmd
    cwds, pid = {}, None
    for line in lsof.stdout.splitlines():
        if line.startswith('p'):
            pid = int(line[1:])
        elif line.startswith('n') and pid is not None:
            cwds[pid] = line[1:]
    found = {}
    for p in paths:
        named = re.compile(re.escape(p) + r'(?=$|[/\s"\'])')
        found[p] = sorted(q for q, cmd in cmds.items() if named.search(cmd)
                          or cwds.get(q) == p or cwds.get(q, '').startswith(p + '/'))
    return found


def chatted(paths: list[str]) -> set[str] | None:
    '''
    the worktrees a Claude Code session worked in within the last 5 days.

    Parameters
    ----------
    paths : list of str
        the worktrees' folders.

    Returns
    -------
    set of str or None
        each path that appears followed by `/` or `"`, so `wt` does not match `wt-r37`, in a
        transcript under `~/.claude/projects`, subagents' included, written within RECENT
        seconds; None when such a transcript cannot be read, since use is then unknown.
    '''
    since, found = time.time() - RECENT, set()
    for log in (Path.home() / '.claude' / 'projects').glob('**/*.jsonl'):
        try:
            if log.stat().st_mtime < since:
                continue
            text = log.read_bytes()
        except OSError:
            return None
        found |= {p for p in paths if f'{p}/'.encode() in text or f'{p}"'.encode() in text}
    return found


def unclean(path: str) -> str:
    '''
    why binning a worktree's folder would lose work.

    Parameters
    ----------
    path : str
        the worktree's folder.

    Returns
    -------
    str
        '' when it holds only tracked, unedited files and caches; otherwise the first reason
        found: uncommitted edits, edits git is told not to look at, files git does not track, a
        folder that cannot be read, or a git command that failed.
    '''
    st = run('git', '--no-optional-locks', '-C', path, 'status', '--porcelain=v1',
             '--untracked-files=no', '--ignore-submodules=none')
    if st.returncode:
        return 'git status failed'
    if st.stdout.strip():
        return 'uncommitted edits'
    lv = run('git', '-C', path, 'ls-files', '-v')
    if lv.returncode:
        return 'git ls-files failed'
    if any(ln[:1] == 'S' or ln[:1].islower() for ln in lv.stdout.splitlines()):
        return 'edits git is told not to look at'
    tracked = set(run('git', '-C', path, 'ls-files', '-z').stdout.split('\0'))
    try:
        for top, dirs, files in walk(Path(path)):
            rel = os.path.relpath(top, path)
            pre = '' if rel == '.' else rel + '/'
            if not pre:
                dirs[:] = [d for d in dirs if d != '.git']
                files = [f for f in files if f != '.git']
            dirs[:] = [d for d in dirs if not is_cache(Path(top) / d)]
            links = [d for d in dirs if os.path.islink(os.path.join(top, d))]
            if any(pre + n not in tracked for n in files + links):
                return 'files git does not track'
    except OSError:
        return 'a folder that cannot be read'
    return ''


def lost_commits(root: Path, path: str) -> str:
    '''
    the commits a worktree holds that no branch, tag or remote holds.

    Parameters
    ----------
    root : Path
        the main worktree.
    path : str
        the linked worktree's folder.

    Returns
    -------
    str
        '' when every commit in its HEAD reflog and its own refs (`refs/worktree`, `refs/bisect`
        and `refs/rewritten`) is reachable from a branch, tag or remote; otherwise how many are
        not, or that its history could not be read or checked.
    '''
    history = run('git', '-C', path, 'log', '-g', '--format=%H', 'HEAD')
    own = run('git', '-C', path, 'for-each-ref', '--format=%(objectname)', 'refs/worktree',
              'refs/bisect', 'refs/rewritten')
    if history.returncode or own.returncode:
        return 'its history cannot be read'
    commits = sorted(set(history.stdout.split() + own.stdout.split()))
    if not commits:
        return ''
    out = run('git', '-C', str(root), 'rev-list', '--stdin', '--not', '--branches', '--tags',
              '--remotes', stdin='\n'.join(commits) + '\n')
    if out.returncode:
        return 'its history cannot be checked'
    left = out.stdout.split()
    return f'{len(left)} commit(s) no branch, tag or remote holds' if left else ''


def worktree_verdict(root: Path, w: dict, users: dict[str, list[int]] | None,
                     chats: set[str] | None, patterns: list[str]) -> tuple[str, str]:
    '''
    whether a linked worktree is finished, or the rule that keeps it.

    Parameters
    ----------
    root : Path
        the main worktree.
    w : dict
        one entry from `worktree_list`.
    users : dict or None
        what `busy` returned for every worktree's path.
    chats : set of str or None
        what `chatted` returned for every worktree's path.
    patterns : list of str
        the deny list, from `deny_patterns`.

    Returns
    -------
    tuple of str
        `('worktree', '')` for one that is on disk, outside `.claude/worktrees/`, unlocked,
        unused by any process or by a session within 5 days, clean, merged into main or master,
        whose every commit is held elsewhere, and which holds no name the settings deny reading;
        otherwise `('', reason)`, naming the first check it failed.
    '''
    path = w['path']
    if w['prunable'] or not Path(path).exists():
        return '', 'missing on disk; git prunes its records'
    if '/.claude/worktrees/' in path + '/':
        return '', 'Claude Code removes its own worktrees'
    if w['locked']:
        return '', 'locked'
    if users is None:
        return '', 'processes could not be listed'
    if users.get(path):
        return '', f"in use by pid {', '.join(map(str, users[path]))}"
    if chats is None:
        return '', 'sessions could not be read'
    if path in chats:
        return '', 'a session worked in it within 5 days'
    why = unclean(path)
    if why:
        return '', why
    found  = [r for r in ('main', 'master')
              if not run('git', '-C', str(root), 'rev-parse', '--verify', '--quiet', r).returncode]
    ref    = found[0] if found else None
    merged = ref and w['head'] and run('git', '-C', str(root), 'merge-base', '--is-ancestor',
                                       w['head'], ref).returncode == 0
    if not merged:
        return '', 'its HEAD is not on main'
    why = lost_commits(root, path)
    if why:
        return '', why
    return ('', SECRET) if holds_secret(Path(path), patterns) else ('worktree', '')


def at_risk(root: Path) -> list[tuple[str, str]]:
    '''
    the branches whose commits live only here.

    Parameters
    ----------
    root : Path
        the main worktree.

    Returns
    -------
    list of tuple of str
        (reason, branch) for each branch ahead of its upstream, or with no upstream and not merged
        into main or master.
    '''
    refs = run('git', '-C', str(root), 'for-each-ref', '--format=%(refname:short)\t%(upstream)\t'
               '%(upstream:track)', 'refs/heads').stdout.splitlines()
    found = [r for r in ('main', 'master')
             if not run('git', '-C', str(root), 'rev-parse', '--verify', '--quiet', r).returncode]
    merged = set(run('git', '-C', str(root), 'branch', '--format=%(refname:short)', '--merged',
                     found[0]).stdout.split()) if found else set()
    out = []
    for line in refs:
        name, upstream, track = (line.split('\t') + ['', ''])[:3]
        if 'ahead' in track:
            out.append((f'{track.strip("[]")} of its upstream: commits not pushed', name))
        elif not upstream and name not in merged:
            out.append(('branch with no upstream, not merged into main: commits only here', name))
    return out


# ── the bin ───────────────────────────────────────────────────────────────────

def stamp() -> str:
    '''the current UTC time, as a batch folder's name.'''
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')


def home(root: Path) -> Path:
    '''this project's folder in the bin, named for its main worktree.'''
    return BIN / root.name


def entries(root: Path) -> list[list[str]]:
    '''the manifest's rows: id, batch time, kind, original path, binned path.'''
    m = home(root) / 'manifest.tsv'
    return [r.split('\t') for r in m.read_text().splitlines() if r] if m.exists() else []


def put(root: Path, batch: Path, kind: str, src: Path) -> str:
    '''
    move one item into a bin batch and record it in the manifest.

    Parameters
    ----------
    root : Path
        the main worktree.
    batch : Path
        this sweep's batch folder.
    kind : str
        `cache`, `twin` or `worktree`.
    src : Path
        the item to move.

    Returns
    -------
    str
        the item's 7-character id, which `restore` takes.

    Raises
    ------
    OSError
        when locking a worktree fails, or recording or moving the item fails; a worktree locked
        before a failure is unlocked again.

    Notes
    -----
    a worktree is locked before it moves, so git keeps its records while it sits in the bin. the
    manifest row is written before the move, so nothing sits in the bin unrecorded; a row whose
    item never arrived reads as gone. an item inside the project lands under `repo/`, and one
    outside it under `outside/` at its full path.
    '''
    inside = root in src.parents
    dst    = batch / ('repo' / src.relative_to(root) if inside
                      else Path('outside') / str(src).lstrip('/'))
    qid    = hashlib.sha1(str(dst).encode()).hexdigest()[:7]
    if kind == 'worktree':
        lock = run('git', '-C', str(root), 'worktree', 'lock', '--reason',
                   f'in the clorox bin as {qid}', str(src))
        if lock.returncode:
            raise OSError(f'git worktree lock failed: {lock.stderr.strip()}')
    try:
        home(root).mkdir(parents=True, exist_ok=True)
        with (home(root) / 'manifest.tsv').open('a') as f:
            f.write(f'{qid}\t{batch.name}\t{kind}\t{src}\t{dst}\n')
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    except OSError:
        if kind == 'worktree':
            run('git', '-C', str(root), 'worktree', 'unlock', str(src))
        raise
    return qid


def human(n: float) -> str:
    '''a byte count in B, KB, MB, GB or TB.'''
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024 or unit == 'TB':
            return f'{n:.0f} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024
    return str(n)


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_sweep(argv: list[str]) -> int:
    '''
    the sweep command: bin every proven leftover and report what moved and what stayed.

    Parameters
    ----------
    argv : list of str
        the arguments after `sweep`; `--in PATH` confines it to PATH, and `--out FILE` also
        writes the full list to FILE.

    Returns
    -------
    int
        0.

    Notes
    -----
    the printed report counts what stayed by reason, while the file lists every item. an item
    that fails to move stays, with the error as its reason. a sweep confined to part of the
    repository, a linked worktree's root included, leaves every worktree and branch alone, and
    every sweep bins into the main worktree's folder of the bin.
    '''
    root           = main_root()
    top, scope     = scope_of(root, argv)
    whole          = top == root and not scope
    patterns       = deny_patterns(root)
    before         = shutil.disk_usage(root).free
    batch          = home(root) / stamp()
    binned, stayed = [], []
    for rel in untracked(top):
        if scope and rel != scope and not rel.startswith(scope + '/'):
            continue
        kind, why = path_verdict(top, rel, patterns)
        (binned if kind else stayed).append((kind or why, rel))
    stayed += at_risk(root) if whole else []
    trees = worktree_list(root) if whole else []
    users = busy([w['path'] for w in trees])
    chats = chatted([w['path'] for w in trees]) if trees else set()
    for w in trees:
        kind, why = worktree_verdict(root, w, users, chats, patterns)
        (binned if kind else stayed).append((kind or f'worktree: {why}', w['path']))
    moved = []
    for kind, target in binned:
        src = Path(target) if kind == 'worktree' else top / target
        try:
            moved.append((put(root, batch, kind, src), kind, target))
        except OSError as exc:
            stayed.append((f'could not move: {exc}', target))
    reasons = {}
    for why, target in stayed:
        reasons.setdefault(why, []).append(target)
    head = [f"clorox sweep of {top / scope if scope else top}, {stamp()}",
            f'free space {human(before)} before, {human(shutil.disk_usage(root).free)} after',
            f'binned {len(moved)} item(s) into {batch}' if moved else 'binned nothing']
    head += [f'  {qid}  {kind:<8}  {target}' for qid, kind, target in moved]
    head.append(f'left {len(stayed)} item(s) where they are')
    full = head + [f'  {why}: {t}' for why, ts in sorted(reasons.items()) for t in ts]
    lines = head + [f'  {len(ts):>4}  {why}'
                    for why, ts in sorted(reasons.items(), key=lambda r: -len(r[1]))]
    if '--out' in argv:
        out = Path(argv[argv.index('--out') + 1]).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text('\n'.join(full) + '\n')
        lines.append(f'full list: {out}')
    print('\n'.join(lines))
    return 0


def cmd_empty(argv: list[str]) -> int:
    '''
    the empty command: delete the bin items binned more than N days ago, 30 by default.

    Parameters
    ----------
    argv : list of str
        the arguments after `empty`; `--days N` sets the cutoff.

    Returns
    -------
    int
        0.

    Notes
    -----
    a deleted worktree is unlocked, so git can prune its records. every batch folder binned more
    than N days ago is removed too, whatever it holds; a folder not named for a batch time stays.
    '''
    root   = main_root()
    days   = float(argv[argv.index('--days') + 1]) if '--days' in argv else DAYS
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    gone   = 0
    for _qid, when, kind, src, dst in entries(root):
        at = dt.datetime.strptime(when, '%Y-%m-%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc)
        if at >= cutoff or not os.path.lexists(dst):
            continue
        p = Path(dst)
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
        if kind == 'worktree':
            run('git', '-C', str(root), 'worktree', 'unlock', src)
        gone += 1
    for batch in (home(root).glob('*/') if home(root).exists() else []):
        try:
            at = dt.datetime.strptime(batch.name, '%Y-%m-%dT%H%M%SZ')
        except ValueError:
            continue
        if at.replace(tzinfo=dt.timezone.utc) < cutoff:
            shutil.rmtree(batch)
    print(f'emptied {gone} item(s) binned more than {days:g} days ago' if gone else
          f'nothing in the bin is older than {days:g} days')
    return 0


def cmd_bin(_argv: list[str]) -> int:
    '''
    the bin command: list what the bin holds for this project.

    Parameters
    ----------
    _argv : list of str
        unused.

    Returns
    -------
    int
        0.
    '''
    rows = [r for r in entries(main_root()) if os.path.lexists(r[4])]
    for qid, when, kind, src, _dst in rows:
        print(f'{qid}  {when}  {kind:<8}  {src}')
    if not rows:
        print('the bin holds nothing for this project')
    return 0


def cmd_restore(argv: list[str]) -> int:
    '''
    the restore command: move one binned item back where it was.

    Parameters
    ----------
    argv : list of str
        the arguments after `restore`; the first is the item's id.

    Returns
    -------
    int
        0 once restored; 1 when the id is unknown, the item is gone from the bin, or something
        stands at its original path again.

    Notes
    -----
    a restored worktree is unlocked; it returns to its own path, so git's links to it still hold.
    '''
    root = main_root()
    qid  = argv[0] if argv else ''
    row  = next((r for r in entries(root) if r[0] == qid), None)
    if row is None:
        print(f'no bin entry {qid}')
        return 1
    _qid, _when, kind, src, dst = row
    if not os.path.lexists(dst):
        print(f'{qid}: already restored or emptied')
        return 1
    if os.path.lexists(src):
        print(f'refused: {src} exists again; move it aside first')
        return 1
    Path(src).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(dst, src)
    if kind == 'worktree':
        run('git', '-C', str(root), 'worktree', 'unlock', src)
    print(f'restored {src}')
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
    commands = {'sweep': cmd_sweep, 'empty': cmd_empty, 'bin': cmd_bin, 'restore': cmd_restore}
    if not argv or argv[0] not in commands:
        print(__doc__)
        return 2
    return commands[argv[0]](argv[1:])


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
