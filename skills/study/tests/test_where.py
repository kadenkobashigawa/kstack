#!/usr/bin/env python3
'''
test_where.py builds throwaway git repositories and notes folders and checks the W that
`where.py` finds for each kind of scope.

Run it with `python3 test_where.py`. It needs git and nothing outside the standard library. It
makes one temporary folder and resolves it, so the /var to /private/var link on macOS cannot
break a comparison. It runs git with no global or system config. It never reads or writes the
real home folder: a case about home passes a fake home to `where.locate`. The exit code is the
number of failed checks.

W1 to W5 hold one folder scope typed five ways (from the top, as `..`, as an absolute path from
`/`, as `.` from inside it, and through a symlink), and W6 the same scope with a trailing slash.
W7 holds the repository's top, W8 a file typed as `../../notes.md`, W9 two file:Symbol scopes,
W10 `../x` into another repository and back, and W11 a linked worktree, where `.git` is a file.
W12 holds a run twice and a clean `git status`, W13 to W15 notes outside git (a folder from three
working folders, a file, and `..`), W16 and W17 `--files` outside git and in git. W18 holds a
home folder, outside git and as a repository's top, W19 the filesystem root, W20 a missing scope,
W21 a broken `.git`, W22 and W23 git missing from PATH, in a repository and outside git. W24
holds a `.study` folder already tracked, W25 a `.study/.gitignore` with other content, W26 a
`!.study/` line in the repository's `.gitignore`, W27 a scope inside a `.study` folder, W28 a
scope typed in another case than the disk spells it, W29 the names W can never take, W30 a
`.study` that is a symlink, W31 the folder names that `w_name` makes, W32 where.py run alone
from a copy with `python3 -I`, and W33 the refusal line on stderr. W34 holds `--files` in git
beside a nested repository, an embedded one, a deleted file, a symlink, a fifo and a deeper tracked
`.study`, W35 a file scope git ignores, and W36 where.py run from Cowork's copy under
`<folder>/.study/.skill/scripts`, which must keep that copy out of git too. W37 holds `--files`
outside git around a nested repository, a worktree-style `.git` file, `.gitignore`,
`.gitattributes`, `.github` and another dot-folder, which stay notes.

W28 needs a case-insensitive filesystem under the temporary folder, as macOS gives by default.
It prints a SKIP line on a case-sensitive one.
'''

from __future__ import annotations

import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE    = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / 'scripts'
SCRIPT  = SCRIPTS / 'where.py'
RESULTS = []
USER    = ('-c', 'user.name=t', '-c', 'user.email=t@t')

sys.path.insert(0, str(SCRIPTS))
import where  # noqa: E402


