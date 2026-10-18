"""
rules — the layout rules a furnished house is checked against, and the floor grid they and
the robot's route are worked on.

Each constant carries its source; the research is in DESIGN.md. check() returns one line per broken
rule.
"""

from __future__ import annotations

import math

from pen import inside, on_edge
from canvas import PLANT, facing, mapper


OVERHEAD = {'pendant', 'sconce', 'string-lights'}
COVER = {'beni-rug', 'jute-rug', 'stripe-rug', 'doormat'}
TUCK = {'desk-chair', 'dining-chair', 'pouf', 'stool'}
TUCKS_UNDER = {'desk', 'white-desk', 'round-table', 'coffee-table', 'island'}
TOPPER = {'cat'}


BED = {'double-bed', 'single-bed'}
SEATS = {'sofa', 'loveseat', 'sectional', 'armchair'}
DESK = {'desk', 'white-desk'}
FRONT_CLEAR = {'dresser': 75, 'wardrobe': 75, 'bookshelf': 61, 'tv-console': 61}
FREE_TURN = {'pouf', 'basket', 'cat'}

# the rules, in centimetres, each with its source (the research is in DESIGN.md)


ROUTE_NARROW = 81   # narrowing allowed for short runs, such as a doorway: ADA 403.5.1
DOOR_CLEAR = 90     # clear approach on both sides of a door: Approved Doc M 2.22, ADA 404.2.4.1
BED_SIDE = 75       # strip beside a bed and at its foot: Approved Doc M 2.25
NIGHTSTAND = (0, 30)                  # gap to the bed: Merrell et al. 2011, table 1
COFFEE_GAP = (36, 46)                 # sofa front to coffee table: Castlery; Merrell 16-18"
COFFEE_LEN = (0.5, 0.75)              # coffee table / sofa length: Castlery (sources disagree)
CONVERSE = (122, 244)                 # armchair centre to sofa centre: Merrell, after Panero
SEAT_FRONT = 76                       # clear in front of a seat: Merrell table 1
DINING = 81                           # table edge to wall or furniture behind a chair: NKBA 8
ISLAND_WALK = 91                      # walkway round a kitchen island: NKBA 7 (36 in)
ISLAND_WORK = 107                     # work aisle on the side the cook stands: NKBA 6 (42 in)
DESK_BACK = 81                        # desk front to what stands behind the chair: NKBA 8
TV_RANGE = (0.78, 1.57)               # screen to sofa centre / screen diagonal: ITU-R BT.1845-1
BED_RUG = 50                          # rug past the bed's sides: IKEA rug guide
LAMP_NEAR = 30                        # a lamp beside each desk, bed and reading seat: Philips
DOCK_SIDES, DOCK_FRONT = 50, 150      # Roborock user manuals: 0.5 m each side, 1.5 m in front
RUG_LEGS = 8                          # a seat's front legs stand on its rug: the user's rule
ADJACENT = 200                        # no two of one piece this close in a room: the user's rule
ACROSS = 60                           # nor back to back through a wall: the same rule
LAMP_APART = 60                       # nor two lamps side by side: the same rule
BED_DOOR = 180                        # floor inside a doorway a bed keeps off: the user's rule
SEAT_WIDTH = 61                       # width per diner at a 36 in counter: NKBA 9 (24 in)
PAIRED = {'nightstand', 'dining-chair', 'pouf', 'stool'}
OFFICE = {'desk', 'desk-chair'}
KIND = {'white-desk': 'desk', 'loveseat': 'sofa', 'sectional': 'sofa'}


def ray_hits(origin, direction, rect, reach=1000) -> bool:
    """Whether a ray from origin along direction meets an axis-aligned rectangle."""
    (ox, oy), (dx, dy) = origin, direction
    x, y, w, h = rect
    if dx == 0:
        return x <= ox <= x + w and (y + h > oy if dy > 0 else y < oy) and \
            min(abs(y - oy), abs(y + h - oy)) <= reach
    return y <= oy <= y + h and (x + w > ox if dx > 0 else x < ox) and \
        min(abs(x - ox), abs(x + w - ox)) <= reach


def ahead(rect, f, depth, inset=0):
    """The strip of floor in front of a piece, as wide as its front and depth deep."""
    x, y, w, h = rect
    return {(0, 1): (x + inset, y + h, w - 2 * inset, depth),
            (0, -1): (x + inset, y - depth, w - 2 * inset, depth),
            (1, 0): (x + w, y + inset, depth, h - 2 * inset),
            (-1, 0): (x - depth, y + inset, depth, h - 2 * inset)}[f]


