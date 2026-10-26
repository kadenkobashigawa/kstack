# Running a change unattended

Load this when a change is driven by `/loop` or left to run while the user is away. Adapted from
pstack's autonomous-run and hillclimb playbooks, its overnight guide, its show-me-your-work skill
and its sequence-verifiable-units and make-operations-idempotent principles (Lauren Tan, MIT).
Practice, not measurement.

"**You own the exit condition. Define done, then drive to it without stopping.**" (pstack,
`skills/poteto-mode/playbooks/autonomous-run.md`, l. 3) This file wraps the routed playbook
(SKILL.md, Playbooks), which keeps its own split: the root plans, reviews and verifies, and fresh
subagents investigate and write (SKILL.md, Subagents). The root also holds the contract below and
keeps the trail.

## Earn the loop first

A loop that can't verify its own work only makes unchecked work faster. Run unattended only when all
four hold: the task has been done once by hand, the agent has the checks you would use (the tests,
the project's verify skill, the logs), every step can stop the line, and failures seen more than
once are already checks rather than reminders (pstack, `docs/guide/07-overnight.md`, ll. 9–16).

## The contract, written before the first iteration

- **Done:** a predicate that can pass or fail (tests green, repro fixed), stated before the first
  iteration (pstack, `skills/poteto-mode/playbooks/autonomous-run.md`, l. 5). A metric target
  carries a floor on attempts, so a lucky early win can't end the run (pstack,
  `skills/poteto-mode/playbooks/hillclimb.md`, l. 7). A duration is not a predicate *(kstack: a
  duration says when to stop, not whether the work is done)*.
- **Where:** a fresh worktree and branch, so the run collides with nothing (pstack,
  `docs/guide/07-overnight.md`, l. 33). Run the code under test from the worktree (for Python,
  `PYTHONPATH` set to it) and check where the package imports from before trusting any result.
  Install nothing, since the worktree shares its environment with the main checkout. A gitignored
  settings file the suite needs is linked from the main checkout, never read or copied *(kstack: an
  editable install points at the main checkout, so a test run from the worktree can load the main
  checkout's code, and an install from the worktree repoints it)*. A command that writes outside the
  worktree (a bin, a database, the user's settings) runs on a copy of that state, never the live one
  *(kstack: an unattended run has nobody to pause for)*. poteto-mode pauses for "irreversible
  writes: force-push to shared branches, deploys, data deletion, customer messages." (pstack,
  `skills/poteto-mode/SKILL.md`, l. 85)
- **Allowed:** what the operator granted in the loop prompt, on top of the standing grant to merge
  into local main (SKILL.md, Autonomy). A merge follows pstack's autopilot-full: "The operator's
  full-autonomy grant plus the root's clean verdict is the merge authorization that babysitting
  alone never has." (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 9) The verdict is
  the gate's (`references/gate.md`). A clean verdict merges into local main. A change the operator
  named, or asked to see first, stops at merge-ready. Never push, deploy or message anyone, which
  SKILL.md, Autonomy, keeps for the operator.
- **Wake:** how the run comes back after it waits. autonomous-run: "An event to watch (CI, a merge,
  a ref advancing) gets a watcher subagent that wakes you on the event, with a long time-based
  heartbeat as fallback. No event gets a fixed-interval heartbeat sized to when the result is worth
  re-checking." (pstack, `skills/poteto-mode/playbooks/autonomous-run.md`, l. 6) Here the watcher is
  a background command (`run_in_background`) that exits when the event happens, and its exit wakes
  the session. The heartbeat is `/loop`'s next wake-up *(kstack, the
  translation: a background command does a watcher subagent's job without spending an agent)*.
- **Trail:** the path of the decision log, one row per iteration (pstack,
  `skills/poteto-mode/playbooks/autonomous-run.md`, l. 10).
- **Escape:** when to stop and write up a dead end instead of spinning (pstack,
  `docs/guide/07-overnight.md`, l. 36).

