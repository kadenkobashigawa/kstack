#!/usr/bin/env python3
"""
gate.py keeps a branch's gate verdict in a ledger, and lands the branch on main once the verdict
is clean. Run it from inside the branch's linked worktree.

  gate.py record lane <name> <PASS|ISSUES|BLOCKED|gap|NO-RUNTIME> --model M --at SHA [--note T]
                          a gap names no commit, so it takes no --at
  gate.py record lane live --kept-from SHA --note T
                          keeps the live row at SHA, from an earlier patch, at this one
  gate.py record finding <id> <act-on|consider|queue|dismissed|nit> [--cmd C] [--note T]
  gate.py record fix <agent> fixed --model M [--note T]
  gate.py status          prints the current patch's lanes, whether its verdict is clean and why
                          not, and each finding's failed corrections, with STOP at two for a
                          finding still act-on. Exits 0 on a clean verdict and 1 otherwise
  gate.py land FILE       refuses an empty patch, a verdict that is not clean, or a main that moved
                          since the merge base. Otherwise it commits the head's tree on main with
                          FILE's message and the verdict, deletes the ledger, and prints the
                          commands that remove the worktree, then the branch

A clean verdict for the current patch needs these lanes, by name:

  gates                   PASS at the current head
  live                    PASS, or NO-RUNTIME
  regression              PASS, whenever live passed
  review...               PASS or ISSUES, on two models

No lane may be BLOCKED or a gap, and no finding may still be act-on.

--at names the commit a lane checked, and that commit must carry the current patch. A gap names
none. Only the live lane outlasts a patch change, because the patch-id rule keeps only a result
with build output. Every other lane runs again. --kept-from names the commit the live drive
checked, at an earlier patch, and the latest live row at that patch must have checked it. gate.py
copies that row's result and model into a new row at this patch. Its note names the commit and,
from --note, the reason. A NO-RUNTIME row drove nothing, so it has no build output to keep, and you
record it again with --at. An act-on finding keeps the command that finds its sites (--cmd). Keep a
finding's id across rounds, because an id still act-on at a later patch is a failed correction. A
fix names the fresh agent that wrote it, never `root`. GATE_MAIN names the main branch (default
`main`).

The ledger is one TSV per branch, `kstack-gate/<branch>.tsv` with each `/` written as `__`, in the
worktree's own git folder (`git rev-parse --absolute-git-dir`). It sits outside the work tree, so
no commit picks it up, and removing the worktree removes it. The same branch name in a new worktree
starts with an empty ledger, and `land` deletes the ledger once main holds the verdict. `record`
refuses a detached HEAD. It also refuses the main worktree, whose git folder is the repository's
own and outlives a deleted branch. git before 2.31 cannot tell the main worktree apart, so there
`record` refuses everywhere. A lane row carries the commit it checked, and any other row carries
the head. Every row carries the stable patch-id of the branch's diff from its merge base with
main, so a new patch starts a new verdict and an old patch's rows never count toward it. gate.py
only appends rows. Within a patch, the latest row for a lane or a finding supersedes the earlier
ones.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import fcntl
import os
import shlex
import subprocess
import sys


COLUMNS = ['ts', 'head', 'patch', 'kind', 'name', 'model', 'result', 'cmd', 'note']
RESULTS = {
    'lane':    {'PASS', 'ISSUES', 'BLOCKED', 'gap', 'NO-RUNTIME'},
    'finding': {'act-on', 'consider', 'queue', 'dismissed', 'nit'},
    'fix':     {'fixed'},
}


def git_bytes(*args: str, cwd: str | None = None, stdin: bytes | None = None) -> bytes:
    """git's stdout as bytes; a failing git prints its own message and exits with its code."""
    p = subprocess.run(['git', *args], cwd=cwd, input=stdin, capture_output=True)
    if p.returncode:
        sys.stderr.write(f'gate: git {args[0]} failed\n{text(p.stderr)}')
        sys.exit(p.returncode)
    return p.stdout


def text(raw: bytes) -> str:
    """Bytes git wrote as text; a name or path that is not UTF-8 keeps its bytes."""
    return raw.decode('utf-8', 'surrogateescape')


