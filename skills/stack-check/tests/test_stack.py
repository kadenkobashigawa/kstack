#!/usr/bin/env python3
"""
test_stack — builds a throwaway repo, a worktree of it, a link to it and two Claude Code session
folders, and checks which session lines `stack.py digest` keeps.

Run it with `python3 test_stack.py`. It needs git. It makes one temporary folder and runs git and
stack.py with HOME inside it and no global or system git config, then removes it. The exit code
is the number of failed checks.

D1 keeps every line of this workspace's own sessions. D2 keeps a line from another folder's
session when its working folder lies in the repo, in a worktree of it, or behind a link to it.
D3 drops the rest of that session, including a sibling folder whose name begins with the repo's,
and gives no header to a session with nothing kept. D4 keeps a line with no working folder out.
D5 to D9 hold the rows a digest keeps: inside the window, once per entry, and never a side chain,
a compact summary, a meta entry, a tool result or a system-written turn. C1 to C4 hold each kind
of `check` finding, F1 the frozen copy and its FROZEN.txt, and U1 the usage.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


HERE    = Path(__file__).resolve().parent
SCRIPT  = HERE.parent / 'scripts' / 'stack.py'
RESULTS = []


def check(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


def raw(path: Path, *entries: dict) -> None:
    """a session log of these entries, as Claude Code writes them, one per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')


def turn(uid: str, text, days_ago: float = 0, **extra) -> dict:
    """a typed user turn stamped `days_ago` days back."""
    at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_ago)
    return dict({'type': 'user', 'uuid': uid, 'timestamp': at.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                 'message': {'role': 'user', 'content': text}}, **extra)


