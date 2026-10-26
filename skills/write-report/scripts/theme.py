'''
theme — the fixed look: a Report laid out as one html page, printed to US Letter by headless
chrome until the contents carry the page numbers the body lands on.

each marked pass prints the page with an invisible marker in every heading: the heading's anchor
behind a token drawn fresh for each build, so no report text can match one. pdftotext finds the
page each marker lands on, and the next pass writes those numbers into the contents. a number
with more digits can push a contents row onto a new line and move every page after it, so
the passes repeat until the numbers read back are the numbers written. the pdf and the html keep
no marker, and everything the page shows is inlined, so the html still works once moved.

Methods
-------
    ToolMissing :
        chrome or pdftotext is not installed; the message says how to install it.
    RenderError :
        chrome or pdftotext ran and failed; the message names the step.
    find_chrome :
        the chrome binary: $CHROME, the macOS app paths, then google-chrome, chromium on PATH.
    preflight :
        confirm chrome and pdftotext are present, before any render starts.
    title_case :
        capitalize a heading's major words, leaving code and short words alone.
    html :
        the whole report as one self-contained html page.
    build :
        write out.pdf and out.html, and return the page count.
'''

from __future__ import annotations

import os
import re
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path



HERE    = Path(__file__).resolve().parent
MAC     = (Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
           Path('/Applications/Chromium.app/Contents/MacOS/Chromium'))
ON_PATH = ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome')
SMALL   = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from', 'in', 'into', 'nor', 'of',
           'on', 'or', 'per', 'than', 'the', 'to', 'via', 'vs', 'with'}
PASSES  = 4
LOGO_W  = 2.4
LOGO_H  = 0.9
URL     = re.compile(r'(?<![">])(https?://(?:&(?:amp|#39);|[^\s<&\x00])*'
                     r'(?:&(?:amp|#39);|[^\s<&.,;:)\x00]))')


class ToolMissing(Exception):
    '''chrome or pdftotext is not installed; the message says how to install it.'''


class RenderError(Exception):
    '''chrome or pdftotext ran and failed; the message names the step.'''


def find_chrome() -> Path:
    '''
    the chrome binary.

    Returns
    -------
    Path
        $CHROME when set, else the first of the macOS app paths, else the first of ON_PATH found
        on PATH.

    Notes
    -----
    raises ToolMissing listing every place it looked, and naming $CHROME when it is set to a
    file that is not there.
    '''
    env = os.environ.get('CHROME')
    if env:
        if Path(env).is_file():
            return Path(env)
        raise ToolMissing(f'$CHROME is {env}, which is not a file')
    for app in MAC:
        if app.is_file():
            return app
    for name in ON_PATH:
        found = shutil.which(name)
        if found:
            return Path(found)
    raise ToolMissing('chrome not found: looked at $CHROME, ' + ', '.join(map(str, MAC))
                      + ' and ' + ', '.join(ON_PATH) + ' on PATH; install Google Chrome or '
                      'Chromium, or set CHROME to its binary')


def preflight() -> Path:
    '''
    confirm chrome and pdftotext are present.

    Returns
    -------
    Path
        the chrome binary.

    Notes
    -----
    raises ToolMissing for the first tool absent, naming it and its install command. runs
    neither tool. *(kstack: the source theme found a missing pdftotext only after chrome had
    printed the first pass.)*
    '''
    chrome = find_chrome()
    if not shutil.which('pdftotext'):
        raise ToolMissing('pdftotext not found on PATH: it comes with poppler '
                          '(brew install poppler, or apt install poppler-utils)')
    return chrome


def title_case(s: str) -> str:
    '''
    capitalize a heading's major words.

    Parameters
    ----------
    s : str
        a heading as written, in sentence case.

    Returns
    -------
    str
        the heading with each word's first letter capitalized, except short articles,
        conjunctions and prepositions inside it. a `code` span, and a word that holds a digit,
        an underscore or a capital already, stays as written.
    '''
    tokens = re.findall(r'`[^`]*`|[^\s`]+|\s+', s)
    words = [k for k, t in enumerate(tokens) if not t.isspace()]

    def cap(t, k):
        if t.startswith('`') or re.search(r'[\d_A-Z]', t):
            return t
        if k not in (words[0], words[-1]) and t.strip('(').lower() in SMALL:
            return t
        return '/'.join('-'.join(re.sub(r'^([^A-Za-z]*)([a-z])', lambda m: m[1] + m[2].upper(), w)
                                 for w in part.split('-'))
                        for part in t.split('/'))

    return ''.join(cap(t, k) if k in words else t for k, t in enumerate(tokens))


