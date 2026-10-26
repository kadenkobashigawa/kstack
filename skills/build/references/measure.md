# Reporting a number

Load this before you trust, report or act on a number you measured: a speedup, a regression, a
latency, a throughput, an eval score. Adapted from pstack's benchmark-checklist, its
explain-the-number principle and its perf playbook (Lauren Tan, MIT,
`upstream/pstack/skills/benchmark-checklist/`,
`upstream/pstack/skills/principle-explain-the-number/` and
`upstream/pstack/skills/poteto-mode/playbooks/perf-issue.md`). Practice, not measurement.

## Before you run anything

Write the claim you expect to make, in the words you would ship ("export is 30% faster at p50 on the
60k-row set"). The questions below test that sentence. Read the measurement script for what it
times, counts and ignores. Check the machine's load. If it's busy and you can't stop what's running,
interleave the two sides so both see the same noise, and say so (pstack,
`skills/benchmark-checklist/SKILL.md`, ll. 15–17).

A quick ballpark the user asked for can be one run, but still answer questions 4 and 7 and say it
was one run. A choice between options is never a ballpark (pstack,
`skills/benchmark-checklist/SKILL.md`, l. 11).

## The seven questions

The questions are benchmark-checklist's (pstack, `skills/benchmark-checklist/SKILL.md`,
ll. 21–27).

1. **Why not double?** Name the limiter from CPU per process, I/O wait or a profile, and map the
   hot spot to source. "Profile in a run you do not report, because profilers and tracers slow the
   work down." (pstack, `skills/benchmark-checklist/SKILL.md`, l. 21) If the load generator
   saturates first, you measured the load generator. "If a change did not move the number, the
   limiter explains why, so find it before you call the change useless." (pstack,
   `skills/benchmark-checklist/SKILL.md`, l. 21)
2. **Was it tuned?** Every side runs the way production runs it: release build, production settings,
   same data and versions, caches as warm as production sees them. An untuned side means you
   compared configurations, not implementations. "Tune it and measure again before you pick a
   winner. If you cannot tune it, do not pick a winner from that run." (pstack,
   `skills/benchmark-checklist/SKILL.md`, l. 22) Dev timing tells nothing about production timing
   for anything a laptop accelerates *(kstack: one project measured the same embedding call at
   0.084 s a chunk on an M5 Pro, where it ran on the GPU through `mps`, and 4.46 s on one CPU
   thread in production, 53 times slower and invisible locally)*.
3. **Did it break limits?** Do the arithmetic against disk, network and core counts, and against the
   share the changed piece took. A result past a limit measured a cache, a no-op or a bug.
4. **Did it error?** Count failures and check that outputs are correct, not just present.
   Rejections are fast and timeouts are slow, so both distort timing.
5. **Does it reproduce?** At least five runs per side, alternated, reported as median and range. A
   gap smaller than the run-to-run spread is no measurable difference.
6. **Does it matter?** Measure the end-to-end path a user waits on and report the micro result as a
   share of it.
7. **Did it even happen?** Confirm the work ran inside the timed region: the request reached the
   server, the rows were written, the result was used.

## Report

Lead with the verdict: faster, slower, no measurable difference, or inconclusive. Then the number
with its unit, the run count, the range and the limiter. It is inconclusive when you can't name the
limiter, a side ran untuned, or questions 4 and 7 went unchecked (pstack,
`skills/benchmark-checklist/SKILL.md`, ll. 31–33). "Name the gap." (pstack,
`skills/benchmark-checklist/SKILL.md`, l. 33)

## An eval score

An eval score takes the same care, asked of its trials (pstack,
`skills/principle-explain-the-number/SKILL.md`, l. 19):

- Did every run do the task?
- Does the gap hold across trials and models?
- Does the scenario matter?

## A process number

A process number, such as gate rounds, tokens or agents per item, is a claimed number and takes
the questions above. Each sample names the kstack commit the gate ran on, and a comparison uses
samples from one commit per side. benchmark-checklist: "Run every side the way production runs
it ... and the same versions and data." (pstack, `skills/benchmark-checklist/SKILL.md`, l. 22)
swarm: "A measurement brief also names the method ... The worker records both in its result."
(pstack, `skills/swarm/SKILL.md`, l. 26) The root writes `kstack <sha>` as the last line of
its message file, so it sits directly above the `GATE VERDICT:` block, from
`git -C "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)" rev-parse --short HEAD` *(kstack: `gate.py`
records no kstack commit, so the merge commit's message is where a sample reads it)*.

## Making something faster

A speedup is its own playbook, `references/perf.md`. It runs this file's questions on its baseline
and on every number after it (pstack, `skills/poteto-mode/playbooks/perf-issue.md`, l. 5).
