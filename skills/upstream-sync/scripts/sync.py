#!/usr/bin/env python3
'''
sync — the deterministic half of upstream-sync: the pins of the sources kstack imports, every
citation kstack makes into them, each citation run against the imported copy and found again at
the newest head, and the suggested refresh. It writes only inside the run folder it is given, and
refuses one inside the repository.

Commands
--------
    check                         offline: upstream/sources.json reads, NOTICE and
                                  upstream/README.md name each row's short commit, every citation
                                  parses and holds against upstream/, and each declared copy equals
                                  its source; exit 1 on a finding
    scan <run>                    refused on a tree whose tracked files differ from HEAD, the commit
                                  remap.patch applies to; check, then a blobless clone of each
                                  repository, fetched again when the run folder holds it, each pin
                                  proved, every change read and each citation found at the head; writes
                                  <run>/ledger.json and <run>/briefs/<n>.md, whole kstack files
                                  packed up to `CAP` bytes a brief
    settle <run>                  refused, creating nothing, on a run folder with no ledger or a
                                  verdict line it cannot read or whose values are not of their
                                  field's type or values; <run>/verdicts.jsonl rechecked
                                  against the head, a suggestion failing whose path is outside
                                  the clone's import path, under another label, or, for a
                                  partial row, not a file reimport.md copies; writes
                                  <run>/remap.patch, from the verdicts and from each moved
                                  citation in the ledger, editing only citations in rows that
                                  move, <run>/sources.next.json, where a row moves to its head
                                  unless its pin did not prove, its head was not fetched, or a
                                  citation into it is blocked, and <run>/reimport.md, and prints
                                  the count per outcome, why each row held at its pin stays
                                  there, and the edits left out because their row holds

    Each command takes `--repo <path>` to read another kstack checkout than the one this script
    sits in.

Data shape
----------
upstream/sources.json holds the import rows and the declared copies. A file under upstream/
belongs to the row whose folder is its longest match. One `Ledger`, saved as <run>/ledger.json, is
keyed by upstream file, `<label>:<path>` at the pin, where the label is the first folder under
upstream/ and the path is inside it, as a citation writes them. Each `UpstreamFile` holds its
import row, its rename or deletion state, the commits that touched it with their full messages,
its pin-to-head line map, and the ids of the citations into it. The ledger holds each
`Citation`, one per path-and-lines pair, by id, its baseline `Check` in `Ledger.baseline` and its
head `Remap` in `Ledger.remaps`, both by the same id. A brief, a group of whole
kstack files packed up to `CAP` bytes, is a projection of the ledger, never a second record.

Methods
-------
    git :
        a git command's output, or '' when it fails.
    use_repo :
        point the module at the kstack checkout named by `--repo`.
    run_dir, clone_dir :
        the run folder, created unless asked not to, refused inside the repository, and one clone
        inside it.
    tracked_text :
        every markdown file git tracks outside upstream/.
    save, load :
        one run file written as JSON, and read back.
    read_sources :
        upstream/sources.json read and checked for shape.
    check_prose :
        each row whose short commit NOTICE or upstream/README.md leaves out.
    check_copies :
        each file where a declared copy differs from its source.
    flatten, find_parens, split_pairs, parse_lines, quote_before, deviation_after :
        the parts of a citation found in a text.
    parse_text, all_citations :
        every citation in one text, and in every tracked text.
    normalize, fragments, locate_quote :
        a passage compared, and a quote found in a text.
    run_citation, resolve, baseline, check_all :
        one citation run against one text, and against its file inside one copy, every citation
        against upstream/, and every finding.
    clone :
        a blobless clone, fetched again when it exists, with the import paths checked out at the
        head.
    blob_ids, local_blob_ids, prove_pin :
        the pin proved by blob ids.
    name_status, commits :
        the renames, deletions and commits from pin to head, each in one git call.
    line_map, anchor, score, search_row, fuzzy, remap :
        one citation's passage found at the head.
    diff_copy, additions :
        the copies at the head, and the files the head adds.
    build_ledger :
        the ledger.
    section_for, brief_text, pack :
        one kstack file's part of a brief, naming the pin and head copies of each file it cites,
        one brief, and the kstack files packed into briefs.
    read_verdicts, copied, recheck :
        the agents' verdicts, whether the re-import copies a file of a row, and each suggested
        citation run by `resolve` against its row's head copy.
    pin_holds :
        each row that stays at its pin, because its pin did not prove, its head was not fetched,
        or a citation into it is blocked, and why.
    patch_edits, remap_patch :
        the edits remap.patch makes, with those in a held row left out, and the patch.
    next_sources, reimport_plan, counts :
        what settle writes and prints.
    cmd_check, cmd_scan, cmd_settle :
        the commands.
    main :
        dispatch on the command named first.
'''

from __future__ import annotations

import bisect
import dataclasses
import difflib
import functools
import json
import re
import subprocess
import sys
import types
import typing
from pathlib import Path
from typing import Iterator, Literal



REPO     = Path(__file__).resolve().parents[3]
UPSTREAM = REPO / 'upstream'
SOURCES  = UPSTREAM / 'sources.json'
README   = UPSTREAM / 'README.md'
NOTICE   = REPO / 'NOTICE'
TAG      = re.compile(r'\*\(kstack(?:, the translation)?: ')
WEIGHTS  = {'quote': 50, 'prefix': 20, 'suffix': 20, 'position': 2}   # Hypothesis match-quote
CONTEXT  = 32      # characters of pin text kept on each side of a quote
CAP      = 100_000 # bytes of text a brief holds before the next kstack file starts another
REWORDED = 0.6     # a similarity at or above it is reworded, below it gone; tune on real drift
PASS     = {'ok', 'loose', 'paraphrase'}   # the statuses that hold
CURLY    = str.maketrans({'“': '"', '”': '"', '„': '"', '‘': "'", '’': "'"})


# ── types ─────────────────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class Import:
    '''one row of upstream/sources.json: a folder under upstream/ copied from one repository.'''
    folder  : str            # under upstream/: `pstack`, `pstack/skills/maintain-…-skill`
    url     : str
    path    : str            # the folder inside the repository the copy mirrors; '' for the root
    commit  : str            # the pin, 40 hex
    date    : str
    partial : bool = False   # only the files present were imported, and only they are proved

    def label(self) -> str:
        '''the folder's first part, which a citation into it opens with.'''
        return self.folder.split('/')[0]

    def repo_path(self, path: str) -> str:
        '''the repository path of a file at `upstream/<label>/<path>`.'''
        inside = f'{self.label()}/{path}'[len(self.folder):].lstrip('/')
        return f'{self.path}/{inside}'.strip('/') if self.path else inside

    def local_path(self, repo_path: str) -> str:
        '''the path under `upstream/<label>/` of a repository path inside this row.'''
        inside = repo_path[len(self.path):].lstrip('/') if self.path else repo_path
        return f'{self.folder}/{inside}'.strip('/')[len(self.label()):].lstrip('/')


@dataclasses.dataclass
class Sources:
    '''upstream/sources.json read: its rows, and each kstack folder copied from upstream/.'''
    imports : list[Import]
    copies  : dict[str, str]   # `skills/unslop` to `pstack/skills/unslop`

    def owner(self, label: str, path: str) -> Import | None:
        '''the row whose folder is the longest match for `upstream/<label>/<path>`, or None.'''
        full = f'{label}/{path}'
        rows = [r for r in self.imports if full == r.folder or full.startswith(r.folder + '/')]
        return max(rows, key=lambda r: len(r.folder)) if rows else None


@dataclasses.dataclass(frozen=True)
class Span:
    '''one cited run of lines, 1-based and inclusive: `l. 7` is (7, 7), `ll. 13, 16` two spans.'''
    first : int
    last  : int


@dataclasses.dataclass
class Citation:
    '''one path-and-lines pair in a kstack citation; a `;`-separated parenthesis gives several.'''
    id        : str                # `<kfile>:<kline>:<n>`, n the pair's place on its line
    kfile     : str
    kline     : int
    label     : str
    path      : str                # inside the source, as written in backticks
    spans     : tuple[Span, ...]
    raw       : str                # the pair as written, flattened
    trailing  : str = ''           # prose after the line numbers, kept for a suggested edit
    quote     : str | None = None  # the quote that ends right before the parenthesis
    deviation : str | None = None  # the nearest kstack tag after it, a hint for kept


Status = Literal['ok', 'loose', 'paraphrase', 'quote-elsewhere', 'quote-missing',
                 'out-of-range', 'file-missing', 'unparsed']


@dataclasses.dataclass
class Check:
    '''a citation run against one text: `upstream/` for the baseline, a head for a recheck.'''
    id      : str
    status  : Status
    found   : tuple[Span, ...] = ()   # where the quote sits when not at the cited lines
    against : str = 'upstream/'


@dataclasses.dataclass
class Commit:
    '''one upstream commit, with its whole message, subject and body, as the briefs quote it.'''
    sha     : str
    date    : str
    message : str


FileState = Literal['unchanged', 'changed', 'renamed', 'removed']


@dataclasses.dataclass
class UpstreamFile:
    '''one cited or copied upstream file, pin to head; the ledger's key and organizing record.'''
    key       : str                 # `<label>:<path>` at the pin
    folder    : str                 # its import row
    head_path : str | None          # None once removed
    state     : FileState
    why       : set[str]            # `cited`, `copied`, or both
    commits   : list[Commit] = dataclasses.field(default_factory=list)   # oldest first
    lines     : dict[int, int | None] = dataclasses.field(default_factory=dict)  # pin to head
    citations : list[str] = dataclasses.field(default_factory=list)      # ids


@dataclasses.dataclass(frozen=True)
class Anchor:
    '''
    a cited passage as a W3C Text Quote Selector: the quote, or the cited lines' pin text when
    there is none, with up to `CONTEXT` characters of pin text on each side.
    '''
    exact  : str
    prefix : str
    suffix : str


RemapState = Literal['in sync', 'moved', 'edited', 'gone', 'stale', 'blocked']
Found      = Literal['lines', 'quote', 'quote-elsewhere', 'fuzzy', 'none']
DECIDED    = ('in sync', 'moved', 'blocked')   # the states settle reads from the ledger alone


@dataclasses.dataclass
class Remap:
    '''
    where a citation's passage sits at the head: `moved` is the same text at other lines or in
    another file, where the citation rewritten to them holds, `edited` cited lines most of which
    still map, a quote that still holds in cited lines that changed around it, a quote found
    whose shifted lines do not hold it whole, or a fuzzy match at or above `REWORDED`, `stale` a
    failed baseline, and `blocked` a pin not proved or a citation not parsed. `in sync`, `moved`
    and `blocked` are the script's to decide, and no brief holds them.
    '''
    id     : str
    state  : RemapState
    found  : Found              # which step of `remap` found it
    path   : str | None
    spans  : tuple[Span, ...]
    old    : str                # the cited text at the pin
    new    : str                # the text at `spans` at the head
    score  : float              # 1.0 for the same text at mapped lines


