"""
gate_lanes — the commands gate.py runs itself rather than taking a lane's word: a lane's detached
checkout made and removed, one gates check run in its checkout and recorded with its exit code and
output, and the comparison that decides whether a lane's result is kept from an earlier patch.
gate.py's help is the source of truth for their grammar.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

from gate_ledger import (NOT_RUN, Refuse, append, branch_at, changed, evidence_file, git, git_bytes,
                    lane_path, lanes_dir, lanes_out, ledger_path, one_line, patch_of, read_rows,
                    sha256, text, worktree_lock)

#the file in a lane checkout's own git folder that holds the commit it was made at...
LANE_BASE = 'kstack-lane-base'


def run_gates(a: argparse.Namespace, argv: list[str]) -> int:
    """Run one check in the gates lane's checkout and record it, retry the last failed one, or
    rerun the BLOCKED one named after an infrastructure cause."""
    if a.retry and argv and not a.infra:
        raise Refuse('--retry takes no command: it reruns the last failed command, identically')
    if a.infra and not a.retry:
        raise Refuse('--infra goes with --retry: `gate.py run gates --retry --infra --note '
                     '<cause> -- <cmd...>` reruns the BLOCKED command it names once at its tree')
    if a.infra and not argv:
        raise Refuse('--infra names, after --, the BLOCKED command whose two failures the cause '
                     'made, exactly as it ran, so no other command is rerun under that cause')
    if a.infra and not a.note.strip():
        raise Refuse('an infrastructure retry names the cause outside the diff that failed both '
                     'runs, such as a dependency that was down, and how it was cleared (--note)')
    if a.note.strip() and not a.infra:
        raise Refuse('--note goes with --retry --infra, the rerun after an infrastructure failure; '
                     'gate.py writes every other gates row\'s note itself')
    if not a.retry and not argv:
        raise Refuse('gate.py run gates [--at SHA] -- <cmd...> names the check to run after --')
    at   = branch_at()
    head = git('rev-parse', '--verify', f'{a.at or "HEAD"}^{{commit}}')
    if patch_of(head)[1] != at['patch']:
        raise Refuse(f'{a.at} does not carry the current patch; the gates lane runs at a commit '
                     'that does')
    path = ledger_path(at['branch'])
    tree = git('rev-parse', f'{head}^{{tree}}')

    #what a run tested is the commit's tree at this patch, as gate_runs counts it, so an amend
    #that keeps the tree keeps its runs, and a new patch with the same tree gets its own...
    runs = [r for r in read_rows(path) if (r['kind'], r['name']) == ('lane', 'gates')
            and r['exit'] and r['patch'] == at['patch'] and same_tree(r, head, tree)]
    if a.infra:

        #a cause outside the diff fails a command twice and is cleared, once per command per tree...
        failed = [r for r in runs if r['exit'] != NOT_RUN and ran(runs, r['cmd'])[-1] is r
                  and r['result'] == 'BLOCKED'
                  and not any(x['covers'] == 'infra' for x in ran(runs, r['cmd']))]
        if not failed:
            raise Refuse(f'no gates command is BLOCKED at {head[:8]} with its infrastructure retry '
                         'unused; --infra reruns one that failed twice, once per tree')
        cmd = shlex.join(argv)
        if cmd not in [r['cmd'] for r in failed]:
            raise Refuse(f'`{cmd}` is not a gates command BLOCKED at {head[:8]} with its '
                         'infrastructure retry unused; --infra reruns only the one named, '
                         'exactly as it ran: ' + ', '.join(f"`{r['cmd']}`" for r in failed))
    elif a.retry:

        #a run that never started is no run, so a retry whose program was missing is still owed...
        failed = [r for r in runs if r['exit'] != NOT_RUN and ran(runs, r['cmd']) == [r]
                  and r['result'] == 'ISSUES']
        if not failed:
            raise Refuse(f'no gates command is failed at {head[:8]} with its retry unused; --retry '
                         'reruns one that failed once')
        cmd = failed[-1]['cmd']
    else:
        cmd = shlex.join(argv)
        if shlex.split(one_line(cmd)) != argv:
            raise Refuse('a gates command is kept on one ledger line, so no argument holds a tab, '
                         'a newline, or leading, trailing or repeated spaces')
        if ran(runs, cmd):
            last = ran(runs, cmd)[-1]
            raise Refuse(f"`{cmd}` already ran at {last['head'][:8]}"
                         + ('' if last['head'] == head else f', whose tree {head[:8]} shares,')
                         + f" and is {last['result']}; " + {
                'PASS':    'a command runs once per tree',
                'ISSUES':  'its one fresh run is `gate.py run gates --retry`, the identical '
                           'command at the same commit',
                'BLOCKED': 'it failed twice, so it was never a flake: fix it in a new commit, or, '
                           'when a named cause outside the diff failed both runs and is cleared, '
                           'rerun it once with `gate.py run gates --retry --infra --note <cause> '
                           '-- <cmd...>`',
            }.get(last['result'], 'a command runs once per tree'))
    retry = bool(ran(runs, cmd))
    lane  = gates_checkout(head)
    out   = evidence_file(path, 'gates', f'$ {cmd}\n(gate.py run gates at {head} in {lane})\n')

    #the row is written before the checkout goes, so a check that leaves a folder no removal can
    #delete still has its row, and the leftover stays listed for status and land to name...
    try:
        result = record_run(a, path, head, tree, at['patch'], cmd, retry, lane, out)
    finally:
        left = drop_checkout(lane)
    if left:
        print(f'gate: {left}', file=sys.stderr)
    return 0 if result == 'PASS' else 1


def record_run(a: argparse.Namespace, path: str, head: str, tree: str, patch: str, cmd: str,
               retry: bool, lane: str, out: str) -> str:
    """Run `cmd` in `lane`, append its gates row to the ledger at `path`, print its tail and
    its result, and return the result."""
    try:
        with open(out, 'a') as f:
            f.flush()
            code = subprocess.run(shlex.split(cmd), cwd=lane, stdout=f,
                                  stderr=subprocess.STDOUT).returncode
            f.write(f'[exit {code}]\n')
        exit_ = str(code)
    except OSError as e:
        code = None
        with open(out, 'a') as f:
            f.write(f'[did not start: {e.strerror}: {shlex.split(cmd)[0]}]\n')
        exit_ = NOT_RUN
    infra = f'infrastructure retry ({one_line(a.note)})' if a.infra else ''
    if code is None:
        result = 'BLOCKED'
        again  = 'gate.py run gates --retry' if retry else 'the identical command'
        again += f' --infra --note <cause> -- {cmd}' if a.infra else ''
        note   = (f'did not start: {shlex.split(cmd)[0]} is missing or not executable; install '
                  f'it, then run {again} again')
    elif code == 0:
        result, note = 'PASS', f'{infra} passed' if infra else 'the retry passed' if retry else ''
    elif infra:
        result = 'BLOCKED'
        note   = f'{infra} failed with exit {code}: fix it in a new commit'
    elif retry:
        result = 'BLOCKED'
        note   = f'failed again with exit {code}: an identical second failure is never a flake'
    else:
        result, note = 'ISSUES', ''
    append(path, {'head': head, 'patch': patch, 'kind': 'lane', 'name': 'gates',
                  'model': 'root', 'result': result, 'cmd': cmd, 'note': note, 'out': out,
                  'sha256': sha256(out), 'exit': exit_, 'tree': tree,
                  'covers': 'infra' if a.infra and code is not None else ''})
    with open(out, encoding='utf-8', errors='replace') as f:
        tail = f.read().splitlines()[-20:]
    print('\n'.join(tail))
    print(f'gates: {result} at {head[:8]}, `{cmd}`' + (f', exit {code}' if code is not None else '')
          + (f' ({note})' if note else '') + f'\n  out: {out}')
    if result == 'ISSUES':
        print('  its one fresh run: gate.py run gates --retry')
    return result


def same_tree(r: dict, head: str, tree: str) -> bool:
    """Whether gates row `r` tested `tree`: by its tree column, or by its head in a row written
    before gate.py kept the tree."""
    return r['tree'] == tree if r['tree'] else r['head'] == head


def ran(runs: list[dict], cmd: str) -> list[dict]:
    """The rows of `runs` where `cmd` started, oldest first."""
    return [r for r in runs if r['cmd'] == cmd and r['exit'] != NOT_RUN]


def gates_checkout(head: str) -> str:
    """A new detached checkout of `head` for one gates run, <worktree>.lanes/gates-<id>.

    Notes
    -----
    Each run gets its own, so runs started side by side in the background never share files,
    and a fresh checkout holds no untracked or ignored file an earlier run left, so a run tests
    the commit alone. run_gates removes it once the command exits.
    """
    return add_checkout(head)


def add_checkout(commit: str, path: str = '') -> str:
    """`git worktree add --detach` of `commit` at `path`, or at a new gates-<id> folder when `path`
    is empty, under the worktree lock, and the path. A failed add leaves no half-made checkout:
    its folder and any record git kept of it go, then gate.py exits with git's code.

    Notes
    -----
    The lane folder is made and removed under the same lock, so one run never removes it, empty,
    between another's making it and making its checkout inside it.
    """
    with worktree_lock():
        folder = lanes_dir()
        os.makedirs(folder, exist_ok=True)
        path = path or tempfile.mkdtemp(prefix='gates-', dir=folder)
        p = subprocess.run(['git', 'worktree', 'add', '-q', '--detach', path, commit],
                           capture_output=True)
        if p.returncode:
            subprocess.run(['git', 'worktree', 'remove', '--force', path], capture_output=True)
            shutil.rmtree(path, ignore_errors=True)
            drop_folder(path)
    if p.returncode:
        sys.stderr.write(f'gate: git worktree failed\n{text(p.stderr)}')
        sys.exit(p.returncode)
    return path


def drop_folder(path: str) -> None:
    """Remove the lane folder holding `path` once it is empty; the caller holds the lock."""
    try:
        os.rmdir(os.path.dirname(path))
    except OSError:
        pass


def drop_checkout(path: str) -> str:
    """Remove the lane checkout at `path`, untracked files included, and the lane folder once it
    is empty; '' when it went, else what was left.

    Notes
    -----
    A check can leave a folder with no write permission, as Go's module cache is, which `git
    worktree remove --force` cannot delete, and git drops its record of the checkout even then,
    so the leftover would drop out of `git worktree list`. So write permission is restored first,
    the folder is deleted before git's record, and the record stays while the folder does, where
    status and land list it as a checkout still out.
    """
    with worktree_lock():
        writable(path)
        shutil.rmtree(path, ignore_errors=True)
        if os.path.lexists(path):
            return (f'{path} could not be removed, even with write permission restored; git still '
                    'lists it, so status and land name it: remove what is left, then run gate.py '
                    f'lane-remove {os.path.basename(path)}')
        git('worktree', 'remove', '--force', path)
        drop_folder(path)
    return ''


def writable(path: str) -> None:
    """Give the owner write and search permission on every folder under `path`, as `chmod -R u+w`
    does, so each can be emptied; a symlink is never followed."""
    if os.path.islink(path) or not os.path.isdir(path):
        return
    for top, dirs, _ in os.walk(path):
        for d in [top] + [os.path.join(top, d) for d in dirs]:
            if not os.path.islink(d):
                try:
                    os.chmod(d, os.stat(d).st_mode | stat.S_IRWXU)
                except OSError:
                    pass


def same_build(ledger: str, name: str, kept: str, head: str) -> tuple[str, str, str]:
    """The command that showed `kept` and `head` build the same, its output file, and the basis.

    Notes
    -----
    Refuses, naming the changed paths, unless every path the two commits differ in matches a
    GATE_NOISE_PATHS pathspec or GATE_SAME_BUILD, run from the top with the two commits as its
    last two arguments, exits 0.
    """
    paths = changed(kept, head)
    spec  = os.environ.get('GATE_NOISE_PATHS', '').split()
    noise = changed(kept, head, *spec) if spec else set()
    rest  = sorted(paths - noise)
    diff  = shlex.join(['git', 'diff', '--name-only', kept, head])
    lines = [f'$ {diff}', *sorted(paths), '',
             f'GATE_NOISE_PATHS: {" ".join(spec) or "(unset)"}',
             'paths not matched: ' + (', '.join(rest) or 'none')]
    if not rest:
        out = evidence_file(ledger, f'keep-{name}', '\n'.join(lines) + '\n')
        return diff, out, 'every changed path is noise by GATE_NOISE_PATHS'
    same = os.environ.get('GATE_SAME_BUILD', '').strip()
    told = (f"lane {name} is not kept from {kept[:8]}: these paths changed between it and the "
            f"head and match no GATE_NOISE_PATHS pathspec: {', '.join(rest)}")
    redo = (f'. Rerun lane {name} at this patch and record it with --at')
    if not same:
        raise Refuse(told + ', and GATE_SAME_BUILD is unset' + redo)
    argv = [*shlex.split(same), kept, head]
    try:
        p = subprocess.run(argv, cwd=git('rev-parse', '--show-toplevel'), capture_output=True)
        code, said = p.returncode, text(p.stdout + p.stderr)
    except OSError as e:
        code, said = None, f'{e.strerror}: {argv[0]}'
    out = evidence_file(ledger, f'keep-{name}', '\n'.join(
        [*lines, '', f'$ {shlex.join(argv)}', said.rstrip('\n'), f'[exit {code}]']) + '\n')
    if code != 0:
        why = 'did not start' if code is None else f'exited {code}'
        raise Refuse(f'{told}, and GATE_SAME_BUILD {why} (output: {out})' + redo)
    return shlex.join(argv), out, 'GATE_SAME_BUILD exited 0'


def lane_checkout(name: str, sha: str) -> int:
    branch_at()
    path   = lane_path(name)
    commit = git('rev-parse', '--verify', f'{sha or "HEAD"}^{{commit}}')
    registered = path in lanes_out()
    if registered and os.path.lexists(path):
        raise Refuse(f'{path} is already there; gate.py lane-remove {name} first')
    if os.path.lexists(path):
        raise Refuse(f'{path} is there, and git lists no checkout at it, so gate.py did not make '
                     'it and will not delete it: move it aside, then run this again')
    if registered:

        #git still lists a checkout whose folder is gone, and refuses to add one at its path...
        with worktree_lock():
            git('worktree', 'remove', '--force', path)
        print(f'git listed a lane checkout at {path} whose folder was gone; removed that record')
    add_checkout(commit, path)

    #keep the commit beside the checkout's own HEAD, so lane-remove sees a lane that moved it...
    with open(os.path.join(git('-C', path, 'rev-parse', '--absolute-git-dir'), LANE_BASE),
              'w') as f:
        f.write(commit + '\n')
    print(path)
    return 0


def lane_remove(name: str) -> int:
    branch_at()
    path = lane_path(name)
    if path not in lanes_out():
        raise Refuse(f'git lists no lane checkout at {path}')

    #a removal that failed part way leaves a folder with no .git file, which is no checkout...
    if not os.path.isdir(path) or not os.path.isfile(os.path.join(path, '.git')):
        gone = not os.path.lexists(path)
        left = drop_checkout(path)
        if left:
            raise Refuse(left)
        print(f'{path} was gone, so its status could not be read; removed the record git kept '
              'of it' if gone else f'{path} was what a failed removal left, no longer a checkout, '
              'so its status could not be read; removed it and the record git kept of it')
        return 0
    raw = text(git_bytes('-C', path, 'status', '--short', '--untracked-files=all'))
    print(f'git status --short in {path}:')
    print(raw.rstrip('\n') if raw.strip() else '  (clean)')
    edited = [ln for ln in raw.splitlines() if ln and not ln.startswith('??')]
    try:
        with open(os.path.join(git('-C', path, 'rev-parse', '--absolute-git-dir'), LANE_BASE)) as f:
            made = f.read().strip()
    except OSError:
        made = ''
    now   = git('-C', path, 'rev-parse', 'HEAD')
    moved = bool(made) and now != made
    if not made:
        print('  made before gate.py kept its commit, so its HEAD is not compared')
    left = drop_checkout(path)
    if left:
        raise Refuse(left)
    print(f'removed {path}', flush=True)
    if edited or moved:
        said = [f'  {ln}' for ln in edited]
        if moved:
            said.append(f'  HEAD is {now[:8]}, and the checkout was made at {made[:8]}')
        print(f'gate: lane {name} changed tracked files in the commit it checked, committed, or '
              'left that commit, which a lane never does, so its result rests on code that is not '
              'the commit:\n' + '\n'.join(said), file=sys.stderr)
        return 1
    return 0
