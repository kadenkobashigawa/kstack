#!/usr/bin/env python3
'''
page.py writes one study map: a self-contained HTML page of a Document tree (tree.py's output),
its cards and its cross-links, drawn with the vendored markmap-view and d3. A big tree is split
into nested maps of at most CAP nodes, all in the one page. Nothing is fetched at view time.

Commands
--------
    page.py TREE.json [--cards CARDS.json] -o OUT.html [--artifact]
                         TREE.json is one Document as tree.py writes it, optionally with links.
                         CARDS.json is {node id: card text}. Lines split on '\\n', and **bold**
                         is kept.
                         -o is required, so a map is never written beside the repository's files
                         by default. --artifact writes the page with no doctype, html, head or
                         body tags, for a claude.ai artifact.
                         stderr lists the maps, the tips and how many have a card, the links, each
                         warning, and each map left over the cap. The exit code is 0 when the
                         page is written, even with tips that have no card (cards are written as
                         branches open). The exit code is 2, with `page:`, the file and the
                         reason on stderr, when an input or one of the skill's own files is
                         refused or OUT cannot be written. Nothing is written then.

Input
-----
    Document = {"schema": 1, "tree": Node, "links"?: [[from_id, to_id], ...]}
    Node     = {"id", "name", "kind", "file"?, "lines"?, "children": [Node]}
    tree.py also writes scope, commit, dirty, skipped and warnings. page.py does not read them.
    Refusals (exit 2), each with the file and the reason, come from these sites and nowhere else:
        read_text: a file that cannot be read or is not UTF-8. This covers TREE.json and
            CARDS.json (through load_json), and assets/page.html, assets/page.js and each
            vendored file (through render).
        load_json: a file that is not JSON.
        check_document: not an object; schema other than 1; schema or tree missing; a node that
            is not an object, missing id, name, kind or children, or of a kind tree.py does not
            write; a duplicate id.
        check_links: a link that is not a [str, str] pair, that names an id in no node, or that
            links a node to itself.
        check_cards: cards that are not {str: str}; a card on a pointer leaf, or on a node with a
            child that is no pointer leaf.
        write: OUT cannot be written.
    Cleaned: a link given twice is kept once. Warned (exit 0): a card whose id is in no node is
    dropped, not shown.
    A pointer leaf is a childless link source. It is a node with no children that is the source
    of a link, a mention of something whose home is elsewhere. A pointer leaf is never a tip and
    takes no card. A tip is any other node whose children, if it has any, are all pointer
    leaves. Only a tip carries a card.

Maps
----
    split_maps cuts the tree into maps of at most CAP nodes:
    - a tree of CAP nodes or fewer is one map.
    - a node fits when its subtree has CAP nodes or fewer, or when its own map would get no
      portal, so splitting it cannot make it smaller.
    - otherwise the map is its root and every layer down to the cut layer. Each node on the cut
      layer that has children is a portal. In this map it has no children, and its subtree is
      its own map, split by the same rule. Siblings are all treated alike.
    - the cut layer is the shallowest whole layer whose nodes all fit. When the map down to that
      layer would hold more than CAP nodes, the cut layer is instead the shallowest layer whose
      map fits, and its portals that do not fit are split by the same rule. A map only grows
      with depth, so that layer is the first one. When even the first layer's map is over the
      cap, the cut is at the first layer too, which gives the smallest map there is.
    - a portal is a node of kind root, dir or file, or a child of the map's own root (the class
      layer of a file whose map this is). When the layer holds any other node with children (in
      a class, or a class of a file that is not this map's root), the cut rises to that node's
      file. The file is the portal, and its own map cuts at its class layer. So a map whose root
      is a class, function or method is never split, and a file is cut only at its class layer.
    - a map left over the cap (one layer holds too many nodes, or one class does) is kept whole,
      and stderr names it and its size. No other map is over the cap.
    map_links places each link on every map that shows its source, as [from, end, home]. home
    is the link's target. end is the target when the map shows it. Otherwise end is the portal
    whose subtree holds the target, or else the map's root, the way up. A link that would end
    on its own source there is left out. page.js draws a link only while its source's own box
    is on screen, never from a folded source's open ancestor. A link whose home is on another
    map ends at a round portal for that home on the map's rim. Any other link ends at its end's
    box, or at the nearest open box above it. Two links that would join the same two places
    are drawn once.

Page
----
    render fills the slots of assets/page.html in one pass, so text put in one slot is never
    read as another slot. The page's data is one JSON object in a script of type
    application/json: MAPS {map id: tree}, UP {map id: [parent map id or null, label]}, LINKS
    {map id: [[from id, end id, home id], ...]} and TOP. Every <, >, & and line or paragraph
    separator in it is a \\u escape, so no id, label or card can end or reopen a script.
    page.js reads the data with JSON.parse, so an id such as __proto__ is an own key. Each tree
    node is {content, children, payload}, and payload is {id, c, card?, portal?}. Those are the
    Document id, the branch index within its map (-1 on the root), the card's HTML on a tip,
    and 1 on a portal. The logic is in assets/page.js.

Methods
-------
    Node :
        the Node keys page.py reads.
    Payload :
        what the page keeps on each markmap node.
    MMNode :
        one node in the shape markmap-view reads.
    Vendored :
        one vendored library: its name, version, licence, files and sha256.
    StudyMap :
        one map of the set: its id, parent map, tree, size and portals.
    Built :
        the page text and the counts report() prints.
    PageError :
        an input or output the page cannot be built from. The message names the file and reason.
    read_text :
        a file's text, or PageError naming it.
    load_json :
        a file's parsed JSON, or PageError naming it.
    check_document :
        the Document and its nodes by id, after every shape rule.
    check_links :
        the links as (from, to) pairs, each once, every end a known id.
    pointer_leaves :
        the ids of the pointer leaves.
    is_tip :
        whether a node is a tip: it is not a pointer leaf, and every child of it is one.
    check_cards :
        the kept cards by id and a warning per dropped one. It refuses a card on a node that is
        not a tip.
    walk :
        every node of a tree, parents before children.
    split_maps :
        the tree cut into maps of at most CAP nodes, top map first.
    map_links :
        the links each map draws, as [from, end, home], by map id.
    label :
        a node's label: its real name, with () on functions and methods.
    card_html :
        a card's text as escaped HTML paragraphs, **bold** kept.
    to_markmap :
        one map's tree in the shape markmap-view reads.
    script_text :
        a script file's text, made safe inside a script tag.
    json_text :
        a value as JSON that is safe inside a script tag.
    render :
        the whole page from the checked Document, its cards and links.
    artifact_form :
        the page without document tags, for an artifact.
    write :
        the page written in one atomic step.
    report :
        the stderr summary.
    main :
        parse the arguments, build, write, report.
'''

