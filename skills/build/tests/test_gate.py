#!/usr/bin/env python3
"""
test_gate — runs gate.py against throwaway repositories and checks the ledger's verdict and the
merge that reads it.

Run it with `python3 test_gate.py`. Each check builds its own repository in a temporary folder:
main checked out in one worktree, the change on a branch in another. The exit code is the number
of failed checks.

G1 to G5 hold what a clean verdict needs: a passing gates lane, a live lane or a NO-RUNTIME record
(G4b), two review lanes on two models, and no BLOCKED lane or gap. G2 holds what a fresh lane row
needs: a known result, its model and the commit it checked, at the current patch. G2b holds that a
fix row names its model and never the root, and that an act-on finding keeps its command. G2c keeps
a lane's commit given short or by name as its full sha. G2d keeps a lane with build output from an
older patch, with a note and no result or model of its own, never gates or a review lane, and
records a gap with no commit. G2e takes --kept-from only at a commit where the ledger holds a row of
that lane from an earlier patch, and copies the latest one's result and model, unless it is
NO-RUNTIME, which has no build output to keep. G2f refuses a commit whose live row a later row at
its patch, at another commit, replaced, and keeps that later one. G2g keeps a regression lane only
while the merge base with main is the one it ran on, and a live lane across a moved main. G4c
refuses a gap lane, G4d a live lane with ISSUES, and G5b a gates lane standing in for a review lane.

G6 holds that an act-on finding blocks and a new patch needs its lanes again, G6b that an act-on
finding at an older patch blocks a later one and status names the patch it was recorded at, G6c that
a later row on a finding at the same patch supersedes it, and G6d that status prints an open
finding's command. G6e holds that after a tests-only patch change the review lanes are never kept,
and the verdict needs two fresh review lanes on two models. G6f holds that an act-on finding carried
past a new commit and two fresh PASS reviews is not clean and land refuses. G6g refuses fixed for a
finding act-on at the current patch, never recorded, or already closed, G6h closes a carried finding
with fixed at the later patch, and G6i with dismissed. G6j holds that fixed at a later patch leaves
the finding open at its own patch, so a reset back to it is not clean and land refuses, G6k the
same for a revert, and G6l refuses fixed where the finding's own row at this patch is act-on.
G6m and G6n hold that an older closing row at a patch never hides a newer act-on row recorded at
another, so a reset back to the closing row's patch is not clean and land refuses. G7 counts
failed corrections and says STOP at two. G7a holds that it does not say STOP at one, G7c that it
says STOP for a finding carried open to a patch with no row of its own, and G7b that it does not
for a finding no longer act-on at the current patch, whose count stays.

G8 refuses to land without a clean verdict. G9 lands past a main that moved on paths the change
does not touch, on main's new commit, and the verdict line names the move. G9b refuses a new head
that keeps the patch until the gates lane runs again at it, and G9c refuses an empty patch. After
main moved, G9d refuses when main changed a path the change touches, G9e when the merge of main and
the head conflicts, and G9f when main changed a path that GATE_CHECK_PATHS names, which G9g reads
from the repository top when landing from a subfolder. G9h refuses past a moved main when the gates
lane was recorded while main's tip was not the head's merge base, and G9i lands once it was recorded
on the rebased head. G9j reads the main a row recorded in a ledger whose header predates that
column.

G10 lands one commit carrying the verdict, each lane with the commit it checked and each fixer with
its model, from a subfolder of the branch's worktree, and updates main's worktree. G10b deletes the
ledger once it has, G10c lands a kept live lane at the commit it checked, its note saying so, and
G10d keeps the ledger of another branch the same worktree had checked out, and the folder they
share. G10e prints the commands that remove the whole worktree, then delete the branch, which run
from the subfolder it landed from. G11 lands the tree of the head the verdict was read at. G12
lands with no worktree on main, and G13 refuses when main moves during the landing, keeping both
main's new commit and the ledger. G14 refuses to record on a detached HEAD. G15 prints git's
own message for a failing git, with no traceback, and G15b one that is not UTF-8. G16 gets the
patch-id the shell pipe gets for a lone CR and a byte that is not UTF-8.

G17 holds that removing a worktree removes its ledger, which lives in the worktree's git folder,
though the branch stays. G17a starts the same branch name in a new worktree with an empty ledger,
and G17b refuses to record in main's worktree, whose git folder is the repository's own. G17c
refuses to record anywhere when git echoes --path-format back, as git before 2.31 does, or drops it
and names a git folder by a relative path, and G17d in a main worktree whose path holds a newline.
G18 holds that a record waits for another writer's lock on the ledger, so a ledger two writers
begin at once has one header, first, and G18b that an empty ledger file gets the header first. G1
reads a ledger not yet written as an empty one.
"""

