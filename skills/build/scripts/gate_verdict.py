"""
gate_verdict — whether a branch's ledger rows make a clean verdict for a patch at a head, and the
counts the verdict prints beside it: the lanes each round size rests on, the live checks and the
gates runs they need, the findings still open, and the failed fixes per premise. These read rows
and write nothing. gate.py's help is the source of truth for what they mean.
"""

from __future__ import annotations

from gate_ledger import MODELS, NOT_RUN, latest, one_line, receipt_state


def declared_checks(rows: list[dict]) -> dict[str, dict]:
    """Each live check declared at the change, at any patch, with its latest declaring row."""
    return {r['name']: r for r in rows if r['kind'] == 'live-check' and r['result'] == 'declared'}


def check_states(rows: list[dict], head: str) -> dict[str, str]:
    """Each declared live check's latest VERIFIED or UNREACHED at `head`, or '' with none there."""
    out = {n: '' for n in declared_checks(rows)}
    for r in rows:
        if r['kind'] == 'live-check' and r['head'] == head and r['result'] != 'declared' \
                and r['name'] in out:
            out[r['name']] = r['result']
    return out


def checked_live(rows: list[dict], lanes: dict[str, dict]) -> tuple[dict[str, dict], list[str]]:
    """`lanes` with the live lane BLOCKED when a declared check is UNREACHED at its commit, and
    why the live lane falls short of its checks.

    Notes
    -----
    A ledger that declares no live check reads as it did before live checks existed.
    """
    c = lanes.get('checker')
    if c and c['result'] in ('PASS', 'ISSUES'):
        gone = sorted(n for n, s in check_states(rows, c['head']).items() if s == 'UNREACHED')
        if gone:
            out, why = checked_live(rows, {**lanes, 'checker': {**c, 'result': 'BLOCKED'}})
            return out, [f"live check(s) {', '.join(gone)} are UNREACHED at {c['head'][:8]}, so "
                         'lane checker is BLOCKED', *why]
    r = lanes.get('live')
    if r and r['result'] == 'NO-RUNTIME' and declared_checks(rows):
        why = (f"lane live is NO-RUNTIME at {r['head'][:8]}, but live check(s) "
               f"{', '.join(sorted(declared_checks(rows)))} are declared, and a declared check "
               'means the change has a runtime surface, so lane live is BLOCKED')
        return {**lanes, 'live': {**r, 'result': 'BLOCKED'}}, [why]
    if not r or r['result'] in ('NO-RUNTIME', 'gap'):
        return lanes, []
    states = check_states(rows, r['head'])
    if not states:
        return lanes, []
    unreached = sorted(n for n, s in states.items() if s == 'UNREACHED')
    if unreached:
        why = (f"live check(s) {', '.join(unreached)} are UNREACHED at {r['head'][:8]}, so lane "
               'live is BLOCKED')
        return {**lanes, 'live': {**r, 'result': 'BLOCKED'}}, [why]
    unrun = sorted(n for n, s in states.items() if s != 'VERIFIED')
    if r['result'] == 'PASS' and unrun:
        return lanes, [f"lane live is PASS at {r['head'][:8]}, but live check(s) "
                       f"{', '.join(unrun)} have no VERIFIED row there"]
    return lanes, []


def gate_runs(rows: list[dict], patch: str, head: str,
              tree: str = '') -> tuple[bool, list[dict]]:
    """Whether the gates lane passed at `head`, whose tree is `tree`, and the rows that decide it.

    Notes
    -----
    A ledger's gates rows from `gate.py run gates` carry an exit code: the lane passed when the
    last run of every command run at `tree` passed, and no command whose last run at `patch`, at
    any head, failed is still unpassed. A run tested the tree, so a commit with the same tree, as
    an amend of its message makes, has the same runs; a row written before gate.py kept the tree
    matches by its head. A row typed before gate.py ran the gates lane has no exit code, and when
    the latest gates row at `patch` is one, it alone decides, as it did.
    """
    mine = [r for r in rows if (r['kind'], r['name'], r['patch']) == ('lane', 'gates', patch)]
    if not mine:
        return False, []
    if not mine[-1]['exit']:
        r = mine[-1]
        return r['result'] == 'PASS' and r['head'] == head, [r]
    last: dict[str, dict] = {}
    owed: dict[str, dict] = {}
    for r in mine:
        if not r['exit']:
            continue
        owed[r['cmd']] = r
        if (r['tree'] == tree) if (r['tree'] and tree) else r['head'] == head:
            last[r['cmd']] = r

    #a failed command stays failed for the patch until it passes at a later head...
    left = [r for c, r in owed.items() if c not in last and r['result'] != 'PASS']
    runs = list(last.values()) + left
    return bool(last) and all(r['result'] == 'PASS' for r in runs), runs