from __future__ import annotations

import argparse
import html
import json
import os
import re
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict

STUDY    = Path(__file__).resolve().parent.parent
ASSETS   = STUDY / 'assets'
VENDOR   = STUDY / 'vendor'
SCHEMA   = 1
CAP      = 500
KINDS    = ('root', 'dir', 'file', 'class', 'function', 'method')
CODE     = ('class', 'function', 'method')     # kinds inside a file
CALLED   = ('function', 'method')              # kinds whose label gains ()
REQUIRED = ('schema', 'tree')                 # the Document keys page.py reads; links is optional
ESCAPE   = {ord(c): f'\\u{ord(c):04x}' for c in '<>&\u2028\u2029'}


# ── the data shape ────────────────────────────────────────────────────────────

# the Document and Node shapes are tree.py's (its module docstring). page.py restates only the
# keys it reads, because importing tree.py loads tree-sitter, which page.py must not need.

Kind = Literal['root', 'dir', 'file', 'class', 'function', 'method']


class Node(TypedDict):
    '''the Node keys page.py reads; check_document requires each of them.'''
    id: str
    name: str
    kind: Kind
    children: list[Node]


class Payload(TypedDict, total=False):
    '''what the page keeps on each markmap node. fold is markmap's own, and page.py never sets
    it.'''
    id: str
    c: int
    card: str
    portal: int


class MMNode(TypedDict):
    '''one node in the shape markmap-view's setData reads.'''
    content: str
    children: list[MMNode]
    payload: Payload


@dataclass(frozen=True)
class Vendored:
    '''one vendored library, as npm published it. VENDORED is the only list of them, and the
    tests read it.'''
    name: str
    version: str
    licence: str        # its SPDX id
    path: str           # the file the page inlines, relative to VENDOR
    licence_file: str   # relative to VENDOR
    sha256: str         # of the npm release's file


