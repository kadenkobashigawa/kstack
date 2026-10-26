#!/usr/bin/env python3
'''
report — read one report written in Markdown into a numbered tree, and render it to pdf and html.

    python3 report.py REPORT.md [--out BASE] [--check]

writes REPORT.pdf and REPORT.html beside REPORT.md, or BASE.pdf and BASE.html. --check only
confirms chrome and pdftotext. every fault exits 1 with one line naming the file, the line and
the fix. references/format.md is the input dialect this file reads.

Methods
-------
    ReportError :
        a fault in the input, carrying the file and line that caused it.
    Line :
        one source line and where it came from, so an included file's errors name that file.
    Meta :
        the front matter: title, author, release, date and an optional wordmark.
    Section :
        one numbered ## or ### heading and its blocks.
    Part :
        one # heading: a chapter, the references, an appendix or the glossary.
    Report :
        the whole report: its meta and its parts in file order.
    slug :
        the anchor name a heading answers to in a [text](#slug) link.
    front_matter :
        split the --- fenced key: value block off the text and check its keys.
    expand :
        replace each !include line with the lines of the file it names, recursively.
    split_parts :
        cut the body at each # heading and classify each part by its title.
    number :
        assign chapter numbers, appendix letters and the glossary's letter, and check their order.
    resolve_links :
        turn each [text](#slug) in a run of text into a link carrying the heading's number.
    blocks :
        read a run of markdown lines into blocks.
    parse :
        read one report file, and the files it includes, into a Report.
    main :
        preflight, parse, render, and print the page count.
'''

from __future__ import annotations

import argparse
import base64
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NamedTuple



KEYS     = ('title', 'author', 'release', 'date', 'wordmark')
REQUIRED = ('title', 'author', 'release', 'date')
ORDER    = {'chapter': 0, 'references': 1, 'appendix': 2, 'glossary': 3}
NOTES    = {'NOTE': 'Note', 'EXAMPLE': 'Example', 'WARNING': 'Warning'}
IMAGES   = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.gif': 'image/gif', '.webp': 'image/webp'}
INCLUDE  = re.compile(r'!include\s+(\S.*?)\s*')
HEADING  = re.compile(r'(#+) +(.*?)\s*')
FIGURE   = re.compile(r'!\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\(([^)\s]+)\)\s*')
LINK     = re.compile(r'`[^`]*`|(?<!!)\[([^\]]+)\]\(([^)\s]+)\)')
TERM     = re.compile(r'\*\*(.+?)\*\*\s*(?:—|–|:)\s*(.+)', re.S)


class ReportError(Exception):
    '''a fault in the input, carrying the file and line that caused it.'''

    def __init__(self, path: Path, line: int, message: str):
        super().__init__(f'{path}:{line}: {message}')
        self.path    = path
        self.line    = line
        self.message = message


class Line(NamedTuple):
    '''one source line and where it came from, so an included file's errors name that file.'''

    text: str
    path: Path
    no:   int


@dataclass(frozen=True)
class Meta:
    '''the front matter: title, author, release, date and an optional wordmark.'''

    title:    str
    author:   str
    release:  str
    date:     str
    wordmark: Path | None


@dataclass(frozen=True)
class Section:
    '''one numbered ## or ### heading and its blocks.'''

    level:  int
    number: str
    title:  str
    slug:   str
    anchor: str
    blocks: list


@dataclass(frozen=True)
class Part:
    '''one # heading: a chapter, the references, an appendix or the glossary.'''

    kind:     Literal['chapter', 'references', 'appendix', 'glossary']
    number:   str
    title:    str
    slug:     str
    anchor:   str
    intro:    list
    sections: list[Section]


@dataclass(frozen=True)
class Report:
    '''the whole report: its meta and its parts in file order.'''

    meta:   Meta
    parts:  list[Part]
    source: Path


def slug(title: str) -> str:
    '''the anchor name a heading answers to: lowercase, punctuation dropped, spaces as hyphens.'''
    s = re.sub(r'[^\w\s-]', '', title.lower())
    return re.sub(r'\s+', '-', s.strip())


