"""
canvas — a piece and the sheet it is placed on.

A piece (Ink) is drawn once in its own coordinates, with the side that goes against a wall along
the top, and placed by a quarter turn. Shading is worked out after placement, so the light stays in
the upper left whichever way a piece faces: each form gets a shade crescent on its lower right, a
lit edge on its upper left, and a cast shadow down and to the right scaled by its height. A Sheet
collects the placed pieces, the glass, the floor light and the windows into one SVG, or into layers
for the widget; CSS styles it, and render screenshots it in WebKit.
"""

from __future__ import annotations

import json
import math
import random
import re
import subprocess
import sys

from pen import (
    C, blob_pts, circle_pts, closed_strokes, dense, f, fold_ribbon, inside, light_of, mix,
    pen_poly, pen_width, poly_d, rrect_pts, shade_of, smooth,
)


SHADOW_K = 0.085
AMBIENT = '#dcb68c'
FALLOFF = '#c8996c'
RIM = '#ffd08c'
DESKTOP_BG = '#b9c6cf'
DESKTOP = ((0.15, 0.2, 0.28, '#e9c9a8'), (0.8, 0.15, 0.25, '#9fb4c6'), (0.55, 0.85, 0.3, '#d9b8b0'),
           (0.1, 0.9, 0.22, '#a9bba6'), (0.92, 0.75, 0.2, '#e6d3b4'))


# ── a piece ───────────────────────────────────────────────────────────────


PLANT = {'monstera', 'fiddle-leaf', 'rubber-plant', 'snake-plant'}


class Ink:
    """One piece in its own coordinates: (0, 0) is its wall-side corner, footprint w × d."""

    def __init__(self, name, w, d, height, ln=C['line'], seed=0):
        self.name, self.w, self.d, self.height, self.ln = name, w, d, height, ln
        self.rnd = random.Random(f'{name}:{seed}')
        self.ops = []

    def form(self, pts, fill, relief=2.0, cast=None, line='line', straight=False):
        """A filled form: it is shaded, lit and outlined once placed. A straight form's points
        are already dense and are joined as they are, so a cut in it stays sharp."""
        self.ops.append(('form', pts, fill, relief, cast, line, straight))

    def flat(self, pts, fill, straight=False):
        self.ops.append(('flat', pts, fill, straight))

    def mark(self, pts, cls, closed=False):
        self.ops.append(('mark', pts, cls, closed))

    def fold(self, pts, fabric, width=3.0):
        """A fold in cloth: its ridge line, with a shadow sliver on the side away from the light."""
        self.ops.append(('fold', pts, fabric, width))

    def clipped(self, outline, marks, cls):
        """Marks kept inside an outline, such as a rug's pattern."""
        self.ops.append(('clipped', outline, marks, cls))

    def poly(self, pts, fill):
        """A straight-sided fill, such as the grout or the seams under a floor."""
        self.ops.append(('poly', pts, fill))

    def begin_clip(self, outline, straight=False):
        """Everything drawn until end_clip stays inside the outline."""
        self.ops.append(('begin', outline, straight))

    def leaf(self, px, py):
        """Start one leaf, hung from (px, py): everything drawn until end_leaf moves with it."""
        self.ops.append(('leaf', px, py))

    def end_leaf(self):
        self.ops.append(('endleaf',))

    def light(self, cx, cy, reach, surface=None):
        """A lamp's light. The room gathers these and lights itself in one pass: a pool on the
        floor, the near edges of furniture, and the surface the lamp stands on, if given."""
        self.ops.append(('light', cx, cy, reach, surface))

    def end_clip(self):
        self.ops.append(('end',))

    def rr(self, x, y, w, h, r, wob=0.3, step=7.0):
        return rrect_pts(x, y, w, h, r, self.rnd, wob, step)

    def circ(self, cx, cy, r, wob=0.2, n=20):
        return circle_pts(cx, cy, r, self.rnd, wob, n)

    def blob(self, cx, cy, rx, ry, wob=0.06, n=18, rot=0.0):
        return blob_pts(cx, cy, rx, ry, self.rnd, wob, n, rot)

    def dims(self, rot):
        if rot in (0, 180):
            return self.w, self.d
        if rot in (90, 270):
            return self.d, self.w
        a = math.radians(rot)
        return (abs(self.w * math.cos(a)) + abs(self.d * math.sin(a)),
                abs(self.w * math.sin(a)) + abs(self.d * math.cos(a)))


def mapper(ink, X, Y, rot):
    """Where a point in a piece's own coordinates lands once the piece is placed."""
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def tw(p):
        x, y = p
        if rot % 90:
            u, v = x - ink.w / 2, y - ink.d / 2
            return (X + ink.w / 2 + u * ca - v * sa, Y + ink.d / 2 + u * sa + v * ca)
        if rot == 90:
            return (X + ink.d - y, Y + x)
        if rot == 180:
            return (X + ink.w - x, Y + ink.d - y)
        if rot == 270:
            return (X + y, Y + ink.w - x)
        return (X + x, Y + y)

    return tw


