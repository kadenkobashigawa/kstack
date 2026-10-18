#!/usr/bin/env python3
"""
furnish — furnishes the houses plans.py generates, room by room, and keeps a suite only once
rules.py's check passes.

Usage
-----
    furnish.py preview <out-dir> [seed ...]    each house furnished, all nine suites, as PNG
    furnish.py pin <seed> <pad>[=room,...] ...  keep rooms as they stand now, by number-pad spot

A pinned room is saved to pins.json and stands exactly as it was in every later build, while the
rooms round it are furnished afresh; the suites sit like a number pad, 7 top left, 3 bottom
right.

A room is furnished from groups: a bed with its nightstands, rug and the clear floor round it; a
television, sofa, coffee table and armchair; a desk and its chair; a dining table and its chairs
or a marble kitchen island; and a little oval table with two poufs under it, in a bedroom and,
when its floor has room, in a study.
Each group is laid out once in its own frame, its back against a wall, and carries the floor it
must keep clear (beside a bed, in front of a seat or a dresser, behind a desk chair).
The furnisher tries every wall and every position along it and keeps the first spot where the
group stands on the room's floor, touches nothing already placed, and keeps its clear floor clear.
Doorways, the sliding door and the dock keep their approaches clear the same way.

A suite is then checked whole by rules.check, the rules with their sources; a suite that fails is
furnished again from a fresh roll, and the best attempt kept.
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import canvas
import decor
import furniture
import layout
import pen
import rules
import vacuum
import plans

PINS = Path(__file__).with_name('pins.json')



CELL = plans.CELL
HALF = 7
TRIES = 18
TALL = {'wardrobe', 'bookshelf'}
SOFT = rules.COVER | rules.OVERHEAD | rules.TOPPER

#how much of a room's floor its pieces stand on, rugs left out, in the hand-laid house the user
#approved: each room is filled toward its own kind's share...
FILL = {'living': 0.21, 'bedroom': 0.36, 'study': 0.23}

#at most this many dressers, wardrobes and bookshelves to a room, so walls are not lined with
#them: the user's rule...
STORAGE = {'dresser', 'wardrobe', 'bookshelf'}
STORE_MAX = {'living': 3, 'bedroom': 3, 'study': 2}
ROT_OF = {(0, 1): 0, (-1, 0): 90, (0, -1): 180, (1, 0): 270}


# ── groups, in their own frame ────────────────────────────────────────────


class Group:
    """Pieces laid out in a frame whose wall is the line y = 0 with the room below it: each
    piece by its centre and turn, each clear zone as a rectangle, with the pieces allowed in it
    and whether it must be the room's floor."""

    def __init__(self, name, prefer='any'):
        self.name, self.prefer = name, prefer
        self.items, self.clear = [], []

    def add(self, ink, cx, cy, rot=0):
        self.items.append((ink, cx, cy, rot))
        return self

    def keep(self, x0, y0, x1, y1, allowed=(), floor=True):
        self.clear.append(((min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)),
                           set(allowed), floor))
        return self

    def span(self):
        xs = []
        for ink, cx, _, rot in self.items:
            w, _ = ink.dims(rot)
            xs += [cx - w / 2, cx + w / 2]
        for (x, _, w, _), _, _ in self.clear:
            xs += [x, x + w]
        return min(xs), max(xs)


def turned(group):
    """The same free-standing group turned a quarter round about its middle."""
    g = Group(group.name, group.prefer)
    for ink, cx, cy, rot in group.items:
        g.items.append((ink, -cy, cx, (rot + 90) % 360 if rot % 90 == 0 else rot + 90))
    for (x, y, w, h), allowed, floor in group.clear:
        g.clear.append(((-y - h, x, h, w), allowed, floor))
    return g


def against(ink, cx=0.0, rot=0):
    """A piece's centre when it stands with its back to the wall, facing the room."""
    _, depth = ink.dims(rot)
    return cx, HALF + depth / 2


# ── a room's walls ────────────────────────────────────────────────────────


def runs_of(room_of, kind):
    """The room's walls as (axis, line, from, to, inward normal) in centimetres."""
    out = []
    for axis, line, a, b, n in plans.runs_between(room_of, lambda c: room_of[c] == kind,
                                                  lambda c: room_of.get(c) != kind):
        out.append((axis, line * CELL, a * CELL, b * CELL, n))
    return out


def corners_of(cells):
    """The room's inside corners, each with the direction into the room."""
    out = []
    for c in cells:
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            vx, vy = c[0] + dx, c[1] + dy
            around = [(vx - 1, vy - 1), (vx, vy - 1), (vx - 1, vy), (vx, vy)]
            inside = [a for a in around if a in cells]
            if len(inside) == 1 and inside[0] == c:
                out.append(((vx * CELL, vy * CELL), (1 if c[0] >= vx else -1, 1 if c[1] >= vy else -1)))
    return out


def within(rect, cells, margin) -> bool:
    """Whether the rectangle, grown by the margin, lies wholly on the room's cells."""
    x, y, w, h = rect
    i0, i1 = math.floor((x - margin) / CELL), math.floor((x + w + margin - 1e-6) / CELL)
    j0, j1 = math.floor((y - margin) / CELL), math.floor((y + h + margin - 1e-6) / CELL)
    return all((i, j) in cells for i in range(i0, i1 + 1) for j in range(j0, j1 + 1))


# ── placing ───────────────────────────────────────────────────────────────


