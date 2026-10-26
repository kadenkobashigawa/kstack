#!/usr/bin/env python3
"""
test_report — checks write-report's parser, numbering, includes, links, html, tool discovery and
wordmark flattening, and renders the example report for real when Chrome is installed.

Run it with `python3 skills/write-report/tests/test_report.py`. It writes only inside one
tempfile folder, which it removes. The exit code is the number of failed checks.

R1 holds the front matter: a missing date, an unknown key, a missing wordmark file and a missing
front matter each name what is wrong. R2 numbers three chapters 1 to 3, the references 4, two
appendices A and B and the glossary C, with sections under each and a ### count that restarts
under each ##. R3 refuses an appendix before a chapter, a second glossary, a chapter after the
references and a ### with no ## above it, each at its line. R4 resolves links: a section link
carries its number, a chapter and an appendix link carry their names, and an unknown slug, a
relative file link and a slug two headings share each stop the build at the link's line, while a
shared slug nobody links is fine. R5 parses every fenced markdown example in
references/format.md. R6 keeps #### unnumbered, reads --- as a page break, ignores # inside a code
fence and leaves a link inside a code span alone. R7 refuses a glossary item that is not
**term** — definition, and references with no numbered list. R8 reads a Table: caption as one
line, directly or a blank line above its table, and refuses a caption no table follows and a table
of separator rows only, each at its line. R9 resolves links in table and figure captions, refusing
a dead or javascript: link, and keeps brackets in a figure caption. R10 names the line a fault sits
on: a list item past the first, an item's second line, a nested item, a box's content, a glossary
item, and a line after an include, in its own file. R11 refuses a wordmark with no viewBox, a
remote, missing or unknown-type figure, an unknown box kind, ## under References or Glossary, text
before the first # and an empty report.

I1 splices an included file: numbering runs on across it, its path and its figure resolve against
its own folder, and a link from the main file reaches a heading in it. I2 names the including file
and line for a missing include, I3 for a cycle, and I4 for an included file with front matter. I5
leaves an !include inside a code fence as text, and I6 names the file and line of a fence an
included file leaves open.

T1 holds that html with no wordmark has no logo element and keeps the title page. T2 holds that
html with a wordmark inlines it with no file:// and no source path, sized from its aspect. T3
finds chrome at $CHROME first, then the mac path, then PATH, names a $CHROME that is not a file,
and lists every place when there is none. T4 refuses a missing pdftotext by name. T5 title-cases
headings and leaves code, digits and capitals alone. T6 holds the html headings title-cased from a
sentence-case source. T7 holds the cli's one-line error and exit code. T8 escapes quotes, < and
</style> in the title, the release, link and bare addresses, a caption and the wordmark's label,
so no input text closes an attribute or the style sheet. T9 raises RenderError for a chrome that
fails or writes no pdf, and holds that chrome prints with a throwaway profile in the temp folder.
T10 stubs the prints and raises RenderError, writing nothing, for page numbers that never settle,
a lost marker and an unmarked print that differs, and holds that each build draws its own marker
token.

W1 keeps the hole in an O-shaped path whatever way its two subpaths were drawn: the winding number
is zero inside the counter and nonzero in the ring, the outline runs clockwise and the hole
counterclockwise, and a curve walked backwards traces the same outline. W2 winds two abutting
squares the same way, so their seam closes, also when one starts on the edge they share. W3
refuses a <rect>, a stroke, an arc and a skew, naming each. W4 reads relative and H/V commands as
their absolute equivalent. W5 refuses a <style> element, a class attribute, and a stroke set on a
parent group, in a group's style or on the svg; a path takes its group's fill none unless it sets
its own fill, and a style property beats the attribute beside it, either way round.

L1 reads forbidden words from $KSTACK_PRIVATE_TERMS, comma-separated, and holds that no file in
the skill contains one. It skips when the variable is unset. S1 renders assets/example.md for real
into the temp folder, and skips only when Chrome is absent: page 1 holds the title, each contents
entry's page holds that heading, the html has no marker and no file://, and no temp folder is
left behind. S2 renders a report over 100 pages whose late contents rows sit near the width where a
third digit wraps them, and holds every contents entry on its page. S3 renders a report whose text
holds @@x@@ and @@VERSION@@, the shape of a page marker, and holds both in the pdf's text.
"""

from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path


HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(SKILL / 'scripts'))

import report    # noqa: E402
import theme     # noqa: E402
import wordmark  # noqa: E402


RESULTS = []
FRONT = '---\ntitle: T\nauthor: A\nrelease: 1\ndate: D\n---\n'


