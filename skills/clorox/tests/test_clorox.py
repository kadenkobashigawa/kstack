#!/usr/bin/env python3
"""
test_clorox — builds a throwaway repo and bin, and checks that the bin keeps every item it holds
until its batch is past the cutoff.

Run it with `python3 test_clorox.py`. It needs git. It makes one temporary folder and runs git and
clorox with HOME and CLOROX_BIN inside it and no global or system git config, then removes it. The
exit code is the number of failed checks.

B1 to B7 hold the bin's order and its age rule: an item is recorded before it moves, a row whose
item never arrived reads as gone, and `empty` deletes batch folders by age alone. G1 to G3 check
that an expired item is still emptied and a fresh one survives and restores. K1 to K4 and K25 to
K26 keep every name the settings deny reading where it is, in a cache, a twin or a worktree, and
stop the sweep when the settings cannot be read. K5 to K11 prove each leftover kind: twins byte for
byte, no links, an original that exists, the twin name, the cache signature, and `__pycache__` of
`.pyc` alone. K12 to K18 and K28 to K29 keep each worktree a rule holds, K19 and K27 confine a
sweep to its target in any worktree, K20 lists branches whose commits live only here, K21 to K24
restore, unlock and lock in order, K30 prints the usage, K31 keeps every worktree when `ps` is not
installed, and K32 holds a worktree a session touched under 5 whole days ago, as pstack's
`worktree-audit.sh` does.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


HERE      = Path(__file__).resolve().parent
SCRIPT    = HERE.parent / 'scripts' / 'clorox.py'
PYC       = 'x.cpython-313.pyc'
TAG       = b'Signature: 8a477f597d28d172789f06886806bc55'
DENIED    = 'holds a name your settings deny reading, or cannot be read'
UNTWINNED = 'an iCloud twin with no identical original'
RESULTS   = []


def check(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


def stamp(days_ago: float = 0) -> str:
    """a batch folder's name for a time `days_ago` days back."""
    at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_ago)
    return at.strftime('%Y-%m-%dT%H%M%SZ')


