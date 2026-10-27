#!/usr/bin/env python3
'''
test_page.py builds study map pages with `page.py` and checks what they do in headless Chromium.

Run it with `python3 test_page.py`. It needs Python's playwright package and its Chromium; it
never installs either. It makes one temporary folder for its inputs and pages. The exit code is
the number of failed checks.

P1 to P5 and P18 hold split_maps: a tree in K-Stack's layer shape (six top folders, one of them
over the cap), a tree at the cap and one node over it, an oversized file cut at its class layer, a
layer over the cap kept whole, and a cut layer whose map would be over the cap. P6 to P8 hold
map_links: a link into another map ends at the portal that leads to it, a link whose target is
outside the map ends at the map's root, and a link whose source is in another map is not drawn.
P9 to P15, P22 and P23 hold the command: a page written and its stderr counts, a pointer leaf that
is no tip, each refusal, a card that names no node, --artifact, -o required, the over-cap note,
labels and escaping. P16 and P17 hold the vendored files' hashes and the NOTICE rows. P19 to P21
hold a Document of schema and tree alone, a missing template or vendored file refused, and the
libraries placed by name.

B1 to B13 open a one-map page and drive it: plain click and Cmd or Ctrl-click on a branch and on
the centre, hover cards, the hover lighting of the path and its links, a link's ends on its boxes
across the two trees, a link folded into one box, the arrow that opens the way, the layout switch,
no network, and Cmd-click on a Mac. B24 forces each platform and holds that only its own
modifier opens everything. B14 to B17 hold a card and names holding the template's slot
markers, ids that read as HTML or as `__proto__`, the centre of a map with one branch, and the
arrow's spotlight cleared over empty canvas. B18 to B21 hold how a link is drawn (a path of
triangles beneath the boxes), that folding never measures a path, reduced motion, and the bottom
bar's buttons. S1 to S7 open a page of four maps: portals, the swap and the breadcrumb, folds kept
per map, the Back button, a link that ends at the round portal of its home, no network, and the
breadcrumb's frosted bar and chevrons. S8 to S14 open a map whose links lead to two other maps:
one portal per home, links only from sources on screen, portals outside the map and inside Fit,
a pointer tip's card and the portal it turns, everything still once the hover ends, and a portal's
click and what it leaves behind. S15 holds two portals that meet across the left ray, and S16 and
S17 Back pressed with the pointer still after a portal click and after an arrow click. S18 holds
the spread of portals along the rim, the overfull rim and end clusters meeting across the cut
among them (the wrap guard then merges every portal into one block), and S19 the rim point of a
ray of no length. B22 and B23 hover every carded tip in a small window and a zoomed-out large
one, two-sided and one-sided: each card stays inside the window, where page.js's rule puts it.
B25 opens every branch and presses Fit in a small, a middle and a large window, in both layouts:
each box is the topmost element at its centre, never the bottom bar or the breadcrumb. B26 does
the same on the four-map page, where the breadcrumb shows: each box also sits 14 px below it.
'''

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE    = Path(__file__).resolve().parent
STUDY   = HERE.parent
REPO    = STUDY.parent.parent
SCRIPT  = STUDY / 'scripts' / 'page.py'
RESULTS = []
D3_HEAD = '// https://d3js.org v7.9.0'      # the first line of d3.min.js
MM_HEAD = '(function(exports, d32) {'       # the first line of markmap-view.js
SHA256  = {'d3/d3.min.js': 'f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539',
           'markmap-view/markmap-view.js':
               '861eb6d20af18aaa300878d46d695722a73625c58b40f49236af027f18b74e07'}
SETTLE  = 750      # ms: markmap's 500 ms tween and the link overlay that follows it


def check(name: str, ok: bool, detail: str = '') -> None:
    ok = bool(ok)       # a check may end on a value such as [] or None, which is a fail
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


def load_page():
    '''page.py as a module, or None when it cannot be imported.'''
    try:
        spec = importlib.util.spec_from_file_location('page', SCRIPT)
        mod  = importlib.util.module_from_spec(spec)
        sys.modules['page'] = mod       # dataclasses look their module up here
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:      # the red run, before page.py exists
        print(f'page.py does not import: {e}')
        return None


def node(id: str, kind: str, children: list | None = None, name: str | None = None) -> dict:
    return {'id': id, 'name': name or id.rsplit('/', 1)[-1], 'kind': kind,
            'children': children or []}


def flat_dir(id: str, size: int) -> dict:
    return node(id, 'dir', [node(f'{id}/f{i}', 'file') for i in range(size - 1)])


def kstack_shape() -> dict:
    '''
    a tree in K-Stack's layer shape: six top folders, five of them flat and under the cap, and
    skills over it, made of 30 skill folders of 22 nodes. every top folder fits on the second
    layer, but the top map down to that layer would hold 584 nodes, so the top map cuts at its
    first layer and skills splits on its own.
    '''
    skills = node('skills', 'dir', [
        node(f'skills/s{k}', 'dir', [
            node(f'skills/s{k}/m{i}.py', 'file', [node(f'skills/s{k}/m{i}.py/f{j}', 'function')
                                                 for j in range(6)]) for i in range(3)])
        for k in range(30)])
    return node('.', 'root', [flat_dir('.claude', 124), flat_dir('apps', 377),
                              flat_dir('hooks', 16), skills, flat_dir('tests', 9),
                              flat_dir('upstream', 26)])


def document(tree: dict, links: list | None = None) -> dict:
    doc = {'schema': 1, 'scope': '.', 'commit': '0' * 40, 'dirty': False, 'skipped': {},
           'warnings': [], 'tree': tree}
    if links is not None:
        doc['links'] = links
    return doc


def files(prefix: str, count: int, funcs: int) -> list:
    return [node(f'{prefix}/m{i}.py', 'file',
                 [node(f'{prefix}/m{i}.py/f{j}', 'function') for j in range(funcs)])
            for i in range(count)]


def run(*args: str | Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True,
                          text=True, check=False)


def write_json(at: Path, data) -> Path:
    at.write_text(json.dumps(data))
    return at


def summary(maps) -> list:
    return [(m.id, m.parent, m.size, list(m.portals)) for m in maps]


# ── the fixtures the browser cases open ───────────────────────────────────────

SMALL = node('.', 'root', name='demo', children=[
    node('src', 'dir', [
        node('src/a.py', 'file', [
            node('src/a.py/Cls', 'class', [node('src/a.py/Cls/run', 'method'),
                                           node('src/a.py/Cls/stop', 'method')]),
            node('src/a.py/helper', 'function')]),
        node('src/b.js', 'file', [node('src/b.js/main', 'function'),
                                  node('src/b.js/util', 'function')])]),
    node('tests', 'dir', [node('tests/t.py', 'file', [node('tests/t.py/test_a', 'function'),
                                                      node('tests/t.py/test_b', 'function')])]),
    node('docs', 'dir', [node('docs/d.py', 'file', [node('docs/d.py/build', 'function')])]),
    node('tools', 'dir', [node('tools/x.py', 'file', [node('tools/x.py/go', 'function'),
                                                      node('tools/x.py/a<b>', 'function')])]),
])
SMALL_LINKS = [['tests/t.py/test_a', 'src/a.py/Cls/run'], ['docs/d.py/build', 'src/b.js/main'],
               ['tools/x.py/go', 'docs/d.py/build'], ['src/a.py/helper', 'src/b.js/util'],
               ['docs/d.py/build', 'src/b.js/main']]
SMALL_CARDS = {'src/a.py/Cls/run': 'Runs the **loop** once.\nThen stops.',
               'src/a.py/Cls/stop': 'Stops it.', 'src/b.js/main': 'The entry point.',
               'docs/d.py': 'Holds the docs build.'}
SMALL_IDS = set()
_stack = [SMALL]
while _stack:
    _n = _stack.pop()
    SMALL_IDS.add(_n['id'])
    _stack.extend(_n['children'])

SET = node('.', 'root', name='proj', children=[
    node('app', 'dir', files('app', 25, 10)),
    node('lib', 'dir', files('lib', 25, 10)),
    node('docs', 'dir', [node('docs/x.py', 'file', [node('docs/x.py/go', 'function')])]),
])
SET_LINKS = [['docs', 'app/m1.py/f2'], ['lib/m0.py/f0', 'app/m1.py/f2'],
             ['app/m0.py/f0', 'app/m1.py/f2']]
SET_CARDS = {'app/m0.py/f1': 'The second function.'}


# ── split_maps and map_links ──────────────────────────────────────────────────