VENDORED: tuple[Vendored, ...] = (
    Vendored('d3', '7.9.0', 'ISC', 'd3/d3.min.js', 'd3/LICENSE',
             'f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539'),
    Vendored('markmap-view', '0.18.12', 'MIT', 'markmap-view/markmap-view.js',
             'markmap-view/LICENSE',
             '861eb6d20af18aaa300878d46d695722a73625c58b40f49236af027f18b74e07'),
)


@dataclass(frozen=True)
class StudyMap:
    '''one map of the set. Its id is its root's node id, and the top map's parent is None.'''
    id: str
    parent: str | None
    tree: Node                  # the map's own nodes, where a portal keeps its keys, no children
    size: int
    portals: tuple[str, ...]    # in tree order


@dataclass(frozen=True)
class Built:
    '''the page text and the counts report() prints.'''
    page: str
    maps: list[StudyMap]
    tips: int
    carded: int
    links: int


class PageError(Exception):
    '''an input or output the page cannot be built from. The message names the file and reason.'''


# ── the boundary: everything is checked here, and trusted after ──────────────

def read_text(path: Path) -> str:
    '''a file's text. Raises PageError naming the file when it cannot be read or is not UTF-8.'''
    try:
        return path.read_text(encoding='utf-8')
    except OSError as e:
        raise PageError(f'{path}: cannot be read: {e.strerror}') from e
    except UnicodeDecodeError as e:
        raise PageError(f'{path}: not UTF-8') from e


def load_json(path: Path) -> Any:
    '''the parsed JSON of a file. Raises PageError naming the file when it cannot be read or
    parsed.'''
    text = read_text(path)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise PageError(f'{path}: not JSON: {e.msg} at line {e.lineno}') from e


def check_document(raw: Any, path: Path) -> tuple[dict, dict[str, Node]]:
    '''
    the Document and every node by id, once every shape rule holds.

    Parameters
    ----------
    raw : Any
        the parsed JSON.
    path : Path
        the file it came from, for the message.

    Returns
    -------
    tuple[dict, dict[str, Node]]
        the Document as given, and its nodes by id.

    Raises
    ------
    PageError
        naming the file, the rule and the first offending id: not an object, schema other than
        the int 1, schema or tree missing, a node not an object or missing id, name, kind or
        children, a kind not in KINDS, or an id given twice. The check is one walk with a stack, so
        a deep tree does not reach the recursion limit.
    '''
    if not isinstance(raw, dict):
        raise PageError(f'{path}: not a Document: the top level is not an object')
    schema = raw.get('schema')
    if type(schema) is not int or schema != SCHEMA:
        raise PageError(f'{path}: schema is {schema!r}, and page.py reads schema {SCHEMA}')
    for key in REQUIRED:
        if key not in raw:
            raise PageError(f'{path}: the Document has no {key!r}')
    by_id: dict[str, Node] = {}
    stack = [(raw['tree'], 'the tree')]
    while stack:
        n, where = stack.pop()
        if not isinstance(n, dict):
            raise PageError(f'{path}: a node under {where} is not an object')
        if not isinstance(n.get('id'), str):
            raise PageError(f'{path}: a node under {where} has no id')
        nid = n['id']
        for key, kind in (('name', str), ('kind', str), ('children', list)):
            if not isinstance(n.get(key), kind):
                raise PageError(f'{path}: node {nid!r} has no {key}')
        if n['kind'] not in KINDS:
            raise PageError(f"{path}: node {nid!r} has kind {n['kind']!r}, not one of "
                            f"{', '.join(KINDS)}")
        if nid in by_id:
            raise PageError(f'{path}: id {nid!r} appears twice')
        by_id[nid] = n
        stack.extend((c, repr(nid)) for c in reversed(n['children']))
    return raw, by_id


def check_links(raw: Any, by_id: dict[str, Node], path: Path) -> list[tuple[str, str]]:
    '''
    the Document's links as (from, to) pairs in order, each pair once, or [] when links is absent.
    Raises PageError when links is not a list of [str, str] pairs, when an end names no node,
    or when a link goes from a node to itself. The message names the link's index.
    '''
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise PageError(f'{path}: links is not a list')
    kept: dict[tuple[str, str], None] = {}
    for i, link in enumerate(raw):
        if not (isinstance(link, list) and len(link) == 2
                and all(isinstance(e, str) for e in link)):
            raise PageError(f'{path}: links[{i}] is not a [from id, to id] pair')
        for end in link:
            if end not in by_id:
                raise PageError(f'{path}: links[{i}] names {end!r}, which is no node')
        if link[0] == link[1]:
            raise PageError(f'{path}: links[{i}] links {link[0]!r} to itself')
        kept[(link[0], link[1])] = None
    return list(kept)


