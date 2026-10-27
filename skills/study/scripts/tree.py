#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tree-sitter==0.26.0",
#     "tree-sitter-python==0.25.0",
#     "tree-sitter-javascript==0.25.0",
# ]
# ///
'''
tree.py writes the outline of one scope of a git repository as one JSON tree of its folders,
files, classes, functions and methods. The definitions come from each grammar package's own
queries/tags.scm.

Commands
--------
    tree.py SCOPE [-o FILE]
                         SCOPE is a path inside a git repository. It is a folder, a file, or
                         file:Symbol, dotted for nesting (gate.py:land, a.py:Cls.meth). The
                         command writes the document to FILE, or to stdout without -o. The node
                         counts, the skipped counts and the warnings go to stderr. The command
                         exits 2 with `tree:` and the reason on stderr when it cannot outline,
                         stat or enter the scope, or cannot write the -o file.

Output
------
    {"schema": 1, "scope": str, "commit": str, "dirty": bool,
     "skipped": {".md": 3, "symlink": 1}, "warnings": [str], "tree": Node}
    Node = {"id", "name", "kind", "file"?, "lines"?, "children": [Node]}

    kind is root, dir, file, class, function or method. file (repo-relative) and lines
    ([start, end], 1-based, inclusive) are on file, class, function and method nodes, and on a
    root that is a file or a symbol. id is the repo-relative path to the node joined with '/'.
    A definition's id reads skills/build/scripts/gate.py/land, and the repository root's id is '.'.
    A name repeated among siblings gets '~2', '~3' on its id by order, and keeps its name.
    scope is the argument with its links resolved, relative to the repository its target lies in.
    That repository is the one outlined. A link in the argument is followed the way it was typed.
    A scope matches git's spelling exactly, case included. Its path is a literal pathspec. A scope
    typed in another case than git's index or work tree spells it is refused, naming git's
    spelling, even where the filesystem ignores case.
    commit is HEAD. dirty is whether a tracked file under the scope has uncommitted changes.
    skipped counts the tracked files whose extension has no grammar, by extension ('' for none).
    It counts under 'symlink' each tracked symlink and each tracked file reached through one, and
    under 'submodule' each submodule. None of them is followed. warnings lists each file with
    syntax errors (its definitions are still kept), each tracked file missing from the working
    tree, and each file that cannot be stat'ed or read, with the reason.

Methods
-------
    NodeBase :
        the keys every node has.
    Node :
        one node of the tree, with file and lines on code nodes.
    Document :
        the output document.
    Lang :
        one grammar: its package, its extensions and its decorator wrapper.
    Definition :
        one tags.scm definition and its span.
    TreeError :
        a scope or file the outline cannot be built from.
    node :
        one node, with its keys in output order.
    repo_vars :
        the environment variables git lists as naming a repository, read from git once.
    git :
        a git command's output. It runs without the variables repo_vars lists and without any
        GIT_*_PATHSPECS, and raises with git's stderr or with the reason it cannot enter cwd.
    scope_of :
        the repository root, the scope inside it, the symbol part and whether the scope is a file,
        from the argument.
    tracked :
        every path git tracks under a path, once each and sorted, with its index mode.
    misspelled :
        the refusal naming how git's index spells a scope typed in another case, or ''.
    grammar_for :
        the LANGS row for a file's extension, or None.
    grammar :
        the parser and tags query of one LANGS row, loaded once.
    syntax_errors :
        the count of ERROR and MISSING nodes in a parse tree.
    definitions :
        the class, function and method definitions in one file's bytes, and its syntax errors.
    suffixed :
        sibling names made distinct for their ids.
    nest :
        definitions as nodes, each under its nearest enclosing definition.
    file_node :
        the node of one file with its definitions below it.
    dir_tree :
        folder nodes between the root and its file nodes, by path.
    pick_symbol :
        the definition node a dotted symbol names inside a file node.
    outline :
        the whole document for a scope argument.
    write :
        the document written to a file in one atomic step.
    report :
        the stderr summary of a document.
    main :
        parse the arguments, write the document, report on stderr.
'''

from __future__ import annotations

import argparse
import functools
import importlib
import json
import os
import secrets
import stat
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal, TypedDict

