# The two lenses

Load this when you review a change as one of build's gate review lanes. Each lane runs as pstack's
autopilot-full describes and build's gate ports: "Run the audit as two or more review lanes with the
full brief. Give each lane one main focus, such as consumer parity with trunk, lifetimes and races,
or data and config safety." (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 8) Both
lanes hold the change to the same rubric, all 18 of build's code rules in `references/rules.md`,
beside this file. Each reports a finding by its rule number. A lane's lens is its main focus.
It says where the lane looks hardest, never which rules it may skip. Each lane gets the change
pinned to exact SHAs, the stated intent and the rest of its brief, in the fields of build's
SKILL.md (The brief), which `references/gate.md` (A round, lane 3) fills. It reports findings in
the shape at the bottom, or "no findings".

The ways to look come from pstack's interrogate review. The structure lens draws on the rubric's
Structural Integrity and Complexity Budget sections (pstack,
`skills/interrogate/references/rubric.md`, ll. 32–43, 56–68) and the code-quality dimensions
(pstack, `skills/interrogate/references/code-quality-review.md`, ll. 21–35). The correctness lens
draws on the rubric's Correctness, Verification and Security sections (pstack,
`skills/interrogate/references/rubric.md`, ll. 5–17, 45–54, 70–77). A third source is
cursor-team-kit's thermo-nuclear review (MIT; cursor-team-kit,
`skills/thermo-nuclear-code-quality-review/SKILL.md`, ll. 73–87). Practice, not measurement.

*(kstack: the focus is split by rules, structure on Sonnet and correctness on Opus as the gate
staffs its lanes.)* Interrogate instead gives every reviewer "the same prompt and rubric", because
"The adversarial signal comes from model diversity, not assigned personas." (pstack,
`skills/interrogate/SKILL.md`, l. 9) *(kstack: Claude Code runs only Claude models, so kstack splits
the focus to get a second angle that model diversity alone gives weakly. Two Claude models are
weaker diversity than two model families, as build's `references/gate.md` says of its own lanes in
A round.)*

Both lanes trace before they claim. A finding names `file:line` and the rule it breaks, and shows
why it is a problem, not only that it is (pstack,
`skills/interrogate/references/reviewer-prompt.md`, l. 46). Read the project's CLAUDE.md invariants
and the decision record that covers the files first. A pattern the codebase uses on purpose is not
a defect (pstack, `skills/interrogate/references/lead-judgment.md`, l. 38).

## structure: rules 1 to 8 and 18

**Does this already exist?** (rule 4) For each new function, class, route, query, helper or
constant, search for something that already does the job. Grep the key identifiers and their
synonyms, the SQL table names, the route paths, the error strings, and similar call shapes. Name the
existing helper and where it lives.

**Is it in the right place?** (rules 2, 4 and 6) Check the change against the project's layering
(its architecture or layers decision record, if it has one) and its ownership rules, such as a rule
that only the data-access layer builds queries. code-quality-review asks to "Keep logic in the
canonical layer and reuse existing helpers." (pstack,
`skills/interrogate/references/code-quality-review.md`, l. 33)

**Is there a simpler shape?** (rules 1, 3, 5 and 7) Look for the restructure that deletes complexity
rather than moving it (pstack, `skills/interrogate/references/code-quality-review.md`, l. 21).
Screen with the red flags in build's `references/design.md`, Screen for red flags.

**Do the docs still tell the truth?** (rule 18) Read the module docstrings and their Methods lists,
the function docstrings, and the CLAUDE.md claims and decision records that describe the changed
code. Check any source a claim cites. A claim of fact in a decision record that cites nothing and
isn't common knowledge is a finding too, filed under rule 18. *(kstack: rule 18 holds a cited claim
to its source, and an uncited claim has no source to hold it to, so this lens files it as rule 18's
extension rather than let it pass unchecked.)*

## correctness: rules 9 to 17

**Does it do what the intent says?** (rules 9 to 11) When a finding depends on a value being
possible, trace the call chain that makes it possible (pstack,
`skills/interrogate/references/rubric.md`, l. 17). A hypothetical the callers can't produce is not
a finding (pstack, `skills/interrogate/references/lead-judgment.md`, l. 24).

**Security.** (rule 12) For each finding, trace the input path: user input reaching SQL, a shell, a
template or a file path, or an endpoint or query that skips the project's visibility or permission
check.

**Blast radius past grep.** (rules 9 and 10) Look for what the change breaks that a symbol search
won't show: a JSON field a client reads, a database column, a migration that edits shipped history,
a config key set elsewhere, a background thread, startup and shutdown order.

**Tests.** (rules 13 to 15) Break a changed line in your head and ask which test would fail. Hold
any new test to the can't-fail shapes in build's `references/verify.md`, Intent check on every test
you kept, which also says when a passing test stays. Changed behaviour that nothing would catch is a
finding, with the cheapest check that would catch it.

## Finding shape

The shape adapts interrogate's reviewer output (pstack,
`skills/interrogate/references/reviewer-prompt.md`, ll. 59–67) and adds the rule line.

```
### <severity: critical | warning | nit> · <short title>
**rule:** <number from rules.md; an uncited decision-record claim files as 18>
**where:** <file:line or function>
**finding:** <what is wrong>
**evidence:** <how you know: the trace, the grep, the run; quote the code>
**fix:** <what to do instead, at the right layer> (optional)
```

`critical`: a bug, data loss, a security hole, or behaviour that is fundamentally broken. `warning`:
a design or maintainability problem that will cause pain. `nit`: style or naming (pstack,
`skills/interrogate/references/reviewer-prompt.md`, ll. 35–38). Zero findings is a valid review.
Say "no findings" and stop (pstack, `skills/interrogate/references/reviewer-prompt.md`, l. 53).
