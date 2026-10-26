# The wait on a permission prompt

When a robovac turn asks permission and the person leaves the prompt unanswered for about six
seconds, the robot drives home and docks with its **!**, since the agent is waiting on them. Once
they allow it, the robot goes out again when the approved tool's result comes back, and docks again
when the turn finishes.

## Sub-features

- `wait-dock` docks the robot after the prompt's notice, about 6 s after the prompt opened.
- `wait-quick` leaves the robot out for a prompt answered within those 6 s.
- `wait-out` sends the robot out again when the approved tool's result arrives.
- `wait-why` shows "Waiting on you" as the hover's why while docked in the wait.
- `wait-two` keeps it docked until the last of two prompts waiting at once is answered.

## How to get to it (user POV)

- In a robovac session, a turn calls a tool the person's settings don't allow, and Claude Code
  shows its permission prompt. The person answers it late, in the app or the terminal.

## Driving it with verify.py

Preconditions:

- Both sides launched and their doctor all PASS.
- The scenario is `scenarios/wait-on-prompt.json`, unchanged across sides.

- **Start the session.** Step 1 sends `/robovac Use the Bash tool to run exactly: {runs} say ...`.
  Its `say` prompt is allowed at once (`wait-quick`): the clock shows no `end waiting on you`
  before `end finished`. Still `first-turn-done`: docked with its **!**.
- **Ask and hold.** Step 3 asks to `touch waited.txt`. The scenario holds the answer 30 s.
  Still `asked`: the whole house, the run going. The clock shows `Notification
  permission_prompt` and `log end waiting on you` about 6 s after the `asked` line (`wait-dock`).
- **In the wait.** Still `in-the-wait`: the camera on the dock, the **!** over it.
- **Approve.** The scenario allows at 30 s. The clock shows `log start via=again` at the touch's
  PostToolUse or its PostToolBatch, which come together for one call (`wait-out`). Still
  `after-approval`: the whole house, during `sleep 8`.
- **Turn ends.** Still `turn-done`: docked with its **!** after `end finished`. The
  clock's last line lists `waited.txt`, the approved command's side effect.
- **Proof.** `python3 $V diff "$E"`, then read each still beside its clock line on both sides.

## Gotchas

- `sleep` is a command Claude Code allows without asking, so the scenario's second Bash runs with no
  prompt. A command that does prompt would open a second wait.
- `wait-why` and `wait-two` need the hover and a two-prompt scenario. This drive doesn't reach them.
- The model's reply is the one input not held fixed: if one side's clock shows a different command
  asked, or a second `asked`, the comparison is INCONCLUSIVE.
