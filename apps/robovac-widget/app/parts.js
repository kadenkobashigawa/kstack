/* * parts — what the page's files share: the robovacParts object each of them adds itself to, and
 *   the helpers more than one of them uses.
 *   Methods: img, between
 */

(() => {

  function img(src, cls, x, y, w, h) {
    const el = document.createElement('img');
    el.src = src;
    el.className = cls;
    el.alt = '';
    el.draggable = false;
    Object.assign(el.style, { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px` });
    return el;
  }

  function between(a, b) {
    return a + Math.random() * (b - a);
  }

  window.robovacParts = { img, between };

})();