class World:
    """a repo with a tracked file and an untracked __pycache__, a HOME and an empty bin."""

    def __init__(self, tmp: Path, name: str):
        self.home = tmp / name / 'home'
        self.bin  = tmp / name / 'bin'
        self.repo = tmp / name / 'repo'
        self.env  = {**{k: v for k, v in os.environ.items() if not k.startswith('GIT_')},
                     'HOME': str(self.home), 'CLOROX_BIN': str(self.bin),
                     'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
        (self.home / '.claude').mkdir(parents=True)
        (self.home / '.claude' / 'settings.json').write_text('{"permissions": {"deny": []}}')
        (self.repo / 'a' / '__pycache__').mkdir(parents=True)
        (self.repo / 'a' / 'x.py').write_text('x = 1\n')
        (self.repo / 'a' / '__pycache__' / PYC).write_bytes(b'pyc')
        self.git('init', '-q', '-b', 'main')
        self.git('add', 'a/x.py')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base')

    @property
    def shelf(self) -> Path:
        """this repo's folder in the bin."""
        return self.bin / self.repo.name

    @property
    def cache(self) -> Path:
        return self.repo / 'a' / '__pycache__' / PYC

    def git(self, *argv: str) -> str:
        return subprocess.run(['git', *argv], cwd=self.repo, env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def clorox(self, *argv: str, cwd: Path | None = None, env: dict | None = None) -> tuple[int, str]:
        """clorox's exit code and its printed output."""
        out = subprocess.run([sys.executable, str(SCRIPT), *argv], cwd=cwd or self.repo,
                             env=env or self.env, capture_output=True, text=True)
        return out.returncode, out.stdout + out.stderr

    def deny(self, *rules: str) -> None:
        """the user's settings, denying these Read rules."""
        (self.home / '.claude' / 'settings.json').write_text(
            json.dumps({'permissions': {'deny': [f'Read({r})' for r in rules]}}))

    def put_file(self, rel: str, data: bytes = b'x') -> Path:
        """an untracked file at `rel` in the repo."""
        f = self.repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        return f

    def commit(self, *paths: str, cwd: Path | None = None) -> None:
        """commit these paths in the repo, or in the worktree at `cwd`."""
        subprocess.run(['git', 'add', *paths], cwd=cwd or self.repo, env=self.env, check=True)
        subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'c'],
                       cwd=cwd or self.repo, env=self.env, check=True)

    def tree(self, name: str) -> Path:
        """a finished worktree beside the repo: on main's commit, clean and unlocked."""
        wt = self.repo.parent / name
        self.git('worktree', 'add', '-q', '-b', name, str(wt))
        return wt

    def sweep(self, *argv: str, **kw) -> tuple[int, str, str]:
        """a sweep's exit code, printed report and full list."""
        out = self.repo.parent / 'sweep.md'
        out.unlink(missing_ok=True)
        rc, printed = self.clorox('sweep', *argv, '--out', str(out), **kw)
        return rc, printed, out.read_text() if out.exists() else ''

    def binned(self) -> list[str]:
        """the original path of every item the manifest records."""
        return [r[3] for r in self.rows()]

    def python(self, code: str) -> str:
        """run `code` with clorox loaded as `c`, in the repo, under this world's HOME and bin."""
        prog = ('import importlib.util, sys\n'
                f'spec = importlib.util.spec_from_file_location("clorox", {str(SCRIPT)!r})\n'
                'c = importlib.util.module_from_spec(spec)\n'
                'spec.loader.exec_module(c)\n' + code)
        out = subprocess.run([sys.executable, '-c', prog], cwd=self.repo, env=self.env,
                             capture_output=True, text=True)
        return out.stdout + out.stderr

    def put_failing(self, error: str) -> str:
        """bin a/__pycache__ through `put`, with the move replaced by one that raises `error`."""
        return self.python(
            'import shutil\n'
            'real = shutil.move\n'
            'def move(src, dst):\n'
            f'    {"real(src, dst)" if error == "KeyboardInterrupt" else "pass"}\n'
            f'    raise {error}\n'
            'c.shutil.move = move\n'
            'try:\n'
            '    c.put(c.main_root(), c.home(c.main_root()) / c.stamp(), "cache",\n'
            '          c.main_root() / "a" / "__pycache__")\n'
            f'except {error}:\n'
            '    print("interrupted")\n')

    def batch(self, name: str, recorded: bool = False) -> Path:
        """a batch folder holding a copy of the cache, with a manifest row for it if `recorded`."""
        p = self.shelf / name / 'repo' / 'a' / '__pycache__' / PYC
        p.parent.mkdir(parents=True)
        p.write_bytes(b'pyc')
        if recorded:
            with (self.shelf / 'manifest.tsv').open('a') as f:
                f.write(f'abc1234\t{name}\tcache\t{self.repo / "a" / "__pycache__"}\t'
                        f'{p.parent}\n')
        return self.shelf / name

    def rows(self) -> list[list[str]]:
        m = self.shelf / 'manifest.tsv'
        return [r.split('\t') for r in m.read_text().splitlines() if r] if m.exists() else []


def b1_young_unrecorded_batch_survives(tmp: Path) -> None:
    w = World(tmp, 'b1')
    batch = w.batch(stamp())
    rc, out = w.clorox('empty')
    check('B1 a batch binned minutes ago with no manifest row survives empty',
          rc == 0 and (batch / 'repo' / 'a' / '__pycache__' / PYC).exists(), out.strip())


def b2_unrecordable_item_stays(tmp: Path) -> None:
    w = World(tmp, 'b2')
    w.shelf.mkdir(parents=True)
    manifest = w.shelf / 'manifest.tsv'
    manifest.write_text('')
    manifest.chmod(0o444)
    _, out = w.clorox('sweep', '--in', str(w.repo / 'a'))
    manifest.chmod(0o644)
    rc, _ = w.clorox('empty')
    check('B2 an item the manifest cannot record stays where it was',
          rc == 0 and w.cache.exists() and 'could not move' in out, out.strip().splitlines()[-1])


def b3_crash_after_move_is_restorable(tmp: Path) -> None:
    w = World(tmp, 'b3')
    out = w.put_failing('KeyboardInterrupt')
    rc, _ = w.clorox('empty')
    _, listed = w.clorox('bin')
    qid = w.rows()[0][0] if w.rows() else ''
    w.clorox('restore', qid)
    check('B3 an item interrupted right after its move is listed and restored',
          rc == 0 and 'interrupted' in out and 'a/__pycache__' in listed and w.cache.exists(),
          listed.strip())


def b4_other_folders_stay(tmp: Path) -> None:
    w = World(tmp, 'b4')
    other = w.shelf / 'notes'
    other.mkdir(parents=True)
    w.batch(stamp(31))
    rc, out = w.clorox('empty')
    check('B4 a folder in the bin that is not a batch is left alone',
          rc == 0 and other.exists(), out.strip())


