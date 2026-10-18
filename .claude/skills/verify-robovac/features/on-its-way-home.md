# Sent out on its way home

A robot driving home from a turn that just ended keeps going until it has docked, and only then goes
back out for the turn that started on its way, as a robot vacuum empties its bin mid-pass: it never
turns round on the route. Docking on the way back out shows no **!** and no zoom.

## Sub-features

- `home-first` keeps a robot driving home on its way when a new turn starts, until it docks.
- `home-out` sends it straight back out from its dock, with no **!** and no zoom.

## How to get to it (user POV)

- Send a robovac session its next prompt within a few seconds of its last turn's end, while the
  robot is still driving home.

## Driving it with verify.py

Preconditions:

- Both sides launched and their doctor all PASS.
- The scenario is `scenarios/on-its-way-home.json`.

- **The first turn ends.** Step 1 replies at once; the clock shows `log end finished`, and the film
  shows the robot turning for home.
- **A turn starts on the way.** Step 3 starts just after step 1's result, with `log start via=again`
  in the clock while the robot drives home. Still `on-its-way`: the whole house. The
  film shows the robot carry on to its dock and back in (`home-first`), with no **!** over it and
  the camera still on the whole house, then drive out again (`home-out`); still `out-again`
  shows it on its lanes during the step's 20 s wait.
- **End.** Still `docked`: docked with its **!** after `end finished`.

## Gotchas

- The proof is the film between `on-its-way` and `out-again`: a still shows where the robot is, not
  which way it is driving.
- The robot reaches its dock by where it was, so a robot near its dock can dock before the second
  turn starts, and the drive shows nothing; read the film for where it was at step 1's end.
- The 20 s wait is Python's: Claude Code refuses a standalone foreground `sleep 30` ("Blocked:
  standalone sleep 30", seen 2026-10-18), and where its limit lies below that is not measured.
