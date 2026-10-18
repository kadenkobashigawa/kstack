"""
decor — the plants, rugs, pouf, basket and cat that dress a room.
"""

from __future__ import annotations

import math

from pen import C, blob_pts, dense, pen_poly, place, profile_leaf, sample
from canvas import Ink, recorded
from furniture import CLOTH, THROW


# ── decor ─────────────────────────────────────────────────────────────────


POT = {'white': C['lin50'], 'black': C['black'], 'basket': C['oak300']}


def pot(k, cx, cy, r, kind, cast):
    """A plant pot from above: its rim, the soil, and on a basket pot the weave."""
    k.form(k.circ(cx, cy, r, wob=0.15), POT[kind], relief=1.6, cast=cast)
    k.flat(k.circ(cx, cy, r * 0.8, wob=0.1), C['wal700'])
    if kind == 'basket':
        for i in range(int(r * 2)):
            a = i * math.tau / int(r * 2)
            k.mark([(cx + r * 0.84 * math.cos(a), cy + r * 0.84 * math.sin(a)),
                    (cx + r * 0.98 * math.cos(a + 0.08), cy + r * 0.98 * math.sin(a + 0.08))],
                   'weave')


def monstera_leaf(L, W, rnd, cuts=4):
    """One monstera leaf, base at the origin and tip at (L, 0), drawn from photographs: a broad
    heart, cut by smooth slits that widen inward to a rounded end, so the leaf falls into fingers
    with soft tips; a pale midrib; and a row of long oval holes beside it. Returns the outline,
    the finger veins and the holes (each as points)."""
    prof = [(0.05, 0.0), (-0.07, 0.30), (-0.02, 0.62), (0.12, 0.86), (0.3, 0.98), (0.5, 0.97),
            (0.68, 0.84), (0.83, 0.6), (0.94, 0.3), (1.0, 0.0)]
    sides, veins, holes = [], [], []
    for sgn in (-1, 1):
        edge = sample([(t * L, sgn * w * W / 2 * (1 + rnd.uniform(-0.03, 0.03))) for t, w in prof], 4)
        at = [0.24 + n * (0.54 / (cuts - 1)) + rnd.uniform(-0.02, 0.02) for n in range(cuts)]
        out, n, skip, tips = [], 0, None, []
        for x, y in edge:
            if skip and math.dist((x, y), skip) < 0.05 * L:
                continue
            if n < cuts and x >= at[n] * L and abs(y) > W * 0.2:
                if out and math.dist(out[-1], (x, y)) < 0.04 * L:
                    out.pop()
                qx, qy = x - 0.2 * L * abs(y) / (W / 2) * 0.78, y * rnd.uniform(0.2, 0.28)
                ax, ay = qx - x, qy - y
                la = math.hypot(ax, ay)
                ux, uy = ax / la, ay / la
                bx, by = -uy, ux
                if bx > 0:
                    bx, by = -bx, -by
                side = []
                for u, hw in ((0, 0.016), (0.35, 0.017), (0.7, 0.026), (0.92, 0.02)):
                    side.append((x + ux * la * u, y + uy * la * u, hw * L))
                out += [(px + bx * h, py + by * h) for px, py, h in side]
                out.append((qx + ux * 0.02 * L, qy + uy * 0.02 * L))
                out += [(px - bx * h, py - by * h) for px, py, h in reversed(side)]
                tips.append((x, y))
                skip, n = (x, y), n + 1
            else:
                out.append((x, y))
        sides.append(out)
        ends = [(L * 0.05, sgn * W * 0.2)] + tips + [(L * 0.97, 0)]
        for (x0, y0), (x1, y1) in zip(ends, ends[1:]):
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            veins.append([(mx - 0.13 * L, my * 0.1), (mx - 0.04 * L, my * 0.6), (mx, my * 0.86)])
        for x0, x1 in zip(at, at[1:]):
            hx, hy = (x0 + x1) / 2 * L - 0.1 * L, sgn * W / 2 * rnd.uniform(0.2, 0.26)
            holes.append(blob_pts(hx, hy, 0.055 * L, 0.018 * L, rnd, wob=0.03, n=12,
                                  rot=sgn * 0.75))
    return sides[0] + sides[1][::-1][1:-1], veins, holes


