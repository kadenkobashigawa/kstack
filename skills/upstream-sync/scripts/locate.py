'''
locate — one citation's passage found at the head: through the line map from pin to head, by its
quote in the head file and then across its row's head files, and last by a fuzzy match scored
with Hypothesis's weights.

Methods
-------
    line_map :
        each pin line's head line.
    anchor :
        a citation's passage as a W3C Text Quote Selector.
    similar, score :
        how much of one text another holds in order, and how well a head span matches an anchor.
    search_row, fuzzy :
        every head file and span under a row that holds an anchor's text, and the best close span.
    remap :
        one citation's passage found at the head.
'''

from __future__ import annotations

import bisect
import dataclasses
import difflib
from pathlib import Path

from cite import fragments, index, locate_quote, normalize, quote_hits, read_lines, run_citation
from cite import text_at
from model import PASS, Anchor, Check, Citation, Import, Remap, Span, UpstreamFile


WEIGHTS  = {'quote': 50, 'prefix': 20, 'suffix': 20, 'position': 2}   # Hypothesis match-quote
CONTEXT  = 32      # characters of pin text kept on each side of a quote
REWORDED = 0.6     # a similarity at or above it is reworded, below it gone; tune on real drift


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
    text, owner = index(tuple(pin), False)
    first, last = citation.spans[0].first, citation.spans[-1].last
    if citation.quote and fragments(citation.quote):
        found = quote_hits(citation.quote, tuple(pin), False)
        inside = [h for h in found if first <= h[2] and h[3] <= last] or found
        if inside:
            start, end = inside[0][0], inside[0][1]
            return Anchor(normalize(citation.quote), text[max(0, start - CONTEXT):start],
                          text[end:end + CONTEXT])
        exact = normalize(citation.quote)
    else:
        exact = text_at(pin, citation.spans)
    start = bisect.bisect_left(owner, first)
    end = bisect.bisect_right(owner, last)
    return Anchor(exact, text[max(0, start - CONTEXT):start].strip(),
                  text[end:end + CONTEXT].strip())


def similar(a: str, b: str) -> float:
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
    text, owner = index(tuple(lines), False)
    start = bisect.bisect_left(owner, span.first)
    end = bisect.bisect_right(owner, span.last)
    here = text[start:end].strip()
    quote = 1.0 if target.exact and target.exact in here else similar(target.exact, here)
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
        lines = read_lines(where / name)
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
            here = text_at(lines, (span,))
            if not here or len(words & set(here.split())) < REWORDED * len(words):
                continue
            if similar(target.exact, here) < REWORDED:
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
    old = text_at(pin, citation.spans)
    done = lambda state, found, path, spans, lines, s: Remap(
        citation.id, state, found, path, tuple(spans), old, text_at(lines, tuple(spans)), s)
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
                        similar(old, text_at(head, spans)))
    locator = citation.quote if citation.quote and fragments(citation.quote) else None
    pin_at = citation.spans[0].first
    if locator:
        at = [h for h in quote_hits(locator, tuple(pin), False)
              + quote_hits(locator, tuple(pin), True)
              if citation.spans[0].first <= h[2] <= citation.spans[-1].last]
        pin_at = at[0][2] if at else pin_at

    def placed(lines: list[str], hits: list[Span]) -> list[tuple[Span, ...]]:
        out = []
        for hit in hits:
            spans = tuple(Span(s.first + hit.first - pin_at, s.last + hit.first - pin_at)
                          for s in citation.spans)
            if spans[0].first < 1 or spans[-1].last > len(lines):
                continue
            if locator or all(text_at(lines, (a,)) == text_at(pin, (b,))
                              for a, b in zip(spans, citation.spans)):
                out.append(spans)
        return out

    def best(lines: list[str], options: list[tuple[Span, ...]], hint: int | None):
        return max(options, key=lambda sp: score(target, lines, Span(sp[0].first, sp[-1].last),
                                                 hint))

    def holds(path: str, spans: tuple[Span, ...], lines: list[str]) -> bool:
        moved = dataclasses.replace(citation, path=path, spans=spans)
        return run_citation(moved, lines, 'head').status in PASS

    seek = locator or text_at(pin, citation.spans[:1])
    if head is not None:
        options = placed(head, locate_quote(seek, head))
        if options:
            spans = best(head, options, near)
            same = spans == citation.spans and file.head_path == citation.path
            if same or not holds(file.head_path, spans, head):
                return done('edited', 'quote', file.head_path, spans, head,
                            similar(old, text_at(head, spans)))
            return done('moved', 'quote', file.head_path, spans, head, 1.0)
    elsewhere: dict[str, list[Span]] = {}
    for path, span in search_row(where, row, Anchor(seek, '', '')):
        if path != file.head_path:
            elsewhere.setdefault(path, []).append(span)
    found = []
    for path, hits in elsewhere.items():
        lines = read_lines(where / row.repo_path(path)) or []
        found += [(score(target, lines, Span(sp[0].first, sp[-1].last), None), path, sp, lines)
                  for sp in placed(lines, hits)]
    if found:
        _, path, spans, lines = max(found, key=lambda x: x[0])
        if not holds(path, spans, lines):
            return done('edited', 'quote-elsewhere', path, spans, lines,
                        similar(old, text_at(lines, spans)))
        return done('moved', 'quote-elsewhere', path, spans, lines, 1.0)
    if head is not None:
        hit = fuzzy(target, head, near, 1 if locator else
                    sum(s.last - s.first + 1 for s in citation.spans))
        if hit:
            return done('edited', 'fuzzy', file.head_path, (hit[0],), head, hit[1])
    return done('gone', 'none', file.head_path, (), None, 0.0)
