"""
layout — the hand-laid house, a suite laid out in it, and the sheet that draws laid-out suites.
"""

from __future__ import annotations

import math
import sys

from pen import poly_d
from canvas import PLANT, Part, Sheet, curtains, mapper
from furniture import (
    armchair, coffee_table, desk, desk_chair, dining_chair, double_bed, dresser, nightstand,
    pendant, round_table, sconce, side_table, single_bed, sofa, string_lights, tv_console,
    wardrobe,
)
from decor import (
    CAT_PIVOTS, basket, beni_rug, cat, doormat, fiddle_leaf, floor_lamp, jute_rug, monstera, pouf,
    rubber_plant, stripe_rug,
)
from vacuum import dock, dock_part, robot
from planks import FLOOR, plank_floor
from rules import COVER, centre, check


UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)


def plan_a(v):
    """The first floor plan: a bedroom, an L-shaped study with a reading nook, and a living room
    with dining, about 8.8 by 8.4 m. Laid out to the clearance rules in check(); v picks the
    variation: woods, fabrics, setups, coats and seeds."""
    n = v['seed']
    wd, wl = v['wood'], v['wood2']
    return dict(
        rooms=[
            dict(name='bedroom',
                 poly=[(0, 0), (480, 0), (480, 420), (0, 420)],
                 rugs=[(lambda: beni_rug(n, 170, 250), 115, 140, 90)],
                 pieces=[(lambda: monstera(n, v['pot']), -14, -14, 0),
                         (lambda: nightstand(n, wd), 125, 7, 0),
                         (lambda: nightstand(n + 1, wd), 313, 7, 0),
                         (lambda: double_bed(n, wd, v['duvet'], v['throw']), 170, 7, 0),
                         (Part(cat, n, v['cat']), 215, 135, 25),
                         (lambda: string_lights(250, n), 115, 8, 0),
                         (lambda: fiddle_leaf(n + 3), 400, 0, 0),
                         (lambda: wardrobe(n, wd), 413, 100, 90),
                         (lambda: dresser(n, wd), 7, 230, 270),
                         (lambda: pouf(n, v['pouf']), 128, 305, 15),
                         (lambda: pouf(n + 1, v['pouf']), 285, 310, -20),
                         (lambda: coffee_table(n, wd, 'notepad'), 180, 300, 0),
                         (lambda: desk_chair(n + 3, v['seat']), 377, 307, 180),
                         (lambda: desk(n + 3, wd, 'writing'), 340, 353, 180),
                         (lambda: basket(n, v['throw']), 195, 368, 30)]),
            dict(name='study',
                 poly=[(480, 0), (880, 0), (880, 600), (640, 600), (640, 420), (480, 420)],
                 rugs=[(lambda: jute_rug(n), 696, 440, 0),
                       (lambda: stripe_rug(n, 205, 230), 600, 75, 90)],
                 pieces=[(lambda: desk_chair(n, v['seat']), 552, 62, 0),
                         (lambda: desk(n, wd, v['desk']), 500, 7, 0),
                         (lambda: fiddle_leaf(n, 'black'), 800, 0, 0),
                         (lambda: single_bed(n + 2, wd, 'linen', v['throw']), 668, 130, 90),
                         (lambda: side_table(n, wd, 'lamp'), 826, 228, 0),
                         (lambda: dresser(n + 1, wd), 487, 200, 270),
                         (lambda: armchair(n, v['chair']), 720, 508, 180),
                         (lambda: sconce(n), 755, 581, 180),
                         (lambda: side_table(n + 1, wd, 'lamp'), 668, 540, 0),
                         (lambda: floor_lamp(n, 'oat'), 822, 546, 0)]),
            dict(name='living room',
                 poly=[(0, 420), (640, 420), (640, 600), (880, 600), (880, 840), (0, 840)],
                 rugs=[(lambda: beni_rug(n + 1, 180, 270), 120, 545, 90),
                       (lambda: jute_rug(n + 1, 220), 440, 560, 0),
                       (lambda: doormat(n), 435, 780, 0)],
                 pieces=[(lambda: tv_console(n, wl), 175, 427, 0),
                         (lambda: sconce(n + 1), 147, 427, 0), (lambda: sconce(n + 2), 343, 427, 0),
                         (lambda: rubber_plant(n + 1), 550, 418, 0),
                         (lambda: coffee_table(n + 1, wl, 'books'), 200, 560, 0),
                         (lambda: sofa(n, v['sofa'], v['pillows']), 150, 660, 180),
                         (Part(cat, n + 1, v['cat2']), 235, 668, 100),
                         (lambda: armchair(n + 2, v['pillows']), 40, 555, 270),
                         (lambda: side_table(n + 2, wl, 'lamp'), 60, 650, 0),
                         (lambda: floor_lamp(n + 1), 100, 705, 0),
                         (lambda: fiddle_leaf(n + 4), -6, 766, 0),
                         (lambda: dining_chair(n, wl), 528, 706, 0),
                         (lambda: dining_chair(n + 1, wl), 528, 590, 180),
                         (lambda: dining_chair(n + 2, wl), 470, 648, 90),
                         (lambda: dining_chair(n + 3, wl), 586, 648, 270),
                         (lambda: round_table(n, wl, v['table']), 500, 620, 0),
                         (lambda: pendant(n), 528, 648, 0),
                         (lambda: dresser(n + 3, wl), 700, 607, 0),
                         (lambda: monstera(n + 1, 'basket'), 794, 754, 0)]),
        ],
        doors=[((20, 420), (110, 420), UP), ((490, 420), (580, 420), UP)],
        windows=[((0, 90), (0, 200), RIGHT), ((680, 0), (790, 0), DOWN),
                 ((0, 660), (0, 770), RIGHT)],
        sliders=[((360, 840), (600, 840), UP)],
        entry=((360, 840), (600, 840)),
        dock=(812, 680, 90), robot=(430, 480))