@recorded
def monstera(seed=0, pot_kind='white'):
    """A monstera from above: big split leaves overlapping round its pot on short stalks, an outer
    ring of the oldest and widest, newer ones laid over the middle."""
    k = Ink('monstera', 110, 110, 110, C['leaf800'], seed)
    cx = cy = 55
    outer = [(i * math.tau / 5 + k.rnd.uniform(-0.25, 0.25), k.rnd.uniform(38, 46),
              k.rnd.uniform(6, 10)) for i in range(5)]
    inner = [(a + math.tau / 10 + k.rnd.uniform(-0.2, 0.2), k.rnd.uniform(28, 34),
              k.rnd.uniform(1, 4)) for a, _, _ in outer[:3]]
    for a, L, stalk in outer + inner:
        k.mark([(cx, cy), (cx + stalk * math.cos(a), cy + stalk * math.sin(a))], 'petiole')
    pot(k, cx, cy, 15, pot_kind, 40)
    for n, (a, L, stalk) in enumerate(outer + inner):
        outline, veins, holes = monstera_leaf(L, L * k.rnd.uniform(0.86, 0.94), k.rnd)
        bx, by = cx + stalk * math.cos(a), cy + stalk * math.sin(a)
        k.leaf(bx, by)
        k.form(place(outline, bx, by, a), C['leaf600'] if n % 2 else C['leaf400'], relief=1.6,
               cast=110)
        for hole in holes:
            k.form(place(hole, bx, by, a), C['hole'], relief=0, line='line thin')
        for v in veins:
            k.mark(place(v, bx, by, a), 'vein light')
        k.mark(place([(0, 0), (L * 0.5, 0), (L * 0.93, 0)], bx, by, a), 'rib light')
        k.end_leaf()
    return k


@recorded
def fiddle_leaf(seed=0, pot_kind='white'):
    """A fiddle-leaf fig: broad, wavy, round-tipped leaves round its pot."""
    k = Ink('fiddle-leaf', 80, 80, 130, C['leaf800'], seed)
    prof = [(0, 0.05), (0.12, 0.3), (0.32, 0.48), (0.55, 0.66), (0.75, 0.9), (0.88, 0.92),
            (0.97, 0.55), (1.0, 0.0)]
    leaves = []
    for i in range(12):
        a = i * math.tau / 12 + k.rnd.uniform(-0.25, 0.25)
        leaves.append((a, k.rnd.uniform(18, 26), k.rnd.uniform(15, 19), k.rnd.uniform(4, 12), i))
    for i in range(7):
        a = k.rnd.uniform(0, math.tau)
        leaves.append((a, k.rnd.uniform(16, 22), k.rnd.uniform(13, 17), k.rnd.uniform(1, 5), i + 13))
    for a, L, W, d0, i in leaves:
        k.mark([(40, 40), (40 + (d0 + 2) * math.cos(a), 40 + (d0 + 2) * math.sin(a))], 'petiole')
    pot(k, 40, 40, 12, pot_kind, 30)
    for a, L, W, d0, i in sorted(leaves, key=lambda v: -v[3]):
        local = profile_leaf(L, W, prof, k.rnd, wave=0.05)
        bx, by = 40 + d0 * math.cos(a), 40 + d0 * math.sin(a)
        k.leaf(bx, by)
        k.form(place(local, bx, by, a), C['leaf400'] if i % 3 else C['leaf600'], relief=1.4,
               cast=130)
        k.mark(place([(0, 0), (L * 0.5, 0), (L * 0.85, 0)], bx, by, a), 'rib')
        for t in (0.35, 0.55, 0.72):
            for s in (-1, 1):
                k.mark(place([(L * t, 0), (L * (t + 0.12), s * W * 0.28)], bx, by, a), 'vein')
        k.end_leaf()
    return k


