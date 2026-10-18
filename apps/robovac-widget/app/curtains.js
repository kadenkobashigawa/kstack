/* * curtains — the curtains in every window of a suite, seen from above, filling like sails as each
 *   gust comes and falling back into their pleats; still with reduced motion.
 *   Methods: curtainsLayer
 */

(() => {

  const { between } = window.robovacParts;

  //a curtain seen from above: pinned along its rod at the wall, the fabric below can fill like a
  //sail, its hem sweeping into the room and toward the middle of the window, a wave running
  //along it, then falling back into a band of gathered pleats against the wall...
  function panelPath(at, uOut, uFree, d, g, phase) {
    const pts = [];
    for (let k = 0; k <= 5; k++) {
      pts.push(at(uOut + (uFree - uOut) * k / 5, 1.5));
    }
    const h1 = [uFree + d * 11 * g, 6 + 35 * g];
    const bend = [uFree + d * 16 * g + d * 4 * g * Math.sin(phase), 3 + 22 * g];
    for (let k = 1; k <= 7; k++) {
      const t = k / 7;
      const u = (1 - t) ** 2 * uFree + 2 * (1 - t) * t * bend[0] + t * t * h1[0];
      const v = (1 - t) ** 2 * 1.5 + 2 * (1 - t) * t * bend[1] + t * t * h1[1];
      pts.push(at(u, v));
    }
    const h0 = [uOut + d * 2.4 * g, 5 + 18 * g];
    for (let k = 1; k <= 11; k++) {
      const t = k / 12;
      const u = h1[0] + (h0[0] - h1[0]) * t;
      const v = h1[1] + (h0[1] - h1[1]) * t
        + g * 5.6 * Math.sin(Math.PI * t)
        + g * 2.4 * Math.sin(phase * 1.3 + k * 0.9)
        + (1 - g) * 1.8 * Math.abs(Math.sin(k * 1.35));
      pts.push(at(u, v));
    }
    pts.push(at(h0[0], h0[1]));
    for (let k = 1; k <= 3; k++) {
      const t = k / 4;
      pts.push(at(h0[0] + (uOut - h0[0]) * t, h0[1] + (1.5 - h0[1]) * t));
    }
    const outline = smoothPath(pts);

    //the folds run from the rod down to the hem...
    const folds = [0.25, 0.5, 0.75].map((f) => {
      const top = at(uOut + (uFree - uOut) * f, 2.4);
      const hem = pts[13 + Math.round((1 - f) * 10)];
      const lo = [top[0] + (hem[0] - top[0]) * 0.88, top[1] + (hem[1] - top[1]) * 0.88];
      return `M${top[0].toFixed(1)},${top[1].toFixed(1)} L${lo[0].toFixed(1)},${lo[1].toFixed(1)}`;
    }).join(' ');
    return [outline, folds];
  }

  //a closed curve through the points, so the fabric's edge is soft; the same commands every
  //frame, so the edge can be morphed from one frame to the next...
  function smoothPath(pts) {
    const n = pts.length;
    const p = (i) => pts[(i + n) % n];
    let out = `M${p(0)[0].toFixed(1)},${p(0)[1].toFixed(1)}`;
    for (let i = 0; i < n; i++) {
      const [a, b, c, d] = [p(i - 1), p(i), p(i + 1), p(i + 2)];
      const c1 = [b[0] + (c[0] - a[0]) / 6, b[1] + (c[1] - a[1]) / 6];
      const c2 = [c[0] - (d[0] - b[0]) / 6, c[1] - (d[1] - b[1]) / 6];
      out += ` C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} `
        + `${c[0].toFixed(1)},${c[1].toFixed(1)}`;
    }
    return out + ' Z';
  }

  //how hard the wind is blowing through the cycle: still, a gust builds, flutters, and dies...
  function gustAt(t) {
    const ease = (x) => x * x * (3 - 2 * x);
    if (t < 0.12 || t > 0.86) {
      return 0;
    }
    if (t < 0.32) {
      return ease((t - 0.12) / 0.2);
    }
    if (t < 0.62) {
      return 0.82 + 0.18 * Math.cos((t - 0.32) * 26);
    }
    return 1 - ease((t - 0.62) / 0.24);
  }

  function curtainsLayer(windows, house) {
    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('class', 'layer curtains');
    svg.setAttribute('width', house.w);
    svg.setAttribute('height', house.h);
    svg.setAttribute('viewBox', `0 0 ${house.w} ${house.h}`);
    svg.innerHTML = '<defs><filter id="curtain-soft" x="-20%" y="-20%" width="140%" height="140%">'
      + '<feGaussianBlur stdDeviation="2.2"/></filter></defs>';
    const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const FRAMES = 48;
    windows.forEach((w, n) => {
      const [ax, ay] = w.a;
      const [bx, by] = w.b;
      const [nx, ny] = w.n;
      const L = Math.hypot(bx - ax, by - ay);
      const tx = (bx - ax) / L;
      const ty = (by - ay) / L;
      const at = (u, v) => [ax + tx * u + nx * (7 + v), ay + ty * u + ny * (7 + v)];
      const dur = between(8, 12);
      const begin = -between(0, dur);
      for (const [uOut, uFree, d, lag] of [[-14, 26, 1, 0], [L + 14, L - 26, -1, 0.05]]) {
        const frames = [];
        for (let f = 0; f <= FRAMES; f++) {
          const t = ((f / FRAMES) - lag + 1) % 1;
          frames.push(panelPath(at, uOut, uFree, d, still ? 0 : gustAt(t), t * Math.PI * 6 + n));
        }
        const g = document.createElementNS(NS, 'g');
        const make = (cls, i, extra = '') => {
          const path = document.createElementNS(NS, 'path');
          path.setAttribute('class', cls);
          path.setAttribute('d', frames[0][i]);
          if (extra) {
            path.setAttribute('transform', extra);
          }
          if (!still) {
            const anim = document.createElementNS(NS, 'animate');
            anim.setAttribute('attributeName', 'd');
            anim.setAttribute('dur', `${dur}s`);
            anim.setAttribute('begin', `${begin}s`);
            anim.setAttribute('repeatCount', 'indefinite');
            anim.setAttribute('values', frames.map((fr) => fr[i]).join(';'));
            path.append(anim);
          }
          g.append(path);
        };
        make('curtain-shadow', 0, 'translate(2.5 2.5)');
        make('curtain-cloth', 0);
        make('curtain-fold', 1);
        svg.append(g);
      }

      //the rod runs across the whole window a little off the wall, over the curtains' tops...
      const [r0, r1] = [at(-20, 3.4), at(L + 20, 3.4)];
      const rod = document.createElementNS(NS, 'g');
      rod.setAttribute('class', 'curtain-rod');
      rod.innerHTML = `<line class="rod-shadow" x1="${r0[0] + 1.6}" y1="${r0[1] + 1.6}" `
        + `x2="${r1[0] + 1.6}" y2="${r1[1] + 1.6}"/>`
        + `<line class="rod" x1="${r0[0]}" y1="${r0[1]}" x2="${r1[0]}" y2="${r1[1]}"/>`
        + `<line class="rod-glint" x1="${r0[0]}" y1="${r0[1] - 0.5}" x2="${r1[0]}" y2="${r1[1] - 0.5}"/>`
        + [r0, r1].map(([x, y]) => `<circle class="finial" cx="${x}" cy="${y}" r="2.8"/>`).join('');
      svg.append(rod);
    });
    return svg;
  }

  window.robovacParts.curtainsLayer = curtainsLayer;

})();
