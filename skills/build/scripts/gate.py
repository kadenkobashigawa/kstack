#!/usr/bin/env python3
"""
gate.py keeps a branch's gate verdict in a ledger, runs the gates lane's checks itself, makes and
removes the detached checkouts its lanes run in, and lands the branch on main once the verdict is
clean. Run it from inside the branch's linked worktree. references/gate.md holds the rules this
script enforces; this help is the source of truth for its grammar, and `gate.py <command> --help`
and `gate.py record <kind> --help` print each one's.

  gate.py run gates [--at SHA] -- <cmd...>
      Run one check in a checkout of its own and record it: its command, exit code and output.
  gate.py run gates [--at SHA] --retry
      Rerun the latest failed check at SHA identically, once; a second failure is BLOCKED.
  gate.py run gates [--at SHA] --retry --infra --note CAUSE -- <cmd...>
      Rerun the BLOCKED check <cmd...> at SHA identically, once per tree, after CAUSE, named and
      outside the diff, failed both runs and was cleared; <cmd...> is that check as it ran.
  gate.py lane-checkout <name> [<sha>]
      Make lane <name>'s detached checkout of <sha> (default: the branch's head) at
      <worktree>.lanes/<name>, beside the branch's worktree, and print its path. Refuses a name
      that is not one path segment, or a checkout that is already out.
  gate.py lane-remove <name>
      Print `git status --short` of lane <name>'s checkout, then remove it with --force. Exits 1
      after removing when the lane changed tracked files, committed, or moved the checkout off the
      commit it was made at, since a lane never edits the commit it checks. A lane keeps its
      evidence outside its checkout, which this deletes.

  gate.py record lane <name> <PASS|ISSUES|BLOCKED|NO-RUNTIME> --model M --at SHA --out FILE
                      [--cmd C] [--note T] [--covers LANE ...]
  gate.py record lane <name> gap --model M [--note T]
  gate.py record lane <name> --kept-from SHA --note T
  gate.py record live-check <id> --note T
  gate.py record live-check <id> <VERIFIED|UNREACHED> --at SHA [--note T]
  gate.py record round <full|minor|wording|void> --note T
  gate.py record finding <id> blocks --lane LANE --cmd C --premise P [--note T]
  gate.py record finding <id> <follow-up|dropped> --lane LANE [--cmd C] [--note T]
  gate.py record finding <id> fixed --by AGENT --model M [--text] [--note T]
  gate.py status
  gate.py land FILE       FILE holds the commit message; the verdict is appended to it

The gates lane. gate.py runs it; a typed `record lane gates` row is refused. `run gates` runs the
command after -- in a new detached checkout of SHA (default: the head), <worktree>.lanes/gates-<id>,
made for that run and removed after it, so runs started side by side in the background share no
work tree and a run tests the commit alone, without a shell, and writes the full output to a file
beside the ledger. git keeps every checkout's record in the repository's git folder, so runs take
turns, under a lock there, only to add and remove their checkouts; a failed add leaves no checkout.
Its row keeps the command, the exit code, the commit's tree, the file and its sha256: exit 0 is
PASS and any other exit ISSUES. Run one command per check. A run counts for the commit's tree at
the patch, so a commit with the same tree and patch, as an amend of its message makes, has the same
runs, and a rebase that keeps the tree but changes the patch has none. The gates lane passes at a
head only when the last run at its tree of every command run there exited 0, and no command whose
last run at the patch, at any head, failed is still unpassed: a failed command stays failed for the
patch until it passes at a later head. A subset, --lf or another worker count is a different
command and never clears a failed one. A command runs once per tree. Its one fresh run is `run
gates --retry`, which takes no command and reruns the latest failed one identically at the same
tree: exit 0 is PASS, and a second failure is BLOCKED, since an identical second failure is never a
flake. A BLOCKED command whose two failures a named cause outside the diff made, such as a
dependency that was down, reruns once more at that tree after the cause is cleared, as `run gates
--retry --infra --note CAUSE -- <cmd...>`, naming that command as it ran: exit 0 is PASS, a failure
is BLOCKED for good there, and its row keeps the cause. A command whose program is missing or not
executable never starts: gate.py records it BLOCKED with exit `none`, naming the program. A run that
never started is no run: once the program is installed, the identical command runs again at that
head, or, when it was the retry that never started, --retry does. A tool missing inside a script
exits as the script does, usually 127, and is a failure like any other. `run` exits 0 when the
command passed, 1 when it was recorded ISSUES or BLOCKED, and 2 when it refuses.

Receipts. Every other lane row with a result carries --out, the file holding the lane's full output:
a run lane's command output, or a review lane's report, which gives each finding's command and the
output it printed. gate.py never reads a report: the root does, and records each finding it names
with a finding row that names the lane (Findings, below). gate.py refuses a missing or empty
file, or one inside the branch's worktree or a detached checkout, and stores its absolute path and
sha256. A lane that runs something (every lane but a `review*` lane) also names the full command it
ran, verbatim, with --cmd; a review lane takes no --cmd, since it runs one command per finding and
each blocking finding keeps its own. A rerun of a lane at a commit where its latest row failed
(ISSUES or BLOCKED) must be the identical --cmd: a fresh run is the same full command at the same
commit, never a subset. BLOCKED and NO-RUNTIME rows say why with --note: the missing prerequisite,
or why the change has no runtime surface. `status` prints each lane's command, file and hash, and a
lane whose file is gone or changed since its row was written makes the verdict not clean. A row
written before gate.py took receipts has none and counts as it did.

Live checks. Each live check written up front, before the code, is declared at the change with
`record live-check <id> --note`, its scenario and pass condition. After the live lane runs, each
gets a row from the lane's report: VERIFIED --at the commit the lane drove, or UNREACHED there,
with --note naming the missing prerequisite. `record lane live PASS --at SHA` is refused unless at
least one check is declared and every declared check is VERIFIED at SHA; a check UNREACHED at SHA
makes the live lane BLOCKED, so only BLOCKED is taken there, and the verdict reads a live row with
an UNREACHED check as BLOCKED. A minor round's checker records the checks it drives the same way,
--at its own commit: a check UNREACHED there makes the checker BLOCKED, refused PASS or ISSUES,
and read as BLOCKED. NO-RUNTIME, for a change with no runtime surface, needs no checks, and a
declared check means the change has a surface: NO-RUNTIME is refused once any check is declared,
and an older NO-RUNTIME row beside a declared check reads as BLOCKED. A ledger that declares no live
check reads as it did before live checks existed.

Kept lanes. --kept-from keeps a lane's result from an earlier patch when what the lane ran builds
the same at both commits, and gate.py decides that itself: every path `git diff --name-only`
lists between the kept commit and the head matches a GATE_NOISE_PATHS pathspec, or the
GATE_SAME_BUILD command, run from the repository's top with the kept commit and the head as its
last two arguments, exits 0. Otherwise it refuses, naming the changed paths, and the lane runs
again at this patch, recorded with --at. The comparison's output, written beside the ledger, is
the kept row's receipt, so a keep takes no --cmd or --out. It refuses gates, checker and `review*`
lanes, a NO-RUNTIME source row, and a commit whose latest row at its patch checked another commit.

Rounds. The first round is full. A later round is sized by its fix with `record round`: full for
new behaviour, a redesign or a large new diff; minor, the gates lane and one checker lane at the
new patch, for a minor fix, a rebase or a conflict resolution; wording, the gates lane alone, for a
wording-only change. A patch with no round row is full. A full round's verdict needs its own live
lane, PASS or NO-RUNTIME, and two review lanes on two models, PASS or ISSUES. A minor or wording
round rests on the last full round's lanes as they were, findings included, not on their being
clean, and is refused when no full round ran before it. The last full round is the latest earlier
patch sized full, by a round row or by having none, at which a lane other than the gates lane ran;
a head with gates runs alone, such as a fixer's commit that was never code-ready, is no round. A
wording round reruns nothing, so it is also refused while a lane of the last full round is BLOCKED
or a gap. Its verdict is clean when: the gates lane passes at the head; each lane of the last full
round that was BLOCKED or a gap, which did not run, reruns at the new patch, or, for a lane other
than a review lane, the checker's row covers it (--covers LANE); that round, with those reruns, has
a live lane and two review lanes on two models, PASS or ISSUES, whatever they found, since a review
is never covered (one checker is one model); every blocking finding from any round is closed by a
fixed row its round bears out; and the last full round's live lane passed, or was NO-RUNTIME, with
its live checks VERIFIED at its commit, or a live lane passed at this patch, or the checker
VERIFIED, at its commit, every live check that live lane left failed or unreached. A live pass
before the last full round never counts. A minor round also needs its checker lane, PASS or ISSUES,
at this patch, and a live lane recorded at this patch must be PASS or NO-RUNTIME. In every round,
each ISSUES lane the verdict rests on has at least one finding row written after it that names it
with --lane; a finding row written before rows named a lane counts for every ISSUES lane at its
patch.

An operator's stop mid-round finishes the round or backs out of it. `record round void --note T`
backs out: it voids every lane row but the gates lane's, every VERIFIED or UNREACHED live-check
row, and every finding row but a blocking one, recorded at this patch before it, and the round
reruns. A gates run is gate.py's own record and a blocking finding is a defect the root verified,
so a void keeps both; it keeps the round's size; and a rerun after a voided ISSUES or BLOCKED row
must still be that row's identical --cmd. status and the landed verdict list each void.

Findings. <id> is the finding's ID, R<round>-<X><n>, and the brief gives each lane its own X, so
two lanes of one round never share one: a row is refused for an ID another lane's row first
recorded at this patch. A lane rerun in the same round numbers on from the IDs its letter already
used, and a blocks row is refused for an ID that already blocks at this patch, whichever lane's row
recorded it, so a kept blocking finding is never replaced by a new defect under its ID. A blocks,
follow-up or dropped row names, with --lane, the lane whose report holds the finding; the root reads
each ISSUES report and records each finding it names. A lane at a later patch that reports an
earlier finding still failing is that finding blocking again: the root records it blocks there with
--lane naming that lane, which reopens it and counts against its premise. A blocking row names, with
--premise, the one sentence its fix will assume. Failed fixes are counted per premise: each blocking
row counts against the premise it names, whatever its ID, compared without case, repeated spaces or
a final period, and each later patch at which a blocking row names that premise is a failed fix of
it. status prints each premise's count with its IDs, and STOP at two while one of them is still
open. A blocking row that names no premise, as in a ledger written before premises, counts under its
ID, as it did. A finding sorted blocking is closed only by a fixed row: a follow-up or dropped row
for it is refused, and one in an older ledger reads as nothing. `fixed` closes a finding left
blocking at an earlier patch, and --by names the fresh agent that wrote the fix and --model its
family. --by refuses root, a finding ID's shape (R<n>-...), and any finding ID in the ledger. A
fixed row closes its finding only when the round at its patch has a lane that found the sites clean:
a checker lane (PASS or ISSUES) there for a minor round, or a review lane there for a full round. A
lane there that found it still failing is a blocking row for it there, which keeps it open. A
wording round runs no such lane, so its fixed row closes only a finding whose sites are text and
says so with --text, which gate.py takes as the root's word; a fixed row is refused without --text
where the patch's round is already wording. A fixed row its round does not bear out leaves the
finding open, and a later fixed row may replace it. The old bucket names are read as the new: act-on
as blocks, consider, queue and nit as follow-up, dismissed as dropped. The old `record fix` row is
gone; a ledger's fix rows still read, and land lists them.

A model M is a family: opus, sonnet, haiku or fable, in any case. The gates lane, which gate.py
runs for the root, is recorded as root.

Exit codes: `record` and `lane-checkout` exit 0, or 2 when they refuse. `run` exits 0, 1 or 2 as
above. `lane-remove` exits 0, 1 when the lane changed tracked files or moved its checkout, or 2 when
it refuses. `status` exits 0 on a clean verdict and 1 otherwise. `land` exits 0 once main holds the
commit, and 1 when it refuses. A failing git exits with git's code.

Environment: GATE_MAIN names the main branch (default `main`). GATE_CHECK_PATHS holds the
space-separated pathspecs, read from the repository's top, of the paths that decide which checks
run; a main that moved on one refuses a landing. GATE_NOISE_PATHS holds the space-separated
pathspecs, read the same way, of the paths that never change what a lane builds (empty by
default), and GATE_SAME_BUILD a command that exits 0 when two commits, given as its last two
arguments, build the same (unset by default).

The ledger is one TSV per branch, `kstack-gate/<branch>.tsv` with the branch name percent-encoded,
in the worktree's own git folder (`git rev-parse --absolute-git-dir`). It sits outside the work
tree, so no commit picks it up, and removing the worktree removes it. gate.py's own output files,
from `run gates` and keeps, sit beside it in `kstack-gate/<branch>.runs/`. The ledger's columns are
ts, head, patch, kind, name, model, result, cmd, note, main, out, sha256, by, exit, covers,
premise, tree, lane. A ledger written before out, sha256, by, exit, covers, premise, tree and lane
existed reads with them empty, and a gates row with no tree matches by its head. A lane row's
head, and a VERIFIED or UNREACHED live-check row's, is the commit it checked, and any other row's
head is the branch's head. patch is the verbatim patch-id of the branch's diff from its merge base
with main, `git patch-id --verbatim`, which keeps whitespace, so
a re-indent is a new patch; main is main's tip when the row was written. A row written when gate.py
used `--stable` holds a patch-id no current patch has, so its lanes rerun.
gate.py only appends rows, and a later row for a lane, a finding or a live check supersedes the
earlier ones. covers holds a checker row's --covers lanes, `text` for a fixed row recorded with
--text, or `infra` for a gates run made with --infra. lane holds a finding row's --lane.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys

#gate.py runs as a script or is loaded by path, so its sibling modules are found beside it...
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gate_lanes import lane_checkout, lane_remove, run_gates, same_build                  # noqa: E402
from gate_ledger import (FINDING_ID, LANE_NAME, OLD_BUCKETS, RESULTS, Refuse,  # noqa: E402
                    append, branch_at, changed, family, git, latest, lanes_out, ledger_path, main_ref,
                    main_worktree, one_line, patch_of, read_rows, receipt, receipt_state, sha256,
                    text, where)
from gate_verdict import (check_states, declared_checks, failed_corrections, findings_at,  # noqa: E402
                     fix_unproven, gate_runs, last_full, premises, size_of, unvoided, verdict)


def record_lane(a: argparse.Namespace) -> int:
    if a.name == 'gates':
        raise Refuse('the gates lane is run, not typed: `gate.py run gates [--at SHA] -- <cmd...>` '
                     'runs each check in the lane\'s checkout and records its exit code and '
                     'output, and `gate.py run gates --retry` reruns a failed one')
    if a.covers and (a.name != 'checker' or a.kept_from):
        raise Refuse('--covers names the full-round lanes a minor round\'s checker reran, so only '
                     'a checker row takes it')
    if a.kept_from:
        return keep(a)
    name, result, review = a.name, a.result, a.name.startswith('review')
    for lane in a.covers:
        if not LANE_NAME.fullmatch(lane) or lane in ('gates', 'checker'):
            raise Refuse(f'{lane!r} is not a full-round lane a checker can rerun; gates runs at '
                         'every head, and checker is this row')
        if lane.startswith('review'):
            raise Refuse(f'{lane} is a review lane, and one checker is one model, so it covers no '
                         'review lane; a BLOCKED or gap review reruns at this patch, recorded '
                         'with --at')
    if result not in RESULTS['lane']:
        raise Refuse(f'a lane result is one of {sorted(RESULTS["lane"])}')
    model = family('lane', a.model, gates=name == 'gates')
    if result == 'gap':
        if a.at:
            raise Refuse('a gap names no commit, since the lane reported none; record it without '
                         '--at')
        if a.cmd or a.out:
            raise Refuse('a gap has no run to show; record it with --model and --note only')
    elif not a.at:
        raise Refuse('a lane row names the commit it checked (--at); only a gap names none, and a '
                     'result kept from an earlier patch takes --kept-from')
    if review and a.cmd:
        raise Refuse(f'{name} is a review lane, which runs one command per finding; its report '
                     '(--out) holds them, and each blocking finding keeps its own --cmd')
    ran = not review and result in ('PASS', 'ISSUES', 'BLOCKED')
    if ran and not a.cmd.strip():
        raise Refuse(f'lane {name} ran something; --cmd names the full command it ran, verbatim')
    if result in ('BLOCKED', 'NO-RUNTIME') and not a.note.strip():
        raise Refuse(f'a {result} row says why with --note: the missing prerequisite and the route '
                     'tried, or why the change has no runtime surface')
    out, digest = receipt(a.out) if result != 'gap' else ('', '')
    at   = branch_at()
    head = at['head']
    if a.at:
        head = git('rev-parse', '--verify', f'{a.at}^{{commit}}')
        if patch_of(head)[1] != at['patch']:
            raise Refuse(f'{a.at} does not carry the current patch; a lane the patch-id rule keeps '
                         'from an earlier patch takes --kept-from, and gates runs again')
    path = ledger_path(at['branch'])
    rows = read_rows(path)
    if name in ('live', 'checker') and result in ('PASS', 'ISSUES', 'BLOCKED'):
        live_gate(unvoided(rows), head, result, name)
    if name == 'live' and result == 'NO-RUNTIME' and declared_checks(unvoided(rows)):
        raise Refuse(f"live check(s) {', '.join(sorted(declared_checks(unvoided(rows))))} are "
                     'declared, and a declared check means the change has a runtime surface, so '
                     'the live lane is not NO-RUNTIME: drive the checks, or record BLOCKED with '
                     '--note naming the missing prerequisite')

    #a fresh run after a failure is the identical full command, never --lf or a subset...
    before = [r for r in rows if (r['kind'], r['name'], r['head']) == ('lane', name, head)]
    cmd    = one_line(a.cmd)
    if ran and before and before[-1]['result'] in ('ISSUES', 'BLOCKED') \
            and before[-1]['cmd'] and before[-1]['cmd'] != cmd:
        raise Refuse(f"lane {name}'s last row at {head[:8]} is {before[-1]['result']} from "
                     f"`{before[-1]['cmd']}`; its fresh run is that identical command at the same "
                     'commit, never a subset, --lf or another worker count')
    append(path, {'head': head, 'patch': at['patch'], 'kind': 'lane', 'name': name,
                  'model': model, 'result': result, 'cmd': cmd, 'note': a.note, 'out': out,
                  'sha256': digest, 'covers': ' '.join(dict.fromkeys(a.covers))})
    return 0


def keep(a: argparse.Namespace) -> int:
    """Keep the latest `name` lane row at `kept`'s earlier patch here, once the two builds match.

    Notes
    -----
    gate.py compares the kept commit with the head itself: every path `git diff --name-only`
    lists matches a GATE_NOISE_PATHS pathspec, or the GATE_SAME_BUILD command exits 0 given the
    two commits. The comparison's output is the kept row's receipt.
    """
    name = a.name
    if name.startswith('review'):
        raise Refuse(f'{name} is a review lane, which reads source and has no build output to '
                     'keep; the review of the change runs fresh, recorded with --at')
    if name == 'checker':
        raise Refuse("checker is the minor round's one verifier, which runs at the new patch; "
                     'record it with --at')
    if a.result or a.model or a.at:
        raise Refuse('--kept-from takes no result, --model or --at: the kept row gives the result '
                     'and the model')
    if a.cmd or a.out:
        raise Refuse('--kept-from takes no --cmd or --out: gate.py compares the two commits '
                     'itself, by GATE_NOISE_PATHS and GATE_SAME_BUILD, and keeps that output as '
                     'the receipt')
    if not a.note.strip():
        raise Refuse('a kept lane says why the patch-id rule keeps it (--note)')
    at   = branch_at()
    kept = git('rev-parse', '--verify', f'{a.kept_from}^{{commit}}')
    then = patch_of(kept)[1]
    if then == at['patch']:
        raise Refuse(f'{a.kept_from} carries the current patch; record its lane with --at')
    path = ledger_path(at['branch'])
    src  = latest(unvoided(read_rows(path)), 'lane', then).get(name)
    if not src:
        raise Refuse(f'the ledger holds no {name} row at the patch {a.kept_from} carries to keep')
    if src['head'] != kept:
        raise Refuse(f"the latest {name} row at the patch {a.kept_from} carries checked "
                     f"{src['head'][:8]}, and supersedes any row at {a.kept_from}")
    if src['result'] == 'NO-RUNTIME':
        raise Refuse(f'the {name} row at {a.kept_from} is NO-RUNTIME, which has no build output to '
                     'keep; record NO-RUNTIME again with --at at this patch')
    cmd, out, basis = same_build(path, name, kept, at['head'])
    append(path, {'head': kept, 'patch': at['patch'], 'kind': 'lane', 'name': name,
                  'model': src['model'], 'result': src['result'], 'cmd': cmd,
                  'note': f'kept from {kept[:8]}, {basis}: {a.note}', 'out': out,
                  'sha256': sha256(out)})
    return 0


def record_round(a: argparse.Namespace) -> int:
    if a.size not in RESULTS['round']:
        raise Refuse(f'a round result is one of {sorted(RESULTS["round"])}')
    if not a.note.strip():
        raise Refuse('a round row says why the fix is that size, or why the round is voided '
                     '(--note)')
    at   = branch_at()
    path = ledger_path(at['branch'])
    rows = unvoided(read_rows(path))
    if a.size in ('minor', 'wording'):
        mark = {'kind': 'round', 'name': 'round', 'patch': at['patch'], 'result': a.size}
        then = last_full(rows + [mark], at['patch'])
        if not then:
            raise Refuse(f'a {a.size} round rests on an earlier full round, and none ran before '
                         'this patch; the first round runs in full')
        down = sorted(n for n, r in latest(rows, 'lane', then).items()
                      if r['result'] in ('BLOCKED', 'gap'))
        if a.size == 'wording' and down:
            raise Refuse(f"lane(s) {', '.join(down)} of the last full round, at patch "
                         f'{then[:12]}, are BLOCKED or a gap, and a wording round runs the gates '
                         'lane alone, so nothing would rerun them; size it minor, whose checker '
                         'or a rerun at this patch takes their place')
    append(path, {'head': at['head'], 'patch': at['patch'], 'kind': 'round', 'name': 'round',
                  'result': a.size, 'note': a.note})
    return 0


def record_finding(a: argparse.Namespace) -> int:
    name   = a.id
    result = OLD_BUCKETS.get(a.bucket, a.bucket)
    if result not in RESULTS['finding']:
        raise Refuse(f'a finding result is one of {sorted(RESULTS["finding"])}')
    if result == 'blocks' and not a.cmd.strip():
        raise Refuse('a finding that blocks keeps the command that finds its sites (--cmd)')
    if result == 'blocks' and not a.premise.strip():
        raise Refuse('a finding that blocks names, in one sentence, the premise its fix will '
                     'assume (--premise), since failed fixes are counted per premise')
    if result != 'blocks' and a.premise.strip():
        raise Refuse('--premise is the premise a blocking finding\'s fix will assume, so only '
                     'blocks takes it')
    by, model = one_line(a.by), ''
    if result != 'fixed' and (by or a.model or a.text):
        raise Refuse('--by, --model and --text describe a fix, so only fixed takes them')
    if result == 'fixed' and a.lane:
        raise Refuse('--lane names the lane whose report a blocks, follow-up or dropped row sorts; '
                     'a fixed row sorts no report, and its round\'s lanes bear it out')
    if result != 'fixed' and not a.lane:
        raise Refuse(f'a {result} row names the lane whose report holds the finding (--lane), '
                     'since gate.py reads no report and an ISSUES lane is sorted only by rows that '
                     'name it')
    if result == 'fixed':
        if not by:
            raise Refuse('fixed names the fresh agent that wrote the fix (--by) and its --model')
        if by.lower() == 'root':
            raise Refuse('the root never writes a fix; name the fresh agent that did (--by)')
        if FINDING_ID.match(by):
            raise Refuse(f'{by} is shaped like a finding ID, R<round>-<n>; --by names the agent '
                         'that wrote the fix, and the finding is the first argument')
        model = family('fixed finding', a.model)
    at   = branch_at()
    path = ledger_path(at['branch'])
    rows = unvoided(read_rows(path))
    if a.lane:
        if not LANE_NAME.fullmatch(a.lane):
            raise Refuse(f'{a.lane!r} is not a lane name: one word of letters, digits, `.`, `_` '
                         'and `-`')

        #two lanes of one round number their findings apart, so a new ID is one lane's alone...
        mine  = [r for r in rows if (r['kind'], r['name']) == ('finding', name)]
        other = [r['lane'] for r in mine if r['lane'] not in ('', a.lane)]
        if mine and mine[0]['patch'] == at['patch'] and other:
            raise Refuse(f"{name} is lane {other[0]}'s finding, first recorded at this "
                         f'patch, and two lanes of one round never share an ID: record lane '
                         f"{a.lane}'s finding under an ID of its own, with --note giving the ID "
                         'its report used')

    #a lane that reports twice in one round, rerun after a void, BLOCKED or a gap, numbers from
    #the same round and letter, so a second blocks row at a patch would replace a kept defect...
    if result == 'blocks' and any((r['kind'], r['name'], r['result'], r['patch'])
                                  == ('finding', name, 'blocks', at['patch']) for r in rows):
        raise Refuse(f'{name} already blocks at this patch, from an earlier row, and a blocking '
                     'finding stays open until its own fixed row, so its ID is never reused: give '
                     'the new finding its own ID, the next number after the last its lane\'s '
                     'letter used, with --note giving the ID its report used')
    if result in ('follow-up', 'dropped') and any(
            (r['kind'], r['name'], r['result']) == ('finding', name, 'blocks') for r in rows):
        raise Refuse(f'{name} was sorted blocking, and a blocking finding is closed only by a '
                     f'fixed row its round bears out; it is never re-sorted {result}')
    if result == 'fixed':
        if by in {r['name'] for r in rows if r['kind'] == 'finding'} | {name}:
            raise Refuse(f'{by} is a finding in this ledger; --by names the agent that wrote the '
                         'fix')
        was = findings_at(rows, at['patch']).get(name, {})

        #a fixed row no lane bore out closes nothing, so its finding is still blocking...
        if was.get('result') == 'fixed' and fix_unproven(rows, was):
            was = [r for r in rows if (r['kind'], r['name'], r['result'])
                   == ('finding', name, 'blocks')][-1]
        if was.get('result') != 'blocks' or was['patch'] == at['patch']:
            raise Refuse(f'fixed closes a finding left blocking at an earlier patch, once a later '
                         f'round found its sites clean; {name} is not one')
        if size_of(rows, at['patch']) == 'wording' and not a.text:
            raise Refuse('a wording round runs no lane that finds sites clean, so its fixed row '
                         'closes only a finding whose sites are text, and says so with --text')
    append(path, {'head': at['head'], 'patch': at['patch'], 'kind': 'finding', 'name': name,
                  'model': model, 'result': result, 'cmd': a.cmd, 'note': a.note, 'by': by,
                  'covers': 'text' if a.text else '', 'premise': a.premise, 'lane': a.lane})
    return 0


def record_live_check(a: argparse.Namespace) -> int:
    """Declare a live check up front, or record what the live lane's report says of one."""
    name, state = a.id, a.state
    if not LANE_NAME.fullmatch(name) or name.upper() in RESULTS['live-check']:
        raise Refuse(f'{name!r} is not a live-check id: one word of letters, digits, `.`, `_` and '
                     '`-`, then VERIFIED or UNREACHED to record what the live lane found')
    if state and state not in ('VERIFIED', 'UNREACHED'):
        raise Refuse('a live check is declared with --note alone, then recorded VERIFIED or '
                     'UNREACHED --at the commit the live lane drove')
    at   = branch_at()
    path = ledger_path(at['branch'])
    rows = unvoided(read_rows(path))
    if not state:
        if a.at:
            raise Refuse('a live check is declared at the change, before the code, so it names no '
                         'commit; --at goes on its VERIFIED or UNREACHED row')
        if not a.note.strip():
            raise Refuse('a live check is declared with its scenario and pass condition (--note)')
        append(path, {'head': at['head'], 'patch': at['patch'], 'kind': 'live-check',
                      'name': name, 'result': 'declared', 'note': a.note})
        return 0
    if name not in declared_checks(rows):
        raise Refuse(f'live check {name} was never declared; declare it up front with `gate.py '
                     f'record live-check {name} --note <scenario and pass condition>`')
    if not a.at:
        raise Refuse(f'a {state} row names the commit the live lane drove (--at)')
    if state == 'UNREACHED' and not a.note.strip():
        raise Refuse('an UNREACHED check names the missing prerequisite and the route tried '
                     '(--note)')
    head = git('rev-parse', '--verify', f'{a.at}^{{commit}}')
    if patch_of(head)[1] != at['patch']:
        raise Refuse(f'{a.at} does not carry the current patch; the live lane drives a commit that '
                     'does')
    append(path, {'head': head, 'patch': at['patch'], 'kind': 'live-check', 'name': name,
                  'result': state, 'note': a.note})
    return 0


