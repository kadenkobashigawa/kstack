'''
scan — the ledger a scan writes: a blobless clone of each upstream repository, each pin proved
by blob ids, the renames, deletions and commits from pin to head, each citation found at the head
by `locate`, the declared copies diffed at the head, and the files the head adds.

Methods
-------
    clone :
        a blobless clone, fetched again when it exists, with the import paths checked out at the
        head.
    blob_ids, local_blob_ids, prove_pin :
        the pin proved by blob ids.
    name_status, commits :
        the renames, deletions and commits from pin to head, each in one git call.
    diff_copy, additions :
        the copies at the head, and the files the head adds.
    build_ledger :
        the ledger.
'''

from __future__ import annotations

import difflib
import re
import subprocess
from pathlib import Path

import home
from cite import read_lines, text_at
from home import clone_dir, git, tracked_files
from locate import line_map, remap
from model import (Addition, Check, Citation, Commit, Copy, Import, Ledger, Remap, Sources,
                   UpstreamFile)


# ── the clone and the proof ───────────────────────────────────────────────────

def clone(url: str, dest: Path, paths: list[str]) -> Path:
    '''
    a blobless clone of one repository, then a sparse checkout of the import paths at the head,
    so the head files arrive in one batched fetch and no blob is fetched one at a time; a clone
    the run folder already holds is fetched again and moved to the remote's head.
    '''
    if not (dest / '.git').is_dir():
        dest.parent.mkdir(parents=True, exist_ok=True)
        out = subprocess.run(['git', 'clone', '--quiet', '--filter=blob:none', '--no-checkout',
                              url, str(dest)], capture_output=True, text=True)
        if out.returncode:
            raise RuntimeError(f'git clone {url} failed: {out.stderr.strip()}')
    else:
        out = subprocess.run(['git', 'fetch', '--quiet', 'origin', 'HEAD'], cwd=dest,
                             capture_output=True, text=True)
        if out.returncode:
            raise RuntimeError(f'git fetch {url} failed: {out.stderr.strip()}')
        git('update-ref', 'HEAD', 'FETCH_HEAD', cwd=dest)
    if '' not in paths:
        git('sparse-checkout', 'set', '--cone', *sorted(set(paths)), cwd=dest)
    subprocess.run(['git', 'read-tree', '-mu', 'HEAD'], cwd=dest, capture_output=True)
    return dest


def blob_ids(where: Path, rev: str, path: str) -> dict[str, str]:
    '''path inside `path` to blob id at one commit, from `git ls-tree -r`, which reads no blob.'''
    out = git('ls-tree', '-r', '-z', rev, *([path] if path else []), cwd=where, strip=False)
    ids = {}
    for entry in out.split('\0'):
        meta, _, name = entry.partition('\t')
        if meta.split(' ')[1:2] == ['blob']:
            ids[name[len(path):].lstrip('/') if path else name] = meta.split(' ')[2]
    return ids


def local_blob_ids(folder: Path, skip: list[Path]) -> dict[str, str]:
    '''path to `git hash-object` id for the imported copy, past the folders of nested rows.'''
    rel = folder.relative_to(home.REPO).as_posix()
    files = {k: v for k, v in tracked_files(rel).items()
             if not any(s == v.parent or s in v.parents for s in skip)}
    names = sorted(files)
    out = subprocess.run(['git', 'hash-object', '--stdin-paths'], cwd=home.REPO,
                         capture_output=True, text=True,
                         input='\n'.join(str(files[n]) for n in names) + '\n')
    return dict(zip(names, out.stdout.split())) if names else {}


def prove_pin(row: Import, sources: Sources, where: Path) -> list[str]:
    '''
    each file where the row's copy and the tree at its pin differ, empty once proved; a partial
    row proves only the files it holds, and a whole row also fails on a file it lacks, unless
    kstack's .gitignore leaves that file out on purpose.
    '''
    if not git('cat-file', '-t', row.commit, cwd=where) == 'commit':
        return [f'the pin {row.commit[:7]} is not in {row.url}']
    nested = [r for r in sources.imports if r.folder.startswith(row.folder + '/')]
    inside = [r.folder[len(row.folder) + 1:] + '/' for r in nested]
    theirs = {k: v for k, v in blob_ids(where, row.commit, row.path).items()
              if not any(k.startswith(p) for p in inside)}
    mine = local_blob_ids(home.UPSTREAM / row.folder, [home.UPSTREAM / r.folder for r in nested])
    lacking = [f'upstream/{row.folder}/{rel}' for rel in sorted(set(theirs) - set(mine))]
    ignored = set(subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'], cwd=home.REPO,
                                 capture_output=True, text=True,
                                 input='\n'.join(lacking) + '\n').stdout.split('\n'))
    out = []
    for rel in sorted(set(mine) | set(theirs)):
        if rel not in theirs:
            out.append(f'upstream/{row.folder}/{rel}: not in {row.url} at {row.commit[:7]}')
        elif rel not in mine:
            if not row.partial and f'upstream/{row.folder}/{rel}' not in ignored:
                out.append(f'upstream/{row.folder}/{rel}: in {row.url} at {row.commit[:7]}, '
                           'not imported')
        elif mine[rel] != theirs[rel]:
            out.append(f'upstream/{row.folder}/{rel}: differs from {row.commit[:7]}')
    return out