# ── front matter and includes ────────────────────────────────────────────────

def front_matter(path: Path, text: str) -> tuple[Meta, int]:
    '''
    split the front matter off a report.

    Parameters
    ----------
    path : Path
        the report, for error messages and to resolve wordmark against.
    text : str
        the whole file.

    Returns
    -------
    tuple
        (meta, index of the first body line).

    Notes
    -----
    raises ReportError on a file that does not open with ---, front matter with no closing ---, a
    line that is not key: value, a missing required key, an unknown or repeated key, or a
    wordmark that is not an svg file or has no viewBox. a hand parser, not yaml: one key: value
    per line.
    '''
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        raise ReportError(path, 1, 'no front matter: open the file with a --- line, then '
                                   'title:, author:, release: and date:, then ---')
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == '---')
    except StopIteration:
        raise ReportError(path, 1, 'front matter has no closing --- line') from None
    found = {}
    for i in range(1, end):
        if not lines[i].strip():
            continue
        m = re.fullmatch(r'(\w+):\s*(.*?)\s*', lines[i])
        if not m:
            raise ReportError(path, i + 1, f'not a key: value line: {lines[i]!r}')
        key, value = m[1], m[2]
        if key not in KEYS:
            raise ReportError(path, i + 1, f'unknown front matter key {key!r}; '
                                           f'the keys are {", ".join(KEYS)}')
        if key in found:
            raise ReportError(path, i + 1, f'front matter key {key!r} is given twice')
        found[key] = (value, i + 1)
    missing = [k for k in REQUIRED if not found.get(k, ('',))[0]]
    if missing:
        raise ReportError(path, 1, f'front matter is missing {", ".join(missing)}')
    wordmark = None
    if found.get('wordmark', ('',))[0]:
        value, no = found['wordmark']
        wordmark = (path.parent / value).resolve()
        if wordmark.suffix.lower() != '.svg' or not wordmark.is_file():
            raise ReportError(path, no, f'wordmark {value} is not an svg file beside the report '
                                        f'(looked for {wordmark})')
        root = re.search(r'<svg\b[^>]*>', wordmark.read_text())
        if not root or 'viewBox' not in root[0]:
            raise ReportError(path, no, f'wordmark {value} has no viewBox; run '
                                        'scripts/wordmark.py on it first')
    meta = Meta(*(found[k][0] for k in REQUIRED), wordmark=wordmark)
    return meta, end + 1


def expand(lines: list[Line], stack: tuple[Path, ...]) -> list[Line]:
    '''
    replace each !include line with the lines of the file it names, recursively.

    Parameters
    ----------
    lines : list of Line
        one file's body lines.
    stack : tuple of Path
        the files being included right now, outermost first, to catch a cycle.

    Returns
    -------
    list of Line
        the lines with every include spliced in, each still naming its own file and line.

    Notes
    -----
    a path resolves against the including file's folder. an include inside a code fence stays
    text. raises ReportError at the include line for a missing file, a cycle, or an included file
    that opens with front matter, and at the opening fence for a fence a file leaves unclosed.
    *(kstack: one numbering pass reads the spliced lines, so a split report numbers the same as
    one file.)*
    '''
    out, fence = [], None
    for line in lines:
        if line.text.startswith('```'):
            fence = None if fence else line
        m = None if fence else INCLUDE.fullmatch(line.text)
        if not m:
            out.append(line)
            continue
        target = (line.path.parent / m[1]).resolve()
        if not target.is_file():
            raise ReportError(line.path, line.no, f'!include {m[1]}: no such file ({target})')
        if target in stack:
            chain = ' -> '.join(p.name for p in stack[stack.index(target):] + (target,))
            raise ReportError(line.path, line.no, f'!include {m[1]} makes a cycle: {chain}')
        text = target.read_text().splitlines()
        if text and text[0].strip() == '---':
            raise ReportError(line.path, line.no, f'!include {m[1]}: an included file has no '
                                                  'front matter; only the main file carries it')
        out += expand([Line(t, target, i) for i, t in enumerate(text, 1)], stack + (target,))
    if fence:
        raise ReportError(fence.path, fence.no, 'code fence is never closed')
    return out