## A discovery during a handed-over task

When the task is handed over, a discovery that stands between the run and its predicate is the
run's own: a broken skill the run uses, a related bug on the predicate's path, a flaky verifier the
predicate runs. autonomous-run: "Mid-run discoveries are yours." (pstack,
`skills/poteto-mode/playbooks/autonomous-run.md`, l. 9) The run fixes it out of band, as a change on
its own branch through build, and then goes back to the predicate. "Keep the predicate as the main
drive, and return to it after each side fix." (pstack,
`skills/poteto-mode/playbooks/autonomous-run.md`, l. 9) *(kstack, the translation: a branch of its
own that passes the gate, in place of pstack's "their own PR")*. A discovery that does not block the
predicate is recorded, not fixed (`references/contain.md`). *(kstack: autonomous-run makes every
discovery the run's own, and contain.md keeps a non-blocking one out of every run, attended or not.
Taking only the blocking ones keeps both rules true.)*

## When no task is handed over

One task per run, and the code rules choose it. The run checks a slice against `references/rules.md`
in the rules' order (built well, works, written true), then takes the worst broken rule and nothing
else. orchestrate holds the same line for a large run: "Mid-run discoveries fix only what blocks the
frontier. Everything else parks in follow-ups." (pstack,
`skills/poteto-mode/playbooks/orchestrate.md`, l. 109) *(kstack: this is robovac's build step, which
takes one task per run, `skills/robovac/SKILL.md`.)*

1. **Where.** The run works in its own fresh worktree off current main (the contract's Where).
2. **Review the slice.** Before the built-well rules, write the slice's accretion story from its
   history (`git log` on its files): what it was asked to do, in order, in 3 to 6 lines. Rule 5,
   "built in, not bolted on", is judged against that story *(kstack: rule 5 asks how the code would
   look had each requirement been known from the start, which needs the order they came in)*. The
   check runs as pstack's interrogate over the slice. Two reviewers, one Opus and one Sonnet, grade
   it. Each gets the slice, its accretion story and `references/rules.md` as the rubric.
   Interrogate's reason: "The adversarial signal comes from model diversity, not assigned personas."
   (pstack, `skills/interrogate/SKILL.md`, l. 9) Interrogate's default reviewers are two model
   families (pstack, `skills/interrogate/SKILL.md`, ll. 38–41). *(kstack, the translation: Claude
   Code runs only Claude models, so here they are Opus and Sonnet, the same pair as the gate's
   review lanes.)*
3. **Sort.** The root sorts their findings into the gate's buckets (`references/judgment.md`), with
   the slice standing in for the diff *(kstack, the translation: interrogate reviews a diff, and
   here it reviews a slice)*. An act-on finding is a broken rule.
4. **One task.** The worst proven broken rule is the run's only task. Its fix is a change, so it
   goes to its playbook (SKILL.md, Playbooks), which ends at the gate (`references/gate.md`) and the
   merge. Then the run ends. autonomous-run drives its side fixes the same way: "Address broken
   skills, related bugs, ... yourself via poteto-mode." (pstack,
   `skills/poteto-mode/playbooks/autonomous-run.md`, l. 9) The other findings are recorded as the
   queue bucket in `references/judgment.md` says, and left for a later run. The predicate is that
   the rule is no longer broken at the commit that merged, or at the merge-ready branch when the
   operator asked to see the change first.
5. **When the task's fix fails,** `references/when-a-fix-fails.md` decides what happens next. Where
   that file stops the work, the run ends and writes the problem up in its reply only.
6. **End clean.** The run removes its worktree when it ends. It deletes its branch only once the
   branch has merged, or when the task failed and the branch holds nothing worth keeping. A branch
   at merge-ready stays, since it is the work. pstack's worktree-cleanup prunes worktrees and keeps
   the branches: "Branch refs survive, so no commits are lost." (pstack,
   `skills/poteto-mode/playbooks/worktree-cleanup.md`, l. 9) The run's trail lives in its own folder
   and goes with it.

