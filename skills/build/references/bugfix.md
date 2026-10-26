# Fixing a bug

Load this when the change corrects a defect. Adapted from pstack's bug-fix playbook, its tdd skill
and the benny repro rules (Lauren Tan, MIT). Practice, not measurement.

"**You own this task. Plan, review, verify.** Delegate investigation and the fix to subagents, stay
in the lead." (pstack, `skills/poteto-mode/playbooks/bug-fix.md`, l. 3) The root plans, reviews and
verifies. Fresh subagents investigate, write the test and write the fix (SKILL.md, Subagents). Each
step below names the check in SKILL.md it carries out and who does it.

Every shipped line traces to runtime evidence. A change that "might help" is a hypothesis, not a
fix, and it does not ship. When evidence refutes a hypothesis, revert what it motivated (pstack,
`skills/poteto-mode/playbooks/bug-fix.md`, l. 5).

## 1. Reproduce it on the surface it was reported on

Carries out check 1 (understand) by running the bug instead of asking about it, and gives check 4
(verify) its baseline. A subagent drives the reproduction. The root reads the captured values, not
the subagent's summary.

- Drive the real path: the project's verify skill for the UI or API, the real command for a CLI.
  pstack says "Reproduce it yourself", meaning the agent and not the user (pstack,
  `skills/poteto-mode/playbooks/bug-fix.md`, l. 7). Ask the user to reproduce only with a stated
  reason the surface can't be reached, after driving it as far as it goes.
- **The symptom must appear twice.** Reset between attempts so the second is independent. Read a
  real value to cross-check what the screen shows. Inspection confirms. It never injects the
  symptom.
- **Check for an existing fix first.** If a commit or branch plausibly fixes the bug, verify that
  fix instead: the baseline shows the bug twice, and the patched build doesn't, twice. Don't race
  it.
- If the bug won't reproduce, tighten the conditions or instrument until it fires. No repro, no fix.

## 2. Read the affected path

Carries out check 1 (understand), `references/understand.md`. An Explore subagent runs the search
for anything bigger than one file. The root writes the results: the placement line, the impact
set and its tests (the risk list), and the written interpretation. For a bug, the interpretation
names **the correct final state and the broken one**. A loading state, a dialog or a setup step is
not the bug. The bug is the state where right and broken diverge. *(kstack: pstack's bug-fix seeds
its hypotheses with its how skill at this step. kstack has no how skill. Check 1 carries the one
question it takes from how, the placement line, and hands the gate and `references/contain.md` the
interpretation they judge against.)*

## 3. Binary-search the cause

Carries out check 1 (understand): the cause is confirmed by evidence, never assumed. The root lists
the candidate causes and picks each split. Subagents gather the evidence for a split and report it
back.

Seed the candidates from the affected path as step 2 read it, and from its regression history
(`git log` on the affected files). *(kstack: pstack seeds them with its how and why skills. kstack
has neither skill, and takes from how only the placement question, which check 1's placement line
in `references/understand.md` asks.)* Each pass, take the split that rules out the most, get runtime
evidence (logs, a probe, a debugger, a query), and eliminate. When state is unclear, add
instrumentation and read it as the code runs. Confirm the surviving mechanism with evidence before
planning the fix. For a bug that appears after a restart, suspect stale persistent state (caches,
lock files, serialized rows) before code (pstack, `skills/principle-fix-root-causes/SKILL.md`,
l. 23). A long or stubborn hunt runs under `/loop`, with `references/long-run.md`.

## 4. Write the failing test, and run it before the fix

Carries out check 4 (verify), its first rule: the test comes before the code it checks. A subagent
writes the test and runs it. The root confirms that it fails, and fails for the intended reason,
before anyone touches the code. pstack's tdd: "Write the failing test first." (pstack,
`skills/tdd/SKILL.md`, l. 17) Then "Run the new test before fixing. Confirm it fails for the
intended reason." (pstack, `skills/tdd/SKILL.md`, l. 18)

The test is required when there is an obvious cheap local test path. When the only test would need
brittle mocks, production-only state or broad fixture churn, use the closest executable check
instead (a script, a real request, a verify-skill drive) and say why (pstack, `skills/tdd/SKILL.md`,
l. 24). "Prefer no new test over a bad test." (pstack, `skills/tdd/SKILL.md`, l. 26)

## 5. Fix the root, at its layer

Carries out check 2 (simplify), since the fix sits in the layer where the defect lives, and check 3
(contain), since the diff holds only what the interpretation named. The root plans the fix. A fresh
subagent writes it from a brief that points at the files and carries the interpretation, the risk
list and the failing test. The root reviews the diff. pstack: "Delegate implementation to a subagent
... with a specific scope." (pstack, `skills/poteto-mode/playbooks/bug-fix.md`, l. 9)

The fix is the smallest change the evidence justifies, in the layer where the defect lives. A guard
that silences the symptom (a null check, a retry, a broad except) is not a fix. Fix every place the
same pattern appears, in the same change. The fix brief carries the command that lists those places,
such as a `git grep`, with its output. The fixer reruns it after the fix (`references/gate.md`,
The verdict). Record an instance that belongs to another owner in the project's findings
queue instead. pstack's playbook says "If it crosses a function boundary, `architect` first"
(pstack, `skills/poteto-mode/playbooks/bug-fix.md`, l. 9). Here `references/design.md`, the sketch
step, runs first *(kstack: `references/design.md`, Design it twice, says why it runs on Opus and
Sonnet)*. After two failed fixes for the same issue, stop and follow
`references/when-a-fix-fails.md`.

## 6. Prove it on the same surface

Carries out check 4 (verify). The root verifies. A subagent may drive the app, and the root reads
its captured evidence rather than its summary.

The original repro now passes, twice, on the same surface, with the same real value cross-checked.
"Inconclusive" or a different surface is not a pass. Flag it (pstack,
`skills/poteto-mode/playbooks/bug-fix.md`, l. 10). A unit test shows branch behaviour, not that the
bug is gone. Then run the risk list, and smoke the nearby states, inputs and failure paths.

## 7. Order the commits as the argument

The root orders the commits, one concern per commit. The failing test or repro script lands before
the fix, so history reads red then green (pstack, `skills/poteto-mode/playbooks/bug-fix.md`, l. 11).

## 8. Run the gate (`references/gate.md`)

The gate is the independent check that check 4 (verify) ends on. The root starts it, and fresh
agents that did not write the change run it on the fix's own local branch. pstack: "Run **Opening a
PR**." (pstack, `skills/poteto-mode/playbooks/bug-fix.md`, l. 13) A clean verdict merges into
local main under the standing grant (SKILL.md, Autonomy). A change the operator named, or asked to
see first, stops at merge-ready. *(kstack, the translation: kstack merges local branches, so
Opening a PR, with its PR text and its forge, has no counterpart here. The gate is the step where a
change leaves its author.)*

**Reply:** what was broken, the root cause, the fix, and the failing-then-passing output verbatim.
Then the branch and the gate's verdict, or the merge commit.
