"""
pen — the palette, and the shapes and strokes the pieces are drawn with.

Units are centimetres at true size. Every line is a pen stroke: a filled outline, full width
mid-stroke and thin where the pen lands and lifts, and a closed outline is one to three overlapping
strokes. DESIGN.md holds the palette.
"""

from __future__ import annotations

import math


C = {
    'line': '#6c4a3a', 'wall': '#3f322c',
    'oak50': '#f6e6c8', 'oak100': '#efd6a8', 'oak200': '#e3c08b', 'oak300': '#d0a46f',
    'oak500': '#a87b52',
    'wal300': '#a66f4b', 'wal500': '#7d5038', 'wal700': '#5a3a2b',
    'lin50': '#fcf7ee', 'lin200': '#efe4d2', 'lin400': '#dbcab0', 'lin600': '#b9a689',
    'black': '#3d3633',
    'chr50': '#f1f3f2', 'chr200': '#d3d8d8', 'chr400': '#a5adae', 'chr700': '#6d7577',
    'leaf200': '#bcd59c', 'leaf400': '#88b26f', 'leaf600': '#5f8d55', 'leaf800': '#41673f',
    'olive': '#a9b89b', 'olive600': '#7f9473',
    'hole': '#5c6a4a', 'marble': '#f3efe8', 'rubber400': '#6f9a5d', 'rubber600': '#4f7d47',
    'rubber800': '#3a6236', 'sheath': '#a8524a', 'sage50': '#e3e9d5', 'sage100': '#f1f4e9', 'sage300': '#b8c7a1',
    'cognac': '#dba25e', 'cognac600': '#b97d3e',
    'glass': '#d7e6e4', 'glow': '#ffe2a6', 'core': '#fff7e4',
    'rwhite': '#fdfdfb', 'rgrey': '#dfe1e1',
    'dwhite': '#fafaf7', 'dgrey': '#d4d6d5',
    'cat': '#f7ecdb', 'ginger': '#e9b57c',
    'paper': '#ece2d1',
}


PEN = {'marble-vein': 0.7, 'hob-ring': 0.8, 'spout': 1.8, 'gloss': 1.1, 'rod': 1.2, 'wire': 0.5, 'tassel': 0.8, 'glint': 0.9, 'petiole': 1.6, 'grain': 0.6, 'knot': 0.55, 'stripe': 1.2, 'whisker': 0.35, 'line': 1.45, 'detail': 0.9, 'rib': 0.8, 'vein': 0.55, 'edge': 0.8, 'vine': 0.85,
       'twig': 1.15, 'bristle': 1.0, 'fringe': 0.8, 'weave': 0.8, 'chrome-ring': 1.1, 'arm': 2.6}


def pen_width(cls: str) -> float | None:
    w = PEN.get(cls.split()[0])
    return w * 0.55 if w and 'thin' in cls.split() else w


# ── colour ────────────────────────────────────────────────────────────────


def mix(a: str, b: str, t: float) -> str:
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x + (y - x) * t):02x}' for x, y in zip(pa, pb))


def shade_of(c: str) -> str:
    return mix(c, '#2a201b', 0.22)


def light_of(c: str) -> str:
    return mix(c, '#fff8ec', 0.42)


# ── geometry ──────────────────────────────────────────────────────────────


