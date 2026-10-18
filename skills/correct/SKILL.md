---
name: correct
description: Find the mistakes agents keep repeating in this project and make each one impossible rather than remembered. Tries architecture first, then types, then a hook or lint whose error names the fix, then a test, and writes a memory or doc only for judgment calls. Proves each new check fails on a real past mistake and keeps a rule-to-enforcer table. Use when the user types /correct, when the same correction has been given twice, or when vet keeps filing the same class of finding.
disable-model-invocation: true
argument-hint: "[a mistake class to start from]"
---

# correct

A correction in chat fixes one run. A rule in a memory or a CLAUDE.md fixes nothing when an agent
skips it, and compliance falls as a session grows long. This skill changes the project so the next
agent can't make the mistake: assume every contributor sees only the files it opened, copies the
nearest example, and takes the shortest path that works. pstack: "Design the repo so a change that
looks right from one file is right for the whole repo."

Adapted from pstack's correct skill and its encode-lessons-in-structure principle (Lauren Tan, MIT).
Practice, not measurement.

## 1. Find the mistake classes

Read what pstack names, "recent commits, reverts, review comments, agent instruction files, and
comments that explain workarounds", scoped to this project:

- recent commits in `git log`, and the reverts and fix-up commits among them,
- vet's findings that ended `fixed`, and the ones dismissed as noise (a noisy lens is a class too;
  a `consider` finding dismissed by the person's decision is not noise, so leave it out), in place
  of review comments *(the translation: the projects here merge locally, so there is no PR
  to comment on)*,
- the agent instruction files: the CLAUDE.md files and the project's skills,
- comments in the code that explain a workaround,
- the feedback memories (the project's memory index, "How we work" first) and the user's corrections
  in this project's recent session transcripts *(ours: they are where Claude Code keeps a
  correction)*.

Group them into classes. **A class counts once it has happened twice.** Start from the class the user
named, if any.

## 2. Fix each class at the highest level that works

1. **Architecture.** One owner per piece of state, one supported way per task, internals that can't be
   imported, one source of truth instead of hand-synced lists, and the old way deleted so nobody copies
   it.
2. **Types.** pstack: "Enforce it with types so the bad state can't be written. If bad code still
   compiles, add a lint or CI check whose error names the file, type, or function to use instead."
3. **A mechanical check whose error names the fix.** A hook in the project's settings (on the tool
   event where the mistake happens) *(ours: a Claude Code hook runs a script on the tool event where
   the mistake is made, deterministic, with no model in the loop, so it refuses the mistake before
   it lands)*, a lint rule, a CI step, or a guard at the boundary. If the pattern is already common,
   fail only when a change adds more of it.
4. **A test** that fails when the mistake is made, written the way build's `references/verify.md`
   requires (it must be able to fail).
5. **A memory or a doc, last, and only for judgment calls** no check can express. Nothing fails when
   an agent skips it, so a rule that could be a check never stays prose. For a judgment call,
   encode-lessons says: "make the instruction more prominent and add an example of the failure
   mode".

When a rule is already written down and the mistake happened again, that is a repeat: fix it at a
higher level in the same change, and delete the prose copy so the rule lives in one place.

## 3. Prove and land it

pstack: "Then fix the most frequent classes now, one commit each." Here each class is one `/build`
change, and committing it follows the project's usual rule *(ours: the translation of "one commit
each", since each project here decides when work is committed)*.

- Every check, hook or test is a code change and goes through `/build`.
- **Prove each new check fails on a real past instance**: replay the mistake from git history or the
  transcript, show the check refusing it, then show it passing on correct work.
- **One command in both places.** pstack: "Run the same command locally and in CI."
- An exception goes on the offending line with a reason, an expiry date and the user's approval.
- Show the user what you changed and the proof.

## 4. Keep the rule table

The project's workflow decision record (find it from CLAUDE.md; else CLAUDE.md itself) keeps one
table *(ours: pstack keeps it "in the agent instruction file"; a project here names its decision
records in its own CLAUDE.md, and the table lives with them)*:

```
| Rule | Enforced by | Proved against |
|---|---|---|
| <the rule, one line> | <hook, lint, test or "judgment: memory <name>"> | <the past instance, sha or session date> |
```

pstack: "When the operator corrects you, fix the mistake and add the rule." A rule whose mistake can
no longer happen is removed from the table and from wherever else it was written. A rule enforced by
nothing is either on its way up the ladder or marked judgment on purpose.

**Reply:** each class with its evidence, the level you fixed it at and why a higher one didn't work,
the proof, and the updated table rows.