@recorded
def rubber_plant(seed=0, pot_kind='white'):
    """A rubber plant (Ficus elastica) from above, after an overhead photograph: big oval glossy
    leaves with pointed tips and pale midribs, fanned out in tiers from the centre, the oldest and
    longest outside; a rolled new leaf in its red sheath at the very middle."""
    k = Ink('rubber-plant', 90, 90, 140, C['leaf800'], seed)
    cx = cy = 45
    pot(k, cx, cy, 13, pot_kind, 40)
    prof = [(0, 0.12), (0.15, 0.62), (0.45, 1.0), (0.75, 0.84), (0.93, 0.42), (1, 0)]
    tiers = ((8, 25, 31, 10.5, 12.5, 7, C['rubber800']), (6, 19, 23, 8.5, 10, 4, C['rubber600']),
             (4, 12, 15, 6.5, 7.5, 2, C['rubber400']))
    off = k.rnd.uniform(0, math.tau)
    for t, (count, lmin, lmax, wmin, wmax, r0, fill) in enumerate(tiers):
        for i in range(count):
            a = off + (i + 0.5 * t) * math.tau / count + k.rnd.uniform(-0.18, 0.18)
            L, W = k.rnd.uniform(lmin, lmax), k.rnd.uniform(wmin, wmax)
            bx, by = cx + r0 * math.cos(a), cy + r0 * math.sin(a)
            k.leaf(bx, by)
            k.form(place(profile_leaf(L, W, prof, k.rnd), bx, by, a), fill, relief=1.5, cast=140)
            k.mark(place([(0, 0), (L * 0.5, 0), (L * 0.92, 0)], bx, by, a), 'rib light')
            k.mark(place([(L * 0.22, -W * 0.18), (L * 0.5, -W * 0.24), (L * 0.72, -W * 0.16)],
                         bx, by, a), 'gloss')
            k.end_leaf()
    sheath = place(profile_leaf(9, 3, [(0, 0.5), (0.5, 1), (1, 0)], k.rnd), cx - 2, cy + 1.5, -0.9)
    k.form(sheath, C['sheath'], relief=0.8)
    return k


@recorded
def snake_plant(seed=0, pot_kind='black'):
    """A snake plant: upright blades seen nearly tip-on."""
    k = Ink('snake-plant', 40, 40, 80, C['leaf800'], seed)
    pot(k, 20, 20, 12, pot_kind, 30)
    for i in range(8):
        a = i * math.tau / 8 + k.rnd.uniform(-0.25, 0.25)
        L, W = k.rnd.uniform(14, 21), k.rnd.uniform(5.5, 7)
        lf = place(profile_leaf(L, W, [(0, 0.5), (0.5, 1), (0.85, 0.7), (1, 0)], k.rnd),
                   20 + 2 * math.cos(a), 20 + 2 * math.sin(a), a)
        k.leaf(20 + 2 * math.cos(a), 20 + 2 * math.sin(a))
        k.form(lf, C['leaf600'] if i % 2 else C['leaf800'], relief=0.9, cast=80)
        k.mark(lf, 'edge', closed=True)
        k.end_leaf()
    return k


@recorded
def floor_lamp(seed=0, shade='linen'):
    """A floor lamp from above: a wide shade with the bulb glowing through its top."""
    k = Ink('floor-lamp', 40, 40, 150, C['lin600'], seed)
    k.form(k.circ(20, 20, 18, wob=0.15, n=26), CLOTH[shade][0], relief=3, cast=150)
    k.mark(k.circ(20, 20, 15.5, wob=0.12, n=24), 'detail faint', closed=True)
    k.flat(k.circ(20, 20, 7, wob=0.06, n=16), C['core'])
    k.mark(k.circ(20, 20, 7, wob=0.06, n=16), 'line', closed=True)
    k.light(20, 20, 100)
    return k


@recorded
def beni_rug(seed=0, w=160, h=230):
    """A cream Beni rug: a soft lattice, a border stripe and fringe at both ends."""
    k = Ink('beni-rug', w, h, 1, C['lin600'], seed)
    out = k.rr(0, 0, w, h, 3, wob=0.35)
    k.form(out, C['lin200'], relief=0)
    lat, s = [], 34
    for i in range(-10, 10):
        lat.append([(i * s, 0), (i * s + h, h)])
        lat.append([(i * s + h, 0), (i * s, h)])
    k.clipped(out, lat, 'lattice')
    k.mark(k.rr(8, 8, w - 16, h - 16, 2, wob=0.3), 'detail', closed=True)
    for x in range(4, int(w) - 2, 5):
        for y0, dy in ((0, -4.5), (h, 4.5)):
            k.mark([(x, y0), (x + k.rnd.uniform(-0.8, 0.8), y0 + dy + k.rnd.uniform(-0.6, 0.6))],
                   'fringe')
    return k


