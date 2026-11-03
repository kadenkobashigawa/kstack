# The gate

Load this at the last step of the playbook the change routed to (SKILL.md, Playbooks), for every
change that will merge. The gate takes a change from "verified by its author" to "verified by
agents that did not write it". shipping's rule: "Only a verdict from an agent that did not write
the code counts, because an author checks what it meant to build." (pstack,
`skills/poteto-mode/playbooks/shipping.md`, l. 5)

The gate is ported from pstack (Lauren Tan, MIT, `upstream/pstack/`): autopilot-full steps 2 to 5,
shipping's patch-id rule, interrogate's brief and swarm. *(kstack: ...)* marks a departure, and
*(kstack, the translation: ...)* marks where a pstack PR becomes a local branch or commit
(CONTRIBUTING.md, Citations). Background is in `references/evidence.md`.

## The unit of work

Each self-contained change is its own branch, in its own linked worktree, with one owner from build
to merge, and is gated and merged alone (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`,
l. 3). The owner is the only writer of its branch (pstack,
`skills/poteto-mode/playbooks/orchestrate.md`, l. 9), which is why one fresh agent writes each
round's fixes (A fresh agent writes the fix, below). `gate.py record` refuses the main worktree. Run
independent branches in parallel off main and never stack them, so each lands on its own (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 13). That rule covers a queue of independent
items. For dependent work pstack stacks: "Stack a PR only when it builds on another PR." (pstack,
`skills/poteto-mode/playbooks/autopilot-stack.md`, l. 6) kstack sequences instead. A change that
builds on another unmerged branch, or touches a file that branch touches, waits for it to merge,
then branches off the new main *(kstack: a sequenced branch's verdict never ran on code beneath it
that main lacks, so it needs none of a stack's restack rules)*. The root sequences colliding work
(pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 19). *(kstack, the translation:
pstack's unit is a PR, and here it is a local branch.)*

**A file that every change edits is shared state, and the root is its only writer.** A tracker, a
changelog or a todo list that each branch edits makes every landing collide with the next, and
each collision costs a rebase and a gates run. pstack's coordinator keeps "the program's state in
the Project tracker" (pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 5), and the default
for shared state is to "Give each actor its own owned file, key, branch, or state directory, and
merge only at the read/reporting boundary." (pstack,
`skills/principle-separate-before-serializing-shared-state/SKILL.md`, l. 15) So no branch's patch
touches such a file. The root updates it on main after each landing. When an operator's brief puts
it in every branch, the root states that cost and proposes the update on main before it starts.
*(kstack, the translation: the update on main is the reporting boundary. It records a landing, not
a follow-up, which goes only in the Reply and the merge commit, per `references/judgment.md`.)*

A round's findings against the change go back in one fix-forward on the change's own branch. A
defect outside the change is not fixed on this branch. It goes to follow-up
(`references/judgment.md`), since only the fixes that block the work are kept and the rest are
parked as follow-ups (pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 20). A defect
outside the change that blocks it is fixed first, as a change of its own (pstack,
`skills/poteto-mode/playbooks/autonomous-run.md`, l. 9).

## A round

A round starts at the commit the author calls code-ready, and again at each later code-ready
commit that changes the patch, sized as Sizing a later round says. A head the gates lane alone ran
at, such as a fixer's commit that was never code-ready, is no round, and `gate.py` never rests a
sized round on it *(kstack: a review probe's work-in-progress head became the round a later minor
round rested on)*. Each lane names the exact commit it
checked. The round ends when every lane has returned, and no commit moves the branch's head before
then *(kstack: fix commits that moved the head stopped a round's gates lanes mid-suite, per
`references/evidence.md`, Run evidence behind the gate)*.

**Spawn every lane of a round in one message.** "Spawn all N workers in one message" (pstack,
`skills/swarm/SKILL.md`, l. 27). The root starts the gates lane's commands in the same turn. So no
lane of the round is still unspawned when a fixer could start *(kstack: in a build session a fixer
was spawned before the round's live lane, which then checked a head the fix had already moved)*.

**An operator's stop during a round finishes the round or backs out of it.** "Stop at a safe
boundary. Finish the current atomic step or back out of it. Start nothing new, and cancel any
nested subagents." (pstack, `skills/poteto-mode/playbooks/pause-safely.md`, l. 5) *(kstack, the
translation: the round is the atomic step. The root either lets the lanes in flight return and
records them, or stops them and backs out with `gate.py record round void --note <why>`. A void
cancels this patch's lane rows, its VERIFIED and UNREACHED live-check rows and its non-blocking
finding rows recorded before it, and the round reruns at its size. It keeps the gates runs, which
are `gate.py`'s own record, and every blocking finding, a defect the root verified. A lane rerun
after a voided ISSUES or BLOCKED row still repeats that row's `--cmd`. The reply says which way the
round ended, and names the lanes a resume must run at the same commit before any fix starts.)*

**Each lane works in its own detached checkout of the exact commit it checks**, never in the
branch's worktree, so the files under a running lane are that commit's alone. "When workers verify
or measure commits, each brief names the exact SHAs." and "Give each worker its own writable output
when it writes." (pstack, `skills/swarm/SKILL.md`, l. 23) pstack's live lane checks out the head SHA
on its own machine (pstack, `skills/poteto-mode/playbooks/multi-phase-plan.md`, ll. 71, 73). Make
the checkout with `gate.py lane-checkout <name> [<sha>]`, which prints its path, and remove it with
`gate.py lane-remove <name>` once the lane returns. `lane-remove` prints the checkout's status, then
removes it with `--force`, untracked files included, and exits 1 when the lane changed tracked
files, committed, or moved the checkout off the commit it was made at, since a lane never edits the
commit it checks. So each lane brief names an evidence path
outside every worktree, and the lane writes its output there: "Cleanup removes instances and scratch
state, never the evidence" (pstack, `skills/create-verification-skill/SKILL.md`, l. 31). A review
lane keeps its repros in its checkout, as interrogate's brief says, and copies each repro a finding
cites to that path before it returns. The root keeps recording from the branch's worktree, since
`gate.py record` refuses a detached HEAD. *(kstack, the translation: pstack's lane has its own
machine, and a linked worktree gives it only its own files. Ports, database servers, connection
limits and CPU stay shared with every other lane and session on the machine.)*

**Before a round's lanes start, the root reads the project's statement of what can run side by
side**, in its verify skill or its `CLAUDE.md`. pstack's verify skill records it, under Isolate:
"can two instances run side by side (ports, data dirs, profiles)? If not, say so in the generated
skill" (pstack, `skills/create-verification-skill/SKILL.md`, l. 19). Separate the shared state
first, such as a database server or a port per lane: "When concurrent actors might share mutable
state, first ask whether they need the same mutable object. If not, eliminate the sharing." (pstack,
`skills/principle-separate-before-serializing-shared-state/SKILL.md`, l. 9) Serialize only when one
shared target is a real invariant, and then with a lock or a sequential phase, never a note in a
brief: "Only when one shared write target is a real invariant, serialize access structurally"
(pstack, `skills/principle-separate-before-serializing-shared-state/SKILL.md`, l. 16), because
"Instructions and conventions are not concurrency control." (pstack,
`skills/principle-separate-before-serializing-shared-state/SKILL.md`, l. 9) When the project states
no limit and a lane's output shows a shared resource running out, the failure is infrastructure
(lane 1), and the root asks the operator to add the limit to the project's verify skill *(kstack:
the limit is a fact about the project, so the project states it, not kstack)*.

**The author rebases onto main before it reports the code-ready commit**, so verification runs on
the base the patch lands on (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 10).
Before that commit, and before any later commit that needs a verifier, the author runs the
project's checks for the touched paths on the commit itself (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 10). *(kstack, the translation: the
project's checks are the ones its `CLAUDE.md` or `AGENTS.md` files and its rules name, such as
`.claude/rules/` or a contributing guide. kstack's `CONTRIBUTING.md` names
`claude plugin validate .` for changes under `skills/`. A round starts at a commit, not a push.)*

A full round has four lanes. The root runs the gates lane itself, and fresh agents that did not
write the code run the other three (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`,
l. 14).

