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

You need Claude Code, `git` and `python3`. Pick one of the two methods below. With both, kstack's
hooks would run twice.

### From the plugin marketplace

In Claude Code, run:

```
/plugin marketplace add kadenkobashigawa/kstack
/plugin install kstack@kstack
```

Plugin skills are namespaced, so you type `/kstack:robovac`, `/kstack:polish` and so on. Update with
`/plugin marketplace update kstack`, and uninstall with `/plugin uninstall kstack@kstack`.

### From a clone

Use this if you want to edit the skills.

```bash
git clone https://github.com/kadenkobashigawa/kstack.git ~/kstack
~/kstack/install.sh
```

`install.sh` links each skill into `~/.claude/skills` and each agent into `~/.claude/agents`, so
every project and every Claude Code surface picks them up, without the `kstack:` prefix. It also
adds kstack's hooks to `~/.claude/settings.json`, after saving a backup beside it as
`settings.json.kstack-backup`. It never overwrites an existing folder, and it's safe to run again.
Each run also removes the hooks and dead links that a retired skill left behind. It removes only a
dead link into the clone's `skills` or `agents` folder, so a dead link to anywhere else stays. Keep
the clone outside `~/.claude`, because Claude Code asks before every edit inside a `.claude` folder.

**Update** by pulling and running the installer again, then rebuilding Robovac if you use it:

```bash
git -C ~/kstack pull && ~/kstack/install.sh
```

**Uninstall** by deleting the links in `~/.claude/skills` and `~/.claude/agents` that point into
`~/kstack`, and removing kstack's hooks from `~/.claude/settings.json`. Each of those hooks runs a
script under `$HOME/.claude/skills/<name>/`, where `<name>` is one of those links. If you built
Robovac, delete `~/Applications/Robovac.app` too.

## Skills

Every skill except the seven you type yourself loads a one-line description into every session, so
Claude can use it when it fits. `robovac`, `clorox` and `stack-check` stay visible this way so
that a loop or a robovac pass can call them. `correct`, `polish`, `unslop`, `technical-writing`,
`improve-codebase-architecture` and the two verification skills cost nothing until you run them.

| Skill | What it does | Runs |
|---|---|---|
| `build` | Sends each code change through one of four playbooks (feature, bug fix, refactor, performance). The session you talk to leads, and fresh subagents write the code. The steps map what the change touches, simplify it, keep the diff on task and run it on the real path. A clean review by agents that did not write the change merges it into local main. | Automatically |
| `elon` | Questions every requirement in a design, deletes what nobody needs, then simplifies what's left. | Automatically, in design work |
| `teach` | Writing rules for explanations: plain words, short active sentences, and a clear line between what's known and what's inferred. | Automatically, when explaining |
| `write-report` | Writes a report or manual in Markdown and renders it to a numbered PDF and a matching web page in a fixed manual layout, after a technical-writing and unslop pass on its prose. | Automatically, when asked for a report or a manual delivered as a PDF |
| `study` | Builds an interactive mind map of one scope (code, a skill or notes) and opens it beside the chat, then walks you through a branch, writes hover cards for it, or quizzes you on it. Maps and cards stay in a `.study/` folder, kept out of git by a `.study/.gitignore` that `where.py` writes. In a git repository that folder is at the top of the work tree; outside git it is in the studied folder. | Automatically, when asked to study or map something or for a mind map, or to walk through, write cards for or quiz on a map; or `/study` |
| `robovac` | One cleanup pass over a project: clears leftovers, reviews your Claude Code setup, and fixes one proven code problem, merging that fix into local main. It never pushes. | In a loop, or `/robovac` |
| `clorox` | Moves proven leftovers (caches, `__pycache__`, duplicate iCloud copies, finished worktrees) into a bin it empties after 30 days. | Inside `robovac` |
| `stack-check` | Reviews your skills, agents, hooks and memory against the last week of sessions, and suggests edits without applying them. | Inside `robovac` |
| `correct` | Turns a mistake made twice into a hook, lint rule or test. | `/correct` |
| `polish` | Tidies comments and docstrings, and proves Python behavior didn't change. | `/polish` |
| `unslop` | Cuts the tells that mark writing as machine-written. A verbatim copy of pstack's skill. | `/unslop` |
| `technical-writing` | Shapes a document so a tired engineer understands it on first read: one kind of document per page, plain sentences, conditions first. A verbatim copy of pstack's skill. | `/technical-writing` |
| `improve-codebase-architecture` | Finds shallow modules worth deepening, draws them as a before-and-after HTML report, then interviews you about the one you pick. Never changes code. | `/improve-codebase-architecture` |
| `create-verification-skill` | Generates a `verify-<app>` skill that launches, drives and checks your real app. | `/create-verification-skill` |
| `maintain-verification-skill` | Keeps a `verify-<app>` skill accurate as the app changes. | `/maintain-verification-skill` |

