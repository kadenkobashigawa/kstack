# The run follows its turn

A session becomes a robovac session when a prompt starts with `/robovac`, or `/loop`, an interval
and then `/robovac`, and its robot has two states: out sweeping while its agent works, and docked
with its **!** when nothing works or something waits on the person. This feature is the plain turn:
the robot leaves its dock as a turn starts, sweeps however long the turn thinks or a tool runs, and
drives home to dock with its **!** when the turn finishes with nothing left running, as the camera
zooms in on it. A prompt that only mentions `/robovac` starts nothing. Background work, questions
and forms, and a turn starting while the robot drives home are features of their own.

## Sub-features

- `turn-mention` starts no run for a prompt that only mentions `/robovac`.
- `turn-start` sends a robot out at a prompt that starts with `/robovac`.
- `turn-sweep` keeps it sweeping through every tool call of the turn.
- `turn-dock` docks it with its **!** and zooms the camera in on it when the turn finishes with no
  background work running.
- `turn-again` sends it out again at the session's next prompt, in the same suite.
- `turn-say` gives the run the line `runs.py say` set, which the hover shows.

## How to get to it (user POV)

- Type `/robovac`, `/robovac <file or folder>`, or `/loop 12h /robovac` in a Claude Code session.
- In the Desktop app, type `/loop 12h run the robovac skill`, where the Skill tool starts the run.
- Open the Robovac app from `~/Applications`, Spotlight or the Dock.

## Driving it with verify.py

Preconditions:

- Both sides launched and their doctor all PASS.
- The scenario is `scenarios/run-follows-turn.json`.

- **Mention only.** Step 1 asks "is /robovac a command?". Still `mention-only`: no robot out, and
  the clock shows no `log start` (`turn-mention`).
- **Start.** Step 2 starts with `/robovac`, sets the line with `{runs} say`, and runs `sleep 6`
  twice. The clock shows `log start via=prompt` and `log say` (`turn-start`, `turn-say`). Stills
  `sweeping` and `still-sweeping`: the whole house (`turn-sweep`).
- **Dock.** Still `docked`: the camera on the dock, the **!** over it, after
  `log end finished` (`turn-dock`).
- **Again.** Step 4 is a plain prompt. Still `next-prompt-sweeps`: the whole house after
  `log start via=again`; still `docked-again` after its end (`turn-again`).

## Gotchas

- The Skill tool's path (`/loop ... run the robovac skill`) needs the robovac skill loaded, which
  the drive session doesn't load; this map reaches only the typed `/robovac`.
- `/robovac-widget` and `/loop 5m check /robovac` are mentions, not starts: runs.py's own tests
  hold those cases, not this drive.
- A run's suite stays ten minutes after it stops; a second claim within that time in the same app
  isn't fresh, so launch a new claim, which opens a new test copy.
