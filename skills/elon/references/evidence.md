# The evidence behind the algorithm

## Why step 2 carries the value

People systematically default to additive transformations and overlook subtractive ones.
Across eight experiments, participants were less likely to identify advantageous subtractive
changes **when nothing cued them to consider subtraction**.
— Adams, Converse, Hales & Klotz, *Nature* 592:258–261 (2021)

**Cueing works.** Reminding participants they could 'add or subtract' raised the odds that
they listed at least one subtractive idea (odds ratio **1.93**, experiments 2 and 3), and
telling them 'removing pieces is free' raised the share who found the subtractive fix from 41%
to 61% (φ = 0.20, experiment 1). Every cue in the paper named both options; it tested no
subtraction-only cue.

That is the whole justification for this skill existing: it is a cue, and cues are the
measured intervention against subtraction neglect.

## Why the stopping rule is inverted here

Musk's rule is to over-delete and add back at least 10%: "In fact, if you do not end up adding
back at least 10% of them, then you didn't delete enough." (Walter Isaacson, *Elon Musk*, 2023).
That is calibrated for manufacturing, where restoring a part costs a part.

Here a cut from working code is a lost capability, and build's check 2 ("Can existing code
already do this?") keeps it or has its loss approved. An approved loss stands rather than being
reversed, so a wrong cut costs more than a missing part, and the rule inverts: delete until just
right. What was nearly cut is reported in the pass, not decided here.

## Why the confirm step exists

Recognition succeeds where recall quietly drops low-salience items, which is why checklists
supply external retrieval cues rather than relying on unaided memory. The WHO surgical safety
checklist cut deaths from 1.5% to 0.8% and inpatient complications from 11.0% to 7.0% (Haynes
et al., *New England Journal of Medicine* 360:491-499, 2009).

The effective shape is **do-confirm**, not read-do: run the pass, then verify against the
written list. Read-do is often the worse form for expert work.

For an agent specifically: in multi-document question answering, GPT-3.5-Turbo's accuracy
dropped by **more than 20%** when the answer's document sat in the middle of its context rather
than at either end, and in the worst case fell below its accuracy with no documents at all (Liu
et al., "Lost in the Middle: How Language Models Use Long Contexts", *Transactions of the
Association for Computational Linguistics*; arXiv:2307.03172). A pass run from context rather
than from the artifact systematically under-weights the middle.

## What was considered and rejected

**TRIZ trimming's function transfer** — removing a component and redistributing its useful
function to the remaining system or the supersystem. Rejected: it exists because TRIZ deletes
aggressively in physical systems where every useful function must be preserved somewhere.
Deleting until just right means a removed part had no job left to reassign.

**TRIZ's function-map prerequisite** — build a component-and-function model before trimming.
Rejected: this skill runs inside a design step that has just enumerated the parts, so the map
is satisfied by the caller.