HOUSE = [
    dict(plan=plan_a, at=(0, 0), mirror=False, floor='honey',
         v=dict(seed=0, wood='walnut', wood2='oak', duvet='linen', throw='cognac', cat='ginger',
                cat2='grey', pot='white', pouf='cognac', seat='cognac', desk='dual',
                chair='cognac', sofa='oat', pillows='sage', table='tea')),
    dict(plan=plan_a, at=(880, 160), mirror=True, floor='amber',
         v=dict(seed=10, wood='oak', wood2='walnut', duvet='sage', throw='oat', cat='black',
                cat2='cream', pot='black', pouf='sage', seat='linen', desk='laptop',
                chair='sage', sofa='linen', pillows='cognac', table='flowers')),
]


ROTATE_MIRROR = {90: 270, 270: 90}


def laid_out(su):
    """A suite as it stands in the house: its plan, mirrored if asked, moved to its place. Every
    piece comes back with its footprint, so the layout can be checked before it is drawn."""
    plan, (ax, ay), mir = su['plan'](su['v']), su['at'], su['mirror']
    W = max(x for r in plan['rooms'] for x, _ in r['poly'])
    fx = (lambda x: ax + W - x) if mir else (lambda x: ax + x)
    rooms = []
    for r in plan['rooms']:
        items = []
        for kind, entries in (('rug', r['rugs']), ('piece', r['pieces'])):
            for make, x, y, rot in entries:
                ink = make()
                w, d = ink.dims(rot)
                free = rot % 90 != 0
                cx = x + (ink.w if free else w) / 2
                cy = y + (ink.d if free else d) / 2
                if mir:
                    cx, rot = W - cx, -rot if free else ROTATE_MIRROR.get(rot, rot)
                px = cx - (ink.w if free else w) / 2
                items.append((ink, ax + px, ay + y, rot, (ax + cx - w / 2, ay + cy - d / 2, w, d)))
        rooms.append(dict(name=r['name'], poly=[(fx(x), ay + y) for x, y in r['poly']], items=items))
    doors = [((fx(a[0]), ay + a[1]), (fx(b[0]), ay + b[1]), (-into[0], into[1]) if mir else into)
             for a, b, into in plan['doors']]
    entry = tuple((fx(p[0]), ay + p[1]) for p in plan['entry'])
    flip = (lambda v: (-v[0], v[1])) if mir else (lambda v: v)
    openings = {key: [((fx(a[0]), ay + a[1]), (fx(b[0]), ay + b[1]), flip(into))
                      for a, b, into in plan.get(key, [])] for key in ('windows', 'sliders')}
    dx, dy, drot = plan['dock']
    dk = dock()
    dw, dd = dk.dims(drot)
    dock_at = (fx(dx) - dw if mir else ax + dx, ay + dy, ROTATE_MIRROR.get(drot, drot) if mir else drot)
    rx, ry = plan['robot']
    robot_at = (fx(rx) - 35.3 if mir else ax + rx, ay + ry)
    return dict(floor=su['floor'], rooms=rooms, doors=doors, entry=entry, dock=(dk,) + dock_at,
                robot=robot_at, **openings)


SWAY = PLANT


def house(n: int, layered=False) -> Sheet:
    """The first n suites of the hand-laid house."""
    suites = [laid_out(su) for su in HOUSE[:n]]
    for line in check(suites):
        print('layout:', line, file=sys.stderr)
    return house_sheet(suites, layered)


