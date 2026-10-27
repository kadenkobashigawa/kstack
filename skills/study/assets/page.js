// page.js draws one study map page. page.py inlines it after d3, markmap-view and the page's
// data, one JSON object in the sm-data script: MAPS {map id: tree}, UP {map id: [parent map id
// or null, label]}, LINKS {map id: [[from id, end id, home id], ...]} and TOP. It renders one map
// at a time. Both trees come from one data tree. The cross-links sit on a layer beneath them,
// and the portals and the link ends sit on a layer above them.
(function(){

// ── setup ─────────────────────────────────────────────────────────────────────

const {Markmap} = window.markmap;
const {MAPS, UP, LINKS, TOP} = JSON.parse(document.getElementById('sm-data').textContent);
const COLORS = d3.schemeTableau10;
const base = {
  autoFit: false, duration: 500, scrollForPan: false, spacingVertical: 8, paddingX: 0,
  maxWidth: 300, initialExpandLevel: 2,
  color: n => (n.payload && n.payload.c >= 0) ? COLORS[n.payload.c % COLORS.length] : '#7a8796'
};
const R = Markmap.create('#mmR', Object.assign({}, base));
const L = Markmap.create('#mmL', Object.assign({}, base, {zoom: false, pan: false}));
const svgL = document.getElementById('mmL'), svgR = document.getElementById('mmR');
const wrapEl = document.getElementById('wrap'), xg = document.getElementById('xg');
const ag = document.getElementById('ag');
const reduce = matchMedia('(prefers-reduced-motion: reduce)');
const crumbsEl = document.getElementById('crumbs');
const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

const store = {
  get(k){ try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v){ try { localStorage.setItem(k, v); } catch (e) {} }
};
let side = store.get('sm-layout') !== 'right';
const savedTheme = store.get('sm-theme');
if (savedTheme === 'dark' || savedTheme === 'light') {
  document.documentElement.setAttribute('data-theme', savedTheme);
}

// each node's home: the map that shows it as its own box, not as a portal, and its label
const HOME = new Map();
for (const [id, tree] of Object.entries(MAPS)) {
  walk(tree, n => { if (!n.payload.portal) HOME.set(n.payload.id, {map: id, html: n.content}); });
}

// the map on screen, and what each map looked like when it was left
let mapId = TOP, DATA = MAPS[TOP];
const left = new Map();

const clone = o => JSON.parse(JSON.stringify(o));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const trees = () => side ? [R, L] : [R];
const hasKids = n => !!(n.children && n.children.length);

// Cmd-click on a Mac and Ctrl-click elsewhere mean everything under the box
const wantsAll = e => isMac ? e.metaKey : e.ctrlKey;

// every node of a tree with its parent, each parent before its children
function walk(n, fn, parent = null){
  fn(n, parent);
  (n.children || []).forEach(c => walk(c, fn, n));
}

// a node's fold, set on a new payload as markmap's own toggleNode does
function setFold(n, fold){ n.payload = Object.assign({}, n.payload, {fold}); }

// open one level. The node opens, and each child that has children stays closed
function openOne(n){
  setFold(n, 0);
  (n.children || []).forEach(c => { if (hasKids(c)) setFold(c, 1); });
}

// the right tree's zoom set to t, eased over ms when ms is given
function zoomTo(t, ms){
  const s = d3.select(svgR);
  (ms ? s.transition().duration(ms) : s).call(R.zoom.transform, t);
}

// ── layout ────────────────────────────────────────────────────────────────────

function split(){
  const r = clone(DATA), l = clone(DATA);
  r.children = (DATA.children || []).filter((_, i) => i % 2 === 0).map(clone);
  l.children = (DATA.children || []).filter((_, i) => i % 2 === 1).map(clone);
  l.content = '<span style="visibility:hidden">' + DATA.content + '</span>';
  return [r, l];
}
function rootRect(mm){ const d = mm.state.data; return d && d.state && d.state.rect; }

// the mirrored left tree in the right tree's model space: x becomes m - x, y becomes y + dy
function mirror(){
  const rr = rootRect(R), rl = rootRect(L);
  if (!rr || !rl) return null;
  return {m: 2 * rr.x + rr.width, dy: (rr.y + rr.height) - (rl.y + rl.height)};
}
function sync(t){
  t = t || d3.zoomTransform(svgR);
  xg.setAttribute('transform', t.toString());
  ag.setAttribute('transform', t.toString());
  if (!side) return;
  const f = mirror();
  if (!f) return;
  const k = t.k, tx = t.x + k * f.m, ty = t.y + k * f.dy;
  L.g.attr('transform', `translate(${tx},${ty}) scale(${-k},${k})`);
}
R.zoom.on('zoom.sync', e => { sync(e.transform); hide(); });
for (const mm of [R, L]) {
  const orig = mm.renderData.bind(mm);
  mm.renderData = async function(d){
    clearSpot();
    const p = orig(d);
    paint(mm); sync(); index(); follow();
    await p;
    paint(mm); sync(); index(); drawLinks(); respot();
  };
}

// plain click opens one level (children stay closed). Cmd-click opens or closes everything
// under the box
for (const mm of [R, L]) {
  mm.handleClick = (e, d) => {
    hide();
    if (wantsAll(e)) return mm.toggleNode(d, true);
    if (d.payload.fold) { openOne(d); return mm.renderData(); }
    return mm.toggleNode(d, false);
  };
}

// the left tree's centre is a hidden copy over the right one's, so it is marked to take no input
function paint(mm){
  mm.g.selectAll('g.markmap-node').attr('data-id', d => d.payload.id)
    .classed('sm-mirror', d => mm === L && d === L.state.data)
    .style('--c', d => d.payload.c >= 0 ? base.color(d) : null);
}
for (const [mm, svg] of [[R, svgR], [L, svgL]]) {
  svg.addEventListener('click', e => {
    const fo = e.target.closest && e.target.closest('g.markmap-node>foreignObject');
    if (!fo) return;
    const d = d3.select(fo.parentNode).datum();
    if (!d) return;
    if (d.payload.portal) return goTo(d.payload.id, fo);

    // either tree's root is the centre, judged by the map's own children, not that tree's half
    if (d === mm.state.data) { if (hasKids(DATA)) centerToggle(wantsAll(e)); return; }
    if (hasKids(d)) mm.handleClick(e, d);
  });
}

// the centre follows the same rule on both sides: plain click opens one level, Cmd-click all
async function centerToggle(all){
  hide();
  const close = !R.state.data.payload.fold;
  for (const mm of trees()) {
    const root = mm.state.data;
    if (all) walk(root, n => setFold(n, close ? 1 : 0));
    else if (close) setFold(root, 1);
    else openOne(root);
  }
  await Promise.all(trees().map(mm => mm.renderData()));
  fit(true);
}

// the box around both trees, and around them and their portals with their names
function treeBounds(){
  const a = R.state.rect;
  let x1 = a.x1, x2 = a.x2, y1 = a.y1, y2 = a.y2;
  if (side && L.state.rect) {
    const f = mirror(), b = L.state.rect;
    x1 = Math.min(x1, f.m - b.x2); x2 = Math.max(x2, f.m - b.x1);
    y1 = Math.min(y1, b.y1 + f.dy); y2 = Math.max(y2, b.y2 + f.dy);
  }
  return {x1, x2, y1, y2};
}
function bounds(){
  const b = treeBounds();
  for (const p of PPOS.values()) {
    b.x1 = Math.min(b.x1, p.x - 70); b.x2 = Math.max(b.x2, p.x + 70);
    b.y1 = Math.min(b.y1, p.y - PR - 10); b.y2 = Math.max(b.y2, p.y + PR + 10);
  }
  return b;
}
// the band of the svg that no fixed bar covers: below the breadcrumb when it shows, above the
// bottom bar, each with the bars' own 14 px gap (kstack: Fit put a tip under #bar at 480 by 360)
function clearBand(){
  const r = svgR.getBoundingClientRect(), bar = document.getElementById('bar');
  const top = crumbsEl.hidden ? 0 : crumbsEl.getBoundingClientRect().bottom - r.top + 14;
  const bottom = Math.min(r.height, bar.getBoundingClientRect().top - r.top - 14);
  return {W: r.width, top, H: Math.max(1, bottom - top)};
}
function fit(animate = true){
  const {W, top, H} = clearBand(), b = bounds();

  // boxes sit half a box below their layout slot
  b.y1 -= 10; b.y2 += 34; b.x1 -= 10; b.x2 += 10;
  const s = Math.min(W / (b.x2 - b.x1) * 0.92, H / (b.y2 - b.y1) * 0.92, 2);
  const x = (W - (b.x2 - b.x1) * s) / 2 - b.x1 * s;
  const y = top + (H - (b.y2 - b.y1) * s) / 2 - b.y1 * s;
  zoomTo(d3.zoomIdentity.translate(x, y).scale(s), animate ? 500 : 0);
}

// every node's fold by id, from the trees on screen
function folds(){
  const out = new Map();
  for (const mm of trees()) {
    if (mm.state.data) walk(mm.state.data, n => out.set(n.payload.id, n.payload.fold || 0));
  }
  return out;
}

// the current map on screen with the given folds (or the default first view) and zoom (or a fit)
async function mount(two, kept, t){
  const restore = r => walk(r, n => {
    if (kept.has(n.payload.id)) setFold(n, kept.get(n.payload.id));
  });
  svgL.style.display = two ? '' : 'none';
  for (const mm of [R, L]) {
    mm.options.initialExpandLevel = kept ? -1 : base.initialExpandLevel;
    mm.options.duration = 0;
  }
  const [r, l] = two ? split() : [clone(DATA), null];
  if (kept) { restore(r); if (l) restore(l); }
  if (two) await Promise.all([R.setData(r), L.setData(l)]); else await R.setData(r);
  for (const mm of [R, L]) mm.options.duration = 500;
  paint(R); paint(L);
  if (t) zoomTo(t); else fit(false);
  index(); drawLinks();
}

let switching = false;
async function setLayout(two, animate = true){
  if (switching) return;
  switching = true;

  // remember what is open so the switch keeps it
  const kept = R.state.data ? folds() : null;
  hide(); clearSpot();
  if (animate) {
    wrapEl.style.transition = 'opacity .18s ease'; wrapEl.style.opacity = '0';
    await sleep(190);
  }
  side = two;
  store.set('sm-layout', two ? 'side' : 'right');
  document.getElementById('bLayout').textContent = two ? 'Two-sided' : 'One-sided';
  await mount(two, kept, null);
  if (animate) {
    await sleep(20);
    wrapEl.style.transition = 'opacity .26s ease'; wrapEl.style.opacity = '1';
  }
  switching = false;
}
const scaleBy = k => d3.select(svgR).transition().duration(250).call(R.zoom.scaleBy, k);
document.getElementById('bLayout').onclick = () => setLayout(!side);
document.getElementById('bIn').onclick = () => scaleBy(1.25);
document.getElementById('bOut').onclick = () => scaleBy(0.8);
document.getElementById('bFit').onclick = () => fit(true);
document.getElementById('bDark').onclick = () => {
  const root = document.documentElement, attr = root.getAttribute('data-theme');
  const isDark = attr ? attr === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  const next = isDark ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  store.set('sm-theme', next);
};

// ── zoom ──────────────────────────────────────────────────────────────────────

// smooth wheel zoom with easing, and drag inertia. d3 keeps drag-pan only
R.zoom.filter(e => e.type !== 'wheel' && !e.button && !e.ctrlKey);
let anim = null, target = null, anchor = [0, 0], vel = [0, 0], last = null;
function stopAnim(){ if (anim) cancelAnimationFrame(anim); anim = null; }
wrapEl.addEventListener('wheel', e => {
  e.preventDefault(); e.stopPropagation(); hide();
  const cur = d3.zoomTransform(svgR);
  const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1;
  const rate = e.ctrlKey ? 0.012 : 0.0022;
  target = Math.min(4, Math.max(0.05, (target ?? cur.k) * Math.exp(-e.deltaY * unit * rate)));
  anchor = [e.clientX, e.clientY - svgR.getBoundingClientRect().top];
  vel = [0, 0];
  if (!anim) anim = requestAnimationFrame(stepZoom);
}, {passive: false, capture: true});
function stepZoom(){
  const t = d3.zoomTransform(svgR), k = t.k + (target - t.k) * 0.18;
  const [px, py] = anchor, f = k / t.k;
  zoomTo(d3.zoomIdentity.translate(px - (px - t.x) * f, py - (py - t.y) * f).scale(k));
  if (Math.abs(target - k) / target > 0.002) anim = requestAnimationFrame(stepZoom);
  else { anim = null; target = null; }
}
R.zoom
  .on('start.inertia', e => {
    if (!e.sourceEvent) return;
    stopAnim(); target = null; last = null; vel = [0, 0];
  })
  .on('zoom.inertia', e => {
    if (!e.sourceEvent || e.sourceEvent.type !== 'mousemove') return;
    const now = performance.now(), t = e.transform;
    if (last) {
      const dt = Math.max(1, now - last.time);
      vel = [0.8 * vel[0] + 0.2 * (t.x - last.x) / dt * 16,
             0.8 * vel[1] + 0.2 * (t.y - last.y) / dt * 16];
    }
    last = {x: t.x, y: t.y, time: now};
  })
  .on('end.inertia', e => {
    if (!e.sourceEvent || !last || performance.now() - last.time > 80) return;
    const glide = () => {
      vel = [vel[0] * 0.92, vel[1] * 0.92];
      if (Math.hypot(vel[0], vel[1]) < 0.3) { anim = null; return; }
      const t = d3.zoomTransform(svgR);
      zoomTo(d3.zoomIdentity.translate(t.x + vel[0], t.y + vel[1]).scale(t.k));
      anim = requestAnimationFrame(glide);
    };
    anim = requestAnimationFrame(glide);
  });
window.addEventListener('resize', () => sync());

// ── links ─────────────────────────────────────────────────────────────────────

// rebuilt on every render: nodes and elements by id, each id's nearest shown box, the links
// drawn, the links touching each box, and the homes on other maps that links end at
let NODE = new Map(), EL = new Map(), SHOWN = new Map(), DRAWN = [], TOUCH = new Map();
let PORTS = [], PPOS = new Map();
const PR = 15;      // a portal's radius where links end

function index(){
  NODE = new Map(); EL = new Map(); SHOWN = new Map();
  for (const mm of trees()) {
    const root = mm.state.data;
    if (!root) continue;

    // a box is open when its parent is open and unfolded. A closed one shows as its nearest
    // open ancestor. the left tree's centre is the right tree's, so it is not indexed
    const open = new Map();
    walk(root, (n, parent) => {
      const id = n.payload.id;
      open.set(n, !parent || (open.get(parent) && !parent.payload.fold));
      if (mm === L && n === root) return;
      NODE.set(id, {d: n, mm, parent});
      SHOWN.set(id, open.get(n) ? id : SHOWN.get(parent.payload.id));
    });
    mm.g.selectAll('g.markmap-node').each(function(d){
      if (!(mm === L && d === root)) EL.set(d.payload.id, this);
    });
  }

  // a link is drawn only while its source's own box is on screen. It ends at a portal when its
  // home is on another map, or else at its end's nearest shown box. Two links that would join
  // the same two places are drawn once
  DRAWN = []; TOUCH = new Map();
  const seen = new Set();
  (LINKS[mapId] || []).forEach(([f, e, h], i) => {
    if (SHOWN.get(f) !== f) return;
    const port = HOME.get(h).map !== mapId, b = port ? h : SHOWN.get(e);
    const key = f + '\n' + b;
    if (b === undefined || b === f || seen.has(key)) return;
    seen.add(key);
    const l = {i, f, e, h, b, port, key};
    DRAWN.push(l);
    for (const id of port ? [f] : [f, b]) {
      if (!TOUCH.has(id)) TOUCH.set(id, []);
      TOUCH.get(id).push(l);
    }
  });
  PORTS = [...new Set(DRAWN.filter(l => l.port).map(l => l.b))];

  d3.select(ag).selectAll('path.xl').data(DRAWN, l => l.i).join('path').attr('class', 'xl')
    .attr('data-from', l => l.f).attr('data-to', l => l.e).attr('data-home', l => l.h)
    .each(function(l){ l.el = this; });
  const g = d3.select(xg);
  g.selectAll('g.xp').data(PORTS, h => h).join(enter => {
    const p = enter.append('g').attr('class', 'xp');
    p.append('circle').attr('class', 'po').attr('r', 17);
    p.append('circle').attr('class', 'pi').attr('r', 11);
    p.append('circle').attr('class', 'pd').attr('r', 5);
    p.append('text').attr('y', PR + 16);
    return p;
  })
    .attr('data-home', h => h)
    .style('--pc', h => base.color(NODE.get(DRAWN.find(l => l.port && l.b === h).f).d))
    .on('click', (ev, h) => { ev.stopPropagation(); jumpTo(h, ev); })
    .on('pointerenter', (ev, h) => { PHOVER.add(h); portalHot(h, true); })
    .on('pointerleave', (ev, h) => { PHOVER.delete(h); portalHot(h, false); })
    .select('text').text(h => plain(HOME.get(h).html));
  g.selectAll('circle.xh').data(DRAWN, l => l.i).join('circle').attr('class', 'xh').attr('r', 9)
    .attr('data-from', l => l.f).attr('data-to', l => l.e).each(function(l){ l.hit = this; })
    .on('click', (ev, l) => {
      ev.stopPropagation();
      if (l.port) return jumpTo(l.h, ev);
      pin = {x: ev.clientX, y: ev.clientY, id: l.e};
      openPathTo(l.e);
    });
}

// a label's text, from the escaped HTML page.py wrote
function plain(html){
  const t = document.createElement('template');
  t.innerHTML = html;
  return t.content.textContent;
}

// a box in the right tree's model space, from the live transform markmap tweens, or null before
// its first layout
function box(id, f){
  const el = EL.get(id), n = NODE.get(id);
  if (!el || !n) return null;
  const tr = el.transform.baseVal;
  if (!tr.numberOfItems) return null;
  const m = tr.getItem(0).matrix, r = n.d.state.rect;
  if (!r || !r.width) return null;
  let x1 = m.e, x2 = m.e + r.width;
  const y = m.f + r.height + (n.mm === L && f ? f.dy : 0);
  if (n.mm === L) {
    if (!f) return null;
    [x1, x2] = [f.m - x2, f.m - x1];
  }
  return {x1, x2, y};
}
function portBox(h){
  const p = PPOS.get(h);
  return p ? {x1: p.x - PR, x2: p.x + PR, y: p.y} : null;
}

// a link's cubic curve, as its four points. Each end leaves from the edge that faces the other
// box, or both leave from the right when the boxes share a column
function curve(A, B){
  let ps = 1, qs = -1;
  if (B.x2 < A.x1) { ps = -1; qs = 1; } else if (B.x1 <= A.x2) qs = 1;
  const p = [ps > 0 ? A.x2 : A.x1, A.y], q = [qs > 0 ? B.x2 : B.x1, B.y];
  const dx = Math.max(40, Math.abs(q[0] - p[0]) / 2);
  return [p, [p[0] + ps * dx, p[1]], [q[0] + qs * dx, q[1]], q];
}

// a curve cut into STEPS straight steps by arithmetic, with the distance run to each step's end.
// links redraw on every frame of a fold, so nothing here measures the page
const STEPS = 48, GAP = 7, HALF = 1.6, WING = 1.4;
function sample([p0, p1, p2, p3]){
  const pts = [], run = [0];
  for (let i = 0; i <= STEPS; i++) {
    const t = i / STEPS, u = 1 - t;
    const a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t;
    pts.push([a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
              a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]]);
    if (i) run.push(run[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  }
  return {pts, run};
}

// one filled path of triangles GAP apart along a sampled curve, starting off along it, each
// 2 * HALF long and pointing toward the target
function arrows({pts, run}, off){
  const out = [], len = run[STEPS], n = v => v.toFixed(1);
  for (let s = off + 4, i = 1; s < len - 2; s += GAP) {
    while (i < STEPS && run[i] < s) i++;
    const [ax, ay] = pts[i - 1], [bx, by] = pts[i], step = run[i] - run[i - 1] || 1;
    const k = (s - run[i - 1]) / step, ux = (bx - ax) / step, uy = (by - ay) / step;
    const x = ax + (bx - ax) * k, y = ay + (by - ay) * k;
    const cx = x - ux * HALF, cy = y - uy * HALF;
    out.push(`M${n(x + ux * HALF)},${n(y + uy * HALF)}L${n(cx - uy * WING)},${n(cy + ux * WING)}`
             + `L${n(cx + uy * WING)},${n(cy - ux * WING)}Z`);
  }
  return out.join('');
}

// the rim: a rectangle of half sides rx and ry around (cx, cy), measured by s, the distance
// along it clockwise from the middle of its left side, where the ray to the left meets it.
// rimAt is the point at s. rimOn is the s where the ray from the centre along (dx, dy) meets the
// rim, and it is the middle of the right side for a ray of no length
const APART = 110;
function rimAt({cx, cy, rx, ry}, s){
  const P = 4 * (rx + ry);
  s = (((s - ry) % P) + P) % P;
  if (s < 2 * rx) return {x: cx - rx + s, y: cy - ry};
  if ((s -= 2 * rx) < 2 * ry) return {x: cx + rx, y: cy - ry + s};
  if ((s -= 2 * ry) < 2 * rx) return {x: cx + rx - s, y: cy + ry};
  return {x: cx - rx, y: cy + ry - (s - 2 * rx)};
}
function rimOn({rx, ry}, dx, dy){
  const k = 1 / (Math.max(Math.abs(dx) / rx, Math.abs(dy) / ry) || 1), x = dx * k, y = dy * k;
  const lr = Math.abs(dx) / rx >= Math.abs(dy) / ry;
  const s = lr ? (dx >= 0 ? 2 * rx + ry + y : 4 * rx + 3 * ry - y)
               : (dy < 0 ? rx + x : 3 * rx + 2 * ry - x);
  return (s + ry) % (4 * (rx + ry));
}

// each portal sits on the rim, 130 px outside the box around the map, on the ray from the map's
// centre through the average of its callers, so its links fan in from their side of the map.
// The portals are then spread along the rim so that no two are closer than APART px. On an
// overfull rim, one shorter than n * APART for n portals, they sit rim / n apart instead
function placePorts(f){
  PPOS = new Map();
  if (!PORTS.length) return;

  // boxes sit half a box below their layout slot
  const {x1, x2, y1, y2} = treeBounds(), pad = 130;
  const rim = {cx: (x1 + x2) / 2, cy: (y1 + y2 + 30) / 2,
               rx: (x2 - x1) / 2 + pad, ry: (y2 + 30 - y1) / 2 + pad};
  const want = [];
  for (const h of PORTS) {
    let sx = 0, sy = 0, k = 0;
    for (const l of DRAWN) {
      const A = l.port && l.b === h ? box(l.f, f) : null;
      if (A) { sx += (A.x1 + A.x2) / 2; sy += A.y; k++; }
    }
    if (k) want.push({h, s: rimOn(rim, sx / k - rim.cx, sy / k - rim.cy)});
  }
  spread(want, 4 * (rim.rx + rim.ry));
  for (const w of want) PPOS.set(w.h, rimAt(rim, w.s));
}

// spread sets each w.s in want, a list of {s} wanted along a rim of length P, to where it sits.
// The rim is cut at the widest gap between wanted spots, so the list runs along a line. Each
// spot starts as its own cluster. A cluster sits centred on the mean of its members' wanted
// spots, and its members step apart in order. Two neighbouring clusters closer than step merge,
// until none are. step is APART, or P / n when n * APART is longer than the rim. If the first
// and last clusters then come closer than step across the cut, the wrap guard merges all n
// portals into one block, step apart and centred on the mean of every wanted spot, clusters
// clear of both ends included, so a block that would have stood alone moves too
function spread(want, P){
  const n = want.length, step = Math.min(APART, P / n);
  if (!n) return;
  want.sort((A, B) => A.s - B.s);
  const gap = i => (i + 1 < n ? want[i + 1].s : want[0].s + P) - want[i].s;
  let cut = n - 1;
  for (let i = 0; i < n - 1; i++) if (gap(i) > gap(cut)) cut = i;
  const line = [...want.slice(cut + 1), ...want.slice(0, cut + 1)];
  const at = line.map((w, i) => w.s - (i < n - 1 - cut ? P : 0));
  const half = c => (c.k - 1) * step / 2;
  const clusters = [];
  for (let i = 0; i < n; i++) {
    clusters.push({sum: at[i], k: 1});
    for (let A, B; clusters.length > 1; ) {
      A = clusters[clusters.length - 2]; B = clusters[clusters.length - 1];
      if (B.sum / B.k - half(B) - (A.sum / A.k + half(A)) >= step) break;
      clusters.splice(-2, 2, {sum: A.sum + B.sum, k: A.k + B.k});
    }
  }
  const first = clusters[0], last = clusters[clusters.length - 1];
  const all = last.sum / last.k + half(last) - (first.sum / first.k - half(first)) > P - step;
  let i = 0;
  for (const c of all ? [{sum: at.reduce((a, b) => a + b, 0), k: n}] : clusters) {
    for (let j = 0; j < c.k; j++) line[i++].s = c.sum / c.k - half(c) + j * step;
  }
}

function drawLinks(){
  const f = side ? mirror() : null;
  placePorts(f);
  d3.select(xg).selectAll('g.xp').each(function(h){
    const p = PPOS.get(h);
    if (!p) return this.setAttribute('display', 'none');
    this.removeAttribute('display');
    this.setAttribute('transform', `translate(${p.x},${p.y})`);
  });
  for (const l of DRAWN) {
    const A = box(l.f, f), B = l.port ? portBox(l.b) : box(l.b, f);
    if (!A || !B) { l.el.removeAttribute('d'); l.line = null; continue; }
    const c = curve(A, B);
    l.line = sample(c);
    l.el.setAttribute('d', arrows(l.line, motion(l).off));
    l.hit.setAttribute('cx', c[3][0]); l.hit.setAttribute('cy', c[3][1]);
  }
}

// links follow markmap's own tween: redraw them on every frame until it ends
let followUntil = 0, following = false;
function follow(){
  followUntil = performance.now() + R.options.duration + 80;
  if (following) return;
  following = true;
  const step = () => {
    drawLinks();
    if (performance.now() < followUntil) requestAnimationFrame(step); else following = false;
  };
  requestAnimationFrame(step);
}

// open every folded ancestor of a node, then spotlight it
async function openPathTo(id){
  const n = NODE.get(id);
  if (!n) return;
  let changed = false;
  for (let p = n.parent; p; p = NODE.get(p.payload.id).parent) {
    if (p.payload.fold) { setFold(p, 0); changed = true; }
  }
  if (changed) await n.mm.renderData();
  const el = EL.get(id);
  if (el) spotlight(el, NODE.get(id).mm);
}

// ── maps ──────────────────────────────────────────────────────────────────────

const chevron = document.getElementById('chevron').content.firstElementChild;
function crumbs(){
  const chain = [];
  for (let id = mapId; id != null; id = UP[id][0]) chain.unshift(id);
  crumbsEl.hidden = Object.keys(MAPS).length < 2;
  crumbsEl.replaceChildren();
  chain.forEach((id, i) => {
    if (i) crumbsEl.append(chevron.cloneNode(true));
    const last = i === chain.length - 1, el = document.createElement(last ? 'span' : 'button');
    el.textContent = UP[id][1];
    if (!last) el.onclick = () => goTo(id);
    crumbsEl.append(el);
  });
}

// swap to another map: zoom in from a portal's box, or out toward the map above
let moving = false;
async function goTo(id, from, pop){
  if (moving || switching || id === mapId || !MAPS[id]) return;
  moving = true;
  hide(); clearSpot();
  left.set(mapId, {kept: folds(), t: d3.zoomTransform(svgR)});
  let down = false;
  for (let m = UP[id][0]; m != null; m = UP[m][0]) if (m === mapId) down = true;
  const r = from ? from.getBoundingClientRect() : null;
  wrapEl.style.transformOrigin = r ? `${r.left + r.width / 2}px ${r.top + r.height / 2}px`
                                   : '50% 50%';
  wrapEl.style.transition = 'transform .22s ease-in, opacity .22s ease-in';
  wrapEl.style.transform = `scale(${down ? 1.8 : 0.6})`; wrapEl.style.opacity = '0';
  await sleep(230);
  wrapEl.style.transition = 'none'; wrapEl.style.transform = 'none';
  wrapEl.style.transformOrigin = '50% 50%';
  mapId = id; DATA = MAPS[id];

  // a pin belongs to the map it was set on, so the switch drops it
  pin = null;
  const was = left.get(id);
  await mount(side, was ? was.kept : null, was ? was.t : null);
  crumbs();
  wrapEl.style.transform = `scale(${down ? 0.6 : 1.4})`;
  void wrapEl.offsetWidth;
  wrapEl.style.transition = 'transform .26s ease-out, opacity .26s ease-out';
  wrapEl.style.transform = ''; wrapEl.style.opacity = '1';
  if (!pop) { try { history.pushState({sm: id}, ''); } catch (e) {} }
  moving = false;
}

// a portal's click goes to its home's map, opens the way to the home and spotlights the home.
// The pin is set after the switch, which drops any pin, so it belongs to the home's map
async function jumpTo(h, ev){
  await goTo(HOME.get(h).map);
  await sleep(300);
  pin = {x: ev.clientX, y: ev.clientY, id: h};
  await openPathTo(h);
}
window.addEventListener('popstate', e => {
  const id = e.state && e.state.sm;
  if (id) goTo(id, null, true);
});

// ── cards and spotlight ───────────────────────────────────────────────────────

const hc = document.getElementById('hc');
let cur = null, HOT = [];

// an arrow click's spotlight stays until the pointer moves 6 px away, through markmap's
// re-renders and the boxes moving under it. It ends on the first move away. Over a box, that
// box's hover takes over. Over bare canvas, where no box fires, the spotlight clears here
let pin = null;
function pinned(e){
  if (!pin) return false;
  if (Math.hypot(e.clientX - pin.x, e.clientY - pin.y) < 6) return true;
  pin = null;
  if (!(e.target.closest && e.target.closest('g.markmap-node'))) { hide(); clearSpot(); }
  return false;
}
function respot(){ const el = pin && EL.get(pin.id); if (el) spotlight(el, NODE.get(pin.id).mm); }
function hide(){ hc.classList.remove('on'); cur = null; }
function spotlight(g, mm){
  const d = d3.select(g).datum(), path = new Set();
  for (let n = d; n; n = (NODE.get(n.payload.id) || {}).parent) path.add(n);
  for (const t of [R, L]) {
    const root = t.state.data;
    t.g.selectAll('g.markmap-node').classed('lit', n => (t === mm && path.has(n)) || n === root);
    t.g.selectAll('path.markmap-link').classed('lit', l => t === mm && path.has(l.target));
  }
  lightLinks(path, mm.state.data);
  wrapEl.classList.add('spot');
}

// the links touching the lit path go hot. The centre is on every path, so it lights none
function lightLinks(path, root){
  for (const el of HOT) el.classList.remove('hot');
  HOT = [];
  for (const n of path) {
    if (n === root) continue;
    for (const l of TOUCH.get(n.payload.id) || []) { l.el.classList.add('hot'); HOT.push(l.el); }
  }
  heat();
}
function clearSpot(){
  wrapEl.classList.remove('spot');
  for (const el of HOT) el.classList.remove('hot');
  HOT = [];
  heat();
}

// a hovered portal lights the links that end at it
const PHOVER = new Set();
function portalHot(h, on){
  for (const l of DRAWN) {
    if (!l.port || l.b !== h) continue;
    l.el.classList.toggle('hot', on);
    if (on) HOT.push(l.el);
  }
  heat();
}

// ── motion ────────────────────────────────────────────────────────────────────

// a hot link's triangles speed up to 40 px/s toward its target, and a cold one coasts to a stop
// where it is. A portal turns while it is hovered or any of its links is hot. Each keeps its
// place across redraws. One loop runs while anything moves and stops once everything is still,
// and under reduced motion nothing moves
const SLIDE = {top: 40, stop: 0.5}, TURN = {top: 260, stop: 2};
const LMOT = new Map(), SPIN = new Map();
let ticking = false;
const motion = l => LMOT.get(l.key) || LMOT.set(l.key, {off: 0, v: 0, on: false}).get(l.key);

// every link's and portal's heat from the classes the spotlight and portals set
function heat(){
  const lit = new Set();
  for (const l of DRAWN) {
    const on = motion(l).on = l.el.classList.contains('hot');
    if (l.port && on) lit.add(l.b);
  }
  d3.select(xg).selectAll('g.xp').each(function(h){
    const on = PHOVER.has(h) || lit.has(h);
    if (!on && !SPIN.has(this)) return;
    const st = SPIN.get(this) || {a: this.angle || 0, v: 0, rings: this.querySelectorAll('circle')};
    st.on = on;
    SPIN.set(this, st);
  });
  tick();
}

// eases st toward its kind's top speed while on, or to a stop. It returns true while st moves
// or will move
function ease(st, kind, dt){
  const want = st.on && !reduce.matches ? kind.top : 0;
  st.v += (want - st.v) * (1 - Math.exp(-(st.on ? 2.2 : 1.6) * dt));
  if (!want && st.v < kind.stop) st.v = 0;
  return st.v > 0 || want > 0;
}

function tick(){
  if (ticking) return;
  ticking = true;
  let last = performance.now();
  const step = now => {
    const dt = Math.max(0, Math.min(0.05, (now - last) / 1000));
    last = now;
    let busy = false;
    for (const l of DRAWN) {
      const st = motion(l);
      if (!ease(st, SLIDE, dt)) continue;
      busy = true;
      st.off = (st.off + st.v * dt) % GAP;
      if (l.line) l.el.setAttribute('d', arrows(l.line, st.off));
    }
    for (const [g, st] of SPIN) {
      if (!ease(st, TURN, dt)) { g.angle = st.a; SPIN.delete(g); continue; }
      busy = true;
      st.a = (st.a + st.v * dt) % 360;
      st.rings[0].setAttribute('transform', `rotate(${st.a})`);
      st.rings[1].setAttribute('transform', `rotate(${-st.a * 1.6})`);
    }
    if (busy) requestAnimationFrame(step); else ticking = false;
  };
  requestAnimationFrame(step);
}

function onOver(e, isLeft){
  if (pinned(e)) return;
  const g = e.target.closest && e.target.closest('g.markmap-node');
  if (!g) return;
  const d = d3.select(g).datum();
  if (!d) return;
  spotlight(g, isLeft ? L : R);

  // page.py puts a card only on a tip, and a tip's children, when it has any, are pointer leaves
  if (!d.payload.card) { hide(); return; }
  if (g === cur) return;
  cur = g;
  g.querySelector('foreignObject').style.cursor = 'help';
  hc.innerHTML = d.payload.card;
  // the card is 360 px wide. It opens 16 px past the tip's outer end, right of a right-side tip
  // and left of a left-side one, when its left and right edges both sit 12 px or more inside the
  // window there. Otherwise it opens 16 px past the tip's other end, when they do there.
  // Otherwise it takes the outer end's spot, moved sideways only as far as it takes to sit 12 px
  // inside. Vertically it is centred on the tip, moved only as far as it takes to sit 12 px
  // inside. In a window too small for the card, its left and top edges sit 12 px inside
  const r = g.getBoundingClientRect(), w = 360, m = 12;
  const out  = isLeft ? r.left - 16 - w : r.right + 16;
  const back = isLeft ? r.right + 16 : r.left - 16 - w;
  const fits = x => x >= m && x + w <= innerWidth - m;
  const x = fits(out) ? out : fits(back) ? back : Math.max(m, Math.min(out, innerWidth - m - w));
  hc.style.left = x + 'px'; hc.style.top = '0px';
  const h = hc.getBoundingClientRect().height;
  const y = Math.max(m, Math.min(r.top + r.height / 2 - h / 2, innerHeight - m - h));
  hc.style.top = y + 'px'; hc.classList.add('on');
}
function onOut(e){
  if (pinned(e)) return;
  const to = e.relatedTarget, g = e.target.closest && e.target.closest('g.markmap-node');
  const toG = to && to.closest ? to.closest('g.markmap-node') : null;
  if (toG !== g) { hide(); if (!toG) clearSpot(); }
}
svgR.addEventListener('mouseover', e => onOver(e, false)); svgR.addEventListener('mouseout', onOut);
svgL.addEventListener('mouseover', e => onOver(e, true)); svgL.addEventListener('mouseout', onOut);
svgR.addEventListener('mousedown', () => { hide(); clearSpot(); });
document.addEventListener('pointermove', pinned);

try { history.replaceState({sm: TOP}, ''); } catch (e) {}
crumbs();
setLayout(side, false);
})();
