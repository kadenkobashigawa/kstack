#!/usr/bin/env python3
"""
test_gate — runs gate.py against throwaway repositories and checks the ledger's verdict and the
merge that reads it.

Run it with `python3 test_gate.py`. Each check builds its own repository in a temporary folder:
main checked out in one worktree, the change on a branch in another. Each check prints its label,
which says what it holds, and the exit code is the number of failed checks.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse


SCRIPT   = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'gate.py')
failures = 0

#lanes keep their evidence outside every worktree, so the tests keep theirs in a folder apart...
EVIDENCE = tempfile.mkdtemp(prefix='gate-evidence-')


def evidence(body: str = '12 passed\n') -> str:
    """A new file outside every test repository, holding `body`, as a lane's full output."""
    fd, path = tempfile.mkstemp(suffix='.txt', dir=EVIDENCE)
    with os.fdopen(fd, 'w') as f:
        f.write(body)
    return path


#the tests' kept lanes differ from the head only in .txt and .md files, which this calls noise...
NOISE = {**os.environ, 'GATE_NOISE_PATHS': '*.txt *.md'}

#each gates check a test runs is its own command, since a command runs once per head...
RUNS = iter(range(1, 10 ** 6))

def grounds(finding: str) -> list[str]:
    """The premise a blocking `finding`'s fix assumes, one per finding unless a test shares one."""
    return ['--premise', f'the fix of {finding} holds']


#the fresh agent that wrote a fix, and its model, as a fixed row names them...
FIXER = ['--by', 'fixer-1', '--model', 'sonnet']


def sh(*args: str, cwd: str) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


#the lane a finding row names when a test does not name one, as every row but fixed names one...
SORTER = 'review-a'


def gate(*args: str, cwd: str, env: dict | None = None,
         bare: bool = False) -> subprocess.CompletedProcess:
    """gate.py run with `args`; a finding row other than fixed names lane SORTER unless it names
    a lane or `bare` is set."""
    if args[:2] == ('record', 'finding') and len(args) > 3 and args[3] != 'fixed' \
            and '--lane' not in args and not bare:
        args = (*args, '--lane', SORTER)
    return subprocess.run([sys.executable, SCRIPT, *args], cwd=cwd, capture_output=True, text=True,
                          env=env)


def head(where: str) -> str:
    return sh('git', 'rev-parse', 'HEAD', cwd=where).strip()


def repo(tmp: str) -> tuple[str, str]:
    """A repository with main in `main/` and branch `feat` one commit ahead in `feat/`."""
    main = os.path.join(tmp, 'main')
    os.makedirs(main)
    for a in (['init', '-q', '-b', 'main'], ['config', 'user.email', 't@t'],
              ['config', 'user.name', 't'], ['commit', '-q', '--allow-empty', '-m', 'root']):
        sh('git', *a, cwd=main)
    feat = os.path.join(tmp, 'feat')
    sh('git', 'worktree', 'add', '-q', '-b', 'feat', feat, cwd=main)
    commit(feat, 'a.txt', 'one\n', 'first')
    return main, feat


def commit(where: str, name: str, text: str, msg: str) -> None:
    with open(os.path.join(where, name), 'w') as f:
        f.write(text)
    sh('git', 'add', name, cwd=where)
    sh('git', 'commit', '-q', '-m', msg, cwd=where)


def lane(feat: str, name: str, result: str, model: str,
         at: str | None = None) -> subprocess.CompletedProcess:
    """Record a lane that checked `at`, by default the branch's head, with its receipt.

    Notes
    -----
    The gates lane is run, not typed, so a gates PASS runs `true` and any other result `false`,
    and `model` is not used. A live PASS first declares live check L1 and verifies it at `at`.
    """
    at = at or head(feat)
    if name == 'gates':
        prog = 'true' if result == 'PASS' else 'false'
        return gate('run', 'gates', '--at', at, '--', prog, f'check-{next(RUNS)}', cwd=feat)
    if name == 'live' and result == 'PASS':
        gate('record', 'live-check', 'L1', '--note', 'a.txt reads as written', cwd=feat)
        gate('record', 'live-check', 'L1', 'VERIFIED', '--at', at, cwd=feat)

    body = 'R0-1: a nit, follow-up\n' if result == 'ISSUES' else '12 passed\n'
    args = ['record', 'lane', name, result, '--model', model, '--at', at, '--out', evidence(body)]
    if not name.startswith('review'):
        args += ['--cmd', f'run-{name} --all']
    if result in ('BLOCKED', 'NO-RUNTIME'):
        args += ['--note', 'the reason']
    out = gate(*args, cwd=feat)

    #the root reads an ISSUES lane's report and records each finding it names, from that lane...
    if result == 'ISSUES':
        gate('record', 'finding', f'R0-{name}', 'follow-up', '--lane', name, '--note', 'a nit',
             cwd=feat)
    return out


def clean_lanes(feat: str) -> None:
    lane(feat, 'gates', 'PASS', 'sonnet')
    lane(feat, 'live', 'NO-RUNTIME', 'opus')
    lane(feat, 'review-correctness', 'PASS', 'opus')
    lane(feat, 'review-structure', 'ISSUES', 'sonnet')


def message(tmp: str) -> str:
    path = os.path.join(tmp, 'msg.txt')
    with open(path, 'w') as f:
        f.write('Add a.txt\n\nWhy it exists.\n')
    return path


def drop(main: str, where: str, name: str) -> None:
    """Remove the worktree at `where` and delete branch `name`, as a run whose task failed does."""
    sh('git', 'worktree', 'remove', '--force', where, cwd=main)
    sh('git', 'branch', '-D', name, cwd=main)


def shim(tmp: str, script: str) -> dict:
    """An environment whose `git` runs the sh `script` first, with $REAL the real git."""
    folder = os.path.join(tmp, 'shim')
    os.makedirs(folder)
    path = os.path.join(folder, 'git')
    with open(path, 'w') as f:
        f.write(f'#!/bin/sh\nREAL={shutil.which("git")}\n{script}\nexec "$REAL" "$@"\n')
    os.chmod(path, 0o755)
    return {**os.environ, 'PATH': folder + os.pathsep + os.environ['PATH']}


def ledger(main: str, branch: str, worktree: str = '') -> str:
    """Where `branch`'s ledger lives: the git folder of linked `worktree`, or of main's worktree."""
    folder = os.path.join(main, '.git', 'worktrees', worktree) if worktree else \
        os.path.join(main, '.git')
    return os.path.join(folder, 'kstack-gate', urllib.parse.quote(branch, safe='') + '.tsv')


def check(label: str, ok: bool, detail: str = '') -> None:
    global failures
    print(f"{'ok  ' if ok else 'FAIL'} {label}" + (f': {detail}' if detail and not ok else ''))
    failures += not ok