def facing(rot):
    """A piece's front, the side away from the wall it backs onto, as a unit vector."""
    return {0: (0, 1), 90: (-1, 0), 180: (0, -1), 270: (1, 0)}.get(rot % 360, (0, 1))


def glazing(opening, T, sliding):
    """A window or sliding door seen from above, set in the wall: painted frames on both faces,
    glass between, a mullion; a sliding door is two framed panels on their tracks, a handle on
    the inner one."""
    (ax, ay), (bx, by), _ = opening
    along_x = abs(bx - ax) >= abs(by - ay)
    x1, x2, y1, y2 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)

    def rect(u0, u1, v0, v1, cls, extra=''):
        if along_x:
            return (f'<rect class="{cls}" x="{f(u0)}" y="{f(v0)}" width="{f(u1 - u0)}" '
                    f'height="{f(v1 - v0)}"{extra}/>')
        return (f'<rect class="{cls}" x="{f(v0)}" y="{f(u0)}" width="{f(v1 - v0)}" '
                f'height="{f(u1 - u0)}"{extra}/>')

    u0, u1 = (x1, x2) if along_x else (y1, y2)
    c = ay if along_x else ax
    out = [rect(u0, u1, c - T / 2, c + T / 2, 'threshold' if sliding else 'sill')]
    if sliding:
        #an oak threshold under the panels, filling the opening and no wider than the wall...
        #two black-framed panels on their own tracks, overlapping in the middle...
        out.append(rect(u0 + 1, u1 - 1, c - 0.4, c + 0.4, 'track'))
        mid = (u0 + u1) / 2
        for p0, p1, v0, v1 in ((u0 + 1.5, mid + 9, c - T / 2 + 0.6, c - 0.8),
                               (mid - 9, u1 - 1.5, c + 0.8, c + T / 2 - 0.6)):
            out.append(rect(p0, p1, v0, v1, 'slider-frame'))
            out.append(rect(p0 + 2.4, p1 - 2.4, v0 + 1.4, v1 - 1.4, 'pane slider'))
            for g in (0.22, 0.3, 0.62):
                gp = p0 + (p1 - p0) * g
                out.append(rect(gp, gp + (p1 - p0) * 0.05, v0 + 1.6, v1 - 1.6, 'glint-bar'))
        side = (opening[2][1] if along_x else opening[2][0]) or 1
        hv = c + side * (T / 2 - 1.2)
        out.append(rect(mid - 15, mid - 11, min(hv, hv - side * 3.2), max(hv, hv - side * 3.2),
                        'handle'))
        out.append(rect(u0, u0 + 2.5, c - T / 2, c + T / 2, 'jamb'))
        out.append(rect(u1 - 2.5, u1, c - T / 2, c + T / 2, 'jamb'))
        out.append(rect(u0, u1, c - T / 2, c + T / 2, 'threshold-line'))
        return ''.join(out)
    out.append(rect(u0 + 1.5, u1 - 1.5, c - 2.4, c + 2.4, 'pane'))
    out.append(rect(u0 + 1.5, u1 - 1.5, c - 2.4, c + 2.4, 'frame'))
    mid = (u0 + u1) / 2
    out.append(rect(mid - 1, mid + 1, c - 3.2, c + 3.2, 'mullion'))
    out.append(rect(u0, u1, c - T / 2, c + T / 2, 'frame'))
    return ''.join(out)


def light_patch(opening, T, depth):
    """The light a window lets onto the floor: the opening's width, reaching into the room and
    widening a little, brightest at the sill."""
    (ax, ay), (bx, by), (nx, ny) = opening
    fx, fy = ax + nx * T / 2, ay + ny * T / 2
    gx, gy = bx + nx * T / 2, by + ny * T / 2
    tx, ty = (gx - fx), (gy - fy)
    L = math.hypot(tx, ty) or 1
    tx, ty = tx / L * 34, ty / L * 34
    far_a = (fx + nx * depth - tx, fy + ny * depth - ty)
    far_b = (gx + nx * depth + tx, gy + ny * depth + ty)
    mid = ((fx + gx) / 2, (fy + gy) / 2)
    return [(fx, fy), (gx, gy), far_b, far_a], mid, (mid[0] + nx * depth, mid[1] + ny * depth)


