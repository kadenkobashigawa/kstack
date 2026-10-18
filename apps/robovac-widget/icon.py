#!/usr/bin/env python3
'''
icon — the app's icon, drawn from the house's own pieces: the robot, its dock and the oak floor,
in the house's pen, on macOS's icon grid.

Usage
-----
    icon.py options <out-dir>   the three candidate icons at 1024 px, and a sheet of them small
    icon.py build <option>      mac/AppIcon.icns from one option: docked, sweeping or room, with
                                its 16 and 32 px sizes drawn from the plainer `small` scene

Methods
-------
    squircle :
        the icon's rounded-square outline on the 1024 grid.
    scene :
        one option's floor, pieces and evening light, in centimetres.
    icon_svg :
        one option as a 1024 px SVG on the icon grid.
    main :
        dispatch on the command named first.
'''

from __future__ import annotations

import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import canvas
import decor
import pen
import planks
import vacuum



HERE   = Path(__file__).resolve().parent
GRID   = 1024
BODY   = 824
MARGIN = (GRID - BODY) / 2


# ── the icon's shape ──────────────────────────────────────────────────────────

def squircle(x0: float, y0: float, size: float, n: float = 5.0, steps: int = 256) -> str:
    '''the superellipse macOS draws its icon body as, |x|^n + |y|^n = 1, as an SVG path.'''
    r, cx, cy, pts = size / 2, x0 + size / 2, y0 + size / 2, []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        pts.append((cx + r * math.copysign(abs(c) ** (2 / n), c),
                    cy + r * math.copysign(abs(s) ** (2 / n), s)))
    return 'M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in pts) + ' Z'


# ── the three options ─────────────────────────────────────────────────────────

def scene(option: str) -> tuple[canvas.Sheet, float]:
    '''
    one option's floor, pieces and evening light, in centimetres.

    Parameters
    ----------
    option : str
        `docked`, the robot backed into its dock; `sweeping`, the robot alone mid-turn on the
        planks; `room`, the robot inside a corner of walls with a plant; or `small`, the sweeping
        robot without brushes or seams, larger and with a heavier pen, for 16 and 32 px.

    Returns
    -------
    tuple
        the sheet, and the side of the square it covers in centimetres.
    '''
    R = vacuum.ROBOT_R
    if option == 'docked':
        S = 84.0
        s = canvas.Sheet(S, S)
        s.place(planks.plank_floor('icon-floor', S, S, framed=False, **planks.FLOOR['honey']), 0, 0)
        dk = vacuum.dock()
        dx, dy = (S - 45) / 2, 6.0
        s.place(vacuum.dock_part(dk, 'mat'), dx, dy)
        s.place(vacuum.robot(), dx + vacuum.DOCKED_AT[0] - R, dy + vacuum.DOCKED_AT[1] - R, 180)
        s.place(vacuum.dock_part(dk, 'tower'), dx, dy)
        return s, S
    if option == 'sweeping':
        S = 60.0
        s = canvas.Sheet(S, S)
        s.place(planks.plank_floor('icon-floor', S, S, framed=False, **planks.FLOOR['honey']), 0, 0)
        s.place(vacuum.robot(seed=3), S / 2 - R, S / 2 - R, -28)
        return s, S
    if option == 'small':
        S = 42.0
        s = canvas.Sheet(S, S, pen.C['oak100'])
        s.place(vacuum.robot(seed=3, part='body'), S / 2 - R, S / 2 - R, -28)
        s.raw(f'<circle cx="{S / 2}" cy="{S / 2}" r="{R - 0.4}" fill="none" '
              f'stroke="{pen.C["line"]}" stroke-width="2.4"/>')
        return s, S
    S, wall = 96.0, 12.0
    s = canvas.Sheet(S, S, pen.C['wall'])
    s.place(planks.plank_floor('icon-floor', S - wall, S - wall, framed=False, **planks.FLOOR['honey']),
            wall, wall)
    s.place(vacuum.robot(seed=5), S * 0.58 - R, S * 0.6 - R, -18)
    s.place(decor.snake_plant(seed=2), wall + 1, wall + 1)
    return s, S


