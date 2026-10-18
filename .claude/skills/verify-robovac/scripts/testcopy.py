'''
testcopy — a revision's test copy of the app: exported from git, built under its own bundle id,
opened on a claim's log, and taken out of Launch Services with what macOS kept for it.

Methods
-------
    revision :
        a commit-ish's full sha, or None.
    export :
        a revision's files, copied out of git into a folder.
    images :
        give an exported tree the house images its revision names.
    build :
        compile a test copy of the app from an exported tree, as build.sh does.
    obtain :
        a revision's test copy: the round's own when one was built, else a new one.
    open_app :
        start a side's test copy and wait for its window.
    leftovers :
        what macOS keeps for a test copy under ~/Library.
    unregister :
        take a test copy out of Launch Services and remove what macOS kept for it.
'''

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import common



BUILDS  = Path(tempfile.gettempdir()).resolve() / 'verify-robovac' / 'builds'
PREFIX  = 'com.kstack.robovac.verify-'
LSREG   = ('/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework'
           '/Support/lsregister')
SWIFTC  = ('-O', '-swift-version', '5', '-parse-as-library', '-framework', 'Cocoa', '-framework',
           'WebKit')
SOURCES = ('Robovac.swift', 'Runs.swift')


# ── a revision's test copy ────────────────────────────────────────────────────

def revision(rev: str, repo: Path) -> str | None:
    '''a commit-ish's full sha in `repo`, or None when git cannot name it.'''
    done = common.run('git', '-C', repo, 'rev-parse', '--verify', f'{rev}^{{commit}}')
    return None if done.returncode else done.stdout.strip()


