# kstack

A Claude Code skill set: skills that build, review and clean a project, and a small Mac app that
shows a robot vacuum sweeping while robovac cleans.

<p align="center">
  <img src="apps/robovac-widget/screenshots/robovac.gif" width="640"
       alt="The Robovac app: a robot vacuum sweeping along a round dining table in a top-down house">
  <br>
  <sub>The Robovac app while a <code>/robovac</code> run is going: one robot per run, sweeping its own suite.</sub>
</p>

**Built on [pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan
([@poteto](https://github.com/poteto)).** Most of what's here started as one of its skills, ported to
Claude Code and merged with our own; the originals are kept untouched under `upstream/`, beside
Cursor's sister plugins. Three independent Opus judges voted on every component on 2026-10-09.
Everyone else it draws on is in [Credits](#credits).

## Install

You need Claude Code, `git` and `python3`.

```bash
git clone https://github.com/kadenkobashigawa/kstack.git ~/kstack
```

```bash
~/kstack/install.sh
```

`install.sh` links every skill into `~/.claude/skills` and every agent into `~/.claude/agents`, then
merges kstack's hooks into `~/.claude/settings.json`, backing the file up beside itself first. It
never overwrites a real folder, and it's safe to run again. kstack lives in `~/kstack` rather than
`~/.claude` because Claude Code asks before every edit inside a `.claude` folder, even in bypass mode.

**The Robovac app** needs macOS 13 or later, Apple's Command Line Tools (`xcode-select --install`)
and the GitHub CLI signed in (`gh auth login`), because the house images come from a kstack release.

```bash
~/kstack/apps/robovac-widget/mac/build.sh
```

```bash
open ~/Applications/Robovac.app
```

`build.sh` compiles the app on your Mac and installs it in `~/Applications`, so it opens from
Spotlight or the Dock like any other app. A build made on your own Mac carries no download
quarantine, so Gatekeeper doesn't stop it. A copy sent to another Mac, by AirDrop or a download,
does get quarantined and blocked, so build it on each Mac instead.

**To update,** pull and run both scripts again: `git -C ~/kstack pull`, then `install.sh`, then
`build.sh` if you use the app. **To remove,** delete the links in `~/.claude/skills` and
`~/.claude/agents` that point into `~/kstack`, take the hooks that run `~/.claude/skills/vet` and
`~/.claude/skills/robovac` scripts out of `~/.claude/settings.json`, and drag Robovac from
`~/Applications` to the Trash.

## The skills

**Auto** means Claude reaches for it on its own and its description loads in every session. **Typed**
means only you start it, with `/name`, so it costs no context until used.

| Skill | Starts | Job | Built from |
|---|---|---|---|
| `build` | auto, every code change | Understand, simplify, contain, verify; per-kind references for bugs, refactors, one-way-door design, measured numbers and unattended runs; every change to be merged passes the gate, and the 18 code rules set the bar | ours, plus pstack's bug-fix, refactoring, architect, blast-radius, tdd, benchmark-checklist, autonomous-run, prototype and principles; the gate from autopilot-full, shipping and swarm; the rules from interrogate's rubric, OWASP, OpenSSF Scorecard and twelve-factor |
| `elon` | auto, inside design | Question every requirement, delete, then simplify | ours |
| `teach` | auto, whenever explaining or writing | Sentence rules on top of the Concise output style: conversational, plain, marked edges, sourced | ours, plus unslop's machine-written tells |
| `vet` | as a loop, or typed | Review every commit landing on main; monthly canary | new: interrogate, swarm, show-me-your-work, autopilot-full's review lanes, thermo-nuclear review |
| `robovac` | as a loop, or typed | One cleaning pass over the project, or one file or folder of it, every run: clorox, then stack-check, then build, then this session's loose ends | new: authoring-a-skill's delegation, autopilot-stack's `/loop` cadence, recall's branch in flight, and the stop rules of pause-safely and create-verification-skill |
| `clorox` | inside robovac | Bin a project's proven leftovers (signed caches, `__pycache__`, identical iCloud twins, finished worktrees); empty bin batches past 30 days | pstack's worktree-cleanup and build-the-lever, the CACHEDIR.TAG spec, PEP 3147, Claude Code's trash rule |
| `stack-check` | inside robovac | Review the Claude Code setup as one system from the last 7 days of sessions; suggested edits, never applied | pstack's reflect, its templates verbatim with Claude Code's names plus two lines of ours (read from the frozen copy, weigh the target first), and its tooling lens on Sonnet in place of reflect's other-family default |
| `correct` | typed | Turn a mistake made twice into a hook, lint or test | pstack's correct and encode-lessons |
| `polish` | typed | Comment and docstring hygiene, proven by parse tree for Python files | ours |
| `create-verification-skill` | typed | Generate a project's own `verify-<app>` skill: launch, doctor, drive, evidence, cleanup, a feature map, proved once end to end | pstack's, translated to `.claude/skills/`, plus a data rule from our first verify skill |
| `maintain-verification-skill` | typed | Keep a `verify-<app>` skill and its feature map honest: source readers per feature, one live pass over every feature, one commit of proven corrections | pstack's, translated (a commit, not a PR) |

Also installed, not in this repo: `impeccable` (third-party, all UI work) and `graphify`
(third-party, parked as typed-only). Project skills live in their projects.

**Agents:** `vet-reviewer` (read-only reviewer with one lens per spawn), `researcher` (read-only
prior-art research on the web and GitHub, for build's design and refactor methods) and
`impeccable-finish-reviewer` (the finish review the global rules require; nothing had registered it).

## The loops

**vet watch, the background reviewer.** Open a new Claude tab and type `/loop /vet watch`. Each tick
reviews any new commits on main as one range: two fresh reviewers (structure: duplicates, placement,
a simpler shape, docs that now lie; correctness: intent, security, blast radius, whether tests reach
the changed lines), then a lead checks every finding itself and reports the proven ones in its reply
and a notification, as `open` (to fix) or `consider` (a call for you). Once a month it replays a
known past bug to check it still catches one. It wakes when main moves (after five quiet minutes) or
hourly, and stays silent unless it finds something. It keeps only a cursor (one commit) and the date
of its last canary, no ledger and no findings file, and no other agent audits its trail, since it is
the final reviewer. It never edits code, commits, pushes or deploys. If the tab closes, the next
session you open says how many commits are unreviewed. `/vet status` shows where it stands.

**robovac, the cleaning pass.** Open another tab and type `/loop 12h /robovac`, or type
`/robovac <file or folder>` once when you finish a piece of work. Each run is one whole pass over the
project the tab is in, or over that file or folder, with nothing skipped as clean. It works in a
folder of its own in the project's git directory and deletes it at the end, so a pass leaves no
report on disk: what you need is in its final reply.
- **clorox** moves proven leftovers into a bin at `~/.clorox/<repo>/` and leaves everything else.
- **stack-check** runs reflect's three lenses and its synthesizer over the setup; its suggested
  edits come in the reply, and it applies nothing.
- **build** runs unattended over the code rules and takes one task per pass: the worst proven broken
  rule, built in a fresh worktree, passed through the gate, and merged into the project's local main
  on a clean verdict, with no ask. Your `/robovac` is the grant. It never pushes. The worktree and
  branch are removed when the pass ends, merged or not, and the other findings are not recorded. If
  the task fails twice, the pass stops and says why in its reply.

In the Desktop app, a slash command can't sit inside another command's arguments, so type
`/loop 12h run the robovac skill` there.

`vet` and `robovac` are the loop skills left visible to the model: a `/loop` wake re-enters each
through the Skill tool, which refuses a typed-only skill. Each description says to use it only when
typed or looped.

**An unattended change.** In your work tab: `/loop <task>. Done when <check>. Work in a new
worktree.` `build` loads `references/long-run.md`: one change, one check and one trail row per
iteration, the predicate never relaxed. With no task handed over, its task is the code rules in
`references/rules.md`: a broken rule sends that slice through build's checks 1 to 5. Each
self-contained change is its own branch, gated and merged alone; only overlapping work waits. Every
change passes the gate in `references/gate.md`: fresh agents re-run the checks at the exact commit,
prove the load-bearing behavior live on the smallest surface that can disprove it, review it in two
lanes on two models (Sonnet by default, Opus for correctness) and compare with main, with three
agents at most at once. The session running the gate sorts the findings itself, and a fresh lead
sorts only when that session wrote the fix. It merges on your grant plus a clean verdict, as
pstack's autopilot-full has it, and stops at merge-ready without your grant. It never deploys.

**What happens to findings.** The work session owns what vet reports and what a robovac pass replies
with: fix through `/build`, or dismiss with the disproof. A `consider` finding is built, or you
decide against it. A class seen twice goes to `/correct`.

## Robovac, the app

<p align="center">
  <img src="apps/robovac-widget/screenshots/robovac-window.png" width="600"
       alt="The Robovac window: two suites of rooms on a glass panel, each with its own robot">
</p>

Open it whenever you want to see what robovac is doing; it doesn't need to stay up. Each robovac
session gets its own suite of three rooms, with its own robot and dock, up to nine at once. A robot
has two states, tied to what its session's agent is doing. It sweeps while the agent works: a turn
in progress, loop or not, however long it thinks or a tool runs, and after the turn while a
background shell or a background agent still runs. It docks, and floats a **!** over its dock, when
nothing is working, when the session closes, or when something waits on you: a question or an MCP
form as it opens, a permission prompt once it has waited about six seconds, so a prompt approved at
once never sends it home. A wait outranks background work but not the turn's own: a background
agent's prompt docks it only once the turn has ended. It goes out again once no prompt is open, one
asked after it docked included: an approved prompt closes when its call's result comes back, after
the tool has run, and one denied without Esc when its agent's batch ends; while only subagents'
prompts wait, the main agent's next call sends it out, since the main agent works on only past a
background prompt. A robot already driving home docks first, then goes back out a moment later.
Esc ends the turn and docks the robot, unless a background shell still runs, which an Esc doesn't
stop; an Esc in the instant between the turn's last reply and its Stop hook leaves no mark, so the
robot docks six seconds after that reply. As a robot docks the camera zooms in on it. Hovering a
robot shows its run's one line, plus why it stopped. Opened mid-run, the app shows the robots
already sweeping.

Scroll to zoom, drag to pan, and double-click to fit the whole house. An arrow key follows the
robot nearest the middle, and esc or 0 return to the whole house.

Everything stays on your Mac. kstack's hooks append each run's start (with its folder and its
transcript's path) and stop, the run's one line, whether its turn is open and the id and kind of
each background task still running, each permission prompt as an ask (the agent and, for a
subagent, its transcript's path, the tool, and a digest of each input value, never the value), each
MCP form as an ask naming its server, a waiting notice with no prompt or form open as an ask of its
own, and each answer, to `~/.claude/robovac/runs.jsonl`, and the app reads that file when it opens
and every two seconds after. A run on another machine doesn't show here. `ROBOVAC_RUNS` points
the app at another log.

## How it's wired

- **`skills/<name>`** is linked from `~/.claude/skills/<name>`, and **`agents/<name>.md`** from
  `~/.claude/agents/<name>.md`. Edit here and commit here; the links make every edit live at once.
  User-level skills reach every project and every Claude Code surface: the terminal, VS Code and the
  Desktop app, which reads the same `~/.claude` configuration. No skill here is tied to one project:
  a project's own `verify-<app>` skill is made inside that project by `/create-verification-skill`.
- **`.claude/skills/verify-robovac`** is kstack's own: it proves a change to the Robovac app or the
  robovac hooks with a real Claude Code session and a filmed test copy of the app, against a
  baseline. Claude Code loads it in sessions opened in this repository; `install.sh` doesn't link it.
- **`hooks/hooks.json`** holds vet's SessionStart line and robovac's run hooks for the app.
  `hooks/install.py` merges them into `~/.claude/settings.json`: it adds the missing ones, takes out
  a kstack hook that `hooks.json` no longer has, and leaves every other hook alone.
- **`apps/<name>`** holds programs that are not skills, as pstack keeps benny under `automations/`.
  `apps/robovac-widget` is the Robovac app; its `PRODUCT.md` and `DESIGN.md` hold its decisions, and
  its build output is ignored.
- **`upstream/`** holds pstack, cursor-team-kit, ralph-loop, continual-learning and orchestrate exactly
  as imported (MIT, see `NOTICE`). Every other commit is a diff against them. A parked part is ported
  from there, never rewritten from memory.
- **Outside the repo:** `~/.claude/settings.json` also parks graphify as typed-only
  (`skillOverrides`) and keeps session logs 60 days. The VS Code setting
  `claudeCode.environmentVariables` sets `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`, which brings back the
  checklist for Claude 5 models. A project opts into the loops and `/correct` by naming them in its
  own `CLAUDE.md`, and keeps its rule-to-enforcer table in its own decision records.

## Parked in `upstream/`, and what would bring each back

| Part | Bring it back when |
|---|---|
| hillclimb | a single metric needs pushing over many iterations |
| eval | skill changes need blind proof that they change behaviour |
| runtime-forensics, trace-forensics | a live leak or spin, or a captured profile to read |
| arena | a second model family becomes reachable from Claude Code |
| benny | bug reports start arriving from outside (Slack, users) |
| visual-parity | a styling-system migration needs pixel-exact equivalence |
| control-cli | an interactive command-line surface needs driving |

**Dropped:** the always-on router (`poteto-mode`) and model routing, all PR and stack machinery
(the projects here merge locally; autopilot-full's gate and merge rule live on in build's
`references/gate.md`), the comment strippers (they delete required docstrings), pstack's duplicate
writing and teaching skills, TypeScript and Grok Bot pieces, and the principles our skills already
state.

## Changing it

Edit the file under `skills/` or `agents/`, run it once on a real case (a skill that never ran is a
draft), and commit. Keep the description short and specific: an auto skill's description costs
context in every session. A new skill that only you start gets `disable-model-invocation: true`.

For the app, `apps/robovac-widget/mac/build.sh` rebuilds and reinstalls it. `mac/images.sh build`
remakes the house images (it needs Playwright's WebKit and Pillow), and `mac/images.sh publish`
releases them and updates `images.lock`, so other Macs fetch the new pack. `mac/demo.sh` records the
GIF at the top of this page; it needs `ffmpeg`, the Command Line Tools and Screen Recording
permission for the app you run it from.

## Credits

- **[pstack](https://github.com/cursor/plugins/tree/main/pstack)** by Lauren Tan
  ([@poteto](https://github.com/poteto)), MIT. It's the source of most of kstack: build's methods
  and its gate, vet's reviewers, clorox's cleanup, stack-check's reflect, `/correct`, the
  verification skills, and the writing tells `teach` checks for.
- **[cursor-team-kit](https://github.com/cursor/plugins/tree/main/cursor-team-kit)** and
  **[continual-learning](https://github.com/cursor/plugins/tree/main/continual-learning)** by Eric
  Zakariasson, and **[ralph-loop](https://github.com/cursor/plugins/tree/main/ralph-loop)** and
  **[orchestrate](https://github.com/cursor/plugins/tree/main/orchestrate)** by Cursor, MIT, all from
  [cursor/plugins](https://github.com/cursor/plugins). vet's thermo-nuclear review comes from
  cursor-team-kit. ralph-loop implements Geoffrey Huntley's
  [Ralph Wiggum technique](https://ghuntley.com/ralph/).
- **[impeccable](https://github.com/pbakaus/impeccable)** by Paul Bakaus (Apache 2.0) runs all UI
  work, including the Robovac app's design, and **[graphify](https://github.com/Graphify-Labs/graphify)**
  is parked as typed-only. Both are installed alongside kstack, not shipped in it.
- The code rules draw on [OWASP](https://owasp.org), the
  [OpenSSF Scorecard](https://github.com/ossf/scorecard) and [the Twelve-Factor App](https://12factor.net);
  clorox follows the [CACHEDIR.TAG spec](https://bford.info/cachedir/) and
  [PEP 3147](https://peps.python.org/pep-3147/).

`NOTICE` carries the MIT copyright lines, and each skill that adapts upstream work names its source
in its own files.

## License

MIT, in [`LICENSE`](LICENSE). The parts adapted from pstack and Cursor's plugins keep their own MIT
notices, listed in [`NOTICE`](NOTICE).
