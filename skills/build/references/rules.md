# The code rules

What good code is held to. The unattended loop checks a slice against these rules, and a broken one
sends that slice through build's checks 1 to 5. The gate's review lanes hold every change to the same
rules, so a fix for one rule can't break another. Run them in this order: built well, then works,
then written true. A restructure goes first because it can delete the code a bug lives in, and docs
go last because they describe the code that results.

Most rules come from pstack's interrogate rubric and its code-quality approval bar (Lauren Tan, MIT,
`upstream/pstack/skills/interrogate/references/`). The rest come from the current sources linked at
each rule. Each rule had a named owner when it was kept (2026-10-10). Rules that nobody needed were
cut. Every approval-bar item kept a rule. These rubric items have none: type coercion, integer
overflow, string encoding, stale closures and dangling references (correctness); instructions where
structure would be better (root causes); abstraction level and coupling (structural integrity);
trusting the self-report of delegated or async work (verification); and whether the user
experience justifies the complexity (complexity budget).

## Built well

1. **No file pushed past 1,000 lines** without a very strong reason. [approval bar]
2. **No tangled growth.** No ad-hoc branching tangled into an existing flow, and no feature checks
   scattered across shared code. [approval bar]
3. **Nothing that buys nothing.** No wrapper, abstraction or cast that adds indirection without
   clarity. No abstraction with one call site, no option for a case that doesn't exist, no dead code.
   [approval bar, rubric: complexity budget]
4. **One concept, one place.** No duplicate of an existing helper, and logic in its canonical layer.
   Where an old path has no external consumers, don't keep it beside the new one: "If there are no
   external consumers, migrate callers and delete the old path in the same wave." [approval bar,
   rubric: structural integrity]
5. **Built in, not bolted on.** "If the new requirement had been known from the start, would the code
   look like this?" No incidental complexity that a restructure would delete. [rubric: structural
   integrity, approval bar]
6. **Validation at the boundary.** Validate data once where it enters the system, then trust it
   inside. [rubric: structural integrity]
7. **Data structures fit the access patterns.** "The right structure makes downstream code obvious."
   [rubric: structural integrity]
8. **No one-query-per-row loading (N+1).** Related rows load in a batch, not with one query per
   parent. Use the ORM's own loading options; for SQLAlchemy, [Relationship Loading
   Techniques](https://docs.sqlalchemy.org/en/21/orm/queryguide/relationships.html).

## Works

9. **Correct at the edges.** Empty and missing inputs, boundary values, swallowed errors, off-by-one
   and races. Trace the call chain that makes a bad value possible before claiming it. [rubric:
   correctness]
10. **State survives repetition and concurrency.** It is safe to run twice, and after a crash halfway.
    Shared mutable state is serialized by structure (locks, phases, exclusive ownership), not by
    conventions. [rubric: correctness]
11. **The root cause is fixed.** No guard that masks a broken invariant, no retry that hides a broken
    contract, no cast that silences a modelling error. [rubric: root causes vs. symptoms]
12. **No security holes.** No user input reaching SQL, a shell, eval or HTML unsanitized. No missing
    permission check, no secrets in code, logs or errors, no gap between check and use. Trace the
    input path for each finding. [rubric: security]
13. **Every guarantee line has a test that fails when it breaks.** Break the line on purpose; a mutant
    that survives is the gap. Tests check behaviour, not implementation. [rubric: verification;
    pstack test-behavior-not-implementation; mutation is build's own]
14. **Integrations are tested for real.** Check the real thing, not a proxy such as a cached state or
    a file's timestamp. [rubric: verification]
15. **No flaky tests, and no weakened assertions.** "If the bug is flaky, make the test deterministic
    where possible and document the signal being locked down." Don't weaken an existing assertion
    unless the expected behaviour has really changed. [pstack tdd]
16. **Dependencies are safe.** Pinned: lock files, and Docker and CI dependencies pinned by hash. No
    known vulnerabilities (check CVE, NVD and OSV), none unused, none unmaintained, all from official
    sources. [[OWASP A03:2025](https://owasp.org/Top10/2025/A03%5F2025-Software%5FSupply%5FChain%5FFailures/),
    [OpenSSF Scorecard](https://github.com/ossf/scorecard/blob/main/docs/checks.md)]
17. **Dev, CI and production run the same,** backing services included. CI tokens are read-only by
    default. [[twelve-factor: dev/prod parity](https://12factor.net/dev-prod-parity), OpenSSF
    Scorecard: Token-Permissions]

## Written true

18. **Every doc matches the code, and every cited claim matches its source.** That covers docstrings,
    `CLAUDE.md` files and decision records. Where a doc says X and the code does Y, quote both. A
    cited source that no longer supports its claim is a broken rule. [pstack why:
    "Doc vs. reality drift"]
