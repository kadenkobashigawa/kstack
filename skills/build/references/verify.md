# Verifying a change

Check 4's mechanics. The order below is by what each catches, not by cost.

## Run the risk list first

Check 1 gave you the tests covering every reference you're disturbing. Run those, not just
the test you wrote. It's the step with the strongest measured effect we found — from a
single study on a small sample, so weigh it accordingly.

A reference with no test covering it is a finding. Say so — don't let an absent test read
as a passing one.

## Mutate the changed lines

Break each changed line on purpose and confirm something fails. Coverage can't show this: at
Meta, about half the tests that caught a fault the existing suite missed added no line
coverage, so the suite had already run that line and passed.

Scope it to the lines you changed. Don't chase a global mutation score.

Practical forms: flip a comparison, swap a boundary, drop a clause, return a constant, skip
a side effect. If nothing fails, the assertion is decorative.

Mutation is one of the risky operations check 5 means — it deliberately breaks working code
and then restores it. Checkpoint first.

## Run the whole thing, and judge it against the interpretation

**Conditions.** Real data volume, the real path, the real device. A view that renders
nothing at real scale is a failure to investigate, not a passing check. Ask of every gate:
*can this actually reach the thing that would break, under the conditions it really runs
in?*

**Scope and acceptance.** Run the change the way it is actually reached — through the whole
path a person or caller takes to get to it — and judge the result against the written
interpretation from check 1, not against the tests you wrote. Those tests share your
misunderstanding if you had one; the interpretation is what the change was supposed to mean.

## Intent check on every test you kept

Tests written over existing code transcribe current behavior — bugs included — as
"expected". For each test, ask whether it asserts the **requirement** or replays the
**implementation**. Reject any test whose expected value was computed by the code under
test. Delete any test whose intent you can't state in one sentence.

This is why order matters: tests written before the code detect ~25% of faults, tests
written after flawed code ~14%.

**A test that would still pass if every function it calls returned `None` can't fail for a
defect.** Five shapes do that (from pstack's test-behavior-not-implementation, practice
rather than measurement):

- **Weak or no assertion** — only "is not None", "is truthy", "doesn't raise", "length > 0".
- **Mock or absence only** — only "was called", "wasn't called", "is empty".
- **Self-referential** — the expected value comes from the code under test.
- **Constant pin** — the assertion restates a hand-kept constant, default or prompt string.
- **Fixture asserts fixture** — the subject never runs inside the test body.

A new test calls the code the way its users do and asserts a literal expected value or an observable
effect. An existing test with the first, second, third or fifth shape is proved broken when a mutant
of the line it claims to guard survives it *(ours: pstack needs no mutant, since a test that still
passes with every call returning `None` "cannot fail for a defect"; the mutant is build's own check,
check 4 and rule 13)*. A constant pin is broken by its shape alone, whatever its mutants show, as
pstack has it: it restates a value the code holds, so it "observes no behavior and cannot fail for a
defect", and "A constant pin also fails when someone edits the constant or the prompt it restates,
so it prevents that edit." Fix a
broken test with pstack's remedies: "For an absence, assert the presence on the other input in the
same test. For a constant, test the mechanism that reads it", and "When no such assertion exists,
delete the test." A passing test of another shape that does catch its mutants stays: swapping it for
a "stronger" one is not a fix *(ours: the person refused that swap, and until 2026-10-10 this line
read "replacing a passing test is the user's call")*.

## Don't write these

Over-testing is over-complication wearing a lab coat:

- fixed line-coverage targets — past ~70% you're testing trivia and taxing refactors
- tests of private internals or call order — they break on refactor and catch nothing
- E2E beyond a small smoke set — slow, brittle, expensive to keep alive
- snapshots of anything nondeterministic
- known-failing tests left red — quarantine with a deadline or delete
- flaky tests treated as noise — a flake is a bug; never normalize "just re-run it"

## When the change touches an LLM call

Split it in two. The **deterministic half** — prompt construction, response parsing,
malformed-output repair, shape validation, retry and fallback control flow, persistence,
cost accounting — is tested with a fake at the project's own LLM wrapper, never at the
vendor SDK. Feed it canned bad outputs collected from real traces.

The **model-behavior half** — what the model actually returns — is scored, never asserted.
Exact-match assertions on live output are structurally flaky even at temperature zero.

## How sure are you

Every claim the change's safety rests on gets pushed as far down this ladder as is cheap,
and the report says where it stopped (from pstack's blast-radius, practice rather than
measurement):

1. You said so — worth nothing on its own.
2. You pointed at the line — a real `file:line`, or the library's own source.
3. You walked the bad case and showed it can't reach.
4. You ran it — a script or test calling the real code, failing loudly if you're wrong.
5. You reproduced it in the running app.

## A second pair of eyes

When the risk list is wide, the verifier should not be the author. Fresh context, briefed on
the interpretation from check 1, scoped to requirement gaps and contract violations — a
reviewer told to find problems always will, so bound what it's looking for.
