# The sketch step

A playbook calls this step when the change crosses a function boundary: `references/feature.md`
step 2, `references/bugfix.md` step 5, `references/refactor.md` step 3, and `references/perf.md`
step 4. pstack's trigger is poteto-mode's "Code crossing a function boundary → the **architect**
skill, parallel design exploration before implementing" (pstack, `skills/poteto-mode/SKILL.md`,
l. 22), and bug-fix's "If it crosses a function boundary, `architect` first." (pstack,
`skills/poteto-mode/playbooks/bug-fix.md`, l. 9) A change inside one function skips this step and
says so. The root runs it. Subagents sketch the candidates and review the sketch, and the root
picks the design and sorts the findings. Adapted from pstack's architect skill, its
design-red-flags reference and its exhaust-the-design-space and model-the-domain principles
(Lauren Tan, MIT). Practice, not measurement. `/elon` still runs first, because none of this
applies to a part that should not exist.

Architect's method: "Sketch types, function signatures, class shapes, and module boundaries with
`not implemented` bodies and pseudocode. Synthesize across multiple model perspectives, then fill in
code against the chosen sketch. If implementation proves the sketch wrong, throw it out and
redesign." (pstack, `skills/architect/SKILL.md`, l. 9) Check 1 (understand) has already read the
systems the change touches, which stands in for architect's Phase A, "Ground the problem" (pstack,
`skills/architect/SKILL.md`, l. 21) *(kstack: architect grounds with its how and why skills. kstack
has neither, and carries only how's placement question, which check 1's placement line asks)*. The
sections below then run in architect's order: shape the design, write the sketch, interrogate it,
build against it, and scrap it when it's wrong.

## Start from the caller

Write how the code will be used before what it does: the call site, the types it takes and returns,
the module it lives in. A design that reads awkwardly at its call site will be awkward everywhere.

## Name the data shape

Name it as check 1 says (`references/understand.md`), before writing any signature.

## Design it twice

Sketch two structurally different candidates and compare them on what each makes easy and hard to
change (pstack, `skills/architect/SKILL.md`, l. 35). One attempt locks in the first shape that came
to mind (mattpocock-skills, `skills/engineering/codebase-design/DESIGN-IT-TWICE.md`, l. 3). Do this
every time, even when the first candidate looks sufficient (pstack, `skills/architect/SKILL.md`,
l. 35). Architect takes its candidates from arena runners on two model families (pstack,
`skills/architect/SKILL.md`, ll. 31–33). Here two subagents, one Opus and one Sonnet, each sketch
a candidate from the same brief. The root reads both end to end, picks the base "on which
candidate a future maintainer can extend most easily without breaking invariants" (pstack,
`skills/arena/SKILL.md`, l. 49), and lists what the other does better. A fresh subagent folds that
list into the base, since the root writes no code *(kstack: Claude Code runs only Claude models, so
the two runners are Opus and Sonnet, a weaker spread than two model families. The gate's review
lanes use the same pair. Arena's rubric and cross-judge are not carried.)* When the shape is new
to this codebase, check each candidate against prior art (`references/prior-art.md`) before
choosing. Skip it when the design follows a pattern the codebase already uses (pstack,
`skills/poteto-mode/playbooks/prototype.md`, l. 8). The `researcher` agent runs that with a fresh
context, given this folder's `prior-art.md` path in its brief.

## Screen for red flags

Each of these is a reason to revise the shape, not a style note. The first eight are pstack's
design-red-flags list (pstack, `skills/architect/references/design-red-flags.md`, ll. 5–57). The
next three come from cursor-team-kit's strict code-quality review (cursor-team-kit,
`skills/thermo-nuclear-code-quality-review/SKILL.md`, ll. 95–109), and the last from pstack's
encode-lessons-in-structure principle.

- **Shallow module.** A big interface hiding little: callers coordinate several calls for one
  operation, or options expose internal stages.
- **Information leakage.** One internal decision (a representation, a policy, a wire format) appears
  in several modules, so changing it needs coordinated edits.
- **Temporal decomposition.** Modules split by execution order (load, validate, save) instead of by
  the decision each one hides, repeating one representation across the boundaries.
- **Pass-through method.** Forwards the same arguments to a method of the same shape and adds
  nothing.
- **Split ownership.** More than one module writes the same state or keeps its own copy of it.
- **Two ways to do one task.** Whichever way an agent finds first keeps gaining callers. Keep one,
  move the callers, delete the rest in the same change.
- **Importable internals.** A caller can reach inside the module, so internals become interface.
- **Hand-synced list.** The same items listed in two places. Derive one from the other, or make the
  build fail when they disagree.