def live_gate(rows: list[dict], head: str, result: str, lane: str = 'live') -> None:
    """Refuse a live or checker result at `head` that the declared live checks do not bear out.

    Notes
    -----
    A check UNREACHED at `head` makes either lane BLOCKED. Only a live PASS needs every declared
    check VERIFIED, since a checker drives only the checks the earlier live lane left.
    """
    states    = check_states(rows, head)
    unreached = sorted(n for n, s in states.items() if s == 'UNREACHED')
    if unreached and result != 'BLOCKED':
        raise Refuse(f"live check(s) {', '.join(unreached)} are UNREACHED at {head[:8]}, which "
                     f'makes the {lane} lane BLOCKED; record it BLOCKED with --note naming the '
                     'missing prerequisite')
    if result != 'PASS' or lane != 'live':
        return
    if not states:
        raise Refuse('a live PASS rests on the live checks written up front, and the ledger '
                     'declares none; declare each with `gate.py record live-check <id> --note '
                     '<scenario and pass condition>`, or record NO-RUNTIME for a change with no '
                     'runtime surface')
    unrun = sorted(n for n, s in states.items() if s != 'VERIFIED')
    if unrun:
        raise Refuse(f"live check(s) {', '.join(unrun)} have no VERIFIED row at {head[:8]}; record "
                     'each from the live lane\'s report with `gate.py record live-check <id> '
                     'VERIFIED --at SHA`, since a gap is not a pass')


