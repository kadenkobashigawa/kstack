# How kstack works

The README covers installing and using kstack. This page covers what happens underneath: the
cleanup pass, the review every change goes through, and how the repository is wired into Claude
Code. Commands are shown as a clone install names them. With the plugin, prefix each with `kstack:`,
as in `/kstack:robovac`.

## robovac: the cleanup pass

Run `/loop 12h /robovac` in its own tab, or `/robovac <file or folder>` once after finishing a piece
of work. Each run is one whole pass over the project the tab is in, or over that file or folder. It
works in a temporary folder inside the project's git directory and deletes it at the end, so
everything you need is in its final reply.

- **clorox** moves leftovers it can prove are safe to remove into a bin at `~/.clorox/<repo>/`:
  caches that mark themselves as caches, `__pycache__` folders, identical iCloud " 2" copies and
  finished worktrees. Everything else stays. Bin batches older than 30 days are deleted.
- **stack-check** reviews your skills, agents, hooks, instruction files and memory against the last
  7 days of sessions that worked in this repository, from any workspace, and suggests edits in its
  reply. It applies nothing.
- **build** checks the code against the rules in `skills/build/references/rules.md` and takes one
  task per pass: the worst rule break it can prove. It builds the fix in a fresh worktree, sends it
  through the review below, and on a clean verdict merges it into the project's local `main`
  without asking, under build's standing grant to merge locally. It never pushes. The worktree is
  removed when the pass ends. The branch is deleted once merged. A branch left at merge-ready, or a
  failed one that holds work worth keeping, stays. The pass lists its other findings in its reply
  and leaves them for the next pass. If the task fails twice, the pass stops and says why.

In the Claude Code desktop app, a slash command can't go inside another command's arguments, so type
`/loop 12h run the robovac skill` there.

robovac is kstack's only loop skill, so it stays one Claude can invoke. A `/loop` wake re-enters it
through the Skill tool, which refuses a skill marked typed-only (`disable-model-invocation`).
Instead, its description says to use it only when typed or looped.

## Unattended changes

To hand Claude a task to finish on its own, type in your work tab:

```
/loop <task>. Done when <check>. Work in a new worktree.
```

`build` then follows `skills/build/references/long-run.md`: one change, one check and one log
entry per iteration, and the done-check is never relaxed. With no task given, the run checks its
part of the code against the code rules and takes one task: the worst broken rule it can prove,
fixed through one of build's playbooks.

## The review every change goes through

build routes each code change to one of four playbooks: feature, bug fix, refactor or performance.
The session you talk to leads, and fresh subagents write the code. Every playbook ends at the same
review, which build calls the gate (`skills/build/references/gate.md`). Each self-contained change
is its own branch, in its own worktree, reviewed and merged alone. Only changes that touch the same
files wait for each other. Before a round, the author runs the checks the project's own rules name
for the files it touched. Then, for each change, fresh agents that did not write it:

1. re-run the tests and checks at the exact commit,
2. prove the main behavior live on the smallest real surface that could disprove it,
3. review the diff in two lanes on two models (Opus for correctness, Sonnet for structure), and
4. compare the result with `main`.

`skills/build/scripts/gate.py` records each lane's result in the
branch's ledger. A clean verdict merges the change into local `main` under a standing grant, as in
pstack's autopilot-full. `gate.py land` makes that merge as one commit whose message carries a
`GATE VERDICT:` line, and it refuses without a clean verdict. A change you named, or asked to see
first, stops at merge-ready. Pushing stays yours, and build never deploys.

## What happens to findings

The session you work in owns what a robovac pass replies with. Fix a finding through `/build`, or
dismiss it with the reason it's wrong. A `consider` finding is a call only you can make: build it,
or decide against it. For a kind of mistake seen twice, the session proposes `/correct`, which only
you can type, and which turns the mistake into a hook, lint rule or test.

## How the repository is wired

- **`.claude-plugin/`** makes the repository both a plugin marketplace and the one plugin in it.
  Claude Code copies the plugin into `~/.claude/plugins/cache/` and reads its skills, agents and
  `hooks/hooks.json` from there. With no version in `plugin.json`, every commit is a new version.