# ── structure and numbering ──────────────────────────────────────────────────

def split_parts(lines: list[Line]) -> list[tuple]:
    '''
    cut the body at each # heading.

    Parameters
    ----------
    lines : list of Line
        the body lines, includes already spliced in.

    Returns
    -------
    list
        (kind, title, line, intro lines, [(level, title, line, lines)]) per # heading, unnumbered;
        level is 2 for ## and 3 for ###. #### and deeper stay in the lines as unnumbered headings.

    Notes
    -----
    raises ReportError on text before the first # heading, or an empty appendix title.
    '''
    parts, body, fence = [], None, False
    for line in lines:
        if line.text.startswith('```'):
            fence = not fence
        m = None if fence else HEADING.fullmatch(line.text)
        if m and len(m[1]) == 1:
            title = m[2]
            kind = {'References': 'references', 'Glossary': 'glossary'}.get(title, 'chapter')
            if title.startswith('Appendix:'):
                kind, title = 'appendix', title[len('Appendix:'):].strip()
                if not title:
                    raise ReportError(line.path, line.no, 'an appendix needs a title: '
                                                          '# Appendix: <title>')
            body = []
            parts.append((kind, title, line, body, []))
        elif parts and m and len(m[1]) in (2, 3):
            body = []
            parts[-1][4].append((len(m[1]), m[2], line, body))
        elif parts:
            body.append(line)
        elif line.text.strip():
            raise ReportError(line.path, line.no, 'text before the first # heading; every '
                                                  'report starts with a # chapter')
    return parts


def number(raw: list[tuple]) -> list[tuple[str, list[str]]]:
    '''
    assign every part and section its number, and check the reserved parts' order.

    Parameters
    ----------
    raw : list of tuple
        split_parts' output.

    Returns
    -------
    list
        (part number, [section numbers]) per raw part: chapters 1..n, then the references
        numbered n+1, then appendices A, B, ..., then the glossary lettered after the last
        appendix; ## and ### under a part number as 2.1 and 2.1.3.

    Notes
    -----
    the one place numbers and letters are decided. raises ReportError when a reserved part is out
    of order or repeated, or a ### has no ## above it.
    '''
    out, chapters, letters, stage = [], 0, 0, 0
    for kind, title, where, _, sections in raw:
        if ORDER[kind] < stage or (ORDER[kind] == stage and kind in ('references', 'glossary')):
            raise ReportError(where.path, where.no, f'"{where.text}" is out of order: chapters, '
                              'then one References, then appendices, then one Glossary')
        stage = ORDER[kind]
        if kind == 'chapter':
            chapters += 1
            num = str(chapters)
        elif kind == 'references':
            num = str(chapters + 1)
        else:
            num = chr(ord('A') + letters)
            letters += 1
        counts, nums = [0, 0], []
        for level, _, line, _ in sections:
            if level == 2:
                counts = [counts[0] + 1, 0]
            elif counts[0] == 0:
                raise ReportError(line.path, line.no, '### with no ## above it in this part')
            else:
                counts[1] += 1
            nums.append('.'.join([num] + [str(c) for c in counts[:level - 1]]))
        out.append((num, nums))
    return out