def status() -> int:
    at   = where()
    raw  = read_rows(ledger_path(at['branch']))
    rows = unvoided(raw)
    tree = git('rev-parse', f"{at['head']}^{{tree}}")
    ok, why, lanes = verdict(rows, at['patch'], at['head'], tree)
    print(f"{at['branch']} at {at['head'][:8]}, patch {at['patch'][:12]}, "
          f"round {size_of(rows, at['patch'])}")
    _, runs = gate_runs(rows, at['patch'], at['head'], tree)
    shown   = [(n, r) for n, r in sorted(lanes.items()) if n != 'gates' or not r['exit']]
    shown  += [('gates', r) for r in runs if r['exit']]
    for name, r in sorted(shown, key=lambda nr: nr[0]):
        print(f"  {name:<20} {r['result']:<10} {r['model']:<7} at {r['head'][:8]}")
        if r['cmd']:
            print(f"      cmd: {r['cmd']}" + (f" (exit {r['exit']})" if r['exit'] else ''))
        if r['exit'] and r['note']:
            print(f"      note: {r['note']}")
        state = receipt_state(r)
        if state:
            print(f"      out: {r['out']} (sha256 {r['sha256'][:12]}, {state})")
        elif r['result'] != 'gap':
            print('      out: none, the row was written before gate.py took receipts')
        if name in ('live', 'checker') and r['result'] != 'NO-RUNTIME':
            for check, state in sorted(check_states(rows, r['head']).items()):
                print(f"      live-check {check}: {state or 'not recorded'} at {r['head'][:8]}")
    if 'live' not in lanes:
        for check, r in sorted(declared_checks(rows).items()):
            print(f"  live-check {check} declared: {r['note']}")
    print('  verdict: clean' if ok else '  verdict: not clean')
    for w in why:
        print(f'    - {w}')

    #a finding still open at this patch stops, since a third fix would start from it...
    now = findings_at(rows, at['patch'])
    key = premises(rows)
    for k, n in sorted(failed_corrections(rows).items()):
        ids  = sorted(key.get(k, ()))
        open_ = any(now.get(i, {}).get('result') == 'blocks' for i in ids)
        stop = ' STOP: write the premise both fixes shared and test it before a third fix' \
            if n >= 2 and open_ else ''
        what = f'finding {k}' if not k.startswith('premise: ') else \
            f"premise \"{k[len('premise: '):]}\" ({', '.join(ids)})"
        print(f'  {what}: {n} failed correction(s).{stop}')
    for r in raw:
        if (r['kind'], r['result']) == ('round', 'void') and r['patch'] == at['patch']:
            print(f"  round voided at {r['head'][:8]}: {r['note']}")
    for path in lanes_out():
        print(f'  lane checkout still out: {path} (gate.py lane-remove {os.path.basename(path)})')
    return 0 if ok else 1


