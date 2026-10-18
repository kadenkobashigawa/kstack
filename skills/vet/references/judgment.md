# Lead judgment

The reviewers are aggressive on purpose, and aggression without context produces noise. The lead
filters, checks and decides; it does not aggregate. From pstack's interrogate lead-judgment framework
(MIT). Practice, not measurement.

**The buckets are build's.** `~/.claude/skills/build/references/gate.md`, The verdict, holds the
five buckets (act on, consider, queue, nit, dismissed) and what proves a finding, ported from the same
lead-judgment framework. This file keeps only what vet adds: the filters, the proof-ladder rung, and
how each bucket is recorded, because vet reports and never repairs.

## Drop

- **Nitpick gravity.** A reviewer with nothing serious to say inflates nits. All nits means the code
  is probably fine; say so.
- **Hypothetical, not actual.** "What if this is None" is a finding only if a caller can pass None.
  Trace the call site yourself.
- **Premature abstraction.** A suggested extraction with one call site and no second use coming.
- **"I would have done it differently."** Dismiss it unless the reviewer showed a concrete problem.
- **Missing context that isn't proven.** Patterns consistent with the rest of the codebase, or
  advice that breaks a constraint the reviewer couldn't see. A proven defect in code the range
  didn't touch is not dropped: it is queue.

## Keep

- Both lanes found the same thing independently.
- The finding names a concrete execution path, not a possibility.
- It shows something the author's model of the code missed.
- Security and correctness findings get extra scrutiny before being dismissed, even from one lane.

## Check it yourself

Before a finding is filed as act on or queue, push its evidence down the proof ladder in build's
`references/verify.md` as far as is cheap, and record the rung: you pointed at the line, you walked
the bad case, you ran a script or test against the real code, you reproduced it in the running app.
A finding that stays at "the reviewer said so" is not proven, so it is dismissed with that reason.

## Recording each bucket

*(ours: vet never edits code, and the work session triages each finding, as SKILL.md says, so the
buckets become statuses in the tick's reply instead of a fix-forward)*

- **act on:** the reply, status `open`.
- **queue:** the reply, status `open`; its **where** names the file outside the range.
- **consider:** the reply, status `consider`, with the options.
- **nit:** the reply, one line each after the findings; it blocks nothing.
- **dismissed:** the tick's working notes, with its reason. They end with the tick.

## Calibrate

lead-judgment: "If your 'Act On' list has more than 5 items, you're probably not filtering hard
enough." Here that is a reason to re-check each act-on finding against the proof test above, never
to demote a proven one. Rank security, data loss and migration first. "The 'Dismissed' section is
not busywork. It's a trust mechanism." A dismissal's reason lives in the tick's working notes only,
and no agent audits them, by Kaden's choice (SKILL.md, Not carried), so the lead has no one to
check its filter and holds it to the proof test above.
