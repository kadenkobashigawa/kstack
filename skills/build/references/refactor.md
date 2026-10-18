# Changing structure without changing behaviour

Load this when the change reshapes code (rename, extract, inline, dedupe, move) and must not change
what it does. Adapted from pstack's refactoring playbook and its subtract-before-you-add,
minimize-reader-load and migrate-callers principles (Lauren Tan, MIT). Practice, not measurement.

A restructure is its own diff (SKILL.md, CONTAIN). If the cleanup turns up a bug or a missing
feature, pstack's refactoring playbook sets the order:
"split it out and ship the structural change first against the pinned contract."

1. **Pin the behaviour before anything moves.** A characterization test, a recorded output, or an
   equivalence script that captures what the code does today. Lint and type checks are not a pin.
   No coverage in the area means the pin gets written first.
2. **Name the target shape.** What the module layout and call graph would be if built today, and the
   structure the code is missing (a table, a state machine, a typed model). The reshape must delete
   branches or invalid states, not add a layer. When the shape is new to the codebase, check it
   against prior art first (`references/prior-art.md`). Where pstack's playbook runs architect when
   "the target crosses a function boundary", here `references/design.md` loads only when the target
   is a one-way door *(ours: the 2026-10-09 vote merged architect into `references/design.md` for
   one-way doors, and architect's design exploration runs on arena, parked until Claude Code can
   reach a second model family)*.
3. **Subtract before you add.** Delete dead code, collapse one-caller wrappers, drop redundant
   validators, remove orphaned references, then introduce the new shape.
4. **Move in small steps that each keep the pin green.** For an API reshape that no external user
   depends on, migrate every caller and delete the old API in the same change: no shim, no parallel
   old and new paths. Check every rename against strings, docs and back-references, which a symbol
   search misses.
5. **Prove behaviour unchanged on the real artifact.** For a larger reshape, an equivalence run
   (old vs new output diff, or a recorded baseline replayed against the new code). For a cosmetic-only
   change, polish's parse-tree proof is the gate.
6. **Keep it only if it's easier to read.** The measure is reader load: layers between a question and
   its answer, and hidden state a reader must hold. Can a new reader answer "where does X come from"
   and "what can change X" quickly? If the diff doesn't lower that somewhere, revert it.
7. **Order the commits.** "Rebase into small ordered commits. A subtraction commit, then the
   reshape, then any follow-on cleanup." Each one keeps the pin green before the next lands.

**Reply:** the structure that changed, the pin, the equivalence proof, the reader-load change, and
what was reverted.