def split_cases(page) -> None:
    if page is None:
        for n in range(1, 9):
            check(f'P{n} (page.py does not import)', False)
        return
    maps   = page.split_maps(kstack_shape())
    skills = [f'skills/s{k}' for k in range(30)]
    want   = ([('.', None, 7, ['.claude', 'apps', 'hooks', 'skills', 'tests', 'upstream']),
               ('.claude', '.', 124, []), ('apps', '.', 377, []), ('hooks', '.', 16, []),
               ('skills', '.', 31, skills)] + [(s, 'skills', 22, []) for s in skills]
              + [('tests', '.', 9, []), ('upstream', '.', 26, [])])
    check('P1 the K-Stack shape splits into a 7-node top map with 6 portals, and skills, over the '
          'cap, into a map of its 30 skill folders',
          summary(maps) == want, str(summary(maps)[:6]))

    at_cap   = node('.', 'root', [node('a', 'dir', [node(f'a/f{i}', 'file') for i in range(498)])])
    over_cap = node('.', 'root', [node('a', 'dir', [node(f'a/f{i}', 'file') for i in range(499)])])
    one, two = page.split_maps(at_cap), page.split_maps(over_cap)
    check('P2 a tree of 500 nodes is one map, and one of 501 cuts at its first fitting layer',
          summary(one) == [('.', None, 500, [])]
          and summary(two) == [('.', None, 2, ['a']), ('a', '.', 500, [])],
          f'{summary(one)} {summary(two)}')

    classes = [node(f'src/big.py/C{k}', 'class',
                    [node(f'src/big.py/C{k}/m{j}', 'method') for j in range(200)])
               for k in range(3)]
    big  = node('.', 'root', [node('src', 'dir', [
        node('src/big.py', 'file', classes + [node('src/big.py/f', 'function')])])])
    maps = page.split_maps(big)
    want = [('.', None, 3, ['src/big.py']),
            ('src/big.py', '.', 5, ['src/big.py/C0', 'src/big.py/C1', 'src/big.py/C2']),
            ('src/big.py/C0', 'src/big.py', 201, []), ('src/big.py/C1', 'src/big.py', 201, []),
            ('src/big.py/C2', 'src/big.py', 201, [])]
    check('P3 an oversized file is a portal and its own map cuts at its class layer',
          summary(maps) == want, str(summary(maps)))

    flat  = node('.', 'root', [node(f'f{i}.py', 'file') for i in range(600)])
    klass = node('.', 'root', [node('x.py', 'file', [
        node('x.py/K', 'class', [node(f'x.py/K/m{j}', 'method',
                                      [node(f'x.py/K/m{j}/h', 'function')])
                                 for j in range(300)])])])
    wide = node('.', 'root', [node('flat', 'dir', [node(f'flat/f{i}.py', 'file')
                                                   for i in range(600)]),
                              node('b', 'dir', [node('b/x.py', 'file')])])
    check('P4 one layer over 500 stays whole on the smallest map it can, and a class over the cap '
          'is its own map, never split',
          summary(page.split_maps(flat)) == [('.', None, 601, [])]
          and summary(page.split_maps(wide)) == [('.', None, 3, ['flat', 'b']),
                                                 ('flat', '.', 601, []), ('b', '.', 2, [])]
          and summary(page.split_maps(klass)) == [('.', None, 2, ['x.py']),
                                                  ('x.py', '.', 2, ['x.py/K']),
                                                  ('x.py/K', 'x.py', 601, [])],
          f'{summary(page.split_maps(flat))[:1]} {summary(page.split_maps(klass))}')

    sum_a = node('A', 'dir', [node('A/1', 'dir', [
        node(f'A/1/d{j}', 'dir', [node(f'A/1/d{j}/f{i}', 'file') for i in range(250)])
        for j in range(3)])])
    sum_b = node('B', 'dir', [node(f'B/s{j}', 'dir', [node(f'B/s{j}/f', 'file')])
                              for j in range(250)])
    maps  = page.split_maps(node('.', 'root', [sum_a, sum_b]))
    check('P18 a map whose fitting layer would put it over the cap cuts at its shallowest layer '
          'that fits, and its branches over the cap are portals split the same way',
          summary(maps)[:3] == [('.', None, 3, ['A', 'B']), ('A', '.', 5, ['A/1/d0', 'A/1/d1',
                                                                         'A/1/d2']),
                                ('A/1/d0', 'A', 251, [])]
          and max(m.size for m in maps) <= 500,
          f'{summary(maps)[:3]} {max(m.size for m in maps)}')

    tree = page.split_maps(big)[0].tree
    check('P5 a portal keeps its keys in its parent map and has no children there',
          tree['children'][0]['children'][0] == {'id': 'src/big.py', 'name': 'big.py',
                                                  'kind': 'file', 'children': []},
          str(tree['children'][0]['children'][0])[:200])

    maps  = page.split_maps(SET)
    links = page.map_links(maps, SET, [tuple(l) for l in SET_LINKS])
    check('P6 a link into another map ends at the portal whose subtree holds its target, and '
          'carries its target as its home',
          links.get('.') == [['docs', 'app', 'app/m1.py/f2']], str(links))
    check("P7 a link whose target is outside the map ends at the map's root, and one that would "
          'end where it starts is not drawn',
          links.get('lib') == [['lib/m0.py/f0', 'lib', 'app/m1.py/f2']]
          and links.get('docs') == [],
          str(links))
    check('P8 a link inside one map keeps its ends, and a source in another map is not drawn',
          links.get('app') == [['app/m0.py/f0', 'app/m1.py/f2', 'app/m1.py/f2']], str(links))


# ── the command ───────────────────────────────────────────────────────────────

def command_cases(tmp: Path, page) -> None:
    tree  = write_json(tmp / 'small.json', document(SMALL, SMALL_LINKS))
    cards = write_json(tmp / 'small.cards.json', SMALL_CARDS)
    out   = tmp / 'small.html'
    r     = run(tree, '--cards', cards, '-o', out)
    text  = out.read_text() if out.exists() else ''
    check('P9 a page is written, exit 0, with tips counted and the tips without a card counted; '
          'a pointer leaf is no tip, a node whose children are all pointer leaves is one, and its '
          'card is in the page',
          r.returncode == 0 and text.startswith('<!doctype html>')
          and 'page: 7 tips, 4 with a card, 3 without\n' in r.stderr
          and 'page: 4 links on 1 map\n' in r.stderr
          and payload(page_data(text)['MAPS']['.'], 'docs/d.py').get('card')
          == '<p>Holds the docs build.</p>',
          f'{r.returncode} {r.stderr}')

    def refused(name: str, data, reason: str, as_cards: bool = False) -> None:
        bad = tmp / f'{name}.json'
        bad.write_text(data if isinstance(data, str) else json.dumps(data))
        o = tmp / f'{name}.html'
        q = run(tree, '--cards', bad, '-o', o) if as_cards else run(bad, '-o', o)
        check(f'P10 {name} is refused with page:, the file and the reason, and writes nothing',
              q.returncode == 2 and q.stderr == f'page: {bad}: {reason}\n' and not o.exists(),
              f'{q.returncode} {q.stderr!r}')

    good = document(SMALL, SMALL_LINKS)
    refused('not JSON', '{"schema": 1,', 'not JSON: Expecting property name enclosed in double '
            'quotes at line 1')
    refused('not an object', '[1]', 'not a Document: the top level is not an object')
    refused('schema 2', dict(good, schema=2), 'schema is 2, and page.py reads schema 1')
    refused('schema true', dict(good, schema=True), 'schema is True, and page.py reads schema 1')
    refused('a missing key', {k: v for k, v in good.items() if k != 'tree'},
            "the Document has no 'tree'")
    refused('a node with no kind', document(node('.', 'root', [{'id': 'a', 'name': 'a',
                                                                 'children': []}])),
            "node 'a' has no kind")
    refused('a node of an unknown kind', document(node('.', 'root', [node('a', 'module')])),
            "node 'a' has kind 'module', not one of root, dir, file, class, function, method")
    refused('a duplicate id', document(node('.', 'root', [node('a', 'dir', [node('a', 'file')])])),
            "id 'a' appears twice")
    refused('a link to a missing id', document(SMALL, [['docs', 'nowhere']]),
            "links[0] names 'nowhere', which is no node")
    refused('a self-link', document(SMALL, [['docs', 'src'], ['docs', 'docs']]),
            "links[1] links 'docs' to itself")
    refused('a link that is not a pair', document(SMALL, [['docs']]),
            'links[0] is not a [from id, to id] pair')
    refused('a card on a non-tip', {'src/a.py': 'A file.'},
            "the card for 'src/a.py' sits on a node with a child that is no pointer leaf; only "
            'tips carry cards', as_cards=True)

    # tests/t.py has one pointer leaf, test_a, and one child that points nowhere, test_b
    refused('a card above a pointer leaf and a plain tip', {'tests/t.py': 'A test file.'},
            "the card for 'tests/t.py' sits on a node with a child that is no pointer leaf; only "
            'tips carry cards', as_cards=True)
    refused('a card on a pointer leaf', {'tests/t.py/test_a': 'Checks a.'},
            "the card for 'tests/t.py/test_a' sits on a pointer leaf, which takes no card; only "
            'tips carry cards', as_cards=True)
    refused('cards not an object', ['x'], 'cards is not an object of node id to text',
            as_cards=True)

    # a/f is the source of a link but has a child, so it is no pointer leaf, and a is no tip
    deep  = write_json(tmp / 'deep.json', document(node('.', 'root', [
        node('a', 'dir', [node('a/f', 'file', [node('a/f/g', 'function')])])]), [['a/f', 'a/f/g']]))
    above = write_json(tmp / 'deep.cards.json', {'a': 'A folder.'})
    q     = run(deep, '--cards', above, '-o', tmp / 'deep.html')
    check('P22 a link source with children is no pointer leaf, so a card on its parent is refused',
          q.returncode == 2 and q.stderr == f"page: {above}: the card for 'a' sits on a node with "
          'a child that is no pointer leaf; only tips carry cards\n',
          f'{q.returncode} {q.stderr!r}')

    # check's two children are pointer leaves, so check is a tip, and neither leaf is one; notes,
    # a childless branch of the centre, is the other tip and keeps its branch box
    ptr = write_json(tmp / 'ptr.json', document(node('.', 'root', [node('feature', 'dir', [
        node('feature/check', 'file', [node('feature/check/p1', 'function'),
                                       node('feature/check/p2', 'function')])]),
        node('notes', 'dir')]),
        [['feature/check/p1', 'feature'], ['feature/check/p2', 'feature']]))
    q   = run(ptr, '-o', tmp / 'ptr.html')
    pmap = page_data((tmp / 'ptr.html').read_text()).get('MAPS', {}).get('.')
    leaf = leaves(pmap) if pmap else None
    check('P23 a node whose children are all pointer leaves is a tip, and the pointer leaves are '
          'not counted as tips, so the one sm-leaf box is that tip\'s; a tip that is a branch of '
          'the centre is counted and keeps its branch box',
          q.returncode == 0 and 'page: 2 tips, 0 with a card, 2 without\n' in q.stderr
          and leaf == ['feature/check'], f'{q.stderr} {leaf}')

    stray = write_json(tmp / 'stray.cards.json', dict(SMALL_CARDS, gone='An old card.'))
    o     = tmp / 'stray.html'
    q     = run(tree, '--cards', stray, '-o', o)
    check('P11 a card naming no node is a warning, exit 0, and is not in the page',
          q.returncode == 0 and f"page: warning: {stray}: the card for 'gone' names no node, so "
          'it is not shown\n' in q.stderr and 'An old card.' not in o.read_text(),
          f'{q.returncode} {q.stderr}')

    art = tmp / 'small.art.html'
    q   = run(tree, '--cards', cards, '-o', art, '--artifact')
    a   = art.read_text() if art.exists() else ''
    check('P12 --artifact writes the page with no doctype, html, head or body tags',
          q.returncode == 0 and a and all(t not in a.lower() for t in
                                          ('<!doctype', '<html', '<head>', '<body>', '</body>',
                                           '</html>')) and '<title>' in a,
          q.stderr)

    q = run(tree)
    check('P13 -o is required', q.returncode == 2 and '-o' in q.stderr, q.stderr)

    bare = write_json(tmp / 'bare.json', {'schema': 1, 'tree': SMALL})
    q    = run(bare, '-o', tmp / 'bare.html')
    check('P19 a Document of schema and tree alone is built, exit 0',
          q.returncode == 0 and (tmp / 'bare.html').exists(), q.stderr)

    missing = []
    for gone in ('assets/page.html', 'assets/page.js', 'vendor/d3/d3.min.js',
                 'vendor/markmap-view/markmap-view.js'):
        copy = tmp / f'copy-{gone.replace("/", "-")}'
        for part in ('scripts/page.py', 'assets/page.html', 'assets/page.js',
                     'vendor/d3/d3.min.js', 'vendor/markmap-view/markmap-view.js'):
            (copy / part).parent.mkdir(parents=True, exist_ok=True)
            (copy / part).write_bytes((STUDY / part).read_bytes())
        (copy / gone).unlink()
        o = tmp / f'{copy.name}.html'
        q = subprocess.run([sys.executable, str(copy / 'scripts' / 'page.py'), str(tree), '-o',
                            str(o)], capture_output=True, text=True, check=False)
        # page.py names the resolved path: on macOS the temp folder sits under /private
        named = f'page: {copy.resolve() / gone}: cannot be read'
        if not (q.returncode == 2 and q.stderr.startswith(named)
                and 'Traceback' not in q.stderr and not o.exists()):
            missing.append((gone, q.returncode, q.stderr[-160:]))
    check('P20 a missing template, page script or vendored file is refused with page:, the file '
          'and the reason, exit 2', not missing, str(missing))

    flat = write_json(tmp / 'flat.json', document(node('.', 'root', [node(f'f{i}.py', 'file')
                                                                     for i in range(600)])))
    q    = run(flat, '-o', tmp / 'flat.html')
    check('P14 a map over the cap is written, exit 0, and stderr says which and how big',
          q.returncode == 0 and "page: note: map '.' has 601 nodes, over the 500 cap\n" in q.stderr,
          q.stderr)

    if page is None:
        check('P15 (page.py does not import)', False)
    else:
        labels = {n['id']: page.label(n) for n in (node('a', 'dir'), node('a.py', 'file'),
                                                   node('a.py/C', 'class'),
                                                   node('a.py/C/m', 'method'),
                                                   node('a.py/f', 'function'))}
        check('P15 functions and methods gain (), other labels keep their real names, and a '
              'label is escaped in the page',
              labels == {'a': 'a', 'a.py': 'a.py', 'a.py/C': 'C', 'a.py/C/m': 'm()',
                         'a.py/f': 'f()'}
              and page_data(text)['MAPS']['.']['children'][3]['children'][0]['children'][1]
              ['content'] == '<span class="sm-node sm-leaf">a&lt;b&gt;()</span>'
              and 'a<b>()' not in text, str(labels))