# ── html ─────────────────────────────────────────────────────────────────────

def _esc(s: str) -> str:
    '''escape the five characters html gives meaning to in text and in quoted attributes.'''
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;'))


def _inline(s: str) -> str:
    '''
    escape s, then render **bold**, *italics*, `code`, links, bare addresses and \\ breaks.

    Notes
    -----
    the escape runs before any tag is built, so an href is escaped text too and a quote in an
    address cannot close its attribute. a bare address stops at an escaped quote or bracket.
    '''
    codes = []

    def hold(m):
        codes.append(f'<code>{m[1]}</code>')
        return f'\x00{len(codes) - 1}\x00'

    #a code span is set aside first, so a link or a star inside it stays text...
    s = re.sub(r'`([^`]+)`', hold, _esc(s))
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![*\w])\*(?![\s*])(.+?)(?<![\s*])\*(?![*\w])', r'<em>\1</em>', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', s)

    #a bare address becomes a link unless it already sits inside one...
    s = URL.sub(r'<a class="url" href="\1">\1</a>', s)
    s = re.sub(r'\x00(\d+)\x00', lambda m: codes[int(m[1])], s)
    return s.replace('\\\n', '<br>')


def _title(s: str) -> str:
    '''a heading's text: title-cased, escaped, code spans set in code.'''
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', _esc(title_case(s)))


def _list(kind: str, items: list) -> str:
    '''a list; one of five items or fewer never splits across pages.'''
    keep = ' class="keep"' if len(items) <= 5 else ''
    out = []
    for item in items:
        if isinstance(item, tuple):
            text, (sub, subitems) = item
            out.append(f'<li>{_inline(text)}{_list(sub, subitems)}</li>')
        else:
            out.append(f'<li>{_inline(item)}</li>')
    return f'<{kind}{keep}>' + ''.join(out) + f'</{kind}>'


def _blocks(blocks: list, counts: dict, level: int, refs: bool = False) -> list[str]:
    '''each block as html; counts numbers tables and figures through the whole report.'''
    out = []
    for b in blocks:
        kind = b[0]
        if kind == 'p':
            out.append(f'<p>{_inline(b[1])}</p>')
        elif kind == 'ol' and refs:
            out.append('<ol class="refs">' + ''.join(f'<li>{_inline(r)}</li>'
                                                     for r in b[1]) + '</ol>')
        elif kind in ('ul', 'ol'):
            out.append(_list(kind, b[1]))
        elif kind == 'note':
            out.append(f'<div class="note"><div class="note-k">{_esc(b[1])}</div>'
                       f'<p>{_inline(b[2])}</p></div>')
        elif kind == 'table':
            counts['table'] += 1
            head = ''.join(f'<th>{_inline(h)}</th>' for h in b[2])
            rows = ''.join('<tr>' + ''.join(f'<td>{_inline(c)}</td>' for c in r) + '</tr>'
                           for r in b[3])
            title = f' – {_inline(b[1])}' if b[1] else ''
            out.append(f'<table><caption>Table {counts["table"]}{title}</caption>'
                       f'<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>')
        elif kind == 'figure':
            counts['figure'] += 1
            title = f' – {_inline(b[1])}' if b[1] else ''
            out.append(f'<figure>{b[2]}<figcaption>Figure {counts["figure"]}{title}'
                       '</figcaption></figure>')
        elif kind == 'code':
            out.append(f'<pre><code>{_esc(b[1])}</code></pre>')
        elif kind == 'heading':
            tag = min(level + 2, 6)
            out.append(f'<h{tag} class="sub">{_title(b[1])}</h{tag}>')
        elif kind == 'break':
            out.append('<div class="newpage"></div>')
        elif kind == 'glossary':
            out.append('<dl class="glossary">' + ''.join(
                f'<dt>{_inline(t)}</dt><dd>{_inline(d)}</dd>' for t, d in b[1]) + '</dl>')
    return out


def _svg(path: Path, cls: str, label: str, style: str = '') -> str:
    '''an svg file as inline markup carrying a class, a label and a style, with no prolog.'''
    text = path.read_text()
    text = re.sub(r'<!--.*?-->', '', text[text.find('<svg'):], flags=re.S).strip()
    attrs = f' class="{cls}" role="img" aria-label="{_esc(label)}"'
    attrs += f' style="{style}"' if style else ''
    return re.sub(r'<svg\b', '<svg' + attrs, text, count=1)


