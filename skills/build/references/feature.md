# Building a feature

Load this when the change adds behaviour. Adapted from pstack's feature playbook and the
poteto-mode rules it leans on (Lauren Tan, MIT, `upstream/pstack/skills/poteto-mode/`). Practice,
not measurement.

"**You own the design. Plan, review, verify.** Delegate implementation. Stay in the lead." (pstack,
`skills/poteto-mode/playbooks/feature.md`, l. 3) The root plans, reviews and verifies, and fresh
subagents write the code (SKILL.md, Subagents). Each step below names the check in SKILL.md it
carries out and who does it.

1. **Read the affected subsystem.** pstack: "`how` over the affected subsystem." (pstack,
   `skills/poteto-mode/playbooks/feature.md`, l. 5) Carries out check 1 (understand): the placement
   line, the impact set and the tests that cover it (the risk list), the data shape, and the written
   interpretation. For anything bigger than a one-file change, an Explore subagent runs the search
   and hands its answer back, and the root writes the results. *(kstack: pstack runs its how skill
   here. kstack has no how skill, and takes from it only the placement question, which check 1's
   placement line asks.)*
2. **Sketch it first when it crosses a function boundary.** pstack: "`architect` for parallel design
   exploration." (pstack, `skills/poteto-mode/playbooks/feature.md`, l. 6) Carries out check 2
   (simplify): `/elon` decides whether each part should exist and reuse is checked. Then
   `references/design.md` designs it twice and writes the chosen sketch, signatures with
   not-implemented bodies, before any code. It interrogates the sketch only when the design is
   contested or hard to undo. The root runs `/elon` and picks the design, and subagents sketch the
   candidates. A change inside one function skips the sketch and says so. *(kstack: pstack's feature
   playbook runs architect at this step every time. Here it runs on poteto-mode's own trigger, the
   condition `references/bugfix.md` and `references/refactor.md` use.)* That trigger is "Code
   crossing a function boundary" (pstack, `skills/poteto-mode/SKILL.md`, l. 22).
3. **Write the throughput checkpoint.** pstack: "Write the throughput checkpoint as four todo items.
   A dimension that genuinely does not apply (single file, no fan-out) keeps its item with `n/a:
   <reason>` rather than being dropped" (pstack, `skills/poteto-mode/playbooks/feature.md`, l. 7).
   Carries out check 3 (contain), since each workstream's diff holds only what the interpretation
   named, and check 1's one-writer rule. The root writes it.
   - **Blocking first steps.** "Gates run before fan-out." (pstack,
     `skills/poteto-mode/playbooks/feature.md`, l. 8)
   - **Independent workstreams.** "Disjoint files, services, or layers parallelize. Shared writes
     serialize." (pstack, `skills/poteto-mode/playbooks/feature.md`, l. 9) A workstream that is a
     self-contained change is its own branch (`references/gate.md`, The unit of work).
   - **Shared mutable state.** "Default to splitting the target" (pstack,
     `skills/poteto-mode/playbooks/feature.md`, l. 10), per pstack's
     separate-before-serializing-shared-state principle. "Serialize only for real invariants."
     (pstack, `skills/poteto-mode/playbooks/feature.md`, l. 10)
   - **Smallest safe decomposition.** "If one worker is best, name why." (pstack,
     `skills/poteto-mode/playbooks/feature.md`, l. 11)
4. **Delegate the code to a fresh subagent.** pstack: "Delegate code-writing to a subagent ... with
   a specific scope (file paths, named data shape and its organizing structure ..., chosen before
   the delegate writes logic, and success criteria)." (pstack,
   `skills/poteto-mode/playbooks/feature.md`, l. 12) Carries out check 2 (simplify) and check 3
   (contain) through that scope, and check 4 (verify) through its first rule, since the delegate
   writes the test before the code it checks. The subagent writes, and the root reviews.
   - **The brief** points at files rather than pasting them, and carries the written
     interpretation and the risk list from step 1 *(kstack: check 3 judges the diff against the
     interpretation and check 4 runs the risk list, so the writer needs both)*.
   - **The model.** A change that alters behaviour goes to Opus, and a trivial mechanical edit to
     Sonnet. pstack's default feature model is `grok-4.7-xhigh-fast`, and poteto-mode sends
     "Trivial mechanical edits" to the fast code model (pstack, `skills/poteto-mode/SKILL.md`,
     l. 95). *(kstack: Claude Code runs only Claude models, and SKILL.md, Subagents, gives any
     change that alters behaviour to Opus.)*
   - **More than one valid shape.** pstack: "When the implementation admits multiple valid shapes
     (error handling, abstraction layer, test structure), delegate via the **arena** skill instead."
     (pstack, `skills/poteto-mode/playbooks/feature.md`, l. 12) Here two delegates, one Opus and one
     Sonnet, write it from the same brief. The root picks the base and lists what the other did
     better. A fresh subagent folds that list in, as `references/design.md`, Design it twice,
     does for a sketch *(kstack: kstack has no arena skill)*.
   - **No skipping it.** "Mandatory: no skip-with-reason escape, and Laziness Protocol does not
     override it (the gain is review separation, not lines saved). A subagent forbidden to spawn
     satisfies this by owning the diff directly with the same review separation. No "standing by"
     reply that waits on a nested agent." (pstack, `skills/poteto-mode/playbooks/feature.md`, l. 12)
   - **How it writes.** Comments follow the project's own comment rules, where pstack has "Comments
     per **Comments**" (pstack, `skills/poteto-mode/playbooks/feature.md`, l. 12). "Surgical edits,
     re-ground against the source for upstream-derived files. Port shared-primitive improvements to
     all consumers and verify each. Commit liberally." (pstack,
     `skills/poteto-mode/playbooks/feature.md`, l. 12)
   - **The root reviews the diff.** poteto-mode: "You own every subagent's work. Review the diff and
     write your own summary, don't pass through what it said." (pstack,
     `skills/poteto-mode/SKILL.md`, l. 97)
