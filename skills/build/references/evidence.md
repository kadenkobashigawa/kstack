# The evidence behind each check

Read this when a rule looks arbitrary, or when you want to argue with one. The four checks
trace to something measured; the practice adopted from pstack is named as practice at the
end, and the load-bearing judgment calls say so at their own line.

## The four failure modes

Andrej Karpathy, 26 January 2026, after shifting from ~80% manual coding to ~80%
agent-driven over two months:

- **Unchecked assumptions** — *"The models make wrong assumptions on your behalf and just
  run along with them without checking. They don't manage their confusion, don't seek
  clarifications, don't surface inconsistencies, don't present tradeoffs, don't push back
  when they should."*
- **Over-complication** — *"They really like to overcomplicate code and APIs, bloat
  abstractions, don't clean up dead code... implement a bloated construction over 1000 lines
  when 100 would do."*
- **Orthogonal damage** — *"They still sometimes change/remove comments and code they don't
  sufficiently understand as side effects, even if orthogonal to the task."*
- **Unvalidated execution** — shipping without running it.

The four checks are one per pattern. That is the whole structure.

## Why it fires on every edit, including one-line fixes

Benchmarks measure whether an agent produces correct code for the current specification,
never whether that code stays extensible. Under repeated editing, each turn preserves and
extends the previous turn's anti-patterns, and round-local tests miss regressions against
still-active requirements. The small edit is where the decay compounds.
— SlopCodeBench, arXiv:2603.24755

## Check 1 — impact analysis

An AST-based code-test graph that tells the agent which tests to verify, on SWE-bench Verified
with Qwen3-Coder 30B (100 instances): test-level regressions 6.08% → 1.82%, while resolution
dipped 31% → 29% because the agent abstained more often. TDD prompting alone: 9.94%
regressions, worse than baseline. Given to a different model and agent as a skill
(Qwen3.5-35B-A3B with OpenCode, 25 instances), resolution rose 24% → 32%, six instances to
eight, with no regressions on either side. Contextual information beats procedural
instruction.
— TDAD, arXiv:2603.17973

**Weigh it honestly.** The regression result rests on 100 instances and one model,
Qwen3-Coder 30B. The resolution result rests on 25 instances and one other model,
Qwen3.5-35B-A3B, and a difference of two instances. Both models are local, both weaker than
the models running this skill. One study, one benchmark. It is the strongest evidence here and
it is not settled.

## Check 2 — reuse and simplicity

Across 211M changed lines: refactored ("moved") lines fell from 24.1% in 2020 to 9.5% in
2024, duplicated blocks rose eightfold, copy/paste +41%, and code revised within two weeks
of commit went from 3.1% to 5.7%. Duplication is the measurable signature of AI-written
code, which is why reuse is a specific counter rather than a style preference.
— GitClear

Note what this also rules out: a rule to *minimize* the diff reinforces the same pathology.
Refactoring collapsed while duplication rose. The right size is set by the code's condition.

## Check 2 — size as a signal

Code volume is a **near-perfect predictor of structural degradation** in LLM- and
agent-generated systems. Two findings from the same audit: a *Reasoning-Complexity
Trade-off*, where more capable models generate more bloated and more coupled code, and the
*Volume-Quality Inverse Law*. Neither functional correctness nor detailed prompting
mitigates the decay — which is why this is a measurement in the check rather than an
instruction to write concisely.
— AI-Generated Smells, arXiv:2605.02741

## Check 3 — restructuring is its own diff

Refactoring performed **in conjunction with other changes** ("floss refactoring") is
markedly more bug-prone, and bugs appear as soon as the first subsequent change lands on the
refactored code. Developers do not experience refactoring as behaviour-preserving; only
4–12% of refactoring operations happen in the week before a release, which reads as
deliberate risk avoidance.
— When Does a Refactoring Induce Bugs? (SCAM 2012); replication arXiv:2009.11685

## Check 4 — why green tests are not enough

Coverage does not show that tests reach the semantics. In Meta's mutation-guided test
generation, about half (49%) of the new tests that caught a fault every existing test missed
added no line coverage: the suite already ran that line and passed over the fault. Agents
fail the same way at the patch level: GPT-5 submitted a patch on every run and resolved 44%,
and confident wrong patches repeated run after run made up 68% of its failing runs (80% of
Llama 4's). Metamorphic and differential testing target the same class: programs that
compile and pass their tests yet produce the wrong result.
— "Mutation-Guided LLM-based Test Generation at Meta" (arXiv:2501.12862), Kaizen
(arXiv:2607.04058), "Confident and Wrong" (arXiv:2603.25764)

Tests written before the code detect ~25% of faults; tests written after flawed code detect
~14%, because they encode the same misunderstanding. Order matters; ceremony doesn't.
— arXiv:2607.05139

Judging the result against the written interpretation rather than against your own tests:
across 20,574 real developer-agent sessions, misalignment between what was asked and what
was delivered is a primary, distinct failure — separate from the code being wrong.
— arXiv:2605.29442

Running it at real data volume on the real device is **judgment, not measurement**. Nothing
we found measures it. It stays because a check that cannot reach the failure is not
evidence, and toy fixtures routinely cannot.

Author-is-not-verifier is classical separation of duties, formalized for agent teams as the
2+N pattern.
— arXiv:2606.20615

## Practice adopted from pstack

The per-kind references (`bugfix.md`, `refactor.md`, `design.md`, `measure.md`,
`long-run.md`), the placement line, the data-shape rule, the fork rule, the
five can't-fail test shapes, the proof ladder and the premise rule after two failed fixes are
adapted from Lauren Tan's pstack and Cursor's cursor-team-kit (both MIT, imported untouched under
`upstream/` in the repo that holds this skill). They are an experienced practitioner's
working rules, chosen by a three-judge vote on 2026-10-09, not measured findings. Each
reference says so at its top.

The one-writer rule in `SKILL.md` check 1 is build's own: it was in the skill before the port
(commit 6fceb9e). Pstack's architect design red flag "Split ownership" states the same rule
("Give each piece of state one owner"), so the two agree, but build did not take it from there.

## Where this skill came from

Born 2026-07-03 out of a three-day whack-a-mole build: the user and the agent shared the same UI
vision but held different architectures, so every fix spawned new bugs. That is the failure the
UNDERSTAND check and the two-strike rule exist to catch, and it is why an architecture
interpretation gets written down before code rather than after.

Project history rather than published measurement.
