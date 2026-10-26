# Changing structure without changing behaviour

Load this when the change reshapes code (rename, extract, inline, dedupe, move) and must not change
what it does. Adapted from pstack's refactoring playbook and its subtract-before-you-add,
minimize-reader-load and migrate-callers principles (Lauren Tan, MIT). Practice, not measurement.

"**You own the contract. The structure changes. The behavior does not.**" (pstack,
`skills/poteto-mode/playbooks/refactoring.md`, l. 3) The root plans, reviews and verifies, and fresh
subagents investigate and write, as in pstack's bug-fix playbook: "Delegate investigation and the
fix to subagents, stay in the lead." (pstack, `skills/poteto-mode/playbooks/bug-fix.md`, l. 3) The
refactoring playbook delegates its edits the same way, "with a specific scope (file paths, the names
being moved, the behavior to hold)" (pstack, `skills/poteto-mode/playbooks/refactoring.md`, l. 11).
SKILL.md, Subagents, holds the rule. Each step below names the check in SKILL.md it carries out and
who does it.

A restructure is its own diff (check 3, `references/contain.md`). If the cleanup turns up a bug or a
missing feature, pstack's refactoring playbook sets the order: "split it out and ship the structural
change first against the pinned contract." (pstack, `skills/poteto-mode/playbooks/refactoring.md`,
l. 5) The same line allows a redesign: "A redesign is allowed, but name it and route to Feature."
(pstack, `skills/poteto-mode/playbooks/refactoring.md`, l. 5) A target shape that changes what the
code does is a redesign. Name it, and run it through `references/feature.md`.

1. **Learn the contract.** pstack: "Run the **how** skill over the affected subsystem to learn the
   contract" (pstack, `skills/poteto-mode/playbooks/refactoring.md`, l. 7). Carries out check 1
   (understand), `references/understand.md`: the placement line, the impact set and its tests (the
   risk list), and the written interpretation, which names the structure that moves and states that
   behaviour holds. For anything bigger than a one-file change, an Explore subagent runs the search,
   and the root writes the results. *(kstack: kstack has no how skill. Check 1 carries the contract
   reading, and of how it takes only the placement question.)*
2. **Pin the behaviour before anything moves.** A characterization test, a recorded output, or an
   equivalence script that captures what the code does today. Lint and type checks are not a pin.
   No coverage in the area means the pin gets written first. Carries out check 4 (verify), its first
   rule: the test comes before the code it checks. A subagent writes the pin, and the root confirms
   it passes on the code as it stands.
3. **Name the target shape.** Name the structure the code is missing (a table, a state machine, a
   typed model). "Boring code stays when the shape is already clear and local." (pstack,
   `skills/poteto-mode/playbooks/refactoring.md`, l. 8) The reshape must delete branches or invalid
   states, not add a layer (pstack, `skills/poteto-mode/playbooks/refactoring.md`, l. 8). Then state
   what the module layout and call graph would be if built today (pstack,
   `skills/poteto-mode/playbooks/refactoring.md`, l. 9).
   Carries out check 2 (simplify). The root names the shape. pstack's playbook runs architect when
   "the target crosses a function boundary" (pstack, `skills/poteto-mode/playbooks/refactoring.md`,
   l. 9). Here `references/design.md`, the sketch step, runs first. Its subagents sketch two
   candidates *(kstack: `references/design.md`, Design it twice, says why it runs on Opus and
   Sonnet)*, and it checks a shape new to the codebase against prior art
   (`references/prior-art.md`). *(kstack: judgment. This step merges pstack's steps 2 and 3, which
   name the missing structure and then the target shape.)*
4. **Subtract before you add.** Delete dead code, collapse one-caller wrappers, drop redundant
   validators, remove orphaned references, then introduce the new shape (pstack,
   `skills/poteto-mode/playbooks/refactoring.md`, l. 10). The smallest change that reaches the
   target shape ships, and a speculative cleanup that "might help" gets reverted (pstack,
   `skills/poteto-mode/playbooks/refactoring.md`, l. 10). Carries out check 2 (simplify), nothing
   orphaned. A fresh subagent writes the subtraction, and the root reviews the diff.
5. **Move in small steps that each keep the pin green.** For an API reshape, migrate every caller
   and delete the old API in the same change. No shim, and no parallel old and new paths. Check
   every rename against the files themselves, because a rename misses uses in strings, docs and
   back-references (pstack, `skills/poteto-mode/playbooks/refactoring.md`, l. 11). The same-change
   rule holds when no external user depends on the old API (pstack,
   `skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md`, l. 18). Carries out check 3
   (contain): the diff moves structure and nothing else. A fresh subagent writes the edits from a
   brief with the fields in SKILL.md, The brief, whose SCOPE names the file paths and the names
   being moved and whose ACCEPTANCE names the behaviour to hold, and the root reviews the diff.
6. **Prove behaviour unchanged on the real artifact.** For a larger reshape, run an equivalence
   check: diff old output against new, replay a recorded baseline against the new code, or make a
   smoke run on the matching surface (pstack, `skills/poteto-mode/playbooks/refactoring.md`,
   l. 12). The smoke run drives the changed path through the project's `verify-<app>` skill when it
   has one *(kstack, the translation: the project's verify skill in place of pstack's control
   skill)*. For a cosmetic-only change to Python files, polish's proof script is the equivalence
   proof. It compares each file's parse tree before and after the edit, with comments and
   docstrings stripped. Run it with `snapshot` before the edit and `verify` after it:
   `$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../polish/scripts/proof.py` *(kstack: polish already
   ships this proof for cosmetic edits, and its parser covers only Python)*. Carries out check 4
   (verify). The root verifies.
7. **Keep it only if it's easier to read.** The measure is reader load (pstack,
   `skills/poteto-mode/playbooks/refactoring.md`, l. 13): layers between a question and its answer,
   and hidden state a reader must hold. Can a new reader answer "where does X come from" and "what
   can change X" quickly (pstack, `skills/principle-minimize-reader-load/SKILL.md`, l. 23)? If the
   diff doesn't lower that somewhere, revert it. Carries out check 2 (simplify). The root judges.
8. **Order the commits.** "Rebase into small ordered commits. A subtraction commit, then the
   reshape, then any follow-on cleanup." (pstack, `skills/poteto-mode/playbooks/refactoring.md`,
   l. 14) Each one keeps the pin green before the next lands. The root orders the commits, one
   concern per commit.
9. **Run the gate (`references/gate.md`).** pstack: "Run **Opening a PR**." (pstack,
   `skills/poteto-mode/playbooks/refactoring.md`, l. 14) The gate is the independent check that
   check 4 (verify) ends on. The root starts it and runs its checks, and fresh agents that did not
   write the change run its other lanes on the refactor's own local branch. A clean verdict merges
   into local main under the standing grant (SKILL.md, Autonomy). A change the operator named, or
   asked to see first, stops at merge-ready. *(kstack, the translation: kstack merges local
   branches, so Opening a PR, with its PR text and its forge, has no counterpart here. The gate is
   the step where a change leaves its author.)*

**Reply:** the structure that changed, the pin, the equivalence proof, the reader-load change, what
shipped and what was reverted, and "No new behavior." (pstack,
`skills/poteto-mode/playbooks/refactoring.md`, l. 16) Then the branch and the gate's verdict, or the
merge commit.