def curtains(window, T, seed=0):
    """A pair of open curtains at a window, seen from above, drawn where they hang. Each is
    gathered in pleats against the wall at one side of the window, on a shared rod, and lets a
    loose tail of fabric fall toward the middle; the breeze through the window catches the tails.
    Returns the gathered part (it holds still) and the two tails, each with the point it hangs
    from and which way the wind turns it."""
    (ax, ay), (bx, by), (nx, ny) = window
    Lw = math.hypot(bx - ax, by - ay)
    tx, ty = (bx - ax) / Lw, (by - ay) / Lw
    rnd = random.Random(f'curtain:{seed}:{ax}:{ay}')

    def at(u, v):
        return (ax + tx * u + nx * (T / 2 + v), ay + ty * u + ny * (T / 2 + v))

    still = Ink('curtain', 1, 1, 30, C['lin600'], seed)
    for u0, u1 in ((-12, 18), (Lw - 18, Lw + 12)):
        edge = [at(u0, 1.5)] + [at(u0 + (u1 - u0) * k / 10,
                                    12 + 1.8 * math.sin(k * 1.9 + seed) + rnd.uniform(-0.5, 0.5))
                                for k in range(11)] + [at(u1, 1.5)]
        still.form(edge, C['lin50'], relief=1.8, cast=40)
        for k in range(1, 10):
            u = u0 + (u1 - u0) * k / 10
            still.mark([at(u, 2.4), at(u + rnd.uniform(-0.6, 0.6), 11)], 'detail faint')

    #the rod runs the full width a little off the wall, over the curtains' tops...
    rod = [at(-20, 2.2), at(Lw + 20, 2.2), at(Lw + 20, 4.6), at(-20, 4.6)]
    still.form(rod, C['black'], relief=0.4, cast=60, straight=True, line='line thin')
    for u in (-20, Lw + 20):
        still.form(circle_pts(*at(u, 3.4), 2.8, rnd, 0.05, 12), C['chr200'], relief=0.6)
    tails = []
    reach = min(52, Lw * 0.42)
    for sgn, u_pivot in ((1, 14), (-1, Lw - 14)):
        k = Ink('curtain-tail', 1, 1, 30, C['lin600'], seed)
        side_a, side_b = [], []
        for n in range(13):
            s_ = reach * n / 12
            half = (1.6 + 5.2 * math.sin(math.pi * min(1, (s_ / reach) ** 0.7))
                    + 0.8 * math.sin(n * 1.7 + seed))
            u = u_pivot + sgn * s_
            side_a.append(at(u, 7 - half * 0.7))
            side_b.append(at(u, 7 + half))
        outline = side_a + side_b[::-1]
        k.form(outline, C['lin50'], relief=1.6, cast=30)
        for off in (-2, 1.5, 4.5):
            k.mark([at(u_pivot + sgn * 3, 7 + off * 0.4), at(u_pivot + sgn * reach * 0.55, 7 + off),
                    at(u_pivot + sgn * reach * 0.85, 7 + off * 1.2)], 'detail faint')
        px, py = at(u_pivot, 7)
        turn = 1 if sgn * (tx * ny - ty * nx) > 0 else -1
        tails.append((k, (px, py), turn))
    return still, tails


