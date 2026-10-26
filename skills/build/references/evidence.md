# The evidence behind each check

Read this when a rule looks arbitrary, or when you want to argue with one. Each section says what a
check rests on: a measured result, pstack's practice, or kstack's judgment. Practice and judgment
say so at their own line.

## The failure modes

Andrej Karpathy named these failures on 26 January 2026, after shifting from about 80% manual coding
to about 80% agent-driven coding over two months (Karpathy, 2026):

- **Unchecked assumptions.** The models make wrong assumptions on your behalf and just run along
  with them without checking. They don't manage their confusion, don't seek clarifications, don't
  surface inconsistencies, don't present tradeoffs, don't push back when they should.
- **Over-complication.** They really like to overcomplicate code and APIs, bloat abstractions, don't
  clean up dead code... implement a bloated construction over 1000 lines when 100 would do.
- **Orthogonal damage.** They still sometimes change/remove comments and code they don't
  sufficiently understand as side effects, even if orthogonal to the task.

Checks 1 to 3 (understand, simplify, contain) counter these three, one each. Check 4 (verify)
counters a fourth failure that build adds, unvalidated execution: shipping code nobody ran
*(kstack: judgment, see Check 4 below)*. Check 5 (automate) is kstack's judgment, tagged in its
own file. The rule for a failed fix is pstack practice, covered under Practice adopted from pstack.

## Why it fires on every edit, including one-line fixes

Open-source projects that adopted Cursor saw a substantial and persistent rise in static analysis
warnings and code complexity (He et al., 2026). The paper measures projects, not single edits.
Running every check on a one-line fix is kstack's reading of it. The decay builds up one edit at a
time, so no edit is too small to check *(kstack: judgment)*.

## Check 1 (understand)

The impact set, and the one fact that makes a change safe, follow pstack's blast-radius skill
(pstack, `skills/blast-radius/SKILL.md`, ll. 1–35). Running it on every change is kstack's call,
made proportional by the impact set's size.

## Check 2 (simplify)

Check for reuse before writing, and make the smallest change that solves the problem. Both come
from pstack's laziness protocol, "Consolidate decisions" and "Minimize the diff" (pstack,
`skills/principle-laziness-protocol/SKILL.md`, ll. 13–14).

## Check 3 (contain): restructuring is its own diff

Code touched by refactoring performed **in conjunction with other changes** ("floss refactoring")
is more bug-prone, and bugs appear as soon as the first later change lands on the refactored code
(Ferreira et al., 2018). Refactoring is behaviour-preserving in theory only, and developers see it
as costly and risky (Kim et al., 2012; Di Penta et al., 2020).

## Check 4 (verify): why green tests are not enough

Line coverage does not show that a test checks what the line does. In Meta's mutation-guided test
generation, about half (49%) of the new tests that caught a fault every existing test missed
added no line coverage (Foster et al., 2025). The suite already ran that line and passed over
the fault.

Write the failing test first and run it before the fix (pstack, `skills/tdd/SKILL.md`,
ll. 17–18).

Check 4 judges the result against the written interpretation rather than against your own tests,
because a change can be built right and still be the wrong change (Boehm, 1984).

Build adds unvalidated execution to Karpathy's three because the other checks all end in a claim,
and only a run shows the claim holds *(kstack: judgment)*.

Running it at real data volume on the real device is **judgment, not measurement**. Nothing we
found measures it. It stays because a check that cannot reach the failure is not evidence, and toy
fixtures often cannot *(kstack: judgment)*.

The author does not verify their own change. Google holds even a directory's owners to that: they
get their code reviewed before committing (Sadowski et al., 2018).

## Practice adopted from pstack

The playbooks (`feature.md`, `bugfix.md`, `refactor.md`, `perf.md`), the sketch step
(`design.md`), the modifiers (`measure.md`, `long-run.md`), the placement line, the data-shape
rule, the fork rule, the five can't-fail test shapes, the proof ladder and the premise rule after
two failed fixes are adapted from Lauren Tan's pstack and Cursor's cursor-team-kit. Both are MIT,
imported untouched under `upstream/` in the repo that holds this skill. They are an experienced
practitioner's working rules, not measured findings. The routing into one playbook per change and
`feature.md` come from pstack's poteto-mode and its feature playbook. A three-judge vote on
2026-10-09 chose the rest. That vote is project history, and its record is not in this repo.

The one-writer rule in check 1, `references/understand.md`, is build's own. It was in the skill
before the pstack port, in history older than this repo's first commit. pstack's architect design
red flag "Split ownership" states the same rule, "Give each piece of state one owner" (pstack,
`skills/architect/references/design-red-flags.md`, ll. 35–39). The two agree, but build did not
take the rule from there.