def land(message_file: str) -> int:
    try:
        with open(message_file) as f:
            message = f.read().rstrip()
    except OSError as e:
        print(f'gate: not landing, the commit message file {message_file} cannot be read: '
              f'{e.strerror}', file=sys.stderr)
        return 1
    at   = where()
    raw  = read_rows(ledger_path(at['branch']))
    rows = unvoided(raw)
    if at['patch'] == 'empty':
        print(f'gate: not landing, the branch changes nothing against {main_ref()}',
              file=sys.stderr)
        return 1
    tree = git('rev-parse', f"{at['head']}^{{tree}}")
    ok, why, lanes = verdict(rows, at['patch'], at['head'], tree)
    if not ok:
        print('gate: not landing, the verdict for this patch is not clean:', file=sys.stderr)
        for w in why:
            print(f'  - {w}', file=sys.stderr)
        return 1
    tip  = git('rev-parse', main_ref())
    if at['base'] != tip and lanes['gates'].get('main') != at['base']:
        print(f"gate: not landing, {main_ref()} moved since the merge base, and the gates lane at "
              f"this head was recorded while {main_ref()} was not that base. Rebase onto "
              f"{main_ref()}, rerun the gates lane, then land.", file=sys.stderr)
        return 1
    landed = tree
    if at['base'] != tip:
        landed, why = merge_past(at['base'], tip, at['head'])
        if why:
            print(f'gate: not landing, {main_ref()} moved since the merge base and {why}. Rebase '
                  'onto it, rerun the checks and record the lanes the patch-id rule does not '
                  'keep.', file=sys.stderr)
            return 1
    lines = [f"GATE VERDICT: clean at {at['head'][:8]}, patch-id {at['patch'][:12]} "
             f"(base {at['base'][:8]})."]
    if at['base'] != tip:
        lines[0] += (f' {main_ref()} had moved to {tip[:8]}; the merge with it was clean and '
                     'touched no path the patch changes.')
    size = latest([r for r in rows if r['result'] != 'void'], 'round', at['patch']).get('round')
    if size:
        lines.append(f"- round: {size['result']} ({size['note']})")
    _, runs = gate_runs(rows, at['patch'], at['head'], tree)
    for name, r in sorted(lanes.items()):
        if name == 'gates' and r['exit']:
            for g in runs:
                lines.append(f"- gates: {g['result']}, root, at {g['head'][:8]} "
                             f"(`{g['cmd']}`, exit {g['exit']}"
                             + (f"; {g['note']})" if g['note'] else ')'))
            continue
        note = f" ({r['note']})" if r['note'] else ''
        lines.append(f"- {name}: {r['result']}, {r['model']}, at {r['head'][:8]}{note}")
    drives = [lanes[n]['head'] for n in ('live', 'checker')
              if n in lanes and lanes[n]['result'] != 'NO-RUNTIME']
    for check, r in sorted(declared_checks(rows).items()):
        if drives:
            seen = ', '.join(f"{check_states(rows, h)[check] or 'not recorded'} at {h[:8]}"
                             for h in dict.fromkeys(drives))
            lines.append(f"- live-check {check}: {seen} ({r['note']})")
    for r in raw:
        if (r['kind'], r['result']) == ('round', 'void') and r['patch'] == at['patch']:
            lines.append(f"- round voided at {r['head'][:8]} ({r['note']})")
    for r in rows:
        if r['kind'] == 'fix':
            lines.append(f"- fix: {r['name']}, {r['model']}")
        elif r['kind'] == 'finding' and r['result'] == 'fixed' and r['by']:
            lines.append(f"- fix: {r['by']}, {r['model']}, closed {r['name']}")
    body   = message + '\n\n' + '\n'.join(lines) + '\n'

    #build the cleanup commands before main moves, -D since main gets a new commit, not the head...
    repo   = ['git', '-C', git('rev-parse', '--path-format=absolute', '--git-common-dir')]
    ends   = [[*repo, 'worktree', 'remove', git('rev-parse', '--show-toplevel')],
              [*repo, 'branch', '-D', at['branch']]]
    commit = git('commit-tree', landed, '-p', tip, stdin=body)
    wt = main_worktree()
    if wt:
        git('merge', '--ff-only', '-q', commit, cwd=wt)
    else:
        git('update-ref', f'refs/heads/{main_ref()}', commit, tip)
    os.remove(ledger_path(at['branch']))
    print(f'{main_ref()} is now {commit[:8]}')
    for lane in lanes_out():
        print(f'the root removes the lane checkout first: gate.py lane-remove '
              f'{os.path.basename(lane)}')
    print('the root removes the worktree:')
    print('  ' + shlex.join(ends[0]))
    print('then the operator deletes the branch, since git refuses it while a worktree has the '
          'branch, and the git-guard hook refuses git branch -D to agents:')
    print('  ' + shlex.join(ends[1]))
    return 0


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


