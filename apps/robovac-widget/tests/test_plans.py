#!/usr/bin/env python3
"""
test_plans — checks the order the app shows a house's suites in (plans.sweep) for every house the
build ships.

Run it with `python3 tests/test_plans.py`. It generates the plans for houses 1, 12 and 14, which
takes no rendering, and reads app/build/data.js when a build is there. The exit code is the number
of failed checks.

O1 starts at the corner suite with the most glass, O2 ends at the opposite corner, O3 moves one
block further from the start at most per step, O4 keeps every prefix one piece, and O5 holds that
the built data.js lists its suites in that order. O6 starts at a corner even when an edge suite
has more glass. O7 holds that widget.py build marks its folder local before drawing.

O8 and O9 hold that neighbouring suites never share a floor wood, on a block of four suites and in
the three shipped houses. O10 holds that a route sweeps lanes across an open floor, end to end. O11
holds that rules.check reports a piece standing in a door's, or the entry's, approach. O12 holds
that a living room too awkward for a television group counts as failing, in furnish_rooms and in
what furnished hands back.
"""

from __future__ import annotations

import json
import math
import random
import sys
import tempfile
from pathlib import Path


HERE    = Path(__file__).resolve().parent
WIDGET  = HERE.parent
SEEDS   = (1, 12, 14)
RESULTS = []

sys.path.insert(0, str(WIDGET))

import furnish  # noqa: E402
import plans  # noqa: E402
import rules  # noqa: E402
import widget  # noqa: E402



def check(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if not ok and detail else ''))


def glass(su: dict) -> float:
    """a suite's window and sliding-door length."""
    return sum(math.dist(p, q) for p, q, _ in su['windows'] + su['sliders'])


