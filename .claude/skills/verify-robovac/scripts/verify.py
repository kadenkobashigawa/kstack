#!/usr/bin/env python3
'''
verify — drives the Robovac app the way a robovac session does, for the verify-robovac skill: a
test copy of the app built from one revision, a Claude Code session in the desktop app's own host
mode (host.py) whose hooks are that revision's, and the evidence of each drive in one claim folder.

Commands
--------
    claim <slug>                    make the evidence folder for one claim, under the repository's
                                    git directory, and print it
    launch <E> <side> <rev> [--later]
                                    export <rev> (a commit, or WORKTREE for the checkout as it
                                    stands), build its test copy and open it; --later builds only,
                                    for a scenario that opens the app mid-turn
    doctor <E> <side>               read-only: whether this side is worth driving; exit 1 if not
    drive <E> <side> <scenario>     run a scenario's turns against the side's app and hooks, filming
                                    the window, and write the side's clock
    diff <E>                        the two sides' stills side by side and their log rows, in diff/
    cleanup <E>                     stop, unregister and remove what this claim started, and move
                                    its sessions' transcripts to the Trash; the evidence stays
    end-round                       remove the test copies the round's claims shared, once the
                                    round's last claim is cleaned up
    observe                         a hook: log its payload for the clock; prints nothing, exits 0
    continue-once <flag> <reason>   a Stop hook: continue the turn once, with <reason> as its prompt

<E> is the folder `claim` printed and <side> is baseline or treatment.

Methods
-------
    claude_binary :
        the newest Claude Code binary the desktop app has installed.
    cmd_claim :
        the claim command.
    cmd_launch :
        the launch command.
    doctor :
        the read-only checks, as (ok, line) pairs.
    cmd_doctor :
        the doctor command.
    cmd_drive :
        the drive command.
    cmd_diff :
        the diff command.
    trashable :
        whether a transcript folder is this claim's to trash.
    cmd_cleanup :
        the cleanup command.
    cmd_end_round :
        the end-round command.
    observe :
        the observer hook.
    continue_once :
        the Stop hook that continues a turn once.
    main :
        dispatch on the command named first.
'''

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import common
import session
import testcopy



APPS     = Path.home() / 'Library' / 'Application Support' / 'Claude' / 'claude-code'
PROJECTS = Path.home() / '.claude' / 'projects'
REAL_LOG = Path.home() / '.claude' / 'robovac' / 'runs.jsonl'


# ── claim, launch, doctor ─────────────────────────────────────────────────────

def claude_binary() -> Path | None:
    '''the newest Claude Code binary the desktop app has installed, by version, or None.'''
    found = []
    for path in APPS.glob('*/*/claude.app/Contents/MacOS/claude'):
        version = path.relative_to(APPS).parts[0]
        if re.fullmatch(r'\d+(\.\d+)*', version):
            found.append((tuple(int(p) for p in version.split('.')), str(path)))
    return Path(max(found)[1]) if found else None


def cmd_claim(slug: str) -> Path:
    '''make <git-common-dir>/verify-robovac/<time>-<slug>/ with its three folders, and print it.'''
    if not common.NAME.match(slug):
        raise SystemExit('verify: a claim slug is lowercase kebab-case')
    gitdir = common.run('git', '-C', common.HERE, 'rev-parse', '--path-format=absolute',
                        '--git-common-dir')
    claim  = (Path(gitdir.stdout.strip()) / 'verify-robovac'
              / f"{time.strftime('%Y-%m-%d-%H%M%S')}-{slug}")
    for part in ('baseline', 'treatment', 'diff'):
        (claim / part).mkdir(parents=True)
    common.note(claim, f'claim folder made for {slug}')
    print(claim)
    return claim