## Each iteration

Make the smallest change the evidence justifies, check it against the predicate, commit if it moved,
revert it if it didn't (pstack, `skills/poteto-mode/playbooks/autonomous-run.md`, l. 7). One
change, one check, one trail row. A plateau means change approach, not stop. Never relax the
predicate to declare victory (pstack, `docs/guide/07-overnight.md`, l. 56). Each step must be safe
to re-run after a crash: it converges on the same end state whatever a half-finished earlier run
left behind (pstack, `skills/principle-make-operations-idempotent/SKILL.md`, l. 9).

## A question for the person

A choice only the person can make does not hold up work that doesn't need it.
principle-never-block-on-the-human: "*Execution* should not block." (pstack,
`skills/principle-never-block-on-the-human/SKILL.md`, l. 20) The run puts the question, its options
and the default it takes in its reply, and in its trail when it keeps one. A robovac pass keeps no
file, so the reply is the person's only way to see the question and overrule the default after.
orchestrate parks each human gate as its "question, options, default on no answer" (pstack,
`skills/poteto-mode/playbooks/orchestrate.md`, l. 30) and lists "gates awaiting the human (the only
asks)" (pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 111) in its Reply. The default is
the option the run recommends, and it applies once the work reaches the choice with no answer yet.
For a destructive or outward-facing choice, the default is not to do it *(kstack: SKILL.md,
Autonomy, pauses for irreversible work, and an unattended run has nobody to pause for)*. A run that
has nothing left to do without the answer ends and hands back, with the question as the last thing
it says *(kstack: the last line is the one the person reads first on return. On 2026-10-18 a
blocking question idled a session for 3 h 39 min overnight while work that didn't need it waited.)*

## The trail

One TSV file, append-only, one row per decision or iteration:

```
ts	phase	decision	why	evidence	result
```

`evidence` is a pointer (a sha, `file:line`, an artifact path), never a paragraph. `result` is the
predicate state (`tests green`, `reverted`, `INCONCLUSIVE`, `open`). A new row supersedes a wrong
one, and no row is edited. Keep it out of git unless a reviewer needs it to trust the result
(pstack, `skills/show-me-your-work/SKILL.md`, ll. 13–22, 46–52). A run with no task handed over
keeps its trail in the run's own folder, and the trail goes when the run ends *(kstack: robovac's
pass leaves nothing on disk but clorox's bin)*.

## Handing back

Before reporting, check every row against what actually happened in the transcript, and add rows for
any fork or revert the trail missed (pstack, `skills/show-me-your-work/SKILL.md`, ll. 57–63). Then
show-me-your-work's cross-model review: "spawn a subagent on a different model family from the one
that did the work. Self-review is not a substitute." (pstack, `skills/show-me-your-work/SKILL.md`,
l. 67) It reads the trail and the transcript and flags weak evidence, skipped checks and risky
calls. *(kstack, the translation: Claude Code runs only Claude models, so the reviewer is a
different Claude model from the one that did the work, which is weaker diversity, as
`references/gate.md` says of its review lanes.)* The reply ends with that Attention list, led by the
reviewer's model on its own line, `reviewed by <model>` (pstack,
`skills/show-me-your-work/SKILL.md`, l. 74).

**Reply:** the predicate, the iterations run, what landed with the gate's Reply for it
(`references/gate.md`), what was reverted, the final predicate state, the questions parked for the
person (each with its options and the default taken), the trail path (when the trail outlives the
run), and the cost: wall time, and each agent's tokens as its task notification reports them.
autonomous-run's Reply is "the exit condition, iterations run, what landed, what was discarded,
final predicate state" (pstack, `skills/poteto-mode/playbooks/autonomous-run.md`, l. 13). *(kstack:
the parked questions, the trail path and the cost are added, because the person reviews an
unattended run after the fact.)*