class Suite:
    """One suite being furnished: what stands where, and the floor that must stay clear."""

    def __init__(self, plan, around=(), pinned=None):
        self.plan, self.around = plan, list(around)
        self.items = {kind: [] for kind in sorted(set(plan['room_of'].values()))}
        self.solids, self.clear, self.lamps = [], [], []
        self.groups = {}
        self.fixed = set(pinned or ())
        for kind, rows in (pinned or {}).items():
            for ink, X, Y, rot, rect in unpinned(rows):
                self.items[kind].append((ink, X, Y, rot, rect))
                if ink.name not in SOFT:
                    self.solids.append((ink.name, rules.footprint(ink, rect), kind))
                if rules.lamp(ink):
                    self.lamps.append((rules.footprint(ink, rect), kind))
        for a, b, n in plan['doors'] + plan['sliders']:
            x1, x2, y1, y2 = min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])
            zone = ((x1 - rules.DOOR_CLEAR, y1, 2 * rules.DOOR_CLEAR, y2 - y1) if x1 == x2 else
                    (x1, y1 - rules.DOOR_CLEAR, x2 - x1, 2 * rules.DOOR_CLEAR))
            self.clear.append((zone, set(), False, None))
        for zone in rules.landings(plan['doors']):
            self.clear.append((zone, None, False, rules.BED))
        for (ax, ay), (bx, by), (nx, ny) in plan['windows']:
            x1, x2, y1, y2 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
            zone = ((x1, y1 + (HALF if ny > 0 else -HALF - 60), x2 - x1, 60) if ny else
                    (x1 + (HALF if nx > 0 else -HALF - 60), y1, 60, y2 - y1))
            self.clear.append((zone, None, False, TALL))

    def cells(self, kind):
        return {c for c, k in self.plan['room_of'].items() if k == kind}

    def blocked(self, name, rect) -> bool:
        """Whether a piece standing here would hit another piece or someone's clear floor."""
        if name in SOFT:
            return False
        for other, r, _ in self.solids:
            if rules.overlap(rect, r, -1):
                return True
        for r, allowed, _, forbid in self.clear:
            if rules.overlap(rect, r, -1):
                if forbid is not None:
                    if name in forbid:
                        return True
                elif name not in allowed:
                    return True
        return False

    def fits(self, kind, placed, zones) -> bool:
        cells = self.cells(kind)

        #a bed lies only on its own rug: no other rug goes under one, and no bed onto one...
        rugs = [rect for ink, *_, rect in self.items[kind] if ink.name in rules.COVER - {'doormat'}]
        beds = [r for name, r, room in self.solids if room == kind and name in rules.BED]
        for ink, _, _, _, rect in placed:
            if ink.name in rules.BED and any(rules.overlap(rect, r, -1) for r in rugs):
                return False
            if ink.name in rules.COVER - {'doormat'} and any(rules.overlap(rect, b, -1) for b in beds):
                return False
        for ink, _, _, _, rect in placed:
            fp = rules.footprint(ink, rect)
            if ink.name in SOFT and ink.name not in rules.COVER:
                continue
            if not within(fp, cells, HALF - 0.5):
                return False
            if self.blocked(ink.name, fp):
                return False
            if ink.name not in SOFT and self.twinned(kind, ink.name, fp):
                return False
            if rules.lamp(ink) and any(room == kind and rules.gap(fp, r) < rules.LAMP_APART
                                   for r, room in self.lamps):
                return False
        for rect, allowed, floor, _ in zones:
            if floor and not within(rect, cells, 0):
                return False
            for name, r, _ in self.solids:
                if name not in allowed and rules.overlap(rect, r, -1):
                    return False
        return True

    def commit(self, kind, placed, zones) -> bool:
        """Stand the pieces, unless that would cut a doorway off from the walkway: then put
        everything back and say no."""
        mark = (len(self.items[kind]), len(self.solids), len(self.clear), len(self.lamps))
        for ink, X, Y, rot, rect in placed:
            self.items[kind].append((ink, X, Y, rot, rect))
            if ink.name not in SOFT:
                self.solids.append((ink.name, rules.footprint(ink, rect), kind))
            if rules.lamp(ink):
                self.lamps.append((rules.footprint(ink, rect), kind))
        self.clear += zones
        if any(ink.name not in SOFT for ink, *_ in placed) and not self.route_ok():
            del self.items[kind][mark[0]:]
            del self.solids[mark[1]:]
            del self.clear[mark[2]:]
            del self.lamps[mark[3]:]
            return False
        return True

    def route_ok(self) -> bool:
        """rules.py's walkway rule on the check's own 5 cm grid: every doorway reachable from the
        entry along a path 81 cm wide."""
        rooms = [dict(name=k, poly=p) for k, p in self.plan['rooms']]
        entry = (self.plan['sliders'][0][:2] if self.plan['sliders'] else
                 self.plan['doors'][0][:2])
        solids = [r for _, r, _ in self.solids]
        return rules.walkway_ok(rooms, self.plan['doors'], entry, solids, cell=5)

    def cover(self, kind) -> float:
        """The share of the room's floor its pieces stand on, rugs left out."""
        floor = len(self.cells(kind)) * CELL * CELL
        return sum(r[2] * r[3] for _, r, room in self.solids if room == kind) / floor

    def twinned(self, kind, name, fp) -> bool:
        """Whether the same piece already stands near this spot: in the room, or back to back
        through a wall, here or in a suite next door."""
        office = not any(ink.name == 'double-bed' for ink, *_ in self.items[kind])
        return any(rules.twins(name, other, office and room == kind) and
                   rules.gap(fp, r) < (rules.ADJACENT if room == kind else rules.ACROSS)
                   for other, r, room in self.solids) or \
            any(rules.twins(name, other) and rules.gap(fp, r) < rules.ACROSS for other, r in self.around)

    def backed(self, group, run, u) -> bool:
        """Whether every piece the group stands against the wall has wall behind the whole of
        it: not past the wall's end, not across a doorway, and a wall light not on a window."""
        axis, L, a, b, _ = run
        x0, x1 = group.span()
        to_world, _ = self.frame(run, u, x1 - x0)
        k = 0 if axis == 'y' else 1

        def on_line(segs):
            return [(min(p[k], q[k]), max(p[k], q[k])) for p, q, _ in segs
                    if abs(p[1 - k] - L) < 0.5 and abs(q[1 - k] - L) < 0.5]

        doors = on_line(self.plan['doors'] + self.plan['sliders'])
        glass = on_line(self.plan['windows'])
        for ink, cx, cy, rot in group.items:
            if ink.name in rules.COVER | rules.TOPPER or rot % 90:
                continue
            w, depth = ink.dims(rot)
            if cy - depth / 2 > HALF + 5:
                continue
            ends = [to_world(cx - w / 2 - x0, cy)[k], to_world(cx + w / 2 - x0, cy)[k]]
            u0, u1 = min(ends), max(ends)
            if u0 < a - 0.5 or u1 > b + 0.5:
                return False
            near = doors + (glass if ink.name in rules.OVERHEAD else [])
            if any(u0 < g1 and g0 < u1 for g0, g1 in near):
                return False
        return True

    def frame(self, run, u, width):
        """The map from a group's frame to the house, for a group whose span starts u along the
        wall."""
        axis, L, _, _, n = run
        ey = n
        ex = (ey[1], -ey[0])
        along = u if (ex[0] if axis == 'y' else ex[1]) > 0 else u + width
        ox, oy = (along, L) if axis == 'y' else (L, along)
        return (lambda lx, ly: (ox + lx * ex[0] + ly * ey[0], oy + lx * ex[1] + ly * ey[1])), \
            ROT_OF[n]

    def realise(self, group, run, u):
        x0, x1 = group.span()
        to_world, wall_rot = self.frame(run, u, x1 - x0)
        placed = []
        for ink, cx, cy, rot in group.items:
            wx, wy = to_world(cx - x0, cy)
            r = (wall_rot + rot) % 360 if rot % 90 == 0 else wall_rot + rot
            w, h = ink.dims(r % 360 if rot % 90 == 0 else r)
            rect = (wx - w / 2, wy - h / 2, w, h)
            X, Y = (wx - ink.w / 2, wy - ink.d / 2) if rot % 90 else (rect[0], rect[1])
            placed.append((ink, X, Y, r, rect))
        zones = []
        for (x, y, w, h), allowed, floor in group.clear:
            ax, ay = to_world(x - x0, y)
            bx, by = to_world(x + w - x0, y + h)
            zones.append(((min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay)), allowed, floor,
                          None))
        return placed, zones

    def mark(self):
        """Where the suite stands now, to come back to with undo."""
        return ({k: len(v) for k, v in self.items.items()}, len(self.solids), len(self.clear),
                len(self.lamps), dict(self.groups))

    def undo(self, mark):
        """Take away everything placed since the mark."""
        counts, solids, clear, lamps, groups = mark
        for k, n in counts.items():
            del self.items[k][n:]
        del self.solids[solids:]
        del self.clear[clear:]
        del self.lamps[lamps:]
        self.groups = groups

    def snapshot(self):
        """Everything standing now, kept aside to come back to with restore."""
        return ({k: list(v) for k, v in self.items.items()}, list(self.solids), list(self.clear),
                list(self.lamps), dict(self.groups))

    def restore(self, snap):
        items, solids, clear, lamps, groups = snap
        self.items = {k: list(v) for k, v in items.items()}
        self.solids, self.clear, self.lamps = list(solids), list(clear), list(lamps)
        self.groups = dict(groups)

    def stored(self, kind) -> int:
        """How many dressers, wardrobes and bookshelves stand in the room."""
        return sum(1 for ink, *_ in self.items[kind] if ink.name in STORAGE)

    def place(self, kind, group, rnd, away=None) -> bool:
        """Put the group against the first wall spot of the room where it fits; with away, the
        spot farthest from that point first."""
        runs = runs_of(self.plan['room_of'], kind)
        rnd.shuffle(runs)
        x0, x1 = group.span()
        width = x1 - x0
        if away:
            spots = []
            for run in runs:
                _, _, a, b, _ = run
                for u in range(int(a) - 30, int(b - width) + 31, 15):
                    to_world, _ = self.frame(run, u, width)
                    cx, cy = to_world(width / 2, 60)
                    spots.append((-math.dist((cx, cy), away), run, u))
            spots.sort(key=lambda s: s[0])
            for _, run, u in spots:
                if not self.backed(group, run, u):
                    continue
                placed, zones = self.realise(group, run, u)
                if self.fits(kind, placed, zones) and self.commit(kind, placed, zones):
                    self.groups[kind, group.name] = self.groups.get((kind, group.name), 0) + 1
                    return True
            return False
        for run in runs:
            _, _, a, b, _ = run
            if b - a < width - 40:
                continue
            spots = [a + k * 15 for k in range(int((b - a - width + 60) / 15) + 1)]
            spots = [u - 30 for u in spots]
            mid = (a + b - width) / 2
            if group.prefer == 'middle':
                spots.sort(key=lambda u: abs(u - mid) + rnd.uniform(0, 20))
            elif group.prefer == 'corner':
                spots.sort(key=lambda u: min(abs(u - a), abs(b - u - width)) + rnd.uniform(0, 20))
            else:
                rnd.shuffle(spots)
            for u in spots:
                if not self.backed(group, run, u):
                    continue
                placed, zones = self.realise(group, run, u)
                if self.fits(kind, placed, zones) and self.commit(kind, placed, zones):
                    self.groups[kind, group.name] = self.groups.get((kind, group.name), 0) + 1
                    return True
        return False

    def place_free(self, kind, group, rnd, centre=False) -> bool:
        """Put a group that stands free of the walls (a dining table) wherever it fits; with
        centre, as near the middle of the room's floor as it fits."""
        cells = self.cells(kind)
        xs = [c[0] * CELL for c in cells]
        ys = [c[1] * CELL for c in cells]
        spots = [(x, y) for x in range(min(xs), max(xs) + CELL, 15)
                 for y in range(min(ys), max(ys) + CELL, 15)]
        rnd.shuffle(spots)
        if centre:
            mx = sum(c[0] + 0.5 for c in cells) * CELL / len(cells)
            my = sum(c[1] + 0.5 for c in cells) * CELL / len(cells)
            spots.sort(key=lambda p: math.dist(p, (mx, my)) + rnd.uniform(0, 60))
        for ox, oy in spots[:1500 if centre else 400]:
            placed, zones = [], []
            for ink, cx, cy, rot in group.items:
                w, h = ink.dims(rot)
                rect = (ox + cx - w / 2, oy + cy - h / 2, w, h)
                X, Y = ((ox + cx - ink.w / 2, oy + cy - ink.d / 2) if rot % 90
                        else (rect[0], rect[1]))
                placed.append((ink, X, Y, rot, rect))
            for (x, y, w, h), allowed, floor in group.clear:
                zones.append(((ox + x, oy + y, w, h), allowed, floor, None))
            if self.fits(kind, placed, zones) and self.commit(kind, placed, zones):
                return True
        return False

    def corner(self, kind, ink, rnd, inset=26, partner=None) -> bool:
        """Stand a plant's pot tight into a free corner of the room, and a partner, if given,
        beside it along one of the corner's two walls."""
        spots = corners_of(self.cells(kind))
        rnd.shuffle(spots)
        for (vx, vy), (sx, sy) in spots:
            cx, cy = vx + sx * inset, vy + sy * inset
            rect = (cx - ink.w / 2, cy - ink.d / 2, ink.w, ink.d)
            placed = [(ink, rect[0], rect[1], 0, rect)]
            if partner:
                along = rnd.choice(((sx, 0), (0, sy)))
                px = vx + sx * 22 + along[0] * 58
                py = vy + sy * 22 + along[1] * 58
                prect = (px - partner.w / 2, py - partner.d / 2, partner.w, partner.d)
                placed.append((partner, prect[0], prect[1], 0, prect))
            if self.fits(kind, placed, []) and self.commit(kind, placed, []):
                return True
        return False


