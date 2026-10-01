// Apple Photos-style grid density.
//
// While fingers move, the grid scales continuously with the pinch (a compositor-only CSS
// transform around the pinch point), so it tracks 1:1 with no steps or lag. When the pinch
// ends, the grid snaps to the nearest column count: layout changes once, and every visible
// tile glides from where it was on screen to its new place (FLIP, Web Animations).
// A new pinch during the glide just finishes it and carries on, so nothing is ever locked.
//
// Input sources:
//   Chrome / Edge / Firefox trackpad pinch -> `wheel` events with ctrlKey = true
//   Safari (macOS) trackpad pinch          -> `gesturestart` / `gesturechange` / `gestureend`
//   iOS / iPadOS Safari touch pinch         -> gesture events (same handler)
//   Other touchscreens                      -> two-finger touch events
//   Keyboard                                -> + / -
//
// axis() === "x" (timeline view): the pinch stretches time and the timelines re-wrap to the page
// width as it goes (stretch.preview(scale) re-lays them out live, stretch.commit(scale) keeps it).
// The stretch is continuous and separate from the grid's levels, so there is no snap. No transform
// and no glide: the layout itself changes, and the frame under the fingers is kept at the same height.

export const LEVELS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20];
const SNAP_MS = 320;
const EASE = "cubic-bezier(.2, .9, .25, 1)";
const WHEEL_GAIN = 0.011;   // scale = exp(-deltaY * gain); Chrome's own pinch-zoom uses ~0.01
const WHEEL_END_MS = 140;   // ctrl+wheel has no "end" event: treat a pause as the end
const NUDGE = 0.12;         // a pinch this big (|ln scale|) always moves at least one level
const KEY_STRETCH = 1.5;    // + / - in the timeline view

const ln = Math.log;

