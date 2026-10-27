# How to run a verbal quiz

Load this only when the person asks in chat to be quizzed out loud *(kstack: the operator's rule)*.
In a verbal quiz, the person answers out loud, one question at a time, and sees no options. In other
cases, use [quiz-card.md](quiz-card.md) in Claude's app or
[ask-user-question.md](ask-user-question.md) in Claude Code. The rules here are kstack's own, with
no upstream source. [evidence.md](evidence.md) holds the papers cited here.

## Set up the quiz

1. **Pick one branch.** When the person names none, ask which branch.
2. **Draw every question from the branch's tips** and from the cards keyed by those tips' node ids.
   Never add facts the map does not hold, even true ones *(kstack: the operator's rule)*. For a code
   branch, ask what a folder, file, class or function does, or why it exists. Never ask about syntax
   *(kstack: code quizzes help the person remember what things do)*.

## Ask the questions

Do these steps for each tip in the branch, one tip at a time:

1. Ask one question out loud about the tip. Show no options and no hint.
2. Wait for the person's best answer. When the person is unsure, ask for a guess (Huelser &
   Metcalfe, 2012; Grimaldi & Karpicke, 2012). The person can skip, and a skip counts as a miss.
   Say that the skip is marked wrong, and give the right answer, so a guess always beats a skip
   *(kstack: the operator's rule; a person remembers the correction to their own wrong guess
   better than an answer they were given)*.
3. Say yes or no, and give one plain sentence that says why. When the answer is wrong or vague,
   also give the right answer (Rowland, 2014). Write that sentence by the `teach` skill's rules.
4. In the same message, ask the question about the next tip *(kstack: the operator's rule, the
   shortest cycle from answer to feedback)*.

Keep each question and its answer in your own context. Do not show the answer before the person
replies. Ask one question per message.

## Stop

Stop when the person asks to stop, or when you have asked about every tip. To close, name the
branch, and say in one or two sentences which tips the person knew and which they are still unsure
of. Never save the questions or the person's results anywhere *(kstack: a person memorizes saved
questions as questions, and a count of right answers looks like proof that they know the
material)*.
