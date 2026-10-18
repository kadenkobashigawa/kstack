#!/usr/bin/env python3
'''
install — merges kstack's hooks into a Claude Code settings file: the ones in hooks.json are added
where missing, a hook that names a kstack skill but is no longer in hooks.json is taken out, and
every other hook is left as it is. The file is backed up beside itself before it changes.

hooks.json is written for the plugin install, where Claude Code fills in ${CLAUDE_PLUGIN_ROOT}. A
settings file has no plugin root, so each command's ${CLAUDE_PLUGIN_ROOT}/skills/ becomes
$HOME/.claude/skills/, where install.sh links the same skills.

Usage
-----
    install.py <hooks.json> <settings.json> <skills-dir>

Methods
-------
    owned :
        whether a hook command runs a kstack skill's script.
    merge :
        the settings with kstack's hooks brought up to date, and what changed.
    main :
        merge, write and report.
'''

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

#a hook command's plugin path, and where install.sh links the same skills...
PLUGIN = '${CLAUDE_PLUGIN_ROOT}/skills/'
LINKED = '$HOME/.claude/skills/'


def owned(command: str, skills: set[str]) -> bool:
    '''whether a hook command runs a script under one of kstack's skill folders.'''
    return any(re.search(rf'(\$HOME|~)/\.claude/skills/{re.escape(s)}/', command) for s in skills)


def merge(settings: dict, want: dict, skills: set[str]) -> tuple[dict, list[str]]:
    '''
    the settings with kstack's hooks brought up to date, and what changed.

    Parameters
    ----------
    settings : dict
        the settings file as read.
    want : dict
        hooks.json's `hooks`: event name to a list of {matcher, hooks}.
    skills : set of str
        the names of kstack's skill folders, which decide what counts as kstack's.

    Returns
    -------
    tuple
        the new settings, and one line per hook added or removed.
    '''
    hooks = settings.setdefault('hooks', {})
    wanted = {(ev, m.get('matcher', ''), h['command'])
              for ev, entries in want.items() for m in entries for h in m['hooks']}
    changes = []
    for ev in list(hooks):
        for entry in list(hooks[ev]):
            kept = []
            for h in entry.get('hooks', []):
                key = (ev, entry.get('matcher', ''), h.get('command', ''))
                if owned(key[2], skills) and key not in wanted:
                    changes.append(f'removed {ev} hook: {key[2]}')
                else:
                    kept.append(h)
            entry['hooks'] = kept
            if not kept:
                hooks[ev].remove(entry)
        if not hooks[ev]:
            del hooks[ev]
    for ev, entries in want.items():
        have = hooks.setdefault(ev, [])
        for m in entries:
            matcher = m.get('matcher', '')
            present = {x.get('command') for e in have if e.get('matcher', '') == matcher
                       for x in e.get('hooks', [])}
            missing = [h for h in m['hooks'] if h['command'] not in present]
            if missing:
                have.append({'matcher': matcher, 'hooks': missing} if matcher else {'hooks': missing})
                changes += [f'added {ev} hook: {h["command"]}' for h in missing]
    return settings, changes


def main(argv: list[str]) -> int:
    '''
    merge kstack's hooks into the settings file, write it if anything changed, and report.

    Parameters
    ----------
    argv : list of str
        the hooks file, the settings file and the skills folder.

    Returns
    -------
    int
        0, or 2 with this docstring printed for a wrong argument count.
    '''
    if len(argv) != 3:
        print(__doc__)
        return 2
    want = json.loads(Path(argv[0]).read_text().replace(PLUGIN, LINKED))['hooks']
    target = Path(argv[1]).expanduser()
    skills = {p.name for p in Path(argv[2]).iterdir() if (p / 'SKILL.md').exists()}
    settings = json.loads(target.read_text()) if target.exists() else {}
    settings, changes = merge(settings, want, skills)
    if not changes:
        print(f'hooks: {target} already has kstack\'s hooks')
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy2(target, target.with_name(target.name + '.kstack-backup'))
    target.write_text(json.dumps(settings, indent=2) + '\n')
    for line in changes:
        print(f'hooks: {line}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