@dataclasses.dataclass
class Copy:
    '''one declared verbatim copy, each differing file marked against the pin and the head.'''
    kfolder : str
    source  : str
    at_pin  : dict[str, str]    # file to `differs`, `only-kstack` or `only-upstream`
    at_head : dict[str, str]
    diff    : str               # the run file holding the unified diff against the head


@dataclasses.dataclass
class Addition:
    '''one file the head adds under an import, with the commits that added and changed it.'''
    folder  : str
    path    : str
    skill   : bool              # a SKILL.md, which names a new upstream skill
    commits : list[Commit]
    renamed : str | None = None # for a partial row, the pin path of a file imported now


@dataclasses.dataclass
class Ledger:
    '''the run's one record, keyed by upstream file; every other run file is read from it.'''
    scanned   : str                          # the kstack commit remap.patch applies to
    sources   : Sources
    heads     : dict[str, str]               # repository URL to head commit
    proof     : dict[str, list[str]]         # row folder to files that failed; empty is proved
    files     : dict[str, UpstreamFile]      # by `<label>:<path>` at the pin
    citations : dict[str, Citation]
    baseline  : dict[str, Check]             # by citation id
    remaps    : dict[str, Remap]             # by citation id
    copies    : list[Copy]
    added     : list[Addition]
    removed   : list[str]                    # every imported file the head deletes
    unparsed  : list[tuple[str, int, str]]   # file, line, text

    def by_kfile(self) -> dict[str, list[str]]:
        '''the citation ids grouped by kstack file, in path order, as the briefs pack them.'''
        out: dict[str, list[str]] = {}
        for c in sorted(self.citations.values(), key=lambda c: (c.kfile, c.kline, c.id)):
            out.setdefault(c.kfile, []).append(c.id)
        return out


Sort    = Literal['no effect', 'pointer drift', 'changed on purpose', 'no stated reason']
Outcome = Literal['in sync', 'updated', 'diverged', 'updated and diverged', 'blocked']


@dataclasses.dataclass
class Verdict:
    '''one line of <run>/verdicts.jsonl: one agent's judgment of one citation.'''
    id       : str
    sort     : Sort
    outcome  : Outcome
    commit   : str | None      # the evidence for a change on purpose
    old      : str
    new      : str
    citation : str | None      # the suggested parenthesis, rechecked by settle
    edit     : str | None      # the suggested rule wording, which stays prose in the reply
    kept     : bool = False    # the agent's judgment that a kstack tag marks this rule its own


# ── where things live ─────────────────────────────────────────────────────────

def git(*args: str, cwd: Path | None = None, strip: bool = True) -> str:
    '''a git command's output, stripped unless `strip` is off, or '' when it fails.'''
    out = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if out.returncode:
        return ''
    return out.stdout.strip() if strip else out.stdout


def use_repo(path: Path) -> None:
    '''point every path this module reads at another kstack checkout, for `--repo`.'''
    global REPO, UPSTREAM, SOURCES, README, NOTICE
    REPO = path.resolve()
    UPSTREAM, NOTICE = REPO / 'upstream', REPO / 'NOTICE'
    SOURCES, README = UPSTREAM / 'sources.json', UPSTREAM / 'README.md'


def run_dir(arg: str, create: bool = True) -> Path:
    '''
    the run folder named on the command line, created unless `create` is off, and refused inside
    the repository.
    '''
    run = Path(arg).expanduser().resolve()
    if run == REPO or REPO in run.parents:
        sys.exit(f'sync: the run folder {run} is inside the repository {REPO}; use mktemp -d')
    if create:
        run.mkdir(parents=True, exist_ok=True)
    return run


def clone_dir(run: Path, url: str) -> Path:
    '''where one repository's clone sits inside the run folder.'''
    return run / 'clones' / re.sub(r'[^A-Za-z0-9]+', '-', url).strip('-')


def tracked_text() -> list[Path]:
    '''
    every markdown file (`*.md`) git tracks outside upstream/, which is where citations live; a
    citation-shaped string in code, such as a test fixture, is never read.
    '''
    names = git('ls-files', '-z', '--', '*.md', cwd=REPO, strip=False).split('\0')
    return [REPO / n for n in sorted(names)
            if n and not n.startswith('upstream/') and (REPO / n).is_file()]


def _plain(obj):
    '''an object as JSON holds it: dataclasses as objects, sets as sorted lists.'''
    if dataclasses.is_dataclass(obj):
        return {f.name: _plain(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, (set, frozenset)):
        return sorted(_plain(x) for x in obj)
    if isinstance(obj, (list, tuple)):
        return [_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    return obj


def _build(tp, value):
    '''a JSON value read back into the type `tp` names.'''
    if value is None:
        return None
    origin, args = typing.get_origin(tp), typing.get_args(tp)
    if dataclasses.is_dataclass(tp):
        hints = typing.get_type_hints(tp)
        return tp(**{f.name: _build(hints[f.name], value[f.name])
                     for f in dataclasses.fields(tp) if f.name in value})
    if origin in (typing.Union, types.UnionType):
        return _build(next(a for a in args if a is not type(None)), value)
    if origin is list:
        return [_build(args[0], x) for x in value]
    if origin is set:
        return {_build(args[0], x) for x in value}
    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_build(args[0], x) for x in value)
        return tuple(_build(a, x) for a, x in zip(args, value))
    if origin is dict:
        return {_build(args[0], k): _build(args[1], v) for k, v in value.items()}
    return int(value) if tp is int else float(value) if tp is float else value


RUN_FILES = {'ledger.json': Ledger}


def save(run: Path, name: str, obj) -> Path:
    '''one run file written as JSON, dataclasses as objects and sets as sorted lists.'''
    path = run / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_plain(obj), indent=1, ensure_ascii=False) + '\n')
    return path


def load(run: Path, name: str):
    '''one run file read back into the types above.'''
    value = json.loads((run / name).read_text())
    return _build(RUN_FILES[name], value) if name in RUN_FILES else value


# ── pins and copies ───────────────────────────────────────────────────────────

def read_sources(path: Path = SOURCES) -> Sources:
    '''
    upstream/sources.json read, failing on a missing field, a commit that is not 40 hex, a folder
    that is not under upstream/, or a copy whose source is not.
    '''
    if not path.is_file():
        raise ValueError(f'{path} is missing')
    data = json.loads(path.read_text())
    rows = []
    for n, row in enumerate(data.get('imports') or []):
        missing = [k for k in ('folder', 'url', 'path', 'commit', 'date') if k not in row]
        if missing:
            raise ValueError(f'{path.name}: import {n} has no {", ".join(missing)}')
        if not re.fullmatch(r'[0-9a-f]{40}', row['commit']):
            raise ValueError(f'{path.name}: {row["folder"]}: commit {row["commit"]} is not 40 hex')
        if '..' in row['folder'].split('/') or not (UPSTREAM / row['folder']).is_dir():
            raise ValueError(f'{path.name}: {row["folder"]} is not a folder under upstream/')
        rows.append(Import(row['folder'], row['url'], row['path'].strip('/'), row['commit'],
                           row['date'], bool(row.get('partial', False))))
    if not rows:
        raise ValueError(f'{path.name} names no import')
    copies = data.get('copies') or {}
    for kfolder, source in copies.items():
        if '..' in source.split('/') or not (UPSTREAM / source).is_dir():
            raise ValueError(f'{path.name}: the source of {kfolder}, {source}, '
                             'is not under upstream/')
    return Sources(rows, dict(copies))


def check_prose(sources: Sources, readme: str, notice: str) -> list[str]:
    '''one finding per row whose short commit, the first 7 hex, NOTICE or the README leaves out.'''
    out = []
    for row in sources.imports:
        for name, text in (('NOTICE', notice), ('upstream/README.md', readme)):
            if row.commit[:7] not in text:
                out.append(f'{name} does not name the pin of upstream/{row.folder}, '
                           f'{row.commit[:7]}')
    return out


def _tracked_files(folder: str) -> dict[str, Path]:
    '''each file git tracks under a repository folder, by its path inside that folder.'''
    names = git('ls-files', '-z', '--', folder, cwd=REPO, strip=False).split('\0')
    return {n[len(folder) + 1:]: REPO / n for n in names if n and (REPO / n).is_file()}


def check_copies(sources: Sources) -> list[str]:
    '''one finding per file where a declared copy and its upstream/ source differ in bytes.'''
    out = []
    for kfolder, source in sources.copies.items():
        mine, theirs = _tracked_files(kfolder), _tracked_files(f'upstream/{source}')
        for rel in sorted(set(mine) | set(theirs)):
            if rel not in theirs:
                out.append(f'{kfolder}/{rel}: in the copy, not in upstream/{source}')
            elif rel not in mine:
                out.append(f'{kfolder}/{rel}: in upstream/{source}, missing from the copy')
            elif mine[rel].read_bytes() != theirs[rel].read_bytes():
                out.append(f'{kfolder}/{rel}: differs from upstream/{source}/{rel}')
    return out


# ── citations ─────────────────────────────────────────────────────────────────

BLOCK = re.compile(r'([-*+]|\d+[.)]|#+|\||>|```|~~~)(\s|$)')


def flatten(text: str) -> tuple[str, list[int]]:
    '''
    a text with each line break inside a paragraph, and its indentation, read as one space, and
    each offset's line; a blank line, or a line that opens a list item, heading, table row,
    quote or fence, starts a new paragraph after a newline.
    '''
    out: list[str] = []
    owner: list[int] = []
    for n, line in enumerate(text.split('\n'), 1):
        body = line.strip()
        if not body:
            if out and out[-1] != '\n':
                out.append('\n')
                owner.append(n)
            continue
        if out and out[-1] != '\n':
            out.append('\n' if BLOCK.match(body) else ' ')
            owner.append(n)
        out.append(body)
        owner.extend([n] * len(body))
    return ''.join(out), owner


def _opener(labels: set[str]) -> re.Pattern:
    '''the opening of a citation: a parenthesis, a known label and a comma.'''
    names = '|'.join(re.escape(x) for x in sorted(labels, key=len, reverse=True))
    return re.compile(rf'\(({names}),\s')


def find_parens(flat: str, labels: set[str]) -> Iterator[tuple[int, int]]:
    '''
    the start and end of every balanced parenthesis that opens with a known label; one left open
    at its paragraph's end comes back with its end equal to its start.
    '''
    for m in _opener(labels).finditer(flat):
        depth, code = 0, False
        for i in range(m.start(), len(flat)):
            ch = flat[i]
            if ch == '\n':
                break
            if ch == '`':
                code = not code
            elif not code and ch == '(':
                depth += 1
            elif not code and ch == ')':
                depth -= 1
                if depth == 0:
                    yield m.start(), i + 1
                    break
        else:
            yield m.start(), m.start()
            continue
        if depth:
            yield m.start(), m.start()