def g1_to_g5() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        s = gate('status', cwd=feat)
        check('G1 no ledger yet reads as an empty one, which is not clean', s.returncode == 1
              and 'verdict: not clean' in s.stdout and 'Traceback' not in s.stderr, s.stderr)
        bad   = lane(feat, 'regression', 'GREEN', 'x').returncode
        none  = gate('record', 'lane', 'regression', 'PASS', '--at', head(feat),
                     cwd=feat).returncode
        blind = gate('record', 'lane', 'regression', 'PASS', '--model', 'opus', cwd=feat).returncode
        first = head(feat)
        commit(feat, 'a.txt', 'two\n', 'second')
        stale = lane(feat, 'regression', 'PASS', 'opus', at=first).returncode
        check('G2 a lane row needs a known result, its model and a commit at the current patch',
              (bad, none, blind, stale) == (2, 2, 2, 2), str((bad, none, blind, stale)))
        bare  = gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), cwd=feat).returncode
        check('G2b an act-on finding names its command', bare == 2, str(bare))
        clean_lanes(feat)
        s = gate('status', cwd=feat)
        check('G3 gates, NO-RUNTIME and two review models are clean', s.returncode == 0, s.stdout)
        lane(feat, 'regression', 'BLOCKED', 'sonnet')
        s = gate('status', cwd=feat)
        check('G4 a BLOCKED lane is not a pass', s.returncode == 1 and 'BLOCKED' in s.stdout)
        gate('record', 'lane', 'regression', 'gap', '--model', 'sonnet', cwd=feat)
        s = gate('status', cwd=feat)
        check('G4c a gap is not a pass', s.returncode == 1 and 'gap' in s.stdout, s.stdout)
        lane(feat, 'regression', 'PASS', 'sonnet')
        lane(feat, 'live', 'ISSUES', 'sonnet')
        s = gate('status', cwd=feat)
        check('G4d a live lane with ISSUES is not a pass', s.returncode == 1
              and 'no live lane' in s.stdout, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        short = head(feat)[:7]
        lane(feat, 'gates', 'PASS', 'sonnet', at=short)
        lane(feat, 'live', 'NO-RUNTIME', 'opus', at='HEAD')
        lane(feat, 'review-a', 'PASS', 'opus', at=short)
        lane(feat, 'review-b', 'PASS', 'sonnet', at=short)
        s = gate('status', cwd=feat)
        check('G2c a lane\'s commit given short or by name is kept as its full sha',
              s.returncode == 0, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        old = head(feat)
        for name in ('live', 'gates', 'review-a', 'regression'):
            lane(feat, name, 'PASS', 'opus')
        commit(feat, 'a.txt', 'two\n', 'second')
        keep  = ('--kept-from', old, '--note')
        why   = gate('record', 'lane', 'live', '--kept-from', old, cwd=feat, env=NOISE).returncode
        said  = gate('record', 'lane', 'live', 'PASS', *keep, 'n', cwd=feat, env=NOISE).returncode
        extra = [gate('record', 'lane', 'live', *keep, 'n', *more, cwd=feat, env=NOISE).returncode
                 for more in (['--at', head(feat)], ['--model', 'opus'])]
        other = [gate('record', 'lane', name, *keep, 'n', cwd=feat, env=NOISE).returncode
                 for name in ('gates', 'review-a', 'regression')]
        kept  = gate('record', 'lane', 'live', *keep, 'only a test changed', cwd=feat,
                     env=NOISE).returncode
        gap   = gate('record', 'lane', 'regression', 'gap', '--model', 'opus', cwd=feat).returncode
        hint  = lane(feat, 'gates', 'PASS', 'sonnet', at=old).stderr
        review = gate('record', 'lane', 'review-a', *keep, 'n', cwd=feat, env=NOISE).stderr
        check('G2d a lane with build output is kept, with why and no result or model of its own, '
              'never gates or a review lane; a gap names no commit',
              (why, said, kept, gap) == (2, 2, 0, 0) and extra == [2, 2]
              and other == [2, 2, 0] and 'current patch' in hint and 'no build output' in review,
              str((why, said, extra, other, kept, gap)) + hint + review)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        first = head(feat)
        lane(feat, 'live', 'NO-RUNTIME', 'haiku')
        lane(feat, 'live', 'ISSUES', 'sonnet')
        commit(feat, 'a.txt', 'two\n', 'second')
        second = head(feat)
        lane(feat, 'review-a', 'PASS', 'opus')
        commit(feat, 'a.txt', 'three\n', 'third')
        third = head(feat)
        gate('record', 'finding', 'live', 'nit', cwd=feat)
        commit(feat, 'a.txt', 'four\n', 'fourth')
        fourth = head(feat)
        lane(feat, 'live', 'NO-RUNTIME', 'haiku')
        commit(feat, 'a.txt', 'five\n', 'fifth')
        lane(feat, 'live', 'PASS', 'opus')
        held = [gate('record', 'lane', 'live', '--kept-from', sha, '--note', 'n', cwd=feat,
                     env=NOISE)
                for sha in (second, third, fourth, 'HEAD', first)]
        live = [ln.split()[:3] for ln in gate('status', cwd=feat).stdout.splitlines()
                if ln.split()[:1] == ['live']]
        check('G2e --kept-from takes a commit only where the ledger holds a live lane row from an '
              'earlier patch, copies the latest one\'s result and model, and refuses NO-RUNTIME',
              [r.returncode for r in held] == [2, 2, 2, 2, 0] and 'build output' in held[2].stderr
              and live == [['live', 'ISSUES', 'sonnet']],
              f'{[r.returncode for r in held]} {held[2].stderr} {live}')
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        replaced = head(feat)
        lane(feat, 'live', 'PASS', 'sonnet')
        sh('git', 'commit', '-q', '--allow-empty', '-m', 'same patch', cwd=feat)
        later = head(feat)
        lane(feat, 'live', 'ISSUES', 'opus')
        commit(feat, 'a.txt', 'two\n', 'second')
        keep = ['record', 'lane', 'live', '--kept-from']
        old = gate(*keep, replaced, '--note', 'n', cwd=feat, env=NOISE)
        new = gate(*keep, later, '--note', 'n', cwd=feat, env=NOISE)
        live = [ln.split()[:3] for ln in gate('status', cwd=feat).stdout.splitlines()
                if ln.split()[:1] == ['live']]
        check('G2f --kept-from refuses a commit whose live row a later one at its patch replaced, '
              'and keeps the later one', old.returncode == 2 and new.returncode == 0
              and live == [['live', 'ISSUES', 'opus']], f'{old.stderr} {new.stderr} {live}')
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        old = head(feat)
        lane(feat, 'live', 'PASS', 'sonnet')
        commit(main, 'b.txt', 'main\n', 'main moves')
        sh('git', 'rebase', '-q', 'main', cwd=feat)
        commit(feat, 'test_a.txt', 't\n', 'a test')
        live = gate('record', 'lane', 'live', '--kept-from', old, '--note', 'n', cwd=feat,
                    env=NOISE)
        check('G2g a live lane is kept across a moved main', live.returncode == 0, live.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'review-a', 'PASS', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G4b no live lane and no NO-RUNTIME record is not clean', s.returncode == 1
              and 'no live lane' in s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'PASS', 'sonnet')
        lane(feat, 'review-a', 'PASS', 'sonnet')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G5 two review lanes on one model are not clean', s.returncode == 1)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'NO-RUNTIME', 'opus')
        lane(feat, 'review-a', 'PASS', 'opus')
        s = gate('status', cwd=feat)
        check('G5b a gates lane on another model is not a second review lane', s.returncode == 1
              and 'fewer than two review lanes' in s.stdout, s.stdout)


def g6_g7() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n one a.txt',
             cwd=feat)
        s = gate('status', cwd=feat)
        check('G6d status prints an open finding\'s command', s.returncode == 1
              and 'grep -n one a.txt' in s.stdout, s.stdout)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        fresh = gate('status', cwd=feat)
        check('G6 an act-on finding blocks, and a new patch needs its lanes again',
              s.returncode == 1 and fresh.returncode == 1 and 'no gates lane' in fresh.stdout)
        clean_lanes(feat)
        s = gate('status', cwd=feat)
        check('G6b an act-on finding at an older patch blocks a later one, naming its patch',
              s.returncode == 1 and 'blocking finding F1 is open' in s.stdout
              and 'recorded at patch' in s.stdout, s.stdout)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        s = gate('status', cwd=feat).stdout
        check('G7a a finding back after one fix is counted, without STOP',
              '1 failed correction' in s and 'STOP' not in s, s)
        commit(feat, 'a.txt', 'three\n', 'fix 2')
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        s = gate('status', cwd=feat).stdout
        check('G7 a finding back after two fixes says STOP', '2 failed correction' in s
              and 'STOP' in s, s)
        commit(feat, 'a.txt', 'four\n', 'design settled')
        moved = gate('status', cwd=feat).stdout
        check('G7c a finding carried open to a new patch with no row there keeps its count and '
              'STOP',
              '2 failed correction' in moved and 'STOP' in moved, moved)
        resort = gate('record', 'finding', 'F1', 'dismissed', '--note', 'the design settled it',
                      cwd=feat)
        closed = gate('status', cwd=feat).stdout
        check('G7b a blocking finding is never re-sorted dismissed, so it stays open with its '
              'count and STOP', resort.returncode == 2 and 'fixed row' in resort.stderr
              and '2 failed correction' in closed and 'STOP' in closed, resort.stderr + closed)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'follow-up', '--note', 'a nit', cwd=feat)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        same = gate('status', cwd=feat)
        resort = gate('record', 'finding', 'F1', 'dismissed', '--note', 'a misreading', cwd=feat)
        later = gate('status', cwd=feat)
        check('G6c a later blocking row on a finding at the same patch supersedes its follow-up '
              'row, and re-sorting it dropped is refused (R1-G16)',
              same.returncode == 1 and 'F1 is open' in same.stdout and resort.returncode == 2
              and later.returncode == 1 and 'F1 is open' in later.stdout,
              same.stdout + resort.stderr + later.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        msg = message(tmp)
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'NO-RUNTIME', 'opus')
        lane(feat, 'review-a', 'ISSUES', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n one a.txt',
             cwd=feat)
        commit(feat, 'b.txt', 'unrelated\n', 'another change')
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'NO-RUNTIME', 'opus')
        lane(feat, 'review-a', 'PASS', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        r = gate('land', msg, cwd=feat)
        check('G6f an act-on finding carried past a new commit and two fresh PASS reviews is not '
              'clean, and land refuses', s.returncode == 1 and 'F1' in s.stdout
              and r.returncode == 1 and 'F1' in r.stderr, s.stdout + r.stderr)
        same = gate('record', 'finding', 'F2', 'act-on', *grounds('F2'), '--cmd', 'grep -n x',
                    cwd=feat)
        early = gate('record', 'finding', 'F2', 'fixed', *FIXER,
                     '--note', 'its sites came back clean',
                     cwd=feat)
        never = gate('record', 'finding', 'F3', 'fixed', *FIXER,
                     '--note', 'no such finding', cwd=feat)
        gate('record', 'finding', 'F4', 'dismissed', '--note', 'a misreading', cwd=feat)
        shut = gate('record', 'finding', 'F4', 'fixed', *FIXER,
                    '--note', 'already closed', cwd=feat)
        check('G6g fixed closes only a finding open at an earlier patch: never one act-on at this '
              'patch, one never recorded, or one already closed',
              same.returncode == 0 and [early.returncode, never.returncode, shut.returncode]
              == [2, 2, 2], early.stderr + never.stderr + shut.stderr)
        fixed = gate('record', 'finding', 'F1', 'fixed', *FIXER,
                     '--note', 'grep -n one a.txt is empty',
                     cwd=feat)
        s = gate('status', cwd=feat)
        check('G6h fixed at the later patch closes a carried act-on finding, and F2, blocking at '
              'this patch, still holds the verdict', fixed.returncode == 0
              and s.returncode == 1 and 'F1' not in s.stdout and 'F2 is open' in s.stdout,
              fixed.stderr + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        clean_lanes(feat)
        held = gate('status', cwd=feat)
        resort = gate('record', 'finding', 'F1', 'dismissed', '--note', 'a misreading', cwd=feat)
        s = gate('status', cwd=feat)
        check('G6i a carried blocking finding is never re-sorted dismissed at a later patch, so it '
              'stays open (R1-G16)', held.returncode == 1 and resort.returncode == 2
              and s.returncode == 1 and 'F1 is open' in s.stdout, held.stdout + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        msg = message(tmp)
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'NO-RUNTIME', 'opus')
        lane(feat, 'review-a', 'ISSUES', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n one a.txt',
             cwd=feat)
        bad = head(feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        good = head(feat)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'fixed', *FIXER,
             '--note', 'grep -n one a.txt is empty', cwd=feat)
        sh('git', 'reset', '-q', '--hard', bad, cwd=feat)
        s = gate('status', cwd=feat)
        r = gate('land', msg, cwd=feat)
        check('G6j fixed at a later patch does not close the finding at its own patch: a reset '
              'back to it is not clean, and land refuses', s.returncode == 1
              and 'blocking finding F1 is open' in s.stdout and r.returncode == 1
              and 'F1' in r.stderr, s.stdout + r.stderr)
        sh('git', 'reset', '-q', '--hard', good, cwd=feat)
        sh('git', 'revert', '--no-edit', 'HEAD', cwd=feat)
        lane(feat, 'gates', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G6k a revert back to the patch where a finding was recorded act-on is not clean',
              s.returncode == 1 and 'blocking finding F1 is open' in s.stdout, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        bad = head(feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        sh('git', 'reset', '-q', '--hard', bad, cwd=feat)
        back = gate('record', 'finding', 'F1', 'fixed', *FIXER,
                    '--note', 'no round ran here', cwd=feat)
        check('G6l fixed is refused at a patch where the finding\'s own row is act-on, whatever '
              'another patch holds', back.returncode == 2, back.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        msg = message(tmp)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'dismissed', '--note', 'a misreading', cwd=feat)
        mid = head(feat)
        commit(feat, 'a.txt', 'three\n', 'fix 2')
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        sh('git', 'reset', '-q', '--hard', mid, cwd=feat)
        s = gate('status', cwd=feat)
        r = gate('land', msg, cwd=feat)
        check('G6m an older closing row at this patch does not hide a newer act-on row at a later '
              'one: a reset back to it is not clean, and land refuses', s.returncode == 1
              and 'blocking finding F1 is open' in s.stdout and r.returncode == 1
              and 'F1' in r.stderr, s.stdout + r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        msg = message(tmp)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'dismissed', '--note', 'a misreading', cwd=feat)
        first = head(feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        sh('git', 'reset', '-q', '--hard', first, cwd=feat)
        s = gate('status', cwd=feat)
        r = gate('land', msg, cwd=feat)
        check('G6n a finding sorted dismissed and then act-on at a later patch is open when a '
              'reset brings back the dismissed patch, and land refuses', s.returncode == 1
              and 'blocking finding F1 is open' in s.stdout and r.returncode == 1
              and 'F1' in r.stderr, s.stdout + r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        old = head(feat)
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'PASS', 'sonnet')
        lane(feat, 'regression', 'PASS', 'sonnet')
        lane(feat, 'review-correctness', 'ISSUES', 'opus')
        lane(feat, 'review-structure', 'PASS', 'sonnet')
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        commit(feat, 'test_a.txt', 't\n', 'a test')
        lane(feat, 'gates', 'PASS', 'sonnet')
        held  = [gate('record', 'lane', name, '--kept-from', old, '--note',
                      'only a test changed', cwd=feat, env=NOISE).returncode
                 for name in ('gates', 'live', 'regression', 'review-correctness',
                              'review-structure')]
        lane(feat, 'review-correctness', 'PASS', 'opus')
        one   = gate('status', cwd=feat)
        lane(feat, 'review-structure', 'PASS', 'sonnet')
        gate('record', 'finding', 'F1', 'fixed', *FIXER,
             '--note', 'its sites came back clean', cwd=feat)
        two   = gate('status', cwd=feat)
        check('G6e after a tests-only patch change the review lanes are never kept, and the '
              'verdict needs two fresh review lanes on two models',
              held == [2, 0, 0, 2, 2] and one.returncode == 1
              and 'fewer than two review lanes' in one.stdout and two.returncode == 0,
              f'{held} {one.stdout} {two.stdout}')


def g8_to_g9() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        msg = message(tmp)
        r = gate('land', msg, cwd=feat)
        check('G8 no clean verdict, no landing', r.returncode == 1)
        clean_lanes(feat)
        base  = sh('git', 'merge-base', 'main', 'feat', cwd=main).strip()
        commit(main, 'b.txt', 'main moved\n', 'elsewhere')
        moved = head(main)
        r = gate('land', msg, cwd=feat)
        body  = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        first = sh('git', 'rev-parse', 'main^', cwd=main).strip()
        both  = all(os.path.exists(os.path.join(main, n)) for n in ('a.txt', 'b.txt'))
        check('G9 lands past a main that moved on paths the change does not touch, keeping main\'s '
              'commit, and the verdict names the move', r.returncode == 0 and first == moved
              and both and f'base {base[:8]}' in body and f'moved to {moved[:8]}' in body,
              r.stderr + body)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        msg = message(tmp)
        clean_lanes(feat)
        sh('git', 'commit', '-q', '--allow-empty', '-m', 'same patch', cwd=feat)
        kept = gate('land', msg, cwd=feat)
        check('G9b a new head with the same tree keeps the gates runs, since a run tested the '
              'tree', kept.returncode == 0, kept.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, _ = repo(tmp)
        none = os.path.join(tmp, 'none')
        sh('git', 'worktree', 'add', '-q', '-b', 'none', none, cwd=main)
        clean_lanes(none)
        r = gate('land', message(tmp), cwd=none)
        count = sh('git', 'rev-list', '--count', 'main', cwd=main).strip()
        check('G9c an empty patch does not land', r.returncode == 1 and count == '1'
              and 'changes nothing' in r.stderr, r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        commit(main, 'c.txt', '1\n2\n3\n4\n5\n6\n7\n', 'seven lines')
        sh('git', 'rebase', '-q', 'main', cwd=feat)
        commit(feat, 'c.txt', 'one\n2\n3\n4\n5\n6\n7\n', 'first line')
        clean_lanes(feat)
        commit(main, 'c.txt', '1\n2\n3\n4\n5\n6\nseven\n', 'last line')
        tip = head(main)
        r = gate('land', message(tmp), cwd=feat)
        check('G9d a main that moved on a path the change touches refuses, naming the path, though '
              'the merge is clean', r.returncode == 1 and head(main) == tip and 'c.txt' in r.stderr
              and 'rebase' in r.stderr.lower(), r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        os.makedirs(os.path.join(feat, 'd'))
        commit(feat, os.path.join('d', 'f.txt'), 'f\n', 'a folder d')
        clean_lanes(feat)
        commit(main, 'd', 'a file\n', 'a file d')
        tip = head(main)
        r = gate('land', message(tmp), cwd=feat)
        check('G9e a main whose merge with the head conflicts refuses, though no path is on both '
              'sides', r.returncode == 1 and head(main) == tip and 'is not clean' in r.stderr
              and 'rebase' in r.stderr.lower(), r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        commit(main, 'c.txt', '1\n2\n3\n4\n5\n6\n7\n', 'seven lines')
        sh('git', 'rebase', '-q', 'main', cwd=feat)
        commit(feat, 'c.txt', 'one\n2\n3\n4\n5\n6\n7\n', 'first line')
        clean_lanes(feat)
        sh('git', 'mv', 'c.txt', 'd.txt', cwd=main)
        sh('git', 'commit', '-q', '-m', 'rename c.txt', cwd=main)
        tip = head(main)
        r = gate('land', message(tmp), cwd=feat)
        check('G9k a main that renamed a file the patch edits refuses, naming the overlap',
              r.returncode == 1 and head(main) == tip and 'c.txt' in r.stderr
              and 'changed paths the patch changes' in r.stderr, r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        clean_lanes(feat)
        commit(main, 'ci.yml', 'jobs\n', 'main changes the checks')
        tip = head(main)
        env = {**os.environ, 'GATE_CHECK_PATHS': 'docs ci.yml'}
        sub = os.path.join(feat, 'sub')
        os.makedirs(sub)
        r = gate('land', message(tmp), cwd=feat, env=env)
        check('G9f a main that moved on a path GATE_CHECK_PATHS names refuses, naming the path',
              r.returncode == 1 and head(main) == tip and 'ci.yml' in r.stderr
              and 'GATE_CHECK_PATHS' in r.stderr and 'rebase' in r.stderr.lower(), r.stderr)
        low = gate('land', message(tmp), cwd=sub, env=env)
        check('G9g GATE_CHECK_PATHS names paths from the repository top, so landing from a '
              'subfolder refuses too', low.returncode == 1 and head(main) == tip
              and 'ci.yml' in low.stderr, low.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        commit(main, 'b.txt', 'main moved\n', 'before the gates')
        clean_lanes(feat)
        tip = head(main)
        r = gate('land', message(tmp), cwd=feat)
        check('G9h past a main that moved, a gates lane that ran on a stale base refuses',
              r.returncode == 1 and head(main) == tip and 'rebase onto' in r.stderr.lower()
              and 'gates lane' in r.stderr, r.stderr)
        sh('git', 'rebase', '-q', 'main', cwd=feat)
        lane(feat, 'gates', 'PASS', 'sonnet')
        commit(main, 'e.txt', 'main moved again\n', 'after the gates')
        r = gate('land', message(tmp), cwd=feat)
        check('G9i a gates lane that ran on the rebased head lands past a later main move',
              r.returncode == 0, r.stderr)


def g10_to_g15() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        reviewed = head(feat)
        sh('git', 'commit', '-q', '--allow-empty', '-m', 'same patch', cwd=feat)
        now = head(feat)
        clean_lanes(feat)
        lane(feat, 'review-correctness', 'PASS', 'opus', at=reviewed)
        with open(ledger(main, 'feat', 'feat'), 'a') as f:
            f.write('\t'.join(['2026-10-24T00:00:00+00:00', now, 'p', 'fix', 'fixer-1', 'sonnet',
                               'fixed', '', '', 'm']) + '\n')
        sub = os.path.join(feat, 'sub')
        os.makedirs(sub)
        r = gate('land', message(tmp), cwd=sub)
        body = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        same = sh('git', 'rev-parse', 'main^{tree}', cwd=main) == \
            sh('git', 'rev-parse', 'feat^{tree}', cwd=main)
        count = sh('git', 'rev-list', '--count', 'main', cwd=main).strip()
        on_disk = os.path.exists(os.path.join(main, 'a.txt'))
        check('G10 lands one verdict commit from a subfolder, and main\'s worktree follows',
              r.returncode == 0 and same and count == '2' and on_disk
              and 'GATE VERDICT: clean' in body
              and f'review-correctness: PASS, opus, at {reviewed[:8]}' in body
              and f'gates: PASS, root, at {now[:8]} (`true check-' in body
              and '- fix: fixer-1, sonnet' in body, r.stderr + body)
        check('G10b landing deletes the ledger', not os.path.exists(ledger(main, 'feat', 'feat')))
        said = [ln.strip() for ln in r.stdout.splitlines() if ln.startswith('  git ')]
        ran  = subprocess.run(' && '.join(said), shell=True, cwd=sub, capture_output=True,
                              text=True)
        left = sh('git', 'branch', '--list', 'feat', cwd=main).strip()
        check('G10e land prints the command the root runs to remove the whole worktree, then the '
              'one the operator runs to delete the branch, and they run from the subfolder it '
              'landed from',
              len(said) == 2 and 'worktree remove' in said[0] and 'branch -D' in said[1]
              and 'the root removes the worktree' in r.stdout
              and 'the operator deletes the branch' in r.stdout
              and ran.returncode == 0 and not os.path.exists(feat) and not left
              and sh('git', 'rev-list', '--count', 'main', cwd=main).strip() == '2',
              r.stdout + ran.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        checked = head(feat)
        lane(feat, 'live', 'PASS', 'sonnet')
        commit(feat, 'test_a.txt', 't\n', 'a test')
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'review-correctness', 'PASS', 'opus')
        lane(feat, 'review-structure', 'ISSUES', 'sonnet')
        lane(feat, 'regression', 'PASS', 'sonnet')
        gate('record', 'lane', 'live', '--kept-from', 'HEAD~1', '--note',
             'only a test changed', cwd=feat, env=NOISE)
        r = gate('land', message(tmp), cwd=feat)
        body = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        check('G10c a kept live lane lands at the commit it checked, its note saying it was kept',
              r.returncode == 0 and f'live: PASS, sonnet, at {checked[:8]} (kept from '
              f'{checked[:8]}, every changed path is noise by GATE_NOISE_PATHS: only a test '
              'changed)' in body, r.stderr + body)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        sh('git', 'switch', '-q', '-c', 'other', 'main', cwd=feat)
        commit(feat, 'o.txt', 'o\n', 'other')
        lane(feat, 'gates', 'PASS', 'sonnet')
        sh('git', 'switch', '-q', 'feat', cwd=feat)
        clean_lanes(feat)
        r = gate('land', message(tmp), cwd=feat)
        check('G10d landing one branch keeps another branch\'s ledger and the folder they share',
              r.returncode == 0 and os.path.exists(ledger(main, 'other', 'feat')), r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        clean_lanes(feat)
        read_at = head(feat)
        quiet = '>/dev/null 2>&1'
        env = shim(tmp, f'case "$*" in *"^{{tree}}"*) echo x > {feat}/sneak.txt; '
                        f'"$REAL" -C {feat} add sneak.txt {quiet}; '
                        f'"$REAL" -C {feat} commit -q -m sneak {quiet} ;; esac')
        r = gate('land', message(tmp), cwd=feat, env=env)
        landed = sh('git', 'rev-parse', 'main^{tree}', cwd=main)
        wanted = sh('git', 'rev-parse', f'{read_at}^{{tree}}', cwd=main)
        check('G11 land commits the tree of the head its verdict was read at',
              r.returncode == 0 and landed == wanted, r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        sh('git', 'checkout', '-q', '-b', 'parking', cwd=main)
        clean_lanes(feat)
        r = gate('land', message(tmp), cwd=feat)
        same = sh('git', 'rev-parse', 'main^{tree}', cwd=main) == \
            sh('git', 'rev-parse', 'feat^{tree}', cwd=main)
        count = sh('git', 'rev-list', '--count', 'main', cwd=main).strip()
        check('G12 lands with no worktree on main', r.returncode == 0 and same and count == '2',
              r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        sh('git', 'checkout', '-q', '-b', 'parking', cwd=main)
        clean_lanes(feat)
        race = sh('git', 'commit-tree', 'main^{tree}', '-p', 'main', '-m', 'race', cwd=main).strip()
        env = shim(tmp, f'[ "$1" = commit-tree ] && "$REAL" -C {main} update-ref refs/heads/main '
                        f'{race}')
        r = gate('land', message(tmp), cwd=feat, env=env)
        tip = sh('git', 'rev-parse', 'main', cwd=main).strip()
        check('G13 main moving during the landing refuses it, and keeps main and the ledger',
              r.returncode != 0 and 'Traceback' not in r.stderr and tip == race
              and os.path.exists(ledger(main, 'feat', 'feat')), r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        sh('git', 'checkout', '-q', '--detach', cwd=feat)
        held = lane(feat, 'gates', 'PASS', 'sonnet').returncode
        note = gate('record', 'finding', 'F1', 'nit', cwd=feat).returncode
        check('G14 record refuses a detached HEAD', held == 2 and note == 2
              and not os.path.exists(ledger(main, 'HEAD', 'feat')))
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        r = gate('status', cwd=feat, env={**os.environ, 'GATE_MAIN': 'no-such-branch'})
        check('G15 a failing git prints its own message, with no traceback', r.returncode != 0
              and 'Traceback' not in r.stderr and 'no-such-branch' in r.stderr, r.stderr)
        r = gate('status', cwd=feat, env={**os.environ, 'GATE_MAIN': os.fsdecode(b'\xff')})
        check('G15b a failing git whose message is not UTF-8 prints it, with no traceback',
              r.returncode != 0 and 'Traceback' not in r.stderr and 'object name' in r.stderr,
              r.stderr)


def g16_to_g18() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        with open(os.path.join(feat, 'c.txt'), 'wb') as f:
            f.write(b'a\rb\xff\n')
        sh('git', 'add', 'c.txt', cwd=feat)
        sh('git', 'commit', '-q', '-m', 'a lone CR and a byte that is not UTF-8', cwd=feat)
        base  = sh('git', 'merge-base', 'main', 'HEAD', cwd=feat).strip()
        piped = subprocess.run(f'git diff {base}..HEAD | git patch-id --verbatim', shell=True,
                               cwd=feat, capture_output=True).stdout.split()[0].decode()
        s = gate('status', cwd=feat)
        check('G16 the patch-id is the shell pipe\'s, for a lone CR and a byte that is not UTF-8',
              f'patch {piped[:12]}' in s.stdout and 'Traceback' not in s.stderr,
              piped + s.stdout + s.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        held = os.path.exists(ledger(main, 'feat', 'feat'))
        sh('git', 'worktree', 'remove', feat, cwd=main)
        left = [os.path.join(d, n) for d, _, names in os.walk(os.path.join(main, '.git'))
                for n in names if n == 'feat.tsv']
        kept = sh('git', 'branch', '--list', 'feat', cwd=main).strip()
        check('G17 removing a worktree removes its ledger, though the branch stays',
              held and not left and kept.endswith('feat'), str(left))
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        drop(main, feat, 'feat')
        sh('git', 'worktree', 'add', '-q', '-b', 'feat', feat, cwd=main)
        commit(feat, 'a.txt', 'again\n', 'made again')
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        s = gate('status', cwd=feat).stdout
        check('G17a the same branch name in a new worktree starts with an empty ledger',
              'failed correction' not in s and 'blocking finding F1' in s, s)
    with tempfile.TemporaryDirectory() as tmp:
        main, _ = repo(tmp)
        sh('git', 'switch', '-q', '-c', 'one', cwd=main)
        commit(main, 'one.txt', '1\n', 'one')
        old = head(main)
        commit(main, 'one.txt', '2\n', 'two')
        said = [gate('record', *args, cwd=main) for args in (
            ('finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n 1'),
            ('lane', 'regression', 'PASS', '--model', 'sonnet', '--at', 'HEAD', '--cmd', 'run',
             '--out', evidence()),
            ('lane', 'live', '--kept-from', old, '--note', 'n'))]
        check('G17b record refuses in main\'s worktree, whose git folder outlives a deleted branch',
              [r.returncode for r in said] == [2, 2, 2]
              and all('main worktree' in r.stderr for r in said)
              and not os.path.exists(os.path.dirname(ledger(main, 'one'))),
              ''.join(r.stderr for r in said))
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        sh('git', 'switch', '-q', '-c', 'one', cwd=main)
        commit(main, 'one.txt', '1\n', 'one')
        sub = os.path.join(main, 'sub')
        os.makedirs(sub)
        env  = shim(tmp, 'case "$*" in *--path-format=absolute*) [ -n "$OLD" ] && '
                         'echo "--path-format=absolute"; '
                         'exec "$REAL" rev-parse --git-dir --git-common-dir ;; esac')
        old  = {**env, 'OLD': '1'}
        said = [gate('record', 'finding', 'F1', 'nit', cwd=at, env=old) for at in (main, feat)]
        said.append(gate('record', 'finding', 'F1', 'nit', cwd=sub, env=env))
        check('G17c record refuses where git echoes --path-format back, as before 2.31, or drops '
              'it and names a git folder relative to a subfolder of main\'s worktree',
              [r.returncode for r in said] == [2, 2, 2] and all('2.31' in r.stderr for r in said)
              and not os.path.exists(os.path.dirname(ledger(main, 'one')))
              and not os.path.exists(ledger(main, 'feat', 'feat')),
              ''.join(r.stderr for r in said))
    with tempfile.TemporaryDirectory() as tmp:
        main, _ = repo(os.path.join(tmp, 'a\n', 'b'))
        sh('git', 'switch', '-q', '-c', 'one', cwd=main)
        commit(main, 'one.txt', '1\n', 'one')
        r = gate('record', 'finding', 'F1', 'nit', cwd=main)
        check('G17d record refuses in a main worktree whose path splits into more than two lines',
              r.returncode == 2 and not os.path.exists(os.path.dirname(ledger(main, 'one'))),
              r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        path   = ledger(main, 'feat', 'feat')
        header = 'ts\thead\tpatch\tkind\tname\tmodel\tresult\tcmd\tnote\tmain'
        other  = f'2026-10-24T00:00:00+00:00\t{head(feat)}\tp\tfinding\tF0\t\tnit\t\t\tm'
        os.makedirs(os.path.dirname(path))
        with open(path, 'a') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            proc = subprocess.Popen([sys.executable, SCRIPT, 'record', 'finding', 'F1', 'nit',
                                     '--lane', SORTER],
                                    cwd=feat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            held.write(f'{header}\n{other}\n')
        proc.wait(timeout=60)
        with open(path) as f:
            lines = f.read().splitlines()
        check('G18 a record waits for another writer\'s lock, so a new ledger has one header first',
              lines[:2] == [header, other] and lines.count(header) == 1 and len(lines) == 3,
              str(lines))
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        path = ledger(main, 'feat', 'feat')
        os.makedirs(os.path.dirname(path))
        open(path, 'w').close()
        gate('record', 'finding', 'F1', 'nit', cwd=feat)
        with open(path) as f:
            lines = f.read().splitlines()
        check('G18b a ledger file left empty, as by a writer that died after opening it, gets the '
              'header first', len(lines) == 2 and lines[0].startswith('ts\thead\t'), str(lines))


def g19() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'PASS', 'sonnet')
        lane(feat, 'review-correctness', 'PASS', 'opus')
        lane(feat, 'review-structure', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G19 a live lane that passed needs no regression lane for a clean verdict',
              s.returncode == 0 and 'regression' not in s.stdout, s.stdout)


def g20_to_g23() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'live', 'NO-RUNTIME', 'opus')
        case = lane(feat, 'review-a', 'PASS', 'opus')
        same = lane(feat, 'review-b', 'PASS', ' Opus ')
        s    = gate('status', cwd=feat)
        root = [lane(feat, name, r, 'root').returncode
                for name, r in (('review-b', 'PASS'), ('live', 'NO-RUNTIME'))]
        odd  = [lane(feat, 'review-b', 'PASS', m).returncode for m in ('gpt', 'opus-ish', 'x')]
        check('G20 a model is its family, lowercased: Opus and opus are one model, root is only '
              'the gates lane, and an unknown model is refused',
              case.returncode == 0 and same.returncode == 0 and s.returncode == 1
              and 'fewer than two review lanes' in s.stdout and root == [2, 2]
              and odd == [2, 2, 2], f'{s.stdout} {root} {odd}')
        lane(feat, 'review-b', 'PASS', 'Sonnet')
        s = gate('status', cwd=feat)
        check('G20b two families clean the review part, and the row holds the family lowercased',
              s.returncode == 0 and 'sonnet' in s.stdout and 'Sonnet' not in s.stdout, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'live', 'NO-RUNTIME', 'opus')
        lane(feat, 'review-a', 'PASS', 'opus')
        lane(feat, 'review-b', 'NO-RUNTIME', 'sonnet')
        s = gate('status', cwd=feat)
        check('G5c a review lane recorded NO-RUNTIME does not count as a review',
              s.returncode == 1 and 'fewer than two review lanes' in s.stdout, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        said = gate('record', 'lane', 'regression', 'NO-TRUNK-FEATURE', '--model', 'sonnet',
                    '--at', head(feat), '--note', 'main has no a.txt to read', cwd=feat)
        check('G21 NO-TRUNK-FEATURE is no longer a lane result, since no regression lane is '
              'required', said.returncode == 2, said.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        gate('record', 'finding', 'F1', 'consider', '--note', 'sorted again', cwd=feat)
        commit(feat, 'a.txt', 'three\n', 'fix 2')
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        s = gate('status', cwd=feat).stdout
        check('G7d an act-on row sorted again at its own patch still counts as a failed '
              'correction, so STOP holds', '2 failed correction' in s and 'STOP' in s, s)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        r = lane(feat, 'regression', 'gap', 'sonnet')
        check('G2h a gap that names a commit is refused', r.returncode == 2
              and '--at' in r.stderr, r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        sh('git', 'switch', '-q', '-c', 'a/b', cwd=feat)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        sh('git', 'switch', '-q', '-c', 'a__b', cwd=feat)
        s = gate('status', cwd=feat).stdout
        check('G23 branches a/b and a__b keep separate ledgers', 'F1' not in s
              and os.path.exists(ledger(main, 'a/b', 'feat')), s)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        sh('git', 'tag', 'feat', cwd=main)
        clean_lanes(feat)
        s = gate('status', cwd=feat)
        r = gate('land', message(tmp), cwd=feat)
        check('G23b a tag named like the branch leaves the branch name whole, so its ledger is '
              'found and land deletes the branch by name',
              s.returncode == 0 and s.stdout.startswith('feat at') and r.returncode == 0
              and 'branch -D feat' in r.stdout and 'heads/' not in r.stdout,
              s.stdout + r.stdout + r.stderr)


def g24() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'live', 'NO-RUNTIME', 'opus')
        lane(feat, 'review-a', 'PASS', 'opus')
        path = ledger(main, 'feat', 'feat')
        with open(path) as f:
            last = f.read().splitlines()[-1].split('\t')
        said = []
        for name, model in (('review-b', ' Opus '), ('review-b', 'gpt'), ('review-b', 'Sonnet ')):
            with open(path, 'a') as f:
                f.write('\t'.join([*last[:4], name, model, 'PASS', '', '', last[9]]) + '\n')
            said.append(gate('status', cwd=feat))
        check('G24 a review row written before the model check counts by its family, and a model '
              'outside the families counts for none',
              [r.returncode for r in said] == [1, 1, 0]
              and all('fewer than two review lanes' in r.stdout for r in said[:2]),
              ''.join(r.stdout for r in said))
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        sh('git', 'switch', '-q', '-c', 'fix/item-x', cwd=feat)
        gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', 'grep -n x', cwd=feat)
        new = ledger(main, 'fix/item-x', 'feat')
        old = os.path.join(os.path.dirname(new), 'fix__item-x.tsv')
        os.replace(new, old)
        s = gate('status', cwd=feat)
        gate('record', 'finding', 'F2', 'nit', cwd=feat)
        with open(new) as f:
            names = [line.split('\t')[4] for line in f.read().splitlines()[1:]]
        check('G24b a branch whose ledger has the old name, each / as __, keeps its open findings, '
              'and the ledger moves to the new name', s.returncode == 1
              and 'blocking finding F1 is open' in s.stdout and not os.path.exists(old)
              and names == ['F1', 'F2'], f'{s.stdout} {names}')
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'live', 'PASS', 'sonnet')
        first = head(feat)
        commit(feat, 'b.md', 'docs\n', 'docs')
        kept = gate('record', 'lane', 'live', '--kept-from', first, '--note', '   ',
                    cwd=feat, env=NOISE)
        check('G24c a note of only whitespace is no note for a kept lane',
              kept.returncode == 2 and '--note' in kept.stderr, kept.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        sh('git', 'switch', '-q', '-c', 'x__y', cwd=feat)
        gate('record', 'finding', 'K1', 'act-on', *grounds('K1'), '--cmd', 'grep -n k', cwd=feat)
        sh('git', 'switch', '-q', '-c', 'x/y', cwd=feat)
        moved = gate('status', cwd=feat)
        sh('git', 'switch', '-q', 'x__y', cwd=feat)
        s = gate('status', cwd=feat)
        check('G24d a branch a/b leaves the ledger of a live branch a__b where it is',
              'K1' not in moved.stdout and s.returncode == 1
              and 'blocking finding K1 is open' in s.stdout
              and os.path.exists(ledger(main, 'x__y', 'feat')), moved.stdout + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        r = gate('record', 'finding', 'F1', 'act-on', *grounds('F1'), '--cmd', ' \t ', cwd=feat)
        check('G24e a --cmd of only whitespace is no command for an act-on finding',
              r.returncode == 2 and '--cmd' in r.stderr, r.stderr)


def full_round(feat: str) -> None:
    """A full round at the head: gates, a live pass and two review lanes on two models."""
    lane(feat, 'gates', 'PASS', 'root')
    lane(feat, 'live', 'PASS', 'sonnet')
    lane(feat, 'review-a', 'PASS', 'opus')
    lane(feat, 'review-b', 'ISSUES', 'sonnet')


def size(feat: str, kind: str,
         why: str = 'the fix renames one variable') -> subprocess.CompletedProcess:
    return gate('record', 'round', kind, '--note', why, cwd=feat)


def g25_to_g31() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        odd  = size(feat, 'small').returncode
        bare = gate('record', 'round', 'minor', cwd=feat).returncode
        blank = size(feat, 'minor', ' \t ').returncode
        check('G25 a round row is full, minor or wording, and says why (--note)',
              (odd, bare, blank) == (2, 2, 2), str((odd, bare, blank)))
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        full_round(feat)
        first = head(feat)
        commit(feat, 'a.txt', 'two\n', 'minor fix')
        lane(feat, 'gates', 'PASS', 'root')
        unsized = gate('status', cwd=feat)
        said = size(feat, 'minor')
        none = gate('status', cwd=feat)
        lane(feat, 'checker', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        r = gate('land', message(tmp), cwd=feat)
        body = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        check('G26 a later patch with no round row needs a full round again',
              unsized.returncode == 1 and 'fewer than two review lanes' in unsized.stdout,
              unsized.stdout)
        check('G26b a minor round needs one checker lane at its patch',
              said.returncode == 0 and none.returncode == 1 and 'checker' in none.stdout,
              said.stderr + none.stdout)
        check('G26c a minor round is clean with the earlier full round\'s lanes, one checker and '
              'gates at the head, and the verdict block names the round and the earlier lanes',
              s.returncode == 0 and r.returncode == 0 and 'round: minor' in body
              and f'review-a: PASS, opus, at {first[:8]}' in body and 'checker: PASS' in body,
              s.stdout + r.stderr + body)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        full_round(feat)
        lane(feat, 'checker', 'PASS', 'sonnet')
        first = head(feat)
        commit(feat, 'a.txt', 'two\n', 'minor fix')
        size(feat, 'minor')
        lane(feat, 'gates', 'PASS', 'root')
        kept = gate('record', 'lane', 'checker', '--kept-from', first, '--note',
                    'only a test changed', cwd=feat, env=NOISE)
        s = gate('status', cwd=feat)
        check('G26d a minor round\'s checker runs at the new patch, so --kept-from refuses it and '
              'the round is not clean', kept.returncode == 2 and 'checker' in kept.stderr
              and s.returncode == 1 and 'checker' in s.stdout, kept.stderr + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        full_round(feat)
        commit(feat, 'a.txt', 'two\n', 'reword a message')
        size(feat, 'wording', 'only a README sentence changed')
        nogates = gate('status', cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        s = gate('status', cwd=feat)
        check('G27 a wording round needs no checker, but still needs gates at the head',
              nogates.returncode == 1 and 'no gates lane' in nogates.stdout
              and s.returncode == 0, nogates.stdout + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        minor, wording = size(feat, 'minor'), size(feat, 'wording')
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'checker', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G28 a minor or wording round with no earlier full round is refused, since the first '
              'round runs in full, and the patch stays full (R1-G1)',
              [minor.returncode, wording.returncode] == [2, 2]
              and 'full round' in minor.stderr and 'round full' in s.stdout
              and s.returncode == 1, minor.stderr + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'live', 'PASS', 'sonnet')
        lane(feat, 'review-a', 'PASS', 'opus')
        lane(feat, 'review-b', 'PASS', 'opus')
        commit(feat, 'a.txt', 'two\n', 'minor fix')
        size(feat, 'minor')
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'checker', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G28b a sized round whose earlier full round had one review model is not clean',
              s.returncode == 1 and 'fewer than two review lanes' in s.stdout, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        full_round(feat)
        gate('record', 'finding', 'F1', 'blocks', *grounds('F1'), '--cmd', 'grep -n one a.txt',
             cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix F1')
        size(feat, 'minor')
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'checker', 'PASS', 'sonnet')
        held = gate('status', cwd=feat)
        gate('record', 'finding', 'F1', 'fixed', *FIXER,
             '--note', 'its sites came back clean', cwd=feat)
        s = gate('status', cwd=feat)
        check('G29 a finding that blocks stays open through a sized round until a later row '
              'closes it', held.returncode == 1 and 'blocking finding F1 is open' in held.stdout
              and s.returncode == 0, held.stdout + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        full_round(feat)
        for n in (2, 3):
            commit(feat, 'a.txt', f'{n}\n', f'minor fix {n}')
            size(feat, 'minor')
            lane(feat, 'gates', 'PASS', 'root')
            lane(feat, 'checker', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G30 a second minor round still rests on the last full round', s.returncode == 0,
              s.stdout)
        commit(feat, 'a.txt', '4\n', 'new behaviour')
        size(feat, 'full', 'the fix adds a new code path')
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'checker', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G30b a round sized full needs its own live and review lanes, not a checker',
              s.returncode == 1 and 'fewer than two review lanes' in s.stdout, s.stdout)
        commit(feat, 'a.txt', '5\n', 'minor fix 5')
        size(feat, 'minor')
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'checker', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G30c a minor round after an unfinished full round rests on that full round, so it '
              'is not clean', s.returncode == 1 and 'full round' in s.stdout, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        bare = gate('record', 'finding', 'F1', 'blocks', *grounds('F1'), cwd=feat).returncode
        new  = [gate('record', 'finding', f'N{i}', b, cwd=feat).returncode
                for i, b in enumerate(('follow-up', 'dropped'))]
        old  = gate('record', 'finding', 'F2', 'act-on', *grounds('F2'), '--cmd', 'grep -n x',
                    cwd=feat)
        gate('record', 'finding', 'F3', 'queue', cwd=feat)
        with open(ledger(main, 'feat', 'feat')) as f:
            results = [line.split('\t')[6] for line in f.read().splitlines()[1:]]
        s = gate('status', cwd=feat)
        check('G31 the buckets are blocks, follow-up and dropped; blocks keeps its command, and '
              'an old bucket name is recorded as its new one',
              bare == 2 and new == [0, 0] and old.returncode == 0
              and results == ['follow-up', 'dropped', 'blocks', 'follow-up']
              and 'blocking finding F2 is open' in s.stdout, f'{results} {s.stdout}')


def g32_receipts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        at    = ['--model', 'sonnet', '--at', head(feat)]
        empty = evidence('')
        inner = os.path.join(feat, 'out.txt')
        with open(inner, 'w') as f:
            f.write('12 passed\n')
        said = [gate('record', 'lane', 'regression', 'PASS', *at, '--cmd', 'pytest -q', *out,
                     cwd=feat)
                for out in ([], ['--out', os.path.join(tmp, 'none.txt')], ['--out', empty],
                            ['--out', inner])]
        check('G32 a lane row refuses an output file that is missing, absent, empty or inside the '
              "branch's worktree", [r.returncode for r in said] == [2, 2, 2, 2]
              and 'output (--out)' in said[0].stderr and 'missing or empty' in said[1].stderr
              and 'missing or empty' in said[2].stderr and 'inside the worktree' in said[3].stderr,
              ''.join(r.stderr for r in said))
        path = gate('lane-checkout', 'live', cwd=feat).stdout.strip()
        held = os.path.join(path, 'out.txt')
        with open(held, 'w') as f:
            f.write('12 passed\n')
        lanes = gate('record', 'lane', 'live', 'PASS', *at, '--cmd', 'drive', '--out', held,
                     cwd=feat)
        gate('lane-remove', 'live', cwd=feat)
        check('G32b a lane row refuses an output file inside a lane checkout, which lane-remove '
              'deletes', lanes.returncode == 2 and 'inside the worktree' in lanes.stderr,
              lanes.stderr)
        out  = ['--out', evidence()]
        bare = gate('record', 'lane', 'regression', 'PASS', *at, *out, cwd=feat)
        rev  = gate('record', 'lane', 'review-a', 'PASS', *at, '--cmd', 'pytest', *out, cwd=feat)
        ok   = gate('record', 'lane', 'review-a', 'PASS', *at, *out, cwd=feat)
        why  = [gate('record', 'lane', 'live', r, *at, '--cmd', 'drive', *out, cwd=feat)
                for r in ('BLOCKED', 'NO-RUNTIME')]
        check('G32c a run lane names its command and a review lane none; BLOCKED and NO-RUNTIME '
              'say why', bare.returncode == 2 and '--cmd' in bare.stderr and rev.returncode == 2
              and 'review lane' in rev.stderr and ok.returncode == 0
              and [r.returncode for r in why] == [2, 2] and all('--note' in r.stderr for r in why),
              bare.stderr + rev.stderr + ok.stderr + ''.join(r.stderr for r in why))
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        log = evidence('pytest -q\n3 passed\n')
        gate('record', 'lane', 'regression', 'PASS', '--model', 'sonnet', '--at', head(feat),
             '--cmd', 'pytest   -q', '--out', log, cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'live', 'NO-RUNTIME', 'opus')
        lane(feat, 'review-a', 'PASS', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        with open(ledger(main, 'feat', 'feat')) as f:
            rows = [ln.split('\t') for ln in f.read().splitlines()]
        digest = hashlib.sha256(b'pytest -q\n3 passed\n').hexdigest()
        s = gate('status', cwd=feat)
        check('G32d a lane row keeps its command, its output file\'s real path and sha256, and '
              'status prints them',
              rows[0][10:] == ['out', 'sha256', 'by', 'exit', 'covers', 'premise', 'tree', 'lane']
              and rows[1][7] == 'pytest -q' and rows[1][10] == os.path.realpath(log)
              and rows[1][11] == digest and s.returncode == 0 and 'cmd: pytest -q' in s.stdout
              and f'out: {os.path.realpath(log)} (sha256 {digest[:12]}, matches)' in s.stdout,
              str(rows[:2]) + s.stdout)
        with open(log, 'a') as f:
            f.write('edited\n')
        moved = gate('status', cwd=feat)
        os.remove(log)
        gone = gate('status', cwd=feat)
        check('G32e an output file changed or gone since its row was written makes the verdict '
              'not clean', moved.returncode == 1 and 'is changed since' in moved.stdout
              and gone.returncode == 1 and 'is gone since' in gone.stdout,
              moved.stdout + gone.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        at   = ['--model', 'sonnet', '--at', head(feat), '--out']
        fail = gate('record', 'lane', 'regression', 'ISSUES', *at, evidence('R1-1: 3 failed\n'),
                    '--cmd', 'pytest -q -n 4', cwd=feat)
        subset = [gate('record', 'lane', 'regression', 'PASS', *at, evidence(), '--cmd', c,
                       cwd=feat)
                  for c in ('pytest -q -n 4 --lf', 'pytest -q -n 0', 'pytest -q tests/a.py')]
        same = gate('record', 'lane', 'regression', 'PASS', *at, evidence(), '--cmd',
                    'pytest  -q -n 4', cwd=feat)
        check('G32f a rerun at a commit whose last row for the lane failed is the identical full '
              'command, never --lf, another worker count or a subset', fail.returncode == 0
              and [r.returncode for r in subset] == [2, 2, 2]
              and all('identical command' in r.stderr for r in subset) and same.returncode == 0,
              ''.join(r.stderr for r in subset) + same.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        old = head(feat)
        lane(feat, 'live', 'PASS', 'sonnet')
        commit(feat, 'test_a.txt', 't\n', 'a test')
        keep = ['record', 'lane', 'live', '--kept-from', old, '--note', 'only a test changed']
        said = [gate(*keep, *more, cwd=feat, env=NOISE) for more in (
            ['--cmd', 'cmp a b'], ['--out', evidence()],
            ['--cmd', 'cmp a b', '--out', evidence()])]
        check('G32g a kept lane takes no --cmd or --out, since gate.py compares the two commits '
              'itself', [r.returncode for r in said] == [2, 2, 2]
              and all('compares the two commits' in r.stderr for r in said),
              ''.join(r.stderr for r in said))
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        h, path = head(feat), ledger(main, 'feat', 'feat')
        pid = gate('status', cwd=feat).stdout.split('patch ')[1].split(',')[0]
        full = subprocess.run('git diff $(git merge-base main HEAD) HEAD | git patch-id --verbatim',
                              shell=True, cwd=feat, capture_output=True,
                              text=True).stdout.split()[0]
        assert full.startswith(pid)
        os.makedirs(os.path.dirname(path))
        old = [['gates', 'root', 'PASS', 'pytest -q'], ['live', 'sonnet', 'NO-RUNTIME', ''],
               ['review-a', 'opus', 'PASS', ''], ['review-b', 'sonnet', 'ISSUES', '']]
        with open(path, 'w') as f:
            f.write('ts\thead\tpatch\tkind\tname\tmodel\tresult\tcmd\tnote\tmain\n')
            for name, model, result, cmd in old:
                f.write('\t'.join(['2026-10-24T00:00:00+00:00', h, full, 'lane', name, model,
                                   result, cmd, '', 'm']) + '\n')
            f.write('\t'.join(['2026-10-24T00:00:00+00:00', h, full, 'finding', 'R1-1', '',
                               'nit', 'grep -n x', '', 'm']) + '\n')
            f.write('\t'.join(['2026-10-24T00:00:00+00:00', h, full, 'finding', 'R1-2', '',
                               'dismissed', '', '', 'm']) + '\n')
        before = gate('status', cwd=feat)
        lane(feat, 'review-b', 'PASS', 'sonnet')
        after = gate('status', cwd=feat)
        with open(path) as f:
            lines = f.read().splitlines()
        check('G32h a ledger written before receipts reads clean with its old buckets, and a new '
              'row appended to it reads its receipt past the old header', before.returncode == 0
              and 'out: none' in before.stdout and after.returncode == 0
              and lines[0].count('\t') == 9 and lines[-1].count('\t') == 17
              and 'matches' in after.stdout.split('review-b')[1].split('\n  ')[1],
              before.stdout + after.stdout)


def g33_findings() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        full_round(feat)
        gate('record', 'finding', 'R1-1', 'blocks', *grounds('R1-1'), '--cmd', 'grep -n one a.txt',
             cwd=feat)
        gate('record', 'finding', 'F9', 'follow-up', cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix R1-1')
        full_round(feat)
        old  = gate('record', 'fix', 'fixer-1', 'fixed', '--model', 'opus', cwd=feat)
        fix  = ['record', 'finding', 'R1-1', 'fixed']
        said = [gate(*fix, *more, cwd=feat) for more in (
            ['--model', 'opus'], ['--by', 'root', '--model', 'opus'],
            ['--by', ' Root ', '--model', 'opus'], ['--by', 'R1-1', '--model', 'opus'],
            ['--by', 'r4-k2', '--model', 'opus'], ['--by', 'F9', '--model', 'opus'],
            ['--by', 'fixer-1'], ['--by', 'fixer-1', '--model', 'gpt'],
            ['--by', 'fixer-1', '--model', 'root'])]
        side = [gate('record', 'finding', 'F8', b, *more, cwd=feat).returncode for b, more in (
            ('follow-up', ['--by', 'fixer-1']), ('dropped', ['--model', 'opus']))]
        check('G33 the fix row is gone, and fixed names a fresh agent and its model: never none, '
              'root, a finding ID\'s shape or a finding in the ledger',
              old.returncode == 2 and 'record finding <id> fixed --by' in old.stderr
              and [r.returncode for r in said] == [2] * 9 and side == [2, 2]
              and 'finding ID' in said[3].stderr and 'finding in this ledger' in said[5].stderr,
              old.stderr + ''.join(r.stderr for r in said))
        ok = gate(*fix, '--by', 'agent-7f3e', '--model', 'Sonnet', '--note', 'sites clean',
                  cwd=feat)
        with open(ledger(main, 'feat', 'feat')) as f:
            row = f.read().splitlines()[-1].split('\t')
        s = gate('status', cwd=feat)
        r = gate('land', message(tmp), cwd=feat)
        body = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        check('G33b fixed --by closes the finding in one row that names its fixer, and the '
              'verdict lists the fix', ok.returncode == 0
              and row[4:7] == ['R1-1', 'sonnet', 'fixed']
              and row[12] == 'agent-7f3e' and s.returncode == 0 and r.returncode == 0
              and '- fix: agent-7f3e, sonnet, closed R1-1' in body, ok.stderr + s.stdout + body)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        kinds = ('lane', 'round', 'finding', 'live-check')
        helps = {k: gate('record', k, '--help', cwd=feat) for k in kinds}
        top   = gate('--help', cwd=feat)
        rec   = gate('record', '--help', cwd=feat)
        run   = gate('run', '--help', cwd=feat)
        grammar = ['run gates [--at SHA] -- <cmd...>', 'run gates [--at SHA] --retry',
                   'record lane <name> --kept-from SHA --note T',
                   'record live-check <id> --note T',
                   'record live-check <id> <VERIFIED|UNREACHED> --at SHA [--note T]',
                   'record finding <id> fixed --by AGENT --model M', 'lane-checkout <name> [<sha>]',
                   'lane-remove <name>', 'GATE_NOISE_PATHS', 'GATE_SAME_BUILD',
                   'record round <full|minor|wording|void> --note T',
                   'record finding <id> blocks --lane LANE --cmd C --premise P [--note T]',
                   'record finding <id> <follow-up|dropped> --lane LANE',
                   'run gates [--at SHA] --retry --infra --note CAUSE',
                   '[--covers LANE ...]', 'fixed --by AGENT --model M [--text]']
        check('G33c --help and each command and record <kind> --help print that grammar',
              all(r.returncode == 0 for r in [top, rec, run, *helps.values()])
              and all(g in top.stdout for g in grammar)
              and '--at SHA --out FILE' in helps['lane'].stdout
              and 'record lane <name> --kept-from SHA --note T' in helps['lane'].stdout
              and 'record round <full|minor|wording|void> --note T' in helps['round'].stdout
              and 'record finding <id> blocks --lane LANE --cmd C --premise P' in
              helps['finding'].stdout and '--retry --infra --note CAUSE' in run.stdout
              and 'record finding <id> fixed --by AGENT --model M' in helps['finding'].stdout
              and 'record live-check <id> <VERIFIED|UNREACHED> --at SHA' in
              helps['live-check'].stdout
              and 'run gates [--at SHA] --retry' in run.stdout
              and all(k in rec.stdout for k in helps) and 'run' in top.stdout,
              top.stdout + rec.stdout + run.stdout + ''.join(r.stdout for r in helps.values()))


def g34_lanes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        first = head(feat)
        commit(feat, 'a.txt', 'two\n', 'second')
        r = gate('lane-checkout', 'gates', cwd=feat)
        path = r.stdout.strip()
        want = os.path.realpath(feat) + '.lanes' + os.sep + 'gates'
        listed = sh('git', 'worktree', 'list', '--porcelain', cwd=main)
        block = listed.split(f'worktree {path}\n')[1].split('\n\n')[0] if path in listed else ''
        check('G34 lane-checkout makes a detached checkout of the head beside the branch\'s '
              'worktree and prints only its path', r.returncode == 0 and path == want
              and head(path) == head(feat) and 'detached' in block, r.stdout + r.stderr + listed)
        at = gate('lane-checkout', 'base', first, cwd=feat)
        again = gate('lane-checkout', 'gates', cwd=feat)
        bad = [gate('lane-checkout', n, cwd=feat).returncode for n in ('../x', 'a/b', '.hid', '')]
        s = gate('status', cwd=feat)
        check('G34b lane-checkout takes a commit, refuses a checkout already out or a name that '
              'is not one path segment, and status lists the checkouts still out',
              at.returncode == 0 and head(at.stdout.strip()) == first and again.returncode == 2
              and 'lane-remove gates' in again.stderr and bad == [2, 2, 2, 2]
              and 'lane checkout still out' in s.stdout and 'lane-remove base' in s.stdout,
              at.stderr + again.stderr + s.stdout)
        with open(os.path.join(path, 'cache.txt'), 'w') as f:
            f.write('scratch\n')
        gone = gate('lane-remove', 'gates', cwd=feat)
        with open(os.path.join(at.stdout.strip(), 'a.txt'), 'w') as f:
            f.write('edited\n')
        edit = gate('lane-remove', 'base', cwd=feat)
        none = gate('lane-remove', 'gates', cwd=feat)
        left = sh('git', 'worktree', 'list', cwd=main)
        check('G34c lane-remove prints the checkout\'s git status, removes it past untracked '
              'files, exits 1 naming a tracked file the lane changed, and refuses a lane with no '
              'checkout', gone.returncode == 0 and '?? cache.txt' in gone.stdout
              and not os.path.exists(path) and edit.returncode == 1 and 'a.txt' in edit.stderr
              and not os.path.exists(at.stdout.strip()) and none.returncode == 2
              and '.lanes' not in left and not os.path.exists(os.path.dirname(path)),
              gone.stdout + gone.stderr + edit.stdout + edit.stderr + none.stderr + left)
        sh('git', 'checkout', '-q', '--detach', cwd=feat)
        said = [gate('lane-checkout', 'x', cwd=at).returncode for at in (main, feat)]
        check('G34d lane-checkout refuses main\'s worktree and a detached HEAD', said == [2, 2],
              str(said))


def rows_of(main: str, kind: str = '', name: str = '') -> list[dict]:
    """The rows of feat's ledger, as dicts, of `kind` and `name` when given."""
    with open(ledger(main, 'feat', 'feat')) as f:
        lines = [ln.split('\t') for ln in f.read().splitlines()]
    rows = [dict(zip(lines[0], ln)) for ln in lines[1:]]
    return [r for r in rows if kind in ('', r['kind']) and name in ('', r['name'])]


def reviews(feat: str) -> None:
    """The live and review lanes of a clean full round, leaving gates to the test."""
    lane(feat, 'live', 'NO-RUNTIME', 'opus')
    lane(feat, 'review-a', 'PASS', 'opus')
    lane(feat, 'review-b', 'PASS', 'sonnet')


def g35_run_gates() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        reviews(feat)
        ok   = gate('run', 'gates', '--', 'sh', '-c', 'echo 3 passed; git rev-parse HEAD', cwd=feat)
        row  = rows_of(main, 'lane', 'gates')[-1]
        path = os.path.realpath(feat) + '.lanes' + os.sep + 'gates-'
        with open(row['out']) as f:
            said = f.read()
        s = gate('status', cwd=feat)
        check('G35 run gates runs the command in a checkout of its own, removed after, and records '
              'its command, exit code, output file and hash, as root', ok.returncode == 0
              and row['cmd'] == "sh -c 'echo 3 passed; git rev-parse HEAD'" and row['exit'] == '0'
              and row['result'] == 'PASS' and row['model'] == 'root'
              and '3 passed' in said and f'in {path}' in said and head(feat) in said
              and not os.path.exists(os.path.dirname(path))
              and row['sha256'] == hashlib.sha256(said.encode()).hexdigest()
              and '.runs' in row['out'] and s.returncode == 0
              and "cmd: sh -c 'echo 3 passed; git rev-parse HEAD' (exit 0)" in s.stdout,
              ok.stdout + ok.stderr + s.stdout)
        flag = os.path.join(tmp, 'flag')
        flaky = ['sh', '-c', f'test -f {flag}']
        fail = gate('run', 'gates', '--', *flaky, cwd=feat)
        s    = gate('status', cwd=feat)
        again = gate('run', 'gates', '--', *flaky, cwd=feat)
        other = gate('run', 'gates', '--', 'sh', '-c', 'exit 0', cwd=feat)
        held  = gate('status', cwd=feat)
        check('G35b a failed command makes the gates lane not clean though another passed, its '
              'plain rerun is refused for --retry, and a different command never clears it',
              fail.returncode == 1 and rows_of(main, 'lane', 'gates')[-2]['result'] == 'ISSUES'
              and s.returncode == 1 and f'test -f {flag}' in s.stdout and 'is ISSUES' in s.stdout
              and again.returncode == 2 and '--retry' in again.stderr and other.returncode == 0
              and held.returncode == 1, s.stdout + again.stderr + held.stdout)
        cmd   = gate('run', 'gates', '--retry', '--', 'true', cwd=feat)
        open(flag, 'w').close()
        retry = gate('run', 'gates', '--retry', cwd=feat)
        last  = rows_of(main, 'lane', 'gates')[-1]
        s     = gate('status', cwd=feat)
        none  = gate('run', 'gates', '--retry', cwd=feat)
        check('G35c --retry takes no command, reruns the failed one identically, and its pass '
              'makes the lane clean; with no failed command it refuses',
              cmd.returncode == 2 and retry.returncode == 0
              and last['cmd'] == shlex.join(flaky)
              and last['result'] == 'PASS' and s.returncode == 0 and none.returncode == 2,
              cmd.stderr + retry.stdout + retry.stderr + s.stdout + none.stderr)
        twice = ['sh', '-c', 'exit 4']
        gate('run', 'gates', '--', *twice, cwd=feat)
        second = gate('run', 'gates', '--retry', cwd=feat)
        last   = rows_of(main, 'lane', 'gates')[-1]
        s      = gate('status', cwd=feat)
        third  = gate('run', 'gates', '--retry', cwd=feat)
        plain  = gate('run', 'gates', '--', *twice, cwd=feat)
        check('G35d a second failure of the retried command is BLOCKED, and nothing reruns it at '
              'that head', second.returncode == 1 and last['result'] == 'BLOCKED'
              and last['exit'] == '4' and 'never a flake' in last['note'] and s.returncode == 1
              and third.returncode == 2 and plain.returncode == 2
              and 'never a flake' in plain.stderr, second.stdout + s.stdout + plain.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        reviews(feat)
        bin_ = os.path.join(tmp, 'bin')
        os.makedirs(bin_)
        miss = gate('run', 'gates', '--', 'gate-test-tool', '--all', cwd=feat)
        row  = rows_of(main, 'lane', 'gates')[-1]
        with open(os.path.join(bin_, 'gate-test-tool'), 'w') as f:
            f.write('#!/bin/sh\necho ok\n')
        os.chmod(os.path.join(bin_, 'gate-test-tool'), 0o755)
        env  = {**os.environ, 'PATH': bin_ + os.pathsep + os.environ['PATH']}
        s    = gate('status', cwd=feat)
        rerun = gate('run', 'gates', '--', 'gate-test-tool', '--all', cwd=feat, env=env)
        after = gate('status', cwd=feat)
        check('G35e a command whose program is missing is BLOCKED with exit none, naming it, and '
              'runs again once the program is there', miss.returncode == 1
              and row['result'] == 'BLOCKED' and row['exit'] == 'none'
              and 'gate-test-tool' in row['note'] and s.returncode == 1
              and rerun.returncode == 0 and after.returncode == 0,
              miss.stdout + miss.stderr + s.stdout + rerun.stderr + after.stdout)
        with open(os.path.join(bin_, 'gate-test-flaky'), 'w') as f:
            f.write('#!/bin/sh\nexit 1\n')
        os.chmod(os.path.join(bin_, 'gate-test-flaky'), 0o755)
        first = gate('run', 'gates', '--', 'gate-test-flaky', cwd=feat, env=env)
        lost  = gate('run', 'gates', '--retry', cwd=feat)
        owed  = gate('run', 'gates', '--retry', cwd=feat, env=env)
        last  = rows_of(main, 'lane', 'gates')[-1]
        check('G35i a retry whose program was missing is no run, so --retry is still owed, and its '
              'second failure is BLOCKED', first.returncode == 1 and lost.returncode == 1
              and '--retry' in rows_of(main, 'lane', 'gates')[-2]['note']
              and owed.returncode == 1 and last['exit'] == '1' and last['result'] == 'BLOCKED',
              lost.stdout + owed.stdout + owed.stderr)
        typed = [gate('record', 'lane', 'gates', *more, cwd=feat) for more in (
            ['PASS', '--model', 'root', '--at', head(feat), '--cmd', 'pytest', '--out',
             evidence()], ['gap', '--model', 'root'])]
        spaced = gate('run', 'gates', '--', 'echo', 'a  b', cwd=feat)
        bare   = gate('run', 'gates', cwd=feat)
        check('G35f a typed gates row is refused, naming gate.py run gates; a command needs -- '
              'and one ledger line', [r.returncode for r in typed] == [2, 2]
              and all('gate.py run gates' in r.stderr for r in typed)
              and spaced.returncode == 2 and bare.returncode == 2,
              ''.join(r.stderr for r in typed) + spaced.stderr + bare.stderr)
        gate('run', 'gates', '--', 'sh', '-c', 'echo edited > a.txt', cwd=feat)
        clean = gate('run', 'gates', '--', 'sh', '-c', 'git diff --exit-code', cwd=feat)
        check('G35g a check that edits a tracked file leaves the next run\'s checkout untouched',
              clean.returncode == 0, clean.stdout + clean.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        h, path = head(feat), ledger(main, 'feat', 'feat')
        full = subprocess.run('git diff $(git merge-base main HEAD) HEAD | git patch-id --verbatim',
                              shell=True, cwd=feat, capture_output=True,
                              text=True).stdout.split()[0]
        os.makedirs(os.path.dirname(path))
        old = [['gates', 'root', 'ISSUES', 'pytest -q'], ['gates', 'root', 'PASS', 'pytest --lf'],
               ['live', 'sonnet', 'PASS', ''], ['review-a', 'opus', 'PASS', ''],
               ['review-b', 'sonnet', 'PASS', '']]
        with open(path, 'w') as f:
            f.write('ts\thead\tpatch\tkind\tname\tmodel\tresult\tcmd\tnote\tmain\n')
            for name, model, result, cmd in old:
                f.write('\t'.join(['2026-10-24T00:00:00+00:00', h, full, 'lane', name, model,
                                   result, cmd, '', 'm']) + '\n')
        s = gate('status', cwd=feat)
        check('G35h a ledger whose gates rows were typed reads as it did: its latest gates row '
              'decides, and a live PASS with no live checks declared counts',
              s.returncode == 0, s.stdout)


def g36_keep() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        old = head(feat)
        lane(feat, 'live', 'PASS', 'sonnet')
        lane(feat, 'regression', 'PASS', 'sonnet')
        os.makedirs(os.path.join(feat, 'src'))
        commit(feat, os.path.join('src', 'app.py'), 'print(2)\n', 'code')
        commit(feat, 'notes.md', 'docs\n', 'docs')
        keep = ['record', 'lane', 'live', '--kept-from', old, '--note', 'only docs changed']
        bare = gate(*keep, cwd=feat)
        part = gate(*keep, cwd=feat, env={**os.environ, 'GATE_NOISE_PATHS': '*.md'})
        check('G36 a keep whose commits differ in a path no GATE_NOISE_PATHS pathspec matches is '
              'refused, naming those paths and --at', bare.returncode == 2
              and 'src/app.py' in bare.stderr and '--at' in bare.stderr
              and part.returncode == 2 and 'src/app.py' in part.stderr
              and 'notes.md' not in part.stderr.split('pathspec:')[1]
              and 'GATE_SAME_BUILD is unset' in part.stderr, bare.stderr + part.stderr)
        noise = {**os.environ, 'GATE_NOISE_PATHS': '*.md src'}
        kept  = gate(*keep, cwd=feat, env=noise)
        row   = rows_of(main, 'lane', 'live')[-1]
        with open(row['out']) as f:
            said = f.read()
        s = gate('status', cwd=feat)
        check('G36b a keep whose every changed path is noise is kept, its receipt the diff gate.py '
              'ran', kept.returncode == 0 and row['head'] == old
              and row['cmd'] == f'git diff --name-only {old} {head(feat)}'
              and 'src/app.py' in said and 'notes.md' in said
              and row['sha256'] == hashlib.sha256(said.encode()).hexdigest()
              and 'every changed path is noise' in row['note'] and 'matches' in s.stdout,
              kept.stderr + str(row) + said)
        script = os.path.join(tmp, 'same.sh')
        with open(script, 'w') as f:
            f.write('#!/bin/sh\necho "compared $1 $2"\nexit "$CODE"\n')
        os.chmod(script, 0o755)
        same  = ['record', 'lane', 'regression', '--kept-from', old, '--note', 'same binary']
        built = {**os.environ, 'GATE_SAME_BUILD': script}
        diff  = gate(*same, cwd=feat, env={**built, 'CODE': '1'})
        ok    = gate(*same, cwd=feat, env={**built, 'CODE': '0'})
        row   = rows_of(main, 'lane', 'regression')[-1]
        with open(row['out']) as f:
            said = f.read()
        check('G36c GATE_SAME_BUILD given the two commits decides a keep the noise paths do not: '
              'a nonzero exit refuses, naming the paths, and exit 0 keeps with its output',
              diff.returncode == 2 and 'src/app.py' in diff.stderr and 'exited 1' in diff.stderr
              and ok.returncode == 0 and row['cmd'] == f'{script} {old} {head(feat)}'
              and f'compared {old} {head(feat)}' in said
              and 'GATE_SAME_BUILD exited 0' in row['note'],
              diff.stderr + ok.stderr + said)


def g37_live_checks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        h    = head(feat)
        live = ['record', 'lane', 'live']
        args = ['--model', 'sonnet', '--at', h, '--cmd', 'drive', '--out']
        none = gate(*live, 'PASS', *args, evidence(), cwd=feat)
        chk  = ['record', 'live-check']
        bad  = [gate(*chk, *more, cwd=feat).returncode for more in (
            ['L1'], ['L1', '--note', 'n', '--at', h], ['L9', 'VERIFIED', '--at', h],
            ['VERIFIED', '--note', 'n'], ['L1', 'PASSED', '--at', h])]
        gate(*chk, 'L1', '--note', 'open a.txt; it reads one', cwd=feat)
        gate(*chk, 'L2', '--note', 'save a.txt; it reads two', cwd=feat)
        more = [gate(*chk, 'L1', 'VERIFIED', cwd=feat).returncode,
                gate(*chk, 'L2', 'UNREACHED', '--at', h, cwd=feat).returncode]
        check('G37 a live check is declared with --note and no commit, then recorded VERIFIED or '
              'UNREACHED --at a commit; a live PASS with none declared is refused',
              none.returncode == 2 and 'declares none' in none.stderr and bad == [2] * 5
              and more == [2, 2], none.stderr + str(bad) + str(more))
        gate(*chk, 'L1', 'VERIFIED', '--at', h, cwd=feat)
        half = gate(*live, 'PASS', *args, evidence(), cwd=feat)
        gate(*chk, 'L2', 'UNREACHED', '--at', h, '--note', 'no display to drive the save',
             cwd=feat)
        unre = [gate(*live, r, *args, evidence(), cwd=feat) for r in ('PASS', 'ISSUES')]
        blk  = gate(*live, 'BLOCKED', *args, evidence(), '--note', 'no display', cwd=feat)
        gate('run', 'gates', '--', 'true', cwd=feat)
        lane(feat, 'review-a', 'PASS', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G37b a live PASS needs every declared check VERIFIED at its commit, naming the '
              'others; an UNREACHED check takes only BLOCKED, and the verdict is not clean',
              half.returncode == 2 and 'L2' in half.stderr and 'L1' not in half.stderr
              and [r.returncode for r in unre] == [2, 2]
              and all('UNREACHED' in r.stderr for r in unre) and blk.returncode == 0
              and s.returncode == 1 and 'live-check L2: UNREACHED' in s.stdout,
              half.stderr + ''.join(r.stderr for r in unre) + blk.stderr + s.stdout)
        gate(*chk, 'L2', 'VERIFIED', '--at', h, '--note', 'drove it on a display', cwd=feat)
        ok = gate(*live, 'PASS', *args, evidence(), cwd=feat)
        s  = gate('status', cwd=feat)
        check('G37c a later VERIFIED row supersedes UNREACHED, and with every check VERIFIED the '
              'live PASS is taken and clean', ok.returncode == 0 and s.returncode == 0
              and 'live-check L1: VERIFIED' in s.stdout and 'live-check L2: VERIFIED' in s.stdout,
              ok.stderr + s.stdout)
        gate(*chk, 'L3', '--note', 'a late check', cwd=feat)
        late = gate('status', cwd=feat)
        gate(*chk, 'L3', 'UNREACHED', '--at', h, '--note', 'no route', cwd=feat)
        gone = gate('status', cwd=feat)
        msg  = message(tmp)
        land = gate('land', msg, cwd=feat)
        check('G37d a check declared after the live PASS makes the verdict not clean until it is '
              'VERIFIED, and one UNREACHED reads the live lane as BLOCKED, so land refuses',
              late.returncode == 1 and 'L3 have no VERIFIED row' in late.stdout
              and gone.returncode == 1 and 'lane live is BLOCKED' in gone.stdout
              and land.returncode == 1, late.stdout + gone.stdout + land.stderr)
        gate(*chk, 'L3', 'VERIFIED', '--at', h, cwd=feat)
        land = gate('land', msg, cwd=feat)
        body = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        check('G37e the verdict block lists each live check and its state, and no gates checkout '
              'is left to remove', land.returncode == 0
              and f'- live-check L2: VERIFIED at {h[:8]} (save a.txt; it reads two)' in body
              and 'lane-remove' not in land.stdout, land.stderr + body + land.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        first = head(feat)
        commit(feat, 'a.txt', 'two\n', 'second')
        gate('record', 'live-check', 'L1', '--note', 'n', cwd=feat)
        stale = gate('record', 'live-check', 'L1', 'VERIFIED', '--at', first, cwd=feat)
        nort  = lane(feat, 'live', 'NO-RUNTIME', 'opus')
        gate('record', 'live-check', 'L1', 'VERIFIED', '--at', head(feat), cwd=feat)
        sh('git', 'commit', '-q', '--allow-empty', '-m', 'same patch', cwd=feat)
        other = gate('record', 'lane', 'live', 'PASS', '--model', 'sonnet', '--at', head(feat),
                     '--cmd', 'drive', '--out', evidence(), cwd=feat)
        check('G37f a check is recorded only at a commit with the current patch, counts only for '
              'a live lane at that commit, and NO-RUNTIME is refused once a check is declared '
              '(R1-G5)', stale.returncode == 2
              and nort.returncode == 2 and 'runtime surface' in nort.stderr
              and other.returncode == 2 and 'L1' in other.stderr,
              stale.stderr + nort.stderr + other.stderr)



def g38_rounds() -> None:
    blocks = ['record', 'finding', 'R1-1', 'blocks', *grounds('R1-1'), '--cmd', 'grep -n one a.txt']
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        first = head(feat)
        lane(feat, 'gates', 'PASS', 'root')
        gate('record', 'live-check', 'L1', '--note', 'a.txt reads two', cwd=feat)
        lane(feat, 'live', 'ISSUES', 'sonnet')
        lane(feat, 'review-a', 'ISSUES', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        gate(*blocks, cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix R1-1')
        size(feat, 'minor', 'a one-line fix')
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'checker', 'PASS', 'sonnet')
        gate('record', 'finding', 'R1-1', 'fixed', *FIXER, cwd=feat)
        held = gate('status', cwd=feat)
        gate('record', 'live-check', 'L1', 'VERIFIED', '--at', head(feat), cwd=feat)
        s = gate('status', cwd=feat)
        r = gate('land', message(tmp), cwd=feat)
        body = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        check('G38g the verdict block shows each live check at the live lane\'s commit and at the '
              'checker\'s', r.returncode == 0 and f'- live-check L1: not recorded at {first[:8]}, '
              f'VERIFIED at {head(feat)[:8]} (a.txt reads two)' in body, r.stderr + body)
        check('G38 a minor round rests on the last full round as it was, failed live lane and '
              'findings included: the checker driving the live checks it left failed makes it '
              'clean, and with no drive and no live pass anywhere it is not',
              held.returncode == 1 and "live lane, at patch" in held.stdout
              and 'did not pass' in held.stdout
              and s.returncode == 0 and 'is not clean' not in held.stdout,
              held.stdout + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        full_round(feat)
        lane(feat, 'regression', 'BLOCKED', 'sonnet')
        commit(feat, 'a.txt', 'two\n', 'minor fix')
        size(feat, 'minor', 'a one-line fix')
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'checker', 'PASS', 'sonnet')
        held = gate('status', cwd=feat)
        ran  = ['record', 'lane', 'checker', 'PASS', '--model', 'sonnet', '--at', head(feat),
                '--cmd', 'run-checker --all', '--out', evidence()]
        gate(*ran, '--covers', 'regression', cwd=feat)
        s = gate('status', cwd=feat)
        check('G38b a full-round lane that was BLOCKED is not a pass for a minor round until it '
              'reruns at the new patch or the checker covers it', held.returncode == 1
              and 'lane regression of the full round' in held.stdout
              and '--covers regression' in held.stdout and s.returncode == 0,
              held.stdout + s.stdout)
        bad = [gate('record', 'lane', 'regression', 'PASS', '--model', 'sonnet', '--at',
                    head(feat), '--cmd', 'r', '--out', evidence(), '--covers', 'live',
                    cwd=feat).returncode,
               gate(*ran, '--covers', 'gates', cwd=feat).returncode,
               gate('record', 'finding', 'R9-1', 'follow-up', '--text', cwd=feat).returncode]
        check('G38c --covers goes only on a checker row and names a full-round lane, and --text '
              'only on a fixed row', bad == [2, 2, 2], str(bad))
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        full_round(feat)
        gate(*blocks, cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix R1-1')
        size(feat, 'minor', 'a one-line fix')
        lane(feat, 'gates', 'PASS', 'root')
        gate('record', 'finding', 'R1-1', 'fixed', *FIXER, cwd=feat)
        commit(feat, 'b.txt', 'reworded\n', 'reword')
        size(feat, 'wording', 'a message reworded')
        lane(feat, 'gates', 'PASS', 'root')
        s = gate('status', cwd=feat)
        check('G38d a fixed row recorded at a minor patch with no checker there closes nothing, '
              'whatever round follows', s.returncode == 1
              and "R1-1's fixed row" in s.stdout and 'no checker lane' in s.stdout, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        full_round(feat)
        gate(*blocks, cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'reword the line')
        size(feat, 'wording', 'only the line\'s wording changed')
        lane(feat, 'gates', 'PASS', 'root')
        typed = gate('record', 'finding', 'R1-1', 'fixed', *FIXER, cwd=feat)
        held  = gate('status', cwd=feat)
        gate('record', 'finding', 'R1-1', 'fixed', *FIXER, '--text', cwd=feat)
        s = gate('status', cwd=feat)
        check('G38e a wording round closes only a finding whose sites are text (--text)',
              typed.returncode == 2 and '--text' in typed.stderr and held.returncode == 1
              and s.returncode == 0, typed.stderr + held.stdout + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        full_round(feat)
        gate(*blocks, cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix R1-1')
        gate('record', 'finding', 'R1-1', 'fixed', *FIXER, cwd=feat)
        size(feat, 'wording', 'sized after the fix row')
        lane(feat, 'gates', 'PASS', 'root')
        held = gate('status', cwd=feat)
        again = gate('record', 'finding', 'R1-1', 'fixed', *FIXER, '--text', cwd=feat)
        s = gate('status', cwd=feat)
        check('G38f a fixed row its round does not bear out reads as still open, and a fixed row '
              'that is borne out replaces it', held.returncode == 1 and "R1-1's fixed row" in
              held.stdout and again.returncode == 0 and s.returncode == 0,
              held.stdout + again.stderr + s.stdout)



def g39_premises() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        cmd  = ['--cmd', 'grep -n one a.txt']
        bare = gate('record', 'finding', 'R1-1', 'blocks', *cmd, cwd=feat)
        side = gate('record', 'finding', 'R1-2', 'follow-up', '--premise', 'p', cwd=feat)
        check('G39 a blocking finding names its premise, and only a blocking one takes it',
              bare.returncode == 2 and '--premise' in bare.stderr and side.returncode == 2,
              bare.stderr + side.stderr)
        premise = ['--premise', 'The cache is rebuilt on every save.']
        gate('record', 'finding', 'R1-1', 'blocks', *cmd, *premise, cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        gate('record', 'finding', 'R2-1', 'blocks', *cmd, *premise, cwd=feat)
        one = gate('status', cwd=feat).stdout
        commit(feat, 'a.txt', 'three\n', 'fix 2')
        gate('record', 'finding', 'R3-4', 'blocks', *cmd, '--premise',
             'the cache is  rebuilt on every save', cwd=feat)
        two = gate('status', cwd=feat).stdout
        check('G39b a new ID naming the same premise is a failed fix of it, compared without case, '
              'spacing or a final period, and the second says STOP whatever the IDs',
              '(R1-1, R2-1): 1 failed correction' in one and 'STOP' not in one
              and '(R1-1, R2-1, R3-4): 2 failed correction' in two and 'STOP' in two,
              one + two)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        cmd = ['--cmd', 'grep -n one a.txt']
        gate('record', 'finding', 'R1-1', 'blocks', *cmd, '--premise', 'first', cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        gate('record', 'finding', 'R1-1', 'blocks', *cmd, '--premise', 'second', cwd=feat)
        s = gate('status', cwd=feat).stdout
        commit(feat, 'a.txt', 'three\n', 'fix 2')
        gate('record', 'finding', 'R1-1', 'blocks', *cmd, '--premise', 'second', cwd=feat)
        t = gate('status', cwd=feat).stdout
        check('G39c each blocking row counts against the premise it names, so the same ID back '
              'under a new premise counts under that premise (R1-G9)',
              'failed correction' not in s
              and 'premise "second" (R1-1): 1 failed correction' in t
              and 'premise "first"' not in t, s + t)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        path = ledger(main, 'feat', 'feat')
        os.makedirs(os.path.dirname(path))
        heads = []
        for n in range(3):
            commit(feat, 'a.txt', f'{n}\n', f'fix {n}')
            heads.append(head(feat))
        with open(path, 'w') as f:
            f.write('ts\thead\tpatch\tkind\tname\tmodel\tresult\tcmd\tnote\tmain\n')
            for n, h in enumerate(heads):
                f.write('\t'.join(['2026-10-24T00:00:00+00:00', h, f'p{n}', 'finding', 'F1', '',
                                   'act-on', 'grep -n x', '', 'm']) + '\n')
            f.write('\t'.join(['2026-10-24T00:00:00+00:00', heads[0], 'p0', 'finding', 'F2', '',
                               'act-on', 'grep -n y', '', 'm']) + '\n')
        s = gate('status', cwd=feat).stdout
        check('G39d a ledger written before premises keeps its per-ID count',
              'finding F1: 2 failed correction(s)' in s and 'F2' not in s.split('verdict')[0]
              and 'premise "' not in s, s)


def g40_void() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'live', 'PASS', 'sonnet')
        lane(feat, 'review-a', 'PASS', 'opus')
        lane(feat, 'regression', 'ISSUES', 'sonnet')
        gate('record', 'finding', 'R1-1', 'blocks', '--cmd', 'grep -n x', *grounds('R1-1'),
             cwd=feat)
        gate('record', 'finding', 'R1-2', 'dropped', '--note', 'a misreading', cwd=feat)
        bare = gate('record', 'round', 'void', cwd=feat)
        void = gate('record', 'round', 'void', '--note', 'the operator stopped the round', cwd=feat)
        s = gate('status', cwd=feat)
        subset = gate('record', 'lane', 'regression', 'PASS', '--model', 'sonnet', '--at',
                      head(feat), '--cmd', 'run-regression --lf', '--out', evidence(), cwd=feat)
        check('G40 record round void backs out of a round: its lane, live-check result and '
              'sorted finding rows go, but the gates runs, a blocking finding and the identical '
              'rerun rule stay', bare.returncode == 2 and void.returncode == 0
              and s.returncode == 1 and 'no live lane ran' in s.stdout
              and 'fewer than two review lanes' in s.stdout and 'gates   ' in s.stdout
              and 'blocking finding R1-1 is open' in s.stdout
              and 'round voided at' in s.stdout and 'review-a' not in s.stdout
              and subset.returncode == 2, bare.stderr + s.stdout + subset.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        full_round(feat)
        commit(feat, 'a.txt', 'two\n', 'minor fix')
        size(feat, 'minor')
        lane(feat, 'gates', 'PASS', 'root')
        lane(feat, 'checker', 'ISSUES', 'sonnet')
        gate('record', 'round', 'void', '--note', 'stopped mid-round', cwd=feat)
        held = gate('status', cwd=feat)
        lane(feat, 'checker', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        r = gate('land', message(tmp), cwd=feat)
        body = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        check('G40b a void keeps the round\'s size and voids only its own patch\'s rows, and the '
              'landed verdict lists it', held.returncode == 1 and 'round minor' in held.stdout
              and 'checker lane at this patch' in held.stdout and s.returncode == 0
              and r.returncode == 0 and '- round voided at' in body
              and '- round: minor' in body
              and 'review-a: PASS' in body, held.stdout + s.stdout + r.stderr + body)


def g41_checker_checks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'gates', 'PASS', 'root')
        gate('record', 'live-check', 'L1', '--note', 'a.txt reads two', cwd=feat)
        lane(feat, 'live', 'ISSUES', 'sonnet')
        lane(feat, 'review-a', 'PASS', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        commit(feat, 'a.txt', 'two\n', 'minor fix')
        size(feat, 'minor')
        lane(feat, 'gates', 'PASS', 'root')
        args = ['record', 'lane', 'checker', '--model', 'sonnet', '--at', head(feat), '--cmd',
                'drive', '--out']
        gate(*args[:3], 'PASS', *args[3:], evidence(), cwd=feat)
        gate('record', 'live-check', 'L1', 'UNREACHED', '--at', head(feat), '--note',
             'no display', cwd=feat)
        late = gate('status', cwd=feat)
        said = gate(*args[:3], 'PASS', *args[3:], evidence(), cwd=feat)
        blk  = gate(*args[:3], 'BLOCKED', *args[3:], evidence(), '--note', 'no display', cwd=feat)
        check('G41 a live check UNREACHED at the checker\'s commit makes the checker BLOCKED: the '
              'verdict reads it so, and a checker PASS there is refused',
              late.returncode == 1 and 'lane checker is BLOCKED' in late.stdout
              and said.returncode == 2 and 'checker lane BLOCKED' in said.stderr
              and blk.returncode == 0, late.stdout + said.stderr + blk.stderr)


def old_row(main: str, name: str, result: str, out: str) -> None:
    """Append to feat's ledger a copy of lane `name`'s last row with `result` and receipt `out`,
    as a row that gate.py's own refusals did not write, in an older ledger or by hand."""
    path = ledger(main, 'feat', 'feat')
    with open(path) as f:
        lines = f.read().splitlines()
    cols = lines[0].split('\t')
    row  = [dict(zip(cols, ln.split('\t'))) for ln in lines[1:]]
    last = [r for r in row if (r['kind'], r['name']) == ('lane', name)][-1]
    with open(out, 'rb') as f:
        last.update(result=result, out=out, sha256=hashlib.sha256(f.read()).hexdigest())
    with open(path, 'a') as f:
        f.write('\t'.join(last[c] for c in cols) + '\n')


def reviewed(feat: str, a: str = 'PASS', b: str = 'PASS') -> None:
    """Two review lanes on two models at the head, with results `a` and `b`."""
    lane(feat, 'review-a', a, 'opus')
    lane(feat, 'review-b', b, 'sonnet')


def g42_round_one() -> None:
    """The first review round's blocking findings, each from the reviewer's repro."""
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        h = head(feat)
        gate('record', 'live-check', 'L1', '--note', 'save, reload, still there', cwd=feat)
        gate('record', 'live-check', 'L1', 'UNREACHED', '--at', h, '--note', 'no account',
             cwd=feat)
        nort = lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        reviewed(feat)
        lane(feat, 'gates', 'PASS', 'root')
        s = gate('status', cwd=feat)
        check('R1-G5 a declared live check means a runtime surface: NO-RUNTIME is refused, and the '
              'verdict is not clean', nort.returncode == 2 and 'runtime surface' in nort.stderr
              and s.returncode == 1, nort.stderr + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        reviewed(feat)
        fail = ['run', 'gates', '--', 'sh', '-c', 'exit 1']
        gate(*fail, cwd=feat)
        gate('run', 'gates', '--retry', cwd=feat)
        sh('git', 'commit', '-q', '--amend', '--no-edit', '-m', 'reworded', cwd=feat)
        again = gate(*fail, cwd=feat)
        retry = gate('run', 'gates', '--retry', cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        s = gate('status', cwd=feat)
        check('R1-G6 an amend that keeps the tree keeps a BLOCKED gates command and its used '
              'retry, so the verdict is not clean', again.returncode == 2
              and 'BLOCKED' in again.stderr and retry.returncode == 2 and s.returncode == 1
              and "`sh -c 'exit 1'` is BLOCKED" in s.stdout, again.stderr + s.stdout)
        commit(main, 'b.txt', 'main\n', 'main moves')
        sh('git', 'rebase', '-q', 'main', cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        s = gate('status', cwd=feat)
        check('R1-G6b a failed gates command stays failed for the patch until it passes at a later '
              'head: a rebase, a new tree with the same patch, that runs other commands is not '
              'clean', s.returncode == 1 and "sh -c 'exit 1'" in s.stdout, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        gate('run', 'gates', '--', 'sh', '-c', 'echo built > gen.out', cwd=feat)
        commit(feat, 'b.txt', 'b\n', 'second')
        r = gate('run', 'gates', '--', 'test', '-f', 'gen.out', cwd=feat)
        check('R1-G10 a gates run tests the commit alone: a file an earlier run left is gone',
              r.returncode == 1 and 'ISSUES' in r.stdout, r.stdout + r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        reviewed(feat, 'BLOCKED', 'BLOCKED')
        lane(feat, 'gates', 'PASS', 'root')
        commit(feat, 'a.txt', 'two\n', 'minor')
        size(feat, 'minor')
        cov = gate('record', 'lane', 'checker', 'PASS', '--model', 'sonnet', '--at', head(feat),
                   '--cmd', 'ran it', '--out', evidence(), '--covers', 'review-a', 'review-b',
                   cwd=feat)
        lane(feat, 'checker', 'PASS', 'sonnet')
        lane(feat, 'gates', 'PASS', 'root')
        s = gate('status', cwd=feat)
        check('R1-G7 a checker covers no review lane, and BLOCKED reviews never read the change, '
              'so the verdict is not clean', cov.returncode == 2 and 'one model' in cov.stderr
              and s.returncode == 1 and 'never read the change' in s.stdout,
              cov.stderr + s.stdout)
        wording = size(feat, 'wording', 'a typo')
        check('R1-G3 a wording round after a full round with a BLOCKED lane is refused, since it '
              'runs the gates lane alone', wording.returncode == 2
              and 'gates lane alone' in wording.stderr, wording.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        lane(feat, 'review-a', 'PASS', 'opus')
        gate('record', 'lane', 'review-b', 'gap', '--model', 'sonnet', '--note', 'no commit',
             cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        commit(feat, 'a.txt', 'two\n', 'minor')
        size(feat, 'minor')
        lane(feat, 'checker', 'PASS', 'sonnet')
        lane(feat, 'gates', 'PASS', 'root')
        held = gate('status', cwd=feat)
        lane(feat, 'review-b', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('R1-G2 a gap review is cleared by its rerun at the new patch, and only by that',
              held.returncode == 1 and 'review-b' in held.stdout and s.returncode == 0,
              held.stdout + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        gate('record', 'live-check', 'L1', '--note', 'scenario', cwd=feat)
        gate('record', 'lane', 'live', 'gap', '--model', 'sonnet', '--note', 'no commit', cwd=feat)
        reviewed(feat)
        lane(feat, 'gates', 'PASS', 'root')
        commit(feat, 'a.txt', 'two\n', 'minor')
        size(feat, 'minor')
        gate('record', 'live-check', 'L1', 'VERIFIED', '--at', head(feat), cwd=feat)
        lane(feat, 'checker', 'PASS', 'sonnet')
        lane(feat, 'gates', 'PASS', 'root')
        s = gate('status', cwd=feat)
        check('R1-G8 a gap live lane behaves as a BLOCKED one: the checker VERIFYING every '
              'declared check clears it', s.returncode == 0, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'live', 'PASS', 'opus')
        reviewed(feat)
        lane(feat, 'gates', 'PASS', 'root')
        commit(feat, 'a.txt', 'redesign\n', 'redesign')
        size(feat, 'full', 'a redesign')
        lane(feat, 'live', 'ISSUES', 'opus')
        reviewed(feat)
        lane(feat, 'gates', 'PASS', 'root')
        commit(feat, 'a.txt', 'fix\n', 'fix')
        size(feat, 'minor')
        lane(feat, 'checker', 'PASS', 'sonnet')
        lane(feat, 'gates', 'PASS', 'root')
        s = gate('status', cwd=feat)
        check('R1-G15 a live PASS before the last full round does not stand in for that round\'s '
              'failed live lane; the checker must drive past it', s.returncode == 1
              and 'did not pass' in s.stdout, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        a = evidence('R1-1: data loss, repro: ./crash.sh exits 1\n')
        b = evidence('R1-2: wrong output\n')
        gate('record', 'lane', 'review-a', 'ISSUES', '--model', 'opus', '--at', head(feat),
             '--out', a, cwd=feat)
        gate('record', 'lane', 'review-b', 'ISSUES', '--model', 'sonnet', '--at', head(feat),
             '--out', b, cwd=feat)
        bare = gate('record', 'lane', 'review-c', 'ISSUES', '--model', 'sonnet', '--at',
                    head(feat), '--out', evidence('it looks off\n'), cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        held = gate('status', cwd=feat)
        check('R1-G11 an ISSUES lane that no finding row names is not clean, each lane on its '
              'own, and an ISSUES report is taken whatever its text, since gate.py reads none',
              held.returncode == 1 and 'names lane review-a' in held.stdout
              and 'names lane review-b' in held.stdout and 'names lane review-c' in held.stdout
              and bare.returncode == 0, held.stdout + bare.stderr)
        gate('record', 'finding', 'R1-1', 'follow-up', '--lane', 'review-a', cwd=feat)
        gate('record', 'finding', 'R1-2', 'dropped', '--lane', 'review-b', cwd=feat)
        gate('record', 'lane', 'review-c', 'PASS', '--model', 'sonnet', '--at', head(feat),
             '--out', evidence(), cwd=feat)
        s = gate('status', cwd=feat)
        check('R1-G11b once each ISSUES lane has a finding row naming it, the verdict is clean',
              s.returncode == 0, s.stdout)
        old_row(main, 'review-c', 'ISSUES', evidence('a race in the save path\n'))
        held = gate('status', cwd=feat)
        gate('record', 'finding', 'R1-3', 'blocks', '--lane', 'review-c', '--cmd',
             'grep -n save a.txt', *grounds('R1-3'), cwd=feat)
        later = gate('status', cwd=feat)
        check('R2-G4 an ISSUES row written by hand after the finding rows is not sorted by them, '
              'and is by a finding row after it that names its lane',
              held.returncode == 1 and 'names lane review-c' in held.stdout
              and 'names lane review-c' not in later.stdout
              and 'blocking finding R1-3 is open' in later.stdout, held.stdout + later.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        nxt = iter(range(2, 10))

        def move() -> None:
            n = next(nxt)
            commit(feat, 'a.txt', f'{n}\n', f'fix {n}')
        cmd = ['--cmd', 'grep -n x a.txt']
        gate('record', 'finding', 'R1-1', 'blocks', *cmd, '--premise', 'A holds', cwd=feat)
        move()
        gate('record', 'finding', 'R2-1', 'blocks', *cmd, '--premise', 'B holds', cwd=feat)
        move()
        gate('record', 'finding', 'R2-1', 'blocks', *cmd, '--premise', 'A holds.', cwd=feat)
        one = gate('status', cwd=feat).stdout
        move()
        gate('record', 'finding', 'R4-1', 'blocks', *cmd, '--premise', 'a  HOLDS.', cwd=feat)
        two = gate('status', cwd=feat).stdout
        check('R1-G9 each blocking row counts against the premise it names, whatever its ID\'s '
              'first premise, so the third patch naming one premise says STOP',
              'premise "a holds" (R1-1, R2-1): 1 failed correction' in one
              and 'premise "a holds" (R1-1, R2-1, R4-1): 2 failed correction' in two
              and 'STOP' in two, one + two)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        gate('record', 'lane', 'live', 'BLOCKED', '--model', 'sonnet', '--at', head(feat),
             '--cmd', 'drive', '--out', evidence(), '--note', 'no device', cwd=feat)
        reviewed(feat)
        lane(feat, 'gates', 'PASS', 'root')
        commit(feat, 'a.txt', 'two\n', 'minor')
        size(feat, 'minor')
        both = gate('record', 'lane', 'checker', 'PASS', '--model', 'sonnet', '--at', head(feat),
                    '--cmd', 'ran it', '--out', evidence(), '--covers', 'live', 'regression',
                    cwd=feat)
        row = rows_of(os.path.dirname(feat) + '/main', 'lane', 'checker')
        check('R1-G12 --covers takes its lanes after one flag, as its usage line shows',
              both.returncode == 0 and row and row[-1]['covers'] == 'live regression',
              both.stderr + str(row))


def patch_line(feat: str) -> str:
    return gate('status', cwd=feat).stdout.split('patch ')[1].split(',')[0]


def g43_round_two() -> None:
    """The second review round's findings on honest states, each from the reviewer's repro."""
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        commit(feat, 'app.py', 'def f(x):\n    if x:\n        return 2\n    return 3\n', 'f')
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        reviewed(feat)
        lane(feat, 'gates', 'PASS', 'root')
        clean, was = gate('status', cwd=feat), patch_line(feat)
        commit(feat, 'app.py', 'def f(x):\n    if x:\n        return 2\n        return 3\n',
               're-indent')
        lane(feat, 'gates', 'PASS', 'root')
        s = gate('status', cwd=feat)
        check('R2-G1 a re-indent, which changes what Python runs, is a new patch, so no review or '
              'live lane carries to it', clean.returncode == 0 and patch_line(feat) != was
              and s.returncode == 1 and 'no live lane ran' in s.stdout, clean.stdout + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        bug = ['--model', 'opus', '--at', head(feat), '--out']
        gate('record', 'lane', 'review-a', 'ISSUES', *bug, evidence('R1-1: f(1) prints 2\n'),
             cwd=feat)
        lane(feat, 'review-b', 'PASS', 'sonnet')
        gate('record', 'finding', 'R1-1', 'blocks', '--cmd', 'python3 -c f', *grounds('R1-1'),
             cwd=feat)
        commit(feat, 'a.txt', 'fix\n', 'a fix that did not hold')
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        still = ['--model', 'opus', '--at', head(feat), '--out']
        gate('record', 'lane', 'review-a', 'ISSUES', *still,
             evidence('R1-1 is NOT fixed: f(1) still prints 2\n'), cwd=feat)
        lane(feat, 'review-b', 'PASS', 'sonnet')
        lane(feat, 'gates', 'PASS', 'root')
        gate('record', 'finding', 'R1-1', 'blocks', '--lane', 'review-a', '--cmd', 'python3 -c f',
             *grounds('R1-1'), cwd=feat)
        fixed = gate('record', 'finding', 'R1-1', 'fixed', *FIXER, cwd=feat)
        held = gate('status', cwd=feat)
        check('R2-G3 a lane at a fix\'s patch that reports the finding still failing is a blocking '
              'row for it there, which keeps it open and refuses fixed at that patch',
              fixed.returncode == 2 and held.returncode == 1
              and 'blocking finding R1-1 is open' in held.stdout, fixed.stderr + held.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        path = gate('lane-checkout', 'review-a', cwd=feat).stdout.strip()
        commit(path, 'a.txt', 'a lane edit\n', 'a lane commits')
        made = gate('lane-remove', 'review-a', cwd=feat)
        path = gate('lane-checkout', 'live', cwd=feat).stdout.strip()
        sh('git', 'checkout', '-q', '--detach', 'main', cwd=path)
        left = gate('lane-remove', 'live', cwd=feat)
        gate('lane-checkout', 'review-b', cwd=feat)
        kept = gate('lane-remove', 'review-b', cwd=feat)
        check('R2-G5 lane-remove exits 1 when the lane committed or moved its checkout off the '
              'commit it was made at, and 0 when it left the commit as it was',
              made.returncode == 1 and 'made at' in made.stderr and left.returncode == 1
              and 'made at' in left.stderr and kept.returncode == 0,
              made.stdout + made.stderr + left.stderr + kept.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        reviewed(feat)
        gate('run', 'gates', '--', 'sh', '-c', 'exit 0', cwd=feat)
        commit(main, 'b.txt', 'main\n', 'main moves')
        landed = gate('land', message(tmp), cwd=feat)
        body = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        files = sh('git', 'ls-tree', '--name-only', 'main', cwd=main).split()
        check('R2-G8 land past a moved main lists the head\'s gates runs and commits the merged '
              'tree', landed.returncode == 0 and "- gates: PASS, root" in body
              and "sh -c 'exit 0'" in body and {'a.txt', 'b.txt'} <= set(files),
              landed.stderr + body + str(files))
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        test = 'echo built > build.out; sleep 2; test -f build.out'
        slow = subprocess.Popen([sys.executable, SCRIPT, 'run', 'gates', '--', 'sh', '-c', test],
                                cwd=feat, stdout=subprocess.PIPE, text=True)
        time.sleep(0.7)
        fast = gate('run', 'gates', '--', 'true', cwd=feat)
        said = slow.communicate()[0]
        check('R2-G9 two gates runs started side by side share no files, so one run never cleans '
              'away what the other built', slow.returncode == 0 and fast.returncode == 0
              and 'PASS' in said, said + fast.stdout + fast.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        commit(feat, 'b.txt', 'two\n', 'c2')
        gate('run', 'gates', '--', 'true', cwd=feat)
        sh('git', 'cherry-pick', head(feat) + '~1', cwd=main)
        sh('git', 'rebase', '-q', 'main', cwd=feat)
        rerun = gate('run', 'gates', '--', 'true', cwd=feat)
        reviews(feat)
        s = gate('status', cwd=feat)
        check('R2-G10 a rebase that keeps the tree but changes the patch gets its own gates runs',
              rerun.returncode == 0 and s.returncode == 0, rerun.stderr + s.stdout)


def g44_round_three() -> None:
    """The third review round's findings on honest states, each from the reviewer's repro."""
    issues = ['ISSUES', '--model']
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        h = head(feat)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        gate('record', 'lane', 'review-a', *issues, 'opus', '--at', h, '--out',
             evidence('R1-1 A is broken, a nit\n'), cwd=feat)
        gate('record', 'lane', 'review-b', *issues, 'sonnet', '--at', h, '--out',
             evidence('R1-1 data loss on save\n'), cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        gate('record', 'finding', 'R1-1', 'dropped', '--lane', 'review-a', '--note', 'nit',
             cwd=feat)
        one   = gate('status', cwd=feat)
        clash = gate('record', 'finding', 'R1-1', 'blocks', '--lane', 'review-b', *grounds('R1-1'),
                     '--cmd', 'grep -n save a.txt', cwd=feat)
        gate('record', 'finding', 'R1-B1', 'blocks', '--lane', 'review-b', *grounds('R1-B1'),
             '--cmd', 'grep -n save a.txt', '--note', 'reported as R1-1', cwd=feat)
        two   = gate('status', cwd=feat)
        bare  = [gate('record', 'finding', 'R1-9', b, cwd=feat, bare=True).returncode
                 for b in ('follow-up', 'dropped')]
        fixed = gate('record', 'finding', 'R1-B1', 'fixed', *FIXER, '--lane', 'review-b', cwd=feat)
        check('R3-1 two lanes that number their findings alike are sorted apart: each ISSUES lane '
              'needs a finding row naming it, an ID one lane holds at this patch is refused to '
              'another, and every row but fixed names its lane',
              one.returncode == 1 and 'names lane review-b' in one.stdout
              and 'names lane review-a' not in one.stdout and clash.returncode == 2
              and "lane review-a's finding" in clash.stderr and two.returncode == 1
              and 'names lane review-b' not in two.stdout and 'R1-B1 is open' in two.stdout
              and bare == [2, 2] and fixed.returncode == 2,
              one.stdout + clash.stderr + two.stdout + fixed.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        gate('record', 'lane', 'review-a', *issues, 'opus', '--at', head(feat), '--out',
             evidence('R1-1: f(None) returns 3\n'), cwd=feat)
        lane(feat, 'review-b', 'PASS', 'sonnet')
        gate('record', 'finding', 'R1-1', 'blocks', '--lane', 'review-a', '--cmd', 'f(None)',
             '--premise', 'f must reject None', cwd=feat)
        commit(feat, 'a.txt', 'fix R1-1\n', 'fix R1-1')
        size(feat, 'minor')
        gate('record', 'lane', 'checker', *issues, 'sonnet', '--at', head(feat), '--cmd',
             'f(None); f(-1)', '--out', evidence('R1-1: sites clean. R2-1: f(-1) returns 2\n'),
             cwd=feat)
        gate('record', 'finding', 'R1-1', 'fixed', *FIXER, cwd=feat)
        gate('record', 'finding', 'R2-1', 'follow-up', '--lane', 'checker', cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        clean = gate('status', cwd=feat)
        check('R3-7 a checker ISSUES report that names a fixed finding clean leaves it fixed, '
              'since gate.py reads no report, and the root sorts the report\'s own finding',
              clean.returncode == 0, clean.stdout)
        commit(feat, 'a.txt', 'fix R2-1, which breaks R1-1\n', 'fix R2-1')
        size(feat, 'minor')
        gate('record', 'lane', 'checker', *issues, 'sonnet', '--at', head(feat), '--cmd',
             'f(None); f(-1)', '--out', evidence('R1-1 still fails: f(None) exits 0\n'),
             cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        slip  = gate('status', cwd=feat)
        again = gate('record', 'finding', 'R1-1', 'blocks', '--lane', 'checker', '--cmd',
                     'f(None)', '--premise', 'f must reject None', cwd=feat)
        held  = gate('status', cwd=feat)
        refix = gate('record', 'finding', 'R1-1', 'fixed', *FIXER, cwd=feat)
        check('R3-2 a later lane that reports a closed finding failing again is not clean until '
              'the root records it blocking again from that lane, which reopens it, counts '
              'against its premise, and refuses fixed at that patch',
              slip.returncode == 1 and 'names lane checker' in slip.stdout
              and again.returncode == 0 and held.returncode == 1
              and 'blocking finding R1-1 is open' in held.stdout
              and 'premise "f must reject none" (R1-1): 1 failed correction' in held.stdout
              and refix.returncode == 2, slip.stdout + again.stderr + held.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        gate('record', 'lane', 'review-a', *issues, 'opus', '--at', head(feat), '--out',
             evidence('R1-1: f(None) returns 3\n'), cwd=feat)
        gate('record', 'finding', 'R1-1', 'blocks', '--lane', 'review-a', '--cmd', 'f(None)',
             *grounds('R1-1'), cwd=feat)
        gate('record', 'round', 'void', '--note', 'operator stop', cwd=feat)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        gate('record', 'lane', 'review-a', *issues, 'opus', '--at', head(feat), '--out',
             evidence('R1-1: a different defect\n'), cwd=feat)
        rerun = gate('status', cwd=feat)
        check('R3-1b a blocking row a void kept sorts the voided report, not the rerun\'s, so the '
              'rerun ISSUES lane needs a finding row of its own',
              rerun.returncode == 1 and 'names lane review-a' in rerun.stdout, rerun.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        env = shim(tmp, 'if [ "$1" = worktree ] && [ "$2" = add ]; then\n'
                        f'  if ! mkdir {tmp}/adding 2>/dev/null; then echo overlap >&2; exit 128; '
                        'fi\n  sleep 0.3; "$REAL" "$@"; c=$?; rmdir ' + f'{tmp}/adding; exit $c\n'
                        'fi')
        procs = [subprocess.Popen([sys.executable, SCRIPT, 'run', 'gates', '--', 'true', f'w{i}'],
                                  cwd=feat, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True) for i in range(6)]
        said  = [p.communicate()[0] for p in procs]
        runs  = rows_of(main, 'lane', 'gates')
        left  = os.path.realpath(feat) + '.lanes'
        check('R3-3 gates runs started side by side take turns to add their checkouts, so none '
              'fails on another\'s half-made one', [p.returncode for p in procs] == [0] * 6
              and len(runs) == 6 and not os.path.exists(left), '\n'.join(said))
        env = shim(tmp + '/b', 'if [ "$1" = worktree ] && [ "$2" = add ]; then\n'
                               '  mkdir -p "$5/half"; echo "fatal: commondir" >&2; exit 128\nfi')
        half = gate('run', 'gates', '--', 'true', 'half', cwd=feat, env=env)
        check('R3-3b a failed checkout add leaves no half-made gates folder and no row',
              half.returncode == 128 and 'commondir' in half.stderr and not os.path.exists(left)
              and len(rows_of(main, 'lane', 'gates')) == 6, half.stderr + str(os.listdir(tmp)))
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        h = head(feat)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        gate('record', 'lane', 'review-a', *issues, 'opus', '--at', h, '--out',
             evidence('R1-1: f(None) returns 3\n'), cwd=feat)
        lane(feat, 'review-b', 'PASS', 'sonnet')
        gate('record', 'finding', 'R1-1', 'blocks', '--lane', 'review-a', '--cmd', 'f(None)',
             *grounds('R1-1'), cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        commit(feat, 'broken.py', 'syntax error(\n', 'wip fix')
        lane(feat, 'gates', 'ISSUES', 'root')
        commit(feat, 'broken.py', '\n', 'code-ready fix')
        minor = size(feat, 'minor')
        lane(feat, 'checker', 'PASS', 'sonnet')
        gate('record', 'finding', 'R1-1', 'fixed', *FIXER, cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        s = gate('status', cwd=feat)
        check('R3-4 a head with gates runs alone is no round, so a minor round rests on the last '
              'one that ran lanes', minor.returncode == 0 and s.returncode == 0, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        flag = os.path.join(tmp, 'db-up')
        reviews(feat)
        first = gate('run', 'gates', '--', 'test', '-f', flag, cwd=feat)
        retry = gate('run', 'gates', '--retry', cwd=feat)
        with open(flag, 'w') as f:
            f.write('up\n')
        rerun = gate('run', 'gates', '--', 'test', '-f', flag, cwd=feat)
        nonote = gate('run', 'gates', '--retry', '--infra', cwd=feat)
        alone  = gate('run', 'gates', '--infra', '--note', 'db', cwd=feat)
        infra  = gate('run', 'gates', '--retry', '--infra', '--note', 'the database was down; '
                      'restarted', '--', 'test', '-f', flag, cwd=feat)
        twice  = gate('run', 'gates', '--retry', '--infra', '--note', 'again', '--', 'test',
                      '-f', flag, cwd=feat)
        s      = gate('status', cwd=feat)
        landed = gate('land', message(tmp), cwd=feat)
        body   = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        check('R3-8 a gates command BLOCKED by a cause outside the diff reruns once at its tree '
              'with --retry --infra --note, which the row and the landed verdict keep',
              first.returncode == 1 and retry.returncode == 1 and rerun.returncode == 2
              and '--infra' in rerun.stderr and nonote.returncode == 2 and alone.returncode == 2
              and infra.returncode == 0 and twice.returncode == 2 and s.returncode == 0
              and 'the database was down' in s.stdout and landed.returncode == 0
              and 'the database was down' in body,
              rerun.stderr + infra.stdout + infra.stderr + twice.stderr + s.stdout + body)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        path = gate('lane-checkout', 'review-a', cwd=feat).stdout.strip()
        shutil.rmtree(path)
        gone = gate('lane-remove', 'review-a', cwd=feat)
        path = gate('lane-checkout', 'review-b', cwd=feat).stdout.strip()
        shutil.rmtree(path)
        again = gate('lane-checkout', 'review-b', cwd=feat)
        made  = os.path.isdir((again.stdout.strip().splitlines() or [''])[-1])
        out   = gate('status', cwd=feat).stdout
        gate('lane-remove', 'review-b', cwd=feat)
        os.makedirs(os.path.join(os.path.realpath(feat) + '.lanes', 'stray'))
        stray = gate('lane-checkout', 'stray', cwd=feat)
        check('R3-9 lane-remove and lane-checkout clear git\'s record of a lane checkout whose '
              'folder is gone, and a stray folder is named as not gate.py\'s',
              gone.returncode == 0 and 'was gone' in gone.stdout and again.returncode == 0
              and made
              and 'review-a' not in out and stray.returncode == 2
              and 'git lists no checkout' in stray.stderr,
              gone.stdout + gone.stderr + again.stdout + again.stderr + stray.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        missing = gate('land', os.path.join(tmp, 'no-such-file'), cwd=feat)
        lane(feat, 'gates', 'PASS', 'root')
        sh('git', 'commit', '-q', '--amend', '-m', 'same tree', cwd=feat)
        twice = gate('run', 'gates', '--', 'true', f'check-{next(RUNS) - 1}', cwd=feat)
        check('R3-10 land with a message file that is not there refuses with gate.py\'s own line, '
              'and R3-11 a passed command\'s refusal says once per tree',
              missing.returncode == 1 and 'Traceback' not in missing.stderr
              and 'cannot be read' in missing.stderr and twice.returncode == 2
              and 'once per tree' in twice.stderr, missing.stderr + twice.stderr)


def g45_round_four() -> None:
    """The fourth review round's blocking findings, each from the reviewer's repro."""
    issues = ['ISSUES', '--model']
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        h = head(feat)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        gate('record', 'lane', 'review-a', *issues, 'opus', '--at', h, '--out',
             evidence('R1-A1: f(None) returns 3\n'), cwd=feat)
        gate('record', 'finding', 'R1-A1', 'blocks', '--lane', 'review-a', '--cmd', 'f(None)',
             '--premise', 'f must reject None', cwd=feat)
        gate('record', 'round', 'void', '--note', 'operator stop', cwd=feat)
        lane(feat, 'live', 'NO-RUNTIME', 'sonnet')
        gate('record', 'lane', 'review-a', *issues, 'opus', '--at', h, '--out',
             evidence('R1-A1: f(-1) returns 2\n'), cwd=feat)
        reuse = gate('record', 'finding', 'R1-A1', 'blocks', '--lane', 'review-a', '--cmd',
                     'f(-1)', '--premise', 'negative input is falsy', cwd=feat)
        lane(feat, 'review-b', 'ISSUES', 'sonnet')
        other = gate('record', 'finding', 'R1-A1', 'blocks', '--lane', 'review-b', '--cmd',
                     'f(-1)', '--premise', 'negative input is falsy', cwd=feat)
        own   = gate('record', 'finding', 'R1-A2', 'blocks', '--lane', 'review-a', '--cmd',
                     'f(-1)', '--premise', 'negative input is falsy', '--note',
                     'reported as R1-A1', cwd=feat)
        s = gate('status', cwd=feat).stdout
        check('R4-1 a blocks row for an ID that already blocks at this patch is refused from any '
              'lane, so a rerun lane\'s new defect never replaces the one a void kept',
              reuse.returncode == 2 and 'its own ID' in reuse.stderr and other.returncode == 2
              and own.returncode == 0 and 'R1-A1 is open; its sites: f(None)' in s
              and 'R1-A2 is open; its sites: f(-1)' in s, reuse.stderr + other.stderr + s)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        left = os.path.realpath(feat) + '.lanes'
        ro   = ['sh', '-c', 'mkdir -p cache/mod && echo x > cache/mod/f && chmod -R a-w cache/mod']
        run  = gate('run', 'gates', '--', *ro, cwd=feat)
        rows = rows_of(main, 'lane', 'gates')
        path = gate('lane-checkout', 'live', cwd=feat).stdout.strip()
        os.makedirs(os.path.join(path, 'node_modules', 'x'))
        open(os.path.join(path, 'node_modules', 'x', 'a'), 'w').close()
        sh('chmod', '-R', 'a-w', os.path.join(path, 'node_modules'), cwd=feat)
        rm = gate('lane-remove', 'live', cwd=feat)
        check('R4-2 a check or a lane that leaves a read-only folder in its checkout is recorded, '
              'and its checkout removed, write permission restored first',
              run.returncode == 0 and [r['result'] for r in rows] == ['PASS']
              and rm.returncode == 0 and not os.path.exists(left),
              run.stdout + run.stderr + rm.stdout + rm.stderr)
        if shutil.which('chflags'):
            stuck = ['sh', '-c', 'echo x > pinned && chflags uchg pinned']
            run   = gate('run', 'gates', '--', *stuck, cwd=feat)
            rows  = rows_of(main, 'lane', 'gates')
            out   = gate('status', cwd=feat).stdout
            name  = [ln.split('lane-remove ')[-1].rstrip(')') for ln in out.splitlines()
                     if 'lane checkout still out' in ln]
            for top, _, files in os.walk(left):
                for f in files:
                    sh('chflags', 'nouchg', os.path.join(top, f), cwd=feat)
            rm = gate('lane-remove', *name[:1], cwd=feat)
            check('R4-2b a checkout no removal can delete keeps its row and stays listed, so '
                  'status names it and lane-remove clears it once it can go',
                  run.returncode == 0 and len(rows) == 2 and rows[-1]['result'] == 'PASS'
                  and 'could not be removed' in run.stderr and len(name) == 1
                  and rm.returncode == 0 and not os.path.exists(left),
                  run.stderr + out + rm.stdout + rm.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        down, count = os.path.join(tmp, 'dep-down'), os.path.join(tmp, 'b-count')
        open(down, 'w').close()
        with open(count, 'w') as f:
            f.write('0\n')
        a = ['test', '!', '-e', down]
        b = ['sh', '-c', f'n=$(cat {count}); echo $((n+1)) > {count}; test $n -ge 2']
        for cmd in (a, b):
            gate('run', 'gates', '--', *cmd, cwd=feat)
            gate('run', 'gates', '--retry', cwd=feat)
        os.remove(down)
        note  = ['--retry', '--infra', '--note', 'dependency A needs was down; it is back up']
        bare  = gate('run', 'gates', *note, cwd=feat)
        wrong = gate('run', 'gates', *note, '--', 'test', '-e', down, cwd=feat)
        named = gate('run', 'gates', *note, '--', *a, cwd=feat)
        rows  = {r['cmd']: r for r in rows_of(main, 'lane', 'gates')}
        check('R4-3 --infra reruns only the BLOCKED command it names, so a code failure never '
              'passes under another command\'s cause',
              bare.returncode == 2 and wrong.returncode == 2 and 'not a gates command' in
              wrong.stderr and named.returncode == 0 and rows[shlex.join(a)]['result'] == 'PASS'
              and rows[shlex.join(b)]['result'] == 'BLOCKED',
              bare.stderr + wrong.stderr + named.stdout + named.stderr)


if __name__ == '__main__':
    g1_to_g5()
    g6_g7()
    g8_to_g9()
    g10_to_g15()
    g16_to_g18()
    g19()
    g20_to_g23()
    g24()
    g25_to_g31()
    g32_receipts()
    g33_findings()
    g34_lanes()
    g35_run_gates()
    g36_keep()
    g37_live_checks()
    g38_rounds()
    g39_premises()
    g40_void()
    g41_checker_checks()
    g42_round_one()
    g43_round_two()
    g44_round_three()
    g45_round_four()
    shutil.rmtree(EVIDENCE)
    sys.exit(failures)
