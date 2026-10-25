# The gate

Load after check 4 (verify) for every change that is to be merged, whatever method the table at the
top of SKILL.md picked. The gate takes a change from "verified by its author" to "verified by agents
that did not write it".

Ported from pstack's autopilot-full playbook (steps 2, 4 and 5), its shipping playbook (the patch-id
rule) and its swarm skill (Lauren Tan, MIT, `upstream/pstack/skills/`). The translation for Claude
Code and local merges is marked where it departs from pstack.

shipping's rule: "Safe means a verdict from an agent that did not write the code. CI green is not a
verdict, and an approving bot review is not a verdict."

## The unit of work

Each self-contained change is its own branch, gated and merged alone. autopilot-full: "One owner runs
each PR from build to merge", and "Run owners in true parallel and never stack." Many branches run at
once when the work is self-contained: "one writer per branch, disjoint files, cross-PR drift
absorbed by rebase". "Self-contained PRs branch straight off main, and sequenced work is
merge-then-branch." "Only genuinely overlapping work serializes": a change that touches a file
another unmerged branch touches waits for that branch to merge, then branches off the new main. A
round's findings are not separate changes: they go back in one fix-forward on the change's own
branch, as below, since autopilot-full has "In fix rounds, the owner keeps that merge base". A fix
outside the change, found along the way, is a change of its own: autonomous-run's "Put out-of-band
fixes in their own PR." *(ours, the translation: pstack's unit is a PR, here it is a local branch)*.

## A round

A round starts at the commit the author calls code-ready, and again at every later commit that
changes the patch. Before that commit starts a round, its author runs the checks the project's own
rules name for the paths it touches, on the commit itself. autopilot-full: "Before a push that
starts a round, run the pre-review checks that the repo's AGENTS.md files and rules name for the
touched paths. Run them on the committed head." *(the translation: for pstack's "AGENTS.md files
and rules", a project here has its `CLAUDE.md` or `AGENTS.md` files and its rules, such as
`.claude/rules/` or a contributing guide that names checks (kstack's `CONTRIBUTING.md` names
`claude plugin validate .` for changes under `skills/`); and a round starts at a commit rather than
a push)*. At that exact commit, fresh agents run these lanes. None of them wrote the code.

1. **Gates.** Re-run the checks at that commit: the risk list from check 1 (understand), and the
   project's own pre-merge checks (tests, lint, type checks). The commit is checked as committed: "A hook pass is
   not proof." A check that cannot run, its tool missing or its access refused, makes the lane
   BLOCKED and names what was missing, never PASS: benny's reproduce-and-fix-issues, "If the
   environment cannot provide a required capability, report `Blocked` and state what was
   missing."
2. **Live.** "Prove the load-bearing behavior live on the real surface the change touches", through
   the project's verify skill (`verify-<app>`). "The live lane is the floor, and a verdict without it
   is not clean." The drive is sized to the change's load-bearing behaviour, not to every claim in
   it. cursor-team-kit's verify-this: "Pick the smallest local surface that can disprove it." So
   anything a smaller surface can disprove, such as a unit, a script or a fixture, is a test run in
   the gates lane, not a drive. A round builds one test copy of the app per version under test, not
   one per claim *(ours: a copy per claim multiplies builds and agents for no new evidence)*. A
   change with no runtime surface (docs only) records that fact instead. *(The docs-only case is
   ours.)*
3. **Review, in two or more lanes.** "Audit the diff, distrusting the PR body. Run the audit as two
   or more review lanes with the full brief. Give each lane one main focus, such as consumer parity
   with trunk, lifetimes and races, or data and config safety." Each lane holds the diff to
   `references/rules.md`, reports by rule number, and rates each finding `critical`, `warning` or
   `nit`, as interrogate's reviewer prompt does. The full brief carries the change's stated intent,
   the rules, every capability the change drops with who approves each loss (the person who asked,
   or this verdict under the operator's grant: check 2 in SKILL.md) *(ours, as that rule is)*, and
   the run's never-list, the things the run may not read or touch. Every brief the gate writes, a
   lane's, the lead's or a fixer's, points at what it needs. poteto-mode's "Defaults for every
   `Task` call" include "file pointers not inlined context", so commits and paths go as pointers
   and the agent reads them itself. A report a brief depends on is the exception, since a report
   is a reply and not a file: orchestrate's brief template has "upstream reports pasted in full
   when this unit depends on them, because workers cannot see siblings". *(pstack draws its
   adversarial signal from different model families. Claude Code runs only Claude models, so the
   lanes use different Claude models, such as Opus and Sonnet, and name which ran. This is weaker
   diversity, and named as such.)*
4. **Regression.** "Run the same load-bearing scenario on current trunk. If trunk does not have the
   feature, record that fact and gate the behavior the diff adds plus the end state the user waits
   for instead of pretending trunk can produce it."