def f(v: float) -> str:
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def smooth(pts: list[tuple[float, float]], closed: bool = True) -> str:
    """Catmull-Rom through the points, as cubic Bézier path data."""
    n = len(pts)
    d = f'M{f(pts[0][0])},{f(pts[0][1])}'
    for i in range(n if closed else n - 1):
        p0 = pts[(i - 1) % n] if closed else pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed else pts[min(i + 2, n - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f' C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}'
    return d + (' Z' if closed else '')


def sample(ctrl: list[tuple[float, float]], k: int = 5) -> list[tuple[float, float]]:
    """Dense points along an open Catmull-Rom curve through the control points."""
    n, out = len(ctrl), []
    for i in range(n - 1):
        p0, p1 = ctrl[max(i - 1, 0)], ctrl[i]
        p2, p3 = ctrl[i + 1], ctrl[min(i + 2, n - 1)]
        out.extend(cr(p0, p1, p2, p3, j / k) for j in range(k))
    return out + [ctrl[-1]]


def rrect_pts(x, y, w, h, r, rnd, wob=0.3, step=7.0):
    """Points round a rounded rectangle, each nudged off the edge: the hand line.

    r is one radius, or four (top-left, top-right, bottom-right, bottom-left)."""
    rs = r if isinstance(r, tuple) else (r, r, r, r)
    tl, tr, br, bl = (min(v, w / 2, h / 2) for v in rs)
    segs = [
        ('l', (x + tl, y), (x + w - tr, y), (0, -1)), ('a', (x + w - tr, y + tr), tr, -90),
        ('l', (x + w, y + tr), (x + w, y + h - br), (1, 0)), ('a', (x + w - br, y + h - br), br, 0),
        ('l', (x + w - br, y + h), (x + bl, y + h), (0, 1)), ('a', (x + bl, y + h - bl), bl, 90),
        ('l', (x, y + h - bl), (x, y + tl), (-1, 0)), ('a', (x + tl, y + tl), tl, 180),
    ]
    pts = []
    for s in segs:
        if s[0] == 'l':
            (ax, ay), (bx, by), (nx, ny) = s[1], s[2], s[3]
            n = max(1, round(math.hypot(bx - ax, by - ay) / step))
            for i in range(n):
                t, j = i / n, rnd.uniform(-wob, wob)
                pts.append((ax + (bx - ax) * t + nx * j, ay + (by - ay) * t + ny * j))
        else:
            (cx, cy), rr, a0 = s[1], s[2], s[3]
            if rr <= 0.01:
                continue
            n = max(2, round(rr * math.pi / 2 / (step * 0.6)))
            for i in range(n):
                a = math.radians(a0 + 90 * i / n)
                q = rr + rnd.uniform(-wob, wob)
                pts.append((cx + q * math.cos(a), cy + q * math.sin(a)))
    return pts


def blob_pts(cx, cy, rx, ry, rnd, wob=0.06, n=18, rot=0.0):
    """Points round a loose ellipse; wob is a fraction of the radius."""
    pts, ph = [], rnd.uniform(0, math.tau)
    for i in range(n):
        a = math.tau * i / n
        k = 1 + wob * math.sin(3 * a + ph) + rnd.uniform(-wob, wob) * 0.6
        px, py = rx * k * math.cos(a), ry * k * math.sin(a)
        pts.append((cx + px * math.cos(rot) - py * math.sin(rot),
                    cy + px * math.sin(rot) + py * math.cos(rot)))
    return pts


def circle_pts(cx, cy, r, rnd, wob=0.2, n=20):
    return [(cx + (r + rnd.uniform(-wob, wob)) * math.cos(math.tau * i / n),
             cy + (r + rnd.uniform(-wob, wob)) * math.sin(math.tau * i / n)) for i in range(n)]


def cr(p0, p1, p2, p3, t):
    return tuple(0.5 * (2 * p1[a] + (-p0[a] + p2[a]) * t
                        + (2 * p0[a] - 5 * p1[a] + 4 * p2[a] - p3[a]) * t * t
                        + (-p0[a] + 3 * p1[a] - 3 * p2[a] + p3[a]) * t ** 3) for a in (0, 1))


def dense(ctrl, closed, step=0.9):
    """Points about step apart along the same Catmull-Rom curve smooth() draws."""
    n, out = len(ctrl), []
    for i in range(n if closed else n - 1):
        p0 = ctrl[(i - 1) % n] if closed else ctrl[max(i - 1, 0)]
        p1, p2 = ctrl[i], ctrl[(i + 1) % n]
        p3 = ctrl[(i + 2) % n] if closed else ctrl[min(i + 2, n - 1)]
        k = max(2, math.ceil(math.dist(p1, p2) / step))
        out.extend(cr(p0, p1, p2, p3, j / k) for j in range(k))
    return out if closed else out + [ctrl[-1]]


def normals(pts):
    out, n = [], len(pts)
    for i in range(n):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        q = math.hypot(tx, ty) or 1
        out.append((-ty / q, tx / q))
    return out


def run_lengths(pts):
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    return cum


def pen_poly(pts, W, rnd, taper=(True, True), wmin=0.18):
    """The outline of one pen stroke along dense points: full width mid-stroke, thin where
    the pen lands and lifts, with a little pressure wander."""
    cum, nrm = run_lengths(pts), normals(pts)
    L = cum[-1] or 1
    tl = min(0.32 * L, 3 + 2.2 * W)
    ph, fr = rnd.uniform(0, math.tau), rnd.uniform(0.8, 1.6)
    left, right = [], []
    for (x, y), (nx, ny), c in zip(pts, nrm, cum):
        e = 1.0
        if taper[0]:
            e = min(e, c / tl)
        if taper[1]:
            e = min(e, (L - c) / tl)
        e = max(0.0, min(1.0, e))
        e = e * e * (3 - 2 * e)
        w = W * (wmin + (1 - wmin) * e) * (1 + 0.09 * math.sin(fr * c / 6 + ph))
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    return left + right[::-1]


def poly_d(poly):
    return 'M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in poly) + ' Z'


def closed_strokes(P, W, rnd):
    """A closed outline drawn as a hand draws one: one to three strokes, overlapping where
    the pen picks up again."""
    m, per = len(P), run_lengths(P + P[:1])[-1]
    ns = 1 if per < 70 else 2 if per < 320 else 3
    s0, ov = rnd.randrange(m), max(2, int(0.03 * m))
    return [pen_poly([P[i % m] for i in range(s0 + j * m // ns, s0 + (j + 1) * m // ns + ov + 1)],
                     W, rnd) for j in range(ns)]


def fold_ribbon(P, width):
    """The shadow along a fold: a sliver beside the ridge, on the side away from the light."""
    nrm, cum = normals(P), run_lengths(P)
    L = cum[-1] or 1
    s = 1 if sum(nx + ny for nx, ny in nrm) >= 0 else -1
    bulge = [width * max(0.0, math.sin(math.pi * c / L)) ** 0.8 for c in cum]
    outer = [(x + s * nx * b, y + s * ny * b) for (x, y), (nx, ny), b in zip(P, nrm, bulge)]
    return P + outer[::-1]


def on_edge(pt, poly) -> bool:
    """Whether a point lies on one of a straight-walled polygon's edges."""
    x, y = pt
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2)) or \
                (y1 == y2 == y and min(x1, x2) <= x <= max(x1, x2)):
            return True
    return False


def inside(pt, poly) -> bool:
    x, y, hit = pt[0], pt[1], False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def place(pts, x, y, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(x + px * c - py * s, y + px * s + py * c) for px, py in pts]


def profile_leaf(L, W, prof, rnd, splits=(), wave=0.0):
    """A leaf from a half-width profile of (t, w) pairs: base at the origin, tip at (L, 0).

    splits are fractions along the leaf where a cut runs in toward the midrib, as monstera's do."""
    sides = []
    for sgn in (-1, 1):
        ph = rnd.uniform(0, math.tau)
        ctrl = [(t * L, sgn * w * W / 2 * (1 + rnd.uniform(-0.04, 0.04)
                                           + wave * math.sin(9 * t + ph))) for t, w in prof]
        pts = sample(ctrl, 6)
        for s in splits:
            s += rnd.uniform(-0.03, 0.03)
            i = min(range(len(pts)), key=lambda k: abs(pts[k][0] - s * L))
            if 1 <= i < len(pts) - 1:
                x0, y0 = pts[i]
                pts[i] = (x0 + 0.04 * L, y0 * 0.3)
                pts.insert(i, (x0 - 0.012 * L, y0 * 1.0))
                pts.insert(i + 2, (x0 + 0.012 * L, y0 * 0.98))
        sides.append(pts)
    return sides[0] + sides[1][::-1][1:-1]
