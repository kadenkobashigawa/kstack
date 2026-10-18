/* * robot — one run's robot: out of its dock and round its lanes while its run goes, from wherever
 *   it is the shortest way home and backed into its dock when the run ends, and out again only
 *   once it has docked.
 *   Methods: Robot
 */

(() => {

  //the house's robot parts, written by widget.py...
  const D = window.ROBOVAC;
  const { img, Grid } = window.robovacParts;
  const pace = Number(new URLSearchParams(location.search).get('speed') || 1);

  //a real robot vacuum drives about 0.25 m/s and turns on the spot...
  const DRIVE = 24 * pace;
  const TURN = 110 * pace;

  class Robot {
    constructor(fleet, spec) {
      const parts = D.robot.parts;
      this.spec = spec;
      this.grid = new Grid(spec.grid);
      this.el = document.createElement('div');
      this.el.className = 'robot';
      this.rotor = document.createElement('div');
      this.rotor.className = 'rotor';

      //the shadow and the shine stay put while the body turns, so the light holds still...
      const sh = parts.shadow;
      this.el.append(img(`build/${sh.src}`, 'shadow', -sh.w / 2, -sh.h / 2, sh.w, sh.h));
      D.robot.hubs.forEach(([hx, hy], n) => {
        this.rotor.append(img(`build/${parts.brush.src}`, `brush ${n ? 'right' : 'left'}`,
          hx - 11, hy - 11, 22, 22));
      });
      const b = parts.body;
      this.rotor.append(img(`build/${b.src}`, 'body', -b.w / 2, -b.h / 2, b.w, b.h));
      this.el.append(this.rotor);
      this.el.append(img(`build/${parts.shine.src}`, 'shine', -b.w / 2, -b.h / 2, b.w, b.h));
      fleet.append(this.el);
      this.x = spec.hood[0];
      this.y = spec.hood[1];
      this.th = spec.heading;
      this.state = 'docked';
      this.token = 0;
      this.move = null;
      this.homing = null;
      this.pose();
    }

    pose() {
      this.el.style.transform = `translate(${this.x}px, ${this.y}px)`;
      this.rotor.style.transform = `rotate(${this.th}deg)`;
    }

    //where the robot is right now, partway through whatever it was doing...
    settle() {
      const m = this.move;
      if (!m) {
        return;
      }
      const t = m.anim.effect.getComputedTiming().progress ?? 1;
      if (m.kind === 'turn') {
        this.th = m.from + (m.to - m.from) * t;
      } else {
        this.x = m.from[0] + (m.to[0] - m.from[0]) * t;
        this.y = m.from[1] + (m.to[1] - m.from[1]) * t;
      }
      this.move = null;
      m.anim.cancel();
      this.pose();
    }

    async play(kind, el, frames, dur, from, to, easing) {
      const anim = el.animate(frames, { duration: dur, easing, fill: 'forwards' });
      this.move = { kind, anim, from, to };
      try {
        await anim.finished;
      } catch {
        return false;
      }
      this.move = null;
      if (kind === 'turn') {
        this.th = ((to % 360) + 360) % 360;
      } else {
        [this.x, this.y] = to;
      }
      this.pose();
      anim.cancel();
      return true;
    }

    turnTo(th) {
      const d = ((th - this.th + 540) % 360) - 180;
      if (Math.abs(d) < 0.5) {
        return Promise.resolve(true);
      }
      const to = this.th + d;
      return this.play('turn', this.rotor,
        [{ transform: `rotate(${this.th}deg)` }, { transform: `rotate(${to}deg)` }],
        Math.abs(d) / TURN * 1000, this.th, to, 'ease-in-out');
    }

    driveTo(p) {
      const from = [this.x, this.y];
      const dist = Math.hypot(p[0] - from[0], p[1] - from[1]);
      if (dist < 0.5) {
        return Promise.resolve(true);
      }
      return this.play('drive', this.el,
        [{ transform: `translate(${from[0]}px, ${from[1]}px)` }, { transform: `translate(${p[0]}px, ${p[1]}px)` }],
        dist / DRIVE * 1000, from, p, 'linear');
    }

    //turn on the spot to face the point, then drive straight to it...
    async headTo(p) {
      const d = Math.hypot(p[0] - this.x, p[1] - this.y);
      if (d > 0.5 && !await this.turnTo(Math.atan2(p[0] - this.x, -(p[1] - this.y)) * 180 / Math.PI)) {
        return false;
      }
      return this.driveTo(p);
    }

    //to a point by the shortest way the grid allows...
    async goTo(p, token) {
      const here = [this.x, this.y];
      const path = this.grid.sees(here, p) ? [p] : this.grid.route(here, p);
      for (const q of path) {
        if (token !== this.token || !await this.headTo(q)) {
          return false;
        }
      }
      return true;
    }

    async start() {
      if (this.state === 'running' || this.state === 'leaving') {
        return;
      }

      //one driving home docks first, and the page's next wake sends it back out, as a real robot
      //empties its bin mid-pass, so it never turns round on the way...
      if (this.state === 'homing') {
        return;
      }
      const token = ++this.token;
      this.settle();
      this.el.classList.add('running');
      if (this.state === 'docked') {
        this.state = 'leaving';
        if (!await this.driveTo(this.spec.out) || token !== this.token) {
          return;
        }
      }
      this.state = 'running';
      for (;;) {
        for (const p of this.spec.route) {
          if (!await this.goTo(p, token)) {
            return;
          }
        }
      }
    }

    //a run already going when the page opened: the robot starts on its lanes, at the waypoint
    //the time since the run began reaches going round the route at driving speed, facing the next...
    async resume(elapsed) {
      const route = this.spec.route;
      const token = ++this.token;
      const legs = route.map((p, i) => {
        const q = route[(i + 1) % route.length];
        return Math.hypot(q[0] - p[0], q[1] - p[1]);
      });
      const loop = legs.reduce((a, b) => a + b, 0) || 1;
      let left = (Math.max(0, elapsed) * DRIVE) % loop;
      let i = 0;
      while (i < legs.length - 1 && left > legs[i]) {
        left -= legs[i];
        i += 1;
      }
      const [p, q] = [route[i], route[(i + 1) % route.length]];
      [this.x, this.y] = p;
      this.th = Math.atan2(q[0] - p[0], -(q[1] - p[1])) * 180 / Math.PI;
      this.pose();
      this.el.classList.add('running');
      this.state = 'running';
      for (let j = i + 1; ; j += 1) {
        if (!await this.goTo(route[j % route.length], token)) {
          return;
        }
      }
    }

    where() {
      const m = this.move;
      if (!m || m.kind !== 'drive') {
        return [this.x, this.y];
      }
      const t = m.anim.effect.getComputedTiming().progress ?? 1;
      return [m.from[0] + (m.to[0] - m.from[0]) * t, m.from[1] + (m.to[1] - m.from[1]) * t];
    }

    //wherever it is, the robot finds its way home, turns its back to the dock and reverses in;
    //one still rolling out of the dock just backs straight in again. It resolves once docked,
    //called again on the way home too...
    finish() {
      if (this.state === 'docked') {
        return Promise.resolve();
      }
      if (this.state !== 'homing') {
        this.homing = this.home();
      }
      return this.homing;
    }

    async home() {
      const token = ++this.token;
      const inLane = this.state === 'leaving';
      this.settle();
      this.state = 'homing';
      if (!inLane && (!await this.goTo(this.spec.out, token) || token !== this.token)) {
        return;
      }
      if (!await this.turnTo(this.spec.heading) || !await this.driveTo(this.spec.hood)) {
        return;
      }
      this.el.classList.remove('running');
      this.state = 'docked';
    }
  }

  window.robovacParts.Robot = Robot;

})();