def cmd_launch(claim: Path, side: str, rev: str, later: bool) -> None:
    '''get one side's test copy (the round's, when built), and unless `later`, open it.'''
    if (claim / side / 'setup.json').exists():
        raise SystemExit(f'verify: {side} was launched for this claim already; make a new claim')
    repo   = Path(common.run('git', '-C', common.HERE, 'rev-parse',
                             '--show-toplevel').stdout.strip())
    claude = claude_binary()
    sha, tree, app, bundle, reused = testcopy.obtain(claim, rev, repo, side)
    common.record(claim, 'apps', {'app': str(app), 'id': bundle})
    setup = {'side': side, 'rev': rev, 'sha': sha, 'tree': str(tree), 'app': str(app),
             'id': bundle, 'log': str(claim / side / 'runs.jsonl'), 'house': 1, 'later': later,
             'claude': str(claude) if claude else None,
             'claude_version': common.run(claude, '--version').stdout.strip() if claude else None}
    (claim / side / 'setup.json').write_text(json.dumps(setup, indent=1) + '\n')
    common.note(claim, f'launch {side}: {rev} = {sha}, test copy {bundle}'
                + (", the round's earlier build reused" if reused else ' built'))
    if not later:
        w = testcopy.open_app(claim, side)
        common.note(claim, f'{side} app open, window {w[0]} at {w[1]},{w[2]} {w[3]}x{w[4]}')
    print(f'{side}: {sha}  {app}' + ('  (reused)' if reused else ''))


def doctor(claim: Path, side: str) -> list[tuple[bool, str]]:
    '''
    the read-only checks that say whether a side is worth driving.

    Parameters
    ----------
    claim : Path
        the claim folder.
    side : str
        baseline or treatment.

    Returns
    -------
    list of (bool, str)
        each check's result and its line: the side launched; its app running from its own test
        copy, under its own bundle id, built from the side's revision, with its window on screen,
        or, launched --later or closed after a drive, not open yet; Screen Recording granted; the log inside the claim and
        never the person's own; the revision's runs.py present; and Claude Code signed in.
    '''
    path = claim / side / 'setup.json'
    if not path.exists():
        return [(False, f'{side} was never launched: run launch first')]
    setup, out = json.loads(path.read_text()), []
    app   = Path(setup['app'])
    exe   = str(app / 'Contents' / 'MacOS' / 'Robovac')
    pid   = setup.get('pid')
    comm  = common.run('ps', '-o', 'comm=', '-p', pid).stdout.strip() if pid else ''
    later = (setup.get('later') or setup.get('closed')) and not pid
    shut  = 'app not open yet: the scenario opens it' if setup.get('later') \
        else 'app closed after its last drive: the next drive opens it'
    out.append((comm == exe or later, shut if later else f'app pid {pid} runs {comm or "nothing"}'))
    plist = common.run('plutil', '-extract', 'CFBundleIdentifier', 'raw',
                       app / 'Contents' / 'Info.plist').stdout.strip()
    out.append((plist == setup['id'] and plist.startswith(testcopy.PREFIX), f'bundle id {plist}'))
    stamp = app / 'Contents' / 'Resources' / 'verify.json'
    built = json.loads(stamp.read_text()).get('sha') if stamp.exists() else None
    out.append((built == setup['sha'], f'test copy built from {built}'))
    if not later:
        found = common.window(claim, pid) if comm == exe else None
        out.append((found is not None, f'window on screen: {found}' if found else
                    "no window on screen: the mac helper's front brings it forward"))
    granted = common.mac(claim, 'preflight').stdout.strip()
    out.append((granted == 'yes', f'Screen Recording granted to this process: {granted}'))
    log = Path(setup['log'])
    out.append((log.parent == claim / side and log != REAL_LOG, f'log {log}'))
    runs = Path(setup['tree']) / 'skills' / 'robovac' / 'scripts' / 'runs.py'
    out.append((os.access(runs, os.X_OK), f'hooks run {runs}'))
    claude = setup.get('claude')
    status = (common.run(claude, 'auth', 'status').stdout
              if claude and Path(claude).exists() else '{}')
    try:
        signed = json.loads(status).get('loggedIn') is True
    except ValueError:
        signed = False
    out.append((signed, f"Claude Code {setup.get('claude_version')} signed in: {signed}"
                + ('' if signed else f' (the person runs "{claude}" auth login)')))
    return out


def cmd_doctor(claim: Path, side: str) -> int:
    '''print each check as PASS or FAIL; exit 1 when any fails.'''
    checks = doctor(claim, side)
    for ok, line in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {line}")
    return 0 if all(ok for ok, _ in checks) else 1


# ── the drive ─────────────────────────────────────────────────────────────────