def _logo_size(path: Path) -> tuple[float, float]:
    '''
    the title-page wordmark's (width, height) in inches, from its viewBox.

    Notes
    -----
    the wordmark fills a 2.4in-wide slot, capped at 0.9in tall: a 5.7:1 wordmark gets 0.42in and
    a square logo 0.9in, the two heights the source theme set by eye. *(kstack: derived from the
    aspect so a project's own logo needs no tuning.)*
    '''
    box = re.search(r'viewBox="([^"]+)"', path.read_text())
    w, h = [float(v) for v in re.split(r'[\s,]+', box[1].strip())][2:4]
    height = min(LOGO_H, LOGO_W * h / w)
    return height * w / h, height


def html(report, pages: dict[str, int] | None = None, token: str | None = None) -> str:
    '''
    the whole report as one html page.

    Parameters
    ----------
    report : Report
        from report.parse.
    pages : dict, optional
        each heading's anchor to its pdf page; None, or an anchor missing from it, draws "00".
    token : str, optional
        build's token for this render; given, every heading carries an invisible marker.

    Returns
    -------
    str
        html with theme.css and the wordmark inlined, so the file works wherever it is moved.

    Notes
    -----
    the title page and the nav panel inline the same svg; a wordmark made by wordmark.py fills
    with currentColor, so the dark panel shows it white with no second file. with no wordmark
    there is no logo element and the title page keeps its layout. headings are title-cased here.
    '''
    m = report.meta
    counts, toc, body = {'table': 0, 'figure': 0}, [], []

    def heading(level, num, title, anchor, cls=''):
        mark = f'<span class="mk">{_marker(token, anchor)}</span>' if token else ''
        toc.append((level, num, title, anchor))
        return (f'<h{level + 1} id="{anchor}"{cls}>{mark}<span class="num">{_esc(num)}</span>'
                f'{_title(title)}</h{level + 1}>')

    for part in report.parts:
        body.append(heading(1, part.number, part.title, part.anchor))
        body += _blocks(part.intro, counts, 1, refs=part.kind == 'references')
        for s in part.sections:
            body.append(heading(s.level, s.number, s.title, s.anchor))
            body += _blocks(s.blocks, counts, s.level)

    got = pages or {}
    rows = ''.join(
        f'<li class="l{level}"><a href="#{anchor}"><span class="n">{_esc(num)}</span>'
        f'<span class="t">{_title(t)}</span><span class="lead"></span>'
        f'<span class="pg">{got.get(anchor, "00")}</span></a></li>'
        for level, num, t, anchor in toc if level <= (2 if num[0].isalpha() else 3))

    logo = nav = ''
    if m.wordmark:
        w, h = _logo_size(m.wordmark)
        logo = _svg(m.wordmark, 'logo', m.title, f'width:{w:.3f}in;height:{h:.3f}in')
        nav = f'<a class="nav-logo" href="#">{_svg(m.wordmark, "", m.title)}</a>'

    #a css string escapes its quote and backslash, and < as \3c so </style> cannot end the sheet...
    def q(s):
        return s.replace('\\', '\\\\').replace('"', '\\"').replace('<', '\\3c ')

    header = (f'@page {{ @top-left {{ content: "{q(m.title)}"; }} '
              f'@top-right {{ content: "Release {q(m.release)}"; }} }}')
    css = (HERE / 'theme.css').read_text()
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(m.title)}</title>
<style>{css}
{header}</style></head>
<body>
<section class="titlepage">
  {logo}
  <h1>{_esc(m.title)}</h1>
  <div class="rule"></div>
  <div class="release">Release {_esc(m.release)}</div>
  <div class="author">{_esc(m.author)}</div>
  <div class="date">{_esc(m.date)}</div>