def git(*args: str, cwd: str | None = None, stdin: str | None = None) -> str:
    """git's stdout as text, stripped."""
    data = None if stdin is None else stdin.encode()
    return text(git_bytes(*args, cwd=cwd, stdin=data)).strip()


def main_ref() -> str:
    return os.environ.get('GATE_MAIN', 'main')


def patch_of(rev: str) -> tuple[str, str]:
    """The merge base of `rev` with main, and the stable patch-id of the diff from it to `rev`."""
    base = git('merge-base', main_ref(), rev)

    #keep the diff as bytes, as a shell pipe does, since text mode turns a lone CR into a newline...
    pid  = text(git_bytes('patch-id', '--stable', stdin=git_bytes('diff', base, rev))).split()
    return base, pid[0] if pid else 'empty'


def where() -> dict:
    """The branch, its head, its merge base with main and its stable patch-id."""
    head        = git('rev-parse', 'HEAD')
    base, patch = patch_of(head)
    return {'branch': git('rev-parse', '--abbrev-ref', 'HEAD'), 'head': head, 'base': base,
            'patch': patch}


def ledger_path(branch: str) -> str:
    """`branch`'s ledger, in this worktree's own git folder, which goes when the worktree does."""
    name = branch.replace('/', '__') + '.tsv'
    return os.path.join(git('rev-parse', '--absolute-git-dir'), 'kstack-gate', name)


def read_rows(path: str) -> list[dict]:
    """The ledger's rows; a ledger not yet written, or deleted by `land`, has none."""
    try:
        with open(path, newline='') as f:
            return list(csv.DictReader(f, delimiter='\t'))
    except FileNotFoundError:
        return []


def one_line(s: str) -> str:
    return ' '.join(s.split())


def refuse(why: str) -> int:
    print(f'gate: {why}', file=sys.stderr)
    return 2


def branch_at() -> dict:
    """where(), for a row's branch; a detached HEAD, main's worktree or old git exits 2."""
    at = where()
    if at['branch'] == 'HEAD':
        sys.exit(refuse('HEAD is detached; record from the branch being gated'))
    dirs = git('rev-parse', '--path-format=absolute', '--git-dir', '--git-common-dir').split('\n')
    if len(dirs) != 2 or not all(map(os.path.isabs, dirs)):
        sys.exit(refuse('git gave no two absolute git folders, so whether this is the main '
                        'worktree is unknown; --path-format needs git 2.31 or later'))
    if dirs[0] == dirs[1]:
        sys.exit(refuse("this is the main worktree, whose git folder is the repository's own and "
                        "outlives a deleted branch; record from the branch's linked worktree"))
    return at


def append(path: str, row: list[str]) -> None:
    """Append `row` to the ledger at `path`, stamped now, with the header first in a new ledger."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    with open(path, 'a', newline='') as f:

        #one writer at a time, so the size read below is the file this row lands in...
        fcntl.flock(f, fcntl.LOCK_EX)
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        if not os.fstat(f.fileno()).st_size:
            w.writerow(COLUMNS)
        w.writerow([ts, *map(one_line, row)])


def record(kind: str, name: str, result: str, model: str, cmd: str, note: str, sha: str) -> int:
    if result not in RESULTS[kind]:
        return refuse(f'a {kind} result is one of {sorted(RESULTS[kind])}')
    if kind in ('lane', 'fix') and not model:
        return refuse(f'a {kind} row names its model (--model)')
    if kind == 'lane' and not sha and result != 'gap':
        return refuse('a lane row names the commit it checked (--at); only a gap names none, and a '
                      'live result kept from an earlier patch takes --kept-from')
    if kind == 'finding' and result == 'act-on' and not cmd:
        return refuse('an act-on finding keeps the command that finds its sites (--cmd)')
    if kind == 'fix' and one_line(name).lower() == 'root':
        return refuse('the root never writes a fix; name the fresh agent that did')
    at   = branch_at()
    head = at['head']
    if kind == 'lane' and sha:
        head = git('rev-parse', '--verify', f'{sha}^{{commit}}')
    if kind == 'lane' and sha and patch_of(head)[1] != at['patch']:
        return refuse(f'{sha} does not carry the current patch; only the live lane is kept from an '
                      'earlier patch (--kept-from with --note), and every other lane runs again')
    append(ledger_path(at['branch']), [head, at['patch'], kind, name, model, result, cmd, note])
    return 0


def keep(kind: str, name: str, result: str, model: str, cmd: str, note: str, sha: str,
         kept: str) -> int:
    """Keep the latest live row at `kept`'s earlier patch, if it checked `kept`, at this patch."""
    if (kind, name) != ('lane', 'live'):
        return refuse('only the live lane is kept from an earlier patch; the gates and every other '
                      'lane run again at this one')
    if result or model or cmd or sha:
        return refuse('--kept-from takes only --note: the kept row gives the result and the model')
    if not note:
        return refuse('a kept lane says why the patch-id rule keeps it (--note)')
    at   = branch_at()
    head = git('rev-parse', '--verify', f'{kept}^{{commit}}')
    then = patch_of(head)[1]
    if then == at['patch']:
        return refuse(f'{kept} carries the current patch; record its lane with --at')
    path = ledger_path(at['branch'])
    src  = latest(read_rows(path), 'lane', then).get(name)
    if not src:
        return refuse(f'the ledger holds no {name} row at the patch {kept} carries to keep')
    if src['head'] != head:
        return refuse(f"the latest {name} row at the patch {kept} carries checked "
                      f"{src['head'][:8]}, and supersedes any row at {kept}")
    if src['result'] == 'NO-RUNTIME':
        return refuse(f'the {name} row at {kept} is NO-RUNTIME, which has no build output to keep; '
                      'record NO-RUNTIME again with --at at this patch')
    append(path, [head, at['patch'], 'lane', name, src['model'], src['result'], '',
                  f'kept from {head[:8]}: {note}'])
    return 0


