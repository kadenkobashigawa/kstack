"""
vacuum — the robot, its dock and the ! that floats over it when a run stops.
"""

from __future__ import annotations

import math

from pen import C, dense
from canvas import Ink, recorded


# ── the robot and its dock ────────────────────────────────────────────────


ROBOT_R = 17.65
BRUSH_HUBS = ((-12.4, -10.5), (12.4, -10.5))


def robot(seed=0, part='whole'):
    """The Qrevo Curv 2 Flow from above, front up the page. The widget draws it in parts: the
    body turns with the robot, while its shadow and its shine stay put, so the light keeps
    falling from the upper left; each side brush is its own part, spinning on its hub."""
    R = ROBOT_R
    if part == 'brush':
        k = Ink('brush', 22, 22, 0, C['chr700'], seed)
        for j in range(3):
            a = math.radians(-90 + j * 120)
            k.mark([(11, 11), (11 + 9.5 * math.cos(a), 11 + 9.5 * math.sin(a))], 'bristle')
        k.form(k.circ(11, 11, 1.6, wob=0, n=8), C['chr400'], relief=0, line='line thin')
        return k
    k = Ink('robot', 2 * R, 2 * R, 12, C['chr700'], seed)
    c = R
    if part == 'body':
        k.form(k.circ(c, c, R, wob=0.08, n=26), C['rwhite'], relief=0)
        w = math.sqrt(R ** 2 - 6.5 ** 2) - 0.6
        k.mark([(c - w, c - 6.5), (c, c - 7.6), (c + w, c - 6.5)], 'detail')
        k.form(k.rr(c - 4.8, c - 15.4, 9.6, 3.6, 1.8, wob=0.04, step=3), C['rgrey'], relief=0)
        k.flat(k.circ(c - 2.1, c - 13.6, 0.7, wob=0, n=6), C['chr700'])
        k.flat(k.circ(c + 2.1, c - 13.6, 0.7, wob=0, n=6), C['chr700'])
        k.form(k.circ(c, c - 3, 4.9, wob=0.05, n=14), C['rwhite'], relief=0)
        k.mark(k.circ(c, c - 3, 3.1, wob=0.04, n=12), 'detail', closed=True)
        k.mark([(c - 3.5, c + 10.5), (c + 3.5, c + 10.5)], 'detail faint')
        return k
    for sx in (-1, 1):
        hx, hy, ph = c + sx * 12.4, c - 10.5, k.rnd.uniform(0, 120)
        for j in range(3):
            a = math.radians(ph + j * 120)
            k.mark([(hx, hy), (hx + 9.5 * math.cos(a), hy + 9.5 * math.sin(a))], 'bristle')
    k.form(k.circ(c, c, R, wob=0.08, n=26), C['rwhite'], relief=1.4, cast=12)
    w = math.sqrt(R ** 2 - 6.5 ** 2) - 0.6
    k.mark([(c - w, c - 6.5), (c, c - 7.6), (c + w, c - 6.5)], 'detail')
    k.form(k.rr(c - 4.8, c - 15.4, 9.6, 3.6, 1.8, wob=0.04, step=3), C['rgrey'], relief=0.4)
    k.flat(k.circ(c - 2.1, c - 13.6, 0.7, wob=0, n=6), C['chr700'])
    k.flat(k.circ(c + 2.1, c - 13.6, 0.7, wob=0, n=6), C['chr700'])
    k.form(k.circ(c, c - 3, 4.9, wob=0.05, n=14), C['rwhite'], relief=0.9)
    k.mark(k.circ(c, c - 3, 3.1, wob=0.04, n=12), 'detail', closed=True)
    k.mark([(c - 3.5, c + 10.5), (c + 3.5, c + 10.5)], 'detail faint')
    return k


@recorded
def dock(seed=0, part='whole'):
    """The multifunctional dock: a white hood over a grey tower, and the mat the robot drives up
    onto, its ramp's curved lip in front. In parts, the mat lies on the floor under the robot and
    the tower stands over it, so a docked robot tucks its back half under the hood."""
    k = Ink('dock', 45, 61, 45, C['chr700'], seed)
    if part in ('whole', 'mat'):
        lip = [(1, 43), (44, 43), (44.6, 52), (40, 58.6), (22.5, 60.6), (5, 58.6), (0.4, 52)]
        k.form(lip, C['dgrey'], relief=1)
        k.mark([(6, 49), (39, 49)], 'detail')
        k.mark([(7, 54), (38, 54)], 'detail')
    if part in ('whole', 'tower'):
        k.form(k.rr(0, 0, 45, 45, (12, 12, 6, 6), wob=0.12), C['dgrey'], relief=1, cast=45)
        k.form(k.rr(1.6, 1.2, 41.8, 41.6, (13, 13, 6, 6), wob=0.1), C['dwhite'], relief=2.2)
        k.mark([(5, 30), (22.5, 31.2), (40, 30)], 'detail')
        k.mark([(19.5, 30.9), (22.5, 33.6), (25.5, 30.9)], 'detail')
    return k


def alert(seed=0, fill=C['lin50']):
    """The mark over a stopped run's robot: a cream !, alone, in the house's pen; inked, it is the
    small ! that opens the hover slip's why."""
    k = Ink('alert', 14, 30, 6, C['line'], seed)
    cast = 4 if fill == C['lin50'] else None
    bar = dense([(3.4, 4.2), (7, 1.6), (10.6, 4.2), (8.9, 19.4), (7, 20.6), (5.1, 19.4)], True, 0.3)
    k.form(bar, fill, relief=1.2, cast=cast, straight=True)
    k.form(k.circ(7, 25.6, 2.9, wob=0.04, n=14), fill, relief=1.2, cast=cast)
    return k


#where a docked robot's middle sits on the dock: back half under the hood, front half on the mat...
DOCKED_AT = (22.5, 41)


def dock_part(dk, part):
    """One part of a dock already made, drawn from what it recorded."""
    _, args, kw = getattr(dk, 'made', ('dock', [], {}))
    return dock(*args, **{**kw, 'part': part})