def findings_at(rows: list[dict], patch: str) -> dict[str, dict]:
    """Each finding's deciding row at `patch`: open when its latest row there or anywhere blocks.

    Notes
    -----
    An open finding maps to the blocking row that holds it open, the one at `patch` first. A closed
    one maps to its latest row at `patch`, else its latest row at any patch.
    """
    rows = sorted_rows(rows)
    here = latest(rows, 'finding', patch)
    out  = {**latest(rows, 'finding'), **here}
    for name, r in latest(rows, 'finding').items():
        if r['result'] == 'blocks' and here.get(name, {}).get('result') != 'blocks':
            out[name] = r
    return out


def sorted_rows(rows: list[dict]) -> list[dict]:
    """`rows` without a follow-up or dropped row of a finding that an earlier row sorted as
    blocking: a blocking finding is closed only by a fixed row, so such a row, which `record`
    refuses now and an older ledger may hold, changes nothing."""
    blocked: set[str] = set()
    out = []
    for r in rows:
        if r['kind'] == 'finding':
            if r['result'] == 'blocks':
                blocked.add(r['name'])
            elif r['result'] in ('follow-up', 'dropped') and r['name'] in blocked:
                continue
        out.append(r)
    return out


def size_of(rows: list[dict], patch: str) -> str:
    """The size the root recorded for `patch`'s round, full when it recorded none."""
    sized = [r for r in rows if r['result'] != 'void']
    return latest(sized, 'round', patch).get('round', {}).get('result', 'full')


def unvoided(rows: list[dict]) -> list[dict]:
    """`rows` without those a later `record round void` row voided at its patch.

    Notes
    -----
    A void backs out of a round the operator stopped: it drops every lane row but the gates lane's,
    every VERIFIED or UNREACHED live-check row, and every finding row but a blocking one, recorded
    at its patch before it. A gates run is gate.py's own record and a blocking finding is a defect
    the root verified, so neither is voided.
    """
    voids = [(i, r['patch']) for i, r in enumerate(rows)
             if (r['kind'], r['result']) == ('round', 'void')]
    if not voids:
        return rows

    def voided(i: int, r: dict) -> bool:
        if not any(i < j and r['patch'] == p for j, p in voids):
            return False
        return (r['kind'] == 'lane' and r['name'] != 'gates') \
            or (r['kind'] == 'live-check' and r['result'] != 'declared') \
            or (r['kind'] == 'finding' and r['result'] != 'blocks')
    return [r for i, r in enumerate(rows) if not voided(i, r)]


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


def full_lanes(lanes: dict[str, dict], stood_in: set[str]) -> list[str]:
    """Which lanes the last full round lacks once its BLOCKED and gap lanes were rerun: a live
    lane and two review lanes on two models that read the change.

    Notes
    -----
    A minor or wording round rests on the full round's lanes whatever they found, so a lane that
    ran and failed counts here. A BLOCKED or gap lane did not run: `lanes` holds its rerun at the
    new patch when there is one, and `stood_in` the lanes the checker covered or, for live,
    drove past. A review lane is never stood in for, since one checker is one model, so a BLOCKED
    or gap review counts only once it reruns.
    """
    why  = []
    live = lanes.get('live', {}).get('result')
    if live in (None, 'gap', 'BLOCKED') and 'live' not in stood_in:
        why.append('no live lane ran, and no NO-RUNTIME record says the change has no surface')
    reviews = [r for n, r in lanes.items() if n.startswith('review')
               and r['result'] in ('PASS', 'ISSUES')]
    if len({r['model'].strip().lower() for r in reviews} & set(MODELS)) < 2:
        why.append('fewer than two review lanes on two models read the change')
    return why


def live_passed(rows: list[dict], live: dict | None) -> bool:
    """Whether `live`, the live lane the verdict rests on, passed or was NO-RUNTIME with its live
    checks held at its commit."""
    if not live or live['result'] not in ('PASS', 'NO-RUNTIME'):
        return False
    lanes, why = checked_live(rows, {'live': live})
    return lanes['live']['result'] in ('PASS', 'NO-RUNTIME') and not why