def b5_unrecordable_worktree_is_unlocked(tmp: Path) -> None:
    w = World(tmp, 'b5')
    wt = w.repo.parent / 'wt'
    w.git('worktree', 'add', '-q', '-b', 'wt', str(wt))
    w.shelf.mkdir(parents=True)
    manifest = w.shelf / 'manifest.tsv'
    manifest.write_text('')
    manifest.chmod(0o444)
    _, out = w.clorox('sweep')
    manifest.chmod(0o644)
    listed = w.git('worktree', 'list', '--porcelain')
    check('B5 a finished worktree the manifest cannot record stays, unlocked',
          wt.exists() and 'could not move' in out and 'locked' not in listed, out.strip())


def b6_recorded_batch_waits_for_its_cutoff(tmp: Path) -> None:
    w = World(tmp, 'b6')
    batch = w.batch(stamp(29), recorded=True)
    rc, kept = w.clorox('empty')
    _, listed = w.clorox('bin')
    survived = rc == 0 and batch.exists() and 'abc1234' in listed
    rc, emptied = w.clorox('empty', '--days', '28')
    check('B6 a recorded batch 29 days old survives empty, and empty --days 28 removes it',
          survived and rc == 0 and not batch.exists() and 'emptied 1 item(s)' in emptied,
          f'{kept.strip()} / {emptied.strip()}')


def b7_row_without_its_item_reads_as_gone(tmp: Path) -> None:
    w = World(tmp, 'b7')
    out = w.put_failing('OSError')
    _, listed = w.clorox('bin')
    qid = w.rows()[0][0] if w.rows() else ''
    _, restored = w.clorox('restore', qid)
    if w.rows():
        row = w.rows()[0]
        (w.shelf / 'manifest.tsv').write_text('\t'.join([row[0], stamp(31), *row[2:]]) + '\n')
    rc, emptied = w.clorox('empty')
    check('B7 a row whose move failed leaves the item in place and reads as gone',
          'interrupted' in out and w.cache.exists() and qid != ''
          and 'the bin holds nothing for this project' in listed
          and 'already restored or emptied' in restored and rc == 0,
          f'{listed.strip()} / {restored.strip()} / {emptied.strip()}')


def g1_expired_item_is_emptied(tmp: Path) -> None:
    w = World(tmp, 'g1')
    batch = w.batch(stamp(31), recorded=True)
    rc, out = w.clorox('empty')
    check('G1 an item binned 31 days ago is emptied and its batch removed',
          rc == 0 and not batch.exists() and 'emptied 1 item(s)' in out, out.strip())


def g2_expired_unrecorded_batch_is_removed(tmp: Path) -> None:
    w = World(tmp, 'g2')
    batch = w.batch(stamp(31))
    rc, out = w.clorox('empty')
    check('G2 a batch 31 days old with nothing recorded in it is removed',
          rc == 0 and not batch.exists(), out.strip())


def g3_fresh_item_survives_and_restores(tmp: Path) -> None:
    w = World(tmp, 'g3')
    _, swept = w.clorox('sweep', '--in', str(w.repo / 'a'))
    moved = not w.cache.exists()
    rc, _ = w.clorox('empty')
    qid = w.rows()[0][0] if w.rows() else ''
    w.clorox('restore', qid)
    check('G3 a swept item survives empty and restore puts it back',
          moved and rc == 0 and w.cache.exists(), swept.strip())


# ── what stays: names the settings deny ────────────────────────────────────


def k1_a_denied_name_in_a_cache_or_as_a_twin_stays(tmp: Path) -> None:
    w = World(tmp, 'k1')
    w.deny('./.env', '**/*.pem')
    w.put_file('cache/CACHEDIR.TAG', TAG)
    w.put_file('cache/sub/.env', b'KEY=1')
    w.put_file('key.pem', b'pem')
    w.put_file('key 2.pem', b'pem')
    _, _, full = w.sweep()
    check('K1 a signed cache holding .env, and a twin whose own name is denied, stay',
          (w.repo / 'cache' / 'sub' / '.env').exists() and (w.repo / 'key 2.pem').exists()
          and f'{DENIED}: cache' in full and f'{DENIED}: key 2.pem' in full, full)