def resolve_links(text: str, where: list[Line], targets: dict) -> str:
    '''
    rewrite each [text](#slug) as a link to the heading's anchor followed by its number.

    Parameters
    ----------
    text : str
        a run of markdown, its lines joined with newlines.
    where : list of Line
        the source line of each line of text, so an error names the file and line the link sits
        on, also when a paragraph runs across an include.
    targets : dict
        each slug to a list of (anchor, label, Line) for every heading that has it.

    Returns
    -------
    str
        the text, with "[Scope](#scope)" turned into "[Scope](#s-1-1-1) (1.1.1)".

    Notes
    -----
    a link inside a `code` span is text and stays. http(s) and mailto links pass through.
    raises ReportError on an unknown slug, a slug two headings share, or any other link, which
    would be dead in the pdf.
    '''
    def to(m):
        if m[0].startswith('`'):
            return m[0]
        at = where[min(text[:m.start()].count('\n'), len(where) - 1)]
        href = m[2]
        if re.match(r'(https?|mailto):', href):
            return m[0]
        if not href.startswith('#'):
            raise ReportError(at.path, at.no, f'link {href} is dead in the pdf; link a heading '
                                              'as (#slug) or give a full https:// address')
        hits = targets.get(href[1:], [])
        if not hits:
            raise ReportError(at.path, at.no, f'no heading has the slug {href}; a slug is the '
                                              'heading lowercased, punctuation dropped, '
                                              'spaces as hyphens')
        if len(hits) > 1:
            lines = ', '.join(f'{h[2].path.name}:{h[2].no}' for h in hits)
            raise ReportError(at.path, at.no, f'{href} names {len(hits)} headings ({lines}); '
                                              'reword one of them')
        anchor, label, _ = hits[0]
        return f'[{m[1]}](#{anchor}) ({label})'

    return LINK.sub(to, text)


# ── blocks ───────────────────────────────────────────────────────────────────

def _items(chunk: list[Line]) -> list:
    '''split a list's lines into items, each [lines, nested], nested None or (kind, [lines]).'''
    items, nested = [], None
    for line in chunk:
        top = re.match(r'(?:-|\d+\.) (.*)', line.text)
        sub = re.match(r'\s{2,}(-|\d+\.) (.*)', line.text)
        if top:
            items.append([[line._replace(text=top[1])], None])
            nested = None
        elif sub:
            if nested is None:
                nested = []
                items[-1][1] = ('ul' if sub[1] == '-' else 'ol', nested)
            nested.append([line._replace(text=sub[2])])
        elif nested:
            nested[-1].append(line._replace(text=line.text.strip()))
        else:
            items[-1][0].append(line._replace(text=line.text.strip()))
    return items


def _figure(where: Line, caption: str, href: str) -> tuple:
    '''a figure block whose art is inline svg or a data: uri; raises ReportError otherwise.'''
    if re.match(r'\w+:', href):
        raise ReportError(where.path, where.no, f'figure {href} is not a local file; save it '
                                                'beside the report and name it by path')
    file = (where.path.parent / href).resolve()
    if not file.is_file():
        raise ReportError(where.path, where.no, f'figure {href}: no such file ({file})')
    kind = file.suffix.lower()
    if kind == '.svg':
        svg = file.read_text()
        start = svg.find('<svg')
        if start < 0:
            raise ReportError(where.path, where.no, f'figure {href} holds no <svg> element')
        return ('figure', caption, svg[start:].strip())
    if kind not in IMAGES:
        raise ReportError(where.path, where.no, f'figure {href}: use svg, png, jpg, gif or webp')
    data = base64.b64encode(file.read_bytes()).decode()
    alt = caption.replace('&', '&amp;').replace('"', '&quot;')
    return ('figure', caption, f'<img src="data:{IMAGES[kind]};base64,{data}" alt="{alt}">')


