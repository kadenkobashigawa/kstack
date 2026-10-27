#!/usr/bin/env python3
'''
test_tree.py builds throwaway git repositories and checks the outline `tree.py` writes for them.

Run it with `python3 test_tree.py`. It needs git and uv. It makes one temporary folder, runs git
with no global or system config inside it, and runs tree.py with `uv run`, which reads the
script's pinned dependencies. The exit code is the number of failed checks.

T1 to T10 hold a folder scope: nested folders, Python classes, methods, nested and decorated
functions, JavaScript classes and functions, path ids, sibling suffixes, the files git does not
track, the skipped extensions and the syntax warnings. T11 and T12 hold a file scope and a
file:Symbol scope, T13 to T16 the four ways a scope is refused, T17 the commit and dirty fields,
T18 and T19 the -o file, T20 the grammar table against the pinned dependencies, T21 a tracked file
deleted from the working tree or made a folder, T22 and T23 the repository root and a scope given
from a subfolder, T24 two definitions that start at one byte, T25 a folder scope whose name holds
':', and T26 the -o file's mode under the umask. T27 holds tracked symlinks and a submodule as
files in the scope, and T28 a link as the argument, followed into this repository, into another
repository or out of any. T29 holds a merge conflict, T30 spaces at the ends of names, T31 a named
function that is a variable's value, T32 the .mjs and .cjs extensions, T33 a scope that looks like
a glob, T34 a folder scope with no tracked files, T35 a filename that is not UTF-8, T36 an
unreadable file, T37 a folder that cannot be entered, in a run and as the scope, T38 the
file:Symbol example in tree.py's Commands text, run on that file in this repository, T39 git's
repository variables set in the caller's environment, T40 a file scope that git's index holds as a
symlink or a submodule, T41 a scope outside the work tree that core.worktree names, T43 a
repository whose parent folder, and a folder inside it, can be entered but not listed, T45 two
folders whose names differ only in case, and T46 git's pathspec variables set in the caller's
environment. T53 holds a folder, a file and a file:Symbol typed in another case than git's index
spells them, an accented letter included, T54 a repository folder typed in another case than git
reports its work tree, T55 an untracked name that differs only in case from a tracked one, T56 an
untracked hard link to a tracked file under a name that differs in case or normal form, T57 an
untracked folder that a tracked symlink, named in another case, points to, and T58 a tracked file
whose folder is now a symlink, under git's spelling, to that folder renamed in another case.

T36, T37 and T43 need permission bits that hold. As root they run tree.py under setpriv with the
DAC override capabilities dropped; when neither works they print a SKIP line. T53 and T54 need a
case-insensitive filesystem under the temporary folder, as macOS gives by default and TMPDIR can
name elsewhere, and T45 and T55 to T58 a case-sensitive one; each prints a SKIP line on the other
kind.
'''

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE    = Path(__file__).resolve().parent
SCRIPT  = HERE.parent / 'scripts' / 'tree.py'
UV      = shutil.which('uv') or str(Path.home() / '.local' / 'bin' / 'uv')
RESULTS = []
USER    = ('-c', 'user.name=t', '-c', 'user.email=t@t')
SETPRIV = ('setpriv', '--bounding-set=-dac_override,-dac_read_search',
           '--inh-caps=-dac_override,-dac_read_search')

MOD_PY = '''\
import functools


class Cls:
    def first(self):
        return 1

    @property
    def prop(self):
        return 2

    def second(self):
        def helper():
            return 3
        return helper()


def outer():
    def inner():
        return 4
    return inner()


@functools.cache
def cached():
    return 5


def twice():
    return 6


def twice():
    return 7


def main():
    return 0
'''

APP_JS = '''\
// a widget
class Widget {
  constructor(name) {
    this.name = name;
  }

  render() {
    return this.name;
  }
}

function main() {
  return new Widget('w').render();
}
'''

BROKEN_PY = '''\
def good():
    return 1


def bad(:
    pass


def also_good():
    return 2
'''

LEAF_PY = 'def main():\n    return 0'

CHAIN_JS = 'var y = function f() {}.x = function () {};\n'