def pointer_leaves(by_id: dict[str, Node], links: list[tuple[str, str]]) -> set[str]:
    '''the ids of the nodes that are the source of a link and have no children.'''
    return {src for src, _ in links if not by_id[src]['children']}


def is_tip(node: Node, pointers: set[str]) -> bool:
    '''whether node is a tip: it is not a pointer leaf, and each of its children, if it has any,
    is one.'''
    return node['id'] not in pointers and all(c['id'] in pointers for c in node['children'])


def check_cards(raw: Any, by_id: dict[str, Node], links: list[tuple[str, str]],
                path: Path) -> tuple[dict[str, str], list[str]]:
    '''
    the cards kept, by id, and one warning per card whose id names no node. Such a card is
    dropped. Raises PageError when cards is not {str: str}, or when a card sits on a node that
    is not a tip, meaning a pointer leaf or a node with a child that is no pointer leaf.
    '''
    if not (isinstance(raw, dict) and all(isinstance(v, str) for v in raw.values())):
        raise PageError(f'{path}: cards is not an object of node id to text')
    kept, warnings = {}, []
    pointers = pointer_leaves(by_id, links)
    for nid, text in raw.items():
        if nid not in by_id:
            warnings.append(f'{path}: the card for {nid!r} names no node, so it is not shown')
        elif nid in pointers:
            raise PageError(f'{path}: the card for {nid!r} sits on a pointer leaf, which takes no '
                            'card; only tips carry cards')
        elif not is_tip(by_id[nid], pointers):
            raise PageError(f'{path}: the card for {nid!r} sits on a node with a child that is no '
                            'pointer leaf; only tips carry cards')
        else:
            kept[nid] = text
    return kept, warnings


# ── maps ──────────────────────────────────────────────────────────────────────

def walk(tree: Node) -> list[Node]:
    '''every node of a tree, each parent before its children, children in order.'''
    out, stack = [], [tree]
    while stack:
        n = stack.pop()
        out.append(n)
        stack.extend(reversed(n['children']))
    return out


def split_maps(tree: Node, cap: int = CAP) -> list[StudyMap]:
    '''
    the tree cut into maps by the rule in the module docstring (Maps), top map first, then each
    portal's maps depth first in tree order.

    Notes
    -----
    Sizes and parents are counted once. Whether a node fits needs its own cut, so cuts are
    cached by id. Only nodes over the cap get a cut, and a cut reads the layers below its node,
    so the work is the size of each oversized subtree, summed.
    '''
    nodes  = walk(tree)
    parent = {c['id']: n for n in nodes for c in n['children']}
    size   = {}
    for n in reversed(nodes):
        size[n['id']] = 1 + sum(size[c['id']] for c in n['children'])
    cuts: dict[str, list[Node]] = {}

    def fits(n: Node) -> bool:
        return size[n['id']] <= cap or not cut(n)

    def cut(m: Node) -> list[Node]:
        '''the portals of m's own map, or [] when it is one whole map.'''
        if m['id'] in cuts:
            return cuts[m['id']]
        cuts[m['id']] = []
        if size[m['id']] <= cap or m['kind'] in CODE:
            return []
        layers = [[m]]
        while layers[-1]:
            layers.append([c for n in layers[-1] for c in n['children']])
        depth = {n['id']: d for d, layer in enumerate(layers) for n in layer}
        d = next(d for d in range(1, len(layers)) if all(fits(n) for n in layers[d]))
        while True:
            inside = [n for n in layers[d] if n['children'] and n['kind'] in CODE
                      and parent[n['id']] is not m]
            if not inside:
                break
            files = []
            for n in inside:
                while n['kind'] in CODE:
                    n = parent[n['id']]
                files.append(max(depth[n['id']], 1))
            d = min(files)

        # when the map down to layer d is over the cap, cut at the first layer, the smallest map
        if sum(len(layer) for layer in layers[:d + 1]) > cap:
            d = 1
        cuts[m['id']] = [n for n in layers[d] if n['children']]
        return cuts[m['id']]

    def own(m: Node, portals: set[str]) -> tuple[Node, int]:
        '''m's map: a copy of its nodes down to its portals, which keep no children.'''
        top, count = dict(m, children=[]), 1
        stack = [(m, top)]
        while stack:
            src, dst = stack.pop()
            if src is not m and src['id'] in portals:
                continue
            for c in src['children']:
                cc = dict(c, children=[])
                dst['children'].append(cc)
                stack.append((c, cc))
                count += 1
        return top, count

    out, todo = [], [(tree, None)]
    while todo:
        m, up = todo.pop()
        portals = cut(m)
        ids     = tuple(p['id'] for p in portals)
        view, count = own(m, set(ids))
        out.append(StudyMap(m['id'], up, view, count, ids))
        todo.extend((p, m['id']) for p in reversed(portals))
    return out