def blocks(lines: list[Line], targets: dict) -> list:
    '''
    read a run of markdown lines into blocks.

    Parameters
    ----------
    lines : list of Line
        the lines under one heading.
    targets : dict
        the slug table resolve_links reads.

    Returns
    -------
    list
        Block tuples in order: ('p', text), ('ul' | 'ol', items, lines), ('note', kind, text),
        ('table', caption, head, rows), ('figure', caption, art), ('code', src),
        ('heading', text) and ('break',). a list's lines hold each item's first Line.

    Notes
    -----
    paragraphs, - and 1. lists with one nested level, ``` code, pipe tables captioned by a
    "Table: caption" line above, > [!NOTE], [!EXAMPLE] and [!WARNING] boxes, #### headings that
    stay unnumbered, ![caption](file) figures and a --- page break. a caption is one line, and the
    next block after it is its table. every link, in a caption too, resolves against the Line it
    sits on. raises ReportError on a figure that is remote, missing or of an unknown type, an
    unknown box kind, a caption no table follows, a table with no header row or a bad link.
    '''
    out, caption, i = [], None, 0

    def link(where):
        return resolve_links('\n'.join(ln.text for ln in where), where, targets)

    while i < len(lines):
        line = lines[i]
        text = line.text
        if not text.strip():
            i += 1
            continue
        if caption and not text.startswith('|'):
            raise ReportError(caption.path, caption.no, f'"{caption.text}" has no table after '
                                                        'it; put the | rows on the next lines')
        m = HEADING.fullmatch(text)
        if m:
            out.append(('heading', link([line._replace(text=m[2])])))
            i += 1
            continue
        if text.startswith('```'):
            end = next(j for j in range(i + 1, len(lines)) if lines[j].text.startswith('```'))
            out.append(('code', '\n'.join(ln.text for ln in lines[i + 1:end])))
            i = end + 1
            continue
        if text.strip() == '---':
            out.append(('break',))
            i += 1
            continue
        fig = FIGURE.fullmatch(text)
        if fig:
            art = _figure(line, fig[1], fig[2])[2]
            out.append(('figure', link([line._replace(text=fig[1])]), art))
            i += 1
            continue
        if text.startswith('Table: '):
            caption = line
            i += 1
            continue
        end = i + 1
        while (end < len(lines) and lines[end].text.strip()
               and not lines[end].text.startswith(('#', '```', '![', 'Table: '))
               and lines[end].text.strip() != '---'):
            end += 1
        chunk, i = lines[i:end], end
        if text.startswith('|'):
            rows = []
            for ln in chunk:
                if re.fullmatch(r'\|[\s:|-]+\|', ln.text.strip()):
                    continue
                cells = [c.strip() for c in ln.text.strip().strip('|').split('|')]
                rows.append([link([ln._replace(text=c)]) for c in cells])
            if not rows:
                raise ReportError(line.path, line.no, 'a table needs a header row of | cells '
                                                      'above its |---| line')
            title = link([caption._replace(text=caption.text[len('Table: '):])]) if caption else ''
            out.append(('table', title, rows[0], rows[1:]))
            caption = None
        elif text.startswith('>'):
            body = [ln._replace(text=re.sub(r'^> ?', '', ln.text)) for ln in chunk]
            kind = re.fullmatch(r'\[!(\w+)\]', body[0].text.strip())
            if kind and kind[1].upper() not in NOTES:
                raise ReportError(line.path, line.no, f'box [!{kind[1]}] is not one of '
                                                      '[!NOTE], [!EXAMPLE], [!WARNING]')
            content = body[1:] if kind else body
            out.append(('note', NOTES[kind[1].upper()] if kind else 'Note',
                        link(content) if content else ''))
        elif re.match(r'(-|\d+\.) ', text):
            raw = _items(chunk)
            items = [link(t) if n is None else (link(t), (n[0], [link(s) for s in n[1]]))
                     for t, n in raw]
            out.append(('ul' if text.startswith('-') else 'ol', items, [t[0] for t, _ in raw]))
        else:
            out.append(('p', link(chunk)))
    if caption:
        raise ReportError(caption.path, caption.no, f'"{caption.text}" has no table after it; '
                                                    'put the | rows on the next lines')
    return out


def _glossary(where: Line, intro: list) -> list:
    '''the glossary's one list as ('glossary', [(term, definition)]); raises ReportError.'''
    lists = [b for b in intro if b[0] == 'ul']
    if len(lists) != 1 or len(intro) != 1:
        raise ReportError(where.path, where.no, 'Glossary holds one - list of '
                                                '**term** — definition items and nothing else')
    terms = []
    for item, at in zip(lists[0][1], lists[0][2]):
        m = TERM.fullmatch(item if isinstance(item, str) else item[0])
        if not m:
            raise ReportError(at.path, at.no, f'glossary item {item!r} is not '
                                              '**term** — definition')
        terms.append((m[1], m[2]))
    return [('glossary', terms)]