def page_data(text: str) -> dict:
    '''the page's data object, as page.js reads it.'''
    m = re.search(r'<script type="application/json" id="sm-data">(.*?)</script>', text, re.S)
    return json.loads(m[1]) if m else {}


def payload(tree: dict, id: str) -> dict:
    '''the payload of the node id in a markmap tree of the page's data, or {}.'''
    stack = [tree]
    while stack:
        n = stack.pop()
        if n['payload']['id'] == id:
            return n['payload']
        stack.extend(n['children'])
    return {}


def leaves(tree: dict) -> list[str]:
    '''the ids of the nodes whose box in a markmap tree of the page's data is sm-leaf, sorted.'''
    out, stack = [], [tree]
    while stack:
        n = stack.pop()
        if 'sm-leaf' in n['content'].split('"')[1].split():
            out.append(n['payload']['id'])
        stack.extend(n['children'])
    return sorted(out)


def vendored_cases(page) -> None:
    if page is None:
        check('P16 (page.py does not import)', False)
        check('P17 (page.py does not import)', False)
        return
    vendor = STUDY / 'vendor'
    hashes = [(v.path, hashlib.sha256((vendor / v.path).read_bytes()).hexdigest()
               == SHA256.get(v.path) == v.sha256, (vendor / v.licence_file).is_file())
              for v in page.VENDORED]
    check('P16 each vendored file matches the sha256 of its npm release and has its LICENSE '
          'beside it', len(hashes) == 2 and all(ok and lic for _, ok, lic in hashes), str(hashes))

    kept = page.VENDORED
    try:
        page.VENDORED = tuple(reversed(kept))
        text = page.render({'schema': 1, 'tree': SMALL}, {}, []).page
        order = 0 <= text.find(D3_HEAD) < text.find(MM_HEAD)
    except Exception as e:
        order = f'{type(e).__name__}: {e}'
    finally:
        page.VENDORED = kept
    check('P21 each library goes in its own slot by name, whatever the order of VENDORED',
          order is True, str(order))
    notice = (REPO / 'NOTICE').read_text()
    rows   = [(v.name, v.version, v.licence) for v in page.VENDORED
              if not any(v.name in l and v.version in l and v.licence in l
                         and f'skills/study/vendor/{v.path.split("/")[0]}' in l
                         for l in notice.splitlines())]
    check('P17 NOTICE names each vendored library, its version, licence and folder on one row',
          not rows, f'missing {rows}')


# ── the page in a browser ─────────────────────────────────────────────────────

JS_VISIBLE = '''() => [...new Set([...document.querySelectorAll('#mmR g.markmap-node, '
  + '#mmL g.markmap-node')].filter(g => g.closest('svg').style.display !== 'none')
  .map(g => g.dataset.id))].sort()'''

# a link's triangles, from its path: [centre x, centre y, length] each, in the page's pixels, and
# the zoom's scale
JS_TRIS = '''sel => { const el = document.querySelector(sel); if (!el || !el.getAttribute('d'))
  return null; const m = el.getScreenCTM();
  const at = (x, y) => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f];
  const tris = el.getAttribute('d').split('Z').filter(Boolean).map(t => {
    const v = t.match(/-?[\\d.]+/g).map(Number), p = [0, 2, 4].map(i => at(v[i], v[i + 1]));
    const bx = (p[1][0] + p[2][0]) / 2, by = (p[1][1] + p[2][1]) / 2;
    return [(p[0][0] + bx) / 2, (p[0][1] + by) / 2, Math.hypot(p[0][0] - bx, p[0][1] - by),
            p[0][0] - bx, p[0][1] - by]; });
  return {tris, k: Math.hypot(m.a, m.b)}; }'''

# a link's first and last triangle's centres, and the zoom's scale; null when it is not drawn
JS_ENDS = '''sel => { const t = (''' + JS_TRIS + ''')(sel); if (!t || !t.tris.length) return null;
  const a = t.tris[0], z = t.tris[t.tris.length - 1];
  return [[a[0], a[1]], [z[0], z[1]], t.k]; }'''

JS_BOX = '''sel => { const e = document.querySelector(sel); if (!e) return null;
  const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }'''


def node_sel(id: str, side: str = '') -> str:
    svg = f'#{side} ' if side else ''
    return f'{svg}g.markmap-node[data-id="{id}"]'


def link_sel(src: str, end: str) -> str:
    return f'#mmA path.xl[data-from="{src}"][data-to="{end}"]'


def near_end(ends) -> float:
    '''how far from its box a link's end triangle may sit: the first triangle is 4 to 11 px of the
    curve from its end, times the zoom, and 3 px of slack.'''
    return 11 * ends[2] + 3


def on_box(point, box, pad: float = 3) -> bool:
    x, y = point
    return box[0] - pad <= x <= box[2] + pad and box[1] - pad <= y <= box[3] + pad


def open_page(browser, path: Path, mac: bool | None = None, wait: int = 30000):
    '''mac None keeps the platform the browser reports; True or False forces a Mac or a non-Mac.'''
    ctx = browser.new_context(viewport={'width': 1400, 'height': 900})
    if mac is not None:
        ctx.add_init_script("Object.defineProperty(navigator, 'platform', "
                            f"{{get: () => '{'MacIntel' if mac else 'Linux x86_64'}'}})")
    pg = ctx.new_page()
    pg.requests = []
    pg.on('request', lambda r: pg.requests.append(r.url))
    pg.goto(path.as_uri())
    pg.errors = []
    pg.on('pageerror', lambda e: pg.errors.append(str(e)))
    try:
        pg.wait_for_selector(node_sel('.', 'mmR'), timeout=wait)
    except Exception:       # the page never drew its centre; the case reads that as a failure
        pass
    pg.wait_for_timeout(SETTLE)
    return ctx, pg


def click(pg, id: str, mod: str | None = None, side: str = '') -> None:
    '''a real click at the node's box; force skips the actionability wait, so the event goes to
    whatever the page has on top there, as a person's click does. mod 'all' presses the key that
    means everything on the platform the page reports: Cmd on a Mac, Ctrl elsewhere.'''
    if mod == 'all':
        mod = ('Meta' if pg.evaluate('/Mac|iPhone|iPad/.test(navigator.platform)')
               else 'Control')
    pg.click(node_sel(id, side) + ' foreignObject', modifiers=[mod] if mod else [], force=True)
    pg.wait_for_timeout(SETTLE)


def portal_sel(home: str) -> str:
    return f'#mmX g.xp[data-home="{home}"]'


