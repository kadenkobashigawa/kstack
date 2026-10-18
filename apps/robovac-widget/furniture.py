"""
furniture — the beds, desks, chairs, tables, storage and lights that stand in a room.
"""

from __future__ import annotations

import math

from pen import C, dense, mix, pen_poly, place, profile_leaf
from canvas import Ink, recorded


# ── beds ──────────────────────────────────────────────────────────────────


def pillow(k, x, y, w, h, fill, relief=4.5, sham=False):
    """A plump pillow: piping round it, a dent across the middle, the corners pinched. A sham has
    a flat flange round the plump part, so it shows a second, inner seam."""
    k.form(k.rr(x, y, w, h, 8, wob=0.7, step=6), fill, relief, cast=22)
    if sham:
        k.mark(k.rr(x + 5, y + 5, w - 10, h - 10, 6, wob=0.4, step=6), 'detail', closed=True)
        k.form(k.rr(x + 7, y + 7, w - 14, h - 14, 6, wob=0.5, step=6), fill, relief=2, line=None)
    else:
        k.mark(k.rr(x + 3.2, y + 3.2, w - 6.4, h - 6.4, 6, wob=0.5, step=6), 'detail faint',
               closed=True)
        k.mark([(x + w - 2, y + h * 0.25), (x + w - 2.4, y + h * 0.75)], 'detail faint')
    k.fold([(x + w * 0.22, y + h * 0.3), (x + w * 0.5, y + h * 0.42), (x + w * 0.78, y + h * 0.34)],
           fill, 2.2)
    for cx, cy, dx, dy in ((x + 3, y + 3, 3, 2.4), (x + w - 3, y + 3, -3, 2.4),
                           (x + 3, y + h - 3, 3, -2.4), (x + w - 3, y + h - 3, -3, -2.4)):
        k.mark([(cx, cy), (cx + dx, cy + dy)], 'detail')


def quilting(k, outline, x0, x1, ys):
    """Channel quilting: rows of small stitches across a duvet, kept inside its outline."""
    k.clipped(outline, [[(x0, y), ((x0 + x1) / 2, y + k.rnd.uniform(-1.5, 1.5)), (x1, y)]
                        for y in ys], 'stitch')


def knit(k, outline, x0, x1, y0, y1, step=4.6):
    """A chunky knit: rows of little chevrons, kept inside the throw."""
    rows = []
    y = y0
    while y < y1:
        rows.append([(x, y + (1.4 if n % 2 else -1.4)) for n, x in enumerate(
            [x0 + i * 3.2 for i in range(int((x1 - x0) / 3.2) + 1)])])
        y += step
    k.clipped(outline, rows, 'knit')


WOOD = {
    'walnut': (C['wal300'], C['wal500'], C['wal700']),
    'oak': (C['oak200'], C['oak300'], C['oak500']),
    'black': (C['black'], '#332c29', '#272220'),
}
CLOTH = {'linen': (C['lin50'], C['lin200']), 'oat': (C['lin200'], C['lin50']),
         'sage': (C['sage50'], C['sage100'])}
THROW = {'cognac': C['cognac'], 'grey': C['chr200'], 'sage': C['sage300'], 'oat': C['lin400']}


@recorded
def double_bed(seed=0, frame='walnut', duvet='linen', throw='cognac'):
    """A double bed: two pillows, the duvet turned back past both sides, a throw across the
    foot."""
    _, mid, deep = WOOD[frame]
    body, fold = CLOTH[duvet]
    k = Ink('double-bed', 140, 208, 45, deep, seed)
    k.form(k.rr(0, 0, 140, 208, 5, wob=0.25), mid, relief=2, cast=45)
    k.form(k.rr(-2, 0, 144, 10, 3, wob=0.2), deep, relief=1.2)
    if frame != 'black':
        k.mark([(10, 4.6), (40, 5.2), (70, 4.6)], 'grain')
        k.mark([(84, 5), (110, 5.6), (132, 5)], 'grain')
    k.form(k.rr(4, 9, 132, 195, 6), C['lin50'], relief=1.5)
    k.mark([(8, 58), (30, 60), (50, 57)], 'detail faint')
    pillow(k, 9, 11, 59, 40, C['lin50'], sham=True)
    pillow(k, 72, 11, 59, 40, C['lin50'], sham=True)
    pillow(k, 16, 33, 48, 28, fold)
    pillow(k, 76, 33, 48, 28, fold)
    duvet = k.rr(-5, 74, 150, 138, 11, wob=1.7, step=5)
    k.form(duvet, body, relief=6.5, cast=45)
    quilting(k, duvet, -6, 146, range(96, 205, 18))
    k.mark(k.rr(-1, 78, 142, 130, 9, wob=1.2, step=6), 'detail faint', closed=True)
    k.fold([(12, 98), (30, 106), (50, 109), (68, 103)], body, 3.4)
    k.fold([(30, 168), (44, 160), (60, 166)], body, 2.6)
    k.fold([(96, 92), (108, 100), (124, 98)], body, 2.4)
    k.fold([(84, 114), (100, 126), (118, 133), (134, 129)], body, 3.2)
    k.fold([(20, 128), (27, 139), (30, 151)], body, 2.6)
    k.fold([(58, 122), (73, 136), (82, 151)], body, 2.8)
    k.fold([(104, 140), (112, 150)], body, 2)
    k.form(k.rr(-10, 64, 160, 19, 8, wob=1.3, step=5), fold, relief=3.6, cast=25)
    k.mark([(-6, 70), (40, 70.8), (100, 70.2), (146, 70.6)], 'detail faint')
    k.fold([(6, 76), (36, 78.5), (70, 77)], fold, 1.6)
    if throw:
        t = THROW[throw]
        cover = k.rr(-10, 155, 160, 44, 4, wob=1.5, step=5)
        k.form(cover, t, relief=4.2, cast=22)
        knit(k, cover, -12, 152, 159, 198)
        for y in range(158, 199, 4):
            for x0, dx in ((-10, -4), (150, 4)):
                k.mark([(x0, y), (x0 + dx + k.rnd.uniform(-0.8, 0.8), y + k.rnd.uniform(-0.6, 0.6))],
                       'tassel')
        for x0 in (-10, 137):
            k.form(k.rr(x0, 156.5, 13, 41, 2.5, wob=1.1, step=5), mix(t, '#2a201b', 0.12),
                   relief=0, line=None)
        for x0 in (3, 137):
            k.mark([(x0, 158), (x0 + 1.2, 168), (x0 - 0.8, 182), (x0 + 0.6, 196)], 'detail')
        k.fold([(30, 157), (36, 170), (31, 184), (35, 197)], t, 2.6)
        k.fold([(62, 158), (66, 176), (61, 196)], t, 2.4)
        k.fold([(98, 157), (94, 171), (100, 186), (97, 198)], t, 2.6)
        k.fold([(118, 160), (124, 172)], t, 1.8)
        k.form([(118, 199.5), (149, 199), (148, 184)], mix(t, '#fff8ec', 0.25), relief=0.8)
        for x in (14, 46, 80, 112):
            k.mark([(x, 158 + k.rnd.uniform(-1, 1)), (x + k.rnd.uniform(-1.5, 1.5), 177),
                    (x + k.rnd.uniform(-1, 1), 196 + k.rnd.uniform(-1, 1))], 'detail faint')
    return k


