## Check 5 (automate) scripts a step once it repeats, and never blocks a change

Automate last, never first. Automating a step that still changes from run to run is the error
this ordering prevents. The ordering is step 5 of Musk's algorithm as `/elon` runs it, "Automate.
Last. Automating an unstable design freezes it." (`skills/elon/SKILL.md`, l. 24) A script nobody
has written yet never holds a change back from the gate *(kstack: judgment)*.

- **Three times, then script it.** Turn a manual step you've done the same way three times into a
  script or a hook *(kstack: the count of three is judgment)*.
- **Nontrivial work builds the tool that does it or proves it** when the tool is what makes the
  work checkable: a codemod, a script, a generator (pstack,
  `skills/principle-build-the-lever/SKILL.md`, ll. 8, 15). "The bar is triviality, not
  repetition." (pstack, `skills/principle-build-the-lever/SKILL.md`, l. 21) The count of three
  applies to a step that comes back across changes. The tool applies to the work in front of you,
  so a one-off that only a script can prove gets its script now.
- **The impact search is the first candidate** *(kstack: judgment, since check 1 runs it on every
  change, so a script for it pays back soonest)*.
- **Invariants become mechanical checks.** An invariant is a rule that must always hold. One
  written in prose can go false without anyone noticing. A check fails where everyone can see
  it. pstack's encode-lessons-in-structure: "Encode recurring fixes in mechanisms (tools, code,
  metadata, automation) instead of textual instructions." (pstack,
  `skills/principle-encode-lessons-in-structure/SKILL.md`, l. 9)
- **A check you can rerun beats one you did by eye.** A reviewer can run the script that proves
  a change again, so keep it where they can find it. pstack's build-the-lever: "the tool is one
  artifact a reviewer can read and rerun to check the work." (pstack,
  `skills/principle-build-the-lever/SKILL.md`, l. 10)
- **A correction made twice goes to `/correct`.** Only the operator can type `/correct`, so propose
  it to them. It turns that kind of mistake into a lint, a hook or a test, so the next change can't
  repeat it. pstack's correct: "A class counts once it has happened twice." (pstack,
  `skills/correct/SKILL.md`, l. 15)
- **Commit a checkpoint before anything risky** *(kstack: judgment)*.