class Sheet:
    """An SVG canvas that places pieces and works out their light after placement."""

    def __init__(self, w, h, bg=None):
        self.w, self.h, self.bg = w, h, bg
        self.defs, self.body, self.n = [], [], 0
        self.lights, self.forms, self.top = [], [], []
        self.room_polys, self.panel, self.blurs = [], None, set()
        self.sprites = {}
        self.inside = None
        self.panes = []
        self.curtain_windows = []

    def uid(self) -> str:
        self.n += 1
        return f'k{self.n}'

    def blur(self, std) -> str:
        """One shared blur filter per softness, so a hundred shadows cost a handful of filters."""
        key = f'b{str(std).replace(".", "_")}'
        if key not in self.blurs:
            self.blurs.add(key)
            self.defs.append(f'<filter id="{key}" x="-150%" y="-150%" width="400%" height="400%">'
                             f'<feGaussianBlur stdDeviation="{std}"/></filter>')
        return key

    def crescent(self, d, fill, off, cls):
        """The form less a copy of itself shifted by off: a sliver along one side."""
        m = self.uid()
        self.defs.append(f'<mask id="{m}"><path d="{d}" fill="#fff"/><path d="{d}" fill="#000" '
                         f'transform="translate({f(off)},{f(off)})"/></mask>')
        return f'<path class="{cls}" fill="{fill}" d="{d}" mask="url(#{m})"/>'

    def place(self, ink, X, Y, rot=0):
        """Put a piece down with its footprint's corner at X, Y. A quarter turn keeps the footprint
        on the grid; any other angle (a cat, a pouf) turns it about its own middle."""
        tw = mapper(ink, X, Y, rot)

        prnd = random.Random(f'{ink.name}:{X}:{Y}:{rot}')

        def ink_line(wp, cls, closed, straight=False):
            w = pen_width(cls)
            if w is None:
                return f'<path class="{cls}" d="{smooth(wp, closed)}"/>'
            polys = (closed_strokes(wp if straight else dense(wp, True), w, prnd) if closed
                     else [pen_poly(dense(wp, False), w, prnd)])
            return ''.join(f'<path class="ink {cls}" d="{poly_d(q)}"/>' for q in polys)

        out = [f'<g class="piece {ink.name}">']
        pooled = []
        for op in ink.ops:
            if op[0] == 'form':
                _, pts, fill, relief, cast, line, straight = op
                d = (poly_d if straight else smooth)([tw(p) for p in pts])
                if cast and ink.name in PLANT:
                    k = min(10.0, SHADOW_K * cast)
                    pooled.append((d, k))
                elif cast:
                    k = min(10.0, SHADOW_K * cast)
                    out.append(f'<path class="ao" d="{d}" filter="url(#{self.blur(2.2)})"/>')
                    out.append(f'<path class="cast" d="{d}" transform="translate({f(k)},{f(k)})" '
                               f'filter="url(#{self.blur(round(0.35 * k + 0.8, 1))})"/>')
                out.append(f'<path class="base" fill="{fill}" d="{d}"/>')
                if relief:
                    out.append(self.crescent(d, shade_of(fill), -relief, 'shade'))
                    out.append(self.crescent(d, light_of(fill), min(1.1, relief * 0.45), 'light'))
                if ink.height >= 5:
                    out.append(f'<!--rim:{len(self.forms)}-->')
                    self.forms.append((d, [tw(p) for p in pts]))
                if line:
                    out.append(ink_line([tw(p) for p in pts], line, True, straight))
            elif op[0] == 'flat':
                d = (poly_d if op[3] else smooth)([tw(p) for p in op[1]])
                out.append(f'<path class="base" fill="{op[2]}" d="{d}"/>')
            elif op[0] == 'mark':
                _, pts, cls, closed = op
                out.append(ink_line([tw(p) for p in pts], cls, closed))
            elif op[0] == 'fold':
                _, pts, fabric, width = op
                P = dense([tw(p) for p in pts], False)
                out.append(f'<path class="fold" fill="{mix(fabric, "#2a201b", 0.2)}" '
                           f'd="{poly_d(fold_ribbon(P, width))}"/>')
                out.append(f'<path class="ink detail" d="{poly_d(pen_poly(P, 0.9, prnd))}"/>')
            elif op[0] == 'poly':
                out.append(f'<path class="base" fill="{op[2]}" d="{poly_d([tw(p) for p in op[1]])}"/>')
            elif op[0] == 'begin':
                c, wp = self.uid(), [tw(p) for p in op[1]]
                self.defs.append(f'<clipPath id="{c}"><path d="{poly_d(wp) if op[2] else smooth(wp)}"/>'
                                 '</clipPath>')
                out.append(f'<g clip-path="url(#{c})">')
            elif op[0] == 'light':
                _, cx, cy, reach, surface = op
                self.lights.append((tw((cx, cy)), reach, surface is not None))
                if surface:
                    out.append(f'<!--surface:{len(self.lights) - 1}:{smooth([tw(p) for p in surface])}-->')
            elif op[0] == 'end':
                out.append('</g>')
            elif op[0] == 'leaf':
                lx, ly = tw((op[1], op[2]))
                out.append(f'<!--leaf:{f(lx)}:{f(ly)}-->')
            elif op[0] == 'endleaf':
                out.append('<!--/leaf-->')
            else:
                _, outline, marks, cls = op
                c = self.uid()
                self.defs.append(f'<clipPath id="{c}"><path d="{smooth([tw(p) for p in outline])}"/>'
                                 '</clipPath>')
                ds = ' '.join(smooth([tw(p) for p in m], False) for m in marks)
                out.append(f'<path class="{cls}" clip-path="url(#{c})" d="{ds}"/>')
        out.append('</g>')

        #a plant's leaves cast one soft shadow together, as foliage does...
        if pooled:
            k = max(kk for _, kk in pooled)
            shade = ''.join(f'<path d="{d}"/>' for d, _ in pooled)
            out.insert(1, f'<g class="cast" transform="translate({f(k)},{f(k)})" '
                          f'filter="url(#{self.blur(round(0.35 * k + 0.8, 1))})">{shade}</g>')
        self.body.append(''.join(out))

    def text(self, x, y, s, cls='label'):
        self.body.append(f'<text class="{cls}" x="{f(x)}" y="{f(y)}">{s}</text>')

    def rooms(self, polys, doors, windows=(), sliders=(), T=14):
        """Rooms as puzzle pieces. Each outline is a wall's centre line, stroked T thick with soft
        corners, and each wall casts a soft shadow into its room. A doorway is an opening in the
        wall that the floor runs through, given by its two jambs and the side it opens to. A
        window and a sliding glass door are set into the outer walls, glazed, each letting a
        patch of light onto the floor."""
        self.room_polys = polys
        m = self.uid()
        holes = ''
        for (ax, ay), (bx, by), _ in list(doors) + list(windows) + list(sliders):
            x1, x2, y1, y2 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
            if abs(bx - ax) < abs(by - ay):
                holes += f'<rect x="{f(x1 - T)}" y="{f(y1)}" width="{2 * T}" height="{f(y2 - y1)}"/>'
            else:
                holes += f'<rect x="{f(x1)}" y="{f(y1 - T)}" width="{f(x2 - x1)}" height="{2 * T}"/>'
        self.defs.append(f'<mask id="{m}"><rect width="{self.w}" height="{self.h}" fill="#fff"/>'
                         f'<g fill="#000">{holes}</g></mask>')
        walls = []
        for poly in polys:
            c = self.uid()
            self.defs.append(f'<clipPath id="{c}"><path d="{poly_d(poly)}"/></clipPath>'
                             f'<filter id="{c}s" x="-10%" y="-10%" width="120%" height="120%">'
                             f'<feGaussianBlur stdDeviation="5"/></filter>')
            self.body.append(f'<g clip-path="url(#{c})" mask="url(#{m})"><path class="wallcast" '
                             f'd="{poly_d(poly)}" filter="url(#{c}s)"/></g>')
            walls.append(f'<path class="wall" d="{poly_d(poly)}" stroke-width="{T}"/>')
        self.top.append(f'<g mask="url(#{m})">{"".join(walls)}</g>')
        for w in windows:
            self.top.append(glazing(w, T, sliding=False))
            self.panes.append(light_patch(w, T, 150))
        for w in sliders:
            self.top.append(glazing(w, T, sliding=True))
            self.panes.append(light_patch(w, T, 210))

    def glass_panel(self, x, y, w, h, r, backdrop=True):
        """The widget's glass: the house floats on it. The desktop behind is only a stand-in so a
        still image can show the frost; the app uses macOS's own glass material."""
        self.panel = (x, y, w, h, r, backdrop)

    def panel_markup(self) -> str:
        x, y, w, h, r, backdrop = self.panel
        c = self.uid()
        blobs = ''.join(f'<circle cx="{f(bx * self.w)}" cy="{f(by * self.h)}" r="{f(br * self.w)}" '
                        f'fill="{bc}"/>' for bx, by, br, bc in DESKTOP)
        self.defs.append(f'<clipPath id="{c}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/>'
                         f'</clipPath><filter id="{c}b" x="-20%" y="-20%" width="140%" height="140%">'
                         f'<feGaussianBlur stdDeviation="{f(self.w / 30)}"/></filter>'
                         f'<filter id="{c}d" x="-20%" y="-20%" width="140%" height="140%">'
                         f'<feGaussianBlur stdDeviation="10"/></filter>'
                         f'<linearGradient id="{c}g" x1="0" y1="0" x2="0" y2="1">'
                         f'<stop offset="0" stop-color="#fff" stop-opacity=".34"/>'
                         f'<stop offset="1" stop-color="#fff" stop-opacity=".16"/></linearGradient>')
        out = ''
        if backdrop:
            out += (f'<rect width="{self.w}" height="{self.h}" fill="{DESKTOP_BG}"/>'
                    f'<g filter="url(#{c}d)">{blobs}</g>'
                    f'<rect x="{x}" y="{y + 6}" width="{w}" height="{h}" rx="{r}" fill="#000" '
                    f'opacity=".16" filter="url(#{c}d)"/>'
                    f'<g clip-path="url(#{c})"><rect width="{self.w}" height="{self.h}" '
                    f'fill="{DESKTOP_BG}"/><g filter="url(#{c}b)">{blobs}</g></g>')
        return out + (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#{c}g)"/>'
                      f'<rect class="glass-edge" x="{x + 0.6}" y="{y + 0.6}" width="{w - 1.2}" '
                      f'height="{h - 1.2}" rx="{r}"/>')

    def floor_light(self):
        """Where lamp pools land: after the floor and the rugs, before the furniture."""
        self.body.append('<!--floorlight-->')

    def rim(self, d, pts, lights) -> str:
        """Lamp light caught on the edges of a form that face a lamp nearby."""
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        out = []
        for (lx, ly), reach, _ in lights:
            if inside((lx, ly), pts):
                continue
            near = 1 - min(math.dist((lx, ly), p) for p in pts) / reach
            if near <= 0.03:
                continue
            i = near ** 1.2
            q = math.hypot(lx - cx, ly - cy) or 1
            t = 1.0 + 1.6 * i
            m = self.uid()
            self.defs.append(f'<mask id="{m}"><path d="{d}" fill="#fff"/><path d="{d}" fill="#000" '
                             f'transform="translate({f(-(lx - cx) / q * t)},{f(-(ly - cy) / q * t)})"/>'
                             '</mask>')
            out.append(f'<path class="screen" fill="{RIM}" opacity="{f(min(0.95, i * 1.15))}" '
                       f'd="{d}" mask="url(#{m})"/>')
        return ''.join(out)

    def lit_body(self, split=False):
        """The body with every light placeholder filled in. Split, the lamp pools come back on
        their own, so the widget can let them breathe."""
        pool = self.uid()
        self.defs.append(f'<radialGradient id="{pool}">' + ''.join(
            f'<stop offset="{o}" stop-color="{C["glow"]}" stop-opacity="{a}"/>'
            for o, a in ((0, .4), (.15, .3), (.4, .15), (.7, .05), (1, 0))) + '</radialGradient>')
        pools = ''.join(f'<circle class="screen" cx="{f(lx)}" cy="{f(ly)}" '
                        f'r="{f(reach * (0.8 if on_surface else 1))}" fill="url(#{pool})"/>'
                        for (lx, ly), reach, on_surface in self.lights)
        soft = self.blur(14)
        for poly, near, far in self.panes:
            gid = self.uid()
            self.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                             f'x1="{f(near[0])}" y1="{f(near[1])}" x2="{f(far[0])}" y2="{f(far[1])}">'
                             f'<stop offset="0" stop-color="{C["core"]}" stop-opacity=".3"/>'
                             f'<stop offset="1" stop-color="{C["core"]}" stop-opacity="0"/>'
                             '</linearGradient>')
            pools += (f'<path class="screen" d="{poly_d(poly)}" fill="url(#{gid})" '
                      f'filter="url(#{soft})"/>')
        if self.inside:
            pools = f'<g clip-path="url(#{self.inside})">{pools}</g>'
        body = ''.join(self.body).replace('<!--floorlight-->', '' if split else pools)
        body = re.sub(r'<!--rim:(\d+)-->',
                      lambda m: self.rim(*self.forms[int(m.group(1))], self.lights), body)

        def surface(m):
            (lx, ly), reach, _ = self.lights[int(m.group(1))]
            c = self.uid()
            self.defs.append(f'<clipPath id="{c}"><path d="{m.group(2)}"/></clipPath>')
            return (f'<circle class="screen" clip-path="url(#{c})" cx="{f(lx)}" cy="{f(ly)}" '
                    f'r="{f(reach * 0.75)}" fill="url(#{pool})"/>')

        body = re.sub(r'<!--surface:(\d+):([^>]*)-->', surface, body)
        return (body, pools) if split else body

    def ambient(self) -> str:
        """Evening dimness over every room, warm and deeper toward each room's walls, with a soft
        hole cut wherever a lamp shines: lamps light by keeping the dark away, not by adding glare."""
        xs = [p[0] for poly in self.room_polys for p in poly]
        ys = [p[1] for poly in self.room_polys for p in poly]
        x, y, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
        c = self.uid()
        defs = [f'<clipPath id="{c}c">' + ''.join(f'<path d="{poly_d(q)}"/>' for q in self.room_polys)
                + '</clipPath>',
                f'<radialGradient id="{c}h"><stop offset="0" stop-color="#000" stop-opacity=".85"/>'
                f'<stop offset=".3" stop-color="#000" stop-opacity=".55"/>'
                f'<stop offset=".65" stop-color="#000" stop-opacity=".2"/>'
                f'<stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>',
                f'<mask id="{c}m"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff"/>'
                + ''.join(f'<circle cx="{f(lx)}" cy="{f(ly)}" r="{f(reach)}" fill="url(#{c}h)"/>'
                          for (lx, ly), reach, _ in self.lights)
                + ''.join(f'<path d="{poly_d(poly)}" fill="#000" opacity=".32" '
                          f'filter="url(#{self.blur(18)})"/>' for poly, _, _ in self.panes)
                + '</mask>']
        falloff = []
        for n, q in enumerate(self.room_polys):
            qx, qy = [p[0] for p in q], [p[1] for p in q]
            bx, by, bw, bh = min(qx), min(qy), max(qx) - min(qx), max(qy) - min(qy)
            defs.append(f'<clipPath id="{c}r{n}"><path d="{poly_d(q)}"/></clipPath>'
                        f'<radialGradient id="{c}f{n}" gradientUnits="userSpaceOnUse" '
                        f'cx="{f(bx + bw / 2)}" cy="{f(by + bh / 2)}" r="{f(max(bw, bh) * 0.7)}">'
                        f'<stop offset=".4" stop-color="#fff"/><stop offset="1" '
                        f'stop-color="{FALLOFF}"/></radialGradient>')
            falloff.append(f'<rect class="multiply" clip-path="url(#{c}r{n})" x="{bx}" y="{by}" '
                           f'width="{bw}" height="{bh}" fill="url(#{c}f{n})"/>')
        self.defs.extend(defs)
        return (f'<g class="multiply" mask="url(#{c}m)" clip-path="url(#{c}c)">'
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{AMBIENT}"/>{"".join(falloff)}'
                '</g>')

    def svg(self, css, scale=1.0, lit=True) -> str:
        bg = f'<rect width="{self.w}" height="{self.h}" fill="{self.bg}"/>' if self.bg else ''
        bg += self.panel_markup() if self.panel else ''
        if lit and self.room_polys:
            inner = bg + self.lit_body() + self.ambient() + ''.join(self.top)
        else:
            inner = bg + re.sub(r'<!--[^>]*-->', '', ''.join(self.body)) + ''.join(self.top)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="{f(self.w * scale)}" height="{f(self.h * scale)}"><style>{css}</style>'
                f'<defs>{"".join(self.defs)}</defs>{inner}</svg>')

    def raw(self, markup):
        self.body.append(markup)

    def layers(self, css):
        """The sheet as the widget's stack of layers, each a full-size SVG over the same
        viewBox: floor (with rugs), furniture, glow (the lamp pools), ambient (the evening
        dimness) and walls; plus one SVG per sprite, the pieces that move."""
        body, pools = self.lit_body(split=True)
        ambient = self.ambient()
        floor, furniture = body.split('<!--layer:furniture-->')
        sprites = {}

        def take(m):
            sprites[m.group(1)] = m.group(2)
            return ''

        furniture = re.sub(r'<!--sprite:([\w-]+)-->(.*?)<!--/sprite-->', take, furniture,
                           flags=re.S)
        def wrap(inner):
            return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} '
                    f'{self.h}" width="{f(self.w)}" height="{f(self.h)}"><style>{css}'
                    f'</style><defs>{"".join(self.defs)}</defs>{inner}</svg>')
        def clean(t):
            return re.sub(r'<!--[^>]*-->', '', t)
        out = {'floor': wrap(clean(floor)), 'furniture': wrap(clean(furniture)),
               'glow': wrap(pools), 'ambient': wrap(ambient), 'walls': wrap(''.join(self.top))}
        split = {}
        for k, v in sprites.items():
            leaves = [(float(m.group(1)), float(m.group(2)), clean(m.group(3)))
                      for m in re.finditer(r'<!--leaf:([-\d.]+):([-\d.]+)-->(.*?)<!--/leaf-->', v,
                                           re.S)]
            base = re.sub(r'<!--leaf:[^>]*-->.*?<!--/leaf-->', '', v, flags=re.S)
            split[k] = dict(base=wrap(clean(base)), leaves=leaves)
        return out, split


