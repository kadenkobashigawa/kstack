#!/usr/bin/env python3
"""
test_install_sh — runs install.sh with HOME set to a throwaway folder and checks what it links.

Run it with `python3 tests/test_install_sh.py`; it uses the repo this file sits in, or a repo named
first. Every run of install.sh gets its own fresh HOME from tempfile, never the real one. The exit
code is 1 if any check fails.

I0 holds that the repo has skills and agents to link. I1 links every skill folder that holds a
SKILL.md, and every agent, into the repo on a fresh HOME. I2 holds that a second run links and
relinks nothing and leaves settings.json byte-identical. I3 names a real folder in a skill link's
place on a skipped line and leaves it a real folder holding only its own file; I4 leaves a real file
in an agent link's place as it was. I5 relinks a link that points elsewhere, without writing into
the old target. I6 holds that the closing count names only links into the repo, not a link into a
folder beside it whose path starts with the repo's. I7 runs a copy of install.sh in a throwaway repo
whose skills folder holds one folder with no SKILL.md beside a real skill, and holds that it links
only the real one and counts only that one.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


repo = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent).resolve()
skills = sorted(p.parent.name for p in repo.glob('skills/*/SKILL.md'))
agents = sorted(p.name for p in repo.glob('agents/*.md'))
fails = []
def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + (f'  [{got}]' if got and not ok else ''))
    ok or fails.append(name)
def run(home, at=repo):
    """the install.sh in `at` once, with HOME set to `home`, as (exit code, stdout and stderr)."""
    env = dict(os.environ, HOME=str(home))
    r = subprocess.run(['bash', str(at / 'install.sh')], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr
def links(home, kind):
    """every link in `home`'s .claude/<kind>, as name -> target."""
    d = Path(home) / '.claude' / kind
    return {p.name: os.readlink(p) for p in d.iterdir() if p.is_symlink()}
def done(out):
    """the closing line's skill count, agent count and folder, or None."""
    m = re.search(r'^done: (\d+) skill link\(s\), (\d+) agent link\(s\) into (.*)$', out, re.M)
    return m and (int(m[1]), int(m[2]), m[3])
def named(out, word, path):
    """whether a `word` line of install.sh's output names `path`."""
    return re.search(rf'^{word} +{re.escape(str(path))}[: ]', out, re.M) is not None


want_skills = {n: str(repo / 'skills' / n) for n in skills}
want_agents = {n: str(repo / 'agents' / n) for n in agents}
check('I0 the repo has skills and agents to link', bool(skills) and bool(agents), repo)

with tempfile.TemporaryDirectory() as h:
    code, out = run(h)
    check('I1 a fresh HOME runs clean', code == 0, out[-400:])
    check('I1b every skill holding a SKILL.md is linked into the repo',
          links(h, 'skills') == want_skills, links(h, 'skills'))
    check('I1c every agent is linked into the repo', links(h, 'agents') == want_agents, links(h, 'agents'))
    check('I1d the count names every link', done(out) == (len(skills), len(agents), str(repo)), done(out))

    settings = Path(h) / '.claude' / 'settings.json'
    before = settings.read_bytes()
    code, out = run(h)
    check('I2 a second run links and relinks nothing',
          code == 0 and not re.search(r'^(re)?linked ', out, re.M), out[-400:])
    check('I2b and leaves settings.json byte-identical', settings.read_bytes() == before)

with tempfile.TemporaryDirectory() as h:
    folder = Path(h) / '.claude' / 'skills' / skills[0]
    folder.mkdir(parents=True)
    (folder / 'mine.txt').write_text('mine\n')
    file = Path(h) / '.claude' / 'agents' / agents[0]
    file.parent.mkdir(parents=True)
    file.write_text('my agent\n')
    code, out = run(h)
    check('I3 a real folder in a skill link\'s place is named on a skipped line',
          named(out, 'skipped', folder), out[-400:])
    check('I3b and stays a real folder holding only its own file',
          not folder.is_symlink() and folder.is_dir() and os.listdir(folder) == ['mine.txt']
          and (folder / 'mine.txt').read_text() == 'mine\n',
          folder.is_symlink() or os.listdir(folder))
    check('I3c the rest are still linked, and the run exits 0',
          code == 0 and links(h, 'skills') == {n: t for n, t in want_skills.items() if n != skills[0]},
          f'exit {code}')
    check('I4 a real file in an agent link\'s place stays as it was',
          not file.is_symlink() and file.read_text() == 'my agent\n')
    check('I4b and is named on a skipped line', named(out, 'skipped', file), out[-400:])
    check('I4c the count leaves out the two it skipped',
          done(out) == (len(skills) - 1, len(agents) - 1, str(repo)), done(out))

with tempfile.TemporaryDirectory() as h:
    old = Path(h) / 'elsewhere'
    old.mkdir()
    dst = Path(h) / '.claude' / 'skills' / skills[0]
    dst.parent.mkdir(parents=True)
    dst.symlink_to(old)
    code, out = run(h)
    check('I5 a link that points elsewhere is relinked into the repo',
          code == 0 and os.readlink(dst) == want_skills[skills[0]] and named(out, 'relinked', dst),
          out[-400:])
    check('I5b and nothing is written into its old target', list(old.iterdir()) == [], list(old.iterdir()))

with tempfile.TemporaryDirectory() as h:
    # I6: a link into <repo>-other, a sibling whose path starts with the repo's; it need not exist...
    for kind, name in (('skills', 'zz'), ('agents', 'zz.md')):
        d = Path(h) / '.claude' / kind
        d.mkdir(parents=True, exist_ok=True)
        (d / name).symlink_to(f'{repo}-other/{kind}/{name}')
    code, out = run(h)
    check('I6 the count names only links into the repo, not one into a folder beside it',
          code == 0 and done(out) == (len(skills), len(agents), str(repo)), done(out))
with tempfile.TemporaryDirectory() as t:
    # I7: a repo whose skills folder holds a folder with no SKILL.md beside a real skill...
    fake = Path(t).resolve() / 'repo'
    for name, text in (('skills/real/SKILL.md', '---\nname: real\n---\n'),
                       ('skills/notes/README.md', 'notes\n'), ('agents/a.md', 'an agent\n')):
        (fake / name).parent.mkdir(parents=True, exist_ok=True)
        (fake / name).write_text(text)
    shutil.copy2(repo / 'install.sh', fake / 'install.sh')
    shutil.copytree(repo / 'hooks', fake / 'hooks')
    home = Path(t) / 'home'
    code, out = run(home, fake)
    check('I7 a skill folder with no SKILL.md is not linked, and the count leaves it out',
          code == 0 and links(home, 'skills') == {'real': str(fake / 'skills' / 'real')}
          and done(out) == (1, 1, str(fake)), f'{links(home, "skills")} {done(out)}')
sys.exit(1 if fails else 0)
