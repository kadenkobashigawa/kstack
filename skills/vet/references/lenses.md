# The two lenses

Each reviewer is one review lane, as pstack's autopilot-full runs them and build's gate ports: "Run
the audit as two or more review lanes with the full brief. Give each lane one main focus, such as
consumer parity with trunk, lifetimes and races, or data and config safety." Both lanes hold the
range to the same rubric, build's code rules in the build skill's `references/rules.md` (`../../build/references/rules.md`
from this file), all 18
of them, and report each finding by its rule number. A lane's lens is its main focus: it says where
the lane looks hardest, never which rules it may skip. Each gets the range as two exact SHAs, the
stated intent and the CI result, and reports findings in the shape at the bottom, or "no findings".
The ways to look come from pstack's interrogate rubric and code-quality lens and cursor-team-kit's
thermo-nuclear review (MIT). Practice, not measurement.

*(ours: the focus is split by rules, structure on Sonnet and correctness on Opus as the gate staffs
its lanes, where interrogate gives every reviewer "the same prompt and rubric" because "The
adversarial signal comes from model diversity, not assigned personas." The 2026-10-09 vote chose the
split: "split lenses on fresh Claude contexts replace model diversity" (C025,
judge B's verdict). Two Claude models are weaker diversity
than two model families, as build's `references/gate.md` says of its own lanes.)*

Both lanes: trace before you claim. A finding names `file:line` and the rule it breaks, and shows
why it is a problem, not only that it is. Read the project's CLAUDE.md invariants and the decision
record that covers the files first; a pattern the codebase uses on purpose is not a defect.

## structure: rules 1 to 8 and 18

**Does this already exist?** (rule 4) For each new function, class, route, query, helper or
constant, search for something that already does the job: grep the key identifiers and their
synonyms, the SQL table names, the route paths, the error strings, and similar call shapes. Name the
existing helper and where it lives.

**Is it in the right place?** (rules 2, 4 and 6) Check the change against the project's layering
(its architecture or layers decision record, if it has one) and its ownership rules (for example,
"repositories own SQL").

**Is there a simpler shape?** (rules 1, 3, 5 and 7) Look for the restructure that deletes complexity
rather than moving it, and screen with the red flags in build's `references/design.md`.

**Do the docs still tell the truth?** (rule 18) Read the module docstrings and their Methods lists,
the function docstrings, and the CLAUDE.md claims and decision records that describe the changed
code, and check any source a claim cites. A claim of fact in a decision record that cites nothing
and isn't common knowledge is a finding too, filed under rule 18. *(ours, from vet's first version:
rule 18 holds a cited claim to its source, and an uncited one has no source to hold it
to, so this lens files it as rule 18's extension rather than let it pass unchecked.)*

## correctness: rules 9 to 17

**Does it do what the intent says?** (rules 9 to 11) When a finding depends on a value being
possible, trace the call chain that makes it possible; a hypothetical the callers can't produce is
not a finding.

**Security.** (rule 12) For each finding, trace the input path: user input reaching SQL, a shell, a
template or a file path, or an endpoint or query that skips the project's visibility or permission
check.

**Blast radius past grep.** (rules 9 and 10) What the change breaks that a symbol search won't
show: a JSON field a client reads, a database column, a migration that edits shipped history, a
config key set elsewhere, a background thread, startup and shutdown order.

**Tests.** (rules 13 to 15) Break a changed line in your head and ask which test would fail; hold
any new test to the can't-fail check in build's `references/verify.md`, which also says when a
passing test stays. Changed behaviour that nothing would catch is a finding, with the cheapest check
that would catch it.

## Finding shape

```
### <severity: critical | warning | nit> · <short title>
**rule:** <number from rules.md; an uncited decision-record claim files as 18>
**where:** <file:line or function>
**finding:** <what is wrong>
**evidence:** <how you know: the trace, the grep, the run; quote the code>
**fix:** <what to do instead, at the right layer> (optional)
```

`critical`: a bug, data loss, a security hole, or behaviour that is fundamentally broken. `warning`:
a design or maintainability problem that will cause pain. `nit`: style or naming. Zero findings is a
valid review; say "no findings" and stop.