from tree_sitter import Language, Parser, Query, QueryCursor
from tree_sitter import Node as TSNode


# ── the data shape ────────────────────────────────────────────────────────────

Kind = Literal['root', 'dir', 'file', 'class', 'function', 'method']


class NodeBase(TypedDict):
    '''the keys every node has.'''
    id: str
    name: str
    kind: Kind
    children: list[Node]


class Node(NodeBase, total=False):
    '''one node of the tree as written, with file and lines only on code nodes.'''
    file: str
    lines: list[int]


class Document(TypedDict):
    '''the output document.'''
    schema: int
    scope: str
    commit: str
    dirty: bool
    skipped: dict[str, int]
    warnings: list[str]
    tree: Node


@dataclass(frozen=True)
class Lang:
    '''one grammar. Adding a language takes one row here and one pinned dependency above.'''
    module: str                  # the grammar package, such as tree_sitter_python
    extensions: tuple[str, ...]  # file suffixes it reads
    wrapper: str | None          # node type that wraps a definition with its decorators


@dataclass(frozen=True)
class Definition:
    '''one tags.scm definition and its span, decorators included.'''
    name: str
    kind: Literal['class', 'function', 'method']
    start_byte: int
    end_byte: int
    start_line: int
    end_line: int


LANGS: tuple[Lang, ...] = (
    Lang('tree_sitter_python', ('.py',), 'decorated_definition'),
    Lang('tree_sitter_javascript', ('.js', '.mjs', '.cjs'), None),
)
KEPT = {'definition.class': 'class', 'definition.function': 'function',
        'definition.method': 'method'}
UNFOLLOWED = {'120000': 'symlink', '160000': 'submodule'}  # index modes outline() never reads
WORDS = {'dir': ('folder', 'folders'), 'file': ('file', 'files'), 'class': ('class', 'classes'),
         'function': ('function', 'functions'), 'method': ('method', 'methods')}


class TreeError(Exception):
    '''a scope or file the outline cannot be built from. The message names it and the reason.'''


def node(id: str, name: str, kind: Kind, children: list[Node], file: str | None = None,
         lines: list[int] | None = None) -> Node:
    '''one node, keys in output order, file and lines only when given.'''
    out: Node = {'id': id, 'name': name, 'kind': kind}
    if file is not None:
        out['file'], out['lines'] = file, lines
    out['children'] = children
    return out


# ── repository and scope ──────────────────────────────────────────────────────

@functools.cache
def repo_vars() -> frozenset[str]:
    '''
    the environment variables that `git rev-parse --local-env-vars` lists (GIT_DIR,
    GIT_OBJECT_DIRECTORY and the rest that name a repository or a part of one), read once.
    Raises TreeError when git cannot be run.
    '''
    try:
        out = subprocess.run(['git', 'rev-parse', '--local-env-vars'], capture_output=True,
                             check=True)
    except OSError as e:
        raise TreeError(f'git rev-parse: {e.strerror}') from None
    except subprocess.CalledProcessError as e:
        raise TreeError(f"git rev-parse: {e.stderr.decode(errors='replace').strip()}") from None
    return frozenset(os.fsdecode(out.stdout).split())


def git(*args: str, cwd: Path) -> str:
    '''
    a git command's output as it printed it, decoded as filenames are (os.fsdecode), so a name
    that is not UTF-8 survives. Raises TreeError with git's stderr when the command fails, and
    with the reason when it cannot enter cwd. git runs without the variables of the caller's
    environment that repo_vars lists, so the repository is always the one git finds from cwd.
    It also runs without every GIT_ variable whose name ends in _PATHSPECS. With
    --literal-pathspecs, GIT_ICASE_PATHSPECS and GIT_GLOB_PATHSPECS make git fail, and
    GIT_LITERAL_PATHSPECS adds nothing.
    '''
    env = {k: v for k, v in os.environ.items()
           if k not in repo_vars() and not (k.startswith('GIT_') and k.endswith('_PATHSPECS'))}
    try:
        out = subprocess.run(['git', '--literal-pathspecs', *args], cwd=cwd, env=env,
                             capture_output=True, check=False)
    except OSError as e:
        raise TreeError(f'{cwd}: git {args[0]}: {e.strerror}') from None
    if out.returncode != 0:
        raise TreeError(f"{cwd}: git {args[0]}: {out.stderr.decode(errors='replace').strip()}")
    return os.fsdecode(out.stdout)