# ── the changes ───────────────────────────────────────────────────────────────

def name_status(where: Path, row: Import) -> list[tuple[str, str, str | None]]:
    '''
    the status, pin path and head path of each file the head changes under a row, from one
    `git diff -M --name-status <pin> HEAD -- <path>`; an added file's pin path is ''.
    '''
    out = git('diff', '-M', '--name-status', '-z', row.commit, 'HEAD', '--', row.path or '.',
              cwd=where, strip=False).split('\0')
    rows, i = [], 0
    while i < len(out) - 1:
        status = out[i][:1]
        if status in 'RC':
            rows.append((status, out[i + 1], out[i + 2]))
            i += 3
        elif status:
            path = out[i + 1]
            rows.append((status, '' if status == 'A' else path, None if status == 'D' else path))
            i += 2
        else:
            i += 1
    return rows


def commits(where: Path, row: Import) -> dict[str, list[Commit]]:
    '''
    each head path under a row to the commits that touched it, oldest first, from one `git log
    --format --name-only`, which reads no blob.
    '''
    out = git('log', '--reverse', '--no-renames', '--format=%x1e%H%x1f%aI%x1f%B%x1f', '--name-only',
              f'{row.commit}..HEAD', '--', row.path or '.', cwd=where, strip=False)
    touched: dict[str, list[Commit]] = {}
    for record in out.split('\x1e')[1:]:
        sha, date, message, names = (record.split('\x1f') + ['', '', '', ''])[:4]
        commit = Commit(sha, date, message.strip())
        for name in names.split('\n'):
            if name.strip():
                touched.setdefault(name.strip(), []).append(commit)
    return touched


def diff_copy(kfolder: str, source: str, where: Path, row: Import, run: Path) -> Copy:
    '''one declared copy against its source at the pin and at the head, with the diff written.'''
    mine = tracked_files(kfolder)
    pin = tracked_files(f'upstream/{source}')
    base = where / row.repo_path(source.split('/', 1)[1] if '/' in source else '')
    head = {p.relative_to(base).as_posix(): p for p in base.rglob('*') if p.is_file()} \
        if base.is_dir() else {}

    def marks(theirs: dict[str, Path]) -> dict[str, str]:
        out = {}
        for rel in sorted(set(mine) | set(theirs)):
            if rel not in theirs:
                out[rel] = 'only-kstack'
            elif rel not in mine:
                out[rel] = 'only-upstream'
            elif mine[rel].read_bytes() != theirs[rel].read_bytes():
                out[rel] = 'differs'
        return out

    at_head = marks(head)
    diff = []
    for rel in at_head:
        a = mine[rel].read_text(errors='replace').splitlines(True) if rel in mine else []
        b = head[rel].read_text(errors='replace').splitlines(True) if rel in head else []
        diff += difflib.unified_diff(a, b, f'a/{kfolder}/{rel}', f'b/{kfolder}/{rel}')
    name = f'copies/{re.sub(r"[^A-Za-z0-9]+", "-", kfolder)}.diff'
    (run / 'copies').mkdir(parents=True, exist_ok=True)
    (run / name).write_text(''.join(diff))
    return Copy(kfolder, source, marks(pin), at_head, name)


def additions(status: list[tuple[str, str, str | None]], row: Import,
              touched: dict[str, list[Commit]]) -> list[Addition]:
    '''
    the files the head adds under a row, SKILL.md files first; for a partial row only SKILL.md
    files, since its other files were never imported, and each file imported now that the head
    renames, at its new path.
    '''
    out = []
    for kind, old, head in status:
        skill = head is not None and head.rsplit('/', 1)[-1] == 'SKILL.md'
        if (kind == 'R' and row.partial
                and (home.UPSTREAM / row.label() / row.local_path(old)).is_file()):
            out.append(Addition(row.folder, row.local_path(head), skill, touched.get(head, []),
                                row.local_path(old)))
        if kind != 'A' or head is None or row.partial and not skill:
            continue
        out.append(Addition(row.folder, row.local_path(head), skill, touched.get(head, [])))
    return sorted(out, key=lambda a: (not a.skill, a.path))


