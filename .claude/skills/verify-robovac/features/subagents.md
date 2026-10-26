# Subagents

A subagent's permission prompt waits on the person like the main agent's own: the robot docks
after its notice. A foreground subagent's approved tool sends the robot out again, since the
subagent works on. While only a background agent's prompt waits, the main agent's next call or
batch sends it out, since the main agent works on past it.

## Sub-features

- `sub-fg-dock` docks the robot for a foreground subagent's prompt left about 6 s.
- `sub-fg-out` sends it out again when that subagent's approved tool's result arrives.
- `sub-bg-out` keeps it out, or sends it out, while only a background agent's prompt waits and
  the main agent keeps calling tools.
- `sub-end` docks it when the main turn finishes.

## How to get to it (user POV)

- In a robovac turn, the agent calls the Agent tool, in the foreground or with
  `run_in_background`, and the subagent asks permission.

## Driving it with verify.py

Preconditions:

- Both sides launched and their doctor all PASS.
- The scenario is `scenarios/subagents.json`.

- **Foreground prompt.** Step 1 starts a foreground subagent whose `touch fg.txt` is held 26 s.
  Still `fg-waiting`: docked, after `log end waiting on you` (`sub-fg-dock`).
- **Approve it.** Still `fg-approved`: the whole house during the subagent's `sleep 6`,
  after `log start via=again` (`sub-fg-out`). Still `fg-done`: docked (`sub-end`).
- **Background prompt.** Step 3 starts a background agent whose `touch bg.txt` is held 20 s while
  the main agent runs `sleep 3` five times. Still `bg-waiting`: the whole house, with the
  clock showing the main agent's calls going on (`sub-bg-out`).
- **After.** Stills `bg-approved` and `bg-done`. The step waits for two results, the turn's and the
  background agent's report.

## Gotchas

- The `asked` lines name the asking agent. A subagent's request carries its agent id, the main
  agent's says `main`. Compare them across sides before judging.
- A background agent's report can start a turn of its own. Its `start` and `end` rows are part of
  the drive, not noise.
- Subagents run on the model the Agent tool picks, not always haiku, so a side can take longer.