def scope_of(arg: str) -> tuple[Path, str, str, bool]:
    '''
    the repository root, the scope inside it, the symbol part and whether the scope is a file.

    Parameters
    ----------
    arg : str
        a folder, a file, or file:Symbol, relative to the working directory or absolute.

    Returns
    -------
    tuple
        the repository's top folder, the scope as a posix path relative to it ('.' for the
        top), the dotted symbol ('' when there is none), and True when the scope is a file,
        where a file is anything but a folder.

    Notes
    -----
    The argument splits at its last ':' only when the part before it is a regular file, so a
    path holding ':' still works. Each path is checked with one os.stat and never with a
    pathlib yes-or-no check, which from Python 3.14 returns False on any error, including a
    folder that cannot be entered. A path that is not there (ENOENT, ENOTDIR) is "no such file
    or folder". Any other error is its own reason. The stat says whether the path is a file or
    a folder. The path is resolved first and the repository is found from the resolved path.
    So a link in the argument is followed the way it was typed, and the repository is the one
    its target lies in. A scope matches git's spelling exactly, case included. The scope is the
    resolved path as typed, and it must lie under the work tree as git spells it. So a work
    tree folder typed in another case than git reports it, as a filesystem that ignores case
    allows, is not under the work tree. It raises TreeError when the path does not exist,
    cannot be stat'ed, sits in a folder git cannot enter, or lies outside a git repository. It
    also raises when the resolved path is not under the work tree git reports, and the message
    names both paths.
    '''
    path, symbol, mode = arg, '', None
    head, sep, tail = arg.rpartition(':')
    try:
        if sep and tail:
            try:
                st = os.stat(head)
            except (FileNotFoundError, NotADirectoryError):
                st = None
            if st is not None and stat.S_ISREG(st.st_mode):
                path, symbol, mode = head, tail, st.st_mode
        if mode is None:
            try:
                mode = os.stat(path).st_mode
            except (FileNotFoundError, NotADirectoryError):
                raise TreeError(f'{path}: no such file or folder') from None
        p      = Path(path).resolve(strict=True)
        folder = stat.S_ISDIR(mode)
    except OSError as e:
        raise TreeError(f'{e.filename or path}: {e.strerror}') from None
    top = Path(git('rev-parse', '--show-toplevel', cwd=p if folder else p.parent)
               .removesuffix('\n')).resolve()
    if not p.is_relative_to(top):
        raise TreeError(f'{path}: resolves to {p}, not under the work tree git reports, {top}')
    return top, p.relative_to(top).as_posix(), symbol, not folder


def tracked(repo: Path, rel: str) -> dict[str, str]:
    '''
    every repo-relative path git ls-files lists under rel, sorted, with its index mode. A path
    in a merge conflict is listed once per stage, and is kept once here.
    '''
    entries = (e.partition('\t') for e in git('ls-files', '-s', '-z', '--', rel, cwd=repo)
               .split('\0') if e)
    return dict(sorted((path, meta.split(' ', 1)[0]) for meta, _, path in entries))


def through_link(path: Path) -> bool:
    '''
    True when path goes through a symlink in any part of it, so that its real path differs.
    Precondition: the path is absolute and its repo part is resolved. Then only a symlink
    below the repository root can make the real path differ.
    '''
    return os.path.realpath(path) != str(path)


def misspelled(repo: Path, rel: str) -> str:
    '''
    the refusal for a scope git tracks nothing under because git's index spells it otherwise,
    or '' when there is no such spelling.

    Notes
    -----
    A spelling is the first parts of a tracked path in the whole index, as many as the scope
    has. It is git's spelling of the scope when all three of these hold. It is the same as the
    scope in NFC with its case folded. No part of it is a symlink (see through_link, the rule
    outline skips links by). And os.lstat finds it the same file as rel, which is resolved and
    so holds no symlink either. On a filesystem that keeps case apart, a name that differs only
    in case is named only when it is a hard link to rel. It is never named when it or a folder
    above it is a symlink, or when it is another file. rel itself is never a spelling, because
    git tracks nothing under it. This function only names the spelling in the refusal. It never
    decides what is outlined.
    '''
    def same(w: str) -> bool:
        try:
            return (not through_link(repo / w)
                    and os.path.samestat(os.lstat(repo / w), os.lstat(repo / rel)))
        except OSError:
            return False

    n, want = rel.count('/') + 1, unicodedata.normalize('NFC', rel).casefold()
    leads   = {'/'.join(f.split('/')[:n]) for f in git('ls-files', '-z', cwd=repo).split('\0')}
    ways    = sorted(w for w in leads
                     if unicodedata.normalize('NFC', w).casefold() == want and same(w))
    return (f"{rel}: git tracks it as {' and '.join(ways)}; scopes match git's "
            'spelling exactly') if ways else ''