def split_pairs(inner: str, labels: set[str]) -> list[tuple[str | None, str, str, int]]:
    '''
    the label, path and rest of each `;`-separated pair in one parenthesis, with the place of the
    part it came from; a pair that names only a path takes the label before it, and so does one
    whose path follows prose, `see `b.md`, l. 2`, when line numbers follow the path. A part that
    names a label and no path comes back with an empty path, and one that names neither, such as
    `Mayer, 2009`, or a path after prose with no line numbers, is prose and left out.
    '''
    names = '|'.join(re.escape(x) for x in sorted(labels, key=len, reverse=True))
    pairs, last = [], None
    for n, part in enumerate(inner.split(';')):
        m = re.match(rf'\s*(?:({names}),\s*)?`([^`]+)`(.*)$', part, re.S)
        if m:
            last = m.group(1) or last
            pairs.append((last, m.group(2), m.group(3), n))
            continue
        m = re.match(rf'\s*({names}),', part)
        if m:
            last = m.group(1)
            pairs.append((last, '', part.strip(), n))
            continue
        m = re.match(r'[^`]*?`([^`]+)`(.*)$', part, re.S)
        if m and parse_lines(m.group(2)):
            pairs.append((last, m.group(1), m.group(2), n))
    return pairs


NUM = r'\d+(?:\s*[–-]\s*\d+)?'


def parse_lines(rest: str) -> tuple[tuple[Span, ...], str] | None:
    '''the spans of `l. N`, `ll. N–M` or `ll. N, M`, and the prose after them, or None.'''
    m = re.match(rf'\s*,\s*ll?\.\s*({NUM}(?:\s*,\s*{NUM})*)(.*)$', rest, re.S)
    if not m:
        return None
    spans = []
    for part in re.split(r'\s*,\s*', m.group(1).strip()):
        a, _, b = re.sub(r'\s', '', part).replace('–', '-').partition('-')
        first, last = int(a), int(b or a)
        if first < 1 or last < first:
            return None
        spans.append(Span(first, last))
    return tuple(spans), re.sub(r'^\s*,\s*', '', m.group(2)).strip()


def quote_before(flat: str, start: int) -> str | None:
    '''the double-quoted text that ends right before a parenthesis, or None.'''
    before = flat[:start].rstrip(' ')
    if not before or before[-1] not in '"”':
        return None
    opening = '“' if before[-1] == '”' else '"'
    i = before.rfind(opening, 0, len(before) - 1)
    if i < 0 or '\n' in before[i:]:
        return None
    quote = before[i + 1:-1].strip()
    return quote or None


def deviation_after(flat: str, end: int) -> str | None:
    '''
    the nearest `*(kstack: …)*` tag that follows a citation in the same paragraph or table cell,
    before the next citation: a hint the brief shows for kept, which the judging agent, reading
    the rule, decides in its verdict, since the tag may mark another sentence.
    '''
    seg = flat[end:]
    stop = min([len(seg)] + [i for i in (seg.find('\n'), seg.find('|')) if i >= 0]
               + [m.start() for m in re.finditer(r'\([a-z][a-z-]*, `', seg)][:1])
    m = TAG.search(seg, 0, stop)
    if not m:
        return None
    depth = 0
    for i in range(m.start() + 1, len(seg)):
        depth += {'(': 1, ')': -1}.get(seg[i], 0)
        if depth == 0:
            return seg[m.start():i + 2] if seg[i + 1:i + 2] == '*' else seg[m.start():i + 1]
    return seg[m.start():stop]


def parse_text(kfile: str, text: str, labels: set[str]) -> tuple[list[Citation],
                                                                   list[tuple[str, int, str]]]:
    '''every citation in one text, and each parenthesis that names a label and did not parse.'''
    citations, unparsed, _ = _parse(kfile, text, labels)
    return citations, unparsed


def _parse(kfile: str, text: str,
           labels: set[str]) -> tuple[list[Citation], list[tuple[str, int, str]], list[int]]:
    '''`parse_text`, with the flattened offset of each citation's parenthesis beside it.'''
    flat, owner = flatten(text)
    citations, unparsed, on_line, starts = [], [], {}, []
    for start, end in find_parens(flat, labels):
        kline = owner[start]
        if end == start:
            unparsed.append((kfile, kline, flat[start:start + 80] + ' … left open'))
            continue
        quote, deviation = quote_before(flat, start), deviation_after(flat, end)
        inner = flat[start + 1:end - 1]
        pieces = [p.strip() for p in inner.split(';')]
        for label, path, rest, k in split_pairs(inner, labels):
            raw = pieces[k]
            lines = parse_lines(rest) if path else None
            if not label or not lines:
                unparsed.append((kfile, kline, flat[start:end]))
                continue
            on_line[kline] = n = on_line.get(kline, 0) + 1
            citations.append(Citation(f'{kfile}:{kline}:{n}', kfile, kline, label, path, lines[0],
                                      raw, lines[1], quote, deviation))
            starts.append(start)
    return citations, unparsed, starts


def all_citations(sources: Sources) -> tuple[list[Citation], list[tuple[str, int, str]]]:
    '''every citation in every tracked text, with the labels the rows name.'''
    labels = {row.label() for row in sources.imports}
    citations, unparsed = [], []
    for path in tracked_text():
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        found, bad = parse_text(str(path.relative_to(REPO)), text, labels)
        citations += found
        unparsed += bad
    return citations, unparsed


# ── matching ──────────────────────────────────────────────────────────────────

def normalize(text: str, loose: bool = False) -> str:
    '''
    a passage as compared: whitespace runs as one space and curly quotes straightened, and with
    `loose`, `*`, `_` and backticks dropped too, since a quote can drop markdown emphasis.
    '''
    text = text.translate(CURLY)
    if loose:
        text = re.sub(r'[*_`]', '', text)
    return ' '.join(text.split())


def fragments(quote: str) -> list[str]:
    '''a quote cut at its ellipses and bracketed insertions, each part searched on its own.'''
    parts = re.split(r'\.\.\.|…|\[[^\]]*\]', quote)
    return [p for p in (x.strip().strip('.,;:').strip() for x in parts) if p]


@functools.lru_cache(maxsize=4096)
def _index(lines: tuple[str, ...], loose: bool) -> tuple[str, tuple[int, ...]]:
    '''a text's lines normalized and joined by one space, with each character's line.'''
    chars: list[str] = []
    owner: list[int] = []
    for n, line in enumerate(lines, 1):
        norm = normalize(line, loose)
        if not norm:
            continue
        if chars:
            chars.append(' ')
            owner.append(n)
        chars.append(norm)
        owner.extend([n] * len(norm))
    return ''.join(chars), tuple(owner)


def _hits(quote: str, lines: tuple[str, ...], loose: bool) -> list[tuple[int, int, int, int]]:
    '''each place a quote's fragments sit in order: start and end offsets, first and last line.'''
    text, owner = _index(lines, loose)
    frags = [normalize(f, loose) for f in fragments(quote)]
    frags = [f for f in frags if f]
    if not frags:
        return []
    out, i = [], text.find(frags[0])
    while i >= 0:
        cur, ok = i + len(frags[0]), True
        for f in frags[1:]:
            j = text.find(f, cur)
            if j < 0:
                ok = False
                break
            cur = j + len(f)
        if not ok:
            break
        out.append((i, cur, owner[i], owner[cur - 1]))
        i = text.find(frags[0], i + 1)
    return out


def locate_quote(quote: str, lines: list[str]) -> list[Span]:
    '''every span of a text that holds each fragment of a quote, in order, exactly or loosely.'''
    for loose in (False, True):
        hits = _hits(quote, tuple(lines), loose)
        if hits:
            return sorted({Span(a, b) for _, _, a, b in hits}, key=lambda s: (s.first, s.last))
    return []


def _cited(lines: list[str], spans: tuple[Span, ...]) -> tuple[str, ...]:
    '''the lines a citation's spans name, the ones in range.'''
    return tuple(lines[n - 1] for s in spans for n in range(s.first, s.last + 1)
                 if 0 < n <= len(lines))


def _text(lines: list[str] | None, spans: tuple[Span, ...]) -> str:
    '''the normalized text at a citation's spans.'''
    return normalize(' '.join(_cited(lines, spans))) if lines else ''


def run_citation(citation: Citation, lines: list[str] | None, against: str) -> Check:
    '''
    one citation run against one text, None for a missing file: the file exists, each span is in
    range, and the quote sits at the spans, exactly or loosely, else where it does sit.
    '''
    if lines is None:
        return Check(citation.id, 'file-missing', (), against)
    if any(s.last > len(lines) for s in citation.spans):
        return Check(citation.id, 'out-of-range', (), against)
    if not citation.quote or not fragments(citation.quote):
        return Check(citation.id, 'paraphrase', (), against)
    sub = _cited(lines, citation.spans)
    for loose, status in ((False, 'ok'), (True, 'loose')):
        if _hits(citation.quote, sub, loose):
            return Check(citation.id, status, (), against)
    found = locate_quote(citation.quote, lines)
    status = 'quote-elsewhere' if found else 'quote-missing'
    return Check(citation.id, status, tuple(found), against)


def _lines(path: Path) -> list[str] | None:
    '''a file's lines, or None when it is not there or not text.'''
    try:
        return path.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeDecodeError):
        return None


def resolve(citation: Citation, root: Path, file: Path, against: str) -> Check:
    '''
    one citation run against its file in one copy, as `check` runs every citation against
    upstream/ and settle against the head: a file that is not inside the copy's `root` is
    `file-missing`.
    '''
    if _escapes(citation.path) or root.resolve() not in file.resolve().parents:
        return Check(citation.id, 'file-missing', (), against)
    return run_citation(citation, _lines(file), against)


def baseline(citations: list[Citation], sources: Sources) -> dict[str, Check]:
    '''every citation run against its file under upstream/, the copy at the pin, by citation id.'''
    return {c.id: resolve(c, UPSTREAM / c.label, UPSTREAM / c.label / c.path, 'upstream/')
            for c in citations}


def check_all(sources: Sources) -> tuple[list[Citation], list[tuple[str, int, str]],
                                         dict[str, Check], list[str]]:
    '''every citation, the unparsed ones, each baseline check, and every finding `check` prints.'''
    readme = README.read_text() if README.is_file() else ''
    notice = NOTICE.read_text() if NOTICE.is_file() else ''
    findings = check_prose(sources, readme, notice)
    citations, unparsed = all_citations(sources)
    checks = baseline(citations, sources)
    for c in citations:
        chk = checks[c.id]
        if chk.status not in PASS:
            where = ', '.join(f'{s.first}–{s.last}' for s in chk.found)
            findings.append(f'{c.kfile}:{c.kline}: ({c.raw}) {chk.status}'
                            + (f', the quote sits at {where}' if where else ''))
    findings += [f'{f}:{n}: does not parse: {t}' for f, n, t in unparsed]
    return citations, unparsed, checks, findings + check_copies(sources)


