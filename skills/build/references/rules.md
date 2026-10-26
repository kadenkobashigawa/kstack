# The code rules

What good code is held to. The unattended loop checks a slice against these rules, and the fix for a
broken one is a change that goes to its playbook (SKILL.md, Playbooks). The gate's review lanes hold
every change to all of these rules, so a fix for one rule is checked against the others. Run them in
this order: built well, then works, then written true. A restructure goes first because it can
delete the code a bug lives in, and docs go last because they describe the code that results
*(kstack: judgment)*.

Most rules come from pstack's interrogate rubric and its code-quality approval bar (Lauren Tan, MIT,
`upstream/pstack/skills/interrogate/references/`). The rest come from the sources cited at each
rule, listed in `references/evidence.md`, References. The list was cut on 2026-10-10 to the rules
someone needed *(kstack: who needed each rule was not recorded)*. Every approval-bar item kept a
rule. These rubric items have none: type coercion, integer overflow, string encoding, stale
closures and dangling references (correctness); instructions where structure would be better
(root causes); abstraction level and coupling (structural integrity); trusting the self-report of
delegated or async work (verification); and whether the user experience justifies the complexity
(complexity budget).

## Built well

1. **No file pushed past 1,000 lines** without a very strong reason (pstack,
   `skills/interrogate/references/code-quality-review.md`, l. 43).
2. **No tangled growth.** No ad-hoc branching tangled into an existing flow, and no feature checks
   scattered across shared code (pstack, `skills/interrogate/references/code-quality-review.md`,
   l. 43).
3. **Nothing that buys nothing.** No wrapper, abstraction or cast that adds indirection without
   clarity (pstack, `skills/interrogate/references/code-quality-review.md`, ll. 29, 43). No
   abstraction with one call site, no option for a case that doesn't exist, no dead code (pstack,
   `skills/interrogate/references/rubric.md`, ll. 61–63).
4. **One concept, one place.** No duplicate of an existing helper, and logic in its canonical layer
   (pstack, `skills/interrogate/references/code-quality-review.md`, l. 43). Where an old path has no
   external consumers, don't keep it beside the new one: "If there are no external consumers,
   migrate callers and delete the old path in the same wave." (pstack,
   `skills/interrogate/references/rubric.md`, l. 41)
5. **Built in, not bolted on.** "If the new requirement had been known from the start, would the
   code look like this?" (pstack, `skills/interrogate/references/rubric.md`, l. 40) No incidental
   complexity that a restructure would delete (pstack,
   `skills/interrogate/references/code-quality-review.md`, l. 43).
6. **Validation at the boundary.** Validate data once where it enters the system, then trust it
   inside (pstack, `skills/interrogate/references/rubric.md`, l. 36).
7. **Data structures fit the access patterns.** "The right structure makes downstream code obvious."
   (pstack, `skills/interrogate/references/rubric.md`, l. 39)
8. **No one-query-per-row loading (N+1).** Related rows load in a batch, not with one query per
   parent. Use the ORM's own loading options, such as SQLAlchemy's eager loading (SQLAlchemy,
   2026).

## Works

9. **Correct at the edges.** Empty and missing inputs, boundary values, swallowed errors, off-by-one
   and races. Trace the call chain that makes a bad value possible before claiming it (pstack,
   `skills/interrogate/references/rubric.md`, ll. 9–12, 17).
10. **State survives repetition and concurrency.** It is safe to run twice, and after a crash
    halfway. Shared mutable state is serialized by structure (locks, phases, exclusive ownership),
    not by conventions (pstack, `skills/interrogate/references/rubric.md`, ll. 14–15).
11. **The root cause is fixed.** No guard that masks a broken invariant, no retry that hides a
    broken contract, no cast that silences a modelling error (pstack,
    `skills/interrogate/references/rubric.md`, ll. 25–27).
12. **No security holes.** No user input reaching SQL, a shell, eval or HTML unsanitized. No missing
    permission check, no secrets in code, logs or errors, no gap between check and use. Trace the
    input path for each finding (pstack, `skills/interrogate/references/rubric.md`, ll. 72–77).
13. **Every guarantee line has a test that fails when it breaks.** Break the line on purpose. If no
    test fails, that is the gap *(kstack: mutation testing, as in `references/verify.md`)*. Tests
    check behaviour, not implementation (pstack, `skills/interrogate/references/rubric.md`, l. 49;
    `skills/principle-test-behavior-not-implementation/SKILL.md`, l. 9).
14. **Integrations are tested for real.** Check the real thing, not a proxy such as a cached state
    or a file's timestamp (pstack, `skills/interrogate/references/rubric.md`, ll. 52–53).
15. **No flaky tests, and no weakened assertions.** "If the bug is flaky, make the test
    deterministic where possible and document the signal being locked down." (pstack,
    `skills/tdd/SKILL.md`, l. 33) Don't weaken an existing assertion unless the expected behaviour
    has really changed (pstack, `skills/tdd/SKILL.md`, l. 31).
16. **Dependencies are safe.** Pinned: lock files, and Docker and CI dependencies pinned by hash. No
    known vulnerabilities (check CVE, NVD and OSV), none unused, none unmaintained, all from
    official sources (OWASP, 2025; OpenSSF, 2026, Pinned-Dependencies).
17. **Dev, CI and production run the same,** backing services included. CI tokens are read-only by
    default (Wiggins, 2017; OpenSSF, 2026, Token-Permissions).

## Written true

18. **Every doc matches the code, and every cited claim matches its source.** That covers
    docstrings, `CLAUDE.md` files and decision records. Where a doc says X and the code does Y,
    quote both. A cited source that no longer supports its claim is a broken rule. pstack's why
    skill flags "Doc vs. reality drift" (pstack, `skills/why/references/sources/notion.md`, l. 42).
