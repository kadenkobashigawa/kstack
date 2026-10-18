# Fixing a bug

Load this when the change corrects a defect. Adapted from pstack's bug-fix playbook, its tdd skill and
the benny repro rules (Lauren Tan, MIT). Practice, not measurement.

Every shipped line traces to runtime evidence. A change that "might help" is a hypothesis, not a fix,
and it does not ship. When evidence refutes a hypothesis, revert what it motivated.

## 1. Reproduce it yourself, on the surface it was reported on

- Drive the real path: the project's verify skill for the UI or API, the real command for a CLI.
  Ask the user to reproduce only with a stated reason the surface can't be reached, after driving it
  as far as it goes.
- **Name the correct final state and the broken one before you start.** A loading state, a dialog or
  a setup step is not the bug; the state where right and broken diverge is.
- **The symptom must appear twice.** Reset between attempts so the second is independent. Read a real
  value to cross-check what the screen shows. Inspection confirms; it never injects the symptom.
- **Check for an existing fix first.** A commit or branch that plausibly fixes it switches you to
  verifying that fix (baseline shows the bug twice, patched build doesn't, twice). Don't race it.
- If it won't reproduce, tighten the conditions or instrument until it fires. No repro, no fix.

## 2. Binary-search the cause

List the candidate causes. Seed them from the affected path as check 1 read it, and from its
regression history (`git log` on the affected files). *(ours: pstack seeds them with its how and
why skills. kstack has neither skill; of how it carries only the placement question, which
check 1's placement line in SKILL.md asks.)* Each pass, take the split that rules out the most, get
runtime evidence (logs, a probe, a debugger, a query), and eliminate. When state is unclear, add
instrumentation and read it as the code runs. Confirm the surviving mechanism with evidence before
planning the fix. Restart bugs: suspect stale persistent state (caches, lock files, serialized
rows) before code. A long or stubborn hunt runs under `/loop`, with `references/long-run.md`.

## 3. Fix the root, at its layer

The smallest change the evidence justifies, in the layer where the defect lives. A guard that
silences the symptom (a null check, a retry, a broad except) is not a fix. Grep for the same pattern
and fix every instance in the same change, or record the others if they belong to another owner.
Where pstack's playbook says "If it crosses a function boundary, `architect` first", here
`references/design.md` loads only when the fix is a one-way door *(ours: the 2026-10-09 vote merged
architect into `references/design.md` for one-way doors, and architect's design exploration runs on
arena, parked until Claude Code can reach a second model family)*.

## 4. Test first when it's cheap

When there is an obvious cheap local test path, write the failing test first, run it, and confirm it
fails for the intended reason before touching the code. When the only test would need brittle mocks,
production-only state or broad fixture churn, use the closest executable check instead (a script, a
real request, a verify-skill drive) and say why. **No test beats a bad test.**

## 5. Prove it on the same surface

The original repro now passes, twice, on the same surface, with the same real value cross-checked.
"Inconclusive" or a different surface is not a pass; flag it. A unit test shows branch behaviour, not
that the bug is gone. Then smoke the blast radius: nearby states, inputs and failure paths.

## 6. Order the commits as the argument

The failing repro (test or script) lands before the fix, so history reads red then green.

**Reply:** what was broken, the root cause, the fix, and the failing-then-passing output verbatim.
