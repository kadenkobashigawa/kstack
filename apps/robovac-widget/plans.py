#!/usr/bin/env python3
"""
plans — generates houses for the widget: up to nine suites that lock together like puzzle
pieces, each split into rooms, with doors between its rooms and windows on the outside.

Usage
-----
    plans.py preview <out-dir> [seed ...]    the empty plans, for a look before furnishing

A house starts as a three-by-three grid of near-square blocks, one per suite. Every pair of
neighbouring suites then trades a tab: a block of one is handed to the other across their shared
wall, so each piece keys into the next. Suites are built and furnished in the order a breadth-first
walk from the middle suite meets them, and the app shows them in another: the corner suite with
the most glass first, then block by block across to the opposite corner, so a lone run gets two
outside walls of windows and whatever the number of runs (up to nine), the suites showing form
one piece (the user, 2026-10-14).

A suite is split into rooms by the squarified-treemap method (Bruls, Huizing & van Wijk 2000),
which Marson & Musse (2010) adapted to generating floor plans: the rooms' shares of the floor
are laid out as rectangles as close to square as the suite allows. The living room is the hub:
each other room opens off it, or, when it shares no wall with the living room, off a room that
does. A window or sliding door is only ever put on a wall that is
outside even when all nine suites stand, so no later suite ever joins onto glass.

Everything works on a grid of CELL-cm squares; rooms come back as polygons in centimetres.
"""

from __future__ import annotations

import math
import random
import sys
from collections import deque
from pathlib import Path



CELL = 30
SUITES = 9
TAB_W = (8, 12)
TAB_D = (4, 7)
MIN_ROOM = 9
PROGRAM = (('living', 0.44), ('bedroom', 0.32), ('study', 0.24))
PROGRAM_EVEN = (('living', 0.38), ('bedroom', 0.33), ('study', 0.29))


# ── the house: suites as puzzle pieces ────────────────────────────────────


def neighbours(c):
    i, j = c
    return ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1))


def connected(cells) -> bool:
    if not cells:
        return False
    start = next(iter(cells))
    seen, q = {start}, deque([start])
    while q:
        for n in neighbours(q.popleft()):
            if n in cells and n not in seen:
                seen.add(n)
                q.append(n)
    return len(seen) == len(cells)


def covered(cells, k=MIN_ROOM) -> set:
    """The cells of the set that sit in some k-by-k block of it; the rest are thinner than k."""
    out = set()
    for (i, j) in cells:
        if all((i + a, j + b) in cells for a in range(k) for b in range(k)):
            out.update((i + a, j + b) for a in range(k) for b in range(k))
    return out


def thick(cells, k=MIN_ROOM) -> bool:
    """Whether no part of the set is thinner than k."""
    return covered(cells, k) == set(cells)


def blocks(rnd):
    """A three-by-three grid of near-square suite blocks, about 8 to 9.5 m a side; columns share
    their widths and rows their heights, so the seams line up before the tabs are cut."""
    widths = [rnd.randint(27, 32) for _ in range(3)]
    heights = [rnd.randint(27, 32) for _ in range(3)]
    owner, cores, y = {}, {}, 0
    for r, h in enumerate(heights):
        x = 0
        for c, w in enumerate(widths):
            cores[3 * r + c] = (x, y, w, h)
            for i in range(x, x + w):
                for j in range(y, y + h):
                    owner[(i, j)] = 3 * r + c
            x += w
        y += h
    return owner, cores


def shared_runs(owner, a, b):
    """The straight stretches of wall suites a and b share, each as a list of (cell of a, cell of
    b) pairs in order."""
    pairs = [(c, n) for c, s in owner.items() if s == a for n in neighbours(c) if owner.get(n) == b]
    runs = {}
    for c, n in pairs:
        axis = 'v' if c[1] == n[1] else 'h'
        key = (axis, c[0] if axis == 'v' else c[1], n[0] if axis == 'v' else n[1])
        runs.setdefault(key, []).append((c, n))
    return [sorted(v, key=lambda p: p[0][1] if k[0] == 'v' else p[0][0]) for k, v in runs.items()]


