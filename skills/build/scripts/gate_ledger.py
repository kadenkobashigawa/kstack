"""
gate_ledger — the git facts and the ledger every gate.py command reads and writes: the branch, its head
and its patch-id, the ledger's rows, the receipts that hold a lane's output, and the lane
checkouts beside the branch's worktree. gate.py's help is the source of truth for what they mean.
"""

from __future__ import annotations

import contextlib
import csv
import datetime
import fcntl
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse


COLUMNS = ['ts', 'head', 'patch', 'kind', 'name', 'model', 'result', 'cmd', 'note', 'main',
           'out', 'sha256', 'by', 'exit', 'covers', 'premise', 'tree', 'lane']
RESULTS = {
    'lane':       {'PASS', 'ISSUES', 'BLOCKED', 'gap', 'NO-RUNTIME'},
    'round':      {'full', 'minor', 'wording', 'void'},
    'finding':    {'blocks', 'follow-up', 'dropped', 'fixed'},
    'live-check': {'declared', 'VERIFIED', 'UNREACHED'},
}

#the exit column of a gates run whose command never started, as when its program is missing...
NOT_RUN = 'none'
MODELS = ('opus', 'sonnet', 'haiku', 'fable')

#a ledger written before the three buckets, or a brief that still names the five, keeps working...
OLD_BUCKETS = {'act-on': 'blocks', 'consider': 'follow-up', 'queue': 'follow-up',
               'nit': 'follow-up', 'dismissed': 'dropped'}

#gate.md's finding ID, R<round>-<n>, which an agent's name never takes...
FINDING_ID = re.compile(r'R\d+-', re.IGNORECASE)

LANE_NAME  = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*')


class Refuse(Exception):
    """A refusal: run() prints it after `gate: ` and exits 2."""


def git_bytes(*args: str, cwd: str | None = None, stdin: bytes | None = None) -> bytes:
    """git's stdout as bytes. A failing git prints its own message and exits with its code."""
    p = subprocess.run(['git', *args], cwd=cwd, input=stdin, capture_output=True)
    if p.returncode:
        sys.stderr.write(f'gate: git {args[0]} failed\n{text(p.stderr)}')
        sys.exit(p.returncode)
    return p.stdout


def text(raw: bytes) -> str:
    """Bytes git wrote as text. A name or path that is not UTF-8 keeps its bytes."""
    return raw.decode('utf-8', 'surrogateescape')


def git(*args: str, cwd: str | None = None, stdin: str | None = None) -> str:
    """git's stdout as text, stripped."""
    data = None if stdin is None else stdin.encode()
    return text(git_bytes(*args, cwd=cwd, stdin=data)).strip()


def main_ref() -> str:
    return os.environ.get('GATE_MAIN', 'main')


def patch_of(rev: str) -> tuple[str, str]:
    """The merge base of `rev` with main, and the verbatim patch-id of the diff from it to `rev`.

    Notes
    -----
    --verbatim keeps whitespace, so a re-indent, which can change what Python or YAML does, is a
    new patch, while line numbers still drop out, so a rebase that only moves the hunks keeps it.
    """
    base = git('merge-base', main_ref(), rev)

    #keep the diff as bytes, as a shell pipe does, since text mode turns a lone CR into a newline...
    pid  = text(git_bytes('patch-id', '--verbatim', stdin=git_bytes('diff', base, rev))).split()
    return base, pid[0] if pid else 'empty'


def where() -> dict:
    """The branch, its head, its merge base with main and its verbatim patch-id."""
    head        = git('rev-parse', 'HEAD')
    base, patch = patch_of(head)
    return {'branch': branch(), 'head': head, 'base': base, 'patch': patch}


def branch() -> str:
    """The checked-out branch's full name, or 'HEAD' when HEAD is detached."""

    #read the full ref, since a short name is `heads/x` when a tag `x` exists...
    p = subprocess.run(['git', 'symbolic-ref', '-q', 'HEAD'], capture_output=True)
    ref = text(p.stdout).strip()
    return ref[len('refs/heads/'):] if ref.startswith('refs/heads/') else 'HEAD'


