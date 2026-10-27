# How to walk the person through a map

Load this when the person names a branch of a study map and wants it explained. The walkthrough is
the main use of a map, and quizzes come after it *(kstack: the operator's rule)*. For hover cards,
use [cards.md](cards.md). The rules here are kstack's own, with no upstream source.

## Open the map and wait

When the person runs `/study <scope>`, build the map with the page builder and open it beside the
chat. Then give a one-line overview that names the top branches, and wait for the person to name
one *(kstack: the operator's rule)*.

Open the map in a side panel whenever one exists, so the person can see the map and the chat at
once *(kstack: the operator's rule)*:

- **In Claude's app,** publish the page as an artifact. It opens in the artifact panel. If the
  panel is closed, tell the person where to click to open it.
- **In the Claude Code desktop app,** open the page in the Browser pane. Give the page's path, which
  the person can click, or tell them to press Cmd+Shift+B. You can drive the pane yourself.
- **In a terminal or an SSH session,** there is no side panel. Open the page in the system browser.

## Give the lecture from the top down

Do these steps for the branch the person names:

1. Open the branch on the map, or tell the person which box to click. If the branch is a portal,
   the stacked box, say that clicking it opens the branch's own map, and that the breadcrumb leads
   back.
2. Start at the branch itself. Say in a sentence or two what it is for and how its parts fit.
3. Move down one level at a time. Say which box to click next, then explain each child in the order
   the map shows it.
4. At a pointer leaf, say where the real piece lives, and that its row of triangles on the map
   leads there. When the home is on another map, the row ends at a round portal at the map's
   edge, and clicking the portal opens that map at the home. Explain the piece when the lecture
   reaches its home branch.
5. Stop after a few pieces and wait. The person asks questions and says when to move on. Move on
   only then *(kstack: the operator's rule)*.

Read the source of each piece before you explain it. For code, that is the folder, file, class or
function at the file and line range the tree gives. For a skill or a note, it is the sections the
outline covers. Every fact comes from the source. When the source cannot answer something, say so,
and say which parts you traced and which you infer (`skills/teach/SKILL.md`, "Mark the edges of
what you know"). Explain from the source, not from the cards, because a card can be stale and the
lecture never depends on a card *(kstack: the operator's rule)*.

## Write the lecture for read aloud

The person plays the lecture with read aloud, so the lecture text has to sound right when a voice
reads it *(kstack: the operator's rule)*. Follow these rules:

- Write the way you would talk: conversational and casual, clear, not too technical, and never
  babyish. Follow `skills/teach/SKILL.md` for every sentence.
- Write plain paragraphs. Use no bold labels, tables, headings or bullet lists inside the lecture.
- Use no symbols, arrows or abbreviations that a voice reads badly. Write "returns" in place of an
  arrow and "and" in place of an ampersand.
- Name each piece by its real name, the way you would say it out loud: "the land function in
  gate.py". Keep full paths out of the spoken text and put them in the links (below).
- Define a word the first time you need it. An analogy can give the gist, and then the real name
  takes over (`skills/teach/SKILL.md`, "Analogies land the gist, then hand off").

Claude's app shows the **Read aloud** button on a message only after the turn settles, and a
background agent that is still running can keep the button hidden. While agents run, end each part
of the lecture and then send one short follow-up message, so that part's **Read aloud** button shows
*(kstack: the operator's rule)*.

## Bring in the supporting material

Supporting material is one kind of step. Open it at the point in the lecture where it helps
*(kstack: the operator's rule)*:

- **A reference image** opens in the browser, in the same side panel as the map when there is one.
- **A PDF or a doc** opens beside the chat.
- **A link to every source file the lecture covers** goes in chat, so the person opens the file in
  the app and never searches folders or an IDE for it. In Claude's app, give `computer://` links to
  the files on the person's computer. In Claude Code, give the file paths, which the desktop app
  opens in its panes.

Put the links after the spoken paragraphs of each message, as a short list, so read aloud reaches
them last *(kstack: a voice reads a path as a string of slashes)*.

## Answer questions and close the branch

Answer each question in the same spoken voice, from the source, and answer only the question asked
(`skills/teach/SKILL.md`, "One thing, properly"). If a question belongs to another branch, say
which branch, and offer to go there next.

When the branch is done, say so in one sentence. Offer the next branch, cards for this one as
[cards.md](cards.md) describes, or a quiz on it. For the quiz, use
[quiz-card.md](quiz-card.md) in Claude's app or [ask-user-question.md](ask-user-question.md) in
Claude Code, or [verbal.md](verbal.md) when the person asks to answer out loud.
