# The code rules

What good code is held to. The unattended loop checks a slice against these rules, and the fix for a
broken one is a change that goes to its playbook (SKILL.md, Playbooks). A change's own review round
does not grade by them. Its reviewers get interrogate's break-it brief, which leaves out "style,
naming, structure, and risks that need a future change to matter" (pstack,
`skills/interrogate/SKILL.md`, l. 19). Structural problems get found and fixed here instead, one
per pass, as cursor-team-kit keeps its strict maintainability review in a skill of its own
(cursor-team-kit, `skills/thermo-nuclear-code-quality-review/SKILL.md`, l. 9). Run the rules in
this order: built well, then works, then written true. A restructure goes first because it can
delete the code a bug lives in, and docs go last because they describe the code that results
*(kstack: judgment)*.

The list was cut on 2026-10-10 from pstack's interrogate rubric and its code-quality approval bar,
to the rules someone needed *(kstack: who needed each rule was not recorded)*. pstack has since
deleted both files. The rules now cite where upstream keeps each one, mostly cursor-team-kit's
thermo-nuclear review and pstack's principle skills, and the other sources are listed in
`references/evidence.md`, References.

## Built well

1. **No file pushed past 1,000 lines** without a very strong reason (cursor-team-kit,
   `skills/thermo-nuclear-code-quality-review/SKILL.md`, l. 34).
2. **No tangled growth.** No ad-hoc branching tangled into an existing flow, and no feature logic
   scattered across shared code (cursor-team-kit,
   `skills/thermo-nuclear-code-quality-review/SKILL.md`, ll. 40–43, 62).
3. **Nothing that buys nothing.** No wrapper, abstraction or cast that adds indirection without
   clarity (cursor-team-kit, `skills/thermo-nuclear-code-quality-review/SKILL.md`, ll. 54, 57). No
   abstraction a single caller doesn't need, no option for a case that doesn't exist, no dead code
   (pstack, `skills/principle-foundational-thinking/SKILL.md`, l. 13;
   `skills/principle-subtract-before-you-add/SKILL.md`, ll. 3, 15–16).
4. **One concept, one place.** No duplicate of an existing helper, and logic in its canonical layer
   (cursor-team-kit, `skills/thermo-nuclear-code-quality-review/SKILL.md`, ll. 61–64). Where an old
   path has no external users, don't keep it beside the new one: "Migrate callers and delete the old
   API in the same wave instead of preserving compatibility layers." (pstack,
   `skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md`, ll. 3, 12)
5. **Built in, not bolted on.** "Redesign as if the requirement had been a foundational assumption
   from the start." (pstack, `skills/principle-redesign-from-first-principles/SKILL.md`, l. 9) No
   incidental complexity that a restructure would delete (cursor-team-kit,
   `skills/thermo-nuclear-code-quality-review/SKILL.md`, ll. 46–49).
6. **Validation at the boundary.** Validate data where it enters the system, then trust it inside
   (pstack, `skills/principle-boundary-discipline/SKILL.md`, ll. 9, 14–15).
7. **Data structures fit the access patterns.** "Define core types early, trace every access
   pattern, and choose structures that match the dominant paths." (pstack,
   `skills/principle-foundational-thinking/SKILL.md`, l. 11)
8. **No one-query-per-row loading (N+1).** Related rows load in a batch, not with one query per
   parent. Use the ORM's own loading options, such as SQLAlchemy's eager loading (SQLAlchemy,
   2026).

## Works

9. **Correct at the edges.** Null paths, races and off-by-one (mattpocock-skills,
   `docs/engineering/code-review.md`, l. 14), edge cases (pstack,
   `skills/principle-foundational-thinking/SKILL.md`, l. 13) and swallowed errors (pstack,
   `skills/principle-fix-root-causes/SKILL.md`, l. 17). Prove a bad value with a run against the
   real code before claiming it (pstack, `skills/interrogate/SKILL.md`, l. 19).
10. **State survives repetition and concurrency.** It is safe to run twice, and after a crash
    halfway (pstack, `skills/principle-make-operations-idempotent/SKILL.md`, l. 9). Shared mutable
    state is serialized by structure (lockfiles, sequential phases, exclusive ownership), not by
    conventions (pstack, `skills/principle-separate-before-serializing-shared-state/SKILL.md`,
    l. 9).
11. **The root cause is fixed.** No guard, retry, swallowed error, clamped value or discarded state
    that hides a bug (pstack, `skills/principle-fix-root-causes/SKILL.md`, l. 17), and no silent
    fallback over an unclear invariant (cursor-team-kit,
    `skills/thermo-nuclear-code-quality-review/SKILL.md`, l. 59).
12. **No security holes.** Review for security as well as correctness (cursor-team-kit,
    `skills/review-and-ship/SKILL.md`, l. 16). No user input reaching SQL, a shell, eval or HTML
    unsanitized (OWASP, 2025, A05). No missing permission check, since access is denied by
    default (OWASP, 2025, A01). No crypto keys in source code (OWASP, 2025, A04), and no
    sensitive data in logs (OWASP, 2025, A09) or error messages (OWASP, 2025, A10). A security,
    privacy, auth or permission-boundary finding is never skipped as noise (pstack,
    `skills/poteto-mode/references/bugbot-triage.md`, l. 79).
13. **Every guarantee line has a test that fails when it breaks.** Break the line on purpose. If no
    test fails, that is the gap *(kstack: mutation testing, as in `references/verify.md`)*. Tests
    check behaviour, not implementation (pstack,
    `skills/principle-test-behavior-not-implementation/SKILL.md`, ll. 9, 13–14).
14. **Integrations are tested for real.** Check the real thing, not a proxy such as a cached state
    or a file's timestamp (pstack, `skills/principle-prove-it-works/SKILL.md`, ll. 11–15).
15. **No flaky tests, and no weakened assertions.** "If the bug is flaky, make the test
    deterministic where possible and document the signal being locked down." (pstack,
    `skills/tdd/SKILL.md`, l. 33) Don't weaken an existing assertion unless the expected behaviour
    has really changed (pstack, `skills/tdd/SKILL.md`, l. 31).
16. **Dependencies are safe.** Pinned: lock files, and Docker and CI dependencies pinned by hash. No
    known vulnerabilities (check CVE, NVD and OSV), none unused, none unmaintained, all from
    official sources (OWASP, 2025, A03; OpenSSF, 2026, Pinned-Dependencies).
17. **Dev, CI and production run the same,** backing services included. CI tokens are read-only by
    default (Wiggins, 2017; OpenSSF, 2026, Token-Permissions).

## Written true

18. **Every doc matches the code, and every cited claim matches its source.** That covers
    docstrings, `CLAUDE.md` files and decision records. Where a doc says X and the code does Y,
    quote both. A cited source that no longer supports its claim is a broken rule. pstack's why
    skill flags "Doc vs. reality drift" (pstack, `skills/why/references/sources/notion.md`, l. 42).