Each lane names the exact commit it checked.

## Staffing

- **Review lanes default to Sonnet.** swarm sends its workers to the fast model: "Pick the worker
  model from the `swarm workers` line in `~/.cursor/rules/pstack-models.mdc`. If the rule or that
  line is missing, use `grok-4.7-xhigh-fast`." *(ours: Claude Code runs only Claude models, so the
  fast model is Sonnet.)*
- **Opus takes the correctness lane, and any fixer whose change is behaviour.** *(ours: the lane
  where a miss ships a wrong result, and the writer of a change that alters what the code does, get
  the stronger model. Reasoning, not measurement.)*
- **Two review lanes on two models, every round.** interrogate: "The adversarial signal comes from
  model diversity, not assigned personas." One Opus and one Sonnet, as lane 3 says.
- **At most three agents at once**, since agents share the session's usage limit *(ours)*.

## The verdict

From swarm: each lane returns `PASS`, `ISSUES` or `BLOCKED` with evidence, and "A worker that can
prove a defect reports `ISSUES` and lists every issue it can prove, not only the first." A lane
that doesn't record the commit it checked is re-run once, and after that it is a gap. "A gap does not
count as a pass."

**The root decides which findings are proven before any of them blocks**, after interrogate's step 5
and its `references/lead-judgment.md`. The root is the session running the gate. It reads the diff
and every lane's findings itself, and puts each finding in one of five buckets, with
lead-judgment's rules: "You are the lead reviewer. ... Don't aggregate. Filter, contextualize, and
decide." That is autopilot-full's "You own the verdicts, never the PRs", where "the root keeps only
verification, countersigns, and audits". A separate fresh lead sorts only when the root wrote the
fix being judged, since a writer must not judge its own fix. *(ours: interrogate's lead is a
separate agent. In the 2026-10-17 converge run, the four lead agents used 17% of its 8.7M agent
tokens, and the root had already read every lane's report.)* The buckets' names are interrogate's,
except that queue takes the place of its Noted, "Technically valid but not actionable": here no
proven rule break is left unactionable, by the rule after the list. The fifth bucket, nit, is ours.
What a bucket holds departs from interrogate where marked.
- **act on:** every proven defect against the diff, which is every proven break of a numbered rule
  in `references/rules.md`, whatever severity its lane gave it. A break that changes no behaviour
  counts: an untested guarantee line (rule 13), a file past 1,000 lines (rule 1) or a duplicate
  helper (rule 4). autopilot-full sends "every proven finding against the PR to the owner in one
  fix-forward", and "A defect that a lane filed as a note is a finding." *(ours: interrogate's act
  on holds the issues that "would block a real PR"; here every proven rule break does, by the rule
  after the list.)* A finding is proven when it "identifies a concrete execution path, not a
  hypothetical", which lead-judgment lists among the signs a finding deserves attention. Two more
  tests are ours: it quotes the line that breaks a rule in `references/rules.md`, the lanes' rubric,
  or it names a doc claim the code contradicts, which is rule 18. A claim of fact in a decision
  record that cites nothing and isn't common knowledge files under rule 18 too, as an extension of
  ours from vet's first version.
- **consider:** a call only the person who asked can make, such as taste or product scope, with the
  options. It goes to the report. *(ours: interrogate's consider also holds points "you're not sure
  they outweigh the cost of addressing them right now". Here no proven rule break waits, by the rule
  after the list, so it keeps only the calls the person must make.)*