# ── one file ──────────────────────────────────────────────────────────────────

def grammar_for(path: str) -> Lang | None:
    '''the LANGS row whose extensions hold the path's suffix, or None.'''
    return next((g for g in LANGS if PurePosixPath(path).suffix in g.extensions), None)


@functools.cache
def grammar(lang: Lang) -> tuple[Parser, Query]:
    '''the parser and the package's own queries/tags.scm query for one grammar.'''
    mod      = importlib.import_module(lang.module)
    language = Language(mod.language())
    tags     = (Path(mod.__file__).parent / 'queries' / 'tags.scm').read_text()
    return Parser(language), Query(language, tags)


def syntax_errors(root: TSNode) -> int:
    '''the count of ERROR and MISSING nodes. It walks only into subtrees that hold one.'''
    count, stack = 0, [root]
    while stack:
        n = stack.pop()
        count += n.is_error or n.is_missing
        if n.has_error:
            stack.extend(n.children)
    return count


def definitions(lang: Lang, source: bytes) -> tuple[list[Definition], int]:
    '''
    the class, function and method definitions in one file's bytes, and its syntax errors.

    Parameters
    ----------
    lang : Lang
        the file's grammar.
    source : bytes
        the file's content.

    Returns
    -------
    tuple
        the definitions sorted by start, outer before inner, and the count of syntax errors.

    Notes
    -----
    It keeps the definition.class, definition.function and definition.method captures and
    drops every other capture. A definition inside lang.wrapper (its decorators) takes the
    wrapper's span. A captured function that is the value or the right side of another capture
    is one definition with it, and only the outer one is kept. In `const g = function h() {}`,
    h is such a function. Two definitions can start at one byte, as x and f do in
    `var y = function f() {}.x = function () {}`, so the longer one sorts first.
    '''
    parser, query = grammar(lang)
    root          = parser.parse(source).root_node
    found: list[tuple[TSNode, Definition]] = []
    for _, caps in QueryCursor(query).matches(root):
        for cap, kind in KEPT.items():
            for n in caps.get(cap, []):
                span = n.parent if n.parent is not None and n.parent.type == lang.wrapper else n
                name = caps['name'][0].text.decode(errors='replace')
                found.append((n, Definition(name, kind, span.start_byte, span.end_byte,
                                            span.start_point[0] + 1, span.end_point[0] + 1)))
    captured = {n.id for n, _ in found}

    def is_value(n: TSNode) -> bool:
        p = n.parent
        return p is not None and p.id in captured and any(
            v is not None and v.id == n.id
            for v in (p.child_by_field_name('value'), p.child_by_field_name('right')))

    defs = sorted((d for n, d in found if not is_value(n)),
                  key=lambda d: (d.start_byte, -d.end_byte))
    return defs, syntax_errors(root)


def suffixed(names: list[str]) -> list[str]:
    '''each name, with '~2', '~3' added to its second and later repeats in order.'''
    seen: dict[str, int] = {}
    out = []
    for n in names:
        seen[n] = seen.get(n, 0) + 1
        out.append(n if seen[n] == 1 else f'{n}~{seen[n]}')
    return out