</section>
<section class="front"><nav class="toc">{nav}<h2 class="toc-title">Contents</h2>
<ol>{rows}</ol></nav></section>
<main>
{chr(10).join(body)}
</main>
</body></html>'''


# ── print ────────────────────────────────────────────────────────────────────

def _render(chrome: Path, page: str, pdf: Path, tmp: Path) -> None:
    '''print one html page to pdf with headless chrome, through a file in tmp.'''
    src = tmp / (pdf.stem + '.html')
    src.write_text(page)

    #a throwaway profile keeps a running chrome and its first-run prompts out of the print...
    cmd = [str(chrome), '--headless=new', '--disable-gpu', '--no-first-run',
           '--no-pdf-header-footer', '--generate-pdf-document-outline',
           f'--user-data-dir={tmp / "profile"}', f'--print-to-pdf={pdf}', src.as_uri()]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise RenderError(f'chrome did not finish printing {pdf.name} in 180 s') from None
    if r.returncode or not pdf.is_file():
        tail = (r.stderr.strip().splitlines() or ['no output'])[-1]
        raise RenderError(f'chrome failed printing {pdf.name} (exit {r.returncode}): {tail}')


def _text(pdf: Path) -> str:
    '''the pdf's text, one form feed after each page.'''
    r = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True, text=True)
    if r.returncode:
        raise RenderError(f'pdftotext failed on {pdf.name}: {r.stderr.strip()}')
    return r.stdout


def _anchors(report) -> list[str]:
    '''every heading's anchor, parts and sections, in file order.'''
    return [a for p in report.parts for a in [p.anchor] + [s.anchor for s in p.sections]]


def _marker(token: str, anchor: str = r'([\w-]+)') -> str:
    '''
    one heading's page marker, or with no anchor the pattern that finds every marker.

    Notes
    -----
    token is hex from secrets.token_hex, so it needs no escaping in the pattern, and an author
    cannot type a marker without knowing a token drawn after the report was parsed.
    '''
    return f'@@{token}-{anchor}@@'


def _page_map(text: str, anchors: list[str], token: str) -> dict[str, int]:
    '''each anchor's page in a marked pdf's text; raises RenderError when a marker is lost.'''
    pages = {}
    for n, page in enumerate(text.split('\f'), start=1):
        for anchor in re.findall(_marker(token), page):
            pages.setdefault(anchor, n)
    lost = [a for a in anchors if a not in pages]
    if lost:
        raise RenderError(f'pdftotext found no page marker for {len(lost)} headings '
                          f'({", ".join(lost[:5])}), so their contents pages are unknown')
    return pages


def _words(text: str) -> list[list[str]]:
    '''the words on each page, so two prints compare by content, not by spacing.'''
    return [page.split() for page in text.split('\f')]


def build(report, out: Path) -> int:
    '''
    write out.pdf and out.html.

    Parameters
    ----------
    report : Report
        from report.parse.
    out : Path
        the output path without an extension.

    Returns
    -------
    int
        the pdf's page count.

    Notes
    -----
    each marked pass prints the page with markers and reads every heading's page back; the next
    pass writes those pages into the contents. the passes stop when a pass reads back the pages it
    was given, at most PASSES of them. then one print without markers makes the pdf, and its
    words must match the last marked pass's page for page, the markers taken out. every marker
    carries this build's token, so taking them out leaves report text that looks like one alone.
    temporary files live in a tempfile folder that is removed on failure too, and nothing is
    written beside out until every pass has succeeded, the pdf first. raises ToolMissing, or RenderError when chrome or pdftotext fails,
    a marker is lost, the pages never settle, or the unmarked print lays out differently.
    *(kstack: the source printed twice, and a contents number that grew a digit on the second
    print moved the pages after it unchecked.)*
    '''
    chrome = preflight()
    out, anchors, token = Path(out), _anchors(report), secrets.token_hex(8)
    with tempfile.TemporaryDirectory(prefix='write-report-') as name:
        tmp = Path(name)
        pages = None
        for _ in range(PASSES):
            _render(chrome, html(report, pages, token), tmp / 'marked.pdf', tmp)
            marked = _text(tmp / 'marked.pdf')
            got = _page_map(marked, anchors, token)
            if got == pages:
                break
            pages = got
        else:
            raise RenderError(f'the contents page numbers still moved after {PASSES} passes')
        final = html(report, pages)
        _render(chrome, final, tmp / 'final.pdf', tmp)
        text = _text(tmp / 'final.pdf')
        if _words(text) != _words(re.sub(_marker(token), '', marked)):
            raise RenderError('the pdf printed without page markers laid out differently from '
                              'the marked pass that set its contents pages')
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp / 'final.pdf', out.with_name(out.name + '.pdf'))
        out.with_name(out.name + '.html').write_text(final)
    return text.count('\f')
