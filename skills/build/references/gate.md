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

Each self-contained change is its own branch, in its own linked worktree, with one owner from
build to merge, and is gated and merged alone (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 3). The owner is the only writer of its
branch (pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 9), which is why one fresh agent
writes each round's fixes (A fresh agent writes the fix, below). `gate.py record` refuses the main
worktree. Run branches in parallel off main and never stack them, so each lands on its own (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 13). The root sequences colliding work
(pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 19), so a change that touches a file
another unmerged branch touches waits for that branch to merge, then branches off the new main.
*(kstack, the translation: pstack's unit is a PR, and here it is a local branch.)*

A round's findings against the change go back in one fix-forward on the change's own branch. A
defect outside the change is not fixed on this branch. It goes to follow-up
(`references/judgment.md`), since only the fixes that block the work are kept and the rest are
parked as follow-ups (pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 20). A defect
outside the change that blocks it is fixed first, as a change of its own (pstack,
`skills/poteto-mode/playbooks/autonomous-run.md`, l. 9).

## A round

A round starts at the commit the author calls code-ready, and again at each later commit that
changes the patch, sized as Sizing a later round says. Each lane names the exact commit it
checked. The round ends when every lane has returned, and no commit moves the branch's head before
then *(kstack: fix commits that moved the head stopped a round's gates lanes mid-suite, per
`references/evidence.md`, Run evidence behind the gate)*.

**Each lane works in its own detached checkout of the exact commit it checks**, never in the
branch's worktree, so the files under a running lane are that commit's alone.
"When workers verify or measure commits, each brief names the exact SHAs." and "Give each worker
its own writable output when it writes." (pstack, `skills/swarm/SKILL.md`, l. 23) pstack's live
lane checks out the head SHA on its own machine (pstack,
`skills/poteto-mode/playbooks/multi-phase-plan.md`, ll. 71, 73). Make the checkout with
`git worktree add --detach <path> <sha>`, and remove it by that exact path,
`git worktree remove <path>`, once the lane returns. The root keeps recording from the branch's
worktree, since `gate.py record` refuses a detached HEAD. *(kstack, the translation: a linked
worktree is the lane's own machine.)*

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

1. **Gates: the root re-runs every check at the commit.** The root runs the commands itself, in the
   background, and records each command's count. No agent is spawned for it: "A deterministic
   lever beats fan-out. If the tool can process every unit in one pass, run it yourself." (pstack,
   `skills/principle-build-the-lever/SKILL.md`, l. 16) The commands are the risk list from check 1
   (understand), the project's pre-merge checks (tests, lint, type checks), and every site command
   from the previous round's fix briefs (Otherwise, fix forward). When a researcher wrote a note
   for the change, the lane also reads `git status` and the branch diff for any file the
   researcher was not given, since it writes only the one note path its brief names
   (`agents/researcher.md`, Write only the note), and such a file fails the lane *(kstack: the
   operator's proposal, step 1, as no check yet shows Claude Code can limit an agent's Write tool
   to one path)*. The lane runs at every new head,
   because "every new head needs its own green CI" (pstack,
   `skills/poteto-mode/playbooks/autopilot-full.md`, l. 5). A check that cannot run, because its
   tool is missing or its access is refused, makes the lane BLOCKED, never PASS, and its row names
   what was missing (pstack, `automations/benny/skills/reproduce-and-fix-issues/SKILL.md`, l. 183).
   **A failing check that might be a flake is classified before any rerun.** "Flake or
   infrastructure earns one fresh build, never a job retry. One retry only. An identical second
   failure means it was never flake, so reclassify and read the child logs instead of retrying
   blind. A failure in code the diff never touches means a stale base, so check with
   `git merge-base --is-ancestor` before assuming flake. Report a stale base as needing a rebase
   instead of burning retries. Only a failure in the diff's own code gets a commit." (pstack,
   `skills/poteto-mode/playbooks/babysit.md`, l. 19) *(kstack, the translation: a fresh build is one
   fresh run of the failing command at the same commit, the child logs are that command's full
   output, and the stale-base check is `git merge-base --is-ancestor main <commit>`.)* A flake that
   passes on its one fresh run is still named in the Reply, by test and command *(kstack: rule 15
   in `references/rules.md` makes a flaky test a defect, so it is recorded rather than dropped)*.
