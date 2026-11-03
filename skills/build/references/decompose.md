# Splitting a large change into units

Load this when SKILL.md, Playbooks, routes a large or cross-cutting change here, before any
playbook runs. Adapted from Phases A and B of pstack's figure-it-out skill (Lauren Tan, MIT,
`upstream/pstack/skills/figure-it-out/`). Practice, not measurement.

The root runs this step and writes the unit list. Each unit then runs its own playbook, where fresh
subagents write the code (SKILL.md, Subagents).

## Decide whether the change is large

poteto-mode routes "A large or cross-cutting effort (a migration across many call sites, an
ambitious multi-part change)" here "even when a narrower playbook like Feature fits" (pstack,
`skills/poteto-mode/SKILL.md`, l. 126). Upstream gives no line count, so the root makes the call
by the kind of change, as `references/gate.md` does for a large diff *(kstack: a number would be
kstack's invention)*. Skip this step, and say so in the task list, by multi-phase-plan's rule:
"When the change is one or two files with an obvious approach, skip the plan." (pstack,
`skills/poteto-mode/playbooks/multi-phase-plan.md`, l. 5)

## Frame the change

figure-it-out's Phase A: "Ground first, then commit." (pstack, `skills/figure-it-out/SKILL.md`,
l. 17) Beside the Done predicate (`references/long-run.md`, The contract), the root states two
things before it designs the units:

- **Scope.** "Scope, quantified: rough units and effort, plus the blockers grounding surfaced."
  (pstack, `skills/figure-it-out/SKILL.md`, l. 20)
- **Rigor.** "The rigor level, biased high. One-way doors and high blast radius get more.
  Reversible low-stakes steps get less. Rigor is gates and artifacts, not "try harder"." (pstack,
  `skills/figure-it-out/SKILL.md`, l. 21) A unit's rigor is the evidence it names and the gate it
  runs (`references/gate.md`) *(kstack, the translation: build's gates and evidence are
  figure-it-out's gates and artifacts)*.

"Present the framing and tradeoffs before committing to a long run. Reversible work proceeds (the
**never-block-on-the-human** principle skill), but a multi-hour run earns one checkpoint." (pstack,
`skills/figure-it-out/SKILL.md`, l. 23) The root presents the scope, the rigor level and the unit
list together, once, before the first unit starts.

## Design the units

1. **Split the change into units.** "Decompose into atomic, independently-landable units."
   (pstack, `skills/figure-it-out/SKILL.md`, l. 27) Each unit is "one change with its own
   evidence" (pstack, `skills/poteto-mode/playbooks/multi-phase-plan.md`, l. 8), so each unit is
   its own branch, gated and merged alone (`references/gate.md`, The unit of work) *(kstack, the
   translation: pstack's unit is a PR, and here it is a local branch)*.
2. **Put the riskiest unknown first.** "Sequence riskiest-unknown-first. Scaffold and verification
   come before features" (pstack, `skills/figure-it-out/SKILL.md`, l. 27). The unit whose design
   could still turn out wrong lands before the units that build on it.
3. **Build the check before the work.** "Build the verification harness before the work, with the
   baseline captured from the pre-change state" (pstack, `skills/figure-it-out/SKILL.md`, l. 29),
   so each check compares the old value with the new one. The harness is the first unit, or the
   first commit of it, and it captures its baseline on main before any other unit lands.
4. **Sketch a one-way door.** "For one-way-door design decisions, run the **architect** skill (it
   runs **arena**)." (pstack, `skills/figure-it-out/SKILL.md`, l. 30) Here that is
   `references/design.md`, the sketch step, inside the unit that holds the decision. It skips
   mechanical work, as that file says.
5. **Fan out only across seams.** "Parallelize only across seams, and give each worker its own
   worktree or branch" (pstack, `skills/figure-it-out/SKILL.md`, l. 31). Units that touch the same
   file run one after the other (`references/gate.md`, The unit of work). "Don't over-fan."
   (pstack, `skills/figure-it-out/SKILL.md`, l. 31)
6. **Write the unit list down.** "Write the designed phase list down. That list is what the human
   reviews." (pstack, `skills/figure-it-out/SKILL.md`, l. 32) Put each unit in the task list as a
   concrete item (pstack, `skills/figure-it-out/SKILL.md`, l. 34), with its playbook, its branch,
   the units it waits for and the evidence that proves it.

**Done when** every unit names its playbook, its evidence and the units it waits for, the harness
unit comes first, and the list is in the task list.

## Run the units in order

Each unit routes to its row in SKILL.md, Playbooks, and runs that playbook through its gate and
merge. A unit that builds on another branches off main only after that unit merges
(`references/gate.md`, The unit of work). figure-it-out runs each unit "verifying each unit before
starting the next instead of batching checks at the end." (pstack,
`skills/figure-it-out/SKILL.md`, l. 38) A unit that stops at merge-ready, because the operator asked
to see it first, holds every unit that builds on it.

## The other phases are in long-run.md

figure-it-out runs four more phases around this one, and `references/long-run.md` holds each:

- Phase A's falsifiable predicate is that file's contract, Done. Its scope, rigor and checkpoint
  are Frame the change, above.
- Phase C's loop is its Each iteration.
- Phase D's audit trail is its The trail.
- Phase E's check of the whole against the predicate is its Handing back.

A large change runs those four sections whether or not the operator is away, since figure-it-out
adds all its phases as todos: "Then add the phases below as todos." (pstack,
`skills/figure-it-out/SKILL.md`, l. 13)

**Reply:** "the playbook you designed, the rigor level and why, the decision-trail path, what's
verified against the predicate, and what's still open." (pstack, `skills/figure-it-out/SKILL.md`,
l. 52) The playbook is the unit list, and the rigor level is the one Frame the change set. Then
each landed unit's gate Reply (`references/gate.md`).