# ── the whole report ─────────────────────────────────────────────────────────

def parse(path: Path) -> Report:
    '''
    read one report file, and the files it includes, into a Report.

    Parameters
    ----------
    path : Path
        the report's main file.

    Returns
    -------
    Report
        the meta and the numbered parts, every link resolved.

    Notes
    -----
    raises ReportError naming the file and line of the first fault: an empty report, a
    References or Glossary with ## sections, References with no numbered list, and every fault
    the steps it calls raise.
    '''
    path = Path(path).resolve()
    text = path.read_text()
    meta, start = front_matter(path, text)
    body = [Line(t, path, i) for i, t in enumerate(text.splitlines()[start:], start + 1)]
    raw = split_parts(expand(body, (path,)))
    if not raw:
        raise ReportError(path, start + 1, 'the report has no # chapter')
    numbers = number(raw)

    #every heading's slug, anchor and label, so links can point forward as well as back...
    targets = {}
    for (kind, title, where, _, sections), (num, nums) in zip(raw, numbers):
        word = 'Chapter' if kind in ('chapter', 'references') else 'Appendix'
        heads = [(f'Appendix: {title}' if kind == 'appendix' else title, num, f'{word} {num}',
                  where)]
        heads += [(t, n, n, line) for (_, t, line, _), n in zip(sections, nums)]
        for t, n, label, line in heads:
            targets.setdefault(slug(t), []).append(('s-' + n.replace('.', '-'), label, line))

    parts = []
    for (kind, title, where, intro, sections), (num, nums) in zip(raw, numbers):
        if kind in ('references', 'glossary') and sections:
            raise ReportError(sections[0][2].path, sections[0][2].no,
                              f'{title} takes no ## sections')
        head = blocks(intro, targets)
        if kind == 'references' and not any(b[0] == 'ol' for b in head):
            raise ReportError(where.path, where.no, 'References holds one numbered list')
        if kind == 'glossary':
            head = _glossary(where, head)
        secs = [Section(level, n, t, slug(t), 's-' + n.replace('.', '-'), blocks(lines, targets))
                for (level, t, _, lines), n in zip(sections, nums)]
        name = f'Appendix: {title}' if kind == 'appendix' else title
        parts.append(Part(kind, num, title, slug(name), 's-' + num, head, secs))
    return Report(meta, parts, path)


def main(argv: list[str] | None = None) -> int:
    '''
    preflight, parse, render, and print the page count.

    Parameters
    ----------
    argv : list of str, optional
        the arguments after the program name; None reads sys.argv.

    Returns
    -------
    int
        0 on success; 1 with one line on stderr naming the fault.

    Notes
    -----
    the preflight runs before parse, so a missing chrome is reported before any input error.
    '''
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import theme

    ap = argparse.ArgumentParser(prog='report.py', description=__doc__.split('\n\n')[0])
    ap.add_argument('report', nargs='?', type=Path, help='the report .md file')
    ap.add_argument('--out', type=Path, help='output path without extension')
    ap.add_argument('--check', action='store_true', help='only confirm chrome and pdftotext')
    args = ap.parse_args(argv)
    try:
        chrome = theme.preflight()
        if args.check:
            print(f'chrome: {chrome}\npdftotext: found')
            return 0
        if not args.report:
            ap.error('name the report .md file')
        report = parse(args.report)
        out = (args.out or report.source.with_suffix('')).resolve()
        pages = theme.build(report, out)
    except (ReportError, theme.ToolMissing, theme.RenderError) as e:
        print(f'report.py: {e}', file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f'report.py: no such file: {e.filename}', file=sys.stderr)
        return 1
    print(f'{out.name}.pdf: {pages} pages, and {out.name}.html')
    return 0


if __name__ == '__main__':
    sys.exit(main())