1. **Gates: the root re-runs every check at the commit.** The root runs each command itself, in the
   background, as `gate.py run gates --at <sha> -- <cmd...>`, one command per check. That runs it
   without a shell in a new detached checkout of the commit, `<worktree>.lanes/gates-<id>`, made
   for that run, and records the command and its exit code, with its full output in a file under
   `kstack-gate/<branch>.runs/` in the worktree's git folder. Then it removes the checkout, write
   permission restored first, so a read-only folder a check left, such as Go's module cache, goes
   too. The row is written before the removal, and a checkout that still cannot be removed stays in
   git's list, so `status` and `land` name it for `gate.py lane-remove` *(kstack: in a review
   probe, a check that left a read-only folder made the removal fail before its row was written,
   on every rerun, and git dropped its record of the leftover, so nothing named it)*. Exit 0 is PASS
   and any other exit ISSUES. So the commands started together in the background share no work
   tree: each actor gets "its own owned file, key, branch, or state directory" (pstack,
   `skills/principle-separate-before-serializing-shared-state/SKILL.md`, l. 15) *(kstack: two runs
   in one shared checkout cleaned away each other's build output, and a run started at one commit
   tested another, in review probes)*. They still share the repository's git folder, where git
   keeps every checkout's record and one `git worktree add` read another's half-made record and
   failed. The record list is one shared target, so `gate.py` serializes access to it with a lock
   file there, held only while it adds or removes a checkout, and the commands run side by side:
   "Only when one shared write target is a real invariant, serialize access structurally" (pstack,
   `skills/principle-separate-before-serializing-shared-state/SKILL.md`, l. 16). A failed add
   leaves no checkout behind *(kstack: in review probes, runs started together failed on git's
   race and left empty checkout folders)*. A run tests the commit alone, since its checkout holds no
   file an earlier run left, and a run counts for the commit's tree at the patch, so a command runs
   once per tree there, and a commit with the same tree and patch, as an amend of its message makes,
   keeps that tree's runs, its used retry and its BLOCKED commands *(kstack: review probes passed a
   broken commit on a build output an earlier run had left, and cleared a BLOCKED command by
   amending the commit message)*. The lane passes at a head when the last run at
   its tree of every command run there exited 0, and no command whose last run at the patch, at any
   head, failed is still unpassed: a failed command stays failed for the patch until it passes at a
   later head. `gate.py` refuses a hand-typed
   gates row, `record lane gates`, so the row is the run, never the root's account of it *(kstack:
   hand-typed gates rows recorded PASS on reruns of only the failed tests, in two build sessions,
   and "If the fix is structural, only use the structural fix." (pstack,
   `skills/principle-encode-lessons-in-structure/SKILL.md`, l. 11))*. No agent is spawned for it: "A
   deterministic lever beats fan-out. If the tool can process every unit in one pass, run it
   yourself." (pstack, `skills/principle-build-the-lever/SKILL.md`, l. 16) The commands are the risk
   list from check 1 (understand), the project's pre-merge checks (tests, lint, type checks), and
   every site command from the previous round's fix briefs (Otherwise, fix forward). When a
   researcher wrote a note for the change, the lane also reads `git status` and the branch diff for
   any file the researcher was not given, since it writes only the one note path its brief names
   (`agents/researcher.md`, Write only the note), and such a file fails the lane *(kstack: the
   operator's proposal, step 1, as no check yet shows Claude Code can limit an agent's Write tool to
   one path)*. The lane runs at every new head, because "every new head needs its own green CI"
   (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 5). A check that cannot run is
   never PASS, and the Reply names what was missing (pstack,
   `automations/benny/skills/reproduce-and-fix-issues/SKILL.md`, l. 183). A command whose program is
   missing or not executable never starts, and `gate.py` records it BLOCKED with exit `none`, naming
   the program. A run that never started is no run, so once the program is installed the identical
   command runs again at that head, or `--retry` does when the retry was what never started. A tool
   missing inside a script, or refused access, exits as the script does and is recorded ISSUES, a
   failure like any other. **A failing check that might be a flake is classified before any rerun.**
   "Flake or infrastructure earns one fresh build, never a job retry. One retry only. An identical
   second failure means it was never flake, so reclassify and read the child logs instead of
   retrying blind. A failure in code the diff never touches means a stale base, so check with `git
   merge-base --is-ancestor` before assuming flake. Report a stale base as needing a rebase instead
   of burning retries. Only a failure in the diff's own code gets a commit." (pstack,
   `skills/poteto-mode/playbooks/babysit.md`, l. 19) *(kstack, the translation: a fresh build is the
   identical full command at the same commit, which `gate.py run gates --retry` reruns once. A rerun
   of only the failed tests, such as `pytest --lf` or a list of failing files, or a rerun with a
   changed worker count, is a job retry, and is a different command that never clears the failed
   one. `--retry` takes no command, so it cannot run one. A retry that exits 0 records PASS, which
   clears the command, since its last run passed. A second failure records it BLOCKED, and the fix
   is a new commit. The child logs are that command's full output,
   which `gate.py` records, and the stale-base check is `git merge-base --is-ancestor main
   <commit>`.)* **A BLOCKED command whose cause is outside the diff reruns once more, named.** When
   the child logs show both failures came from infrastructure the diff never touches, such as a
   dependency that was down or a port another process held, and the cause is cleared, the root
   reruns it once at that tree with `gate.py run gates --retry --infra --note <cause> -- <cmd...>`,
   the cause and how it was cleared, naming that command exactly as it ran. `gate.py` refuses a
   command that is not BLOCKED there with its infrastructure retry unused, so another BLOCKED
   command never reruns under that cause *(kstack: in a review probe, an infrastructure retry with
   no command reran the latest BLOCKED one, a failure in the diff, and it passed under the other
   command's cause)*. Exit 0 records PASS, and a failure records BLOCKED, which nothing reruns
   at that tree. The row and the landed verdict keep the cause, and the Reply names it. A failure
   in the diff's own code, or a cause the root cannot name, is never infrastructure: it gets a
   commit, as babysit says *(kstack: babysit's one retry assumes the infrastructure is back on the
   fresh build, and a review probe showed a command BLOCKED by a dependency that was down could not
   be rerun once it was up, since a commit that keeps the tree keeps the BLOCKED run)*. A flake
   that passes on its one fresh run is still named in the Reply, by test and
   command *(kstack: rule 15 in `references/rules.md` makes a flaky test a defect, so it is recorded
   rather than dropped)*.
2. **Live: prove the load-bearing behaviour on the real surface the change touches**, through the
   project's verify skill (`verify-<app>`). It drives the live checks the root wrote up front,
   before the code, each one user flow with a scenario and a pass condition
   (`references/understand.md`, Write the live checks before the code). "The verdict is not clean
   without the live lane, or before you audit the merge-ready report's receipts, because no lane
   trusts a claim it has not checked." (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`,
   l. 14) The receipts audit is in The verdict, below. The drive covers the load-bearing
   behaviour, not every claim. Pick the smallest local surface that can disprove a claim
   (cursor-team-kit, `skills/verify-this/SKILL.md`, l. 22), so a claim that a unit, a script or a
   fixture can disprove is a test in the gates lane. A round builds one test copy of the app per
   version under test, not one per claim *(kstack: a copy per claim adds builds and agents but no
   evidence)*.
   **Each live check is a row in the ledger.** The root records each check as it writes it, with
   `gate.py record live-check <id> --note <scenario and pass condition>`. The live lane's report
   gives each check VERIFIED or UNREACHED, and the root records each with
   `gate.py record live-check <id> <VERIFIED|UNREACHED> --at <sha>`. "For coverage, every required
   slice needs a result." (pstack, `skills/swarm/SKILL.md`, l. 37) *(kstack, the translation: each
   live check written up front is a required slice.)* `gate.py` refuses `record lane live PASS --at
   <sha>` unless at least one check is declared and every declared check is VERIFIED at that commit,
   and a check UNREACHED there makes the lane BLOCKED, the only result it then takes. A check that
   ran and failed gets neither row, and the lane reports ISSUES with that finding. **A drive that
   cannot reach the load-bearing path is BLOCKED**, and its row names the missing prerequisite and
   the route tried. "A feature that can't be reached is `verified-unreachable` only with the
   concrete prerequisite (auth, entitlement, OS, external state) and the route attempted" (pstack,
   `skills/maintain-verification-skill/SKILL.md`, l. 33). The fix is a project fixture, recorded in
   the verify skill's Gotchas, never an easier check: "Never weaken the journey to make it pass."
   (pstack, `skills/create-verification-skill/SKILL.md`, l. 36) For example, a check passes when a
   saved record survives a reload. A drive that stopped at a sign-in refusal and judged the save
   from the page's source never reached that path. It reports the check UNREACHED and names the
   missing test account, and the lane is BLOCKED, not PASS *(kstack: live lanes recorded PASS on
   drives that never reached the path, in two build sessions)*. A change with no runtime surface
   records that fact instead, with `gate.py record lane live NO-RUNTIME --model <family> --at <sha>
   --out <file> --note <why>`, which needs no `--cmd` and no live checks *(kstack: pstack's lanes
   all drive a surface, so it has no record for a change without one)*. NO-RUNTIME is never the
   outcome of a drive that could not reach a surface the change has. A declared live check means
   the change has a surface, so `gate.py` refuses NO-RUNTIME once any check is declared, and reads
   an older NO-RUNTIME row beside a declared check as BLOCKED *(kstack: a review probe recorded
   NO-RUNTIME over an UNREACHED check and landed)*.
