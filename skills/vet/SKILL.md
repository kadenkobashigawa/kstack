---
name: vet
description: Background review of every commit landing on main; two fresh read-only reviewers, a lead that keeps only proven findings, a monthly canary, never edits code. Use only when the user types /vet or a /loop runs it (`/loop /vet watch`).
argument-hint: "[watch | <range> | status | canary]"
---

# vet

The author never reviews its own work. Nobody can read the whole codebase either, so work can
recreate something that already exists, land in the wrong place, or pass every test and still not
be the best solution. vet is the second pair of eyes that runs without being asked: it reviews every
commit that lands on main. The standing code is robovac's job, though a proven defect a reviewer
meets there is still filed, as queue.

**It reports; it never repairs.** A tick reports its findings in its reply and its notification, and
keeps no file of them. The work session triages each one: fix it through `/build`, or dismiss it
with the disproof. A `consider` finding is built, or the person decides against it. A finding class seen twice goes to `/correct` so the next change can't repeat
it.

Built from pstack's interrogate, swarm, show-me-your-work and autopilot-full's review lanes, and
cursor-team-kit's strict code-quality review (MIT, under `upstream/` in this skill's repo), adapted
to Claude only; its reviewers hold each range to build's code rules, as the gate's lanes do. It
stays model-invocable on purpose: a `/loop` wake re-enters it through the Skill tool, which refuses
a typed-only skill.

## The one script

`scripts/vet.sh` owns the mechanical steps. The lead writes the findings, which are judgment, in the
shape under Reviewing a range.

```
S=${CLAUDE_SKILL_DIR}/scripts/vet.sh
$S dir               # state directory: state/report/vet/ when that is gitignored, else .git/vet/
$S init              # first run: the cursor starts at main's tip
$S pending           # unreviewed commits on main, oldest first
$S ci <rev>          # GitHub Actions conclusion: success, failure, pending, none, or error
$S advance <sha>     # move the cursor forward along main, only once every lane for the range has
                     # returned; exits 2 for a commit behind the cursor or not on main
$S block <min> <why> # hold retries of a BLOCKED range for <min> minutes
$S watch             # blocks until main moves past the cursor, has been still five minutes,
                     # and no block is in force
$S due-canary        # exit 0 when no canary has run this calendar month
$S canary-done       # record today's UTC date as the canary's one line
$S status            # one line; `--hook` is the SessionStart form
```

