# kstack

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Skills for [Claude Code](https://claude.com/claude-code) that build, review and clean up a codebase,
plus Robovac, a small macOS app that shows each cleanup run as a robot vacuum sweeping a house.

<p align="center">
  <img src="apps/robovac-widget/screenshots/robovac.gif" width="640"
       alt="The Robovac app: a robot vacuum sweeping along a round dining table in a top-down house">
</p>

kstack began as a Claude Code port of [pstack](https://github.com/cursor/plugins/tree/main/pstack)
by Lauren Tan, and most of its skills still build on pstack's. See [Credits](#credits).

## Install

You need Claude Code, `git` and `python3`.

```bash
git clone https://github.com/kadenkobashigawa/kstack.git ~/kstack
~/kstack/install.sh
```

`install.sh` links each skill into `~/.claude/skills` and each agent into `~/.claude/agents`, so
every project and every Claude Code surface picks them up. It also adds kstack's hooks to
`~/.claude/settings.json`, after saving a backup beside it. It never overwrites an existing folder,
and it's safe to run again. Keep the clone outside `~/.claude`, because Claude Code asks before
every edit inside a `.claude` folder.

**Update** by pulling and running the installer again:

```bash
git -C ~/kstack pull && ~/kstack/install.sh
```

**Uninstall** by deleting the links in `~/.claude/skills` and `~/.claude/agents` that point into
`~/kstack`, and removing the hooks that call `~/.claude/skills/vet` or `~/.claude/skills/robovac`
from `~/.claude/settings.json`.

## Skills

Automatic skills load a one-line description into every session, so Claude uses them when they fit.
The rest cost nothing until you run them.

| Skill | What it does | Runs |
|---|---|---|
| `build` | Four checks on every code change: understand what it touches, simplify, keep the diff on task, and verify it on the real path. | Automatically |
| `elon` | Questions every requirement in a design, deletes what nobody needs, then simplifies what's left. | Automatically, in design work |
| `teach` | Writing rules for explanations: plain words, short active sentences, and clear about what's known versus inferred. | Automatically, when explaining |
| `vet` | Reviews each new commit on `main` with two independent reviewers and reports only the findings it can prove. | In a loop, or `/vet` |
| `robovac` | One cleanup pass over a project: clears leftovers, reviews your Claude Code setup, and fixes one proven code problem. | In a loop, or `/robovac` |
| `clorox` | Moves proven leftovers (caches, `__pycache__`, duplicate iCloud copies, finished worktrees) into a bin it empties after 30 days. | Inside `robovac` |
| `stack-check` | Reviews your skills, agents, hooks and memory against the last week of sessions, and suggests edits without applying them. | Inside `robovac` |
| `correct` | Turns a mistake made twice into a hook, lint rule or test. | `/correct` |
| `polish` | Tidies comments and docstrings, and proves Python behavior didn't change. | `/polish` |
| `create-verification-skill` | Generates a `verify-<app>` skill that launches, drives and checks your real app. | `/create-verification-skill` |
| `maintain-verification-skill` | Keeps a `verify-<app>` skill accurate as the app changes. | `/maintain-verification-skill` |

Three agents come with them:

- `vet-reviewer`: a read-only code reviewer that `vet` spawns, one focus per reviewer.
- `researcher`: read-only prior-art research across docs, GitHub and papers, used by `build` for
  design work.
- `impeccable-finish-reviewer`: a final review for UI work built with
  [impeccable](https://github.com/pbakaus/impeccable), which you install separately.

## Running the loops

`vet` and `robovac` are meant to run on a schedule with Claude Code's `/loop`, each in its own tab.

**Commit review.** `/loop /vet watch` reviews new commits on `main` after the branch has been quiet
for five minutes, or hourly. Two fresh reviewers read each batch, one for structure and one for
correctness, and a lead keeps only the findings it can prove. vet never edits code, commits or
pushes.

**Cleanup.** `/loop 12h /robovac` runs a full pass twice a day, or run `/robovac <file or folder>`
once after finishing a piece of work. Each pass bins leftovers, reviews your setup, and fixes the
worst code-rule problem it can prove. The fix is built in a temporary worktree, reviewed by agents
that didn't write it, and merged into your local `main` only if the review is clean. robovac never
pushes, and it reports everything in its final reply.

In the Claude Code desktop app, type `/loop 12h run the robovac skill` instead, since a slash command
can't go inside another command's arguments.

[docs/how-it-works.md](docs/how-it-works.md) covers the loops, the review process and unattended
runs in detail.

## Robovac

Robovac shows each running robovac session as a robot in its own suite of rooms, up to nine at once.
A robot sweeps while its session works and docks when the session is done or waiting on you, so you
can see at a glance which tab needs you.

It needs macOS 13 or later and Apple's Command Line Tools (`xcode-select --install`). To build it and
install it in `~/Applications`:

```bash
~/kstack/apps/robovac-widget/mac/build.sh
open ~/Applications/Robovac.app
```

Build it on each Mac you use it on, because Gatekeeper blocks a copy sent from another Mac.

**Privacy.** kstack's hooks log robovac sessions' activity to `~/.claude/robovac/runs.jsonl`, which
the app reads. Tool inputs are stored only as digests, and nothing leaves your Mac. The
[app's README](apps/robovac-widget/README.md) lists exactly what's recorded.

## Repository layout

```
skills/      the skills, linked into ~/.claude/skills
agents/      the agents, linked into ~/.claude/agents
hooks/       kstack's hooks and the script that merges them into settings.json
apps/        the Robovac app
docs/        how the loops and reviews work
upstream/    pstack and Cursor's plugins, unmodified, for reference
tests/       tests for install.sh
```

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to change a
skill and run the tests.

## Credits

- [pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan
  ([@poteto](https://github.com/poteto)) is the source of most of kstack: build's methods and review
  process, vet's reviewers, clorox, stack-check, `/correct` and the verification skills.
- [cursor-team-kit](https://github.com/cursor/plugins/tree/main/cursor-team-kit),
  [continual-learning](https://github.com/cursor/plugins/tree/main/continual-learning),
  [ralph-loop](https://github.com/cursor/plugins/tree/main/ralph-loop) and
  [orchestrate](https://github.com/cursor/plugins/tree/main/orchestrate) from
  [cursor/plugins](https://github.com/cursor/plugins). ralph-loop implements Geoffrey Huntley's
  [Ralph Wiggum technique](https://ghuntley.com/ralph/).
- [impeccable](https://github.com/pbakaus/impeccable) by Paul Bakaus shaped Robovac's design.
- The code rules draw on [OWASP](https://owasp.org), the
  [OpenSSF Scorecard](https://github.com/ossf/scorecard) and
  [the Twelve-Factor App](https://12factor.net). clorox follows the
  [CACHEDIR.TAG spec](https://bford.info/cachedir/) and [PEP 3147](https://peps.python.org/pep-3147/).

Each skill names what it adapts in its own files, and [docs/how-it-works.md](docs/how-it-works.md#where-each-skill-comes-from)
traces every skill to its sources.

## License

MIT, see [LICENSE](LICENSE). The parts adapted from pstack and Cursor's plugins keep their own MIT
notices, listed in [NOTICE](NOTICE).
