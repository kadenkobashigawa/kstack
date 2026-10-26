# The evidence behind the algorithm

## Why step 2 carries the value

**Adams et al. (2021).** Adams, Converse, Hales & Klotz, "People systematically overlook subtractive
changes", *Nature* 592:258–261. Across eight experiments, participants were less likely to find
helpful subtractive changes **when nothing cued them to consider subtraction**.

**Cueing works.** Reminding participants they could 'add or subtract' raised the odds that they
listed at least one subtractive idea (odds ratio **1.93**, experiments 2 and 3), and telling them
'removing pieces is free' raised the share who found the subtractive fix from 41% to 61% (φ = 0.20,
experiment 1). Every cue in the paper named both options. It tested no subtraction-only cue.

This skill is a cue. The paper measured only cues that named both adding and subtracting, so the
claim that a subtraction-only cue also works is judgment.

## Why the stopping rule is inverted here

**Isaacson (2023).** Walter Isaacson, *Elon Musk*, Simon & Schuster. The book sets out the five
steps and their order. Musk's rule is to over-delete and add back at least 10%: "In fact, if you do
not end up adding back at least 10% of them, then you didn't delete enough." That rule fits
manufacturing, where restoring a part costs a part.

Here a cut from working code is a lost capability, and build's check 2 ("Can existing code already
do this?") keeps it or has its loss approved. An approved loss stands rather than being reversed, so
a wrong cut costs more than a missing part, and the rule inverts: delete until just right. What was
nearly cut is reported in the pass, not decided here.

## Why the confirm step exists

**Haynes et al. (2009).** "A surgical safety checklist to reduce morbidity and mortality in a global
population", *New England Journal of Medicine* 360:491–499. The WHO surgical safety checklist cut
deaths from 1.5% to 0.8% and inpatient complications from 11.0% to 7.0%. A checklist puts the list
outside the reader's memory.

The confirm step runs **do-confirm**: run the pass, then check it against the written parts.
Choosing do-confirm over read-do, which reads each item before doing it, is judgment: the pass is
expert work and the list is the artifact itself.

**Liu et al. (2024).** "Lost in the Middle: How Language Models Use Long Contexts", *Transactions of
the Association for Computational Linguistics* 12. In multi-document question answering,
GPT-3.5-Turbo's accuracy dropped by **more than 20%** when the answer's document sat in the middle
of its context rather than at either end. In the worst case it fell below its accuracy with no
documents at all. A pass run from context rather than from the artifact under-weights the middle.

## What was considered and rejected

**TRIZ trimming's function transfer** — removing a component and redistributing its useful function
to the remaining system or the supersystem. Rejected: it exists because TRIZ deletes aggressively in
physical systems where every useful function must be preserved somewhere. Deleting until just right
means a removed part had no job left to reassign.

**TRIZ's function-map prerequisite** — build a component-and-function model before trimming.
Rejected: this skill runs inside a design step that has just enumerated the parts, so the map is
satisfied by the caller.