# ── scan: the clone and the proof ─────────────────────────────────────────────

def clone(url: str, dest: Path, paths: list[str]) -> Path:
    '''
    a blobless clone of one repository, then a sparse checkout of the import paths at the head,
    so the head files arrive in one batched fetch and no blob is fetched one at a time; a clone
    the run folder already holds is fetched again and moved to the remote's head.
    '''
    if not (dest / '.git').is_dir():
        dest.parent.mkdir(parents=True, exist_ok=True)
        out = subprocess.run(['git', 'clone', '--quiet', '--filter=blob:none', '--no-checkout',
                              url, str(dest)], capture_output=True, text=True)
        if out.returncode:
            raise RuntimeError(f'git clone {url} failed: {out.stderr.strip()}')
    else:
        out = subprocess.run(['git', 'fetch', '--quiet', 'origin', 'HEAD'], cwd=dest,
                             capture_output=True, text=True)
        if out.returncode:
            raise RuntimeError(f'git fetch {url} failed: {out.stderr.strip()}')
        git('update-ref', 'HEAD', 'FETCH_HEAD', cwd=dest)
    if '' not in paths:
        git('sparse-checkout', 'set', '--cone', *sorted(set(paths)), cwd=dest)
    subprocess.run(['git', 'read-tree', '-mu', 'HEAD'], cwd=dest, capture_output=True)
    return dest


def blob_ids(where: Path, rev: str, path: str) -> dict[str, str]:
    '''path inside `path` to blob id at one commit, from `git ls-tree -r`, which reads no blob.'''
    out = git('ls-tree', '-r', '-z', rev, *([path] if path else []), cwd=where, strip=False)
    ids = {}
    for entry in out.split('\0'):
        meta, _, name = entry.partition('\t')
        if meta.split(' ')[1:2] == ['blob']:
            ids[name[len(path):].lstrip('/') if path else name] = meta.split(' ')[2]
    return ids


def local_blob_ids(folder: Path, skip: list[Path]) -> dict[str, str]:
    '''path to `git hash-object` id for the imported copy, past the folders of nested rows.'''
    rel = folder.relative_to(REPO).as_posix()
    files = {k: v for k, v in _tracked_files(rel).items()
             if not any(s == v.parent or s in v.parents for s in skip)}
    names = sorted(files)
    out = subprocess.run(['git', 'hash-object', '--stdin-paths'], cwd=REPO, capture_output=True,
                         text=True, input='\n'.join(str(files[n]) for n in names) + '\n')
    return dict(zip(names, out.stdout.split())) if names else {}


def prove_pin(row: Import, sources: Sources, where: Path) -> list[str]:
    '''
    each file where the row's copy and the tree at its pin differ, empty once proved; a partial
    row proves only the files it holds, and a whole row also fails on a file it lacks, unless
    kstack's .gitignore leaves that file out on purpose.
    '''
    if not git('cat-file', '-t', row.commit, cwd=where) == 'commit':
        return [f'the pin {row.commit[:7]} is not in {row.url}']
    nested = [r for r in sources.imports if r.folder.startswith(row.folder + '/')]
    inside = [r.folder[len(row.folder) + 1:] + '/' for r in nested]
    theirs = {k: v for k, v in blob_ids(where, row.commit, row.path).items()
              if not any(k.startswith(p) for p in inside)}
    mine = local_blob_ids(UPSTREAM / row.folder, [UPSTREAM / r.folder for r in nested])
    lacking = [f'upstream/{row.folder}/{rel}' for rel in sorted(set(theirs) - set(mine))]
    ignored = set(subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'], cwd=REPO,
                                 capture_output=True, text=True,
                                 input='\n'.join(lacking) + '\n').stdout.split('\n'))
    out = []
    for rel in sorted(set(mine) | set(theirs)):
        if rel not in theirs:
            out.append(f'upstream/{row.folder}/{rel}: not in {row.url} at {row.commit[:7]}')
        elif rel not in mine:
            if not row.partial and f'upstream/{row.folder}/{rel}' not in ignored:
                out.append(f'upstream/{row.folder}/{rel}: in {row.url} at {row.commit[:7]}, '
                           'not imported')
        elif mine[rel] != theirs[rel]:
            out.append(f'upstream/{row.folder}/{rel}: differs from {row.commit[:7]}')
    return out


# ── scan: the changes ─────────────────────────────────────────────────────────

def name_status(where: Path, row: Import) -> list[tuple[str, str, str | None]]:
    '''
    the status, pin path and head path of each file the head changes under a row, from one
    `git diff -M --name-status <pin> HEAD -- <path>`; an added file's pin path is ''.
    '''
    out = git('diff', '-M', '--name-status', '-z', row.commit, 'HEAD', '--', row.path or '.',
              cwd=where, strip=False).split('\0')
    rows, i = [], 0
    while i < len(out) - 1:
        status = out[i][:1]
        if status in 'RC':
            rows.append((status, out[i + 1], out[i + 2]))
            i += 3
        elif status:
            path = out[i + 1]
            rows.append((status, '' if status == 'A' else path, None if status == 'D' else path))
            i += 2
        else:
            i += 1
    return rows


def commits(where: Path, row: Import) -> dict[str, list[Commit]]:
    '''
    each head path under a row to the commits that touched it, oldest first, from one `git log
    --format --name-only`, which reads no blob.
    '''
    out = git('log', '--reverse', '--no-renames', '--format=%x1e%H%x1f%aI%x1f%B%x1f', '--name-only',
              f'{row.commit}..HEAD', '--', row.path or '.', cwd=where, strip=False)
    touched: dict[str, list[Commit]] = {}
    for record in out.split('\x1e')[1:]:
        sha, date, message, names = (record.split('\x1f') + ['', '', '', ''])[:4]
        commit = Commit(sha, date, message.strip())
        for name in names.split('\n'):
            if name.strip():
                touched.setdefault(name.strip(), []).append(commit)
    return touched


def line_map(old: list[str], new: list[str]) -> dict[int, int | None]:
    '''each pin line's head line from difflib's matching blocks, or None where the line changed.'''
    out: dict[int, int | None] = {n: None for n in range(1, len(old) + 1)}
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for a, b, size in matcher.get_matching_blocks():
        for k in range(size):
            out[a + k + 1] = b + k + 1
    return out


def anchor(citation: Citation, pin: list[str]) -> Anchor:
    '''the citation's quote, or its cited lines' pin text, with its context from the pin copy.'''
    text, owner = _index(tuple(pin), False)
    first, last = citation.spans[0].first, citation.spans[-1].last
    if citation.quote and fragments(citation.quote):
        hits = _hits(citation.quote, tuple(pin), False)
        inside = [h for h in hits if first <= h[2] and h[3] <= last] or hits
        if inside:
            start, end = inside[0][0], inside[0][1]
            return Anchor(normalize(citation.quote), text[max(0, start - CONTEXT):start],
                          text[end:end + CONTEXT])
        exact = normalize(citation.quote)
    else:
        exact = _text(pin, citation.spans)
    start = bisect.bisect_left(owner, first)
    end = bisect.bisect_right(owner, last)
    return Anchor(exact, text[max(0, start - CONTEXT):start].strip(),
                  text[end:end + CONTEXT].strip())


def _similar(a: str, b: str) -> float:
    '''how much of `a`, word by word, `b` holds in order, from 0 to 1.'''
    wa, wb = a.split(), b.split()
    if not wa:
        return 1.0 if not wb else 0.0
    blocks = difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_matching_blocks()
    return sum(x.size for x in blocks) / max(len(wa), len(wb))


def score(target: Anchor, lines: list[str], span: Span, near: int | None) -> float:
    '''
    how well a head span matches an anchor, by Hypothesis's weights: quote 50, prefix 20,
    suffix 20 and position 2, the last by distance from the mapped line.
    '''
    text, owner = _index(tuple(lines), False)
    start = bisect.bisect_left(owner, span.first)
    end = bisect.bisect_right(owner, span.last)
    here = text[start:end].strip()
    quote = 1.0 if target.exact and target.exact in here else _similar(target.exact, here)
    before = text[max(0, start - len(target.prefix) - 1):start].strip()
    after = text[end:end + len(target.suffix) + 1].strip()
    ratio = lambda a, b: 1.0 if a == b else difflib.SequenceMatcher(None, a, b).ratio()
    position = 0.0 if near is None else 1 - min(1.0, abs(span.first - near) / max(1, len(lines)))
    total = (WEIGHTS['quote'] * quote + WEIGHTS['prefix'] * ratio(target.prefix, before)
             + WEIGHTS['suffix'] * ratio(target.suffix, after) + WEIGHTS['position'] * position)
    return total / sum(WEIGHTS.values())


def _head_files(where: Path, row: Import) -> list[str]:
    '''every file of a row checked out at the head, as repository paths.'''
    base = where / row.path if row.path else where
    return sorted(p.relative_to(where).as_posix() for p in base.rglob('*')
                  if p.is_file() and '.git' not in p.relative_to(where).parts)


def search_row(where: Path, row: Import, target: Anchor) -> list[tuple[str, Span]]:
    '''every head file and span under a row that holds the anchor's exact text.'''
    out = []
    for name in _head_files(where, row):
        lines = _lines(where / name)
        if lines:
            out += [(row.local_path(name), s) for s in locate_quote(target.exact, lines)]
    return out


def fuzzy(target: Anchor, lines: list[str], near: int | None,
          size: int = 1) -> tuple[Span, float] | None:
    '''
    the best-scoring head span whose text is close to the anchor's, and its score; a span is
    close when it holds at least `REWORDED` of the anchor's words in order, and its length is
    within two lines of `size`, the cited lines' count.
    '''
    words = set(target.exact.split())
    best = None
    for size in sorted({max(1, size + d) for d in (-2, -1, 0, 1, 2)}):
        for first in range(1, len(lines) - size + 2):
            span = Span(first, first + size - 1)
            here = _text(lines, (span,))
            if not here or len(words & set(here.split())) < REWORDED * len(words):
                continue
            if _similar(target.exact, here) < REWORDED:
                continue
            s = score(target, lines, span, near)
            if best is None or s > best[1]:
                best = (span, s)
    return best


def _near(citation: Citation, file: UpstreamFile) -> int:
    '''the head line the line map gives the first cited line, or the nearest one it maps.'''
    first = citation.spans[0].first
    for d in range(0, 50):
        for n in (first - d, first + d):
            if file.lines.get(n):
                return file.lines[n] - (n - first)
    return first


