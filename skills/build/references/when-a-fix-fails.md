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
reason: "Each failure under a shared premise is evidence about the premise." (pstack,
`skills/principle-attack-the-premise/SKILL.md`, l. 11)

Revert to the last good state. pstack's bug-fix playbook: "When evidence refutes a hypothesis,
revert what it motivated." (pstack, `skills/poteto-mode/playbooks/bug-fix.md`, l. 5) Write down
what was wrong, not what you tried *(kstack: judgment)*. Give the next attempt to a fresh subagent
with that note in its brief. poteto-mode's fresh-subagent default covers the hand-off: "This holds
for a fix round, a follow-up, a retry, and the next queue item." (pstack,
`skills/poteto-mode/SKILL.md`, l. 99)

## Write the premise and take the census before the third fix

pstack: "Do not start the next fix before the premise is written down and the census exists."
(pstack, `skills/principle-attack-the-premise/SKILL.md`, l. 20)

1. **Write the premise down.** pstack: "The premise is the one sentence that every failed fix
   assumed." (pstack, `skills/principle-attack-the-premise/SKILL.md`, l. 14)
2. **Take the census.** Count the problem per actor. An actor is each thing the failing check runs
   over, such as a caller, a worker, a file or a row *(kstack: pstack leaves "actor" undefined)*.
   pstack: "The census shows which actors hold the imbalance, not how large it is. Write the census
   as a rerunnable script" (pstack, `skills/principle-attack-the-premise/SKILL.md`, l. 15).
3. **Read the skew.** When the same few actors hold most of the problem on every run, something
   assigns them that role. Find what assigns it, and treat that as the next root cause (pstack,
   `skills/principle-attack-the-premise/SKILL.md`, l. 16).
4. **Remove the asymmetry instead of compensating for it.** Move, rotate or randomize the role so
   that no actor holds it on every run. A return path, a shared pool or a periodic rebalance leaves
   the assignment in place and adds work on every run (pstack,
   `skills/principle-attack-the-premise/SKILL.md`, l. 17).

An even census clears the premise. pstack: "If the census is even across actors, the premise is not
the cause. Look for the cause elsewhere and keep the census as evidence." (pstack,
`skills/principle-attack-the-premise/SKILL.md`, l. 21)

## A fix that creates new bugs points at the design

Don't patch the new bug. Go back to check 1 (`references/understand.md`) and re-read what the change
reaches. Then go to check 2 (`references/simplify.md`) and ask whether the change sits at the wrong
layer *(kstack: the three-day build in `references/evidence.md`, Where this skill came from, where
every fix spawned new bugs because the user and the agent held different architectures)*.

## A scan that keeps growing points at the mechanism

When each fix extends a source scan to catch the reviewer's next case, the premise both fixes
shared is that a scan can guard the property. A scan fits only a fixed syntactic pattern. Replace
it with the strongest structural mechanism the situation allows, in the order
`references/design.md` quotes under Screen for red flags (pstack,
`skills/principle-encode-lessons-in-structure/SKILL.md`, l. 19). *(kstack: per
`references/evidence.md`, Run evidence behind the gate.)*

## How the count is kept

The count belongs to the issue, not to the agent, so a fresh subagent inherits it through the
prior agent's report in its brief. Inside the gate, each act-on finding has an ID in the round's
record, and a finding that comes back is a failed correction against that ID
(`references/gate.md`, The verdict). Outside the gate, a fix that fails the test it was written to
pass also counts *(kstack: pstack counts failures at "the same gate", and a fix's own test is the
first gate it meets)*. An unattended run stops on the second failure (`references/long-run.md`).
