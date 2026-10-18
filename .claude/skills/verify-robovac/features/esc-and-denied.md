# Esc and a denied prompt

Esc stops the turn, and no hook runs for it, so the app watches the session's transcript for its
interrupt line and docks the robot at once; the next prompt starts a run again. A prompt the person
denies without Esc lets the turn go on, so the robot docks for the wait and goes out again at the
denial.

## Sub-features

- `esc-prompt` docks the robot for Esc pressed at a permission prompt, its why "Interrupted".
- `esc-tool` docks it at once for Esc pressed while a tool runs.
- `esc-next` sends it out again at the session's next prompt.
- `deny-plain` docks it for the wait and sends it out at a denial made without Esc.

## How to get to it (user POV)

- Press Esc in the terminal, or the stop button in the Claude app, while a robovac turn runs.
- Choose No at a permission prompt, with or without Esc.

## Driving it with verify.py

Preconditions:

- Both sides launched and their doctor all PASS.
- The scenario is `scenarios/esc-and-denied.json`.

- **Start the session.** Step 1 replies `ready`. Still `ready`: docked with its **!**.
  It is the drive's baseline, taken past the drive home, not a part under test.
- **Esc at a prompt.** Step 2's `touch` is denied with `interrupt` after 24 s, as Esc at the prompt
  answers it. Still `prompt-waiting`: docked for the wait. Still `esc-at-prompt`:
  still docked, and the clock shows `log end interrupted` (`esc-prompt`).
- **Esc mid-tool.** Step 4 runs `python3 -c "import time; time.sleep(30)"`, because Claude Code
  refuses a standalone `sleep 30`; the scenario sends the host's interrupt while it runs. The tool
  must still be running at the Esc: a turn that has already ended makes the Esc a no-op, and Esc
  mid-tool is never reached. Still `sleeping`: the whole house. Still `esc-mid-tool`: docked
  (`esc-tool`); the log's `end interrupted` may only land at the next hook, while the app docks
  from the transcript.
- **Denied.** Step 6's `touch` is denied without Esc after 24 s. Still `deny-waiting`:
  docked. The clock shows `log answered` and `log start via=again` at the denial's
  `PostToolBatch`, then `end finished`; still `denied-then-done` after it (`deny-plain`).
- **Next prompt.** Each step after an Esc starts with `log start via=again` (`esc-next`).

## Gotchas

- The app reads the transcript the run's start row names, so a still taken before the app's next
  2 s read can show the robot still out.
- A denial with Esc ends the turn with an `error_during_execution` result; that is the turn's end,
  not a failed drive.
