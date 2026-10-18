# The app's own basics

The Robovac app is an ordinary Mac window. Opened while a run is going, it shows that run's robot
already out sweeping, with no arrival played. Hovering a robot shows its run's one line, the one
`runs.py say` set, and, once the run has stopped, why: Finished, Waiting on you, Interrupted, Its
session closed, Went quiet for twelve hours, or the error it stopped on.

## Sub-features

- `app-opens-going` shows a run already going as a robot already out, the moment the app opens.
- `app-hover-line` shows the run's own line in the slip over a hovered robot.
- `app-hover-why` adds why the run stopped, once it has.
- `app-dock-zoom` zooms the camera in on a robot as it docks; Esc or 0 fits the house again.

## How to get to it (user POV)

- Open Robovac from `~/Applications`, Spotlight or the Dock while a robovac turn runs.
- Move the pointer over a robot.
- Press Esc or 0, or choose View, Fit the House.

## Driving it with verify.py

Preconditions:

- Launch each side with `--later`, so the app is closed when the drive starts.
- The scenario is `scenarios/app-basics.json`.
- Computer-use access to `Robovac Verify` for the hover and the keys.

- **Open mid-run.** Step 1 starts the run with `{runs} say "verifying the app opens on a run
  going"` and `sleep 20`; the scenario opens the app mid-run and the film starts then. Still
  `opened-mid-run`: the whole house with the robot out on its lanes, and the film shows
  no drive from the dock (`app-opens-going`).
- **Hover.** While the run sweeps, take a screenshot with the computer-use tools, find the white
  disc, and hover it. The slip reads the `say` line (`app-hover-line`). After still `docked`,
  hover the docked robot: the slip adds "Finished" (`app-hover-why`).
- **Fit.** Still `docked` shows the zoom (`app-dock-zoom`); press `0` with the computer-use tools
  and screenshot the whole house again.

## Gotchas

- The hover and keys are the person's own input, so they go through the computer-use tools on the
  test copy; the page's `ROBOVAC_KEYS` would press keys from inside and is never set.
- A still before the app opens is marked MISSED; anchor stills after the `open`.
- The film starts at the `open`, so its second 0 is the clock's `film started` line, not 0.