LANE_USAGE = """\
gate.py record lane <name> <PASS|ISSUES|BLOCKED|NO-RUNTIME> --model M --at SHA --out FILE
                           [--cmd C] [--note T] [--covers LANE ...]
       gate.py record lane <name> gap --model M [--note T]
       gate.py record lane <name> --kept-from SHA --note T"""

LANE_HELP = """\
A lane row: the result of lane <name> at the commit it checked (--at), which must carry the
current patch. The gates lane is never typed: `gate.py run gates` runs and records it, and a
`record lane gates` row is refused.

--out is the file holding the lane's full output, outside the branch's worktree and every lane
checkout; gate.py refuses it missing or empty and keeps its path and sha256. A lane that runs
something, every lane but a `review*` one, names the full command it ran with --cmd, verbatim; a
review lane takes no --cmd, as its report holds one command per finding. A rerun at a commit whose
latest row for the lane is ISSUES or BLOCKED must repeat that row's --cmd exactly. BLOCKED and
NO-RUNTIME take --note: the missing prerequisite and the route tried, or why the change has no
runtime surface. M is opus, sonnet, haiku or fable.

The live lane: PASS is refused unless at least one live check is declared and every declared check
has a VERIFIED row at --at's commit (`gate.py record live-check --help`); a check UNREACHED there
makes the lane BLOCKED, so only BLOCKED is taken. NO-RUNTIME, for a change with no runtime
surface, needs no checks.

The checker lane, a minor round's one verifier, takes --covers LANE ... naming each lane of the last
full round it reran because that lane was BLOCKED or a gap; no other row takes --covers. It never
covers a review lane, since one checker is one model: a BLOCKED or gap review reruns at this patch.

NO-RUNTIME is refused once any live check is declared, since a declared check means the change has
a runtime surface.

gate.py never reads a report. The root reads an ISSUES lane's report and records each finding it
names with `gate.py record finding <id> <bucket> --lane <name>`, and the verdict is not clean until
an ISSUES row has at least one such row written after it.

A gap is a lane that reported no commit: no --at, --cmd or --out.

--kept-from SHA keeps the lane's latest row at SHA's earlier patch, which must have checked SHA,
once gate.py finds the two commits build the same: every path `git diff --name-only SHA HEAD`
lists matches a GATE_NOISE_PATHS pathspec, or the GATE_SAME_BUILD command exits 0 given SHA and
HEAD as its last two arguments. Otherwise it refuses, naming the changed paths: rerun the lane at
this patch and record it with --at. gate.py writes the comparison's output as the kept row's
receipt, so a keep takes no --cmd or --out; --note says why the patch-id rule keeps it. It copies
the kept row's result and model, and refuses checker, `review*` lanes and a NO-RUNTIME row."""