from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
import sys
import tempfile
import time


SCRIPT   = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'gate.py')
failures = 0


def sh(*args: str, cwd: str) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def gate(*args: str, cwd: str, env: dict | None = None) -> subprocess.CompletedProcess:
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
    """Record a lane that checked `at`, by default the branch's head."""
    return gate('record', 'lane', name, result, '--model', model, '--at', at or head(feat),
                cwd=feat)


def clean_lanes(feat: str) -> None:
    lane(feat, 'gates', 'PASS', 'sonnet')
    lane(feat, 'live', 'NO-RUNTIME', 'root')
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
    return os.path.join(folder, 'kstack-gate', f'{branch}.tsv')


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
        bad   = lane(feat, 'gates', 'GREEN', 'x').returncode
        none  = gate('record', 'lane', 'gates', 'PASS', '--at', head(feat), cwd=feat).returncode
        blind = gate('record', 'lane', 'gates', 'PASS', '--model', 'x', cwd=feat).returncode
        first = head(feat)
        commit(feat, 'a.txt', 'two\n', 'second')
        stale = lane(feat, 'gates', 'PASS', 'x', at=first).returncode
        check('G2 a lane row needs a known result, its model and a commit at the current patch',
              (bad, none, blind, stale) == (2, 2, 2, 2), str((bad, none, blind, stale)))
        loose = gate('record', 'fix', 'fixer-1', 'fixed', cwd=feat).returncode
        roots = [gate('record', 'fix', n, 'fixed', '--model', 'opus', cwd=feat).returncode
                 for n in ('root', 'Root', ' ROOT ')]
        bare  = gate('record', 'finding', 'F1', 'act-on', cwd=feat).returncode
        check('G2b a fix row names its model and never the root; an act-on finding its command',
              loose == 2 and roots == [2, 2, 2] and bare == 2, str((loose, roots, bare)))
        clean_lanes(feat)
        s = gate('status', cwd=feat)
        check('G3 gates, NO-RUNTIME and two review models are clean', s.returncode == 0, s.stdout)
        lane(feat, 'regression', 'BLOCKED', 'sonnet')
        s = gate('status', cwd=feat)
        check('G4 a BLOCKED lane is not a pass', s.returncode == 1 and 'BLOCKED' in s.stdout)
        lane(feat, 'regression', 'gap', 'sonnet')
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
        lane(feat, 'live', 'NO-RUNTIME', 'root', at='HEAD')
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
        why   = gate('record', 'lane', 'live', '--kept-from', old, cwd=feat).returncode
        said  = gate('record', 'lane', 'live', 'PASS', *keep, 'n', cwd=feat).returncode
        extra = [gate('record', 'lane', 'live', *keep, 'n', *more, cwd=feat).returncode
                 for more in (['--at', head(feat)], ['--model', 'opus'], ['--cmd', 'grep -n x'])]
        other = [gate('record', 'lane', name, *keep, 'n', cwd=feat).returncode
                 for name in ('gates', 'review-a', 'regression')]
        kept  = gate('record', 'lane', 'live', *keep, 'only a test changed', cwd=feat).returncode
        gap   = gate('record', 'lane', 'regression', 'gap', '--model', 'opus', cwd=feat).returncode
        hint  = lane(feat, 'gates', 'PASS', 'sonnet', at=old).stderr
        review = gate('record', 'lane', 'review-a', *keep, 'n', cwd=feat).stderr
        check('G2d a lane with build output is kept, with why and no result or model of its own, '
              'never gates or a review lane; a gap names no commit',
              (why, said, kept, gap) == (2, 2, 0, 0) and extra == [2, 2, 2]
              and other == [2, 2, 0] and '--kept-from' in hint and 'no build output' in review,
              str((why, said, extra, other, kept, gap)) + hint + review)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        first = head(feat)
        lane(feat, 'live', 'NO-RUNTIME', 'haiku')
        lane(feat, 'live', 'PASS', 'sonnet')
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
        held = [gate('record', 'lane', 'live', '--kept-from', sha, '--note', 'n', cwd=feat)
                for sha in (second, third, fourth, 'HEAD', first)]
        live = [ln.split() for ln in gate('status', cwd=feat).stdout.splitlines()
                if ln.split()[:1] == ['live']]
        check('G2e --kept-from takes a commit only where the ledger holds a live lane row from an '
              'earlier patch, copies the latest one\'s result and model, and refuses NO-RUNTIME',
              [r.returncode for r in held] == [2, 2, 2, 2, 0] and 'build output' in held[2].stderr
              and live == [['live', 'PASS', 'sonnet']],
              f'{[r.returncode for r in held]} {held[2].stderr} {live}')
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        replaced = head(feat)
        lane(feat, 'live', 'PASS', 'sonnet')
        sh('git', 'commit', '-q', '--allow-empty', '-m', 'same patch', cwd=feat)
        later = head(feat)
        lane(feat, 'live', 'ISSUES', 'opus')
        commit(feat, 'a.txt', 'two\n', 'second')
        old = gate('record', 'lane', 'live', '--kept-from', replaced, '--note', 'n', cwd=feat)
        new = gate('record', 'lane', 'live', '--kept-from', later, '--note', 'n', cwd=feat)
        live = [ln.split() for ln in gate('status', cwd=feat).stdout.splitlines()
                if ln.split()[:1] == ['live']]
        check('G2f --kept-from refuses a commit whose live row a later one at its patch replaced, '
              'and keeps the later one', old.returncode == 2 and new.returncode == 0
              and live == [['live', 'ISSUES', 'opus']], f'{old.stderr} {new.stderr} {live}')
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        old = head(feat)
        lane(feat, 'live', 'PASS', 'sonnet')
        lane(feat, 'regression', 'PASS', 'sonnet')
        commit(feat, 'test_a.txt', 't\n', 'a test')
        same = gate('record', 'lane', 'regression', '--kept-from', old, '--note', 'n', cwd=feat)
        commit(main, 'b.txt', 'main\n', 'main moves')
        sh('git', 'rebase', '-q', 'main', cwd=feat)
        moved = gate('record', 'lane', 'regression', '--kept-from', old, '--note', 'n', cwd=feat)
        live  = gate('record', 'lane', 'live', '--kept-from', old, '--note', 'n', cwd=feat)
        check('G2g a regression lane is kept only while the merge base with main is the one it ran '
              'on, and a live lane is kept across a moved main',
              same.returncode == 0 and moved.returncode == 2 and 'merge base' in moved.stderr
              and live.returncode == 0, same.stderr + moved.stderr + live.stderr)
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
        lane(feat, 'live', 'NO-RUNTIME', 'root')
        lane(feat, 'review-a', 'PASS', 'opus')
        s = gate('status', cwd=feat)
        check('G5b a gates lane on another model is not a second review lane', s.returncode == 1
              and 'fewer than two review lanes' in s.stdout, s.stdout)