def latest(rows: list[dict], kind: str, patch: str) -> dict[str, dict]:
    """The last row of `kind` at `patch` for each name; a later row supersedes."""
    out: dict[str, dict] = {}
    for r in rows:
        if r['kind'] == kind and r['patch'] == patch:
            out[r['name']] = r
    return out


def verdict(rows: list[dict], patch: str, head: str) -> tuple[bool, list[str], dict]:
    """Whether the rows make a clean verdict for `patch` at `head`, why not, and its lanes."""
    lanes = latest(rows, 'lane', patch)
    why   = []
    for name, r in lanes.items():
        if r['result'] in ('BLOCKED', 'gap'):
            why.append(f"lane {name} is {r['result']}, and that is not a pass")
    gates = lanes.get('gates', {})
    if gates.get('result') != 'PASS' or gates.get('head') != head:
        why.append('no gates lane passed at this head, and the checks re-run at every new head')
    live = lanes.get('live', {}).get('result')
    if live not in ('PASS', 'NO-RUNTIME'):
        why.append('no live lane ran, and no NO-RUNTIME record says the change has no surface')
    if live == 'PASS' and lanes.get('regression', {}).get('result') != 'PASS':
        why.append('no regression lane ran the live scenario on main')
    reviews = [r for n, r in lanes.items() if n.startswith('review')
               and r['result'] in ('PASS', 'ISSUES')]
    if len({r['model'] for r in reviews}) < 2:
        why.append('fewer than two review lanes on two models')
    for name, r in sorted(latest(rows, 'finding', patch).items()):
        if r['result'] == 'act-on':
            why.append(f"act-on finding {name} is open; its sites: {r['cmd']}")
    return not why, why, lanes


def failed_corrections(rows: list[dict]) -> dict[str, int]:
    """For each finding, the patches after its first at which its latest row was still act-on."""
    patches = dict.fromkeys(r['patch'] for r in rows if r['kind'] == 'finding')
    counts: dict[str, int] = {}
    for patch in patches:
        for name, r in latest(rows, 'finding', patch).items():
            if r['result'] == 'act-on':
                counts[name] = counts.get(name, 0) + 1
    return {name: n - 1 for name, n in counts.items() if n > 1}