ROUND_USAGE = 'gate.py record round <full|minor|wording|void> --note T'

ROUND_HELP = """\
The size of this patch's round, and why: full for new behaviour, a redesign or a large new diff;
minor for a minor fix, a rebase or a conflict resolution; wording for a wording-only change. The
first round is full, and a patch with no round row needs a full round. A minor or wording round
rests on the last full round's lanes as they were, findings included, and is refused when no full
round ran before it. The last full round is the latest earlier patch sized full, by a round row or
by having none, at which a lane other than the gates lane ran. A minor round adds one checker lane
at this patch, and a wording round adds none, so wording is refused while a lane of the last full
round is BLOCKED or a gap. Every round needs the gates lane at the head. `gate.py --help` (Rounds)
gives the verdict each size needs.

void backs out of a round an operator stopped: it voids this patch's lane rows but the gates
lane's, its VERIFIED and UNREACHED live-check rows, and its finding rows but the blocking ones,
recorded before it, and keeps the round's size. --note says why."""

FINDING_USAGE = """\
gate.py record finding <id> blocks --lane LANE --cmd C --premise P [--note T]
       gate.py record finding <id> <follow-up|dropped> --lane LANE [--cmd C] [--note T]
       gate.py record finding <id> fixed --by AGENT --model M [--text] [--note T]"""

