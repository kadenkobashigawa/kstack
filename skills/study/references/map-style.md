# Writing a map that reads like the notes

Load this when a map grows with a course, lesson by lesson, and the learner reads it as a summary of
the notes. It sets what the map holds, how each box is worded, and how to move the map when the
learner asks. *(kstack: the operator's rule)*

## Show what's been taught, plus the current lesson

The map holds the lessons taught so far and the current lesson in full. The current lesson's boxes
are all built before its first lecture ([lesson-build.md](lesson-build.md)), and the learner opens
them branch by branch as the lectures go. Nothing from a later lesson goes on the map. *(kstack:
the operator's rule)*

## Word every box as a name or a sentence

- **Unit, lesson and part boxes are names in Title Case,** such as "Part 2: The Gate".
- **Every other box is one or two full sentences ending in a period,** such as "Like charges push
  each other apart." A topic name like "Charge" says what a branch is about but teaches nothing.

This rule replaces the Title Case labels that "Write an outline Document" in SKILL.md asks for, for
a map of this kind. *(kstack: the operator's rule)*

## Put one idea in each box

- **One idea per box.** "Current is a flow of electrons along a wire. It is measured in amps." is
  one box. The unit is part of the same idea, so it doesn't get a child box of its own.
- **A box never has exactly one child.** A new layer is a group of two or more details that open up
  the box above it. One appended fact belongs in the box above.
- **Break each lesson down layer by layer** until every box at the bottom is one point the learner
  understands.

*(kstack: the operator's rule)*

## Follow the notes

The boxes say what the notes say, in the same order, in shorter sentences. Build the boxes from the
finished notes, never the other way round. *(kstack: the operator's rule)*

## Keep ids fixed

Start each id with the unit, such as `u01/transistor/gate`, and never change an id, so saved cards
carry over as the map grows. The map holds text only. Pictures live in the notes. *(kstack: the
operator's rule)*

## Move the map only when asked, without dragging

The page adds a glide after a fast drag, so a drag lands past where it was aimed. To centre a
branch, use a script:

1. Measure the branch's boxes with `getBoundingClientRect`.
2. Send the page a slow drag of exactly the offset: a `mousedown` on `#mmR`, ten `mousemove` events
   16 milliseconds apart, a pause of 150 milliseconds, then `mouseup`. The page skips the glide
   when the mouse rests for more than 80 milliseconds before release.
3. Take a screenshot to check the result.

Opening the map file again in the Browser pane opens a new tab, so close the old one.

**After every rebuild, reopen the map where the learner is.** Reloading the page closes every
branch. So after each rebuild, open the path down to the current part: for each box from the root
to that part, dispatch a `click` on the first `div` inside the box's `foreignObject` (search
`#mmR` and `#mmL`, and skip copies with zero width), waiting about 800 milliseconds between clicks.
Then click the page's Fit button (`#bFit`) and take a screenshot to check. *(kstack: the operator's
rule)*