3. **Review: two lanes, one on Opus and one on Sonnet, try to break the change.** Both get the
   same brief, interrogate's, verbatim (pstack, `skills/interrogate/SKILL.md`, l. 19):

   > Break this change. Prove each finding with a run against the real code, such as a failing
   > test, a repro script, or command output that shows the wrong behavior. For a design or plan,
   > run a prototype or probe the current tree. Keep repros in your own worktree. Report each
   > finding with a title, the exact command, the output it printed, and the output the intent
   > requires. Leave out anything you did not run. That covers style, naming, structure, and risks
   > that need a future change to matter. No findings is a valid result.

   One clause follows it: "Also report each doc line the change made wrong, with the line and the
   command or file that shows it is wrong." autopilot-full blocks for "a doc line the PR made
   wrong" (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 16), and without the clause
   "Leave out anything you did not run" would let a reviewer skip a false sentence *(kstack: the
   operator's proposal, step 6)*. A second clause follows: "Tag each finding R<round>-<X><n>, with
   this round's number and your lane's letter <X>, and for each earlier finding this brief names,
   say whether it still fails." The root gives each lane its own letter, so two lanes of one round
   never share an ID, and `gate.py` refuses a finding row for an ID another lane's row first
   recorded at this patch *(kstack: two review lanes both numbered their findings from R<round>-1,
   and one finding row sorted both, in review probes)*. A lane rerun in the same round, after a
   void, a BLOCKED row or a gap, gets the same clause and one more: "Number your findings on from
   R<round>-<X><n>, the last ID your letter used." The root fills in that ID, or gives the rerun the
   next unused letter. `gate.py` refuses a blocking row for an ID that already blocks at this
   patch, whichever lane's row recorded it, and the root records the new finding under an ID of its
   own *(kstack: a lane rerun after a void numbered from R1-A1 again, and its blocking row replaced
   the one the void kept, so that defect landed, in a review probe)*. `gate.py` reads no
   report. The root reads it and records each finding it names (The root audits each lane's
   receipts, below) *(kstack: a script that read IDs out of a report's text missed a regression
   and read a clean mention as a failure, in review probes)*. The brief's scope is the branch diff
   from its merge base with main, and its intent is the change's stated intent (pstack,
   `skills/interrogate/SKILL.md`, l. 13). It has the fields in SKILL.md, The brief, and its CONTEXT
   also carries every capability the change drops, with who approves each loss, the person who asked
   or this verdict under the operator's grant, per check 2 in `references/simplify.md` *(kstack, as
   that rule is)*. Adversaries find different failures, so the verdict keeps every verified finding,
   not one lane's list (pstack, `skills/interrogate/SKILL.md`, l. 25). *(kstack: Claude Code runs
   only Claude models, so the two lanes use two Claude models and name which ran. pstack puts each
   verifier on a different model family (pstack, `skills/poteto-mode/playbooks/orchestrate.md`,
   l. 13), and two Claude models are weaker diversity than that.)* A lane's `--model` is its family,
   `opus`, `sonnet`, `haiku` or `fable`, in any case, and `gate.py` refuses any other name, so two
   spellings of one family never count as two models *(kstack: free-text model names let "opus"
   and "Opus" pass as two)*. A review lane's name starts with `review`.

