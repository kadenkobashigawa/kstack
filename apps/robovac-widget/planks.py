"""
planks — the plank floors a suite stands on.
"""

from __future__ import annotations

from pen import C, mix, place
from canvas import Ink, Sheet
from vacuum import robot


# ── floors ────────────────────────────────────────────────────────────────


FLOOR = {
    'honey': dict(tones=[C['oak100'], C['oak100'], C['oak50'], C['oak200']],
                  seam=mix(C['oak200'], C['oak500'], 0.55)),
    'amber': dict(tones=['#d6a672', '#cf9c66', '#dcb07d', '#c4905e'],
                  seam=mix('#c4905e', C['wal700'], 0.45), grain='amber', bw=19, lengths=(100, 190)),
    'walnut': dict(tones=[C['wal300'], C['wal300'], '#b07a55', C['wal500']], seam=C['wal700'],
                   grain='walnut', bw=20, lengths=(110, 200)),
}


def box(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def board(k, pts_local, cx, cy, ang, L, w, tones, grain, gap=0.45):
    """One floorboard: a slightly bevelled plank, grain running its length, now and then a knot."""
    tone = mix(k.rnd.choice(tones), C['wal700'] if grain == 'walnut' else C['oak300'],
               k.rnd.uniform(0, 0.12))
    k.form(place(pts_local, cx, cy, ang), tone, relief=0.7, line=None)
    for _ in range(k.rnd.choice((1, 1, 2))):
        u, v = k.rnd.uniform(-L / 2 + 6, L / 2 - 26), k.rnd.uniform(-w / 2 + 2.6, w / 2 - 2.6)
        gl = k.rnd.uniform(12, 26)
        k.mark(place([(u, v), (u + gl / 2, v + k.rnd.uniform(-1, 1)), (u + gl, v)], cx, cy, ang),
               f'grain {grain}')
    if k.rnd.random() < 0.07:
        u, v = k.rnd.uniform(-L / 2 + 8, L / 2 - 8), k.rnd.uniform(-w / 2 + 3, w / 2 - 3)
        k.mark(place(k.blob(u, v, 1.6, 1, wob=0.05, n=8), cx, cy, ang), 'knot', closed=True)


def floor_frame(name, W, H, seam, framed=True):
    k = Ink(name, W, H, 0)
    edge = k.rr(0, 0, W, H, 4, wob=0.2) if framed else box(0, 0, W, H)
    k.begin_clip(edge, straight=not framed)
    k.poly(box(-4, -4, W + 8, H + 8), seam)
    return k, edge


def plank_floor(name, W, H, tones, seam, grain='light', bw=18.0, lengths=(90, 180),
                framed=True):
    """Planks running across the room, joints staggered row to row."""
    k, edge = floor_frame(name, W, H, seam, framed)
    y = 0.0
    while y < H:
        x = -k.rnd.uniform(0, lengths[1])
        while x < W:
            L = k.rnd.uniform(*lengths)
            local = k.rr(-L / 2 + 0.45, -bw / 2 + 0.45, L - 0.9, bw - 0.9, 0.8, wob=0.08, step=9)
            board(k, local, x + L / 2, y + bw / 2, 0, L, bw, tones, grain)
            x += L
        y += bw
    k.end_clip()
    if framed:
        k.mark(edge, 'line', closed=True)
    return k


def floors() -> Sheet:
    S, gap = 170, 26
    s = Sheet(3 * S + 4 * gap, S + 90, C['paper'])
    for n, name in enumerate(FLOOR):
        x = gap + n * (S + gap)
        s.place(plank_floor(f'{name}-floor', S, S, **FLOOR[name]), x, 30)
        s.text(x + S / 2, 30 + S + 22, f'{name} planks')
        s.place(robot(), x + S / 2 - 17.65, 30 + S / 2 - 17.65)
    return s