@recorded
def single_bed(seed=0, frame='black', duvet='oat', throw='grey'):
    """A single bed with knobs at its corners, the duvet turned back past both sides, and a knit
    throw."""
    _, mid, deep = WOOD[frame]
    body, fold = CLOTH[duvet]
    k = Ink('single-bed', 95, 205, 40, deep, seed)
    k.form(k.rr(0, 0, 95, 205, 4, wob=0.2), mid if frame != 'black' else C['black'], relief=1,
           cast=40)
    k.form(k.rr(4, 6, 87, 195, 5), C['lin50'], relief=1.5)
    k.form(k.rr(-1, 0, 97, 6, 3, wob=0.15), deep if frame != 'black' else C['black'], relief=0.8)
    for cx, cy in ((2, 3), (93, 3), (2, 202), (93, 202)):
        k.form(k.circ(cx, cy, 2.7, wob=0.05, n=10), C['chr200'] if frame == 'black' else deep,
               relief=0.9)
    pillow(k, 11, 12, 73, 34, C['lin50'], sham=True)
    duvet = k.rr(-4, 56, 103, 152, 9, wob=1.2, step=5)
    k.form(duvet, body, relief=5.5, cast=40)
    quilting(k, duvet, -5, 100, range(76, 150, 18))
    k.fold([(12, 82), (30, 90), (50, 87)], body, 3)
    k.fold([(56, 104), (70, 116), (84, 120)], body, 2.8)
    k.fold([(18, 118), (24, 132)], body, 2.2)
    k.form(k.rr(-8, 49, 111, 15, 6, wob=0.7, step=6), fold, relief=2.6, cast=20)
    if throw:
        t = THROW[throw]
        k.form(k.rr(-6, 150, 107, 40, 8, wob=0.9, step=6), t, relief=3.6, cast=20)
        for x in range(4, 96, 9):
            k.mark([(x + (1.6 if j % 2 else -1.6), 153 + j * 4.4) for j in range(9)], 'detail')
        k.fold([(30, 152), (34, 170), (32, 188)], t, 2.2)
    return k


@recorded
def nightstand(seed=0, wood='walnut'):
    """A nightstand with a linen lamp and a book."""
    top_c, _, deep = WOOD[wood]
    k = Ink('nightstand', 42, 38, 55, deep, seed)
    top = k.rr(0, 0, 42, 38, 4, wob=0.25)
    k.form(top, top_c, relief=2.2, cast=55)
    if wood != 'black':
        k.mark([(4, 8), (10, 8.6), (16, 8)], 'grain')
        k.mark([(26, 31), (33, 31.6), (38, 31)], 'grain')
    k.form(k.rr(4, 24, 13, 10, 1.2, wob=0.1), C['cognac'] if wood != 'oak' else C['sage300'],
           relief=0.8, cast=4)
    k.mark([(6, 31.5), (15, 31.5)], 'detail')
    table_lamp(k, 25, 16, 10.5, 25, top)
    return k


def table_lamp(k, cx, cy, r, cast, surface=None):
    k.light(cx, cy, r * 6.5, surface)
    k.form(k.circ(cx, cy, r, wob=0.15), C['lin50'], relief=2.4, cast=cast)
    k.flat(k.circ(cx, cy, r * 0.42, wob=0.08, n=14), C['core'])
    k.mark(k.circ(cx, cy, r * 0.42, wob=0.08, n=14), 'line', closed=True)


# ── desks and chairs ──────────────────────────────────────────────────────


def pothos(k, px, py, trail):
    """A small white pot with heart leaves trailing along the points in trail."""
    k.form(k.circ(px, py, 6, wob=0.1, n=12), C['lin50'], relief=1, cast=12)
    k.flat(k.circ(px, py, 4.6, wob=0.05, n=12), C['wal700'])
    k.mark([(px, py)] + trail, 'vine')
    for i, (vx, vy) in enumerate(trail + [(px - 4, py + 5), (px + 3, py - 5)]):
        lf = place(profile_leaf(7.5, 6.8, [(0, 0.3), (0.3, 0.95), (0.7, 0.7), (1, 0)], k.rnd),
                   vx, vy, k.rnd.uniform(0, math.tau))
        k.form(lf, C['leaf400'] if i % 2 else C['leaf200'], relief=0.7)


def succulent(k, x, y):
    """A rosette succulent in a chrome bowl."""
    k.form(k.circ(x, y, 6.5, wob=0.1, n=14), C['chr200'], relief=1, cast=8)
    for i in range(7):
        a = i * math.tau / 7
        lf = place(profile_leaf(5, 3.4, [(0, 0.2), (0.4, 1), (1, 0)], k.rnd),
                   x + 0.6 * math.cos(a), y + 0.6 * math.sin(a), a)
        k.form(lf, C['leaf200'] if i % 2 else C['olive'], relief=0.4, line='line thin')


def phone(k, x, y, ang):
    k.form(place(k.rr(-3.8, -7.5, 7.6, 15, 1.8, wob=0.02, step=2), x, y, ang), C['black'],
           relief=0.5, cast=2)
    k.mark(place([(-2, -5), (1.4, -1.6)], x, y, ang), 'glint')