def links_now(pg) -> dict:
    '''each drawn link by its source: [opacity, its path].'''
    return pg.evaluate('''() => Object.fromEntries([...document.querySelectorAll(
      "#mmA path.xl")].filter(p => p.getAttribute("d")).map(p => [p.dataset.from,
      [+getComputedStyle(p).opacity, p.getAttribute("d")]]))''')


def drawn(pg) -> list:
    return pg.evaluate('[...document.querySelectorAll("#mmA path.xl")].filter(p => '
                       'p.getAttribute("d")).map(p => p.dataset.from + ">" + p.dataset.to).sort()')


def crumbs(pg) -> list:
    return pg.evaluate('[...document.querySelectorAll("#crumbs > *")].map(e => '
                       'e.classList.contains("sep") ? "sep" : e.textContent)')


def visible(pg) -> set:
    return set(pg.evaluate(JS_VISIBLE))


def browser_cases(tmp: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        check(f'B1 to S6 (playwright does not import: {e})', False)
        return
    small = tmp / 'small.html'
    sets  = tmp / 'set.html'
    run(write_json(tmp / 'set.json', document(SET, SET_LINKS)), '--cards',
        write_json(tmp / 'set.cards.json', SET_CARDS), '-o', sets)
    if not small.exists() or not sets.exists():
        check('B1 to S6 (no page was built)', False)
        return
    top = {'.', 'src', 'tests', 'docs', 'tools'}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        fit_cases(browser, tmp)
        ctx, pg = open_page(browser, small)
        check('B1 the page opens with the centre and its branches shown, branches closed',
              visible(pg) == top, str(visible(pg)))
        folded = drawn(pg)

        click(pg, 'src')
        check('B2 a plain click on a branch opens one level, and its children stay closed',
              visible(pg) == top | {'src/a.py', 'src/b.js'}, str(visible(pg)))

        click(pg, 'tests', 'all')
        check('B3 Cmd or Ctrl-click on a branch opens everything under it',
              visible(pg) == top | {'src/a.py', 'src/b.js', 'tests/t.py', 'tests/t.py/test_a',
                                    'tests/t.py/test_b'}, str(visible(pg)))

        before = visible(pg)
        pg.click('#bLayout')
        pg.wait_for_timeout(SETTLE)
        one = visible(pg)
        pg.click('#bLayout')
        pg.wait_for_timeout(SETTLE)
        check('B4 the layout switch keeps every fold, one-sided and back to two-sided',
              one == before and visible(pg) == before
              and pg.evaluate('document.getElementById("mmL").style.display') == '',
              f'{sorted(before ^ one)} {sorted(before ^ visible(pg))}')

        pg.hover(node_sel('tests/t.py/test_a') + ' foreignObject', force=True)
        pg.wait_for_timeout(250)
        card = pg.evaluate('[document.getElementById("hc").classList.contains("on"), '
                           'document.getElementById("hc").innerText]')
        pg.hover(node_sel('tests/t.py') + ' foreignObject', force=True)
        pg.wait_for_timeout(250)
        none = pg.evaluate('document.getElementById("hc").classList.contains("on")')
        pg.hover(node_sel('tests/t.py/test_b') + ' foreignObject', force=True)
        pg.wait_for_timeout(250)
        bare = pg.evaluate('document.getElementById("hc").classList.contains("on")')
        click(pg, 'docs')
        pg.hover(node_sel('docs/d.py') + ' foreignObject', force=True)
        pg.wait_for_timeout(250)
        tip = pg.evaluate('[document.getElementById("hc").classList.contains("on"), '
                          'document.getElementById("hc").innerText]')
        click(pg, 'docs')
        check('B5 hovering a node whose children are all pointer leaves shows its card; a pointer '
              'leaf, a non-tip and a tip with no card show none',
              card[0] is False and tip == [True, 'Holds the docs build.']
              and not none and not bare, f'{card} {tip} {none} {bare}')

        # tests is open all the way and src one level, so only test_a's link has its source shown
        some = drawn(pg)
        click(pg, 'docs', 'all')
        click(pg, 'tools', 'all')
        pg.click('#bFit')
        pg.wait_for_timeout(SETTLE)
        three = sorted(['tests/t.py/test_a>src/a.py/Cls/run', 'docs/d.py/build>src/b.js/main',
                        'tools/x.py/go>docs/d.py/build'])
        check('B6 a link is drawn only while its source is on screen, so a folded branch sends '
              'none and opening it sends its links, and a repeated link is drawn once',
              folded == [] and some == ['tests/t.py/test_a>src/a.py/Cls/run']
              and drawn(pg) == three, f'{folded} {some} {drawn(pg)}')

        def light(id: str) -> dict:
            pg.mouse.move(5, 5)
            pg.wait_for_timeout(200)
            pg.hover(node_sel(id) + ' foreignObject', force=True)
            pg.wait_for_timeout(300)
            return links_now(pg)

        lit = light('tests/t.py/test_a')
        pg.wait_for_timeout(300)
        later = links_now(pg)
        cold = {k: v for k, v in lit.items() if k != 'tests/t.py/test_a'}
        check('B7 hovering lights its path and its links: full opacity and sliding triangles on '
              'those links only',
              lit.get('tests/t.py/test_a') and lit['tests/t.py/test_a'][0] == 1
              and lit['tests/t.py/test_a'][1] != later['tests/t.py/test_a'][1]
              and cold and all(o < .5 and later[k][1] == d for k, (o, d) in cold.items())
              and pg.evaluate(f'document.querySelector(\'{node_sel("tests")}\')'
                              '.classList.contains("lit")'),
              str(lit))
        lit = light('docs/d.py/build')
        pg.wait_for_timeout(300)
        pg.mouse.move(5, 5)
        pg.wait_for_timeout(100)
        coast = links_now(pg)
        pg.wait_for_timeout(200)
        drift = links_now(pg)
        pg.wait_for_timeout(2700)       # a link coasts to a stop in under 3 s
        rest = links_now(pg)
        pg.wait_for_timeout(300)
        still = links_now(pg)
        check('B8 a link lights from either end, coasts on for a moment once the hover ends, and '
              'at rest every link is faint and still',
              lit.get('docs/d.py/build', [0])[0] == 1 and lit.get('tools/x.py/go', [0])[0] == 1
              and lit.get('tests/t.py/test_a', [1])[0] < .5
              and coast.get('docs/d.py/build') != drift.get('docs/d.py/build')
              and rest and rest == still and all(o < .5 for o, _ in rest.values()), f'{lit} {rest}')

        ends = pg.evaluate(JS_ENDS, link_sel('tests/t.py/test_a', 'src/a.py/Cls/run'))
        src  = pg.evaluate(JS_BOX, node_sel('src/a.py', 'mmR') + ' foreignObject')
        frm  = pg.evaluate(JS_BOX, node_sel('tests/t.py/test_a', 'mmL') + ' foreignObject')
        check('B9 a link from the left tree to the right tree runs from its pointer box to the '
              'nearest shown box of its target',
              ends is not None and on_box(ends[0], frm, near_end(ends))
              and on_box(ends[1], src, near_end(ends)),
              f'{ends} {frm} {src}')

        pg.click('#mmX circle.xh[data-from="tests/t.py/test_a"]')
        pg.wait_for_timeout(SETTLE + 100)
        shown = visible(pg)
        check('B10 clicking an arrow opens the way to its target and spotlights it',
              'src/a.py/Cls/run' in shown and pg.evaluate(
                  f'document.querySelector(\'{node_sel("src/a.py/Cls/run")}\')'
                  '.classList.contains("lit")'), str(sorted(shown)))

        click(pg, '.', side='mmR')
        closed = visible(pg)
        click(pg, '.', 'all', side='mmR')
        everything = visible(pg)
        click(pg, '.', side='mmR')
        click(pg, '.', side='mmR')
        check('B11 the centre: a plain click closes it, Cmd or Ctrl-click opens everything on both sides, '
              'and a plain click opens one level',
              closed == {'.'} and everything == SMALL_IDS and visible(pg) == top,
              f'{closed} {sorted(SMALL_IDS - everything)} {visible(pg)}')
        check('B12 the page makes no network request', all(u.startswith('file:')
                                                           for u in pg.requests), str(pg.requests))
        ctx.close()

        ctx, pg = open_page(browser, small, mac=True)
        click(pg, 'tests', 'Meta')
        click(pg, '.', side='mmR')
        click(pg, '.', 'Meta', side='mmR')
        check('B13 on a Mac, Cmd-click opens everything, on a branch and on the centre',
              visible(pg) == SMALL_IDS, str(sorted(SMALL_IDS - visible(pg))))
        ctx.close()

        # the host turns a real Ctrl-click into a context menu on a Mac, so these clicks are
        # events with the key's flag set, and either half of the rule is held on any host
        held, key = {}, '''([sel, k]) => document.querySelector(sel).dispatchEvent(
          new MouseEvent("click", {bubbles: true, [k]: true}))'''
        for mac, own, other in ((True, 'metaKey', 'ctrlKey'), (False, 'ctrlKey', 'metaKey')):
            ctx, pg = open_page(browser, small, mac=mac)
            pg.evaluate(key, [node_sel('tests') + ' foreignObject', other])
            pg.wait_for_timeout(SETTLE)
            wrong = 'tests/t.py/test_a' in visible(pg)
            click(pg, '.', side='mmR')
            pg.evaluate(key, [node_sel('.', 'mmR') + ' foreignObject', own])
            pg.wait_for_timeout(SETTLE)
            held[own] = (wrong, visible(pg) == SMALL_IDS)
            ctx.close()
        check('B24 Cmd opens everything on a Mac and Ctrl does not; Ctrl opens everything '
              'elsewhere and Cmd does not', held == {'metaKey': (False, True),
                                                     'ctrlKey': (False, True)}, str(held))

        ctx, pg = open_page(browser, sets)
        shadow = pg.evaluate('''() => [getComputedStyle(document.querySelector(
          'g.markmap-node[data-id="app"] .sm-branch')).boxShadow,
          getComputedStyle(document.querySelector('g.markmap-node[data-id="."] .sm-root'))
          .boxShadow]''')
        stacked = [len([p for p in re.split(r',\s*(?![^()]*\))', s) if 'inset' not in p])
                   for s in shadow]
        pg.hover(node_sel('app') + ' foreignObject', force=True)
        pg.wait_for_timeout(250)
        card = pg.evaluate('document.getElementById("hc").classList.contains("on")')
        check('S1 the top map shows its portals as stacked boxes, and a portal has no card',
              visible(pg) == {'.', 'app', 'lib', 'docs'} and stacked[0] >= 2 and stacked[1] == 0
              and not card and crumbs(pg) == ['proj'],
              f'{visible(pg)} {stacked} {card}')

        ends = pg.evaluate(JS_ENDS, link_sel('docs', 'app'))
        port = pg.evaluate(JS_BOX, portal_sel('app/m1.py/f2') + ' circle.pd')
        docs = pg.evaluate(JS_BOX, node_sel('docs') + ' foreignObject')
        check("S2 a link into another map ends at the round portal of its home, not at the "
              'stacked box that leads to it',
              ends is not None and port is not None and on_box(ends[0], docs, near_end(ends))
              and on_box(ends[1], port, near_end(ends) + 17 * ends[2]),
              f'{ends} {docs} {port}')

        click(pg, 'app')
        pg.wait_for_timeout(300)
        inner = visible(pg)
        check('S3 clicking a portal swaps to its map, and the breadcrumb shows the path',
              inner == {'app'} | {f'app/m{i}.py' for i in range(25)}
              and crumbs(pg) == ['proj', 'sep', 'app'], f'{sorted(inner)[:5]} {crumbs(pg)}')

        click(pg, 'app/m0.py')
        opened = visible(pg)
        pg.click('#crumbs button')
        pg.wait_for_timeout(SETTLE)
        back = visible(pg)
        click(pg, 'app')
        pg.wait_for_timeout(300)
        check('S4 the breadcrumb goes back up, and a map keeps its folds when it is entered again',
              'app/m0.py/f0' in opened and back == {'.', 'app', 'lib', 'docs'}
              and visible(pg) == opened, f'{sorted(back)} {len(opened)} {len(visible(pg))}')

        pg.go_back()
        pg.wait_for_timeout(SETTLE)
        up = visible(pg)
        pg.go_forward()
        pg.wait_for_timeout(SETTLE)
        check('S5 the Back and Forward buttons move between maps',
              up == {'.', 'app', 'lib', 'docs'} and visible(pg) == opened,
              f'{sorted(up)} {len(visible(pg))}')
        check('S6 the page of maps makes no network request',
              all(u.startswith('file:') for u in pg.requests), str(pg.requests))

        glass = []
        for theme in ('light', 'dark'):
            pg.evaluate(f'document.documentElement.setAttribute("data-theme", "{theme}")')
            glass.append(pg.evaluate('''() => { const c = document.getElementById('crumbs'),
              s = getComputedStyle(c), b = getComputedStyle(document.getElementById('bar'));
              return [s.backdropFilter, s.backgroundColor, b.backdropFilter,
                [...c.querySelectorAll('.sep')].map(e => e.tagName.toLowerCase()).join(),
                c.textContent.includes('\u203a')]; }'''))
        check('S7 the breadcrumb bar is frosted glass in both themes, the button bar is not, and '
              'each separator is an svg chevron with no › left',
              all('blur' in f and 'saturate' in f and 'rgba' in bg and bf == 'none'
                  and seps == 'svg' and not arrow for f, bg, bf, seps, arrow in glass),
              str(glass))
        ctx.close()

        tricky_cases(browser, tmp)
        link_cases(browser, tmp)
        portal_cases(browser, tmp)
        back_cases(browser, tmp)
        rim_cases(browser)
        edge_cases(browser, tmp)
        browser.close()


def tricky_cases(browser, tmp: Path) -> None:
    '''B14 to B17: pages built from inputs that once broke the page, and the arrow's spotlight.'''
    marks = '/*__PAGE__*/ /*__DATA__*/ /*__D3__*/ /*__MARKMAP__*/ __TITLE__'
    slots = node('.', 'root', name=f'demo {marks}', children=[
        node('a', 'dir', [node('a/x.py', 'file', [node('a/x.py/f', 'function')])]),
        node('b', 'dir', [node('b/y.py', 'file')])])
    out = tmp / 'slots.html'
    run(write_json(tmp / 'slots.json', document(slots)), '--cards',
        write_json(tmp / 'slots.cards.json', {'b/y.py': f'Holds {marks}.'}), '-o', out)
    ctx, pg = open_page(browser, out, wait=3000)
    shown = visible(pg)
    if shown:
        click(pg, 'b')
        pg.click('#bFit')
        pg.wait_for_timeout(SETTLE)
        pg.hover(node_sel('b/y.py') + ' foreignObject', force=True)
        pg.wait_for_timeout(250)
    card = pg.evaluate('document.getElementById("hc").innerText')
    text = out.read_text() if out.exists() else ''
    check('B14 a card and a name holding the slot markers render as text, and each library and '
          'the page script are in the page once',
          shown == {'.', 'a', 'b'} and card == f'Holds {marks}.' and not pg.errors
          and pg.title() == f'demo {marks}'
          and [text.count(h) for h in (D3_HEAD, MM_HEAD, '// page.js ')] == [1, 1, 1],
          f'{shown} {card!r} {pg.errors[:1]} {pg.title()!r}')
    ctx.close()

    proto = node('.', 'root', name='demo', children=[
        node('a', 'dir', [node('a/<!--<script>.py', 'file')]),
        node('z', 'dir', [flat_dir('z/__proto__', 500)])])
    proto['children'][1]['children'][0]['name'] = '__proto__'
    proto['children'][1]['children'][0]['id'] = '__proto__'
    out = tmp / 'proto.html'
    run(write_json(tmp / 'proto.json', document(proto)), '-o', out)
    ctx, pg = open_page(browser, out, wait=3000)
    first = visible(pg)
    bar   = pg.evaluate('!document.getElementById("crumbs").hidden')
    if first:
        click(pg, 'a')
        click(pg, 'z')
    opened = visible(pg)
    if first:
        click(pg, '__proto__')
        pg.wait_for_timeout(300)
    check('B15 a file id that reads as an HTML comment and a script tag, and a map named '
          '__proto__, give a working page that counts both maps and shows its breadcrumb',
          first == {'.', 'a', 'z'} and bar and 'a/<!--<script>.py' in opened
          and '__proto__' in opened
          and crumbs(pg) == ['demo', 'sep', '__proto__']
          and len(visible(pg)) == 500 and not pg.errors,
          f'{first} {bar} {sorted(opened)} {crumbs(pg)} {len(visible(pg))} {pg.errors[:1]}')
    ctx.close()

    one = node('.', 'root', name='demo', children=[
        node('only', 'dir', [node('only/x.py', 'file', [node('only/x.py/f', 'function')]),
                             node('only/y.py', 'file')])])
    out = tmp / 'one.html'
    run(write_json(tmp / 'one.json', document(one)), '-o', out)
    ctx, pg = open_page(browser, out)
    first = visible(pg)
    centre = pg.evaluate(JS_BOX, node_sel('.', 'mmR') + ' foreignObject')
    under  = pg.evaluate('([x, y]) => document.elementFromPoint(x, y).closest("svg").id',
                         [(centre[0] + centre[2]) / 2, (centre[1] + centre[3]) / 2])
    pg.mouse.click((centre[0] + centre[2]) / 2, (centre[1] + centre[3]) / 2)
    pg.wait_for_timeout(SETTLE)
    closed = visible(pg)
    centre = pg.evaluate(JS_BOX, node_sel('.', 'mmR') + ' foreignObject')
    pg.mouse.click((centre[0] + centre[2]) / 2, (centre[1] + centre[3]) / 2)
    pg.wait_for_timeout(SETTLE)
    reopened = visible(pg)

    # a click that reaches the left tree's hidden centre still goes by the map's own children
    pg.evaluate('document.querySelector(\'#mmL g.markmap-node[data-id="."] foreignObject\')'
                '.dispatchEvent(new MouseEvent("click", {bubbles: true}))')
    pg.wait_for_timeout(SETTLE)
    check('B16 the empty left tree takes no input at the centre, and a plain click on the centre '
          'of a map with one branch, on either tree, closes it and opens it again',
          under == 'mmR' and first == {'.', 'only'} and closed == {'.'} and reopened == first
          and visible(pg) == {'.'}, f'{under} {first} {closed} {reopened} {visible(pg)}')
    ctx.close()

    ctx, pg = open_page(browser, tmp / 'small.html')

    # with everything open the arrow click moves no box, so the pointer stays on bare canvas
    click(pg, '.', side='mmR')
    click(pg, '.', 'all', side='mmR')
    arrow = pg.evaluate(JS_BOX, '#mmX circle.xh[data-from="tests/t.py/test_a"]')
    x, y  = (arrow[0] + arrow[2]) / 2, (arrow[1] + arrow[3]) / 2
    pg.mouse.move(x, y)
    pg.mouse.click(x, y)
    pg.wait_for_timeout(SETTLE + 100)
    lit = pg.evaluate('document.getElementById("wrap").classList.contains("spot")')
    bare = pg.evaluate('''([x, y]) => { for (let a = 0; a < 16; a++) {
      const px = x + 50 * Math.cos(a * Math.PI / 8), py = y + 50 * Math.sin(a * Math.PI / 8),
        e = document.elementFromPoint(px, py);
      if (e && e.id === 'mmR') return [px, py]; }
      return null; }''', [x, y])
    if bare:
        pg.mouse.move(*bare)
        pg.wait_for_timeout(300)
    check('B17 an arrow click spotlights its target, and one move 50 px onto the bare svg clears '
          'it',
          lit and bare is not None
          and not pg.evaluate('document.getElementById("wrap").classList.contains("spot")'),
          f'{lit} {bare}')
    ctx.close()


TRIANGLES = re.compile(r'(M-?[\d.]+,-?[\d.]+(L-?[\d.]+,-?[\d.]+){2}Z)+')


def link_cases(browser, tmp: Path) -> None:
    '''B18 to B21: how links are drawn, what folding costs, reduced motion and the bottom bar.'''
    ctx = browser.new_context(viewport={'width': 1400, 'height': 900})
    # every call to the page-measuring path methods is counted, wherever the page makes it
    ctx.add_init_script('''window.measured = 0;
      for (const k of ['getTotalLength', 'getPointAtLength']) {
        const f = SVGGeometryElement.prototype[k];
        SVGGeometryElement.prototype[k] = function(...a){
          window.measured++; return f.apply(this, a); };
      }''')
    pg = ctx.new_page()
    pg.goto((tmp / 'small.html').as_uri())
    pg.wait_for_selector(node_sel('.', 'mmR'))
    pg.wait_for_timeout(SETTLE)
    click(pg, '.', side='mmR')
    click(pg, '.', 'all', side='mmR')
    sel   = link_sel('tests/t.py/test_a', 'src/a.py/Cls/run')
    paths = pg.evaluate('''() => [...document.querySelectorAll("path.xl")].map(p => [
      p.closest("svg").id, p.getAttribute("d") || "", p.getAttribute("marker-end"),
      getComputedStyle(p).fill, getComputedStyle(p).stroke])''')
    under = pg.evaluate('''() => !!(document.getElementById("mmA")?.compareDocumentPosition(
      document.getElementById("mmR")) & Node.DOCUMENT_POSITION_FOLLOWING)''')
    tris  = pg.evaluate(JS_TRIS, sel)
    gaps  = ([math.hypot(b[0] - a[0], b[1] - a[1]) / tris['k']
              for a, b in zip(tris['tris'], tris['tris'][1:])] if tris else [])
    sizes = [t[2] / tris['k'] for t in tris['tris']] if tris else []
    ahead = ([a[3] * (b[0] - a[0]) + a[4] * (b[1] - a[1]) > 0
              for a, b in zip(tris['tris'], tris['tris'][1:])] if tris else [])
    check('B18 each link is one filled path of small triangles, one every 7 px and about 3 px '
          'long, each pointing on toward the target, on a layer beneath the boxes, with no marker',
          paths and all(svg == 'mmA' and TRIANGLES.fullmatch(d) and marker is None
                        and fill != 'none' and stroke == 'none'
                        for svg, d, marker, fill, stroke in paths)
          and under and not pg.evaluate('document.querySelectorAll("marker").length')
          and len(gaps) > 3 and all(6 < g < 8 for g in gaps) and all(2.5 < z < 4 for z in sizes)
          and all(ahead),
          f'{paths[:2]} {under} {gaps[:4]} {sizes[:2]}')

    pg.evaluate('window.measured = 0')
    for _ in range(2):
        click(pg, 'src', 'all')
        click(pg, 'tests')
    js = (STUDY / 'assets' / 'page.js').read_text()
    check('B19 folding and opening branches never measures a path: no getTotalLength or '
          'getPointAtLength call, and page.js names neither',
          pg.evaluate('window.measured') == 0 and 'getTotalLength' not in js
          and 'getPointAtLength' not in js, str(pg.evaluate('window.measured')))

    buttons = pg.evaluate('[...document.querySelectorAll("#bar button")].map(b => b.textContent)')
    check('B21 the bottom bar holds exactly Two-sided, +, \u2212, Fit and Theme, and no test '
          'button is in the page',
          buttons == ['Two-sided', '+', '\u2212', 'Fit', 'Theme']
          and not pg.evaluate('!!document.querySelector("#bPortal, #bArrow")'), str(buttons))
    ctx.close()

    ctx = browser.new_context(viewport={'width': 1400, 'height': 900}, reduced_motion='reduce')
    pg  = ctx.new_page()
    pg.goto((tmp / 'small.html').as_uri())
    pg.wait_for_selector(node_sel('.', 'mmR'))
    pg.wait_for_timeout(SETTLE)
    click(pg, 'tests', 'all')
    pg.click('#bFit')
    pg.wait_for_timeout(SETTLE)
    pg.hover(node_sel('tests/t.py/test_a') + ' foreignObject', force=True)
    pg.wait_for_timeout(200)
    one = links_now(pg).get('tests/t.py/test_a')
    pg.wait_for_timeout(400)
    two = links_now(pg).get('tests/t.py/test_a')
    check('B20 under reduced motion a lit link goes full but its triangles do not move',
          one is not None and one[0] == 1 and one == two, f'{one} {two}')
    ctx.close()


PORT = node('.', 'root', name='port', children=[
    node('a', 'dir', [node('a/p.md', 'file', [node('a/p.md/s1', 'function'),
                                              node('a/p.md/s2', 'function')]),
                      node('a/q.md', 'file', [node('a/q.md/s3', 'function'),
                                              node('a/q.md/s4', 'function')])]),
    node('big', 'dir', files('big', 25, 10)),
    node('big2', 'dir', files('big2', 25, 10))])
PORT_LINKS = [['a/p.md', 'big/m1.py/f2'], ['a/p.md', 'big2/m1.py/f0'],
              ['a/p.md/s1', 'big/m1.py/f2'], ['a/q.md', 'big2/m0.py/f0'],
              ['a/p.md/s2', 'a/q.md/s3'], ['a/p.md/s2', 'a/q.md/s4']]
PORT_CARDS = {'a/p.md': 'Two steps, each a pointer.'}


def portal_cases(browser, tmp: Path) -> None:
    '''S8 to S14: links whose home is on another map end at round portals on the map's rim.'''
    out = tmp / 'port.html'
    q   = run(write_json(tmp / 'port.json', document(PORT, PORT_LINKS)), '--cards',
              write_json(tmp / 'port.cards.json', PORT_CARDS), '-o', out)
    if q.returncode != 0:
        check(f'S8 to S14 (the portal page was not built: {q.stderr.strip()})', False)
        return
    ctx, pg = open_page(browser, out)
    cdp = ctx.new_cdp_session(pg)
    cdp.send('Performance.enable')

    # every animation frame the page asks for from here on is counted
    pg.evaluate('''() => { window.frames_asked = 0; const ask = window.requestAnimationFrame;
      window.requestAnimationFrame = f => { window.frames_asked++; return ask(f); }; }''')
    frames = lambda: pg.evaluate('window.frames_asked')

    # a narrow window, where the first view of the map fits only if it fits its portals too
    pg.set_viewport_size({'width': 900, 'height': 700})
    pg.click('#bFit')
    pg.wait_for_timeout(SETTLE)
    click(pg, 'a')
    pg.wait_for_timeout(300)
    on_screen = lambda h: pg.evaluate(f'''() => {{ const r = document.querySelector(
      '{portal_sel(h)}').getBoundingClientRect(); return r.left >= 0 && r.top >= 0
      && r.right <= innerWidth && r.bottom <= innerHeight; }}''')
    homes = lambda: pg.evaluate('''() => [...document.querySelectorAll("#mmX g.xp")]
      .filter(g => g.getAttribute("display") !== "none")
      .map(g => [g.dataset.home, g.querySelector("text").textContent]).sort()''')
    first = homes()
    ends  = pg.evaluate(JS_ENDS, '#mmA path.xl[data-from="a/p.md"][data-home="big/m1.py/f2"]')
    port  = pg.evaluate(JS_BOX, portal_sel('big/m1.py/f2') + ' circle.pd')
    seen  = [on_screen(h) for h, _ in first]
    check('S8 a link whose home is on another map ends at a round portal named for its home, one '
          'per home, and the first view of a map holds its portals',
          first == [['big/m1.py/f2', 'f2()'], ['big2/m0.py/f0', 'f0()'], ['big2/m1.py/f0', 'f0()']]
          and ends is not None and port is not None
          and on_box(ends[1], port, near_end(ends) + 17 * ends[2]) and all(seen),
          f'{first} {ends} {port} {seen}')
    pg.set_viewport_size({'width': 1400, 'height': 900})
    pg.click('#bFit')
    pg.wait_for_timeout(SETTLE)

    folded = drawn(pg)
    click(pg, 'a/p.md')
    opened = drawn(pg)
    check("S9 a folded branch's pointers send no links and opening it sends them: two links into "
          'one portal, and two links between the same two boxes drawn once',
          folded == ['a/p.md>a', 'a/p.md>a', 'a/q.md>a']
          and opened == ['a/p.md/s1>a', 'a/p.md/s2>a/q.md/s3', 'a/p.md>a', 'a/p.md>a', 'a/q.md>a']
          and homes() == first, f'{folded} {opened} {homes()}')

    def outside() -> list:
        boxes = pg.evaluate('''() => [...document.querySelectorAll("#mmR g.markmap-node>"
          + "foreignObject, #mmL g.markmap-node:not(.sm-mirror)>foreignObject")].map(f => {
          const r = f.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })''')
        hull = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes)]
        return [pg.evaluate(JS_BOX, portal_sel(h) + ' circle.pd') for h, _ in first], hull

    pg.click('#bFit')
    pg.wait_for_timeout(SETTLE)
    ports, hull = outside()
    k     = pg.evaluate('document.getElementById("ag").getScreenCTM().a')
    centre = lambda b: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    apart = [math.dist(centre(a), centre(b)) / k for i, a in enumerate(ports) if a
             for b in ports[i + 1:] if b]
    check("S10 each portal sits outside the box around the map's boxes, two portals of one caller "
          'slide apart along the rim, and Fit keeps every portal and its name on screen',
          len(ports) == 3 and None not in ports
          and all(not on_box(centre(p), hull, 20) for p in ports)
          and min(apart) > 80 and all(on_screen(h) for h, _ in first),
          f'{ports} {hull} {apart}')

    turn = lambda h: pg.evaluate(f'''() => document.querySelector('{portal_sel(h)} circle.po')
      ?.getAttribute('transform')''')
    pg.hover(node_sel('a/p.md') + ' foreignObject', force=True)
    pg.wait_for_timeout(600)
    card = pg.evaluate('[document.getElementById("hc").classList.contains("on"), '
                       'document.getElementById("hc").innerText]')
    a1, b1 = turn('big/m1.py/f2'), turn('big2/m0.py/f0')
    pg.wait_for_timeout(300)
    a2, b2 = turn('big/m1.py/f2'), turn('big2/m0.py/f0')
    check("S11 hovering a tip whose children are pointers shows its card and spins a portal its "
          'links end at, and not one they do not',
          card == [True, 'Two steps, each a pointer.'] and a1 and a1 != a2 and b1 == b2,
          f'{card} {a1} {a2} {b1} {b2}')

    pg.mouse.move(5, 450)
    pg.wait_for_timeout(100)
    c1 = turn('big/m1.py/f2')
    pg.wait_for_timeout(200)
    c2 = turn('big/m1.py/f2')
    pg.wait_for_timeout(3700)       # a portal and a link coast to a stop in under 3 s
    metric = lambda: {m['name']: m['value'] for m in cdp.send('Performance.getMetrics')['metrics']}
    before, at, asked = metric(), turn('big/m1.py/f2'), frames()
    pg.wait_for_timeout(2000)
    after = metric()
    check('S12 once the hover ends everything coasts to a stop: the portal still turns just after, '
          'and then no layout and no animation frame in 2 s of idle',
          a1 != a2 and c1 != c2 and after['LayoutCount'] == before['LayoutCount']
          and turn('big/m1.py/f2') == at and frames() == asked,
          f"{after['LayoutCount'] - before['LayoutCount']} layouts, {frames() - asked} frames")

    if pg.query_selector(portal_sel('big/m1.py/f2')):
        pg.click(portal_sel('big/m1.py/f2'))
    pg.wait_for_timeout(SETTLE + 600)
    check("S13 clicking a portal goes to its home's map and spotlights the home",
          crumbs(pg) == ['port', 'sep', 'big'] and 'big/m1.py/f2' in visible(pg)
          and pg.evaluate(f'''document.querySelector('{node_sel("big/m1.py/f2")}')
            .classList.contains('lit')''') and not pg.errors,
          f'{crumbs(pg)} {sorted(visible(pg))[:4]} {pg.errors[:1]}')

    # the portal was hovered and turning when it was clicked, and its map is gone from the page
    pg.mouse.move(5, 450)
    pg.wait_for_timeout(4000)
    asked = frames()
    pg.wait_for_timeout(1000)
    idle = frames() - asked
    pg.go_back()
    pg.wait_for_timeout(SETTLE + 3000)
    at = turn('big/m1.py/f2')
    pg.wait_for_timeout(400)
    check('S14 after a jump through a portal nothing keeps turning: no animation frame on the '
          "home's map, and back on the first map its portal is still",
          idle == 0 and crumbs(pg) == ['port', 'sep', 'a'] and turn('big/m1.py/f2') == at,
          f'{idle} frames, {crumbs(pg)} {at}')
    ctx.close()


