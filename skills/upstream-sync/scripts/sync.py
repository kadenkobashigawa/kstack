#!/usr/bin/env python3
'''
sync — the deterministic half of upstream-sync: the pins of the sources kstack imports, every
citation kstack makes into them, each citation run against the imported copy and found again at
the newest head, and the suggested refresh. It writes only inside the run folder it is given, and
refuses one inside the repository.

Commands
--------
    check                         offline: upstream/sources.json reads, NOTICE and
                                  upstream/README.md name each row's short commit, every citation
                                  parses and holds against upstream/, and each declared copy equals
                                  its source; exit 1 on a finding
    scan <run>                    refused on a tree whose tracked files differ from HEAD, the commit
                                  remap.patch applies to; check, then a blobless clone of each
                                  repository, fetched again when the run folder holds it, each pin
                                  proved, every change read and each citation found at the head; writes
                                  <run>/ledger.json and <run>/briefs/<n>.md, whole kstack files
                                  packed up to `CAP` bytes a brief
    settle <run>                  refused, creating nothing, on a run folder with no ledger or a
                                  verdict line it cannot read or whose values are not of their
                                  field's type or values; <run>/verdicts.jsonl rechecked
                                  against the head, a suggestion failing whose path is outside
                                  the clone's import path, under another label, or, for a
                                  partial row, not a file reimport.md copies; writes
                                  <run>/remap.patch, from the verdicts and from each moved
                                  citation in the ledger, editing only citations in rows that
                                  move, <run>/sources.next.json, where a row moves to its head
                                  unless its pin did not prove, its head was not fetched, or a
                                  citation into it is blocked, and <run>/reimport.md, and prints
                                  the count per outcome, why each row held at its pin stays
                                  there, and the edits left out because their row holds

    Each command takes `--repo <path>` to read another kstack checkout than the one this script
    sits in.

Data shape
----------
upstream/sources.json holds the import rows and the declared copies. A file under upstream/
belongs to the row whose folder is its longest match. One `Ledger`, saved as <run>/ledger.json, is
keyed by upstream file, `<label>:<path>` at the pin, where the label is the first folder under
upstream/ and the path is inside it, as a citation writes them. Each `UpstreamFile` holds its
import row, its rename or deletion state, the commits that touched it with their full messages,
its pin-to-head line map, and the ids of the citations into it. The ledger holds each
`Citation`, one per path-and-lines pair, by id, its baseline `Check` in `Ledger.baseline` and its
head `Remap` in `Ledger.remaps`, both by the same id. A brief, a group of whole
kstack files packed up to `CAP` bytes, is a projection of the ledger, never a second record.

Modules
-------
Each sits beside this script, which puts its own folder on the import path.

    model :
        the types: the rows of sources.json, a citation and its checks, the ledger, a verdict.
    home :
        where things live, the run files written and read back, and sources.json read.
    cite :
        each citation found in a text, its quote found, and each run against its file.
    locate :
        one citation's passage found at the head.
    scan :
        the clones, the proofs, the changes from pin to head, and the ledger.
    brief :
        the briefs, a projection of the ledger.
    settle :
        the verdicts rechecked, the rows held at their pins, remap.patch and the re-import plan.

Methods
-------
    cmd_check, cmd_scan, cmd_settle :
        the commands.
    main :
        dispatch on the command named first.
'''

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import home                                                              # noqa: E402
from brief import CAP, pack                                              # noqa: E402
from cite import check_all                                               # noqa: E402
from home import clone_dir, git, load, read_sources, run_dir, save, use_repo  # noqa: E402
from model import PASS, Ledger                                           # noqa: E402
from scan import build_ledger                                            # noqa: E402
from settle import (counts, next_sources, patch_edits, patch_text, pin_holds,  # noqa: E402
                    read_verdicts, recheck, reimport_plan)

# the names test_sync.py reads from this module beside the ones the commands use
from brief import brief_text, section_for                                # noqa: E402,F401
from cite import all_citations, parse_text                               # noqa: E402,F401
from home import check_prose                                             # noqa: E402,F401
from model import DECIDED, Import, Sources, Verdict                      # noqa: E402,F401
from settle import _place, copied, remap_patch                           # noqa: E402,F401