# ── the groups ────────────────────────────────────────────────────────────


class Roll:
    """One suite's choices: a wood per room, its fabrics, and a running seed for every piece."""

    def __init__(self, rnd):
        self.rnd, self.n = rnd, 0
        self.duvet = rnd.choice(['linen', 'oat', 'sage'])
        self.throw = rnd.choice(['cognac', 'grey', 'sage', 'oat'])
        self.fabric = rnd.choice(['oat', 'sage', 'linen'])
        self.accent = rnd.choice(['cognac', 'sage'])
        self.coat = rnd.choice(list(decor.COAT))

    def seed(self):
        self.n += 1
        return self.n

    def cat(self, chance) -> bool:
        """Whether the suite's one cat curls up here."""
        if getattr(self, 'has_cat', False) or self.rnd.random() > chance:
            return False
        self.has_cat = True
        return True

    def pot(self):
        return self.rnd.choice(['white', 'black', 'basket'])


def bed_group(roll, wood, double, foot=False):
    s = roll.seed
    if double:
        bed = furniture.double_bed(s(), wood, roll.duvet, roll.throw)
        g = Group('bed', 'middle').add(bed, *against(bed))
        for side in (-1, 1):
            ns = furniture.nightstand(s(), wood)
            g.add(ns, side * (bed.w / 2 + ns.w / 2), HALF + ns.d / 2)
            g.keep(side * bed.w / 2, HALF + 60, side * (bed.w / 2 + rules.BED_SIDE), HALF + bed.d,
                   allowed={'nightstand'})
        g.add(furniture.string_lights(250, s()), 0, HALF + 6)
        rug = decor.beni_rug(s(), 170, bed.w + 2 * rules.BED_RUG + 10)
        g.add(rug, 0, HALF + 100 + 85, 90)
    else:
        bed = furniture.single_bed(s(), wood, roll.duvet, roll.throw)
        g = Group('bed', 'corner').add(bed, *against(bed))
        side = roll.rnd.choice((-1, 1))
        ns = furniture.nightstand(s(), wood)
        g.add(ns, side * (bed.w / 2 + ns.w / 2), HALF + ns.d / 2)
        g.keep(-side * bed.w / 2, HALF + 60, -side * (bed.w / 2 + rules.BED_SIDE), HALF + bed.d)
        rug = decor.stripe_rug(s(), bed.w + 2 * rules.BED_RUG + 20, 200)
        g.add(rug, 0, HALF + 95 + 100, 90)
    g.keep(-bed.w / 2, HALF + bed.d, bed.w / 2, HALF + bed.d + rules.BED_SIDE, allowed=rules.TUCK)
    if foot:
        #the little oval table with its two poufs, just past the clear floor at the foot...
        for ink, cx, cy, rot in pouf_table(roll, wood):
            g.add(ink, cx, HALF + bed.d + rules.BED_SIDE + 12 + cy, rot)
    if roll.cat(0.6):
        g.add(canvas.Part(decor.cat, s(), roll.coat)(), roll.rnd.uniform(-25, 25),
              HALF + bed.d * roll.rnd.uniform(0.55, 0.75), roll.rnd.uniform(-60, 60))
    return g