def check(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


def shape(node: dict) -> tuple:
    '''a node as (id, name, kind, file, lines, children), nested, for literal comparison.'''
    return (node['id'], node['name'], node['kind'], node.get('file'),
            node.get('lines'), [shape(c) for c in node['children']])


def write(at: Path, files: dict[str, str]) -> None:
    '''each file written under a folder, its parent folders made.'''
    for rel, text in files.items():
        (at / rel).parent.mkdir(parents=True, exist_ok=True)
        (at / rel).write_text(text)


def child(node: dict, name: str) -> dict:
    '''the first child of a node with this name, or an empty leaf so a check fails, not raises.'''
    return next((c for c in node['children'] if c['name'] == name),
                {'id': '', 'name': '', 'kind': '', 'children': []})


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        tmp  = Path(t).resolve()
        env  = {**{k: v for k, v in os.environ.items() if not k.startswith('GIT_')},
                'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': str(tmp / 'gc'),
                'GIT_CEILING_DIRECTORIES': str(tmp)}
        repo = tmp / 'repo'
        pkg  = repo / 'pkg'

        def git(*a: str, cwd: Path = repo) -> str:
            return subprocess.run(['git', *a], cwd=cwd, env=env, check=True,
                                  capture_output=True, text=True).stdout.strip()

        probe = tmp / 'probe'
        probe.write_text('')
        probe.chmod(0)
        bind  = SETPRIV if os.geteuid() == 0 else ()
        held  = not bind or bool(shutil.which('setpriv')) and subprocess.run(
            [*bind, 'cat', str(probe)], capture_output=True, check=False).returncode != 0

        def tree(*a: str, cwd: Path = repo, bound: bool = False,
                 extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
            '''tree.py run with a and cwd; bound runs it where permission bits hold, as root too,
            and extra adds to its environment.'''
            return subprocess.run([*(bind if bound else ()), UV, 'run', '-q', '--script',
                                   str(SCRIPT), *a], cwd=cwd, env={**env, **(extra or {})},
                                  capture_output=True, text=True, check=False)

        def doc(*a: str, cwd: Path = repo) -> tuple[dict, str]:
            r = tree(*a, cwd=cwd)
            try:
                return json.loads(r.stdout), r.stderr
            except ValueError:
                return {'tree': {'id': '', 'name': '', 'kind': '', 'children': []}, 'skipped': {},
                        'warnings': []}, r.stderr

        files = {'pkg/mod.py': MOD_PY, 'pkg/app.js': APP_JS, 'pkg/broken.py': BROKEN_PY,
                 'pkg/core/deep/leaf.py': LEAF_PY, 'pkg/notes.md': '# notes\n',
                 'pkg/Makefile': 'all:\n', '.gitignore': 'pkg/ignored.py\n',
                 'pkg/gone.py': 'def gone():\n    pass\n', 'pkg/core.py': ''}
        for rel, text in files.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text(text)
        git('init', '-q', '-b', 'main')
        git('add', '-A')
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'c')
        (pkg / 'untracked.py').write_text('def untracked():\n    pass\n')
        (pkg / 'ignored.py').write_text('def ignored():\n    pass\n')
        (pkg / 'gone.py').unlink()

        d, err = doc('pkg')
        root   = d['tree']
        core   = child(root, 'core')
        check('T1 a folder scope nests folders by path, sorted by name with folders and files '
              'mixed, and an empty file is a leaf',
              (root['id'], root['name'], root['kind'], 'file' in root, 'lines' in root) ==
              ('pkg', 'pkg', 'root', False, False)
              and [c['name'] for c in root['children']] ==
              ['app.js', 'broken.py', 'core', 'core.py', 'mod.py']
              and shape(child(root, 'core.py')) == ('pkg/core.py', 'core.py', 'file', 'pkg/core.py',
                                                    [1, 1], [])
              and shape(core) == ('pkg/core', 'core', 'dir', None, None, [
                  ('pkg/core/deep', 'deep', 'dir', None, None, [
                      ('pkg/core/deep/leaf.py', 'leaf.py', 'file', 'pkg/core/deep/leaf.py',
                       [1, 2], [
                          ('pkg/core/deep/leaf.py/main', 'main', 'function',
                           'pkg/core/deep/leaf.py', [1, 2], [])])])])
              and 'tree: 2 folders, 5 files, 2 classes, 12 functions, 4 methods' in err,
              f'{[c["name"] for c in root["children"]]} {shape(core)} {err}')

        mod = child(root, 'mod.py')
        f   = 'pkg/mod.py'
        check('T2 a Python class holds its methods, decorated ones from the decorator line',
              shape(child(mod, 'Cls')) == ('pkg/mod.py/Cls', 'Cls', 'class', f, [4, 15], [
                  ('pkg/mod.py/Cls/first', 'first', 'method', f, [5, 6], []),
                  ('pkg/mod.py/Cls/prop', 'prop', 'method', f, [8, 10], []),
                  ('pkg/mod.py/Cls/second', 'second', 'method', f, [12, 15], [
                      ('pkg/mod.py/Cls/second/helper', 'helper', 'function', f, [13, 14], [])])])
              and (mod['kind'], mod.get('file'), mod.get('lines')) == ('file', f, [1, 38]),
              str(shape(child(mod, 'Cls'))))
        check('T3 a function nested in a function is a function',
              shape(child(mod, 'outer')) == ('pkg/mod.py/outer', 'outer', 'function', f, [18, 21], [
                  ('pkg/mod.py/outer/inner', 'inner', 'function', f, [19, 20], [])]),
              str(shape(child(mod, 'outer'))))
        check('T4 a decorated function starts at its decorator',
              shape(child(mod, 'cached')) == ('pkg/mod.py/cached', 'cached', 'function', f,
                                               [24, 26], []), str(shape(child(mod, 'cached'))))

        app = child(root, 'app.js')
        g   = 'pkg/app.js'
        check('T5 a JS class holds its methods but not its constructor, beside a top function',
              [shape(c) for c in app['children']] == [
                  ('pkg/app.js/Widget', 'Widget', 'class', g, [2, 10], [
                      ('pkg/app.js/Widget/render', 'render', 'method', g, [7, 9], [])]),
                  ('pkg/app.js/main', 'main', 'function', g, [12, 14], [])],
              str([shape(c) for c in app['children']]))
        mains = sorted(n['id'] for c in (app, mod, child(child(core, 'deep'), 'leaf.py'))
                       for n in c['children'] if n['name'] == 'main')
        check('T6 functions named main in different files have different ids',
              mains == ['pkg/app.js/main', 'pkg/core/deep/leaf.py/main', 'pkg/mod.py/main'],
              str(mains))
        check('T7 a name repeated among siblings gets ~2 on its id, and keeps its name',
              [(c['id'], c['name'], c['lines']) for c in mod['children'] if c['name'] == 'twice'] ==
              [('pkg/mod.py/twice', 'twice', [29, 30]), ('pkg/mod.py/twice~2', 'twice', [33, 34])],
              str([c['id'] for c in mod['children']]))
        flat = json.dumps(d)
        check('T8 untracked and gitignored files stay out of the tree',
              'untracked' not in flat and 'ignored' not in flat, flat[:200])
        check('T9 a file with no grammar is left out and counted by extension',
              d.get('skipped') == {'': 1, '.md': 1}
              and 'notes' not in flat and 'Makefile' not in flat
              and 'tree: skipped with no grammar: no extension 1, .md 1' in err,
              f"{d.get('skipped')} {err}")
        broken = child(root, 'broken.py')
        check('T10 a file with a syntax error is a warning, and its definitions are kept',
              'pkg/broken.py: 1 syntax error' in d['warnings']
              and 'tree: warning: pkg/broken.py: 1 syntax error' in err
              and [c['name'] for c in broken['children']] == ['good', 'bad', 'also_good'],
              f"{d.get('warnings')} {[c['name'] for c in broken['children']]}")

        d, _ = doc('pkg/mod.py')
        check('T11 a file scope is a root with the file and its lines, holding its top-level defs',
              (d.get('scope'), d['tree']['id'], d['tree']['name'], d['tree']['kind'],
               d['tree'].get('file'), d['tree'].get('lines')) ==
              ('pkg/mod.py', 'pkg/mod.py', 'mod.py', 'root', 'pkg/mod.py', [1, 38])
              and [c['id'] for c in d['tree']['children']] ==
              ['pkg/mod.py/Cls', 'pkg/mod.py/outer', 'pkg/mod.py/cached', 'pkg/mod.py/twice',
               'pkg/mod.py/twice~2', 'pkg/mod.py/main'], str(d.get('tree', {}).get('id')))
        d, _ = doc('pkg/mod.py:Cls.second')
        check('T12 a file:Cls.meth scope is a root at that method, holding what it nests',
              d.get('scope') == 'pkg/mod.py:Cls.second' and shape(d['tree']) ==
              ('pkg/mod.py/Cls/second', 'second', 'root', f, [12, 15], [
                  ('pkg/mod.py/Cls/second/helper', 'helper', 'function', f, [13, 14], [])]),
              str(shape(d['tree'])))

        r = tree('pkg/mod.py:Cls.nope', '-o', str(tmp / 'never.json'))
        check('T13 a missing symbol exits 2 naming it on stderr, and writes nothing',
              r.returncode == 2 and r.stdout == '' and r.stderr.startswith('tree: ')
              and 'Cls.nope' in r.stderr and 'first, prop, second' in r.stderr
              and not (tmp / 'never.json').exists(), f'{r.returncode} {r.stderr}')
        r = tree('pkg/nowhere.py')
        check('T14 a missing path exits 2 with tree: and the reason',
              r.returncode == 2 and r.stderr.startswith('tree: ')
              and 'pkg/nowhere.py: no such file or folder' in r.stderr,
              f'{r.returncode} {r.stderr}')
        r = tree('pkg/untracked.py')
        check('T15 a file scope git does not track exits 2 with tree: and the reason',
              r.returncode == 2 and 'pkg/untracked.py: not tracked by git' in r.stderr,
              f'{r.returncode} {r.stderr}')
        (tmp / 'loose').mkdir()
        (tmp / 'loose' / 'a.py').write_text('def a():\n    pass\n')
        r = tree('a.py', cwd=tmp / 'loose')
        check('T16 a path outside any git repository exits 2 with tree: and the reason',
              r.returncode == 2 and r.stderr.startswith('tree: ')
              and 'not a git repository' in r.stderr, f'{r.returncode} {r.stderr}')

        (pkg / 'core' / 'scratch.py').write_text('def scratch():\n    pass\n')
        head   = git('rev-parse', 'HEAD')
        before = doc('pkg/core')[0]
        (pkg / 'mod.py').write_text(MOD_PY + '\n\ndef added():\n    pass\n')
        after  = doc('pkg/mod.py')[0]
        check('T17 commit is HEAD, an untracked file leaves dirty false, and an edit makes it true',
              (before.get('commit'), before.get('dirty'), after.get('commit'), after.get('dirty'))
              == (head, False, head, True)
              and doc('pkg')[0].get('dirty') is True,
              f"{before.get('dirty')} {after.get('dirty')}")

        out, keep = tmp / 'out' / 'tree.json', tmp / 'out' / 'keep.json'
        out.parent.mkdir()
        keep.write_text('keep me\n')
        out.symlink_to(keep)
        r     = tree('pkg/core', '-o', str(out))
        wrote = out.read_text() if out.exists() else ''
        check('T18 -o writes the document to the file, replacing it, with no temp file left',
              r.returncode == 0 and r.stdout == '' and json.loads(wrote or '{}').get('scope') ==
              'pkg/core' and wrote == tree('pkg/core').stdout and not out.is_symlink()
              and keep.read_text() == 'keep me\n'
              and sorted(p.name for p in out.parent.iterdir()) == ['keep.json', 'tree.json'],
              f'{r.returncode} {r.stderr} {sorted(p.name for p in out.parent.iterdir())}')
        r = tree('pkg/core', '-o', str(tmp / 'no-such-dir' / 'tree.json'))
        (out.parent / 'a-folder').mkdir()
        q = tree('pkg/core', '-o', str(out.parent / 'a-folder'))
        check('T19 -o into a missing folder, or onto a folder, exits 2 and leaves no temp file',
              r.returncode == 2 and r.stderr.startswith('tree: ') and q.returncode == 2
              and q.stderr.startswith('tree: ') and sorted(p.name for p in out.parent.iterdir())
              == ['a-folder', 'keep.json', 'tree.json'], f'{r.stderr} {q.stderr}')

        text  = SCRIPT.read_text() if SCRIPT.exists() else ''
        block = re.search(r'^# /// script\n(.*?)^# ///$', text, re.DOTALL | re.MULTILINE)
        deps  = re.findall(r'"([a-z0-9-]+)==([0-9.]+)"', block.group(1) if block else '')
        langs = [n for n in ast.walk(ast.parse(text)) if isinstance(n, (ast.Assign, ast.AnnAssign))
                 and any(getattr(x, 'id', '') == 'LANGS'
                         for x in getattr(n, 'targets', [getattr(n, 'target', None)]))]
        mods  = sorted(c.args[0].value for c in ast.walk(langs[0]) if isinstance(c, ast.Call)) \
            if langs else []
        check('T20 the grammar modules in LANGS and the pinned PEP 723 dependencies are the same',
              bool(mods) and mods == sorted(n.replace('-', '_') for n, _ in deps
                                            if n != 'tree-sitter'), f'{mods} {deps}')

        (pkg / 'core.py').unlink()
        (pkg / 'core.py').mkdir()
        d, err = doc('pkg')
        check('T21 a tracked file deleted from the working tree, or made a folder, is a warning, '
              'not a node',
              {f'pkg/{n}: tracked but missing from the working tree'
               for n in ('gone.py', 'core.py')} <= set(d.get('warnings', []))
              and not {'gone.py', 'core.py'} & {c['name'] for c in d['tree']['children']},
              str(d.get('warnings')))
        d, _ = doc('.')
        check('T22 the repository root has id ., the folder name, and children ids without ./',
              (d.get('scope'), d['tree']['id'], d['tree']['name'],
               [c['id'] for c in d['tree']['children']], d.get('skipped')) ==
              ('.', '.', 'repo', ['pkg'], {'': 2, '.md': 1}), str(d.get('tree', {}).get('id')))
        d, _ = doc('mod.py:Cls', cwd=pkg)
        check('T23 a scope given from a subfolder is normalized to the repository',
              (d.get('scope'), d['tree']['id']) == ('pkg/mod.py:Cls', 'pkg/mod.py/Cls'),
              str(d.get('scope')))

        two = tmp / 'two'
        (two / 'odd:dir').mkdir(parents=True)
        (two / 'odd:dir' / 'x.py').write_text('def x():\n    pass\n')
        (two / 'chain.js').write_text(CHAIN_JS)
        git('init', '-q', '-b', 'main', cwd=two)
        git('add', '-A', cwd=two)
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'c', cwd=two)
        d, _ = doc('chain.js', cwd=two)
        check('T24 two definitions that start at one byte are both kept, the longer one outer',
              [shape(c) for c in d['tree']['children']] == [
                  ('chain.js/x', 'x', 'function', 'chain.js', [1, 1], [
                      ('chain.js/x/f', 'f', 'function', 'chain.js', [1, 1], [])])],
              str([shape(c) for c in d['tree']['children']]))
        d, _ = doc('odd:dir', cwd=two)
        check("T25 a folder whose name holds ':' given as the scope outlines that folder",
              (d.get('scope'), d['tree']['id'], [c['id'] for c in d['tree']['children']]) ==
              ('odd:dir', 'odd:dir', ['odd:dir/x.py']), str(d.get('scope')))

        modes = []
        for mask in (0o022, 0o027):
            old = os.umask(mask)
            try:
                tree('pkg/core', '-o', str(tmp / f'mode-{mask:o}.json'))
            finally:
                os.umask(old)
            p = tmp / f'mode-{mask:o}.json'
            modes.append(p.stat().st_mode & 0o777 if p.exists() else None)
        check('T26 -o makes a file with mode 0666 less the umask, as a plain write would',
              modes == [0o644, 0o640], str([oct(m) if m else m for m in modes]))

        def init(at: Path) -> None:
            git('init', '-q', '-b', 'main', cwd=at)
            git('add', '-A', cwd=at)
            git(*USER, 'commit', '-q', '-m', 'c', cwd=at)

        links, outside = tmp / 'links', tmp / 'outside'
        write(outside, {'s.py': 'def secret():\n    pass\n', 'w.py': 'def secret2():\n    pass\n'})
        write(links, {'top.py': 'def top():\n    pass\n', 'sub/a.py': 'def a():\n    pass\n',
                      'dd/w.py': 'def w():\n    pass\n'})
        (links / 'tl.py').symlink_to('top.py')
        (links / 'link.py').symlink_to('../outside/s.py')
        (links / 'ldir').symlink_to('sub')
        init(links)
        git('update-index', '--add', '--cacheinfo', f"160000,{git('rev-parse', 'HEAD', cwd=links)},"
            'subm', cwd=links)
        git(*USER, 'commit', '-q', '-m', 'gitlink', cwd=links)
        shutil.rmtree(links / 'dd')
        (links / 'dd').symlink_to('../outside')
        d, err = doc('.', cwd=links)
        check('T27 a tracked symlink is never followed and a submodule is not missing: each is '
              'left out and counted in skipped',
              [c['name'] for c in d['tree']['children']] == ['sub', 'top.py']
              and [c['name'] for c in child(d['tree'], 'sub')['children']] == ['a.py']
              and d.get('skipped') == {'submodule': 1, 'symlink': 4} and d.get('warnings') == []
              and 'secret' not in json.dumps(d)
              and 'tree: skipped, not followed: submodule 1, symlink 4' in err,
              f"{[c['name'] for c in d['tree']['children']]} {d.get('skipped')} "
              f"{d.get('warnings')} {err}")
        other = tmp / 'other'
        write(other, {'o/p.py': 'def p():\n    pass\n'})
        init(other)
        (links / 'ofile.py').symlink_to('../other/o/p.py')
        (links / 'odir').symlink_to('../other/o')
        (links / 'lout').symlink_to('../outside')
        d, _   = doc('tl.py', cwd=links)
        fl, _  = doc('ofile.py:p', cwd=links)
        dl, _  = doc('odir', cwd=links)
        r      = tree('lout', cwd=links)
        check('T28 a link argument is followed and the repository its target lies in is outlined: '
              'a file here, a file and a folder in another repository, and a folder in none '
              'exits 2',
              (d.get('scope'), d['tree']['id']) == ('top.py', 'top.py')
              and (fl.get('scope'), fl['tree']['id']) == ('o/p.py:p', 'o/p.py/p')
              and (dl.get('scope'), [c['id'] for c in dl['tree']['children']]) == ('o', ['o/p.py'])
              and r.returncode == 2 and r.stderr.startswith('tree: ')
              and 'not a git repository' in r.stderr,
              f"{d.get('scope')} {fl.get('scope')} {dl.get('scope')} {r.returncode} {r.stderr}")

        merge = tmp / 'merge'
        write(merge, {'c.py': 'def base():\n    pass\n'})
        init(merge)
        git('checkout', '-q', '-b', 'other', cwd=merge)
        write(merge, {'c.py': 'def other():\n    pass\n'})
        git(*USER, 'commit', '-q', '-am', 'other', cwd=merge)
        git('checkout', '-q', 'main', cwd=merge)
        write(merge, {'c.py': 'def mine():\n    pass\n'})
        git(*USER, 'commit', '-q', '-am', 'mine', cwd=merge)
        conflict = subprocess.run(['git', *USER, 'merge', '-q', 'other'], cwd=merge, env=env,
                                  capture_output=True, check=False).returncode
        stages   = git('ls-files', '-s', cwd=merge).count('c.py')
        d, _ = doc('.', cwd=merge)
        check('T29 a file in a merge conflict is one node, not one per stage',
              (conflict, stages) == (1, 3) and [c['id'] for c in d['tree']['children']] == ['c.py'],
              str([c['id'] for c in d['tree']['children']]))

        lead = tmp / 'lead '
        write(lead, {' lead.py': 'def lead():\n    pass\n', 'b.py': 'def b():\n    pass\n'})
        init(lead)
        d, err = doc('.', cwd=lead)
        check('T30 a leading space on a filename and a trailing space on the repository folder '
              'are kept',
              [c['name'] for c in d['tree']['children']] == [' lead.py', 'b.py']
              and [c['name'] for c in child(d['tree'], ' lead.py')['children']] == ['lead']
              and d.get('warnings') == [], f"{[c['name'] for c in d['tree']['children']]} {err}")

        js = tmp / 'js'
        write(js, {'value.js': 'const g = function h() {};\nconst o = { k: function k() {} };\n'
                               'a.b = function c() {};\n',
                   'm.mjs': 'export function m() {}\n', 'c.cjs': 'function c() {}\n',
                   'd*/x.py': 'def x():\n    pass\n', 'da/y.py': 'def y():\n    pass\n',
                   '.gitignore': 'build/\n'})
        init(js)
        write(js, {'build/b.js': 'function b() {}\n', 'loose/n.py': 'def n():\n    pass\n'})
        d, _ = doc('value.js', cwd=js)
        v    = 'value.js'
        check('T31 a named function that is the value of a variable, a key or an assignment is one '
              'node with the outer name',
              [shape(c) for c in d['tree']['children']] == [
                  ('value.js/g', 'g', 'function', v, [1, 1], []),
                  ('value.js/k', 'k', 'function', v, [2, 2], []),
                  ('value.js/b', 'b', 'function', v, [3, 3], [])],
              str([shape(c) for c in d['tree']['children']]))
        d, _ = doc('.', cwd=js)
        check('T32 .mjs and .cjs files are outlined as JavaScript',
              [c['id'] for c in child(d['tree'], 'm.mjs')['children']] == ['m.mjs/m']
              and [c['id'] for c in child(d['tree'], 'c.cjs')['children']] == ['c.cjs/c'],
              str([c['id'] for c in d['tree']['children']]))
        (js / 'da' / 'y.py').write_text('def y2():\n    pass\n')
        d, _ = doc('d*', cwd=js)
        (js / 'da' / 'y.py').write_text('def y():\n    pass\n')
        check("T33 a scope is a literal path, so 'd*' does not match the folder beside it, and a "
              'change there does not make it dirty',
              [c['id'] for c in d['tree']['children']] == ['d*/x.py'] and d.get('dirty') is False,
              str([c['id'] for c in d['tree']['children']]) + f" dirty={d.get('dirty')}")
        r, q = tree('loose', cwd=js), tree('build', cwd=js)
        check('T34 a folder scope with no tracked files, untracked or ignored, exits 2 naming it',
              (r.returncode, q.returncode) == (2, 2)
              and r.stderr.startswith('tree: ') and 'no tracked files under loose' in r.stderr
              and q.stderr.startswith('tree: ') and 'no tracked files under build' in q.stderr,
              f'{r.returncode} {r.stderr} {q.returncode} {q.stderr}')

        latin = tmp / 'latin'
        latin.mkdir()
        with open(os.fsencode(latin) + b'/caf\xe9.py', 'w') as fh:
            fh.write('def cafe():\n    pass\n')
        write(latin, {'locked.py': 'def locked():\n    pass\n', 'open.py': 'def ok():\n    pass\n'})
        init(latin)
        d, err = doc('caf\udce9.py', cwd=latin)
        check('T35 a filename that is not UTF-8 is read and named',
              (d['tree']['name'], [c['name'] for c in d['tree']['children']]) ==
              ('caf\udce9.py', ['cafe']), f"{d['tree']['name']!r} {err}")
        lockd = tmp / 'lockd'
        write(lockd, {'locked/l.py': 'def l():\n    pass\n', 'o.py': 'def o():\n    pass\n'})
        init(lockd)
        if not held:
            print('SKIP  T36 and T37 an unreadable file and folder (permission bits do not hold: '
                  'root without setpriv)')
        else:
            (latin / 'locked.py').chmod(0)
            r, q = tree('.', cwd=latin, bound=True), tree('locked.py', cwd=latin, bound=True)
            d    = json.loads(r.stdout or '{}')
            check('T36 an unreadable file is a warning and the run goes on, and as a file scope '
                  'it exits 2 with that reason',
                  r.returncode == 0 and 'locked.py: cannot be read: Permission denied'
                  in d.get('warnings', []) and 'open.py' in r.stdout and q.returncode == 2
                  and q.stderr == 'tree: locked.py: cannot be read: Permission denied\n',
                  f'{r.returncode} {r.stderr} {q.returncode} {q.stderr}')
            (latin / 'locked.py').chmod(0o644)
            (lockd / 'locked').chmod(0)
            r    = tree('.', cwd=lockd, bound=True)
            d    = json.loads(r.stdout or '{}')
            refused = [tree(a, cwd=lockd, bound=True) for a in ('locked', 'locked/l.py',
                                                               'locked/l.py:l')]
            check('T37 a folder that cannot be entered is a warning per file in a run, and as the '
                  'scope, its file or a symbol in it, exits 2 with tree: and the reason',
                  r.returncode == 0 and d.get('warnings') ==
                  ['locked/l.py: cannot be read: Permission denied']
                  and [c['id'] for c in d['tree']['children']] == ['o.py']
                  and [q.returncode for q in refused] == [2, 2, 2]
                  and all(q.stderr.startswith('tree: ') and q.stderr.count('\n') == 1
                          and q.stderr.endswith(': Permission denied\n') for q in refused)
                  and refused[1].stderr == refused[2].stderr ==
                  'tree: locked/l.py: Permission denied\n',
                  f'{r.returncode} {r.stderr} {[(q.returncode, q.stderr) for q in refused]}')
            (lockd / 'locked').chmod(0o755)

        example = re.search(r'\((gate\.py:[\w.]+)', text)
        r = tree(f'skills/build/scripts/{example.group(1)}', cwd=HERE.parents[2]) if example \
            else None
        check("T38 the Commands text's gate.py:Symbol example names a definition gate.py has",
              r is not None and r.returncode == 0, r.stderr if r else 'no example')

        plain = tree('pkg/core')
        set_  = {k: tree('pkg/core', extra={k: v}) for k, v in (
            ('GIT_WORK_TREE', str(other)), ('GIT_DIR', str(other / '.git')),
            ('GIT_INDEX_FILE', str(other / '.git' / 'index')),
            ('GIT_COMMON_DIR', str(other / '.git')),
            ('GIT_OBJECT_DIRECTORY', str(other / '.git' / 'objects')))}
        check('T39 GIT_DIR, GIT_WORK_TREE, GIT_INDEX_FILE, GIT_COMMON_DIR and GIT_OBJECT_DIRECTORY '
              'set to another repository leave the outline as it is without them',
              plain.returncode == 0 and all((q.returncode, q.stdout) == (0, plain.stdout)
                                            for q in set_.values()),
              str({k: (q.returncode, q.stderr[-200:]) for k, q in set_.items()
                   if (q.returncode, q.stdout) != (0, plain.stdout)}))
        specs = {(k, a): tree(a, extra=dict.fromkeys(k.split('+'), '1')) for k in (
            'GIT_LITERAL_PATHSPECS', 'GIT_ICASE_PATHSPECS', 'GIT_GLOB_PATHSPECS',
            'GIT_NOGLOB_PATHSPECS', 'GIT_LITERAL_PATHSPECS+GIT_ICASE_PATHSPECS')
            for a in ('pkg/core', 'pkg/mod.py')}
        bare  = {a: tree(a) for a in ('pkg/core', 'pkg/mod.py')}
        ceil  = tree('pkg/core', extra={'GIT_CEILING_DIRECTORIES': str(repo)})
        check("T46 git's pathspec variables set in the caller's environment, one at a time or "
              'GIT_LITERAL_PATHSPECS and GIT_ICASE_PATHSPECS together, leave the outline as it is '
              'without them, and another GIT_ variable still reaches git',
              all(r.returncode == 0 for r in bare.values())
              and ceil.returncode == 2 and 'not a git repository' in ceil.stderr
              and all((q.returncode, q.stdout) == (0, bare[a].stdout)
                      for (_, a), q in specs.items()),
              str({k: (q.returncode, q.stderr[-200:]) for k, q in specs.items()
                   if (q.returncode, q.stdout) != (0, bare[k[1]].stdout)}))

        kinds = tmp / 'kinds'
        write(kinds, {'a.py': 'def a():\n    pass\n'})
        (kinds / 'l.py').symlink_to('a.py')
        init(kinds)
        git('update-index', '--add', '--cacheinfo', f"160000,{git('rev-parse', 'HEAD', cwd=kinds)},"
            'g.py', cwd=kinds)
        git(*USER, 'commit', '-q', '-m', 'gitlink', cwd=kinds)
        (kinds / 'l.py').unlink()
        write(kinds, {'l.py': 'def l():\n    pass\n', 'g.py': 'def g():\n    pass\n'})
        refused = [tree(a, cwd=kinds) for a in ('l.py', 'g.py')]
        check("T40 a file scope that is a symlink or a submodule in git's index, with a regular "
              'file in the working tree, exits 2 saying so',
              [(q.returncode, q.stderr) for q in refused] == [
                  (2, "tree: l.py: a symlink in git's index, and those are never followed\n"),
                  (2, "tree: g.py: a submodule in git's index, and those are never followed\n")],
              str([(q.returncode, q.stderr) for q in refused]))

        moved, elsewhere = tmp / 'moved', tmp / 'elsewhere'
        write(moved, {'pkg/a.py': 'def a():\n    pass\n'})
        elsewhere.mkdir()
        init(moved)
        git('config', 'core.worktree', str(elsewhere), cwd=moved)
        r = tree('pkg', cwd=moved)
        check('T41 a scope outside the work tree git reports, set by core.worktree, exits 2 '
              'naming the path and that work tree',
              (r.returncode, r.stderr) == (2, f'tree: pkg: resolves to {moved / "pkg"}, not '
                                              f'under the work tree git reports, {elsewhere}\n'),
              f'{r.returncode} {r.stderr[-300:]}')

        trav = tmp / 'trav'
        write(trav / 'repo', {'pkg/a.py': 'def a():\n    pass\n',
                              'shut/sub/b.py': 'def b():\n    pass\n'})
        init(trav / 'repo')
        if not held:
            print('SKIP  T43 a folder that can be entered but not listed (permission bits do not '
                  'hold: root without setpriv)')
        else:
            (trav / 'repo' / 'shut').chmod(0o311)
            trav.chmod(0o311)
            runs = {a: tree(a, cwd=trav / 'repo', bound=True)
                    for a in ('.', 'pkg', 'shut', 'shut/sub', 'shut/sub/b.py:b')}
            trav.chmod(0o755)
            (trav / 'repo' / 'shut').chmod(0o755)
            got = {a: (r.returncode, json.loads(r.stdout or '{}').get('scope'),
                       'warning' in r.stderr) for a, r in runs.items()}
            check('T43 a repository whose parent folder, and a folder inside it, can be entered '
                  'but not listed (mode 0311) is outlined at every scope, with no warning',
                  got == {a: (0, a, False) for a in runs},
                  str({a: (r.returncode, r.stderr[-200:]) for a, r in runs.items()}))

        cased = tmp / 'Cased'
        write(cased, {'Pkg/Mod.py': 'def f():\n    pass\n', 'Pkg/sub/s.py': 'def s():\n    pass\n',
                      '\u00c9cole/m.py': 'def m():\n    pass\n'})
        if (tmp / 'PROBE').exists():
            init(cased)
            hint = "git tracks it as {}; scopes match git's spelling exactly"
            ok   = {a: tree(a, cwd=cased) for a in ('Pkg', 'Pkg/Mod.py:f', '\u00c9cole')}
            runs = {a: tree(a, cwd=cased) for a in ('pkg', 'PKG/SUB', 'Pkg/MOD.PY',
                                                    'pkg/mod.py:f', '\u00e9cole')}
            got  = {a: (r.returncode, r.stdout, r.stderr) for a, r in runs.items()}
            want = {a: (2, '', f'tree: {rel}: {hint.format(spelled)}\n') for a, rel, spelled in (
                ('pkg', 'pkg', 'Pkg'), ('PKG/SUB', 'PKG/SUB', 'Pkg/sub'),
                ('Pkg/MOD.PY', 'Pkg/MOD.PY', 'Pkg/Mod.py'),
                ('pkg/mod.py:f', 'pkg/mod.py', 'Pkg/Mod.py'),
                ('\u00e9cole', '\u00e9cole', '\u00c9cole'))}
            check('T53 a folder, a file or a file:Symbol typed in another case than git spells '
                  'it, an accented letter included, on a case-insensitive filesystem, exits 2 '
                  "naming git's spelling, and git's own spelling is outlined",
                  got == want and all(r.returncode == 0 for r in ok.values()),
                  str(({a: g for a, g in got.items() if g != want[a]},
                       {a: r.stderr[-200:] for a, r in ok.items() if r.returncode})))
            mixed = tmp / 'mixed'
            write(mixed, {'Pkg/a.py': 'def a():\n    pass\n', 'Pkg/b.py': 'def b():\n    pass\n'})
            git('init', '-q', '-b', 'main', cwd=mixed)
            git('add', 'Pkg/a.py', cwd=mixed)
            blob = git('hash-object', '-w', 'Pkg/b.py', cwd=mixed)
            git('update-index', '--add', '--cacheinfo', f'100644,{blob},pkg/b.py', cwd=mixed)
            git(*USER, 'commit', '-q', '-m', 'c', cwd=mixed)
            r = tree('PKG', cwd=mixed)
            check('T53 a folder typed in another case than either of two spellings git tracks it '
                  'under exits 2 naming both',
                  (r.returncode, r.stderr) == (2, f"tree: PKG: {hint.format('Pkg and pkg')}\n"),
                  f'{r.returncode} {r.stderr[-300:]}')
            git('config', 'core.worktree', str(cased), cwd=cased)
            r = tree('cased/Pkg', cwd=tmp)
            check('T54 a scope whose repository folder is typed in another case than git reports '
                  'its work tree, as macOS reports it and core.worktree makes it here, on a '
                  'case-insensitive filesystem, exits 2 naming the path it resolves to and '
                  'that work tree',
                  (r.returncode, r.stderr) == (2, f'tree: cased/Pkg: resolves to {tmp}/cased/Pkg, '
                                                  f'not under the work tree git reports, '
                                                  f'{cased}\n'),
                  f'{r.returncode} {r.stderr[-300:]}')
            print('SKIP  T45 and T55 to T58 names that differ only in case (the temporary '
                  f'folder is case-insensitive: {tmp})')
        else:
            print('SKIP  T53 and T54 a scope typed in another case (the temporary folder is '
                  f'case-sensitive: {tmp})')
            twins = tmp / 'twins'
            write(twins, {'Pkg/a.py': 'def a():\n    pass\n', 'pkg/b.py': 'def b():\n    pass\n'})
            init(twins)
            runs = {a: tree(a, cwd=twins) for a in ('pkg', 'Pkg', 'PKG')}
            got  = {a: (r.returncode, [c['id'] for c in json.loads(r.stdout or '{}')
                                       .get('tree', {'children': []})['children']], r.stderr)
                    for a, r in runs.items()}
            git('config', 'core.ignorecase', 'true', cwd=twins)
            icase = {a: tree(a, cwd=twins) for a in ('pkg', 'Pkg')}
            git('config', 'core.ignorecase', 'false', cwd=twins)
            check('T45 on a case-sensitive filesystem two folders whose names differ only in case '
                  'are two scopes, with core.ignorecase true too, and a third case is no such '
                  'folder',
                  {a: g[:2] for a, g in got.items()} == {'pkg': (0, ['pkg/b.py']),
                                                         'Pkg': (0, ['Pkg/a.py']), 'PKG': (2, [])}
                  and got['PKG'][2] == 'tree: PKG: no such file or folder\n'
                  and all(r.stdout == runs[a].stdout for a, r in icase.items()), str(got))
            apart = tmp / 'apart'
            write(apart, {'Pkg/a.py': 'def a():\n    pass\n'})
            init(apart)
            write(apart, {'pkg/a.py': 'def a():\n    pass\n', 'Gone/g.py': ''})
            git('add', 'Gone/g.py', cwd=apart)
            git(*USER, 'commit', '-q', '-m', 'g', cwd=apart)
            (apart / 'Gone' / 'g.py').rename(apart / 'pkg' / 'g.py')
            (apart / 'Gone').rename(apart / 'gone')
            refused = [tree(a, cwd=apart) for a in ('pkg', 'pkg/a.py:a', 'gone')]
            check('T55 on a case-sensitive filesystem an untracked folder or file whose name '
                  'differs only in case from a tracked one, there or gone, is refused as '
                  "untracked, naming no spelling of git's",
                  [(q.returncode, q.stderr) for q in refused] == [
                      (2, 'tree: no tracked files under pkg\n'),
                      (2, 'tree: pkg/a.py: not tracked by git, or its extension has no '
                          'grammar\n'),
                      (2, 'tree: no tracked files under gone\n')],
                  str([(q.returncode, q.stderr) for q in refused]))
            write(apart, {'\u00c9cole.py': 'def e():\n    pass\n', 'Cafe\u0301.py': ''})
            git('add', '\u00c9cole.py', 'Cafe\u0301.py', cwd=apart)
            git(*USER, 'commit', '-q', '-m', 'e', cwd=apart)
            os.link(apart / '\u00c9cole.py', apart / 'E\u0301cole.py')
            os.link(apart / 'Cafe\u0301.py', apart / 'Caf\u00e9.py')
            os.link(apart / 'Pkg' / 'a.py', apart / 'Pkg' / 'A.py')
            refused = [tree(a, cwd=apart) for a in ('E\u0301cole.py', 'Caf\u00e9.py',
                                                    'Pkg/A.py:a')]
            check("T56 an untracked hard link to a tracked file, named in another case or "
                  "another Unicode normal form, exits 2 naming git's spelling",
                  [(q.returncode, q.stderr) for q in refused] == [
                      (2, "tree: E\u0301cole.py: git tracks it as \u00c9cole.py; scopes match "
                          "git's spelling exactly\n"),
                      (2, "tree: Caf\u00e9.py: git tracks it as Cafe\u0301.py; scopes match git's "
                          'spelling exactly\n'),
                      (2, "tree: Pkg/A.py: git tracks it as Pkg/a.py; scopes match git's "
                          'spelling exactly\n')],
                  str([(q.returncode, q.stderr) for q in refused]))
            aimed = tmp / 'aimed'
            write(aimed, {'Pkg/a.py': 'def a():\n    pass\n'})
            (aimed / 'pkg').symlink_to('Pkg')
            git('init', '-q', '-b', 'main', cwd=aimed)
            git('add', 'pkg', cwd=aimed)
            git(*USER, 'commit', '-q', '-m', 'c', cwd=aimed)
            refused = [tree(a, cwd=aimed) for a in ('Pkg', 'pkg')]
            check("T57 on a case-sensitive filesystem an untracked folder that git's index holds "
                  'a symlink to under a name that differs only in case, typed either way, is '
                  "refused as untracked, naming no spelling of git's",
                  [(q.returncode, q.stderr) for q in refused]
                  == [(2, 'tree: no tracked files under Pkg\n')] * 2,
                  str([(q.returncode, q.stderr) for q in refused]))
            relinked = tmp / 'relinked'
            write(relinked, {'pkg/a.py': 'def a():\n    pass\n'})
            init(relinked)
            (relinked / 'pkg').rename(relinked / 'Pkg')
            (relinked / 'pkg').symlink_to('Pkg')
            refused = [tree(a, cwd=relinked) for a in ('Pkg/a.py', 'pkg/a.py', 'Pkg')]
            check("T58 on a case-sensitive filesystem a tracked file whose folder was renamed in "
                  'another case, with a symlink left under the old name, is refused as '
                  "untracked, naming no spelling of git's that runs through the symlink",
                  [(q.returncode, q.stderr) for q in refused] == [
                      (2, 'tree: Pkg/a.py: not tracked by git, or its extension has no '
                          'grammar\n')] * 2 + [(2, 'tree: no tracked files under Pkg\n')],
                  str([(q.returncode, q.stderr) for q in refused]))
    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
