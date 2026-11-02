---
name: build
description: "Runs on every code change, one line or one module. Routes the change to one playbook (feature, bug fix, refactor or performance) that the root session leads while fresh subagents write the code, and merges it into local main only after a review by agents that did not write it. Use when writing or changing any code, or when the user types /build or says \"build X\", \"add a feature\", \"fix this\", \"refactor\" or \"make it faster\"."
---

# build

build runs on every code change, one-line fixes included, because AI-assisted code gathers warnings
and complexity that persist (He et al., 2026). It routes the change to one playbook, whose steps
carry out the checks. Its shape is pstack's poteto-mode (Lauren Tan, MIT,
`upstream/pstack/skills/poteto-mode/`) *(kstack: the playbooks come before the checks, so you pick
one first)*. Why each check exists is in `references/evidence.md`.

## Non-negotiables

- **The root leads, and fresh subagents do the work** (`## Subagents`). The root is the session
  the user talks to. pstack's bug-fix playbook: "**You own this task. Plan, review, verify.**
  Delegate investigation and the fix to subagents, stay in the lead." (pstack,
  `skills/poteto-mode/playbooks/bug-fix.md`, l. 3)
- **Every change that merges passes the gate** (`references/gate.md`), whatever its playbook. The
  root runs the gate's checks, and fresh agents that did not write the change run its other lanes,
  where two review lanes on two models try to break it. Give each
  self-contained change its own branch, in its own linked worktree, gated and merged alone. A
  change waits only for one it overlaps (`references/gate.md`, The unit of work).
- **Read the project's specifics from the repo on each run**: its test commands, where findings
  go, and what counts as a reference in its language (imports, calls, config keys). Never write
  them into this file *(kstack: build serves any project)*.

## Triggers

- **Code crossing a function boundary → `references/design.md`**, the sketch step, before any
  code. poteto-mode sends it to its architect skill (pstack, `skills/poteto-mode/SKILL.md`, l. 23).
- **A nontrivial multi-step task → the throughput checkpoint**, per `references/feature.md` step 3
  (pstack, `skills/poteto-mode/SKILL.md`, l. 26).
- **Prose in the diff (docs, comments, commit messages) → kstack's `technical-writing` and
  `unslop` skills, before the code-ready commit** (pstack, `skills/poteto-mode/SKILL.md`, l. 28).
  Both are verbatim copies of pstack's, and only the operator can invoke them, so read each file:
  `$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../technical-writing/SKILL.md` and `../unslop/SKILL.md`
  beside it. Make each count true at its commit, with the command that regenerates it (pstack,
  `skills/technical-writing/SKILL.md`, l. 96). *(kstack: one pass over finished prose for the gate,
  where poteto-mode writes clean as it goes and gives comments their own rule.)*
- **A claimed number (speedup, regression, latency, score) → `references/measure.md`** before you
  report or act on it (pstack, `skills/poteto-mode/SKILL.md`, l. 32). A process number, such as
  gate rounds, tokens or agents per item, is a claimed number, and each sample names the kstack
  commit the gate ran on (`references/measure.md`, A process number).
- **A broken skill found mid-task → fix it on its own branch, through build.** Don't block on it,
  and don't work around it (pstack, `skills/poteto-mode/SKILL.md`, l. 36). *(kstack: a branch where
  pstack opens a PR, since build merges locally, `references/gate.md`, Merge preparation.)*
- **Long or unattended work (`/loop`, or the user away) → `references/long-run.md`** around the
  routed playbook, with its decision trail per pstack's show-me-your-work skill (pstack,
  `skills/poteto-mode/playbooks/autonomous-run.md`, l. 9; pstack, `skills/poteto-mode/SKILL.md`,
  ll. 37, 142).

## Playbooks

**Route every change to exactly one playbook.** Match the change to a row, open the file, and copy
its steps verbatim into the task list before any task-specific item. A step you skip stays in the
list as `skip: <reason>` (pstack, `skills/poteto-mode/SKILL.md`, l. 124).

| The change | Playbook |
|---|---|
| adds behaviour | `references/feature.md` |
| corrects a defect | `references/bugfix.md` |
| reshapes code without changing behaviour | `references/refactor.md` |
| makes something faster without changing behaviour | `references/perf.md` |

The rows are pstack's split (pstack, `skills/poteto-mode/playbooks/refactoring.md`, l. 3). A change
that fits two rows is two diffs through two playbooks, because check 3 never restructures and
changes behaviour in one diff. Ship the structural change first, with a test that pins today's
behaviour. A redesign found during a refactor is a feature: name it and route it to
`references/feature.md` (pstack, `skills/poteto-mode/playbooks/refactoring.md`, l. 5). *(kstack:
every code change adds, corrects, reshapes or speeds up code, so build needs no figure-it-out
fallback.)*

