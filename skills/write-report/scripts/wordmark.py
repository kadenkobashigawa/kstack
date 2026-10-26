#!/usr/bin/env python3
'''
wordmark — flatten a logo svg into one path a printer renders without seams, keeping its holes.

    python3 wordmark.py SOURCE.svg OUT.svg

a renderer anti-aliases each abutting shape alone, so every shared edge prints a hairline. it
bakes the transforms into one path and winds each outline one way and each hole the other, so a
nonzero fill closes the seams and the inside of an O stays empty. the output fills with
currentColor, so the report's title page shows it black and the screen's dark panel white.

Methods
-------
    subpaths :
        split svg path data into closed subpaths of line and cubic segments.
    depth :
        how many other subpaths contain a subpath; even is an outline, odd is a hole.
    flatten :
        every subpath of an svg, transforms applied, wound by depth, as one path's data.
    main :
        write OUT.svg with fill currentColor and a viewBox fitted to the outline.
'''

from __future__ import annotations

import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path



NS       = '{http://www.w3.org/2000/svg}'
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
SKIP     = {'title', 'desc', 'metadata', 'defs'}
ARGS     = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'S': 4, 'Q': 4, 'T': 2, 'Z': 0}


# ── transforms ───────────────────────────────────────────────────────────────

def _compose(outer: tuple, inner: tuple) -> tuple:
    '''the transform that applies inner, then outer, as svg nesting does.'''
    a, b, c, d, e, f = outer
    A, B, C, D, E, F = inner
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D,
            a * E + c * F + e, b * E + d * F + f)


def _transform(text: str | None) -> tuple:
    '''an svg transform list (matrix, translate, scale, rotate) as one matrix.'''
    m = IDENTITY
    for name, args in re.findall(r'(\w+)\s*\(([^)]*)\)', text or ''):
        v = [float(x) for x in re.split(r'[\s,]+', args.strip()) if x]
        if name == 'matrix' and len(v) == 6:
            step = tuple(v)
        elif name == 'translate':
            step = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == 'scale':
            step = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == 'rotate':
            r = math.radians(v[0])
            cx, cy = (v[1], v[2]) if len(v) == 3 else (0, 0)
            step = _compose(_compose((1, 0, 0, 1, cx, cy),
                                     (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)),
                            (1, 0, 0, 1, -cx, -cy))
        else:
            raise ValueError(f'unsupported transform {name}({args}); apply it in the editor first')
        m = _compose(m, step)
    return m


def _apply(m: tuple, pt: tuple) -> tuple:
    '''the point pt under the transform m.'''
    a, b, c, d, e, f = m
    return (a * pt[0] + c * pt[1] + e, b * pt[0] + d * pt[1] + f)


# ── path data ────────────────────────────────────────────────────────────────