Two agents come with them:

- `researcher`: read-only prior-art research across docs, GitHub and papers, used by `build` for
  design work.
- `impeccable-finish-reviewer`: a final review for UI work built with
  [impeccable](https://github.com/pbakaus/impeccable), which you install separately.

## Running robovac

`robovac` is meant to run on a schedule with Claude Code's `/loop`, in its own tab. The commands
below are a clone install's. With the plugin, type `/kstack:robovac`.

`/loop 12h /robovac` runs a full pass twice a day, or run `/robovac <file or folder>` once after
finishing a piece of work. Each pass bins leftovers, reviews your setup, and fixes the worst
code-rule problem it can prove. The fix is built in a temporary worktree, reviewed by agents that
didn't write it, and merged into your local `main` only if the review is clean. robovac never
pushes. Its final reply lists what it moved, suggested and merged. Other findings are left for the
next pass.

In the Claude Code desktop app, type `/loop 12h run the robovac skill` instead, since a slash
command can't go inside another command's arguments.

[docs/how-it-works.md](docs/how-it-works.md) covers robovac, the review process and unattended
runs in detail.

## Robovac

Robovac shows each running robovac session as a robot in its own suite of rooms, up to nine at once.
A robot sweeps while its session works and docks when the session is done or waiting on you, so you
can see at a glance which tab needs you.

It needs macOS 13 or later and Apple's Command Line Tools (`xcode-select --install`), and it builds
from a clone of this repository. To build it and install it in `~/Applications`:

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
.claude-plugin/  the plugin and marketplace manifests
skills/          the skills, linked into ~/.claude/skills
agents/          the agents, linked into ~/.claude/agents
hooks/           kstack's hooks and the script that merges them into settings.json
apps/            the Robovac app
docs/            how robovac, unattended runs and the review work
upstream/        pstack, Cursor's plugins and Matt Pocock's skills, unmodified, for reference
tests/           tests for install.sh
```

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to change a
skill and run the tests.

## Credits

- [pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan
  ([@poteto](https://github.com/poteto)) is the source of most of kstack: build's methods and review
  process, clorox, stack-check, `/correct`, the verification skills, and `unslop` and
  `technical-writing`, which are copied verbatim.
- [cursor-team-kit](https://github.com/cursor/plugins/tree/main/cursor-team-kit),
  [continual-learning](https://github.com/cursor/plugins/tree/main/continual-learning),
  [ralph-loop](https://github.com/cursor/plugins/tree/main/ralph-loop) and
  [orchestrate](https://github.com/cursor/plugins/tree/main/orchestrate) from
  [cursor/plugins](https://github.com/cursor/plugins). ralph-loop implements Geoffrey Huntley's
  [Ralph Wiggum technique](https://ghuntley.com/ralph/).
- [Matt Pocock's skills](https://github.com/mattpocock/skills) are the source of
  `improve-codebase-architecture`, with the codebase-design, grilling and domain-modeling skills it
  reads.
- [impeccable](https://github.com/pbakaus/impeccable) by Paul Bakaus shaped Robovac's design.
- [markmap](https://github.com/markmap/markmap) by Gerald and [d3](https://d3js.org) by Mike
  Bostock draw study's maps, vendored under `skills/study/vendor/` (see `NOTICE`).
- The code rules draw on [OWASP](https://owasp.org), the
  [OpenSSF Scorecard](https://github.com/ossf/scorecard) and
  [the Twelve-Factor App](https://12factor.net). clorox follows the
  [CACHEDIR.TAG spec](https://bford.info/cachedir/) and [PEP 3147](https://peps.python.org/pep-3147/).

Each skill names what it adapts in its own files, and
[docs/how-it-works.md](docs/how-it-works.md#where-each-skill-comes-from) traces every skill to its
sources.

## License

MIT, see [LICENSE](LICENSE). The parts adapted from pstack, Cursor's plugins and Matt Pocock's
skills keep their own MIT notices, listed in [NOTICE](NOTICE).