## The checks

The checks are poteto-mode's Principles (pstack, `skills/poteto-mode/SKILL.md`, l. 15), and each
playbook step names the one it carries out. Read a check's file in full before you apply it, because
it says when the check is satisfied (pstack, `skills/poteto-mode/SKILL.md`, l. 41). Checks 1 to 3
counter the failures Karpathy names (Karpathy, 2026).

- **1. Understand** (`references/understand.md`). Counters unchecked assumptions. Before the first
  line of code: the placement line, the impact set (everything the change reaches) and its tests,
  the data shape, and the written interpretation of what the request means.
- **2. Simplify** (`references/simplify.md`). Counters over-complication. Deciding what to build
  and how big: whether it should exist (`/elon`), what already does it, which layer it belongs
  in, no bloat, nothing orphaned.
- **3. Contain** (`references/contain.md`). Counters orthogonal damage, meaning changes to code
  the task never concerned. Every hunk traces to the interpretation, unrelated problems are recorded
  rather than fixed in this diff, and restructuring never shares a diff with a behaviour change.
- **4. Verify** (`references/verify.md`). Counters unvalidated execution, shipping code nobody
  ran *(kstack: build adds this fourth failure to Karpathy's three, `references/evidence.md`, Check
  4)*. Before anything is called done: the risk list, each changed line broken on purpose to prove
  a test catches it, the whole path run for real, the result judged against the interpretation,
  then the gate.
- **5. Automate** (`references/automate.md`). Never blocks a merge. Once a step repeats three times,
  script it, and build the tool now when only a tool can prove the work. An invariant becomes a
  mechanical check, and a correction made twice becomes a `/correct` proposal to the operator.
- **When a fix fails** (`references/when-a-fix-fails.md`). After the second failed fix for one
  issue, stop, revert, write down the premise both fixes shared, and count the problem per actor
  before a third fix.

## Autonomy

**Decide reversible work alone, and pause for the operator on irreversible work**: force-pushes
to shared branches, deploys, data deletion, customer messages (pstack,
`skills/poteto-mode/SKILL.md`, ll. 84, 86), and pushes to a shared remote *(kstack: build merges
to local main only)*.

**Use any MCP tool for reversible work, without asking** (pstack, `skills/poteto-mode/SKILL.md`,
l. 84). *(kstack: pstack also lets external actions such as team chat and ticket updates proceed
unasked. Here a message or any other outward action still pauses, as the list above says.)*

**Run it instead of asking.** When a fact a run could show answers a choice, run it. Ask only for
a product or preference call no experiment can settle. Under a full-autonomy grant, decide and
report a call the grant covers, and apply a default for a call only the operator can make (pstack,
`skills/poteto-mode/SKILL.md`, l. 21).

**"Don't stop", "going to bed", "run until done" and "be fully autonomous" mean keep going**
(pstack, `skills/poteto-mode/SKILL.md`, l. 88).

**A merge needs the operator's grant and a clean verdict** (pstack,
`skills/poteto-mode/playbooks/autopilot-full.md`, ll. 7, 17). The grant to merge into local main is
standing, so a clean verdict merges, and pushing stays the operator's *(kstack: a local merge can be
undone until the push, and the operator pushes)*. A change the operator names, or one they ask to
see first, stops at merge-ready, a clean verdict on a branch (`references/gate.md`, Merge
preparation).

**No is an acceptable answer.** When the operator asks whether to do something, invites more
scope, or shows you an approach, give your real judgment. Decline or push back when that is the
true answer, and choose candor over agreement (pstack, `skills/poteto-mode/SKILL.md`, l. 90).

## Subagents

**Give each investigation, piece of writing and fix to a fresh subagent**, fix rounds, follow-ups,
retries and the next queue item included. Hand it the original brief, every later directive, and
the prior agent's report and branch. Reuse an agent only when the work needs its checkout, its
uncommitted changes, or a process it still runs (pstack, `skills/poteto-mode/SKILL.md`, l. 102).

**The root owns the result.** Review each diff and write your own summary. A second opinion is
the same prompt against a different model (pstack, `skills/poteto-mode/SKILL.md`, l. 100). So the
gate runs its two review lanes, one on Opus and one on Sonnet, with one shared brief
(`references/gate.md`, A round, lane 3).