- **`skills/<name>`** is linked from `~/.claude/skills/<name>` by a clone install, and
  **`agents/<name>.md`** from `~/.claude/agents/<name>.md`. A skill finds its own scripts and its
  sibling skills through `${CLAUDE_SKILL_DIR}`, so the same files work under either install. You
  edit and commit in the repository, and the links make every edit live at once. User-level skills
  reach every project and every Claude Code surface: the terminal, VS Code and the desktop app. No
  skill here is tied to one project. A project's own `verify-<app>` skill is made inside that
  project by `/create-verification-skill`.
- **`.claude/skills/verify-robovac`** is kstack's own test skill. It proves a change to the Robovac
  app or its hooks with a real Claude Code session and a filmed test copy of the app, against a
  baseline. Claude Code loads it in sessions opened in this repository, and `install.sh` doesn't
  link it.
- **`hooks/hooks.json`** holds robovac's run hooks for the app, and no other hooks. Each command
  runs its script from `${CLAUDE_PLUGIN_ROOT}/skills/`, which Claude Code fills in for the plugin.
  For a clone install, `hooks/install.py` merges them into `~/.claude/settings.json` with
  `$HOME/.claude/skills/` in that place. It adds missing ones, removes hooks that run a kstack
  skill's script but are no longer in `hooks.json`, and leaves every other hook alone. A kstack
  skill is one the checkout holds, or one whose `~/.claude/skills` link, live or dead, points into
  the checkout's `skills/`, so a retired skill's hook goes too, even when git-ignored files keep its
  folder there. It then removes each dead link in
  `~/.claude/skills` that points into the checkout's `skills/`, and each in `~/.claude/agents` that
  points into its `agents/`. A link into anywhere else, `upstream/` included, stays.
- **`apps/<name>`** holds programs that are not skills, as pstack keeps benny under
  `automations/`. `apps/robovac-widget` is the Robovac app.
- **`upstream/`** holds pstack, four of Cursor's plugins and part of Matt Pocock's skills exactly as
  imported (MIT, see `NOTICE`), so every adapted part can be compared with its source. See
  [upstream/README.md](../upstream/README.md).
- A project needs no setup for robovac or `/correct`. Naming them in its own `CLAUDE.md` tells
  every session there how the project uses them.

## Where each skill comes from

| Skill | Built from |
|---|---|
| `build` | Ours, plus pstack's poteto-mode (one playbook per change, its triggers, Autonomy and Subagents) and its feature, bug-fix, refactoring, perf-issue, autonomous-run and prototype playbooks. Also pstack's architect, interrogate, blast-radius, tdd, benchmark-checklist, technical-writing and show-me-your-work skills, and its principles, attack-the-premise among them. The gate comes from pstack's autopilot-full, shipping and swarm. The code rules come from interrogate's rubric, OWASP, the OpenSSF Scorecard and the Twelve-Factor App. |
| `elon` | Ours. |
| `teach` | Ours, plus the machine-written tells from pstack's unslop. |
| `write-report` | kstack's own. Its layout's values trace to Sphinx's LaTeX output, DocBook XSL-FO, the PostgreSQL manual and the Read the Docs theme, and its prose step reads kstack's technical-writing and unslop. |
| `robovac` | New, drawing on pstack's authoring-a-skill (delegation), autopilot-stack (the `/loop` cadence), autonomous-run and orchestrate (one task, the rest left for later), autopilot-full (the merge grant), and the stop rules of pause-safely and create-verification-skill. |
| `clorox` | pstack's worktree-cleanup and build-the-lever, the CACHEDIR.TAG spec, PEP 3147 and Claude Code's trash rule. |
| `stack-check` | pstack's reflect, its templates kept verbatim with Claude Code's names, plus two lines of kstack's own, and its tooling lens run on Sonnet. The 7-day window is pstack's recall default. |
| `correct` | pstack's correct and encode-lessons. |
| `polish` | Ours. |
| `unslop` | pstack's unslop, copied verbatim. |
| `technical-writing` | pstack's technical-writing, copied verbatim. |
| `create-verification-skill` | pstack's, translated to `.claude/skills/`, plus a data rule from our first verify skill. |
| `maintain-verification-skill` | pstack's, translated to end in a commit rather than a PR. |
| `improve-codebase-architecture` | Matt Pocock's, with the codebase-design, grilling and domain-modeling skills it calls carried as references, and grilling's rounds asked through AskUserQuestion. |
