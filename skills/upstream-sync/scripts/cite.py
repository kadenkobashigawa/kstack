'''
cite — kstack's citations: each one found in a markdown text, its quote found in an upstream
text, and each run against its file, as `check` runs every citation against upstream/.

Methods
-------
    flatten, find_parens, split_pairs, parse_lines, quote_before, kept_hint_after :
        the parts of a citation found in a text.
    parse_text, parse_with_starts, all_citations :
        every citation in one text, the same with where each parenthesis opens, and every
        citation in every tracked text.
    fmt_lines :
        spans written as kstack writes them.
    normalize, fragments, locate_quote :
        a passage compared, and a quote found in a text.
    run_citation, escapes, resolve, baseline, check_all :
        one citation run against one text, whether its path climbs out of its folder, the
        citation run against its file inside one copy, every citation against upstream/, and
        every finding.
'''

from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Iterator

import home
from home import check_copies, check_prose, inside, tracked_text
from model import PASS, Check, Citation, Sources, Span


TAG   = re.compile(r'\*\(kstack(?:, the translation)?: ')
CURLY = str.maketrans({'“': '"', '”': '"', '„': '"', '‘': "'", '’': "'"})
BLOCK = re.compile(r'([-*+]|\d+[.)]|#+|\||>|```|~~~)(\s|$)')
NUM   = r'\d+(?:\s*[–-]\s*\d+)?'


# ── citations ─────────────────────────────────────────────────────────────────

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


def split_pairs(inner: str, labels: set[str]) -> list[tuple[str | None, str, str, str]]:
    '''
    the label, path and rest of each `;`-separated pair in one parenthesis, with the part it came
    from as written, stripped; a pair that names only a path takes the label before it, and so
    does one whose path follows prose, `see `b.md`, l. 2`, when line numbers follow the path. A
    part that names a label and no path comes back with an empty path, and one that names
    neither, such as `Mayer, 2009`, or a path after prose with no line numbers, is prose and left
    out.
    '''
    names = '|'.join(re.escape(x) for x in sorted(labels, key=len, reverse=True))
    pairs, last = [], None
    for part in inner.split(';'):
        m = re.match(rf'\s*(?:({names}),\s*)?`([^`]+)`(.*)$', part, re.S)
        if m:
            last = m.group(1) or last
            pairs.append((last, m.group(2), m.group(3), part.strip()))
            continue
        m = re.match(rf'\s*({names}),', part)
        if m:
            last = m.group(1)
            pairs.append((last, '', part.strip(), part.strip()))
            continue
        m = re.match(r'[^`]*?`([^`]+)`(.*)$', part, re.S)
        if m and parse_lines(m.group(2)):
            pairs.append((last, m.group(1), m.group(2), part.strip()))
    return pairs


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


def kept_hint_after(flat: str, end: int) -> str | None:
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
    citations, unparsed, _ = parse_with_starts(kfile, text, labels)
    return citations, unparsed


def parse_with_starts(kfile: str, text: str, labels: set[str]) -> tuple[
        list[Citation], list[tuple[str, int, str]], list[int]]:
    '''`parse_text`, with the flattened offset of each citation's parenthesis beside it.'''
    flat, owner = flatten(text)
    citations, unparsed, on_line, starts = [], [], {}, []
    for start, end in find_parens(flat, labels):
        kline = owner[start]
        if end == start:
            unparsed.append((kfile, kline, flat[start:start + 80] + ' … left open'))
            continue
        quote, hint = quote_before(flat, start), kept_hint_after(flat, end)
        for label, path, rest, raw in split_pairs(flat[start + 1:end - 1], labels):
            lines = parse_lines(rest) if path else None
            if not label or not lines:
                unparsed.append((kfile, kline, flat[start:end]))
                continue
            on_line[kline] = n = on_line.get(kline, 0) + 1
            citations.append(Citation(f'{kfile}:{kline}:{n}', kfile, kline, label, path, lines[0],
                                      raw, lines[1], quote, hint))
            starts.append(start)
    return citations, unparsed, starts


