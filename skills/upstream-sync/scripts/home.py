'''
home — where things live: the kstack checkout and its upstream/ folder, the run folder and its
clones, the files git tracks, the run files written and read back, and upstream/sources.json
with the pins and copies it declares.

`REPO`, `UPSTREAM`, `SOURCES`, `README` and `NOTICE` name the checkout this script sits in until
`use_repo` points them at another; every module reads them here, as `home.REPO`, at call time.

Methods
-------
    git :
        a git command's output, or '' when it fails.
    use_repo :
        point every path at the kstack checkout named by `--repo`.
    inside :
        whether a path resolves to a folder or somewhere below it.
    run_dir, clone_dir :
        the run folder, created unless asked not to, refused inside the repository, and one clone
        inside it.
    tracked_text, tracked_files :
        every markdown file git tracks outside upstream/, and every file git tracks in a folder.
    save, load :
        one run file written as JSON, and the ledger read back.
    read_sources :
        upstream/sources.json read and checked for shape.
    check_prose :
        each row whose short commit NOTICE or upstream/README.md leaves out.
    check_copies :
        each file where a declared copy differs from its source.
'''

from __future__ import annotations

import dataclasses
import json
import re
import subprocess
import sys
from pathlib import Path

from model import Import, Ledger, Sources, decode


REPO     = Path(__file__).resolve().parents[3]
UPSTREAM = REPO / 'upstream'
SOURCES  = UPSTREAM / 'sources.json'
README   = UPSTREAM / 'README.md'
NOTICE   = REPO / 'NOTICE'


def git(*args: str, cwd: Path | None = None, strip: bool = True) -> str:
    '''a git command's output, stripped unless `strip` is off, or '' when it fails.'''
    out = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if out.returncode:
        return ''
    return out.stdout.strip() if strip else out.stdout


def use_repo(path: Path) -> None:
    '''point every path this module names at another kstack checkout, for `--repo`.'''
    global REPO, UPSTREAM, SOURCES, README, NOTICE
    REPO = path.resolve()
    UPSTREAM, NOTICE = REPO / 'upstream', REPO / 'NOTICE'
    SOURCES, README = UPSTREAM / 'sources.json', UPSTREAM / 'README.md'


def inside(root: Path, path: Path) -> bool:
    '''whether `path`, resolved, is `root`, resolved, or lies below it.'''
    root, path = root.resolve(), path.resolve()
    return path == root or root in path.parents


def run_dir(arg: str, create: bool = True) -> Path:
    '''
    the run folder named on the command line, created unless `create` is off, and refused inside
    the repository.
    '''
    run = Path(arg).expanduser().resolve()
    if inside(REPO, run):
        sys.exit(f'sync: the run folder {run} is inside the repository {REPO}; use mktemp -d')
    if create:
        run.mkdir(parents=True, exist_ok=True)
    return run


def clone_dir(run: Path, url: str) -> Path:
    '''where one repository's clone sits inside the run folder.'''
    return run / 'clones' / re.sub(r'[^A-Za-z0-9]+', '-', url).strip('-')


def tracked_text() -> list[Path]:
    '''
    every markdown file (`*.md`) git tracks outside upstream/, which is where citations live; a
    citation-shaped string in code, such as a test fixture, is never read.
    '''
    names = git('ls-files', '-z', '--', '*.md', cwd=REPO, strip=False).split('\0')
    return [REPO / n for n in sorted(names)
            if n and not n.startswith('upstream/') and (REPO / n).is_file()]


def tracked_files(folder: str) -> dict[str, Path]:
    '''each file git tracks under a repository folder, by its path inside that folder.'''
    names = git('ls-files', '-z', '--', folder, cwd=REPO, strip=False).split('\0')
    return {n[len(folder) + 1:]: REPO / n for n in names if n and (REPO / n).is_file()}


def _plain(obj):
    '''an object as JSON holds it: dataclasses as objects, sets as sorted lists.'''
    if dataclasses.is_dataclass(obj):
        return {f.name: _plain(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, (set, frozenset)):
        return sorted(_plain(x) for x in obj)
    if isinstance(obj, (list, tuple)):
        return [_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    return obj


def save(run: Path, name: str, obj) -> Path:
    '''one run file written as JSON, dataclasses as objects and sets as sorted lists.'''
    path = run / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_plain(obj), indent=1, ensure_ascii=False) + '\n')
    return path


def load(run: Path, name: str) -> Ledger:
    '''the ledger, the one run file read back, from `name` in the run folder, by `decode`.'''
    return decode(Ledger, json.loads((run / name).read_text()))


# ── pins and copies ───────────────────────────────────────────────────────────

def read_sources(path: Path = SOURCES) -> Sources:
    '''
    upstream/sources.json read, failing on a missing field, a commit that is not 40 hex, a folder
    that is not under upstream/, or a copy whose source is not.
    '''
    if not path.is_file():
        raise ValueError(f'{path} is missing')
    data = json.loads(path.read_text())
    rows = []
    for n, row in enumerate(data.get('imports') or []):
        missing = [k for k in ('folder', 'url', 'path', 'commit', 'date') if k not in row]
        if missing:
            raise ValueError(f'{path.name}: import {n} has no {", ".join(missing)}')
        if not re.fullmatch(r'[0-9a-f]{40}', row['commit']):
            raise ValueError(f'{path.name}: {row["folder"]}: commit {row["commit"]} is not 40 hex')
        if '..' in row['folder'].split('/') or not (UPSTREAM / row['folder']).is_dir():
            raise ValueError(f'{path.name}: {row["folder"]} is not a folder under upstream/')
        rows.append(Import(row['folder'], row['url'], row['path'].strip('/'), row['commit'],
                           row['date'], bool(row.get('partial', False))))
    if not rows:
        raise ValueError(f'{path.name} names no import')
    copies = data.get('copies') or {}
    for kfolder, source in copies.items():
        if '..' in source.split('/') or not (UPSTREAM / source).is_dir():
            raise ValueError(f'{path.name}: the source of {kfolder}, {source}, '
                             'is not under upstream/')
    return Sources(rows, dict(copies))


def check_prose(sources: Sources, readme: str, notice: str) -> list[str]:
    '''one finding per row whose short commit, the first 7 hex, NOTICE or the README leaves out.'''
    out = []
    for row in sources.imports:
        for name, text in (('NOTICE', notice), ('upstream/README.md', readme)):
            if row.commit[:7] not in text:
                out.append(f'{name} does not name the pin of upstream/{row.folder}, '
                           f'{row.commit[:7]}')
    return out


def check_copies(sources: Sources) -> list[str]:
    '''one finding per file where a declared copy and its upstream/ source differ in bytes.'''
    out = []
    for kfolder, source in sources.copies.items():
        mine, theirs = tracked_files(kfolder), tracked_files(f'upstream/{source}')
        for rel in sorted(set(mine) | set(theirs)):
            if rel not in theirs:
                out.append(f'{kfolder}/{rel}: in the copy, not in upstream/{source}')
            elif rel not in mine:
                out.append(f'{kfolder}/{rel}: in upstream/{source}, missing from the copy')
            elif mine[rel].read_bytes() != theirs[rel].read_bytes():
                out.append(f'{kfolder}/{rel}: differs from upstream/{source}/{rel}')
    return out
