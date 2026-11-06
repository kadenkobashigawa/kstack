# Building a lesson before it's taught

Load this before the first lecture of a lesson, when the person learns from notes and a map that
should already hold the whole lesson. Everything for the lesson is ready before its first lecture
plays. The learner then opens the lesson one map branch at a time. [ground-up.md](ground-up.md)
decides what the lesson is and how it splits into parts. [lecture.md](lecture.md) delivers it.
*(kstack: the operator's rule)*

## Build the lesson in this order

1. **Plan the parts** as [ground-up.md](ground-up.md) describes. Name the working idea the lesson
   unlocks, break it down until every piece rests on something already taught, and order the
   parts.
2. **Check every claim against a source you open.** Use a textbook, official docs, a
   manufacturer's page or a university course. Where a source says something different from the
   plan, the source wins, and the plan changes before anything is written. A claim that no source
   supports stays out of the notes. Raise it with the person in chat instead.
3. **Find the moment in the video that shows each part, and capture its frames,** as
   [video-capture.md](video-capture.md) describes. When no video shows a part, use the best diagram
   instead, or leave the part without a picture.
4. **Write the notes for every part,** following "Write lecture notes, not a ledger" below. Place
   each frame in its part, with a caption.
5. **Build the map boxes for every part from those notes,** as [map-style.md](map-style.md)
   describes. The notes and the map say the same things, in the same order. The map says them in
   shorter sentences.
6. **Run the unslop and technical-writing passes** over the notes and the map boxes. Teach wins
   where they disagree.

*(kstack: the operator's rule)*

## Write lecture notes, not a ledger

The notes are what the learner studies from. They hold only the lesson: what each thing is, how it
works, and its pictures. They never hold the builder's working notes. That means no record of what
has or hasn't been taught, no explanation of how a number was worked out, and no note on which
source left something out or where a video's narration and screen disagree. They also hold no
*Inferred* labels and no remarks about the course's own choices. Put all of that in chat. In the
notes, state the correct fact and leave the bookkeeping out. *(kstack: the operator's rule)*

- **The full source list goes at the top** of the notes. Each lesson ends with one short Sources
  line that names what it drew on.
- **Each frame gets a caption** that names the video and links to the second the frame comes from,
  as [video-capture.md](video-capture.md) describes.

## Let background agents do the heavy work

Research, notes and frame capture can run in background agents while the learner studies. Only one
agent edits a notes file at a time. When two agents need the same file, have one write a draft
somewhere else, then merge the draft yourself. An agent that uses the browser follows
[video-capture.md](video-capture.md), and its brief says so. *(kstack: the operator's rule)*
