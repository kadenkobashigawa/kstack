#!/usr/bin/env python3
'''
where.py finds W, the folder that holds one scope's map files and saved cards, makes it, and
keeps it out of git. It needs only the Python standard library, so it runs before uv is
installed and from the scripts that Cowork copies to the Mac.

Commands
--------
    where.py SCOPE [--files]
                         SCOPE is a folder, a file, or file:Symbol, relative to the working
                         folder or absolute. The command makes W, prints one JSON line (see
                         Output) and exits 0. A second run changes nothing. It exits 2 with
                         `where:` and the reason on one stderr line, and prints nothing on stdout,
                         when the scope has no W. With --files it also lists the files an outline
                         of the scope reads.

Output
------
    {"w": str, "top": str, "scope": str, "symbol": str, "is_file": bool, "git": bool,
     "url": str, "files"?: [str]}

    w is <top>/.study/<name>, where name is w_name(scope, symbol). top is the repository's work
    tree when a .git file or folder lies at or above the scope, and otherwise the scope's own
    folder: the scope itself, or the folder that holds a file scope. scope is the path relative
    to top, '.' for top itself. git says which of the two top is. url is the file URL of
    <w>/map.html. files are absolute and sorted, each a regular file that exists (never a
    folder, a symlink or a fifo), and none lies under a .study folder. A file scope lists
    itself alone, even when git ignores it, because the scope names it.

Rules
-----
    Inside git, top comes from git, and any git failure is a refusal: git missing, a broken
    .git, or a repository git will not open. Outside git, git never runs. W is never in the
    home folder itself and never at the filesystem root. A scope inside a .study folder is
    refused, and so is a scope typed in another case or Unicode form than the disk spells it,
    naming the disk's spelling.

    W is kept out of git by <top>/.study/.gitignore, which holds `*` and so ignores everything
    in .study, itself included. git reads it in the main checkout and in every linked worktree,
    and no path into .git is needed. A .study/.gitignore that is already there is left as it
    is. In git, a .study that git tracks, or a W that git does not ignore, is refused.

    Cowork copies the scripts to <folder>/.study/.skill/scripts on the Mac. When where.py runs
    from a folder so placed, it also writes that .study's .gitignore, so the copy stays out of
    git when the scope is a subfolder and its own .study lies deeper.

Methods
-------
    ScopeError :
        a scope that has no W. tree.py raises it as TreeError.
    Where :
        one resolved scope and its W.
    repo_vars :
        the environment variables git lists as naming a repository, read from git once.
    git :
        a git command's output, run without those variables and without any GIT_*_PATHSPECS.
    split_scope :
        the path, the symbol, the resolved path and whether it is a folder, from the argument.
    work_tree :
        the repository's top and the scope relative to it, from git.
    git_dir_above :
        the nearest folder at or above a folder that holds a .git entry, or None.
    disk_spelling :
        a path spelled as the disk spells each of its parts, or '' when it already is.
    w_name :
        the one folder name under .study for a scope and symbol.
    locate :
        the Where record of an argument. It writes nothing.
    folder_at :
        a folder made unless it is there, and refused unless it is a real folder.
    ignore_study :
        a .study folder's .gitignore holding `*`, written unless one is there.
    ensure :
        .study, its .gitignore and W made, and W checked to be ignored.
    ensure_copy :
        the .gitignore of the .study folder that holds where.py, when Cowork copied it there.
    regular :
        whether a path is a regular file, not through a link.
    note_files :
        the files under the scope that an outline reads.
    main :
        parse the arguments, make W and print the JSON line.
'''

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import stat
import subprocess
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

STUDY  = '.study'
IGNORE = b'*\n'


class ScopeError(Exception):
    '''a scope that has no W. The message names the path and the reason.'''


@dataclass(frozen=True)
class Where:
    '''one resolved scope and its W. See Output in the module text.'''
    w: Path
    top: Path
    scope: str
    symbol: str
    is_file: bool
    git: bool
    url: str