pstack no longer requires a regression drive on trunk. A failure on trunk behaviour "is recorded
against trunk and does not block the PR" (pstack,
`skills/poteto-mode/playbooks/multi-phase-plan.md`, l. 66). When a finding's origin is in doubt, the
root reruns it at the base commit instead (`references/judgment.md`, The three buckets).

**Every lane and fixer brief has the fields in SKILL.md, The brief.** A lane's SCOPE is its
detached checkout of the exact commit, and its REPORT names that commit and tags each finding as
lane 3's second clause says, for the live lane and the checker too.

## Sizing a later round

"A full swarm runs once, at the code-ready head. Another full swarm runs only for new behavior, a
redesign, or a large new diff. A rebase, a merge-conflict resolution, or a minor fix gets a single
verifier at the new head, and a wording-only change gets none." (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 14) So the first round always runs in full,
one-line fixes included, and the kind of the fix alone decides the size of each later round:

- **Full**, for new behaviour, a redesign or a large new diff: all four lanes again.
- **Minor**, for a minor fix, or a rebase or a conflict resolution that changes the patch-id: the
  gates lane and one checker lane, named `checker`, at the new patch. The checker is one fresh
  agent that did not write the code and runs the change the way a user would (pstack,
  `skills/poteto-mode/playbooks/shipping.md`, l. 5).
- **Wording**, for a wording-only change: the gates lane alone. Nothing in a wording round reruns
  a lane, so `record round wording` is refused while a lane of the last full round is BLOCKED or a
  gap, and that round is sized minor instead *(kstack: the gates lane alone cannot replace a lane
  that never ran)*.

**A rebase or a conflict resolution that leaves the patch-id unchanged keeps the verdict**, and the
new head reruns the gates lane only. In pstack, "a PR whose `git patch-id` the restack leaves
unchanged keeps its verdict." (pstack, `skills/poteto-mode/playbooks/autopilot-stack.md`, l. 6),
and "every new head needs its own green CI" (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 5). *(kstack: autopilot-full l. 14 gives "A
rebase, a merge-conflict resolution" a single verifier. kstack reads that as a rebase that changes
the patch-id, which reconciles l. 14 with the patch-id lines. pstack never states that reading.)*
Two safeguards still hold. When main changed a caller of the patch, or something the patch depends
on, the patch's checks run on the merge result (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 19), as Merge preparation, step 3, says. When
code the verdict ran on is no longer beneath the patch, as after main reverted a commit, the patch
needs a fresh verdict: "It needs a fresh verdict first, because its old one ran with that code
beneath it and trunk does not have it." (pstack, `skills/poteto-mode/playbooks/shipping.md`, l. 6)

Upstream gives no line count for "minor" or "large", so the root makes the call by the kind of
change. Wording-only means text no program or agent acts on, such as a README, a product or design
record, or a comment. In a skill set, a `SKILL.md`, a reference or an agent's definition is code,
since an agent runs it *(kstack: the meaning of docs the patch-id rule below already uses)*. The
root records the size and why with `gate.py record round <full|minor|wording> --note <why>`, and a
patch with no round row needs a full round. `record round minor` or `wording` is refused when no
full round ran before it. A full round never repeats to convergence: "Each fix
adds new code to review", and "There is no convergence guarantee." (mattpocock-skills,
`docs/engineering/code-review.md`, l. 77)

**A sized round rests on the last full round before it, findings included.** That round is the
latest earlier patch sized full, by a `round full` row or by having no round row, at which a lane
other than the gates lane ran. `gate.py status` counts that round's lanes, at the commits they
checked, toward a minor or wording round's verdict, and every finding they raised stays open until a
later row closes it. The full round need not have been clean: what a sized round needs to be clean
is in The verdict, below. The verdict block in the merge commit lists the full round's lanes at the
commits they checked. *(kstack: upstream names no condition on the full round's result.
autopilot-full l. 14 sizes each later round by the kind of its fix alone, so a full round that found
defects is still the base, and its findings carry forward instead of forcing another full round.)*

**A fix round stays on its base.** Rebase again only "on a `git merge-tree` conflict with trunk, on
a CI failure that comes from a change on trunk, or when a known concurrent change to the same files
lands" (pstack, `skills/poteto-mode/playbooks/multi-phase-plan.md`, l. 61), because each rebase
restarts the checks (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 10). *(kstack,
the translation: a CI failure is a gates-lane failure that the stale-base check in lane 1 traces
to main, and a known concurrent change is a commit on main that touches a file the branch
changes.)*

