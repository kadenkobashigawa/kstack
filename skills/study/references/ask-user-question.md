# How to run a quiz through AskUserQuestion

Load this when you quiz the person in Claude Code. AskUserQuestion, Claude Code's question tool, is
the default quiz there *(kstack: the operator's rule)*. In Claude's app, use
[quiz-card.md](quiz-card.md). When the person asks to be quizzed out loud, use
[verbal.md](verbal.md) instead. The rules here are kstack's own, with no upstream source.
[evidence.md](evidence.md) holds the papers cited here.

## Pick one branch

Quiz one branch or sub-branch of the map at a time. When the person names none, ask which branch.
Draw every question from that branch's tips and from the cards keyed by those tips' node ids. Never
add facts the map does not hold, even true ones *(kstack: the operator's rule)*. If a branch has no
cards yet, you can write questions only from its tip labels. Tell the person, and offer to write the
cards first.

## Write one set

A set is one call with 4 questions of 4 options each *(kstack: the operator's rule)*. The tool
allows 1 to 4 questions per call and 2 to 4 options per question. If a branch is too small to fill
4 questions, ask fewer. Follow these rules for each question:

- **`question`** asks one thing that a tip or its card states. For a code branch, ask what a folder,
  file, class or function does, or why it exists. Never ask about syntax *(kstack: code quizzes
  help the person remember what things do)*.
- **`header`** names the tip's topic in 12 characters or fewer. It never reveals the answer.
- **Each option's `label`** is one plain answer of a few words. Give each label in a question a
  different text, because the tool returns the picked label and you grade the answer by it. Never
  name other options by letter, such as "A and B". You can use "All of the above" *(kstack: the
  operator's rule)*.
- **Each option's `description`** adds one neutral line of detail. It never hints at which option is
  right.
- **The wrong options** are close distractors taken from sibling tips in the same branch *(kstack:
  the operator's rule)*.
- **The correct option moves.** Put it in a different position from question to question, because
  the tool keeps your order *(kstack: a fixed position shows the answer)*.
- **`multiSelect` stays off,** because each question has one correct answer.
- **No "(Recommended)" label.** Add no hint either, unless the person asks for hints.

The tool always adds an "Other" choice, where the person can answer in their own words. Keep the
correct answer and a short explanation for each question in your own context. Do not show either
before the person answers.

## Grade the answers

The tool returns each picked label, or the person's own words for "Other". Grade each answer by
these rules:

- A picked label is right when it matches the correct option's label.
- An "Other" answer is right when it states the meaning of the correct answer in other words.

Right after the person answers, send one short message with every result *(kstack: the operator's
rule, the shortest cycle from answer to feedback)*. For each question, say right or wrong. For each
missed question, also give the correct answer and one plain sentence that says why *(kstack: the
feedback that follows a missed question is what makes the practice work)* (Rowland, 2014). Write
that sentence by the `teach` skill's rules. Write nothing else between sets.

## Offer the next set

Offer the next set at the end of the results message. Choose the next set by what the person missed:

- If the person missed questions, ask the next set about the same tips again. Reword each question
  and keep its answer. Fill any spare places in the set with tips you have not asked about yet.
  Repeat until the person misses no question in the branch.
- If the person missed none, offer the next branch.
- If a missed question shows that a tip's card is unclear or wrong, tell the person, and offer to
  rewrite that card.

Never save the questions or the person's results anywhere *(kstack: a person memorizes saved
questions as questions, and a count of right answers looks like proof that they know the
material)*.
