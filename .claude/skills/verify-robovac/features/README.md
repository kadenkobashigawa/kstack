# Robovac verification map

This directory is the maintained source for verifying what a person sees of robovac: the Robovac
app's robots, moved by the robovac hooks of a Claude Code session. Read the index before driving,
then use the matching feature file as the recipe. Each feature has a scenario of the same name in
`../scenarios/`.

## Baseline preconditions

- Run everything from the repository root, with `V=.claude/skills/verify-robovac/scripts/verify.py`.
- Make one claim folder per claim: `E=$(python3 $V claim <slug>)`.
- Launch each side from a revision: `python3 $V launch "$E" baseline <rev>`, then the treatment.
- Run `python3 $V doctor "$E" <side>` and require every line PASS before a drive.
- Tell the person before a drive: the test window comes to the front and is filmed.
- Never drive the person's own Robovac app, their Claude app or a session they started.

## Driving conventions

- Every feature starts from an empty log and an empty session folder; its scenario holds the rest.
- Drive both sides with the same scenario file, unchanged between them.
- The session's first prompt starts with `/robovac`, which makes it a robovac session; every later
  prompt in that session starts a run again.
- A permission prompt's, a question's or a form's answer is the scenario's `answers` entry, in the
  order they arrive: its hold is the person's pause before clicking. A permission prompt answered
  within about 6 s never docks the robot; a question or a form docks it as it opens.
- The robot drives home along its route before the camera zooms in, which took from 3 s to about
  31 s from the `end` row on the 2026-10-18 films (the longest, 31 s, in
  `2026-10-18-004018-two-states-2`; one drive in `2026-10-18-022717-questions-and-forms` had not
  docked when its film ended, 19 s after its end). A still taken after a turn ends waits that out;
  one taken while a prompt, question or form waits comes before its answer, so it can catch the
  robot on its way home. When a still does, the log rows and the film decide.
- Hover and keyboard are the person's own input: drive them with the computer-use tools on the
  test copy, `Robovac Verify`, never by script.
- Run `python3 $V cleanup "$E"` after every drive, failed ones included.
- A commit's test copy is built once per round and reused by every claim that names it; run
  `python3 $V end-round` when the round's last claim is cleaned up.
- A drive quits its test copy when the recording ends; do not leave the window open by hand.

## Proof and skip reporting

- Pair every still with the log row at its time in `<side>/clock.md`; a still alone proves nothing.
- A docked robot is the camera zoomed in on its dock with a **!**; a going one is the whole house.
- Side effects: the rows in `<side>/runs.jsonl` and the files listed at the end of the clock.
- Compare the `asked` lines of both clocks; different tool calls make the claim INCONCLUSIVE.
- A still marked MISSED, a turn timed out or a doctor FAIL is INCONCLUSIVE; report its line.
- Do not report a sub-feature as verified through another feature's drive.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing what the person sees. It
then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every way a person reaches it.
3. `Driving it with verify.py` starts with `Preconditions:` and pairs each action with its
   scenario step and the observable result.
4. `Gotchas` lists traps that can waste or invalidate a run.

Keep implementation details out of the map. Name only user paths, scenario steps, required state,
commands and observable proof.

## Features

| Feature | Scenario | Last driven |
|---|---|---|
| [The run follows its turn](./run-follows-turn.md): sweeps while the turn works, docks with its ! once it ends with nothing running | `run-follows-turn.json` | 2026-10-17, 80cf3ea against 23b1d70: no verdict written (`2026-10-17-195541-run-follows-turn`) |
| [The wait on a permission prompt](./wait-on-prompt.md): docks after the ~6 s notice, out again once the approved tool finishes | `wait-on-prompt.json` | 2026-10-17, 80cf3ea against 7f00c4f: both dock and go out alike, so NOT VERIFIED for a difference (`2026-10-17-143520-wait-on-prompt`) |
| [A Stop hook continues the turn](./stop-hook-continues.md): docks at the first Stop, out again at the continuation's first call | `stop-hook-continues.json` | 2026-10-17, 80cf3ea against 23b1d70: no verdict written (`2026-10-17-195542-stop-hook-continues`) |
| [Background work keeps it out](./background-work.md): a background shell or agent past the turn's end, docked after its report's turn | `background-work.json` | 2026-10-18, a550130 against 5c4a1a5: VERIFIED, one still early for a 25 s drive home (`2026-10-18-023438-background-work`) |
| [A question or a form docks it as it opens](./questions-and-forms.md): no notice to wait for; out again once answered | `questions-and-forms.json` | 2026-10-18, a550130 against 5c4a1a5: VERIFIED, two baseline stills off by the drive home (`2026-10-18-022717-questions-and-forms`) |
| [Sent out on its way home](./on-its-way-home.md): docks first, then straight back out | `on-its-way-home.json` | not yet |
| [Esc and a denied prompt](./esc-and-denied.md): Esc docks at once; a plain denial goes out again | `esc-and-denied.json` | 2026-10-17, 80cf3ea against 23b1d70: INCONCLUSIVE, run with its own `scenario.json`: this scenario's steps with two 45 s pauses, an early-denial step, an extra still and the app opened at the first prompt (`"open": ["prompt", 0]`) added, and earlier result stills (+8 and +16) (`2026-10-17-193918-esc-and-denied`) |
| [Subagents](./subagents.md): a foreground subagent's prompt, a background agent during a wait | `subagents.json` | 2026-10-17, 80cf3ea against 23b1d70: VERIFIED (`2026-10-17-192534-subagents`) |
| [The app's own basics](./app-basics.md): opens on runs already going; the hover slip's line and why | `app-basics.json` | not yet |
