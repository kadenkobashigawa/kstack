---
name: correct
description: "Turns a mistake agents have made twice into a check that refuses it. In order of preference: an architecture change, a type, a hook or lint whose error names the fix, or a test, with a memory only for judgment calls. Proves each check against a real past instance and keeps the project's rule-to-enforcer table. Run it with /correct, optionally naming the mistake class. Claude proposes the command and cannot start it."
disable-model-invocation: true
argument-hint: "[a mistake class to start from]"
---

# correct

A correction in chat fixes one run. A rule in a memory or a CLAUDE.md fixes nothing when an agent
skips it (pstack, `skills/principle-encode-lessons-in-structure/SKILL.md`, l. 11). This skill
changes the project so the next agent can't make the mistake. Assume every contributor sees only the
files it opened, copies the nearest example, and takes the shortest path that works. "Design the
repo so a change that looks right from one file is right for the whole repo." (pstack,
`skills/correct/SKILL.md`, l. 11)

Adapted from pstack's correct skill and its encode-lessons-in-structure principle (Lauren Tan, MIT).
Practice, not measurement.

## 1. Find the mistake classes

Read what pstack names, "recent commits, reverts, review comments, agent instruction files, and
comments that explain workarounds" (pstack, `skills/correct/SKILL.md`, l. 15), scoped to this
project:

- recent commits in `git log`, and the reverts and fix-up commits among them,
- the gate's findings and a robovac pass's reports that the work session fixed, and the ones it
  dismissed with a disproof (a noisy lens is a class too, but a `consider` finding the person
  decided against is not noise, so leave it out), in place of review comments *(kstack, the
  translation: the projects here merge locally, so there is no PR to comment on)*,
- the agent instruction files: the CLAUDE.md files and the project's skills,
- comments in the code that explain a workaround,
- the feedback memories (the project's memory index, "How we work" first) and the user's corrections
  in this project's recent session transcripts *(kstack: they are where Claude Code keeps a
  correction)*.

Group them into classes. **A class counts once it has happened twice** (pstack,
`skills/correct/SKILL.md`, l. 15). Start from the class the user named, if any.

## 2. Fix each class at the highest level that works

1. **Architecture.** One owner per piece of state, one supported way per task, internals that can't
   be imported, one source of truth instead of hand-synced lists, and the old way deleted so nobody
   copies it (pstack, `skills/correct/SKILL.md`, l. 19).
2. **Types.** "Enforce it with types so the bad state can't be written. If bad code still compiles,
   add a lint or CI check whose error names the file, type, or function to use instead." (pstack,
   `skills/correct/SKILL.md`, l. 20)
3. **A mechanical check whose error names the fix.** A hook in the project's settings *(kstack: a
   Claude Code hook is a script that runs on the tool event where the mistake is made. It is
   deterministic, with no model in the loop, so it refuses the mistake before it lands)*, a lint
   rule, a CI step, or a guard at the boundary. If the pattern is already common, fail only when a
   change adds more of it (pstack, `skills/correct/SKILL.md`, l. 20).
4. **A test** that fails when the mistake is made, written the way build's `references/verify.md`
   requires: break the guarded line on purpose and the test fails *(kstack, the translation: pstack
   asks to "Test the behavior" (pstack, `skills/correct/SKILL.md`, l. 21), and build's mutation
   check is how kstack proves a test checks behavior)*. "Fix or delete any test that would still
   pass if every function it calls returned nothing." (pstack, `skills/correct/SKILL.md`, l. 21)
5. **A memory or a doc, last, and only for judgment calls** no check can express. Nothing fails when
   an agent skips it, so a rule that could be a check never stays prose (pstack,
   `skills/correct/SKILL.md`, l. 22). For a judgment call, "make the instruction more prominent and
   add an example of the failure mode" (pstack,
   `skills/principle-encode-lessons-in-structure/SKILL.md`, l. 17).

When a rule is already written down and the mistake happened again, that is a repeat. Fix it at a
higher level in the same change (pstack, `skills/correct/SKILL.md`, l. 30), and delete the prose
copy so the rule lives in one place (pstack,
`skills/principle-encode-lessons-in-structure/SKILL.md`, l. 16).

## 3. Prove and land it

"Then fix the most frequent classes now, one commit each." (pstack, `skills/correct/SKILL.md`,
l. 26) Here each class is one `/build` change, and committing it follows the project's usual rule
*(kstack: the translation of "one commit each", since each project here decides when work is
committed)*.

- Every check, hook or test is a code change and goes through `/build`.
- **Prove each new check fails on a real past instance** (pstack, `skills/correct/SKILL.md`, l. 26).
  Replay the mistake from git history or the transcript, and show the check refusing it. Then show
  it passing on correct work *(kstack: a check that refuses everything also refuses the past
  instance)*.
- **One command in both places.** "Run the same command locally and in CI." (pstack,
  `skills/correct/SKILL.md`, l. 26)
- An exception goes on the offending line with a reason, an expiry date and the user's approval
  (pstack, `skills/correct/SKILL.md`, l. 26).
- Show the user what you changed and the proof *(kstack: the user reviews what a run changed)*.

## 4. Keep the rule table

The project's workflow decision record, which CLAUDE.md points to, keeps one table. A project
without one keeps the table in CLAUDE.md itself *(kstack: pstack keeps it "in the agent
instruction file" (pstack, `skills/correct/SKILL.md`, l. 30). A project here names its decision
records in its own CLAUDE.md, and the table lives with them. The "Proved against" column is
kstack's, so each row carries its proof)*:

```
| Rule | Enforced by | Proved against |
|---|---|---|
| <the rule, one line> | <hook, lint, test or "judgment: memory <name>"> | <the past instance, sha or session date> |
```

"When the operator corrects you, fix the mistake and add the rule." (pstack,
`skills/correct/SKILL.md`, l. 30) A rule whose mistake can no longer happen is removed from the
table (pstack, `skills/correct/SKILL.md`, l. 30) and from wherever else it was written. A rule
enforced by nothing is either on its way up the ladder or marked judgment on purpose *(kstack:
judgment)*.

**Reply:** each class with its evidence, the level you fixed it at and why a higher one didn't work
(pstack, `skills/correct/SKILL.md`, l. 32), the proof, and the updated table rows.