def remap(citation: Citation, file: UpstreamFile, base: Check, pin: list[str],
          head: list[str] | None, where: Path, row: Import) -> Remap:
    '''
    one citation's passage found at the head, in order: the line map, whole or for at least
    `REWORDED` of the cited lines, the exact quote in the head file, the exact quote across the
    row's head files, the hit nearest the mapped line when there are several, then a fuzzy match
    whose `REWORDED` threshold splits edited from gone.
    '''
    old = _text(pin, citation.spans)
    done = lambda state, found, path, spans, lines, s: Remap(
        citation.id, state, found, path, tuple(spans), old, _text(lines, tuple(spans)), s)
    if base.status not in PASS:
        return done('stale', 'none', file.head_path, (), None, 0.0)
    target, near = anchor(citation, pin), _near(citation, file)
    if head is not None:
        mapped = [[file.lines.get(n) for n in range(s.first, s.last + 1)] for s in citation.spans]
        if all(None not in m and m == list(range(m[0], m[0] + len(m))) for m in mapped):
            spans = tuple(Span(m[0], m[-1]) for m in mapped)
            same = spans == citation.spans and file.head_path == citation.path
            return done('in sync' if same else 'moved', 'lines', file.head_path, spans, head, 1.0)
        kept = [[x for x in m if x is not None] for m in mapped]
        if all(kept) and sum(map(len, kept)) >= REWORDED * sum(map(len, mapped)) and all(
                a[-1] < b[0] for a, b in zip(kept, kept[1:])):
            spans = tuple(Span(k[0], k[-1]) for k in kept)
            return done('edited', 'lines', file.head_path, spans, head,
                        _similar(old, _text(head, spans)))
    locator = citation.quote if citation.quote and fragments(citation.quote) else None
    pin_at = citation.spans[0].first
    if locator:
        at = [h for h in _hits(locator, tuple(pin), False) + _hits(locator, tuple(pin), True)
              if citation.spans[0].first <= h[2] <= citation.spans[-1].last]
        pin_at = at[0][2] if at else pin_at

    def placed(lines: list[str], hits: list[Span]) -> list[tuple[Span, ...]]:
        out = []
        for hit in hits:
            spans = tuple(Span(s.first + hit.first - pin_at, s.last + hit.first - pin_at)
                          for s in citation.spans)
            if spans[0].first < 1 or spans[-1].last > len(lines):
                continue
            if locator or all(_text(lines, (a,)) == _text(pin, (b,))
                              for a, b in zip(spans, citation.spans)):
                out.append(spans)
        return out

    def best(lines: list[str], options: list[tuple[Span, ...]], hint: int | None):
        return max(options, key=lambda sp: score(target, lines, Span(sp[0].first, sp[-1].last),
                                                 hint))

    def holds(path: str, spans: tuple[Span, ...], lines: list[str]) -> bool:
        moved = dataclasses.replace(citation, path=path, spans=spans)
        return run_citation(moved, lines, 'head').status in PASS

    seek = locator or _text(pin, citation.spans[:1])
    if head is not None:
        options = placed(head, locate_quote(seek, head))
        if options:
            spans = best(head, options, near)
            same = spans == citation.spans and file.head_path == citation.path
            if same or not holds(file.head_path, spans, head):
                return done('edited', 'quote', file.head_path, spans, head,
                            _similar(old, _text(head, spans)))
            return done('moved', 'quote', file.head_path, spans, head, 1.0)
    elsewhere: dict[str, list[Span]] = {}
    for path, span in search_row(where, row, Anchor(seek, '', '')):
        if path != file.head_path:
            elsewhere.setdefault(path, []).append(span)
    found = []
    for path, hits in elsewhere.items():
        lines = _lines(where / row.repo_path(path)) or []
        found += [(score(target, lines, Span(sp[0].first, sp[-1].last), None), path, sp, lines)
                  for sp in placed(lines, hits)]
    if found:
        _, path, spans, lines = max(found, key=lambda x: x[0])
        if not holds(path, spans, lines):
            return done('edited', 'quote-elsewhere', path, spans, lines,
                        _similar(old, _text(lines, spans)))
        return done('moved', 'quote-elsewhere', path, spans, lines, 1.0)
    if head is not None:
        hit = fuzzy(target, head, near, 1 if locator else
                    sum(s.last - s.first + 1 for s in citation.spans))
        if hit:
            return done('edited', 'fuzzy', file.head_path, (hit[0],), head, hit[1])
    return done('gone', 'none', file.head_path, (), None, 0.0)


def diff_copy(kfolder: str, source: str, where: Path, row: Import, run: Path) -> Copy:
    '''one declared copy against its source at the pin and at the head, with the diff written.'''
    mine = _tracked_files(kfolder)
    pin = _tracked_files(f'upstream/{source}')
    base = where / row.repo_path(source.split('/', 1)[1] if '/' in source else '')
    head = {p.relative_to(base).as_posix(): p for p in base.rglob('*') if p.is_file()} \
        if base.is_dir() else {}

    def marks(theirs: dict[str, Path]) -> dict[str, str]:
        out = {}
        for rel in sorted(set(mine) | set(theirs)):
            if rel not in theirs:
                out[rel] = 'only-kstack'
            elif rel not in mine:
                out[rel] = 'only-upstream'
            elif mine[rel].read_bytes() != theirs[rel].read_bytes():
                out[rel] = 'differs'
        return out

    at_head = marks(head)
    diff = []
    for rel in at_head:
        a = mine[rel].read_text(errors='replace').splitlines(True) if rel in mine else []
        b = head[rel].read_text(errors='replace').splitlines(True) if rel in head else []
        diff += difflib.unified_diff(a, b, f'a/{kfolder}/{rel}', f'b/{kfolder}/{rel}')
    name = f'copies/{re.sub(r"[^A-Za-z0-9]+", "-", kfolder)}.diff'
    (run / 'copies').mkdir(parents=True, exist_ok=True)
    (run / name).write_text(''.join(diff))
    return Copy(kfolder, source, marks(pin), at_head, name)


def additions(status: list[tuple[str, str, str | None]], row: Import,
              touched: dict[str, list[Commit]]) -> list[Addition]:
    '''
    the files the head adds under a row, SKILL.md files first; for a partial row only SKILL.md
    files, since its other files were never imported, and each file imported now that the head
    renames, at its new path.
    '''
    out = []
    for kind, old, head in status:
        skill = head is not None and head.rsplit('/', 1)[-1] == 'SKILL.md'
        if (kind == 'R' and row.partial
                and (UPSTREAM / row.label() / row.local_path(old)).is_file()):
            out.append(Addition(row.folder, row.local_path(head), skill, touched.get(head, []),
                                row.local_path(old)))
        if kind != 'A' or head is None or row.partial and not skill:
            continue
        out.append(Addition(row.folder, row.local_path(head), skill, touched.get(head, [])))
    return sorted(out, key=lambda a: (not a.skill, a.path))


def build_ledger(run: Path, sources: Sources, citations: list[Citation],
                 checks: dict[str, Check], unparsed: list[tuple[str, int, str]]) -> Ledger:
    '''the ledger: one clone per repository, each pin proved, each cited or copied file read.'''
    heads, proof, wheres = {}, {}, {}
    for url in dict.fromkeys(r.url for r in sources.imports):
        paths = [r.path for r in sources.imports if r.url == url]
        try:
            wheres[url] = clone(url, clone_dir(run, url), paths)
            heads[url] = git('rev-parse', 'HEAD', cwd=wheres[url])
        except RuntimeError as e:
            heads[url] = ''
            for r in sources.imports:
                if r.url == url:
                    proof[r.folder] = [str(e)]
    status, touched = {}, {}
    for row in sources.imports:
        if row.folder in proof:
            continue
        where = wheres[row.url]
        proof[row.folder] = prove_pin(row, sources, where)
        owned = lambda p: p and sources.owner(row.label(), row.local_path(p)) == row
        status[row.folder] = [s for s in name_status(where, row) if owned(s[2] or s[1])]
        touched[row.folder] = commits(where, row)
    wanted: dict[str, set[str]] = {}
    for c in citations:
        wanted.setdefault(f'{c.label}:{c.path}', set()).add('cited')
    for source in sources.copies.values():
        for rel in _tracked_files(f'upstream/{source}'):
            label, _, inside = source.partition('/')
            wanted.setdefault(f'{label}:{inside + "/" if inside else ""}{rel}', set()).add('copied')
    files: dict[str, UpstreamFile] = {}
    for key, why in sorted(wanted.items()):
        label, path = key.split(':', 1)
        row = sources.owner(label, path)
        file = UpstreamFile(key, row.folder if row else '', path, 'unchanged', why)
        files[key] = file
        if row is None or row.folder not in status:
            continue
        rpath = row.repo_path(path)
        for kind, old, new in status[row.folder]:
            if old == rpath:
                file.state = {'D': 'removed', 'R': 'renamed'}.get(kind, 'changed')
                file.head_path = row.local_path(new) if new else None
        seen = {}
        for p in (rpath, row.repo_path(file.head_path) if file.head_path else None):
            for commit in touched[row.folder].get(p or '', []):
                seen.setdefault(commit.sha, commit)
        file.commits = list(seen.values())
        pin = _lines(UPSTREAM / label / path) or []
        head = _lines(wheres[row.url] / row.repo_path(file.head_path)) if file.head_path else None
        file.lines = line_map(pin, head) if head is not None else {n: None for n in
                                                                    range(1, len(pin) + 1)}
    remaps = {}
    for c in citations:
        file = files[f'{c.label}:{c.path}']
        file.citations.append(c.id)
        row = sources.owner(c.label, c.path)
        pin = _lines(UPSTREAM / c.label / c.path) or []
        if row is None or proof.get(row.folder):
            remaps[c.id] = Remap(c.id, 'blocked', 'none', None, (), _text(pin, c.spans), '', 0.0)
            continue
        where = wheres[row.url]
        head = _lines(where / row.repo_path(file.head_path)) if file.head_path else None
        remaps[c.id] = remap(c, file, checks[c.id], pin, head, where, row)
    copies = []
    for kfolder, source in sources.copies.items():
        row = sources.owner(*source.split('/', 1))
        if row and row.url in wheres:
            copies.append(diff_copy(kfolder, source, wheres[row.url], row, run))
    added, removed = [], []
    for row in sources.imports:
        if row.folder not in status:
            continue
        added += additions(status[row.folder], row, touched[row.folder])
        for kind, old, _ in status[row.folder]:
            local = row.local_path(old) if old else ''
            if kind in 'DR' and (UPSTREAM / row.label() / local).is_file():
                removed.append(f'{row.label()}/{local}')
    return Ledger(git('rev-parse', 'HEAD', cwd=REPO), sources, heads, proof, files,
                  {c.id: c for c in citations}, checks, remaps, copies, added, removed, unparsed)


