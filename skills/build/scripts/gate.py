#!/usr/bin/env python3
"""
gate.py keeps a branch's gate verdict in a ledger, and lands the branch on main once the verdict
is clean. Run it from inside the branch's linked worktree. references/gate.md holds the rules this
script enforces: what a clean verdict needs, how a later round is sized, when a lane is kept from
an earlier patch, when a finding is open, and when `land` merges past a moved main.

  gate.py record lane <name> <RESULT> --model M --at SHA [--note T]
                          RESULT is PASS, ISSUES, BLOCKED or NO-RUNTIME; M is opus, sonnet, haiku
                          or fable, or root on the gates lane
  gate.py record lane <name> gap --model M [--note T]
  gate.py record lane <name> --kept-from SHA --note T
  gate.py record round <full|minor|wording> --note T
                          the size of this patch's round, and why; a patch with no round row
                          needs a full round
  gate.py record finding <id> <blocks|follow-up|dropped|fixed> [--cmd C] [--note T]
                          --cmd C is required for blocks: the command that finds its sites. The
                          old names are read as the new: act-on as blocks, consider, queue and
                          nit as follow-up, dismissed as dropped
  gate.py record fix <agent> fixed --model M [--note T]
  gate.py status
  gate.py land FILE       FILE holds the commit message; the verdict is appended to it

Exit codes: `record` exits 0, or 2 when it refuses. `status` exits 0 on a clean verdict and 1
otherwise. `land` exits 0 once main holds the commit, and 1 when it refuses. A failing git exits
with git's code. GATE_MAIN names the main branch (default `main`), and GATE_CHECK_PATHS holds the
space-separated pathspecs, read from the repository's top, that decide which checks run.

The ledger is one TSV per branch, `kstack-gate/<branch>.tsv` with the branch name percent-encoded,
in the worktree's own git folder (`git rev-parse --absolute-git-dir`). It sits outside the work
tree, so no commit picks it up, and removing the worktree removes it. Its columns are COLUMNS
below. A lane row's head is the commit it checked, and any other row's head is the branch's head.
patch is the stable patch-id of the branch's diff from its merge base with main, and main is main's
tip when the row was written. gate.py only appends rows, and a later row for a lane or a finding
supersedes the earlier ones.
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
import urllib.parse


COLUMNS = ['ts', 'head', 'patch', 'kind', 'name', 'model', 'result', 'cmd', 'note', 'main']
RESULTS = {
    'lane':    {'PASS', 'ISSUES', 'BLOCKED', 'gap', 'NO-RUNTIME'},
    'round':   {'full', 'minor', 'wording'},
    'finding': {'blocks', 'follow-up', 'dropped', 'fixed'},
    'fix':     {'fixed'},
}
MODELS = ('opus', 'sonnet', 'haiku', 'fable')

#a ledger written before the three buckets, or a brief that still names the five, keeps working...
OLD_BUCKETS = {'act-on': 'blocks', 'consider': 'follow-up', 'queue': 'follow-up',
               'nit': 'follow-up', 'dismissed': 'dropped'}


def git_bytes(*args: str, cwd: str | None = None, stdin: bytes | None = None) -> bytes:
    """git's stdout as bytes. A failing git prints its own message and exits with its code."""
    p = subprocess.run(['git', *args], cwd=cwd, input=stdin, capture_output=True)
    if p.returncode:
        sys.stderr.write(f'gate: git {args[0]} failed\n{text(p.stderr)}')
        sys.exit(p.returncode)
    return p.stdout


def text(raw: bytes) -> str:
    """Bytes git wrote as text. A name or path that is not UTF-8 keeps its bytes."""
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
    return {'branch': branch(), 'head': head, 'base': base, 'patch': patch}


def branch() -> str:
    """The checked-out branch's full name, or 'HEAD' when HEAD is detached."""

    #read the full ref, since a short name is `heads/x` when a tag `x` exists...
    p = subprocess.run(['git', 'symbolic-ref', '-q', 'HEAD'], capture_output=True)
    ref = text(p.stdout).strip()
    return ref[len('refs/heads/'):] if ref.startswith('refs/heads/') else 'HEAD'


def ledger_path(branch: str) -> str:
    """`branch`'s ledger, in this worktree's own git folder, which goes when the worktree does."""

    #percent-encode every byte but letters, digits and `_.-~`, so no two branches share a file...
    name   = urllib.parse.quote(branch.encode('utf-8', 'surrogateescape'), safe='') + '.tsv'
    folder = os.path.join(git('rev-parse', '--absolute-git-dir'), 'kstack-gate')
    path   = os.path.join(folder, name)
    stem   = branch.replace('/', '__')
    old    = os.path.join(folder, stem + '.tsv')

    #the old name is also branch `a__b`'s own, so a ledger moves only when no such branch lives...
    ref  = ['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{stem}']
    live = subprocess.run(ref, capture_output=True).returncode == 0
    if '/' in branch and not live and not os.path.exists(path) and os.path.exists(old):
        os.replace(old, path)
    return path


