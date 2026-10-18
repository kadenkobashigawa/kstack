#!/usr/bin/env python3
"""
test_install — runs hooks/install.py against throwaway settings files and checks the merge.

Run it with `python3 hooks/tests/test_install.py`; it uses this repo's hooks.json and skills, or
an install.py and repo named first. The exit code is 1 if any check fails.

H1 fills a missing file. H2 takes out a stale kstack hook and leaves the person's own hooks, other
skills' hooks and other settings alone, backing the file up first. H3 and H5 hold that a second run
changes nothing and that only stale hooks go. H6 keeps one command wanted under two matchers. H7
holds that hooks.json runs every script from the plugin root, and that the settings file gets the
same commands with install.sh's link folder in its place.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


repo = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent.parent
inst = sys.argv[1] if len(sys.argv) > 1 else str(repo / 'hooks' / 'install.py')
fails = []
def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + (f'  [{got}]' if got and not ok else ''))
    ok or fails.append(name)
def run(target, *extra):
    return subprocess.run([sys.executable, inst, str(repo / 'hooks/hooks.json'), str(target),
                           str(repo / 'skills'), *extra], capture_output=True, text=True)
raw = (repo / 'hooks/hooks.json').read_text()
want = json.loads(raw.replace('${CLAUDE_PLUGIN_ROOT}/skills/', '$HOME/.claude/skills/'))['hooks']


def cmds(s):
    """every hook in a settings dict, as (event, matcher, command), sorted."""
    return sorted((ev, e.get('matcher', ''), h['command']) for ev, es in s.get('hooks', {}).items()
                  for e in es for h in e['hooks'])


with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp) / 'settings.json'
    r = run(t)
    s = json.loads(t.read_text())
    check('H1 a missing file gets every kstack hook', cmds(s) == cmds({'hooks': want}), cmds(s))
    check('H1b and no backup of nothing', not (Path(tmp) / 'settings.json.kstack-backup').exists())

    mine = {'type': 'command', 'command': 'echo mine'}
    other = {'type': 'command', 'command': '"$HOME/.claude/skills/impeccable/scripts/x.sh"'}
    stale = {'type': 'command', 'command': '"$HOME/.claude/skills/stack-check/scripts/footprint.py" hook'}
    before = {'model': 'opus', 'hooks': {'SessionStart': [{'hooks': [mine, stale]}],
                                          'PostToolUse': [{'matcher': 'Edit', 'hooks': [other]}],
                                          'Stop': [{'hooks': [stale]}],
                                          'PreCompact': [{'hooks': [stale]}]}}
    t.write_text(json.dumps(before))
    r = run(t)
    s = json.loads(t.read_text())
    flat = cmds(s)
    check('H2 a stale kstack hook is taken out', all(c[2] != stale['command'] for c in flat), flat)
    check('H2b a hook of my own stays', ('SessionStart', '', 'echo mine') in flat, flat)
    check('H2c a non-kstack skill\'s hook stays', ('PostToolUse', 'Edit', other['command']) in flat, flat)
    check('H2d every wanted hook is there once', all(flat.count(c) == 1 for c in cmds({'hooks': want})), flat)
    check('H2e other settings stay', s.get('model') == 'opus', s.get('model'))
    check('H2f no empty entry or event is left',
          all(e['hooks'] for es in s['hooks'].values() for e in es) and all(s['hooks'].values()), s['hooks'])
    check('H2g the old file is backed up', json.loads((Path(tmp) / 'settings.json.kstack-backup').read_text()) == before)
    check('H2h the report names the changes', 'removed SessionStart hook' in r.stdout and 'added' in r.stdout, r.stdout)

    text = t.read_text()
    r = run(t)
    check('H3 a second run changes nothing', t.read_text() == text and 'already has' in r.stdout, r.stdout)
    check('H4 a wrong argument count exits 2', run(t, 'extra').returncode == 2)
    # H5: a settings file that already has every kstack hook, plus a stale one, loses only the stale...
    fresh = Path(tmp) / 'fresh.json'
    run(fresh)
    s = json.loads(fresh.read_text())
    s['hooks']['PreCompact'] = [{'hooks': [stale]}]
    fresh.write_text(json.dumps(s))
    run(fresh)
    s = json.loads(fresh.read_text())
    check('H5 only the stale hook goes, and no empty entry comes',
          cmds(s) == cmds({'hooks': want}) and all(e['hooks'] for es in s['hooks'].values() for e in es),
          s['hooks'])

    # H6: one command under two matchers of one event is added under both...
    two = Path(tmp) / 'two.json'
    c = want['PreToolUse'][0]['hooks'][0]
    two.write_text(json.dumps({'hooks': {'PreToolUse': [{'matcher': 'Skill', 'hooks': [c]},
                                                        {'matcher': 'Bash', 'hooks': [c]}]}}))
    t2 = Path(tmp) / 's2.json'
    subprocess.run([sys.executable, inst, str(two), str(t2), str(repo / 'skills')], capture_output=True)
    got = sorted(e['matcher'] for e in json.loads(t2.read_text())['hooks']['PreToolUse'])
    check('H6 a command wanted under two matchers gets both', got == ['Bash', 'Skill'], got)

    # H7: hooks.json is the plugin's, and the settings file gets install.sh's paths...
    plugin = [h['command'] for es in json.loads(raw)['hooks'].values() for e in es for h in e['hooks']]
    check('H7 every hooks.json command runs its script from ${CLAUDE_PLUGIN_ROOT}/skills/',
          plugin and all('${CLAUDE_PLUGIN_ROOT}/skills/' in c and '.claude/' not in c for c in plugin), plugin)
    seven = Path(tmp) / 'seven.json'
    run(seven)
    merged = [c[2] for c in cmds(json.loads(seven.read_text()))]
    check('H7b the settings file gets each command with $HOME/.claude/skills/ and no plugin root',
          len(merged) == len(plugin) and all('$HOME/.claude/skills/' in c and 'CLAUDE_PLUGIN_ROOT' not in c
                                             for c in merged), merged)
sys.exit(1 if fails else 0)