def _fmt_lines(spans: tuple[Span, ...]) -> str:
    '''spans written as kstack writes them: `l. 7`, `ll. 7–9` or `ll. 7, 12`.'''
    if len(spans) == 1 and spans[0].first == spans[0].last:
        return f'l. {spans[0].first}'
    return 'll. ' + ', '.join(f'{s.first}' if s.first == s.last else f'{s.first}–{s.last}'
                              for s in spans)


def _rule(flat: str, i: int) -> str:
    '''
    the paragraph, or table cell, of a flattened kstack text that holds offset `i`, where a
    citation's parenthesis opens.
    '''
    start, end = flat.rfind('\n', 0, i) + 1, flat.find('\n', i)
    para = flat[start:end if end >= 0 else len(flat)]
    if para.startswith('|'):
        at, cells = i - start, para.split('|')
        for cell in cells:
            if at <= len(cell):
                return cell.strip()
            at -= len(cell) + 1
    return para


JUDGE = ('Judge each citation below against the upstream text at the head, never against a '
         'commit message. Sort it as no effect, pointer drift, changed on purpose or no stated '
         'reason, and give it one outcome: in sync, updated, diverged, updated and diverged, or '
         'blocked. Each upstream file below names its pin copy under the repository\'s upstream/, '
         'its head copy in the run\'s clone, and the head tree it sits in: read and search them '
         'as you need, such as to tell a passage the head moved or reworded from one it removed. '
         'Return one JSON line per citation with the keys id, sort, outcome, commit, old, new, '
         'citation, edit and kept. Kept is true when a `*(kstack: …)*` tag marks the citation\'s '
         'rule as kstack\'s own; the kept hint is only the nearest such tag after the citation, '
         'which may mark another sentence, so read the rule and decide. A citation you mark kept '
         'gets no rule edit. Edit nothing.')


def section_for(kfile: str, ledger: Ledger, run: Path) -> str | None:
    '''
    one kstack file's part of a brief: each upstream file it cites, with the paths of its pin
    copy, its head copy and the head tree in `run`'s clone, and each citation left to judge with
    its rule, its old and new upstream text, and every commit message whole. None when the script
    decided every citation.
    '''
    ids = [i for i in ledger.by_kfile().get(kfile, []) if ledger.remaps[i].state not in DECIDED]
    if not ids:
        return None
    text = (REPO / kfile).read_text(encoding='utf-8')
    flat, _ = flatten(text)
    found, _, starts = _parse(kfile, text, {r.label() for r in ledger.sources.imports})
    opened = {c.id: s for c, s in zip(found, starts)}
    out = [f'## `{kfile}`', '']
    by_file: dict[str, list[str]] = {}
    for i in ids:
        c = ledger.citations[i]
        by_file.setdefault(f'{c.label}:{c.path}', []).append(i)
    for key, cids in by_file.items():
        f = ledger.files[key]
        row = next((r for r in ledger.sources.imports if r.folder == f.folder), None)
        head = ledger.heads.get(row.url, '')[:7] if row else ''
        label, path = key.split(':', 1)
        moved = f', now `{f.head_path}`' if f.head_path and f.head_path != path else ''
        clone = clone_dir(run, row.url) if row else None
        out += [f'### `{key}`: {f.state}{moved}', '',
                f'- Pin copy: `{UPSTREAM / label / path}`',
                f'- Head copy: `{clone / row.repo_path(f.head_path)}`' if clone and f.head_path
                else '- Head copy: none, the head removes it',
                f'- Head tree: `{clone / row.path}`' if clone else '- Head tree: none', '',
                f'Commits from {row.commit[:7] if row else "?"} to {head} that touched it, oldest '
                f'first: {len(f.commits)}.', '']
        for commit in f.commits:
            out += [f'#### {commit.sha[:12]} {commit.date}', '', '~~~~text', commit.message,
                    '~~~~', '']
        for i in cids:
            c, r, b = ledger.citations[i], ledger.remaps[i], ledger.baseline[i]
            out += [f'#### Citation `{i}`', '',
                    f'- As written: ({c.raw})',
                    f'- Quote: "{c.quote}"' if c.quote else '- Quote: none, a paraphrase',
                    f'- Kept hint: {c.deviation}' if c.deviation else '- Kept hint: none',
                    f'- Baseline against upstream/: {b.status}'
                    + (' (stale at the pin)' if b.status not in PASS else ''),
                    f'- At the head: {r.state}, found by {r.found}'
                    + (f', `{r.path}`, {_fmt_lines(r.spans)}' if r.spans else '')
                    + f', score {r.score:.2f}', '',
                    'The rule in kstack:', '', '> ' + _rule(flat, opened.get(i, 0)), '',
                    f'Upstream at the pin, {_fmt_lines(c.spans)}:', '', '> ' + (r.old or '(none)'),
                    '', 'Upstream at the head'
                    + (f', {_fmt_lines(r.spans)}:' if r.spans else ': not found'), '',
                    '> ' + (r.new or '(none)'), '']
    return '\n'.join(out)


def brief_text(n: int, kfiles: list[str], sections: dict[str, str]) -> str:
    '''brief `n`: a header naming the kstack files it covers, what to return, and their sections.'''
    head = [f'# Brief {n}', '', f'Kstack files: {len(kfiles)}.', ''] + [f'- `{k}`' for k in kfiles]
    return '\n'.join(head + ['', JUDGE, ''] + [sections[k] for k in kfiles])


def pack(ledger: Ledger, run: Path, cap: int = CAP) -> list[tuple[list[str], str]]:
    '''
    the briefs as kstack files and text: each kstack file with a citation left to judge goes whole
    into one, in path order, and a brief takes the next file while its whole text, the paths each
    section names in `run` included, stays within `cap` bytes, so a file over `cap` gets a brief
    of its own.
    '''
    sections = {k: s for k in ledger.by_kfile() if (s := section_for(k, ledger, run))}
    groups: list[list[str]] = []
    for k in sections:
        if groups and len(brief_text(len(groups), groups[-1] + [k], sections).encode()) <= cap:
            groups[-1].append(k)
        else:
            groups.append([k])
    return [(g, brief_text(n, g, sections)) for n, g in enumerate(groups, 1)]


# ── settle ────────────────────────────────────────────────────────────────────

def _fits(tp, value) -> bool:
    '''whether a JSON value is of a verdict field's type: a string, one of a `Literal`'s, or None.'''
    if typing.get_origin(tp) is Literal:
        return isinstance(value, str) and value in typing.get_args(tp)
    if typing.get_origin(tp) in (typing.Union, types.UnionType):
        return any(_fits(a, value) for a in typing.get_args(tp))
    return value is None if tp is type(None) else isinstance(value, tp)