def pouf_table(roll, wood):
    """The little oval table with two poufs of one colour pushed in under its ends, a little off
    centre: its pieces, by centre, with the table's top edge at y = 0. The poufs come first, so
    the table is drawn over them."""
    s = roll.seed
    table = furniture.coffee_table(s(), wood, roll.rnd.choice(['notepad', 'books']))
    knit = roll.rnd.choice(['cognac', 'sage', 'oat'])
    out = []
    for side in (-1, 1):
        out.append((decor.pouf(s(), knit), side * roll.rnd.uniform(46, 54),
                    table.d / 2 + roll.rnd.uniform(3, 8), roll.rnd.uniform(-30, 30)))
    out.append((table, 0, table.d / 2, 0))
    return out


def tea_group(roll, wood):
    """The pouf table standing free on the floor, on a small round rug."""
    g = Group('tea')
    g.add(decor.jute_rug(roll.seed(), 200), 0, 30)
    for ink, cx, cy, rot in pouf_table(roll, wood):
        g.add(ink, cx, cy, rot)
    return g


def wall_piece(roll, kind, wood):
    """A dresser, wardrobe, bookshelf or sideboard against a wall, its front kept clear."""
    s = roll.seed
    ink = {'wardrobe': furniture.wardrobe, 'dresser': furniture.dresser, 'bookshelf': furniture.bookshelf}[kind](s(), wood)
    g = Group(kind, 'any').add(ink, *against(ink))
    front = rules.FRONT_CLEAR[ink.name]
    g.keep(-ink.w / 2 + 5, HALF + ink.d, ink.w / 2 - 5, HALF + ink.d + front, allowed={'pouf'})
    return g