**Opus writes any fix or change that alters behaviour. Sonnet runs the mechanical work, and the
live lane and the checker.** poteto-mode sends the hardest changes to its strongest model and
trivial edits to its fast one (pstack, `skills/poteto-mode/SKILL.md`, l. 96), and verification
stays on the swarm workers' model (pstack, `skills/poteto-mode/SKILL.md`, l. 98). *(kstack: Claude
Code runs only Claude models, so Opus is the strongest and Sonnet the fast one.)*

**Run every subagent in the background**, so the root keeps working while it runs (pstack,
`skills/poteto-mode/SKILL.md`, l. 96).

**Pass `effort: "medium"` on every Agent call**, for writers, fixers, gate lanes, the researcher
and every other subagent. The Agent tool takes an `effort` parameter for each call, and it
overrides the agent's own `effort` field and the session's level (Claude Code docs,
`sub-agents`, https://code.claude.com/docs/en/sub-agents). pstack picks the level per job (pstack,
`skills/poteto-mode/SKILL.md`, l. 98). *(kstack: the operator set one level for every subagent,
since Opus 5.5 does the work at medium.)*

**Only the root spawns agents.** A subagent owns its diff directly, with the same review separation
(pstack, `skills/poteto-mode/playbooks/feature.md`, l. 12). *(kstack: pstack's single owner fans
out after the blocking phase, l. 19. Here the root spawns every agent, so it sees all the
work.)*

### The brief

**Every brief build writes, for a writer, a fixer or a gate lane, has these fields.** Each kickoff
names the goal, the paths the worker may and may not write, the actions it must not take, and the
evidence that proves the work is done. "If you can't name the evidence, the unit isn't scoped yet."
(pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 18) Every brief stands alone and
includes "the goal, scope, exact slice or race arm, how to verify, and what to report" (pstack,
`skills/swarm/SKILL.md`, l. 31). kstack writes those parts as these fields *(kstack: one template
for every brief, so a missing part shows as an empty field)*:

```
GOAL         one sentence, the outcome, executable by a stranger with no chat access
SCOPE        paths this unit may write; paths it may not; its own linked worktree and branch,
             or for a lane the detached checkout of the exact commit it checks; for code, the
             named data shape and its organizing structure
CONTEXT      file pointers, not inlined context; reports this unit depends on pasted in full,
             because workers cannot see siblings
ACCEPTANCE   the evidence that proves the work is done, one checkable criterion per line
VERIFY       exact commands the project's rules name for the touched paths, plus known gotchas
FORBIDDEN    no merge, no push, no rebase, no force-push, no fixes outside scope, plus
             unit-specific bans
REPORT       status, branch, head SHA, verdict, what you actually ran, deviations,
             suggested follow-ups
```

- **SCOPE** names the data shape because pstack's feature step delegates "with a specific scope
  (file paths, named data shape and its organizing structure ...)" (pstack,
  `skills/poteto-mode/playbooks/feature.md`, l. 12).
- **CONTEXT** gives pointers, not pasted files (pstack, `skills/poteto-mode/SKILL.md`, l. 96), so
  commits and paths go as pointers and the agent reads them itself. A report the unit depends on
  is pasted in full, because "Workers can't see their siblings." (pstack,
  `skills/poteto-mode/playbooks/orchestrate.md`, l. 10)
- **VERIFY** carries the commands because the author runs them on the committed head before a
  round (`references/gate.md`, A round).
- **REPORT** uses `PASS`, `ISSUES` or `BLOCKED` with evidence for a lane (pstack,
  `skills/swarm/SKILL.md`, l. 31).
- **A brief that cannot name its evidence is not spawned**, since that unit is not scoped yet
  (pstack, `skills/poteto-mode/playbooks/orchestrate.md`, l. 18).
- **A run of many items samples its briefs.** "Read a sample of each sub-coordinator's kickoffs
  while its workers run, and fix its instructions when one fails." (pstack,
  `skills/poteto-mode/playbooks/orchestrate.md`, l. 19) *(kstack, the translation: the root writes
  every brief, so it reads one sampled brief per wave alongside the run, and a failing brief fixes
  the template it came from, not only that brief.)*
- **A fix brief for a doc finding carries the deletion** and proposes no new prose, per the rule
  on a false or unsupported claim (`references/gate.md`, The verdict).
- *(kstack, the translation: pstack's PRs become the local branch and its head commit, and the
  ban on `gt` becomes a ban on merging and pushing, which the root alone does. Claude Code loads
  the project's `CLAUDE.md` files into every subagent, which carries the standing orders.)*

## Every rule names its source or says it is reasoning

Each rule carries a citation or a *(kstack: reason)* tag, in the style of `CONTRIBUTING.md`,
Citations.
