#!/usr/bin/env python3
'''
install — brings kstack's part of a Claude Code folder up to date. It merges kstack's hooks into
the folder's settings file: the ones in hooks.json are added where missing, a hook that names a
kstack skill but is no longer in hooks.json is taken out, and every other hook is left as it is.
The file is backed up beside itself before it changes. Then it removes each dead link in the
folder's skills/ and agents/ that points into the checkout's folder of the same name, which is
where install.sh links them, and prints how many live links into those two folders remain.

A skill is kstack's when the checkout has skills/<name>/SKILL.md, or when the folder's
skills/<name> is a link, live or dead, into the checkout's skills/, where only install.sh links.
The second case covers a retired skill. Its link is dead once the folder is gone, or live when
git-ignored files such as __pycache__/ keep the folder with no SKILL.md, and either way the link
is the last trace of its name, so the names are read before any link is removed. A link into
anywhere else in the checkout, such as upstream/, is the person's own and stays.

hooks.json is written for the plugin install, where Claude Code fills in ${CLAUDE_PLUGIN_ROOT}. A
settings file has no plugin root, so each command's ${CLAUDE_PLUGIN_ROOT}/skills/ becomes
$HOME/.claude/skills/, where install.sh links the same skills.

Usage
-----
    install.py <hooks.json> <settings.json> <skills-dir>

The Claude Code folder is the settings file's folder, and the checkout is the skills folder's
parent.

Methods
-------
    Checkout :
        a kstack checkout, its realpath prefix, and the names kstack owns.
    inside :
        whether a link's target resolves into a folder of the checkout.
    checkout :
        the Checkout for a skills folder, with names read from the checkout and the links.
    owned :
        whether a hook command runs a kstack skill's script.
    merge :
        the settings with kstack's hooks brought up to date, and what changed.
    write :
        back up and write the settings file, and report.
    prune :
        remove dead links into one checkout folder from one folder.
    live :
        how many live links in one folder resolve into one checkout folder.
    main :
        read the names, merge and write, prune, count.
'''

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

#a hook command's plugin path, and where install.sh links the same skills...
PLUGIN = '${CLAUDE_PLUGIN_ROOT}/skills/'
LINKED = '$HOME/.claude/skills/'


@dataclass(frozen=True)
class Checkout:
    '''a kstack checkout as install.sh named it, its realpath prefix, and the names kstack owns.'''

    path:  Path
    root:  str
    names: frozenset[str]


def inside(link: Path, root: str) -> bool:
    '''whether a link's target, resolved as far as it exists, lies under `root`.'''

    #realpath follows the link and any link in its target's path, even when the target is gone...
    return os.path.realpath(link).startswith(root)


def checkout(skills: Path, linked: Path) -> Checkout:
    '''
    the Checkout for a skills folder, with names read from the checkout and from the links.

    Parameters
    ----------
    skills : Path
        the checkout's skills folder, as install.sh passed it.
    linked : Path
        the Claude Code folder's skills/, where install.sh links them. It may not exist.

    Returns
    -------
    Checkout
        names are every skills/<name>/SKILL.md, plus every link, live or dead, in `linked`
        that is `inside` the checkout's skills/.

    Notes
    -----
    Call it before `prune`, because a retired skill's link is the only record that its name was
    kstack's. The link is live when git-ignored files outlive the skill's SKILL.md in its folder.
    '''
    root = os.path.realpath(skills.parent) + '/'
    names = {p.name for p in skills.iterdir() if (p / 'SKILL.md').exists()}
    if linked.is_dir():
        names |= {p.name for p in linked.iterdir()
                  if p.is_symlink() and inside(p, root + 'skills/')}
    return Checkout(skills.parent, root, frozenset(names))


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


def write(target: Path, settings: dict, changes: list[str]) -> None:
    '''
    back up and write the settings file if anything changed, and print one line per change.

    Parameters
    ----------
    target : Path
        the settings file.
    settings : dict
        the merged settings.
    changes : list of str
        merge's report. When it is empty, write prints that the file already has kstack's
        hooks and leaves the file alone.
    '''
    if not changes:
        print(f'hooks: {target} already has kstack\'s hooks')
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        backup = target.with_name(target.name + '.kstack-backup')

        #copy2 carries the mode over, so a read-only backup from an earlier run is removed first...
        backup.unlink(missing_ok=True)
        shutil.copy2(target, backup)
    target.write_text(json.dumps(settings, indent=2) + '\n')
    for line in changes:
        print(f'hooks: {line}')


def prune(folder: Path, root: str) -> list[Path]:
    '''
    remove every dead link in `folder` whose target resolves under `root`, and print each.

    Parameters
    ----------
    folder : Path
        the Claude Code folder's skills/ or agents/. A missing folder removes nothing.
    root : str
        the realpath, with a trailing '/', of the checkout folder install.sh links `folder` to.

    Returns
    -------
    list of Path
        the links removed, each printed as `unlinked  <path> (was <target>)`.

    Notes
    -----
    Removes only a link whose target is missing and is `inside` root. It never follows a link and
    never removes a real file, so anything not proven kstack's stays.
    '''
    if not folder.is_dir():
        return []
    gone = []
    for p in sorted(folder.iterdir()):
        if p.is_symlink() and not p.exists() and inside(p, root):
            print(f'unlinked  {p} (was {os.readlink(p)})')
            p.unlink()
            gone.append(p)
    return gone


def live(folder: Path, root: str) -> int:
    '''how many links in `folder` have an existing target `inside` root, or 0 for no folder.'''
    if not folder.is_dir():
        return 0
    return sum(1 for p in folder.iterdir() if p.is_symlink() and p.exists() and inside(p, root))


def main(argv: list[str]) -> int:
    '''
    bring kstack's part of the settings file's folder up to date, and report.

    Parameters
    ----------
    argv : list of str
        the hooks file, the settings file and the checkout's skills folder.

    Returns
    -------
    int
        0, or 2 with this module's docstring printed for a wrong argument count.

    Notes
    -----
    The order is the contract. The names are read from the links first, the settings are written
    second, and the dead links go third. A failed settings write leaves the links, so a re-run
    still finds the retired names. Pruning first would lose them and strand the hook.
    '''
    if len(argv) != 3:
        print(__doc__)
        return 2
    target   = Path(argv[1]).expanduser()
    claude   = target.parent
    ks       = checkout(Path(argv[2]), claude / 'skills')
    want     = json.loads(Path(argv[0]).read_text().replace(PLUGIN, LINKED))['hooks']
    settings = json.loads(target.read_text()) if target.exists() else {}
    write(target, *merge(settings, want, set(ks.names)))
    for kind in ('skills', 'agents'):
        prune(claude / kind, ks.root + kind + '/')
    print(f'done: {live(claude / "skills", ks.root + "skills/")} skill link(s), '
          f'{live(claude / "agents", ks.root + "agents/")} agent link(s) into {ks.path}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
