# Building the impact set

Check 1's output. The evidence: an AST-based code-test graph feeding *which tests to verify*
cut regressions from 6.08% to 1.82% on 100 instances; resolution moved little, dipping from
31% to 29% there and rising from 24% to 32% (six instances to eight) when a second model used
the graph as a skill. The same study found TDD prompting **alone** made regressions worse
(9.94%) — models benefit from context about what's at risk far more than from procedure
about how to work.

That is the most direct evidence behind any check in this skill. It is also one study on
125 instances with two local non-frontier models — the best finding available, not a law.
Do it before you write.

## What counts as a reference

Start from the symbol, file, or constant you're about to change, then find everything that
reaches it. Code is the easy half:

- direct callers, imports, re-exports
- subclasses, implementations, overrides
- anything matching by string where the language allows dynamic dispatch (getattr,
  reflection, dependency injection, route registries, plugin tables)

The half that gets missed, and where multi-file coherence failures are documented:

- config keys and environment variables, and every file that sets them
- templates, static assets, client-side code that names a server route or field
- test fixtures and factories
- database migrations, schema declarations, seed data
- documentation that states the behavior — a doc that now lies is a broken reference
- deployment files: compose, Dockerfile, CI config, infrastructure declarations

A documented failure: a constant moved from config to environment, with the compose file
left stale. Nothing in the code diff was wrong.

## Find the one fact it's safe because of

Listing callers is the easy half; grep does it in a second. Most changes that look risky
are safe because of a single fact ("this only drops cache entries that are already dead").
Find that fact, then prove it by running the real code, not by writing it up — a writeup
reads as convincing whether or not it's true. Then look where grep stops: the library's
own source at its pinned version, when things run (startup, teardown, a background
thread), and what a symbol search can't see (a JSON field a client reads, a database
column, a wire format, a feature flag, code three hops downstream). From pstack's
blast-radius skill; practice rather than measurement.

## Then map to tests

For each reference, find the tests that exercise it. That set is the **risk list**, and
check 4 runs it. If a reference has no test covering it, that is itself a finding — say so
rather than silently treating it as covered.

## When the search can't be exhaustive

Dynamic languages, string-keyed dispatch, and generated code all defeat a complete search.
The rule is not "find everything" — it's **name what you found and say why the search stops
where it does**. An honest boundary is usable; a silent one is not.

## Proportionality

A one-line fix to a private helper has an impact set of one file and its test. A change to a
shared constant has an impact set spanning config, deployment, and docs. The work scales
itself — don't inflate the small case, don't skip the large one.