def touching(a: dict, b: dict) -> bool:
    """whether two suites share a wall: some cell of one sits beside a cell of the other."""
    return any((x + dx, y + dy) in b['cells'] for x, y in a['cells']
               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def wood_clashes() -> int:
    """neighbouring pairs sharing a floor wood, over 200 rolls of woods_for on four touching suites."""
    owner = {(0, 0): 0, (1, 0): 1, (0, 1): 2, (1, 1): 3}
    return sum(woods[a] == woods[b] for roll in range(200)
               for woods in [plans.woods_for(owner, [0, 1, 2, 3], random.Random(roll))]
               for a, b in ((0, 1), (0, 2), (1, 3), (2, 3)))


def sweep_lanes() -> tuple[list, int, int]:
    """the route over an open 80 by 60 cell floor, its lane spacing in cells, and the lane rows."""
    g = dict(cell=5, nx=80, ny=60, dist={(i, j): 99 for i in range(80) for j in range(60)})
    step = max(1, round(widget.LANE / g['cell']))
    return widget.coverage(g, (0, 0)), step, len(range(0, g['ny'], step))


def approach_lines(su: dict, door: tuple, entry: bool) -> list[str]:
    """rules.check's lines about an approach, with `door` made one of the suite's doors or its entry."""
    changed = dict(su, entry=door[:2]) if entry else dict(su, doors=[door] + su['doors'][1:])
    return [ln for ln in rules.check([changed]) if 'approach' in ln]


def main() -> int:
    orders = {}
    for seed in SEEDS:
        house = plans.generate(seed)
        suites = [house['suites'][i] for i in house['reveal']]
        blocks = [su['block'] for su in suites]
        orders[seed] = house['reveal']
        corners = [su for su in house['suites'] if su['block'] in (0, 2, 6, 8)]
        r0, c0 = divmod(blocks[0], 3)
        steps = [abs(b // 3 - r0) + abs(b % 3 - c0) for b in blocks]
        check(f'O1 house {seed} starts at the corner suite with the most glass',
              blocks[0] in (0, 2, 6, 8) and glass(suites[0]) == max(map(glass, corners)), str(blocks))
        check(f'O2 house {seed} ends at the opposite corner', blocks[-1] == 8 - blocks[0], str(blocks))
        check(f'O3 house {seed} moves one block further at most per step',
              all(0 <= b - a <= 1 for a, b in zip(steps, steps[1:])) and sorted(blocks) == list(range(9)),
              str(steps))
        check(f'O4 house {seed} shows one piece whatever the number of runs',
              all(any(touching(suites[k], s) for s in suites[:k]) for k in range(1, len(suites))),
              str(blocks))
    fake = [dict(block=b, windows=[((0, 0), (900 if b == 1 else 100 * (b in (0, 2, 6, 8)), 0), None)],
                 sliders=[]) for b in range(9)]
    first = fake[plans.sweep(fake)[0]]['block']
    check('O6 a corner comes first even when an edge suite has more glass', first in (0, 2, 6, 8),
          str(first))
    data = WIDGET / 'app' / 'build' / 'data.js'
    if data.exists():
        built = json.loads(data.read_text().split('=', 1)[1].rstrip().rstrip(';'))
        dirs = {h['seed']: [int(su['dir'].rstrip('/').split('/')[-1]) for su in h['suites']]
                for h in built['houses']}
        check('O5 the built data.js lists every house\'s suites in that order',
              all(dirs.get(s) == orders[s] for s in SEEDS), str(dirs))
    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp) / 'build'
        build.mkdir()
        (build / '.pack').write_text('robovac-images-x')
        try:
            widget.main(['widget.py', 'build', tmp, 'not-a-seed'])
        except ValueError:
            pass
        check('O7 a widget.py build marks the folder local before it draws anything',
              not (build / '.pack').exists())
    houses = [plans.generate(seed) for seed in SEEDS]
    shared = [(h['seed'], a['block'], b['block']) for h in houses
              for i, a in enumerate(h['suites']) for b in h['suites'][i + 1:]
              if touching(a, b) and a['floor'] == b['floor']]
    check('O8 woods_for gives touching suites different floor woods, over 200 rolls',
          wood_clashes() == 0, str(wood_clashes()))
    check('O9 no two touching suites of a shipped house share a floor wood', not shared, str(shared))
    route, step, lanes = sweep_lanes()
    rows = sorted({c[1] for c in route if c[1] % step == 0})
    ends = {(c[0], c[1]) for c in route}
    check('O10 a route over open floor sweeps every lane, end to end',
          rows == list(range(0, 60, step)) and len(rows) == lanes
          and all((0, j) in ends and (79, j) in ends for j in rows), str(rows))
    su = furnish.house(1, 1)[0]
    name, (x, y, w, h) = next((n, fp) for n, fp in furnish.solids_of(su) if n != 'rug')
    door = ((x + w / 2, y + h / 2 - 40), (x + w / 2, y + h / 2 + 40), None)
    wide = ((x + w / 2 - 40, y + h + 40), (x + w / 2 + 40, y + h + 40), None)
    check('O11 rules.check reports a piece standing in a door\'s approach, and in the entry\'s, '
          'whether the door runs up and down or across',
          not [ln for ln in rules.check([su]) if 'approach' in ln]
          and any(f'{name} stands in its approach' in ln for ln in approach_lines(su, door, False))
          and any(f'{name} stands in its approach' in ln for ln in approach_lines(su, door, True))
          and any(f'{name} stands in its approach' in ln for ln in approach_lines(su, wide, False))
          and any(f'{name} stands in its approach' in ln for ln in approach_lines(su, wide, True)),
          str(approach_lines(su, door, False)) + str(approach_lines(su, wide, False)))
    plan = plans.generate(1)['suites'][0]
    place, tries = furnish.Suite.place, furnish.TRIES
    furnish.TRIES = 1
    furnish.Suite.place = lambda self, kind, group, rnd, away=None: (
        group.name != 'tv' and place(self, kind, group, rnd, away))
    try:
        missing = furnish.furnish_rooms(furnish.Suite(plan, (), None), plan, random.Random('o12'))
        _, broken = furnish.furnished(plan, 'o12')
    finally:
        furnish.Suite.place, furnish.TRIES = place, tries
    check('O12 a living room that holds no television group is a missing piece, and failing',
          'living: television group' in missing and 'missing living: television group' in broken,
          f'{missing} {broken}')
    failed = RESULTS.count(False)
    print(f'{len(RESULTS) - failed}/{len(RESULTS)} passed')
    return failed


if __name__ == '__main__':
    sys.exit(main())