JS_PORTS = '''() => [...document.querySelectorAll("#mmX g.xp")]
  .filter(g => g.getAttribute("display") !== "none")
  .map(g => { const m = g.transform.baseVal.getItem(0).matrix;
                return [g.dataset.home, m.e, m.f]; })'''


def back_cases(browser, tmp: Path) -> None:
    '''S15 to S17: two portals that meet across the left ray, and Back with the pointer still.'''
    wrap = node('.', 'root', name='wrap', children=[
        node('big', 'dir', files('big', 25, 10)), node('p1', 'dir'),
        node('big2', 'dir', files('big2', 25, 10)), node('p2', 'dir'), node('x', 'dir')])
    out = tmp / 'wrap.html'
    run(write_json(tmp / 'wrap.json', document(wrap, [['p1', 'big/m1.py/f2'],
                                                      ['p2', 'big2/m1.py/f0']])), '-o', out)
    ctx, pg = open_page(browser, out)
    pg.click('#bFit')
    pg.wait_for_timeout(SETTLE)
    ports = pg.evaluate(JS_PORTS)
    ctx.close()

    # one caller sends links to three homes, so all three portals want one spot on the right side
    three = node('.', 'root', name='three', children=[
        node('big', 'dir', files('big', 25, 10)), node('f1', 'dir'), node('c', 'dir'),
        node('big2', 'dir', files('big2', 25, 10)), node('f2', 'dir')])
    out = tmp / 'three.html'
    run(write_json(tmp / 'three.json', document(three, [['c', 'big/m1.py/f2'],
                                                        ['c', 'big2/m1.py/f0'],
                                                        ['c', 'big/m0.py/f0']])), '-o', out)
    ctx, pg = open_page(browser, out)
    pg.click('#bFit')
    pg.wait_for_timeout(SETTLE)
    trio = pg.evaluate(JS_PORTS)
    ctx.close()
    apart = [[math.dist(a[1:], b[1:]) for i, a in enumerate(ps) for b in ps[i + 1:]]
             for ps in (ports, trio)]
    check('S15 two portals whose callers sit either side of the left ray are 110 px apart or more '
          'along the rim, the last and the first compared too, and three that want one spot are '
          'spread until each is 110 px from the next',
          len(ports) == 2 and min(apart[0]) >= 109.5 and len(trio) == 3
          and len({x for _, x, _ in trio}) == 1 and min(apart[1]) >= 109.5,
          f'{ports} {trio} {apart}')

    # each Back below is pressed with the pointer still where it clicked, so its pin is still set
    out = tmp / 'port.html'
    ctx, pg = open_page(browser, out)
    click(pg, 'a')
    pg.click(portal_sel('big/m1.py/f2'))
    pg.wait_for_timeout(SETTLE + 600)
    pg.evaluate('history.back()')
    pg.wait_for_timeout(SETTLE + 600)
    after = crumbs(pg), 'a/p.md' in visible(pg), list(pg.errors)
    pg.click('#crumbs button')
    pg.wait_for_timeout(SETTLE)
    check('S16 Back after a portal click, with the pointer still, shows the first map whole with '
          'no error, and the breadcrumb still goes up from it',
          after == (['port', 'sep', 'a'], True, []) and crumbs(pg) == ['port']
          and 'big' in visible(pg) and not pg.errors, f'{after} {crumbs(pg)} {pg.errors[:1]}')
    ctx.close()

    ctx, pg = open_page(browser, out)
    click(pg, 'a')
    click(pg, 'a/p.md')
    pg.click('#mmX circle.xh[data-from="a/p.md/s2"][data-to="a/q.md/s3"]', force=True)
    pg.wait_for_timeout(SETTLE)
    lit = pg.evaluate(f'''document.querySelector('{node_sel("a/q.md/s3")}')
      .classList.contains('lit')''')
    pg.evaluate('history.back()')
    pg.wait_for_timeout(SETTLE + 600)
    after = crumbs(pg), 'big' in visible(pg), list(pg.errors)
    click(pg, 'a')
    pg.wait_for_timeout(300)
    check('S17 Back after an arrow click inside a map, with the pointer still, shows the map above '
          'with no error, and its portals still lead down',
          lit and after == (['port'], True, []) and crumbs(pg) == ['port', 'sep', 'a']
          and not pg.errors, f'{lit} {after} {crumbs(pg)} {pg.errors[:1]}')
    ctx.close()