def mug(k, x, y, color=None):
    k.form(k.circ(x, y, 4.6, wob=0.1, n=12), color or C['lin50'], relief=1, cast=10)
    k.flat(k.circ(x, y, 3, wob=0.05, n=12), C['wal700'])


@recorded
def desk(seed=0, wood='walnut', setup='laptop'):
    """A desk set up one of three ways. Laptop: a black desk lamp, the open laptop, a phone, a mug,
    a notebook and a trailing pothos. Dual: two monitors turned in, speakers, keyboard and mouse on
    a felt pad, a phone and a mug. Writing: a linen lamp, an open notebook and pen, a stack of
    books, tea on a saucer and a succulent."""
    top_c, _, deep = WOOD[wood]
    W, D = (150, 65) if setup == 'dual' else (120, 60)
    k = Ink('desk', W, D, 75, deep, seed)
    top = k.rr(0, 0, W, D, 4, wob=0.25)
    k.form(top, top_c, relief=2.2, cast=75)
    for gx, gy, gl in ((W - 36, D - 14, 24), (30, D - 10, 16), (W - 24, 6, 14)):
        k.mark([(gx, gy), (gx + gl / 2, gy + k.rnd.uniform(-1, 1)), (gx + gl, gy)], 'grain')
    if setup == 'laptop':
        k.light(30, 30, 52, top)
        k.form(k.rr(44, 18, 34, 23, 2.5, wob=0.12), C['chr200'], relief=1.2, cast=4)
        k.form(k.rr(43.5, 14.5, 35, 3.6, 1.5, wob=0.08), C['black'], relief=0.5)
        for yy in (22, 26, 30):
            k.mark([(48, yy), (74, yy)], 'detail faint')
        k.form(k.rr(56, 33.5, 10, 5.5, 1.2, wob=0.05), C['chr200'], relief=0.6)
        mug(k, 92, 34)
        phone(k, 86, 18, 0.25)
        k.form(k.rr(100, 10, 15, 21, 1.5, wob=0.12), C['lin200'], relief=0.8, cast=2)
        k.mark([(103, 15), (112, 28)], 'detail')
        k.form(k.circ(13, 12, 5.2, wob=0.1, n=12), C['black'], relief=1, cast=4)
        k.mark([(13, 12), (25, 24)], 'arm')
        k.form(k.circ(27, 26, 5.6, wob=0.1, n=12), C['chr200'], relief=1.4, cast=30)
        k.flat(k.circ(25.6, 24.6, 1.1, wob=0, n=8), C['lin50'])
        pothos(k, 10, 48, [(16, 54), (14, 61), (22, 67), (31, 64), (38, 69)])
    elif setup == 'dual':
        k.light(75, 16, 50, top)
        for mx, ang in ((47, -0.16), (103, 0.16)):
            k.form(place(k.rr(-7, -1, 14, 9, 3, wob=0.05), mx, 18, ang), C['chr200'], relief=0.7,
                   cast=3)
            k.form(place(k.rr(-27, -2.5, 54, 5, 2, wob=0.06), mx, 12, ang), C['black'],
                   relief=0.6, cast=40)
            k.mark(place([(-24, -1.2), (-6, -1.2)], mx, 12, ang), 'glint')
        for sx in (12, W - 12):
            k.form(k.rr(sx - 6.5, 6, 13, 15, 2.5, wob=0.08), C['black'], relief=0.8, cast=18)
            k.form(k.circ(sx, 15.5, 3.6, wob=0.04, n=12), C['chr400'], relief=0.6)
            k.flat(k.circ(sx, 9.6, 1.4, wob=0, n=8), C['chr200'])
        k.form(k.rr(48, 34, 50, 14, 2, wob=0.1), C['lin200'], relief=0.8, cast=2)
        for row in range(3):
            k.mark([(51, 37.5 + row * 3.4), (95, 37.5 + row * 3.4)], 'dots')
        k.form(k.rr(104, 31, 24, 19, 3, wob=0.1), C['chr400'], relief=0, line='line thin')
        k.form(k.blob(116, 40.5, 3, 4.6, wob=0.02, n=10), C['lin50'], relief=0.6)
        phone(k, 136, 44, -0.2)
        mug(k, 26, 46, C['black'])
    else:
        table_lamp(k, W - 18, 16, 10, 30, top)
        k.form(k.rr(40, 20, 40, 26, 1.5, wob=0.12), C['lin50'], relief=0.9, cast=2)
        k.mark([(60, 20.5), (60, 45.5)], 'detail')
        for yy in (25, 29, 33, 37, 41):
            k.mark([(43, yy), (57, yy)], 'detail faint')
            k.mark([(63, yy), (77 - (yy == 41) * 5, yy)], 'detail faint')
        k.form(place(k.rr(0, -0.9, 15, 1.8, 0.9, wob=0.02, step=2), 84, 26, 0.6), C['black'],
               relief=0.4, cast=3)
        for n, (bc, dx) in enumerate(((C['black'], 0), (C['cognac'], 1.6), (C['sage300'], 0.4))):
            k.form(k.rr(8 + dx, 24 + n * 1.4, 22 - n * 1.6, 28 - n * 2, 1.4, wob=0.1), bc,
                   relief=0.7, cast=4)
        k.form(k.circ(96, 42, 7.5, wob=0.08, n=16), C['lin50'], relief=0.8, cast=2)
        mug(k, 96, 42)
        succulent(k, 15, 12)
    return k


@recorded
def white_desk(seed=0):
    """A white desk: a monitor on a chrome foot with a succulent beside it, a keyboard, a mouse, a
    black mug, a phone and books."""
    k = Ink('white-desk', 110, 55, 75, C['chr700'], seed)
    k.form(k.rr(0, 0, 110, 55, 3, wob=0.2), C['lin50'], relief=1.8, cast=75)
    k.form(k.rr(47, 12, 16, 9, 3, wob=0.08), C['chr200'], relief=0.8, cast=3)
    k.form(k.rr(25, 7, 60, 4.6, 2, wob=0.08), C['black'], relief=0.6, cast=40)
    k.mark([(28, 8.4), (46, 8.4)], 'glint')
    k.form(k.rr(33, 27, 42, 13, 2, wob=0.1), C['lin200'], relief=0.8, cast=2)
    for row in range(3):
        k.mark([(36, 30.5 + row * 3.2), (72, 30.5 + row * 3.2)], 'dots')
    k.form(k.blob(83, 34, 3, 4.6, wob=0.02, n=10), C['lin50'], relief=0.6)
    mug(k, 95, 29, C['black'])
    phone(k, 100, 44, -0.3)
    k.form(k.rr(5, 9, 18, 25, 1.5, wob=0.12), C['cognac'], relief=1, cast=3)
    k.form(k.rr(6.5, 11, 16, 21, 1.5, wob=0.12), C['lin200'], relief=0.8)
    succulent(k, 99, 12)
    return k