## Staffing

SKILL.md's "## Subagents" holds the general rules, such as which model writes a fix and the effort
each role runs at. The gate adds which model runs each lane.

- **The two review lanes run one on Opus and one on Sonnet, with the same brief**, as lane 3 says.
  "A second opinion is the same prompt against a different model." (pstack,
  `skills/poteto-mode/SKILL.md`, l. 100)
- **The live lane and the checker run on Sonnet.** Verification stays on the `swarm workers`
  model (pstack, `skills/poteto-mode/SKILL.md`, l. 98), whose default is `grok-4.7-xhigh-fast`
  (pstack, `skills/swarm/SKILL.md`, l. 22). *(kstack, the translation: Claude Code runs only Claude
  models, so the default worker model is Sonnet.)*
- **The gates lane is no agent**, since the root runs its commands (lane 1), so its rows carry
  `root` as the model, which no other row takes.

## The verdict

Each lane returns `PASS`, `ISSUES` or `BLOCKED` with evidence. A lane that can prove a defect
reports `ISSUES` and lists every issue it can prove, not only the first (pstack,
`skills/swarm/SKILL.md`, l. 31). A lane agent that doesn't report the commit it checked is re-run
once, and after that it is a gap, `gate.py record lane <name> gap --model <family>`, with no
`--at`, `--cmd` or `--out` since it named no commit. The gates lane is never a gap, since `gate.py`
runs it and refuses every typed `record lane gates` row. A gap does not count as a pass (pstack,
`skills/swarm/SKILL.md`, l. 37).

**The ledger records the verdict.** The root writes each lane result, live check, round size and
finding, with the `fixed` row that closes a finding, to the branch's ledger with
`scripts/gate.py record`, and the gates lane with `gate.py run gates`, each run as
`$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/scripts/gate.py`. `gate.py status` says whether the verdict
is clean. A verdict covers one head SHA, so a new push needs a new verdict (pstack,
`skills/poteto-mode/playbooks/orchestrate.md`, l. 19). Each row carries the patch-id, and a lane
counts only at its own patch, except the earlier full round a sized round rests on. The ledger,
not memory or the transcript, answers whether a change was verified *(kstack: build has no forge
to hold a verdict, so a file the script reads holds it)*. A finding carries across patches, as
"A finding stays open until a later row closes it", below, says. `record` runs only in the
branch's own linked worktree, so the ledger goes when the worktree does: it refuses a detached
HEAD and the main worktree, whose git folder outlives a deleted branch, and on git older than
2.31, which cannot tell the main worktree apart, it refuses everywhere.

**The root audits each lane's receipts, then records the lane and each finding it reports.** "Read
the diff or the artifact, not only the worker's summary." (pstack,
`skills/poteto-mode/playbooks/orchestrate.md`, l. 19) "The root audits the receipts in the
merge-ready report before the verdict." (pstack, `skills/poteto-mode/playbooks/multi-phase-plan.md`,
l. 65) The root reads the lane's output against each pass condition written up front. A live check
whose evidence does not show its pass condition is UNREACHED or failed, whatever the lane's summary
says. A lane row is `gate.py record lane <name> <result> --model <family> --at <sha> --out <file>`,
where the result is PASS, ISSUES, BLOCKED or NO-RUNTIME. `--out` is the file holding the lane's full
output, and `gate.py` refuses it missing, empty, or inside the branch's worktree or a lane checkout,
since `gate.py lane-remove` deletes the lane's checkout. It keeps the file's path and sha256, and a
file gone or changed since makes the verdict not clean. Then the root records each finding the
report names, as a finding row that names the lane with `--lane <name>`, and `gate.py` holds the
verdict not clean until each ISSUES lane has at least one such row written after it. A PASS, ISSUES
or BLOCKED row of any lane but a `review*` one names the full command it ran, verbatim, with
`--cmd`, and a rerun at a commit whose latest row for the lane is ISSUES or BLOCKED repeats that
`--cmd` exactly. A review lane takes no `--cmd`, since each of its blocking findings keeps its own.
A BLOCKED or NO-RUNTIME row says why with `--note`. *(kstack: upstream names the receipts audit but
no recorder, so these flags and refusals are kstack's. Each puts a check where the root's word
stood, per "If the fix is structural, only use the structural fix." (pstack,
`skills/principle-encode-lessons-in-structure/SKILL.md`, l. 11))*

**`gate.py` guards the states an honest root reaches, and the receipts audit catches a row the root
knows is false.** "A guard is a fix only when the state it handles is legitimate." (pstack,
`skills/principle-fix-root-causes/SKILL.md`, l. 3) So each refusal stops a mistake an honest root
makes, such as a lane row at the wrong commit or a finding left unsorted, and none tries to stop a
root that records a row it knows is false *(kstack: the operator's choice, after a review round's
probes found holes that only a root recording false rows reaches)*. That root is caught by the audit
autopilot-full puts before the verdict: "The verdict is not clean without the live lane, or before
you audit the merge-ready report's receipts, because no lane trusts a claim it has not checked."
(pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 14) Before `gate.py land`, the root
reads each lane's `--out` report and records each finding it names with a finding row naming the
lane, a finding an earlier round raised included, and checks that the round of every `fixed` row
reports that finding fixed. `gate.py` sees only that an ISSUES lane has a row naming it, not that
every finding in its prose has one. Four holes stay open by design, each a place where `gate.py`
takes the root's word, and the audit checks each. A whitespace-only commit made to rerun a BLOCKED
gates command is a new patch, whose gates runs start fresh. A PASS row recorded for a review lane
over its ISSUES row at the same commit supersedes it, so that report's findings drop out of the
check that each has a row. A round sized wording over a change to code, or a `fixed` row's
`--text` over sites that are code, ends clean with no lane rerunning them, so the audit checks the
round's size and each `--text` against the diff. A `GATE_NOISE_PATHS` or `GATE_SAME_BUILD` the
root set inline, rather than the project's, decides which changes a kept lane may skip, so the
audit checks that both match the project's stated config *(kstack: a live run of the gate ended
clean on each of the last two, on the root's word alone)*.