2. **Live: prove the load-bearing behaviour on the real surface the change touches**, through the
   project's verify skill (`verify-<app>`). It drives the live checks the root wrote up front,
   before the code, each one user flow with a scenario and a pass condition
   (`references/understand.md`, Write the live checks before the code). The verdict is not clean
   without the live lane (pstack,
   `skills/poteto-mode/playbooks/autopilot-full.md`, l. 14). The drive covers the load-bearing
   behaviour, not every claim. Pick the smallest local surface that can disprove a claim
   (cursor-team-kit, `skills/verify-this/SKILL.md`, l. 22), so a claim that a unit, a script or a
   fixture can disprove is a test in the gates lane. A round builds one test copy of the app per
   version under test, not one per claim *(kstack: a copy per claim adds builds and agents but no
   evidence)*. A change with no runtime surface records that fact instead
   (`gate.py record lane live NO-RUNTIME`) *(kstack: pstack's lanes all drive a surface, so it has
   no record for a change without one)*.
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
   operator's proposal, step 6)*. The brief's scope is the branch diff from its merge base with
   main, and its intent is the change's stated intent (pstack, `skills/interrogate/SKILL.md`,
   l. 13). It has the fields in SKILL.md, The brief, and its CONTEXT also carries every capability
   the change drops, with who approves each loss, the person who asked or this verdict under the
   operator's grant, per check 2 in `references/simplify.md` *(kstack, as that rule is)*.
   Adversaries find different failures, so the verdict keeps every verified finding, not one
   lane's list (pstack, `skills/interrogate/SKILL.md`, l. 25). *(kstack: Claude Code runs only
   Claude models, so the two lanes use two Claude models and name which ran. pstack puts each
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
detached checkout of the exact commit, and its REPORT names that commit.

## Sizing a later round

"A full swarm runs once, at the code-ready head. Another full swarm runs only for new behavior, a
redesign, or a large new diff. A rebase, a merge-conflict resolution, or a minor fix gets a single
verifier at the new head, and a wording-only change gets none." (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 14) So the first round always runs in full,
one-line fixes included, and the fix decides the size of each later round:

- **Full**, for new behaviour, a redesign or a large new diff: all four lanes again.
- **Minor**, for a minor fix, a rebase or a conflict resolution: the gates lane and one checker
  lane, named `checker`, at the new patch. The checker is one fresh agent that did not write the
  code and runs the change the way a user would (pstack,
  `skills/poteto-mode/playbooks/shipping.md`, l. 5).
- **Wording**, for a wording-only change: the gates lane alone.

Upstream gives no line count for "minor" or "large", so the root makes the call by the kind of
change. Wording-only means text no program or agent acts on, such as a README, a product or design
record, or a comment. In a skill set, a `SKILL.md`, a reference or an agent's definition is code,
since an agent runs it *(kstack: the meaning of docs the patch-id rule below already uses)*. The
root records the size and why with `gate.py record round <full|minor|wording> --note <why>`, and a
patch with no round row needs a full round. A full round never repeats to convergence: "Each fix
adds new code to review", and "There is no convergence guarantee." (mattpocock-skills,
`docs/engineering/code-review.md`, l. 77)

`gate.py status` rests a minor or wording round on the lanes of the last full round before it,
which must be clean, and the verdict block in the merge commit lists those lanes at the commits
they checked. A sized round with no earlier full round is not clean.

**A fix round stays on its base.** Rebase again only "on a `git merge-tree` conflict with trunk, on
a CI failure that comes from a change on trunk, or when a known concurrent change to the same files
lands" (pstack, `skills/poteto-mode/playbooks/multi-phase-plan.md`, l. 61), because each rebase
restarts the checks (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 10). *(kstack,
the translation: a CI failure is a gates-lane failure that the stale-base check in lane 1 traces
to main, and a known concurrent change is a commit on main that touches a file the branch
changes.)*

## Staffing

SKILL.md's "## Subagents" holds the general rules, such as which model writes a fix and the effort
every subagent runs at. The gate adds which model runs each lane.

- **The two review lanes run one on Opus and one on Sonnet, with the same brief**, as lane 3 says.
  "A second opinion is the same prompt against a different model." (pstack,
  `skills/poteto-mode/SKILL.md`, l. 100)
- **The live lane and the checker run on Sonnet.** Verification stays on the `swarm workers`
  model (pstack, `skills/poteto-mode/SKILL.md`, l. 98), whose default is `grok-4.7-xhigh-fast`
  (pstack, `skills/swarm/SKILL.md`, l. 22). *(kstack, the translation: Claude Code runs only Claude
  models, so the default worker model is Sonnet.)*
- **The gates lane is no agent**, since the root runs its commands (lane 1), so its row records
  `--model root`, which no other row takes.

## The verdict

Each lane returns `PASS`, `ISSUES` or `BLOCKED` with evidence. A lane that can prove a defect
reports `ISSUES` and lists every issue it can prove, not only the first (pstack,
`skills/swarm/SKILL.md`, l. 31). A lane agent that doesn't report the commit it checked is re-run
once, and after that it is a gap, recorded without `--at` since it named no commit. A gap does
not count as a pass (pstack, `skills/swarm/SKILL.md`, l. 37).