def js_function(name: str) -> str:
    '''the source of one top-level function in page.js, from its function line to its closing
    brace.'''
    js    = (STUDY / 'assets' / 'page.js').read_text()
    start = js.index(f'\nfunction {name}(') + 1
    return js[start:js.index('\n}\n', start) + 2]


def rim_gaps(placed: list[float], rim: float) -> list[float]:
    '''the gaps along a rim of length rim between neighbouring positions, the last and the first
    compared too.'''
    m = sorted(s % rim for s in placed)
    return [(m[(i + 1) % len(m)] + (rim if i + 1 == len(m) else 0)) - m[i] for i in range(len(m))]


JS_SPREAD = '''([src, cases]) => { eval(src + '; window.spread = spread;');
  return cases.map(([P, ss]) => { const want = ss.map((s, i) => ({i, s}));
    window.spread(want, P); return want.sort((A, B) => A.i - B.i).map(w => w.s); }); }'''


def rim_cases(browser) -> None:
    '''S18 and S19: portals spread along the rim, and the rim point of a zero ray.'''
    pg = browser.new_page()
    one, seam, fits, full, apart, pair, wrap, even = pg.evaluate(JS_SPREAD, [
        'const APART = 110;\n' + js_function('spread'),
        [[4000, [1000] * 28], [4000, [3990] * 10 + [5] * 18], [1040, [500] * 9],
         [1040, [500] * 10], [4000, [0, 500, 1000]], [4000, [1000, 1000]],
         [1040, [130, 130, 210, 250, 460, 670, 890, 920]],
         [1040, [40, 210, 280, 320, 330, 510, 660, 820, 910, 1000]]]])
    gaps = {k: rim_gaps(v, r) for k, v, r in (('one', one, 4000), ('seam', seam, 4000),
                                               ('fits', fits, 1040), ('full', full, 1040),
                                               ('wrap', wrap, 1040), ('even', even, 1040))}
    rel = [(s + 10 / 28 + 2000) % 4000 - 2000 for s in seam]     # seam's spots from their mean
    check('S18 28 portals that want one spot end 110 px apart along the rim, centred on it, and '
          'so do 28 across the rim\'s seam, in the order they want; 9 of 110 px fit a rim of '
          '1040, 10 do not and spread evenly 104 px apart; portals already apart stay where they '
          'want to be; clusters that meet across the cut still keep 110 px, and 10 scattered on a '
          'rim of 1040 sit 104 apart',
          all(abs(g - 110) < 0.5 for g in sorted(gaps['one'])[:-1])
          and abs(sum((s - 1000 + 2000) % 4000 - 2000 for s in one) / 28) < 0.5
          and sorted(gaps['seam'])[0] >= 109.5 and sorted(gaps['seam'])[-1] > 900
          and abs(max(map(abs, rel)) - 13.5 * 110) < 0.5 and max(rel[:10]) < min(rel[10:])
          and min(gaps['wrap']) >= 109.5 and all(abs(g - 104) < 0.5 for g in gaps['even'])
          and min(gaps['fits']) >= 109.5 and all(abs(g - 104) < 0.5 for g in gaps['full'])
          and apart == [0, 500, 1000] and [round(s, 6) for s in pair] == [945, 1055],
          f'{ {k: (round(min(g), 2), round(max(g), 2)) for k, g in gaps.items()} } {apart} {pair}')
    at = pg.evaluate('''(src) => { eval(src + '; window.rimOn = rimOn; window.rimAt = rimAt;');
      const rim = {cx: 0, cy: 0, rx: 300, ry: 200};
      return [rim, window.rimOn(rim, 0, 0), window.rimAt(rim, window.rimOn(rim, 0, 0))]; }''',
                     js_function('rimAt') + js_function('rimOn'))
    check('S19 a ray of no length, callers averaging exactly to the centre, meets the rim in the '
          'middle of its right side',
          at[1:] == [2 * 300 + 2 * 200, {'x': 300, 'y': 0}], str(at))
    pg.close()