def house_sheet(suites, layered=False, margin=46, pad=30, frame=None) -> Sheet:
    """Laid-out suites, one per run, floating on the glass. A suite has one floor throughout;
    its rooms open into each other through doorways, and suites meet at solid walls. Everything
    stands inside the walls, so a plant's leaves never reach past them. Layered, the robots are
    left out (the widget drives them) and the pieces that move become sprites. A frame, the
    offset and size of a whole house, places one suite where it stands in that house."""
    rooms = [r for su in suites for r in su['rooms']]
    xs = [p[0] for r in rooms for p in r['poly']]
    ys = [p[1] for r in rooms for p in r['poly']]
    ox, oy = pad + margin - min(xs), pad + margin - min(ys)
    W = max(xs) - min(xs) + 2 * (margin + pad)
    H = max(ys) - min(ys) + 2 * (margin + pad)
    if frame:
        (ox, oy), (W, H) = frame
    s = Sheet(W, H)
    s.glass_panel(pad, pad, W - 2 * pad, H - 2 * pad, 30, backdrop=not layered)
    s.offset, s.suites = (ox, oy), suites
    def moved(poly):
        return [(x + ox, y + oy) for x, y in poly]
    inside_walls = s.uid()
    s.inside = inside_walls
    s.defs.append(f'<clipPath id="{inside_walls}">' + ''.join(
        f'<path d="{poly_d(moved(r["poly"]))}"/>' for r in rooms) + '</clipPath>')
    for k, su in enumerate(suites):
        polys = [moved(r['poly']) for r in su['rooms']]
        qx, qy = [p[0] for q in polys for p in q], [p[1] for q in polys for p in q]
        c = s.uid()
        s.defs.append(f'<clipPath id="{c}">' + ''.join(f'<path d="{poly_d(q)}"/>' for q in polys)
                      + '</clipPath>')
        s.raw(f'<g clip-path="url(#{c})">')
        s.place(plank_floor(f'suite-{k}-floor', max(qx) - min(qx), max(qy) - min(qy),
                            **FLOOR[su['floor']], framed=False), min(qx), min(qy))
        s.raw('</g>')
    for r in rooms:
        for ink, x, y, rot, _ in r['items']:
            if ink.name in COVER:
                s.place(ink, x + ox, y + oy, rot)

    #each dock's mat lies on the floor, under its robot...
    for su in suites:
        dk, dx, dy, drot = su['dock']
        s.place(dock_part(dk, 'mat'), dx + ox, dy + oy, drot)
    s.floor_light()
    s.raw('<!--layer:furniture-->')
    s.raw(f'<g clip-path="url(#{inside_walls})">')
    for r in rooms:
        own = s.uid()
        poly = moved(r['poly'])
        s.defs.append(f'<clipPath id="{own}"><path d="{poly_d(poly)}"/></clipPath>')
        s.raw(f'<g clip-path="url(#{own})">')
        for ink, x, y, rot, rect in r['items']:
            if ink.name in COVER:
                continue
            cx, cy = centre(rect)
            if layered and ink.name == 'cat':
                for part in ('tail', 'ear-l', 'ear-r', 'body'):
                    piece_ = ink.remake(part=part)
                    px, py = mapper(piece_, x + ox, y + oy, rot)(CAT_PIVOTS.get(part, (19, 26)))
                    sid = f'cat-{len(s.sprites)}-{part}'
                    s.sprites[sid] = dict(kind=part.split('-')[0], px=px, py=py, cx=cx + ox,
                                          cy=cy + oy)
                    s.raw(f'<!--sprite:{sid}--><g clip-path="url(#{own})">')
                    s.place(piece_, x + ox, y + oy, rot)
                    s.raw('</g><!--/sprite-->')
                continue
            moving = layered and ink.name in SWAY
            if moving:
                sid = f'{ink.name}-{len(s.sprites)}'
                s.sprites[sid] = dict(kind='sway', px=cx + ox, py=cy + oy, cx=cx + ox, cy=cy + oy,
                                      room=poly)
                s.raw(f'<!--sprite:{sid}--><g clip-path="url(#{own})">')
            s.place(ink, x + ox, y + oy, rot)
            if moving:
                s.raw('</g><!--/sprite-->')
        s.raw('</g>')
    for su in suites:
        dk, dx, dy, drot = su['dock']
        if not layered:
            s.place(robot(), su['robot'][0] + ox, su['robot'][1] + oy, (drot + 180) % 360)
        s.place(dock_part(dk, 'tower'), dx + ox, dy + oy, drot)
    s.raw('</g>')
    def shift(key):
        return [((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), into)
                for su in suites for a, b, into in su[key]]

    s.raw(f'<g clip-path="url(#{inside_walls})">')
    for n, window in enumerate(shift('windows')):
        still, tails = curtains(window, 14, n)
        if layered:
            s.curtain_windows.append(window)
            continue
        s.place(still, 0, 0)
        for tail, _, _ in tails:
            s.place(tail, 0, 0)

    #the sliding door has its curtains too, drawn open and still: the door stays shut...
    for n, door in enumerate(shift('sliders')):
        still, _ = curtains(door, 14, 100 + n)
        s.place(still, 0, 0)
    s.raw('</g>')
    windows = shift('windows')
    for meta in s.sprites.values():
        if meta['kind'] == 'sway':
            near = min((math.dist((meta['px'], meta['py']), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
                        for a, b, _ in windows), default=1e9)
            meta['amp'] = 6.5 if near < 200 else 3.6
    s.rooms([moved(r['poly']) for r in rooms], shift('doors'), windows, shift('sliders'))
    return s
