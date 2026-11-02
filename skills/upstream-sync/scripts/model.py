'''
model — the types every part of sync reads and writes: the rows of upstream/sources.json, a
citation and its checks, the ledger a scan writes, and the verdict a judging agent returns.

Methods
-------
    decode :
        a JSON value read back into the type a field names, refused when it is not of that type.
'''

from __future__ import annotations

import dataclasses
import types
import typing
from typing import Literal


PASS    = {'ok', 'loose', 'paraphrase'}          # the statuses that hold
DECIDED = ('in sync', 'moved', 'blocked')        # the states settle reads from the ledger alone
UPDATED = ('updated', 'updated and diverged')    # the outcomes whose suggestion remap.patch takes


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
    kept_hint : str | None = None  # the nearest kstack tag after it, a hint for kept


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


def decode(tp, value):
    '''
    a JSON value read back into the type a field names.

    Parameters
    ----------
    tp : type
        a dataclass above, a `Literal`, a union with None, a list, set, tuple or dict of them, or
        a plain type such as `str` or `bool`.
    value : object
        the value as `json.loads` gives it: a dataclass as an object, a set or tuple as a list.

    Returns
    -------
    object
        the value as `tp`: each dataclass built, a dict's `int` keys read back from strings, and
        an `int` or `float` converted.

    Raises
    ------
    ValueError
        when the value is not of `tp`: None where `tp` takes no None, a string outside a
        `Literal`'s values, or a value not of its plain type.
    '''
    origin, args = typing.get_origin(tp), typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        for a in args:
            if a is not type(None):
                try:
                    return decode(a, value)
                except ValueError:
                    continue
        raise ValueError(tp)
    if value is None:
        raise ValueError(tp)
    if origin is Literal:
        if isinstance(value, str) and value in args:
            return value
        raise ValueError(tp)
    if dataclasses.is_dataclass(tp):
        if not isinstance(value, dict):
            raise ValueError(tp)
        hints = typing.get_type_hints(tp)
        return tp(**{f.name: decode(hints[f.name], value[f.name])
                     for f in dataclasses.fields(tp) if f.name in value})
    if origin in (list, set, tuple):
        if not isinstance(value, list):
            raise ValueError(tp)
        if origin is list:
            return [decode(args[0], x) for x in value]
        if origin is set:
            return {decode(args[0], x) for x in value}
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(decode(args[0], x) for x in value)
        return tuple(decode(a, x) for a, x in zip(args, value))
    if origin is dict:
        if not isinstance(value, dict):
            raise ValueError(tp)
        return {decode(args[0], k): decode(args[1], v) for k, v in value.items()}
    if tp is int or tp is float:
        return tp(value)
    if isinstance(value, tp):
        return value
    raise ValueError(tp)