EDGE_CARDS = dict(SMALL_CARDS, **{'src/a.py/Cls/run': 'Runs the loop. ' * 30,
                                  'tests/t.py/test_b': 'Checks b.', 'tools/x.py/a<b>':
                                  'Compares. ' * 12})
# the windows and how many times to zoom out after a fit: at 480 by 360 the tips sit by the
# window's edges and in its middle, and zoomed out at 1400 by 900 they leave room outside them
EDGE = [((480, 360), 0), ((1400, 900), 2)]

JS_TIP = '''sel => { const e = [...document.querySelectorAll(sel)].find(e =>
  e.getBoundingClientRect().width); const r = e.getBoundingClientRect();
  return [r.left, r.top, r.right, r.bottom, e.closest('svg').id === 'mmL']; }'''


def card_at(win, box, h: float) -> tuple[str, float, float]:
    '''which rule places a card h tall for a tip with this box in a window win, and where: at
    the tip's outer end ('out') when it fits 12 px inside the window, else across the tip
    ('across') when that fits, else the outer end held 12 px inside ('held'); vertically centred
    on the tip and held 12 px inside.'''
    (w, wh), left = win, box[4]
    out, back = (box[0] - 376, box[2] + 16) if left else (box[2] + 16, box[0] - 376)
    rule, x = next(((r, x) for r, x in (('out', out), ('across', back)) if 12 <= x <= w - 372),
                   ('held', max(12, min(out, w - 372))))
    return rule, x, max(12, min((box[1] + box[3]) / 2 - h / 2, wh - 12 - h))