def icon_svg(option: str) -> str:
    '''one option as a 1024 px SVG: the scene clipped to the icon body, dimmed toward its edges.'''
    s, S = scene(option)
    inner = re.sub(r' width="[^"]*" height="[^"]*"', '', s.svg(canvas.CSS, lit=False), count=1)
    inner = inner.replace('<svg ', f'<svg x="{MARGIN}" y="{MARGIN}" width="{BODY}" '
                          f'height="{BODY}" ', 1)
    body = squircle(MARGIN, MARGIN, BODY)
    dim = canvas.AMBIENT
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}" '
            f'width="{GRID}" height="{GRID}"><defs>'
            f'<clipPath id="body"><path d="{body}"/></clipPath>'
            f'<filter id="drop" x="-20%" y="-20%" width="140%" height="140%">'
            f'<feGaussianBlur stdDeviation="14"/></filter>'
            f'<radialGradient id="evening" cx="38%" cy="34%" r="78%">'
            f'<stop offset="0.45" stop-color="#ffffff"/><stop offset="1" stop-color="{canvas.FALLOFF}"/>'
            f'</radialGradient></defs>'
            f'<path d="{body}" fill="{pen.C["wall"]}" opacity="0.32" filter="url(#drop)" '
            f'transform="translate(0 12)"/>'
            f'<g clip-path="url(#body)">{inner}'
            f'<rect x="{MARGIN}" y="{MARGIN}" width="{BODY}" height="{BODY}" fill="{dim}" '
            f'style="mix-blend-mode:multiply" opacity="0.28"/>'
            f'<rect x="{MARGIN}" y="{MARGIN}" width="{BODY}" height="{BODY}" '
            f'fill="url(#evening)" style="mix-blend-mode:multiply" opacity="0.55"/></g>'
            f'<path d="{body}" fill="none" stroke="{pen.C["line"]}" stroke-opacity="0.35" '
            f'stroke-width="3"/></svg>')


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    '''
    dispatch on the command named first.

    Parameters
    ----------
    argv : list of str
        the command line after the script's name.

    Returns
    -------
    int
        0, or 2 with the module's header printed for an unknown command.
    '''
    if argv[:1] == ['options'] and len(argv) > 1:
        out = Path(argv[1]).resolve()
        out.mkdir(parents=True, exist_ok=True)
        jobs = []
        for option in ('docked', 'sweeping', 'room'):
            p = out / f'icon-{option}.svg'
            p.write_text(icon_svg(option))
            jobs.append((str(p), GRID, GRID, 1))
        canvas.render(jobs)
        cells = ''.join(
            f'<g transform="translate({40 + i * 420} 40)">'
            f'<image href="icon-{o}.png" width="256" height="256"/>'
            f'<image href="icon-{o}.png" x="270" y="0" width="64" height="64"/>'
            f'<image href="icon-{o}.png" x="270" y="80" width="32" height="32"/>'
            f'<image href="icon-{o}.png" x="270" y="128" width="16" height="16"/>'
            f'<text x="128" y="292" text-anchor="middle" font-family="-apple-system" '
            f'font-size="20" fill="#3f322c">{o}</text></g>'
            for i, o in enumerate(('docked', 'sweeping', 'room')))
        sheet = out / 'icon-options.svg'
        sheet.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1300 340" '
                         f'width="1300" height="340"><rect width="1300" height="340" '
                         f'fill="#e9e6e1"/>{cells}</svg>')
        canvas.render([(str(sheet), 1300, 340, 1)])
        print(out / 'icon-options.png')
        return 0
    if argv[:1] == ['build'] and len(argv) > 1:
        with tempfile.TemporaryDirectory() as tmp:
            svg = Path(tmp) / 'icon.svg'
            svg.write_text(icon_svg(argv[1]))
            small = Path(tmp) / 'small.svg'
            small.write_text(icon_svg('small'))
            canvas.render([(str(svg), GRID, GRID, 1), (str(small), GRID, GRID, 1)])
            sets = Path(tmp) / 'AppIcon.iconset'
            sets.mkdir()
            for size in (16, 32, 128, 256, 512):
                for scale in (1, 2):
                    px = size * scale
                    name = f'icon_{size}x{size}{"@2x" if scale == 2 else ""}.png'
                    art = small if size <= 32 else svg
                    subprocess.run(['sips', '-z', str(px), str(px), str(art)[:-4] + '.png',
                                    '--out', str(sets / name)], check=True, capture_output=True)
            dest = HERE / 'mac' / 'AppIcon.icns'
            subprocess.run(['iconutil', '-c', 'icns', str(sets), '-o', str(dest)], check=True)
            shutil.copy(str(svg)[:-4] + '.png', HERE / 'mac' / 'AppIcon.png')
        print(dest)
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