def read_rows(path: str) -> list[dict]:
    """The ledger's rows. A ledger not yet written, or deleted by `land`, has none."""
    try:
        with open(path, newline='') as f:
            rows = list(csv.DictReader(f, delimiter='\t'))
    except FileNotFoundError:
        return []
    for r in rows:
        if r['kind'] == 'finding':
            r['result'] = OLD_BUCKETS.get(r['result'], r['result'])
    return rows


def one_line(s: str) -> str:
    return ' '.join(s.split())


def refuse(why: str) -> int:
    print(f'gate: {why}', file=sys.stderr)
    return 2


def branch_at() -> dict:
    """where(), for a row's branch. A detached HEAD, main's worktree or old git exits 2."""
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
        w.writerow([ts, *map(one_line, row), git('rev-parse', main_ref())])


def record(kind: str, name: str, result: str, model: str, cmd: str, note: str, sha: str) -> int:
    if kind == 'finding':
        result = OLD_BUCKETS.get(result, result)
    if kind == 'round':
        if result or model or cmd or sha:
            return refuse('a round row takes its size and --note only: record round '
                          '<full|minor|wording> --note <why>')
        name, result = 'round', name
        if not note.strip():
            return refuse('a round row says why the fix is that size (--note)')
    if result not in RESULTS[kind]:
        return refuse(f'a {kind} result is one of {sorted(RESULTS[kind])}')
    if kind in ('lane', 'fix') and not model:
        return refuse(f'a {kind} row names its model (--model)')
    model = one_line(model).lower()
    root = (kind, name, model) == ('lane', 'gates', 'root')
    if kind in ('lane', 'fix') and model not in MODELS and not root:
        return refuse(f'a {kind} row names its model family, one of {", ".join(MODELS)}; only the '
                      'gates lane, which the root runs itself, is recorded as root')
    if kind == 'lane' and result == 'gap' and sha:
        return refuse('a gap names no commit, since the lane reported none; record it without --at')
    if kind == 'lane' and not sha and result != 'gap':
        return refuse('a lane row names the commit it checked (--at); only a gap names none, and a '
                      'result kept from an earlier patch takes --kept-from')
    if kind == 'finding' and result == 'blocks' and not cmd.strip():
        return refuse('a finding that blocks keeps the command that finds its sites (--cmd)')
    if kind == 'fix' and one_line(name).lower() == 'root':
        return refuse('the root never writes a fix; name the fresh agent that did')
    at   = branch_at()
    head = at['head']
    if kind == 'lane' and sha:
        head = git('rev-parse', '--verify', f'{sha}^{{commit}}')
    if kind == 'lane' and sha and patch_of(head)[1] != at['patch']:
        return refuse(f'{sha} does not carry the current patch; a lane the patch-id rule keeps '
                      'from an earlier patch takes --kept-from with --note, and gates runs again')
    path = ledger_path(at['branch'])
    if kind == 'finding' and result == 'fixed':
        was = findings_at(read_rows(path), at['patch']).get(name, {})
        if was.get('result') != 'blocks' or was['patch'] == at['patch']:
            return refuse(f'fixed closes a finding left blocking at an earlier patch, once a later '
                          f'round found its sites clean; {name} is not one')
    append(path, [head, at['patch'], kind, name, model, result, cmd, note])
    return 0


def keep(kind: str, name: str, result: str, model: str, cmd: str, note: str, sha: str,
         kept: str) -> int:
    """Keep the latest `name` lane row at `kept`'s earlier patch, if it checked `kept`, here."""
    if kind != 'lane' or name == 'gates':
        return refuse('only a lane with build output is kept from an earlier patch; gates is the '
                      'checks, which run again at every head')
    if name.startswith('review'):
        return refuse(f'{name} is a review lane, which reads source and has no build output to '
                      'keep; the review of the change runs fresh, recorded with --at')
    if name == 'checker':
        return refuse('checker is the minor round\'s one verifier, which runs at the new patch; '
                      'record it with --at')
    if result or model or cmd or sha:
        return refuse('--kept-from takes only --note: the kept row gives the result and the model')
    if not note.strip():
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


def latest(rows: list[dict], kind: str, patch: str | None = None) -> dict[str, dict]:
    """The last row of `kind` at `patch`, or at any patch, for each name. A later row supersedes."""
    out: dict[str, dict] = {}
    for r in rows:
        if r['kind'] == kind and patch in (None, r['patch']):
            out[r['name']] = r
    return out


