#!/usr/bin/env python3
'''
block-dangerous-git — a PreToolUse hook on Bash that refuses the git commands that destroy work:
git push, git reset --hard, git clean -f and -fd, git branch -D, and git checkout . and
git restore . (mattpocock-skills, `skills/misc/git-guardrails-claude-code/scripts/block-dangerous-git.sh`,
ll. 6–16). A refused call exits 2 with upstream's message on stderr, which Claude Code shows the
model in place of running the command (l. 20). It also refuses git stash *(kstack: the stash stack
is shared across worktrees, and a private project build writer used `git stash` in a worktree,
2026-11-01)*; Matt's list has no stash. Every other call exits 0 with no output.

Ported from upstream's bash script to Python *(kstack: kstack needs only git and python3, and
upstream reads the command with jq, so a Mac without jq would read an empty command and refuse
nothing)*. Two tests run, and either refuses. The first is upstream's: its patterns grepped over
the whole command line (ll. 18–19), so a mention such as `echo git push` is refused too. The
second reads the command as shell words, cut at ;, &&, ||, | and newlines, and judges every word
that is `git` or ends in `/git`, anywhere in a segment and so behind any wrapper or shell keyword,
by the subcommand and arguments that follow it *(kstack: a grep misses `git checkout -- .`, which
a build verify agent ran in the main checkout on 2026-11-01, `git -C <dir> branch -D`, which
gate.py land prints, and the spellings git accepts for the same commands: a long option's
unambiguous prefix such as `--har`, `--hard=x`, and `-df` or `--delete --force` for -D)*. A
command too broken to read as shell words gets the grep alone, with the -- and stash forms added.
Each argument of `sh -c`, `bash -c`, `zsh -c` or `eval`, behind a wrapper too, and each word
holding `$(` or a backquote, is read again as a command of its own.

The hook sees only the command a Bash call types. A git call made inside a script the command runs
is the script's own, as in gate.py, which merges with --ff-only and never pushes.
It reads only the command line Claude Code passes it, so it cannot see through shell indirection
such as a variable or alias standing for git, `git ${x}push`, or a backslash line continuation, and
upstream's grep has the same limit.

Usage
-----
    Claude Code pipes the PreToolUse JSON, {tool_name, tool_input: {command}}, to stdin.
'''

from __future__ import annotations

import json
import os
import re
import shlex
import sys

#upstream's patterns (block-dangerous-git.sh, ll. 6-16), grepped over every command line...
UPSTREAM = ['git push', 'git reset --hard', 'git clean -fd', 'git clean -f', 'git branch -D',
            r'git checkout \.', r'git restore \.', 'push --force', 'reset --hard']
#...and with the -- and stash forms, for a command shlex can't split
PATTERNS = UPSTREAM + [r'git checkout -- \.', r'git stash']

#git's global options that take the next word as their value...
VALUED  = {'-C', '-c', '--git-dir', '--work-tree', '--namespace', '--super-prefix',
           '--config-env', '--exec-path'}
SHELLS  = {'sh', 'bash', 'zsh', 'eval'}
CUTS    = {';', '&', '&&', '|', '||', '|&', '\n', '(', ')', ';;'}
WHOLE   = {'.', './'}
STASH_WHY = ('The stash stack is shared by every worktree of the repository, so a stash or pop here can '
             'take another session\'s changes. Set work aside with a temporary commit instead, '
             '`git add -A && git commit -m wip`, and undo it later with `git reset --soft HEAD~1`.')


def words(command: str) -> list[str]:
    '''the command as shell words, with ;, &, |, (, ), < and > and newlines as words of their own.'''
    lex = shlex.shlex(command, posix=True, punctuation_chars=';&|()<>\n')
    lex.whitespace = ' \t\r'
    lex.whitespace_split = True
    return list(lex)


def segments(ws: list[str]) -> list[list[str]]:
    '''the words cut into simple commands at each operator in CUTS.'''
    out, cur = [], []
    for w in ws:
        if w in CUTS:
            out.append(cur)
            cur = []
        else:
            cur.append(w)
    return [s for s in out + [cur] if s]


def spelled(arg: str, option: str, least: int) -> bool:
    '''whether `arg` names long `option`, as git reads it: a prefix of at least `least` letters,
    with or without =value.'''
    name = arg.split('=', 1)[0]
    return len(name) >= least and option.startswith(name)


def judge(sub: str, args: list[str]) -> str:
    '''the blocked pattern one git call matches, or '' when it is allowed.'''
    opts  = args[:args.index('--')] if '--' in args else args
    short = ''.join(a[1:] for a in opts if a.startswith('-') and not a.startswith('--'))
    longs = [a for a in opts if a.startswith('--')]
    paths = args[args.index('--') + 1:] if '--' in args else [a for a in args if not a.startswith('-')]
    if sub == 'stash':
        return 'git stash'
    if sub == 'push':
        return 'git push'
    if sub == 'reset' and any(spelled(a, '--hard', 3) for a in longs):
        return 'git reset --hard'
    if sub == 'clean' and ('f' in short or any(spelled(a, '--force', 3) for a in longs)):
        return 'git clean -f'
    if sub == 'branch':
        delete = 'd' in short or any(spelled(a, '--delete', 3) for a in longs)
        force  = 'f' in short or any(spelled(a, '--force', 3) for a in longs)
        if 'D' in short or (delete and force):
            return 'git branch -D'
    if sub in ('checkout', 'restore') and any(p in WHOLE for p in paths):
        return f'git {sub} .'
    return ''


def git_calls(seg: list[str]) -> str:
    '''the blocked pattern any git word in a simple command matches, with the words after it, or ''.'''
    for i, w in enumerate(seg):
        if w != 'git' and not w.endswith('/git'):
            continue
        rest = seg[i + 1:]
        while rest and rest[0].startswith('-'):
            opt = rest.pop(0)
            if opt in VALUED and rest:
                rest.pop(0)
        if rest and (hit := judge(rest[0], rest[1:])):
            return hit
    return ''


def blocked(command: str, depth: int = 0) -> str:
    '''the blocked pattern a command matches anywhere in it, or ''.'''
    try:
        ws = words(command)
    except ValueError:
        return next((p for p in PATTERNS if re.search(p, command)), '')
    if hit := next((p for p in UPSTREAM if re.search(p, command)), ''):
        return hit
    for seg in segments(ws):
        if hit := git_calls(seg):
            return hit
        if depth > 3:
            continue
        shell = next((i for i, w in enumerate(seg) if os.path.basename(w) in SHELLS), None)
        inner = seg[shell + 1:] if shell is not None else []
        inner += [w for w in seg if '$(' in w or '`' in w]
        for w in inner:
            if hit := blocked(w.replace('`', '\n'), depth + 1):
                return hit
    return ''


def main() -> int:
    '''read the hook's JSON from stdin, and exit 2 with upstream's message for a blocked command.'''
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get('tool_name', 'Bash') != 'Bash':
        return 0
    command = (data.get('tool_input') or {}).get('command') or ''
    if hit := blocked(command):
        print(f"BLOCKED: '{command}' matches dangerous pattern '{hit}'. The user has prevented you "
              'from doing this.' + (' ' + STASH_WHY if hit == 'git stash' else ''), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