CSS = f'''
.ink{{stroke:none}}
.ink.line{{fill:{C['line']}}}
.ink.detail{{fill:{C['line']};opacity:.62}}
.ink.detail.faint{{opacity:.34}}
.ink.rib{{fill:{C['leaf800']};opacity:.55}}
.ink.rib.light{{fill:{C['leaf200']};opacity:.85}}
.ink.vein.light{{fill:{C['leaf200']};opacity:.5}}
.ink.petiole{{fill:{C['leaf600']}}}
.ink.glint{{fill:#fff;opacity:.55}}
.ink.tassel{{fill:{C['line']};opacity:.45}}
.ink.wire{{fill:{C['line']};opacity:.5}}
.stitch{{fill:none;stroke:{C['line']};stroke-width:.6;stroke-dasharray:1.6 2.4;opacity:.32}}
.knit{{fill:none;stroke:{C['line']};stroke-width:.55;stroke-linejoin:round;opacity:.26}}
.ink.vein{{fill:{C['leaf800']};opacity:.32}}
.ink.edge{{fill:{C['leaf200']};opacity:.9}}
.ink.vine{{fill:{C['leaf600']}}}
.ink.twig{{fill:{C['wal500']}}}
.ink.bristle{{fill:{C['chr400']}}}
.ink.fringe{{fill:{C['lin400']}}}
.ink.weave{{fill:{C['oak500']}}}
.ink.chrome-ring{{fill:{C['chr400']}}}
.ink.arm{{fill:{C['black']}}}
.ink.stripe{{fill:#cf8f50}}
.ink.stripe.grey{{fill:#958c86}}
.ink.stripe.black{{fill:#3a3331}}
.ink.stripe.cream{{fill:#e2c7a2}}
.ink.whisker{{fill:{C['line']};opacity:.55}}
.fold{{opacity:.7}}
.cast{{fill:{C['wall']};opacity:.3}}
.ao{{fill:{C['wall']};opacity:.22}}
.dots{{fill:none;stroke:{C['line']};stroke-dasharray:.1 3.2;stroke-width:1.6;stroke-linecap:round;
  stroke-opacity:.4}}
.seam{{fill:none;stroke:{C['oak500']};stroke-width:.55;stroke-opacity:.45}}
.ink.grain{{fill:{C['oak500']};opacity:.42}}
.ink.grain.light{{fill:{C['oak300']};opacity:.75}}
.ink.grain.walnut{{fill:{C['wal700']};opacity:.5}}
.ink.grain.amber{{fill:{C['wal500']};opacity:.42}}
.ink.knot{{fill:{C['oak500']};opacity:.5}}
.lattice{{fill:none;stroke:{C['lin600']};stroke-width:.8;stroke-opacity:.55}}
.cane{{fill:none;stroke:{C['oak500']};stroke-width:.45;stroke-opacity:.5}}
.jute{{fill:none;stroke:{C['oak500']};stroke-width:.6;stroke-opacity:.45}}
.multiply{{mix-blend-mode:multiply}}
.screen{{mix-blend-mode:screen}}
.wall{{fill:none;stroke:{C['wall']};stroke-linejoin:round;stroke-linecap:round}}
.wallcast{{fill:none;stroke:{C['wall']};stroke-width:30;opacity:.22}}
.glass-edge{{fill:none;stroke:#fff;stroke-opacity:.55;stroke-width:1.2}}
.sill{{fill:#efe6d6}}
.pane{{fill:{C['glass']};opacity:.9}}
.frame{{fill:none;stroke:{C['line']};stroke-width:1}}
.frame.dark{{stroke:{C['black']};stroke-width:1.3}}
.mullion{{fill:#efe6d6;stroke:{C['line']};stroke-width:.6}}
.handle{{fill:{C['chr200']};stroke:{C['line']};stroke-width:.5}}
.track{{fill:{C['chr400']}}}
.sill.track-bed{{fill:{C['chr200']}}}
.slider-frame{{fill:{C['black']};stroke:{C['line']};stroke-width:.6}}
.pane.slider{{fill:#cfe0e0;opacity:1}}
.glint-bar{{fill:#fff;opacity:.6}}
.jamb{{fill:{C['wall']}}}
.threshold{{fill:{C['oak300']}}}
.threshold-line{{fill:none;stroke:{C['line']};stroke-width:1}}
.ink.rod{{fill:{C['chr700']}}}
.ink.gloss{{fill:#fff;opacity:.38}}
.ink.marble-vein{{fill:#a59d92;opacity:.45}}
.ink.hob-ring{{fill:{C['chr400']};opacity:.8}}
.ink.spout{{fill:{C['chr400']}}}
.label{{font:500 10px "Avenir Next","Helvetica Neue",sans-serif;fill:{C['line']};
  text-anchor:middle;opacity:.8}}
.title{{font:600 14px "Avenir Next","Helvetica Neue",sans-serif;fill:{C['line']};
  letter-spacing:.6px}}
'''


