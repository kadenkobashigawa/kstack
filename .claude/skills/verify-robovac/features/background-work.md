# Background work keeps it out

A robovac turn can leave work running when it ends: a shell started in the background, or an agent
started with `run_in_background`. The robot stays out sweeping past that turn's end while the work
runs, and docks with its **!** when the turn that the work's own report starts has finished with
nothing left running.

## Sub-features

- `bg-shell-out` keeps the robot out past the turn's end while a background shell runs.
- `bg-agent-out` keeps it out past the turn's end while a background agent runs.
- `bg-report-dock` docks it when the turn the finished task's report starts has ended.

## How to get to it (user POV)

- In a robovac turn, the agent runs a Bash command in the background, or calls the Agent tool with
  `run_in_background`, and replies before the work is done.

## Driving it with verify.py

Preconditions:

- Both sides launched and their doctor all PASS.
- The scenario is `scenarios/background-work.json`.

- **Shell.** Step 1 starts `sleep 20` in the background and replies. The clock shows `hook Stop` and
  no `log end` at it, with `log work turn=False tasks=<id>:shell`. Still `shell-running`:
  the whole house (`bg-shell-out`).
- **Its report.** About 20 s in, Claude Code submits the shell's `<task-notification>` prompt: the
  clock shows `log start via=again`, then `log end finished` at that turn's Stop. Still
  `shell-done`: the camera on the dock, the **!** over it (`bg-report-dock`).
- **Agent.** Step 3 starts a background agent that runs `sleep 15`. The clock shows the turn's
  `hook Stop` with no `log end`, and `log work turn=False tasks=<id>:subagent`. Still
  `agent-running`: the whole house (`bg-agent-out`). Still `agent-done`:
  docked with its **!** after the agent's report turn ends (`bg-report-dock`).

## Gotchas

- Each step waits for two results, the turn's and the report turn's. A report that never comes
  times the step out, which is INCONCLUSIVE.
- A background agent runs on the model the Agent tool picks, so its report lands later on one side
  than the other. Judge by its rows in the clock, not by the still's second alone.
- Claude Code refuses a standalone foreground `sleep 30` ("Blocked: standalone sleep 30", seen
  2026-10-18), so the agent's wait is `sleep 15`, as its probe of 2026-10-17 ran.