def log(path: Path, *lines: tuple[str, str]) -> None:
    """a session log of typed turns, each (working folder, text), stamped now."""
    path.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    with path.open('w') as f:
        for n, (cwd, text) in enumerate(lines):
            f.write(json.dumps({'type': 'user', 'uuid': f'{path.stem}-{n}', 'timestamp': now,
                                'cwd': cwd, 'message': {'role': 'user', 'content': text}}) + '\n')


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t).resolve()
        env = {**{k: v for k, v in os.environ.items() if not k.startswith('GIT_')},
               'HOME': str(tmp), 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': str(tmp / 'gc')}
        repo, wt, link, away = tmp / 'repo', tmp / 'wt', tmp / 'link', tmp / 'away'
        repo.mkdir()
        away.mkdir()

        def git(*a: str) -> None:
            subprocess.run(['git', *a], cwd=repo, env=env, check=True, capture_output=True)

        git('init', '-q', '-b', 'main')
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'c')
        git('worktree', 'add', '-q', str(wt))
        link.symlink_to(repo)
        projects = tmp / '.claude' / 'projects'
        log(projects / re.sub(r'[^A-Za-z0-9]', '-', str(repo)) / 'own.jsonl',
            (str(repo), 'own turn in the repo'), (str(away), 'own turn elsewhere'))
        log(projects / '-elsewhere' / 'mixed.jsonl', (str(repo / 'sub'), 'in the repo'),
            (str(wt), 'in its worktree'), (str(link), 'behind its link'),
            (str(away), 'a private chat elsewhere'), (str(tmp / 'repo2'), 'a sibling folder'))
        log(projects / '-elsewhere' / 'private.jsonl', (str(away), 'nothing to do with the repo'),
            ('', 'a line with no working folder'))
        out = subprocess.run([sys.executable, str(SCRIPT), 'digest', '--project', str(repo)],
                             cwd=repo, env=env, capture_output=True, text=True).stdout
        check('D1 this workspace keeps every line of its own sessions',
              'own turn in the repo' in out and 'own turn elsewhere' in out, out)
        check('D2 another folder keeps lines worked in the repo, its worktree or behind its link',
              all(s in out for s in ('in the repo', 'in its worktree', 'behind its link')), out)
        check('D3 the rest of another folder stays out, and an empty session gets no header',
              'a private chat elsewhere' not in out and 'nothing to do with' not in out
              and 'a sibling folder' not in out
              and 'SESSION private' not in out, out)
        check('D4 a line with no working folder stays out', 'no working folder' not in out, out)

        own = projects / re.sub(r'[^A-Za-z0-9]', '-', str(repo))
        raw(own / 'kinds.jsonl', turn('k1', 'ten days back', days_ago=10), turn('k2', 'replayed line'),
            turn('k3', 'a side chain', isSidechain=True), turn('k4', 'a compact summary',
                                                               isCompactSummary=True),
            turn('k5', 'a meta entry', isMeta=True),
            turn('k6', [{'type': 'tool_result', 'tool_use_id': 't', 'content': 'a tool result'},
                        {'type': 'text', 'text': 'beside a tool result'}]),
            turn('k7', '<system-reminder>a reminder</system-reminder>'),
            turn('k8', '<local-command-stdout>a local command</local-command-stdout>'),
            turn('k9', '<task-notification>a task notice</task-notification>'))
        raw(own / 'replay.jsonl', turn('k2', 'replayed line'))
        out = subprocess.run([sys.executable, str(SCRIPT), 'digest', '--project', str(repo)],
                             cwd=repo, env=env, capture_output=True, text=True).stdout
        check('D5 a line older than the window stays out', 'ten days back' not in out, out)
        check('D6 an entry replayed into a second log is kept once', out.count('replayed line') == 1,
              out)
        check('D7 side chains, compact summaries and meta entries stay out',
              not any(s in out for s in ('a side chain', 'a compact summary', 'a meta entry')), out)
        check('D8 a turn carrying a tool result stays out', 'beside a tool result' not in out, out)
        check('D9 system-written turns stay out',
              not any(s in out for s in ('a reminder', 'a local command', 'a task notice')), out)

        skills = tmp / '.claude' / 'skills'
        for name, front in (('good', 'name: good\ndescription: fine'), ('noname', 'description: x'),
                            ('nodesc', 'name: nodesc'),
                            ('refs', 'name: refs\ndescription: x')):
            (skills / name).mkdir(parents=True)
            (skills / name / 'SKILL.md').write_text(f'---\n{front}\n---\n\nbody\n')
        (skills / 'refs' / 'SKILL.md').write_text(
            '---\nname: refs\ndescription: x\n---\n\nsee `references/gone.md` and [the guide](nowhere.md)\n'
            '`[not a link](inside-code.md)`\n'
            '[a site](https://example.com/gone.md) and [a mail](mailto:t@example.com)\n')
        (skills / 'dead').symlink_to(tmp / 'no-such-skill')
        (repo / 'CLAUDE.md').write_text('# repo\n')
        git('add', 'CLAUDE.md')
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'claude')
        out = subprocess.run([sys.executable, str(SCRIPT), 'check'], cwd=repo, env=env,
                             capture_output=True, text=True).stdout
        check('C1 a SKILL.md frontmatter with no name, and one with no description, are findings',
              'noname/SKILL.md: frontmatter has no name' in out
              and 'nodesc/SKILL.md: frontmatter has no description' in out
              and 'good/SKILL.md' not in out, out)
        check('C2 a references/ path no skill holds is a finding',
              'names references/gone.md, which no skill holds' in out, out)
        check('C3 a markdown link that resolves to nothing is a finding, and one in code, on the web '
              'or to a mail address is not',
              'a link to nowhere.md, which resolves to nothing' in out
              and not any(s in out for s in ('inside-code', 'example.com')), out)
        check('C4 a skill link to nothing is a finding',
              f'{skills / "dead"}: a skill link to {tmp / "no-such-skill"}, which does not exist' in out,
              out)

        frozen = tmp / 'frozen'
        done = subprocess.run([sys.executable, str(SCRIPT), 'freeze', str(frozen)], cwd=repo, env=env,
                              capture_output=True, text=True).stdout
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo, env=env, capture_output=True,
                              text=True).stdout.strip()
        stamp = (frozen / 'FROZEN.txt').read_text() if (frozen / 'FROZEN.txt').exists() else ''
        check('F1 freeze copies each part under its absolute path, and FROZEN.txt names each repo\'s '
              'HEAD', (frozen / str(skills / 'good' / 'SKILL.md').lstrip('/')).exists()
              and (frozen / str(repo / 'CLAUDE.md').lstrip('/')).read_text() == '# repo\n'
              and f'{repo} {head}' in stamp.splitlines(), f'{done} {stamp}')

        got = [subprocess.run([sys.executable, str(SCRIPT), *argv], cwd=repo, env=env,
                              capture_output=True, text=True) for argv in (['scan'], [], ['freeze'])]
        check('U1 an unknown command, none, or freeze with no folder exits 2 with the usage',
              all(r.returncode == 2 for r in got) and all('Commands' in r.stdout for r in got[:2])
              and 'usage: stack.py freeze' in got[2].stdout, str([(r.returncode, r.stdout[:30]) for r in got]))
        plug, off = tmp / 'plug', tmp / 'off'
        for root in (plug, off):
            (root / 'skills' / 'pk').mkdir(parents=True)
            (root / 'skills' / 'pk' / 'SKILL.md').write_text('---\nname: pk\ndescription: x\n---\n')
            (root / 'agents').mkdir()
            (root / 'agents' / 'pa.md').write_text('---\nname: pa\n---\n')
            (root / 'hooks').mkdir()
            (root / 'hooks' / 'hooks.json').write_text('{"hooks": {}}')
        (tmp / '.claude' / 'plugins').mkdir(parents=True, exist_ok=True)
        (tmp / '.claude' / 'plugins' / 'installed_plugins.json').write_text(json.dumps({'version': 2, 'plugins': {
            'p@m': [{'scope': 'user', 'installPath': str(plug)}],
            'off@m': [{'scope': 'user', 'installPath': str(off)}]}}))
        (tmp / '.claude' / 'settings.json').write_text(json.dumps({'enabledPlugins': {'p@m': True, 'off@m': False}}))
        frozen2 = tmp / 'frozen2'
        subprocess.run([sys.executable, str(SCRIPT), 'freeze', str(frozen2)], cwd=repo, env=env,
                       capture_output=True, text=True)
        copied = lambda p: (frozen2 / str(p).lstrip('/')).exists()
        check('P1 freeze takes an enabled plugin\'s skills, agents and hooks.json, and none of a disabled one\'s',
              copied(plug / 'skills' / 'pk' / 'SKILL.md') and copied(plug / 'agents' / 'pa.md')
              and copied(plug / 'hooks' / 'hooks.json') and not copied(off / 'skills' / 'pk' / 'SKILL.md'),
              str(sorted(p.name for p in frozen2.rglob('*') if p.is_file())))
    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