def desk_group(roll, wood, setup):
    s = roll.seed
    desk = furniture.desk(s(), wood, setup)
    chair = furniture.desk_chair(s(), roll.accent)
    g = Group('desk', 'corner').add(chair, 0, HALF + desk.d + chair.d / 2 - 8)
    g.add(desk, *against(desk))
    g.keep(-desk.w / 2 + 5, HALF + desk.d, desk.w / 2 - 5, HALF + desk.d + rules.DESK_BACK,
           allowed={'desk-chair'})
    return g


def reading_group(roll, wood):
    """An armchair facing into the room with a lamp table beside it and a floor lamp."""
    s = roll.seed
    chair = furniture.armchair(s(), roll.rnd.choice(['cognac', 'sage', 'oat']))
    side = roll.rnd.choice((-1, 1))
    table = furniture.side_table(s(), wood, 'lamp')
    g = Group('reading', 'corner').add(chair, *against(chair))
    g.add(table, side * (chair.w / 2 + 5 + table.w / 2), HALF + table.d / 2 + 4)

    #half the reading corners stand on a small round rug, the chair wholly on it...
    if roll.rnd.random() < 0.5:
        g.add(decor.jute_rug(s(), 140), 0, HALF + 72)
    g.keep(-chair.w / 2 + 10, HALF + chair.d, chair.w / 2 - 10, HALF + chair.d + rules.SEAT_FRONT,
           allowed={'pouf', 'side-table'})
    if roll.rnd.random() < 0.5:
        g.add(decor.basket(s(), roll.throw), -side * (chair.w / 2 + 26), HALF + 24,
              roll.rnd.uniform(-40, 40))
    return g


def tv_group(roll, wood, seats, with_chair=True, coffee=True):
    """The television on the wall, sconces either side, and the sofa facing it on a rug: across
    the coffee table at the distances the rules ask, with an armchair to one side and its lamp
    table; or, where the room is too small for that, a loveseat across open floor with a lamp
    table beside it."""
    s = roll.seed
    tv = furniture.tv_console(s(), wood)
    sofa = furniture.sofa(s(), roll.fabric, roll.accent, seats)
    tv_front = HALF + tv.d
    g = Group('tv', 'middle').add(tv, *against(tv))
    for side in (-1, 1):
        g.add(furniture.sconce(s()), side * (tv.w / 2 + 16), HALF + 6)
    side = roll.rnd.choice((-1, 1))
    if coffee:
        table = furniture.coffee_table(s(), wood, roll.rnd.choice(['books', 'notepad']))
        coffee_y = tv_front + rules.FRONT_CLEAR['tv-console'] + 4 + table.d / 2
        sofa_front = coffee_y + table.d / 2 + 40
        g.add(table, 0, coffee_y)
        rug = decor.beni_rug(s(), 180, max(270, sofa.w + (100 if with_chair else 60)))
        g.add(rug, 0, coffee_y + 40, 90)
    else:
        sofa_front = tv_front + 90
        table = furniture.side_table(s(), wood, 'lamp')
        g.add(table, side * (sofa.w / 2 + 5 + table.w / 2), sofa_front + sofa.d - table.d / 2 - 4)
        rug = decor.beni_rug(s(), 140, max(220, sofa.w + 60))
        g.add(rug, 0, sofa_front - 15, 90)
    g.add(sofa, 0, sofa_front + sofa.d / 2, 180)
    g.keep(-tv.w / 2 + 5, tv_front, tv.w / 2 - 5, tv_front + rules.FRONT_CLEAR['tv-console'])
    g.keep(-sofa.w / 2, sofa_front + sofa.d, sofa.w / 2, sofa_front + sofa.d + 45, floor=False)
    if coffee and with_chair:
        chair = furniture.armchair(s(), roll.rnd.choice(['cognac', 'sage', 'oat']))
        ax = side * (sofa.w / 2 + 30 + chair.d / 2)
        g.add(chair, ax, coffee_y, 270 if side < 0 else 90)
        lamp_table = furniture.side_table(s(), wood, 'lamp')
        g.add(lamp_table, ax, coffee_y - chair.w / 2 - 5 - lamp_table.d / 2)
        g.keep(ax - side * chair.d / 2, coffee_y - chair.w / 2 + 10,
               ax - side * (chair.d / 2 + rules.SEAT_FRONT), coffee_y + chair.w / 2 - 10,
               allowed={'coffee-table', 'side-table'})
    g.add(decor.floor_lamp(s()), -side * (sofa.w / 2 + 26), sofa_front + sofa.d - 24)
    if roll.cat(0.4):
        g.add(canvas.Part(decor.cat, s(), roll.coat)(), roll.rnd.uniform(-sofa.w / 3, sofa.w / 3),
              sofa_front + sofa.d / 2 + 6, 180 + roll.rnd.uniform(-40, 40))
    return g