- **Feature logic in a shared path.** A special case or one-off flag inside general-purpose code.
- **A file pushed past about 1,000 lines** by this change, when part of it could stand alone.
- **Partial updates.** Related writes that can leave state half-applied.
- **A source scan guarding a property of data flow.** A scan of the source is a lint. It fits a
  mechanical rule, "a fixed syntactic pattern, a banned API, an import shape, a file-location rule"
  (mattpocock-skills, `skills/engineering/retro/SKILL.md`, l. 19). A property of how data flows
  gets a structural mechanism, in pstack's order: "an unrepresentable state that cannot compile,
  then a lint or banned API that fails CI, then a canonical helper, then a runtime check" (pstack,
  `skills/principle-encode-lessons-in-structure/SKILL.md`, l. 19). A database constraint or a type
  is an unrepresentable state, and writers that all read one helper's value are a canonical helper.
  *(kstack: scans extended round after round missed the reviewer's next mutant, and a structural
  fix held in one round, per `references/evidence.md`, Run evidence behind the gate.)*

## Write the sketch

Write the chosen design as code before any logic: the types, the function signatures, the class
shapes and the module boundaries, each body `not implemented` (the language's own form, such as
`raise NotImplementedError`) or pseudocode. Architect's Outputs: "One file with new types and
signatures for small changes. Module map plus type definitions for larger work." (pstack,
`skills/architect/SKILL.md`, l. 83) From Phase C: "The synthesis can ship as its own commit"
(pstack, `skills/architect/SKILL.md`, l. 49).

## Interrogate the sketch

When the design is contested, or the change is hard to undo, put the sketch under adversarial review
before any body is filled in. Architect's Phase C: "For adversarial pressure on the design before
implementing, run the **interrogate** skill on the synthesized sketch." (pstack,
`skills/architect/SKILL.md`, l. 49) State the intent in one paragraph first, as interrogate's step 2
does (pstack, `skills/interrogate/SKILL.md`, ll. 23–32). Two read-only reviewers, one Opus and one
Sonnet, get the same prompt: the intent, the sketch's paths and `references/rules.md` as the rubric.
Interrogate: "The adversarial signal comes from model diversity, not assigned personas." (pstack,
`skills/interrogate/SKILL.md`, l. 9) The root sorts their findings into the gate's buckets
(`references/judgment.md`), with the sketch standing in for the diff. An act-on finding changes the
sketch before code is written. "The deliverable is a synthesized verdict. Do NOT auto-apply
changes." (pstack, `skills/interrogate/SKILL.md`, l. 11) Interrogate's default reviewers are two
model families (pstack, `skills/interrogate/SKILL.md`, ll. 38–41). *(kstack: Claude Code runs only
Claude models, so here they are Opus and Sonnet, the same pair as the gate's review lanes.)* The
"Contested design" trigger is poteto-mode's (pstack, `skills/poteto-mode/SKILL.md`, l. 24).
*(kstack: "hard to undo" joins it, because a one-way door is where a design finding costs most
after the code exists.)*

There is no human checkpoint by default. Architect's Phase C: "Default: proceed directly to
implementation with the synthesized design. No human checkpoint." (pstack,
`skills/architect/SKILL.md`, l. 45) A checkpoint happens only when the person asks for one.

## Build against the sketch, and scrap it when it's wrong

From architect's Phases D and E. "Replace `not implemented` bodies with code, pseudocode with logic.
The synthesized sketch is the contract." (pstack, `skills/architect/SKILL.md`, l. 55)

"Deviations from the sketch are signal worth surfacing, not friction to absorb silently. If a
function needs a parameter the sketch didn't anticipate, ask whether the sketch was wrong, the
requirement was missed, or the implementation is overreaching." (pstack,
`skills/architect/SKILL.md`, l. 57)

"If implementation keeps producing friction the sketch can't absorb, throw the sketch out." (pstack,
`skills/architect/SKILL.md`, l. 61) The signal is a pattern, not one instance. Architect's tells, in
short (pstack, `skills/architect/SKILL.md`, ll. 63–70):

- the same kind of workaround showing up again and again in unrelated code
- several unrelated edge cases that each need a special-case branch
- types that compile only through escape hatches (`any`, casts, optional fields always set)
- reaching for a lock when the design said the state wasn't shared
- callers that must know the abstraction's internal rules to use it
- two or more independent deviations of the same shape

"Use judgment. A few edge cases don't condemn an architecture." (pstack,
`skills/architect/SKILL.md`, l. 72) To scrap: re-read what has been built (check 1), redesign as if
the new constraints had been day-one assumptions, subtract before adding so the new design starts
smaller than the old, then design it twice again (above). *(kstack: architect re-runs its how skill
and then arena. kstack has no how skill and carries only its placement question, which check 1's
placement line in `references/understand.md` asks. Arena's runners are the Opus and Sonnet
candidates of Design it twice. This skill was born of a three-day build where "every fix
spawned new bugs" while the user and the agent held different architectures. That build showed
Phase E's signal, so the section is carried rather than dropped.)*

## Settle forks by experiment

If a question could be answered by running something (timing, output, layout, whether an approach
works at all), build a throwaway in the scratchpad and let the result decide. Only taste and product
calls go to the user. Visual variants go through impeccable.