def export(rev: str, dest: Path, repo: Path) -> str:
    '''
    a revision's files, copied out of git into a folder.

    Parameters
    ----------
    rev : str
        a commit-ish, or WORKTREE for the checkout as it stands: tracked files and the untracked
        ones git does not ignore.
    dest : Path
        a folder that does not exist yet.
    repo : Path
        the checkout under test.

    Returns
    -------
    str
        the commit's full sha, or WORKTREE followed by the sha of the HEAD it stands on.

    Raises
    ------
    SystemExit
        when git cannot name the revision or archive it.
    '''
    dest.mkdir(parents=True)
    if rev == 'WORKTREE':
        files = common.run('git', '-C', repo, 'ls-files', '-co', '--exclude-standard', '-z').stdout
        for name in filter(None, files.split('\0')):
            if (repo / name).is_file():
                (dest / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(repo / name, dest / name)
        return 'WORKTREE on ' + common.run('git', '-C', repo, 'rev-parse', 'HEAD').stdout.strip()
    sha = revision(rev, repo)
    if not sha:
        raise SystemExit(f'verify: git cannot name {rev}')
    archive = subprocess.run(['git', '-C', str(repo), 'archive', sha], capture_output=True)
    unpack = subprocess.run(['tar', '-x', '-C', str(dest)], input=archive.stdout)
    if archive.returncode or unpack.returncode:
        raise SystemExit(f'verify: git could not archive {rev}')
    return sha


def images(tree: Path, repo: Path) -> None:
    '''
    give an exported tree the house images its revision names.

    Parameters
    ----------
    tree : Path
        the exported tree, which has no apps/robovac-widget/app/build, since git ignores it.
    repo : Path
        the checkout under test, whose own images are copied when they are the same pack.

    Raises
    ------
    SystemExit
        when neither the checkout's images nor the release pack match the revision's images.lock.
    '''
    widget, here = tree / 'apps' / 'robovac-widget', repo / 'apps' / 'robovac-widget'
    lock = (widget / 'mac' / 'images.lock').read_text().split()[0]
    pack = here / 'app' / 'build' / '.pack'

    #the checkout's own copy of the same pack saves a download per side...
    if pack.exists() and pack.read_text().strip() == lock:
        shutil.copytree(here / 'app' / 'build', widget / 'app' / 'build')
        return
    got = common.run('sh', widget / 'mac' / 'images.sh', 'fetch')
    if got.returncode:
        raise SystemExit(f'verify: no house images for {lock}:\n{got.stderr}')


def build(tree: Path, app: Path, bundle_id: str, stamp: dict) -> None:
    '''
    compile a test copy of the app from an exported tree, as build.sh does, under its own id.

    Parameters
    ----------
    tree : Path
        the exported tree.
    app : Path
        the .app bundle to make.
    bundle_id : str
        the copy's own bundle id, under which macOS keeps its window frame, WebKit data, caches and
        Launch Services entry apart from the installed Robovac's.
    stamp : dict
        written to Contents/Resources/verify.json, where doctor reads which revision this is.

    Raises
    ------
    SystemExit
        when swiftc, cp, plutil, rsync or codesign fails.

    Notes
    -----
    the swiftc line, the copied files and the ad hoc signature are build.sh's; build.sh itself
    installs over ~/Applications/Robovac.app and registers it, which a test copy must never do.
    '''
    src, contents = tree / 'apps' / 'robovac-widget' / 'mac', app / 'Contents'
    plist = contents / 'Info.plist'
    (contents / 'MacOS').mkdir(parents=True)
    (contents / 'Resources').mkdir()
    steps = [
        ('swiftc', *SWIFTC, *(src / name for name in SOURCES), '-o',
         contents / 'MacOS' / 'Robovac'),
        ('cp', src / 'Info.plist', plist),
        ('plutil', '-replace', 'CFBundleIdentifier', '-string', bundle_id, plist),
        ('plutil', '-replace', 'CFBundleName', '-string', 'Robovac Verify', plist),
        ('plutil', '-replace', 'CFBundleDisplayName', '-string', 'Robovac Verify', plist),
        ('cp', src / 'AppIcon.icns', contents / 'Resources' / 'AppIcon.icns'),
        ('rsync', '-a', '--delete', '--exclude', '*.svg', f'{src.parent / "app"}/',
         f'{contents / "Resources" / "app"}/'),
    ]
    for step in steps:
        done = common.run(*step)
        if done.returncode:
            raise SystemExit(f'verify: {step[0]} failed:\n{done.stderr}')
    (contents / 'Resources' / 'verify.json').write_text(json.dumps(stamp) + '\n')
    signed = common.run('codesign', '--force', '--sign', '-', app)
    if signed.returncode:
        raise SystemExit(f'verify: codesign failed:\n{signed.stderr}')


def obtain(claim: Path, rev: str, repo: Path, side: str) -> tuple[str, Path, Path, str, bool]:
    '''
    a revision's test copy: the round's own when one was built, else a new one.

    Parameters
    ----------
    claim : Path
        the claim folder, whose record gets the test copy before it is built.
    rev : str
        a commit-ish, or WORKTREE.
    repo : Path
        the checkout under test.
    side : str
        baseline or treatment, which names a WORKTREE copy's bundle id.

    Returns
    -------
    tuple
        the sha (or WORKTREE label), the exported tree, the .app, its bundle id, and whether the
        round's earlier build was reused.

    Notes
    -----
    a commit builds once per round, into BUILDS/<sha>, under the id verify-<sha>: every claim of
    the round that names it reuses the copy, and `end-round` removes it. the copy is marked ready
    only after its build ends, so a build that died is made again. a WORKTREE changes under the
    same name, so it builds into the claim's scratch folder, per claim, and cleanup removes it.
    '''
    sha  = revision(rev, repo) if rev != 'WORKTREE' else None
    base = BUILDS / sha if sha else common.scratch(claim) / side
    bundle = (PREFIX + sha[:12] if sha
              else f"{PREFIX}{''.join(claim.name.split('-')[:4])}-{side}")
    tree, app = base / 'src', base / 'Robovac Verify.app'
    if sha and (base / 'ready').exists():
        return sha, tree, app, bundle, True
    shutil.rmtree(base, ignore_errors=True)
    sha = export(rev, tree, repo)
    images(tree, repo)
    common.record(claim, 'apps', {'app': str(app), 'id': bundle})
    build(tree, app, bundle, {'rev': rev, 'sha': sha})
    (base / 'ready').write_text(sha + '\n')
    return sha, tree, app, bundle, False


# ── opening it and taking it away ─────────────────────────────────────────────

def open_app(claim: Path, side: str) -> list[int]:
    '''
    start a side's test copy and wait for its window.

    Parameters
    ----------
    claim : Path
        the claim folder.
    side : str
        baseline or treatment, launched already.

    Returns
    -------
    list of int
        the window's id, x, y, width and height, also written to the side's setup.json.

    Raises
    ------
    SystemExit
        when no window shows within 20 seconds.

    Notes
    -----
    the app is started from its binary, as demo.sh starts it, with ROBOVAC_RUNS naming the log the
    drive's hooks write and ROBOVAC_HOUSE=1 holding the drawing fixed across sides; ROBOVAC_KEYS is
    never set, since it presses keys on the page from inside. the other side's app, if open, is
    stopped first, so one window is filmed at a time. an app started
    by a background process stays off screen until something brings it forward, so `mac front`
    does, as the person's click on its Dock icon would.
    '''
    setup = json.loads((claim / side / 'setup.json').read_text())
    exe   = Path(setup['app']) / 'Contents' / 'MacOS' / 'Robovac'
    for other in common.SIDES:
        path = claim / other / 'setup.json'
        pid = json.loads(path.read_text()).get('pid') if other != side and path.exists() else None
        if common.stop(claim, pid):
            common.note(claim, f'{other} app stopped, so one window is filmed at a time')
    env = common.clean_env(ROBOVAC_RUNS=setup['log'], ROBOVAC_HOUSE='1')
    proc = subprocess.Popen([str(exe)], env=env,
                            stdout=open(claim / side / 'app.log', 'a'), stderr=subprocess.STDOUT,
                            start_new_session=True)
    common.record(claim, 'procs', {'pid': proc.pid, 'exe': str(exe)})
    found, deadline = None, time.time() + 20
    while not found and time.time() < deadline:
        time.sleep(0.5)
        found = common.window(claim, proc.pid)
        if not found:
            common.mac(claim, 'front', proc.pid)
    if not found:
        raise SystemExit(f'verify: the {side} app (pid {proc.pid}) showed no window in 20 s')

    #the page draws its house once the window shows...
    time.sleep(2)
    setup.update(pid=proc.pid, window=found, closed=False)
    (claim / side / 'setup.json').write_text(json.dumps(setup, indent=1) + '\n')
    return found


def leftovers(bundle_id: str) -> list[Path]:
    '''
    what macOS keeps for a test copy under ~/Library, by its bundle id, whatever HOME says.

    Parameters
    ----------
    bundle_id : str
        a test copy's bundle id.

    Returns
    -------
    list of Path
        its defaults, WebKit data and caches, or nothing for an id outside the verify prefix, so
        the installed Robovac's com.kstack.robovac is never touched.
    '''
    if not bundle_id.startswith(PREFIX) or not common.NAME.match(bundle_id[len(PREFIX):]):
        return []
    lib = Path.home() / 'Library'
    return [lib / 'Preferences' / f'{bundle_id}.plist', lib / 'WebKit' / bundle_id,
            lib / 'Caches' / bundle_id]


def unregister(app: str, bundle_id: str) -> None:
    '''take a test copy out of Launch Services and remove what macOS kept for its verify id.'''
    common.run(LSREG, '-u', app)
    if leftovers(bundle_id):
        common.run('defaults', 'delete', bundle_id)
    for leftover in leftovers(bundle_id):
        if leftover.is_dir():
            shutil.rmtree(leftover)
        elif leftover.exists():
            leftover.unlink()