def map_links(maps: list[StudyMap], tree: Node,
              links: list[tuple[str, str]]) -> dict[str, list[list[str]]]:
    '''
    the links each map draws, as [from id, end id, home id] by map id, by the rule in the module
    docstring (Maps). tree is the whole Document tree, which holds each portal's subtree.
    '''
    by_id = {n['id']: n for n in walk(tree)}
    out   = {}
    for m in maps:
        here   = {n['id'] for n in walk(m.tree)}
        holder = {n['id']: p for p in m.portals for n in walk(by_id[p])}
        drawn  = []
        for src, dst in links:
            if src not in here:
                continue
            end = dst if dst in here else holder.get(dst, m.id)
            if end != src:
                drawn.append([src, end, dst])
        out[m.id] = drawn
    return out


# ── the page ──────────────────────────────────────────────────────────────────

def label(node: Node) -> str:
    '''a node's label: its real name exactly as written, plus () on functions and methods.'''
    return node['name'] + ('()' if node['kind'] in CALLED else '')


def card_html(text: str) -> str:
    '''a card's text as a <p> per non-empty line, each line escaped, then **x** made <b>x</b>.'''
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return ''.join('<p>' + re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html.escape(line, quote=False))
                   + '</p>' for line in lines)


def to_markmap(m: StudyMap, cards: dict[str, str], pointers: set[str]) -> MMNode:
    '''
    one map's tree for markmap-view. Each node holds its escaped label in a box span, with a
    class set by depth (sm-root, sm-branch, then sm-node), sm-portal added on a portal, and the
    payload. sm-leaf marks each node below the branch layer that is no portal and is a tip by
    is_tip, where pointers holds the ids of the pointer leaves. A tip directly under the root
    keeps the plain branch box, so every branch of the centre looks alike.
    '''
    portals = set(m.portals)

    def mm(n: Node, depth: int, c: int) -> MMNode:
        payload: Payload = {'id': n['id'], 'c': c}
        if n['id'] in cards:
            payload['card'] = card_html(cards[n['id']])
        boxes = ['sm-root'] if depth == 0 else ['sm-branch'] if depth == 1 else ['sm-node']
        if n['id'] in portals:
            payload['portal'] = 1
            boxes.append('sm-portal')
        elif depth > 1 and is_tip(n, pointers):
            boxes.append('sm-leaf')
        return {'content': f'<span class="{" ".join(boxes)}">{html.escape(label(n))}</span>',
                'children': [], 'payload': payload}

    top   = mm(m.tree, 0, -1)
    stack = [(m.tree, top, 0, -1)]
    while stack:
        src, dst, depth, c = stack.pop()
        for i, child in enumerate(src['children']):
            branch = i if depth == 0 else c
            cc = mm(child, depth + 1, branch)
            dst['children'].append(cc)
            stack.append((child, cc, depth + 1, branch))
    return top


def script_text(path: Path) -> str:
    '''a script file's text with every </script made <\\/script, so it cannot end its tag.'''
    return read_text(path).replace('</script', '<\\/script')


def json_text(value: Any) -> str:
    '''value as JSON with every <, >, &, U+2028 and U+2029 written as a \\u escape, so it is safe
    in any script.'''
    return json.dumps(value, ensure_ascii=False).translate(ESCAPE)