def findings_at(rows: list[dict], patch: str) -> dict[str, dict]:
    """Each finding's deciding row at `patch`: open when its latest row there or anywhere blocks.

    Notes
    -----
    An open finding maps to the blocking row that holds it open, the one at `patch` first. A closed
    one maps to its latest row at `patch`, else its latest row at any patch.
    """
    here = latest(rows, 'finding', patch)
    out  = {**latest(rows, 'finding'), **here}
    for name, r in latest(rows, 'finding').items():
        if r['result'] == 'blocks' and here.get(name, {}).get('result') != 'blocks':
            out[name] = r
    return out


def size_of(rows: list[dict], patch: str) -> str:
    """The size the root recorded for `patch`'s round, full when it recorded none."""
    return latest(rows, 'round', patch).get('round', {}).get('result', 'full')


def full_round(lanes: dict[str, dict]) -> list[str]:
    """Why `lanes`, one patch's lanes, are not a full round: a live result and two review models."""
    why  = []
    live = lanes.get('live', {}).get('result')
    if live not in ('PASS', 'NO-RUNTIME'):
        why.append('no live lane ran, and no NO-RUNTIME record says the change has no surface')
    reviews = [r for n, r in lanes.items() if n.startswith('review')
               and r['result'] in ('PASS', 'ISSUES')]

    #count families here too, since a row written before record() checked them holds any text...
    if len({r['model'].strip().lower() for r in reviews} & set(MODELS)) < 2:
        why.append('fewer than two review lanes on two models')
    return why


def last_full(rows: list[dict], patch: str) -> str:
    """The latest patch before `patch`'s round row whose round is full, or '' when none ran."""
    marks = [i for i, r in enumerate(rows) if r['kind'] == 'round' and r['patch'] == patch]
    for r in reversed(rows[:marks[-1]] if marks else rows):
        if r['kind'] == 'lane' and r['patch'] != patch and size_of(rows, r['patch']) == 'full':
            return r['patch']
    return ''


def verdict(rows: list[dict], patch: str, head: str) -> tuple[bool, list[str], dict]:
    """Whether the rows make a clean verdict for `patch` at `head`, why not, and its lanes.

    Notes
    -----
    A full round needs its own live and review lanes. A minor round takes them from the last full
    round, adds one checker lane at `patch`, and a wording round adds none. Every round needs the
    gates lane at `head`. The lanes returned are the ones the verdict rests on.
    """
    lanes = latest(rows, 'lane', patch)
    size  = size_of(rows, patch)
    why   = []
    if size == 'full':
        why += full_round(lanes)
    else:
        then = last_full(rows, patch)
        if not then:
            why.append(f'a {size} round rests on an earlier full round, and none ran, since the '
                       'first round runs in full')
        else:
            earlier = latest(rows, 'lane', then)
            for w in full_round(earlier):
                why.append(f'the full round at patch {then[:12]} is not clean: {w}')
            for name, r in earlier.items():
                if r['result'] in ('BLOCKED', 'gap') and name not in lanes:
                    why.append(f"lane {name} of the full round at patch {then[:12]} is "
                               f"{r['result']}, and that is not a pass")
            lanes = {**{n: r for n, r in earlier.items() if n != 'gates'}, **lanes}
        checker = lanes.get('checker', {})
        if size == 'minor' and (checker.get('patch') != patch
                                or checker.get('result') not in ('PASS', 'ISSUES')):
            why.append('a minor round needs one checker lane at this patch')
        live = lanes.get('live', {})
        if live.get('patch') == patch and live.get('result') not in ('PASS', 'NO-RUNTIME'):
            why.append(f"lane live is {live['result']} at this patch, and that is not a pass")
    for name, r in lanes.items():
        if r['patch'] == patch and r['result'] in ('BLOCKED', 'gap'):
            why.append(f"lane {name} is {r['result']}, and that is not a pass")
    gates = lanes.get('gates', {})
    if gates.get('result') != 'PASS' or gates.get('head') != head or gates.get('patch') != patch:
        why.append('no gates lane passed at this head, and the checks re-run at every new head')
    for name, r in sorted(findings_at(rows, patch).items()):
        if r['result'] == 'blocks':
            then = '' if r['patch'] == patch else f", recorded at patch {r['patch'][:12]}"
            why.append(f"blocking finding {name} is open{then}; its sites: {r['cmd']}")
    return not why, why, lanes


def failed_corrections(rows: list[dict]) -> dict[str, int]:
    """For each finding, the patches after its first at which any row recorded it blocking."""
    patches: dict[str, set[str]] = {}
    for r in rows:
        if r['kind'] == 'finding' and r['result'] == 'blocks':
            patches.setdefault(r['name'], set()).add(r['patch'])
    return {name: len(p) - 1 for name, p in patches.items() if len(p) > 1}


