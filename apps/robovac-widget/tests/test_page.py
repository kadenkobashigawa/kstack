#!/usr/bin/env python3
"""
test_page — loads the house page in WebKit and checks how runs open, move, stop and dock.

Run it with the Python in $ROBOVAC_PY, or python3 when that is unset, as
test_icon.sh does; it needs Playwright, its WebKit and Pillow, as requirements-dev.txt pins them:
`"${ROBOVAC_PY:-python3}" tests/test_page.py [app folder]`. It reads `app/`
beside this folder, or the app folder named first. The exit code is 1 if any check fails.

P1 picks the house by `house=<seed>`. P2, P3 and P6 hold that a run already working when the page
opens is out on its lanes from the first frame, at the place its age reaches, and drives on
smoothly. P4 and P7 give every stop its ! for the ten minutes the shell sends as its hold, P21 for
whatever hold its run carries, with none of the page's own, and P22 keeps the suite of a run gone
with no stop logged half a minute after its robot docks; P7 and P8 zoom the camera in on a robot as
it docks, never on one sent out again first, which docks before it goes back out (P8), and P24
keeps one stopped again before it docks docked; P20 brings the house back from a followed robot at
Escape or 0, and P23 jumps the camera with reduced motion. P9 and P10 place every ! over its robot
and inside the whole-house view, and P11 inks the hover slip's !. P12 frames a new run's room after
a dock zoom, P13 keeps a scroll out at the whole-house view from zooming in, and P14 and P16 keep a
right or control click from panning. P15 frames a new run in a room already shown. P5 starts a later
run from its dock. P17 shows the run's line in the hover slip and names each stop, a wait on the
person included, P18 keeps one suite for a run that stops and starts again between two reads, and
P19 has a stopped run's suite take its session's later stop, its why, its run and its hold, and
leaves a suite whose hold has lapsed to go.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


app = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / 'app'
url = f'file://{app}/index.html?app'
fails = []


def check(name, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + name + (f'  [{detail}]' if detail else ''))
    if not ok:
        fails.append(name)


def page(b, opening=None, query='', reduced=False):
    pg = b.new_page(viewport={'width': 560, 'height': 420},
                    reduced_motion='reduce' if reduced else 'no-preference')
    pg.goto(url + query)
    pg.wait_for_function('window.robovac && robovac.runs')

    # the app's first sync, sent once the page has loaded, with each run's start from its age...
    if opening is not None:
        pg.evaluate('runs => robovac.sync(runs.map(r => Object.assign(r, '
                    '{start: Date.now() / 1000 - r.age})))', opening)
    return pg


#the hold the app's shell sends with every run, Runs.swift's showStopFor: ten minutes...
HOLD = 600


def slip(pg, k=0):
    """the hover slip's line and why, read with the pointer over robot k."""
    x, y = pg.evaluate("""k => { const v = robovac.view(), [x, y] = robovac.states().map(r => [r.x, r.y])[k];
      return [v.tx + x * v.s, v.ty + y * v.s]; }""", k)
    pg.mouse.move(x, y)
    pg.wait_for_timeout(400)
    return pg.evaluate("""() => [(document.querySelector('.tip.shown .tip-say') || {}).textContent || '',
      (document.querySelector('.tip.shown .tip-why') || {}).textContent || '']""")


def run(age, **kw):
    """a run of session a, working, `age` seconds old."""
    return dict({'id': 'a', 'age': age, 'say': '', 'state': 'live', 'why': '', 'at': 0, 'hold': HOLD},
                **kw)


