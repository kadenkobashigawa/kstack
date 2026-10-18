---
name: verify-robovac
description: Prove a change to the Robovac Mac app or the robovac hooks with a real Claude Code session in the desktop app's host mode and a filmed test copy of the app, baseline against treatment, ending VERIFIED, NOT VERIFIED or INCONCLUSIVE. Use for changes under apps/robovac-widget, skills/robovac/scripts/runs.py or hooks/hooks.json, a robot that sweeps or docks wrongly, or when build's check 4 or the gate needs the app driven.
---

# verify-robovac

Made for this repository on 2026-10-17 by kstack's create-verification-skill, which is pstack's
(MIT, `upstream/pstack/skills/create-verification-skill/`). The feature map is `features/README.md`.

**What a person touches.** A Claude Code session in which robovac runs. Its hooks
(`hooks/hooks.json`, each running `skills/robovac/scripts/runs.py hook`) append to a run log, and
the Robovac app (`apps/robovac-widget`, built by `mac/build.sh`) reads that log as it opens and
every two seconds after, and moves one robot per robovac session: out sweeping while its agent works,
a turn or background work, and home to its dock with a **!** when nothing works or something waits
on the person. The other surfaces are `runs.py say|live|path` and the house
page opened in a browser, which has no runs; neither is how a person sees robovac.

**How a drive reaches it.** Two halves, both real, joined only by the log file:

- **The session side** is the newest Claude Code binary the Claude desktop app installed, under
  `~/Library/Application Support/Claude/claude-code/<version>/<hash>/claude.app/Contents/MacOS/`,
  started in the desktop app's own host mode, the flags `ps` shows the app using:
  `--output-format stream-json --input-format stream-json --verbose --permission-prompt-tool stdio`.
  In that mode Claude Code sends each permission request to its host as a `can_use_tool` control
  request, and the app answers it when the person clicks; an MCP form comes the same way, as an
  `elicitation` control request. **The person's click is simulated at that protocol**:
  `scripts/host.py` answers each request after the hold the scenario names (a question,
  AskUserQuestion, with each question's first option, and a form filled in by its fields' types),
  and sends Esc as the app does, an `interrupt` control request. A form needs a server that asks:
  for a scenario that sets `form`, `scripts/form.py`, an MCP server whose one tool `ask` opens a
  form mid-call, is the session's only MCP server. The Claude app's own window isn't driven,
  because it is the person's live app: its sessions, its `~/.claude/settings.json` hooks and its
  real run log are theirs.
- **The app side** is a test copy built from the same revision's sources with build.sh's own swiftc
  line, under its own bundle id, opened from its binary with `ROBOVAC_RUNS` naming the claim's log.
  It reads only the rows the hooks really wrote; nothing is replayed into the log or injected into
  the page. `ROBOVAC_HOUSE=1` holds the drawing fixed so two sides film the same house; the page's
  other variable, `ROBOVAC_KEYS`, is never set, since it presses keys on the page from inside.