@recorded
def stripe_rug(seed=0, w=205, h=230):
    """A flatweave rug in bands: a cream field crossed by cognac and sage stripes with thin cocoa
    lines between, a narrow border, and fringe at both short ends."""
    k = Ink('stripe-rug', w, h, 1, C['lin600'], seed)
    out = k.rr(0, 0, w, h, 2.5, wob=0.3)
    k.form(out, C['lin200'], relief=0)
    bands = []
    y = 18
    for band, depth in ((C['cognac'], 14), (C['sage300'], 9), (C['cognac'], 6), (C['sage300'], 14),
                        (C['cognac'], 6), (C['sage300'], 9), (C['cognac'], 14)):
        bands.append((y, depth, band))
        y += depth + (h - 36 - 72) / 6
    for y0, depth, band in bands:
        k.flat(k.rr(4, y0, w - 8, depth, 0.5, wob=0.25, step=9), band, straight=False)
        for yy in (y0 - 2.2, y0 + depth + 2.2):
            k.mark([(6, yy), (w / 2, yy + k.rnd.uniform(-0.4, 0.4)), (w - 6, yy)], 'detail faint')
    k.mark(k.rr(5, 5, w - 10, h - 10, 2, wob=0.25), 'detail', closed=True)
    for x in range(4, int(w) - 2, 5):
        for y0, dy in ((0, -4.5), (h, 4.5)):
            k.mark([(x, y0), (x + k.rnd.uniform(-0.8, 0.8), y0 + dy + k.rnd.uniform(-0.6, 0.6))],
                   'fringe')
    return k


@recorded
def doormat(seed=0):
    """A coir doormat inside the sliding door: a bristly field with a darker border."""
    k = Ink('doormat', 90, 50, 1, C['oak500'], seed)
    k.form(k.rr(0, 0, 90, 50, 2.5, wob=0.25), C['oak300'], relief=0)
    k.mark(k.rr(5, 5, 80, 40, 1.5, wob=0.2), 'detail', closed=True)
    k.clipped(k.rr(6, 6, 78, 38, 1.5, wob=0.1),
              [[(x, 6), (x + 1.2, 44)] for x in range(8, 84, 3)], 'jute')
    return k