SEAT = {'cognac': C['cognac'], 'linen': C['lin200'], 'sage': C['sage300']}


@recorded
def desk_chair(seed=0, seat='cognac'):
    """A desk chair, desk above it: a cushioned seat, soft-black back bar, legs peeking out."""
    k = Ink('desk-chair', 46, 48, 45, C['wal700'], seed)
    for cx, cy in ((3, 3), (43, 3), (3, 38), (43, 38)):
        k.flat(k.circ(cx, cy, 2.1, wob=0, n=8), C['black'])
    k.form(k.rr(2, 0, 42, 40, 11, wob=0.35), SEAT[seat], relief=3, cast=45)
    k.fold([(14, 14), (23, 19), (32, 14)], SEAT[seat], 1.6)
    outer = [(0, 33), (8, 42), (23, 47), (38, 42), (46, 33)]
    inner = [(42, 31), (34, 37.5), (23, 41), (12, 37.5), (4, 31)]
    k.form(outer + inner, C['black'], relief=1.1)
    return k


@recorded
def bar_stool(seed=0, seat='cognac'):
    """A round bar stool from above, set at an island's back edge: a cushioned seat with a
    button in its middle, a thin chrome footrest ring under it and four black legs splaying out
    past the seat."""
    k = Ink('stool', 44, 44, 75, C['wal700'], seed)
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        k.flat(k.circ(22 + 19.5 * math.cos(a), 22 + 19.5 * math.sin(a), 1.9, wob=0, n=8),
               C['black'])
    k.mark(k.circ(22, 22, 18, wob=0.02, n=28), 'chrome-ring', closed=True)
    k.form(k.circ(22, 22, 16, wob=0.08, n=26), SEAT[seat], relief=3, cast=75)
    k.mark(k.circ(22, 22, 11.5, wob=0.05, n=22), 'detail faint', closed=True)
    k.flat(k.circ(22, 22, 1.3, wob=0, n=8), C['line'])
    return k


@recorded
def dining_chair(seed=0, wood='walnut'):
    """A bentwood chair with a cane seat, table above it."""
    top_c, mid, deep = WOOD[wood]
    k = Ink('dining-chair', 44, 44, 45, deep, seed)
    for cx, cy in ((6, 4), (38, 4), (6, 34), (38, 34)):
        k.flat(k.circ(cx, cy, 2, wob=0, n=8), deep)
    seat = k.blob(22, 18, 18.5, 17, wob=0.015, n=22)
    k.form(seat, top_c, relief=2, cast=45)
    cane = k.blob(22, 18, 14.5, 13, wob=0.01, n=20)
    k.form(cane, C['oak100'], relief=1)
    lat = []
    for i in range(-6, 7):
        lat.append([(8 + i * 4.5, 4), (36 + i * 4.5, 32)])
        lat.append([(36 + i * 4.5, 4), (8 + i * 4.5, 32)])
    k.clipped(cane, lat, 'cane')
    outer = [(1, 30), (9, 39), (22, 43), (35, 39), (43, 30)]
    inner = [(40, 29), (33, 35), (22, 38), (11, 35), (4, 29)]
    k.form(outer + inner, mid, relief=1)
    return k


# ── tables ────────────────────────────────────────────────────────────────


@recorded
def round_table(seed=0, wood='oak', setup='flowers'):
    """A round dining table, set with flowers, a bowl of oranges and a mug, or with tea: a white
    pot, two cups on saucers and an open book."""
    top_c, _, deep = WOOD[wood]
    k = Ink('round-table', 100, 100, 75, deep, seed)
    k.form(k.circ(50, 50, 50, wob=0.25, n=36), top_c, relief=2, cast=75)
    k.mark(k.circ(50, 50, 45.5, wob=0.2, n=30), 'detail faint', closed=True)
    for gx, gy, gl in ((22, 40, 18), (58, 26, 20), (60, 76, 16), (30, 70, 12)):
        k.mark([(gx, gy), (gx + gl / 2, gy + k.rnd.uniform(-1.5, 1.5)), (gx + gl, gy)], 'grain')
    if setup == 'flowers':
        k.form(k.circ(28, 64, 10.5, wob=0.12, n=18), C['chr200'], relief=1.6, cast=8)
        for ox, oy in ((25, 61), (32, 63), (27, 68.5)):
            k.form(k.circ(ox, oy, 3.7, wob=0.08, n=12), C['cognac'], relief=1)
            k.flat(k.circ(ox - 1, oy - 1.6, 0.9, wob=0, n=6), C['leaf400'])
        mug(k, 73, 70)
        flowers(k, 52, 44)
    else:
        k.form([(41, 51), (35, 47.5), (34, 52), (39, 55)], C['lin50'], relief=0.4)
        k.form(k.circ(48, 50, 8, wob=0.08, n=18), C['lin50'], relief=1.6, cast=18)
        k.form(k.blob(57.5, 50, 2.4, 4.2, wob=0.02, n=10), C['lin50'], relief=0.4)
        k.form(k.circ(48, 50, 2.6, wob=0.04, n=10), C['lin200'], relief=0.5)
        for cx, cy in ((30, 32), (70, 70)):
            k.form(k.circ(cx, cy, 6.4, wob=0.06, n=16), C['lin50'], relief=0.6, cast=2)
            mug(k, cx, cy)
        k.form(k.rr(58, 22, 30, 21, 1.4, wob=0.12), C['lin50'], relief=0.8, cast=3)
        k.mark([(73, 22.4), (73, 42.6)], 'detail')
        for yy in (26, 30, 34, 38):
            k.mark([(60.5, yy), (71, yy)], 'detail faint')
            k.mark([(75, yy), (86 - (yy == 38) * 4, yy)], 'detail faint')
    return k


