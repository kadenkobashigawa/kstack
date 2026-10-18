---
name: robovac widget
description: A lamplit storybook room seen from straight above, where a Roborock sweeps while a robovac run is going.
colors:
  line-cocoa: "#6c4a3a"
  wall-cocoa: "#3f322c"
  oak-50: "#f6e6c8"
  oak-100: "#efd6a8"
  oak-200: "#e3c08b"
  oak-300: "#d0a46f"
  oak-500: "#a87b52"
  walnut-300: "#a66f4b"
  walnut-500: "#7d5038"
  walnut-700: "#5a3a2b"
  linen-50: "#fcf7ee"
  linen-200: "#efe4d2"
  linen-400: "#dbcab0"
  soft-black: "#3d3633"
  chrome-50: "#f1f3f2"
  chrome-200: "#d3d8d8"
  chrome-400: "#a5adae"
  chrome-700: "#6d7577"
  leaf-200: "#bcd59c"
  leaf-400: "#88b26f"
  leaf-600: "#5f8d55"
  leaf-800: "#41673f"
  cognac-400: "#dba25e"
  glass: "#d7e6e4"
  lamp-glow: "#ffe2a6"
  lamp-core: "#fff7e4"
  robot-white: "#fdfdfb"
  robot-grey: "#dfe1e1"
  dock-white: "#fafaf7"
  dock-grey: "#d4d6d5"
rounded:
  window: "system"
---

# Design System: robovac widget

## Overview

**Creative North Star: "The Lamplit Plan, told like a storybook"**

The look is a rendered floor plan of a home someone lives in, drawn in Cats & Soup's hand: thin
warm-brown lines, flat muted colour, soft rounded shapes and tiny white highlights. The widget shows
the house straight from above, on glass. Thick cocoa walls frame each room. Inside are polished
light oak, white linen, soft-black and chrome fittings, and plants spilling over edges, lit by lamp
pools. The robot drives and little else stirs: leaves, curtains, a cat's ear and lamp glow move
slowly (see Motion).

The arrangement comes from rendered presentation plans (Boyko, Scaline, Wade-DeBeer, Foulli): no
labels, no dimensions, no hatching. The hand comes from Cats & Soup (HIDEA): children's-book
softness, every shape a little chubby, nothing sharp or glossy.

**Key Characteristics:**
- Straight overhead, orthographic, one scale everywhere.
- Thin hand line in warm brown, with flat fills and one shade shape per form.
- Muted, warm and soft: no pure black or white, no saturated colour.
- One light, warm, from the upper left.
- Lived-in detail: duvets askew, throws, leaves over edges, a cat asleep somewhere.

## Colors

Muted honey oak carries the room. Cocoa, linen, soft black, chrome and sage-leaf green are the
other fields, and warm lamp light is the one glow. Every value is pulled toward warm and
desaturated, the way Cats & Soup's palette is.

### Primary
- **Honey Oak** (oak-50 to oak-500): the floor, about 60% of every room.

