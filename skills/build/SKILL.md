---
name: build
description: Runs on every code change, one line or one module. Four checks against the measured ways coding agents fail (understand what the change disturbs and what already does the job, simplify, keep the diff to what was named, verify on the real path), plus methods for bugs, refactors, designs, measured numbers and unattended runs. Use when writing or changing any code, or when the user types /build or says "build X", "new feature", "fix this".
trigger: /build
---

# build

Coding agents fail in four named ways. Every one of them ships code that looks right:
**unchecked assumptions**, **over-complication**, **orthogonal damage**, **unvalidated
execution**. This skill is one check per failure mode, and it runs on every change —
a one-line fix is where the measured decay actually happens.

The checks are proportional by construction. A one-line fix has a small impact set and a
one-sentence interpretation; a new module has a wide one. **Nothing here scales to zero.**

Project specifics — test commands, where findings go, the language's reference syntax —
are derived from the repo each run, never frozen here.

**Some changes carry their own method on top of the four checks.** Load the one that fits
before starting:

| The change | Load |
|---|---|
| corrects a defect | `references/bugfix.md` |
| reshapes code without changing behaviour | `references/refactor.md` |
| is hard to undo: a boundary, schema or interface others build on | `references/design.md` |
| claims a number: a speedup, regression, latency or score | `references/measure.md` |
| runs unattended, under `/loop` or while the user is away | `references/long-run.md` |

**Every change that is to be merged then passes the gate,** `references/gate.md`, whichever method it
used. Each self-contained change is its own branch, gated and merged alone; only overlapping work
waits for another's merge (`references/gate.md`, The unit of work). `references/rules.md` holds the
code rules that the gate's review lanes and the unattended loop both check.

## 1 — UNDERSTAND · counters unchecked assumptions

Models make wrong assumptions on your behalf and run with them. They don't manage their
confusion, don't seek clarification, don't surface inconsistencies, don't push back.

- **Read what you're changing and the contract around it.** Never a remembered version.
- **Find what already does this, and where it belongs.** Before any code, write one
  placement line: the existing code that already does this job (or "none", with the search
  terms you used) and the module that owns the concept. Nobody can read the whole codebase,
  so this is a search, not a recollection; for anything past a one-file change, an Explore
  subagent runs it and the main thread keeps its answer. The question is pstack's `how` skill's,
  "where should this live" and "which package owns this" (`upstream/pstack/skills/how`); kstack
  carries that question alone, as the 2026-10-09 vote placed it (C051).
- **Build the impact set** — every reference to what you're touching: call sites, imports,
  subclasses, config keys, templates, fixtures, docs, migrations. Non-code counts.
- **Map it to tests** — which existing tests cover those references.
- **Name the data shape before the logic** — the structure that organizes it (a table, a
  state machine, a typed model). A new branch on an existing if-chain, or a second boolean
  kept in sync with the first, is the tell that one is missing.
- **Say what you think the request means, and surface what's unclear.** Surface tradeoffs.
  Push back if the ask is wrong. When the change touches state, the interpretation names
  **exactly one writer** for each piece of it — two owners is invisible in a diff, because
  each side looks correct alone.
- **A question you could settle by running something isn't a question.** Timing, output,
  layout, whether an approach works at all: build a throwaway in the scratchpad and let the
  result decide. Only product and taste calls go to the user.

Produces the **risk list** (references + their tests — VERIFY runs it, so it's an input,
not a note) and the **written interpretation** with its placement line (CONTAIN checks the
diff against it, so it has to exist as text).

**Satisfied when** the placement line is written, every reference is named or you can say
why the search was exhaustive, every ambiguity you noticed has been raised, and the
interpretation is written down.

Details: `references/impact.md`.

## 2 — SIMPLIFY · counters over-complication

Models overcomplicate code and APIs, bloat abstractions, and leave dead code behind —
a thousand lines where a hundred would do.

In this order, because simplifying something that should be deleted is the classic error:

1. **Should this exist? Run `/elon`** — it owns this question. Every requirement gets a named
   owner, and one whose owner is "the system" or "good practice" gets deleted rather than
   built. Anything that outputs a design runs through it, not just the large ones.
2. **Can existing code already do this?** Duplication is the measured signature of
   AI-written code, so reuse is the specific counter — check before writing. If you replace
   something that works anyway, name what the old one could do that the new one can't. Each
   is kept, or its loss is approved: by the person who asked, or under the operator's grant
   by a clean gate verdict whose review lanes were told of the loss. A capability lost by
   omission is a regression wearing the word "done" *(ours: reasoning, not measurement)*.
3. **Size the change to the code's condition.** Sound code takes the minimal change. When
   the change would sit *on top of* a defect rather than *in* it, the defect's layer is
   the change. Patching around bad structure is the same error as optimizing a part that
   should have been deleted.
4. **No bloat, and size is the signal.** Code volume is a near-perfect predictor of
   structural degradation, and more capable models produce *more* bloat rather than less —
   detailed prompting doesn't mitigate it. So compare what you wrote against what the job
   needed, mechanically, before judging it. Then: no features beyond the ask, no
   abstraction with one call site, no unrequested configurability, no forwarding wrapper.
5. **Leave nothing orphaned.** Dead code this change strands is part of this change.

**Satisfied when** the requirement has a name, reuse was checked and taken or refused with
a reason, the change sits at the layer its defect lives in, every new abstraction has two
call sites or a written reason, and nothing orphaned remains.

