#!/usr/bin/env python3
"""
test_git_guard — feeds hooks/block-dangerous-git.py the PreToolUse JSON Claude Code sends for a
Bash call, and checks its exit code and message.

Run it with `python3 hooks/tests/test_git_guard.py`, or name another script first. The exit code
is 1 if any check fails.

G1 refuses every form of the blocked list, with exit 2 and the hook's message on stderr: behind a
wrapper or shell syntax, in any spelling git accepts, and as a mention such as `echo git push`,
which upstream's grep also refuses. G2 lets through the git commands kstack's skills run, a
one-file restore among them, with exit 0 and no output. G3 lets through a call that is not Bash, or has no command. G4 holds that hooks.json
registers the guard as a PreToolUse hook on Bash.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent.parent
guard = sys.argv[1] if len(sys.argv) > 1 else str(repo / 'hooks' / 'block-dangerous-git.py')
fails = []
def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + (f'  [{got}]' if got and not ok else ''))
    ok or fails.append(name)
def run(payload):
    return subprocess.run([sys.executable, guard], input=json.dumps(payload),
                          capture_output=True, text=True)
def bash(command):
    return run({'tool_name': 'Bash', 'tool_input': {'command': command}})


BLOCKED = [
    'git push',
    'git push origin main',
    'git push --force origin main',
    'git push -f',
    'git -C /tmp/repo push origin HEAD',
    'git reset --hard',
    'git reset --hard HEAD~1',
    'git -C /tmp/repo reset --hard origin/main',
    'git clean -f',
    'git clean -fd',
    'git clean -fdx',
    'git clean -df',
    'git branch -D feature',
    'git -C /tmp/repo/.git branch -D claude/x',
    'git checkout .',
    'git checkout -- .',
    'git restore .',
    'git restore --staged --worktree .',
    'git status && git checkout -- .',
    'cd /tmp/repo; git reset --hard',
    'echo ok\ngit push origin main',
    'true | git push',
    'bash -c "git push origin main"',
    'echo $(git reset --hard)',
    'git stash',
    'git stash push -u -m x',
    'git stash pop',
    'git stash apply',
    'git -C /x stash list',
    'echo git push',
    'echo git stash',
    'env -i git push',
    '{ git push; }',
    'if true; then git push; fi',
    'for i in 1; do git push; done',
    '! git push',
    'nice -n 5 git push',
    'timeout 60 git push',
    'sudo -u me git push',
    'xargs -I{} git push',
    '>/dev/null git push',
    'timeout 60 git reset --hard',
    'env -i git branch -D x',
    'git reset --har',
    'git reset --h',
    'git reset --hard=x',
    'git branch -d -f x',
    'git branch -df x',
    'git branch -fd x',
    'git branch --delete --force x',
    'git branch --del --forc x',
    'git branch -d --force x',
    'git clean --forc',
    'git clean --force -d',
    'git clean -xf',
]
for c in BLOCKED:
    r = bash(c)
    check(f'G1 refuses {c!r}', r.returncode == 2 and 'BLOCKED' in r.stderr
          and 'The user has prevented you from doing this.' in r.stderr,
          f'exit {r.returncode}, stderr {r.stderr.strip()!r}')

ALLOWED = [
    'git status',
    'git status --porcelain --untracked-files=no',
    'git diff',
    'git diff --name-only main...HEAD',
    'git checkout -- skills/build/SKILL.md',
    'git checkout -- ./hooks/install.py',
    'git checkout HEAD -- src/a.py',
    'git restore src/a.py',
    'git worktree add --detach /tmp/wt abc1234',
    'git worktree add -b claude/x /tmp/wt main',
    'git worktree remove /tmp/wt',
    'git worktree list --porcelain',
    'git commit -m "first"',
    'git commit -F /tmp/msg.txt',
    'git merge --ff-only -q abc1234',
    'git merge-base --is-ancestor main HEAD',
    'git merge-tree --write-tree main HEAD',
    'git log --oneline -5',
    'git rev-parse --show-toplevel',
    'git branch --format=%(refname:short) --merged main',
    'git branch -d merged-branch',
    'git clean -n',
    'git reset --soft HEAD~1',
    'git reset src/a.py',
    'git add -A && git commit -m "x"',
    'git -C /tmp/repo log -1',
    'git checkout -b claude/new',
    'echo "do not push"',
    'git log --oneline stash',
    'git checkout -- one.txt',
    'git worktree add x',
    'git commit -m wip',
    'git branch -d -v merged-branch',
    'git branch --delete merged-branch',
    'git clean -nd',
    'ls .',
]
for c in ALLOWED:
    r = bash(c)
    check(f'G2 allows {c!r}', r.returncode == 0 and not r.stdout and not r.stderr,
          f'exit {r.returncode}, stderr {r.stderr.strip()!r}')

r = run({'tool_name': 'Read', 'tool_input': {'file_path': '/tmp/git push'}})
check('G3 lets a call that is not Bash through', r.returncode == 0, f'exit {r.returncode}')
r = run({'tool_name': 'Bash', 'tool_input': {}})
check('G3b lets a Bash call with no command through', r.returncode == 0, f'exit {r.returncode}')

hooks = json.loads((repo / 'hooks' / 'hooks.json').read_text())['hooks']
found = [e for e in hooks.get('PreToolUse', []) if e.get('matcher') == 'Bash'
         and any('${CLAUDE_PLUGIN_ROOT}/hooks/block-dangerous-git.py' in h['command'] for h in e['hooks'])]
check('G4 hooks.json registers the guard as a PreToolUse hook on Bash', len(found) == 1, found)
sys.exit(1 if fails else 0)
