#!/usr/bin/env python3
"""
draw — the widget's catalog pieces on a sheet, to look at.

Usage
-----
    draw.py catalog <out-dir>   every piece on one sheet, as SVG and 2x PNG
    draw.py floors <out-dir>    the floor swatches, each with the robot on it for scale
    draw.py variations <out-dir>  every piece in its versions
    draw.py house <out-dir>     the house with one, two and three rooms open, on the glass

The pieces are drawn by furniture.py, decor.py and vacuum.py, the floors by planks.py, laid
out and checked by layout.py and rules.py, in the pen and on the sheet of pen.py and
canvas.py. DESIGN.md holds the palette and the rules.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from pen import C
from canvas import CSS, Sheet, render
from furniture import (
    armchair, coffee_table, desk, desk_chair, dining_chair, double_bed, nightstand, round_table,
    sectional, side_table, single_bed, sofa, white_desk,
)
from decor import (
    basket, beni_rug, cat, fiddle_leaf, floor_lamp, jute_rug, monstera, pouf, rubber_plant,
    snake_plant,
)
from vacuum import dock, robot
from planks import floors
from layout import HOUSE, house


def catalog() -> Sheet:
    s = Sheet(920, 720, C['paper'])
    rows = [
        ('Beds', 30, 36), ('Desks', 380, 36), ('Robot and dock', 690, 36),
        ('Tables', 30, 300), ('Decor', 480, 300),
    ]
    for t, x, y in rows:
        s.text(x, y, t, 'title')
    items = [
        (double_bed(), 30, 50, 0, 'double bed'),
        (single_bed(), 190, 50, 0, 'single bed'),
        (nightstand(), 300, 50, 0, 'nightstand'),
        (desk(), 380, 50, 0, None),
        (desk_chair(), 417, 116, 0, 'walnut desk and chair'),
        (white_desk(), 530, 50, 0, 'white desk'),
        (dock(), 700, 50, 0, 'dock'),
        (robot(), 782, 62, 0, 'robot'),
        (dining_chair(), 108, 422, 0, None),
        (dining_chair(1), 108, 306, 180, None),
        (dining_chair(2), 50, 364, 90, None),
        (dining_chair(3), 166, 364, 270, None),
        (round_table(), 80, 336, 0, None),
        (coffee_table(), 262, 356, 0, 'coffee table'),
        (side_table(), 400, 363, 0, 'side table'),
        (monstera(), 480, 316, 0, 'monstera'),
        (fiddle_leaf(), 595, 326, 0, 'fiddle-leaf fig'),
        (rubber_plant(), 685, 320, 0, 'rubber plant'),
        (snake_plant(), 790, 346, 0, 'snake plant'),
        (floor_lamp(), 852, 346, 0, 'floor lamp'),
        (beni_rug(), 30, 520, 90, 'Beni rug'),
        (jute_rug(), 290, 530, 0, 'jute rug'),
        (pouf(), 460, 545, 0, 'knit pouf'),
        (basket(), 535, 550, 0, 'basket'),
        (cat(), 605, 548, 0, 'cat'),
    ]
    for ink, x, y, rot, label in items:
        s.place(ink, x, y, rot)
        if label:
            w, d = ink.dims(rot)
            s.text(x + w / 2, y + d + 16, label)
    s.text(130, 486, 'round table, bentwood chairs')
    return s


def variations() -> Sheet:
    """Every piece in its versions, so rooms drawn from one catalog still differ."""
    s = Sheet(1000, 1220, C['paper'])
    rows = [
        ('Beds', 50, [
            (double_bed(), 0, 'walnut, linen, cognac'),
            (double_bed(1, 'oak', 'sage', 'oat'), 0, 'oak, sage, oat'),
            (double_bed(2, 'black', 'oat', 'grey'), 0, 'black, oat, grey'),
            (single_bed(), 0, 'black, oat, grey'),
            (single_bed(1, 'oak', 'sage', 'cognac'), 0, 'oak, sage, cognac'),
            (nightstand(), 0, 'walnut'), (nightstand(1, 'oak'), 0, 'oak'),
            (nightstand(2, 'black'), 0, 'black')]),
        ('Couches', 335, [
            (sofa(), 0, 'sofa, oat'), (sofa(1, 'sage', 'oat', 2), 0, 'loveseat, sage'),
            (sectional(), 0, 'sectional, linen'), (armchair(), 0, 'armchair, cognac'),
            (armchair(1, 'sage'), 0, 'armchair, sage')]),
        ('Desks', 545, [
            (desk(), 0, 'laptop'), (desk(1, 'walnut', 'dual'), 0, 'two monitors'),
            (desk(2, 'oak', 'writing'), 0, 'writing'), (white_desk(), 0, 'white desk'),
            (desk_chair(), 0, 'cognac'), (desk_chair(1, 'linen'), 0, 'linen'),
            (desk_chair(2, 'sage'), 0, 'sage')]),
        ('Tables', 680, [
            (round_table(), 0, 'flowers'), (round_table(1, 'oak', 'tea'), 0, 'tea'),
            (dining_chair(), 0, 'walnut'), (dining_chair(1, 'oak'), 0, 'oak'),
            (dining_chair(2, 'black'), 0, 'black'), (coffee_table(), 0, 'notepad'),
            (coffee_table(1, 'oak', 'books'), 0, 'books'), (side_table(), 0, 'black'),
            (side_table(1, 'walnut'), 0, 'walnut')]),
        ('Plants and soft things', 850, [
            (monstera(), 0, 'white pot'), (monstera(1, 'basket'), 0, 'basket pot'),
            (fiddle_leaf(), 0, 'white pot'), (fiddle_leaf(1, 'black'), 0, 'black pot'),
            (rubber_plant(), 0, 'white pot'), (rubber_plant(1, 'basket'), 0, 'basket pot'),
            (snake_plant(), 0, 'black pot'), (snake_plant(1, 'white'), 0, 'white pot'),
            (floor_lamp(), 0, 'linen'), (floor_lamp(1, 'oat'), 0, 'oat')]),
        (None, 1070, [
            (pouf(), 0, 'oat'), (pouf(1, 'sage'), 35, 'sage'), (pouf(2, 'cognac'), -20, 'cognac'),
            (basket(), 30, 'cognac'), (basket(1, 'grey'), -40, 'grey'),
            (cat(), 0, 'ginger'), (cat(1, 'grey'), 40, 'grey'), (cat(2, 'black'), -65, 'black'),
            (cat(3, 'cream'), 110, 'cream')]),
    ]
    for title, y, items in rows:
        if title:
            s.text(30, y - 16, title, 'title')
        x = 30
        for ink, rot, label in items:
            w, d = ink.dims(rot)
            px, py = x + (w - ink.w) / 2, y + (d - ink.d) / 2
            s.place(ink, px, py, rot)
            s.text(x + w / 2, y + d + 16, label)
            x += w + 26
    return s


SHEETS = {'catalog': catalog, 'floors': floors, 'variations': variations}


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in (*SHEETS, 'house'):
        print(__doc__)
        return 2
    out = Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    files = []
    if argv[1] == 'house':
        for n in range(1, len(HOUSE) + 1):
            sheet, scale = house(n), 0.56 if n == 1 else 0.46
            p = (out / f'house-{n}.svg').resolve()
            p.write_text(sheet.svg(CSS, scale))
            render([(str(p), math.ceil(sheet.w * scale), math.ceil(sheet.h * scale), 2)])
            files.append(p)
    else:
        sheet = SHEETS[argv[1]]()
        files = [(out / f'{argv[1]}.svg').resolve()]
        files[0].write_text(sheet.svg(CSS))
        render([(str(p), sheet.w, sheet.h, 2) for p in files])
    print('\n'.join(str(p.with_suffix('.png')) for p in files))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