FINDING_HELP = """\
A finding row, <id> being R<round>-<X><n>, X the lane's own letter. The root reads each lane's
report and records each finding it names; gate.py reads no report. blocks, follow-up and dropped
name, with --lane, the lane whose report holds the finding, and an ISSUES lane is not sorted until
a row written after it names it. Each lane's brief gives it its own IDs, so a row is refused for an
ID another lane's row first recorded at this patch, and a blocks row for an ID that already
blocks at this patch, from any lane's row: give the new finding its own ID. A lane at a later patch
that reports an earlier finding still failing is that finding blocking again: record it blocks
there, --lane naming that lane, which reopens it and counts against its premise. fixed takes no
--lane.

blocks needs --cmd, the command that finds its sites, and --premise, the one sentence its fix will
assume; no other row takes --premise. Failed fixes are counted per premise, compared without case,
repeated spaces or a final period: each blocking row counts against the premise it names, whatever
its ID, each later patch at which a blocking row names a premise is a failed fix of it, and status
prints STOP at two. A finding stays open while its latest row at this patch, or at any patch,
blocks. fixed closes one left blocking at an earlier patch, once this round's lanes found its sites
clean: --by names the fresh agent that wrote the fix, never root, a name shaped R<n>-..., or a
finding in the ledger, and --model its family. The fixed row closes the finding only when its
patch's round has a lane that found the sites clean: the checker lane for a minor round, a review
lane for a full one; a lane there that found it still failing is a blocking row there, which keeps
it open. A wording round has none, so its fixed row takes --text, saying the finding's sites are
text, and is refused without it. A fixed row its round does not bear out leaves the finding open,
and a later fixed row may replace it. A finding sorted blocking closes only by a fixed row, so
follow-up and dropped are refused for it. The old bucket names are read as
the new: act-on as blocks, consider, queue and nit as follow-up, dismissed as dropped."""

CHECK_USAGE = """\
gate.py record live-check <id> --note T
       gate.py record live-check <id> <VERIFIED|UNREACHED> --at SHA [--note T]"""

CHECK_HELP = """\
A live check is one of the live checks written up front, before the code: declare each at the
change with --note, its scenario and its pass condition. <id> is one word of letters, digits, `.`,
`_` and `-`. After the live lane runs, record each check from the lane's report: VERIFIED when the
drive reached the path and the pass condition held, UNREACHED when the drive could not reach it,
with --note naming the missing prerequisite and the route tried. --at is the commit the live lane
drove, which must carry the current patch. A later row for a check at the same commit supersedes.

`record lane live PASS --at SHA` is refused unless every declared check is VERIFIED at SHA, and
one UNREACHED there makes the live lane BLOCKED. A check reached whose pass condition failed gets
no VERIFIED row, and the live lane is ISSUES.

A minor round's checker drives the checks the last full round's live lane left failed or
unreached, and records each --at its own commit. VERIFIED there for each of them meets the live
condition of the round's verdict; one UNREACHED there makes the checker BLOCKED."""

RUN_USAGE = """\
gate.py run gates [--at SHA] -- <cmd...>
       gate.py run gates [--at SHA] --retry
       gate.py run gates [--at SHA] --retry --infra --note CAUSE -- <cmd...>"""

