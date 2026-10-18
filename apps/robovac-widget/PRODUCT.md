# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One developer who runs robovac audit loops in Claude Code tabs alongside their own work, and opens
this app when they want to see what robovac is doing. It is eye candy first: something pleasant to
glance at, which also shows whether a run is going.

## Product Purpose

A small window showing a cozy room seen from straight above, where a robot vacuum sweeps while a
robovac run is going and docks when it ends. Success is a thing pleasant enough to keep open while
working, whose one signal, sweeping or docked, is never wrong.

## Positioning

The robot shows whether the agent in a robovac session is working, loop or not: "if the agent is
working, it should be going, if its stopped, the robovac should be docked" (the user, 2026-10-14).
It has two states, sweeping or docked with its !, "genuinely tied to the activity of the agent ...
if it's going, making messages, it's thinking, or there are background tasks going on, then the
RoboVac just continues vacuuming. If the session ends, no more background tasks ... then it docks"
(the user, 2026-10-17). Its state comes from Claude Code hooks, the session's transcript, and one
line the run's agent writes. A session becomes a robovac session when a prompt starts with
`/robovac` (or `/loop` and then `/robovac`) or the Skill tool runs robovac, and stays one until it
closes or goes a week unheard from; a prompt that only mentions `/robovac` does not count. The robot
goes out when a turn of that session's main agent starts and stays out while the turn goes on,
however long it thinks or a tool runs, since neither writes anything until it ends, and after it
while a background shell or a background agent runs: a background shell's call names its task, a
background agent's call returns at once naming its agent, each Stop lists the tasks still running,
and a task that ends starts a turn of its own. It docks when the turn has ended with no background
work running, when the session closes, or when something waits on you, so a loop waiting for its
next wake is docked. "Anything that stops the agent's flow" docks it (the user, 2026-10-17): a
question or an MCP form as it opens, and a permission prompt or an MCP link left about six seconds,
so a prompt approved at once, as auto mode approves, never sends it home: "the robot should go
back" (the user, 2026-10-15). A wait outranks background work, since the ! means it needs you, but
not the turn's own: a prompt from an agent known to run in the background docks the robot only once
the turn has ended. It goes out again once your answer has played out, not at your click: an
approved prompt when its call's result arrives, after the tool has run, and one denied without Esc
when its agent's batch ends. That notice does not say who asked, and two prompts can wait at once,
so the hooks log every prompt and form as an ask (the agent, the tool and a digest of its input,
never the input) and the robot stays docked until no ask that holds it is open, one asked after it
docked included: a prompt closes as just said, a subagent's prompt denied with Esc at the interrupt
line in that subagent's transcript, and a form at its result. While only subagents' prompts wait,
the main agent's next call or batch sends the robot out, since the main agent can start one only
past a background prompt ("If it's going, it should be going"). After a stop other than Esc, any
tool call of the main agent counts as it working, so a turn another Stop hook keeps going docks its
robot at the Stop and sends it back out at its next call, and one that goes on only to reply stays
docked; a subagent's call never does, since no hook would end a run it started. On 2026-10-18 the
user kept that dock, the option that adds no delay: robovac's Stop hook runs beside the others and
cannot know one will keep the turn going, so keeping the robot out through such a turn would mean
docking every turn only once every Stop hook has finished, a median 2.5 s after the reply (the time
from a turn's last assistant line to its `stop_hook_summary` line, over 400 desktop-app turns). A
Stop hook that keeps a turn going sets `hasOutput` true on that line, with one `hookErrors` entry
if it blocks or one `hookAdditionalContext` entry if it adds context; `preventedContinuation` stays
false either way. None of the user's desktop-app turns from 2026-10-14 to 2026-10-18 (UTC) has
them. Esc, and a prompt denied with it, run no hook, so the app watches the session's transcript
for its interrupt line: it ends the turn at once, and an Esc stops every background agent but no
background shell, so the robot docks unless a shell still runs; a robot docked waiting on you shows
Interrupted from then. An Esc in the instant between a turn's last reply and its Stop hook leaves no
hook and no line (seen once, 2026-10-15), so a turn whose last reply ended it and has had no Stop
for six seconds is over too: its Stop hook starts within a tenth of a second (28-56 ms over 25
measured turns) and is killed at five. The hooks log either end at their next event. A message typed
mid-turn leaves it going. A run heard nothing from for twelve hours counts as gone quiet. Beyond
that, the widget shows only the run's own one line, which the agent sets at the start (`runs.py
say`), while its robot is hovered. No task lists, no progress (the user, 2026-10-10).

## Operating Context

- An ordinary Mac app: it opens from `~/Applications`, Spotlight or the Dock, its window sits like
  any other (other windows can cover it), and closing the window quits it. It keeps its frame by
  autosave and no window state for macOS to reopen, so a forced quit never brings back a reopen
  prompt. A native macOS shell
  hosts a web view, which draws the room. It opens on the runs going now, all their suites in
  place at once, with no arrival played for a run that was already going (the user, 2026-10-14).
- The rooms don't fill the window. The house floats on a glass panel, and the space round it is
  macOS's own glass material, blurring whatever is behind the widget (the user's words: "like the
  glassmorphism template we have for [another project], but whatever works").
- **Pan and zoom:** scrolling zooms round the pointer with a short glide, dragging pans, and a
  double click fits the whole house. The window moves by its top edge, or by ⌘-dragging anywhere.
- **Finding a robot:** an arrow key zooms in on the robot nearest the middle and the camera follows
  it; right or up goes on to the next robot, left or down back to the one before, and esc or 0
  return to the whole house. Scrolling while following zooms the follow; a drag lets the robot go.
- **Hovering a robot** shows its run's one line, and, once its run has stopped, why.
- **A run that stops** sends its robot home and floats a ! over its dock, for every stop, a finished
  turn included (the user, 2026-10-14); its suite stays ten minutes before it may leave, counted
  again from a later stop, such as the turn finishing after a wait, and the session's next turn
  takes it back. As the robot docks, the camera zooms in on it the way an arrow key does (the
  user: "auto zoom on the robovac that docs"), even away from a robot an arrow key was following.
  Esc or 0 return to the house, and a follow the camera took at a dock also lets go when a run
  starts or a room comes or goes, so a run that starts after the zoom is never off screen. A robot
  sent out again before it docks drives on home, docks, and goes back out within about a second,
  at the page's next look at its runs, with no ! and no zoom: "Kind of like how RoboVacs empty
  their tank. Mid-pass ... That way there's no glitching" (the user, 2026-10-17); stopped again
  before it docks, it stays docked.
- **The menus:** the app menu (About, Services, Hide, Hide Others, Show All, Quit), File with
  Close (⌘W), View with Fit the House (⌘0), and Window (Minimize, Zoom, Bring All to Front, and
  the tiling items macOS adds); the house's context menu, however it opens, fits it or quits. A
  double click on the top edge does what System Settings says for title bars, Fill included. The
  hooks alone start and stop the robots.
- **The icon** is the robot mid-turn on honey oak, drawn by `icon.py` from the house's own pieces
  in the house's pen, on macOS's icon grid (the user's pick of three, 2026-10-14).
- **Build:** `mac/build.sh` builds the app in a temporary folder and installs it as
  `~/Applications/Robovac.app`, the only copy. The house images come from the release pack
  `images.lock` names, fetched by `mac/images.sh`, so a build needs no Python; `images.sh build`
  remakes them and `images.sh publish` releases them. `icon.py build sweeping` remakes
  `mac/AppIcon.icns`.
- **The hooks:** `skills/robovac/scripts/runs.py hook`, run from the plugin's `hooks/hooks.json`, or from
  `~/.claude/settings.json` after install.sh, for
  UserPromptSubmit, every PreToolUse, PostToolUse, PostToolUseFailure, PostToolBatch,
  PermissionRequest, Elicitation and ElicitationResult, the Notifications that wait on you, Stop,
  StopFailure and SessionEnd, appends to `~/.claude/robovac/runs.jsonl`, logging each prompt and
  form as an ask and each answer it sees, so a wait ends when its last ask is answered, and the
  turn and the background tasks as they move; it prints nothing and never holds a session up (23 ms
  a hook, so 69 ms for a tool call alone in its batch, which runs three, measured with the log at
  its longest). The app reads that log as it opens and
  every two seconds after, and tells the page which runs are going. A new run
  takes the lowest free suite, which is set into the house, and then its robot drives out (a run
  already going when the app opens is shown out on its lanes); a run that ends sends its robot home,
  and ten minutes after it docks, or after its run's last stop when that is later, its suite lifts
  out of the house, unless a later suite still has a run.
- It can stay open for hours, so its CPU, GPU and battery cost matter.

## Capabilities and Constraints

- **Idle:** the robot rests on its dock, charging.
- **A run starts:** the robot leaves the dock and slowly sweeps the open floor. Opened during a
  run, the app shows the robot already sweeping.
- **A run ends:** from wherever it is, the robot plans a route home, drives it and docks. It never
  teleports.
- **Several runs at once:** each run gets its own suite of three rooms, with its own robot and dock,
  up to nine runs. Suites are cut from one generated house like puzzle pieces, so each new run's
  suite slots into the ones showing. The first run gets the corner suite with the most windows, and
  the house grows block by block across to the opposite corner ("start at one of the corners then
  progress to the opposite corner", the user, 2026-10-14). The widget picks a house at random from a
  pool it was built with each time it opens.
- **Motion, after the layouts are settled:**
  - the robot drives, and its side brushes spin
  - the cat stirs now and then
  - leaves sway as if there were a little airflow
  - the lamps breathe very slightly
- **Rooms** are furnished by rule from the catalog when the pool is built, and a room the user
  approves is pinned so later builds keep it. Each carries its own furniture and its own grid of
  open floor, which the robot follows.
- **How rooms are made:** a furniture catalog comes first, and rooms are composed from it by rule
  (`furnish.py`); `widget.py build` generates, furnishes and draws the whole pool.

## Brand Commitments

- 2D and straight top-down, so the robot is never hidden behind a wall.
- Hand-drawn, detailed vector graphics in one fixed palette, shading style and shape style.
- Cozy: light colors, polished wood and warm lighting, with the wood set against black, white and
  chrome. Houseplants, definitely.
- The three isometric cutaway illustrations the user shared (two apartments and a café) set the
  vibe only. They are not top-down.
- **The robot is the Roborock Qrevo Curv 2 Flow, with its multifunctional dock,** drawn true to
  the real product:
  - **Robot:** a gloss-white disc 353 mm across and 119 mm tall. From the front, its top shows a
    pill with two buttons, a round turret, and a plain lid with the wordmark near the back. A
    bumper seam crosses the front, and grey side brushes poke out at the front corners. The
    roller mop is at the rear.
  - **Dock:** about 450 × 450 × 450 mm. It has a gloss-white rounded hood over a light-grey base,
    with a lid seam across the top. A grey ramp with a curved lip sticks out in front.
  - **Docking:** the robot backs in rear first, over the mat, and tucks its back half under
    the hood; its front half rests on the mat.

  The source is Roborock's own product photos (roborockstore.com.au, `products/qrevo-curv-2-flow`).

## Evidence on Hand

No assets yet. The shared illustrations are mood references, not material to trace or ship.

## Product Principles

1. **The signal is true.** Sweeping means a run is live and docked means none is.
2. **Motion is continuous.** Every move is driven from where the robot is; nothing jumps.
3. **Calm enough to keep open while working,** in both look and cost.
4. **Catalog before rooms.** Every room is built from one shared furniture catalog in one style.