## Run evidence behind the gate

Project history from kstack's own runs, not published measurement. Each entry backs a
*(kstack: ...)* tag in `references/gate.md`, `references/judgment.md`, `references/design.md` or
`references/when-a-fix-fails.md`, or a pstack rule the gate took up after the run it names.

- **The root sorts, with no lead agent.** In the 2026-10-17 converge run, four lead agents used 17%
  of the run's 8.7M agent tokens, to sort reports the root had already read.
- **Nothing is held back to save a round.** A run on 2026-10-14 sent proven bugs to its report
  instead of fixing them. The person who asked said to fix a bug rather than defer it.
- **An order-dependent fix lists every order.** In the same 2026-10-14 run, two rounds went to bugs
  that a fix introduced on an input order its author had not traced.
- **A doc fix lists every place the claim reaches.** In the first robovac code run, both doc fixes
  that failed had missed places where the false claim was written.
- **Queue is confirmed by a rerun at the base commit.** In the week of 2026-10-19, four builds
  sorted findings between act on and queue by eye and got it wrong in both directions.
- **The root never writes a fix.** In the same week, the root wrote fixes in five of six builds,
  which left those rounds with no writer apart from their judge.
- **The strict act-on bar ran rounds long.** In the week of 2026-10-19, rounds went to six or seven
  on one change: the gate-ledger build took six review rounds, and the architecture session's item
  took seven review rounds with six fix rounds. The last rounds held findings that broke a rule but
  would not block a real PR. Across the week's builds, 26 of 32 rounds re-reviewed a fix.
- **A run's statistics, 2026-10-26.** One run took 45 items through the gate and merged 7, with
  about 22.8M tokens and about 190 subagents. A clean item cost about 1.2M tokens, 11 agents and 2
  rounds. The two longest took 11 rounds and 4.5M tokens, and 8 rounds and 3.75M tokens.
  - **A doc finding deletes the claim.** On three items the code was proven correct in round 1,
    and 2 to 3 more rounds went to doc and docstring prose: each fixer reworded a sentence, and the
    next review proved the new sentence false. Deleting the claim ended the loop every time.
  - **The fix-forward waits for every lane.** 14 gates lanes stopped mid-suite because a docs-only
    fix commit moved the head while the round's lanes still ran. One suite run cost about 90k to
    140k tokens and 4 to 13 minutes.
  - **A data-flow property gets a structural guard.** Two items spent 3 to 4 rounds each extending
    a source scan to catch the reviewer's next mutant. Both ended when the fix switched to a
    constraint, writers reading one helper's value, or a runtime refusal, and each structural fix
    landed in one round.
  - **Each lane has its own checkout.** Lanes were voided when a rebase ran under a running lane.
    Giving each lane its own detached checkout of the exact commit stopped that.
  - **A later main move does not force a rebase.** Each rebase forced by main moving cost a
    regression drive and an app boot, about 100k to 150k tokens.

## Where this skill came from

build started on 2026-07-03, after a three-day build where every fix caused new bugs. The user and
the agent shared the same UI vision but held different architectures. Check 1 (understand) and the
rule for a failed fix (`references/when-a-fix-fails.md`) exist to catch that failure. That failure
is also why the interpretation of the architecture is written down before the code.

Project history rather than published measurement.

## References

Each entry gives the full reference, a line from the source that supports the claim above, and
how much weight the source carries. A peer-reviewed paper, an official doc or a large company's
engineering publication counts as a source. An arXiv preprint with no venue counts as a lead: it
can point at a result, but it has not been checked by anyone outside its authors.

- **Anthropic (2026).** Glossary: Temperature. Claude Platform documentation.
  https://platform.claude.com/docs/en/about-claude/glossary. "Even with temperature set to 0, the
  results will not be fully deterministic." Official documentation of the model vendor.
- **Boehm, B. W. (1984).** Verifying and Validating Software Requirements and Design
  Specifications. IEEE Software 1(1), 75–88. https://doi.org/10.1109/MS.1984.233702. Verification
  asks "Am I building the product right?" and validation asks "Am I building the right product?"
  The two questions are quoted as later literature quotes them. The original is behind a paywall
  and was not read.
- **Di Penta, M., Bavota, G., and Zampetti, F. (2020).** On the Relationship between Refactoring
  Actions and Bugs: A Differentiated Replication. ESEC/FSE 2020, 556–567.
  https://doi.org/10.1145/3368089.3409695. "refactoring is only in theory behavior-preserving." It
  replicates Bavota et al. (SCAM 2012) on 103 systems and confirms that some refactorings induce
  bugs. It reports Ferreira et al.'s floss-refactoring result in its related work.