def flowers(k, cx, cy):
    k.form(k.circ(cx, cy, 6.2, wob=0.1, n=14), C['lin50'], relief=1.4, cast=30)
    for i in range(6):
        a = i * math.tau / 6 + 0.4
        lf = place(profile_leaf(9, 4, [(0, 0.2), (0.4, 1), (1, 0)], k.rnd), cx, cy, a + 0.5)
        k.form(lf, C['leaf400'], relief=0.6, line='line thin')
    for i in range(5):
        a = i * math.tau / 5
        bx, by = cx + 7 * math.cos(a), cy + 7 * math.sin(a)
        k.form(k.blob(bx, by, 3.8, 3.6, wob=0.12, n=10), C['lin50'], relief=0.9)
        k.flat(k.circ(bx, by, 1.3, wob=0, n=8), C['cognac'])


@recorded
def coffee_table(seed=0, wood='walnut', setup='notepad'):
    """An oval coffee table, with a notepad on a book and a pen, or with a stack of books, a small
    plant and a mug."""
    top_c, _, deep = WOOD[wood]
    k = Ink('coffee-table', 110, 60, 40, deep, seed)
    k.form(k.blob(55, 30, 55, 30, wob=0.008, n=32), top_c, relief=2.2, cast=40)
    for gx, gy, gl in ((70, 12, 22), (18, 40, 14), (76, 46, 16)):
        k.mark([(gx, gy), (gx + gl / 2, gy + k.rnd.uniform(-1, 1)), (gx + gl, gy)], 'grain')
    if setup == 'notepad':
        k.form(k.rr(30, 15, 26, 31, 2, wob=0.12), C['cognac'], relief=1, cast=4)
        k.form(k.rr(33, 17, 21, 26, 1.5, wob=0.12), C['lin200'], relief=0.9, cast=2)
        for yy in (23, 27, 31, 35):
            k.mark([(36, yy), (51 - (yy == 35) * 6, yy)], 'detail faint')
        pen_body = place(k.rr(0, -0.9, 15, 1.8, 0.9, wob=0.02, step=2), 61, 22, 0.45)
        k.form(pen_body, C['black'], relief=0.4, cast=3)
        k.flat(place(k.rr(13.2, -0.7, 2.6, 1.4, 0.6, wob=0, step=2), 61, 22, 0.45), C['chr200'])
    else:
        for n, (bc, dx) in enumerate(((C['sage300'], 0), (C['lin200'], 2), (C['cognac'], 0.8))):
            k.form(place(k.rr(-13 + dx, -9 + n * 1.2, 26 - n * 2, 18 - n * 1.6, 1.4, wob=0.1),
                         36, 30, 0.12), bc, relief=0.8, cast=4)
        k.form(k.circ(74, 22, 6, wob=0.1, n=14), C['lin50'], relief=1, cast=8)
        for n in range(9):
            a = n * math.tau / 9 + k.rnd.uniform(-0.2, 0.2)
            dd = k.rnd.uniform(3.5, 7)
            lx, ly = 74 + dd * math.cos(a), 22 + dd * math.sin(a)
            k.form(k.circ(lx, ly, k.rnd.uniform(2.2, 3.2), wob=0.1, n=10),
                   C['leaf400'] if n % 2 else C['leaf600'], relief=0.6)
        mug(k, 80, 40, C['sage300'])
    return k


@recorded
def side_table(seed=0, wood='black', top='pilea'):
    """A round side table, a chrome rim on the black one, with a pilea or a lamp on it."""
    top_c, _, deep = WOOD[wood]
    k = Ink('side-table', 46, 46, 55, deep, seed)
    surface = k.circ(23, 23, 23, wob=0.12, n=26)
    k.form(surface, top_c, relief=1.2, cast=55)
    if wood == 'black':
        k.mark(k.circ(23, 23, 21.4, wob=0.08, n=26), 'chrome-ring', closed=True)
    if top == 'lamp':
        table_lamp(k, 23, 23, 11, 25, surface)
        return k
    k.form(k.circ(23, 23, 6.5, wob=0.08, n=14), C['lin50'], relief=1, cast=10)
    k.flat(k.circ(23, 23, 5, wob=0.05, n=12), C['wal700'])
    for i in range(9):
        a = i * math.tau / 9 + k.rnd.uniform(-0.2, 0.2)
        dd = k.rnd.uniform(6.5, 10.5)
        lx, ly = 23 + dd * math.cos(a), 23 + dd * math.sin(a)
        k.mark([(23, 23), (lx, ly)], 'vine')
        k.form(k.circ(lx, ly, k.rnd.uniform(3, 4.4), wob=0.12, n=12),
               C['leaf400'] if i % 2 else C['leaf600'], relief=0.8, cast=20)
        k.flat(k.circ(lx, ly, 0.5, wob=0, n=6), C['leaf800'])
    return k


# ── along the walls ───────────────────────────────────────────────────────


SOFA = {'oat': (C['lin400'], C['lin200']), 'sage': (C['sage300'], C['sage50']),
        'linen': (C['lin200'], C['lin50']), 'cognac': (C['cognac'], '#e8b878')}


def throw_pillow(k, cx, cy, ang, color, size=24):
    """A square throw pillow leaning on a couch: plump, corners pinched, piping round it."""
    h = size / 2
    k.form(place(k.rr(-h, -h, size, size, 6, wob=0.35, step=4), cx, cy, ang), color, relief=2.6,
           cast=10)
    k.mark(place(k.rr(-h + 2.6, -h + 2.6, size - 5.2, size - 5.2, 4, wob=0.25, step=4), cx, cy, ang),
           'detail faint', closed=True)
    k.fold(place([(-h * 0.5, -h * 0.1), (0, h * 0.15), (h * 0.5, -h * 0.1)], cx, cy, ang), color, 1.4)


def couch_back(k, w, body):
    """The back cushion: the highest part of a couch, so drawn last, across its full width."""
    k.form(k.rr(0, 0, w, 24, 11, wob=0.7, step=6), body, relief=3.2, cast=30)
    k.fold([(w * 0.3, 14), (w * 0.5, 17), (w * 0.7, 14)], body, 1.6)