def check(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


def skip(name: str, why: str) -> None:
    print(f'SKIP  {name}  ({why})')


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def fails(fn, *args) -> str:
    '''the error message fn raises, or "" when it returns.'''
    try:
        fn(*args)
    except Exception as e:
        return str(e)
    return ''


def nums(rep) -> list[str]:
    return [p.number for p in rep.parts]


# ── R: the parser ────────────────────────────────────────────────────────────

def test_parser(tmp: Path) -> None:
    def parse(text, name='r.md'):
        return report.parse(write(tmp, name, text))

    msg = fails(parse, '---\ntitle: T\nauthor: A\nrelease: 1\n---\n# One\n')
    check('R1 a missing date is named', 'missing date' in msg and ':1:' in msg, msg)
    msg = fails(parse, FRONT.replace('date: D', 'date: D\ncolour: red') + '# One\n')
    check('R1 an unknown key is named at its line', "'colour'" in msg and ':6:' in msg, msg)
    msg = fails(parse, FRONT.replace('date: D', 'date: D\nwordmark: gone.svg') + '# One\n')
    check('R1 a missing wordmark names its path', 'gone.svg' in msg and ':6:' in msg, msg)
    msg = fails(parse, '# One\n')
    check('R1 no front matter is refused', 'no front matter' in msg, msg)

    rep = parse(FRONT + '# One\n## a\n### b\n### c\n## d\n### h\n# Two\n## e\n# Three\n'
                '# References\n\n1. A ref.\n'
                '# Appendix: First\n## f\n### g\n# Appendix: Second\n'
                '# Glossary\n\n- **T** — a term.\n')
    check('R2 chapters, references, appendices and glossary', nums(rep) ==
          ['1', '2', '3', '4', 'A', 'B', 'C'], nums(rep))
    secs = [s.number for p in rep.parts for s in p.sections]
    check('R2 sections number under their part', secs == ['1.1', '1.1.1', '1.1.2', '1.2', '1.2.1',
                                                          '2.1', 'A.1', 'A.1.1'], secs)
    check('R2 kinds follow the titles', [p.kind for p in rep.parts] == [
        'chapter'] * 3 + ['references', 'appendix', 'appendix', 'glossary'])
    check('R2 an appendix title drops its prefix', rep.parts[4].title == 'First')
    rep = parse(FRONT + '# One\n# Glossary\n\n- **T** — a term.\n')
    check('R2 a glossary with no appendix takes A', nums(rep) == ['1', 'A'], nums(rep))

    for name, text, line in (
            ('an appendix before a chapter', '# Appendix: X\n# One\n', 8),
            ('a second glossary', '# One\n# Glossary\n\n- **a** — b\n# Glossary\n\n- **c** — d\n',
             11),
            ('a chapter after the references', '# One\n# References\n\n1. r\n# Two\n', 11),
            ('a ### with no ## above it', '# One\n### deep\n', 8)):
        msg = fails(parse, FRONT + text)
        check(f'R3 {name} is refused at its line', f':{line}:' in msg, msg)

    rep = parse(FRONT + '# One\n## Scope\n### Deep part\n# Two\n# Appendix: Notes\n'
                'See [x](#deep-part), [y](#two), [z](#appendix-notes) and [w](https://e.org).\n')
    text = rep.parts[2].intro[0][1]
    check('R4 a section link carries its number', '[x](#s-1-1-1) (1.1.1)' in text, text)
    check('R4 a chapter link carries Chapter n', '[y](#s-2) (Chapter 2)' in text, text)
    check('R4 an appendix link carries Appendix X', '[z](#s-A) (Appendix A)' in text, text)
    check('R4 a full address passes', '[w](https://e.org).' in text, text)
    msg = fails(parse, FRONT + '# One\n\nSome text\nand [x](#nope).\n')
    check('R4 an unknown slug stops at its line', '#nope' in msg and ':10:' in msg, msg)
    msg = fails(parse, FRONT + '# One\n\n- see [x](other.md)\n')
    check('R4 a relative link stops at its line', 'other.md' in msg and ':9:' in msg, msg)
    msg = fails(parse, FRONT + '# A\n## Method\n# B\n## Method\n# C\n\nsee [m](#method)\n')
    check('R4 a slug two headings share stops when linked', '#method' in msg and ':8' in msg
          and ':10' in msg, msg)
    check('R4 a shared slug nobody links is fine',
          not fails(parse, FRONT + '# A\n## Method\n# B\n## Method\n'))

    fmt = (SKILL / 'references' / 'format.md').read_text()
    examples = [m[1] for m in re.findall(r'^(`{3,})markdown\n(.*?)\n\1$', fmt, re.S | re.M)]
    write(tmp, 'brand/wordmark.svg', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 1"/>')
    bad = []
    for k, ex in enumerate(examples):
        text = ex if ex.startswith('---') else FRONT + ('' if ex.lstrip().startswith('# ')
                                                        else '# Example\n\n') + ex
        err = fails(parse, text, f'fmt{k}.md')
        if err:
            bad.append(f'example {k + 1}: {err}')
    check(f'R5 the {len(examples)} markdown examples in format.md parse', examples and not bad,
          '; '.join(bad))

    rep = parse(FRONT + '# One\n\n#### Decision\n\ntext\n\n---\n\n```\n# not a heading\n```\n'
                '\nsee `[x](nowhere.md)` here\n')
    kinds = [b[0] for b in rep.parts[0].intro]
    check('R6 ####, ---, a fenced # and a code-span link', kinds == ['heading', 'p', 'break',
          'code', 'p'] and len(rep.parts) == 1, kinds)

    msg = fails(parse, FRONT + '# One\n# Glossary\n\n- term: no bold\n')
    check('R7 a glossary item without **term** is refused', 'glossary item' in msg, msg)
    msg = fails(parse, FRONT + '# One\n# References\n\njust prose\n')
    check('R7 references need a numbered list', 'numbered list' in msg, msg)

    rep = parse(FRONT + '# One\n\nTable: Services in scope\n| Service | Owner |\n|---|---|\n'
                '| ingest | data |\n')
    got = rep.parts[0].intro
    check('R8 a caption directly above its table captions it', got == [
        ('table', 'Services in scope', ['Service', 'Owner'], [['ingest', 'data']])], got)
    rep = parse(FRONT + '# One\n\nTable: Spaced\n\n| a |\n|---|\n| 1 |\n')
    got = rep.parts[0].intro
    check('R8 a caption a blank line above its table captions it',
          got == [('table', 'Spaced', ['a'], [['1']])], got)
    msg = fails(parse, FRONT + '# One\n\nTable: Orphan\n\nA paragraph.\n\n| a |\n|---|\n| 1 |\n')
    check('R8 a caption with a paragraph after it is refused at its line',
          'Table: Orphan' in msg and ':9:' in msg, msg)
    msg = fails(parse, FRONT + '# One\n\nTable: Last\n## Next\n\n| a |\n|---|\n| 1 |\n')
    check('R8 a caption at the end of a section is refused', ':9:' in msg and 'Last' in msg, msg)
    rep = parse(FRONT + '# One\n\ntext\nTable: Tight\n| a |\n|---|\n| 1 |\n')
    got = rep.parts[0].intro
    check('R8 a caption right under a paragraph still captions its table',
          got == [('p', 'text'), ('table', 'Tight', ['a'], [['1']])], got)
    msg = fails(parse, FRONT + '# One\n\n|---|\n')
    check('R8 a table of only separator rows is refused at its line',
          'header row' in msg and ':9:' in msg, msg)

    write(tmp, 'pic.svg', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>')
    msg = fails(parse, FRONT + '# One\n\nTable: see [x](other.md)\n\n| a |\n|---|\n| 1 |\n')
    check('R9 a dead link in a table caption stops at its line', 'other.md' in msg
          and ':9:' in msg, msg)
    rep = parse(FRONT + '# One\n## Scope\n\nTable: see [S](#scope)\n\n| a |\n|---|\n| 1 |\n')
    got = rep.parts[0].sections[0].blocks[0][1]
    check('R9 a table caption link carries its number', got == 'see [S](#s-1-1) (1.1)', got)
    msg = fails(parse, FRONT + '# One\n\n![a [x](javascript:void) b](pic.svg)\n')
    check('R9 a javascript: link in a figure caption is refused', 'javascript' in msg
          and ':9:' in msg, msg)
    rep = parse(FRONT + '# One\n## Scope\n\n![a [S](#scope) b](pic.svg)\n\n'
                '![Plan [draft]](pic.svg)\n')
    got = [b[:2] for b in rep.parts[0].sections[0].blocks]
    check('R9 figure captions resolve links and keep brackets', got == [
        ('figure', 'a [S](#s-1-1) (1.1) b'), ('figure', 'Plan [draft]')], got)

    for name, text, line in (
            ('a link in the third list item', '# C\n\n- a\n- b\n- [x](#nope)\n', 11),
            ('a link on an item\'s second line', '# C\n\n- a\n  more [x](#nope)\n', 10),
            ('a link in a nested item', '# C\n\n- a\n  - b\n  - [x](#nope)\n', 11),
            ('a link in a box', '# C\n\n> [!NOTE]\n> [x](#nope)\n', 10),
            ('a link on a box\'s second line', '# C\n\n> [!NOTE]\n> a\n> [x](#nope)\n', 11),
            ('a bad glossary item', '# C\n\ntext\n\n# Glossary\n\n- **a** — b\n- bad\n', 14)):
        msg = fails(parse, FRONT + text)
        check(f'R10 {name} is named at its own line', f'r.md:{line}:' in msg, msg)
    write(tmp, 'q.md', 'the last line of q')
    msg = fails(parse, FRONT + '# C\n\n!include q.md\n[x](#nope)\n')
    check('R10 a link after an include names its own file', 'r.md:10:' in msg, msg)

    write(tmp, 'nobox.svg', '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0,0L1,1Z"/></svg>')
    msg = fails(parse, FRONT.replace('date: D', 'date: D\nwordmark: nobox.svg') + '# One\n')
    check('R11 a wordmark with no viewBox is refused at its line', 'no viewBox' in msg
          and ':6:' in msg, msg)
    write(tmp, 'pic.bmp', 'BM')
    for name, text, word in (
            ('a remote figure', '![x](https://e.org/a.png)', 'not a local file'),
            ('a missing figure', '![x](gone.svg)', 'no such file'),
            ('a figure of an unknown type', '![x](pic.bmp)', 'use svg, png'),
            ('an unknown box kind', '> [!TIP]\n> x', '[!TIP]')):
        msg = fails(parse, FRONT + '# One\n\n' + text + '\n')
        check(f'R11 {name} is refused at its line', word in msg and ':9:' in msg, msg)
    for part in ('References\n\n1. r', 'Glossary\n\n- **a** — b'):
        msg = fails(parse, FRONT + f'# One\n# {part}\n## Inside\n')
        check(f'R11 ## under {part.split()[0]} is refused at its line', 'no ## sections' in msg
              and ':11:' in msg, msg)
    msg = fails(parse, FRONT + 'stray text\n# One\n')
    check('R11 text before the first # is refused at its line', 'before the first #' in msg
          and ':7:' in msg, msg)
    msg = fails(parse, FRONT)
    check('R11 an empty report is refused', 'no # chapter' in msg, msg)


# ── I: includes ──────────────────────────────────────────────────────────────

def test_includes(tmp: Path) -> None:
    root = tmp / 'inc'
    write(root, 'parts/two.md', '# Two\n\n![Pic](pic.svg)\n\n## Inner\n\n!include more/three.md\n')
    write(root, 'parts/pic.svg', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>')
    write(root, 'parts/more/three.md', '# Three\n')
    main = write(root, 'main.md', FRONT + '# One\n\nsee [i](#inner)\n\n!include parts/two.md\n'
                 '# Four\n')
    rep = report.parse(main)
    check('I1 numbering runs on across included files', nums(rep) == ['1', '2', '3', '4'],
          nums(rep))
    fig = rep.parts[1].intro[0]
    check('I1 a figure resolves against its own file', fig[0] == 'figure' and '<svg' in fig[2])
    check('I1 a link reaches a heading in an included file',
          '(#s-2-1) (2.1)' in rep.parts[0].intro[0][1], rep.parts[0].intro[0][1])

    main = write(root, 'gone.md', FRONT + '# One\n\n!include nothere.md\n')
    msg = fails(report.parse, main)
    check('I2 a missing include names the file and line', 'gone.md:9:' in msg
          and 'nothere.md' in msg, msg)
    write(root, 'a.md', '# A\n!include b.md\n')
    write(root, 'b.md', '# B\n\n!include a.md\n')
    main = write(root, 'cyc.md', FRONT + '!include a.md\n')
    msg = fails(report.parse, main)
    check('I3 a cycle names the file and line', 'b.md:3:' in msg and 'a.md -> b.md -> a.md' in msg,
          msg)
    write(root, 'fm.md', FRONT + '# X\n')
    msg = fails(report.parse, write(root, 'withfm.md', FRONT + '# One\n!include fm.md\n'))
    check('I4 an included file with front matter is refused', 'withfm.md:8:' in msg, msg)
    rep = report.parse(write(root, 'fenced.md', FRONT + '# One\n\n```\n!include nothere.md\n```\n'))
    check('I5 an include inside a fence stays text', rep.parts[0].intro == [
        ('code', '!include nothere.md')], rep.parts[0].intro)
    write(root, 'open.md', '# X\n\n```\ncode\n')
    msg = fails(report.parse, write(root, 'opener.md', FRONT + '# One\n!include open.md\n# Two\n'))
    check('I6 a fence an included file leaves open is named', 'open.md:3:' in msg, msg)


# ── T: the theme ─────────────────────────────────────────────────────────────

def test_theme(tmp: Path) -> None:
    src = write(tmp, 'plain.md', FRONT + '# how a record works\n\n## the `kg_search` tool\n')
    page = theme.html(report.parse(src))
    check('T1 no wordmark, no logo element', 'class="logo"' not in page
          and 'class="nav-logo"' not in page and '<img' not in page)
    check('T1 the title page stays', 'class="titlepage"' in page and '<h1>T</h1>' in page)

    logo = write(tmp, 'brand/wide.svg', '<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/'
                 'svg" viewBox="0 0 500 100"><path d="M0,0L500,0L500,100Z"/></svg>')
    src = write(tmp, 'logo.md', FRONT.replace('date: D', 'date: D\nwordmark: brand/wide.svg')
                + '# One\n')
    page = theme.html(report.parse(src))
    check('T2 the wordmark is inlined twice', page.count('<svg') == 2 and 'class="logo"' in page)
    check('T2 no file:// and no source path', 'file://' not in page and str(logo) not in page
          and 'wide.svg' not in page and '<?xml' not in page)
    check('T2 a 5:1 wordmark is 2.4in by 0.48in', 'width:2.400in;height:0.480in' in page)
    write(tmp, 'brand/square.svg', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>')
    check('T2 a square logo is capped at 0.9in', theme._logo_size(tmp / 'brand/square.svg')
          == (0.9, 0.9))

    bins = tmp / 'bin'
    bins.mkdir()
    for name in ('chromium', 'pdftotext'):
        write(bins, name, '#!/bin/sh\n').chmod(0o755)
    mac = write(tmp, 'mac/Google Chrome', '')
    own = write(tmp, 'own/chrome', '')
    saved = dict(os.environ), theme.MAC
    try:
        os.environ['PATH'] = str(bins)
        os.environ['CHROME'] = str(own)
        theme.MAC = (mac,)
        check('T3 $CHROME comes first', theme.find_chrome() == own)
        del os.environ['CHROME']
        check('T3 the mac app path beats PATH', theme.find_chrome() == mac)
        theme.MAC = (tmp / 'mac/none',)
        check('T3 PATH is the last place', theme.find_chrome() == bins / 'chromium')
        os.environ['CHROME'] = str(tmp / 'nope')
        msg = fails(theme.find_chrome)
        check('T3 a $CHROME that is not a file is named', '$CHROME' in msg and 'nope' in msg, msg)
        del os.environ['CHROME']
        (bins / 'chromium').unlink()
        msg = fails(theme.find_chrome)
        check('T3 no chrome lists every place', all(w in msg for w in (
            '$CHROME', 'mac/none', 'google-chrome', 'chromium'))
            and isinstance(_raised(theme.find_chrome), theme.ToolMissing), msg)
        os.environ['CHROME'] = str(own)
        (bins / 'pdftotext').unlink()
        msg = fails(theme.preflight)
        check('T4 a missing pdftotext is named with its install', 'pdftotext' in msg
              and 'poppler' in msg, msg)
    finally:
        os.environ.clear()
        os.environ.update(saved[0])
        theme.MAC = saved[1]

    cases = {'how a record works': 'How a Record Works',
             'the `kg_search` tool and its use': 'The `kg_search` Tool and Its Use',
             'what to look for in v2 of iOS': 'What to Look for in v2 of iOS',
             'run-time and build/test costs': 'Run-Time and Build/Test Costs',
             'where it comes from': 'Where It Comes From'}
    got = {k: theme.title_case(k) for k in cases}
    check('T5 title case', got == cases, str({k: v for k, v in got.items() if v != cases[k]}))
    page = theme.html(report.parse(tmp / 'plain.md'))
    check('T6 headings are title-cased in the html', 'How a Record Works</h2>' in page
          and 'The <code>kg_search</code> Tool</h3>' in page)

    err = io.StringIO()
    with redirect_stderr(err):
        code = report.main([str(write(tmp, 'broken.md', FRONT + '# One\n\n[x](#nope)\n'))])
    line = err.getvalue().strip()
    check('T7 the cli prints one line and exits 1', code == 1 and '\n' not in line
          and 'broken.md:9:' in line, line)

    write(tmp, 'mark.svg', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 1"/>')
    src = write(tmp, 'esc.md', '---\ntitle: Q "x" \'y\' </style><script>t()</script>\nauthor: A\n'
                'release: 1"<\ndate: D\nwordmark: mark.svg\n---\n# One\n\n'
                'See [docs](https://e.org/"onmouseover="alert(1)) and <b>bold</b>.\n\n'
                'Bare https://e.org/a"onmouseover="x and https://e.org/?a=1&b=2 end.\n\n'
                'Table: a "q" <i>cap</i>\n\n| a |\n|---|\n| 1 |\n')
    page = theme.html(report.parse(src))
    head = page[:page.index('<body>')]
    check('T8 a title cannot end the style sheet', head.count('</style>') == 1
          and '<script>' not in page and '\\3c /style>' in head, head[-300:])
    check('T8 a quote in an address cannot close its href', '"onmouseover' not in page
          and 'href="https://e.org/&quot;onmouseover=&quot;alert(1"' in page, page[-900:])
    check('T8 a bare address stops at a quote and keeps its query',
          'href="https://e.org/a"' in page and 'href="https://e.org/?a=1&amp;b=2"' in page,
          page[-900:])
    check('T8 html in a paragraph is shown as text', '&lt;b&gt;bold&lt;/b&gt;' in page)
    check('T8 a caption and the wordmark label are escaped',
          'a &quot;q&quot; &lt;i&gt;cap&lt;/i&gt;' in page
          and 'aria-label="Q &quot;x&quot; &#39;y&#39; &lt;/style&gt;' in page)

    fake = write(tmp, 'fakechrome', '#!/bin/sh\necho "$@" > "$(dirname "$0")/args"\n'
                 'echo "no display" >&2\nexit 3\n')
    fake.chmod(0o755)
    work = tmp / 'renderwork'
    work.mkdir()
    err = _raised(lambda: theme._render(fake, '<p>x</p>', work / 'x.pdf', work))
    check('T9 a chrome that fails raises RenderError with its exit and last line',
          isinstance(err, theme.RenderError) and 'exit 3' in str(err)
          and 'no display' in str(err), str(err))
    args = (tmp / 'args').read_text()
    check('T9 chrome prints with a throwaway profile in the temp folder',
          f'--user-data-dir={work / "profile"}' in args, args)
    write(tmp, 'quietchrome', '#!/bin/sh\nexit 0\n').chmod(0o755)
    err = _raised(lambda: theme._render(tmp / 'quietchrome', '<p>x</p>', work / 'y.pdf', work))
    check('T9 a chrome that writes no pdf raises RenderError', isinstance(err, theme.RenderError),
          str(err))

    rep = report.parse(write(tmp, 'one.md', FRONT + '# One\n'))
    tokens = set()
    for name, marked, final, word in (
            ('pages that never settle', ['@@s-1@@One\f', '\f@@s-1@@One\f'], None, 'still moved'),
            ('a lost marker', ['One\f'], None, 'no page marker'),
            ('an unmarked print that differs', ['@@s-1@@One\f'], 'Two\f', 'laid out')):
        calls = []

        #the stub reads build's token off the page it prints, and writes it into each marker...
        def text(pdf, marked=marked, final=final, calls=calls):
            if pdf.name == 'final.pdf':
                return final
            calls.append(pdf)
            token = re.search(r'class="mk">@@(\w+)-', pdf.read_text())[1]
            tokens.add(token)
            return marked[(len(calls) - 1) % len(marked)].replace('@@s-', f'@@{token}-s-')

        saved = theme.preflight, theme._render, theme._text
        try:
            theme.preflight = lambda: Path('chrome')
            theme._render = lambda chrome, page, pdf, folder: pdf.write_text(page)
            theme._text = text
            err = _raised(lambda: theme.build(rep, tmp / 'stub' / 'one'))
        finally:
            theme.preflight, theme._render, theme._text = saved
        check(f'T10 {name} raises RenderError', isinstance(err, theme.RenderError)
              and word in str(err) and not (tmp / 'stub').exists(), str(err))
    check('T10 each build draws its own marker token', len(tokens) == 3, str(tokens))


def _raised(fn):
    '''the exception fn raises, or None when it returns.'''
    try:
        fn()
    except Exception as e:
        return e


# ── W: the wordmark ──────────────────────────────────────────────────────────

def _winding(d: str, pt: tuple) -> int:
    '''the nonzero winding number of path data d at pt.'''
    total = 0
    for sp in wordmark.subpaths(d):
        poly = wordmark._polygon(sp, 32)
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            if y0 <= pt[1] < y1 and (x1 - x0) * (pt[1] - y0) - (pt[0] - x0) * (y1 - y0) > 0:
                total += 1
            elif y1 <= pt[1] < y0 and (x1 - x0) * (pt[1] - y0) - (pt[0] - x0) * (y1 - y0) < 0:
                total -= 1
    return total


def _svg(tmp: Path, name: str, body: str) -> Path:
    return write(tmp, name, f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
                            f'{body}</svg>')


def test_wordmark(tmp: Path) -> None:
    outer_cw  = 'M10,10 L90,10 L90,90 L10,90 Z'
    inner_cw  = 'M30,30 L70,30 L70,70 L30,70 Z'
    inner_ccw = 'M30,30 L30,70 L70,70 L70,30 Z'
    for name, inner in (('drawn the same way', inner_cw), ('drawn opposite', inner_ccw)):
        d, _, _ = wordmark.flatten(_svg(tmp, 'ring.svg', f'<path d="{outer_cw} {inner}"/>'))
        hole, ring = _winding(d, (40, 40)), _winding(d, (15, 50))
        check(f'W1 an O keeps its hole when {name}', hole == 0 and ring != 0, f'{hole}, {ring}')
        areas = [wordmark._area(wordmark._polygon(sp)) for sp in wordmark.subpaths(d)]
        check(f'W1 the outline runs clockwise and the hole counter when {name}',
              areas[0] > 0 > areas[1], areas)
    d, _, _ = wordmark.flatten(_svg(tmp, 'o.svg', '<g transform="translate(5,5)"><path d="M50,10 '
                                   'C72,10 90,28 90,50 C90,72 72,90 50,90 C28,90 10,72 10,50 '
                                   'C10,28 28,10 50,10 Z M50,30 C61,30 70,39 70,50 C70,61 61,70 '
                                   '50,70 C39,70 30,61 30,50 C30,39 39,30 50,30 Z"/></g>'))
    check('W1 a curved O keeps its counter', _winding(d, (40, 40)) == 0
          and _winding(d, (12, 40)) != 0)

    #the input sits at 15..95 after its translate, and the output starts at 0, so it moved by -10...
    src = wordmark.subpaths(re.search(r' d="([^"]+)"', (tmp / 'o.svg').read_text())[1])
    shape = {(round(x - 10, 1), round(y - 10, 1)) for sp in src
             for x, y in wordmark._polygon(sp, 8)}
    out = {(round(x, 1), round(y, 1)) for sp in wordmark.subpaths(d)
           for x, y in wordmark._polygon(sp, 8)}
    check('W1 a reversed curve traces the same outline', shape == out, f'{len(shape ^ out)} differ')

    d, _, _ = wordmark.flatten(_svg(tmp, 'abut.svg', '<path d="M0,0 L50,0 L50,50 L0,50 Z"/>'
                                    '<path d="M50,0 L50,50 L100,50 L100,0 Z"/>'))
    areas = [wordmark._area(wordmark._polygon(sp)) for sp in wordmark.subpaths(d)]
    check('W2 abutting squares wind the same way', len(areas) == 2 and areas[0] * areas[1] > 0
          and _winding(d, (50, 25)) != 0, areas)

    #this square starts on the shared edge, where a one-point test calls it inside its neighbour...
    d, _, _ = wordmark.flatten(_svg(tmp, 'edge.svg', '<path d="M50,0 L100,0 L100,50 L50,50 Z"/>'
                                    '<path d="M50,20 L50,50 L0,50 L0,0 L50,0 Z"/>'))
    areas = [wordmark._area(wordmark._polygon(sp)) for sp in wordmark.subpaths(d)]
    check('W2 a square starting on the shared edge is not a hole', areas[0] * areas[1] > 0, areas)

    for name, body, word in (('a <rect>', '<rect width="5" height="5"/>', 'rect'),
                             ('a stroke', '<path d="M0,0 L5,5" stroke="#000"/>', 'stroke'),
                             ('an arc', '<path d="M0,0 A5,5 0 0 1 10,10 Z"/>', 'arc'),
                             ('a skew', '<g transform="skewX(10)"><path d="M0,0 L1,1Z"/></g>',
                              'skewX')):
        msg = fails(wordmark.flatten, _svg(tmp, 'bad.svg', body))
        check(f'W3 {name} is refused by name', word in msg, msg)

    rel = wordmark.subpaths('m10,10 h80 v80 h-80 z')
    ab = wordmark.subpaths('M10,10 L90,10 L90,90 L10,90 Z')
    check('W4 relative and H/V commands read as absolute', rel == ab, f'{rel} != {ab}')

    sq = '<path d="M10,10 L90,10 L90,90 L10,90 Z"'
    for name, body, word in (
            ('a <style> element', f'<defs><style>.a{{stroke:#000}}</style></defs>{sq}/>',
             '<style>'),
            ('a class attribute', f'{sq} class="a"/>', 'class'),
            ('a stroke set on a parent group', f'<g fill="none" stroke="#000">{sq}/></g>',
             'stroke'),
            ('a stroke set in a group style', f'<g style="stroke: red">{sq}/></g>', 'stroke'),
            ('a style stroke over stroke="none"', f'{sq} stroke="none" style="stroke:#000"/>',
             'stroke'),
            ('a stroke set on the svg', None, 'stroke')):
        path = (_svg(tmp, 'paint.svg', body) if body else write(
            tmp, 'paint.svg', f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
            f'stroke="#000">{sq}/></svg>'))
        msg = fails(wordmark.flatten, path)
        check(f'W5 {name} is refused by name', word in msg, msg)
    msg = fails(wordmark.flatten, _svg(tmp, 'paint.svg', f'<g fill="none">{sq}/></g>'))
    check('W5 a path inheriting fill none is not filled', 'no filled path' in msg, msg)
    d, _, _ = wordmark.flatten(_svg(tmp, 'paint.svg', f'<g fill="none">{sq} fill="#000"/></g>'))
    check('W5 a path\'s own fill beats its group\'s', d.startswith('M0,0'), d)
    msg = fails(wordmark.flatten,
                _svg(tmp, 'paint.svg', f'{sq} stroke="#000" style="stroke:none"/>'))
    check('W5 a style stroke:none beats a stroke attribute', msg == '', msg)


# ── L and S: leaks and the real render ───────────────────────────────────────

def test_leaks() -> None:
    terms = [t.strip().lower() for t in os.environ.get('KSTACK_PRIVATE_TERMS', '').split(',')
             if t.strip()]
    if not terms:
        skip('L1 no private term in the skill', '$KSTACK_PRIVATE_TERMS is unset')
        return
    hits = []
    for f in sorted(SKILL.rglob('*')):
        if f.is_file() and '__pycache__' not in f.parts:
            text = f.read_bytes().decode('utf-8', 'replace').lower()
            hits += [f'{f.relative_to(SKILL)}: {t}' for t in terms if t in text]
    check(f'L1 no private term in the skill ({len(terms)} terms)', not hits, '; '.join(hits))


def test_render(tmp: Path) -> None:
    try:
        theme.preflight()
    except theme.ToolMissing as e:
        skip('S1 render assets/example.md', str(e))
        return
    before = set(Path(tempfile.gettempdir()).glob('write-report-*'))
    out = tmp / 'render' / 'example'
    code = report.main([str(SKILL / 'assets' / 'example.md'), '--out', str(out)])
    pdf, page = out.with_name('example.pdf'), out.with_name('example.html')
    check('S1 the example renders', code == 0 and pdf.is_file() and page.is_file())
    if code:
        return
    text = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True,
                          text=True).stdout.split('\f')
    check('S1 page 1 holds the title', 'Example Report' in text[0])
    rows = re.findall(r'^\s*([0-9A-Z][0-9.]*)\s+(.+?)\s+(\d+)\s*$', text[1], re.M)
    wrong = [f'{n} {t} on {p}' for n, t, p in rows
             if not re.search(rf'^\s*{re.escape(n)}\s+{re.escape(t)}\s*$', text[int(p) - 1], re.M)]
    check(f'S1 each of the {len(rows)} contents entries is on its page', len(rows) > 10
          and not wrong, '; '.join(wrong))
    html = page.read_text()
    check('S1 the html has no marker and no file://', '@@' not in html and 'file://' not in html)
    left = set(Path(tempfile.gettempdir()).glob('write-report-*')) - before
    check('S1 no temp folder is left', not left, str(left))


def _long_report(folder: Path) -> Path:
    '''a report over 100 pages whose late contents rows sit near the width a third digit wraps.'''
    para = ' '.join(['lorem ipsum dolor sit amet'] * 60) + '.'
    out = [FRONT]
    for c in range(1, 31):
        out += [f'# Filler chapter {c}', ''] + [para, ''] * 8
    out += ['# Late', '']
    for k in range(140):
        out += ['## Heading ' + ' '.join(['abcdefg'] * (8 + k // 12)) + ' x' * (k % 12), '',
                'text.', '']
    return write(folder, 'long.md', '\n'.join(out))


def test_long_render(tmp: Path) -> None:
    try:
        theme.preflight()
    except theme.ToolMissing as e:
        skip('S2 render a report over 100 pages', str(e))
        return
    rep = report.parse(_long_report(tmp))
    out = tmp / 'render' / 'long'
    pages = theme.build(rep, out)
    text = subprocess.run(['pdftotext', '-layout', str(out.with_name('long.pdf')), '-'],
                          capture_output=True, text=True).stdout.split('\f')
    entries = [(p.number, theme.title_case(p.title).split()[0]) for p in rep.parts]
    entries[30:] = [entries[30]] + [(s.number, 'Heading') for s in rep.parts[30].sections]
    first = next(k for k, t in enumerate(text[1:], 1)
                 if re.search(r'^\s*1\s+Filler Chapter 1\s*$', t, re.M))

    #each page's first and last lines are its running header and its folio, not contents rows...
    toc = '\n'.join(ln for page in text[1:first]
                    for ln in [ln for ln in page.splitlines() if ln.strip()][1:-1])

    #a wrapped row holds its page number on one of its lines, so rows and numbers pair in order...
    starts = [re.search(rf'^\s*{re.escape(n)}\s+{w}\b', toc, re.M) for n, w in entries]
    numbers = [int(x) for x in re.findall(r'\s(\d+)\s*$', toc, re.M)]
    wrong = [f'{n} on {p}' for (n, w), p in zip(entries, numbers)
             if not re.search(rf'^\s*{re.escape(n)}\s+{w}\b', text[p - 1], re.M)]
    check(f'S2 the long report runs past 100 pages ({pages})', pages > 100)
    check(f'S2 each of the {len(entries)} contents entries is on its page', all(starts)
          and len(numbers) == len(entries) and not wrong,
          f'{sum(not s for s in starts)} rows missing, {len(numbers)} numbers, wrong: '
          + '; '.join(wrong[:8]))


def test_marker_text(tmp: Path) -> None:
    try:
        theme.preflight()
    except theme.ToolMissing as e:
        skip('S3 render text shaped like a page marker', str(e))
        return
    src = write(tmp, 'at.md', FRONT + '# Introduction\n\nA hidden `@@x@@` marker.\n\n'
                '## How it works\n\nThe placeholder @@VERSION@@ is replaced at build time.\n')
    out = tmp / 'render' / 'at'
    err = _raised(lambda: theme.build(report.parse(src), out))
    check('S3 text shaped like a page marker renders', err is None, str(err))
    if err:
        return
    text = subprocess.run(['pdftotext', '-layout', str(out.with_name('at.pdf')), '-'],
                          capture_output=True, text=True).stdout
    check('S3 the pdf keeps @@x@@ and @@VERSION@@', '@@x@@' in text and '@@VERSION@@' in text,
          text[-400:])


def main() -> int:
    with tempfile.TemporaryDirectory() as name:
        tmp = Path(name)
        test_parser(tmp)
        test_includes(tmp)
        test_theme(tmp)
        test_wordmark(tmp)
        test_leaks()
        test_render(tmp)
        test_long_render(tmp)
        test_marker_text(tmp)
    failed = RESULTS.count(False)
    print(f'\n{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