- **Ferreira, I., Fernandes, E., Cedrim, D., Uchôa, A., Bibiano, A. C., Garcia, A., et al.
  (2018).** The Buggy Side of Code Refactoring: Understanding the Relationship between
  Refactorings and Bugs. ICSE 2018 Companion, Poster Track, 406–407.
  https://doi.org/10.1145/3183440.3195030. "many bugs are introduced in the refactored code as
  soon as the first immediate change is made on it", and code touched by "refactorings performed
  in conjunction with other changes" is more bug-prone. A two-page peer-reviewed poster on five
  Java projects. Bavota et al. (SCAM 2012), cited here before, measures neither finding.
- **Foster, C., Gulati, A., Harman, M., Harper, I., Mao, K., Ritchey, J., Robert, H., and
  Sengupta, S. (2025).** Mutation-Guided LLM-based Test Generation at Meta. FSE 2025 Companion,
  Industry Track, 180–191. https://doi.org/10.1145/3696630.3728544. "a large proportion (49%) of
  test cases that uniquely additionally kill a mutant, do not also add line coverage."
- **Freeman, S., Mackinnon, T., Pryce, N., and Walnes, J. (2004).** Mock Roles, not Objects.
  OOPSLA 2004 Companion, 236–246. https://doi.org/10.1145/1028664.1028765. "Programmers should not
  write mocks for fixed types, such as those defined by the runtime or external libraries."
- **He, H., Miller, C., Agarwal, S., Kästner, C., and Vasilescu, B. (2026).** Speed at the Cost
  of Quality: How Cursor AI Increases Short-Term Velocity and Long-Term Complexity in Open-Source
  Projects. MSR 2026. https://arxiv.org/abs/2511.04427. "a substantial and persistent increase in
  static analysis warnings and code complexity". The same paper finds "The effect on duplicate
  line density is insignificant."
- **Karpathy, A. (2026, January 26).** Post on X. https://x.com/karpathy/status/2015883857489522876.
  "the models make wrong assumptions on your behalf and just run along with them without checking".
  The list at the top condenses his wording, so it carries no quotation marks.
- **Kim, M., Zimmermann, T., and Nagappan, N. (2012).** A Field Study of Refactoring Challenges and
  Benefits. FSE 2012, 1–11. https://doi.org/10.1145/2393596.2393655. At Microsoft, refactoring in
  practice "is not confined to a rigorous definition of semantics-preserving code transformations",
  and "developers perceive that refactoring involves substantial cost and risks".
- **OpenSSF (2026).** Scorecard: Check Documentation. GitHub, ossf/scorecard.
  https://github.com/ossf/scorecard/blob/main/docs/checks.md. Pinned-Dependencies: "For
  Dockerfiles used in building and releasing your project, pin dependencies by hash."
  Token-Permissions: "Set top-level permissions as `read-all` or `contents: read`". The project's
  own documentation of its checks, a living document read in October 2026.
- **OWASP (2025).** A03 Software Supply Chain Failures. OWASP Top 10:2025.
  https://top10.owasp.org/2025/A03_2025-Software_Supply_Chain_Failures/. "Reduce attack surface by
  removing unused dependencies, unnecessary features, components, files, and documentation." The
  standard industry list of web application risks.
- **Sadowski, C., Söderberg, E., Church, L., Sipko, M., and Bacchelli, A. (2018).** Modern Code
  Review: A Case Study at Google. ICSE-SEIP 2018, 181–190.
  https://doi.org/10.1145/3183519.3183525. "even directory owners are expected to have their code
  reviewed before committing."
- **SQLAlchemy (2026).** Relationship Loading Techniques. SQLAlchemy 2.1 Documentation.
  https://docs.sqlalchemy.org/en/21/orm/queryguide/relationships.html. "In SQLAlchemy, the usual
  mitigation for the N+1 problem is to make use of its very capable eager load system." Official
  documentation of the library.
- **Wacker, M. (2015).** Just Say No to More End-to-End Tests. Google Testing Blog.
  https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html. "Google often
  suggests a 70/20/10 split: 70% unit tests, 20% integration tests, and 10% end-to-end tests."
- **Wiggins, A. (2017).** The Twelve-Factor App, X. Dev/prod parity.
  https://12factor.net/dev-prod-parity. "Keep development, staging, and production as similar as
  possible". A practitioner's guide, not measured findings.
