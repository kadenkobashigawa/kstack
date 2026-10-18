/* * grid — the floor grid as the robot sees it: the cells it may stand on, whether it can drive
 *   straight between two points, and the shortest way between them.
 *   Methods: Grid
 */

(() => {

  class Grid {
    constructor(g) {
      Object.assign(this, g);
    }

    at(x, y) {
      return [Math.floor((x - this.x0) / this.cell), Math.floor((y - this.y0) / this.cell)];
    }

    centre(i, j) {
      return [this.x0 + (i + 0.5) * this.cell, this.y0 + (j + 0.5) * this.cell];
    }

    ok(i, j) {
      return i >= 0 && j >= 0 && i < this.nx && j < this.ny && this.bits[j * this.nx + i] === '1';
    }

    //the nearest cell the robot may stand on...
    nearest(i, j) {
      for (let r = 0; r < 40; r++) {
        for (let di = -r; di <= r; di++) {
          for (let dj = -r; dj <= r; dj++) {
            if (Math.max(Math.abs(di), Math.abs(dj)) === r && this.ok(i + di, j + dj)) {
              return [i + di, j + dj];
            }
          }
        }
      }
      return [i, j];
    }

    //whether the robot can drive straight between two points...
    sees(a, b) {
      const n = Math.max(2, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 2.5));
      for (let t = 0; t <= n; t++) {
        const [i, j] = this.at(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n);
        if (!this.ok(i, j)) {
          return false;
        }
      }
      return true;
    }

    //the shortest way between two points, straightened wherever the robot can see ahead...
    route(a, b) {
      const start = this.nearest(...this.at(...a));
      const goal = this.nearest(...this.at(...b));
      const key = (i, j) => j * this.nx + i;
      const came = new Map([[key(...start), null]]);
      const cost = new Map([[key(...start), 0]]);
      const open = [[0, start]];
      while (open.length) {
        let k = 0;
        for (let n = 1; n < open.length; n++) {
          if (open[n][0] < open[k][0]) {
            k = n;
          }
        }
        const [, cur] = open.splice(k, 1)[0];
        if (cur[0] === goal[0] && cur[1] === goal[1]) {
          const cells = [];
          for (let c = cur; c; c = came.get(key(...c))) {
            cells.push(this.centre(...c));
          }
          cells.reverse();
          const out = [];
          let i = 0;
          while (i < cells.length - 1) {
            let j = cells.length - 1;
            while (j > i + 1 && !this.sees(cells[i], cells[j])) {
              j--;
            }
            out.push(cells[j]);
            i = j;
          }
          out.push(b);
          return out;
        }
        for (let di = -1; di <= 1; di++) {
          for (let dj = -1; dj <= 1; dj++) {
            const n = [cur[0] + di, cur[1] + dj];
            if ((di || dj) && this.ok(...n)) {
              const c = cost.get(key(...cur)) + Math.hypot(di, dj);
              if (c < (cost.get(key(...n)) ?? Infinity)) {
                cost.set(key(...n), c);
                came.set(key(...n), cur);
                open.push([c + Math.hypot(goal[0] - n[0], goal[1] - n[1]), n]);
              }
            }
          }
        }
      }
      return [b];
    }
  }

  window.robovacParts.Grid = Grid;

})();
