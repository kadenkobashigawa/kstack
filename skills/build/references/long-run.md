# Running a change unattended

Load this when a change is driven by `/loop` or left to run while the user is away. Adapted from
pstack's autonomous-run and hillclimb playbooks, its overnight guide, its show-me-your-work skill and
its sequence-verifiable-units and make-operations-idempotent principles (Lauren Tan, MIT). Practice,
not measurement.

## Earn the loop first

A loop that can't verify its own work only makes unchecked work faster. Run unattended only when all
four hold: the task has been done once by hand, the agent has the checks you would use (the tests, the
project's verify skill, the logs), every step can stop the line, and failures seen more than once are
already checks rather than reminders.

## The contract, written before the first iteration

- **Done:** a predicate that can pass or fail (tests green, repro fixed, a metric past its target with
  a floor on attempts). A duration is not a predicate.
- **Where:** a fresh worktree and branch, so the run collides with nothing. Run the code under test
  from the worktree (for Python, `PYTHONPATH` set to it) and check where the package imports from
  before trusting any result. Install nothing: the environment is shared with the main checkout. A
  gitignored settings file the suite needs is linked from the main checkout, never read or copied.
  A command that writes outside the worktree (a bin, a database, the user's settings) runs on a copy
  of that state, never the live one (ours: an unattended run has nobody to pause for, where
  poteto-mode pauses for "irreversible writes: force-push to shared branches, deploys, data
  deletion, customer messages.")
- **Allowed:** what the operator granted in the loop prompt. A merge follows pstack's autopilot-full:
  "The operator's full-autonomy grant plus the root's clean verdict is the merge authorization that
  babysitting alone never has." The verdict is the gate's (`references/gate.md`). Without both, the
  work stops at merge-ready. Never deploy or message anyone.
- **Trail:** the path of the decision log.
- **Escape:** when to stop and write up a dead end instead of spinning.

## When no task is handed over

One task per run. The loop's task is the rules. It checks a slice against `references/rules.md` in
their order (built well, works, written true), then takes the worst broken rule and nothing else.

1. **Where.** The run works in its own fresh worktree off current main (the contract's Where).
2. **Review the slice.** Before the built-well rules, write the slice's accretion story from its
   history (`git log` on its files): what it was asked to do, in order, in 3 to 6 lines. Rule 5,
   "built in, not bolted on", is judged against that story. The check runs as pstack's interrogate
   over the slice. Two reviewers, one Opus and one Sonnet, grade it; each gets the slice, its
   accretion story and `references/rules.md` as the rubric. Interrogate's reason: "The adversarial
   signal comes from model diversity, not assigned personas." *(Interrogate's default reviewers are
   two model families. Claude Code runs only Claude models, so here they are two Claude models,
   named, which is the weaker diversity `references/gate.md` names for its review lanes.)*
3. **Sort.** The root sorts their findings into the gate's buckets (`references/gate.md`, The
   verdict), with the slice standing in for the diff. *(interrogate reviews a diff; here it reviews
   a slice.)* An act-on finding is a broken rule.
4. **One task.** The worst proven broken rule is the run's only task: run build's checks 1 to 5 on
   that slice, then the gate (`references/gate.md`), then the merge. Then the run ends. The other
   findings are not recorded *(ours, Kaden, 2026-10-17: "the next rollback call, it's gonna go and
   review everything. Again")*: the next run reviews the slice afresh and finds what still stands.
   The predicate is that the rule is no longer broken at the commit that merged, or at merge-ready
   without the grant.
5. **If the task fails twice, the run stops.** Two failed corrections on the same issue is build's
   stop rule. The run writes the problem up in its reply only, and records nothing else.
6. **End clean.** The run removes its worktree when it ends. It deletes its branch only once the
   branch has merged, or when the task failed and the branch holds nothing worth keeping; a branch at
   merge-ready stays, since it is the work. pstack's worktree-cleanup prunes worktrees and keeps the
   branches: "Branch refs survive, so no commits are lost." The run's trail lives in its own folder
   and goes with it.

## Each iteration

Make the smallest change the evidence justifies, check it against the predicate, commit if it moved,
revert it if it didn't. One change, one check, one trail row. A plateau means change approach, not
stop. Never relax the predicate to declare victory. Each step must be safe to re-run after a crash:
it converges on the same end state whatever a half-finished earlier run left behind.

## A question for the person

A choice only the person can make does not hold up work that doesn't need it.
principle-never-block-on-the-human: "*Execution* should not block." The run puts the question, its
options and the default it takes in its reply, and in its trail when it keeps one: a robovac pass
keeps no file, so the reply is the person's only way to see it and overrule it after. orchestrate
parks each human gate as its "question, options, default on no answer" and lists "gates awaiting
the human (the only asks)" in its Reply. The default is the option the run recommends, and it
applies once the work reaches the choice with no answer yet. For a destructive or outward-facing
choice, the default is not to do it *(ours)*. A run that has nothing left to do without the answer
ends and hands back with the question as the last thing it says, as below *(ours)*. *(ours: on
2026-10-18 a blocking question idled a session for 3 h 39 min overnight while work that didn't need
it waited.)*

## The trail

One TSV file, append-only, one row per decision or iteration:

```
ts	phase	decision	why	evidence	result
```

`evidence` is a pointer (a sha, `file:line`, an artifact path), never a paragraph. `result` is the
predicate state (`tests green`, `reverted`, `INCONCLUSIVE`, `open`). A wrong row is superseded by a
new one, never edited. Keep it out of git unless a reviewer needs it to trust the result. A run with
no task handed over keeps its trail in the run's own folder, and the trail goes when the run ends.

## Handing back

Before reporting, check every row against what actually happened in the transcript, and add rows for
any fork or revert the trail missed. Then show-me-your-work's cross-model review: "spawn a subagent
on a different model family from the one that did the work. Self-review is not a substitute." It
reads the trail and the transcript and flags weak evidence, skipped checks and risky calls. *(Claude
Code runs only Claude models, so the reviewer is a different Claude model from the one that did the
work, which is weaker diversity, as `references/gate.md` says of its review lanes.)* The reply ends
with that Attention list, led by the reviewer's model on its own line (`reviewed by <model>`).

**Reply:** the predicate, iterations run, what landed, what was reverted, the final predicate state,
the questions parked for the person (each with its options and the default taken), the trail path
(when the trail outlives the run), and the cost: wall time, and each agent's tokens
as its task notification reports them *(ours)*.