def render(doc: dict, cards: dict[str, str], links: list[tuple[str, str]]) -> Built:
    '''
    the page: assets/page.html with its slots filled in one pass. The slots take the title, each
    vendored library by its name, the page's data (MAPS, UP, LINKS, TOP as one JSON object) and
    assets/page.js. Raises PageError when the template, page.js or a vendored file cannot be read.
    '''
    maps  = split_maps(doc['tree'])
    nodes = {n['id']: n for n in walk(doc['tree'])}
    ptrs  = pointer_leaves(nodes, links)
    names = {nid: label(n) for nid, n in nodes.items()}
    data  = {'MAPS': {m.id: to_markmap(m, cards, ptrs) for m in maps},
             'UP': {m.id: [m.parent, names[m.id]] for m in maps},
             'LINKS': map_links(maps, doc['tree'], links), 'TOP': maps[0].id}
    lib   = {v.name: VENDOR / v.path for v in VENDORED}
    fill  = {'__TITLE__': html.escape(names[maps[0].id]),
             '/*__D3__*/': script_text(lib['d3']),
             '/*__MARKMAP__*/': script_text(lib['markmap-view']),
             '/*__DATA__*/': json_text(data),
             '/*__PAGE__*/': script_text(ASSETS / 'page.js')}
    page  = re.sub('|'.join(map(re.escape, fill)), lambda s: fill[s[0]],
                   read_text(ASSETS / 'page.html'))
    tips  = [n for n in nodes.values() if is_tip(n, ptrs)]
    return Built(page, maps, len(tips), sum(n['id'] in cards for n in tips),
                 sum(len(v) for v in data['LINKS'].values()))


def artifact_form(page: str) -> str:
    '''the page without doctype, html, head and body tags and the charset and viewport metas.'''
    page = re.sub(r'(?im)^\s*(<!doctype html>|<html>|</html>|<head>|</head>|<body>|</body>)\s*$\n?',
                  '', page)
    return re.sub(r'(?i)<meta charset="UTF-8">\s*<meta name="viewport"[^>]*>\s*', '', page)


def write(out: Path, text: str) -> None:
    '''
    the page written to a temp file beside out and moved over it, so a reader sees the old page
    or the new one. The temp file is removed on failure. Raises PageError when it cannot be
    written.
    '''
    tmp = out.parent / f'.{out.name}.{secrets.token_hex(4)}.tmp'
    try:
        with open(tmp, 'x', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, out)
    except OSError as e:
        raise PageError(f'{out}: {e.strerror}') from e
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def report(built: Built, out: Path, warnings: list[str]) -> None:
    '''the summary on stderr: the path, the maps, the tips with and without a card, the links,
    each warning, and each map over the cap.'''
    big = max(built.maps, key=lambda m: m.size)
    say = lambda s: print(f'page: {s}', file=sys.stderr)
    say(f'wrote {out}')
    say(f"{len(built.maps)} map{'s' * (len(built.maps) != 1)}, the largest {big.id!r} of "
        f'{big.size} nodes')
    say(f'{built.tips} tips, {built.carded} with a card, {built.tips - built.carded} without')
    say(f"{built.links} links on {len(built.maps)} map{'s' * (len(built.maps) != 1)}")
    for w in warnings:
        say(f'warning: {w}')
    for m in built.maps:
        if m.size > CAP:
            say(f'note: map {m.id!r} has {m.size} nodes, over the {CAP} cap')


def main(argv: list[str]) -> int:
    '''parse the arguments, check every input, build and write the page, and report on stderr.
    Return 2 with `page:` and the reason on any refused input or unwritable OUT, before anything
    is written.'''
    ap = argparse.ArgumentParser(prog='page.py', description='a study map page from a tree.py '
                                 'Document, its cards and its links')
    ap.add_argument('tree', type=Path, help='the Document JSON')
    ap.add_argument('--cards', type=Path, default=None, help='{node id: card text}')
    ap.add_argument('-o', '--out', type=Path, required=True, help='the HTML file to write')
    ap.add_argument('--artifact', action='store_true', help='no doctype, html, head or body tags')
    args = ap.parse_args(argv)
    try:
        doc, by_id     = check_document(load_json(args.tree), args.tree)
        links          = check_links(doc.get('links'), by_id, args.tree)
        cards, dropped = (check_cards(load_json(args.cards), by_id, links, args.cards)
                          if args.cards else ({}, []))
        built          = render(doc, cards, links)
        write(args.out, artifact_form(built.page) if args.artifact else built.page)
    except PageError as e:
        print(f'page: {e}', file=sys.stderr)
        return 2
    report(built, args.out, dropped)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