def k2_a_cache_with_an_unreadable_folder_stays(tmp: Path) -> None:
    w = World(tmp, 'k2')
    w.put_file('cache/CACHEDIR.TAG', TAG)
    locked = w.put_file('cache/shut/x', b'x').parent
    locked.chmod(0)
    _, _, full = w.sweep()
    stayed = locked.exists()
    for shut in [locked] if stayed else list(w.bin.rglob('shut')):
        shut.chmod(0o755)
    check('K2 a cache with a folder that cannot be read stays',
          os.getuid() == 0 or (w.repo / 'cache' / 'shut' / 'x').exists() and f'{DENIED}: cache' in full,
          full)


def k3_unreadable_settings_stop_the_sweep(tmp: Path) -> None:
    w = World(tmp, 'k3')
    (w.home / '.claude' / 'settings.json').write_text('{not json')
    rc, printed, _ = w.sweep()
    check('K3 settings that cannot be parsed stop the sweep before anything moves',
          rc != 0 and w.cache.exists() and 'cannot read the deny list' in printed and not w.rows(),
          printed)


def k4_only_a_proven_leftover_names_its_secret(tmp: Path) -> None:
    w = World(tmp, 'k4')
    w.deny('./.env')
    w.put_file('cache/CACHEDIR.TAG', TAG)
    w.put_file('cache/.env', b'KEY=1')
    w.put_file('notes/.env', b'KEY=1')
    _, _, full = w.sweep()
    check('K4 a leftover holding a denied name stays for that reason, and a folder that is no '
          'leftover stays as not proven', f'{DENIED}: cache' in full
          and 'not proven a leftover: notes' in full and (w.repo / 'cache' / '.env').exists(), full)


def k25_a_twin_of_a_denied_name_stays(tmp: Path) -> None:
    w = World(tmp, 'k25')
    w.deny('./.env')
    w.put_file('.env', b'KEY=1')
    w.put_file('.env 2', b'KEY=1')
    _, _, full = w.sweep()
    check('K25 an identical twin of a denied name is judged under its original\'s name, and stays',
          (w.repo / '.env 2').exists() and f'{DENIED}: .env 2' in full, full)


def k26_a_worktree_holding_a_denied_name_stays(tmp: Path) -> None:
    w = World(tmp, 'k26')
    w.deny('**/*.pem')
    w.put_file('key.pem', b'pem')
    w.commit('key.pem')
    wt = w.tree('k26wt')
    _, _, full = w.sweep()
    check('K26 a finished worktree holding a denied name stays', wt.exists()
          and f'worktree: {DENIED}: {wt}' in full, full)


# ── what stays: proof of each leftover kind ────────────────────────────────


def k5_a_twin_that_differs_stays(tmp: Path) -> None:
    w = World(tmp, 'k5')
    w.put_file('n.txt', b'abc')
    w.put_file('n 2.txt', b'abd')
    for name in ('d', 'd 2'):
        w.put_file(f'{name}/same.txt', b'same')
    w.put_file('d/odd.txt', b'one')
    w.put_file('d 2/odd.txt', b'two')
    _, _, full = w.sweep()
    check('K5 a twin one byte off stays, and a folder twin with one file off',
          (w.repo / 'n 2.txt').exists() and (w.repo / 'd 2').exists()
          and f'{UNTWINNED}: n 2.txt' in full and f'{UNTWINNED}: d 2' in full, full)


def k6_a_twin_with_a_link_stays(tmp: Path) -> None:
    w = World(tmp, 'k6')
    for name in ('d', 'd 2'):
        w.put_file(f'{name}/same.txt', b'same')
        (w.repo / name / 'ln').symlink_to('same.txt')
    w.put_file('m.txt', b'same')
    (w.repo / 'm 2.txt').symlink_to('m.txt')
    _, _, full = w.sweep()
    check('K6 a folder twin holding a link, and a twin that is a link to its original, stay',
          (w.repo / 'd 2').exists() and (w.repo / 'm 2.txt').is_symlink()
          and f'{UNTWINNED}: d 2' in full and f'{UNTWINNED}: m 2.txt' in full, full)


def k7_a_twin_with_no_original_stays(tmp: Path) -> None:
    w = World(tmp, 'k7')
    w.put_file('only 2.txt', b'x')
    _, _, full = w.sweep()
    check('K7 a twin whose original is gone stays', (w.repo / 'only 2.txt').exists()
          and f'{UNTWINNED}: only 2.txt' in full, full)