export function setupZoom({ root, onChange, axis = () => "both", stretch }) {
  const store = { get: () => { try { return localStorage.getItem("gridDensity"); } catch { return null; } },
                  set: (v) => { try { localStorage.setItem("gridDensity", v); } catch {} } };
  const raw = store.get();
  const saved = raw === null ? NaN : Number(raw);
  let level = Number.isInteger(saved) && saved >= 0 && saved < LEVELS.length ? saved : defaultLevel();
  apply(level);

  let g = null;        // active pinch: { scale, x, y }
  let frame = 0;       // pending rAF for the transform
  let glides = [];     // running snap animations
  const stretching = () => axis() === "x" && !!stretch;
  const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function defaultLevel() { return LEVELS.indexOf(window.innerWidth < 500 ? 2 : 3); }

  function apply(i) {
    document.documentElement.style.setProperty("--cols", LEVELS[i]);
    onChange?.(i, LEVELS[i]);
  }

  // ------------------------------------------------------------ live pinch

  function begin(x = window.innerWidth / 2, y = window.innerHeight / 2) {
    finishGlides();
    g = { scale: 1, x, y };
    // A stretch re-lays the timeline out every frame: a will-change layer would have to be re-rastered
    // each time, and its unpainted tiles flash white.
    if (stretching()) return;
    const r = root.getBoundingClientRect();
    root.style.transformOrigin = `${x - r.left}px ${y - r.top}px`;
    root.style.willChange = "transform";
  }

  function update(scale) {
    if (!g) return;
    if (stretching()) {
      g.scale = stretch.clamp(scale); // no winding up past the ends
      if (!frame) frame = requestAnimationFrame(() => {
        frame = 0;
        if (!g) return;
        const anchor = anchorAt(g.x, g.y);
        stretch.preview(g.scale);
        keep(anchor);
      });
      return;
    }
    const cols = LEVELS[level];
    const lo = cols / LEVELS.at(-1), hi = cols / LEVELS[0]; // scales that reach the densest / sparsest level
    g.scale = Math.min(hi * 1.6, Math.max(lo / 1.6, scale)); // don't wind up far past the ends
    if (!frame) frame = requestAnimationFrame(() => {
      frame = 0;
      if (!g) return;
      root.style.transform = `scale(${rubber(g.scale, lo, hi)})`;
    });
  }

  // Past the first/last level the grid resists instead of stopping dead.
  function rubber(s, lo, hi) {
    if (s > hi) return hi * (s / hi) ** 0.3;
    if (s < lo) return lo * (s / lo) ** 0.3;
    return s;
  }

  function end() {
    if (!g) return;
    const { scale, x, y } = g;
    g = null;
    cancelAnimationFrame(frame);
    frame = 0;
    if (stretching()) return stretchBy(scale, x, y);
    let next = nearest(LEVELS[level] / scale);
    if (next === level && Math.abs(ln(scale)) > NUDGE) next = clamp(level + (scale < 1 ? 1 : -1));
    commit(next, x, y);
  }

  const clamp = (i) => Math.min(LEVELS.length - 1, Math.max(0, i));
  function nearest(cols) {
    let best = 0;
    LEVELS.forEach((c, i) => { if (Math.abs(ln(c / cols)) < Math.abs(ln(LEVELS[best] / cols))) best = i; });
    return best;
  }

  // ------------------------------------------------------------ snap (FLIP)

  function commit(next, x = window.innerWidth / 2, y = window.innerHeight / 2) {
    finishGlides();
    const before = new Map(visibleTiles().map((t) => [t, t.getBoundingClientRect()]));
    const anchor = anchorAt(x, y);

    root.style.transform = root.style.transformOrigin = root.style.willChange = "";
    if (next !== level) {
      level = next;
      apply(level);
      store.set(level);
    }
    keep(anchor); // the point under the fingers stays over the same tile
    if (reduced()) return;

    for (const t of visibleTiles()) {
      const f = before.get(t), l = t.getBoundingClientRect();
      if (!f) {
        glides.push(t.animate([{ opacity: 0, offset: 0 }], { duration: SNAP_MS, easing: EASE })); // to its own opacity (dimmed if another tile is pinned)
        continue;
      }
      const dx = f.left - l.left, dy = f.top - l.top, s = f.width / l.width;
      if (Math.abs(dx) < .5 && Math.abs(dy) < .5 && Math.abs(s - 1) < .002) continue;
      glides.push(t.animate(
        [{ transformOrigin: "0 0", transform: `translate(${dx}px, ${dy}px) scale(${s})` },
         { transformOrigin: "0 0", transform: "none" }],
        { duration: SNAP_MS, easing: EASE },
      ));
    }
  }

  function stretchBy(scale, x = window.innerWidth / 2, y = window.innerHeight / 2) {
    const anchor = anchorAt(x, y);
    stretch.commit(scale);
    keep(anchor);
  }

  function finishGlides() {
    for (const a of glides) a.finish();
    glides = [];
  }

  function visibleTiles() {
    const h = window.innerHeight, out = [];
    for (const t of root.querySelectorAll(".tile")) {
      const r = t.getBoundingClientRect();
      if (r.bottom > -50 && r.top < h + 50) out.push(t);
      else if (out.length && r.top >= h + 50) break; // tiles are in document order
    }
    return out;
  }

  // Scroll so the anchored tile is back under the point. A re-laid-out timeline replaced the element,
  // so find the new one with the same index.
  function keep(anchor) {
    if (!anchor) return;
    const el = anchor.el.isConnected ? anchor.el : root.querySelector(`.tile[data-i="${anchor.el.dataset.i}"]`);
    if (!el) return;
    const b = el.getBoundingClientRect();
    window.scrollBy(0, b.top + anchor.fy * b.height - anchor.y);
  }

  // The tile under (x, y), and where in it (fy) the point falls. Fallback: the first tile on screen.
  function anchorAt(x, y) {
    const el = document.elementFromPoint(x, y)?.closest?.(".tile");
    if (el) {
      const r = el.getBoundingClientRect();
      return { el, y, fy: (y - r.top) / r.height };
    }
    const first = visibleTiles().find((t) => t.getBoundingClientRect().top >= 0);
    return first ? { el: first, y: first.getBoundingClientRect().top, fy: 0 } : null;
  }

  // ------------------------------------------------------------ inputs

  // Chrome / Edge / Firefox: pinch arrives as ctrl+wheel.
  let wheelTimer;
  window.addEventListener("wheel", (e) => {
    if (!e.ctrlKey) return;
    e.preventDefault(); // stop browser page zoom
    if (!g) begin(e.clientX, e.clientY);
    const dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;         // lines -> pixels
    const d = Math.max(-40, Math.min(40, dy));                      // tame ctrl + mouse-wheel notches
    update(g.scale * Math.exp(-d * WHEEL_GAIN));
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(end, WHEEL_END_MS);
  }, { passive: false });

  // Safari (macOS trackpad, iOS/iPadOS touch): gesture events with a cumulative scale.
  window.addEventListener("gesturestart", (e) => { e.preventDefault(); begin(e.clientX, e.clientY); });
  window.addEventListener("gesturechange", (e) => { e.preventDefault(); update(e.scale); });
  window.addEventListener("gestureend", (e) => { e.preventDefault(); end(); });

  // Other touchscreens. iOS/iPadOS already delivers pinches as gesture events above.
  if (!("ongesturechange" in window)) {
    let d0 = 0;
    const dist = (t) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
    root.addEventListener("touchstart", (e) => {
      if (e.touches.length !== 2) return;
      d0 = dist(e.touches);
      begin((e.touches[0].clientX + e.touches[1].clientX) / 2, (e.touches[0].clientY + e.touches[1].clientY) / 2);
    }, { passive: true });
    root.addEventListener("touchmove", (e) => {
      if (e.touches.length !== 2 || !d0) return;
      e.preventDefault(); // no page zoom; one-finger scrolling is untouched
      update(dist(e.touches) / d0);
    }, { passive: false });
    const stop = (e) => { if (d0 && e.touches.length < 2) { d0 = 0; end(); } };
    root.addEventListener("touchend", stop);
    root.addEventListener("touchcancel", stop);
  }

  // Keyboard: + / -
  window.addEventListener("keydown", (e) => {
    if (e.target.matches?.("input, select, textarea") || e.metaKey || e.ctrlKey) return;
    const k = e.key === "+" || e.key === "=" ? -1 : e.key === "-" || e.key === "_" ? 1 : 0;
    if (!k) return;
    if (stretching()) stretchBy(KEY_STRETCH ** -k);
    else commit(clamp(level + k));
  });

  // stretchBy(factor): a timeline stretch from outside (the zoom slider), keeping the middle of the screen in place
  return { set: (i) => commit(clamp(i)), get level() { return level; }, stretchBy: (s) => stretchBy(s) };
}