@recorded
def sofa(seed=0, fabric='oat', pillows='cognac', seats=3):
    """A sofa of two or three seats, back against the wall: the frame, the arms, the seat
    cushions packed edge to edge, two throw pillows, and the back cushion over everything."""
    body, cushion = SOFA[fabric]
    w = 40 + 57 * seats
    k = Ink('sofa' if seats == 3 else 'loveseat', w, 90, 80, C['lin600'], seed)
    k.form(k.rr(0, 4, w, 86, 14, wob=0.6, step=6), body, relief=2.4, cast=80)
    for x in (0, w - 20):
        k.form(k.rr(x, 10, 20, 80, 10, wob=0.6, step=6), body, relief=2.4)
    cw = (w - 40) / seats
    for n in range(seats):
        x = 20 + n * cw
        k.form(k.rr(x - 0.5, 20, cw + 1, 64, 8, wob=0.7, step=6), cushion, relief=3.4)
        k.fold([(x + cw * 0.22, 44), (x + cw * 0.5, 50), (x + cw * 0.78, 45)], cushion, 1.8)
    for cx, ang in ((40, 0.45), (w - 40, -0.4)):
        throw_pillow(k, cx, 38, ang, THROW[pillows], 34)
    couch_back(k, w, body)
    return k


@recorded
def sectional(seed=0, fabric='linen', pillows='sage'):
    """A corner sofa, back against the wall, with a chaise running out on the right: two seat
    cushions and the long chaise cushion edge to edge, pillows, and the back cushion on top."""
    body, cushion = SOFA[fabric]
    k = Ink('sectional', 240, 160, 80, C['lin600'], seed)
    outline = [(14, 4), (226, 4), (240, 18), (240, 146), (226, 160), (172, 160), (160, 148),
               (160, 90), (14, 90), (0, 76), (0, 18)]
    k.form(outline, body, relief=2.4, cast=80)
    k.form(k.rr(0, 10, 20, 80, 10, wob=0.6, step=6), body, relief=2.4)
    k.form(k.rr(220, 10, 20, 150, 10, wob=0.6, step=6), body, relief=2.4)
    for x in (20, 90):
        k.form(k.rr(x - 0.5, 20, 71, 64, 8, wob=0.7, step=6), cushion, relief=3.4)
        k.fold([(x + 15, 44), (x + 35, 50), (x + 55, 45)], cushion, 1.8)
    k.form(k.rr(160, 20, 61, 136, 9, wob=0.8, step=6), cushion, relief=3.6)
    k.fold([(172, 80), (190, 92), (208, 84)], cushion, 2)
    k.fold([(176, 128), (192, 136)], cushion, 1.6)
    for cx, cy, ang in ((40, 38, 0.45), (200, 40, -0.4)):
        throw_pillow(k, cx, cy, ang, THROW[pillows], 34)
    couch_back(k, 240, body)
    return k


@recorded
def armchair(seed=0, fabric='cognac'):
    """A deep armchair, back against the wall: arms, one fat seat cushion, a small pillow, and
    the back cushion on top."""
    body, cushion = SOFA[fabric]
    k = Ink('armchair', 90, 85, 80, C['lin600'], seed)
    k.form(k.rr(0, 4, 90, 81, 14, wob=0.6, step=6), body, relief=2.4, cast=80)
    for x in (0, 70):
        k.form(k.rr(x, 10, 20, 75, 10, wob=0.6, step=6), body, relief=2.4)
    k.form(k.rr(19.5, 20, 51, 60, 9, wob=0.7, step=6), cushion, relief=3.4)
    k.fold([(30, 44), (45, 50), (60, 45)], cushion, 1.8)
    throw_pillow(k, 45, 36, 0.08, C['lin200'], 28)
    couch_back(k, 90, body)
    return k


@recorded
def wardrobe(seed=0, wood='walnut'):
    """A tall wardrobe, back against the wall: its top seen from above, a bevelled edge, the grain,
    and the lip of its doors along the front."""
    top_c, mid, deep = WOOD[wood]
    k = Ink('wardrobe', 100, 60, 120, deep, seed)
    k.form(k.rr(0, 0, 100, 60, 3, wob=0.2), top_c, relief=2.6, cast=120)
    k.mark(k.rr(4, 4, 92, 50, 2, wob=0.15), 'detail faint', closed=True)
    k.form(k.rr(1, 54, 98, 6, 1.5, wob=0.1), mid, relief=0.6)
    k.mark([(50, 54.5), (50, 59.5)], 'detail')
    for gx, gy, gl in ((12, 16, 30), (52, 34, 28), (20, 44, 18)):
        k.mark([(gx, gy), (gx + gl / 2, gy + k.rnd.uniform(-1, 1)), (gx + gl, gy)], 'grain')
    return k


@recorded
def dresser(seed=0, wood='walnut'):
    """A low dresser, back against the wall, with a lamp, a framed photo, a succulent and a dish
    on top."""
    top_c, _, deep = WOOD[wood]
    k = Ink('dresser', 100, 45, 80, deep, seed)
    top = k.rr(0, 0, 100, 45, 3, wob=0.2)
    k.form(top, top_c, relief=2.2, cast=80)
    k.mark([(40, 34), (52, 34.6), (64, 34)], 'grain')
    table_lamp(k, 16, 16, 9.5, 30, top)
    k.form(place(k.rr(-9, -1.6, 18, 3.2, 0.8, wob=0.02, step=2), 46, 10, 0.08), C['black'],
           relief=0.4, cast=20)
    k.form(place(k.rr(-6, 0, 12, 6, 0.8, wob=0.02, step=2), 46, 11, 0.08), C['lin200'], relief=0)
    succulent(k, 84, 14)
    k.form(k.circ(70, 30, 5.4, wob=0.08, n=14), C['lin50'], relief=0.8, cast=2)
    k.flat(k.circ(68.6, 29.4, 1.2, wob=0, n=8), C['cognac'])
    k.flat(k.circ(71.6, 31.2, 1, wob=0, n=8), C['chr200'])
    return k


