# How to run a quiz on the quiz card

Load this when you quiz the person in Claude's app. The quiz card, the `quiz_display_v0` tool, is
the default quiz there *(kstack: the operator's rule)*. In Claude Code, use
[ask-user-question.md](ask-user-question.md). When the person asks to be quizzed out loud, use
[verbal.md](verbal.md) instead. The rules here are kstack's own, with no upstream source.
[evidence.md](evidence.md) holds the papers cited here.

## Pick one branch

Quiz one branch or sub-branch of the map at a time. When the person names none, ask which branch.
Draw every question from that branch's tips and from the cards keyed by those tips' node ids. Never
add facts the map does not hold, even true ones *(kstack: the operator's rule)*. If a branch has no
cards yet, you can write questions only from its tip labels. Tell the person, and offer to write the
cards first.

## Write the questions

Write 5 questions, unless the person asks for a different number *(kstack: the operator's rule)*.
Follow these rules for each question:

- **The prompt** asks one thing that a tip or its card states. For a code branch, ask what a folder,
  file, class or function does, or why it exists. Never ask about syntax *(kstack: code quizzes
  help the person remember what things do)*.
- **The options** are four or five plain answers. The correct one is the single best answer. The
  wrong ones are close distractors taken from sibling tips in the same branch, so the person has to
  tell similar tips apart *(kstack: the operator's rule)*.
- **No option names other options by letter,** such as "A and B". The quiz card shuffles the
  options, so after the shuffle the letters point at the wrong options. You can use "All of the
  above", because it reads correctly in any position *(kstack: the operator's rule)*.
- **The feedback lines** go in `correct_feedback` and `incorrect_feedback`. Write a short custom
  line for each. Vary the lines across questions, and keep the line for a wrong answer encouraging.
- **The explanation** says in one or two plain sentences why the answer is right (Rowland, 2014).
  Write it by the `teach` skill's rules: use the real names, and use no jargon that the tip's card
  did not define.
- **No hint.** Add `hint` only when the person asks for hints *(kstack: the operator's rule)*.

## Make the call

Set `question_type: "multiple_choice"` on each question. Give each question an `id`, such as `q1`,
and its `options` as `{id, text}` pairs. Set its `correct_option_id` to the `id` of the correct
option. Give the quiz a `title` that names the branch. Give it a `summary` of fewer than 45
characters with no closing period, such as `5-question quiz on the gate`.

If the person asks to review, to memorize, or for flashcards, set `initial_mode: "flashcards"`. In
flashcard mode, write each explanation so that it gives the answer and says why. The distractors can
be easy *(kstack: the operator's rule)*.

## Offer the next quiz

The quiz card has its own retake button, which asks all 5 questions again. Leave it as it is
*(kstack: the operator's rule)*.

The quiz card does not tell you the person's answers. When the person finishes, offer the next
branch, or this branch again in flashcard mode. If the person says a question showed that a tip's
card is unclear or wrong, offer to rewrite that card.

Never save the questions or the person's results anywhere *(kstack: a person memorizes saved
questions as questions, and a count of right answers looks like proof that they know the
material)*.