def interlock(owner, rnd):
    """Trade a tab across every shared wall, keeping every suite whole and nowhere thin."""
    count = max(owner.values()) + 1
    for a in range(count):
        for b in range(a + 1, count):
            for run in shared_runs(owner, a, b):
                if len(run) < TAB_W[0] + 12:
                    continue
                for _ in range(12):
                    w = rnd.randint(*TAB_W)
                    if len(run) < w + 12:
                        continue
                    start = rnd.randint(6, len(run) - w - 6)
                    d = rnd.randint(*TAB_D)
                    giver, taker = (a, b) if rnd.random() < 0.5 else (b, a)
                    moved = []
                    for c, n in run[start:start + w]:
                        inner = n if owner[c] == giver else c
                        step = (inner[0] - (c if inner == n else n)[0],
                                inner[1] - (c if inner == n else n)[1])
                        for k in range(d):
                            cell = (inner[0] + step[0] * k, inner[1] + step[1] * k)
                            if owner.get(cell) != taker:
                                break
                            moved.append(cell)
                    if len(moved) != w * d:
                        continue
                    trial = dict(owner)
                    for cell in moved:
                        trial[cell] = giver
                    rest = {c for c, s in trial.items() if s == taker}
                    grown = {c for c, s in trial.items() if s == giver}
                    if connected(rest) and thick(rest) and thick(grown):
                        owner.clear()
                        owner.update(trial)
                        break
    return owner