@functools.cache
def repo_vars() -> frozenset[str]:
    '''
    the environment variables that `git rev-parse --local-env-vars` lists (GIT_DIR,
    GIT_OBJECT_DIRECTORY and the rest that name a repository or a part of one), read once.
    Raises ScopeError when git cannot be run.
    '''
    try:
        out = subprocess.run(['git', 'rev-parse', '--local-env-vars'], capture_output=True,
                             check=True)
    except OSError as e:
        raise ScopeError(f'git rev-parse: {e.strerror}') from None
    except subprocess.CalledProcessError as e:
        raise ScopeError(f"git rev-parse: {e.stderr.decode(errors='replace').strip()}") from None
    return frozenset(os.fsdecode(out.stdout).split())


def git(*args: str, cwd: Path, literal: bool = True) -> str:
    '''
    a git command's output as it printed it, decoded as filenames are (os.fsdecode), so a name
    that is not UTF-8 survives. Raises ScopeError with git's stderr when the command fails, and
    with the reason when it cannot enter cwd. git runs without the variables of the caller's
    environment that repo_vars lists, so the repository is always the one git finds from cwd.
    It also runs without every GIT_ variable whose name ends in _PATHSPECS. With
    --literal-pathspecs, GIT_ICASE_PATHSPECS and GIT_GLOB_PATHSPECS make git fail, and
    GIT_LITERAL_PATHSPECS adds nothing. literal=False leaves --literal-pathspecs out, for a
    command that refuses it, as check-ignore does.
    '''
    env = {k: v for k, v in os.environ.items()
           if k not in repo_vars() and not (k.startswith('GIT_') and k.endswith('_PATHSPECS'))}
    try:
        out = subprocess.run(['git', *(['--literal-pathspecs'] if literal else []), *args],
                             cwd=cwd, env=env, capture_output=True, check=False)
    except OSError as e:
        raise ScopeError(f'{cwd}: git {args[0]}: {e.strerror}') from None
    if out.returncode != 0:
        raise ScopeError(f"{cwd}: git {args[0]}: {out.stderr.decode(errors='replace').strip()}")
    return os.fsdecode(out.stdout)


