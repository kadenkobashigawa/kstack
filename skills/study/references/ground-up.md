# Teaching from the ground up

Load this when the person wants to learn a system from its foundations rather than from the top
down, such as building a computer from electricity upward. It decides what gets taught next and
how a lesson splits into parts. For delivering a lesson, use [lecture.md](lecture.md). For building
a lesson before it's taught, use [lesson-build.md](lesson-build.md). *(kstack: the operator's
rule)*

## Teach things in the order they're built

Every idea has a physical form, and nothing can be built before the things it's made of. So the
next lesson is always the lowest thing not yet covered that the goal depends on. A processor comes
late, because it's made of logic gates, which are made of transistors, which only make sense once
electricity does. The test for what comes next never changes. Ask what has to exist before this
one. *(kstack: the operator's rule)*

## Assume the learner knows nothing

Every word in a lesson is either everyday English or a term an earlier lesson explained. If a
lesson needs a word that no earlier lesson explained, that word gets its own lesson or part first.
An expert can't see their own jargon, so check each word, not just each idea (teach, "Use only
words the reader has"; Hinds, 1999). *(kstack: the operator's rule)*

## Describe the real thing, with no analogies

Say what the electrons, wires and switches do. An analogy gives the learner a second picture to
unlearn later. The real mechanism is usually short enough to say directly. This rule overrides
teach's "Analogies land the gist, then hand off" for ground-up teaching. *(kstack: the operator's
rule)*

## Each lesson unlocks one working idea, and the next lesson builds on it

A lesson ends with one working idea the learner can use, such as "a wire is either on or off". The
next lesson starts from that idea and uses it to build something new. In a computer course, the
first lesson unlocks current. The transistor's parts then use current to build the gate, and then
each kind of transistor. *(kstack: the operator's rule)*

## Break a lesson down until every piece rests on something taught

1. Name, in one sentence, the working idea the lesson unlocks.
2. List the pieces that the thing is physically made of, and what each piece does.
3. Check each piece, and each word it needs, against the lessons already taught.
4. Any piece or word not yet covered becomes a part of this lesson, placed before the part that
   needs it. Repeat steps 2 to 4 for the new parts until nothing is left uncovered.
5. Order the parts so that each part uses only the parts before it, with one new idea per part. A
   part that needs two new ideas splits in two. The last part puts the pieces together into the
   working idea the lesson unlocks.

For example, a transistor needs silicon that conducts only when the gate has a voltage on it. That
silicon is doped, and doping hadn't been taught yet. So doping became its own part, placed before
the two kinds of transistor. *(kstack: the operator's rule)*

## Teach one part per lecture

Covering a whole branch in one reply skims it. The learner remembers the names but not how the
parts work. *(kstack: the operator's rule)*