def drove_live(rows: list[dict], live: dict | None, checker: dict) -> bool:
    """Whether `checker` VERIFIED, at its commit, every live check `live` left unverified; a live
    lane that is a gap or missing left every declared check unverified."""
    if not checker:
        return False
    states = check_states(rows, live['head']) if live and live.get('head') \
        else {n: '' for n in declared_checks(rows)}
    left = [n for n, s in states.items() if s != 'VERIFIED']
    now  = check_states(rows, checker['head'])
    return bool(left) and all(now[n] == 'VERIFIED' for n in left)


def unsorted(rows: list[dict], lanes: dict[str, dict]) -> list[str]:
    """Why an ISSUES lane in `lanes` has findings the ledger never sorted: no finding row written
    after it names that lane.

    Notes
    -----
    gate.py never reads a report's prose. The root reads each ISSUES report and records each
    finding it names with `record finding <id> <bucket> --lane <lane>`, so an ISSUES row with no
    such row after it was never sorted. A row before it, such as a blocking row a void kept, sorted
    an earlier report. A finding row written before rows named their lane counts for every ISSUES
    lane at its patch, and a lane row written before gate.py took receipts counts as it did.
    """
    why = []
    for name, r in sorted(lanes.items()):
        if name == 'gates' or r['result'] != 'ISSUES' or not r.get('out'):
            continue
        at = max((i for i, x in enumerate(rows) if x == r), default=-1)
        if not any(x['kind'] == 'finding' and x['result'] != 'fixed'
                   and (x['lane'] == name and i > at
                        or not x['lane'] and x['patch'] == r['patch'])
                   for i, x in enumerate(rows)):
            why.append(f"lane {name} is ISSUES at {r['head'][:8]}, and no finding row written "
                       f'after it names lane {name}: read its report and record each finding it '
                       f'names with `gate.py record finding <id> <bucket> --lane {name}`')
    return why


def fix_unproven(rows: list[dict], r: dict) -> str:
    """'' when the round at fixed row `r`'s patch has a lane that found its sites clean, else what
    that round lacks: a checker for a minor round, a review lane for a full one, and --text for a
    wording round, which runs no lane and closes only a finding whose sites are text.

    Notes
    -----
    A lane at that patch that found the finding still failing is a blocking row for it there,
    recorded by the root from that lane's report, which reopens it; gate.py reads no report.
    """
    size  = size_of(rows, r['patch'])
    lanes = latest(rows, 'lane', r['patch'])
    if size == 'minor':
        if lanes.get('checker', {}).get('result') in ('PASS', 'ISSUES'):
            return ''
        return 'its minor round has no checker lane at that patch'
    if size == 'wording':
        if r['covers'] == 'text':
            return ''
        return ('its wording round runs no lane, so it closes only a finding whose sites are '
                'text (--text)')
    if any(n.startswith('review') and x['result'] in ('PASS', 'ISSUES') for n, x in lanes.items()):
        return ''
    return 'its full round has no review lane at that patch'


def last_full(rows: list[dict], patch: str) -> str:
    """The latest patch before `patch`'s round row whose round is full, or '' when none ran.

    Notes
    -----
    A full round is a patch sized full, by a round row or by having none, at which a lane other
    than the gates lane ran. The gates lane runs at every new head, so a head with gates runs alone,
    such as a fixer's commit that was never code-ready, is no round.
    """
    marks = [i for i, r in enumerate(rows) if r['kind'] == 'round' and r['patch'] == patch
             and r['result'] != 'void']
    for r in reversed(rows[:marks[-1]] if marks else rows):
        if r['kind'] == 'lane' and r['name'] != 'gates' and r['patch'] != patch \
                and size_of(rows, r['patch']) == 'full':
            return r['patch']
    return ''


