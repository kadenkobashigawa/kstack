# The gate

Load this at the last step of the playbook the change routed to (SKILL.md, Playbooks), for every
change that will merge. The gate takes a change from "verified by its author" to "verified by
agents that did not write it". shipping's rule: "Safe means a verdict from an agent that did not
write the code. CI green is not a verdict, and an approving bot review is not a verdict."
(pstack, `skills/poteto-mode/playbooks/shipping.md`, l. 7)

The gate is ported from pstack (Lauren Tan, MIT, `upstream/pstack/`): autopilot-full steps 2 to 5,
shipping's patch-id rule, and swarm. *(kstack: ...)* marks a departure, and *(kstack, the
translation: ...)* marks where a pstack PR becomes a local branch or commit (CONTRIBUTING.md,
Citations). Background is in `references/evidence.md`.

## The unit of work

Each self-contained change is its own branch, in its own linked worktree, with one owner from
build to merge, and is gated and merged alone (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 3). `gate.py record` refuses the main
worktree. Run branches in parallel and never stack them. Many run at once when each has one
writer and disjoint files, and a rebase absorbs the drift between them. A self-contained branch
starts from main, and sequenced work merges before the next branch starts. Only overlapping work
serializes (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 7). A change that touches a file another
unmerged branch touches waits for that branch to merge, then branches off the new main. *(kstack,
the translation: pstack's unit is a PR, and here it is a local branch.)*

A round's findings against the change go back in one fix-forward on the change's own branch, which
keeps its merge base (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 6). A defect
outside the change is not fixed on this branch. It goes to the queue bucket
(`references/judgment.md`), since mid-run discoveries fix only what blocks the frontier (pstack,
`skills/poteto-mode/playbooks/orchestrate.md`, l. 109). A defect outside the change that blocks it
is fixed first, as a change of its own (pstack, `skills/poteto-mode/playbooks/autonomous-run.md`,
l. 9).

## A round

A round starts at the commit the author calls code-ready, and again at every later commit that
changes the patch. At that exact commit four lanes run: the root runs the gates lane itself, and
fresh agents that did not write the code run the other three. Each lane names the exact commit it
checked. The round ends when every lane has returned (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 8). No commit moves the branch's head before
then *(kstack: fix commits that moved the head stopped a round's gates lanes mid-suite, per
`references/evidence.md`, Run evidence behind the gate)*.

**Each lane works in its own detached checkout of the exact commit it checks**, never in the
branch's worktree, so a fix commit or a rebase there cannot change the files under a running lane.
"When workers verify or measure commits, each brief names the exact SHAs." and "Give each worker
its own writable output when it writes." (pstack, `skills/swarm/SKILL.md`, l. 26) pstack's live
lane checks out the head SHA on its own machine (pstack,
`skills/poteto-mode/playbooks/multi-phase-plan.md`, ll. 71, 73). Make the checkout with
`git worktree add --detach <path> <sha>`, and remove it by that exact path,
`git worktree remove <path>`, once the lane returns. The root keeps recording from the branch's
worktree, since `gate.py record` refuses a detached HEAD. *(kstack, the translation: a linked
worktree is the lane's own machine.)*

Before a commit starts a round, its author runs the checks that the project's own rules name for the
touched paths, on the commit itself (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`,
l. 6). *(kstack, the translation: pstack's "AGENTS.md files and rules" are a project's `CLAUDE.md`
or `AGENTS.md` files and its rules, such as `.claude/rules/` or a contributing guide that names
checks. kstack's `CONTRIBUTING.md` names `claude plugin validate .` for changes under `skills/`. A
round starts at a commit, not a push.)*

1. **Gates: the root re-runs every check at the commit.** The root runs the commands itself, in the
   background, and records each command's count. No agent is spawned for it, because "A verifier
   agent whose entire product would be rerunning one command is ceremony, not verification."
   (pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 87) and "A deterministic lever beats
   fan-out." (pstack, `skills/principle-build-the-lever/SKILL.md`, l. 16) The commands are the risk
   list from check 1 (understand), the project's pre-merge checks (tests, lint, type checks), and
   every site command from the previous round's fix briefs (Otherwise, fix forward). The lane
   checks the commit as committed, because "A hook pass is not proof." (pstack,
   `skills/poteto-mode/playbooks/autopilot-full.md`, l. 6) A check that cannot run, because its tool
   is missing or its access is refused, makes the lane BLOCKED, never PASS, and its row names what
   was missing (pstack, `automations/benny/skills/reproduce-and-fix-issues/SKILL.md`, l. 183).
   **A failing check that might be a flake is classified before any rerun.** "Flake or
   infrastructure earns one fresh build, never a job retry. One retry only. An identical second
   failure means it was never flake, so reclassify and read the child logs instead of retrying
   blind. A failure in code the diff never touches means a stale base, so check with
   `git merge-base --is-ancestor` before assuming flake. Report a stale base as needing a rebase
   instead of burning retries. Only a failure in the diff's own code gets a commit." (pstack,
   `skills/poteto-mode/playbooks/babysit.md`, l. 21) *(kstack, the translation: a fresh build is one
   fresh run of the failing command at the same commit, the child logs are that command's full
   output, and the stale-base check is `git merge-base --is-ancestor main <commit>`.)* A flake that
   passes on its one fresh run is still named in the Reply, by test and command *(kstack: rule 15
   in `references/rules.md` makes a flaky test a defect, so it is recorded rather than dropped)*.
2. **Live: prove the load-bearing behaviour on the real surface the change touches** (pstack,
   `skills/poteto-mode/playbooks/autopilot-full.md`, l. 8), through the project's verify skill
   (`verify-<app>`). The live lane is the floor, and a verdict without it is not clean (pstack,
   `skills/poteto-mode/playbooks/autopilot-full.md`, l. 8). The drive covers the load-bearing
   behaviour, not every claim. Pick the smallest local surface that can disprove a claim
   (cursor-team-kit, `skills/verify-this/SKILL.md`, l. 22), so a claim that a unit, a script or a
   fixture can disprove is a test in the gates lane. A round builds one test copy of the app per
   version under test, not one per claim *(kstack: a copy per claim adds builds and agents but no
   evidence)*. A change with no runtime surface records that fact instead
   (`gate.py record lane live NO-RUNTIME`) *(kstack: pstack's lanes all drive a surface, so it has
   no record for a change without one)*.
3. **Review: two or more lanes audit the diff, distrusting the author's account of it.** Each lane
   gets the full brief and one main focus, such as consumer parity with trunk, lifetimes and races,
   or data and config safety (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 8). Each
   lane holds the diff to `references/rules.md`, looks hardest where its lens in
   `references/lenses.md` says (structure or correctness), reports by rule number, and rates each
   finding `critical`, `warning` or `nit` (pstack,
   `skills/interrogate/references/reviewer-prompt.md`, ll. 35–38). The full brief (SKILL.md, The
   brief) carries the change's stated intent and the rules in CONTEXT, and the run's never-list,
   which says what the run may not read or touch, in FORBIDDEN. Its CONTEXT also carries every
   capability the change drops, with who approves each loss:
   the person who asked, or this verdict under the operator's grant, per check 2 in
   `references/simplify.md` *(kstack, as that rule is)*. pstack draws its adversarial signal from
   different model families (pstack, `skills/interrogate/SKILL.md`, ll. 9, 38–41). *(kstack: Claude
   Code runs only Claude models, so the lanes use different Claude models, such as Opus and Sonnet,
   and name which ran. That diversity is weaker than pstack's.)*
4. **Regression: run the same load-bearing scenario on current trunk**, whenever the live lane ran.
   If trunk does not have the feature, record that, and gate the behaviour the diff adds plus the
   end state the user waits for. Do not pretend trunk can produce it (pstack,
   `skills/poteto-mode/playbooks/autopilot-full.md`, l. 8).

**Every lane and fixer brief has the fields in SKILL.md, The brief.** A lane's SCOPE is its
detached checkout of the exact commit, and its REPORT names that commit.

## Staffing

SKILL.md's "## Subagents" holds the general rules, such as which model writes a fix. The gate
adds which model runs each lane.

- **Two review lanes on two models, every round**, one Opus and one Sonnet, as lane 3 says. The
  adversarial signal comes from model diversity, not assigned personas (pstack,
  `skills/interrogate/SKILL.md`, l. 9).
- **The correctness lane runs on Opus, the structure lane on Sonnet.** swarm sends its workers to
  the fast model (pstack, `skills/swarm/SKILL.md`, l. 25), and that is Sonnet here *(kstack: Claude
  Code runs only Claude models)*. Correctness takes Opus because a miss there ships a wrong result
  *(kstack: reasoning, not measurement)*.
- **The live and regression lanes are mechanical work, so they run on Sonnet** (SKILL.md,
  Subagents). The gates lane is no agent, since the root runs its commands (lane 1), so its row
  records `--model root`.

## The verdict

Each lane returns `PASS`, `ISSUES` or `BLOCKED` with evidence. A lane that can prove a defect
reports `ISSUES` and lists every issue it can prove, not only the first (pstack,
`skills/swarm/SKILL.md`, l. 34). A lane agent that doesn't report the commit it checked is re-run
once, and after that it is a gap. A gap does not count as a pass (pstack, `skills/swarm/SKILL.md`,
l. 40).

**The ledger records the verdict.** The root writes each lane result, finding and fix to the
branch's ledger with `scripts/gate.py record`, run as
`$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/scripts/gate.py`. `gate.py status` says whether the verdict
is clean. The lanes are named `gates`, `live`, `regression` and `review-<focus>`. Each row
carries the patch-id, so a new patch starts a new verdict (pstack,
`skills/poteto-mode/playbooks/orchestrate.md`, l. 89). `record` runs only in the branch's own
linked worktree, so the ledger goes when the worktree does.

**The root decides which findings are proven before any of them blocks**, after interrogate's step 5
and lead-judgment. The root is the session running the gate. It reads the diff and every lane's
findings itself, and sorts each finding into one of the five buckets in `references/judgment.md`,
which holds the buckets and the rules for sorting. The root owns the verdicts, never the
change, and keeps only verification, countersigns and audits (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 3). It sorts every round, and can, because it
writes no fix (A fresh agent writes the fix, below). *(kstack: interrogate's lead is a separate
agent, but the root has already read every report, and separate lead agents cost tokens, per
`references/evidence.md`, Run evidence behind the gate.)*

**No bug is held back to save a round.** *(kstack: the person who asked said
to fix a bug rather than defer it, per `references/evidence.md`, Run evidence behind the gate.)* A
round whose findings are all nits is a clean verdict, and its nits go in the Reply.

**A clean verdict** means that, at the head that lands, no lane is BLOCKED or a gap, the gates lane
passed at that head, the live lane passed or the change has no runtime surface, the regression lane
passed whenever the live lane did, two review lanes on different models read the round's diff, a
fresh agent wrote every fix in the round, and the root left nothing in act on. Nits in the Reply do
not count against it. `gate.py status` checks the lane and finding parts of this from the ledger.

**Otherwise, fix forward.** "When the lanes return, send every proven finding against the PR to
the owner in one fix-forward." (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 8)
So the fix-forward starts only when every lane of the round has returned. For each behaviour
finding, ask for a red test that covers every site with the same defect, or a repro receipt where no
test can show the defect. Add that defect to the next round's review brief (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 8). Before the fix is written, its brief lists
the sites, since a fix covers the pattern, not just the instance (pstack,
`skills/principle-fix-root-causes/SKILL.md`, l. 18). A guard the fix adds is a source scan only
when the defect is a fixed syntactic pattern, and a property of how data flows gets a structural
mechanism instead, in the order `references/design.md` gives under Screen for red flags (pstack,
`skills/principle-encode-lessons-in-structure/SKILL.md`, l. 19).

The site list is a command and its output, for a code defect and a doc defect alike. The fix brief's
CONTEXT carries the output, and its VERIFY the command that lists the sites, such as a `git grep`, a
script, or a red test over every input shape. A count is true at the commit that lands it, with the
command that regenerates it (pstack, `skills/technical-writing/SKILL.md`, l. 96), and a census is a
rerunnable script (pstack, `skills/principle-attack-the-premise/SKILL.md`, l. 15). The fixer reruns
the command after the fix and its REPORT gives the new output. The next round's gates lane reruns it
at the new head and records the count.

- **A behaviour that depends on order**, such as hook events, retries or concurrent writers, has a
  site for every order the inputs can arrive in. The brief names each order with the test that
  covers it *(kstack: fixes introduced bugs on orders their authors had not traced,
  per `references/evidence.md`, Run evidence behind the gate)*.
- **A false or unsupported claim in a doc or a comment** has a site at every place the claim
  reaches, and the command finds those places *(kstack: the red-test rule, carried over to docs,
  after failed doc fixes missed places, per `references/evidence.md`, Run evidence behind the
  gate)*. At each site the fix deletes the sentence, by default. unslop: "If you can't restate it
  as a concrete instruction, fact, or number, cut it." (pstack, `skills/unslop/SKILL.md`, l. 61),
  and of an unsourced claim, "Name the source or delete." (pstack, `skills/unslop/SKILL.md`,
  l. 23) Rewrite it only when the reader needs it and it can carry its source or the command that
  regenerates it (pstack, `skills/technical-writing/SKILL.md`, l. 96). A rewrite is new prose to
  review: "Each fix adds new code to review" (mattpocock-skills,
  `docs/engineering/code-review.md`, l. 77). *(kstack: rewording kept doc findings open for rounds
  after the code was proven, and deleting the claim closed them, per `references/evidence.md`, Run
  evidence behind the gate.)*

**A fresh agent writes the fix.** Give new work to a fresh subagent with consolidated scope: the
original brief, every later directive, and the prior agent's report and branch. That holds for a fix
round, a follow-up, a retry and the next queue item (pstack, `skills/poteto-mode/SKILL.md`, l. 99).
The root never writes a fix, and a round whose fix the root wrote is a gap *(kstack: swarm's gap is
a result missing the SHAs its brief names. A root-written fix leaves the round with no writer apart
from its judge, and roots did write fixes, per `references/evidence.md`, Run evidence behind the
gate.)* The fix goes through its playbook again (SKILL.md, Playbooks), test first. The verdict
names the agent and the model that wrote each fix. The new head gets a fresh round, except for lane
results that stay valid under the patch-id rule.

**A finding that comes back is a failed correction.** Each act-on finding gets an ID in the round's
record, `R<round>-<n>`, and the Reply carries it. When a later round reports the same defect, or a
defect that a fix introduced, it is a failed correction against that ID.
`references/when-a-fix-fails.md` says what happens next, based on that count.

## The patch-id rule

Record the verdict's head SHA, base SHA and stable `git patch-id` of the base-to-head diff. A rebase
or a base retarget rewrites SHAs, and can silently invalidate a verdict without touching a check
(pstack, `skills/poteto-mode/playbooks/shipping.md`, l. 9). Before a fix round's lanes start and
before merging, compare the recorded patch-id with the current one,
`git diff <base>..<head> | git patch-id --stable`.

- **They match.** Keep the code verdict, but re-run the checks at the current head. Never accept
  matching commit messages or a green check from an older SHA instead (pstack,
  `skills/poteto-mode/playbooks/shipping.md`, l. 9).
- **They differ only in tests, docs, or lint config.** Build what each lane ran, twice at the
  verdict SHA and once at the current head. A difference is noise if the two builds at the verdict
  SHA also show it, or if it is an embedded commit SHA. Judge each difference, not each file, and
  report each kind of noise with its files. If only noise differs, that lane's result stays valid,
  and checks and a review of the change run fresh. Do not reuse a lane result from a dev server or
  from anything else with no build output. Rerun that lane (pstack,
  `skills/poteto-mode/playbooks/shipping.md`, l. 9). *(kstack, the translation: a lane with build
  output is a live or regression drive of a build, and it is kept by the noise test with
  `gate.py record lane <name> --kept-from <sha> --note <the noise found>`. A regression lane runs
  "the same load-bearing scenario on current trunk" (pstack,
  `skills/poteto-mode/playbooks/autopilot-full.md`, l. 8), so it is kept only while the merge base
  with main is the one it ran on, and `gate.py` refuses it otherwise. A drive against a dev server
  and every review lane, which reads source and builds nothing, rerun. "Checks" are the gates lane,
  at the current head. "A review of the change" is the review lane 3 sets, two or more lanes, here
  two on different models, that read the new commits with the earlier round's brief, recorded with
  `--at`. In a skill set, a `SKILL.md`, a reference or an agent's definition is code, since an agent
  runs it. Docs here are text no program or agent acts on, such as a README, a product or design
  record, and comments.)*
- **They differ in anything else.** Re-verify (pstack, `skills/poteto-mode/playbooks/shipping.md`,
  l. 9).

## Merge preparation

These steps are autopilot-full step 5, with local merges in place of PRs *(kstack, the translation:
kstack merges a local branch into local main, where pstack merges a PR on a forge)*.

1. **Rebase once, when the branch is merge-ready.** Merge only from a head freshly rebased onto
   trunk, and merge prep never comes before a round's lanes start (pstack,
   `skills/poteto-mode/playbooks/autopilot-full.md`, l. 9). Rebase onto current main, then re-run
   the project's checks on that head (lane 1).
2. **Re-check the verdict** with the patch-id rule. A new patch voids the verdict, except the lane
   results that rule keeps.
3. **Check the merge.** Once that head is green and its patch-id matches the verdict's, a later move
   of main does not force another rebase (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`,
   l. 9). Right before the merge, check that `git merge-tree` of the head against local main is
   clean, and that no file main changed since the merge base is one the change touches, or one that
   decides which checks run. If either check fails, rebase again and repeat from step 1. Whenever
   main has moved since the merge base, `gate.py land` first refuses unless the gates row at the
   head recorded main's tip equal to the head's merge base, which is step 1's rebase. Then it runs
   both checks, and refuses, naming the check, when one fails. *(kstack, the translation: pstack's
   CI config paths are the pathspecs a project lists in `GATE_CHECK_PATHS`, empty by default.)*
4. **Merge as one commit** on main, as pstack squash-merges (pstack,
   `skills/poteto-mode/playbooks/autopilot-full.md`, l. 9). The commit message carries the verdict,
   the Reply below, after a line that reads `GATE VERDICT:`. A merge without that verdict, or with a
   verdict that is not clean, does not land.
   `gate.py land <message-file>` makes this commit on main's latest commit, and refuses unless the
   ledger holds a clean verdict for the current patch. The commit holds the head's tree, or the
   merged tree when main had moved, and then its verdict line names the move. It then prints the
   commands that remove the worktree, then the branch.

**Who may merge** is SKILL.md's "## Autonomy" rule. The grant to merge into local main is standing,
so a clean verdict merges. A change the operator named, or asked to see first, ends at merge-ready,
with a clean verdict recorded on its branch.

**Reply:** each lane with its model, the commit it checked and its result (`PASS`, `ISSUES`,
`BLOCKED` or gap). Each fix with the agent and the model that wrote it. The act-on findings with
their IDs. Each flake that passed its fresh run (lane 1). The queue, with where each item was filed.
The consider calls with their options. The nits. The recorded patch-id. The merge commit, or the
branch at merge-ready. That is each verdict and who produced it (pstack,
`skills/poteto-mode/playbooks/shipping.md`, l. 17; pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, l. 13).