def fmt_lines(spans: tuple[Span, ...]) -> str:
    '''spans written as kstack writes them: `l. 7`, `ll. 7–9` or `ll. 7, 12`.'''
    if len(spans) == 1 and spans[0].first == spans[0].last:
        return f'l. {spans[0].first}'
    return 'll. ' + ', '.join(f'{s.first}' if s.first == s.last else f'{s.first}–{s.last}'
                              for s in spans)


def all_citations(sources: Sources) -> tuple[list[Citation], list[tuple[str, int, str]]]:
    '''every citation in every tracked text, with the labels the rows name.'''
    labels = {row.label() for row in sources.imports}
    citations, unparsed = [], []
    for path in tracked_text():
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        found, bad = parse_text(str(path.relative_to(home.REPO)), text, labels)
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
def index(lines: tuple[str, ...], loose: bool) -> tuple[str, tuple[int, ...]]:
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


def quote_hits(quote: str, lines: tuple[str, ...],
               loose: bool) -> list[tuple[int, int, int, int]]:
    '''each place a quote's fragments sit in order: start and end offsets, first and last line.'''
    text, owner = index(lines, loose)
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
        found = quote_hits(quote, tuple(lines), loose)
        if found:
            return sorted({Span(a, b) for _, _, a, b in found}, key=lambda s: (s.first, s.last))
    return []


def _cited(lines: list[str], spans: tuple[Span, ...]) -> tuple[str, ...]:
    '''the lines a citation's spans name, the ones in range.'''
    return tuple(lines[n - 1] for s in spans for n in range(s.first, s.last + 1)
                 if 0 < n <= len(lines))


def text_at(lines: list[str] | None, spans: tuple[Span, ...]) -> str:
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
        if quote_hits(citation.quote, sub, loose):
            return Check(citation.id, status, (), against)
    found = locate_quote(citation.quote, lines)
    status = 'quote-elsewhere' if found else 'quote-missing'
    return Check(citation.id, status, tuple(found), against)


def read_lines(path: Path) -> list[str] | None:
    '''a file's lines, or None when it is not there or not text.'''
    try:
        return path.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeDecodeError):
        return None


def escapes(path: str) -> bool:
    '''whether a citation's path climbs out of its folder, by `..` or from the root.'''
    return path.startswith('/') or '..' in path.split('/')


def resolve(citation: Citation, root: Path, file: Path, against: str) -> Check:
    '''
    one citation run against its file in one copy, as `check` runs every citation against
    upstream/ and settle against the head: a path that `escapes`, or a file that is not inside
    the copy's `root`, is `file-missing`.
    '''
    if escapes(citation.path) or not inside(root, file):
        return Check(citation.id, 'file-missing', (), against)
    return run_citation(citation, read_lines(file), against)


def baseline(citations: list[Citation]) -> dict[str, Check]:
    '''every citation run against its file under upstream/, the copy at the pin, by citation id.'''
    up = home.UPSTREAM
    return {c.id: resolve(c, up / c.label, up / c.label / c.path, 'upstream/') for c in citations}


def check_all(sources: Sources) -> tuple[list[Citation], list[tuple[str, int, str]],
                                         dict[str, Check], list[str]]:
    '''every citation, the unparsed ones, each baseline check, and every finding `check` prints.'''
    readme = home.README.read_text() if home.README.is_file() else ''
    notice = home.NOTICE.read_text() if home.NOTICE.is_file() else ''
    findings = check_prose(sources, readme, notice)
    citations, unparsed = all_citations(sources)
    checks = baseline(citations)
    for c in citations:
        chk = checks[c.id]
        if chk.status not in PASS:
            where = ', '.join(f'{s.first}–{s.last}' for s in chk.found)
            findings.append(f'{c.kfile}:{c.kline}: ({c.raw}) {chk.status}'
                            + (f', the quote sits at {where}' if where else ''))
    findings += [f'{f}:{n}: does not parse: {t}' for f, n, t in unparsed]
    return citations, unparsed, checks, findings + check_copies(sources)