@recorded
def bookshelf(seed=0, wood='walnut'):
    """A tall bookshelf, back against the wall: its top board, with two books lying flat and a
    pothos trailing over the front."""
    top_c, _, deep = WOOD[wood]
    k = Ink('bookshelf', 90, 32, 180, deep, seed)
    k.form(k.rr(0, 0, 90, 32, 2, wob=0.15), top_c, relief=2, cast=120)
    k.mark([(30, 20), (44, 20.6), (58, 20)], 'grain')
    k.form(k.rr(48, 6, 24, 18, 1.2, wob=0.1), C['sage300'], relief=0.7, cast=3)
    k.form(k.rr(50, 8, 21, 15, 1.2, wob=0.1), C['lin50'], relief=0.5)
    pothos(k, 16, 14, [(20, 24), (17, 32), (23, 38), (30, 34)])
    return k


@recorded
def tv_console(seed=0, wood='oak'):
    """A low TV console, back against the wall: a slim television on its stand, a small speaker,
    a stack of books and a little plant."""
    top_c, _, deep = WOOD[wood]
    k = Ink('tv-console', 160, 42, 50, deep, seed)
    top = k.rr(0, 0, 160, 42, 3, wob=0.2)
    k.form(top, top_c, relief=2, cast=50)
    k.mark([(110, 32), (124, 32.6), (138, 32)], 'grain')
    k.form(k.rr(62, 12, 36, 12, 3, wob=0.05), C['chr200'], relief=0.6, cast=3)
    k.form(k.rr(30, 6, 100, 4.4, 1.6, wob=0.05), C['black'], relief=0.5, cast=40)
    k.mark([(34, 7.2), (58, 7.2)], 'glint')
    k.form(k.rr(138, 10, 12, 14, 2.5, wob=0.06), C['black'], relief=0.6, cast=12)
    k.form(k.circ(144, 18, 3.2, wob=0.04, n=12), C['chr400'], relief=0.4)
    for n, (bc, dx) in enumerate(((C['cognac'], 0), (C['lin200'], 1.4))):
        k.form(k.rr(10 + dx, 18 + n * 1.2, 20 - n * 2, 16 - n * 1.6, 1.2, wob=0.08), bc,
               relief=0.6, cast=3)
    succulent(k, 20, 9)
    return k


def faucet(k, x, y, reach=25, swing=0.6):
    """A gooseneck kitchen faucet behind the sink, after the two photos the user chose: a round
    chrome base, a column that rises, bends over and runs out above the bowl, and drops to a
    short spout, with a lever handle on the column's side. Height is drawn a little up the page,
    the way an illustrator shows it from above, and the arm swings toward the bowl's middle, so
    the neck reads as a curve."""
    lift, H, h, r1, r2 = 0.42, 32, 21, 6.5, 3.5
    ux, uy = -math.sin(swing), math.cos(swing)
    def see(a, z, side=0.0):
        return (x + a * ux + side * uy, y + a * uy - side * ux - lift * z)
    neck = [(0, z) for z in (0, 8, 16, H - r1)]
    neck += [(r1 - r1 * math.cos(t), H - r1 + r1 * math.sin(t))
             for t in (math.pi / 2 * i / 6 for i in range(1, 7))]
    neck += [(reach - r2 + r2 * math.sin(t), H - r2 + r2 * math.cos(t))
             for t in (math.pi / 2 * i / 5 for i in range(0, 6))]
    neck += [(reach, h)]
    k.form(k.circ(x, y, 2.9, wob=0.03, n=14), C['chr200'], relief=0.6, cast=30)
    tube = pen_poly(dense([see(a, z) for a, z in neck], False, 0.5), 2.5, k.rnd,
                    taper=(False, False), wmin=1)
    k.form(tube, C['chr200'], relief=0.5, cast=34)
    k.form(k.circ(*see(reach, h), 1.45, wob=0.02, n=10), C['chr200'], relief=0.4)

    #the lever, standing out from the column's right side, tilted up and a little back...
    lever = pen_poly(dense([see(0, 10, 1.2), see(-1, 11.5, 4.5), see(-2, 13, 7.5)], False, 0.5),
                     2.0, k.rnd, taper=(False, False), wmin=1)
    k.form(lever, C['chr200'], relief=0.4, cast=14)


def herb_pot(k, x, y, greens):
    """A little white pot of basil, its leaves fanned round the stem."""
    k.form(k.circ(x, y, 5.6, wob=0.06, n=14), C['lin50'], relief=0.8, cast=16)
    k.flat(k.circ(x, y, 4.4, wob=0.05, n=12), C['wal700'])
    for j in range(9):
        a = j * math.tau / 9 + k.rnd.uniform(-0.25, 0.25)
        lf = place(profile_leaf(k.rnd.uniform(5.6, 7), 4, [(0, 0.3), (0.4, 1), (1, 0)], k.rnd),
                   x + math.cos(a), y + math.sin(a), a)
        k.form(lf, greens[j % 2], relief=0.3, line='line thin')