def k8_other_numbers_are_not_twins(tmp: Path) -> None:
    w = World(tmp, 'k8')
    for name in ('x.txt', 'x 3.txt', 'x2.txt'):
        w.put_file(name, b'same')
    _, _, full = w.sweep()
    check('K8 a copy numbered 3, or with no space before its 2, is not an iCloud twin',
          (w.repo / 'x 3.txt').exists() and (w.repo / 'x2.txt').exists()
          and 'not proven a leftover: x 3.txt' in full and 'not proven a leftover: x2.txt' in full,
          full)


def k9_a_tag_one_digit_off_stays(tmp: Path) -> None:
    w = World(tmp, 'k9')
    w.put_file('cache/CACHEDIR.TAG', TAG[:-1] + b'4')
    _, _, full = w.sweep()
    check('K9 a CACHEDIR.TAG one hex digit off the signature is no cache',
          (w.repo / 'cache').exists() and 'not proven a leftover: cache' in full, full)


def k10_only_pyc_in_pycache_is_a_cache(tmp: Path) -> None:
    w = World(tmp, 'k10')
    w.put_file('a/__pycache__/m.py', b'x = 1')
    w.put_file('a/bytes/m.pyc', b'pyc')
    _, _, full = w.sweep()
    check('K10 a __pycache__ holding a .py, and .pyc files in a folder of another name, stay',
          w.cache.exists() and (w.repo / 'a' / 'bytes').exists()
          and 'not proven a leftover: a/__pycache__' in full
          and 'not proven a leftover: a/bytes' in full, full)


def k11_an_ignored_cache_is_binned(tmp: Path) -> None:
    w = World(tmp, 'k11')
    w.put_file('.gitignore', b'__pycache__/\n')
    w.commit('.gitignore')
    _, printed, _ = w.sweep()
    check('K11 a __pycache__ git ignores is binned too', not w.cache.exists()
          and str(w.repo / 'a' / '__pycache__') in w.binned(), printed)


# ── what stays: worktrees ──────────────────────────────────────────────────


def k12_claude_codes_own_worktree_stays(tmp: Path) -> None:
    w = World(tmp, 'k12')
    wt = w.repo / '.claude' / 'worktrees' / 'k12'
    w.git('worktree', 'add', '-q', '-b', 'k12', str(wt))
    _, _, full = w.sweep()
    check('K12 a worktree under .claude/worktrees/ stays for Claude Code to remove', wt.exists()
          and f'worktree: Claude Code removes its own worktrees: {wt}' in full, full)


def k13_a_locked_worktree_stays(tmp: Path) -> None:
    w = World(tmp, 'k13')
    wt = w.tree('k13wt')
    w.git('worktree', 'lock', str(wt))
    _, _, full = w.sweep()
    check('K13 a locked worktree stays', wt.exists() and f'worktree: locked: {wt}' in full, full)


def k14_unknown_use_keeps_every_worktree(tmp: Path) -> None:
    w = World(tmp, 'k14')
    wt = w.tree('k14wt')
    fake = w.repo.parent / 'fakebin'
    fake.mkdir()
    (fake / 'lsof').write_text('#!/bin/sh\nexit 0\n')
    (fake / 'lsof').chmod(0o755)
    env = dict(w.env, PATH=f'{fake}:{w.env.get("PATH", "")}')
    _, _, full = w.sweep(env=env)
    check('K14 when the processes cannot be listed, every worktree stays', wt.exists()
          and f'worktree: processes could not be listed: {wt}' in full, full)


def k15_a_worktree_in_use_stays(tmp: Path) -> None:
    w = World(tmp, 'k15')
    wt = w.tree('k15wt')
    proc = subprocess.Popen(['sleep', '30'], cwd=wt)
    try:
        _, _, full = w.sweep()
    finally:
        proc.kill()
        proc.wait()
    check('K15 a worktree a process works in stays', wt.exists()
          and f'worktree: in use by pid {proc.pid}: {wt}' in full, full)


def k16_a_worktree_with_work_in_it_stays(tmp: Path) -> None:
    w = World(tmp, 'k16')
    edited, hidden, extra = w.tree('k16e'), w.tree('k16h'), w.tree('k16u')
    (edited / 'a' / 'x.py').write_text('x = 2\n')
    subprocess.run(['git', 'update-index', '--assume-unchanged', 'a/x.py'], cwd=hidden, env=w.env,
                   check=True)
    (extra / 'new.txt').write_text('new')
    _, _, full = w.sweep()
    check('K16 uncommitted edits, a file git is told not to look at, and an untracked file each '
          'keep a worktree', edited.exists() and hidden.exists() and extra.exists()
          and f'worktree: uncommitted edits: {edited}' in full
          and f'worktree: edits git is told not to look at: {hidden}' in full
          and f'worktree: files git does not track: {extra}' in full, full)


