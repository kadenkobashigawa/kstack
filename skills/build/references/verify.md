## Check 4 (verify) counters unvalidated execution

Write the test before the code it checks, because a test written to fit flawed code checks for the
flaw (pstack, `skills/tdd/SKILL.md`, ll. 17–18). Writing it first still isn't verification.
Verification is these steps:

- **Run the risk list.** Run every test covering every reference you named, not only the new test.
- **Mutate the changed lines.** Break each on purpose and confirm something fails. A passing suite
  doesn't prove the tests check what those lines do (Foster et al., 2025).
- **Run the whole thing, the way it runs for real.** Run the full path, at real data volume, on
  the real device, not the unit or a stand-in. The failure this check is named after is
  "should work" (pstack, `skills/principle-prove-it-works/SKILL.md`, l. 9). When the
  project has a verify skill (`verify-<app>`), use it to drive the app the way a user would. It
  compares a baseline build with the changed build and returns VERIFIED, NOT VERIFIED or
  INCONCLUSIVE. Never report INCONCLUSIVE as a pass.
- **Judge the result against the interpretation, not against the change's own tests.** Check 1
  wrote down what this change should mean. Passing the writer's own tests is a weaker claim than
  doing the thing that was asked. A change can be correct on its own terms and still not be the
  change that was asked for (Boehm, 1984).
- **The writer never verifies its own change.** A fresh subagent writes the code, the root
  verifies it, and the gate checks it again (Sadowski et al., 2018).
- **The gate is the independent check,** and every playbook ends on it (`references/gate.md`).
  Fresh agents that wrote none of the change re-run the checks at the exact commit and drive the
  real app. They review the diff against `references/rules.md` in two or more lanes, and run the
  same scenario on main to compare.

The root runs the change: it boots the app, drives it and reads the logs, or reads the captured
evidence of a subagent that did. **Declaring it done is the gate's job, not the root's or the
writer's.** A change is done when `references/gate.md` returns a clean verdict from agents that did
not write it. A clean verdict merges into local main under the standing grant (SKILL.md, Autonomy).
A change the operator named, or asked to see first, stops at merge-ready, with what ran and what
came back. When a condition is out of reach, such as a deploy, production data volume or the real
device, say so. The failure this check is named after is "I couldn't reach it" quietly turning into
"it passed" *(kstack: judgment, not measurement)*.

**Satisfied when** the risk list is green, every changed line has a mutant that something
catches, the whole path ran for real, the result matches the written interpretation, and you
have shown the evidence rather than summarized it. A passing suite is never the only evidence.

## Verify a change in this order

These are check 4's mechanics, ordered by what each catches, not by cost.

### Run the risk list first

Check 1 gave you the tests covering every reference you're disturbing. Run those, not just the
new test.

A reference with no test covering it is a finding. Say so. Don't let an absent test read as a
passing one.

### Mutate the changed lines

Break each changed line on purpose and confirm something fails. Coverage can't show this: at Meta,
about half the tests that caught a fault the existing suite missed added no line coverage, so the
suite had already run that line and passed (Foster et al., 2025).

Scope it to the lines you changed. Don't chase a global mutation score.

Practical forms: flip a comparison, swap a boundary, drop a clause, return a constant, skip
a side effect. If nothing fails, the assertion is decorative.

Mutation is one of the risky operations check 5 means, since it breaks working code on purpose
and then restores it. Commit a checkpoint first.

### Run the whole thing, and judge it against the interpretation

**Conditions.** Real data volume, the real path, the real device. A view that renders
nothing at real scale is a failure to investigate, not a passing check. Ask of every check:
*can this actually reach the thing that would break, under the conditions it really runs
in?*

**Scope and acceptance.** Run the change the way it is actually reached, through the whole path
a person or caller takes to get to it. Judge the result against the written interpretation from
check 1, not against the change's own tests. Those tests share the writer's misunderstanding if it
had one. The interpretation is what the change was supposed to mean.

### Intent check on every test you kept