def cmd_drive(claim: Path, side: str, path: Path) -> int:
    '''run doctor, then the scenario; record its transcript folders and write the side's clock.'''
    scenario = session.load_scenario(path)
    setup    = json.loads((claim / side / 'setup.json').read_text()) \
        if (claim / side / 'setup.json').exists() else {}
    if setup.get('later') and not any('open' in s for s in scenario['steps']):
        raise SystemExit('verify: launched --later, but the scenario never opens the app')
    if cmd_doctor(claim, side):
        raise SystemExit('verify: doctor failed; this side is not worth driving')
    drive = session.Drive(claim, side, scenario)
    common.note(claim, f'drive {side}: {path.name}')
    try:
        drive.run()
    finally:
        hooks = claim / side / 'hooks.jsonl'
        for line in hooks.read_text().splitlines() if hooks.exists() else []:
            transcript = json.loads(line).get('transcript_path')
            if transcript:
                common.record(claim, 'projects', str(Path(transcript).parent))
        (claim / side / 'clock.md').write_text(session.clock(drive))
        common.note(claim, f'{side} drive done: {len(drive.marks)} marks, clock in {side}/clock.md')
    print(claim / side / 'clock.md')
    return 0


# ── diff and cleanup ──────────────────────────────────────────────────────────

def cmd_diff(claim: Path) -> int:
    '''each still both sides took, baseline left and treatment right, and both logs' rows.'''
    names = sorted({p.stem for p in (claim / 'baseline').glob('*.png')}
                   & {p.stem for p in (claim / 'treatment').glob('*.png')})
    for name in names:
        common.run('ffmpeg', '-loglevel', 'error', '-y', '-i', claim / 'baseline' / f'{name}.png',
                   '-i', claim / 'treatment' / f'{name}.png', '-filter_complex', 'hstack',
                   claim / 'diff' / f'{name}.png')
    table = ["# the two logs\n\nEach row the hooks wrote, in seconds from its log's first row.\n"]
    for side in common.SIDES:
        log, setup = claim / side / 'runs.jsonl', claim / side / 'setup.json'
        rows  = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
        label = json.loads(setup.read_text())['sha'][:7] if setup.exists() else 'not launched'
        table.append(f'\n## {side} ({label})\n\n```\n')
        for r in rows:
            table.append(f"{r['t'] - rows[0]['t']:7.1f}  {session.described(r)}\n")
        table.append('```\n')
    (claim / 'diff' / 'rows.md').write_text(''.join(table))
    common.note(claim, f'diff: {len(names)} stills side by side, rows in diff/rows.md')
    print(claim / 'diff')
    return 0


def trashable(claim: Path, folder: Path) -> bool:
    '''whether a transcript folder sits in ~/.claude/projects, named for this claim's scratch.'''
    slug = re.sub(r'[^A-Za-z0-9]', '-', str(common.scratch(claim)))
    return folder.parent == PROJECTS and folder.name.startswith(slug + '-') and folder.is_dir()


def cmd_cleanup(claim: Path) -> int:
    '''
    stop, unregister and remove what this claim started, and trash its sessions' transcripts.

    Parameters
    ----------
    claim : Path
        the claim folder; everything in it stays, the lock files of its logs aside.

    Returns
    -------
    int
        0 when nothing it started still runs and the evidence is still there, else 1.

    Notes
    -----
    a process is stopped only by its recorded pid, and only while that pid still runs the
    executable it started (`common.stop`); a test copy in the claim's scratch is unregistered from
    Launch Services and its own files removed (`testcopy.leftovers`), while one built for the
    round stays for the round's other claims; a transcript folder goes to the Trash only when
    `trashable`.
    '''
    have, gone = common.started(claim), []
    for proc in have['procs']:
        if common.stop(claim, proc.get('pid')):
            gone.append(f"stopped pid {proc['pid']}")
    for app in have['apps']:
        if Path(app['app']).is_relative_to(testcopy.BUILDS):
            gone.append(f"kept {app['id']} for the round's other claims (end-round removes it)")
            continue
        testcopy.unregister(app['app'], app['id'])
        gone.append(f"unregistered {app['id']}")
    for folder in map(Path, have['projects']):
        if trashable(claim, folder) and not common.mac(claim, 'trash', folder).returncode:
            gone.append(f'trashed {folder.name}')
    shutil.rmtree(common.scratch(claim), ignore_errors=True)
    for lock in claim.glob('*/runs.jsonl.lock'):
        lock.unlink()
    left = [p for p in have['procs'] if p.get('pid')
            and common.run('ps', '-o', 'comm=', '-p', p['pid']).stdout.strip() == p['exe']]
    kept = sorted(str(p.relative_to(claim)) for p in claim.rglob('*') if p.is_file())
    common.note(claim, f"cleanup: {'; '.join(gone) or 'nothing to stop'}; "
                       f'{len(left)} still running; {len(kept)} evidence files kept')
    print('\n'.join(gone + [f'kept {k}' for k in kept]))
    return 1 if left or not kept else 0