def nest(defs: list[Definition], file: str) -> list[Node]:
    '''
    definitions as nodes, each under its nearest enclosing definition by byte range.

    Parameters
    ----------
    defs : list of Definition
        one file's definitions, sorted by start, outer before inner.
    file : str
        the file's repo-relative path, which is also the parent id of its top-level nodes.

    Returns
    -------
    list of Node
        the top-level definitions, in source order, with their nested ones below.

    Notes
    -----
    A function whose nearest enclosing definition is a class is a method. A function nested
    in a function or a method stays a function.
    '''
    top: list = []
    stack: list = []
    for d in defs:
        while stack and stack[-1][0].end_byte < d.end_byte:
            stack.pop()
        under_class = bool(stack) and stack[-1][0].kind == 'class'
        entry = (d, 'method' if d.kind == 'function' and under_class else d.kind, [])
        (stack[-1][2] if stack else top).append(entry)
        stack.append(entry)

    def nodes(entries: list, parent: str) -> list[Node]:
        out = []
        for (d, kind, kids), seg in zip(entries, suffixed([e[0].name for e in entries])):
            nid = f'{parent}/{seg}'
            out.append(node(nid, d.name, kind, nodes(kids, nid), file,
                            [d.start_line, d.end_line]))
        return out

    return nodes(top, file)


def file_node(source: bytes, rel: str, lang: Lang) -> tuple[Node, int]:
    '''one file's node with its definitions below it, and its count of syntax errors.'''
    defs, errors = definitions(lang, source)
    last         = source.count(b'\n') + (not source.endswith(b'\n'))
    name         = PurePosixPath(rel).name
    return node(rel, name, 'file', nest(defs, rel), rel, [1, last]), errors


# ── the whole tree ────────────────────────────────────────────────────────────

def dir_tree(root: Node, files: list[Node]) -> None:
    '''folder nodes made between the root and each file node by path, every level sorted.'''
    dirs  = {root['id']: root}
    depth = 0 if root['id'] == '.' else len(PurePosixPath(root['id']).parts)
    for f in files:
        parts, parent = PurePosixPath(f['id']).parts, root
        for i in range(depth + 1, len(parts)):
            did = '/'.join(parts[:i])
            if did not in dirs:
                dirs[did] = node(did, parts[i - 1], 'dir', [])
                parent['children'].append(dirs[did])
            parent = dirs[did]
        parent['children'].append(f)
    for d in dirs.values():
        d['children'].sort(key=lambda c: c['name'])


def pick_symbol(file: Node, symbol: str) -> Node:
    '''the definition node a dotted symbol names under a file node. It raises TreeError listing
    the names at the level where the symbol stops matching.'''
    at = file
    for i, part in enumerate(symbol.split('.')):
        segs = [c['id'].rsplit('/', 1)[1] for c in at['children']]
        if part not in segs:
            where = '.'.join(symbol.split('.')[:i]) or 'the top level'
            raise TreeError(f"{file['file']}: no {symbol}; names under {where}: "
                            f"{', '.join(segs) or 'none'}")
        at = at['children'][segs.index(part)]
    return at


