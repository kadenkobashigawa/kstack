# When a fix fails

Load this when a second fix for one issue has failed. `SKILL.md`, `references/gate.md`,
`references/bugfix.md` and `references/long-run.md` point here, and this file is the only full
statement of the rule. Adapted from pstack's attack-the-premise principle (Lauren Tan, MIT,
`upstream/pstack/skills/principle-attack-the-premise/`). Practice, not measurement.

## Stop after the second failed fix

After two failed fixes for the same issue, stop. pstack: "When two or more fixes that share one
premise have failed the same gate, suspect the premise, not the fixes." (pstack,
`skills/principle-attack-the-premise/SKILL.md`, l. 9) *(kstack: kstack counts two failed fixes on
the same issue, which inside the gate is the same finding ID. pstack counts fixes that share a
premise and failed the same gate. A script can count an ID. The premise is written down only
after the stop, in the next section, so it can't be what triggers the stop.)* The principle's
reason: "Each failed fix is evidence against the belief it assumed." (pstack,
`skills/principle-attack-the-premise/SKILL.md`, l. 11)

Revert to the last good state. pstack's bug-fix playbook: "When evidence refutes a hypothesis,
revert what it motivated." (pstack, `skills/poteto-mode/playbooks/bug-fix.md`, l. 5) Write down
what was wrong, not what you tried *(kstack: judgment)*. Give the next attempt to a fresh subagent
with that note in its brief. poteto-mode's fresh-subagent default covers the hand-off: "This holds
for a fix round, a follow-up, a retry, and the next queue item." (pstack,
`skills/poteto-mode/SKILL.md`, l. 102)

## Write the premise and test it before the third fix

pstack: "Do not start the next fix before the premise is written down and tested." (pstack,
`skills/principle-attack-the-premise/SKILL.md`, l. 19)

1. **Write the premise down.** pstack: "The premise is the one sentence that every failed fix
   assumed." (pstack, `skills/principle-attack-the-premise/SKILL.md`, l. 14)
2. **Test the premise.** pstack: "Find an observation that would come out differently if the
   premise were false, and make it. Look at how the failures are distributed, not only at how large
   they are." (pstack, `skills/principle-attack-the-premise/SKILL.md`, l. 15) Make the check a
   script you can rerun (pstack, `skills/principle-attack-the-premise/SKILL.md`, l. 15).
3. **Follow the evidence.** When it contradicts the premise, the cause is elsewhere, so look for
   what the failures share that the premise did not predict. When it confirms the premise, ask the
   next "why", since the earlier fixes may have treated a consequence (pstack,
   `skills/principle-attack-the-premise/SKILL.md`, l. 16).
4. **Remove the condition instead of compensating for it.** When one part always lands on the
   losing side, change what puts it there. A mechanism that cleans up after it leaves the cause in
   place and adds work on every run (pstack, `skills/principle-attack-the-premise/SKILL.md`,
   l. 17).

## A fix that creates new bugs points at the design

Don't patch the new bug. Go back to check 1 (`references/understand.md`) and re-read what the change
reaches. Then go to check 2 (`references/simplify.md`) and ask whether the change sits at the wrong
layer *(kstack: the three-day build in `references/evidence.md`, Where this skill came from, where
every fix spawned new bugs because the user and the agent held different architectures)*.

## A scan that keeps growing points at the mechanism

When each fix extends a source scan to catch the reviewer's next case, the premise both fixes
shared is that a scan can guard the property. A scan fits only a fixed syntactic pattern. Replace
it with a structural mechanism, as `references/design.md` says under Screen for red flags. "If the
fix is structural, only use the structural fix." (pstack,
`skills/principle-encode-lessons-in-structure/SKILL.md`, l. 11) *(kstack: per
`references/evidence.md`, Run evidence behind the gate.)*

## How the count is kept

The count belongs to the issue, not to the agent, so a fresh subagent inherits it through the
prior agent's report in its brief. Inside the gate, each blocking finding has an ID in the round's
record, and a finding that comes back is a failed correction against that ID
(`references/gate.md`, The verdict). Outside the gate, a fix that fails the test it was written to
pass also counts *(kstack: pstack counts failures at "the same gate", and a fix's own test is the
first gate it meets)*. An unattended run stops on the second failure (`references/long-run.md`).