**The root verifies every finding before any of them blocks.** It reruns each finding's command,
keeps a finding when the output shows the failure and the failure breaks the intent, drops the
rest, and merges findings that share a root cause (pstack, `skills/interrogate/SKILL.md`, l. 23).
It sorts each kept finding into one of the three buckets in `references/judgment.md`. The root
owns the verdicts, never the change (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`,
l. 3). It sorts every round, and can, because it writes no fix (A fresh agent writes the fix,
below). *(kstack: no separate lead agent sorts, because the root has already read every report,
and lead agents cost tokens, per `references/evidence.md`, Run evidence behind the gate.)*

**No bug is held back to save a round.** *(kstack: the person who asked said to fix a bug rather
than defer it, per `references/evidence.md`, Run evidence behind the gate.)* A round whose kept
findings all go to follow-up is a clean verdict, and its follow-ups go in the Reply.

**A clean verdict** holds at the head that lands when all of these hold:

- The gates lane passed at that head: the last run there of every command run there exited 0.
- Every blocking finding, from this round or an earlier one, is closed by a `fixed` row at a patch
  where that round's lanes found its sites clean: a review lane there for a full round, the
  checker's PASS or ISSUES row for a minor one. A lane at that patch, or a later one, that found it
  still failing is a blocking row the root records for it there, which reopens it *(kstack: a
  review probe closed a finding on two ISSUES reviews that said it still failed)*. A wording round
  runs no such lane, so its `fixed`
  row closes only a finding whose sites are text and says so with `--text`, which `gate.py` takes
  as the root's word and refuses to go without there. A `fixed` row its round does not bear out
  leaves the finding open.
- A full round has its own live lane, PASS or NO-RUNTIME, at its patch. A minor or wording round
  rests on the last full round's live lane: that lane passed, or was NO-RUNTIME, with its live
  checks VERIFIED at its commit, or a live lane passed at the current patch, or a checker VERIFIED,
  at its commit, every live check that live lane left failed or UNREACHED. A live pass at a patch
  before the last full round never counts, since that round's live result is what the change must
  get past *(kstack: a review probe landed a redesign whose live lane failed, on a live pass from
  before it)*. A live lane recorded at the current patch is PASS or NO-RUNTIME.
- No lane at the current patch is BLOCKED or a gap. A lane of the full round that a sized round
  rests on that was BLOCKED or a gap did not run, and a gap and a BLOCKED lane are handled alike:
  it reruns at the new patch, or, for a lane other than a review lane, the checker reruns it and
  its row names it with `--covers <lane>`. The checker's VERIFIED rows for every live check the
  live lane left unverified cover a live lane that was BLOCKED or a gap. A review lane is never
  covered, since one checker is one model and a review's second opinion is another model (Staffing,
  above): `gate.py` refuses `--covers review*`, and a BLOCKED or gap review counts only once it
  reruns at the new patch.
- A minor round has its checker lane, PASS or ISSUES, at its patch.
- Two review lanes on different models read the change: PASS or ISSUES in the last full round, or
  reruns at the new patch of those that were BLOCKED or a gap. A BLOCKED review never read it.
- Every finding an ISSUES lane reports is sorted: the root records a finding row for each, naming
  the lane. `gate.py` checks that each ISSUES lane the verdict rests on has at least one finding row
  written after it that names it, so a blocking row a void kept never sorts the rerun's report, and
  the root's audit covers the rest *(kstack: a review probe gave a clean verdict on two ISSUES
  reviews with no finding rows; the root's sorting is above)*.
- A fresh agent wrote every fix.

So the checker's brief carries every open finding's site command and every live check that failed
or went UNREACHED. `gate.py status` checks the lane and finding parts of this from the ledger.
*(kstack: these replace a rule that a sized round rests only on a clean full round, which no
upstream line states, per Sizing a later round.)*

**A finding stays open until a later row closes it.** The root records a finding that blocks with
`gate.py record finding <id> blocks --lane <lane> --cmd <command> --premise <sentence>`: the lane
whose report holds it, the command that finds its sites (Otherwise, fix forward, below), and the one
sentence its fix will assume (A finding that comes back is a failed correction, below). `gate.py`
refuses a blocking row without any of them, and a follow-up or dropped row without its `--lane`. A
finding is open at a patch when its latest row at that patch blocks, or its latest row at any patch
does, and closed otherwise. So a blocking finding blocks every later patch, blocks again when a
reset or a revert brings back the patch it was recorded at, since that code still holds the defect,
and an older closing row at a patch never hides a newer blocking row recorded at another. The root
closes it at a later patch with `gate.py record finding <id> fixed --by <agent> --model <family>`,
adding `--text` in a wording round, once that round's lanes reran its site command and it came back
clean. That is the only way it closes. A blocking finding is a defect the root verified before it
blocked (The root verifies every finding, above), and a clean verdict needs it closed by a `fixed`
row, so `gate.py` refuses a follow-up or dropped row for a finding that was sorted blocking, and
reads such a row in an older ledger as nothing *(kstack: re-sorting a blocking finding turned a
review probe's verdict clean with no fix)*. A finding first sorted follow-up may still be sorted
blocking later. `gate.py` refuses `fixed` at a patch whose own row for the finding blocks *(kstack:
review probes landed an act-on finding unfixed, once after a new commit and two fresh passing
reviews, once by a reset to its patch after a later patch closed it, and once by a reset to a patch
whose older row closed it after a later patch recorded it act-on)*.
`gate.py` reads the old bucket names in a ledger or a brief as the new ones: act-on as blocks,
consider, queue and nit as follow-up, and dismissed as dropped.

**Otherwise, fix forward.** Every finding that blocks goes to one fresh fixer in one fix-forward,
once the round ends (A round, above). "Fix all issues raised by the code review in a single fresh
**implementer subagent**." (mattpocock-skills, `skills/engineering/implement-spec/SKILL.md`, l. 38)
For each behaviour finding, ask for a red test that covers every site with the same defect, or a
repro receipt where no test can show the defect. Before the fix is written, its brief lists the
sites: "Check for the pattern, not just the instance. Find every place with the same fault and fix
them all." (pstack, `skills/principle-fix-root-causes/SKILL.md`, l. 19) The next round's review
brief, or its checker's, carries each fixed defect, so that round checks the fix *(kstack: the
site command is how the next round knows the fix held, per this section)*.

The site list is a command and its output, for a code defect and a doc defect alike. The fix brief's
CONTEXT carries the output, and its VERIFY the command that lists the sites, such as a `git grep`, a
script, or a red test over every input shape. A count is true at the commit that lands it, with the
command that regenerates it (pstack, `skills/technical-writing/SKILL.md`, l. 96). The fixer reruns
the command after the fix and its REPORT gives the new output. The next round's gates lane reruns it
at the new head and records the count.

- **A behaviour that depends on order**, such as hook events, retries or concurrent writers, has a
  site for every order the inputs can arrive in. When those orders can be listed, the brief names
  each order with the test that covers it *(kstack: fixes introduced bugs on orders their authors
  had not traced, per `references/evidence.md`, Run evidence behind the gate)*. When they cannot
  all be listed, as with concurrent writers or reconnects, the brief states the property in one
  sentence and the site command checks it over every order within a stated bound. "Formal
  verification checks every case in a stated scope: every order of steps in a model, every input
  up to a bound, or every input." (pstack, `skills/create-formal-verification-skill/SKILL.md`,
  l. 9) The check is a model checker over a small model, or generated inputs against the real
  code: "If no verifier runs on this language, say so, and test the real code with generated
  inputs, not a hand model of the function." (pstack,
  `skills/create-formal-verification-skill/SKILL.md`, l. 19) Show it failing on a broken variant
  first, since "A check that you have never seen fail proves nothing." (pstack,
  `skills/create-formal-verification-skill/SKILL.md`, l. 24) *(kstack: in a build session, probes
  of named orders grew round after round and each round found the next order, and the first clean
  review rested on generated orders.)*
- **A property of how data flows gets a structural guard, not a source scan.** A source scan fits
  only a fixed syntactic pattern. Otherwise the fix is a constraint, a single helper the writers
  read, or a runtime refusal, in the order `references/design.md` gives under Screen for red flags
  *(kstack: source scans grew round after round to catch the next mutant, and a structural fix
  landed in one round, per `references/evidence.md`, Run evidence behind the gate)*. "If the fix
  is structural, only use the structural fix." (pstack,
  `skills/principle-encode-lessons-in-structure/SKILL.md`, l. 11)
- **A false or unsupported claim in a doc or a comment** has a site at every place the claim
  reaches, and the command finds those places *(kstack: the red-test rule, carried over to docs,
  after failed doc fixes missed places, per `references/evidence.md`, Run evidence behind the
  gate)*. At each site the fix deletes the sentence, by default. unslop: "If you can't restate it
  as a concrete instruction, fact, or number, cut it." (pstack, `skills/unslop/SKILL.md`, l. 56),
  and of a vague attribution, "Name the source or delete." (pstack, `skills/unslop/SKILL.md`,
  l. 18) Rewrite it only when the reader needs it and it can carry its source or the command that
  regenerates it (pstack, `skills/technical-writing/SKILL.md`, l. 96). A rewrite is new prose to
  review: "Each fix adds new code to review" (mattpocock-skills,
  `docs/engineering/code-review.md`, l. 77). *(kstack: rewording kept doc findings open for rounds
  after the code was proven, and deleting the claim closed them, per `references/evidence.md`, Run
  evidence behind the gate.)*

**A fresh agent writes the fix.** Give new work to a fresh subagent with consolidated scope: the
original brief, every later directive, and the prior agent's report and branch. That holds for a fix
round, a follow-up, a retry and the next queue item (pstack, `skills/poteto-mode/SKILL.md`, l. 102).
The root never writes a fix, `gate.py record finding <id> fixed` refuses `--by root`, and a round
whose fix the root wrote is a gap *(kstack: a root-written fix leaves the round with no writer apart
from its judge, and roots did write fixes, per `references/evidence.md`, Run evidence behind the
gate.)* The fix goes through its playbook again (SKILL.md, Playbooks), test first. The fixer's
REPORT gives its check-4 verdict, VERIFIED, NOT VERIFIED or INCONCLUSIVE (`references/verify.md`),
and a suspicion about its own diff that it did not drive makes the report INCONCLUSIVE.
"Inconclusive is not a pass." (pstack, `skills/figure-it-out/SKILL.md`, l. 42) So an INCONCLUSIVE
head is not code-ready, and its suspicion goes back to the fixer or to a probe before the next round
starts *(kstack: in a build session, a fixer's undriven suspicions became the next round's critical
findings)*. The verdict names the agent and the model that wrote each fix. The new head
gets a round of the size the fix calls for (Sizing a later round).

**A finding that comes back is a failed correction.** Each blocking finding gets an ID in the
round's record, `R<round>-<X><n>`, and the Reply carries it. When the root sorts the finding, it
also writes the premise its fix will assume, in one sentence, in its blocking row's `--premise`, in
the fix brief's CONTEXT and in the Reply beside the ID (`references/when-a-fix-fails.md`). When a
later round reports the same defect, or a defect that a fix introduced, it is a failed correction,
and the root records it as blocking again at that patch, `--lane` naming the lane that reported it,
and the premise that fix assumed, word for word. That row reopens the finding, whatever its earlier
`fixed` row says.
`gate.py` counts failed fixes per premise, by the premise's text alone: the same ID under a reworded
premise counts under the new wording. Each blocking row counts against the premise it names,
whatever its ID, and each later patch at which a blocking row names a premise is one failed fix of
it: the same ID blocking again under that premise, or a new ID naming it. An ID the root
re-diagnosed counts under the premise its new row names *(kstack: counting an ID under its first
premise hid a third patch naming one premise from STOP in a review probe)*. Premises match without
case, repeated spaces or a final period. A finding carried open from an earlier patch with no new
blocking row is not counted *(kstack: the count measures fixes that failed, not rounds a fix was
pending)*. `gate.py status` prints each premise's count with its IDs, and STOP at two while one of
them is still open. A blocking row that names no premise, as in an older ledger, counts under its
ID. So the match is the root's judgment: a new blocking defect that holds only because a premise is
false names that premise's sentence again, word for word, whatever ID it gets *(kstack: in a long
build session many finding IDs broke one premise, and a count by ID printed STOP once, late)*.
`references/when-a-fix-fails.md` says what happens next, based on that count.

## The patch-id rule

Record the verdict's head SHA, base SHA and `git patch-id` of the base-to-head diff. "A verdict
covers a patch, and a chain rebase moves every PR above it to a new SHA without failing any check."
(pstack, `skills/poteto-mode/playbooks/shipping.md`, l. 7) Before a fix round's lanes start and
before merging, compare the recorded patch-id with the current one,
`git diff <base>..<head> | git patch-id --verbatim`. *(kstack: pstack names plain `git patch-id`,
which ignores whitespace, so a re-indent that changed what Python runs kept the verdict of code no
lane read, in review probes. `--verbatim` keeps whitespace and still ignores line numbers, so the
rule still does what shipping l. 7 asks: a rebase that only moves the patch keeps its verdict, and
a patch that changed in any byte is a new patch.)*

- **They match.** Keep the code verdict, and re-run the checks at the current head, since green CI
  covers one head (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 5).
- **They differ only in tests, docs, or lint config.** A lane's result stands if what it ran builds
  the same at both SHAs apart from noise. "Noise is a difference that also shows up between two
  builds of the verdict SHA, or an embedded commit SHA. Report each kind of noise with its files, so
  a reader can check the call." The change itself still gets fresh checks and a review. A lane with
  no build output, such as a dev server, cannot show this, so rerun it (pstack,
  `skills/poteto-mode/playbooks/shipping.md`, l. 7). *(kstack, the translation: a lane with build
  output is a live drive of a build, kept in a full round with `gate.py record lane live
  --kept-from <sha> ...`, whose `--note` names each kind of noise with its files. `gate.py` refuses
  the keep unless every path that changed between the two commits matches the project's
  `GATE_NOISE_PATHS` pathspecs, empty by default, or the project's `GATE_SAME_BUILD` command exits
  0 on the two commits. So the script, not the root's note, shows that the two build the same, and
  a refused keep reruns the lane with `--at`. `--kept-from` names the commit the lane checked, and
  the latest row of that lane at that commit's patch must have checked it; `gate.py` copies that
  row's result and model and notes the commit. A NO-RUNTIME row built nothing, so it is recorded
  again with `--at`. A drive against a dev server and every review lane, which
  reads source and builds nothing, rerun, and so does a minor round's checker, the "single verifier
  at the new head" (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 14). The fresh
  review of the change is the one its round size sets. Docs here are text no program or agent acts
  on, as Sizing a later round says.)*
- **They differ in anything else.** Re-verify anything else that drifted (pstack,
  `skills/poteto-mode/playbooks/shipping.md`, l. 7).

## Merge preparation

These steps are autopilot-full step 5, with local merges in place of PRs *(kstack, the translation:
kstack merges a local branch into local main, where pstack merges a PR on a forge)*.

1. **Rebase onto current main once the round's lanes have started**, then re-run the project's
   checks on the new head (lane 1) (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`,
   l. 17).
