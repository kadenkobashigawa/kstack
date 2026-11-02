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
`skills/principle-explain-the-number/SKILL.md`, l. 14):

- Did every run do the task?
- Does the gap hold across trials and models?
- Does the scenario matter?

## A process number

A process number, such as gate rounds, tokens or agents per item, is a claimed number and takes
the questions above. Each sample names the kstack commit the gate ran on, and a comparison uses
samples from one commit per side. benchmark-checklist: "Run every side the way production runs
it ... and the same versions and data." (pstack, `skills/benchmark-checklist/SKILL.md`, l. 22)
swarm: "A measurement brief also names the method ... The worker records both in its result."
(pstack, `skills/swarm/SKILL.md`, l. 23) The root writes `kstack <sha>` as the last line of
its message file, so it sits directly above the `GATE VERDICT:` block, from
`git -C "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)" rev-parse --short HEAD` *(kstack: `gate.py`
records no kstack commit, so the merge commit's message is where a sample reads it)*.

An agent's token count comes from its per-request usage records. Each subagent's transcript,
`<session>/subagents/agent-<id>.jsonl` beside the session's `<session>.jsonl` under
`~/.claude/projects/<project>/`, holds one record per content block a request returned. The
records of one request share its `message.id`, and each carries a `message.usage` with
`input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` and `output_tokens`, but
they need not carry the same counts: an early block's record can hold a partial `output_tokens`,
and a request written again later in a transcript can carry zeros. So the count used is each
field's largest value among the request's records, the final count, not the last record's
*(kstack: Claude Code's docs don't describe the transcript; at 12:42 MST on 2026-11-02 the records
of 364 of the 56,165 requests on one machine differed, the `differ` and `req` columns of the
command at the end of this section, and every request total grows while a session on the machine
is live; most differed only in `output_tokens`, with the last record holding the largest, and the
rest because a later record of the request carried zeros)*. The four counts
summed once per distinct `message.id` are the tokens the agent processed; summed over every
record, they count a request once per block. build-the-lever: "A deterministic script turns
"trust me" into "run this"." (pstack, `skills/principle-build-the-lever/SKILL.md`, l. 10)
`ledger.py` keeps the cache write and the cache read apart from uncached input, because a cache
read costs a small fraction of it. For a cost claim, weight the four columns by the pricing page
for the row's model *(kstack: `total` adds the four columns as if each token cost the same, and no
upstream file prices tokens)*.

Two questions take two commands, because a request can sit in several transcripts. Every record
names the session that made the request in `sessionId`, and a copy keeps it: a session forked or
resumed from an earlier one starts with copies of the earlier session's records, in its own
transcript and as copied agent transcripts, under the earlier `sessionId` and `message.id`.

- **What did this session spend?** Run
  `python3 "${CLAUDE_SKILL_DIR}/scripts/ledger.py" <session>.jsonl` for one row per agent and
  totals for the subagents, the root and the session. It counts only the records whose
  `sessionId` is this session's, the `isSidechain` records in its session transcript included,
  since `--all` counts them too. A session id with a transcript in two project folders is one
  session: the ledger reads both folders' transcripts as one, counts each request once and prints
  the same table whichever transcript is named, so one table per session id, plus the work of
  sessions whose transcripts are gone, adds up to the `--all` total *(kstack: `test_ledger.py`'s
  L22 checks that sum on a synthetic machine with forks, a fork of a fork, an agent's fork copies,
  a missing origin, own `isSidechain` records and one id in two folders)*. A copied request was
  spent by the session it names, whether or not that session's transcript is still on the
  machine, so a copy is never in this session's totals. The lines under the table list the
  copies by the session that made them, with how many of their ids that session's own
  transcripts hold, or that it can't look when the transcript sits outside a projects folder and
  no `--projects` names one *(kstack: on 2026-11-02, the line under the table of
  `ledger.py --all` counted no request naming more than one session; one forked session listed
  1,242 root requests and 2,541 agent requests in 66 agent transcripts copied from a session whose
  transcripts held all 3,783 ids, and one copy listed 1,831 root and 4,217 agent requests in 89
  agent transcripts from a session whose transcripts held none of the 6,048)*. An agent that
  forks hands each fork copies of its records under this session's own `sessionId`, so two agent
  rows can hold one request: each row counts it, and the totals count it once *(kstack: on
  2026-11-02 one session's agent rows held 194 more requests than its subagents total, by the
  line under its table)*.
- **What was spent on this machine?** Run
  `python3 "${CLAUDE_SKILL_DIR}/scripts/ledger.py" --all`. It counts each `message.id` once
  across every transcript under the projects folder, so a request copied into a fork, a fork of a
  fork or two sibling forks counts once, and a session whose own transcript is gone counts from
  its copies. One session's transcripts can't answer this: an earlier `ledger.py` counted the
  copies of a session with no transcript left in each session that carried them, so a fork of a
  fork billed that work twice *(kstack: a review's repro on 2026-11-02; nothing in one session's
  transcripts shows the other copies)*.

A record with no `sessionId` counts for no session. The copies include file-history records that
carry none: a snapshot carries no timestamp either, and a delta carries the earlier session's
time, so counting a delta would stretch the root's time back into the earlier session *(kstack:
at 12:42 MST on 2026-11-02 the session transcripts on one machine held 1,287 records with no
`sessionId`, each a `file-history-snapshot` with no timestamp, and 494, each a
`file-history-delta` with one, none of them a request, by the command below, and the counts grow
while a session on the machine is live)*:

```
cat ~/.claude/projects/*/*.jsonl | jq -Rc 'fromjson? | objects | select(.sessionId == null) | [.type, has("timestamp")]' | sort | uniq -c
```

A completion notice's `subagent_tokens` is not spend, and it equals the four counts of the
agent's last request most of the time, not always. Across every session on one machine, it did
for 241 of the 256 agents with a notice in kstack's project folders and for 885 of the 1,231 in
the other folders, and those agents processed 16 and 30 times their notices' sum *(kstack: Claude
Code's docs don't define the field; the `equal`, `noticed`, `processed` and `notices` columns of
the command below at 12:42 MST on 2026-11-02, each agent counted once and each request once, a
request an agent's fork carries included, and they grow while a session on the machine is
live)*. A kstack folder here is one whose name contains `kstack`:

```
python3 "${CLAUDE_SKILL_DIR}/scripts/ledger.py" --all --group kstack
```

A count you write down is true at the commit that lands it and comes with the command that
regenerates it (pstack, `skills/technical-writing/SKILL.md`, l. 96). benchmark-checklist: "Read
the measurement script. Note what it times, counts, and ignores." (pstack,
`skills/benchmark-checklist/SKILL.md`, l. 16)
The notice has no script behind it, so the usage records are what you read *(kstack, the
translation: the records stand in for the measurement script)*. Report spend from the records, and
keep a notice figure for comparison only, since a sum of notices is not spend.

## Making something faster

A speedup is its own playbook, `references/perf.md`. It runs this file's questions on its baseline
and on every number after it (pstack, `skills/poteto-mode/playbooks/perf-issue.md`, l. 5).
