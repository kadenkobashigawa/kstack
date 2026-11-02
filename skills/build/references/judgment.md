# Sorting review findings

Load this when you sort review findings into buckets. The gate loads it for every round
(`references/gate.md`, The verdict). Ported from pstack's interrogate Verify step and
autopilot-full's blocking rule (Lauren Tan, MIT, `upstream/pstack/`). Practice, not measurement.

The root is the gate's root, the session that sorts. The change is the diff the lanes read.

## Verify each finding first

"Sub-agent output is a hypothesis, not evidence." (mattpocock-skills,
`docs/engineering/code-review.md`, l. 73) So the root reruns each finding's command, keeps a
finding when the output shows the failure and the failure breaks the intent, drops the rest, and
merges findings that share a root cause (pstack, `skills/interrogate/SKILL.md`, l. 23). The root
does this itself, with no lead agent *(kstack: lead agents spent tokens sorting reports the root
had already read, per `references/evidence.md`, Run evidence behind the gate)*.

## The three buckets

Each kept finding goes to blocks or follow-up, and each dropped one to dropped. `gate.py record
finding <id> <blocks|follow-up|dropped>` records the bucket.

- **blocks:** "Block a PR only for a problem you can show, with a failing run at the head or a doc
  line the PR made wrong." and "Only a bug a user would hit, a failed gate, or a wrong shipped doc
  blocks" (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 16). A bug the change makes
  or newly reaches always blocks *(kstack: the person who asked said to fix a bug rather than defer
  it, per `references/evidence.md`, Run evidence behind the gate)*. A bug the base already has
  follows the base rule under follow-up, since it "doesn't block unless the PR copies it or newly
  reaches it" (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 16). Every blocking
  finding goes to one fix-forward, with an ID per finding in the Reply, and is recorded with
  `--cmd`, the command that finds its sites (`references/gate.md`, The verdict). How it is closed is
  in `references/gate.md`, A finding stays open until a later row closes it.
- **follow-up:** a kept finding that does not block, since "everything else goes in a follow-up"
  (pstack, `skills/poteto-mode/playbooks/autopilot-full.md`, l. 16). That includes a broken code
  rule in `references/rules.md` that no failing run shows, and a problem the change's base
  already has: "A problem the PR's base already has, whether trunk or the PR below it in a stack,
  doesn't block unless the PR copies it or newly reaches it." (pstack,
  `skills/poteto-mode/playbooks/autopilot-full.md`, l. 16) To tell which, the root reruns the
  finding at the base commit, with its repro, its test or its quoted line. A finding that holds
  there, and that the change neither copies nor newly reaches, is follow-up, whatever severity its
  lane gave it. A finding that doesn't hold there belongs to the change *(kstack: the rerun
  replaces a sort by eye, which got findings wrong both ways, per `references/evidence.md`, Run
  evidence behind the gate)*. A follow-up that only the person who asked can decide, such as taste
  or product scope, names its options in the Reply (pstack,
  `skills/poteto-mode/playbooks/orchestrate.md`, l. 23). Follow-ups go in the Reply and the merge
  commit's message, and nowhere else: no project backlog and no commit to main after the merge
  *(kstack: the operator's decision, 2026-10-26)*. A later change fixes them, not this round's
  fix-forward, since only the fixes that block the work are kept and the rest are parked as
  follow-ups (pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 20). *(kstack: when every
  proven rule break went to a fix round, rounds ran to six or seven, per `references/evidence.md`,
  Run evidence behind the gate.)*
- **dropped:** a finding whose rerun shows no failure, or whose failure does not break the intent
  (pstack, `skills/interrogate/SKILL.md`, l. 23). Each carries its reason, and the Reply gives,
  for each lane, the count of dropped findings and why (pstack, `skills/interrogate/SKILL.md`,
  l. 31).

`gate.py` reads the five old bucket names as the three: act-on as blocks, consider, queue and nit
as follow-up, and dismissed as dropped.