def centre(r):
    return (r[0] + r[2] / 2, r[1] + r[3] / 2)


def front_legs(rect, f, inset=RUG_LEGS):
    """Where a seat's two front legs stand: its front corners, drawn in by the inset."""
    x, y, w, h = rect
    return {(0, 1): [(x + inset, y + h - inset), (x + w - inset, y + h - inset)],
            (0, -1): [(x + inset, y + inset), (x + w - inset, y + inset)],
            (1, 0): [(x + w - inset, y + inset), (x + w - inset, y + h - inset)],
            (-1, 0): [(x + inset, y + inset), (x + inset, y + h - inset)]}[f]


def inside_rect(p, r) -> bool:
    return r[0] <= p[0] <= r[0] + r[2] and r[1] <= p[1] <= r[1] + r[3]


def lamp(ink) -> bool:
    """Whether a piece standing on the floor carries a lamp: a lit dresser, nightstand or table."""
    return ink.name not in OVERHEAD and any(op[0] == 'light' for op in ink.ops)


def twins(a, b, office=False) -> bool:
    """Whether two pieces are the same piece, so may not stand side by side; a set that comes as
    one, such as a bed's two nightstands, is not, and nor are the desks of an office, a room with
    a desk and no double bed, which seats as many people as it has desks."""
    if office and KIND.get(a, a) in OFFICE:
        return False
    return KIND.get(a, a) == KIND.get(b, b) and a not in PAIRED


def landings(doors, depth=BED_DOOR, widen=0):
    """The floor straight in through each doorway, on both its sides: as wide as the opening, and
    depth deep."""
    out = []
    for (ax, ay), (bx, by), *_ in doors:
        x1, x2, y1, y2 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
        if x1 == x2:
            out += [(x1 - depth, y1 - widen, depth, y2 - y1 + 2 * widen),
                    (x1, y1 - widen, depth, y2 - y1 + 2 * widen)]
        else:
            out += [(x1 - widen, y1 - depth, x2 - x1 + 2 * widen, depth),
                    (x1 - widen, y1, x2 - x1 + 2 * widen, depth)]
    return out


def gap(a, b) -> float:
    """The clear distance between two rectangles, 0 when they touch or overlap."""
    dx = max(b[0] - (a[0] + a[2]), a[0] - (b[0] + b[2]), 0)
    dy = max(b[1] - (a[1] + a[3]), a[1] - (b[1] + b[3]), 0)
    return math.hypot(dx, dy)


def floor_grid(su, solid, cell=5):
    """The suite's floor as a grid: which cells are floor, and how far each is from the nearest
    wall or footprint. The robot drives on this grid too. A cell is judged by its centre: off the
    floor, inside a wall (but not a doorway) or inside a footprint, it is blocked."""
    polys = [r['poly'] for r in su['rooms']]
    xs = [p[0] for q in polys for p in q]
    ys = [p[1] for q in polys for p in q]
    x0, y0 = min(xs), min(ys)
    nx, ny = int((max(xs) - x0) / cell) + 1, int((max(ys) - y0) / cell) + 1

    def span(lo, hi, origin, n):
        #the cells whose centres fall strictly between lo and hi...
        a = math.floor((lo - origin) / cell - 0.5) + 1
        b = math.ceil((hi - origin) / cell - 0.5) - 1
        return range(max(a, 0), min(b, n - 1) + 1)

    #the floor, a row at a time: each row's centre line crosses every outline an even number of
    #times, and the cells between pairs of crossings are inside...
    floor = set()
    for q in polys:
        edges = list(zip(q, q[1:] + q[:1]))
        for j in range(ny):
            y = y0 + (j + 0.5) * cell
            cross = sorted(x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                           for (x1, y1), (x2, y2) in edges if (y1 > y) != (y2 > y))
            for a, b in zip(cross[::2], cross[1::2]):
                floor.update((i, j) for i in span(a, b, x0, nx))

    def cells_in(rect):
        x, y, w, h = rect
        return {(i, j) for i in span(x, x + w, x0, nx) for j in span(y, y + h, y0, ny)}

    doors = set()
    for a, b, _ in su['doors']:
        doors |= cells_in((min(a[0], b[0]) - 8, min(a[1], b[1]) - 8, abs(b[0] - a[0]) + 16,
                           abs(b[1] - a[1]) + 16))
    walls = set()
    for q in polys:
        for (ax, ay), (bx, by) in zip(q, q[1:] + q[:1]):
            walls |= cells_in((min(ax, bx) - 7, min(ay, by) - 7, abs(bx - ax) + 14,
                               abs(by - ay) + 14))
    blocked = {(i, j) for j in range(ny) for i in range(nx)} - floor
    blocked |= walls - doors
    for _, _, fp in solid:
        blocked |= cells_in(fp)
    dist = {}
    from collections import deque
    q = deque((b, b) for b in blocked)
    seen = set(blocked)
    for b in blocked:
        dist[b] = 0.0
    while q:
        (i, j), src = q.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            n = (i + di, j + dj)
            if 0 <= n[0] < nx and 0 <= n[1] < ny and n not in seen:
                seen.add(n)
                dist[n] = math.hypot(n[0] - src[0], n[1] - src[1]) * cell
                q.append((n, src))
    return dict(x0=x0, y0=y0, cell=cell, nx=nx, ny=ny, dist=dist, blocked=blocked)