2. **Re-check the verdict** with the patch-id rule. A new patch voids the verdict, except the lane
   results that rule keeps.
3. **Ask whether main's changes can affect the patch**, right before the merge, "because rebasing
   for every trunk move never ends" (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`,
   l. 19).
   - Rebase again and re-run the checks when the code that would land was never tested: a conflict
     in `git merge-tree` of the head against local main, a file both sides changed since the merge
     base, or a change to the files that decide which checks run (pstack,
     `skills/poteto-mode/playbooks/autopilot-full.md`, l. 19). Whenever main has moved since the
     merge base, `gate.py land` first refuses unless the gates row at the head recorded main's tip
     equal to the head's merge base, which is step 1's rebase. Then it runs those three checks, and
     refuses, naming the check, when one fails. *(kstack, the translation: pstack's CI config paths
     are the pathspecs a project lists in `GATE_CHECK_PATHS`, empty by default.)*
   - When main changed a caller of the patch, or something the patch depends on, such as code it
     calls or a dependency version, run the patch's checks on the merge result and merge on a pass
     (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 19). *(kstack, the translation:
     the merge result is the head rebased onto main, so the root rebases and reruns the gates lane
     there. `gate.py land` does not check this, because whether main's change reaches the patch
     takes reading the code.)*
   - Otherwise merge, so a later move of main forces no rebase (pstack,
     `skills/poteto-mode/playbooks/autopilot-full.md`, l. 19).
   - "If trunk would force a third rebase past merge prep, hold and report to the root, which
     sequences the colliding work." (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`,
     l. 19) *(kstack, the translation: the root is the owner here, so it stops the branch at
     merge-ready and reports to the operator which branch collides with which.)*