def g6_g7() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n one a.txt', cwd=feat)
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
              s.returncode == 1 and 'act-on finding F1 is open' in s.stdout
              and 'recorded at patch' in s.stdout, s.stdout)
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        s = gate('status', cwd=feat).stdout
        check('G7a a finding back after one fix is counted, without STOP',
              '1 failed correction' in s and 'STOP' not in s, s)
        commit(feat, 'a.txt', 'three\n', 'fix 2')
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        s = gate('status', cwd=feat).stdout
        check('G7 a finding back after two fixes says STOP', '2 failed correction' in s
              and 'STOP' in s, s)
        commit(feat, 'a.txt', 'four\n', 'design settled')
        moved = gate('status', cwd=feat).stdout
        check('G7c a finding carried open to a new patch with no row there keeps its count and '
              'STOP',
              '2 failed correction' in moved and 'STOP' in moved, moved)
        gate('record', 'finding', 'F1', 'dismissed', '--note', 'the design settled it', cwd=feat)
        closed = gate('status', cwd=feat).stdout
        check('G7b a finding no longer act-on at the current patch keeps its count, without STOP',
              '2 failed correction' in closed and 'STOP' not in closed, closed)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        gate('record', 'finding', 'F1', 'dismissed', '--note', 'a misreading', cwd=feat)
        same = gate('status', cwd=feat)
        gate('record', 'finding', 'F2', 'act-on', '--cmd', 'grep -n y', cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        clean_lanes(feat)
        gate('record', 'finding', 'F2', 'act-on', '--cmd', 'grep -n y', cwd=feat)
        gate('record', 'finding', 'F2', 'dismissed', '--note', 'a misreading', cwd=feat)
        later = gate('status', cwd=feat)
        check('G6c a later row on a finding at the same patch supersedes it',
              same.returncode == 0 and later.returncode == 0
              and 'failed correction' not in later.stdout, same.stdout + later.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        msg = message(tmp)
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'NO-RUNTIME', 'root')
        lane(feat, 'review-a', 'ISSUES', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n one a.txt', cwd=feat)
        commit(feat, 'b.txt', 'unrelated\n', 'another change')
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'NO-RUNTIME', 'root')
        lane(feat, 'review-a', 'PASS', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        r = gate('land', msg, cwd=feat)
        check('G6f an act-on finding carried past a new commit and two fresh PASS reviews is not '
              'clean, and land refuses', s.returncode == 1 and 'F1' in s.stdout
              and r.returncode == 1 and 'F1' in r.stderr, s.stdout + r.stderr)
        same = gate('record', 'finding', 'F2', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        early = gate('record', 'finding', 'F2', 'fixed', '--note', 'its sites came back clean',
                     cwd=feat)
        never = gate('record', 'finding', 'F3', 'fixed', '--note', 'no such finding', cwd=feat)
        gate('record', 'finding', 'F2', 'dismissed', '--note', 'a misreading', cwd=feat)
        shut = gate('record', 'finding', 'F2', 'fixed', '--note', 'already closed', cwd=feat)
        check('G6g fixed closes only a finding open at an earlier patch: never one act-on at this '
              'patch, one never recorded, or one already closed',
              same.returncode == 0 and [early.returncode, never.returncode, shut.returncode]
              == [2, 2, 2], early.stderr + never.stderr + shut.stderr)
        fixed = gate('record', 'finding', 'F1', 'fixed', '--note', 'grep -n one a.txt is empty',
                     cwd=feat)
        s = gate('status', cwd=feat)
        check('G6h fixed at the later patch closes a carried act-on finding', fixed.returncode == 0
              and s.returncode == 0, fixed.stderr + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        clean_lanes(feat)
        held = gate('status', cwd=feat)
        gate('record', 'finding', 'F1', 'dismissed', '--note', 'a misreading', cwd=feat)
        s = gate('status', cwd=feat)
        check('G6i dismissed at the later patch closes a carried act-on finding',
              held.returncode == 1 and s.returncode == 0, held.stdout + s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        msg = message(tmp)
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'NO-RUNTIME', 'root')
        lane(feat, 'review-a', 'ISSUES', 'opus')
        lane(feat, 'review-b', 'PASS', 'sonnet')
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n one a.txt', cwd=feat)
        bad = head(feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        good = head(feat)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'fixed', '--note', 'grep -n one a.txt is empty', cwd=feat)
        sh('git', 'reset', '-q', '--hard', bad, cwd=feat)
        s = gate('status', cwd=feat)
        r = gate('land', msg, cwd=feat)
        check('G6j fixed at a later patch does not close the finding at its own patch: a reset '
              'back to it is not clean, and land refuses', s.returncode == 1
              and 'act-on finding F1 is open' in s.stdout and r.returncode == 1
              and 'F1' in r.stderr, s.stdout + r.stderr)
        sh('git', 'reset', '-q', '--hard', good, cwd=feat)
        sh('git', 'revert', '--no-edit', 'HEAD', cwd=feat)
        lane(feat, 'gates', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G6k a revert back to the patch where a finding was recorded act-on is not clean',
              s.returncode == 1 and 'act-on finding F1 is open' in s.stdout, s.stdout)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        bad = head(feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        sh('git', 'reset', '-q', '--hard', bad, cwd=feat)
        back = gate('record', 'finding', 'F1', 'fixed', '--note', 'no round ran here', cwd=feat)
        check('G6l fixed is refused at a patch where the finding\'s own row is act-on, whatever '
              'another patch holds', back.returncode == 2, back.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        msg = message(tmp)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'dismissed', '--note', 'a misreading', cwd=feat)
        mid = head(feat)
        commit(feat, 'a.txt', 'three\n', 'fix 2')
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        sh('git', 'reset', '-q', '--hard', mid, cwd=feat)
        s = gate('status', cwd=feat)
        r = gate('land', msg, cwd=feat)
        check('G6m an older closing row at this patch does not hide a newer act-on row at a later '
              'one: a reset back to it is not clean, and land refuses', s.returncode == 1
              and 'act-on finding F1 is open' in s.stdout and r.returncode == 1
              and 'F1' in r.stderr, s.stdout + r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        msg = message(tmp)
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'dismissed', '--note', 'a misreading', cwd=feat)
        first = head(feat)
        commit(feat, 'a.txt', 'two\n', 'fix 1')
        clean_lanes(feat)
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        sh('git', 'reset', '-q', '--hard', first, cwd=feat)
        s = gate('status', cwd=feat)
        r = gate('land', msg, cwd=feat)
        check('G6n a finding sorted dismissed and then act-on at a later patch is open when a '
              'reset brings back the dismissed patch, and land refuses', s.returncode == 1
              and 'act-on finding F1 is open' in s.stdout and r.returncode == 1
              and 'F1' in r.stderr, s.stdout + r.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        _, feat = repo(tmp)
        old = head(feat)
        lane(feat, 'gates', 'PASS', 'sonnet')
        lane(feat, 'live', 'PASS', 'sonnet')
        lane(feat, 'regression', 'PASS', 'sonnet')
        lane(feat, 'review-correctness', 'ISSUES', 'opus')
        lane(feat, 'review-structure', 'PASS', 'sonnet')
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        commit(feat, 'test_a.txt', 't\n', 'a test')
        lane(feat, 'gates', 'PASS', 'sonnet')
        held  = [gate('record', 'lane', name, '--kept-from', old, '--note', 'only a test changed',
                      cwd=feat).returncode
                 for name in ('gates', 'live', 'regression', 'review-correctness',
                              'review-structure')]
        lane(feat, 'review-correctness', 'PASS', 'opus')
        one   = gate('status', cwd=feat)
        lane(feat, 'review-structure', 'PASS', 'sonnet')
        gate('record', 'finding', 'F1', 'fixed', '--note', 'its sites came back clean', cwd=feat)
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
        held = gate('land', msg, cwd=feat)
        lane(feat, 'gates', 'PASS', 'sonnet')
        late = gate('land', msg, cwd=feat)
        check('G9b a new head that keeps the patch waits for gates at that head',
              held.returncode == 1 and 'gates' in held.stderr and late.returncode == 0,
              held.stderr + late.stderr)
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
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        path = ledger(main, 'feat', 'feat')
        os.makedirs(os.path.dirname(path))
        with open(path, 'w') as f:
            f.write('ts\thead\tpatch\tkind\tname\tmodel\tresult\tcmd\tnote\n')
        clean_lanes(feat)
        commit(main, 'b.txt', 'main moved\n', 'elsewhere')
        r = gate('land', message(tmp), cwd=feat)
        check('G9j a ledger begun before the main column keeps the main a later row records',
              r.returncode == 0, r.stderr)


def g10_to_g15() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        reviewed = head(feat)
        sh('git', 'commit', '-q', '--allow-empty', '-m', 'same patch', cwd=feat)
        now = head(feat)
        clean_lanes(feat)
        lane(feat, 'review-correctness', 'PASS', 'opus', at=reviewed)
        gate('record', 'fix', 'fixer-1', 'fixed', '--model', 'sonnet', cwd=feat)
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
              and f'gates: PASS, sonnet, at {now[:8]}' in body
              and '- fix: fixer-1, sonnet' in body, r.stderr + body)
        check('G10b landing deletes the ledger', not os.path.exists(ledger(main, 'feat', 'feat')))
        said = [ln.strip() for ln in r.stdout.splitlines() if ln.startswith('  git ')]
        ran  = subprocess.run(' && '.join(said), shell=True, cwd=sub, capture_output=True,
                              text=True)
        left = sh('git', 'branch', '--list', 'feat', cwd=main).strip()
        check('G10e land prints the commands that remove the whole worktree, then delete the '
              'branch, and they run from the subfolder it landed from',
              len(said) == 2 and 'worktree remove' in said[0] and 'branch -D' in said[1]
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
        gate('record', 'lane', 'live', '--kept-from', 'HEAD~1', '--note', 'only a test changed',
             cwd=feat)
        r = gate('land', message(tmp), cwd=feat)
        body = sh('git', 'log', '-1', '--format=%B', 'main', cwd=main)
        check('G10c a kept live lane lands at the commit it checked, its note saying it was kept',
              r.returncode == 0 and f'live: PASS, sonnet, at {checked[:8]} (kept from '
              f'{checked[:8]}: only a test changed)' in body, r.stderr + body)
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
        piped = subprocess.run(f'git diff {base}..HEAD | git patch-id --stable', shell=True,
                               cwd=feat, capture_output=True).stdout.split()[0].decode()
        s = gate('status', cwd=feat)
        check('G16 the patch-id is the shell pipe\'s, for a lone CR and a byte that is not UTF-8',
              f'patch {piped[:12]}' in s.stdout and 'Traceback' not in s.stderr,
              piped + s.stdout + s.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        held = os.path.exists(ledger(main, 'feat', 'feat'))
        sh('git', 'worktree', 'remove', feat, cwd=main)
        left = [os.path.join(d, n) for d, _, names in os.walk(os.path.join(main, '.git'))
                for n in names if n == 'feat.tsv']
        kept = sh('git', 'branch', '--list', 'feat', cwd=main).strip()
        check('G17 removing a worktree removes its ledger, though the branch stays',
              held and not left and kept.endswith('feat'), str(left))
    with tempfile.TemporaryDirectory() as tmp:
        main, feat = repo(tmp)
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        drop(main, feat, 'feat')
        sh('git', 'worktree', 'add', '-q', '-b', 'feat', feat, cwd=main)
        commit(feat, 'a.txt', 'again\n', 'made again')
        gate('record', 'finding', 'F1', 'act-on', '--cmd', 'grep -n x', cwd=feat)
        s = gate('status', cwd=feat).stdout
        check('G17a the same branch name in a new worktree starts with an empty ledger',
              'failed correction' not in s and 'act-on finding F1' in s, s)
    with tempfile.TemporaryDirectory() as tmp:
        main, _ = repo(tmp)
        sh('git', 'switch', '-q', '-c', 'one', cwd=main)
        commit(main, 'one.txt', '1\n', 'one')
        old = head(main)
        commit(main, 'one.txt', '2\n', 'two')
        said = [gate('record', *args, cwd=main) for args in (
            ('finding', 'F1', 'act-on', '--cmd', 'grep -n 1'),
            ('lane', 'gates', 'PASS', '--model', 'sonnet', '--at', 'HEAD'),
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
        header = 'ts\thead\tpatch\tkind\tname\tmodel\tresult\tcmd\tnote'
        other  = f'2026-10-24T00:00:00+00:00\t{head(feat)}\tp\tfinding\tF0\t\tnit\t\t'
        os.makedirs(os.path.dirname(path))
        with open(path, 'a') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            proc = subprocess.Popen([sys.executable, SCRIPT, 'record', 'finding', 'F1', 'nit'],
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
        check('G19 a live lane that passed needs a regression lane on main for a clean verdict',
              s.returncode == 1 and 'no regression lane' in s.stdout, s.stdout)
        lane(feat, 'regression', 'PASS', 'sonnet')
        s = gate('status', cwd=feat)
        check('G19b with the regression lane passed, the verdict is clean', s.returncode == 0,
              s.stdout)


if __name__ == '__main__':
    g1_to_g5()
    g6_g7()
    g8_to_g9()
    g10_to_g15()
    g16_to_g18()
    g19()
    sys.exit(failures)