#every piece maker marked @recorded, by name, so a piece recorded in a saved room can be made again...
MADE = {}


def recorded(fn):
    """A piece maker that writes its name and arguments on every piece it makes, so a room laid
    out once can be saved and made again exactly."""
    def make(*args, **kw):
        ink = fn(*args, **kw)
        ink.made = (fn.__name__, list(args), dict(kw))
        return ink
    make.__name__, make.__doc__ = fn.__name__, fn.__doc__
    MADE[fn.__name__] = make
    return make


def remade(name, args, kw):
    """A piece made again from what it recorded, able to be drawn again in parts like any other."""
    return Part(MADE[name], *args)(**kw)


class Part:
    """A piece maker that remembers its arguments, so the same piece can be drawn again in
    parts."""

    def __init__(self, fn, *args):
        self.fn, self.args = fn, args

    def __call__(self, **kw):
        ink = self.fn(*self.args, **kw)
        ink.remake = lambda **more: self.fn(*self.args, **more)
        return ink


def render(jobs) -> None:
    """Screenshot SVGs in WebKit, the engine the widget's web view uses: (svg, w, h, scale)."""
    code = ('import sys, json\nfrom playwright.sync_api import sync_playwright\n'
            'jobs = json.loads(sys.argv[1])\n'
            'with sync_playwright() as p:\n'
            '    b = p.webkit.launch()\n'
            '    for svg, w, h, sc in jobs:\n'
            '        pg = b.new_page(device_scale_factor=sc, viewport={"width": max(1, int(w) + 1),'
            ' "height": max(1, int(h) + 1)})\n'
            '        pg.goto("file://" + svg)\n'
            '        pg.locator("svg").first.screenshot(path=svg[:-4] + ".png", omit_background=True)\n'
            '        pg.close()\n'
            '    b.close()\n')
    subprocess.run([sys.executable, '-c', code, json.dumps(jobs)], check=True)