- **queue:** a proven defect in code or text the diff didn't write. It goes to the findings queue.
  In a run with one task (`references/long-run.md`, When no task is handed over), it is left for the
  next run, which reviews afresh and finds what still stands; orchestrate's rule is the same shape:
  "Mid-run discoveries fix only what blocks the frontier." *(ours: lead-judgment counts "Suggesting
  changes to code the author didn't write or modify" as missing context and says "Dismiss them
  gracefully." The proven ones are kept here, because check 3 (contain) records what was noticed
  outside the diff instead of fixing it there, and pstack's autonomous-run says "Mid-run
  discoveries are yours.")*
- **dismissed:** only what is not proven: a hypothetical, a preference ("I Would Have Done It
  Differently"), or a misreading that missing context explains, each with its reason. A proven
  finding is never dismissed, whether the diff wrote the code or not. "The 'Dismissed' section is
  not busywork. It's a trust mechanism."
- **nit:** a true finding that breaks no numbered rule in `references/rules.md` and makes no doc
  false, since a false doc breaks rule 18. It is interrogate's `nit`, "Style, naming, minor
  improvement", and the root judges it whatever severity the lane gave it. It is listed in the
  report and blocks nothing. lead-judgment's Nitpick Gravity: "If a reviewer's findings are all nits
  and style preferences, the code is probably fine. Say so." *(ours: that a nit is listed and
  starts no fix round. pstack only says to call such a review fine.)*

Nothing that breaks a rule is held back to save a round *(ours, after a run of 2026-10-14 sent
proven bugs to the report; the person who asked: "if you find a bug, I feel like you should fix it,
not just defer it to save time")*. A round whose findings are all nits is a clean verdict, and its
nits go in the report. *(pstack's root owns the verdicts and never owns the PR. A root that wrote
the fix would be its own judge, so then the lead is a fresh agent.)*

**A clean verdict** means that, at the commit that will merge, no lane is BLOCKED or a gap, the live
lane ran or the change has no runtime surface, two review lanes on different models read the
round's diff, and the root (the fresh lead, when the root wrote the fix) left nothing in act on.
Nits in the report do not count against it.

**Otherwise, fix forward.** Every act-on finding goes back in one fix-forward. From autopilot-full:
"For each behavior finding, ask for a red test that covers every site with the same defect. Where
no test can show the defect, ask for a repro receipt instead. Add that defect to the next round's
review brief." Before the fix is written, its brief lists the sites, by fix-root-causes' rule:
"Check for the pattern, not just the instance (grep for the same pattern, fix all instances)." For
a behaviour that depends on order, such as hook events, retries or concurrent writers, the sites
include every order the inputs can arrive in, and the brief names each one with the test that
covers it *(ours: two of the 2026-10-14 run's rounds went to bugs a fix had introduced on an order
its author had not traced)*. For a false claim in a doc or a comment, the same rule covers every
place the claim reaches. Enumerate those places with a scripted search, or rewrite the sentence to
state the mechanism, so that it holds without a list. *(This carries the red-test rule over to
docs. Both of the first robovac code run's failed doc fixes missed places.)*

**A fresh agent writes the fix.** From poteto-mode: "Fresh subagents by default. Give new work to a
fresh subagent with consolidated scope, meaning the original brief, every later directive, and the
prior agent's report and branch. This holds for a fix round, a follow-up, a retry, and the next
queue item." The fix goes through build's checks 1 to 4 again, test first. The new head gets a fresh
round, except for lane results that stay valid under the patch-id rule below.

**A finding that comes back is a failed correction.** When a round reports a defect a fix was meant
to close, or one a fix introduced, that counts against the issue, and build's rule holds: "Two failed
corrections on the same issue means stop." Write down the premise both fixes shared and test it, or
settle the design the issue belongs to, before a third fix *(ours, after one doc sentence took three
rewrites and a code change across four rounds)*.

## The patch-id rule

From shipping: "Record the verdict head SHA, base SHA, and stable `git patch-id` of that PR's
base-to-head diff. A rebase or base retarget rewrites SHAs and can silently invalidate a verdict
without touching a check." Compare the recorded patch-id (`git diff <base>..<head> | git patch-id
--stable`) with the current one, before a fix round's lanes start and before merging. If they match,
keep the code verdict but re-run the checks at the current head. "Never use matching commit
messages or a green check from an older SHA as a substitute."

If they differ, shipping's next rule decides which lanes run again: "When the two patches differ
only in tests, docs, or lint config, build what each lane ran. Build it twice at the verdict SHA and
once at the current head. A difference is noise if the two builds at the verdict SHA also show it, or
if it is an embedded commit SHA. ... If only noise differs, that lane's result stays valid, and
checks and a review of the change run fresh. Do not reuse a lane result from a dev server or from
anything else with no build output. Rerun that lane. Re-verify anything else when the patch
changed." The review of the change is two lanes on different models reading only the new commits,
with the earlier round's brief. *(Ours: in a skill set, a `SKILL.md`, a reference or an agent's
definition is code, since an agent runs it; docs here are text no program or agent acts on, such as
a README, a product or design record, and comments.)*

## Merge preparation

From autopilot-full step 5, with local merges in place of PRs *(the translation)*:

1. **Rebase.** "The owner merges only from a head freshly rebased onto trunk." Rebase onto current
   main right before merging, then re-run the project's checks on that head.
2. **Re-check the verdict** with the patch-id rule. A new patch voids the verdict, except the lane
   results that rule keeps.
3. **Dry-run the merge.** Fetch main and check that `git merge-tree` of the head against main is
   clean. Check that no file main changed since the merge base is one the change touches, or one that
   decides which checks run (CI config). If either check fails, rebase again and repeat from step 1.
4. **Merge as one commit** on main, carrying the verdict in its message: the lanes, their models and
   the commit they checked. pstack squash-merges.

**Who may merge** is not decided here. autopilot-full's rule is: "The operator's full-autonomy grant
plus the root's clean verdict is the merge authorization that babysitting alone never has", and
"Operator-named items stop at merge-ready and wait for the operator's click." Without the operator's
grant, the gate ends at merge-ready: a clean verdict, recorded, on a branch.
