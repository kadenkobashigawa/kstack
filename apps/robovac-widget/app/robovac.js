/* * robovac — stacks the house, gives each run going a suite and its robot, and moves the camera:
 *   fit, glide, pan, zoom, follow and the hover slip. The curtains, the floor grid and the robot are
 *   their own files, parts.js the helpers they share.
 *   Methods: fit, sync, runs, states, view, boxes, docks
 */

(() => {

  //the house, its layers and the routes, written by widget.py...
  const D = window.ROBOVAC;
  const params = new URLSearchParams(location.search);
  //inside the Mac app the page is the window's content; in a browser it is a preview...
  const native = Boolean(window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.robovac);
  const preview = !params.has('app') && !native;
  const { img, between, curtainsLayer, Robot } = window.robovacParts;

  const win = document.getElementById('window');
  const stage = document.getElementById('stage');
  const view = { s: 1, tx: 0, ty: 0 };
  let runs = 1;
  let robots = [];


  // ── the stage ──────────────────────────────────────────────────────────


  //a house from the pool at random, or the one the address names (`house=<seed>`), for a recording...
  const house = D.houses.find((h) => String(h.seed) === params.get('house')) ||
    D.houses[Math.floor(Math.random() * D.houses.length)];

  //a suite's layers, bottom to top; each suite is a stack of its own, the later ones over the
  //earlier, so a suite can come and go whole without disturbing the others or the robots out...
  const LAYERS = ['floor', 'fleet', 'furniture', 'sprites', 'curtains', 'glow', 'ambient', 'walls'];
  let built = false;

  //until the shell's first word, a run already going is shown as it stands rather than arriving...
  let settled = false;
  let marks = null;
  let suites = [];

  function build() {
    Object.assign(stage.style, { width: `${house.w}px`, height: `${house.h}px` });
    marks = document.createElement('div');
    marks.className = 'marks';
    stage.append(marks);
    built = true;
  }

  //one suite's stack: a layer for each part of the drawing, all inside one box that turns about
  //the suite's middle, so the suite is set into the house and lifted out of it as one piece...
  function addSuite(k, arriving) {
    const su = house.suites[k];
    const base = `build/${su.dir}`;
    const [bx, by, bw, bh] = su.box;
    const box = document.createElement('div');
    box.className = 'suite';
    Object.assign(box.style, { width: `${house.w}px`, height: `${house.h}px`,
      transformOrigin: `${bx + bw / 2}px ${by + bh / 2}px` });
    stage.append(box);
    const pieces = {};
    for (const name of LAYERS) {
      const piece = document.createElement('div');
      piece.className = `piece ${name}`;
      Object.assign(piece.style, { width: `${house.w}px`, height: `${house.h}px` });
      box.append(piece);
      pieces[name] = piece;
    }
    const put = (name, el) => pieces[name].append(el);
    const layer = (name) => img(`${base}${name}.png`, `layer ${name}`, ...su.box);
    put('floor', layer('floor'));
    put('furniture', layer('furniture'));

    //plants' leaves sway and the cats' ears twitch, each on its own pivot...
    for (const sp of su.sprites) {
      let el = img(base + sp.src, `sprite ${sp.kind}`, sp.x, sp.y, sp.w, sp.h);
      const origin = `${sp.px - sp.x}px ${sp.py - sp.y}px`;
      el.style.transformOrigin = origin;

      //a plant barely leans as a whole; each leaf moves on its own stalk, its own way...
      if (sp.kind === 'sway') {
        const plant = img(base + sp.src, 'plant-base', 0, 0, sp.w, sp.h);
        el = document.createElement('div');
        el.className = 'sprite sway';
        Object.assign(el.style, { left: '0px', top: '0px', width: `${sp.w}px`,
          height: `${sp.h}px`, transformOrigin: origin });
        el.append(plant);
        for (const lf of sp.leaves) {
          const leaf = img(base + lf.src, 'leaf', lf.x - sp.x, lf.y - sp.y, lf.size, lf.size);
          const swing = (Math.random() < 0.5 ? -1 : 1) * between(3, 7) * (sp.amp || 3.6) / 3.6;
          leaf.style.setProperty('--swing', `${swing}deg`);
          leaf.style.setProperty('--lift', `${between(1.01, 1.05)}`);
          const t = between(2.4, 5.2);
          leaf.style.animationDuration = `${t}s`;
          leaf.style.animationDelay = `${-between(0, t)}s`;
          el.append(leaf);
        }

        //however it sways, a plant stays inside its own room: its walls fence it in...
        const fence = document.createElement('div');
        fence.className = 'fence';
        Object.assign(fence.style, { left: `${sp.x}px`, top: `${sp.y}px`, width: `${sp.w}px`,
          height: `${sp.h}px` });
        fence.style.clipPath = `polygon(${sp.room.map(([x, y]) => `${x}px ${y}px`).join(', ')})`;
        fence.append(el);
        el.style.setProperty('--amp', sp.amp || 3.6);
        const dur = between(7, 11);
        el.style.setProperty('--dur', `${dur}s`);
        el.style.setProperty('--delay', `${-between(0, dur)}s`);
        put('sprites', fence);
        continue;
      }
      if (sp.kind === 'ear') {
        const dur = between(4, 8);
        el.style.setProperty('--dur', `${dur}s`);
        el.style.setProperty('--delay', `${-between(0, dur)}s`);
        el.style.setProperty('--flick', sp.src.includes('ear-l') ? '-40deg' : '40deg');
      }
      put('sprites', el);
    }
    put('curtains', curtainsLayer(su.windows, house));
    for (const name of ['glow', 'ambient', 'walls']) {
      put(name, layer(name));
    }
    robots[k] = new Robot(pieces.fleet, su.robot);
    //the ! stands over the docked robot, clear of it and of its dock's tower, over walls too...
    const [hx, hy] = su.robot.hood;
    const h = su.robot.heading * Math.PI / 180;
    const mark = document.createElement('div');
    mark.className = 'alert';
    Object.assign(mark.style, { left: `${hx}px`,
      top: `${Math.min(hy - D.robot.r, hy + 18.5 * Math.cos(h) - 22.5)}px` });
    mark.innerHTML = `<div class="lift"><img src="build/${D.robot.parts.alert.src}" alt=""></div>`;
    marks.append(mark);
    suites[k] = { box, mark, anims: [], started: !arriving };
    suites[k].landed = arriving ? land(suites[k]) : Promise.resolve();
  }

  //a new run's suite is set into the house like a puzzle piece: it comes in lifted above the
  //house, its shadow on the suites below, fades up quickly and settles into its place as the view
  //takes in the larger house. Lift and shadow are in screen pixels at the view being glided to...
  const LAND = 900;
  const LAND_AFTER = 380;
  const FADE = 320;
  const LIFT = 720;
  const LIFT_PX = 18;
  const SETTLE = 'cubic-bezier(0.22, 1, 0.36, 1)';
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const raised = (s, k = 1) => `translateY(${-LIFT_PX * k / s}px) scale(${1 + 0.035 * k})`;
  const shadow = (s, k = 1) => `drop-shadow(0 ${14 * k / s}px ${16 * k / s}px rgba(52, 34, 22, ${0.4 * k}))`;
  const flat = 'drop-shadow(0 0 0 rgba(52, 34, 22, 0))';

  //the suite waits, unseen, until every picture in it is decoded, so it lands whole and the frame
  //never stalls on a picture arriving late; a slow picture holds it back at most 1.2 s...
  const MOVING = 'transform, opacity, filter';

  function land(suite) {
    const { box } = suite;
    const s = framing().s;
    const begun = performance.now();
    box.style.willChange = MOVING;
    const timing = { delay: LAND_AFTER, fill: 'backwards' };
    suite.anims = reduced()
      ? [box.animate([{ opacity: 0 }, { opacity: 1 }], { ...timing, duration: 200 })]
      : [
        box.animate([{ opacity: 0 }, { opacity: 1 }], { ...timing, duration: FADE, easing: 'ease-out' }),
        box.animate([{ transform: raised(s), filter: shadow(s) }, { transform: 'none', filter: flat }],
          { ...timing, duration: LAND, easing: SETTLE }),
      ];
    suite.anims.forEach((a) => a.pause());
    const decoded = Promise.all([...box.querySelectorAll('img')].map((im) => im.decode().catch(() => {})));
    const capped = new Promise((done) => setTimeout(done, 1200));
    return Promise.race([decoded, capped]).then(() => {
      if (!box.isConnected) {
        return undefined;
      }
      const waited = performance.now() - begun;
      for (const a of suite.anims) {
        a.currentTime = Math.min(waited, LAND_AFTER);
        a.play();
      }
      suite.started = true;
      return Promise.all(suite.anims.map((a) => a.finished));
    }).catch(() => {}).then(() => {
      box.style.willChange = '';
    });
  }

  //a suite leaving lifts off slowly from wherever it is, its shadow coming up under it, and only
  //then fades, so a session closes as gently as it opened; one that never showed is just taken away...
  function dropSuite(k, animated) {
    const suite = suites[k];
    const robot = robots[k];
    robots.length = k;
    suites.length = k;
    robot.token += 1;
    robot.settle();
    const { box } = suite;
    suite.mark.remove();
    if (!animated || !suite.started) {
      suite.anims.forEach((a) => a.cancel());
      box.remove();
      return;
    }
    const now = getComputedStyle(box);
    const from = { opacity: now.opacity, transform: now.transform, filter: now.filter === 'none' ? flat : now.filter };
    suite.anims.forEach((a) => a.cancel());
    const s = view.s;
    Object.assign(box.style, { opacity: from.opacity, transform: from.transform === 'none' ? '' : from.transform,
      filter: from.filter, willChange: MOVING });
    requestAnimationFrame(() => {
      const fade = box.animate([{ opacity: from.opacity }, { opacity: 0 }], reduced()
        ? { duration: 200, fill: 'forwards' }
        : { duration: LIFT - 280, delay: 280, easing: 'cubic-bezier(0.55, 0, 1, 0.45)', fill: 'forwards' });
      if (!reduced()) {
        box.animate([{ transform: from.transform, filter: from.filter },
          { transform: raised(s, 0.8), filter: shadow(s, 1) }],
        { duration: LIFT, easing: 'cubic-bezier(0.37, 0, 0.63, 1)', fill: 'forwards' });
      }
      fade.finished.catch(() => {}).then(() => box.remove());
    });
  }


  //one state of the widget: the first n suites of the house, one for each run going. Suites
  //already showing stay as they are, robots and all; new ones fade in, and the view glides to
  //take in the house as it now stands...
  function show(n) {
    const count = Math.max(1, Math.min(house.suites.length, n));
    const fresh = !built;
    if (fresh) {
      build();
    }
    const instant = fresh || !settled;
    const shrank = !instant && suites.length > count;

    //the glass frames the suites showing, worked out first so a landing is sized to the view
    //being glided to...
    const shown = house.suites.slice(0, count);
    const xs = shown.flatMap((su) => [su.box[0], su.box[0] + su.box[2]]);
    const ys = shown.flatMap((su) => [su.box[1], su.box[1] + su.box[3]]);
    frame = { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs),
      h: Math.max(...ys) - Math.min(...ys) };
    while (suites.length > count) {
      dropSuite(suites.length - 1, !instant);
    }
    while (suites.length < count) {
      addSuite(suites.length, !instant);
    }
    const changed = !instant && count !== runs;
    runs = count;
    if (following !== null && (following >= count || (followAuto && changed))) {
      following = null;
    }
    if (following !== null) {
      return;
    }
    if (changed && !reduced()) {
      glideFit(shrank ? LIFT * 0.6 : 0);
    } else {
      fit();
    }
  }


  // ── the runs going now ────────────────────────────────────────────────


  //each run going gets a suite of its own, the lowest one free; when it ends its robot drives
  //home, and the suite is held a little while after it docks before it can go to another run or
  //leave the house: a stop for the hold the shell sends with its run, a run gone with no stop
  //for half a minute...
  const HOLD = 30000;
  const ROLL_OUT = 260;
  let slots = [];
  let going = [];
  let real = [];

  //each run's own one line and how it stands, by session, and the stops already seen out...
  let info = {};
  let stoppedRuns = [];
  const seen = new Set();
  const lines = new Map();
  const keyOf = (id) => `${id}@${info[id] ? info[id].start : ''}`;

  //the fewest suites to show, whatever is running: one, or as many as the page's address asks...
  let least = 1;

  //the shell's runs, as the hooks logged them: each a session id, or {id, start, say, state, why,
  //at, hold}, state 'live' while its agent works or 'stopped' once it has stopped, at when, and
  //hold the seconds a stop keeps its suite...
  function sync(entries) {
    info = {};
    real = [];
    stoppedRuns = [];
    for (const entry of entries) {
      const run = typeof entry === 'string' ? { id: entry, say: '', state: 'live', why: '' } : entry;
      info[run.id] = run;
      if (run.say) {
        lines.set(run.id, run.say);
      }
      (run.state === 'stopped' ? stoppedRuns : real).push(run.id);
    }
    resync();
    settled = true;
    if (tipping !== null) {
      const k = tipping;
      tipping = null;
      showTip(k);
    }
  }

  function resync() {
    going = real.slice();
    const now = Date.now();

    //a run that stops sends its robot home, its ! over the dock and its suite kept for its hold,
    //and once it docks the camera finds it, as an arrow key would...
    slots.forEach((s, k) => {
      if (s && s.id && !going.includes(s.id)) {
        const why = info[s.id] && info[s.id].state === 'stopped' ? info[s.id].why : null;
        slots[k] = { id: null, until: null, hold: why ? info[s.id].hold * 1000 : HOLD, was: s.id,
          why, key: s.key };
        const robot = robots[k];
        if (robot) {
          robot.finish().then(() => {
            if (robots[k] === robot && slots[k] && !slots[k].id) {
              track(k, true);
            }
          });
        }
      }
    });
    const home = (k) => !robots[k] || robots[k].state === 'docked';
    slots.forEach((s, k) => {
      if (s && !s.id && s.until === null && home(k)) {
        s.until = now + s.hold;
      }
    });
    const free = (k) => !slots[k] || (!slots[k].id && slots[k].until !== null && now >= slots[k].until);

    //a stopped run's suite takes its session's later stop, a wait's end or a later run that stopped
    //between two reads: its why, its run, and its hold, run from that stop when it ends later...
    slots.forEach((s, k) => {
      const run = s && !s.id && s.was && !free(k) ? info[s.was] : null;
      if (run && run.state === 'stopped' && (run.why !== s.why || keyOf(s.was) !== s.key)) {
        Object.assign(s, { why: run.why, key: keyOf(s.was), hold: run.hold * 1000 });
        if (s.until !== null) {
          s.until = Math.max(s.until, run.at * 1000 + s.hold);
        }
      }
    });
    slots.forEach((s, k) => {
      if (s && s.was && free(k)) {
        seen.add(s.key);
      }
    });
    const lowest = () => {
      let k = 0;
      while (k < slots.length && !free(k)) {
        k += 1;
      }
      return k < house.suites.length ? k : null;
    };
    let started = false;
    for (const id of going) {

      //a run that stopped and went again between two reads keeps its suite, under its new start...
      const mine = slots.find((s) => s && s.id === id);
      if (mine) {
        mine.key = keyOf(id);
        continue;
      }

      //a run going again in its session takes back the suite it stopped in...
      const back = slots.findIndex((s) => s && !s.id && s.was === id && !free(slots.indexOf(s)));
      const k = back >= 0 ? back : lowest();
      if (k !== null) {
        slots[k] = { id, key: keyOf(id), opening: !settled };
        started = true;
      }
    }

    //a run that stopped before the widget saw it still gets a suite and its !...
    for (const id of stoppedRuns) {
      const key = keyOf(id);
      if (seen.has(key) || slots.some((s) => s && (s.id === id || s.key === key))) {
        continue;
      }
      const k = lowest();
      if (k !== null) {
        const { at } = info[id];
        const hold = info[id].hold * 1000;
        slots[k] = { id: null, until: at ? at * 1000 + hold : null, hold, was: id, why: info[id].why,
          key };
      }
    }

    //the house shows every suite up to the furthest one still in use...
    let last = -1;
    slots.forEach((s, k) => {
      if (s && !free(k)) {
        last = k;
      }
    });
    if (Math.max(least, last + 1) !== runs) {
      show(Math.max(least, last + 1));
    }

    //a run starting while the camera holds a dock it went to on its own brings the house back...
    if (started && followAuto && following !== null) {
      following = null;
      if (reduced()) {
        fit();
      } else {
        glideFit();
      }
    }
    slots.forEach((s, k) => {
      if (suites[k]) {
        suites[k].mark.classList.toggle('shown', Boolean(s && s.why && !free(k) && home(k)));
      }
    });
    wake();
  }

  //what the page knows of the run in suite k, going or last gone: its line and why it stopped;
  //nothing once its suite is free for another run...
  function about(k) {
    const s = slots[k];
    const id = s && (s.id || s.was);
    if (!id || (!s.id && s.until !== null && Date.now() >= s.until)) {
      return null;
    }
    return { say: (info[id] && info[id].say) || lines.get(id) || '', why: s.id ? null : s.why };
  }

  //every live run's robot out sweeping, a new one only once its suite has settled in...
  function wake() {
    slots.forEach((s, k) => {
      if (!(s && s.id && robots[k] && suites[k])) {
        return;
      }
      const robot = robots[k];

      //a run already going when the page opened is out on its lanes from the first frame...
      if (s.opening) {
        s.opening = false;
        const run = info[s.id];
        robot.resume(run && run.start ? Date.now() / 1000 - run.start : 0);
        return;
      }
      suites[k].landed.then(() => {
        if (robots[k] === robot && slots[k] && slots[k].id === s.id) {
          setTimeout(() => robots[k] === robot && slots[k] && slots[k].id === s.id && robot.start(),
            ROLL_OUT);
        }
      });
    });
  }

  //the shell sends the runs when they change; between times the holds still run out...
  setInterval(resync, 1000);

  let frame = null;

  //the whole house in view, centred on the glass below a band tall enough for a ! over a top wall...
  const OVER = 44;

  function framing() {
    const p = frame;
    const w = win.clientWidth;
    const h = win.clientHeight;
    const s = Math.min((w - 20) / p.w, (h - OVER - 10) / p.h);
    return { s, tx: (w - p.w * s) / 2 - p.x * s, ty: OVER + (h - OVER - 10 - p.h * s) / 2 - p.y * s };
  }

  function fit() {
    glide = null;
    fitting += 1;
    Object.assign(view, framing());
    paint();
  }

  //the same, eased, when the house grows or shrinks under the viewer; a newer glide or a wheel
  //click takes over from it...
  let fitting = 0;
  const GLIDE = 640;

  let gliding = false;

  function glideFit(after = 0) {
    glide = null;
    const mine = ++fitting;
    const from = { ...view };
    const to = framing();
    const t0 = performance.now() + after;
    const moving = gliding;
    gliding = true;
    const tick = (now) => {
      if (glide || mine !== fitting) {
        return;
      }
      const u = Math.min(1, Math.max(0, (now - t0) / GLIDE));
      const e = moving ? 1 - Math.pow(1 - u, 3)
        : u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
      view.s = from.s + (to.s - from.s) * e;
      view.tx = from.tx + (to.tx - from.tx) * e;
      view.ty = from.ty + (to.ty - from.ty) * e;
      paint();
      if (u < 1) {
        requestAnimationFrame(tick);
      } else {
        gliding = false;
      }
    };
    requestAnimationFrame(tick);
  }

  function paint() {
    stage.style.transform = `translate(${view.tx}px, ${view.ty}px) scale(${view.s})`;
    stage.style.setProperty('--inv', String(1 / view.s));
  }

  //the zoom runs from the whole-house view to 2, where the drawings stay sharp...
  function bounds() {
    return [framing().s, 2];
  }

  //a wheel click sets where the zoom is heading; the view glides there over a few frames...
  let glide = null;

  function zoomAt(cx, cy, factor) {
    const [least, most] = bounds();
    const from = glide ? glide.s : view.s;
    const running = glide && glide.running;
    glide = { s: Math.min(most, Math.max(least, from * factor)), cx, cy, running, t: glide && glide.t };
    if (!running) {
      glide.running = true;
      glide.t = performance.now();
      requestAnimationFrame(step);
    }
  }

  //the view eases toward the target with a quarter-second time constant, whatever the frame rate...
  function step(now) {
    if (!glide) {
      return;
    }
    const dt = Math.max(0, now - glide.t) / 1000;
    glide.t = now;
    const s = view.s + (glide.s - view.s) * (1 - Math.exp(-dt / 0.24));
    const done = Math.abs(glide.s - s) < glide.s * 0.0015;
    const next = done ? glide.s : s;
    view.tx = glide.cx - (glide.cx - view.tx) * (next / view.s);
    view.ty = glide.cy - (glide.cy - view.ty) * (next / view.s);
    view.s = next;
    paint();
    if (done) {
      glide = null;
    } else {
      requestAnimationFrame(step);
    }
  }

  //scrolling zooms in and out round the pointer, about a fifth per wheel click; pinching too...
  win.addEventListener('wheel', (e) => {
    e.preventDefault();
    const r = win.getBoundingClientRect();
    const step = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
    const rate = e.ctrlKey ? 0.01 : 0.0022;
    const factor = Math.exp(-Math.max(-200, Math.min(200, step)) * rate);
    if (following !== null) {
      const [least, most] = bounds();
      followS = Math.min(most, Math.max(least, followS * factor));
      return;
    }
    zoomAt(e.clientX - r.left, e.clientY - r.top, factor);
  }, { passive: false });

  //click and drag pans...
  let drag = null;
  win.addEventListener('pointerdown', (e) => {

    //only a plain primary press pans; a right or control click is the house's menu...
    if (e.button !== 0 || e.ctrlKey) {
      return;
    }
    e.preventDefault();
    following = null;
    glide = null;
    fitting += 1;
    gliding = false;
    drag = { x: e.clientX, y: e.clientY, tx: view.tx, ty: view.ty };
    win.setPointerCapture(e.pointerId);
    win.classList.add('dragging');
  });
  win.addEventListener('pointermove', (e) => {
    if (drag) {
      view.tx = drag.tx + e.clientX - drag.x;
      view.ty = drag.ty + e.clientY - drag.y;
      paint();
    }
  });
  const release = (e) => {
    drag = null;
    win.classList.remove('dragging');
    if (win.hasPointerCapture(e.pointerId)) {
      win.releasePointerCapture(e.pointerId);
    }
  };
  win.addEventListener('pointerup', release);
  win.addEventListener('pointercancel', release);

  //a double click puts the whole house back in view...
  win.addEventListener('dblclick', () => {
    following = null;
    fit();
  });

  window.addEventListener('resize', () => runs && following === null && fit());


  // ── finding the robots ─────────────────────────────────────────────────


  //the arrow keys find a robot and the camera follows it, close in: right or up the next robot,
  //left or down the one before; with one robot, any arrow finds it; esc or 0 go back to the house...
  let following = null;

  //a follow the camera took at a dock gives way when the house changes or a run starts...
  let followAuto = false;
  let followS = null;
  let tracking = 0;

  function track(k, auto = false) {
    followAuto = auto;
    glide = null;
    fitting += 1;
    gliding = false;
    if (following === null) {
      const [least, most] = bounds();
      followS = Math.min(most, Math.max(least * 2, win.clientWidth / 560));
    }
    following = k;
    const mine = ++tracking;
    let last = performance.now();
    const step = (now) => {
      if (mine !== tracking || following !== k || !robots[k]) {
        return;
      }
      const ease = 1 - Math.exp(-Math.min(0.1, (now - last) / 1000) / 0.3);
      last = now;
      const [x, y] = robots[k].where();
      const w = win.clientWidth;
      const h = win.clientHeight;
      if (reduced()) {
        const off = Math.hypot(view.tx + x * view.s - w / 2, view.ty + y * view.s - h / 2);
        if (view.s !== followS || off > Math.min(w, h) * 0.3) {
          Object.assign(view, { s: followS, tx: w / 2 - x * followS, ty: h / 2 - y * followS });
          paint();
        }
      } else {
        view.s += (followS - view.s) * ease;
        view.tx += (w / 2 - x * view.s - view.tx) * ease;
        view.ty += (h / 2 - y * view.s - view.ty) * ease;
        paint();
      }
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  //the robots worth finding: those with a run, going or stopped; every robot when none has one...
  function findable() {
    const withRun = robots.map((_, k) => k).filter((k) => about(k));
    return withRun.length ? withRun : robots.map((_, k) => k);
  }

  //of those, the one nearest the middle of the view...
  function nearest(ks) {
    const cx = (win.clientWidth / 2 - view.tx) / view.s;
    const cy = (win.clientHeight / 2 - view.ty) / view.s;
    const off = (k) => Math.hypot(robots[k].where()[0] - cx, robots[k].where()[1] - cy);
    return ks.reduce((best, k) => (off(k) < off(best) ? k : best), ks[0]);
  }

  window.addEventListener('keydown', (e) => {
    const step = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key];
    if (step && robots.length) {
      e.preventDefault();
      const ks = findable();
      const at = ks.indexOf(following);
      track(at < 0 ? nearest(ks) : ks[(at + step + ks.length) % ks.length]);
    } else if ((e.key === 'Escape' || e.key === '0') && following !== null) {
      following = null;
      if (reduced()) {
        fit();
      } else {
        glideFit();
      }
    }
  });

  //hovering a robot shows its run's own one line, and why it stopped if it has...
  const tip = document.createElement('div');
  tip.className = 'tip';
  win.append(tip);
  let tipping = null;
  const WHY = { finished: 'Finished', interrupted: 'Interrupted', 'waiting on you': 'Waiting on you',
    'session closed': 'Its session closed', 'went quiet': 'Went quiet for twelve hours' };

  let pointer = null;

  function showTip(k) {
    if (k === tipping) {
      return;
    }
    tipping = k;
    const run = k === null ? null : about(k);
    if (!run) {
      tip.classList.remove('shown');
      tipping = null;
      return;
    }
    const { say, why } = run;
    tip.replaceChildren();
    const line = document.createElement('div');
    line.className = 'tip-say';
    line.textContent = say || 'No line from the agent yet';
    tip.append(line);
    if (why) {
      const stop = document.createElement('div');
      stop.className = 'tip-why';
      stop.textContent = WHY[why] || (why.startsWith('error: ') ? `Stopped on an error: ${why.slice(7)}` : why);
      tip.append(stop);
    }
    tip.classList.add('shown');
    const step = () => {
      if (tipping !== k) {
        return;
      }
      if (!robots[k]) {
        showTip(null);
        return;
      }
      const [x, y] = robots[k].where();
      const rx = view.tx + x * view.s;
      const ry = view.ty + y * view.s;
      if (!pointer || Math.hypot(rx - pointer[0], ry - pointer[1]) > Math.max(22, D.robot.r * view.s + 10)) {
        showTip(null);
        return;
      }

      //centred right over the robot, its caret pointing down at it; below it, pointing up, when
      //there is no room above...
      const w = tip.offsetWidth;
      const h = tip.offsetHeight;
      const clear = Math.max(8, D.robot.r * view.s) + 12;
      const left = Math.max(8, Math.min(win.clientWidth - w - 8, rx - w / 2));
      const below = ry - clear - h < 8;
      tip.classList.toggle('below', below);
      tip.style.setProperty('--caret', `${Math.max(21, Math.min(w - 21, rx - left))}px`);
      Object.assign(tip.style, { left: `${left}px`, top: `${below ? ry + clear : ry - clear - h}px` });
      requestAnimationFrame(step);
    };
    step();
  }

  win.addEventListener('pointermove', (e) => {
    if (drag) {
      return;
    }
    const r = win.getBoundingClientRect();
    const px = e.clientX - r.left;
    const py = e.clientY - r.top;
    pointer = [px, py];
    let best = null;
    robots.forEach((robot, k) => {
      const [x, y] = robot.where();
      const d = Math.hypot(view.tx + x * view.s - px, view.ty + y * view.s - py);
      if (d < Math.max(14, D.robot.r * view.s + 4) && (!best || d < best[0])) {
        best = [d, k];
      }
    });
    showTip(best ? best[1] : null);
  });
  win.addEventListener('pointerleave', () => {
    pointer = null;
    showTip(null);
  });


  // ── what the shell calls ───────────────────────────────────────────────


  window.robovac = {
    fit: () => {
      following = null;
      fit();
    },
    sync,
    runs: () => runs,
    states: () => robots.map((r) => ({ state: r.state, x: r.x, y: r.y })),
    view: () => ({ ...view }),
    boxes: () => house.suites.slice(0, runs).map((su) => su.box),
    docks: () => house.suites.slice(0, runs).map((su) => su.robot.hood),
  };

  document.body.classList.add(preview ? 'preview' : 'app');
  least = Number(params.get('runs') || (preview ? 2 : 1));
  show(least);

})();