def ledger_path(branch: str) -> str:
    """`branch`'s ledger, in this worktree's own git folder, which goes when the worktree does."""

    #percent-encode every byte but letters, digits and `_.-~`, so no two branches share a file...
    name   = urllib.parse.quote(branch.encode('utf-8', 'surrogateescape'), safe='') + '.tsv'
    folder = os.path.join(git('rev-parse', '--absolute-git-dir'), 'kstack-gate')
    path   = os.path.join(folder, name)
    stem   = branch.replace('/', '__')
    old    = os.path.join(folder, stem + '.tsv')

    #the old name is also branch `a__b`'s own, so a ledger moves only when no such branch lives...
    ref  = ['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{stem}']
    live = subprocess.run(ref, capture_output=True).returncode == 0
    if '/' in branch and not live and not os.path.exists(path) and os.path.exists(old):
        os.replace(old, path)
    return path


def read_rows(path: str) -> list[dict]:
    """The ledger's rows. A ledger not yet written, or deleted by `land`, has none.

    Notes
    -----
    A ledger written before a column existed has a shorter header, and its later rows may carry
    the new columns past it, so a header that starts COLUMNS reads as all of COLUMNS.
    """
    try:
        with open(path, newline='') as f:
            lines = [ln for ln in csv.reader(f, delimiter='\t') if ln]
    except FileNotFoundError:
        return []
    if not lines:
        return []
    head  = lines[0]
    names = COLUMNS if head == COLUMNS[:len(head)] else head
    rows  = []
    for ln in lines[1:]:
        r = {n: '' for n in COLUMNS}
        r.update(zip(names, ln))
        if r['kind'] == 'finding':
            r['result'] = OLD_BUCKETS.get(r['result'], r['result'])
        rows.append(r)
    return rows


def one_line(s: str) -> str:
    return ' '.join(s.split())


def branch_at() -> dict:
    """where(), for a row's branch. A detached HEAD, main's worktree or old git refuses."""
    at = where()
    if at['branch'] == 'HEAD':
        raise Refuse('HEAD is detached; run this from the branch being gated')
    dirs = git('rev-parse', '--path-format=absolute', '--git-dir', '--git-common-dir').split('\n')
    if len(dirs) != 2 or not all(map(os.path.isabs, dirs)):
        raise Refuse('git gave no two absolute git folders, so whether this is the main '
                     'worktree is unknown; --path-format needs git 2.31 or later')
    if dirs[0] == dirs[1]:
        raise Refuse("this is the main worktree, whose git folder is the repository's own and "
                     "outlives a deleted branch; run this from the branch's linked worktree")
    return at


def append(path: str, row: dict) -> None:
    """Append `row` to the ledger at `path`, stamped now, with the header first in a new ledger."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts  = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    row = {**{n: '' for n in COLUMNS}, **row, 'ts': ts, 'main': git('rev-parse', main_ref())}
    with open(path, 'a', newline='') as f:

        #one writer at a time, so the size read below is the file this row lands in...
        fcntl.flock(f, fcntl.LOCK_EX)
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        if not os.fstat(f.fileno()).st_size:
            w.writerow(COLUMNS)
        w.writerow([one_line(row[n]) for n in COLUMNS])


def family(kind: str, model: str, gates: bool = False) -> str:
    """`model` as its family, lowercased; root only for the gates lane, and nothing else."""
    if not model.strip():
        raise Refuse(f'a {kind} row names its model (--model)')
    model = one_line(model).lower()
    if model not in MODELS and not (gates and model == 'root'):
        raise Refuse(f'a {kind} row names its model family, one of {", ".join(MODELS)}; only the '
                     'gates lane, which the root runs itself, is recorded as root')
    return model


@contextlib.contextmanager
def worktree_lock(shared: bool = False):
    """Hold the repository's lock on its worktree list while git adds, removes or lists one.

    Notes
    -----
    git keeps every worktree's admin folder in the repository's own git folder, and one `git
    worktree add` reads another's half-made folder and fails, so gates runs started side by side
    take turns at add and remove, under this lock, and run their commands in parallel.
    """
    common = git('rev-parse', '--path-format=absolute', '--git-common-dir')
    with open(os.path.join(common, 'kstack-gate-worktrees.lock'), 'a') as f:
        fcntl.flock(f, fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def worktrees() -> list[dict]:
    """Each worktree git lists: its real path, and its branch, or '' when it is detached."""
    out: list[dict] = []
    with worktree_lock(shared=True):
        listed = git('worktree', 'list', '--porcelain')
    for line in listed.splitlines():
        if line.startswith('worktree '):
            out.append({'path': os.path.realpath(line[len('worktree '):]), 'branch': ''})
        elif line.startswith('branch refs/heads/') and out:
            out[-1]['branch'] = line[len('branch refs/heads/'):]
    return out


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def receipt(out: str) -> tuple[str, str]:
    """`out`'s real path and sha256, once it is a file with content outside every lane checkout."""
    if not out.strip():
        raise Refuse('a lane row keeps the file holding its full output (--out)')
    path = os.path.realpath(out)
    if not os.path.isfile(path) or not os.path.getsize(path):
        raise Refuse(f'{out} is missing or empty; --out names the file holding the lane\'s full '
                     'output, written before the row')

    #the deepest worktree holding the file decides, since worktrees can sit inside another...
    top  = os.path.realpath(git('rev-parse', '--show-toplevel'))
    held = [w for w in worktrees() if path.startswith(w['path'] + os.sep)]
    if held:
        w = max(held, key=lambda w: len(w['path']))
        if w['path'] == top or not w['branch']:
            raise Refuse(f'{out} is inside the worktree {w["path"]}, which a commit or a lane\'s '
                         'removal can take; keep evidence outside the branch\'s worktree and '
                         'every lane checkout')
    return path, sha256(path)