4. **Merge as one commit** on main. The commit message is the root's message, which carries the
   Reply below, followed by the verdict block that `gate.py land` appends: a line that reads
   `GATE VERDICT:`, then the round's size, each lane and each fix. A merge without that verdict, or
   with a verdict that is not clean, does not land, since green CI alone never authorizes a merge
   (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 17). `gate.py land <message-file>`
   makes this commit on main's latest commit, and refuses unless the ledger holds a clean verdict
   for the current patch that changes something against main. The commit holds the head's tree, or
   the merged tree when main had moved, and then its verdict line names the move. Merging past a
   moved main needs git 2.38 or later for `git merge-tree --write-tree`, and main moving during
   the landing refuses it. Once main holds the commit, `land` deletes the ledger and prints the
   cleanup commands: `gate.py lane-remove <name>` for each lane checkout still out, such as one an
   interrupted gates run left, then the worktree removal, both of which the root runs, and last `git
   branch -D`, which the operator runs to delete the branch. kstack's git-guard hook
   (`hooks/block-dangerous-git.py`) refuses a forced branch delete to agents, as `-D`, `-df` or
   `--delete --force` and behind a wrapper or `git -C <dir>`, after Matt's
   git-guardrails, where Claude "does not have authority to access these commands"
   (mattpocock-skills, `skills/misc/git-guardrails-claude-code/SKILL.md`, l. 18). *(kstack, the
   translation: pstack squash-merges a PR, and `land` writes the one commit itself.)*

**Who may merge** is SKILL.md's "## Autonomy" rule. The grant to merge into local main is standing,
so a clean verdict merges. A change the operator named, or asked to see first, ends at merge-ready,
with a clean verdict recorded on its branch.

**Reply:** each round with its size and why. Each lane with its model, the commit it checked and its
result (`PASS`, `ISSUES`, `BLOCKED` or gap). Each fix with the agent and the model that wrote it.
The blocking findings with their IDs. Each flake that passed its fresh run (lane 1). The
follow-ups. The recorded patch-id. The merge commit, or the branch at merge-ready. That is each
verdict and who produced it (pstack, `skills/poteto-mode/playbooks/shipping.md`, l. 12), and the
parked follow-ups (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 25).
