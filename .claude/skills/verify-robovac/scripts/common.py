'''
common — what every other verify module reaches through: the claim's timeline and record of what it
started, the processes and the mac helper, and the constants they share.

Methods
-------
    run :
        run a command with its output captured as text.
    clean_env :
        this process's environment without the variables of the session running it.
    scratch :
        the claim's scratch folder, which cleanup removes.
    note :
        add one line to the claim's timeline.
    started :
        the claim's record of what it started.
    record :
        add one item to that record.
    mac :
        run the compiled mac helper.
    window :
        a process's on-screen window id and frame.
    alive :
        whether a pid is a process still running, a zombie not counted.
    stop :
        stop a process this claim started, if it is still the one it started.
'''

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path



HERE   = Path(__file__).resolve().parent
VERIFY = HERE / 'verify.py'
SIDES  = ('baseline', 'treatment')
NAME   = re.compile(r'^[a-z0-9][a-z0-9-]*$')


# ── the disk, processes and the claim ─────────────────────────────────────────

def run(*argv, cwd: Path | None = None) -> subprocess.CompletedProcess:
    '''run a command with its output captured as text; a failed exit comes back in returncode.'''
    return subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True)


def clean_env(**extra: str) -> dict:
    '''this process's environment less every CLAUDE* and ANTHROPIC* variable, plus `extra`.'''
    env = {k: v for k, v in os.environ.items() if not k.startswith(('CLAUDE', 'ANTHROPIC'))}
    return dict(env, **extra)


def scratch(claim: Path) -> Path:
    '''the claim's scratch folder: exports, test copies, the drive's settings and session folder.'''
    return Path(tempfile.gettempdir()).resolve() / 'verify-robovac' / claim.name


def note(claim: Path, text: str) -> None:
    '''add one line, stamped with the local time, to the claim's timeline.md.'''
    with (claim / 'timeline.md').open('a') as f:
        f.write(f"- {time.strftime('%H:%M:%S')} {text}\n")


def started(claim: Path) -> dict:
    '''the claim's record of what it started: processes, test copies and transcript folders.'''
    path = claim / 'started.json'
    return json.loads(path.read_text()) if path.exists() else {'procs': [], 'apps': [],
                                                                'projects': []}


def record(claim: Path, kind: str, item: dict | str) -> None:
    '''
    add one item to the claim's record of what it started.

    Parameters
    ----------
    claim : Path
        the claim folder, which holds started.json.
    kind : str
        'procs' (pid and executable), 'apps' (bundle path and id) or 'projects' (a folder).
    item : dict or str
        a test copy before it is built, a process as soon as its pid is known, and a transcript
        folder once a hook has named it.

    Notes
    -----
    it lives in the claim folder, which cleanup keeps, so a scratch folder lost to a reboot still
    leaves cleanup the test copies to unregister and the transcripts to trash.
    '''
    have = started(claim)
    if item not in have[kind]:
        have[kind].append(item)
    (claim / 'started.json').write_text(json.dumps(have, indent=1) + '\n')


def mac(claim: Path, *args) -> subprocess.CompletedProcess:
    '''run the mac helper, compiled into the claim's scratch folder on first use.'''
    binary = scratch(claim) / 'bin' / 'mac'
    if not binary.exists():
        binary.parent.mkdir(parents=True, exist_ok=True)
        made = run('swiftc', '-O', HERE / 'mac.swift', '-o', binary)
        if made.returncode:
            raise SystemExit(f'verify: mac.swift did not compile:\n{made.stderr}')
    return run(binary, *args)


def window(claim: Path, pid: int | None) -> list[int] | None:
    '''a process's on-screen window as [id, x, y, width, height] in points, or None.'''
    out = mac(claim, 'window', pid).stdout.split() if pid else []
    return [int(v) for v in out] if len(out) == 5 else None


def alive(pid: int) -> bool:
    '''whether `pid` is a process still running; a zombie, which only awaits its parent, is not.'''
    state = run('ps', '-o', 'stat=', '-p', pid).stdout.strip()
    return bool(state) and not state.startswith('Z')


def stop(claim: Path, pid: int | None) -> bool:
    '''stop a process this claim recorded, if that pid still runs the executable it started.'''
    mine = [p for p in started(claim)['procs'] if p.get('pid') == pid]
    if not pid or not mine or run('ps', '-o', 'comm=', '-p', pid).stdout.strip() != mine[0]['exe']:
        return False
    os.kill(pid, signal.SIGTERM)
    for _ in range(20):

        #a child of this process stays a zombie until reaped...
        try:
            os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            pass
        if not alive(pid):
            return True
        time.sleep(0.25)
    os.kill(pid, signal.SIGKILL)
    return True