with sync_playwright() as p:
    b = p.webkit.launch()

    # P1: house=<seed> picks that house, every load...
    pg = page(b)
    seeds = pg.evaluate('ROBOVAC.houses.map(h => h.seed)')
    pg.close()
    want = seeds[-1]
    boxes = set()
    for _ in range(4):
        pg = page(b, query=f'&house={want}')
        boxes.add(json.dumps(pg.evaluate('ROBOVAC.houses.find(h => h.seed === %d).suites[0].box' % want)
                             == pg.evaluate('robovac.boxes()[0]')))
        pg.close()
    check('P1 house=<seed> names the house', boxes == {'true'}, f'seeds {seeds}, matched {boxes}')

    # P22: two runs going, then one gone from the shell's list with no stop logged: its robot docks,
    # and the page, kept open while the checks below run, notes when its suite leaves...
    held = page(b, None, f'&house={want}&speed=8')
    began = time.time() - 30
    held.evaluate(f"robovac.sync({json.dumps([dict(run(30), start=began), dict(run(30), id='b', start=began + 1)])})")
    held.wait_for_timeout(500)
    held.evaluate(f"robovac.sync({json.dumps([dict(run(30), start=began)])})")
    held.evaluate("""() => { window.docked = null; window.dropped = null; setInterval(() => {
      const r = robovac.states()[1];
      if (window.docked === null && r && r.state === 'docked') window.docked = Date.now();
      if (window.dropped === null && robovac.runs() === 1) window.dropped = Date.now(); }, 100); }""")
    held.wait_for_function('window.docked !== null', timeout=30000)

    # P2: a run 196 s old at open is running at once, off its dock...
    now = time.time()
    pg = page(b, [run(196)], f'&house={want}')
    pg.wait_for_timeout(60)
    st = pg.evaluate('robovac.states()')[0]
    dock = pg.evaluate('robovac.docks()')[0]
    off = abs(st['x'] - dock[0]) + abs(st['y'] - dock[1])
    check('P2 an opening run is running at first frame', st['state'] == 'running', st['state'])
    check('P2b and is out on its lanes, away from the dock', off > 40, f'{off:.0f} px from the dock')
    a196 = (round(st['x']), round(st['y']))
    pg.close()

    # P3: it starts at the waypoint its age reaches going round the route at 24 px/s...
    route = None
    got, want_at = {}, {}
    for age in (5, 120, 400):
        pg = page(b, [run(age)], f'&house={want}')
        pg.wait_for_timeout(60)
        st = pg.evaluate('robovac.states()')[0]
        th = float(pg.evaluate("document.querySelector('.robot > div').style.transform")[7:-4])
        running = pg.evaluate("document.querySelector('.robot').classList.contains('running')")
        route = pg.evaluate('ROBOVAC.houses.find(h => h.seed === %d).suites[0].robot.route' % want)
        pg.close()
        legs = [math.hypot(route[(i + 1) % len(route)][0] - route[i][0],
                           route[(i + 1) % len(route)][1] - route[i][1]) for i in range(len(route))]
        left, i = (age * 24) % sum(legs), 0
        while i < len(legs) - 1 and left > legs[i]:
            left -= legs[i]
            i += 1
        got[age] = (round(st['x']), round(st['y']), round(th % 360) % 360, running)
        q = route[(i + 1) % len(route)]
        face = math.degrees(math.atan2(q[0] - route[i][0], -(q[1] - route[i][1])))
        want_at[age] = (round(route[i][0]), round(route[i][1]), round(face % 360) % 360, True)
    check('P3 the place follows the run\'s age', got == want_at and len(set(got.values())) == 3,
          f'got {got}, want {want_at}')

    # P6: once out, it drives on without jumping: no step over 6 px between 100 ms samples...
    pg = page(b, [run(120)], f'&house={want}')
    pts = []
    for _ in range(40):
        pts.append(pg.evaluate("(() => { const m = new DOMMatrix(getComputedStyle("
                               "document.querySelector('.robot')).transform); return [m.e, m.f]; })()"))
        pg.wait_for_timeout(100)
    pg.close()
    step = max(math.hypot(b2[0] - a2[0], b2[1] - a2[1]) for a2, b2 in zip(pts, pts[1:]))
    check('P6 the opening robot drives on smoothly', step < 6, f'largest step {step:.1f} px')
    went = sum(math.hypot(b2[0] - a2[0], b2[1] - a2[1]) for a2, b2 in zip(pts, pts[1:]))
    check('P6b and keeps driving', went > 30, f'{went:.0f} px in 4 s')

    # P4: a run that stopped 11 min ago is past its 10 min hold, so no ! shows; one 1 min ago shows...
    marks = {}
    for age in (11, 1):
        pg = page(b, [run(3600, state='stopped', why='api error', at=now - age * 60)], f'&house={want}')
        pg.wait_for_timeout(1500)
        marks[age] = pg.evaluate("document.querySelectorAll('.alert.shown').length")
        pg.close()
    check('P4 a stop past its hold shows no !', marks[11] == 0, f'{marks}')
    check('P4b a recent stop shows its !', marks[1] == 1, f'{marks}')

    # P7: a working run that stops goes home, shows its !, and the camera settles on its dock...
    pg = page(b, None, f'&house={want}&speed=8')
    began = time.time() - 30
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), start=began)])})")
    pg.wait_for_timeout(300)
    fit_s = pg.evaluate('robovac.view().s')
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), state='stopped', why='finished', start=began, at=time.time())])})")
    for _ in range(100):
        if pg.evaluate('robovac.states()[0].state') == 'docked':
            break
        pg.wait_for_timeout(100)
    pg.wait_for_timeout(2500)
    v = pg.evaluate('robovac.view()')
    dock = pg.evaluate('robovac.docks()[0]')
    cx = (560 / 2 - v['tx']) / v['s']
    cy = (420 / 2 - v['ty']) / v['s']
    alert = pg.evaluate("document.querySelectorAll('.alert.shown').length")
    pg.close()
    check('P7 a stopped run\'s robot docks with its !', alert == 1, f'{alert} shown')
    check('P7b and the camera zooms in on its dock', v['s'] > fit_s * 1.5 and math.hypot(cx - dock[0], cy - dock[1]) < 40,
          f"scale {v['s']:.2f} vs fit {fit_s:.2f}, {math.hypot(cx - dock[0], cy - dock[1]):.0f} px off the dock")

    # P8: a run that works again before its robot reaches the dock: the robot docks first, then
    # goes straight back out, as a real one empties its bin mid-pass, with no ! and no zoom...
    def out_on_its_lanes(pg):
        pg.wait_for_function("robovac.states()[0].state === 'running'", timeout=20000)
        pg.wait_for_timeout(1500)

    def sample(pg, until, secs):
        pg.evaluate("""() => { window.seen = []; setInterval(() => window.seen.push([robovac.states()[0].state,
          document.querySelectorAll('.alert.shown').length, robovac.view().s, robovac.states()[0].x,
          robovac.states()[0].y]), 50); }""")
        for _ in range(secs * 10):
            if pg.evaluate(until):
                break
            pg.wait_for_timeout(100)
        return pg.evaluate('window.seen')

    pg = page(b, None, f'&house={want}&speed=8')
    began = time.time() - 120
    live = dict(run(120), start=began)
    pg.evaluate(f"robovac.sync({json.dumps([live])})")
    out_on_its_lanes(pg)
    fit_s = pg.evaluate('robovac.view().s')
    stop = dict(live, state='stopped', why='waiting on you', at=time.time())
    pg.evaluate(f"robovac.sync({json.dumps([stop])})")
    pg.wait_for_timeout(200)
    pg.evaluate(f"robovac.sync({json.dumps([dict(live, start=time.time())])})")
    seen = sample(pg, """(() => { const s = window.seen.map(([x]) => x), d = s.indexOf('leaving');
      return d >= 0 && s.slice(d).includes('running'); })()""", 25)
    hood = pg.evaluate('robovac.docks()[0]')
    pg.close()

    states = [st for st, *_ in seen]
    left = states.index('leaving') if 'leaving' in states else len(states)
    at = [math.hypot(x - hood[0], y - hood[1]) for st, _, _, x, y in seen if st == 'leaving']
    check('P8 a robot sent out again while it drives home docks first, then goes back out from its dock',
          states[:1] == ['homing'] and 'docked' in states[:left] and 'running' not in states[:left]
          and at and max(at) < 1 and 'running' in states[left:],
          f"{' '.join(dict.fromkeys(states))}, {max(at, default=-1):.1f} px off the dock")
    check('P8b and shows no ! and is not zoomed in on at any point',
          max(n for _, n, *_ in seen) == 0 and max(abs(sc - fit_s) for _, _, sc, *_ in seen) < 0.01,
          f'{max(n for _, n, *_ in seen)} ! shown, scale up to {max(sc for _, _, sc, *_ in seen):.2f} vs fit {fit_s:.2f}')

    # P24: a run that stops again before its robot, sent out again, has reached the dock: the
    # robot docks and stays, its ! shown and the camera on it...
    pg = page(b, None, f'&house={want}&speed=8')
    pg.evaluate(f"robovac.sync({json.dumps([live])})")
    out_on_its_lanes(pg)
    pg.evaluate(f"robovac.sync({json.dumps([dict(stop, at=time.time())])})")
    pg.wait_for_timeout(150)
    pg.evaluate(f"robovac.sync({json.dumps([dict(live, start=time.time())])})")
    pg.wait_for_timeout(150)
    pg.evaluate(f"robovac.sync({json.dumps([dict(stop, why='finished', at=time.time())])})")
    seen = sample(pg, "window.seen.some(([x]) => x === 'docked')", 25)
    pg.wait_for_timeout(3000)
    after = pg.evaluate('window.seen')
    alert = pg.evaluate("document.querySelectorAll('.alert.shown').length")
    s24 = pg.evaluate('robovac.view().s')
    pg.close()
    states = [st for st, *_ in after]
    rest = states[states.index('docked'):] if 'docked' in states else ['never docked']
    early = max((sc for st, _, sc, *_ in after if st == 'homing'), default=0)
    check('P24 a robot stopped again before it docks stays docked, with its ! and the camera on it '
          'from when it docks, not before', set(rest) == {'docked'} and alert == 1
          and s24 > fit_s * 1.5 and early < fit_s * 1.05,
          f"{' '.join(dict.fromkeys(states))}, {alert} !, scale {s24:.2f}, {early:.2f} while homing")

    # P9 and P10: with every suite stopped, each ! stands over its robot, clear of the robot and
    # its dock tower whichever way the dock faces, and the whole-house view shows it whole...
    pg = page(b, None, f'&house={want}')
    n = pg.evaluate('ROBOVAC.houses.find(h => h.seed === %d).suites.length' % want)
    now = time.time()
    pg.evaluate('runs => robovac.sync(runs)', [dict(id=f's{k}', start=now - 600 + k, say='', state='stopped',
                                                   why='finished', at=now, hold=HOLD) for k in range(n)])
    pg.wait_for_timeout(1500)
    measure = """() => {
      const v = robovac.view(), r = ROBOVAC.robot.r;
      const su = ROBOVAC.houses.find(h => h.seed === %d).suites;
      return [...document.querySelectorAll('.alert')].map((m, k) => {
        const box = m.querySelector('img').getBoundingClientRect();
        const [x, y] = su[k].robot.hood, h = su[k].robot.heading * Math.PI / 180;
        return { k, shown: m.classList.contains('shown'), heading: su[k].robot.heading,
          left: box.left, right: box.right, top: box.top, bottom: box.bottom,
          cx: v.tx + x * v.s, cy: v.ty + y * v.s, robotTop: v.ty + (y - r) * v.s,
          towerTop: v.ty + (y + 18.5 * Math.cos(h) - 22.5) * v.s };
      });
    }""" % want
    geo = pg.evaluate(measure)

    # P9 reads each robot close up, as the arrow keys bring it to the middle...
    close = {}
    for _ in range(n):
        pg.keyboard.press('ArrowRight')
        pg.wait_for_timeout(1600)
        here = min(pg.evaluate(measure), key=lambda g: math.hypot(g['cx'] - 280, g['cy'] - 210))
        close[here['k']] = here
    pg.close()
    over = [g for g in close.values() if not (
        g['shown'] and g['bottom'] <= min(g['robotTop'], g['towerTop']) + 0.5
        and abs((g['left'] + g['right']) / 2 - g['cx']) < 2)]
    check('P9 each ! stands over its robot, clear of the robot and its tower, any way the dock faces',
          len(close) == n and not over, str([(g['k'], g['heading'], round(g['bottom'] - min(g['robotTop'], g['towerTop'])),
                                            round((g['left'] + g['right']) / 2 - g['cx'])) for g in over]))
    cut = [(g['k'], round(g['top'])) for g in geo if g['top'] < 0]
    check('P10 the whole-house view shows every ! whole', not cut, str(cut))

    # P11: the hover slip's ! is drawn in ink, so it reads on the cream slip...
    pg = page(b, None, f'&house={want}')
    pg.evaluate('runs => robovac.sync(runs)', [dict(id='s0', start=now - 60, say='', state='stopped',
                                                   why='interrupted', at=now, hold=HOLD)])
    pg.wait_for_timeout(800)
    x, y = pg.evaluate("""() => { const v = robovac.view(), [x, y] = robovac.docks()[0];
      return [v.tx + x * v.s, v.ty + y * v.s]; }""")
    pg.mouse.move(x, y)
    pg.wait_for_timeout(500)
    art = pg.evaluate("""() => { const w = document.querySelector('.tip-why');
      return w ? getComputedStyle(w, '::before').backgroundImage : ''; }""")
    src = art.split('build/')[-1].rstrip('")') if 'build/' in art else ''
    ink = None
    if src:
        from PIL import Image
        im = Image.open(app / 'build' / src).convert('RGBA')
        raw = im.tobytes()
        px = [raw[i:i + 4] for i in range(0, len(raw), 4) if raw[i + 3] > 200]
        ink = sum(0.299 * r + 0.587 * g + 0.114 * bl for r, g, bl, _ in px) / max(1, len(px)) / 255
    pg.close()
    check('P11 the slip\'s ! is dark ink', ink is not None and ink < 0.45, f'{src!r} luminance {ink}')

    # P18: a run that stops and goes again between two of the app's reads keeps one suite...
    pg = page(b, None, '&speed=8')
    now = time.time()
    pg.evaluate('r => robovac.sync(r)', [dict(id='a', start=now - 60, say='', state='live', why='', at=0,
                                             hold=HOLD)])
    pg.wait_for_timeout(1500)
    pg.evaluate('r => robovac.sync(r)', [dict(id='a', start=now + 1, say='', state='live', why='', at=0,
                                             hold=HOLD)])
    pg.wait_for_timeout(1500)
    pg.evaluate('r => robovac.sync(r)', [dict(id='a', start=now + 1, say='', state='stopped', why='finished',
                                             at=now + 3, hold=HOLD)])
    pg.wait_for_function("document.querySelectorAll('.alert.shown').length > 0", timeout=30000)
    pg.wait_for_timeout(1000)
    kept = (pg.evaluate('robovac.runs()'), pg.evaluate("document.querySelectorAll('.alert.shown').length"))
    pg.close()
    check('P18 a run that stops and starts again between two reads keeps one suite and one !',
          kept == (1, 1), f'suites, marks shown: {kept}')

    # P21: a stop holds its suite for the hold its run carries, and the page keeps none of its own:
    # a stop it never saw going, beside one held ten minutes, and one whose robot it watched dock...
    marks_shown = "[...document.querySelectorAll('.alert')].map(m => m.classList.contains('shown'))"
    pg = page(b, None, f'&house={want}')
    now = time.time()
    pg.evaluate('r => robovac.sync(r)', [dict(run(60), id='s0', start=now - 60, state='stopped', why='finished',
                                              at=now, hold=2),
                                         dict(run(60), id='s1', start=now - 59, state='stopped', why='finished',
                                              at=now)])
    pg.wait_for_timeout(1000)
    early = pg.evaluate(marks_shown)
    pg.wait_for_timeout(2500)
    late = pg.evaluate(marks_shown)
    pg.close()
    pg = page(b, None, f'&house={want}&speed=8')
    began = time.time() - 30
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), start=began)])})")
    pg.wait_for_timeout(300)
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), state='stopped', why='finished', start=began, at=time.time(), hold=2)])})")
    pg.wait_for_function("robovac.states()[0].state === 'docked'", timeout=30000)
    pg.wait_for_timeout(1200)
    docked = pg.evaluate(marks_shown)
    pg.wait_for_timeout(3500)
    after = pg.evaluate(marks_shown)
    pg.close()
    check('P21 a stop holds its suite and its ! for the hold its run carries, seen going or not',
          early == [True, True] and late == [False, True] and docked == [True] and after == [False],
          f'unseen {early} -> {late}, watched {docked} -> {after}')

    # P19: a stopped run's slot takes its session's later stop, its why and its time, whether the
    # page saw the run going or not, and when the session's later run stopped unseen...
    later = {}
    pg = page(b, None, f'&house={want}')
    now = time.time()
    wait = dict(run(60), start=now - 60, state='stopped', why='waiting on you', at=now - 595)
    pg.evaluate('r => robovac.sync(r)', [wait])
    pg.wait_for_timeout(800)
    later['unseen'] = [slip(pg)[1]]
    pg.evaluate('r => robovac.sync(r)', [dict(wait, why='finished', at=now + 1)])
    pg.wait_for_timeout(300)
    later['unseen'].append(slip(pg)[1])
    pg.wait_for_timeout(max(0, (now + 7 - time.time()) * 1000))
    later['held'] = pg.evaluate("document.querySelectorAll('.alert.shown').length")
    pg.close()
    pg = page(b, None, f'&house={want}&speed=8')
    began = time.time() - 30
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), start=began)])})")
    pg.wait_for_timeout(300)
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), state='stopped', why='waiting on you', start=began, at=time.time())])})")
    pg.wait_for_function("robovac.states()[0].state === 'docked'", timeout=30000)
    pg.wait_for_timeout(2500)
    later['watched'] = [slip(pg)[1]]
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), state='stopped', why='finished', start=began, at=time.time())])})")
    pg.wait_for_timeout(300)
    later['watched'].append(slip(pg)[1])
    pg.close()
    pg = page(b, None, f'&house={want}')
    now = time.time()
    pg.evaluate('r => robovac.sync(r)', [dict(run(60), start=now - 60, state='stopped', why='waiting on you', at=now)])
    pg.wait_for_timeout(800)
    later['next runs'] = []
    for n, why in ((1, 'finished'), (2, 'finished')):
        pg.evaluate('r => robovac.sync(r)', [dict(run(60), start=now + n, state='stopped', why=why, at=now + n)])
        pg.wait_for_timeout(1500)
        later['next runs'].append([pg.evaluate('robovac.runs()'),
                                   pg.evaluate("document.querySelectorAll('.alert.shown').length"), slip(pg)[1]])
    pg.close()
    pg = page(b, None, f'&house={want}&speed=8')
    began = time.time() - 30
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), start=began)])})")
    pg.wait_for_timeout(300)
    pg.evaluate('robovac.sync([])')
    pg.wait_for_timeout(100)
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), state='stopped', why='finished', start=began, at=time.time(), hold=2)])})")
    pg.wait_for_function("robovac.states()[0].state === 'docked'", timeout=30000)
    pg.wait_for_timeout(1200)
    later['gone, then its stop'] = [pg.evaluate("document.querySelectorAll('.alert.shown').length")]
    pg.wait_for_timeout(3500)
    later['gone, then its stop'].append(pg.evaluate("document.querySelectorAll('.alert.shown').length"))
    pg.close()
    pg = page(b, None, f'&house={want}')
    now = time.time()
    wait = dict(run(60), start=now - 60, state='stopped', why='waiting on you', at=now, hold=2)
    pg.evaluate('r => robovac.sync(r)', [wait])
    pg.wait_for_timeout(2600)
    pg.evaluate('r => robovac.sync(r)', [dict(wait, why='finished', at=now + 1)])
    pg.wait_for_timeout(300)
    later['stop after the hold lapsed'] = pg.evaluate("document.querySelectorAll('.alert.shown').length")
    pg.close()
    check('P19 a stopped run takes its session\'s later stop: the slip names it, its hold runs from it, and '
          'the session\'s later runs that stopped unseen keep the one suite, and a stop arriving after '
          'the hold lapsed brings the suite back no longer',
          later == {'unseen': ['Waiting on you', 'Finished'], 'held': 1,
                    'watched': ['Waiting on you', 'Finished'],
                    'next runs': [[1, 1, 'Finished'], [1, 1, 'Finished']], 'gone, then its stop': [1, 0],
                    'stop after the hold lapsed': 0},
          str(later))

    # P17: the slip names each reason a run stops, a wait on the person included...
    named = {}
    for why in ('finished', 'interrupted', 'waiting on you'):
        pg = page(b, None, f'&house={want}')
        pg.evaluate('runs => robovac.sync(runs)', [dict(id='s0', start=now - 60, say=f'binning {why}',
                                                       state='stopped', why=why, at=now, hold=HOLD)])
        pg.wait_for_timeout(800)
        named[why] = slip(pg)
        pg.close()
    check('P17 the slip shows the run\'s own line, and names a wait on the person in words, as it does '
          'a finish or an Esc', named == {'finished': ['binning finished', 'Finished'],
                                          'interrupted': ['binning interrupted', 'Interrupted'],
                                          'waiting on you': ['binning waiting on you', 'Waiting on you']},
          str(named))

    # P20: from a followed robot, Escape and 0 each bring the whole house back...
    back = {}
    for key in ('Escape', '0'):
        pg = page(b, [run(120)], f'&house={want}')
        pg.wait_for_timeout(300)
        fit_s = pg.evaluate('robovac.view().s')
        pg.keyboard.press('ArrowRight')
        pg.wait_for_timeout(1500)
        near = pg.evaluate('robovac.view().s')
        pg.keyboard.press(key)
        pg.wait_for_timeout(1200)
        back[key] = [near > fit_s * 1.5, abs(pg.evaluate('robovac.view().s') - fit_s) < 0.01]
        pg.close()
    check('P20 Escape and 0 each bring the whole house back from a followed robot',
          back == {'Escape': [True, True], '0': [True, True]}, str(back))

    # P23: with reduced motion an arrow key puts the camera on the robot at once, with no easing...
    pg = page(b, [run(120)], f'&house={want}', reduced=True)
    pg.wait_for_timeout(300)
    fit_s = pg.evaluate('robovac.view().s')
    pg.keyboard.press('ArrowRight')
    pg.wait_for_timeout(150)
    first = pg.evaluate('robovac.view().s')
    pg.wait_for_timeout(1500)
    then = pg.evaluate('robovac.view().s')
    pg.close()
    check('P23 with reduced motion the camera jumps to the robot it follows', first > fit_s * 1.5
          and first == then, f'fit {fit_s:.3f}, 150 ms {first:.3f}, 1.6 s {then:.3f}')

    # P12: after the camera has zoomed in on a docked robot, a new run's room is framed in...
    pg = page(b, None, f'&house={want}&speed=8')
    began = time.time() - 30
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), start=began)])})")
    pg.wait_for_timeout(300)
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), state='stopped', why='finished', start=began, at=time.time())])})")
    for _ in range(100):
        if pg.evaluate('robovac.states()[0].state') == 'docked':
            break
        pg.wait_for_timeout(100)
    pg.wait_for_timeout(800)
    zoomed = pg.evaluate('robovac.view().s')
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), state='stopped', why='finished', start=began, at=time.time()), dict(run(5), id='b', start=time.time())])})")
    pg.wait_for_timeout(2500)
    after = pg.evaluate('robovac.view().s')
    boxes = pg.evaluate('robovac.boxes()')
    v = pg.evaluate('robovac.view()')
    pg.close()
    shown = all(v['tx'] + bx[0] * v['s'] >= -2 and v['tx'] + (bx[0] + bx[2]) * v['s'] <= 562
                and v['ty'] + bx[1] * v['s'] >= -2 and v['ty'] + (bx[1] + bx[3]) * v['s'] <= 422 for bx in boxes)
    check('P12 a new run after a dock zoom brings the whole house back into view',
          len(boxes) == 2 and after < zoomed and shown, f'scale {zoomed:.2f} -> {after:.2f}, rooms in view {shown}')

    # P13: from the whole-house view a scroll out goes no closer...
    pg = page(b, None, f'&house={want}')
    pg.wait_for_timeout(300)
    fit_s = pg.evaluate('robovac.view().s')
    pg.mouse.move(280, 210)
    pg.mouse.wheel(0, 120)
    pg.wait_for_timeout(700)
    out_s = pg.evaluate('robovac.view().s')
    pg.close()
    check('P13 scrolling out at the whole-house view never zooms in', out_s <= fit_s + 1e-6,
          f'{fit_s:.4f} -> {out_s:.4f}')

    # P14: a right click neither pans nor lets a followed robot go...
    pg = page(b, [run(120)], f'&house={want}')
    pg.wait_for_timeout(300)
    pg.keyboard.press('ArrowRight')
    pg.wait_for_timeout(1200)
    pg.mouse.move(280, 210)
    pg.mouse.down(button='right')
    dragging = pg.evaluate("document.querySelector('.window, #win, body').closest('body').querySelector('.dragging') !== null")
    pg.mouse.up(button='right')
    a = pg.evaluate('robovac.view()')
    pg.wait_for_timeout(1500)
    c = pg.evaluate('robovac.view()')
    pg.close()
    check('P14 a right click neither pans nor drops the follow',
          not dragging and (abs(a['tx'] - c['tx']) + abs(a['ty'] - c['ty'])) > 1, f'dragging {dragging}, view moved {a != c}')

    # P15: a run that takes a room already in the house, after a dock zoom, brings the house back...
    pg = page(b, None, f'&house={want}&speed=8&runs=3')
    began = time.time() - 30
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), start=began)])})")
    pg.wait_for_timeout(300)
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), state='stopped', why='finished', start=began, at=time.time())])})")
    for _ in range(100):
        if pg.evaluate('robovac.states()[0].state') == 'docked':
            break
        pg.wait_for_timeout(100)
    pg.wait_for_timeout(800)
    zoomed = pg.evaluate('robovac.view().s')
    pg.evaluate(f"robovac.sync({json.dumps([dict(run(30), state='stopped', why='finished', start=began, at=time.time()), dict(run(5), id='b', start=time.time())])})")
    pg.wait_for_timeout(2500)
    v = pg.evaluate('robovac.view()')
    boxes = pg.evaluate('robovac.boxes()')
    pg.close()
    shown = all(v['tx'] + bx[0] * v['s'] >= -2 and v['tx'] + (bx[0] + bx[2]) * v['s'] <= 562
                and v['ty'] + bx[1] * v['s'] >= -2 and v['ty'] + (bx[1] + bx[3]) * v['s'] <= 422 for bx in boxes)
    check('P15 a new run in a room already shown, after a dock zoom, brings the whole house back',
          len(boxes) == 3 and v['s'] < zoomed and shown, f"scale {zoomed:.2f} -> {v['s']:.2f}, in view {shown}")

    # P16: a control click, like a right click, neither pans nor drops the follow...
    pg = page(b, [run(120)], f'&house={want}')
    pg.wait_for_timeout(300)
    pg.keyboard.press('ArrowRight')
    pg.wait_for_timeout(1200)
    pg.mouse.move(280, 210)
    pg.keyboard.down('Control')
    pg.mouse.down()
    dragging = pg.evaluate("document.querySelector('.dragging') !== null")
    pg.mouse.up()
    pg.keyboard.up('Control')
    a = pg.evaluate('robovac.view()')
    pg.wait_for_timeout(1500)
    c = pg.evaluate('robovac.view()')
    pg.close()
    check('P16 a control click neither pans nor drops the follow',
          not dragging and (abs(a['tx'] - c['tx']) + abs(a['ty'] - c['ty'])) > 1, f'dragging {dragging}')

    # P22, read: the suite of the run gone with no stop left half a minute after its robot docked...
    for _ in range(450):
        if held.evaluate('window.dropped') is not None:
            break
        held.wait_for_timeout(100)
    went = held.evaluate('[window.docked, window.dropped]')
    held.close()
    gap = (went[1] - went[0]) / 1000 if None not in went else None
    check('P22 a run gone with no stop logged keeps its suite half a minute after its robot docks',
          gap is not None and 29.5 <= gap <= 32.5, f'{gap} s')

    # P5: a run arriving after open still drives out of its dock (the opening path is open only)...
    pg = page(b, [], f'&house={want}')
    pg.wait_for_timeout(300)
    pg.evaluate(f'robovac.sync({json.dumps([dict(run(5), start=time.time() - 5)])})')
    pg.wait_for_timeout(60)
    st = pg.evaluate('robovac.states()')[0]
    check('P5 a later run starts from its dock', st['state'] in ('docked', 'leaving'), st['state'])
    pg.close()
    b.close()

sys.exit(1 if fails else 0)