def k17_an_unmerged_worktree_stays(tmp: Path) -> None:
    w = World(tmp, 'k17')
    wt = w.tree('k17wt')
    (wt / 'a' / 'y.py').write_text('y = 1\n')
    w.commit('a/y.py', cwd=wt)
    _, _, full = w.sweep()
    check('K17 a worktree whose HEAD is not on main stays', wt.exists()
          and f'worktree: its HEAD is not on main: {wt}' in full, full)


def k18_a_worktree_holding_a_lost_commit_stays(tmp: Path) -> None:
    w = World(tmp, 'k18')
    wt = w.tree('k18wt')
    (wt / 'a' / 'y.py').write_text('y = 1\n')
    w.commit('a/y.py', cwd=wt)
    subprocess.run(['git', 'reset', '-q', '--hard', 'main'], cwd=wt, env=w.env, check=True)
    _, _, full = w.sweep()
    check('K18 a worktree whose history holds a commit no branch, tag or remote holds stays',
          wt.exists() and f'worktree: 1 commit(s) no branch, tag or remote holds: {wt}' in full, full)


def k28_a_worktree_a_session_worked_in_stays(tmp: Path) -> None:
    w = World(tmp, 'k28')
    wt, near = w.tree('k28wt'), w.tree('k28near')
    chat = w.home / '.claude' / 'projects' / '-x' / 's1' / 'subagents' / 'agent-a.jsonl'
    chat.parent.mkdir(parents=True)
    chat.write_text(json.dumps({'cwd': str(wt)}) + '\n'
                    + json.dumps({'command': f'ls {near}-r37/a'}) + '\n')
    _, _, full = w.sweep()
    check('K28 a worktree named in a transcript written within 5 days stays, and one whose path '
          'only begins a name there does not', wt.exists() and not near.exists()
          and f'worktree: a session worked in it within 5 days: {wt}' in full, full)


def k29_an_older_session_holds_nothing(tmp: Path) -> None:
    w = World(tmp, 'k29')
    wt = w.tree('k29wt')
    chat = w.home / '.claude' / 'projects' / '-x' / 's1.jsonl'
    chat.parent.mkdir(parents=True)
    chat.write_text(json.dumps({'command': f'cd {wt}/a && ls'}) + '\n')
    old = time.time() - 6 * 86400
    os.utime(chat, (old, old))
    _, printed, _ = w.sweep()
    shut = w.home / '.claude' / 'projects' / '-y' / 's2.jsonl'
    shut.parent.mkdir(parents=True)
    shut.write_text('{}\n')
    shut.chmod(0)
    again = w.tree('k29again')
    _, _, full = w.sweep()
    shut.chmod(0o644)
    check('K29 a transcript older than 5 days holds no worktree, and a recent one that cannot be '
          'read holds every one', not wt.exists() and str(wt) in w.binned()
          and (os.getuid() == 0 or again.exists()
               and f'worktree: sessions could not be read: {again}' in full), f'{printed} {full}')


# ── scope, branches and the bin ────────────────────────────────────────────


def k31_a_missing_ps_is_unknown_use(tmp: Path) -> None:
    w = World(tmp, 'k31')
    wt = w.tree('k31wt')
    bare = w.repo.parent / 'barebin'
    bare.mkdir()
    (bare / 'git').symlink_to(shutil.which('git'))
    env = dict(w.env, PATH=str(bare))
    rc, printed, full = w.sweep(env=env)
    rc2, printed2, _ = w.sweep('--in', str(w.repo / 'a'), env=env)
    check('K31 when `ps` is not installed the sweep still runs and keeps every worktree, scoped '
          'or not', rc == 0 and rc2 == 0 and wt.exists()
          and f'worktree: processes could not be listed: {wt}' in full, f'{printed} {printed2}')


def k32_the_session_window_is_pstacks(tmp: Path) -> None:
    w = World(tmp, 'k32')
    inside, outside = w.tree('k32in'), w.tree('k32out')
    for name, wt, days in (('in', inside, 4.5), ('out', outside, 5.5)):
        chat = w.home / '.claude' / 'projects' / '-x' / f'{name}.jsonl'
        chat.parent.mkdir(parents=True, exist_ok=True)
        chat.write_text(json.dumps({'command': f'cd {wt}/a'}) + '\n')
        at = time.time() - days * 86400
        os.utime(chat, (at, at))
    _, printed, full = w.sweep()
    check('K32 a session that touched a worktree 4.5 days ago holds it, as pstack\'s `-le 4` '
          'whole days does, and one 5.5 days ago does not', inside.exists() and not outside.exists()
          and str(outside) in w.binned()
          and f'worktree: a session worked in it within 5 days: {inside}' in full,
          f'{printed} {full}')


