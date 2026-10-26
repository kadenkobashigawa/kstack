# Making something faster

Load this when the change makes something faster without changing what it does. Adapted from
pstack's perf-issue playbook (Lauren Tan, MIT). Practice, not measurement.

"**You own the measurement story. Plan, review, verify the numbers.**" (pstack,
`skills/poteto-mode/playbooks/perf-issue.md`, l. 3) The root plans, reviews and verifies. Fresh
subagents take the measurements and write the fix (SKILL.md, Subagents). Each step below names the
check in SKILL.md it carries out and who does it. Tie every fix to a measurement. Reading the source
is not measuring (pstack, `skills/poteto-mode/playbooks/perf-issue.md`, l. 3).

## 1. Capture a baseline

Carries out check 4 (verify) by giving it a baseline. A subagent measures on the real surface, and
the root vets the number with `references/measure.md` before trusting it (pstack,
`skills/poteto-mode/playbooks/perf-issue.md`, l. 5).

## 2. Read the affected path

Carries out check 1 (understand), `references/understand.md`, and grounds the hypotheses in the
baseline (pstack, `skills/poteto-mode/playbooks/perf-issue.md`, l. 6). An Explore subagent runs the
search for anything bigger than one file. The root writes the results: the placement line, the
risk list and the written interpretation, which names the number to improve and its target. Don't
claim a ceiling without running it (pstack, `skills/poteto-mode/playbooks/perf-issue.md`, l. 6).
*(kstack: pstack runs its how skill here. kstack has no how skill, and check 1 carries the one
question it takes from how, the placement line.)*

## 3. Try the cheapest idea first

Carries out check 2 (simplify). The root works down this list, cheapest first, and stops at the
first idea that meets the target (pstack, `skills/poteto-mode/playbooks/perf-issue.md`, ll. 7–16):

1. Don't do it. Stop work whose result nothing uses.
2. Do it, but not again.
3. Do less of it.
4. Do it later.
5. Do it when nobody is waiting.
6. Do it concurrently.
7. Do it cheaper.

## 4. Fix it, one change per measurement

Carries out checks 2 and 3 (simplify, contain). The root plans the fix from the baseline. When it
crosses a function boundary, `references/design.md`, the sketch step, runs first (pstack,
`skills/poteto-mode/playbooks/perf-issue.md`, l. 17). A fresh subagent writes it, and the root
reviews the diff. Verify each attempt before trying the next (pstack,
`skills/poteto-mode/playbooks/perf-issue.md`, l. 18). Keep a change only if it beats the noise and
the regression tests stay green (pstack, `skills/poteto-mode/playbooks/hillclimb.md`, l. 14).

## 5. Compare before and after

Carries out check 4 (verify). A subagent measures again on the same surface, and the root vets the
new number with `references/measure.md`, as it did the baseline (pstack,
`skills/poteto-mode/playbooks/perf-issue.md`, l. 5). The root compares the two sets of results
directly, not by reading summaries. "Inconclusive" or a different surface is not a pass. Flag it
(pstack, `skills/poteto-mode/playbooks/perf-issue.md`, l. 19).

## 6. Order the commits

The root orders the commits, one concern per commit, in the order that proves the work, as in "a
baseline capture before the treatment" (pstack,
`skills/principle-sequence-verifiable-units/SKILL.md`, l. 15). The commit that carries the fix cites
the measurement (pstack, `skills/poteto-mode/playbooks/perf-issue.md`, l. 20) *(kstack, the
translation: the commit message in place of pstack's PR)*.

## 7. Run the gate (`references/gate.md`)

The gate is the independent check that check 4 (verify) ends on. The root starts it, and fresh
agents that did not write the change run it on the change's own local branch. pstack: "Run
**Opening a PR**." (pstack, `skills/poteto-mode/playbooks/perf-issue.md`, l. 21) A clean verdict
merges into local main under the standing grant (SKILL.md, Autonomy). A change the operator named,
or asked to see first, stops at merge-ready. *(kstack, the translation: kstack merges local
branches, so Opening a PR, with its PR text and its forge, has no counterpart here. The gate is the
step where a change leaves its author.)*

Sustained improvement of one number against a target, rather than a one-off fix, is pstack's
Hillclimb playbook (pstack, `skills/poteto-mode/playbooks/perf-issue.md`, l. 23). *(kstack: build
carries no Hillclimb playbook. Run that work unattended under `references/long-run.md` with the
number as its predicate.)*

**Reply:** the baseline number, the post-fix number, the difference, and where the measurements
are kept (pstack, `skills/poteto-mode/playbooks/perf-issue.md`, l. 25). Then the branch and the
gate's verdict, or the merge commit.