def split_scope(arg: str) -> tuple[str, str, Path, bool]:
    '''
    the path as typed, the dotted symbol ('' when there is none), the resolved path, and True
    when the path is a folder.

    Notes
    -----
    The argument splits at its last ':' only when the part before it is a regular file, so a
    path holding ':' still works. Each path is checked with one os.stat and never with a
    pathlib yes-or-no check, which from Python 3.14 returns False on any error, including a
    folder that cannot be entered. A path that is not there (ENOENT, ENOTDIR) is "no such file
    or folder". Any other error is its own reason. The path is resolved with strict=True, so a
    link in it is followed the way it was typed and a missing last part raises.
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
                raise ScopeError(f'{path}: no such file or folder') from None
        p = Path(path).resolve(strict=True)
    except OSError as e:
        raise ScopeError(f'{e.filename or path}: {e.strerror}') from None
    return path, symbol, p, stat.S_ISDIR(mode)


def work_tree(path: str, p: Path, folder: bool) -> tuple[Path, str]:
    '''
    the top folder of the repository git finds from p, resolved, and p as a posix path relative
    to it ('.' for the top). Raises ScopeError when git fails, and when p is not under the work
    tree git reports, naming both paths. A work tree folder typed in another case than git
    reports it, as a filesystem that ignores case allows, is not under the work tree.
    '''
    top = Path(git('rev-parse', '--show-toplevel', cwd=p if folder else p.parent)
               .removesuffix('\n')).resolve()
    if not p.is_relative_to(top):
        raise ScopeError(f'{path}: resolves to {p}, not under the work tree git reports, {top}')
    return top, p.relative_to(top).as_posix()


def git_dir_above(folder: Path) -> Path | None:
    '''
    the nearest folder at or above folder that holds a .git entry, file or folder, or None. It
    uses os.lstat only and never runs git. git exits 128 both outside a repository and for a
    broken .git, so this, and never a git error, decides whether a scope is inside git.
    Raises ScopeError when a folder on the way cannot be read.
    '''
    for d in (folder, *folder.parents):
        try:
            os.lstat(d / '.git')
            return d
        except (FileNotFoundError, NotADirectoryError):
            continue
        except OSError as e:
            raise ScopeError(f'{d}: {e.strerror}; cannot tell whether it is in git') from None
    return None


def disk_spelling(p: Path) -> str:
    '''
    p with each part spelled as os.listdir spells it, or '' when every part already is. When a
    part is missing from its folder's listing, it is matched to a listed name that equals it in
    NFC with case folded. If os.path.samefile finds both are the same entry, the part takes the
    listed name. A folder that cannot be listed keeps the part as typed. On the case-insensitive
    disk of a Mac, p resolved keeps the case typed, so without this one folder would have one W
    per spelling.
    '''
    cur, wrong = Path(p.anchor), False
    for part in p.parts[1:]:
        try:
            names = os.listdir(cur)
        except OSError:
            names = [part]
        if part not in names:
            want = unicodedata.normalize('NFC', part).casefold()
            for n in names:
                if (unicodedata.normalize('NFC', n).casefold() == want
                        and os.path.samefile(cur / n, cur / part)):
                    part, wrong = n, True
                    break
        cur = cur / part
    return str(cur) if wrong else ''


def w_name(rel: str, symbol: str) -> str:
    '''
    the one folder name under .study for a scope relative to top and a symbol. '%' becomes %25,
    '/' %2F and '@' %40, a leading '.' becomes %2E, and the symbol joins after '@'. So the top
    '.' is %2E. The mapping is one-to-one, and a name never starts with '.' (so it is never
    .gitignore or .skill) and never holds '/' (so no W lies inside another W, and no W meets
    another W's tree.json). A name over 200 bytes keeps its first 150 bytes, then '~' and 12 hex
    digits of the whole name's sha256, so it stays under the 255-byte limit of a file name.
    '''
    def enc(s: str) -> str:
        return s.replace('%', '%25').replace('/', '%2F').replace('@', '%40')

    name = enc(rel)
    if name.startswith('.'):
        name = '%2E' + name[1:]
    if symbol:
        name += '@' + enc(symbol)
    raw = name.encode()
    if len(raw) > 200:
        name = (raw[:150].decode(errors='ignore') + '~'
                + hashlib.sha256(raw).hexdigest()[:12])
    return name


def locate(arg: str, home: Path | None = None) -> Where:
    '''
    the Where record of a scope argument. It writes nothing.

    Parameters
    ----------
    arg : str
        a folder, a file, or file:Symbol, relative to the working folder or absolute.
    home : Path, optional
        the home folder, which W's top may never be. The default is Path.home(), on the
        machine that runs the script.

    Notes
    -----
    It raises ScopeError, naming the path and the reason, for a missing scope (see
    split_scope), a scope the disk spells otherwise, a scope inside a .study folder, a git
    failure inside git (see git_dir_above), and a top that is the home folder or the
    filesystem root.
    '''
    home = (home or Path.home()).resolve()
    path, symbol, p, folder = split_scope(arg)
    if spelled := disk_spelling(p):
        raise ScopeError(f'{path}: the disk spells it {spelled}; type it that way')
    if STUDY in p.parts:
        raise ScopeError(f'{path}: lies inside a {STUDY} folder, which holds maps and not notes')
    base = p if folder else p.parent
    in_git = git_dir_above(base) is not None
    if in_git:
        top, rel = work_tree(path, p, folder)
    else:
        top, rel = base, '.' if folder else p.name
    if top == home:
        raise ScopeError(f'{path}: W would be in the home folder {top}; map a folder inside it')
    if top == Path(top.anchor):
        raise ScopeError(f'{path}: W would be at the filesystem root {top}; map a folder '
                         'inside it')
    w = top / STUDY / w_name(rel, symbol)
    return Where(w, top, rel, symbol, not folder, in_git, (w / 'map.html').as_uri())


def folder_at(p: Path) -> None:
    '''make p unless it is there, and raise ScopeError unless it is a real folder, not a link.'''
    try:
        os.mkdir(p)
    except FileExistsError:
        pass
    if not stat.S_ISDIR(os.lstat(p).st_mode):
        raise ScopeError(f'{p}: not a folder (a symlink or a file), so W cannot lie in it')


def ignore_study(study: Path) -> None:
    '''write study/.gitignore holding `*` unless a file of that name is there.'''
    try:
        fd = os.open(study / '.gitignore', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return
    with os.fdopen(fd, 'wb') as fh:
        fh.write(IGNORE)


def ensure(where: Where) -> None:
    '''
    make <top>/.study, write .study/.gitignore holding `*` unless one is there, then make W.
    In git, first refuse a .study that git tracks, and after the .gitignore refuse a W that
    `git check-ignore` does not report as ignored. A .study or W that is a symlink is refused,
    so W cannot be sent outside top. Raises ScopeError with the reason.
    '''
    study = where.top / STUDY
    try:
        if where.git and (held := git('ls-files', '-z', '--', STUDY, cwd=where.top)):
            raise ScopeError(f"{study}: git tracks {held.split(chr(0))[0]}; W would be tracked")
        folder_at(study)
        ignore_study(study)
        if where.git:
            probe = (where.w / 'map.html').relative_to(where.top).as_posix()
            try:
                git('check-ignore', '-q', '--', probe, cwd=where.top, literal=False)
            except ScopeError as e:
                if not str(e).endswith('check-ignore: '):
                    raise       # git failed, and said why; -q leaves stderr empty on "no"
                raise ScopeError(f'{where.top / probe}: git does not report it as ignored; '
                                 f'{study / ".gitignore"} must hold `*`') from None
        folder_at(where.w)
    except OSError as e:
        raise ScopeError(f'{e.filename or study}: {e.strerror}') from None


def ensure_copy(script: Path) -> None:
    '''
    write the .gitignore of the .study folder above script, when script lies in
    <folder>/.study/.skill/scripts as Cowork copies it. Elsewhere it writes nothing. It runs
    before locate, so a refused scope run from the copy still writes the copy's .gitignore.
    Raises ScopeError when the file cannot be written.
    '''
    scripts = script.resolve().parent
    if (scripts.name, scripts.parent.name, scripts.parent.parent.name) != ('scripts', '.skill',
                                                                            STUDY):
        return
    try:
        ignore_study(scripts.parent.parent)
    except OSError as e:
        raise ScopeError(f'{e.filename or scripts.parent.parent}: {e.strerror}') from None


def regular(p: Path) -> bool:
    '''True when p is a regular file, checked with os.lstat so a link is never one.'''
    try:
        return stat.S_ISREG(os.lstat(p).st_mode)
    except OSError:
        return False


def note_files(where: Where) -> list[str]:
    '''
    the absolute paths of the files under the scope that an outline reads, sorted, each a
    regular file that exists. In git they are the files git lists as tracked, or untracked and
    not ignored, so a folder git lists (a nested or embedded repository), a tracked file that
    is gone, and a symlink are left out. Outside git they are the regular files os.walk finds,
    never through a link and never named or under .git, a folder or a worktree's file, at any
    depth. A nested repository's working files stay: outside git no outer repository decides
    what the folder holds, so every file in it but git's own is a note. None lies in a .study
    folder. A file scope lists itself alone, even when git ignores it, because the scope names
    it.
    '''
    if where.is_file:
        listed = [where.top / where.scope]
    elif where.git:
        listed = [where.top / f for f in git('ls-files', '--cached', '--others',
                                             '--exclude-standard', '-z', '--', where.scope,
                                             cwd=where.top).split('\0')
                  if f and STUDY not in f.split('/')]
    else:
        listed = []
        for d, dirs, names in os.walk(where.top):
            dirs[:] = [n for n in dirs if n not in (STUDY, '.git')]
            listed += [Path(d) / n for n in names if n != '.git']
    return sorted({str(p) for p in listed if regular(p)})


def main(argv: list[str], home: Path | None = None) -> int:
    '''parse the arguments, make W and print one JSON line. Return 2 for a refused scope.'''
    ap = argparse.ArgumentParser(prog='where.py', description="W, the folder for one scope's "
                                 'map and cards, made and kept out of git')
    ap.add_argument('scope', help='folder, file, or file:Symbol')
    ap.add_argument('--files', action='store_true', help='also list the files to outline')
    args = ap.parse_args(argv)
    try:
        ensure_copy(Path(__file__))
        where = locate(args.scope, home)
        ensure(where)
        record = {k: str(v) if isinstance(v, Path) else v for k, v in asdict(where).items()}
        if args.files:
            record['files'] = note_files(where)
    except ScopeError as e:
        print('where: ' + str(e).replace('\n', ' '), file=sys.stderr)
        return 2
    print(json.dumps(record))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