# ── the ledger ────────────────────────────────────────────────────────────────

def build_ledger(run: Path, sources: Sources, citations: list[Citation],
                 checks: dict[str, Check], unparsed: list[tuple[str, int, str]]) -> Ledger:
    '''the ledger: one clone per repository, each pin proved, each cited or copied file read.'''
    up = home.UPSTREAM
    heads, proof, wheres = {}, {}, {}
    for url in dict.fromkeys(r.url for r in sources.imports):
        paths = [r.path for r in sources.imports if r.url == url]
        try:
            wheres[url] = clone(url, clone_dir(run, url), paths)
            heads[url] = git('rev-parse', 'HEAD', cwd=wheres[url])
        except RuntimeError as e:
            heads[url] = ''
            for r in sources.imports:
                if r.url == url:
                    proof[r.folder] = [str(e)]
    status, touched = {}, {}
    for row in sources.imports:
        if row.folder in proof:
            continue
        where = wheres[row.url]
        proof[row.folder] = prove_pin(row, sources, where)
        owned = lambda p: p and sources.owner(row.label(), row.local_path(p)) == row
        status[row.folder] = [s for s in name_status(where, row) if owned(s[2] or s[1])]
        touched[row.folder] = commits(where, row)
    wanted: dict[str, set[str]] = {}
    for c in citations:
        wanted.setdefault(f'{c.label}:{c.path}', set()).add('cited')
    for source in sources.copies.values():
        for rel in tracked_files(f'upstream/{source}'):
            label, _, inside = source.partition('/')
            wanted.setdefault(f'{label}:{inside + "/" if inside else ""}{rel}', set()).add('copied')
    files: dict[str, UpstreamFile] = {}
    for key, why in sorted(wanted.items()):
        label, path = key.split(':', 1)
        row = sources.owner(label, path)
        file = UpstreamFile(key, row.folder if row else '', path, 'unchanged', why)
        files[key] = file
        if row is None or row.folder not in status:
            continue
        rpath = row.repo_path(path)
        for kind, old, new in status[row.folder]:
            if old == rpath:
                file.state = {'D': 'removed', 'R': 'renamed'}.get(kind, 'changed')
                file.head_path = row.local_path(new) if new else None
        seen = {}
        for p in (rpath, row.repo_path(file.head_path) if file.head_path else None):
            for commit in touched[row.folder].get(p or '', []):
                seen.setdefault(commit.sha, commit)
        file.commits = list(seen.values())
        pin = read_lines(up / label / path) or []
        head = read_lines(wheres[row.url] / row.repo_path(file.head_path)) \
            if file.head_path else None
        file.lines = line_map(pin, head) if head is not None else {n: None for n in
                                                                    range(1, len(pin) + 1)}
    remaps = {}
    for c in citations:
        file = files[f'{c.label}:{c.path}']
        file.citations.append(c.id)
        row = sources.owner(c.label, c.path)
        pin = read_lines(up / c.label / c.path) or []
        if row is None or proof.get(row.folder):
            remaps[c.id] = Remap(c.id, 'blocked', 'none', None, (), text_at(pin, c.spans), '', 0.0)
            continue
        where = wheres[row.url]
        head = read_lines(where / row.repo_path(file.head_path)) if file.head_path else None
        remaps[c.id] = remap(c, file, checks[c.id], pin, head, where, row)
    copies = []
    for kfolder, source in sources.copies.items():
        row = sources.owner(*source.split('/', 1))
        if row and row.url in wheres:
            copies.append(diff_copy(kfolder, source, wheres[row.url], row, run))
    added, removed = [], []
    for row in sources.imports:
        if row.folder not in status:
            continue
        added += additions(status[row.folder], row, touched[row.folder])
        for kind, old, _ in status[row.folder]:
            local = row.local_path(old) if old else ''
            if kind in 'DR' and (up / row.label() / local).is_file():
                removed.append(f'{row.label()}/{local}')
    return Ledger(git('rev-parse', 'HEAD', cwd=home.REPO), sources, heads, proof, files,
                  {c.id: c for c in citations}, checks, remaps, copies, added, removed, unparsed)
