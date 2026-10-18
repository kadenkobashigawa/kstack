#!/usr/bin/env python3
"""
test_proof — runs proof.py in throwaway git repos and checks that its tree compare passes a cosmetic
edit, fails a behaviour change, and keeps each baseline until it is cleared.

Run it with `python3 test_proof.py`. It needs git. It makes one temporary folder, runs proof.py
there with HOME inside it and no global or system git config, then removes it. The exit code is the
number of failed checks.

K1 to K11 hold the baselines. K1 fails a deleted call. K2 refuses a second snapshot over an edited
file and keeps the first baseline. K3 lets a second snapshot of an unedited file through. K4 keeps a
repo's baseline when another repo snapshots and clears, and K5 does the same for a linked worktree.
K6 clears the baselines, so verify then finds no snapshot. K7 fails verify with no snapshot. K8
exits 2 outside a git repo. K9 exits 2 with a usage for a command it doesn't know, for clear given
files, and for snapshot given none. K10 keeps the baselines out of the working tree. K11 keeps a
baseline for each of two `__init__.py` files in different folders, since a baseline mirrors its
file's whole path.

C1 to C7 hold the compare. C1 proves a reworded module and function docstring and a new comment
unchanged, which also holds that line numbers stay out of the compare. C2 does the same for a class
docstring, C3 for an async function's, and C4 for a function whose whole body is its docstring, with
a `pass` added after it. C5 fails two swapped statements. C6 fails a changed string statement that
is not a docstring. C7 fails a file that no longer parses, with a verdict and no traceback.

L1 to L3 hold files with no parser here: L1 names an unchanged .css and .js NO PARSER at snapshot
and verify and leaves them out of the count, L2 leaves the exit code to the python files when one of
them is edited, and L3 still fails a changed python file beside them. F1 fails a file deleted after
its snapshot as MISSING, and F2 refuses a snapshot of a missing file, naming it, with no traceback.

M1 pins the measured claim in SKILL.md: dropping an `os.getenv(...)` call from a function that still
uses `os` leaves `ruff check` (when ruff is on PATH) and `py_compile` passing, and only verify
catches it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HERE    = Path(__file__).resolve().parent
SCRIPT  = HERE.parent / 'scripts' / 'proof.py'
RESULTS = []
CALL    = 'import os\n\n\ndef f():\n    os.getenv("X")\n    return os.sep\n'
NOCALL  = 'import os\n\n\ndef f():\n    return os.sep\n'


def check(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


class Repo:
    """a git repo with one commit, where proof.py runs with an isolated HOME and git config."""

    def __init__(self, tmp: Path, name: str):
        self.tmp  = tmp
        self.path = tmp / name
        self.path.mkdir(parents=True)
        self.env  = {**{k: v for k, v in os.environ.items() if not k.startswith('GIT_')},
                     'HOME': str(tmp), 'GIT_CONFIG_NOSYSTEM': '1',
                     'GIT_CONFIG_GLOBAL': str(tmp / 'gitconfig'),
                     'GIT_CEILING_DIRECTORIES': str(tmp)}
        self.git('init', '-q', '-b', 'main')
        self.write('seed.txt', 'seed\n')
        self.git('add', 'seed.txt')
        self.git('commit', '-q', '-m', 'seed')

    def git(self, *args: str) -> str:
        return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                              cwd=self.path, env=self.env, check=True, capture_output=True,
                              text=True).stdout.strip()

    def write(self, name: str, text: str) -> None:
        (self.path / name).write_text(text)

    def proof(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd or self.path,
                              env=self.env, capture_output=True, text=True, timeout=60)


def said(done: subprocess.CompletedProcess) -> str:
    return (done.stdout + done.stderr).strip()[-160:]


# ── the baselines ─────────────────────────────────────────────────────────────

def baseline_checks(tmp: Path) -> None:
    repo = Repo(tmp, 'k1')
    repo.write('x.py', CALL)
    repo.proof('snapshot', 'x.py')
    repo.write('x.py', NOCALL)
    done = repo.proof('verify', 'x.py')
    check('K1 a deleted call fails verify', done.returncode == 1
          and 'BEHAVIOUR CHANGED  x.py' in done.stdout, said(done))

    repo = Repo(tmp, 'k2')
    repo.write('x.py', CALL)
    repo.write('other.py', 'y = 1\n')
    repo.proof('snapshot', 'x.py')
    repo.write('x.py', NOCALL)
    again = repo.proof('snapshot', 'x.py', 'other.py')
    done  = repo.proof('verify', 'x.py')
    check('K2 a second snapshot over an edited file is refused, and the first baseline holds',
          again.returncode == 2 and 'x.py' in again.stderr and done.returncode == 1
          and 'BEHAVIOUR CHANGED' in done.stdout, f'{said(again)} / {said(done)}')

    repo = Repo(tmp, 'k3')
    repo.write('x.py', CALL)
    first  = repo.proof('snapshot', 'x.py')
    second = repo.proof('snapshot', 'x.py')
    done   = repo.proof('verify', 'x.py')
    check('K3 a second snapshot of an unedited file goes through',
          first.returncode == 0 and second.returncode == 0 and done.returncode == 0,
          f'{said(second)} / {said(done)}')

    a, b = Repo(tmp, 'k4a'), Repo(tmp, 'k4b')
    a.write('x.py', CALL)
    b.write('x.py', 'z = 2\n')
    a.proof('snapshot', 'x.py')
    b.proof('snapshot', 'x.py')
    b.proof('clear')
    a.write('x.py', NOCALL)
    done = a.proof('verify', 'x.py')
    check("K4 another repo's snapshot and clear leave this repo's baseline",
          done.returncode == 1 and 'BEHAVIOUR CHANGED' in done.stdout, said(done))

    repo = Repo(tmp, 'k5')
    repo.write('x.py', CALL)
    repo.git('worktree', 'add', '-q', str(tmp / 'k5-wt'))
    repo.proof('snapshot', 'x.py')
    repo.proof('clear', cwd=tmp / 'k5-wt')
    repo.write('x.py', NOCALL)
    done = repo.proof('verify', 'x.py')
    check("K5 a linked worktree's clear leaves the main worktree's baseline",
          done.returncode == 1 and 'BEHAVIOUR CHANGED' in done.stdout, said(done))

    repo = Repo(tmp, 'k6')
    repo.write('x.py', CALL)
    repo.proof('snapshot', 'x.py')
    cleared = repo.proof('clear')
    done    = repo.proof('verify', 'x.py')
    check('K6 clear drops the baselines, so verify finds no snapshot',
          cleared.returncode == 0 and done.returncode == 1 and 'NO SNAPSHOT  x.py' in done.stdout,
          said(done))

    repo = Repo(tmp, 'k7')
    repo.write('x.py', CALL)
    done = repo.proof('verify', 'x.py')
    check('K7 verify with no snapshot fails', done.returncode == 1
          and 'NO SNAPSHOT  x.py' in done.stdout, said(done))

    outside = tmp / 'k8'
    outside.mkdir()
    (outside / 'x.py').write_text(CALL)
    done = repo.proof('snapshot', 'x.py', cwd=outside)
    check('K8 outside a git repo proof.py exits 2', done.returncode == 2
          and 'Traceback' not in done.stderr, said(done))

    bad   = repo.proof('nonsense', 'x.py')
    extra = repo.proof('clear', 'x.py')
    bare  = repo.proof('snapshot')
    check('K9 an unknown command, clear with files and snapshot with none each exit 2',
          bad.returncode == extra.returncode == bare.returncode == 2
          and all('usage' in d.stderr for d in (bad, extra, bare)),
          f'{bad.returncode} {extra.returncode} {bare.returncode}')

    repo   = Repo(tmp, 'k10')
    repo.write('x.py', CALL)
    status = repo.git('status', '--porcelain', '--untracked-files=all')
    repo.proof('snapshot', 'x.py')
    after  = repo.git('status', '--porcelain', '--untracked-files=all')
    check('K10 a snapshot adds nothing to the working tree', after == status, after)

    repo = Repo(tmp, 'k11')
    (repo.path / 'a').mkdir()
    (repo.path / 'b').mkdir()
    repo.write('a/__init__.py', 'x = 1\n')
    repo.write('b/__init__.py', 'y = 2\n')
    snap = repo.proof('snapshot', 'a/__init__.py', 'b/__init__.py')
    same = repo.proof('verify', 'a/__init__.py', 'b/__init__.py')
    repo.write('a/__init__.py', 'x = 3\n')
    one  = repo.proof('verify', 'a/__init__.py', 'b/__init__.py')
    check('K11 two files of one name in different folders keep a baseline each',
          snap.returncode == 0 and same.returncode == 0 and '2/2 proved unchanged' in same.stdout
          and one.returncode == 1 and 'BEHAVIOUR CHANGED  a/__init__.py' in one.stdout
          and 'b/__init__.py' not in one.stdout, f'{said(same)} / {said(one)}')


# ── the compare ───────────────────────────────────────────────────────────────

def edit_proves(tmp: Path, name: str, before: str, after: str) -> subprocess.CompletedProcess:
    """snapshot a file, rewrite it, and verify it, in a fresh repo."""
    repo = Repo(tmp, name)
    repo.write('m.py', before)
    repo.proof('snapshot', 'm.py')
    repo.write('m.py', after)
    return repo.proof('verify', 'm.py')


def compare_checks(tmp: Path) -> None:
    done = edit_proves(tmp, 'c1',
                       '"""mod."""\n\n\ndef f():\n    """fn."""\n    return 1\n',
                       '"""module, reworded."""\n\n\n#a comment...\n\n\ndef f():\n'
                       '    """the function, reworded\n\n    over two lines."""\n    return 1\n')
    check('C1 a reworded module and function docstring, and a new comment, prove unchanged',
          done.returncode == 0 and '1/1 proved unchanged' in done.stdout, said(done))

    done = edit_proves(tmp, 'c2', 'class A:\n    """one."""\n    x = 1\n',
                       'class A:\n    """the other."""\n    x = 1\n')
    check('C2 a reworded class docstring proves unchanged', done.returncode == 0, said(done))

    done = edit_proves(tmp, 'c3', 'async def f():\n    """one."""\n    return 1\n',
                       'async def f():\n    """the other."""\n    return 1\n')
    check('C3 a reworded async function docstring proves unchanged', done.returncode == 0,
          said(done))

    done = edit_proves(tmp, 'c4', 'def f():\n    """one."""\n',
                       'def f():\n    """the other."""\n    pass\n')
    check('C4 a function whose whole body is its docstring proves unchanged when reworded, '
          'with a pass added', done.returncode == 0, said(done))

    done = edit_proves(tmp, 'c5', 'def f():\n    a = 1\n    b = 2\n    return a + b\n',
                       'def f():\n    b = 2\n    a = 1\n    return a + b\n')
    check('C5 two statements swapped fail verify', done.returncode == 1
          and 'BEHAVIOUR CHANGED  m.py' in done.stdout, said(done))

    done = edit_proves(tmp, 'c6', 'def f():\n    x = 1\n    "a note"\n    return x\n',
                       'def f():\n    x = 1\n    "another note"\n    return x\n')
    check('C6 a string statement that is not first in the body is code, so changing it fails',
          done.returncode == 1, said(done))

    done = edit_proves(tmp, 'c7', 'x = 1\n', 'x = (\n')
    check('C7 a file that no longer parses fails verify as unparseable', done.returncode == 1
          and 'UNPARSEABLE  m.py' in done.stdout and 'Traceback' not in done.stderr, said(done))


# ── files the compare can't prove ─────────────────────────────────────────────

def language_checks(tmp: Path) -> None:
    repo = Repo(tmp, 'l1')
    repo.write('a.css', 'a {\n  color: red; /* x */\n}\n')
    repo.write('b.js', '//x\nlet a = 1;\n')
    repo.write('c.py', 'x = 1\n')
    snap = repo.proof('snapshot', 'a.css', 'b.js', 'c.py')
    done = repo.proof('verify', 'a.css', 'b.js', 'c.py')
    check('L1 an unchanged .css and .js are named NO PARSER at snapshot and verify, out of the count',
          snap.returncode == 0 and done.returncode == 0
          and all(f'NO PARSER  {n}' in d.stdout for n in ('a.css', 'b.js') for d in (snap, done))
          and 'snapshot: 1 file(s)' in snap.stdout and '1/1 proved unchanged' in done.stdout
          and 'UNPARSEABLE' not in done.stdout,
          f'{said(snap)} / {said(done)}')

    repo.write('a.css', 'a {\n  color: blue;\n}\n')
    done = repo.proof('verify', 'a.css', 'c.py')
    check('L2 an edited file with no parser leaves the exit code to the python files',
          done.returncode == 0 and 'NO PARSER  a.css' in done.stdout, said(done))

    repo.write('c.py', 'x = 2\n')
    done = repo.proof('verify', 'a.css', 'c.py')
    check('L3 a changed python file beside it still fails, counted alone',
          done.returncode == 1 and '0/1 proved unchanged' in done.stdout, said(done))

    repo = Repo(tmp, 'f1')
    repo.write('g.py', 'x = 1\n')
    repo.proof('snapshot', 'g.py')
    (repo.path / 'g.py').unlink()
    done = repo.proof('verify', 'g.py')
    check('F1 a file deleted after its snapshot fails verify as MISSING, with no traceback',
          done.returncode == 1 and 'MISSING  g.py' in done.stdout and 'Traceback' not in done.stderr,
          said(done))

    repo = Repo(tmp, 'f2')
    repo.write('h.py', 'x = 1\n')
    snap = repo.proof('snapshot', 'h.py', 'gone.py')
    done = repo.proof('verify', 'h.py')
    check('F2 a missing file at snapshot exits 2 naming it, with no traceback and no baseline kept',
          snap.returncode == 2 and 'gone.py' in snap.stderr and 'Traceback' not in snap.stderr
          and 'NO SNAPSHOT  h.py' in done.stdout, f'{said(snap)} / {said(done)}')


def measured_check(tmp: Path) -> None:
    repo = Repo(tmp, 'm1')
    repo.write('m.py', CALL)
    repo.proof('snapshot', 'm.py')
    repo.write('m.py', NOCALL)
    ruff = shutil.which('ruff')
    lint = subprocess.run([ruff, 'check', '--no-cache', '--isolated', 'm.py'], cwd=repo.path,
                          capture_output=True, text=True) if ruff else None
    comp = subprocess.run([sys.executable, '-m', 'py_compile', 'm.py'], cwd=repo.path,
                          capture_output=True, text=True)
    done = repo.proof('verify', 'm.py')
    check('M1 a dropped os.getenv call passes ruff and py_compile, and only verify catches it',
          (lint is None or lint.returncode == 0) and comp.returncode == 0
          and done.returncode == 1 and 'BEHAVIOUR CHANGED' in done.stdout,
          f'ruff {lint and lint.returncode}, py_compile {comp.returncode}, {said(done)}')


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        baseline_checks(Path(t).resolve())
        compare_checks(Path(t).resolve())
        language_checks(Path(t).resolve())
        measured_check(Path(t).resolve())
    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