## 3 — CONTAIN · counters orthogonal damage

Models change or remove comments and code they don't sufficiently understand as side
effects, even when it's orthogonal to the task.

- **The diff contains only what the interpretation named.** It may grow — but only by
  going back and naming it first. Undeclared expansion is what's banned, not expansion.
- **Don't touch what you didn't read the reason for.** Comments, error handling, imports,
  names, formatting — if you don't know why it's there, it stays.
- **Record what you noticed; never fix it in this diff.** Unrelated problems go to the
  project's findings queue. In an unattended run they are the loop's next task: pstack's
  autonomous-run says "Mid-run discoveries are yours."
- **Never restructure and change behaviour in the same diff.** Restructuring done alongside
  other changes is measurably where bugs land, and they land as soon as the first change
  touches the restructured code. Two diffs, in either order.

**Satisfied when** every hunk traces to a named item, and everything noticed-but-unrelated
is written down somewhere else.

## 4 — VERIFY · counters unvalidated execution

Write the test before the code it checks — a test written against flawed code encodes the
flaw. But writing it first is not the verification. This is:

- **Run the risk list.** Every test covering every reference you named, not just the new
  one. Of everything here, this is the check with the most direct evidence behind it —
  one study, small sample, so treat it as the best available finding rather than a law.
- **Mutate the changed lines.** Break each on purpose and confirm something fails. A green
  suite is not evidence that your tests reach the semantics.
- **Run the whole thing, the way it is actually reached.** Not the unit, not a proxy — the
  full path, at real data volume, on the real device. "Should work" is the failure this
  check is named after. (The conditions half of this is judgment, not measurement.) When
  the project has a verify skill (`verify-<app>`), the drive goes through it, and the
  verdict is one of VERIFIED, NOT VERIFIED or INCONCLUSIVE from a baseline against the
  changed build. Inconclusive is never reported as a pass.
- **Judge the result against the interpretation, not against your tests.** Check 1 wrote
  down what this change was supposed to mean. Passing tests you wrote yourself is a weaker
  claim than doing the thing that was asked. A change can be locally correct and still not
  be the change.
- **Have someone other than the author check** when the risk list is wide.
- **Then the gate,** for a change that is to be merged (`references/gate.md`). Fresh agents re-run
  the checks at the exact commit, drive the real app, review the diff against `references/rules.md`
  in two or more lanes, and run the same scenario on main for comparison.

Running it is your job — boot it, drive it, read the logs. **Declaring it done is the gate's,
not the author's.** A change is done when `references/gate.md` returns a clean verdict from
agents that did not write it. With the operator's grant it merges on that verdict; without it,
present what you ran and what came back, and the person who asked decides. And when a
condition is out of reach — a deploy, production data volume,
the real device — say so plainly. "I couldn't reach it" quietly becoming "it passed" is the
failure this check is named after. (Judgment, not measurement.)

**Satisfied when** the risk list is green, every changed line has a mutant that something
catches, the whole path ran for real, the result matches the written interpretation, and the
evidence has been shown rather than summarized — with a green suite never the only
evidence.

Details: `references/verify.md`.

## When a fix isn't working

Two failed corrections on the same issue means stop. The context is polluted with failed
approaches and every further attempt is conditioned on them — revert to the last good
state, write down what was actually wrong rather than what you tried, and restart clean.

Before a third attempt, write down the premise both failed fixes shared — the one sentence
each of them assumed — and test the premise rather than writing another fix that assumes
it. When the imbalance sits with some actors and not others, count it per actor first: the
skew points at whatever assigns them that role.

A fix that creates new bugs sends you backward, not forward. It's a signal about the design,
not an invitation to patch again: return to check 1 and re-read what you're disturbing, then
to check 2 and ask whether the change is sitting at the wrong layer.

## 5 — AUTOMATE · a ratchet, not a gate

Runs last, never first. Automating a step that hasn't stabilized is the ordering error.
The ordering is borrowed; the thresholds below are judgment, not measurement.

- **Three times, then script it.** Anything that fired the same way three times becomes a
  script or a hook.
- **The impact query is the first candidate.** The evidence behind check 1 came from a
  tool, not an instruction — every step toward that compounds.
- **Invariants become mechanical checks.** A written invariant lies quietly; a check fails
  loudly.
- **A check you can rerun beats one you eyeballed.** The script that proves a change is
  the artifact a reviewer can run again; keep it where they can find it.
- **A correction made twice goes to `/correct`.** It turns the mistake class into a lint,
  a hook or a test, so the next change can't repeat it.
- **One concern per commit**, and checkpoint before anything risky. Two reasons for a
  change means two commits.

## Why these four

Each check answers a failure that was measured, not one that felt likely. Read
`references/evidence.md` when a rule looks arbitrary, or when you want to argue with one — it
holds the sources and states the strength of each.

**Where each rule's source is named.** A rule in this file is sourced when `references/evidence.md`
discusses it, or when its own line names a source or a reference that names one.
`references/rules.md`, `references/gate.md`, `references/prior-art.md` and the per-kind methods
name their sources at their top or at the rule. A rule with no source named anywhere is reasoning,
and the load-bearing ones say so at their own line. Keeping that distinction visible is the point,
because a rule claiming evidence it doesn't have is the same confident over-claim this skill exists
to catch.