def receipt_state(r: dict) -> str:
    """'' for a row with no receipt, else 'matches', 'gone' or 'changed' for its output file."""
    if not r.get('out'):
        return ''
    if not os.path.isfile(r['out']):
        return 'gone'
    return 'matches' if sha256(r['out']) == r['sha256'] else 'changed'


def evidence_file(ledger: str, stem: str, body: str) -> str:
    """A new file holding `body`, in the folder beside the ledger that holds gate.py's own output.

    Notes
    -----
    The folder is in the worktree's git folder, like the ledger, so no commit picks it up, no lane
    checkout holds it, and removing the worktree removes it.
    """
    folder = ledger[:-len('.tsv')] + '.runs'
    os.makedirs(folder, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix=f'{stem}-', suffix='.txt', dir=folder)
    with os.fdopen(fd, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(body)
    return path


def latest(rows: list[dict], kind: str, patch: str | None = None) -> dict[str, dict]:
    """The last row of `kind` at `patch`, or at any patch, for each name. A later row supersedes."""
    out: dict[str, dict] = {}
    for r in rows:
        if r['kind'] == kind and patch in (None, r['patch']):
            out[r['name']] = r
    return out


def changed(base: str, rev: str, *spec: str) -> set[str]:
    """The paths `rev` changes since `base`, both sides of a rename, within pathspecs `spec`."""

    #run from the top, so a pathspec names the same paths from any folder of the worktree...
    top = git('rev-parse', '--show-toplevel')
    raw = git_bytes('diff', '--name-only', '--no-renames', '-z', base, rev, '--', *spec, cwd=top)
    return {text(p) for p in raw.split(b'\0') if p}


def main_worktree() -> str | None:
    """The worktree that has main checked out, if one does."""
    for w in worktrees():
        if w['branch'] == main_ref():
            return w['path']
    return None


def lanes_dir() -> str:
    """The folder beside this worktree that holds its lanes' checkouts: <worktree>.lanes."""
    return os.path.realpath(git('rev-parse', '--show-toplevel')) + '.lanes'


def lanes_out() -> list[str]:
    """The lane checkouts git lists in this worktree's lane folder."""
    folder = lanes_dir() + os.sep
    return sorted(w['path'] for w in worktrees() if w['path'].startswith(folder))


def lane_path(name: str) -> str:
    if not LANE_NAME.fullmatch(name):
        raise Refuse(f'{name!r} is not a lane name: one path segment of letters, digits, '
                     '`.`, `_` and `-`, starting with a letter or digit')
    return os.path.join(lanes_dir(), name)