### Secondary
- **Cocoa** (line-cocoa #6c4a3a, wall-cocoa #3f322c): every line, and the walls. The line colour
  is sampled from Cats & Soup's own line work.
- **Linen** (linen-50 to linen-400): bedding, upholstery, white ceramics.
- **Soft Black and Chrome** (soft-black, chrome-50 to chrome-700): lamp bases, legs, the laptop
  and taps. Chrome is a soft grey with one white glint, never mirror-hard.
- **Walnut** (walnut-300 to walnut-700): desks and nightstands, set against the oak.

### Tertiary
- **Leaf** (leaf-200 to leaf-800): every plant. Each leaf has three values: lit edge, body and
  underlap.
- **Cognac** (#dba25e): textile accents, the aim being at most two per room. The furnisher picks
  each piece's colour on its own and nothing caps cognac, so the shipped houses run over it:
  measured on houses 1, 12 and 14 (2026-10-17), 14 of the 81 rooms carry more than two pieces in
  cognac, up to five (10 of them if a pair of poufs counts once). House 12's living room at spot 6
  has a sofa and two armchairs in it; house 14's bedroom at spot 2 has a bed, a desk chair, an
  armchair and a basket.

### Light
- **Lamp Glow** and **Lamp Core**: soft radial pools under lamps. Nothing else glows.

### The robot and dock
Drawn true to the Roborock Qrevo Curv 2 Flow (see PRODUCT.md), in the same soft hand.

### Named Rules
**The One Light Rule.** Light comes from the upper left, plus the lamp pools. Highlights sit on
upper-left edges; shadows fall to the lower right.

**The Shared Light Rule.** A room is lit once, as a whole, never piece by piece. Lamps in the
catalog declare where their light is and how far it reaches. The room is an evening: a warm
dimness (#dcb68c, multiply) lies over everything and deepens toward the walls (#c8996c). Each lamp
cuts a soft hole in that dimness, so it lights by keeping the dark away, not by adding glare.
Close to a lamp:
- a low warm pool on the floor and rugs
- a pool on the surface the lamp stands on
- a warm glint on the furniture edges that face the lamp

Daylight reaches the plan only where an opening is: a window or the sliding door lifts the dimness
there (see Windows and the sliding door). In the widget, the dimness is its own layer between the
robot and the walls, so the robot is lit by the same light as it drives.

**The Quiet Room Rule.** Only what Motion lists moves, and it moves slowly: the robot drives, and
leaves, curtains, a cat's ear and lamp glow stir. Nothing flickers or switches on and off, and
textures hold still.

**The Pen Rule.** Every line is a pen stroke in line-cocoa. It is about 1.45 cm wide mid-stroke
and tapers to about a fifth of that where the pen lands and lifts. A closed outline is one to three
overlapping strokes, the way a hand draws one. Details are thinner strokes of the same pen. Lines
tinted per material were tried and rejected: one cocoa line is closer to Cats & Soup. There are no
ruler-perfect edges, gradients across whole objects, or gloss.

**The Fold Rule.** Cloth shows its folds. Each fold is a ridge stroke with a shadow sliver on the
side away from the light. A duvet's turned-back top runs past both sides of the bed.

## Layout

- **Units:** 1 unit = 1 cm. A room is drawn at true size, and the window scales the house to fit.
  It is rendered at 2× for Retina. The aim is a robot never smaller than 28 pt across, and the page
  sets no floor under it: the robot is 35.3 cm across times the fit scale, which `framing()` in
  robovac.js takes from the suites showing. At the whole-house view of the shipped houses, in the
  default 560 × 420 window, it is 11–15 pt across with one run and 4.5–5 pt with nine; in the
  300 × 220 minimum window it is 5–7 pt with one and 2 pt with nine (worked from the suites' boxes
  in data.js, 2026-10-17). Following a robot zooms it larger.
- **Grid:** the robot's grid is 5 cm cells. Pieces snap to 5 cm and turn only in 90° steps, so
  footprints stay exact.
- **Walls:** 14 cm thick cocoa, drawn on each room's outline with soft corners; windows and the sliding door are glazed into
  outer walls (below).
- **The house:** each run gets a floor plan of its own: a suite of two or three rooms, cleaned by
  one robot from one dock, with **one floor wood throughout the suite**. Rooms are roughly square
  with odd edges (L shapes, notches, tabs); a long thin room looks wrong on its own. A second
  concurrent run's suite slots into the first like a puzzle piece, and suites meet at solid
  walls: no doorway ever joins two runs.
- **Windows and the sliding door:** only on outer walls, and never on a wall where another run's
  suite joins on (checked). A window is glazed into the wall with a painted frame and a mullion; a
  pair of linen curtains hangs open inside it, one at each side, from a black rod with chrome
  finials that runs the window's full width a little off the wall, over the curtains' tops. The
  sliding glass door (240 wide, two black-framed panels on an aluminium track, over an oak threshold
  that lips onto the floor on both sides) is on an outer wall and stays shut: the robot is always
  sealed in. Each opening lays a soft warm patch of light on the floor, brightest at the sill, and
  lifts the evening dimness there. Nothing tall (wardrobe, bookshelf) stands in front of a window.
- **Generated houses (plans.py, furnish.py):** a house is a three-by-three grid of suites, one per
  run, up to nine. Each pair of neighbouring suites trades a tab across their shared wall so the
  pieces lock together: `interlock` tries up to twelve random tabs along each stretch of shared
  wall 6 m or longer and keeps the first that leaves both suites whole and thick, and a wall where
  none fits stays straight. Of the 12 neighbouring pairs in each shipped house, house 12 tabs all
  12, house 1 leaves two straight (the walls between number-pad spots 8 and 9, and 6 and 3, spots
  as under Pinned rooms) and house 14 leaves two straight (8 and 5, and 5 and 2). Suites are built
  and furnished outward from the middle one, and the app shows them from the corner suite with the
  most glass across to the opposite corner, so any number of runs shows one connected piece. A suite's block is split into a living room, a bedroom and a
  study by the squarified treemap (Marson & Musse 2010); tabs join the room they open off. The
  aim is no room thinner than 2.4 m and no neck of the living room narrower than 1.2 m, and
  `tidy_rooms` hands thinner parts to a neighbour, in at most eight rounds. All 81 shipped rooms
  hold a square at least 2.7 m on a side, the narrowest being 2.7 m, and no living room has a
  neck under 1.2 m; but house 14's bedroom at spot 9 keeps a strip 2.1 m long and 0.3 m wide
  along one wall, which `tidy_rooms` returns unchanged (2026-10-17). Every room opens off
  the living room, or, where it shares no wall with the living room, off the room it does share one
  with; no room is ever shut in, and check() names one that is. Neighbouring suites never share a
  floor wood. A house is cut again if any empty suite fails the walkway rule.
- **Pinned rooms:** a room the user approves is pinned by its number-pad spot (7 top left, 3
  bottom right) with `furnish.py pin <seed> <pad>[=room,...]`. It is saved to pins.json, every
  piece with the maker and arguments that drew it, and stands exactly as it was in every later
  build while the rooms round it are furnished afresh under the current rules. House 12 holds the
  pins from the user's critique of 2026-10-10.
- **Furnishing by rule:** each room is furnished from groups laid out once in their own frame
  (bed with nightstands and rug; television, sofa, coffee table and armchair; desk and chair;
  dining table and chairs; the little oval table with two poufs; dock; storage; reading chair),
  each carrying the floor it
  must keep clear. A group goes on the first wall spot where it stands on the floor, touches
  nothing, keeps its clear floor clear and leaves every doorway on the walkway. Whatever stands
  against the wall has wall behind the whole of its back: never past the wall's end into open
  floor, never across a doorway, and a sconce or string of lights never on a window. A chair
  tucked under a desk or table is drawn first, so the table covers the part beneath it. The
  suite is then checked whole by rules.check; one that fails is furnished again from a fresh roll,
  and a living room without its television group or its table counts as failing.
- **Rooms filled to the approved density:** after its main groups, each room takes storage on
  free walls, at most one reading corner (an armchair with its lamp table, half of them on a
  small round rug under the chair) and big plants paired with a snake plant in a corner, until
  its pieces cover the share of floor the user's approved hand-laid house gives that kind of
  room (living 21%, bedroom 36%, study 23%, rugs left out) or nothing more fits. Measured on the
  pool on 2026-10-10: living 20–21%, bedroom 29–33%, study 19–24%. A living room too small for
  the full television group takes a compact one, a loveseat across open floor with a lamp table
  beside it; one with no room left for four chairs takes a round table for two. A room holds at
  most three dressers, wardrobes and bookshelves together, an office two, so no wall is lined with
  them (the user's rule); each room is filled and capped by the part it plays, so an office in
  the room the plan named bedroom is still an office. A pinned room keeps what the user approved,
  over the cap or not.
- **Bedrooms and offices (the user's critique of 2026-10-10):** the bed goes in the larger of the
  two private rooms; it keeps off the floor straight in through a doorway, the opening's width
  for 1.8 m, which is left for coming in; and a bedroom always has a desk or the little table as
  well as its bed, so a bed that leaves no floor for one steps down from double to single, a dorm
  with a desk. The other room is an office: a desk, a second desk at its far end, and, in a study
  of 18 m² or more, a daybed. An office, a room with a desk and no bed, may hold as many desks
  as fit; elsewhere two desks keep 2 m apart like any other twins.
  The little oval table with its two poufs pushed in under its ends stands in a bedroom, at the
  foot of a double bed, just past its clear floor, or else free on a small round rug; a study
  takes one in the middle of its floor too (the user widened this on 2026-10-10).
  A living room gets a dining table or a marble kitchen island, with a 91 cm walkway all round
  (NKBA guideline 7, 36 in) and a 107 cm work aisle on the cook's side (NKBA guideline 6, 42 in);
  a living room with floor to spare gets both, and one of 45 m² or more tries its island first.
  The island stands as near the middle of the room as it fits, either way round, with round bar
  stools along its back edge, one to every 61 cm (NKBA guideline 9: 24 in per diner at a 36 in
  counter), tucked a little under the counter; the walkway behind them is the 91 cm a diner can
  be edged past (NKBA guideline 8a).
  The island follows two photos the user chose (2026-10-10): one steel sink whose apron front
  meets the cook's edge; a gooseneck faucet behind it with a lever on the column's side, its
  height drawn a little up the page so the neck reads as a curve; a black-glass induction hob
  4 cm in from the same edge; three pots of basil and a board with an avocado between them; two
  slim black cylinder pendants over the stone behind. It is 240 long, or 200 with a 60 cm sink and
  hob where the long one will not fit. Wall kitchens and a double sink were tried and dropped.
- **Doorways:** a plain opening in the wall that the floor runs through, set near a room's corner,
  with no threshold, leaf or swing arc. Rooms open off the living room where they share a wall
  with it, else off the room they do share one with. A suite's entry is its living room's
  sliding door, which the plan cuts only where the living room's longest outside wall runs 3.6 m
  or more; with none, the entry is the suite's first inner door. Seven of the 27 shipped suites
  have no sliding door (house 1: one; house 12: four; house 14: two). Nothing stands in a door's
  swing.
- **Every room is lived in:** each has a purpose set where it would really go, the bed in the
  bedroom, the desks in the office, with plants round them, plus a lamp and, wherever one fits, a
  rug. A room with only decor reads as empty.
- **Layout rules, checked by `check()` in rules.py** when a suite is furnished, and when
  `draw.py house` lays out the hand-laid pair (a plan with a broken rule prints it). Numbers in cm,
  from the research of 2026-10-10. Three of the rules below are not among what `check()` tests;
  each says so, with what the shipped houses do (measured 2026-10-17):
  - **Walkways:** every doorway reachable from the entry along a path at least 81 wide, 91 for
    long runs (ADA 2010 §403.5.1; IRC R311.6; NKBA guideline 7; Approved Document M 2.22).
    `check()` tests the 81 only. At 91, 11 of the 27 shipped suites have a doorway the entry
    cannot reach.
  - **Doors:** 90 clear on both sides of every doorway; nothing stands in a door's approach
    (Approved Document M 2.22; ADA §404.2.4.1).
  - **Beds:** headboard on a wall (not tested; all 34 shipped beds stand with their heads at a
    wall); 75 clear beside the bed (both sides of a double, one side of a single) and at its foot;
    nightstands within 30 of the bed; a rug under a bed reaches 50 past its sides (Approved
    Document M 2.25 and diagram 2.4; Merrell et al. 2011, table 1; IKEA rug guide).
  - **Living room:** the sofa faces the TV at 0.78–1.57 times the screen diagonal (ITU-R
    BT.1845-1); the coffee table is 36–46 in front of it and 0.5–0.75 of its length (Castlery,
    practitioner); an armchair on the sofa's rug sits 122–244 from the sofa (Merrell, after
    Panero), facing it or the coffee table (not tested; all 18 shipped armchairs on a sofa's rug
    do), while a reading corner elsewhere in the room stands apart; every seat has a table beside
    or in front and 76 clear in front.
  - **Dining:** 81 from the table edge to any wall or furniture behind a chair, on the sides
    where chairs sit (NKBA 8).
  - **Desks:** 81 behind the chair; a lamp within 30 of every desk, bed and reading chair (Philips
    layered lighting, practitioner).
  - **Storage:** 75 clear in front of a dresser or wardrobe, 61 in front of a bookshelf or TV
    console (Merrell; Approved Document M by analogy).
  - **The dock:** 50 clear each side and 150 in front (Roborock user manuals).
  - Furniture is square to the walls; only poufs, baskets and cats turn freely.
- **Taste on top of the rules (the user's):** large plants stand tight into some corners, not
  all; small plants sit on furniture, never loose on the floor; a small oval table has two poufs
  of one colour tucked under its sides, a little off centre; every room has storage along a
  wall; no desk in a living room. The furnisher adds storage as it fills a room and `check()` does
  not require it: 80 of the 81 shipped rooms have some, and house 12's study at spot 6 holds two
  desks, their chairs and a rubber plant. Checked by `check()` (2026-10-10): a sofa or armchair
  within 40 cm of a rug stands with both front legs on it, taken as 8 cm in from its front
  corners, so the television group's rug reaches under the armchair beside the sofa too; no two
  of the same piece stand within 2 m of each other in a room, or within 60 cm back to back through
  a wall, a suite's wall included, except the sets that come as one (a bed's nightstands, a
  table's chairs and poufs); and no two lamps stand within 60 cm of each other in a room. Suites
  are furnished in the order they are built, each beside the ones before it, and every loop over
  room names runs in sorted order, so a house comes out the same on every build.
- **Variations are settings, not new layouts:** a plan is drawn from a list of settings (woods,
  fabrics, desk setup, table setting, cat coat). The hand-laid house that `draw.py house` shows
  has a second suite that is the same plan, mirrored and given other settings, the same size,
  slotted against the first. The shipped houses are generated, so each suite is its own plan: the
  first two suites measure 950 × 890 and 1100 × 1010 in house 1, 980 × 1160 and 1280 × 980 in house
  12, and 1130 × 1160 and 1130 × 950 in house 14.
- **One wood per room:** every piece in a room shares one wood (walnut, oak or black) and a small
  set of textile colours, so rooms read as furnished on purpose.
- **Variety comes from setups, not colours:** a desk is a laptop desk, a two-monitor desk or a
  writing desk; a table is set with flowers or with tea. Cats, poufs and baskets turn to any angle.
- **The glass:** the house floats on a rounded glass panel with a margin round it. The app uses
  macOS's own glass material; the still renders stand a blurred desktop behind the panel to show
  the frost. Scrolling zooms round the pointer, and dragging pans.

## Motion

Only these move; everything else holds still (the Quiet Room Rule):
- **The robot:** drives at about 24 cm/s and turns on the spot, sweeping lanes 30 apart round
  everything that stands on the floor (beds, desks, tables, chairs, poufs, baskets, plants,
  storage) and over the rugs. When its run ends it takes the shortest way home, turns its back to
  the dock and reverses in under the hood. Its side brushes spin only while it runs. Its shadow
  and shine stay put as it turns, so the light holds still.
- **Plants:** every leaf moves on its own stalk, its own way: it turns 3–7° and lifts a touch
  toward the light over 2.4–5.2 s, each on its own beat, while the plant as a whole barely
  leans; near a window the leaves move about twice as far, in the breeze. A plant is fenced
  by its own room's walls, so its leaves never cross a wall however it moves.
- **Curtains:** two per window, open, gathered against the wall at each side. They move as cloth
  does from above (after an MIT cloth simulation filmed from overhead): the top stays pinned
  along the rod, and in a gust (every 8–12 s) the fabric fills like a sail, its hem sweeping into
  the room and toward the middle of the window with a wave running along it, then falls back to
  its gathered band. It bends; it never swings as one stiff piece.
- **The cat:** an ear swivels back hard and snaps forward, twice, every few seconds. The tail
  holds still (a tail moving as one stiff piece doesn't read as a tail). It does not visibly
  breathe.
- **Lamps:** the glow pulses a little (between 70% and full, 4.5 s), never on and off.
- **Following a robot:** the camera eases toward it (a 0.3 s time constant), zoomed so about
  5.6 m of house fills the window, and keeps it centred as it drives; at real speed the robot
  stays within about 12 px of the middle. The arrows visit only robots whose suite holds a run.
  With reduced motion the camera jumps to the robot, and jumps again only when the robot nears
  the edge of the view. Fitting the house, from the menu or esc, lets the robot go. A robot that
  docks is followed the same way, from the moment it docks, and that follow also lets go when a
  run starts or a room comes or goes.
- **The ! over a stopped run's robot,** every stop's: the glyph alone, cream in the house pen with
  its cast shadow, no badge (the user, 2026-10-14). It keeps its 17 by 32 px at any zoom, centred
  over the docked robot with its bottom 3 px above the higher of the robot's top and its dock
  tower's, and it hops every 1.8 s: up 7 px fast, down, a small squash at its base, then a rest;
  still with reduced motion, and running only while it shows. The marks sit in one layer over
  every suite and wall, so a later suite never covers one, and the whole-house view keeps a 44 px
  band at the top so a ! over a top wall shows whole. The hover slip's why starts with the same
  ! drawn in ink, 7 by 13 px, so it reads on the cream slip.
- **Opening the app:** every suite in use is set in place at once, with no landing, and the view
  fits without gliding; every live run's robot is already out on its lanes, at the point the time
  since its run began reaches, so nothing plays as if a run had just begun. A run that stopped
  keeps its ! for ten minutes from when it stopped, and opening the app zooms in on none.
- **A run's suite arriving (the one authored moment):** each suite is a stack of its own, the later
  over the earlier. The view eases out to frame the larger house (640 ms, ease-in-out, or ease-out
  when it is re-aimed mid-flight); 380 ms in, once there is room, the new suite is set in like a
  puzzle piece: it comes in 18 screen px lifted and 3.5% large, its shadow cast on the suites below,
  fades up over 320 ms and settles over 900 ms (cubic-bezier(0.22, 1, 0.36, 1)); then, for a run
  that starts while the app is open, its robot rolls out of the dock. The suite waits, unseen, until
  every picture in it is decoded (at most 1.2 s), so it lands whole; the robots already out never
  stop or jump. A moving suite gets its own compositing layer only while it moves. Measured in the
  Mac app (2026-10-10, three timed drives): idle never over 19 ms a frame; an arrival or a leaving
  drops a frame or a few near its start, worst 29–71 ms, varying from run to run.
- **A run's suite leaving (the user asked for it slower and smoother, 2026-10-10):** ten minutes
  after its robot docks, or after its run's last stop when that is later (a run the page never saw
  going has no dock, so its stop counts alone; half a minute after the dock for a run gone with no
  stop logged), it lifts gently from wherever it is, its shadow growing under it, and only then
  fades, over 720 ms (cubic-bezier(0.37, 0, 0.63, 1)); the view eases in to the house that remains
  once the suite is mostly gone. A suite that never showed is simply removed.
- **The robot and its dock:** the dock is drawn in two parts, its mat on the floor under the
  robot and its tower over it, so a docked robot rests its front half on the mat with its back
  half under the white hood (the user's note). A run that ends while its robot is still rolling
  out sends it straight back in; a turn cut short keeps the heading it was drawn at.
- Reduced motion turns off everything but the robot; suites then fade in and out and the view
  jumps to its new framing, nothing gliding.

## Elevation & Depth

Depth comes from a flat shade shape inside each form and a soft cast shadow beneath it.

- **Shade shape:** one flat shape on the side away from the light, the base colour one step
  darker.
- **Highlight:** one or two small linen-50 strokes or dots on the lit edge.
- **Contact shadow:** a soft dark halo hugging every grounded piece (blur 2.2), so nothing floats.
- **Cast shadow:** wall-cocoa at about 30% opacity, blurred. It is offset down and right by 0.085 ×
  the piece's height in cm, capped at 10 (a 45 cm bed about 4 units, a wardrobe 10). Its blur
  grows with its offset, so tall pieces cast softer shadows. Blur filters are shared by softness.

## Shapes

- Furniture: soft-cornered rectangles, radius 3 to 8 cm, a little chubby.
- Lamps, pots and the robot: circles.
- Fabric and leaves: loose irregular curves. Fabric never has a straight edge.

## Components

**A catalog piece** is one drawing at true size, with its parts in named layers:
- `cast`: the cast shadow
- `base`: the flat material
- `shade`: the shade shape
- `light`: highlights
- `line`: hand lines
- `detail`: grain, folds, veins

It also carries a `footprint` (the floor the robot can't cross, a rectangle in cm separate from
the art) and a `height` in cm, which sets its shadow. The treatment decides how the layers render;
pieces never hard-code it.

**Floors** are planks in one of three woods:
- honey oak: 18 cm boards
- amber oak: 19 cm boards
- walnut: 20 cm boards

Each floor has staggered joints, a soft bevel on every board, grain running along it and a rare
knot, and is trimmed to the room's walls. Herringbone, checker tile and glazed tile were drawn and
rejected.

**The robot:** a 35.3 cm white disc with a two-button pill and a round turret toward the front, a
bumper seam across the front, and grey side brushes at the front corners.

**The dock:** a 45 × 45 cm white rounded hood over a light-grey base, with the ramp's curved lip in
front, drawn as two parts: the mat under the robot and the tower over it. A docked robot rests its
front half on the mat and tucks its back half under the hood.

**The app icon:** the robot turned −28° on a 60 cm square of honey-oak planks, clipped to macOS's
824 px superellipse body on the 1024 px icon grid, under the house's evening dimness, with a soft
cocoa drop shadow. `icon.py` draws it from the catalog's own robot and floor, in the house's pen.

## Do's and Don'ts

- **Do** keep every piece at true scale.
- **Do** let leaves and throws spill over edges.
- **Don't** add labels, dimensions, hatching or a north arrow to the house. A robot's own line
  shows only while it is hovered, on a paper slip with the house's down-right shadow, centred
  just above the robot with a small caret pointing at it, and below it when the top edge is near.
- **Don't** animate anything but the robot, the plants, curtains, cat and lamps described under
  Motion, the camera, and the ! over a stopped run's dock.
- **Don't** use pure black, pure white, gloss or hard gradients.