def outline(arg: str) -> Document:
    '''
    the whole document for a scope argument.

    Parameters
    ----------
    arg : str
        a folder, a file, or file:Symbol inside a git repository.

    Returns
    -------
    Document
        the outline of every tracked file under the scope that has a grammar.

    Notes
    -----
    It raises TreeError when the scope is refused (see scope_of), when git tracks nothing under
    the scope because its index spells it otherwise (see misspelled), when a file scope is not
    tracked, is a symlink or a submodule in git's index, has no grammar or cannot be read, when
    a folder scope has no tracked files, or when the symbol is not found. A path is never read
    through a symlink. One whose index mode is a symlink or a submodule, or whose real path
    differs from its path, is counted in skipped. A tracked file is stat'ed once without
    following a link. One that is gone or not a regular file is a missing warning, and one that
    cannot be stat'ed or read is a warning with the reason.
    '''
    repo, rel, symbol, is_file = scope_of(arg)
    entries = tracked(repo, rel)
    if not entries and (wrong := misspelled(repo, rel)):
        raise TreeError(wrong)
    skipped: dict[str, int] = {}
    warnings, files = [], []
    for f, mode in entries.items():
        path = repo / f
        lang = grammar_for(f)
        link = UNFOLLOWED.get(mode) or ('symlink' if through_link(path) else '')
        if link or lang is None:
            key = link or PurePosixPath(f).suffix
            skipped[key] = skipped.get(key, 0) + 1
            continue
        try:
            source = path.read_bytes() if stat.S_ISREG(path.lstat().st_mode) else None
        except (FileNotFoundError, NotADirectoryError):
            source = None
        except OSError as e:
            warnings.append(f'{f}: cannot be read: {e.strerror}')
            continue
        if source is None:
            warnings.append(f'{f}: tracked but missing from the working tree')
            continue
        n, errors = file_node(source, f, lang)
        if errors:
            warnings.append(f"{f}: {errors} syntax error{'s' if errors > 1 else ''}")
        files.append(n)
    if is_file:
        held = UNFOLLOWED.get(entries.get(rel, ''))
        if held:
            raise TreeError(f"{rel}: a {held} in git's index, and those are never followed")
        if not files:
            raise TreeError(warnings[0] if warnings else
                            f'{rel}: not tracked by git, or its extension has no grammar')
        tree: Node = dict(pick_symbol(files[0], symbol) if symbol else files[0], kind='root')
    elif not entries:
        raise TreeError(f'no tracked files under {rel}')
    else:
        tree = node(rel, repo.name if rel == '.' else PurePosixPath(rel).name, 'root', [])
        dir_tree(tree, files)
    return {'schema': 1, 'scope': f'{rel}:{symbol}' if symbol else rel,
            'commit': git('rev-parse', 'HEAD', cwd=repo).removesuffix('\n'),
            'dirty': bool(git('status', '--porcelain', '--untracked-files=no', '--', rel,
                              cwd=repo)),
            'skipped': dict(sorted(skipped.items())), 'warnings': warnings, 'tree': tree}


# ── output ────────────────────────────────────────────────────────────────────

def write(out: Path, text: str) -> None:
    '''
    the document written to a file in one atomic step.

    Parameters
    ----------
    out : Path
        the file to write. An existing file or link there is replaced, never written through.
    text : str
        the document.

    Notes
    -----
    It writes a temp file in the same folder, then os.replace moves it over out, so a reader
    sees the old file or the new one and never half of one. The temp file is created with mode
    0666 less the umask, the mode a plain open() gives a new file. The temp file is removed on
    any failure. It raises TreeError when the folder or the file cannot be written.
    '''
    tmp = out.parent / f'.{out.name}.{secrets.token_hex(4)}.tmp'
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    except OSError as e:
        raise TreeError(f'{out}: {e.strerror}') from e
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text)
        os.replace(tmp, out)
    except OSError as e:
        raise TreeError(f'{out}: {e.strerror}') from e
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def report(doc: Document) -> None:
    '''the node counts below the root, the skipped counts and the warnings, on stderr. The skipped
    counts list the extensions first, then the symlinks and submodules that were not followed.'''
    counts = dict.fromkeys(WORDS, 0)
    stack  = list(doc['tree']['children'])
    while stack:
        n = stack.pop()
        counts[n['kind']] += 1
        stack.extend(n['children'])
    print('tree: ' + ', '.join(f'{c} {WORDS[k][c != 1]}' for k, c in counts.items()),
          file=sys.stderr)
    for label, links in (('skipped with no grammar', False), ('skipped, not followed', True)):
        counted = [f"{k or 'no extension'} {c}" for k, c in doc['skipped'].items()
                   if (k in UNFOLLOWED.values()) == links]
        if counted:
            print(f'tree: {label}: ' + ', '.join(counted), file=sys.stderr)
    for w in doc['warnings']:
        print(f'tree: warning: {w}', file=sys.stderr)


def main(argv: list[str]) -> int:
    '''parse the arguments, write the document and report on stderr. Return 2 for a refused scope
    or an -o file it cannot write.'''
    ap = argparse.ArgumentParser(prog='tree.py', description='the outline of one scope of a git '
                                 'repository, as one JSON tree')
    ap.add_argument('scope', help='folder, file, or file:Symbol inside a git repository')
    ap.add_argument('-o', '--out', type=Path, default=None, help='write here; default stdout')
    args = ap.parse_args(argv)
    try:
        doc  = outline(args.scope)
        text = json.dumps(doc, indent=1) + '\n'
        if args.out:
            write(args.out, text)
    except TreeError as e:
        print(f'tree: {e}', file=sys.stderr)
        return 2
    if not args.out:
        sys.stdout.write(text)
    report(doc)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
