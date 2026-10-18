# Reporting a number

Load this before you trust, report or act on a number you measured: a speedup, a regression, a
latency, a throughput, an eval score. Adapted from pstack's benchmark-checklist, its explain-the-number
principle and its perf playbook (Lauren Tan, MIT). Practice, not measurement.

## Before you run anything

Write the claim you expect to make, in the words you would ship ("export is 30% faster at p50 on the
60k-row set"); the questions below test that sentence. Read the measurement script for what it times,
counts and ignores. Check the machine's load; if it's busy and you can't stop what's running,
interleave the two sides so both see the same noise, and say so.

A quick ballpark the user asked for can be one run, but still answer questions 4 and 7 and say it was
one run. A choice between options is never a ballpark.

## The seven questions

1. **Why not double?** Name the limiter: CPU per process, a profiler mapped to source, I/O wait.
   "Profile in a run you do not report, because profilers and tracers slow the work down." If the
   load generator saturates first, you measured the load generator.
2. **Was it tuned?** Every side runs the way production runs it: release build, production settings,
   same data and versions, caches as warm as production sees them. An untuned side means you compared
   configurations, not implementations. Dev timing tells nothing about production timing for anything
   a laptop accelerates *(ours: one project measured the same embedding call at 0.084 s a chunk on
   an M5 Pro, where it ran on the GPU through `mps`, and 4.46 s on one CPU thread in production, 53
   times slower and invisible locally)*.
3. **Did it break limits?** Do the arithmetic against disk, network and core counts, and against the
   share the changed piece took. A result past a limit measured a cache, a no-op or a bug.
4. **Did it error?** Count failures and check outputs are correct, not just present. Rejections are
   fast and timeouts are slow, so both distort timing.
5. **Does it reproduce?** At least five runs per side, alternated, reported as median and range. A gap
   smaller than the run-to-run spread is no measurable difference.
6. **Does it matter?** Measure the end-to-end path a user waits on and report the micro result as a
   share of it.
7. **Did it even happen?** Confirm the work ran inside the timed region: the request reached the
   server, the rows were written, the result was used.

## Report

Lead with the verdict: faster, slower, no measurable difference, or inconclusive. Then the number with
its unit, the run count, the range and the limiter. It is inconclusive when you can't name the
limiter, a side ran untuned, or questions 4 and 7 went unchecked.

## Making something faster

Baseline first, vetted with the questions above. Then try the cheapest idea first, and stop at the
first one that meets the target: don't do it at all; do it but not again; do less of it; do it later;
do it when nobody is waiting; do it concurrently; do it cheaper. One change per measurement, kept only
if it beats the noise and the regression tests stay green. Where pstack's perf playbook says "If it
crosses a function boundary, `architect` first", here `references/design.md` loads only when the fix
is a one-way door *(ours: the 2026-10-09 vote merged architect into `references/design.md` for
one-way doors, and architect's design exploration runs on arena, parked until Claude Code can reach
a second model family)*.