@recorded
def jute_rug(seed=0, d=140):
    """A round jute rug, woven in rings."""
    k = Ink('jute-rug', d, d, 1, C['oak500'], seed)
    c = d / 2
    k.form(k.circ(c, c, c, wob=0.3, n=int(d / 3)), C['oak200'], relief=0)
    for r in range(int(c) - 6, 4, -6):
        k.mark(k.circ(c, c, r, wob=0.35, n=max(10, r // 2)), 'jute', closed=True)
    return k


@recorded
def pouf(seed=0, knit='oat'):
    """A round knit pouf, its panels seamed to a button in the middle."""
    k = Ink('pouf', 50, 50, 40, C['lin600'], seed)
    k.form(k.circ(25, 25, 25, wob=0.35, n=24), {**THROW, 'oat': C['lin400']}[knit], relief=3.2,
           cast=40)
    for i in range(8):
        a = i * math.tau / 8
        k.mark([(25 + 3 * math.cos(a), 25 + 3 * math.sin(a)),
                (25 + 13 * math.cos(a + 0.12), 25 + 13 * math.sin(a + 0.12)),
                (25 + 23.5 * math.cos(a), 25 + 23.5 * math.sin(a))], 'detail')
    k.form(k.circ(25, 25, 2.6, wob=0.05, n=10), C['lin600'], relief=0.5)
    return k


@recorded
def basket(seed=0, throw='cognac'):
    """A seagrass basket with a throw spilling over its rim."""
    k = Ink('basket', 40, 40, 40, C['oak500'], seed)
    k.form(k.circ(20, 20, 20, wob=0.2, n=24), C['oak300'], relief=2, cast=40)
    k.flat(k.circ(20, 20, 16.4, wob=0.15, n=22), C['oak500'])
    k.mark(k.circ(20, 20, 16.4, wob=0.15, n=22), 'line', closed=True)
    for i in range(30):
        a = i * math.tau / 30
        k.mark([(20 + 17.2 * math.cos(a), 20 + 17.2 * math.sin(a)),
                (20 + 19.2 * math.cos(a + 0.06), 20 + 19.2 * math.sin(a + 0.06))], 'weave')
    k.form([(10, 16), (18, 9), (30, 7), (37, 13), (33, 22), (26, 30), (16, 29)], THROW[throw],
           relief=2.2)
    k.mark([(19, 12), (27, 26)], 'detail')
    return k


COAT = {'ginger': (C['ginger'], C['lin50'], '#f2b9a5'), 'grey': ('#c4beb7', C['lin50'], '#eab3a6'),
        'black': ('#4d4542', '#6a605c', '#9a7470'), 'cream': ('#f5e7d1', C['lin50'], '#f2b9a5')}


CAT_PIVOTS = {'tail': (19, 45), 'ear-l': (9.1, 8.6), 'ear-r': (24.9, 8.6)}


@recorded
def cat(seed=0, coat='ginger', part='whole'):
    """A tabby loafing, seen from straight above: a pear-shaped back, the round head in front
    with ears out to the sides and a little muzzle, and a striped tail curled round one haunch.
    The widget draws it in parts so the ears can twitch and the tail can shift: 'tail', 'ear-l',
    'ear-r' and 'body' (everything else); each turns on its pivot in CAT_PIVOTS."""
    k = Ink('cat', 38, 52, 22, C['line'], seed)
    fur, muzzle, pink = COAT[coat]
    stripe = f'stripe {coat}'
    if part in ('whole', 'tail'):
        tail = pen_poly(dense([(18, 46), (26, 49.4), (32.6, 45), (34.4, 36), (32.4, 27.5)], False),
                        5.4, k.rnd, taper=(False, True), wmin=0.3)
        k.form(tail, fur, relief=1, cast=8)
        for p0, p1 in (((26.4, 46.8), (27.4, 51.4)), ((31, 42.2), (35.4, 43.6)),
                       ((32, 35.4), (36.6, 35.2)), ((31.2, 30.4), (35, 29.6))):
            k.mark([p0, p1], stripe)
    ears = {'ear-l': ([(9.4, 4.6), (3.6, 7.4), (8.8, 12.6)], [(8.8, 6.2), (5.6, 7.8), (8.6, 10.6)]),
            'ear-r': ([(24.6, 4.6), (30.4, 7.4), (25.2, 12.6)],
                      [(25.2, 6.2), (28.4, 7.8), (25.4, 10.6)])}
    for name, (ear, inner) in ears.items():
        if part in ('whole', name):
            k.form(ear, fur, relief=0.8)
            k.flat(inner, pink)
    if part not in ('whole', 'body'):
        return k
    pear = [(17, 13), (25, 15), (29, 22), (31.5, 31), (31, 40), (27, 46.5), (17, 49), (7, 46.5),
            (3, 40), (2.5, 31), (5, 22), (9, 15)]
    k.form(pear, fur, relief=2.8, cast=22)
    k.mark([(17, 17), (17.3, 30), (16.8, 44)], stripe)
    for y in range(20, 41, 5):
        for sx in (-1, 1):
            k.mark([(17 + sx * 1.6, y), (17 + sx * 6.5, y + 1.4), (17 + sx * 10.5, y + 3.4)],
                   stripe)
    k.mark([(8, 34), (6.4, 41), (9.2, 46.2)], 'detail faint')
    k.mark([(26, 34), (27.6, 41), (24.8, 46.2)], 'detail faint')
    for sx in (-1, 1):
        for dy, ang in ((-0.6, -0.25), (0.4, 0.0), (1.4, 0.25)):
            x0, y0 = 17 + sx * 3.4, 2.6 + dy
            k.mark([(x0, y0), (x0 + sx * 7 * math.cos(ang), y0 + 7 * math.sin(ang))], 'whisker')
    for cx in (15.1, 18.9):
        k.form(k.circ(cx, 2.6, 2.5, wob=0.05, n=12), muzzle, relief=0.5)
    k.form(k.blob(17, 9.6, 9, 8.4, wob=0.025, n=18), fur, relief=1.8, cast=8)
    for x0, x1 in ((14.2, 15.2), (16.2, 16.6), (18.2, 18.2), (20, 19)):
        k.mark([(x0, 2.6 + abs(x0 - 17) * 0.4), (x1, 12.4)], stripe)
    return k
