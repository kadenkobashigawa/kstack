#!/usr/bin/env python3
"""
test_vet — builds throwaway repos and checks every command of `vet.sh` the vet skill relies on.

Run it with `python3 test_vet.py`. It needs git, bash and python3. It makes one temporary folder and
runs git and vet.sh with HOME inside it, no global or system git config, and a time zone other than
UTC, then removes it. The exit code is the number of failed checks.

D1 keeps the state in the git directory when `state/report/` exists but isn't ignored. D2 keeps it
in `state/report/vet/` when that is ignored. I1 sets the cursor to main's tip. I2 leaves an existing
cursor alone. P1 lists unreviewed commits oldest first. P2 lists a `--no-ff` merge, not the side
branch's commits.

A1 moves the cursor forward to a real commit. A2 holds that a sha that is no commit leaves the
cursor where it was and exits 2. A3 exits 2 with no sha at all. A4 advances to a commit on main when
there is no cursor yet. A5 accepts the cursor itself. A6 refuses a commit behind the cursor and A7
one not on main, each with exit 2 and the cursor kept. A8 clears a block in force. B1 holds retries
for the minutes given, not seconds.

C1 to C7 read GitHub Actions through a fake `gh`: all runs succeeded, one failed, one cancelled, one
timed out, no runs, one still running, and `gh` itself failing.

W1 to W8 hold watch's clock, which runs from when main last moved. W1 waits after main fast-forwards
just now to an hour-old commit. W2 fires when main's reflog moved an hour ago, though its tip commit
is new. W3 waits while a block is in force though main moved and went quiet. W4 waits while main's
tip is the cursor. W5 fires on the tip commit's date when main has no reflog. W6 reads main's
reflog, not HEAD's, while the working tree is on another branch. W7 reads HEAD in a repo with no
main branch. W8 waits after a fresh commit in a repo that keeps no reflog, so the tip commit's date
stands in rather than no date at all.

K1 to K6 decide whether the canary is due from the canary file's one date: no file, a date this
month, a date only last month, this month of last year, a file that is no date, and a ledger an
older vet left, which does not count. N1 has canary-done write today's UTC date as the file's one
line. N2 keeps one line over two runs.

G1 to G3 hold that vet writes nothing that grows. G1 runs every command and finds only the cursor,
the canary date and a hold in the state directory. G2 holds the cursor to one sha and the canary to
one line. G3 holds the old ledger and trail commands gone: each exits 2 and writes nothing.

S1 counts unreviewed commits. S2 says no canary yet without a canary file and the date it ran with
one. S3 reads a canary file that is no date, in three forms, as canary date unknown, in status and
the hook, with nothing on stderr. H1 keeps the SessionStart hook silent when nothing is pending. H2
speaks for unreviewed commits, in the hook's JSON shape. H3 stays silent about a findings file an
older vet left. H5 prints its JSON with no jq on PATH. U1 prints a usage naming every command.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


HERE    = Path(__file__).resolve().parent
SCRIPT  = HERE.parent / 'scripts' / 'vet.sh'
RESULTS = []
HOUR    = 3600


def check(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


class Repo:
    """a repo on main with commits made now, and the vet state that lives in its git directory."""

    def __init__(self, tmp: Path, n: int = 2, branch: str = 'main'):
        self.tmp   = tmp
        self.path  = tmp / 'repo'
        self.path.mkdir(parents=True)
        self.state = self.path / '.git' / 'vet'
        self.env   = {**{k: v for k, v in os.environ.items() if not k.startswith('GIT_')},
                      'HOME': str(tmp), 'GIT_CONFIG_NOSYSTEM': '1',
                      'GIT_CONFIG_GLOBAL': str(tmp / 'gitconfig'), 'TZ': 'Pacific/Honolulu'}
        self.git('init', '-q', '-b', branch)
        for i in range(1, n + 1):
            self.commit(f'c{i}')

    def git(self, *args: str, env: dict | None = None) -> str:
        return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                              cwd=self.path, env=env or self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, msg: str, when: int | None = None) -> str:
        """commit a change to f; `when` dates the commit, and so its reflog entry, in unix time."""
        (self.path / 'f').write_text(msg)
        self.git('add', 'f')
        env = dict(self.env)
        if when is not None:
            env['GIT_COMMITTER_DATE'] = env['GIT_AUTHOR_DATE'] = f'{when} +0000'
        self.git('commit', '-q', '-m', msg, env=env)
        return self.git('rev-parse', 'HEAD')

    def vet(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(['bash', str(SCRIPT), *args], cwd=self.path,
                              env={**self.env, **(env or {})}, capture_output=True, text=True,
                              timeout=60)

    def watch(self, *args: str) -> subprocess.Popen:
        """start `vet.sh watch` in its own process group, so a kill takes its sleep with it."""
        return subprocess.Popen(['bash', str(SCRIPT), 'watch', *args], cwd=self.path,
                                env=self.env, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)

    def cursor(self) -> str:
        f = self.state / 'cursor'
        return f.read_text().strip() if f.exists() else ''

    def canary(self, date: str) -> None:
        """leave a canary file dated `date`, as an earlier `canary-done` would have."""
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / 'canary').write_text(date + '\n')

    def leave(self, name: str, body: str) -> None:
        """leave a file in the state directory, as an older vet wrote its ledger and findings."""
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / name).write_text(body)


def month_ts(months_back: int) -> str:
    """a date on the 15th of this UTC month, or of a month that many months back."""
    now   = datetime.now(timezone.utc)
    index = now.year * 12 + now.month - 1 - months_back
    return f'{index // 12:04d}-{index % 12 + 1:02d}-15'


def fake_gh(tmp: Path, name: str, body: str) -> dict:
    """a PATH whose first `gh` is a shell script with the given body."""
    folder = tmp / f'gh-{name}'
    folder.mkdir()
    gh = folder / 'gh'
    gh.write_text('#!/bin/sh\n' + body + '\n')
    gh.chmod(0o755)
    return {'PATH': f'{folder}{os.pathsep}{os.environ["PATH"]}'}


def path_without(tmp: Path, name: str) -> dict:
    """a PATH of the system folders with every program but one, plus this git and python3."""
    folder = tmp / f'no-{name}'
    folder.mkdir()
    for system in ('/bin', '/usr/bin', '/usr/sbin', '/sbin'):
        for exe in Path(system).iterdir():
            if exe.name != name and not (folder / exe.name).exists():
                (folder / exe.name).symlink_to(exe)
    for tool, found in (('git', shutil.which('git')), ('python3', sys.executable)):
        if found and not (folder / tool).exists():
            (folder / tool).symlink_to(found)
    return {'PATH': str(folder)}


def hook_json(out: str) -> dict:
    """the hook's stdout parsed, or an empty dict when it isn't JSON."""
    try:
        return json.loads(out)
    except ValueError:
        return {}


# ── the state directory, init and pending ─────────────────────────────────────

def state_dir_checks(tmp: Path) -> None:
    repo = Repo(tmp / 'd1')
    (repo.path / 'state' / 'report').mkdir(parents=True)
    out  = repo.vet('dir').stdout.strip()
    check('D1 state/report/ that is not ignored leaves the state in the git directory',
          Path(out).resolve() == repo.state.resolve(), out)

    repo = Repo(tmp / 'd2')
    (repo.path / 'state' / 'report').mkdir(parents=True)
    (repo.path / '.gitignore').write_text('state/report/\n')
    out  = repo.vet('dir').stdout.strip()
    check('D2 an ignored state/report/ holds the state in state/report/vet',
          Path(out).resolve() == (repo.path / 'state' / 'report' / 'vet').resolve(), out)


def init_checks(tmp: Path) -> None:
    repo = Repo(tmp / 'i1')
    repo.vet('init')
    tip  = repo.git('rev-parse', 'main')
    check('I1 init sets the cursor to main\'s tip', repo.cursor() == tip, repo.cursor())

    repo.commit('c3')
    again = repo.vet('init')
    check('I2 init leaves an existing cursor alone',
          again.returncode == 0 and repo.cursor() == tip, repo.cursor())


def pending_checks(tmp: Path) -> None:
    repo   = Repo(tmp / 'p1')
    repo.vet('init')
    newer  = [repo.commit('c3'), repo.commit('c4')]
    listed = repo.vet('pending').stdout.split()
    check('P1 pending lists unreviewed commits oldest first', listed == newer, str(listed))

    repo = Repo(tmp / 'p2')
    repo.vet('init')
    repo.git('checkout', '-q', '-b', 'side')
    repo.commit('s1')
    repo.commit('s2')
    repo.git('checkout', '-q', 'main')
    repo.git('merge', '-q', '--no-ff', '-m', 'merge side', 'side')
    merge  = repo.git('rev-parse', 'main')
    listed = repo.vet('pending').stdout.split()
    check('P2 pending lists a --no-ff merge, not the side branch\'s commits', listed == [merge],
          str(listed))


# ── advance and block ─────────────────────────────────────────────────────────

def advance_checks(tmp: Path) -> None:
    repo = Repo(tmp / 'a1')
    repo.vet('init')
    tip = repo.commit('c3')
    moved = repo.vet('advance', tip)
    check('A1 advance moves the cursor forward to a real commit',
          moved.returncode == 0 and repo.cursor() == tip,
          f'exit {moved.returncode}, cursor {repo.cursor()!r}')

    bad = repo.vet('advance', 'deadbeef' * 5)
    check('A2 a sha that is no commit leaves the cursor and exits 2',
          bad.returncode == 2 and repo.cursor() == tip,
          f'exit {bad.returncode}, cursor {repo.cursor()!r}')

    empty = repo.vet('advance')
    check('A3 advance with no sha exits 2', empty.returncode == 2, f'exit {empty.returncode}')

    repo  = Repo(tmp / 'a4')
    first = repo.git('rev-parse', 'HEAD~1')
    fresh = repo.vet('advance', first)
    check('A4 with no cursor yet, advance to a commit on main works',
          fresh.returncode == 0 and repo.cursor() == first, f'exit {fresh.returncode}')

    same = repo.vet('advance', first)
    check('A5 advance to the cursor itself succeeds',
          same.returncode == 0 and repo.cursor() == first, f'exit {same.returncode}')

    repo = Repo(tmp / 'a6', n=3)
    repo.vet('init')
    before = repo.cursor()
    back = repo.vet('advance', repo.git('rev-parse', 'main~2'))
    check('A6 a commit behind the cursor exits 2 and keeps the cursor',
          back.returncode == 2 and repo.cursor() == before, f'exit {back.returncode}')

    repo.git('checkout', '-q', '-b', 'side')
    side = repo.commit('side')
    repo.git('checkout', '-q', 'main')
    off  = repo.vet('advance', side)
    check('A7 a commit not on main exits 2 and keeps the cursor',
          off.returncode == 2 and repo.cursor() == before, f'exit {off.returncode}')

    repo = Repo(tmp / 'a8')
    repo.vet('init')
    tip  = repo.commit('c3')
    repo.vet('block', '60', 'cap')
    done = repo.vet('advance', tip)
    check('A8 a successful advance clears a block in force',
          done.returncode == 0 and not (repo.state / 'blocked_until').exists(),
          f'exit {done.returncode}')


def block_checks(tmp: Path) -> None:
    repo  = Repo(tmp / 'b1')
    start = int(time.time())
    repo.vet('block', '60', 'usage cap')
    until = int((repo.state / 'blocked_until').read_text())
    check('B1 block holds retries for the minutes given',
          start + 60 * 60 <= until <= int(time.time()) + 60 * 60, f'{until - start} s')


# ── ci, through a fake gh ─────────────────────────────────────────────────────

def ci_checks(tmp: Path) -> None:
    repo  = Repo(tmp / 'c')
    cases = [
        ('C1 all runs succeeded reads success', 'printf "completed success\\ncompleted success\\n"',
         'success'),
        ('C2 a failed run reads failure', 'printf "completed success\\ncompleted failure\\n"',
         'failure'),
        ('C3 a cancelled run reads failure', 'printf "completed cancelled\\n"', 'failure'),
        ('C4 a timed-out run reads failure', 'printf "completed timed_out\\n"', 'failure'),
        ('C5 no runs reads none', 'exit 0', 'none'),
        ('C6 a run still going reads pending', 'printf "completed success\\nin_progress null\\n"',
         'pending'),
        ('C7 gh failing reads error', 'exit 1', 'error'),
    ]
    for i, (name, body, want) in enumerate(cases):
        got = repo.vet('ci', 'HEAD', env=fake_gh(tmp, str(i), body)).stdout.strip()
        check(name, got == want, f'got {got!r}')


# ── watch ─────────────────────────────────────────────────────────────────────

def watch_checks(tmp: Path) -> None:
    now = int(time.time())

    #main fast-forwarded just now to a commit made an hour ago...
    fresh = Repo(tmp / 'w1')
    fresh.vet('init')
    fresh.git('checkout', '-q', '-b', 'feat')
    fresh.commit('old', when=now - HOUR)
    fresh.git('checkout', '-q', 'main')
    fresh.git('merge', '-q', '--ff-only', 'feat')

    #main moved an hour ago by its reflog, onto a commit made just now...
    quiet = Repo(tmp / 'w2')
    quiet.vet('init')
    quiet.git('checkout', '-q', '-b', 'feat')
    tip = quiet.commit('new')
    quiet.git('checkout', '-q', 'main')
    quiet.git('update-ref', '-m', 'moved an hour ago', 'refs/heads/main', tip,
              env={**quiet.env, 'GIT_COMMITTER_DATE': f'{now - HOUR} +0000'})

    #a block in force, with main moved an hour ago, by its reflog and its commit date...
    blocked = Repo(tmp / 'w3')
    blocked.vet('init')
    blocked.commit('old', when=now - HOUR)
    blocked.vet('block', '60', 'cap')

    still = Repo(tmp / 'w4')
    still.vet('init')

    #no reflog for main, and a tip commit an hour old...
    bare = Repo(tmp / 'w5')
    bare.vet('init')
    bare.commit('old', when=now - HOUR)
    (bare.path / '.git' / 'logs' / 'refs' / 'heads' / 'main').unlink()

    #main moved an hour ago, and the working tree went to another branch just now...
    elsewhere = Repo(tmp / 'w6')
    elsewhere.vet('init')
    elsewhere.commit('old', when=now - HOUR)
    elsewhere.git('checkout', '-q', '-b', 'side')
    elsewhere.commit('side')

    #a repo with no main branch, whose HEAD moved an hour ago...
    master = Repo(tmp / 'w7', branch='master')
    master.vet('init')
    master.commit('old', when=now - HOUR)

    #no reflog for main ever, as core.logAllRefUpdates false keeps it, and a tip commit made now...
    unlogged = Repo(tmp / 'w8', n=0)
    unlogged.git('config', 'core.logAllRefUpdates', 'false')
    unlogged.commit('c1')
    unlogged.vet('init')
    unlogged.commit('new')

    #true for the watches that must still be waiting after 3 s, false for those that must fire...
    runs = [('W1 watch waits after main fast-forwards to an hour-old commit', fresh.watch(), True),
            ('W2 watch fires when main moved an hour ago, whatever the tip commit says',
             quiet.watch(), False),
            ('W3 watch waits while a block is in force', blocked.watch(), True),
            ('W4 watch waits while main\'s tip is the cursor', still.watch(), True),
            ('W5 watch fires on the tip commit\'s date when main has no reflog', bare.watch(),
             False),
            ('W6 watch reads main\'s reflog while the working tree is on another branch',
             elsewhere.watch(), False),
            ('W7 watch reads HEAD in a repo with no main branch', master.watch(), False),
            ('W8 watch waits after a fresh commit when main has no reflog', unlogged.watch(),
             True)]
    time.sleep(3)
    for name, proc, waits in runs:
        code = proc.poll()
        if waits:
            check(name, code is None, f'exited {code}')
        else:
            check(name, code == 0, 'still waiting after 3 s' if code is None else f'exited {code}')
    for _, proc, _ in runs:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


# ── the canary date ───────────────────────────────────────────────────────────

def canary_checks(tmp: Path) -> None:
    repo = Repo(tmp / 'k1')
    due  = repo.vet('due-canary')
    check('K1 no canary file means the canary is due', due.returncode == 0,
          f'exit {due.returncode}')

    repo.canary(month_ts(0))
    due = repo.vet('due-canary')
    check('K2 a canary dated this month means it is not due', due.returncode == 1,
          f'exit {due.returncode}')

    repo = Repo(tmp / 'k3')
    repo.canary(month_ts(1))
    due  = repo.vet('due-canary')
    check('K3 a canary dated only last month means it is due', due.returncode == 0,
          f'exit {due.returncode}')

    repo = Repo(tmp / 'k4')
    repo.canary(month_ts(12))
    due  = repo.vet('due-canary')
    check('K4 a canary from this month of last year means it is due', due.returncode == 0,
          f'exit {due.returncode}')

    repo = Repo(tmp / 'k5')
    repo.canary('whenever')
    due  = repo.vet('due-canary')
    check('K5 a canary file that is no date means it is due, with nothing on stderr',
          due.returncode == 0 and due.stderr == '', f'exit {due.returncode}, {due.stderr[:60]!r}')

    repo = Repo(tmp / 'k6')
    repo.leave('ledger.tsv', f'ts\tkind\n{month_ts(0)}T00:00:00Z\tcanary\n')
    due  = repo.vet('due-canary')
    check('K6 a ledger an older vet left does not stand for a canary', due.returncode == 0,
          f'exit {due.returncode}')

    repo = Repo(tmp / 'n1')
    done = repo.vet('canary-done')
    text = (repo.state / 'canary').read_text() if (repo.state / 'canary').exists() else ''
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    check('N1 canary-done writes today\'s UTC date as the one line of the canary file, which '
          'makes the canary not due', done.returncode == 0 and text == today + '\n'
          and repo.vet('due-canary').returncode == 1, f'exit {done.returncode}, {text!r}')

    repo.canary(month_ts(1))
    repo.vet('canary-done')
    repo.vet('canary-done')
    text = (repo.state / 'canary').read_text()
    check('N2 canary-done twice leaves one line, the later date', text == today + '\n', repr(text))


# ── nothing that grows ────────────────────────────────────────────────────────

def keeps_nothing_checks(tmp: Path) -> None:
    repo = Repo(tmp / 'g1')
    repo.vet('init')
    tip  = repo.commit('c3')
    repo.vet('block', '60', 'cap')
    repo.vet('advance', tip)
    repo.vet('block', '60', 'cap')
    repo.vet('canary-done')
    repo.vet('status')
    repo.vet('status', '--hook')
    repo.vet('pending')
    repo.vet('due-canary')
    repo.vet('ci', 'HEAD', env=fake_gh(tmp, 'g1', 'exit 1'))
    kept = sorted(f.name for f in repo.state.iterdir())
    check('G1 every command together leave the cursor, the canary date and a hold, and no file '
          'that grows', kept == ['blocked_until', 'canary', 'cursor'], str(kept))
    canary = repo.state / 'canary'
    lines  = canary.read_text().splitlines() if canary.exists() else []
    check('G2 the cursor is one sha and the canary one line',
          repo.cursor() == tip and len(lines) == 1, f'{repo.cursor()!r}, {lines}')

    repo  = Repo(tmp / 'g3')
    repo.vet('init')
    before = sorted(f.name for f in repo.state.iterdir())
    gone  = [repo.vet('ledger', 'range', 'a..b', 'CLEAN', '0', 'none', 'x'),
             repo.vet('trail', 'judge', 'a', 'b', 'c', 'd')]
    after = sorted(f.name for f in repo.state.iterdir())
    check('G3 the ledger and trail commands are gone: each exits 2 and writes nothing',
          all(g.returncode == 2 for g in gone) and after == before,
          f'{[g.returncode for g in gone]}, {after}')


# ── status and the SessionStart hook ──────────────────────────────────────────

def status_checks(tmp: Path) -> None:
    repo = Repo(tmp / 's1')
    repo.vet('init')
    repo.commit('c3')
    out = repo.vet('status').stdout
    check('S1 status counts unreviewed commits', '1 unreviewed' in out, out.strip())

    repo   = Repo(tmp / 's2')
    repo.vet('init')
    none   = repo.vet('status').stdout
    repo.canary('2026-10-03')
    dated  = repo.vet('status').stdout
    check('S2 status says no canary yet without a canary file, and the date it ran with one',
          'no canary yet' in none and 'canary last ran 2026-10-03' in dated,
          f'{none.strip()!r} / {dated.strip()!r}')

    #a file that is no date, and a date that does not exist...
    wrong = []
    for i, text in enumerate(('whenever', '2026-13-45', '20261017', '')):
        repo = Repo(tmp / f's3-{i}')
        repo.vet('init')
        repo.commit('c3')
        repo.canary(text)
        out  = repo.vet('status')
        hook = repo.vet('status', '--hook')
        said = hook_json(hook.stdout).get('systemMessage', '')
        if not ('canary date unknown' in out.stdout and 'canary date unknown' in said
                and out.stderr == hook.stderr == ''):
            wrong.append(f'{text!r}: {out.stdout.strip()!r} {out.stderr.strip()[:60]!r}')
    check('S3 a canary file that is no date reads as canary date unknown, in status and the hook, '
          'with nothing on stderr', not wrong, '; '.join(wrong))

    repo  = Repo(tmp / 'h1')
    repo.vet('init')
    quiet = repo.vet('status', '--hook')
    check('H1 the hook is silent when nothing is pending',
          quiet.returncode == 0 and quiet.stdout.strip() == '', repr(quiet.stdout[:80]))

    repo.commit('c3')
    said = hook_json(repo.vet('status', '--hook').stdout)
    spec = said.get('hookSpecificOutput', {})
    check('H2 the hook speaks for unreviewed commits, in its JSON shape',
          '1 unreviewed' in said.get('systemMessage', '')
          and spec.get('hookEventName') == 'SessionStart'
          and '/loop /vet watch' in spec.get('additionalContext', ''), str(said)[:120])

    repo = Repo(tmp / 'h3')
    repo.vet('init')
    repo.leave('findings.md', '# vet findings\n\n## V-1 · x\n- **status:** open\n')
    quiet = repo.vet('status', '--hook')
    check('H3 the hook is silent about a findings file an older vet left',
          quiet.returncode == 0 and quiet.stdout.strip() == '', repr(quiet.stdout[:80]))

    repo = Repo(tmp / 'h5')
    repo.vet('init')
    repo.commit('c3')
    bare = repo.vet('status', '--hook', env=path_without(tmp, 'jq'))
    said = hook_json(bare.stdout)
    check('H5 the hook prints its JSON with no jq on PATH',
          bare.returncode == 0
          and said.get('hookSpecificOutput', {}).get('hookEventName') == 'SessionStart',
          f'exit {bare.returncode}, {bare.stderr.strip()[:80]}')


def usage_checks(tmp: Path) -> None:
    repo    = Repo(tmp / 'u1', n=1)
    usage   = repo.vet('no-such-command')
    names   = ('dir', 'init', 'pending', 'status', 'advance', 'ci', 'block', 'watch', 'due-canary',
               'canary-done')
    missing = [n for n in names if not re.search(rf'vet\.sh {re.escape(n)}\b', usage.stderr)]
    check('U1 an unknown command prints a usage naming every command',
          usage.returncode == 2 and not missing, f'exit {usage.returncode}, missing {missing}')


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for group in (state_dir_checks, init_checks, pending_checks, advance_checks,
                      block_checks, ci_checks, watch_checks, canary_checks,
                      keeps_nothing_checks, status_checks, usage_checks):
            group(tmp)
    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