def read_verdicts(run: Path) -> dict[str, Verdict]:
    '''
    <run>/verdicts.jsonl by citation id, failing on a line that is not a JSON object with every
    key, a value that is not of its field's type or among its field's values, or an id the ledger
    does not hold; every check is here, so nothing after it meets a bad row.
    '''
    ledger: Ledger = load(run, 'ledger.json')
    hints = typing.get_type_hints(Verdict)
    out = {}
    path = run / 'verdicts.jsonl'
    for n, line in enumerate(path.read_text().splitlines() if path.is_file() else [], 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as e:
            raise ValueError(f'verdicts.jsonl:{n}: not JSON: {e}') from None
        if not isinstance(row, dict):
            raise ValueError(f'verdicts.jsonl:{n}: not a JSON object')
        missing = [f.name for f in dataclasses.fields(Verdict) if f.name not in row]
        if missing:
            raise ValueError(f'verdicts.jsonl:{n}: no {", ".join(missing)}')
        wrong = [f'{k} {json.dumps(row[k])}' for k in hints if not _fits(hints[k], row[k])]
        if wrong:
            raise ValueError(f'verdicts.jsonl:{n}: not of its field\'s type or values: '
                             + ', '.join(wrong))
        if row['id'] not in ledger.citations:
            raise ValueError(f'verdicts.jsonl:{n}: {row["id"]} is not a citation the ledger holds')
        out[row['id']] = Verdict(**{k: row[k] for k in hints})
    return out


def _suggestion(verdict: Verdict, ledger: Ledger) -> Citation | None:
    '''
    a verdict's suggested citation parsed as recheck and remap_patch both read it, a bare
    parenthesis or one opened by its path taking the original's label, or None when it suggests
    none or it does not parse.
    '''
    text = (verdict.citation or '').strip()
    if not text:
        return None
    original = ledger.citations[verdict.id]
    text = text if text.startswith('(') else f'({text})'
    text = f'({original.label}, {text[1:]}' if text.startswith('(`') else text
    found, _ = parse_text('<verdict>', text, {r.label() for r in ledger.sources.imports})
    return dataclasses.replace(found[0], id=verdict.id,
                               quote=found[0].quote or original.quote) if found else None


def copied(ledger: Ledger, row: Import, path: str) -> bool:
    '''
    whether the re-import reimport.md gives copies `upstream/<label>/<path>` of `row`: any file of
    a whole row, and for a partial row a file imported now, a file imported now at the new path
    upstream renamed it to, or a new SKILL.md.
    '''
    return not row.partial or (UPSTREAM / row.label() / path).is_file() or any(
        a.folder == row.folder and a.path == path and (a.skill or a.renamed)
        for a in ledger.added)


def _moved(ledger: Ledger, i: str) -> bool:
    '''whether the scan moved citation `i` to a place the re-import copies, as `copied` says.'''
    r, c = ledger.remaps[i], ledger.citations[i]
    row = ledger.sources.owner(c.label, r.path) if r.path else None
    return r.state == 'moved' and row is not None and copied(ledger, row, r.path)


def recheck(verdict: Verdict, ledger: Ledger, run: Path) -> Check | None:
    '''
    the suggested citation parsed and run by `resolve` against the head copy of the row that owns
    its path, in `run`'s clone, the clone's import path its root, or None when there is none. It is
    `unparsed` when an updated outcome suggests no citation, since updated means the suggested
    citation points at the passage at the head, and `file-missing` when no row owns the path, when
    it names another label than the citation, since remap.patch edits only the path and line
    numbers, and when `copied` finds that the re-import does not copy its file.
    '''
    if not (verdict.citation or '').strip():
        if verdict.outcome in ('updated', 'updated and diverged'):
            return Check(verdict.id, 'unparsed', (), 'head')
        return None
    c = _suggestion(verdict, ledger)
    if c is None:
        return Check(verdict.id, 'unparsed', (), 'head')
    row = ledger.sources.owner(c.label, c.path)
    if row is None or _escapes(c.path) or c.label != ledger.citations[verdict.id].label:
        return Check(c.id, 'file-missing', (), 'head')
    if not copied(ledger, row, c.path):
        return Check(c.id, 'file-missing', (), 'head')
    clone = clone_dir(run, row.url)
    return resolve(c, clone / row.path if row.path else clone, clone / row.repo_path(c.path),
                   ledger.heads.get(row.url, 'head'))


def _escapes(path: str) -> bool:
    '''whether a citation's path climbs out of its folder, by `..` or from the root.'''
    return path.startswith('/') or '..' in path.split('/')


PAIR = re.compile(rf'([^`]*)`([^`]+)`(\s*,\s*)(ll?\.\s*{NUM}(?:\s*,\s*{NUM})*)(.*)$', re.S)


def _flex(text: str) -> str:
    '''a pattern for flattened text, each run of whitespace matching any run, line breaks too.'''
    return ''.join(r'\s+' if part.isspace() else re.escape(part)
                   for part in re.split(r'(\s+)', text) if part)


def _place(citation: Citation, text: str, at: int) -> re.Match | None:
    '''
    the first exact match of a pair's flattened `raw` in a text from offset `at`, opened by `(` or
    `;` and closed by `;` or `)`; group 1 is the path and group 2 the `l. N` or `ll. N–M`.
    '''
    m = PAIR.match(citation.raw)
    if not m:
        return None
    head, path, mid, lines, tail = m.groups()
    return re.compile(rf'[(;]\s*{_flex(head)}`({re.escape(path)})`{_flex(mid)}({_flex(lines)})'
                      rf'{_flex(tail)}(?=\s*[;)])').search(text, at)


def _relined(written: str, old: tuple[Span, ...], new: tuple[Span, ...]) -> str:
    '''
    a pair's `l. N` or `ll. N–M` as written, renumbered to `new`: each number swapped in place when
    the spans keep their shape, so its spacing and line breaks stay, else written afresh after the
    gap that follows `l.` or `ll.`, the gap's line break kept, or, when the break sat inside the
    list, that break put before `l.` or `ll.`, where no number opens a line.
    '''
    numbers = lambda spans: [n for s in spans for n in dict.fromkeys((s.first, s.last))]
    shape = lambda spans: [s.first == s.last for s in spans]
    if shape(old) == shape(new) and len(re.findall(r'\d+', written)) == len(numbers(old)):
        fresh = iter(numbers(new))
        return re.sub(r'\d+', lambda _: str(next(fresh)), written)
    prefix, _, rest = _fmt_lines(new).partition(' ')
    m = re.match(r'll?\.(\s*)', written)
    gap = m.group(1)
    breaks = None if '\n' in gap else re.search(r'\n\s*', written[m.end():])
    return (breaks.group() if breaks else '') + prefix + (gap or ' ') + rest


def _order(citation: Citation) -> tuple[int, int]:
    '''a citation's place in its file: its line, then its pair number on that line, as numbers.'''
    return citation.kline, int(citation.id.rsplit(':', 1)[1])


def _pointer(ledger: Ledger, i: str,
             verdict: Verdict | None) -> tuple[str, tuple[Span, ...]] | None:
    '''
    the path and spans remap.patch gives citation `i`, or None when it leaves the citation as
    written: with no verdict, a moved citation's place in the ledger, when the re-import copies
    it; with one, its suggestion, when the outcome is updated or the citation moved, and the path
    stays in its folder.
    '''
    r = ledger.remaps[i]
    if verdict is None:
        return (r.path, r.spans) if _moved(ledger, i) else None
    if verdict.outcome not in ('updated', 'updated and diverged') and r.state != 'moved':
        return None
    new = _suggestion(verdict, ledger)
    return (new.path, new.spans) if new and not _escapes(new.path) else None


def patch_edits(ledger: Ledger, verdicts: dict[str, Verdict], held=frozenset()) -> tuple[
        dict[str, dict[str, tuple[str, tuple[Span, ...]]]], dict[str, list[str]]]:
    '''
    the path and spans remap.patch gives each citation it edits, by kstack file and id, and the
    ids of the edits it leaves out, by folder: an edit is left out when a row in `held` owns the
    citation as written or its new path, since only a row that moves is re-imported, so remap.patch
    edits only citations in rows that move.
    '''
    edits: dict[str, dict[str, tuple[str, tuple[Span, ...]]]] = {}
    left: dict[str, list[str]] = {}
    for i, old in ledger.citations.items():
        to = _pointer(ledger, i, verdicts.get(i))
        if not to or to == (old.path, old.spans):
            continue
        rows = [ledger.sources.owner(old.label, p) for p in (old.path, to[0])]
        stay = [r for r in rows if r is not None and r.folder in held]
        if stay:
            left.setdefault(stay[0].folder, []).append(i)
        else:
            edits.setdefault(old.kfile, {})[i] = to
    return edits, left


def remap_patch(ledger: Ledger, verdicts: dict[str, Verdict], held=frozenset()) -> str:
    '''
    a unified diff against the commit scanned that changes only the path and line numbers inside
    citation parentheses: a moved citation with no verdict takes its head path and lines from the
    ledger, and a citation with a verdict takes the suggestion that held at the head, when the
    outcome is updated or the citation moved, so a verdict on a moved citation overrides the
    ledger. An edit into a row in `held` is left out, as `patch_edits` says. Each file's pairs are
    found in order, every pair from the end of the one before, and each edit keeps the whitespace
    and line breaks around and inside the parenthesis.
    '''
    edits, _ = patch_edits(ledger, verdicts, held)
    by_kfile: dict[str, list[Citation]] = {}
    for c in ledger.citations.values():
        if c.kfile in edits:
            by_kfile.setdefault(c.kfile, []).append(c)
    patch = []
    for kfile, wanted in sorted(edits.items()):
        before = git('show', f'{ledger.scanned}:{kfile}', cwd=REPO, strip=False)
        starts = [0] + [m.end() for m in re.finditer('\n', before)]
        cuts, at = [], 0
        for old in sorted(by_kfile[kfile], key=_order):
            m = _place(old, before, max(at, starts[min(old.kline, len(starts)) - 1]))
            if not m:
                continue
            at = m.end(2)
            if old.id not in wanted:
                continue
            path, spans = wanted[old.id]
            if path != old.path:
                cuts.append((m.start(1), m.end(1), path))
            if spans != old.spans:
                relined = _relined(m.group(2), old.spans, spans)
                start = back = m.start(2)
                while relined.startswith('\n') and before[back - 1] in ' \t':
                    back -= 1
                if relined.startswith('\n') and before[back - 1] == '\n':
                    relined = relined.lstrip()   # the list opens a line already
                elif relined.startswith('\n'):
                    start = back
                cuts.append((start, m.end(2), relined))
        after = before
        for a, b, new in sorted(cuts, reverse=True):
            after = after[:a] + new + after[b:]
        if after == before:
            continue
        lines = difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                     f'a/{kfile}', f'b/{kfile}')
        patch.append(f'diff --git a/{kfile} b/{kfile}\n')
        for line in lines:
            patch.append(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n')
    return ''.join(patch)


def pin_holds(ledger: Ledger, verdicts: dict[str, Verdict],
              failed: frozenset[str] = frozenset()) -> dict[str, str]:
    '''
    each row that stays at its pin, by folder, with why, as "Set the sync commit to the commit
    that you checked. Do not move the sync commit for a blocked check" asks: a row moves to its
    head unless its pin did not prove, its head was not fetched, or a citation into it, by the
    row that owns its path as written, is blocked. A citation is blocked when its verdict says
    blocked, when its suggestion is in `failed`, the ids whose suggestion failed `recheck`, or when
    no verdict judged it and its remap is neither `in sync` nor `moved` into a file the re-import
    copies, `stale` included, since an unjudged check has not been checked, or when `patch_edits`
    leaves its edit out because a held row owns its new path, since it cannot then be made true.
    '''
    out = {}
    for row in ledger.sources.imports:
        if ledger.proof.get(row.folder):
            out[row.folder] = 'the pin did not prove: ' + '; '.join(ledger.proof[row.folder][:3])
        elif not ledger.heads.get(row.url):
            out[row.folder] = 'the head was not fetched'
    why: dict[str, list[str]] = {}
    for i, c in ledger.citations.items():
        row = ledger.sources.owner(c.label, c.path)
        if row is None or row.folder in out:
            continue
        v, r = verdicts.get(i), ledger.remaps[i]
        if i in failed:
            reason = 'its suggestion failed the recheck at the head'
        elif v is not None:
            reason = 'blocked' if v.outcome == 'blocked' else None
        elif r.state == 'blocked':
            reason = 'blocked'
        elif r.state == 'moved' and not _moved(ledger, i):
            reason = f'no verdict, moved into {r.path}, which the re-import does not copy'
        else:
            reason = None if r.state in DECIDED else f'no verdict, {r.state} at the head'
        if reason:
            why.setdefault(row.folder, []).append(f'{i} ({reason})')
    while why:
        for folder, notes in why.items():
            out[folder] = 'a citation is blocked: ' + ', '.join(notes)
        why = {}
        for folder, ids in patch_edits(ledger, verdicts, frozenset(out))[1].items():
            for i in ids:
                c = ledger.citations[i]
                row = ledger.sources.owner(c.label, c.path)
                if row is not None and row.folder not in out:
                    why.setdefault(row.folder, []).append(
                        f'{i} (its edit is left out of remap.patch, since upstream/{folder} holds)')
    return {r.folder: out[r.folder] for r in ledger.sources.imports if r.folder in out}


def next_sources(ledger: Ledger, held: dict[str, str],
                 dates: dict[str, str] | None = None) -> Sources:
    '''
    the rows with each pin moved to its head, unless `held`, from `pin_holds`, holds it; `dates`
    gives each repository's head date.
    '''
    rows = [row if row.folder in held else dataclasses.replace(
        row, commit=ledger.heads[row.url], date=(dates or {}).get(row.url, row.date))
        for row in ledger.sources.imports]
    return Sources(rows, dict(ledger.sources.copies))


def reimport_plan(ledger: Ledger, moved: Sources, held: dict[str, str],
                  left: dict[str, list[str]] | None = None) -> str:
    '''
    the re-import at the moved pins, as Markdown. For each moving row it gives the copy, which
    leaves out each held row nested in it, every deletion and addition, and the edit to NOTICE and
    upstream/README.md, which `check` reads for every row's short commit. Where moving rows share a
    held row's short commit, that edit is given once, under the first of them: keep the old short
    commit for the held rows and add the new one for the moving rows. For each held row it gives
    why it stays at its pin, from `pin_holds`, and the citations `left`, from `patch_edits`, whose
    edit remap.patch leaves out.
    '''
    out = ['# Re-import at the moved pins', '']
    for old, new in zip(ledger.sources.imports, moved.imports):
        if old.folder in held:
            out += [f'## upstream/{old.folder}: stays at {old.commit[:7]}', '',
                    f'Held: {held[old.folder]}.', '']
            if (left or {}).get(old.folder):
                out += ['Edits left out of remap.patch, since this row holds: '
                        + ', '.join(f'`{i}`' for i in left[old.folder]) + '.', '']
            continue
        inside = [f'`upstream/{f}/`' for f in held if f.startswith(old.folder + '/')]
        out += [f'## upstream/{old.folder}: {old.commit[:7]} to {new.commit[:7]}', '',
                f'Copy `{new.path or "/"}` from {new.url} at {new.commit} into '
                f'`upstream/{new.folder}/`' + (', only the files imported now, at their new paths where upstream renamed '
                   'them, and each new SKILL.md' if new.partial else '')
                + (f', leaving out {", ".join(inside)}, which stays at its pin' if inside else '')
                + '.', '']
        keep = [f'`upstream/{r.folder}`' for r in ledger.sources.imports
                if r.folder in held and r.commit[:7] == old.commit[:7]]
        same = [o for o, n in zip(ledger.sources.imports, moved.imports)
                if o.folder not in held and o.commit[:7] == old.commit[:7]
                and n.commit[:7] == new.commit[:7]]
        if new.commit[:7] != old.commit[:7] and not keep:
            out += [f'- In `{f}`, change `{old.commit[:7]}` to `{new.commit[:7]}`.'
                    for f in ('NOTICE', 'upstream/README.md')] + ['']
        elif new.commit[:7] != old.commit[:7] and same[0] is not old:
            out += [f'- `NOTICE` and `upstream/README.md`: the edit under '
                    f'`upstream/{same[0].folder}` names this row.', '']
        elif new.commit[:7] != old.commit[:7]:
            add = ', '.join(f'`upstream/{o.folder}`' for o in same)
            out += [f'- In `{f}`, in each sentence that names `{old.commit[:7]}`, keep it for '
                    f'{", ".join(keep)}, which hold{"s" if len(keep) == 1 else ""}, and add '
                    f'`{new.commit[:7]}` for {add}, which move{"s" if len(same) == 1 else ""} '
                    'to it.' for f in ('NOTICE', 'upstream/README.md')] + ['']
        gone = [p for p in ledger.removed if ledger.sources.owner(*p.split('/', 1)) == old]
        out += [f'Deletions: {len(gone)}.', ''] + [f'- `upstream/{p}`' for p in gone] + ['']
        new_files = [a for a in ledger.added if a.folder == old.folder]
        out += [f'Additions: {len(new_files)}.', ''] + [
            f'- `upstream/{old.label()}/{a.path}`'
            + (f' (renamed from `upstream/{old.label()}/{a.renamed}`)' if a.renamed
               else ' (a new skill)' if a.skill else '')
            for a in new_files] + ['']
        for copy in ledger.copies:
            if ledger.sources.owner(*copy.source.split('/', 1)) == old and copy.at_head:
                out += [f'Copy `{copy.kfolder}` from `upstream/{copy.source}`: '
                        f'{len(copy.at_head)} files differ at the head, in `{copy.diff}`.', '']
    return '\n'.join(out)


def counts(ledger: Ledger, verdicts: dict[str, Verdict]) -> dict[str, int]:
    '''
    the number of citations per outcome and per mark, `stale at the pin`, `kept`, which a verdict
    alone decides, and `updated by the script`, a moved citation with no verdict, which counts as
    updated when the re-import copies its new file and has no verdict otherwise.
    '''
    out: dict[str, int] = {}
    for i, c in ledger.citations.items():
        r, v = ledger.remaps[i], verdicts.get(i)
        outcome = v.outcome if v else {'in sync': 'in sync', 'moved': 'updated',
                                       'blocked': 'blocked'}.get(r.state, 'no verdict')
        if not v and r.state == 'moved' and not _moved(ledger, i):
            outcome = 'no verdict'
        out[outcome] = out.get(outcome, 0) + 1
        if not v and _moved(ledger, i):
            out['updated by the script'] = out.get('updated by the script', 0) + 1
        if ledger.baseline[i].status not in PASS:
            out['stale at the pin'] = out.get('stale at the pin', 0) + 1
        if v and v.kept:
            out['kept'] = out.get('kept', 0) + 1
    return out


# ── commands ──────────────────────────────────────────────────────────────────

def _tally(values) -> str:
    '''a count per value, most first.'''
    seen: dict[str, int] = {}
    for v in values:
        seen[v] = seen.get(v, 0) + 1
    return ', '.join(f'{k} {n}' for k, n in sorted(seen.items(), key=lambda x: (-x[1], x[0])))


def cmd_check(argv: list[str]) -> int:
    '''
    the check command: sources.json, the prose pins, every citation against upstream/, and the
    declared copies, with no network; 0 with no finding, else 1 and one line per finding.
    '''
    try:
        sources = read_sources(SOURCES)
    except ValueError as e:
        print(f'finding: {e}')
        return 1
    citations, _, checks, findings = check_all(sources)
    print(f'check: {len(citations)} citation pairs in {len({c.kfile for c in citations})} files; '
          + _tally(c.status for c in checks.values()))
    for f in findings:
        print(f'finding: {f}')
    print(f'{len(findings)} findings' if findings else 'no finding')
    return 1 if findings else 0


def cmd_scan(argv: list[str]) -> int:
    '''
    the scan command: check, then the clones, proofs, remaps, copies and additions, into
    <run>/ledger.json and <run>/briefs/, whose old numbered briefs go first; 0 once written,
    blocked rows too, 1 if sources.json fails or a tracked file differs from HEAD, since the
    citations are read from the working tree and remap.patch applies to HEAD.
    '''
    if len(argv) != 1:
        print('usage: sync.py scan <run> [--repo <path>]')
        return 2
    dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=REPO,
                           capture_output=True, text=True)
    if dirty.returncode or dirty.stdout.strip():
        names = ', '.join(x[3:] for x in dirty.stdout.splitlines()) or dirty.stderr.strip()
        print(f'finding: scan reads the commit remap.patch applies to, and these tracked files '
              f'differ from HEAD: {names}; commit them first')
        return 1
    run = run_dir(argv[0])
    try:
        sources = read_sources(SOURCES)
    except ValueError as e:
        print(f'finding: {e}')
        return 1
    citations, unparsed, checks, findings = check_all(sources)
    for f in findings:
        print(f'finding: {f}')
    ledger = build_ledger(run, sources, citations, checks, unparsed)
    save(run, 'ledger.json', ledger)
    briefs = pack(ledger, run)
    for stale in (run / 'briefs').glob('*.md'):
        if stale.stem.isdigit():
            stale.unlink()
    for n, (_, text) in enumerate(briefs, 1):
        path = run / 'briefs' / f'{n}.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + '\n')
    for row in sources.imports:
        bad = ledger.proof.get(row.folder, [])
        n = len({c.sha for f in ledger.files.values() if f.folder == row.folder for c in f.commits})
        print(f'{row.folder}: {row.commit[:7]} to {ledger.heads.get(row.url, "")[:7]}, '
              + ('proved' if not bad else f'not proved ({len(bad)}: {bad[0]})')
              + f', {n} commits on cited or copied files')
    print(f'baseline: {_tally(c.status for c in ledger.baseline.values())}')
    print(f'at the head: {_tally(r.state for r in ledger.remaps.values())}')
    print(f'added: {len(ledger.added)} ({sum(a.skill and not a.renamed for a in ledger.added)} SKILL.md), '
          f'removed: {len(ledger.removed)}')
    print(f'briefs: {len(briefs)}, at most {CAP:,} bytes each but for a file over it alone'
          + ''.join(f'\n  briefs/{n}.md, {len(t.encode()):,} bytes: {", ".join(g)}'
                    for n, (g, t) in enumerate(briefs, 1)))
    print(f'ledger: {run / "ledger.json"}')
    return 0


