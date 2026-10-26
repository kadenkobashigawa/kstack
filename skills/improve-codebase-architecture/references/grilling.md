# Grilling

From Matt Pocock's skills (MIT), `upstream/mattpocock-skills/skills/productivity/grilling/SKILL.md`, as written except where marked *(kstack)*. Upstream's skill frontmatter is dropped *(kstack: this file is read as a reference, not loaded as a skill)*. The design tree, the frontier, rounds, recommendations and the split between facts and decisions are upstream's. How a round reaches the user is kstack's: through AskUserQuestion, where upstream writes it as chat text.

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

## Asking a round through AskUserQuestion *(kstack)*

Upstream formats a round as numbered chat text, each question followed by a `➡️` line with the recommended answer, and each worded so that "yes" accepts it. Here a round is one or more AskUserQuestion calls, mapped like this:

- **One call holds up to four questions.** A frontier of more than four goes out as back-to-back calls within the same round, and the frontier is recomputed only after the last one returns. The split is for the tool's limit, never by dependence, since nothing in a round depends on another question in it. Numbering isn't needed: each question gets its own answer.
- **`question` carries the whole question**, including the body upstream writes after the title. That body is the context the user needs to decide. When that context needs more room than a question has (a diagram, a code sketch, a long comparison), write it in chat in the same message, just before the call.
- **`header` is the question's title**, twelve characters at most.
- **The recommended answer is the first option, with "(Recommended)" after its label.** It stands in for upstream's `➡️` line, and picking it is upstream's "yes". Its description says why it's your pick.
- **The other options are the real alternatives**, two to four options in all, each description saying what choosing it commits the design to. Don't pad to four, and don't add a strawman to make the recommendation look good.
- **An open question stays open.** Upstream turns the question tool down partly because pickers push the model toward multiple choice with pre-baked answers (mattpocock-skills, `.out-of-scope/native-question-tool.md`, l. 9). So when a question has no short list of answers, ask it as the open question it is. Offer your recommendation and the closest real alternative, and say in the question that "Other" takes an answer in the user's own words. An "Other" answer outranks your options: take it as written.
- **`preview` shows shapes side by side.** When the options are alternative interfaces or before/after code, put a short sketch of each in its option's preview.
- **`multiSelect` only when the options aren't exclusive**, such as which callers must keep working. The tool shows no previews on a multiSelect question, so put any sketch in chat before the call, and name your recommended set in the question text.
- **One question at a time, if the user's instructions ask for it.** Then each call carries one question. Upstream's docs name a `CLAUDE.md` line, "When grilling, ask one question at a time.", as the supported way back (mattpocock-skills, `docs/productivity/grilling.md`, l. 49).

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.

*(kstack)* Ask for that confirmation through AskUserQuestion too, after a short list of the settled decisions in chat. It has two options: "Shared" confirms, and "Not yet" reopens the tree. A picked option comes back as its bare label, with no note from the user. So after "Not yet", the next question asks which branch to reopen. Its options are the settled branches most likely to need it, and "Other" names any other branch. Neither is marked "(Recommended)", because whether the understanding is shared is the user's to say.