RUN_HELP = """\
Run one check of the gates lane in a new detached checkout of SHA (default: the branch's head),
<worktree>.lanes/gates-<id>, made for this run, so runs started side by side share no work tree and
none sees a file an earlier run left, and record it as a gates row: the command, its exit code, the
commit's tree, and its full output in a file gate.py writes beside the ledger, with that file's
sha256. The row is written first, then the checkout is removed, write permission restored so a
read-only folder the check left goes too; a checkout that still cannot be removed stays in git's
list, where status and land name it for lane-remove. The command runs as given, without a
shell; wrap it in `sh -c '...'` to use one. Exit 0 records PASS and any other exit ISSUES. Run one
command per check: the gates lane passes at a head only when the last run at its tree of every
command run there exited 0, and a command whose last run at the patch failed stays failed until it
passes at a later head; a different command, a subset or --lf never clears a failed one. A run
counts for the commit's tree at the patch, so a command runs once per tree there, and an amend that
keeps the tree keeps its runs.

--retry takes no command. It reruns the latest failed command at SHA identically, once: exit 0
records PASS, and a second failure records BLOCKED, since an identical second failure is never a
flake. A BLOCKED command is fixed in a new commit.

--infra, with --retry, --note CAUSE and -- <cmd...>, reruns the BLOCKED command <cmd...> names, as
it ran, at SHA identically, once per command per tree, and refuses one that is not BLOCKED there
with its infrastructure retry unused, when a cause outside the diff failed both runs and is cleared:
a dependency that was down, a port another process held. CAUSE names it and how it was cleared, and
the row keeps it. Exit 0 records PASS, and a failure records BLOCKED, which nothing reruns at that
tree.

git keeps every checkout's record in the repository's git folder, where one add reads another's
half-made record, so runs take turns, under a lock file there, only to add and remove their
checkouts, and run their commands side by side. A failed add leaves no checkout.

A command whose program is missing or not executable never starts: gate.py records it BLOCKED,
with exit `none` and the program named. A run that never started is no run: once the program is
installed, the identical command runs again at that head, or, when it was the retry that never
started, --retry does. A tool a script runs that is missing exits as the script does, usually
127, and is a failure like any other.

Exit codes: 0 when the command passed, 1 when it was recorded ISSUES or BLOCKED, 2 when gate.py
refuses."""


def parser() -> argparse.ArgumentParser:
    raw = argparse.RawDescriptionHelpFormatter
    p   = argparse.ArgumentParser(prog='gate.py', description=__doc__, formatter_class=raw)
    sub = p.add_subparsers(dest='action', required=True, metavar='<command>')
    r   = sub.add_parser('record', help='append a lane, round, finding or live-check row',
                         description='Append one row to the branch\'s ledger. `gate.py record '
                         '<kind> --help` prints that kind\'s grammar.', formatter_class=raw)
    kinds = r.add_subparsers(dest='kind', required=True, metavar='<kind>')
    ln = kinds.add_parser('lane', help='a lane result', description=LANE_HELP,
                          formatter_class=raw, usage=LANE_USAGE)
    ln.add_argument('name')
    ln.add_argument('result', nargs='?', default='')
    ln.add_argument('--at', default='', metavar='SHA')
    ln.add_argument('--kept-from', default='', metavar='SHA')
    ln.add_argument('--model', default='', metavar='M')
    ln.add_argument('--cmd', default='', metavar='C')
    ln.add_argument('--out', default='', metavar='FILE')
    ln.add_argument('--note', default='', metavar='T')
    ln.add_argument('--covers', action='extend', nargs='+', default=[], metavar='LANE')
    rd = kinds.add_parser('round', help="a patch's round size", description=ROUND_HELP,
                          formatter_class=raw, usage=ROUND_USAGE)
    rd.add_argument('size')
    rd.add_argument('--note', default='', metavar='T')
    fd = kinds.add_parser('finding', help='a finding sorted, or closed by a fix',
                          description=FINDING_HELP, formatter_class=raw, usage=FINDING_USAGE)
    fd.add_argument('id')
    fd.add_argument('bucket')
    fd.add_argument('--cmd', default='', metavar='C')
    fd.add_argument('--by', default='', metavar='AGENT')
    fd.add_argument('--model', default='', metavar='M')
    fd.add_argument('--note', default='', metavar='T')
    fd.add_argument('--text', action='store_true')
    fd.add_argument('--premise', default='', metavar='P')
    fd.add_argument('--lane', default='', metavar='LANE')
    lc = kinds.add_parser('live-check', help='a live check declared, or what the live lane found',
                          description=CHECK_HELP, formatter_class=raw, usage=CHECK_USAGE)
    lc.add_argument('id')
    lc.add_argument('state', nargs='?', default='')
    lc.add_argument('--at', default='', metavar='SHA')
    lc.add_argument('--note', default='', metavar='T')
    rn = sub.add_parser('run', help='run one gates check in its checkout and record it',
                        description=RUN_HELP, formatter_class=raw, usage=RUN_USAGE)
    rn.add_argument('lane', choices=['gates'])
    rn.add_argument('--at', default='', metavar='SHA')
    rn.add_argument('--retry', action='store_true')
    rn.add_argument('--infra', action='store_true')
    rn.add_argument('--note', default='', metavar='CAUSE')
    co = sub.add_parser('lane-checkout', help="make a lane's detached checkout, print its path",
                        description='Make lane <name>\'s detached checkout of <sha>, by default '
                        'the branch\'s head, at <worktree>.lanes/<name>, and print its path.')
    co.add_argument('name')
    co.add_argument('sha', nargs='?', default='')
    rm = sub.add_parser('lane-remove', help="print a lane checkout's status, then remove it",
                        description='Print `git status --short` of lane <name>\'s checkout, then '
                        'remove it with --force; exit 1 when the lane changed tracked files, '
                        'committed, or moved the checkout off the commit it was made at.')
    rm.add_argument('name')
    sub.add_parser('status', help='print the verdict for the current patch, and its receipts',
                   description='Print each lane the verdict rests on, with its command, output '
                   'file and hash, each live check, the verdict, each premise\'s failed fixes '
                   'with STOP at two, and each void; exit 0 when the verdict is clean and 1 '
                   'otherwise.')
    sub.add_parser('land', help='land a clean verdict on main as one commit',
                   description='Land the branch on main as one commit whose message is FILE with '
                   'the verdict appended, once the verdict is clean; exit 1 when it refuses.'
                   ).add_argument('message_file', metavar='FILE')
    return p


def run(argv: list[str]) -> int:
    if argv[:2] == ['record', 'fix']:
        print('gate: the fix row is gone; `record finding <id> fixed --by AGENT --model M` closes '
              'a finding and names the fresh agent that wrote its fix', file=sys.stderr)
        return 2

    #a gates command follows --, so its own flags never reach gate.py's parser...
    cmd: list[str] = []
    if argv[:1] == ['run'] and '--' in argv:
        cut = argv.index('--')
        argv, cmd = argv[:cut], argv[cut + 1:]
    a = parser().parse_args(argv)
    try:
        if a.action == 'record':
            return {'lane': record_lane, 'round': record_round, 'finding': record_finding,
                    'live-check': record_live_check}[a.kind](a)
        if a.action == 'run':
            return run_gates(a, cmd)
        if a.action == 'lane-checkout':
            return lane_checkout(a.name, a.sha)
        if a.action == 'lane-remove':
            return lane_remove(a.name)
        if a.action == 'status':
            return status()
        return land(a.message_file)
    except Refuse as why:
        print(f'gate: {why}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