def subpaths(d: str) -> list[dict]:
    '''
    split svg path data into closed subpaths.

    Parameters
    ----------
    d : str
        a path's d attribute: M, L, H, V, C, S, Q, T and Z, absolute or relative.

    Returns
    -------
    list of dict
        one {'start': (x, y), 'segs': [(kind, points)]} per subpath, kind 'L' with one point or
        'C' with three; H and V become lines, S, Q and T become cubics. a fill closes every
        subpath, so one left open is closed here too.

    Notes
    -----
    raises ValueError on an arc (A), naming it: convert arcs to curves in the editor first.
    '''
    tokens = re.findall(r'[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', d)
    bad = [t for t in tokens if t.isalpha() and t.upper() not in ARGS]
    if bad:
        raise ValueError(f'unsupported path command {bad[0]!r}; convert arcs to curves first')
    out, cur, pos, start, cmd, i = [], None, (0.0, 0.0), (0.0, 0.0), None, 0
    last_c = last_q = None
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd, i = tokens[i], i + 1
            if cmd in 'Zz':
                if cur:
                    out.append(cur)
                cur, pos, last_c, last_q = None, start, None, None
                continue
        if cmd is None or cmd in 'Zz':
            raise ValueError('path data has numbers with no command before them')
        n = ARGS[cmd.upper()]
        v = [float(t) for t in tokens[i:i + n]]
        i += n
        rel = cmd.islower()
        up = cmd.upper()

        def at(x, y):
            return (pos[0] + x, pos[1] + y) if rel else (x, y)

        if up == 'M':
            if cur:
                out.append(cur)
            pos = start = at(*v)
            cur = {'start': pos, 'segs': []}
            cmd = 'l' if rel else 'L'
            last_c = last_q = None
            continue
        if cur is None:
            cur = {'start': pos, 'segs': []}
            start = pos
        if up in 'LHV':
            if up == 'H':
                end = (pos[0] + v[0], pos[1]) if rel else (v[0], pos[1])
            elif up == 'V':
                end = (pos[0], pos[1] + v[0]) if rel else (pos[0], v[0])
            else:
                end = at(*v)
            cur['segs'].append(('L', [end]))
            last_c = last_q = None
        elif up in 'CS':
            if up == 'C':
                c1, c2, end = at(v[0], v[1]), at(v[2], v[3]), at(v[4], v[5])
            else:
                c1 = (2 * pos[0] - last_c[0], 2 * pos[1] - last_c[1]) if last_c else pos
                c2, end = at(v[0], v[1]), at(v[2], v[3])
            cur['segs'].append(('C', [c1, c2, end]))
            last_c, last_q = c2, None
        else:
            if up == 'Q':
                q, end = at(v[0], v[1]), at(v[2], v[3])
            else:
                q = (2 * pos[0] - last_q[0], 2 * pos[1] - last_q[1]) if last_q else pos
                end = at(v[0], v[1])

            #a quadratic is the cubic whose controls sit two thirds of the way to its one control...
            c1 = (pos[0] + 2 / 3 * (q[0] - pos[0]), pos[1] + 2 / 3 * (q[1] - pos[1]))
            c2 = (end[0] + 2 / 3 * (q[0] - end[0]), end[1] + 2 / 3 * (q[1] - end[1]))
            cur['segs'].append(('C', [c1, c2, end]))
            last_c, last_q = None, q
        pos = end
    if cur:
        out.append(cur)
    return out


def _polygon(sp: dict, steps: int = 12) -> list[tuple]:
    '''the subpath as points along its outline, each cubic sampled at steps points.'''
    pts, pos = [sp['start']], sp['start']
    for kind, seg in sp['segs']:
        if kind == 'L':
            pts.append(seg[0])
        else:
            (x1, y1), (x2, y2), (x3, y3) = seg
            for k in range(1, steps + 1):
                t = k / steps
                u = 1 - t
                w = (u ** 3, 3 * u * u * t, 3 * u * t * t, t ** 3)
                pts.append((w[0] * pos[0] + w[1] * x1 + w[2] * x2 + w[3] * x3,
                            w[0] * pos[1] + w[1] * y1 + w[2] * y2 + w[3] * y3))
        pos = seg[-1]
    return pts


def _area(poly: list[tuple]) -> float:
    '''signed area; positive runs clockwise on screen, where y points down.'''
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1])) / 2


def _inside(pt: tuple, poly: list[tuple]) -> bool:
    '''whether pt is inside poly by the even-odd rule (a ray cast to the right).'''
    x, y, hit = pt[0], pt[1], False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def depth(sub: list[tuple], others: list[list[tuple]]) -> int:
    '''
    how many of the other outlines contain this one.

    Notes
    -----
    one outline contains another when most of the other's sampled points fall inside it. a
    majority, not one point, because an abutting neighbour shares edge points with this one,
    and a point on a shared edge can land either way. *(kstack: the source wound every subpath
    one way, which closed the seams and filled every counter.)*
    '''
    return sum(1 for o in others if sum(_inside(p, o) for p in sub) * 2 > len(sub))


def _reverse(sp: dict) -> dict:
    '''the same outline walked the other way; a curve swaps its two control points.'''
    nodes = [sp['start']] + [seg[-1] for _, seg in sp['segs']]
    segs = []
    for k in range(len(sp['segs']) - 1, -1, -1):
        kind, seg = sp['segs'][k]
        segs.append(('L', [nodes[k]]) if kind == 'L' else ('C', [seg[1], seg[0], nodes[k]]))
    return {'start': nodes[-1], 'segs': segs}


def _paint(el: ET.Element, inherited: dict) -> dict:
    '''el's stroke and fill: its style beats its attributes, which beat its parents'.'''
    paint = dict(inherited)
    for key in ('stroke', 'fill'):
        if el.get(key):
            paint[key] = el.get(key).strip()
        m = re.search(rf'(?:^|;)\s*{key}\s*:\s*([^;]+)', el.get('style', ''))
        if m:
            paint[key] = m[1].strip()
    return paint