def check(name: str, ok: bool, detail: str = '') -> None:
    '''one PASS or FAIL line, with the detail on a FAIL.'''
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + ('' if ok else f'\n      {detail}'))


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(['git', *USER, *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


def init(repo: Path, files: dict[str, str]) -> Path:
    '''a repository at repo holding files, all committed.'''
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    git('init', '-q', '-b', 'main', cwd=repo)
    git('add', '-A', cwd=repo)
    git('commit', '-qm', 'init', cwd=repo)
    return repo


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    '''where.py run as Cowork runs it, with python3 -I.'''
    return subprocess.run([sys.executable, '-I', str(SCRIPT), *args], cwd=cwd, env=env,
                          capture_output=True, text=True)


def out(r: subprocess.CompletedProcess) -> dict:
    '''the JSON line of a run that exited 0, or {} with the reason under 'error'.'''
    try:
        if r.returncode != 0:
            return {'error': f'rc={r.returncode} {r.stderr.strip()[-300:]}'}
        lines = r.stdout.splitlines()
        if len(lines) != 1:
            return {'error': f'stdout is {len(lines)} lines'}
        return json.loads(lines[0])
    except ValueError as e:
        return {'error': f'not JSON: {e}'}


def refused(r: subprocess.CompletedProcess, *words: str) -> bool:
    '''exit 2, nothing on stdout, and one `where:` line on stderr holding every word.'''
    return (r.returncode == 2 and r.stdout == '' and r.stderr.startswith('where: ')
            and r.stderr.count('\n') == 1 and all(w in r.stderr for w in words))


def why(r: subprocess.CompletedProcess) -> str:
    return f'rc={r.returncode} stdout={r.stdout!r} stderr={r.stderr.strip()[-300:]!r}'


def attempt(fn):
    '''fn's result, or the exception it raised, so one broken case cannot stop the run.'''
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return e


def main() -> int:
    os.environ.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', LC_ALL='C')
    for k in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
        os.environ.pop(k, None)
    tmp = Path(tempfile.mkdtemp(prefix='test_where_')).resolve()
    try:
        return cases(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cases(tmp: Path) -> int:
    R = init(tmp / 'R', {'sub/deep/a.py': 'class Cls:\n    def meth(self):\n        pass\n'
                                          'def f():\n    pass\n',
                         'notes.md': '# notes\n', 'tree.json': '{}\n', '.skill/s.md': 's\n'})
    X = init(tmp / 'X', {'x/b.py': 'pass\n'})
    N = tmp / 'N'
    (N / 't' / 'u').mkdir(parents=True)
    (N / 't' / 'x.md').write_text('# x\n')
    (tmp / 'L').symlink_to(R / 'sub')
    git('worktree', 'add', '-q', str(tmp / 'WT'), cwd=R)
    WT = tmp / 'WT'
    home = tmp / 'home'
    home.mkdir()
    sub_w = R / '.study' / 'sub'

    # ── one scope, one W ──────────────────────────────────────────────────────
    r = run('sub', cwd=R)
    o = out(r)
    check('W1 a folder typed from the top gives <top>/.study/<scope> and the whole record',
          o == {'w': str(sub_w), 'top': str(R), 'scope': 'sub', 'symbol': '', 'is_file': False,
                'git': True, 'url': (sub_w / 'map.html').as_uri()}
          and sub_w.is_dir(), str(o))
    ways = {'W2 `..` from a subfolder': run('..', cwd=R / 'sub' / 'deep'),
            'W3 an absolute path from /': run(str(R / 'sub'), cwd=Path('/')),
            'W4 `.` from inside it': run('.', cwd=R / 'sub'),
            'W5 a symlink to it, from /': run(str(tmp / 'L'), cwd=Path('/')),
            'W6 a trailing slash': run('sub/', cwd=R)}
    for name, r in ways.items():
        check(f'{name} gives the same W as W1', out(r).get('w') == str(sub_w), str(out(r)))
    o = out(run('.', cwd=R))
    check('W7 the top `.` gives <top>/.study/%2E, a name that cannot start with a dot',
          o.get('w') == str(R / '.study' / '%2E') and o.get('scope') == '.', str(o))
    o = out(run('../../notes.md', cwd=R / 'sub' / 'deep'))
    check('W8 a file typed as ../../notes.md gives <top>/.study/notes.md with is_file true',
          (o.get('w'), o.get('is_file'), o.get('scope')) == (str(R / '.study' / 'notes.md'),
                                                              True, 'notes.md'), str(o))
    o1, o2 = out(run('sub/deep/a.py:f', cwd=R)), out(run('sub/deep/a.py:Cls.meth', cwd=R))
    check('W9 a file:Symbol scope encodes / as %2F and joins the symbol after @',
          (o1.get('w'), o1.get('symbol'), o2.get('w'), o2.get('symbol'))
          == (str(R / '.study' / 'sub%2Fdeep%2Fa.py@f'), 'f',
              str(R / '.study' / 'sub%2Fdeep%2Fa.py@Cls.meth'), 'Cls.meth'), f'{o1} {o2}')
    o1, o2 = out(run('../X/x', cwd=R)), out(run('../R/sub', cwd=X))
    check('W10 ../x into another repository lands in that repository, and back',
          (o1.get('w'), o2.get('w')) == (str(X / '.study' / 'x'), str(sub_w))
          and not (R / '.study' / 'x').exists() and not (X / '.study' / 'sub').exists()
          and not (R / 'X').exists(), f'{o1} {o2}')
    r = run('sub', cwd=WT)
    o = out(r)
    st = attempt(lambda: git('status', '--porcelain', '--ignored=no', cwd=WT))
    check('W11 in a linked worktree, whose .git is a file, W is in the worktree and git status '
          'stays empty',
          (WT / '.git').is_file() and o.get('w') == str(WT / '.study' / 'sub')
          and o.get('top') == str(WT) and st == '', f'{o} status={st!r}')

    # ── idempotent and excluded ──────────────────────────────────────────────
    before = attempt(lambda: (R / '.study' / '.gitignore').read_bytes())
    r1, r2 = run('sub', cwd=R), run('sub', cwd=R)
    after = attempt(lambda: (R / '.study' / '.gitignore').read_bytes())
    st = attempt(lambda: git('status', '--porcelain', cwd=R))
    ign = attempt(lambda: subprocess.run(['git', 'check-ignore', '-q', '--',
                                          '.study/sub/map.html'], cwd=R).returncode)
    check('W12 a second run prints the same line, .study/.gitignore holds `*` and stays the same, '
          'git status is empty, and W is ignored',
          r1.returncode == 0 and r1.stdout == r2.stdout and before == after == b'*\n'
          and st == '' and ign == 0, f'{why(r2)} gitignore={after!r} status={st!r} ign={ign}')

    # ── notes outside git ────────────────────────────────────────────────────
    nw = N / 't' / '.study' / '%2E'
    rs = [run(str(N / 't'), cwd=tmp), run('.', cwd=N / 't'), run(str(N / 't'), cwd=home)]
    os_ = [out(r) for r in rs]
    check('W13 a notes folder outside git gives <folder>/.study/%2E from any working folder, '
          'with git false',
          all(o.get('w') == str(nw) and o.get('git') is False and o.get('top') == str(N / 't')
              for o in os_) and not (tmp / '.study').exists()
          and not (home / '.study').exists(), str(os_))
    o = out(run(str(N / 't' / 'x.md'), cwd=tmp))
    check("W14 a notes file outside git gives W in the file's own folder",
          (o.get('w'), o.get('is_file'), o.get('top'))
          == (str(N / 't' / '.study' / 'x.md'), True, str(N / 't')), str(o))
    o = out(run('..', cwd=N / 't' / 'u'))
    check('W15 `..` typed from below a notes folder gives the same W as W13',
          o.get('w') == str(nw), str(o))
    (N / 't' / '.study').mkdir(exist_ok=True)
    (N / 't' / '.study' / 'stale.md').write_text('# old output\n')
    (N / 't' / 'u' / 'v.md').write_text('# v\n')
    (N / 't' / 'u' / 'link.md').symlink_to(N / 't' / 'x.md')
    os.mkfifo(N / 't' / 'u' / 'pipe')
    o = out(run(str(N / 't'), '--files', cwd=tmp))
    check('W16 --files outside git lists the regular notes, no symlink or fifo, and nothing under '
          '.study',
          o.get('files') == [str(N / 't' / 'u' / 'v.md'), str(N / 't' / 'x.md')], str(o))
    (R / 'untracked.md').write_text('# u\n')
    o = out(run('.', '--files', cwd=R))
    files = o.get('files') or []
    check('W17 --files in git lists tracked and untracked files and nothing under .study',
          str(R / 'sub' / 'deep' / 'a.py') in files and str(R / 'untracked.md') in files
          and not any('/.study/' in f for f in files) and files == sorted(files), str(o))

    # ── refusals ─────────────────────────────────────────────────────────────
    hn = tmp / 'homenotes'
    (hn / 'n').mkdir(parents=True)
    (hn / 'n' / 'a.md').write_text('# a\n')
    e1 = attempt(lambda: where.locate(str(hn), home=hn))
    hr = init(tmp / 'homerepo', {'a.md': '# a\n'})
    e2 = attempt(lambda: where.locate(str(hr / 'a.md'), home=hr))
    e3 = attempt(lambda: where.locate(str(hn / 'n'), home=hn))
    check('W18 a top that is the home folder is refused, outside git and in git, and a folder '
          'below home is not',
          isinstance(e1, where.ScopeError) and 'home' in str(e1)
          and isinstance(e2, where.ScopeError) and 'home' in str(e2)
          and isinstance(e3, where.Where) and e3.w == hn / 'n' / '.study' / '%2E'
          and not (hn / '.study').exists() and not (hr / '.study').exists(),
          f'{e1!r} {e2!r} {e3!r}')
    r = run('/', cwd=tmp)
    check('W19 the filesystem root is refused for being the root',
          refused(r, '/', 'filesystem root'), why(r))
    r1, r2 = run(str(R / 'nope'), cwd=tmp), run('sub/nope.py:f', cwd=R)
    check('W20 a missing scope, and a missing file:Symbol, exit 2 with no such file or folder',
          refused(r1, 'no such file or folder') and refused(r2, 'no such file or folder'),
          f'{why(r1)} {why(r2)}')
    for kind, text in (('gitdir', 'gitdir: /nonexistent\n'), ('garbage', 'garbage\n')):
        B = tmp / f'broken-{kind}'
        (B / 'n').mkdir(parents=True)
        (B / '.git').write_text(text)
        r = run(str(B / 'n'), cwd=tmp)
        check(f'W21 a broken .git ({kind}) is a refusal with git\'s reason, never outside git',
              refused(r, 'git') and not (B / '.study').exists()
              and not (B / 'n' / '.study').exists(), why(r))
    nogit = dict(os.environ, PATH='/nonexistent')
    r = run(str(R / 'sub'), cwd=tmp, env=nogit)
    check('W22 git missing from PATH, with the scope in a repository, is a refusal',
          refused(r, 'git'), why(r))
    r = run(str(N / 't'), cwd=tmp, env=nogit)
    check('W23 git missing from PATH, with notes outside git, still gives W (git never runs)',
          out(r).get('w') == str(nw), why(r))
    T = init(tmp / 'T', {'a.md': '# a\n', '.study/old/map.html': 'x\n'})
    r = run('a.md', cwd=T)
    check('W24 a .study folder that git already tracks is refused', refused(r, 'tracked'),
          why(r))
    G = init(tmp / 'G', {'a.md': '# a\n'})
    (G / '.study').mkdir()
    (G / '.study' / '.gitignore').write_text('mine\n')
    r = run('a.md', cwd=G)
    check('W25 a .study/.gitignore with other content is left alone, and a W it does not ignore '
          'is refused',
          refused(r, 'ignored') and (G / '.study' / '.gitignore').read_text() == 'mine\n', why(r))
    Gn = tmp / 'Gn'
    (Gn / '.study').mkdir(parents=True)
    (Gn / '.study' / '.gitignore').write_text('mine\n')
    (Gn / 'a.md').write_text('# a\n')
    o = out(run(str(Gn), cwd=tmp))
    check('W25 outside git, a .study/.gitignore with other content is left alone and W is given',
          o.get('w') == str(Gn / '.study' / '%2E')
          and (Gn / '.study' / '.gitignore').read_text() == 'mine\n', str(o))
    U = init(tmp / 'U', {'a.md': '# a\n', '.gitignore': '!.study/\n'})
    r = run('a.md', cwd=U)
    st = attempt(lambda: git('status', '--porcelain', cwd=U))
    check('W26 a `!.study/` line in the repository .gitignore still leaves W ignored, because '
          'the inner .gitignore is deeper',
          r.returncode == 0 and st == '', f'{why(r)} status={st!r}')
    r1 = run(str(R / '.study' / 'sub'), cwd=tmp)
    r2 = run(str(N / 't' / '.study'), cwd=tmp)
    check('W27 a scope inside a .study folder, in git and outside it, is refused',
          refused(r1, '.study') and refused(r2, '.study')
          and not (N / 't' / '.study' / '.study').exists(), f'{why(r1)} {why(r2)}')
    if (R / 'SUB').exists():
        r1, r2 = run('SUB/Deep', cwd=R), run(str(tmp / 'n' / 'T'), cwd=tmp)
        check('W28 a scope typed in another case than the disk spells it is refused, naming the '
              "disk's spelling, in git and outside it",
              refused(r1, str(R / 'sub' / 'deep')) and refused(r2, str(N / 't'))
              and not (R / '.study' / 'SUB%2FDeep').exists(), f'{why(r1)} {why(r2)}')
    else:
        print(f'SKIP  W28 a scope typed in another case (the temporary folder is case-sensitive: '
              f'{tmp})')
    o1, o2, o3 = (out(run(a, cwd=R)) for a in ('tree.json', '.', '.skill'))
    ws = {o.get('w') for o in (o1, o2, o3)}
    check('W29 the scopes tree.json, `.` and .skill get three distinct W\'s, and none is '
          '.study/.skill',
          len(ws) == 3 and None not in ws and str(R / '.study' / '.skill') not in ws
          and o3.get('w') == str(R / '.study' / '%2Eskill'), f'{o1} {o2} {o3}')
    Y = init(tmp / 'Y', {'a.md': '# a\n'})
    (tmp / 'elsewhere').mkdir()
    (Y / '.study').symlink_to(tmp / 'elsewhere')
    r = run('a.md', cwd=Y)
    check('W30 a .study that is a symlink is refused, and nothing is written where it points',
          refused(r, '.study') and not any((tmp / 'elsewhere').iterdir()), why(r))

    # ── the folder name ──────────────────────────────────────────────────────
    parts = ['a', 'f', '.', '/', '%', '@', '2', 'F', 'E', '%2F']
    seen: dict[str, tuple[str, str]] = {}
    bad: list = []
    for n in range(1, 4):
        for rel in map(''.join, itertools.product(parts, repeat=n)):
            for sym in ('', 'f', 'a.b', '%40'):
                name = attempt(lambda: where.w_name(rel, sym))
                if not isinstance(name, str) or name.startswith('.') or '/' in name:
                    bad.append((rel, sym, name))
                elif seen.setdefault(name, (rel, sym)) != (rel, sym):
                    bad.append((rel, sym, name, seen[name]))
    long = [attempt(lambda: where.w_name('d/' * 150 + str(i), '')) for i in range(3)]
    check('W31 w_name is one-to-one, never starts with a dot and never holds /, and a long scope '
          'keeps a distinct name of at most 255 bytes',
          not bad and all(isinstance(x, str) and len(x.encode()) <= 255 for x in long)
          and len(set(map(str, long))) == 3, f'{bad[:3]} {long!r:.200}')
    pair = attempt(lambda: (where.w_name('a@f', ''), where.w_name('a', 'f')))
    check('W31 a scope holding @ never meets a file:Symbol scope, as a@f and a:f',
          isinstance(pair, tuple) and pair[0] != pair[1], repr(pair))

    # ── how it runs ──────────────────────────────────────────────────────────
    lone = tmp / 'lone'
    lone.mkdir()
    shutil.copy(SCRIPT, lone / 'where.py')
    r = subprocess.run([sys.executable, '-I', str(lone / 'where.py'), str(N / 't')], cwd=Path('/'),
                       capture_output=True, text=True)
    check('W32 where.py copied alone runs under python3 -I from /',
          out(r).get('w') == str(nw), why(r))
    r = run(str(R / 'nope'), cwd=tmp)
    check('W33 a refusal is one line on stderr that starts `where: ` and names the path',
          refused(r, str(R / 'nope')), why(r))

    # ── what --files lists ───────────────────────────────────────────────────
    D = tmp / 'D'
    (D / 'emb').mkdir(parents=True)
    init(D / 'emb', {'e.md': '# e\n'})
    init(D, {'a.md': '# a\n', 'gone.md': '# g\n', 'docs/.study/x.md': '# x\n'})
    (D / 'gone.md').unlink()
    (D / 'inner').mkdir()
    init(D / 'inner', {'i.md': '# i\n'})
    (D / 'ln.md').symlink_to(D / 'a.md')
    os.mkfifo(D / 'pipe')
    o = out(run('.', '--files', cwd=D))
    check('W34 --files in git lists only regular files that exist: no folder of a nested or '
          'embedded repository, no deleted file, no symlink or fifo, nothing in a deeper .study',
          o.get('files') == [str(D / 'a.md')], str(o))
    I = init(tmp / 'I', {'.gitignore': '*.log\n', 'a.md': '# a\n'})
    (I / 'run.log').write_text('log\n')
    o = out(run('run.log', '--files', cwd=I))
    check('W35 a file scope that git ignores lists itself, as the scope names it',
          o.get('files') == [str(I / 'run.log')], str(o))
    CW = tmp / 'CW'
    folder = CW / 'folder'
    (folder / 'sub').mkdir(parents=True)
    (folder / 'sub' / 'n.md').write_text('# n\n')
    copy = folder / '.study' / '.skill' / 'scripts'
    copy.mkdir(parents=True)
    shutil.copy(SCRIPT, copy / 'where.py')
    r = subprocess.run([sys.executable, '-I', str(copy / 'where.py'), str(folder / 'sub')],
                       cwd=Path('/'), capture_output=True, text=True)
    gi = attempt(lambda: (folder / '.study' / '.gitignore').read_bytes())
    git('init', '-q', cwd=CW)
    st = attempt(lambda: git('status', '--porcelain', '--untracked-files=all', cwd=CW))
    check("W36 where.py run from Cowork's copy in <folder>/.study/.skill/scripts, on a subfolder "
          'scope outside git, also ignores the copy, so a repository around the folder sees only '
          'the notes',
          out(r).get('w') == str(folder / 'sub' / '.study' / '%2E') and gi == b'*\n'
          and st == '?? folder/sub/n.md\n', f'{why(r)} gitignore={gi!r} status={st!r}')
    check('W36 where.py run from anywhere else writes nothing beside itself',
          sorted(os.listdir(lone)) == ['where.py'], str(os.listdir(lone)))
    NR = tmp / 'NR'
    init(NR / 'sub', {'s.md': '# s\n'})
    (NR / 'wt').mkdir()
    (NR / 'wt' / '.git').write_text(f"gitdir: {NR / 'sub' / '.git' / 'worktrees' / 'wt'}\n")
    (NR / 'wt' / 'w.md').write_text('# w\n')
    (NR / 'n.md').write_text('# n\n')
    (NR / '.github').mkdir()
    (NR / '.notes').mkdir()
    dotted = [NR / '.gitignore', NR / '.gitattributes', NR / '.github' / 'x.yml',
              NR / '.notes' / 'n.md']
    for f in dotted:
        f.write_text('x\n')
    objects = [p for p in (NR / 'sub' / '.git' / 'objects').rglob('*') if p.is_file()]
    o = out(run(str(NR), '--files', cwd=tmp))
    files = o.get('files') or []
    kept = [NR / 'n.md', NR / 'sub' / 's.md', NR / 'wt' / 'w.md', *dotted]
    check('W37 --files outside git lists nothing under a .git folder or a .git file at any depth, '
          "and keeps a nested repository's working files, other dot-folders and .git* files",
          bool(objects) and o.get('git') is False
          and files == sorted(str(f) for f in kept)
          and not any('.git' in Path(f).parts for f in files), str(o))

    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed} passed, {failed} failed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
