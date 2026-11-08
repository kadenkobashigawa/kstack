# Taking notes from a YouTube video

Load this when a lesson draws on a YouTube video: to read its transcript, find the moments that
show each part, and capture still frames for the notes. It runs in the built-in browser, the
Browser pane, often from a background agent while the learner uses the same pane.
[lesson-build.md](lesson-build.md) says when to run it. *(kstack: the operator's rule)*

## Leave the learner's tabs alone

The learner may be watching a video or reading the map in the pane. Never navigate, reload or close
a tab you didn't open.

1. List the tabs first, so you know which ones are the learner's.
2. Open a tab of your own in the background, without bringing it to the front.
3. Do all the work in that tab.

A tab in the background slows its timers. Keep each script short, and split long loops across
several calls. *(kstack: the operator's rule)*

## Keep every video muted and paused

Audio from a tab the learner can't see is a surprise.

- Set the video to muted right after every page load and after every ad, before any seek or play.
- Keep it paused. Seek to a time instead of playing to it.

*(kstack: the operator's rule)*

## Start every video muted

A watch page can start playing before any script in it runs. So mute the player before the page
loads: in your own tab, open `https://www.youtube.com/robots.txt` first, which is on the same site
but has no player, and set

```js
sessionStorage['yt-player-volume'] = JSON.stringify({data: JSON.stringify({volume: 0, muted: true}), creation: Date.now()})
```

Then load the watch page in the same tab. Session storage belongs to that one tab, so the
learner's tabs keep their own sound. The embed page with `mute=1` doesn't help, because its player
loads no video. *(kstack: the operator's rule)*

## Get past ads

YouTube often plays an ad before the video, and the page marks it with the class `ad-showing`.
While that class is present, set the ad video's current time to its length minus a tenth of a
second and play it, still muted, because a paused ad never ends. Then click the skip button if one
shows. Check again every two seconds until the class is
gone. *(kstack: the operator's rule)*

## Read the transcript and the description

1. Expand the description. It holds the chapter list, the credits and any errata the channel
   posted.
2. Click the button labelled "Show transcript". Each line of the transcript panel holds a timestamp
   and the words spoken from that time.
3. Read the lines in order. The panel lists the whole transcript twice, so stop at the second
   `0:00`. Each timestamp is also followed by the same time spelled out ("1 minute, 4 seconds"), so
   strip that out.
4. Save the transcript to a scratch file, not the repository. It's the channel's text, so the notes
   put it in your own words, never copied.
5. Note the video's title, its year and the people its description credits, for the notes' source
   list.

*(kstack: the operator's rule)*

## Keep only diagrams

A frame earns a place in the notes only when it is a diagram or an animation of the thing itself: a
part, a circuit, a flow of charge, a labelled cutaway. Lecture slides, title cards, screens of code or
program output, and frames that show people, such as a presenter or a host, never go in the notes. Never draw a diagram yourself, in
text art, Mermaid or a rendered image: every picture comes from a source. When no video has a
diagram for a part, leave the part without a picture. *(kstack: the operator's rule)*

## Pick the moments

Use the transcript and the chapter list to choose the moments that show each part of the lesson.
For each moment, capture small candidate frames, 640 pixels wide, at that second and three seconds
later. Name each one `c` and its second, such as `c0186` for 3:06. Then run
`uv run $S/frames.py sheet <candidate folder> <sheet folder>` to lay them out on contact sheets
labelled with their times, and look at each sheet. Keep the frames that show the thing clearly,
and drop any frame with an ad, a blur or a half-finished transition. *(kstack: the operator's
rule)*

## Capture a frame

1. Seek the video to the chosen second, and wait for the `seeked` event plus about 900
   milliseconds, so the frame finishes drawing.
2. Draw the video onto a canvas 1,280 pixels wide, and read the canvas back as a JPEG.
3. Send the frames out of the page by **form POST** to the receiver. Start it in the background
   first with `uv run $S/frames.py receive <scratch folder>`. It listens on port 8765 and writes a
   field named `<folder>__<name>` to `<scratch folder>/<folder>/<name>.jpg`.
   YouTube's security policy blocks scripts on its pages from sending data straight to the
   computer, but it allows a form to be submitted. Submitting the form moves the tab to a different
   page, so collect every frame first, then submit once.
4. Look at each saved frame before keeping it.
5. Move the frames to keep into the course's frame folder, named in order with a short description,
   such as `03-gate-and-channel.jpg`.

*(kstack: the operator's rule)*

## Credit every frame

- **Under each frame, add one caption line** that names the channel and the video and links to the
  exact second: `*Frame at [m:ss](<video URL>&t=<seconds>s) from <channel>, "<title>" (<year>).*`
- **Each frame folder holds a `SOURCE.md`** that names the video, its year, its link and the people
  its description credits.
- **Frames are the channel's work.** Keep them in a private repository as study references, and
  never publish them.

*(kstack: the operator's rule)*

## Clean up

Stop the receiver and close your tab. Candidate frames and contact sheets stay in the scratch
folder. *(kstack: the operator's rule)*