**Nothing grows.** The state directory holds `cursor` (one sha), `canary` (the date of the last
canary, one line) and, while a range is blocked, `blocked_until` (one number, removed by the next
`advance`). Nothing else is written, anywhere: no ledger, no findings file, no trail file. A tick's
trail, its judgments and the reason for each dismissal, lives in its own working notes and ends with
the tick. *(ours, as with robovac's reports: no ledger is kept, because one would only grow.)*

**Not carried:** show-me-your-work's two hand-back steps, the audit of the log against the
transcript ("At the end of the run, before handing back, check the log told the truth") and the
cross-model review of the trail ("spawn a subagent on a different model family from the one that did
the work"), whose flags end every reply in an Attention section. *(ours: a tick replies with its
findings or nothing, as Speak only when it matters says, so it has no hand-back to end with an
Attention list. And vet's trail is never audited by another agent, by the maintainer's choice:
vet is the final reviewer.)*

## Modes

| Invocation | Does |
|---|---|
| `/vet watch` | One loop tick: review what's pending, else run the canary if due, then arm the next wake. Started as `/loop /vet watch` in a dedicated tab. |
| `/vet <range>` | Review one range once (`a1b2c3..main`, `HEAD~3..HEAD`, a single sha). Doesn't move the cursor. |
| `/vet status` | Print the status line. |
| `/vet canary` | Self-test on a known past bug (below). |

## Reviewing a range

1. **Gather.** `git log` and `git diff --stat` for the range, the commit messages as the stated intent,
   `$S ci <tip>`, and `ruff check` on the changed Python files. Note any file the range pushes past
   1,000 lines. When the working tree has uncommitted edits to a file, read the committed version with
   `git show <sha>:<path>`; the working tree is not what was committed.
2. **Two review lanes, in parallel, fresh context.** Spawn two `vet-reviewer` agents in one message,
   each with the range as two exact SHAs (`git rev-parse` both ends first, since a range such as
   `a1b2c3..main` moves while they read), the intent, the CI result, its lens from
   `references/lenses.md`, and the paths of `${CLAUDE_SKILL_DIR}/references/lenses.md` and
   `${CLAUDE_SKILL_DIR}/../build/references/rules.md`, which it reads first. swarm: "When workers verify or measure commits, each brief names the
   exact SHAs." Both hold the range to build's `references/rules.md`, all 18 rules, and name a rule
   per finding; each lens is one main focus:
   - **structure** (`model: sonnet`), rules 1 to 8 and 18: does this already exist, is it in the
     right layer, is there a simpler shape, do the docs still tell the truth.
   - **correctness** (`model: opus`), rules 9 to 17: does it do what the intent says, security,
     invariants, blast radius past grep, whether the tests reach the changed lines.

   The models follow the gate's staffing in build's `references/gate.md`: review lanes default to
   Sonnet, and Opus takes the correctness lane.

   Skip a lane only when it can't apply (no code in the range skips correctness) and log the skip.
   Never more than two agents at once. If the `vet-reviewer` agent type isn't available in this
   session, spawn `general-purpose` and tell it to read `${CLAUDE_SKILL_DIR}/../../agents/vet-reviewer.md`
   first and follow it as its instructions.
3. **Judge.** Apply `references/judgment.md`: drop the noise, check each surviving finding against
   the code yourself, push its evidence down the proof ladder, and sort it into build's gate buckets
   (act on, consider, queue, nit, dismissed).
4. **Report.** Put each act-on and queue finding in the tick's reply with status `open`, and each
   consider finding with status `consider` and its options, all in the shape below, then each nit in
   one line after them, blocking nothing, and send the count in a notification. Keep each judgment
   and each dismissal with its reason in the tick's own working notes, which end with it. In a `/vet
   watch` tick, then `$S advance <tip>`; `/vet <range>` and the canary never move the cursor.
5. **A lane that didn't return** makes the range `BLOCKED`: the cursor stays, and `$S block 60 "<why>"`
   holds the retry for an hour (longer when the cause was the usage cap). A retry after the block is
   allowed and expected; it is not a re-review. A lane whose reply doesn't open with that exact range
   is re-run once, and after a second miss the range is `BLOCKED` the same way, because, in swarm's
   words, "A gap does not count as a pass."

```
## V-<yyyymmdd>-<n> · <one-line title>
- **status:** open | consider
- **where:** <file:line>@<short sha> · range <a>..<b>
- **lens:** structure | correctness · **rule:** <number> · **severity:** critical | warning | nit
- **finding:** <what is wrong, concretely>
- **evidence:** <the proof and its ladder rung>
- **fix prompt:** /build <a paste-ready instruction that fixes it at its layer>
```

## The canary

Both reviewers are Claude, like the author, so they can share its blind spots. Once a month the
canary checks vet still catches a defect it should:

1. Find a commit in `git log` that fixed a bug and whose message or diff names the commit that
   introduced it (a revert counts: the reverted commit is the bug). Pick one at random from those,
   so that successive months differ *(ours: vet keeps no list of the ones it has used)*.
2. Review the range that introduced the bug, exactly as a range, without telling the reviewers why.
   The canary never moves the cursor: its range is behind it, and `$S advance` refuses that.
3. Pass if any kept finding names the defect the fix commit later repaired. Then `$S canary-done`,
   whether it passed or missed. Its findings go in the working notes only: the code they describe
   was fixed long ago. The reply says `canary PASS` or `canary MISS`, with the range and the fix
   commit.
4. A `MISS` is a finding against vet itself: report it as an `open` item whose fix prompt is
   `/correct` on the lens that missed it.

## One tick of the loop (`/vet watch`)

1. First run only: `$S init`, and say once in chat that the loop is up.
2. If `$S pending` lists commits, review them as one range (`<cursor>..<main tip>`).
3. Else, if `$S due-canary`, run the canary.
4. Else nothing to do: no output.
5. **Re-arm as `/loop` instructs.** The event to wait on is `$S watch`, started as a background Bash
   command (`run_in_background`, timeout 7200000) unless one from an earlier tick is still running; it
   ends when main has moved and gone quiet, which re-invokes this session. The fallback heartbeat is
   3600 seconds, and the re-arm prompt is the one the loop started with
   (`/loop /vet watch`, or `/loop /kstack:vet watch` with the plugin). `noop: true` when nothing
   was reviewed.
6. **Speak only when it matters.** A tick with new `open` or `consider` findings replies with them
   in the shape above, and sends a PushNotification with the count; silence otherwise.

Two ticks in a row that end `BLOCKED` for the same reason: say why in the reply, stop the loop with
ScheduleWakeup `stop: true`, and say so in chat.

## Never

- Edit, create or delete a tracked file; commit, push, deploy, or touch a remote.
- Install packages, run paid or `@llm` tests, read `.env` files, or start the app against anything but a
  throwaway database (the project's verify skill knows how).
- Run more than two agents at once, review again a range at or behind the cursor, write a file that
  grows, or relax a lens to clear a range.

## Keeping it honest

- **Noise.** The work session fixes each finding or dismisses it with the disproof. A finding class
  it dismisses twice goes to `/correct` on vet itself, since a count needs a file that vet doesn't
  keep *(ours)*.
- **Shared blind spots.** The monthly canary above; a miss is a finding against vet.
- **A dead loop is silent.** The SessionStart hook prints unreviewed commits in every new session, so a
  loop that died with its tab gets noticed.
