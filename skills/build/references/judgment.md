# Sorting review findings

Load this when you sort review findings into buckets. The gate loads it for every round
(`references/gate.md`, The verdict). Ported from pstack's interrogate lead-judgment (Lauren Tan,
MIT, `upstream/pstack/`). Practice, not measurement.

The lead is the gate's root, the session that sorts. The change is the diff the reviewers read.

The reviewers are aggressive on purpose, and aggression without context produces noise. The lead
filters, puts each finding in context and decides, and never just aggregates (pstack,
`skills/interrogate/references/lead-judgment.md`, ll. 3–7).

## Drop what is not proven

- **Nitpick gravity.** A reviewer with nothing serious to say inflates nits. All nits means the code
  is probably fine, so say so (pstack, `skills/interrogate/references/lead-judgment.md`, l. 20).
- **Hypothetical, not actual.** "What if someone passes null here?" is only a finding if the caller
  can actually pass null. Trace the call site yourself (pstack,
  `skills/interrogate/references/lead-judgment.md`, l. 24).
- **Premature abstraction.** A suggested extraction with one call site and no second use coming
  (pstack, `skills/interrogate/references/lead-judgment.md`, l. 28). The gate holds it to rule 3:
  dismissed unless the diff already adds a second caller.
- **"I would have done it differently."** Dismiss it unless the reviewer showed a concrete problem
  (pstack, `skills/interrogate/references/lead-judgment.md`, l. 32).
- **Missing context that isn't proven.** Patterns consistent with the rest of the codebase, or
  advice that breaks a constraint the reviewer couldn't see (pstack,
  `skills/interrogate/references/lead-judgment.md`, ll. 36–39). A proven defect in code the change
  didn't touch is not dropped. It goes to queue.

## Signs a finding is real

lead-judgment weighs these signs (pstack, `skills/interrogate/references/lead-judgment.md`,
ll. 47–52). The gate holds a finding to the proof test under act on, which shares the second sign.

- Both lanes found the same thing independently.
- The finding names a concrete execution path, not a possibility.
- It shows something the author's model of the code missed.
- Security and correctness findings get extra scrutiny before being dismissed, even from one lane.

**More than five act-on findings is a reason to re-check each one against the proof test, never
to demote a proven one** (pstack, `skills/interrogate/references/lead-judgment.md`, l. 56).

## The five buckets

The bucket names are interrogate's, except that queue replaces its Noted, "Technically valid but not
actionable" (pstack, `skills/interrogate/SKILL.md`, l. 78), because no proven rule break is left
unactionable here. The fifth bucket, nit, is kstack's. Each bucket says where the gate records it,
and marks where its contents depart from interrogate.

- **act on:** every proven defect against the change that would block a real PR, meaning a real
  issue affecting correctness, security or maintainability given the change's goals (pstack,
  `skills/interrogate/SKILL.md`, l. 76). A bug is always act on. So is a new behaviour with no test
  that would catch it breaking (rule 13). Every act-on finding goes to one fix-forward, with an ID
  per finding in the Reply (`references/gate.md`, The verdict). How it is closed is in
  `references/gate.md`, A finding stays open until a later row closes it. A defect that a lane
  filed as a note is still a finding (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`,
  l. 8). A finding is proven when it identifies a concrete execution path, not a hypothetical
  (pstack, `skills/interrogate/references/lead-judgment.md`, l. 48). Two other proofs count: the
  finding quotes the line that breaks a rule in `references/rules.md`, or it names a doc claim the
  code contradicts, which breaks rule 18 *(kstack: a quoted rule line or a contradicted doc is
  proof that needs no execution path)*. A claim of fact in a decision record that cites nothing and
  isn't common knowledge also files under rule 18 *(kstack)*.
- **consider:** a call only the person who asked can make, such as taste or product scope. It goes
  in the Reply with the options. interrogate's Consider also holds points not worth their cost right
  now (pstack, `skills/interrogate/SKILL.md`, l. 77). *(kstack: here a proven break not worth its
  cost now goes to queue, so consider keeps only the person's calls.)*
- **queue:** a proven rule break that would not block a real PR, such as a file past 1,000 lines
  (rule 1) or a duplicate helper (rule 4), whether or not the change wrote it. A later change fixes
  it, not this round's fix-forward. This is interrogate's Noted, kept as work for later rather than
  dropped (pstack, `skills/interrogate/SKILL.md`, l. 78). It goes in the Reply and the merge
  commit's message. When the project's instruction file names a backlog for findings, it also goes
  there, committed to main right after the merge *(kstack: a commit on the branch would change its
  patch and void the verdict)*. pstack parks such follow-ups in the team's own tracker (pstack,
  `skills/reflect/SKILL.md`, l. 55). A project with none keeps no backlog. *(kstack: when every
  proven break went to a fix round, rounds ran to six or seven, per `references/evidence.md`, Run
  evidence behind the gate.)* Queue also holds a proven defect in code or text the change didn't
  write. To confirm that, the lead reruns the finding at the base commit, with its repro, its test
  or its quoted line. A finding that holds there is queue, whatever severity its lane gave it. A
  finding that doesn't hold there belongs to the change, so it is act on *(kstack: the rerun
  replaces a sort by eye, which got findings wrong both ways, per `references/evidence.md`, Run
  evidence behind the gate)*. Mid-run discoveries fix only what blocks the frontier (pstack,
  `skills/poteto-mode/playbooks/orchestrate.md`, l. 109). lead-judgment dismisses changes to code
  the author didn't write (pstack, `skills/interrogate/references/lead-judgment.md`, l. 37).
  *(kstack: proven ones are kept here, because check 3 records what was noticed outside the change
  instead of fixing it there.)*
- **dismissed:** only what is not proven, each with its reason. That is a hypothetical, a
  preference, which lead-judgment calls "I Would Have Done It Differently" (pstack,
  `skills/interrogate/references/lead-judgment.md`, l. 30), or a misreading that missing context
  explains. A proven finding is never dismissed, whether the change wrote the code or not. The
  Dismissed section is a trust mechanism, not busywork (pstack,
  `skills/interrogate/references/lead-judgment.md`, l. 58).
- **nit:** a true finding that breaks no numbered rule in `references/rules.md` and makes no doc
  false, since a false doc breaks rule 18. It is interrogate's `nit`, "Style, naming, minor
  improvement" (pstack, `skills/interrogate/references/reviewer-prompt.md`, l. 38), and the lead
  judges it whatever severity the lane gave it. It blocks nothing. If a reviewer's findings are all
  nits, say the code is probably fine (pstack, `skills/interrogate/references/lead-judgment.md`,
  l. 20). *(kstack: a nit is listed in the Reply and starts no fix round. pstack only says to call
  such a review fine.)*