Tests written over existing code transcribe current behavior, bugs included, as "expected". For each
test, ask whether it asserts the **requirement** or replays the **implementation**. Reject any test
whose expected value was computed by the code under test. Delete any test whose intent you can't
state in one sentence.

**A test that would still pass if every function it calls returned `None` can't fail for a defect.**
Five shapes do that. They are practice rather than measurement, from pstack's
test-behavior-not-implementation (pstack,
`skills/principle-test-behavior-not-implementation/SKILL.md`, ll. 15–21):

- **Weak or no assertion.** It checks only "is not None", "is truthy", "doesn't raise" or
  "length > 0".
- **Mock or absence only.** It checks only "was called", "wasn't called" or "is empty".
- **Self-referential.** The expected value comes from the code under test.
- **Constant pin.** The assertion restates a hand-kept constant, default or prompt string.
- **Fixture asserts fixture.** The subject never runs inside the test body.

Judge each test this way (pstack, `skills/principle-test-behavior-not-implementation/SKILL.md`,
ll. 11–23):

- **A new test** calls the code the way its users do and asserts a literal expected value or an
  observable effect.
- **An existing test with shape 1, 2, 3 or 5** is broken when a mutant of the line it guards
  survives it *(kstack: pstack needs no mutant, since such a test "cannot fail for a defect". The
  mutant is build's own check, check 4 and rule 13)*.
- **A constant pin** is broken by its shape alone. It restates a value the code holds, so it
  observes no behavior, and it blocks a legitimate edit to that value (l. 11, l. 13).
- **Fix a broken test** by asserting the presence on the other input (for an absence), or by
  testing the mechanism that reads the constant (for a pin). When no such assertion exists, delete
  the test (l. 23).
- **A passing test of another shape that catches its mutants stays.** Swapping it for a "stronger"
  one is not a fix *(kstack: the person refused that swap, and until 2026-10-10 this line read
  "replacing a passing test is the user's call")*.

### Don't write these

Over-testing is over-complication. Each of these costs upkeep and catches little:

- fixed line-coverage targets, which tax refactors *(kstack: judgment)*
- tests of private internals or call order, which break on refactor and catch nothing (pstack,
  `skills/principle-test-behavior-not-implementation/SKILL.md`, l. 9)
- E2E beyond a small smoke set, which is slow, brittle and expensive to keep alive (Wacker, 2015)
- snapshots of anything nondeterministic
- known-failing tests left red, which get quarantined with a deadline or deleted *(kstack:
  judgment)*
- flaky tests treated as noise, since a flake is a bug, so never normalize "just re-run it"
  *(kstack: judgment)*

### When the change touches an LLM call

Split it in two. The **deterministic half** is prompt construction, response parsing,
malformed-output repair, shape validation, retry and fallback control flow, persistence and cost
accounting. Test it with a fake at the project's own LLM wrapper, never at the vendor SDK (Freeman
et al., 2004). Feed it canned bad outputs collected from real traces.

The **model-behavior half** is what the model actually returns. Score it, never assert it.
Exact-match assertions on live output are structurally flaky even at temperature zero (Anthropic,
2026).

### How sure are you

Every claim the change's safety rests on gets pushed as far down this ladder as is cheap, and the
report says where it stopped. The ladder is practice rather than measurement, from pstack's
blast-radius (pstack, `skills/blast-radius/SKILL.md`, ll. 21–27):

1. You said so. Worth nothing on its own.
2. You pointed at the line: a real `file:line`, or the library's own source.
3. You walked the bad case and showed it can't reach.
4. You ran it: a script or test calling the real code, failing loudly if you're wrong.
5. You reproduced it in the running app.

### Bound what an independent reviewer looks for

The writer is a subagent and the root verifies, so the verifier is never the author, and the gate
adds reviewers that saw neither. Brief every reviewer the same way: fresh context, the
interpretation from check 1, and a scope of requirement gaps and contract violations. A reviewer
told to find problems always will, so bound what it's looking for (pstack,
`skills/interrogate/references/lead-judgment.md`, l. 20).