def k19_a_scoped_sweep_stays_in_its_target(tmp: Path) -> None:
    w = World(tmp, 'k19')
    other = w.put_file('b/__pycache__/m.pyc', b'pyc')
    wt = w.tree('k19wt')
    w.git('checkout', '-q', '-b', 'lonely')
    w.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'l')
    w.git('checkout', '-q', 'main')
    _, printed, full = w.sweep('--in', str(w.repo / 'a'))
    listed = w.git('worktree', 'list', '--porcelain')
    check('K19 a sweep confined to a folder leaves a cache outside it, every worktree and every '
          'branch untouched and unlisted', other.exists() and not w.cache.exists() and wt.exists()
          and 'locked' not in listed and 'lonely' not in full and 'k19wt' not in full
          and not any(line.endswith(': b') for line in full.splitlines()), full)


def k27_a_scoped_sweep_in_a_linked_worktree(tmp: Path) -> None:
    w = World(tmp, 'k27')
    wt = w.tree('k27wt')
    w.cache.unlink()
    w.cache.parent.rmdir()
    ours = w.put_file('kept/CACHEDIR.TAG', TAG)
    theirs = wt / 'a' / '__pycache__' / PYC
    theirs.parent.mkdir(parents=True)
    theirs.write_bytes(b'pyc')
    rc, printed, _ = w.sweep('--in', str(wt / 'a'), cwd=wt)
    rc2, printed2, _ = w.sweep('--in', str(wt), cwd=wt)
    away, other = tmp / 'k27' / 'away', tmp / 'k27' / 'other'
    away.mkdir()
    subprocess.run(['git', 'init', '-q', str(other)], env=w.env, check=True)
    refused = [w.sweep('--in', str(p), cwd=wt) for p in (away, other)]
    check('K27 from a linked worktree, a sweep of a folder in it bins that worktree\'s cache alone, '
          'the worktree\'s root is in scope, and a folder outside every worktree, in no repository '
          'or another one, is refused', rc == 0 and not theirs.exists() and ours.exists()
          and wt.exists() and str(theirs.parent) in w.binned() and rc2 == 0
          and all(r != 0 and 'outside' in out for r, out, _ in refused),
          f'{printed} / {printed2} / {refused}')


def k20_branches_only_here_are_listed(tmp: Path) -> None:
    w = World(tmp, 'k20')
    remote = tmp / 'k20' / 'remote.git'
    subprocess.run(['git', 'init', '-q', '--bare', str(remote)], env=w.env, check=True)
    w.git('remote', 'add', 'origin', str(remote))
    w.git('push', '-q', '-u', 'origin', 'main:ahead')
    w.git('branch', '--set-upstream-to=origin/ahead', 'main')
    w.git('checkout', '-q', '-b', 'ahead', '--track', 'origin/ahead')
    w.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'a')
    w.git('checkout', '-q', '-b', 'lonely', 'main')
    w.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'l')
    w.git('checkout', '-q', 'main')
    w.git('branch', 'merged', 'main')
    _, _, full = w.sweep()
    check('K20 a branch ahead of its upstream, and one with none and not merged, are listed; a '
          'merged one is not', 'ahead 1 of its upstream: commits not pushed: ahead' in full
          and 'branch with no upstream, not merged into main: commits only here: lonely' in full
          and ': merged' not in full, full)


def k21_restore_refuses_over_an_occupied_path(tmp: Path) -> None:
    w = World(tmp, 'k21')
    w.sweep('--in', str(w.repo / 'a'))
    w.cache.parent.mkdir()
    w.cache.write_bytes(b'new')
    qid = w.rows()[0][0] if w.rows() else ''
    rc, out = w.clorox('restore', qid)
    check('K21 restore refuses to move an item back over something standing at its path',
          rc == 1 and 'refused' in out and w.cache.read_bytes() == b'new', out)