5. **Verify on the matching surface.** pstack: "Verify on the matching surface. "Inconclusive" or
   wrong-surface is not a pass. Flag it." (pstack, `skills/poteto-mode/playbooks/feature.md`, l. 13)
   Carries out check 4 (verify): run the risk list, mutate the changed lines, drive the whole path
   the way it runs for real (the project's `verify-<app>` skill when it has one), and judge the
   result against the written interpretation. INCONCLUSIVE is never reported as a pass. The root
   verifies, and reads a subagent's captured evidence rather than its summary.
6. **Order the commits.** pstack: "Rebase into small, ordered commits. Stack follow-ups. Use the
   **sequence-verifiable-units** principle skill, building, verifying, and committing each small
   unit before the next." (pstack, `skills/poteto-mode/playbooks/feature.md`, ll. 14–15) The root
   orders the commits, one concern per commit. A follow-up is its own branch off main, and one that
   overlaps this change waits for it to merge *(kstack, the translation: in place of stacking)*.
   `references/gate.md` takes this from autopilot-full, "Run owners in true parallel and never
   stack" (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 7).
7. **Interrogate a contested design.** pstack: "If the design is contested, `interrogate` before
   shipping." (pstack, `skills/poteto-mode/playbooks/feature.md`, l. 16) Run it only when step 2
   did not already interrogate the sketch, so a design is interrogated once. pstack
   interrogates the built change here, and architect's interrogation of the sketch is optional
   (pstack, `skills/architect/SKILL.md`, l. 49), so pstack can run both. *(kstack: a second pass
   repeats what the sketch's reviewers already sorted, and the gate still reviews the built
   change.)* Carries out
   check 4 (verify), whose reviewers never wrote the change. It runs over the built change the way
   `references/design.md`, Interrogate the sketch, runs over a sketch. Two read-only reviewers, one
   Opus and one Sonnet, get `references/rules.md` as the rubric, and the root sorts their findings
   into the gate's buckets (`references/judgment.md`).
8. **Run the gate (`references/gate.md`).** pstack: "Run **Opening a PR**." (pstack,
   `skills/poteto-mode/playbooks/feature.md`, l. 17) The gate is the independent check that check 4
   (verify) ends on, run on the feature's own local branch. The root starts it and runs its checks,
   and fresh agents that did not write the change run its other lanes. A clean verdict merges into
   local main under the standing grant (SKILL.md, Autonomy). A change the operator named, or asked
   to see first, stops at merge-ready. *(kstack, the translation: kstack merges local branches, so
   Opening a PR, with its PR text and its forge, has no counterpart here. The gate is the step where
   a change leaves its author.)*

"Code-coupled work (one feature, one migration) goes to a single owner with the checkpoint inline.
That owner fans out internally after the blocking phase. Parent-level fan-out is for slices that
produce independent artifacts (audits, cross-subsystem investigations, competing experiments).
Rewrite the checkpoint at phase boundaries. Spawn a fresh owner rather than chaining interrupts."
(pstack, `skills/poteto-mode/playbooks/feature.md`, l. 19) *(kstack: the root does every fan-out,
so it sees all the work, as SKILL.md, Subagents, says.)*

**Reply:** "what you built, what you chose and why, the throughput checkpoint, open decisions.
Tables for design alternatives." (pstack, `skills/poteto-mode/playbooks/feature.md`, l. 21) Then
the branch and the gate's verdict, or the merge commit *(kstack, the translation: in place of
pstack's PR link)*.
