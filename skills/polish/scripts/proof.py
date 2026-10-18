#!/usr/bin/env python3
'''
prove a polish pass changed no behaviour, by comparing the parse tree before against after.

comments and docstrings are the two things polish is allowed to rewrite, so both are stripped
before the compare — everything else surviving means the edit was cosmetic by construction. only
python files have a parser here: any other path is named NO PARSER, left out of the count, and left
to the cheaper checks. the baselines live in the working tree's own git directory, so two repos or
two worktrees never share them, and a snapshot never replaces a baseline that differs from the
file: verify or clear first.

Methods
-------
snapshot   copy the files aside before the pass edits them, keeping any baseline already there
verify     re-parse each one and diff its tree against the snapshot
clear      drop every baseline, once a verify has passed
main       dispatch on argv
'''

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path


# ── where the baselines live ────────────────────────────────────────────────

def _cache() -> Path | None:
    '''the baseline folder in this working tree's git directory, or None outside a repo'''

    found = subprocess.run(['git', 'rev-parse', '--absolute-git-dir'], capture_output=True,
                           text=True)

    return Path(found.stdout.strip()) / 'polish-before' if found.returncode == 0 else None


def _baseline(cache: Path, p: str) -> Path:
    return cache / Path(p).resolve().relative_to('/')


def _parsed(p: str) -> bool:
    return Path(p).suffix == '.py'


# ── the three commands ──────────────────────────────────────────────────────

def snapshot(cache: Path, paths: list[str]) -> int:
    '''copy each python file into the cache, mirroring its path, unless a different one is kept'''

    missing = [p for p in paths if not Path(p).is_file()]

    if missing:
        print(f'proof.py: no such file: {", ".join(missing)}', file=sys.stderr)
        return 2

    parsed = [p for p in paths if _parsed(p)]
    stale  = [p for p in parsed if _baseline(cache, p).exists()
              and _baseline(cache, p).read_bytes() != Path(p).read_bytes()]

    if stale:
        print(f'proof.py: a different baseline is kept for {", ".join(stale)}; verify or clear '
              'first', file=sys.stderr)
        return 2

    for p in paths:
        if not _parsed(p):
            print(f'  NO PARSER  {p}')
            continue

        dst = _baseline(cache, p)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)

    print(f'snapshot: {len(parsed)} file(s)')
    return 0


def verify(cache: Path, paths: list[str]) -> int:
    '''compare every file against its snapshot and print one line per verdict'''

    failed = []
    parsed = [p for p in paths if _parsed(p)]

    for p in paths:
        if not _parsed(p):
            print(f'  NO PARSER  {p}')
            continue

        before = _baseline(cache, p)

        if not before.exists():
            print(f'  NO SNAPSHOT  {p}')
            failed.append(p)
            continue

        if not Path(p).is_file():
            print(f'  MISSING  {p}')
            failed.append(p)
            continue

        try:
            a, b = _tree(before.read_text()), _tree(Path(p).read_text())
        except SyntaxError as e:
            print(f'  UNPARSEABLE  {p} — {e}')
            failed.append(p)
            continue

        if a != b:
            print(f'  BEHAVIOUR CHANGED  {p}')
            failed.append(p)

    print(f'{len(parsed) - len(failed)}/{len(parsed)} proved unchanged')
    return 1 if failed else 0


def clear(cache: Path) -> int:
    '''drop every baseline this working tree keeps'''

    shutil.rmtree(cache, ignore_errors=True)
    print('cleared')
    return 0


# ── stripping what polish is allowed to touch ───────────────────────────────

def _tree(src: str) -> str:
    '''parse, drop every docstring, and dump — comments never reach the tree at all'''

    mod = ast.parse(src)

    for node in ast.walk(mod):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        body = node.body

        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]

    return ast.dump(mod)


def main() -> int:
    cmd, paths = (sys.argv[1] if len(sys.argv) > 1 else ''), sys.argv[2:]

    if not (cmd in ('snapshot', 'verify') and paths or cmd == 'clear' and not paths):
        print('usage: proof.py {snapshot|verify} FILE...  |  proof.py clear', file=sys.stderr)
        return 2

    cache = _cache()

    if cache is None:
        print('proof.py: not inside a git repo, whose git directory holds the baselines',
              file=sys.stderr)
        return 2

    if cmd == 'clear':
        return clear(cache)

    return (snapshot if cmd == 'snapshot' else verify)(cache, paths)


if __name__ == '__main__':
    raise SystemExit(main())