def dining_group(roll, wood, seats=4):
    """A round table with its chairs tucked in, four round it or a pair facing each other, a
    pendant over it and a jute rug under, 81 cm of clear floor kept behind every chair."""
    s = roll.seed
    g = Group('dining')
    g.add(decor.jute_rug(s(), 220 if seats == 4 else 180), 0, 0)
    for rot, (cx, cy) in ((0, (0, 58)), (180, (0, -58)), (90, (-58, 0)), (270, (58, 0)))[:seats]:
        g.add(furniture.dining_chair(s(), wood), cx, cy, rot)
    g.add(furniture.round_table(s(), wood, roll.rnd.choice(['flowers', 'tea'])), 0, 0)
    g.add(furniture.pendant(s()), 0, 0)
    r = 50 + rules.DINING
    if seats == 4:
        g.keep(-r, -r, r, r, allowed=rules.TUCK)
    else:
        g.keep(-50, -r, 50, r, allowed=rules.TUCK)
        g.keep(-80, -50, 80, 50, allowed=rules.TUCK)
    return g


def island_group(roll, length=240):
    """A marble kitchen island standing free, two pendants over it, a walkway kept clear all
    round and the wider work aisle on the side the cook stands."""
    s = roll.seed
    isl = furniture.island(s(), length)
    rot = roll.rnd.choice((0, 180))
    g = Group('island')

    #round stools along the back edge, one to every 61 cm of it (NKBA 9), tucked a little under
    #the counter; drawn first, so the counter covers what is under it...
    behind = -1 if rot == 0 else 1
    seat = roll.rnd.choice(['cognac', 'linen', 'sage'])
    n = int(isl.w // rules.SEAT_WIDTH)
    for i in range(n):
        g.add(furniture.bar_stool(s(), seat), (i - (n - 1) / 2) * rules.SEAT_WIDTH * 1.05,
              behind * (isl.d / 2 + 12))
    g.add(isl, 0, 0, rot)

    #two slim pendants over the stone behind the sink and the hob, clear of the faucet...
    for x in (-60, 60):
        g.add(furniture.pendant(s(), 'cylinder'), x, -28 if rot == 0 else 28)
    work = rules.ISLAND_WORK if rot == 0 else rules.ISLAND_WALK
    back = rules.ISLAND_WALK if rot == 0 else rules.ISLAND_WORK
    g.keep(-isl.w / 2 - rules.ISLAND_WALK, -isl.d / 2 - back, isl.w / 2 + rules.ISLAND_WALK,
           isl.d / 2 + work)
    return g


def dock_group(roll):
    dk = vacuum.dock(roll.seed())
    g = Group('dock', 'corner').add(dk, *against(dk))
    y0 = HALF + dk.d
    g.keep(-dk.w / 2, y0, dk.w / 2, y0 + rules.DOCK_FRONT)
    for side in (-1, 1):
        g.keep(side * dk.w / 2, HALF, side * (dk.w / 2 + rules.DOCK_SIDES), y0, floor=False)
    return g


# ── a suite ───────────────────────────────────────────────────────────────


WOODS = ['walnut', 'oak', 'black']
BIG_PLANTS = (decor.monstera, decor.fiddle_leaf, decor.rubber_plant)


def furnish_rooms(su, plan, rnd) -> list[str]:
    """Furnish each room of the suite; returns the groups that found no place."""
    roll = Roll(rnd)
    missing = []
    wood = {k: rnd.choice(WOODS) for k in su.items}

    def try_place(kind, group, free=False, required=True):
        ok = (su.place_free if free else su.place)(kind, group, rnd)
        if not ok and required:
            missing.append(f'{kind}: {group.name}')
        return ok

    #the television group first, the most demanding, then the table, then the dock, tucked
    #toward a corner where its clear floor costs the least, then the rest; a pinned room stands
    #as it was and is passed over...
    fixed = su.fixed
    w = wood['living']
    if 'living' not in fixed:
        tvs = ((3, True, True), (2, True, True), (3, False, True), (2, False, True),
               (2, False, False))
        if not any(su.place('living', tv_group(roll, w, *v), rnd) for v in tvs):
            missing.append('living: television group')
            try_place('living', reading_group(roll, w), required=False)
        islands = [lambda n=n, q=q: (turned if q else lambda g: g)(island_group(roll, n))
                   for n in (240, 200) for q in rnd.sample((0, 1), 2)]
        dining = [lambda: dining_group(roll, w), lambda: dining_group(roll, w, 2)]
        big = len(su.cells('living')) * CELL * CELL >= 45e4
        first, second = (islands, dining) if big or rnd.random() < 0.6 else (dining, islands)
        if not any(su.place_free('living', make(), rnd, centre=make in islands)
                   for make in first + second):
            missing.append('living: dining table or island')

        #a living room with floor to spare has both: the island toward the middle, the dining
        #table where it fits...
        has = {ink.name for ink, *_ in su.items['living']}
        for make in dining if 'island' in has else islands:
            if su.place_free('living', make(), rnd, centre=make in islands):
                break
    docked = any(ink.name == 'dock' for kind in fixed for ink, *_ in su.items[kind])
    if not docked and not any(su.place(room, dock_group(roll), rnd)
                              for room in ('living', 'study', 'bedroom') if room not in fixed):
        missing.append('living: dock')
    if 'living' not in fixed and rnd.random() < 0.6 and su.stored('living') < STORE_MAX['living']:
        try_place('living', wall_piece(roll, rnd.choice(['bookshelf', 'dresser']), w),
                  required=False)

    #the bedroom: the bed in the middle of a wall, storage, then a desk or a reading chair; a
    #bedroom too awkward for a bed swaps roles with the study...
    bedded = [k for k in sorted(fixed) if any(ink.name in rules.BED for ink, *_ in su.items[k])
              and k in ('bedroom', 'study')]
    bedroom, study = 'bedroom', 'study'
    if bedded:
        bedroom = bedded[0]
        study = 'study' if bedroom == 'bedroom' else 'bedroom'
    else:
        #the bed goes in the larger room, the biggest bed first; a bed that leaves no floor for a
        #desk or a little table steps down, so even a small room is a dorm with a desk...
        placed = False
        for room in sorted((bedroom, study), key=lambda k: -len(su.cells(k))):
            if room in fixed:
                continue
            for double, foot in ((True, True), (True, False), (False, False)):
                before = su.mark()
                if not su.place(room, bed_group(roll, wood[room], double, foot), rnd):
                    continue
                desked = foot or su.place(room, desk_group(roll, wood[room], 'writing'), rnd)
                if desked or not double:
                    placed = True
                    break
                su.undo(before)
            if placed:
                bedroom, study = room, ('study' if room == 'bedroom' else 'bedroom')
                break
        if not placed:
            missing.append('bedroom: bed')
    w = wood[bedroom]
    if bedroom not in fixed:
        try_place(bedroom, wall_piece(roll, rnd.choice(['wardrobe', 'dresser']), w),
                  required=False)
        if not any(ink.name in rules.DESK for ink, *_ in su.items[bedroom]) and rnd.random() < 0.6:
            try_place(bedroom, desk_group(roll, w, 'writing'), required=False)
        else:
            try_place(bedroom, reading_group(roll, w), required=False)

    #the study: the desk, books, a daybed or a reading chair...
    w = wood[study]
    if study not in fixed:
        setups = ['dual', 'laptop', 'writing']
        rnd.shuffle(setups)
        try_place(study, desk_group(roll, w, setups[0]))
        desks = [rect for ink, *_, rect in su.items[study] if ink.name in rules.DESK]
        daybed = len(su.cells(study)) * CELL * CELL >= 18e4 or rnd.random() < 0.4
        steps = {
            'desk': lambda: bool(desks) and su.place(study, desk_group(roll, w, setups[1]), rnd,
                                                     away=rules.centre(desks[0])),
            'table': lambda: su.place_free(study, tea_group(roll, w), rnd, centre=True),
            'bed': lambda: daybed and su.place(study, bed_group(roll, w, False), rnd),
        }

        #the second desk, the little table and the daybed, in whichever order fits more of them...
        start = su.snapshot()
        best = None
        for order in (('desk', 'table', 'bed'), ('bed', 'desk', 'table')):
            su.restore(start)
            got = sum(bool(steps[s]()) for s in order)
            if best is None or got > best[0]:
                best = (got, su.snapshot())
        su.restore(best[1])
        try_place(study, wall_piece(roll, 'bookshelf', w), required=False)
        try_place(study, reading_group(roll, w), required=False)
    #the bedroom's little table: at the foot of a double bed if it fitted there, else standing
    #free on its own small rug; a study takes one too, in the middle of its floor...
    if bedroom not in fixed and not any(it[0].name == 'coffee-table' for it in su.items[bedroom]):
        su.place_free(bedroom, tea_group(roll, wood[bedroom]), rnd)
    if bedroom not in fixed and not any(it[0].name in rules.DESK | {'coffee-table'}
                                        for it in su.items[bedroom]):
        missing.append('bedroom: a table or desk beside the bed')

    #then fill each room toward the share of floor the approved house gives its kind: storage on
    #free walls, a reading corner, a big plant in a corner, until it is full or nothing fits...
    storage = {'living': ['bookshelf', 'dresser'], 'bedroom': ['wardrobe', 'dresser', 'bookshelf'],
               'study': ['bookshelf', 'dresser']}
    role = {'living': 'living', bedroom: 'bedroom', study: 'study'}
    for kind in [k for k in su.items if k not in fixed]:
        misses, picks = 0, 0
        reading = su.groups.get((kind, 'reading'), 0) > 0
        part = role.get(kind, kind)
        while su.cover(kind) < FILL.get(part, 0.25) and misses < 8 and picks < 24:
            picks += 1
            pick = rnd.random()
            if pick < 0.5 and su.stored(kind) < STORE_MAX.get(part, 2):
                ok = su.place(kind, wall_piece(roll, rnd.choice(storage[part]), wood[kind]), rnd)
            elif pick < 0.75 and not reading:
                ok = reading = su.place(kind, reading_group(roll, wood[kind]), rnd)
            else:
                ok = su.corner(kind, rnd.choice(BIG_PLANTS)(roll.seed(), roll.pot()), rnd,
                               partner=decor.snake_plant(roll.seed(), roll.pot()))
            misses = 0 if ok else misses + 1

    #plants into free corners, the big ones first...
    for kind in [k for k in su.items if k not in fixed]:
        for _ in range(rnd.randint(2, 3)):
            plant = rnd.choice(BIG_PLANTS)(roll.seed(), roll.pot())
            su.corner(kind, plant, rnd)
        if rnd.random() < 0.6:
            su.corner(kind, decor.snake_plant(roll.seed(), roll.pot()), rnd, inset=22)
    return missing


def laid(su, plan, robot_at):
    """The furnished suite in the shape rules.check and layout.house_sheet read."""
    rooms = [dict(name=kind, poly=poly, items=su.items[kind]) for kind, poly in plan['rooms']]
    docks = [(ink, X, Y, rot) for kind in su.items for ink, X, Y, rot, _ in su.items[kind]
             if ink.name == 'dock']
    for r in rooms:
        r['items'] = [it for it in r['items'] if it[0].name != 'dock']
    entry = (plan['sliders'][0][:2] if plan['sliders'] else plan['doors'][0][:2])
    return dict(floor=plan['floor'], rooms=rooms, doors=plan['doors'], entry=entry,
                dock=docks[0] if docks else (vacuum.dock(), 0, 0, 0), robot=robot_at,
                windows=plan['windows'], sliders=plan['sliders'])


def solids_of(suite):
    """A furnished suite's pieces that stand on the floor, as (name, footprint), dock included."""
    out = [(ink.name, rules.footprint(ink, rect)) for r in suite['rooms']
           for ink, _, _, _, rect in r['items'] if ink.name not in SOFT]
    dk, dx, dy, rot = suite['dock']
    w, h = dk.dims(rot)
    return out + [('dock', (dx, dy, w, h))]


def furnished(plan, seed, around=(), pinned=None):
    """The suite furnished, beside the pieces already standing in the suites next door and with
    its pinned rooms as they were: the first attempt that passes every rule, else the one with
    fewest broken rules, and what it still breaks."""
    best = None
    for attempt in range(TRIES):
        rnd = random.Random(f'{seed}:{attempt}')
        su = Suite(plan, around, pinned)
        missing = furnish_rooms(su, plan, rnd)
        docks = [(ink, rect) for k in su.items for ink, _, _, _, rect in su.items[k]
                 if ink.name == 'dock']
        if not docks:
            if best is None:
                best = (laid(su, plan, (0, 0)), ['missing dock'])
            continue
        dk, X, Y, rot, _ = next(it for k in su.items for it in su.items[k] if it[0].name == 'dock')
        hx, hy = canvas.mapper(dk, X, Y, rot)(vacuum.DOCKED_AT)
        out = laid(su, plan, (hx - vacuum.ROBOT_R, hy - vacuum.ROBOT_R))
        broken = rules.check([out], around) + [f'missing {m}' for m in missing]
        if best is None or len(broken) < len(best[1]):
            best = (out, broken)
        if not broken:
            break
    return best


def house(seed, n=plans.SUITES, report=None):
    """A generated house, its first n suites furnished in the order they are built, each beside
    the ones before it and the pinned rooms of the ones after. Broken rules are printed, or handed to
    report(k, lines) when given."""
    plan = plans.generate(seed)
    pins = load_pins().get(str(seed), {})
    later = {int(k): [(ink.name, rules.footprint(ink, rect)) for rows in rooms.values()
                      for ink, _, _, _, rect in unpinned(rows) if ink.name not in SOFT]
             for k, rooms in pins.items()}
    out, around = [], []
    for k, sp in enumerate(plan['suites'][:n]):
        ahead = [s for j, solids in later.items() if j > k for s in solids]
        su, broken = furnished(sp, f'{seed}:{k}', around + ahead, pins.get(str(k)))
        if report:
            report(k, broken)
        for line in broken:
            print(f'house {seed} suite {k + 1}: {line}', file=sys.stderr)
        out.append(su)
        around += solids_of(su)
    return out


# ── pinned rooms ──────────────────────────────────────────────────────────


def load_pins() -> dict:
    """Every pinned room, as {seed: {suite: {room: rows}}}."""
    return json.loads(PINS.read_text()) if PINS.exists() else {}


def unpinned(rows):
    """A pinned room's rows made back into pieces, each where it stood."""
    return [(canvas.remade(name, args, kw), X, Y, rot, tuple(rect))
            for name, args, kw, X, Y, rot, rect in rows]


def numpad(plan) -> dict:
    """Each suite's spot on a number pad, 7 top left to 3 bottom right, by its centre."""
    spots = []
    for k, sp in enumerate(plan['suites']):
        xs, ys = [c[0] for c in sp['cells']], [c[1] for c in sp['cells']]
        spots.append((k, sum(xs) / len(xs), sum(ys) / len(ys)))
    spots.sort(key=lambda s: s[2])
    out = {}
    for row, first in enumerate((7, 4, 1)):
        for col, (k, _, _) in enumerate(sorted(spots[row * 3:row * 3 + 3], key=lambda s: s[1])):
            out[k] = first + col
    return out


def pin(seed, picks) -> dict:
    """Pin rooms as they stand now: picks maps a number-pad spot to its room kinds, or to None for
    every room. Returns what was pinned, as {pad: [rooms]}."""
    plan = plans.generate(seed)
    pad = numpad(plan)
    suites = house(seed)
    pins = load_pins()
    mine = pins.setdefault(str(seed), {})
    done = {}
    for k, su in enumerate(suites):
        if pad[k] not in picks:
            continue
        rooms = picks[pad[k]] or [r['name'] for r in su['rooms']]
        dk, dx, dy, drot = su['dock']
        dw, dh = dk.dims(drot)
        for r in su['rooms']:
            if r['name'] not in rooms:
                continue
            items = list(r['items'])
            if pen.inside((dx + dw / 2, dy + dh / 2), r['poly']):
                items.append((dk, dx, dy, drot, (dx, dy, dw, dh)))
            rows = []
            for ink, X, Y, rot, rect in items:
                name, args, kw = ink.made
                rows.append([name, args, kw, X, Y, rot, list(rect)])
            mine.setdefault(str(k), {})[r['name']] = rows
        done[pad[k]] = rooms
    PINS.write_text(json.dumps(pins, indent=1) + '\n')
    return done


def main(argv: list[str]) -> int:
    if len(argv) >= 4 and argv[1] == 'pin':
        picks = {}
        for arg in argv[3:]:
            spot, _, rooms = arg.partition('=')
            picks[int(spot)] = rooms.split(',') if rooms else None
        for spot, rooms in sorted(pin(int(argv[2]), picks).items()):
            print(f'pinned {spot}: {", ".join(rooms)}')
        return 0
    if len(argv) < 3 or argv[1] != 'preview':
        print(__doc__)
        return 2
    out = Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for seed in [int(a) for a in argv[3:]] or [3]:
        sheet = layout.house_sheet(house(seed))
        p = (out / f'house-{seed}.svg').resolve()
        scale = 0.42
        p.write_text(sheet.svg(canvas.CSS, scale))
        canvas.render([(str(p), math.ceil(sheet.w * scale), math.ceil(sheet.h * scale), 2)])
        print(p.with_suffix('.png'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