**The ledger records the verdict.** The root writes each lane result, round size, finding and fix
to the branch's ledger with `scripts/gate.py record`, run as
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

**A clean verdict** means that, at the head that lands, no lane is BLOCKED or a gap, the gates lane
passed at that head, the round has the lanes its size needs (a full round: the live lane passed or
the change has no runtime surface, and two review lanes on different models read the round's diff;
a minor round: the last full round's lanes and one checker; a wording round: the last full round's
lanes), a fresh agent wrote every fix in the round, and no finding that blocks is open, from this
round or an earlier one. `gate.py status` checks the lane and finding parts of this from the
ledger.

**A finding stays open until a later row closes it.** The root records a finding that blocks with
`--cmd`, the command that finds its sites (Otherwise, fix forward, below), and `gate.py` refuses a
blocking row without it. A finding is open at a patch when its latest row at that patch blocks, or
its latest row at any patch does, and closed otherwise. So a blocking finding blocks every later
patch, blocks again when a reset or a revert brings back the patch it was recorded at, since that
code still holds the defect, and an older closing row at a patch never hides a newer blocking row
recorded at another. The root closes it at a later patch with `fixed` once that round's lanes
reran its site command and it came back clean, or sorts it again as follow-up or dropped.
`gate.py` refuses `fixed` at a patch whose own row for the finding blocks *(kstack: review probes
landed an act-on finding unfixed, once after a new commit and two fresh passing reviews, once by a
reset to its patch after a later patch closed it, and once by a reset to a patch whose older row
closed it after a later patch recorded it act-on)*. `gate.py` reads the old bucket names in a
ledger or a brief as the new ones: act-on as blocks, consider, queue and nit as follow-up, and
dismissed as dropped.

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
  site for every order the inputs can arrive in. The brief names each order with the test that
  covers it *(kstack: fixes introduced bugs on orders their authors had not traced,
  per `references/evidence.md`, Run evidence behind the gate)*.
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
The root never writes a fix, `gate.py` refuses `root` as a fix's agent, and a round whose fix the
root wrote is a gap *(kstack: a root-written fix leaves the round with no writer apart from its
judge, and roots did write fixes, per `references/evidence.md`, Run evidence behind the gate.)* The
fix goes through its playbook again (SKILL.md, Playbooks), test first. The verdict names the agent
and the model that wrote each fix. The new head gets a round of the size the fix calls for
(Sizing a later round).

**A finding that comes back is a failed correction.** Each blocking finding gets an ID in the
round's record, `R<round>-<n>`, and the Reply carries it. When a later round reports the same
defect, or a defect that a fix introduced, it is a failed correction against that ID, and the root
records it as blocking again at that patch. `gate.py` counts each later patch at which any blocking
row was recorded for the finding, even when a later row at that patch sorts it again, and a finding
carried open from an earlier patch without one is not counted *(kstack: the count measures fixes
that failed, not rounds a fix was pending)*. `gate.py status` prints STOP at a count of two for
every finding still open at the current patch, re-recorded there or carried.
`references/when-a-fix-fails.md` says what happens next, based on that count.

## The patch-id rule

Record the verdict's head SHA, base SHA and stable `git patch-id` of the base-to-head diff. "A
verdict covers a patch, and a chain rebase moves every PR above it to a new SHA without failing any
check." (pstack, `skills/poteto-mode/playbooks/shipping.md`, l. 7) Before a fix round's lanes start
and before merging, compare the recorded patch-id with the current one,
`git diff <base>..<head> | git patch-id --stable`.

- **They match.** Keep the code verdict, and re-run the checks at the current head, since green CI
  covers one head (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 5).
- **They differ only in tests, docs, or lint config.** A lane's result stands if what it ran builds
  the same at both SHAs apart from noise. "Noise is a difference that also shows up between two
  builds of the verdict SHA, or an embedded commit SHA. Report each kind of noise with its files, so
  a reader can check the call." The change itself still gets fresh checks and a review. A lane with
  no build output, such as a dev server, cannot show this, so rerun it (pstack,
  `skills/poteto-mode/playbooks/shipping.md`, l. 7). *(kstack, the translation: a lane with build
  output is a live drive of a build, kept by the noise test with `gate.py record lane live
  --kept-from <sha> --note <the noise found>` in a full round. `--kept-from` names the commit the
  lane checked, and the latest row of that lane at that commit's patch must have checked it;
  `gate.py` copies that row's result and model and notes the commit. A NO-RUNTIME row built nothing,
  so it is recorded again with `--at`. A drive against a dev server and every review lane, which
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
   the landing refuses it. Once main holds the commit, `land` deletes the ledger and prints two
   commands: the root runs the first, which removes the worktree, and the operator runs the
   second, `git branch -D`, which deletes the branch. kstack's git-guard hook
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
