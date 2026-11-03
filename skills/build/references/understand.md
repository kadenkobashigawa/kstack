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
  `skills/poteto-mode/SKILL.md`, l. 22; `skills/principle-model-the-domain/SKILL.md`, l. 9).
- **Say what you think the request means, and raise what's unclear.** Raise tradeoffs. Push
  back if the request is wrong. When the change touches state, the interpretation names
  **exactly one writer** for each piece of it. A second writer doesn't show in a diff, because
  each writer's code looks correct on its own.
- **If running something can settle a question, run it instead of asking**, as SKILL.md,
  Autonomy, says.
- **Research before any design** when the change reaches the sketch step (`references/design.md`),
  or when the next step is "finding something out from outside the working directory"
  (mattpocock-skills, `docs/engineering/research.md`, l. 11). The `researcher` agent answers one
  narrow question in a note it writes itself (`references/prior-art.md`, The research note). Matt's
  implement-spec has its exploration subagent save notes so that implementers "focus on
  implementation rather than exploration" (mattpocock-skills,
  `skills/engineering/implement-spec/SKILL.md`, l. 25). Every later brief names the note's path,
  because "Nothing loads a past research file automatically." (mattpocock-skills,
  `docs/engineering/research.md`, l. 49) *(kstack: per `references/evidence.md`, Run evidence
  behind the gate, where research that came after round 6 found what six findings had missed.)*
- **Write the live checks before the code.** For a change someone can reach by running it, write
  each live check now, as one user flow with a concrete scenario and its pass condition, and declare each in the ledger
  with `gate.py record live-check <id> --note <scenario and pass condition>` (`references/gate.md`,
  the live lane). The gate refuses a live PASS until every declared check is VERIFIED. pstack's
  multi-phase-plan writes each live lane up front as "one box with a concrete scenario, the
  screenshot it saves, and its pass predicate" (pstack,
  `skills/poteto-mode/playbooks/multi-phase-plan.md`, l. 13). The gate's live lane drives this list
  (`references/gate.md`). *(kstack: per `references/evidence.md`, Run evidence behind the gate,
  where a defect present from early rounds was first driven in round 7.)*

### Where the research note goes, and how long it lasts

Matt's research skill saves the note "where the repo already keeps such notes; match the existing
convention, and if there is none, put it somewhere sensible and say where." (mattpocock-skills,
`skills/engineering/research/SKILL.md`, l. 12) The root reads that convention from the project on
each run, and kstack names no project's folder. Where the project has none, the root asks the person
once, and the answer goes into the project's `CLAUDE.md` *(kstack: the operator's call, so the next
run reads the place instead of asking again)*.

Before any brief points at the note, the root follows two or three of its links. Matt's docs call
the citations "Your only protection", and a link that lands "on a summary of the thing rather than
the thing" means the run failed (mattpocock-skills, `docs/engineering/research.md`, l. 45).

A note holds short-lived facts, true "as of this week" (mattpocock-skills,
`docs/engineering/research.md`, l. 21). Once the change merges, a decision that should outlast it
moves into a tracked file the project already uses, such as its design doc or a rules file, and the
note is archived: "ADRs yes. Everything else archive or delete after done." (mattpocock-skills,
`docs/engineering/research.md`, l. 41) A later change starts a new note rather than trusting an old
one.

### What the check leaves behind

This check produces two things, and every playbook writes both at its first step. The **risk
list** is the references plus their tests. Check 4 (verify) and the gate run it, so treat it as an
input, not a note. The **written interpretation** carries the placement line. Check 3 (contain) and
the gate judge the diff against it, so it has to exist as text. When they apply, it also leaves the
research note's path, which later briefs name, and the live checks, which the gate's live lane
drives.

**Satisfied when** the placement line is written, every reference is named or you can say why
the search was exhaustive, you have raised every ambiguity you noticed, and the interpretation
is written down. When the change needs them, the research note exists and its links were followed,
and the live checks are written.

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
