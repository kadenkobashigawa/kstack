# Contributing

Issues and pull requests are welcome. For a larger change, open an issue first so we can agree on the
approach.

## Changing a skill or agent

Skills live in `skills/<name>/` and agents in `agents/<name>.md`. After `install.sh`, they're linked
into `~/.claude`, so an edit is live in every session at once.

1. Edit the skill's `SKILL.md` or its references.
2. Run it once on a real case. A skill that has never run is a draft.
3. Run its tests, if it has any, and commit.

Keep each description short and specific: an automatic skill's description is loaded into every
session. A new skill that only you start gets `disable-model-invocation: true` in its front matter.
When a skill adapts something from `upstream/`, name the source in the skill's own files.

## Tests

Each test is a script you run directly:

```bash
python3 tests/test_install_sh.py
python3 hooks/tests/test_install.py
python3 skills/clorox/tests/test_clorox.py
```

The other skills follow the same pattern under `skills/<name>/tests/`. The Robovac app's tests are
in `apps/robovac-widget/tests/`; the page and icon tests need a Python with Playwright and Pillow
(see `apps/robovac-widget/requirements-dev.txt`), which they find through `$ROBOVAC_PY`:

```bash
export ROBOVAC_PY=/path/to/venv/bin/python
"$ROBOVAC_PY" apps/robovac-widget/tests/test_page.py
zsh apps/robovac-widget/tests/test_icon.sh
```

## The Robovac app

- `apps/robovac-widget/mac/build.sh` rebuilds and reinstalls the app.
- `mac/images.sh build` remakes the house images. It needs Playwright's WebKit and Pillow.
- `mac/images.sh publish` releases the new image pack and updates `images.lock`, so other Macs fetch
  it. It needs the GitHub CLI signed in with access to this repository.
- `mac/demo.sh` records the GIF in the README. It needs `ffmpeg`, the Command Line Tools and Screen
  Recording permission for the app you run it from.

A change to the app or its hooks is proved with `.claude/skills/verify-robovac`, which Claude Code
loads in sessions opened in this repository.
