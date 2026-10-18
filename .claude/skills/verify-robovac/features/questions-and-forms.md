# A question or a form docks it as it opens

A question the agent asks with AskUserQuestion, and a form an MCP server opens, stop the agent's
flow until the person answers, so the robot drives home and docks with its **!** the moment either
one opens, with no six-second notice to wait for as a permission prompt has. Once the person
answers, it goes out again when the call that asked comes back, and docks when the turn finishes.

## Sub-features

- `ask-question-dock` docks the robot as a question opens.
- `ask-question-out` sends it out again when the answered question's call comes back.
- `ask-form-dock` docks it as an MCP form opens.
- `ask-form-out` sends it out again when the form's call comes back.

## How to get to it (user POV)

- In a robovac turn, the agent asks a question with its options, or calls a tool of an MCP server
  that asks for input with a form, and the person answers in the app or the terminal.

## Driving it with verify.py

Preconditions:

- Both sides launched and their doctor all PASS.
- The scenario is `scenarios/questions-and-forms.json`, whose `form` gives the session form.py's
  server; the host answers a question with its first option and fills a form in.

- **Question.** Step 1 asks "Proceed?" and the host answers after 26 s. The clock shows `asked:
  AskUserQuestion`, `hook PermissionRequest AskUserQuestion` and `log end waiting on you` at the
  same second, before the `Notification permission_prompt` about 6 s later (`ask-question-dock`).
  Still `question-waiting`: the camera on the dock, the **!** over it.
- **Its answer.** The clock shows `log answered` and `log start via=again` at the question's
  `PostToolUse`. Still `question-answered`: the whole house, during `sleep 8`
  (`ask-question-out`). Still `question-done`: docked after `end finished`.
- **Form.** Step 3 calls `mcp__form__ask`; its permission is allowed at once, and the host fills the
  form in after 26 s. The clock shows `asked: form server=form`, `hook Elicitation server=form` and
  `log end waiting on you` at the same second (`ask-form-dock`). Still `form-waiting`:
  docked with its **!**.
- **Its answer.** The clock shows `hook ElicitationResult`, then `log start via=again` at
  `mcp__form__ask`'s `PostToolUse`. Still `form-answered`: the whole house, during
  `sleep 8` (`ask-form-out`). Still `form-done`: docked after `end finished`.

## Gotchas

- The form step's first request is the tool's own permission prompt, so its `ask` and `answer`
  anchors are that prompt's; its stills are anchored on that prompt's `ask`, the form's own arrival
  within a second of it.
- A permission prompt answered within about 6 s never docks the robot; the form's tool is allowed
  at once for that reason, so only the form docks it.
- The model's reply is the one input not held fixed: a side that asks a second question, or calls
  the form's tool twice, has a different `asked` line, and the comparison is INCONCLUSIVE.
