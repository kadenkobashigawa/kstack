## Check 1 (understand) counters unchecked assumptions

Models make wrong assumptions on your behalf and act on them without checking. They don't notice
when they're confused, don't ask for clarification, don't point out inconsistencies, and don't push
back (Karpathy, 2026).

- **Read what you're changing and the contract around it**, meaning what its callers expect of
  it. Read the current file, never a version you remember.
- **Find what already does this, and where it belongs.** Before writing code, write one line, the
  placement line. It names the existing code that already does this job (or "none", with the search
  terms you used) and the module that owns the concept. Nobody can read the whole codebase, so find
  these by searching, not from memory. For anything bigger than a one-file change, an Explore
  subagent runs the search and hands its answer back to the root. The question comes from
  pstack's `how` skill, "where should this live" and "which package owns this" (pstack,
  `skills/how/SKILL.md`, l. 3). *(kstack: kstack takes only that question from the skill, not its
  subsystem walkthroughs.)*
- **Build the impact set.** It holds every reference to what you're touching: call sites,
  imports, subclasses, config keys, templates, fixtures, docs and migrations. References outside
  the code count too.
- **Map it to tests.** List the existing tests that cover those references.
- **Name the data shape before writing the logic.** The data shape is the structure that organizes
  the data (a table, a state machine, a typed model). A new branch on an existing if-chain, or a
  second boolean kept in sync with the first, is the sign that the code lacks one (pstack,
  `skills/poteto-mode/SKILL.md`, l. 21; `skills/principle-model-the-domain/SKILL.md`, l. 9).
- **Say what you think the request means, and raise what's unclear.** Raise tradeoffs. Push
  back if the request is wrong. When the change touches state, the interpretation names
  **exactly one writer** for each piece of it. A second writer doesn't show in a diff, because
  each writer's code looks correct on its own.
- **If running something can settle a question, run it instead of asking**, as SKILL.md,
  Autonomy, says.

This check produces two things, and every playbook writes both at its first step. The **risk
list** is the references plus their tests. Check 4 (verify) and the gate run it, so treat it as an
input, not a note. The **written interpretation** carries the placement line. Check 3 (contain) and
the gate judge the diff against it, so it has to exist as text.

**Satisfied when** the placement line is written, every reference is named or you can say why
the search was exhaustive, you have raised every ambiguity you noticed, and the interpretation
is written down.

## Build the impact set before you write

Building the impact set gives check 1 its risk list. The search follows pstack's blast-radius
skill, which finds what a change breaks beyond the diff (pstack, `skills/blast-radius/SKILL.md`,
ll. 1–35). Its cost scales with the change, as the last section says.

### Let the impact set set the size of the work

A one-line fix to a private helper has an impact set of one file and its test. A change to a
shared constant has an impact set spanning config, deployment and docs. Don't inflate the small
case, and don't skip the large one.

### Count references outside the code

Start from the symbol, file, or constant you're about to change, then find everything that
reaches it. Code is the easy half:

- direct callers, imports, re-exports
- subclasses, implementations, overrides
- anything matching by string where the language allows dynamic dispatch (getattr,
  reflection, dependency injection, route registries, plugin tables)

The half that gets missed (pstack, `skills/blast-radius/SKILL.md`, l. 35, for what a
symbol search can't see; the rest is kstack practice):

- config keys and environment variables, and every file that sets them
- templates, static assets, client-side code that names a server route or field
- test fixtures and factories
- database migrations, schema declarations, seed data
- documentation that states the behavior, since a doc that now lies is a broken reference
- deployment files: compose, Dockerfile, CI config, infrastructure declarations

For example, a constant moves from config to an environment variable and the compose file still
sets the old one. Nothing in the code diff is wrong *(kstack: an illustration, not a cited case)*.

### Find the one fact it's safe because of

Listing callers is the easy half, and grep does it in a second. Most changes that look risky are
safe because of a single fact ("this call only drops already-dead cache entries and does nothing
else"). Find that fact, then prove it by running the real code, not by writing it up. A writeup
reads as convincing whether or not it's true. Then look where grep stops: the library's own source
at its pinned version, when things run (startup, teardown, a background thread), and what a symbol
search can't see (a JSON field a client reads, a database column, a wire format, a feature flag,
code three hops downstream). This section is practice rather than measurement, from pstack's
blast-radius skill (pstack, `skills/blast-radius/SKILL.md`, ll. 13–35).

### Map each reference to its tests

For each reference, find the tests that exercise it. That set is the **risk list**, and
check 4 runs it. A reference with no test covering it is itself a finding. Say so rather than
treating it as covered.

### Say where a search that can't be exhaustive stops

Dynamic languages, string-keyed dispatch, and generated code all defeat a complete search.
The rule is to **name what you found and say why the search stops where it does**. An honest
boundary is usable. A silent one is not.
