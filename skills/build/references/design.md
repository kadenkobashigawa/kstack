# Designing a change that is hard to undo

Load this for a one-way door: a new module boundary, a schema, a public interface, anything other code
will build on. Adapted from pstack's architect skill, its design-red-flags reference and its
exhaust-the-design-space and model-the-domain principles (Lauren Tan, MIT). Practice, not measurement.
`/elon` still runs first: none of this applies to a part that should not exist.

## Start from the caller

Write how the code will be used before what it does: the call site, the types it takes and returns,
the module it lives in. A design that reads awkwardly at its call site will be awkward everywhere.

## Name the data shape

Pick the structure that organizes the logic before writing the logic: a table or registry over a
branch chain, a state machine over scattered booleans, a typed model over repeated shape assumptions.
**The tell that one is missing:** a new branch on an existing if-chain, or a second boolean kept in
sync with the first.

## Design it twice

For a one-way door, sketch two structurally different candidates and compare them on what each makes
easy and hard to change. One attempt locks in the first shape that came to mind. For a mechanical
change whose shape is already obvious, skip this and say so. Check each candidate against prior art
(`references/prior-art.md`) before choosing; the `researcher` agent runs that with a fresh context, given
this folder's `prior-art.md` path in its brief.

## Screen for red flags

Each of these is a reason to revise the shape, not a style note. The first eight are pstack's
design-red-flags list; the last three come from cursor-team-kit's strict code-quality review.

- **Shallow module.** A big interface hiding little: callers coordinate several calls for one
  operation, or options expose internal stages.
- **Information leakage.** One internal decision (a representation, a policy, a wire format) appears
  in several modules, so changing it needs coordinated edits.
- **Temporal decomposition.** Modules split by execution order (load, validate, save) instead of by
  the decision each one hides, repeating one representation across the boundaries.
- **Pass-through method.** Forwards the same arguments to a method of the same shape and adds nothing.
- **Split ownership.** More than one module writes the same state or keeps its own copy of it.
- **Two ways to do one task.** Whichever way an agent finds first keeps gaining callers. Keep one,
  move the callers, delete the rest in the same change.
- **Importable internals.** A caller can reach inside the module, so internals become interface.
- **Hand-synced list.** The same items listed in two places. Derive one from the other, or make the
  build fail when they disagree.
- **Feature logic in a shared path.** A special case or one-off flag inside general-purpose code.
- **A file pushed past about 1,000 lines** by this change, when part of it could stand alone.
- **Partial updates.** Related writes that can leave state half-applied.

## Build against the design, and scrap it when it's wrong

From architect's Phases D and E. The chosen design is the contract the code is written against.
Architect's "sketch" is its design written as "types, function signatures, class shapes, and module
boundaries", with placeholder bodies. Here the sketch is the design the method above chose: the call
site, the data shape and the module boundary, written down before the code.

"Deviations from the sketch are signal worth surfacing, not friction to absorb silently. If a
function needs a parameter the sketch didn't anticipate, ask whether the sketch was wrong, the
requirement was missed, or the implementation is overreaching."

"If implementation keeps producing friction the sketch can't absorb, throw the sketch out." The
signal is a pattern, not one instance. Architect's tells, in short:

- the same kind of workaround showing up again and again in unrelated code;
- several unrelated edge cases that each need a special-case branch;
- types that compile only through escape hatches (`any`, casts, optional fields always set);
- reaching for a lock when the design said the state wasn't shared;
- callers that must know the abstraction's internal rules to use it;
- two or more independent deviations of the same shape.

"Use judgment. A few edge cases don't condemn an architecture." To scrap: re-read what has been
built (check 1), redesign as if the new constraints had been day-one assumptions, subtract before
adding so the new design starts smaller than the old, then design it twice again (above).
*(ours: architect re-runs its how skill and then arena. kstack has no how skill and carries only its
placement question, which check 1's placement line in SKILL.md asks; arena is parked. The section
is carried rather than dropped because this skill was born of a three-day build where "every fix
spawned new bugs" while the user and the agent held different architectures, which is Phase E's
signal.)*

## Settle forks by experiment

If a question could be answered by running something (timing, output, layout, whether an approach
works at all), build a throwaway in the scratchpad and let the result decide. Only taste and product
calls go to the user. Visual variants go through impeccable.
