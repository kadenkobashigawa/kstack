# How kstack works

The README covers installing and using kstack. This page covers what happens underneath: the two
loops, the review every change goes through, and how the repository is wired into Claude Code.
Commands are shown as a clone install names them; with the plugin, prefix each with `kstack:`, as in
`/kstack:vet`.

## vet: the commit reviewer

Start it in its own tab with `/loop /vet watch`. Each tick reviews any new commits on `main` as one
range:

1. Two fresh reviewers read the range, each with one focus. The structure reviewer looks for
   duplicated code, code in the wrong place, a simpler shape, and docs the change made untrue. The
   correctness reviewer checks intent, security, what else the change affects, and whether the
   tests reach the changed lines.
2. A lead checks every finding itself and reports only the ones it can prove, in its reply and as a
   notification. Each finding is marked `open` (to fix) or `consider` (a call for you to make).

vet wakes when `main` moves, once it has been quiet for five minutes, or hourly. It stays silent
unless it finds something. Once a month it replays a known past bug to check it still catches one.

It keeps very little state: the last commit it reviewed, the date of its last replay and, while a
range is blocked, when to retry. They sit in `.git/vet/`, or in `state/report/vet/` when the project
ignores that folder. It keeps no findings file. It never edits code, commits, pushes or
deploys. If its tab closes, the next session you open tells you how many commits are unreviewed, and
`/vet status` shows where it stands.

## robovac: the cleanup pass

Run `/loop 12h /robovac` in its own tab, or `/robovac <file or folder>` once after finishing a piece
of work. Each run is one whole pass over the project the tab is in, or over that file or folder. It
works in a temporary folder inside the project's git directory and deletes it at the end, so
everything you need is in its final reply.

- **clorox** moves leftovers it can prove are safe to remove into a bin at `~/.clorox/<repo>/`:
  caches that mark themselves as caches, `__pycache__` folders, identical iCloud " 2" copies and
  finished worktrees. Everything else stays. Bin batches older than 30 days are deleted.
- **stack-check** reviews your skills, agents, hooks, instruction files and memory against the last
  7 days of sessions in this repository, and suggests edits in its reply. It applies nothing.
- **build** checks the code against the rules in `skills/build/references/rules.md` and takes one
  task per pass: the worst rule break it can prove. It builds the fix in a fresh worktree, sends it
  through the review below, and on a clean verdict merges it into the project's local `main`
  without asking. Running `/robovac` is your permission for that merge. It never pushes. The
  worktree is removed when the pass ends. The branch is deleted once merged; a branch left at
  ready-to-merge, or a failed one that holds work worth keeping, stays. The pass's other findings
  aren't recorded, since the next pass finds whatever still stands. If the task fails twice, the
  pass stops and says why.

In the Claude Code desktop app, a slash command can't go inside another command's arguments, so type
`/loop 12h run the robovac skill` there.

vet and robovac are the only loop skills Claude can invoke on its own. A `/loop` wake re-enters each
one through the Skill tool, which refuses a skill marked as typed-only, so each description says to
use it only when typed or looped.

## Unattended changes

To hand Claude a task to finish on its own, type in your work tab:

```
/loop <task>. Done when <check>. Work in a new worktree.
```

`build` then follows `skills/build/references/long-run.md`: one change, one check and one log entry
per iteration, and the done-check is never relaxed. With no task given, the task is the code rules: a
broken rule sends that part of the code through build's checks.

## The review every change goes through

build calls it the gate (`skills/build/references/gate.md`). Each self-contained change is its own
branch, reviewed and merged alone; only changes that touch the same files wait for each other. For
each change, fresh agents that did not write it:

1. re-run the tests and checks at the exact commit,
2. prove the main behavior live on the smallest real surface that could disprove it,
3. review the diff in two lanes on two models (Sonnet by default, Opus for correctness), and
4. compare the result with `main`.

At most three agents run at once. The change merges when you have given permission and the verdict
is clean, as in pstack's autopilot-full. Without your permission it stops at ready-to-merge. It
never deploys.