def k22_a_restored_worktree_is_unlocked(tmp: Path) -> None:
    w = World(tmp, 'k22')
    wt = w.tree('k22wt')
    w.sweep()
    gone = not wt.exists()
    qid = next((r[0] for r in w.rows() if r[2] == 'worktree'), '')
    rc, out = w.clorox('restore', qid)
    listed = w.git('worktree', 'list', '--porcelain')
    block = next((b for b in listed.split('\n\n') if b.startswith(f'worktree {wt}')), '')
    check('K22 a binned worktree restored sits at its own path and is unlocked, so git sees it again',
          gone and rc == 0 and block and 'prunable' not in block and 'locked' not in block
          and w.git('-C', str(wt), 'status', '--porcelain') == '', f'{out} {listed}')


def k23_empty_unlocks_a_deleted_worktree(tmp: Path) -> None:
    w = World(tmp, 'k23')
    wt = w.tree('k23wt')
    w.sweep()
    rows = w.rows()
    (w.shelf / 'manifest.tsv').write_text(''.join('\t'.join([r[0], stamp(31), *r[2:]]) + '\n'
                                                  for r in rows))
    rc, out = w.clorox('empty')
    listed = w.git('worktree', 'list', '--porcelain')
    check('K23 empty unlocks a worktree it deletes, so git can prune its record',
          rc == 0 and 'emptied 2 item(s)' in out and str(wt) in listed and 'locked' not in listed,
          f'{out} {listed}')


def k24_a_failed_lock_leaves_the_worktree(tmp: Path) -> None:
    w = World(tmp, 'k24')
    wt = w.tree('k24wt')
    w.git('worktree', 'lock', str(wt))
    out = w.python('from pathlib import Path\n'
                   'try:\n'
                   f'    c.put(c.main_root(), c.home(c.main_root()) / c.stamp(), "worktree", Path({str(wt)!r}))\n'
                   'except OSError as e:\n'
                   '    print("refused", e)\n')
    check('K24 a worktree git refuses to lock is not moved', wt.exists() and 'refused' in out
          and not w.rows(), out)


def k30_an_unknown_command_prints_the_usage(tmp: Path) -> None:
    w = World(tmp, 'k30')
    got = [w.clorox(*argv) for argv in (['scrub'], [])]
    check('K30 an unknown command, or none, exits 2 with the usage',
          all(rc == 2 and 'Commands' in out for rc, out in got), str(got))


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t).resolve()
        for case in (b1_young_unrecorded_batch_survives, b2_unrecordable_item_stays,
                     b3_crash_after_move_is_restorable, b4_other_folders_stay,
                     b5_unrecordable_worktree_is_unlocked, b6_recorded_batch_waits_for_its_cutoff,
                     b7_row_without_its_item_reads_as_gone, g1_expired_item_is_emptied,
                     g2_expired_unrecorded_batch_is_removed, g3_fresh_item_survives_and_restores,
                     k1_a_denied_name_in_a_cache_or_as_a_twin_stays,
                     k2_a_cache_with_an_unreadable_folder_stays, k3_unreadable_settings_stop_the_sweep,
                     k4_only_a_proven_leftover_names_its_secret, k25_a_twin_of_a_denied_name_stays,
                     k26_a_worktree_holding_a_denied_name_stays, k5_a_twin_that_differs_stays,
                     k6_a_twin_with_a_link_stays, k7_a_twin_with_no_original_stays,
                     k8_other_numbers_are_not_twins, k9_a_tag_one_digit_off_stays,
                     k10_only_pyc_in_pycache_is_a_cache, k11_an_ignored_cache_is_binned,
                     k12_claude_codes_own_worktree_stays, k13_a_locked_worktree_stays,
                     k14_unknown_use_keeps_every_worktree, k15_a_worktree_in_use_stays,
                     k16_a_worktree_with_work_in_it_stays, k17_an_unmerged_worktree_stays,
                     k18_a_worktree_holding_a_lost_commit_stays,
                     k28_a_worktree_a_session_worked_in_stays, k29_an_older_session_holds_nothing,
                     k19_a_scoped_sweep_stays_in_its_target, k27_a_scoped_sweep_in_a_linked_worktree,
                     k20_branches_only_here_are_listed, k21_restore_refuses_over_an_occupied_path,
                     k22_a_restored_worktree_is_unlocked, k23_empty_unlocks_a_deleted_worktree,
                     k24_a_failed_lock_leaves_the_worktree, k30_an_unknown_command_prints_the_usage,
                     k31_a_missing_ps_is_unknown_use, k32_the_session_window_is_pstacks):
            case(tmp)
    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
