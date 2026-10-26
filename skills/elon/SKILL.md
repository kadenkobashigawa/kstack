---
name: elon
description: "Runs Musk's algorithm over a design before it is written down: question each requirement and name the person who owns it, delete every part that need not exist, then simplify what is left. Apply it to any structure, schema, API, workflow or skill about to be proposed, and to each part inside it. Use when the user types /elon, when a design is finished but not yet written, or when a structure has parts nobody has questioned."
---

# elon

Musk's five-step algorithm, run as written (Isaacson, 2023). The order matters most: the costly
error is simplifying or automating a part that should have been deleted (Isaacson, 2023).

1. **Make the requirements less dumb.** Question every requirement, and attach a name to
   each — a person, not a department. Requirements from smart people are the most dangerous,
   because nobody questions them (Isaacson, 2023).
2. **Delete the part or the process step.** Not "could this be smaller" — does it need to
   exist at all. People default to adding and overlook subtraction unless something cues
   them to consider it (Adams et al., 2021), and this step is the cue.

   **Delete until just right, not further** *(kstack: Musk over-deletes and adds back at least
   10% (Isaacson, 2023), because a factory part costs a part to restore. A cut from working code
   is a lost capability that someone approves under build's check 2, and that loss stands, so the
   trade inverts.)*
3. **Simplify or optimize.** Only now, and only what survived step 2.
4. **Accelerate cycle time.** Skipped for design work *(kstack: a manufacturing step)*.
5. **Automate.** Last. Automating an unstable design freezes it.

## Confirm against the artifact

Run the five steps first. Then **read the thing you just judged and list its parts from the
text**, not from what you remember of it. Name now anything you didn't name during the pass.

A model reading a long context uses its start and end best and drops the middle (Liu et al.,
2024), so a pass run from context can miss parts in the middle *(kstack: a safeguard for
running it)*.

## Output

Report the pass as: **what each requirement's owner turned out to be**, **what was deleted
and why**, and **what was added back**. A pass can delete nothing. When it does, name the
parts you tried to cut and what kept them, so the reader can see the pass ran.
