# How to write, save and refresh hover cards

Load this when the person asks for cards on a map or a branch. The page builder builds every map
bare, and you write cards only when the person asks *(kstack: the operator's rule)*. For the
lecture, use [walkthrough.md](walkthrough.md). The rules here are kstack's own, with no upstream
source.

## Know what a card holds

A card explains one tip, the end of a branch, in a box that opens when the person hovers the tip.
Follow these rules for every card *(kstack: the operator's rule)*:

- **One card per tip.** A tip is a node with no children, or one whose children are all pointer
  leaves. Any other node with children never gets a card, and the page builder refuses one.
- **A pointer leaf gets no card.** A pointer leaf is a childless node that links to the shared
  piece's home. Hovering it lights its row of triangles to the home node, or to the home's vortex
  portal when the home is on another map, and the home node holds the card.
- **The card is about its tip only.** It names no callers, no sibling tips and no other branch,
  and it gives no file or line numbers.
- **The card stands alone.** Write it from the source, never from the lecture, so it reads right
  for someone who never heard the lecture.

## Write each card

Do these steps for each tip that needs a card:

1. Read the tip's source. For code, that is the function or class body, read at the file and line
   range the tree gives. For a skill or a note, it is the section the tip covers.
2. Read the tip's path from the root down to the tip, as someone who has never seen the source.
   List the questions the path raises: a word nobody defined, a missing reason, a jump between
   steps.
3. Answer those questions in 3 to 5 lines of about 60 to 90 words in all, one idea per line. Open
   each line with a short bold lead phrase.
4. Define a term before you lean on it. You can use an analogy, but always next to the real names
   (`skills/teach/SKILL.md`, "Analogies land the gist, then hand off").
5. Take every fact from the source. When the source cannot answer a question the path raises, say
   so on the card.

Write every card by `skills/teach/SKILL.md`, with no em or en dashes. Use the real names for code,
because the card helps the person read the code itself.

## Save cards and reuse them

All the maps of a set share one cards file, `$W/cards.json` in the folder that SKILL.md names. The
file is one JSON object of node id to card text, and no two nodes in a set share an id *(kstack:
the operator's rule)*. A card's id is its node's id:

- For a node from `tree.py`, the id is the repo-relative path, such as
  `skills/build/scripts/gate.py/land`.
- For a node of a Markdown outline, the id is the one you gave the node in the outline.

Separate the lines of a card with `\n`. Bold, written as `**lead phrase**`, is the only markup the
page keeps.

Write each card once, save it, and reuse it every time the map opens *(kstack: the operator's
rule)*. Never commit cards to the repo.

After you save, rebuild the page with the page builder. It refuses a card on a pointer leaf or on a
node with a child that is no pointer leaf, and it warns about an id that names no node. Fix each
one, and rebuild until the page builder reports no refusal and no warning.

A card whose id names no node usually belongs to a node that was renamed or moved. Tell the person
which card it is, and offer to move it to the node that now covers its source. Never drop the card
without saying so, and never leave it under the old id *(kstack: the operator's rule)*.

## Fan out when there are many tips

For more than about 20 tips, give the work to subagents *(kstack: the threshold the earlier
study-map skill used)*:

1. Start one subagent per file, or per sub-map for a skill or a note.
2. Give each subagent this file, the ids of its tips, and the file and line range or the section of
   each tip.
3. Have each subagent return its cards as an object of node id to card text.
4. Read every returned card against its tip's source yourself before you save it. Rewrite a card
   that adds a fact the source lacks or that leaves its tip *(kstack: a subagent works without the
   rest of the map in view)*.

## Rewrite a card only when asked

A saved card stays as written until the person asks you to rewrite it *(kstack: the operator's
rule)*. If you see that a card no longer matches its tip's source, tell the person, and explain the
tip from its current source.