def cmd_end_round() -> int:
    '''
    remove every test copy the round built, once its last claim is cleaned up.

    Returns
    -------
    int
        0 when none was left, else 1: a copy whose app still runs is kept and named.
    '''
    kept = []
    for base in sorted(testcopy.BUILDS.glob('*')) if testcopy.BUILDS.exists() else []:
        exe = base / 'Robovac Verify.app' / 'Contents' / 'MacOS' / 'Robovac'
        if str(exe) in common.run('ps', '-axo', 'comm=').stdout.splitlines():
            kept.append(f'kept {base.name}: its app still runs')
            continue
        testcopy.unregister(str(base / 'Robovac Verify.app'), testcopy.PREFIX + base.name[:12])
        shutil.rmtree(base)
        print(f'removed {base.name}')
    print('\n'.join(kept))
    return 1 if kept else 0


# ── the hooks ─────────────────────────────────────────────────────────────────

def observe(stdin) -> int:
    '''log one hook payload's identifying fields to $VERIFY_HOOKS; print nothing, always exit 0.'''
    try:
        payload = json.load(stdin)
        keep = {k: payload[k] for k in ('hook_event_name', 'session_id', 'agent_id', 'agent_type',
                                        'tool_name', 'tool_use_id', 'notification_type',
                                        'mcp_server_name', 'transcript_path', 'stop_hook_active',
                                        'error')
                if k in payload}
        for k in ('prompt', 'tool_input', 'message'):
            if k in payload:
                keep[k] = json.dumps(payload[k])[:160]
        keep['t'] = time.time()
        with open(os.environ['VERIFY_HOOKS'], 'a') as f:
            f.write(json.dumps(keep) + '\n')
    except Exception:
        pass
    return 0


def continue_once(flag: Path, reason: str) -> int:
    '''block the first Stop with `reason` as the turn's next instruction; let every later one go.'''
    if flag.exists():
        return 0
    flag.write_text(dt.datetime.now().isoformat() + '\n')
    print(json.dumps({'decision': 'block', 'reason': reason}))
    return 0


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    '''
    dispatch on the command named first.

    Parameters
    ----------
    argv : list of str
        the whole command line, the script's own name first.

    Returns
    -------
    int
        the command's exit code; 2, with this docstring printed, for an unknown command, a side
        that is not baseline or treatment, or a missing argument.
    '''
    cmd, rest = (argv[1], argv[2:]) if len(argv) > 1 else ('', [])
    if cmd == 'observe':
        return observe(sys.stdin)
    if cmd == 'continue-once' and len(rest) == 2:
        return continue_once(Path(rest[0]), rest[1])
    if cmd == 'claim' and len(rest) == 1:
        cmd_claim(rest[0])
        return 0
    if cmd == 'end-round' and not rest:
        return cmd_end_round()
    if cmd in ('diff', 'cleanup') and len(rest) == 1:
        return (cmd_diff if cmd == 'diff' else cmd_cleanup)(Path(rest[0]))
    if len(rest) >= 2 and rest[1] in common.SIDES:
        claim, side = Path(rest[0]), rest[1]
        if cmd == 'launch' and len(rest) in (3, 4) and rest[3:] in ([], ['--later']):
            cmd_launch(claim, side, rest[2], rest[3:] == ['--later'])
            return 0
        if cmd == 'doctor' and len(rest) == 2:
            return cmd_doctor(claim, side)
        if cmd == 'drive' and len(rest) == 3:
            return cmd_drive(claim, side, Path(rest[2]))
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