def reachable(g, starts, radius):
    from collections import deque
    def ok(c):
        return c in g['dist'] and g['dist'][c] > radius
    q, seen = deque(c for c in starts if ok(c)), set(c for c in starts if ok(c))
    while q:
        i, j = q.popleft()
        for n in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if n not in seen and ok(n):
                seen.add(n)
                q.append(n)
    return seen


def walkway_ok(rooms, doors, entry, solids=(), cell=10) -> bool:
    """The walkway rule on its own: every doorway reachable from the entry along a path 81 cm
    wide, on a grid of the given cell size. Rooms are dicts with a poly; solids are rectangles."""
    g = floor_grid(dict(rooms=rooms, doors=doors), [('', '', r) for r in solids], cell=cell)

    def at(pt):
        return (int((pt[0] - g['x0']) / g['cell']), int((pt[1] - g['y0']) / g['cell']))

    a, b = entry
    start = at(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    near = 70 / cell
    wide = reachable(g, [c for c in g['dist'] if math.dist(c, start) < near], ROUTE_NARROW / 2)
    for a, b, _ in doors:
        m = at(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        if not any(math.dist(c, m) < near for c in wide):
            return False
    return True


def check(suites, around=()) -> list[str]:
    """Every layout rule a script can test, from the research in DESIGN.md. Around is the pieces
    of the suites already standing next door, as (name, footprint), so no piece is doubled back
    to back through a suite's wall. Returns one line per broken rule, naming the rule."""
    out = []
    for su in suites:
        placed, solid, lights, lamps = [], [], [], []
        for r in su['rooms']:
            for ink, x, y, rot, rect in r['items']:
                placed.append((r, ink, rot, rect))
                if lamp(ink):
                    lamps.append((r['name'], footprint(ink, rect)))
                tw = mapper(ink, x, y, rot)
                lights += [tw((op[1], op[2])) for op in ink.ops if op[0] == 'light']
                if ink.name not in COVER | OVERHEAD | TOPPER:
                    solid.append((r['name'], ink.name, footprint(ink, rect)))
        dk, dx, dy, drot = su['dock']
        dw, dd = dk.dims(drot)
        dock_rect = (dx, dy, dw, dd)
        solid.append(('dock', 'dock', dock_rect))
        walls_of = {r['name']: r['poly'] for r in su['rooms']}
        def room_of(pt):
            return next((n for n, q in walls_of.items() if inside(pt, q)), None)
        def in_floor(rect):
            return all(room_of(p) for p in (
                (rect[0] + 1, rect[1] + 1), (rect[0] + rect[2] - 1, rect[1] + 1),
                (rect[0] + 1, rect[1] + rect[3] - 1), (rect[0] + rect[2] - 1, rect[1] + rect[3] - 1)))
        def free(rect, skip=()):
            return [n for room, n, fp in solid if n not in skip and overlap(fp, rect, -1)]

        offices = {r['name'] for r in su['rooms']
                   if {ink.name for ink, *_ in r['items']} & DESK
                   and 'double-bed' not in {ink.name for ink, *_ in r['items']}}

        # footprints never overlap, except a chair or pouf tucked under its table
        for a in range(len(solid)):
            for b in range(a + 1, len(solid)):
                (ra, na, fa), (_, nb, fb) = solid[a], solid[b]
                (rb, _, _) = solid[b]
                tucked = ({na, nb} & TUCK) and ({na, nb} & TUCKS_UNDER or {na, nb} <= TUCK)
                if not tucked and overlap(fa, fb, -1):
                    out.append(f'{ra}: {na} overlaps {nb}')
                near = ADJACENT if ra == rb else ACROSS
                if twins(na, nb, ra == rb and ra in offices) and gap(fa, fb) < near:
                    out.append(f'{ra}: two of the {KIND.get(na, na)} stand within {near} cm')
        for room, n, fp in solid:
            for m, fp2 in around:
                if twins(n, m) and gap(fp, fp2) < ACROSS:
                    out.append(f'{room}: the {n} stands back to back with one next door')

        for a in range(len(lamps)):
            for b in range(a + 1, len(lamps)):
                if lamps[a][0] == lamps[b][0] and gap(lamps[a][1], lamps[b][1]) < LAMP_APART:
                    out.append(f'{lamps[a][0]}: two lamps stand within {LAMP_APART} cm')

        # every room has a way in
        ways = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                for a, b, *_ in su['doors'] + su.get('sliders', []) + [su['entry']]]
        for r in su['rooms']:
            if not any(on_edge(m, r['poly']) for m in ways):
                out.append(f'{r["name"]}: has no doorway')

        # a bed keeps off the floor just inside a doorway, which is left for coming in
        for room, n, fp in solid:
            if n in BED and any(overlap(fp, z, -1) for z in landings(su['doors'])):
                out.append(f'{room}: the {n} stands in front of a doorway')

        # doors: a clear approach on both sides
        for (ax, ay), (bx, by), _ in su['doors'] + [su['entry'] + (None,)]:
            x1, x2, y1, y2 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
            zone = ((x1 - DOOR_CLEAR, y1, 2 * DOOR_CLEAR, y2 - y1) if x2 - x1 < y2 - y1 else
                    (x1, y1 - DOOR_CLEAR, x2 - x1, 2 * DOOR_CLEAR))
            for n in free(zone):
                out.append(f'door at {round(x1)},{round(y1)}: {n} stands in its approach')

        # the main route: every doorway reachable from the entry at full walkway width
        g = floor_grid(su, solid)
        def cell(pt):
            return (int((pt[0] - g['x0']) / g['cell']), int((pt[1] - g['y0']) / g['cell']))
        mids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b, _ in su['doors']]
        (ea, eb) = su['entry']
        entry = ((ea[0] + eb[0]) / 2, (ea[1] + eb[1]) / 2)
        near = [c for c in g['dist'] if math.dist(c, cell(entry)) < 14]
        wide = reachable(g, near, ROUTE_NARROW / 2)
        for m in mids:
            if not any(math.dist(c, cell(m)) < 14 for c in wide):
                out.append(f'route: the doorway at {round(m[0])},{round(m[1])} cannot be '
                           f'reached {ROUTE_NARROW} cm wide from the entry')
        su['grid'] = g

        for r, ink, rot, rect in placed:
            n, f = ink.name, facing(rot)
            here = [(r2, ik, ro, rr) for r2, ik, ro, rr in placed if r2 is r]
            if n not in FREE_TURN and rot % 90:
                out.append(f'{r["name"]}: {n} is not square to the walls')
            if n in BED:
                foot = ahead(rect, f, BED_SIDE)
                for m in free(foot, {n} | TUCK):
                    out.append(f'{r["name"]}: {m} stands in the {BED_SIDE} cm at the foot of the {n}')
                sides = [ahead(rect, (f[1], f[0]), BED_SIDE), ahead(rect, (-f[1], -f[0]), BED_SIDE)]
                headroom = 60
                trimmed = []
                for sx, sy, sw, sh in sides:
                    if f == (0, 1):
                        trimmed.append((sx, sy + headroom, sw, sh - headroom))
                    elif f == (0, -1):
                        trimmed.append((sx, sy, sw, sh - headroom))
                    elif f == (1, 0):
                        trimmed.append((sx + headroom, sy, sw - headroom, sh))
                    else:
                        trimmed.append((sx, sy, sw - headroom, sh))
                usable = [t for t in trimmed if in_floor(t) and not free(t, {n, 'nightstand'})]
                if len(usable) < (2 if n == 'double-bed' else 1):
                    out.append(f'{r["name"]}: the {n} needs {BED_SIDE} cm clear beside it on '
                               f'{"both sides" if n == "double-bed" else "one side"}')
                rugs = [rr for rr2, ik, ro, rr in here if ik.name in COVER and overlap(rr, rect)]
                for rr in rugs:
                    rx, ry, rw, rh = rr
                    bx, by, bw, bh = rect
                    if f[1] != 0 and (rx > bx - BED_RUG or rx + rw < bx + bw + BED_RUG):
                        out.append(f'{r["name"]}: the rug under the {n} must reach {BED_RUG} cm '
                                   'past both its sides')
                    if f[0] != 0 and (ry > by - BED_RUG or ry + rh < by + bh + BED_RUG):
                        out.append(f'{r["name"]}: the rug under the {n} must reach {BED_RUG} cm '
                                   'past both its sides')
            if n == 'nightstand':
                beds = [rr for _, ik, _, rr in here if ik.name in BED]
                if beds and min(gap(rect, b) for b in beds) > NIGHTSTAND[1]:
                    out.append(f'{r["name"]}: a nightstand stands more than {NIGHTSTAND[1]} cm from '
                               'its bed')
            if n in SEATS:
                front = ahead(rect, f, SEAT_FRONT, 10)
                bad = free(front, {n, 'coffee-table', 'pouf', 'side-table'} | TUCK)
                if bad or not in_floor(front):
                    out.append(f'{r["name"]}: the {n} needs {SEAT_FRONT} cm clear in front '
                               f'({", ".join(bad) or "a wall"})')
                tables = [rr for _, ik, _, rr in here if ik.name in ('side-table', 'nightstand')
                          and gap(rect, rr) <= 30]
                coffee = [rr for _, ik, _, rr in here if ik.name == 'coffee-table' and
                          ray_hits(centre(rect), f, rr, 46 + rect[3])]
                if not tables and not coffee:
                    out.append(f'{r["name"]}: the {n} has no table beside or in front of it')
                rugs = [rr for _, ik, _, rr in here if ik.name in COVER - {'doormat'}
                        and gap(rect, rr) <= 40]
                legs = front_legs(rect, f)
                if rugs and not any(all(inside_rect(p, rr) for p in legs) for rr in rugs):
                    out.append(f'{r["name"]}: the {n} does not stand with its front legs on the rug')
            if n in ('sofa', 'loveseat', 'sectional'):
                tvs = [rr for _, ik, _, rr in here if ik.name == 'tv-console']
                if not any(ray_hits(centre(rect), f, t) for t in tvs):
                    out.append(f'{r["name"]}: the {n} does not face the TV')
                for t in tvs:
                    d = gap(rect, t) + (rect[3] if f[1] != 0 else rect[2]) / 2
                    if not TV_RANGE[0] * 165 <= d <= TV_RANGE[1] * 165:
                        out.append(f'{r["name"]}: the TV is {round(d)} cm from the {n}, outside '
                                   f'{round(TV_RANGE[0] * 165)} to {round(TV_RANGE[1] * 165)}')
                for _, ik, _, rr in here:
                    if ik.name == 'coffee-table' and ray_hits(centre(rect), f, rr):
                        g2 = gap(rect, rr)
                        if not COFFEE_GAP[0] <= g2 <= COFFEE_GAP[1]:
                            out.append(f'{r["name"]}: the coffee table is {round(g2)} cm from the '
                                       f'{n}, outside {COFFEE_GAP[0]} to {COFFEE_GAP[1]}')
                        span = rr[2] if f[1] != 0 else rr[3]
                        length = rect[2] if f[1] != 0 else rect[3]
                        if not COFFEE_LEN[0] <= span / length <= COFFEE_LEN[1]:
                            out.append(f'{r["name"]}: the coffee table is {span / length:.2f} of the '
                                       f'{n}\'s length, outside {COFFEE_LEN[0]} to {COFFEE_LEN[1]}')
            if n == 'armchair':
                rugs = [rr for _, ik, _, rr in here if ik.name in COVER and overlap(rr, rect)]
                sofas = [rr for _, ik, _, rr in here if ik.name in ('sofa', 'loveseat', 'sectional')
                         and any(overlap(rr, rug) for rug in rugs)]
                for so in sofas:
                    d = math.dist(centre(rect), centre(so))
                    if not CONVERSE[0] <= d <= CONVERSE[1]:
                        out.append(f'{r["name"]}: the armchair sits {round(d)} cm from the sofa, '
                                   f'outside conversation distance {CONVERSE[0]} to {CONVERSE[1]}')
            if n == 'round-table':
                chairs = [rr for _, ik, _, rr in here if ik.name == 'dining-chair']
                sides = [v for v in ((0, 1), (0, -1), (1, 0), (-1, 0))
                         if any(overlap(ahead(rect, v, 40), c) for c in chairs)]
                for v in sides:
                    behind = ahead(rect, v, DINING)
                    for room, m, fp in solid:
                        if room == r['name'] and m not in TUCK | {'round-table'} and \
                                overlap(behind, fp, -1):
                            out.append(f'{room}: {m} is within {DINING} cm behind a dining chair')
                    if not in_floor(behind):
                        out.append(f'{r["name"]}: a dining chair is within {DINING} cm of a wall')
            if n == 'island':
                for v in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    for room, m, fp in solid:
                        if room == r['name'] and m not in {'island', 'stool'} and \
                                overlap(ahead(rect, v, ISLAND_WALK), fp, -1):
                            out.append(f'{room}: {m} is within {ISLAND_WALK} cm of the island')
                for side in [ahead(rect, d, ISLAND_WALK) for d in ((0, 1), (0, -1), (1, 0), (-1, 0))]:
                    if not in_floor(side):
                        out.append(f'{r["name"]}: the island is within {ISLAND_WALK} cm of a wall')
                        break
            if n in DESK:
                back = ahead(rect, f, DESK_BACK, 5)
                bad = free(back, {n, 'desk-chair'})
                if bad or not in_floor(back):
                    out.append(f'{r["name"]}: the {n} needs {DESK_BACK} cm behind its chair '
                               f'({", ".join(bad) or "a wall"})')
            if n in FRONT_CLEAR:
                front = ahead(rect, f, FRONT_CLEAR[n], 5)
                bad = free(front, {n} | TUCK - {'desk-chair'})
                if bad or not in_floor(front):
                    out.append(f'{r["name"]}: the {n} needs {FRONT_CLEAR[n]} cm clear in front '
                               f'({", ".join(bad) or "a wall"})')
            if n in BED | DESK | {'armchair'}:
                if not any(gap(rect, (lx, ly, 0, 0)) <= LAMP_NEAR for lx, ly in lights):
                    out.append(f'{r["name"]}: the {n} has no lamp within {LAMP_NEAR} cm')

        # windows and sliding doors only on outer walls, never where another suite joins on,
        # and nothing tall standing in front of a window
        others = [r['poly'] for o in suites if o is not su for r in o['rooms']]
        own = [r['poly'] for r in su['rooms']]
        for (ax, ay), (bx, by), (nx, ny) in su.get('windows', []) + su.get('sliders', []):
            mx, my = (ax + bx) / 2, (ay + by) / 2
            outside = (mx - nx * 12, my - ny * 12)
            if any(inside(outside, q) for q in others):
                out.append(f'opening at {round(mx)},{round(my)}: faces another suite, not outside')
            if any(inside(outside, q) for q in own):
                out.append(f'opening at {round(mx)},{round(my)}: is on an inner wall')
            x1, x2, y1, y2 = min(ax, bx), max(ax, bx), min(ay, by), max(ay, by)
            zone = ((x1, y1 + (7 if ny > 0 else -67), x2 - x1, 60) if ny else
                    (x1 + (7 if nx > 0 else -67), y1, 60, y2 - y1))
            for room, name, fp in solid:
                if name in ('wardrobe', 'bookshelf') and overlap(fp, zone, -1):
                    out.append(f'{room}: the {name} stands in front of a window')

        # the dock: 0.5 m clear each side and 1.5 m in front, so the robot can leave and return
        f = facing(drot)
        for zone in (ahead(dock_rect, f, DOCK_FRONT), ahead(dock_rect, (f[1], f[0]), DOCK_SIDES),
                     ahead(dock_rect, (-f[1], -f[0]), DOCK_SIDES)):
            bad = free(zone, {'dock'})
            if bad:
                out.append(f'dock: {", ".join(sorted(set(bad)))} within its clearance')
    return out


def overlap(a, b, gap=0.0) -> bool:
    return (a[0] < b[0] + b[2] + gap and b[0] < a[0] + a[2] + gap and
            a[1] < b[1] + b[3] + gap and b[1] < a[1] + a[3] + gap)


def footprint(ink, rect):
    """What a piece occupies on the floor: a plant only its pot, a rug and an overhead light
    nothing."""
    x, y, w, d = rect
    if ink.name in PLANT:
        return (x + w / 2 - 16, y + d / 2 - 16, 32, 32)
    return rect