## What happens to findings

The session you work in owns what vet reports and what a robovac pass replies with. Fix a finding
through `/build`, or dismiss it with the reason it's wrong. A `consider` finding is either built or
you decide against it. A kind of mistake seen twice goes to `/correct`, which turns it into a hook,
lint rule or test.

## How the repository is wired

- **`.claude-plugin/`** makes the repository both a plugin marketplace and the one plugin in it.
  Claude Code copies the plugin into `~/.claude/plugins/cache/` and reads its skills, agents and
  `hooks/hooks.json` from there. With no version in `plugin.json`, every commit is a new version.
- **`skills/<name>`** is linked from `~/.claude/skills/<name>` by a clone install, and
  **`agents/<name>.md`** from `~/.claude/agents/<name>.md`. A skill finds its own scripts and its
  sibling skills through `${CLAUDE_SKILL_DIR}`, so the same files work under either install. You edit and commit in the repository, and the links make every edit
  live at once. User-level skills reach every project and every Claude Code surface: the terminal,
  VS Code and the desktop app. No skill here is tied to one project; a project's own `verify-<app>`
  skill is made inside that project by `/create-verification-skill`.
- **`.claude/skills/verify-robovac`** is kstack's own test skill. It proves a change to the Robovac
  app or its hooks with a real Claude Code session and a filmed test copy of the app, against a
  baseline. Claude Code loads it in sessions opened in this repository; `install.sh` doesn't link
  it.
- **`hooks/hooks.json`** holds vet's session-start line and robovac's run hooks for the app. Each
  command runs its script from `${CLAUDE_PLUGIN_ROOT}/skills/`, which Claude Code fills in for the
  plugin. For a clone install, `hooks/install.py` merges them into `~/.claude/settings.json` with
  `$HOME/.claude/skills/` in that place: it adds missing ones, removes kstack
  hooks that `hooks.json` no longer has, and leaves every other hook alone.
- **`apps/<name>`** holds programs that are not skills, as pstack keeps benny under
  `automations/`. `apps/robovac-widget` is the Robovac app.
- **`upstream/`** holds pstack, four of Cursor's plugins and part of Matt Pocock's skills exactly as
  imported (MIT, see `NOTICE`), so every adapted part can be compared with its source. See
  [upstream/README.md](../upstream/README.md).
- A project opts into the loops and `/correct` by naming them in its own `CLAUDE.md`.

## Where each skill comes from

| Skill | Built from |
|---|---|
| `build` | Ours, plus pstack's bug-fix, refactoring, architect, blast-radius, tdd, benchmark-checklist, autonomous-run, prototype and principles. The gate comes from pstack's autopilot-full, shipping and swarm; the code rules from interrogate's rubric, OWASP, the OpenSSF Scorecard and the Twelve-Factor App. |
| `elon` | Ours. |
| `teach` | Ours, plus the machine-written tells from pstack's unslop. |
| `vet` | New, drawing on pstack's interrogate, swarm, show-me-your-work and autopilot-full's review lanes, and cursor-team-kit's thermo-nuclear review. |
| `robovac` | New, drawing on pstack's authoring-a-skill (delegation), autopilot-stack (the `/loop` cadence), recall (the branch in flight), and the stop rules of pause-safely and create-verification-skill. |
| `clorox` | pstack's worktree-cleanup and build-the-lever, the CACHEDIR.TAG spec, PEP 3147 and Claude Code's trash rule. |
| `stack-check` | pstack's reflect, its templates kept verbatim with Claude Code's names, plus two lines of ours, and its tooling lens run on Sonnet. |
| `correct` | pstack's correct and encode-lessons. |
| `polish` | Ours. |
| `create-verification-skill` | pstack's, translated to `.claude/skills/`, plus a data rule from our first verify skill. |
| `maintain-verification-skill` | pstack's, translated to end in a commit rather than a PR. |
| `improve-codebase-architecture` | Matt Pocock's, with the codebase-design, grilling and domain-modeling skills it calls carried as references, and grilling's rounds asked through AskUserQuestion. |