def status() -> int:
    at   = where()
    rows = read_rows(ledger_path(at['branch']))
    ok, why, lanes = verdict(rows, at['patch'], at['head'])
    print(f"{at['branch']} at {at['head'][:8]}, patch {at['patch'][:12]}, "
          f"round {size_of(rows, at['patch'])}")
    for name, r in sorted(lanes.items()):
        print(f"  {name:<20} {r['result']:<10} {r['model']}")
    print('  verdict: clean' if ok else '  verdict: not clean')
    for w in why:
        print(f'    - {w}')

    #a finding still open at this patch stops, since a third fix would start from it...
    now = findings_at(rows, at['patch'])
    for name, n in sorted(failed_corrections(rows).items()):
        stop = ' STOP: write the premise both fixes shared and test it before a third fix' \
            if n >= 2 and now.get(name, {}).get('result') == 'blocks' else ''
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


def changed(base: str, rev: str, *spec: str) -> set[str]:
    """The paths `rev` changes since `base`, both sides of a rename, within pathspecs `spec`."""

    #run from the top, so a pathspec names the same paths from any folder of the worktree...
    top = git('rev-parse', '--show-toplevel')
    raw = git_bytes('diff', '--name-only', '--no-renames', '-z', base, rev, '--', *spec, cwd=top)
    return {text(p) for p in raw.split(b'\0') if p}


def merge_past(base: str, tip: str, head: str) -> tuple[str, str]:
    """The tree merging `head` into `tip`, which moved past `base`, or why a merge check refuses."""
    p = subprocess.run(['git', 'merge-tree', '--write-tree', '--name-only', tip, head],
                       capture_output=True)
    if p.returncode == 1:
        return '', f'git merge-tree of it and the head is not clean:\n{text(p.stdout + p.stderr)}'
    if p.returncode:
        return '', (f'git merge-tree failed with exit {p.returncode}, so the merge went unchecked; '
                    f'one possible cause is a git older than 2.38, which --write-tree needs:'
                    f'\n{text(p.stderr)}')
    both = changed(base, tip) & changed(base, head)
    if both:
        return '', 'it changed paths the patch changes: ' + ', '.join(sorted(both))
    spec = os.environ.get('GATE_CHECK_PATHS', '').split()
    gates = changed(base, tip, *spec) if spec else set()
    if gates:
        return '', 'it changed paths GATE_CHECK_PATHS names: ' + ', '.join(sorted(gates))
    return text(p.stdout).split('\n', 1)[0].strip(), ''


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
    tip  = git('rev-parse', main_ref())
    tree = git('rev-parse', f"{at['head']}^{{tree}}")
    if at['base'] != tip and lanes['gates'].get('main') != at['base']:
        print(f"gate: not landing, {main_ref()} moved since the merge base, and the gates lane at "
              f"this head was recorded while {main_ref()} was not that base. Rebase onto "
              f"{main_ref()}, rerun the gates lane, then land.", file=sys.stderr)
        return 1
    if at['base'] != tip:
        tree, why = merge_past(at['base'], tip, at['head'])
        if why:
            print(f'gate: not landing, {main_ref()} moved since the merge base and {why}. Rebase '
                  'onto it, rerun the checks and record the lanes the patch-id rule does not '
                  'keep.', file=sys.stderr)
            return 1
    with open(message_file) as f:
        message = f.read().rstrip()
    lines = [f"GATE VERDICT: clean at {at['head'][:8]}, patch-id {at['patch'][:12]} "
             f"(base {at['base'][:8]})."]
    if at['base'] != tip:
        lines[0] += (f' {main_ref()} had moved to {tip[:8]}; the merge with it was clean and '
                     'touched no path the patch changes.')
    size = latest(rows, 'round', at['patch']).get('round')
    if size:
        lines.append(f"- round: {size['result']} ({size['note']})")
    for name, r in sorted(lanes.items()):
        note = f" ({r['note']})" if r['note'] else ''
        lines.append(f"- {name}: {r['result']}, {r['model']}, at {r['head'][:8]}{note}")
    for r in rows:
        if r['kind'] == 'fix':
            lines.append(f"- fix: {r['name']}, {r['model']}")
    body   = message + '\n\n' + '\n'.join(lines) + '\n'

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
    print('the root removes the worktree:')
    print('  ' + shlex.join(ends[0]))
    print('then the operator deletes the branch, since git refuses it while a worktree has the '
          'branch, and the git-guard hook refuses git branch -D to agents:')
    print('  ' + shlex.join(ends[1]))
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