def cmd_settle(argv: list[str]) -> int:
    '''
    the settle command: each verdict's citation rechecked against the head, then remap.patch,
    sources.next.json read back with `read_sources`, and reimport.md; 0 when every suggested
    citation held, else 1 and one line per citation that did not. A run folder with no ledger,
    or a verdict line `read_verdicts` refuses, is 1 and one line, with nothing written.
    '''
    if len(argv) != 1:
        print('usage: sync.py settle <run> [--repo <path>]')
        return 2
    run = run_dir(argv[0], create=False)
    if not (run / 'ledger.json').is_file():
        print(f'finding: {run} holds no ledger.json; run scan into it first')
        return 1
    ledger: Ledger = load(run, 'ledger.json')
    try:
        verdicts = read_verdicts(run)
    except ValueError as e:
        print(f'finding: {e}')
        return 1
    held, failed, wrong = {}, [], set()
    for i, v in verdicts.items():
        chk = recheck(v, ledger, run)
        if chk and chk.status not in PASS:
            failed.append(f'{i}: the {v.outcome} verdict suggests no citation, and updated means '
                          'the suggested citation points at the passage at the head'
                          if not (v.citation or '').strip() else
                          f'{i}: the suggested ({v.citation}) is {chk.status} at the head')
            held[i] = dataclasses.replace(v, outcome='blocked', citation=None)
            wrong.add(i)
        else:
            held[i] = v
    dates = {url: git('log', '-1', '--format=%cs', 'HEAD', cwd=clone_dir(run, url))
             for url in ledger.heads}
    stays = pin_holds(ledger, held, frozenset(wrong))
    (run / 'remap.patch').write_text(remap_patch(ledger, held, frozenset(stays)))
    _, left = patch_edits(ledger, held, frozenset(stays))
    moved = next_sources(ledger, stays, dates)
    (run / 'sources.next.json').write_text(json.dumps({
        'imports': [{k: v for k, v in dataclasses.asdict(r).items() if k != 'partial' or v}
                    for r in moved.imports], 'copies': moved.copies}, indent=1) + '\n')
    try:
        read_sources(run / 'sources.next.json')
    except ValueError as e:
        failed.append(f'sources.next.json does not read back: {e}')
    (run / 'reimport.md').write_text(reimport_plan(ledger, moved, stays, left) + '\n')
    for k, n in counts(ledger, held).items():
        print(f'{k}: {n}')
    for folder, why in stays.items():
        print(f'held at the pin: upstream/{folder}, {why}')
    for folder, ids in left.items():
        print(f'left out of remap.patch: upstream/{folder}, its row holds: {", ".join(ids)}')
    for f in failed:
        print(f'finding: {f}')
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    '''
    dispatch on the command named first.

    Parameters
    ----------
    argv : list of str
        the command line after the script's name; `--repo <path>` anywhere names the kstack
        checkout to read.

    Returns
    -------
    int
        the command's exit code, or 2, with this docstring printed, for an unknown command.
    '''
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 >= len(argv):
            print(__doc__)
            return 2
        use_repo(Path(argv[i + 1]))
        argv = argv[:i] + argv[i + 2:]
    commands = {'check': cmd_check, 'scan': cmd_scan, 'settle': cmd_settle}
    if not argv or argv[0] not in commands:
        print(__doc__)
        return 2
    return commands[argv[0]](argv[1:])


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