def build_order(owner, rnd):
    """The order suites are built and furnished in: the middle suite first, then a breadth-first
    walk outward, so each is furnished beside one piece of the suites before it."""
    count = max(owner.values()) + 1
    adj = {s: set() for s in range(count)}
    for c, s in owner.items():
        for n in neighbours(c):
            t = owner.get(n)
            if t is not None and t != s:
                adj[s].add(t)
    order, q = [count // 2], deque([count // 2])
    while q:
        s = q.popleft()
        for t in sorted(adj[s], key=lambda t: rnd.random()):
            if t not in order:
                order.append(t)
                q.append(t)
    return order


# ── a suite: rooms by squarified treemap ──────────────────────────────────


def squarify(weights, x, y, w, h):
    """Bruls et al.'s squarified treemap: rectangles for the weights, each as square as it can be,
    filling (x, y, w, h)."""
    total = sum(weights)
    areas = [wt / total * w * h for wt in weights]
    out = []

    def worst(row, side):
        s = sum(row)
        return max(max(side * side * r / (s * s), s * s / (side * side * r)) for r in row)

    rest = list(areas)
    while rest:
        side = min(w, h)
        row = [rest.pop(0)]
        while rest and worst(row + [rest[0]], side) <= worst(row, side):
            row.append(rest.pop(0))
        s = sum(row)
        if w >= h:
            cw = s / h
            cy = y
            for r in row:
                out.append((x, cy, cw, r / cw))
                cy += r / cw
            x, w = x + cw, w - cw
        else:
            ch = s / w
            cx = x
            for r in row:
                out.append((cx, y, r / ch, ch))
                cx += r / ch
            y, h = y + ch, h - ch
    return out


def split_rooms(cells, rnd, core):
    """A suite's cells, split into living room, bedroom and study: the treemap divides the
    suite's block as it was before the tabs, every arrangement is tried, and the one whose three
    rooms are all usable and closest to square wins. A tab the suite gained joins the room it
    opens off; a tab it lost is simply gone from that room."""
    x0, y0, w, h = core
    best, best_score = None, -1.0
    options = [(swap, fx, fy, rot, weights) for swap in (0, 1) for fx in (0, 1) for fy in (0, 1)
               for rot in (0, 1) for weights in (PROGRAM, PROGRAM_EVEN)]
    rnd.shuffle(options)
    for swap, flip_x, flip_y, rot, weights in options:
        program = list(weights)
        if swap:
            program[1], program[2] = program[2], program[1]
        W, H = (h, w) if rot else (w, h)
        rects = squarify([p[1] for p in program], 0, 0, W, H)
        rooms = {}
        for (kind, _), (rx, ry, rw, rh) in zip(program, rects):
            for i in range(round(rx), round(rx + rw)):
                for j in range(round(ry), round(ry + rh)):
                    a, b = (j, i) if rot else (i, j)
                    ii = x0 + (w - 1 - a if flip_x else a)
                    jj = y0 + (h - 1 - b if flip_y else b)
                    if (ii, jj) in cells:
                        rooms[(ii, jj)] = kind
        rest = deque(c for c in rooms)
        while rest:
            c = rest.popleft()
            for n in neighbours(c):
                if n in cells and n not in rooms:
                    rooms[n] = rooms[c]
                    rest.append(n)
        rooms = tidy_rooms(rooms)
        kinds = set(rooms.values())
        if len(kinds) < 3:
            continue

        #every room reaches the suite's edge, so none is an island inside the living room...
        edge = {k: sum(1 for c, kk in rooms.items() if kk == k for n in neighbours(c)
                       if n not in cells) for k in kinds}
        score = min(squareness({c for c, k in rooms.items() if k == kind}) for kind in kinds)
        if min(edge.values()) < 8:
            score -= 1

        #a room walled in on most sides by the living room reads as a box in the middle...
        for kind in sorted(kinds - {'living'}):
            mine = [c for c, k in rooms.items() if k == kind]
            sides = [rooms.get(n) for c in mine for n in neighbours(c) if rooms.get(n) != kind]
            boxed = sides.count('living') / max(1, len(sides))
            if boxed > 0.5:
                score -= 2 * (boxed - 0.5)
        if score > best_score:
            best, best_score = rooms, score
    return best or tidy_rooms({c: 'living' for c in cells})


def squareness(cells) -> float:
    """How close a room is to a square that it fills: 1 for a full square, less for long or
    ragged rooms."""
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    return min(w, h) / max(w, h) * len(cells) / (w * h)


def pieces(cells):
    """The connected pieces of a set of cells, largest first."""
    out, seen = [], set()
    for c in cells:
        if c in seen:
            continue
        part, q = {c}, deque([c])
        seen.add(c)
        while q:
            for n in neighbours(q.popleft()):
                if n in cells and n not in seen:
                    seen.add(n)
                    part.add(n)
                    q.append(n)
        out.append(part)
    return sorted(out, key=len, reverse=True)


def tidy_rooms(rooms):
    """Hand a room's slivers thinner than 2.4 m to a neighbour, fold a room too small to furnish
    into the living room, and give stray scraps to whichever room they touch most; repeated
    until nothing moves, so every room ends as one piece."""
    for _ in range(8):
        before = dict(rooms)
        for kind in sorted(set(rooms.values()) - {'living'}):
            mine = {c for c, k in rooms.items() if k == kind}
            for c in mine - covered(mine, 8):
                touch = [rooms[n] for n in neighbours(c) if n in rooms and rooms[n] != kind]
                rooms[c] = 'living' if 'living' in touch or not touch else touch[0]
            mine = {c for c, k in rooms.items() if k == kind}
            if len(mine) < 110:
                for c in mine:
                    rooms[c] = 'living'
        #the living room is the walkway every door opens off: no neck of it narrower than
        #1.2 m, or a walkway 81 cm wide could not pass with room to spare...
        living = {c for c, k in rooms.items() if k == 'living'}
        for c in living - covered(living, 4):
            touch = [rooms[n] for n in neighbours(c) if n in rooms and rooms[n] != 'living']
            if touch:
                rooms[c] = touch[0]
        for kind in sorted(set(rooms.values())):
            for scrap in pieces({c for c, k in rooms.items() if k == kind})[1:]:
                touch = {}
                for c in scrap:
                    for n in neighbours(c):
                        if n in rooms and rooms[n] != kind:
                            touch[rooms[n]] = touch.get(rooms[n], 0) + 1
                to = max(touch, key=touch.get) if touch else 'living'
                for c in scrap:
                    rooms[c] = to
        #a cell mostly surrounded by another room joins it, so walls don't jog for one cell...
        for _ in range(3):
            for c in list(rooms):
                around = [rooms[n] for n in neighbours(c) if n in rooms]
                for kind in set(around):
                    if kind != rooms[c] and around.count(kind) >= 3:
                        rooms[c] = kind
        if rooms == before:
            break
    return rooms


def outline(cells):
    """The outline of a set of cells, as a polygon of corner points in centimetres."""
    edges = set()
    for (i, j) in cells:
        for e in (((i, j), (i + 1, j)), ((i + 1, j), (i + 1, j + 1)),
                  ((i + 1, j + 1), (i, j + 1)), ((i, j + 1), (i, j))):
            if (e[1], e[0]) in edges:
                edges.discard((e[1], e[0]))
            else:
                edges.add(e)
    nxt = {a: b for a, b in edges}
    start = min(nxt)
    loop, p = [start], nxt[start]
    while p != start:
        loop.append(p)
        p = nxt[p]
    corners = [loop[k] for k in range(len(loop))
               if (loop[k - 1][0] - loop[k][0], loop[k - 1][1] - loop[k][1]) !=
               (loop[k][0] - loop[(k + 1) % len(loop)][0], loop[k][1] - loop[(k + 1) % len(loop)][1])]
    return [(x * CELL, y * CELL) for x, y in corners]


# ── doors and windows ─────────────────────────────────────────────────────


def runs_between(rooms, inside, outside):
    """Straight runs of wall between cells that pass inside and cells that pass outside, each as
    (axis, line, from, to, inward normal) in cells."""
    edges = {}
    for c in rooms:
        if not inside(c):
            continue
        for n in neighbours(c):
            if outside(n):
                if c[0] != n[0]:
                    line, at, normal = max(c[0], n[0]), c[1], (1 if c[0] > n[0] else -1, 0)
                    edges.setdefault(('x', line, normal), []).append(at)
                else:
                    line, at, normal = max(c[1], n[1]), c[0], (0, 1 if c[1] > n[1] else -1)
                    edges.setdefault(('y', line, normal), []).append(at)
    out = []
    for (axis, line, normal), ats in edges.items():
        ats.sort()
        s = ats[0]
        for a, b in zip(ats, ats[1:] + [None]):
            if b != a + 1:
                out.append((axis, line, s, a + 1, normal))
                s = b
    return out


def segment(axis, line, a, b):
    """A stretch of wall in centimetres, given in cells along a grid line."""
    if axis == 'x':
        return (line * CELL, a * CELL), (line * CELL, b * CELL)
    return (a * CELL, line * CELL), (b * CELL, line * CELL)


def openings(rooms, house_cells, rnd):
    """Doors from the living room into each other room, or from the room that has the wall when
    one shares none with the living room, and windows (and one sliding door) on the walls that
    stay outside even when the whole house stands."""
    kinds = sorted(set(rooms.values()), key=lambda k: (k != 'living', k))
    doors = []
    joined = {'living'}
    for kind in kinds[1:]:
        best = None
        for other in sorted(joined, key=lambda k: k != 'living'):
            for axis, line, a, b, normal in runs_between(rooms, lambda c: rooms[c] == kind,
                                                         lambda n: rooms.get(n) == other):
                if b - a >= 5 and (best is None or other == 'living'):
                    best = (axis, line, a, b, normal)
            if best:
                break
        if best:
            axis, line, a, b, normal = best
            start = a + 1 if rnd.random() < 0.5 else b - 4
            p, q = segment(axis, line, start, start + 3)
            doors.append((p, q, normal))
            joined.add(kind)

    #a room that shares no wall with the living room opens off one that does, its door at the
    #near end of the longest wall they share, so no room is ever shut in...
    for kind in kinds[1:]:
        if kind in joined:
            continue
        for other in sorted(joined, key=lambda k: (k != 'living', k)):
            runs = [r for r in runs_between(rooms, lambda c: rooms[c] == kind,
                                            lambda n: rooms.get(n) == other) if r[3] - r[2] >= 5]
            if runs:
                axis, line, a, b, normal = max(runs, key=lambda r: (r[3] - r[2], r[1], r[2]))
                p, q = segment(axis, line, a + 1, a + 4)
                doors.append((p, q, normal))
                joined.add(kind)
                break
    windows, sliders = [], []

    def outside(n):
        return n not in house_cells

    for kind in kinds:
        runs = sorted(runs_between(rooms, lambda c: rooms[c] == kind, outside),
                      key=lambda r: r[3] - r[2], reverse=True)
        for k, (axis, line, a, b, normal) in enumerate(runs[:2]):
            length = b - a
            if kind == 'living' and k == 0 and length >= 12:
                mid = (a + b) / 2
                p, q = segment(axis, line, mid - 4, mid + 4)
                sliders.append((p, q, normal))
            elif length >= 6:
                width = min(4.6, length - 2)
                mid = (a + b) / 2 + rnd.uniform(-1, 1) * max(0, (length - width - 2) / 4)
                p, q = segment(axis, line, mid - width / 2, mid + width / 2)
                windows.append((p, q, normal))
    return doors, windows, sliders


# ── the whole house ───────────────────────────────────────────────────────


def walkable(rooms, doors, sliders) -> bool:
    """Whether an empty suite passes the walkway rule, so furnishing has a chance."""
    import rules
    if not doors:
        return False
    polys = [dict(poly=outline({c for c, k in rooms.items() if k == kind}))
             for kind in sorted(set(rooms.values()))]
    entry = sliders[0][:2] if sliders else doors[0][:2]
    return rules.walkway_ok(polys, doors, entry)


def woods_for(owner, order, rnd):
    """A floor wood for each suite, never the same as a neighbour's."""
    adj = {s: set() for s in order}
    for c, s in owner.items():
        for n in neighbours(c):
            t = owner.get(n)
            if t is not None and t != s:
                adj[s].add(t)
    names, out = ['honey', 'amber', 'walnut'], {}
    for s in order:
        free = [w for w in names if w not in {out.get(t) for t in adj[s]}] or names
        out[s] = rnd.choice(free)
    return out


def generate(seed):
    """One house: its suites in the order they are built, each with rooms, doors, windows, a floor
    wood and its grid block, and `reveal`, the order the app shows them in (`sweep`). A house whose
    suites lack a room, or whose empty suites fail the walkway rule, is cut again from a fresh roll."""
    for attempt in range(20):
        rnd = random.Random(f'{seed}:{attempt}')
        owner, cores = blocks(rnd)
        owner = interlock(owner, rnd)
        house_cells = set(owner)
        splits = {s: split_rooms({c for c, t in owner.items() if t == s}, rnd, cores[s])
                  for s in set(owner.values())}
        holes = {s: openings(r, house_cells, rnd) for s, r in splits.items()}
        if all(len(set(r.values())) == 3 for r in splits.values()) and \
                all(len(holes[s][0]) == 2 for s in splits) and \
                all(walkable(splits[s], holes[s][0], holes[s][2]) for s in splits):
            break
    order = build_order(owner, rnd)
    woods = woods_for(owner, order, rnd)
    suites = []
    for s in order:
        rooms = splits[s]
        doors, windows, sliders = holes[s]
        polys = [(kind, outline({c for c, k in rooms.items() if k == kind}))
                 for kind in sorted(set(rooms.values()), key=lambda k: (k != 'living', k))]
        suites.append(dict(rooms=polys, doors=doors, windows=windows, sliders=sliders,
                           cells={c for c, t in owner.items() if t == s}, room_of=rooms,
                           floor=woods[s], block=s))
    return dict(seed=seed, suites=suites, reveal=sweep(suites))


def sweep(suites):
    """The order the app shows suites in, as indices into `suites`: the corner suite with the most
    glass first, then by blocks away from it to the opposite corner, row by row within a step, so
    every prefix is one piece."""
    at = {su['block']: i for i, su in enumerate(suites)}

    #glass is window and sliding-door length, so the lone first suite looks out the most...
    def glass(b):
        su = suites[at[b]]
        return sum(math.dist(p, q) for p, q, _ in su['windows'] + su['sliders'])

    r0, c0 = divmod(max((0, 2, 6, 8), key=lambda b: (glass(b), -b)), 3)
    return sorted(range(len(suites)), key=lambda i: (
        abs(suites[i]['block'] // 3 - r0) + abs(suites[i]['block'] % 3 - c0), suites[i]['block']))


def preview(house, path: Path):
    """The empty plan: floors, walls, doors and windows, each suite in its own wood."""
    import canvas
    import pen
    import planks
    polys = [p for su in house['suites'] for _, p in su['rooms']]
    xs = [x for p in polys for x, _ in p]
    ys = [y for p in polys for _, y in p]
    m = 60
    ox, oy = m - min(xs), m - min(ys)
    s = canvas.Sheet(max(xs) - min(xs) + 2 * m, max(ys) - min(ys) + 2 * m, pen.C['paper'])
    def moved(poly):
        return [(x + ox, y + oy) for x, y in poly]

    def shift(items):
        return [((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), v) for a, b, v in items]

    for n, su in enumerate(house['suites']):
        ps = [moved(p) for _, p in su['rooms']]
        qx = [x for p in ps for x, _ in p]
        qy = [y for p in ps for _, y in p]
        c = s.uid()
        s.defs.append(f'<clipPath id="{c}">' + ''.join(f'<path d="{pen.poly_d(p)}"/>' for p in ps)
                      + '</clipPath>')
        s.raw(f'<g clip-path="url(#{c})">')
        s.place(planks.plank_floor(f'suite-{n}', max(qx) - min(qx), max(qy) - min(qy),
                              **planks.FLOOR[su['floor']], framed=False), min(qx), min(qy))
        s.raw('</g>')
        for kind, p in su['rooms']:
            px = sum(x for x, _ in p) / len(p) + ox
            py = sum(y for _, y in p) / len(p) + oy
            s.text(px, py, f'{n + 1} {kind}')
    s.rooms([moved(p) for p in polys], shift([x for su in house['suites'] for x in su['doors']]),
            shift([x for su in house['suites'] for x in su['windows']]),
            shift([x for su in house['suites'] for x in su['sliders']]))
    path.write_text(s.svg(canvas.CSS, scale=0.5, lit=False))
    return s.w * 0.5, s.h * 0.5


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != 'preview':
        print(__doc__)
        return 2
    import canvas
    out = Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    seeds = [int(a) for a in argv[3:]] or [1, 2, 3, 4]
    for seed in seeds:
        p = (out / f'plan-{seed}.svg').resolve()
        w, h = preview(generate(seed), p)
        canvas.render([(str(p), math.ceil(w), math.ceil(h), 2)])
        print(p.with_suffix('.png'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