The session's first prompt starts with `/robovac`, as a person starts robovac. The drive session
loads no robovac skill (`--setting-sources local` loads none of the person's skills), so Claude
Code passes `/robovac <words>` to the model as text: the hooks see the same prompt a person's
`/robovac` sends, and the words after it are the turn's instructions. Measured 2026-10-17:
UserPromptSubmit carried `/robovac Reply with only the word ready.` and the model replied `ready`.
The cleaning pass itself (clorox, stack-check, build) never runs; the app shows none of it.

`V=.claude/skills/verify-robovac/scripts/verify.py`, run from the repository root, in every
command below. `<E>` is the claim folder `claim` prints; `<side>` is `baseline` or `treatment`.

## Launch

```bash
E=$(python3 $V claim wait-on-prompt)
python3 $V launch "$E" baseline 80cf3ea
```

`launch` exports the revision with `git archive` (or `WORKTREE` for the checkout as it stands,
untracked files git doesn't ignore included), copies the checkout's house images when `images.lock`
names the same pack (else `images.sh fetch`, which needs `gh`), builds `Robovac Verify.app`, and
opens it. **A commit builds once per round**: the copy lives in `<tmp>/verify-robovac/builds/<sha>`
under `com.kstack.robovac.verify-<sha12>`, and every claim of the round that names that commit
reuses it (launch prints `(reused)`), so the gate's live lane builds one copy per version, not one
per claim. A `WORKTREE` changes under one name, so it builds again for each claim, in the claim's
scratch, as `...verify-<claim time>-<side>`. `python3 $V end-round` removes the round's copies once
its last claim is cleaned up, and exits 1 naming any whose app still runs. **Ready** is its window
on screen: `launch` waits up to 20 s, brings the window forward the way a click on its Dock icon
does (an app started from a background process stays off screen until then), waits 2 s for the house
to draw, and prints the side's sha and the test copy's path. Opening one side stops the other side's
app, so one window is filmed at a time. `--later` builds without opening, for a scenario whose
`open` anchor opens the app mid-turn. Teardown is Cleanup below.

**It takes the screen.** Opening and each drive bring the test window to the front, and the film
records that part of the screen, so tell the person before a drive. A window they bring over it
lands in the film; the stills photograph the window alone and stay clean.

## Doctor

```bash
python3 $V doctor "$E" baseline
```

Read-only, one line per check, exit 1 on any FAIL: the app pid runs this side's test copy (or,
`--later` or after a drive closed it, isn't open yet); the copy's bundle id is under the verify
prefix and its stamp is the side's sha; its window is on screen; this process may record the screen
(Screen Recording); the log is inside the claim and never `~/.claude/robovac/runs.jsonl`; the
revision's `runs.py` is there; Claude Code is signed in. Run it before any drive (`drive` runs it
first and refuses on a FAIL) and whenever anything looks off.

A FAIL on the sign-in means the binary's own login expired: `auth status` reports `loggedIn: false`
and a drive fails with "OAuth session expired". The Claude app signs its own sessions in without
it, so the app working proves nothing here. The person runs `"<binary>" auth login` in a browser;
never sign in for them.

## Drive

```bash
python3 $V drive "$E" baseline .claude/skills/verify-robovac/scenarios/wait-on-prompt.json
```

A drive writes the session's settings (the revision's `hooks.json` with `runs.py` pointed at the
exported tree, vet's SessionStart dropped, and an observer hook on every event the clock reads),
films the window's frame with `screencapture -v`, starts the session (`--settings <generated>
--setting-sources local --strict-mcp-config --session-id <new> --model haiku`, its folder in
scratch, its environment without one `CLAUDE*` or `ANTHROPIC*` variable of the session running the
drive), sends each step, takes each still, closes the session the way the app closes one, stops the
film, **quits the test copy by the pid it started and confirms its window is gone** (the `app pid N
quit, window gone` mark in the clock), and writes `<side>/clock.md`. The window is open only from
`launch` to the end of the recording; a second drive of the same side opens it again. Prompts and
answers are the scenario's, never typed by hand, so both sides get the same ones.

**A scenario** is JSON in `scenarios/`, one per mapped feature:

- `steps`: each a `prompt`, or a `pause` in seconds. A prompt may carry:
  - `answers`: in order, one per permission request or form as each arrives,
    `{"hold": s, "behavior": "allow"|"deny", "interrupt": true}`; `interrupt` makes a denial an Esc
    at the prompt, and a form denied is declined. A request past the list is allowed at once, which
    docks nothing for a permission prompt, since it docks only after its notice at about 6 s; a
    question or a form docks as it opens, so give each one its own entry.
  - `shots`: `[anchor, seconds, name]` stills, anchored to the turn's first `prompt`, `ask` (a
    permission request or a form arriving), `answer` (sent) or `result`.
  - `interrupt` and `open`: `[anchor, seconds]`, an Esc mid-turn and the app opened mid-turn.
  - `results` (default 1; 2 where a background agent reports after the turn) and `timeout` (120).
- `files`: names and text to put in the session's folder first.
- `form`: true gives the session `scripts/form.py` as its one MCP server, whose tool is
  `mcp__form__ask`.
- `hooks`: more hooks by event; `{verify}` and `{scratch}` fill in, as in
  `stop-hook-continues.json`'s `{verify} continue-once {scratch}/stop-once '<reason>'`.

`{runs}` in a prompt is the revision's `runs.py`, for the robovac skill's own first step,
`runs.py say "<line>"`, which sets the line the hover shows.

**Reading a still.** The whole house means a run is going, or a robot is still driving home; the
camera zoomed in on a dock with a **!** over it means the robot docked and its run stopped. The
log rows say which, and the film shows the motion between. The robot is the white disc with a
ring on top.

## Evidence

The claim folder is `<git-common-dir>/verify-robovac/<YYYY-mm-dd-HHMMSS>-<slug>/`, in the
repository's git directory: outside every worktree, never tracked or pushed, never swept by clorox,
and never removed by cleanup. It holds verify-this's layout
(`upstream/cursor-team-kit/skills/verify-this/SKILL.md`):

- `claim.md`, written by you before any drive: the claim in falsifiable form (condition, what is
  observed, threshold), the baseline and treatment revisions, the scenario and the data.
- `timeline.md`: one line per helper command, appended by the helpers; add your own steps to it.
- `baseline/` and `treatment/`, each: `setup.json` (revision, sha, bundle, window, Claude Code
  version), `video.mov`, one PNG per still, `clock.md` (driver marks, hooks and log rows on one
  clock), `runs.jsonl` (the log the hooks wrote, the side effect itself), `hooks.jsonl` (each hook
  payload's names and times), `stream.jsonl` (the session's output), `stderr.txt` and `app.log`.
- `diff/`, from `python3 $V diff "$E"`: each still both sides took, baseline left and treatment
  right, and `rows.md`, both logs' rows on their own clocks.
- `verdict.md`, written by you, in verify-this's output shape: `VERIFIED`, `NOT VERIFIED` or
  `INCONCLUSIVE`, the claim, the evidence (each still and row, baseline against treatment), and one
  paragraph naming any confound.

**Proof standards** (pstack's): exercise the real user path, not internal setters or test-only
endpoints; capture the action and the resulting state, not just the final screen; verify side
effects alongside what's visible (here, the log rows and the files the session wrote, listed at
the end of each clock); mocks only where a production boundary already isolates the external
system. The stand-ins are the person's click and, for a form, form.py's server behind the MCP
boundary, both named above. A still alone never proves a state: pair it with the log row at its
time in `clock.md`.

**Verdicts** follow verify-this: VERIFIED when baseline and treatment differ in the claimed way with
no confound; NOT VERIFIED when they don't, or move the wrong way; INCONCLUSIVE when a side has no
valid run, a still MISSED, or the sides' `asked` lines differ (another command, or another number
of prompts), since the model's replies are the one input not held fixed. Where the same calls were
sent differently, two in one message on one side and one each on the other, the verdict names it
as a confound and says which of the claim's moments it can reach. Never report INCONCLUSIVE as a
pass.

**What stays out of the evidence.** The session's opening reply carries the account's email, so
`stream.jsonl` drops it; the transcripts carry it too, so they aren't copied, and go to the Trash
at cleanup.

## Cleanup

```bash
python3 $V cleanup "$E"
ls "$E"/*/video.mov
```

`cleanup` stops each process the claim recorded in `started.json`, by pid, and only while that pid
still runs the executable it started; unregisters each test copy built for a `WORKTREE` from Launch
Services (`lsregister -u`; the round's commit copies wait for `end-round`) and removes its defaults,
WebKit data and caches, which macOS keeps under `~/Library` by bundle id whatever `HOME` says
(measured 2026-10-17, so a temporary `HOME` separates nothing and isn't used), only for ids under
the verify prefix; moves the drive sessions' transcript folders, only those in `~/.claude/projects`
named for this claim's scratch path, to the Trash; removes the scratch folder; and lists the
evidence it kept. It exits 1 if anything it started still runs. Run it after every drive, failed
ones too, then confirm the evidence is still there.

Never: the person's `~/.claude/robovac/runs.jsonl`, `~/.claude/settings.json`,
`~/Applications/Robovac.app` or its `com.kstack.robovac` defaults; `build.sh` (it installs over
the person's app); a process by name.

## Helpers

| File | Run | Does |
|---|---|---|
| `scripts/verify.py` | `python3 $V <command>`; `python3 $V` prints the commands | claim, launch, doctor, drive, diff, cleanup, end-round; and the two hooks a drive installs, `observe` and `continue-once` |
| `scripts/session.py` | imported by verify.py | a scenario checked, the drive session's settings, and the drive itself: the film, the stills, the clock |
| `scripts/testcopy.py` | imported by verify.py and session.py | a revision exported from git, its test copy built, opened and unregistered |
| `scripts/common.py` | imported by the other three | the claim's timeline and record of what it started, processes, and the `mac` helper's calls |
| `scripts/host.py` | imported by session.py | the session in the desktop host mode: prompts sent, requests, questions and forms answered, Esc |
| `scripts/form.py` | started by the session for a scenario with `form` | an MCP server over stdio whose one tool opens a form |
| `scripts/mac.swift` | compiled by common.py into scratch; `mac window <pid>`, `front <pid>`, `preflight`, `trash <path>` | a process's window id and frame, bringing it forward, the Screen Recording check, the Trash |
| `tests/test_verify.py` | `python3 .claude/skills/verify-robovac/tests/test_verify.py` | the helpers' guarantee lines, with a fake Claude Code; exit code is the failures |

## Data

Each side starts from the same inputs: an empty log in the claim folder, which the hooks fill from
the drive's first prompt; an empty session folder plus the scenario's `files`; house 1; the same
scenario file, prompts and holds; the same Claude Code binary and `--model haiku`. No developer
data is copied in: the only dev data this app has is the person's own run log, which holds their
sessions. Production has none. The model's replies are the input not held fixed, so the prompts
name exact commands; check the `asked` lines match across sides before judging.

## Then

`/maintain-verification-skill` keeps `features/` honest as the app changes.
