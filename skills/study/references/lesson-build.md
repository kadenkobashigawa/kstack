# Building a lesson before it's taught

Load this before the first lecture of a lesson, when the person learns from notes and a map that
should already hold the whole lesson. Everything for the lesson is ready before its first lecture
plays. [ground-up.md](ground-up.md) decides what the lesson is and how it splits into parts.
[lecture.md](lecture.md) delivers it. *(kstack: the operator's rule)*

## Build the lesson in this order

1. **Plan the parts** as [ground-up.md](ground-up.md) describes.
2. **Check every claim against a source you open,** such as a textbook, official docs, a
   manufacturer's page or a university course. Where a source says something different from the
   plan, the source wins, and the plan changes before anything is written. A claim that no source
   supports stays out of the notes. Raise it with the person in chat instead.
3. **Find the moment in the video that shows each part, and capture its frames,** as
   [video-capture.md](video-capture.md) describes. When no video shows a part, use the best diagram
   instead, or leave the part without a picture.
4. **Write the notes for every part,** following "Write lecture notes, not a ledger" below. Place
   each frame in its part, with the caption that [video-capture.md](video-capture.md) describes.
5. **Build the map boxes for every part from those notes,** as [map-style.md](map-style.md)
   describes.
6. **Run the unslop and technical-writing passes** over the notes and the map boxes. Teach wins
   where they disagree.

*(kstack: the operator's rule)*

## Write lecture notes, not a ledger

The notes are what the learner studies from. They hold only the lesson: what each thing is, how it
works, and its pictures. They never hold the builder's working notes. That means no record of what
has or hasn't been taught, no explanation of how a number was worked out, and no note on which
source left something out or where a video's narration and screen disagree. They also hold no
*Inferred* labels and no remarks about the course's own choices. Put all of that in chat. In the
notes, state the correct fact and leave the bookkeeping out. The unit's front page holds, in order,
a summary, the lesson list, links to any reference pages, and the full source list at the bottom.
Each lesson ends with one short Sources line that names what it drew on.
*(kstack: the operator's rule)*

## Let background agents do the heavy work

Research, notes and frame capture can run in background agents while the learner studies. Only one
agent edits a notes file at a time. When two agents need the same file, have one write a draft
somewhere else, then merge the draft yourself. An agent that uses the browser follows
[video-capture.md](video-capture.md), and its brief says so. *(kstack: the operator's rule)*

## Add the lesson's terms to the glossary

The unit keeps one glossary page. Each lesson adds the terms it teaches under its own heading,
`## Lesson N: <title>`, in the order the lesson introduces them. Each row holds one term, and its
meaning is one full sentence ending in a period, such as "An atom is the tiny particle all matter
is made of." Spell out every abbreviation in the term or its meaning. *(kstack: the operator's
rule)*

## Brief a build agent from this template

A build agent knows only its brief, so the brief carries everything. Fill in the angle brackets.

```text
Build Lesson <N>, "<title>", of <course> before it is taught. Don't commit.

Read first, in full: ground-up.md, lesson-build.md, video-capture.md and map-style.md in
~/kstack/skills/study/references/, then <the course's own study rules>, then the lessons already
taught: <paths>. Every word in this lesson is everyday English or taught there or earlier in this
lesson. <What the learner already knows, in one or two lines.>

What the lesson should unlock: <one sentence, plus a rough outline>. Plan the parts with
ground-up.md's breakdown, change the outline if the breakdown or the sources say so, and say what
you changed and why.

Sources and video: check every claim against a source you open. Candidate videos: <URLs and
timestamps, if known>. Any channel with clear diagrams is fine. Capture frames per video-capture.md,
in your own background tab with the video muted and paused the whole time, because the learner
may be watching another tab. Never touch other tabs. Keepers go to <asset folder>, numbered after
<the last existing number>.

Deliverables:
1. <lesson file path>, shaped like <the previous lesson file>. Run both writing passes.
2. New source entries in <draft path>/lesson<N>-sources.md.
3. New glossary rows in <draft path>/lesson<N>-terms.md.
4. The map node in <draft path>/lesson<N>-map.json, ids starting <unit id>/<slug>/, per
   map-style.md. Run both writing passes over the box text.
5. The video moment per part in <draft path>/lesson<N>-moments.md.
Don't edit the unit's front page or glossary; another agent may be editing them.

Reply briefly: the final part list, what you changed from the outline and why, the sources used,
anything a source contradicted, the frames captured, and the moment per part.
```

*(kstack: the operator's rule)*

## Merge the lesson in

When the build agent reports back:

1. Read its report for anything a source contradicted or anything it left out, and raise those
   with the learner.
2. Link the lesson from the unit's front page, and add its source entries to the source list at the
   bottom.
3. Add its glossary rows under a new heading for the lesson.
4. Add its map node after the previous lesson's node, rebuild the map, reopen what the learner had
   open, and zoom to the new lesson, as [map-style.md](map-style.md) describes.
5. Commit, then tell the learner in a few lines what the lesson's parts are and what is ready.

*(kstack: the operator's rule)*