def status() -> int:
    at   = where()
    rows = read_rows(ledger_path(at['branch']))
    ok, why, lanes = verdict(rows, at['patch'], at['head'])
    print(f"{at['branch']} at {at['head'][:8]}, patch {at['patch'][:12]}")
    for name, r in sorted(lanes.items()):
        print(f"  {name:<20} {r['result']:<10} {r['model']}")
    print('  verdict: clean' if ok else '  verdict: not clean')
    for w in why:
        print(f'    - {w}')

    #a finding no longer act-on at this patch has no third fix coming, so only an open one stops...
    now = latest(rows, 'finding', at['patch'])
    for name, n in sorted(failed_corrections(rows).items()):
        stop = ' STOP: write the premise both fixes shared and test it before a third fix' \
            if n >= 2 and now.get(name, {}).get('result') == 'act-on' else ''
        print(f'  finding {name}: {n} failed correction(s).{stop}')
    return 0 if ok else 1


def main_worktree() -> str | None:
    """The worktree that has main checked out, if one does."""
    path = None
    for line in git('worktree', 'list', '--porcelain').splitlines():
        if line.startswith('worktree '):
            path = line[len('worktree '):]
        elif line == f'branch refs/heads/{main_ref()}':
            return path
    return None


def land(message_file: str) -> int:
    at   = where()
    rows = read_rows(ledger_path(at['branch']))
    if at['patch'] == 'empty':
        print(f'gate: not landing, the branch changes nothing against {main_ref()}',
              file=sys.stderr)
        return 1
    ok, why, lanes = verdict(rows, at['patch'], at['head'])
    if not ok:
        print('gate: not landing, the verdict for this patch is not clean:', file=sys.stderr)
        for w in why:
            print(f'  - {w}', file=sys.stderr)
        return 1
    tip = git('rev-parse', main_ref())
    if at['base'] != tip:
        print(f'gate: not landing, {main_ref()} moved since the merge base. Rebase onto it, rerun '
              'the checks and record the lanes the patch-id rule does not keep.', file=sys.stderr)
        return 1
    with open(message_file) as f:
        message = f.read().rstrip()
    lines = [f"GATE VERDICT: clean at {at['head'][:8]}, patch-id {at['patch'][:12]} "
             f"(base {at['base'][:8]})."]
    for name, r in sorted(lanes.items()):
        note = f" ({r['note']})" if r['note'] else ''
        lines.append(f"- {name}: {r['result']}, {r['model']}, at {r['head'][:8]}{note}")
    for r in rows:
        if r['kind'] == 'fix':
            lines.append(f"- fix: {r['name']}, {r['model']}")
    body   = message + '\n\n' + '\n'.join(lines) + '\n'
    tree   = git('rev-parse', f"{at['head']}^{{tree}}")

    #build the cleanup commands before main moves, -D since main gets a new commit, not the head...
    repo   = ['git', '-C', git('rev-parse', '--path-format=absolute', '--git-common-dir')]
    ends   = [[*repo, 'worktree', 'remove', git('rev-parse', '--show-toplevel')],
              [*repo, 'branch', '-D', at['branch']]]
    commit = git('commit-tree', tree, '-p', tip, stdin=body)
    wt = main_worktree()
    if wt:
        git('merge', '--ff-only', '-q', commit, cwd=wt)
    else:
        git('update-ref', f'refs/heads/{main_ref()}', commit, tip)
    os.remove(ledger_path(at['branch']))
    print(f'{main_ref()} is now {commit[:8]}')
    print('remove the worktree, then delete the branch, which git refuses while a worktree has it:')
    for cmd in ends:
        print('  ' + shlex.join(cmd))
    return 0


def run(argv: list[str]) -> int:
    p   = argparse.ArgumentParser(prog='gate.py', description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='action', required=True)
    r   = sub.add_parser('record')
    r.add_argument('kind', choices=sorted(RESULTS))
    r.add_argument('name')
    r.add_argument('result', nargs='?', default='')
    r.add_argument('--at', default='')
    r.add_argument('--kept-from', default='')
    r.add_argument('--model', default='')
    r.add_argument('--cmd', default='')
    r.add_argument('--note', default='')
    sub.add_parser('status')
    sub.add_parser('land').add_argument('message_file')
    a = p.parse_args(argv)
    if a.action == 'record' and a.kept_from:
        return keep(a.kind, a.name, a.result, a.model, a.cmd, a.note, a.at, a.kept_from)
    if a.action == 'record':
        return record(a.kind, a.name, a.result, a.model, a.cmd, a.note, a.at)
    if a.action == 'status':
        return status()
    return land(a.message_file)


if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