def edge_cases(browser, tmp: Path) -> None:
    '''B22 and B23: hover cards by the window's edges, in both layouts.'''
    out = tmp / 'edge.html'
    run(write_json(tmp / 'edge.json', document(SMALL, SMALL_LINKS)), '--cards',
        write_json(tmp / 'edge.cards.json', EDGE_CARDS), '-o', out)
    ctx, pg = open_page(browser, out)
    for id in ('src', 'tests', 'docs', 'tools'):
        click(pg, id, 'all')
    seen = []
    for win, zoom_out in EDGE:
        pg.set_viewport_size({'width': win[0], 'height': win[1]})
        for _ in ('one-sided', 'two-sided'):
            pg.click('#bLayout')
            pg.wait_for_timeout(SETTLE)
            pg.click('#bFit')
            pg.wait_for_timeout(SETTLE)
            for _ in range(zoom_out):
                pg.click('#bOut')
                pg.wait_for_timeout(SETTLE)
            for id in EDGE_CARDS:
                pg.mouse.move(win[0] / 2, 2)
                pg.wait_for_timeout(150)
                pg.hover(node_sel(id) + ' foreignObject', force=True)
                pg.wait_for_timeout(300)
                seen.append((win, pg.evaluate('document.getElementById("mmL").style.display'),
                             id, pg.evaluate(JS_TIP, node_sel(id)), pg.evaluate(JS_BOX, '#hc')))
    ctx.close()
    whole = len(seen) == 4 * len(EDGE_CARDS) and {s[1] for s in seen} == {'', 'none'}
    outside = [(w, lay, id, [round(v) for v in c]) for w, lay, id, _, c in seen
               if c[0] < 0 or c[1] < 0 or c[2] > w[0] or c[3] > w[1]]
    check('B22 every card, by the left, right, top and bottom edges of a 480 by 360 window and '
          'in its middle, and in a zoomed-out 1400 by 900 one, two-sided and one-sided, sits '
          'wholly inside the window',
          whole and not outside, f'{len(seen)} {outside}')
    placed = [(w, lay, id, *card_at(w, b, c[3] - c[1]), c[0], c[1])
              for w, lay, id, b, c in seen]
    wrong = [p for p in placed if abs(p[4] - p[6]) > 0.5 or abs(p[5] - p[7]) > 0.5]
    check('B23 each card opens at its tip\'s outer end, 16 px off, when it fits 12 px inside the '
          'window, else across the tip when that fits, else held 12 px inside; vertically it is '
          'centred on the tip and held 12 px inside; and some card falls under each rule',
          whole and not wrong and {p[3] for p in placed} == {'out', 'across', 'held'},
          f'{wrong} {sorted({p[3] for p in placed})}')

# the branches to open one level at a time, parents first, so no case needs Cmd or Ctrl
OPEN_ALL = ['src', 'src/a.py', 'src/a.py/Cls', 'src/b.js', 'tests', 'tests/t.py', 'docs',
            'docs/d.py', 'tools', 'tools/x.py']
FIT_WINDOWS = [(480, 360), (800, 500), (1400, 900)]
# each shown box whose centre is not its own topmost element: [id, centre y, what is on top]; the
# left tree's centre is skipped, as split() hides its name and the right centre sits over it
JS_HIDDEN = '''() => [...document.querySelectorAll('#mmR g.markmap-node, #mmL g.markmap-node')]
  .filter(g => !(g.dataset.id === '.' && g.closest('svg').id === 'mmL'))
  .map(g => [g, g.querySelector(':scope > foreignObject')]).filter(([g, fo]) => fo
  && fo.getBoundingClientRect().width && g.closest('svg').style.display !== 'none')
  .map(([g, fo]) => { const r = fo.getBoundingClientRect(), x = (r.left + r.right) / 2,
    y = (r.top + r.bottom) / 2, e = document.elementFromPoint(x, y);
    return [g.dataset.id, Math.round(y), e && e.closest('g.markmap-node') === g ? null
      : e ? (e.closest('#bar, #crumbs') || e).id || e.tagName : 'outside']; })
  .filter(r => r[2])'''


def fitted(browser, out: Path, opens: list, windows: list, js: str = '[]') -> list:
    '''Open each branch, then Fit at each window in both layouts: [window, mmL display, shown
    boxes, JS_HIDDEN, js] per fit.'''
    ctx, pg = open_page(browser, out)
    for id in opens:            # a fit first, so the next branch is on screen to click
        pg.click('#bFit')
        pg.wait_for_timeout(SETTLE)
        click(pg, id)
    seen = []
    for w, h in windows:
        pg.set_viewport_size({'width': w, 'height': h})
        for _ in ('one-sided', 'two-sided'):
            pg.click('#bLayout')
            pg.wait_for_timeout(SETTLE)
            pg.click('#bFit')
            pg.wait_for_timeout(SETTLE)
            seen.append(((w, h), pg.evaluate('document.getElementById("mmL").style.display'),
                         pg.evaluate(f'({JS_VISIBLE})().length'), pg.evaluate(JS_HIDDEN),
                         pg.evaluate(js)))
    ctx.close()
    return seen


# each shown box whose top is above the breadcrumb's bottom plus its 14 px gap: [id, top, limit]
JS_HIGH = '''() => { const c = document.getElementById('crumbs'), lim = c.hidden ? -1
  : c.getBoundingClientRect().bottom + 14;
  return [...document.querySelectorAll('#mmR g.markmap-node, #mmL g.markmap-node')]
  .filter(g => g.closest('svg').style.display !== 'none')
  .map(g => [g.dataset.id, g.querySelector(':scope > foreignObject')]).filter(([, fo]) => fo
  && fo.getBoundingClientRect().width).map(([id, fo]) => [id, fo.getBoundingClientRect().top, lim])
  .filter(r => r[1] < r[2] - 0.5); }'''


def fit_cases(browser, tmp: Path) -> None:
    '''B25 and B26: Fit leaves every box clear of the bars, in both layouts, on one map and four.'''
    out = tmp / 'fit.html'
    run(write_json(tmp / 'fit.json', document(SMALL, SMALL_LINKS)), '-o', out)
    seen = fitted(browser, out, OPEN_ALL, FIT_WINDOWS)
    whole = len(seen) == 6 and {s[1] for s in seen} == {'', 'none'} and \
        all(s[2] == len(SMALL_IDS) for s in seen)
    hidden = [(win, lay, bad) for win, lay, _, bad, _ in seen if bad]
    check('B25 after Fit with every branch open, at 480 by 360, 800 by 500 and 1400 by 900, '
          'one-sided and two-sided, each box is the topmost element at its centre, never under '
          'the bottom bar or the breadcrumb',
          whole and not hidden, f'{[s[:3] for s in seen]} {hidden}')

    out = tmp / 'fit-set.html'
    run(write_json(tmp / 'fit-set.json', document(SET, SET_LINKS)), '-o', out)
    seen = fitted(browser, out, [], FIT_WINDOWS[:2], JS_HIGH)    # its branches are all portals
    whole = len(seen) == 4 and {s[1] for s in seen} == {'', 'none'} and \
        all(s[2] == 4 for s in seen)
    bad = [(win, lay, hid, high) for win, lay, _, hid, high in seen if hid or high]
    check('B26 on the four-map page, after Fit with every branch open, at 480 by 360 and 800 by '
          '500, one-sided and two-sided, each box is the topmost element at its centre and its top '
          'is 14 px or more below the breadcrumb',
          whole and not bad, f'{[s[:3] for s in seen]} {bad}')


def main() -> int:
    page = load_page()
    split_cases(page)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        command_cases(tmp, page)
        vendored_cases(page)
        browser_cases(tmp)
    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
