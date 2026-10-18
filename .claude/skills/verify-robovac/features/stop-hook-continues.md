# A Stop hook continues the turn

When another Stop hook the person has installed (a loop runner, a checker) refuses to let a turn
end and hands the agent more to do, the turn goes on, but the robot docks at the first Stop, goes
out again with the main agent's next tool call, and docks for good when the turn really ends. A
continuation that only replies, with no tool call, leaves it docked throughout.

## Sub-features

- `stop-dock` docks the robot at the first Stop, though the turn goes on.
- `stop-continue` sends the robot out again at the main agent's first call after a blocked Stop.
- `stop-line` keeps the run's own line through the continuation.
- `stop-end` docks it when the continued turn finishes.

## How to get to it (user POV)

- Install a Stop hook that answers `{"decision": "block", "reason": "..."}`, such as ralph-loop's,
  or one that answers with `hookSpecificOutput.additionalContext`, such as impeccable's, and run a
  robovac turn.

## Driving it with verify.py

Preconditions:

- Both sides launched and their doctor all PASS.
- The scenario is `scenarios/stop-hook-continues.json`, whose `hooks` add verify.py's
  `continue-once`, standing in for the person's own Stop hook: it blocks the first Stop with
  "run sleep 10, then reply continued" and lets every later one go.

- **First Stop.** Step 1 is `/robovac Reply with only the word first.` The clock shows `hook Stop`
  and `log end finished` (`stop-dock`), then the continuation's `hook PreToolUse Bash` and
  `log start via=again` (`stop-continue`).
- **Continuation.** Still `continued`: the whole house, during `sleep 10`.
- **End.** Still `docked`: docked with its **!** after the second `log end finished`
  (`stop-end`).

## Gotchas

- The stand-in is verification scaffolding, written to the drive's settings and gone with the
  scratch folder; the person's own Stop hooks are never loaded.
- The first Stop and the continuation's first call can land within one 2 s read of the log, so
  the app may never show the dock between them; the log rows still show both.
- `stop-line` needs the hover; this drive doesn't reach it.
- The user asked on 2026-10-15 that a turn a Stop hook keeps going not dock at all. On 2026-10-18
  the user kept the dock, the option that adds no delay, so this drive shows the dock and the way
  back out. Keeping the robot out would mean waiting at every turn's end for every Stop hook to
  finish, a median 2.5 s: the time from a turn's last assistant line to its `stop_hook_summary`
  line, over 400 desktop-app turns.
- A Stop hook that keeps a turn going sets `hasOutput` true on that line, with one `hookErrors`
  entry if it blocks or one `hookAdditionalContext` entry if it adds context;
  `preventedContinuation` stays false either way. None of the user's desktop-app turns from
  2026-10-14 to 2026-10-18 (UTC) has them.