def __getattr__(name: str):
    '''`REPO`, `UPSTREAM`, `SOURCES`, `README` and `NOTICE` as `home` holds them now.'''
    if name in ('REPO', 'UPSTREAM', 'SOURCES', 'README', 'NOTICE'):
        return getattr(home, name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def _tally(values) -> str:
    '''a count per value, most first.'''
    seen: dict[str, int] = {}
    for v in values:
        seen[v] = seen.get(v, 0) + 1
    return ', '.join(f'{k} {n}' for k, n in sorted(seen.items(), key=lambda x: (-x[1], x[0])))


def cmd_check(argv: list[str]) -> int:
    '''
    the check command: sources.json, the prose pins, every citation against upstream/, and the
    declared copies, with no network; 0 with no finding, else 1 and one line per finding.
    '''
    try:
        sources = read_sources(home.SOURCES)
    except ValueError as e:
        print(f'finding: {e}')
        return 1
    citations, _, checks, findings = check_all(sources)
    print(f'check: {len(citations)} citation pairs in {len({c.kfile for c in citations})} files; '
          + _tally(c.status for c in checks.values()))
    for f in findings:
        print(f'finding: {f}')
    print(f'{len(findings)} findings' if findings else 'no finding')
    return 1 if findings else 0


def cmd_scan(argv: list[str]) -> int:
    '''
    the scan command: check, then the clones, proofs, remaps, copies and additions, into
    <run>/ledger.json and <run>/briefs/, whose old numbered briefs go first; 0 once written,
    blocked rows too, 1 if sources.json fails or a tracked file differs from HEAD, since the
    citations are read from the working tree and remap.patch applies to HEAD.
    '''
    if len(argv) != 1:
        print('usage: sync.py scan <run> [--repo <path>]')
        return 2
    dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'],
                           cwd=home.REPO, capture_output=True, text=True)
    if dirty.returncode or dirty.stdout.strip():
        names = ', '.join(x[3:] for x in dirty.stdout.splitlines()) or dirty.stderr.strip()
        print(f'finding: scan reads the commit remap.patch applies to, and these tracked files '
              f'differ from HEAD: {names}; commit them first')
        return 1
    run = run_dir(argv[0])
    try:
        sources = read_sources(home.SOURCES)
    except ValueError as e:
        print(f'finding: {e}')
        return 1
    citations, unparsed, checks, findings = check_all(sources)
    for f in findings:
        print(f'finding: {f}')
    ledger = build_ledger(run, sources, citations, checks, unparsed)
    save(run, 'ledger.json', ledger)
    briefs = pack(ledger, run)
    for stale in (run / 'briefs').glob('*.md'):
        if stale.stem.isdigit():
            stale.unlink()
    for n, (_, text) in enumerate(briefs, 1):
        path = run / 'briefs' / f'{n}.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + '\n')
    for row in sources.imports:
        bad = ledger.proof.get(row.folder, [])
        n = len({c.sha for f in ledger.files.values() if f.folder == row.folder for c in f.commits})
        print(f'{row.folder}: {row.commit[:7]} to {ledger.heads.get(row.url, "")[:7]}, '
              + ('proved' if not bad else f'not proved ({len(bad)}: {bad[0]})')
              + f', {n} commits on cited or copied files')
    print(f'baseline: {_tally(c.status for c in ledger.baseline.values())}')
    print(f'at the head: {_tally(r.state for r in ledger.remaps.values())}')
    print(f'added: {len(ledger.added)} ({sum(a.skill for a in ledger.added)} SKILL.md), '
          f'removed: {len(ledger.removed)}')
    print(f'briefs: {len(briefs)}, at most {CAP:,} bytes each but for a file over it alone'
          + ''.join(f'\n  briefs/{n}.md, {len(t.encode()):,} bytes: {", ".join(g)}'
                    for n, (g, t) in enumerate(briefs, 1)))
    print(f'ledger: {run / "ledger.json"}')
    return 0


def cmd_settle(argv: list[str]) -> int:
    '''
    the settle command: each verdict's citation rechecked against the head, then remap.patch,
    sources.next.json read back with `read_sources`, and reimport.md; 0 when every suggested
    citation held, else 1 and one line per citation that did not. A run folder with no ledger,
    or a verdict line `read_verdicts` refuses, is 1 and one line, with nothing written.
    '''
    if len(argv) != 1:
        print('usage: sync.py settle <run> [--repo <path>]')
        return 2
    run = run_dir(argv[0], create=False)
    if not (run / 'ledger.json').is_file():
        print(f'finding: {run} holds no ledger.json; run scan into it first')
        return 1
    ledger: Ledger = load(run, 'ledger.json')
    try:
        verdicts = read_verdicts(run)
    except ValueError as e:
        print(f'finding: {e}')
        return 1
    held, failed, wrong = {}, [], set()
    for i, v in verdicts.items():
        chk = recheck(v, ledger, run)
        if chk and chk.status not in PASS:
            failed.append(f'{i}: the {v.outcome} verdict suggests no citation, and updated means '
                          'the suggested citation points at the passage at the head'
                          if not (v.citation or '').strip() else
                          f'{i}: the suggested ({v.citation}) is {chk.status} at the head')
            held[i] = dataclasses.replace(v, outcome='blocked', citation=None)
            wrong.add(i)
        else:
            held[i] = v
    dates = {url: git('log', '-1', '--format=%cs', 'HEAD', cwd=clone_dir(run, url))
             for url in ledger.heads}
    stays = pin_holds(ledger, held, frozenset(wrong))
    edits, left = patch_edits(ledger, held, frozenset(stays))
    (run / 'remap.patch').write_text(patch_text(ledger, edits))
    moved = next_sources(ledger, stays, dates)
    (run / 'sources.next.json').write_text(json.dumps({
        'imports': [{k: v for k, v in dataclasses.asdict(r).items() if k != 'partial' or v}
                    for r in moved.imports], 'copies': moved.copies}, indent=1) + '\n')
    try:
        read_sources(run / 'sources.next.json')
    except ValueError as e:
        failed.append(f'sources.next.json does not read back: {e}')
    (run / 'reimport.md').write_text(reimport_plan(ledger, moved, stays, left) + '\n')
    for k, n in counts(ledger, held).items():
        print(f'{k}: {n}')
    for folder, why in stays.items():
        print(f'held at the pin: upstream/{folder}, {why}')
    for folder, ids in left.items():
        print(f'left out of remap.patch: upstream/{folder}, its row holds: {", ".join(ids)}')
    for f in failed:
        print(f'finding: {f}')
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    '''
    dispatch on the command named first.

    Parameters
    ----------
    argv : list of str
        the command line after the script's name; `--repo <path>` anywhere names the kstack
        checkout to read.

    Returns
    -------
    int
        the command's exit code, or 2, with this docstring printed, for an unknown command.
    '''
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 >= len(argv):
            print(__doc__)
            return 2
        use_repo(Path(argv[i + 1]))
        argv = argv[:i] + argv[i + 2:]
    commands = {'check': cmd_check, 'scan': cmd_scan, 'settle': cmd_settle}
    if not argv or argv[0] not in commands:
        print(__doc__)
        return 2
    return commands[argv[0]](argv[1:])


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