def _walk(el: ET.Element, m: tuple, paint: dict, found: list) -> None:
    '''collect every path's subpaths under el, transforms and paint inherited; refuse the rest.'''
    if not el.tag.startswith(NS):
        return
    tag = el.tag[len(NS):]
    if tag in SKIP:
        return
    if tag not in ('svg', 'g', 'path'):
        raise ValueError(f'unsupported element <{tag}>; convert shapes and text to paths first')
    m = _compose(m, _transform(el.get('transform')))
    paint = _paint(el, paint)
    if tag == 'path':
        if paint.get('stroke', 'none') != 'none':
            raise ValueError('a <path> has a stroke, set on it or on a group above it; outline '
                             'strokes to fills first')
        if paint.get('fill') == 'none':
            return
        for sp in subpaths(el.get('d', '')):
            found.append({'start': _apply(m, sp['start']),
                          'segs': [(k, [_apply(m, p) for p in seg]) for k, seg in sp['segs']]})
    for child in el:
        _walk(child, m, paint, found)


def flatten(svg: Path) -> tuple[str, float, float]:
    '''
    every subpath of an svg as one path's data.

    Parameters
    ----------
    svg : Path
        the logo to read.

    Returns
    -------
    tuple
        (d, width, height): the path data shifted so its bounds start at 0,0, and its size.

    Notes
    -----
    an outline at even depth winds clockwise and a hole at odd depth counterclockwise, so the
    nonzero rule fills abutting outlines as one and leaves counters empty. a path takes the
    stroke and fill of the groups above it. raises ValueError on an element other than a path or
    group, a stroke, an arc or a skew, naming it, and on an svg with no filled path. a <style>
    element or a class attribute is refused too, because css can paint a path by class and this
    reads no css.
    '''
    root = ET.parse(svg).getroot()
    for el in root.iter():
        if el.tag == NS + 'style':
            raise ValueError('a <style> element can paint paths by class, and this reads no css; '
                             'export the logo with presentation attributes instead')
        if el.get('class') is not None:
            raise ValueError(f'<{el.tag[len(NS):]}> has a class attribute, which css can paint, '
                             'and this reads no css; export with presentation attributes instead')
    found = []
    _walk(root, IDENTITY, {}, found)
    if not found:
        raise ValueError(f'{svg} has no filled path')
    polys = [_polygon(sp) for sp in found]
    wound = []
    for k, (sp, poly) in enumerate(zip(found, polys)):
        hole = depth(poly, polys[:k] + polys[k + 1:]) % 2 == 1
        wound.append(_reverse(sp) if (_area(poly) < 0) != hole else sp)
    xs = [x for p in polys for x, _ in p]
    ys = [y for p in polys for _, y in p]
    x0, y0 = min(xs), min(ys)

    def num(v):
        return f'{v:.2f}'.rstrip('0').rstrip('.')

    d = []
    for sp in wound:
        d.append(f'M{num(sp["start"][0] - x0)},{num(sp["start"][1] - y0)}')
        for kind, seg in sp['segs']:
            d.append(kind + ' '.join(f'{num(x - x0)},{num(y - y0)}' for x, y in seg))
        d.append('Z')
    return ''.join(d), max(xs) - x0, max(ys) - y0


def main(argv: list[str] | None = None) -> int:
    '''
    write OUT.svg from SOURCE.svg, and print its size.

    Parameters
    ----------
    argv : list of str, optional
        SOURCE.svg and OUT.svg; None reads sys.argv.

    Returns
    -------
    int
        0 on success, 1 with one line on stderr when the source cannot be read or holds something
        unsupported, and 2 with the usage when the arguments are not two paths.
    '''
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print('usage: wordmark.py SOURCE.svg OUT.svg', file=sys.stderr)
        return 2
    src, out = Path(argv[0]), Path(argv[1])
    try:
        d, w, h = flatten(src)
    except (ValueError, ET.ParseError, OSError) as e:
        print(f'wordmark.py: {src}: {e}', file=sys.stderr)
        return 1
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.2f} {h:.2f}">'
                   f'<path fill="currentColor" fill-rule="nonzero" d="{d}"/></svg>\n')
    print(f'{out.name}: {w:.0f} x {h:.0f}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