def verdict(rows: list[dict], patch: str, head: str,
            tree: str = '') -> tuple[bool, list[str], dict]:
    """Whether the rows make a clean verdict for `patch` at `head`, why not, and its lanes.

    Notes
    -----
    A full round needs its own live and review lanes. A minor round takes them from the last full
    round, adds one checker lane at `patch`, and a wording round adds none. Every round needs the
    gates lane at `head`, and every receipt the verdict rests on still matches its file. The lanes
    returned are the ones the verdict rests on.
    """
    rows = unvoided(rows)
    lanes, why = checked_live(rows, latest(rows, 'lane', patch))
    size = size_of(rows, patch)
    if size == 'full':
        why += full_round(lanes)
    else:
        then = last_full(rows, patch)
        if not then:
            why.append(f'a {size} round rests on an earlier full round, and none ran, since the '
                       'first round runs in full')
        else:
            earlier, _ = checked_live(rows, latest(rows, 'lane', then))
            checker = lanes.get('checker', {})
            if checker.get('result') not in ('PASS', 'ISSUES'):
                checker = {}
            drove   = drove_live(rows, earlier.get('live'), checker)
            covered = {n for n in checker.get('covers', '').split() if not n.startswith('review')}
            stood   = covered | ({'live'} if drove else set())

            #a BLOCKED or gap lane did not run, so its rerun here takes its place...
            merged = dict(earlier)
            for name, r in earlier.items():
                rerun = lanes.get(name)
                if r['result'] not in ('BLOCKED', 'gap'):
                    continue
                if rerun and rerun['result'] not in ('BLOCKED', 'gap'):
                    merged[name] = rerun
                elif name.startswith('review'):
                    why.append(f"lane {name} of the full round at patch {then[:12]} is "
                               f"{r['result']}, so it never read the change: it reruns at this "
                               'patch, since one checker is one model and covers no review lane')
                elif name not in stood:
                    why.append(f"lane {name} of the full round at patch {then[:12]} is "
                               f"{r['result']}, so it could not run: it reruns at this patch, or "
                               f"the checker's row covers it (--covers {name})")
            why += [f'the last full round, at patch {then[:12]}, is missing a lane: {w}'
                    for w in full_lanes(merged, stood)]
            rerun = lanes.get('live') if lanes.get('live', {}).get('patch') == patch else None
            if not live_passed(rows, earlier.get('live')) and not live_passed(rows, rerun) \
                    and not drove:
                why.append(f"the last full round's live lane, at patch {then[:12]}, did not pass, "
                           'no live lane passed at this patch, and the checker did not VERIFY '
                           'every live check that live lane left failed or unreached')
            lanes = {**{n: r for n, r in merged.items() if n != 'gates'}, **lanes}
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
    why += unsorted(rows, lanes)
    passed, runs = gate_runs(rows, patch, head, tree)
    failed = [r for r in runs if r['exit'] and r['result'] != 'PASS']
    if not passed and not failed:
        why.append('no gates lane passed at this head, and the checks re-run at every new head')
    elif not passed:
        why += [f"gates command `{r['cmd']}` is {r['result']} at this head"
                + (f" ({r['note']})" if r['note'] else '') for r in failed]
    audit = [(n, r) for n, r in sorted(lanes.items()) if n != 'gates' or not r['exit']]
    for name, r in audit + [('gates', r) for r in runs if r['exit']]:
        state = receipt_state(r)
        if state in ('gone', 'changed'):
            why.append(f"lane {name}'s output file {r['out']} is {state} since its row was "
                       'written, so its receipt cannot be audited')
    for name, r in sorted(findings_at(rows, patch).items()):
        if r['result'] == 'blocks':
            then = '' if r['patch'] == patch else f", recorded at patch {r['patch'][:12]}"
            why.append(f"blocking finding {name} is open{then}; its sites: {r['cmd']}")
        elif r['result'] == 'fixed' and fix_unproven(rows, r):
            why.append(f"finding {name}'s fixed row at patch {r['patch'][:12]} rests on no lane "
                       f"that found its sites clean: {fix_unproven(rows, r)}")
    return not why, why, lanes


def premise_key(premise: str) -> str:
    """A premise as the count compares it: lowercased, spaced once, without a final period."""
    return one_line(premise).lower().rstrip('.')


def row_premise(r: dict) -> str:
    """Blocking row `r`'s count key: the premise it names, compared by premise_key, or its
    finding's ID when it names none, as in a ledger written before premises."""
    return 'premise: ' + premise_key(r['premise']) if r['premise'].strip() else r['name']


def premises(rows: list[dict]) -> dict[str, set[str]]:
    """Each count key, with the IDs of the blocking rows that named it."""
    out: dict[str, set[str]] = {}
    for r in rows:
        if (r['kind'], r['result']) == ('finding', 'blocks'):
            out.setdefault(row_premise(r), set()).add(r['name'])
    return out


def failed_corrections(rows: list[dict]) -> dict[str, int]:
    """For each premise, the patches after its first at which any blocking row named it.

    Notes
    -----
    Each blocking row counts against the premise it names, whatever its ID, so the same ID coming
    back and a new ID naming the same premise are both failed fixes of it, and an ID whose later
    row names another premise counts there. A row that names no premise counts under its ID, as
    before premises existed.
    """
    patches: dict[str, set[str]] = {}
    for r in rows:
        if r['kind'] == 'finding' and r['result'] == 'blocks':
            patches.setdefault(row_premise(r), set()).add(r['patch'])
    return {k: len(p) - 1 for k, p in patches.items() if len(p) > 1}