@recorded
def island(seed=0, length=240):
    """A marble kitchen island seen from above, its cook's side at the bottom, after the two
    photos the user chose: a white top veined in grey; one steel sink whose apron front meets the
    cook's edge, its gooseneck faucet behind the bowl; a black-glass induction hob a few
    centimetres from the same edge, its rings drawn faintly; and between them three pots of
    basil and a board with an avocado."""
    L, D = length, 100
    k = Ink('island', L, D, 92, C['chr700'], seed)
    k.form(k.rr(0, 0, L, D, 5, wob=0.15), C['marble'], relief=2.4, cast=92)
    for _ in range(int(L / 40)):
        y = k.rnd.uniform(14, 86)
        x = k.rnd.uniform(6, 60)
        pts = [(x, y)]
        while pts[-1][0] < L - 8 and len(pts) < 9:
            px, py = pts[-1]
            pts.append((min(L - 6, px + k.rnd.uniform(22, 40)),
                        max(6, min(94, py + k.rnd.uniform(-12, 12)))))
        k.mark(pts, 'marble-vein')

    #the sink: one steel bowl set into the stone, its apron front flush with the cook's edge...
    sx, sw, sd, r = 16, (76 if L >= 240 else 60), 48, 3.5
    top = D - sd
    bowl = [(sx, D - j * 1.5) for j in range(int((sd - r) / 1.5))]
    bowl += [(sx + r - r * math.cos(t), top + r - r * math.sin(t))
             for t in (math.pi / 2 * i / 6 for i in range(7))]
    bowl += [(sx + r + j * 1.5, top) for j in range(1, int((sw - 2 * r) / 1.5))]
    bowl += [(sx + sw - r + r * math.sin(t), top + r - r * math.cos(t))
             for t in (math.pi / 2 * i / 6 for i in range(7))]
    bowl += [(sx + sw, top + r + j * 1.5) for j in range(1, int((sd - r) / 1.5) + 1)]
    k.form(bowl, C['chr400'], relief=-2.4, line='line thin', straight=True)
    k.mark(k.rr(sx + 5, top + 5, sw - 10, sd - 9, 5, wob=0.02, step=3), 'detail faint',
           closed=True)
    k.form(k.rr(sx, D - 2.2, sw, 2.2, 0.6, wob=0.02, step=3), C['chr200'], relief=0.3,
           line='line thin')
    k.flat(k.circ(sx + sw * 0.5, top + 26, 2.1, wob=0, n=10), C['chr700'])
    k.mark(k.circ(sx + sw * 0.5, top + 26, 3.2, wob=0, n=12), 'detail faint', closed=True)
    faucet(k, sx + sw * 0.66, top - 5)

    #the hob, four centimetres in from the cook's edge, with its touch controls at the front...
    hw, hd = (76 if L >= 240 else 60), 52
    hx, hy = L - 16 - hw, D - 4 - hd
    k.form(k.rr(hx, hy, hw, hd, 3, wob=0.04), C['black'], relief=0.5, cast=1)
    left, right = hx + hw * 0.25, hx + hw * 0.75
    for cx, cy, r in ((left, hy + 16, 11), (left, hy + 39, 8), (right, hy + 14, 8),
                      (right, hy + 36.5, 11)):
        k.mark(k.circ(cx, cy, r, wob=0.05, n=18), 'hob-ring', closed=True)
    for dx in range(4):
        k.flat(k.circ(hx + hw / 2 - 6.75 + dx * 4.5, hy + hd - 4, 0.8, wob=0, n=6), C['chr400'])

    #between them, three pots of basil along the back and a board with an avocado...
    mid = (sx + sw + hx) / 2
    for n, gx in enumerate((mid - 14, mid, mid + 14)):
        herb_pot(k, gx, 13 + (n % 2) * 2, (C['leaf400'], C['leaf200']) if n != 1 else
                 (C['leaf200'], C['leaf400']))
    bx, by = mid - 15, D - 40
    k.form(k.rr(bx, by, 30, 19, 3, wob=0.05), C['oak200'], relief=0.8, cast=6)
    k.mark([(bx + 4, by + 9), (bx + 15, by + 9.4), (bx + 26, by + 9)], 'grain')
    for n, ax in enumerate((bx + 9, bx + 20)):
        half = k.blob(ax, by + 9.5, 4.4, 5.8, wob=0.03, n=14, rot=0.3 if n else -0.3)
        k.form(half, C['olive600'], relief=0.6)
        k.flat(k.blob(ax, by + 9.5, 3.4, 4.7, wob=0.02, n=14, rot=0.3 if n else -0.3),
               C['leaf200'])
        if not n:
            k.form(k.circ(ax, by + 10.5, 1.9, wob=0.03, n=10), C['wal500'], relief=0.5)
    return k


# ── lights ────────────────────────────────────────────────────────────────


@recorded
def pendant(seed=0, shade='rattan'):
    """A pendant lamp over a table, seen from above: a woven dome with the cord's cap in the middle,
    or, over an island, a slim black cylinder. Its light pools on the table under it and the
    floor round it."""
    if shade == 'cylinder':
        k = Ink('pendant', 16, 16, 70, C['line'], seed)
        k.light(8, 8, 90)
        k.form(k.circ(8, 8, 7, wob=0.03, n=18), C['black'], relief=1.6, cast=70)
        k.mark(k.circ(8, 8, 5.2, wob=0.02, n=16), 'detail faint', closed=True)
        k.form(k.circ(8, 8, 1.6, wob=0.02, n=8), C['chr400'], relief=0.3)
        return k
    k = Ink('pendant', 44, 44, 70, C['oak500'], seed)
    k.light(22, 22, 120)
    fill = C['oak200'] if shade == 'rattan' else C['black']
    k.form(k.circ(22, 22, 20, wob=0.2, n=28), fill, relief=2.8, cast=70)
    if shade == 'rattan':
        for i in range(16):
            a = i * math.tau / 16
            k.mark([(22 + 5 * math.cos(a), 22 + 5 * math.sin(a)),
                    (22 + 18.5 * math.cos(a), 22 + 18.5 * math.sin(a))], 'weave')
        for r in (9, 14):
            k.mark(k.circ(22, 22, r, wob=0.15, n=20), 'detail faint', closed=True)
    k.form(k.circ(22, 22, 3.4, wob=0.05, n=10), C['black'], relief=0.6)
    return k


@recorded
def sconce(seed=0):
    """A wall sconce, seen from above: a small brass half-shade against the wall, glowing."""
    k = Ink('sconce', 20, 12, 160, C['wal700'], seed)
    k.light(10, 6, 80)
    k.form([(1, 0), (19, 0), (17, 6), (13, 10), (7, 10), (3, 6)], C['oak300'], relief=1, cast=20)
    k.flat(k.blob(10, 4.4, 4, 2.6, wob=0.04, n=10), C['core'])
    return k


@recorded
def string_lights(length=200, seed=0):
    """A string of fairy lights along a wall: a sagging wire and a row of warm bulbs."""
    k = Ink('string-lights', length, 12, 150, C['line'], seed)
    n = int(length // 16)
    pts = [(x, 2 + 6 * math.sin(math.pi * (x % 66) / 66)) for x in
           [length * i / (n * 3) for i in range(n * 3 + 1)]]
    k.mark(pts, 'wire')
    for i in range(1, n):
        x = length * i / n
        y = 2 + 6 * math.sin(math.pi * (x % 66) / 66)
        k.light(x, y, 26)
        k.form(k.circ(x, y + 1.2, 1.6, wob=0.05, n=8), C['core'], relief=0, line='line thin')
    return k
