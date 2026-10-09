import { LEVELS, setupZoom } from "./zoom.js";
import { renderDocument } from "./document.js";
import { renderMap, leaveMap } from "./map.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const pct = (x) => `${Math.round(x * 100)}%`;
const clock = (s) => {
  s = Math.max(0, Math.round(s));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
};

const panel = $("panel"), main = $("main");
// The live count: moved into the Evidence and Sort & filter panels when they open (a panel redraw detaches it,
// so it is held here rather than looked up by id).
const statsEl = $("stats");
const cats = new Set(); // the chosen categories (Sort & filter); a frame must have every one
let facets = { category: {}, year: {} }; // counts over the whole folder, from the first load
const videos = new Map();   // video_id -> { duration_s, frame_times: [[frame_id, t], ...], ... }
const details = new Map();  // frame_id -> Promise<full frame record>
let items = [], total = 0, current = -1, facetsLoaded = false;
// Scrubbing / arrow keys scroll the grid under a still cursor. Ignore the hovers that causes
// until the pointer really moves.
let hoverPaused = false, pointerXY = "";
// A clicked frame is pinned: the panel sticks to it and the other tiles dim, until it's clicked again.
let pinned = null;          // frame_id
// The Video and Evidence panels hold the panel like a pin; the library shown is picked by the `lib` cookie.
let panelMode = null, currentLib = "";  // panelMode: "video" | "evidence"
// Hovering frames while Video or Evidence is open previews them in its place; leaving the images brings it back.
let peek = null;            // { nodes, focus } of the Video/Evidence panel while a frame is previewed
// Clicking the panel title switches every title between the original and YouTube's English title.
// Timeline view: each video drawn as an editing timeline, with a marker at every extracted frame.
// Its subtitles mode shows each video's captions instead of the filmstrip.
// The chosen view is remembered per browser (localStorage.view), so a reload stays on it; the first visit opens on the
// gallery (with the Video panel, the panel's resting state).
const VIEWS = ["grid", "map", "timeline", "subtitles", "document"];
const savedView = (() => { try { const v = localStorage.getItem("view"); return VIEWS.includes(v) ? v : "grid"; } catch { return "grid"; } })();
let timeline = savedView === "timeline" || savedView === "subtitles", subs = savedView === "subtitles";
let documentView = savedView === "document";
// Temporal Map (map.js): a video's inferred path on a map, in step with the video; it takes over main and #research.
let mapView = savedView === "map";
// The first time the gallery is drawn (every page load, hard reloads included), the images on screen fade in one
// by one in a random order across the grid; later re-draws (search, filters) fade in all at once. They wait until
// those images have arrived (or REVEAL_WAIT_MS), so on a hard reload, with nothing cached, they still appear
// scattered rather than in the order they download.
let revealPending = true;
const REVEAL_MS = 1400;      // the random delays are spread over this
const REVEAL_WAIT_MS = 3000; // the longest the images on screen wait for each other

// ---------------------------------------------------------------- data

async function loadVideos() {
  for (const v of await (await fetch("/api/videos?limit=1000")).json()) {
    v.order = new Map(v.frame_times.map(([id], k) => [id, k + 1])); // 1-based position in the video
    videos.set(v.video_id, v);
  }
}

let loadSeq = 0;
// The last frame list, by query: switching view asks for the same frames, so it is drawn at once from here
// instead of fetched again. Anything else (a search, a filter, a job adding videos) fetches afresh.
let framesCache = null; // { key, res }
async function load(reuse = false) {
  const seq = ++loadSeq;
  if (documentView) return renderDocument(main, $("research"));
  if (mapView) return renderMap(main, $("research"));
  const keep = items[current]?.frame_id;
  const p = new URLSearchParams({ limit: 500 });
  if ($("q").value) p.set("q", $("q").value);
  for (const c of cats) p.append("category", c);
  if ($("year").value) p.set("year", $("year").value);
  if (queryImage) { p.set("sort", "image"); p.set("image", queryImage.id); }
  else if ($("sort").value) p.set("sort", $("sort").value); // (the image sort is the branch above)
  // The API returns at most 500 frames per request: page through all of them, or the grid silently
  // drops whole videos and the numbering stops matching the timeline tally.
  const key = p.toString();
  const res = reuse && framesCache?.key === key ? { ...framesCache.res, items: [...framesCache.res.items] }
    : await (await fetch("/api/frames?" + p)).json();
  while (res.items.length < res.total) {
    p.set("offset", res.items.length);
    const page = await (await fetch("/api/frames?" + p)).json();
    if (!page.items.length) break;
    res.items.push(...page.items);
  }
  if (seq !== loadSeq) return; // a newer search started while this one was loading
  framesCache = { key, res: { ...res, items: [...res.items] } };
  if (!facetsLoaded) {
    facets = res.facets;
    for (const k of Object.keys(res.facets.year)) $("year").add(new Option(k, k));
    if (panelMode === "filters" && !peek) showFilters();
    total = res.total;
    facetsLoaded = true;
  }
  render(res.items);
  showStats(res.items);
  warmSoon();
  current = -1;
  const pin = items.findIndex((it) => it.frame_id === pinned);
  if (pin >= 0) return setPin(pin);
  setPin(-1);
  const again = items.findIndex((it) => it.frame_id === keep);
  again >= 0 ? select(again) : (endPeek(), intro());
}

function detail(id) {
  if (!details.has(id)) {
    details.set(id, fetch("/api/frames/" + encodeURIComponent(id)).then((r) => {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).catch((e) => { details.delete(id); throw e; }));
  }
  return details.get(id);
}

// ---------------------------------------------------------------- grid

function render(list) {
  if (documentView || mapView) return;
  const sorted = !timeline && !!($("sort").value || queryImage);
  const groups = new Map();
  if (sorted) {
    // Keep the server's order; each run of frames with the same sort_group is laid out as one block.
    let key, n = 0;
    for (const it of list) {
      if (it.sort_group !== key) { key = it.sort_group; groups.set(n++, []); }
      groups.get(n - 1).push(it);
    }
  } else {
    // By video, in the order the server returned them (so a sort still decides which videos come first).
    for (const it of list) {
      if (!groups.has(it.video_id)) groups.set(it.video_id, []);
      groups.get(it.video_id).push(it);
    }
    for (const g of groups.values()) g.sort((a, b) => a.timestamp_s - b.timestamp_s);
  }
  main.classList.toggle("sorted", sorted);
  main.classList.toggle("timeline", timeline);
  main.classList.toggle("subtitles", subs);
  thumbs.disconnect();
  items = [...groups.values()].flat(); // index order == on-screen order

  const q = $("q").value.trim();
  // an empty folder (a new project) shows nothing at all; "no match" is only for a search or filter
  main.innerHTML = items.length || !library.frames ? "" : `<p class="empty">No frames match${q ? ` “${esc(q)}”` : ""}${
    cats.size || $("year").value ? " with these filters" : ""}.</p>`;
  if (timeline) return items.length && renderTimeline(groups);
  const reveal = revealPending && items.length > 0 && !reduced();
  if (items.length) revealPending = false;
  let i = 0;
  for (const frames of groups.values()) {
    const order = videos.get(frames[0].video_id)?.order;
    const sec = document.createElement("section");
    // Tile numbers: position in the video, or rank in the chosen sort.
    sec.innerHTML = `<div class="grid">${frames.map((it) =>
        `<figure class="tile" data-i="${i}"><span class="n">${sorted ? ++i : (i++, order?.get(it.frame_id) ?? "")}</span>` +
        `<img loading="lazy" decoding="async" src="${it.thumb_url}" alt=""></figure>`).join("")}</div>`;
    main.append(sec);
  }
  const imgs = [...main.querySelectorAll("img")];
  // (measuring here also settles their style at opacity 0, so even cached images fade rather than pop in)
  const held = new Set(reveal ? imgs.filter((img) => { const r = img.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; }) : []);
  for (const img of imgs) {
    if (held.has(img)) continue; // (images below the screen fade in as they load, when scrolled to)
    if (img.complete) img.classList.add("loaded");
    else img.addEventListener("load", () => img.classList.add("loaded"), { once: true });
  }
  if (held.size) revealGallery([...held]);
}

function revealGallery(shown) {
  const arrived = (img) => img.complete || new Promise((ok) => {
    img.addEventListener("load", ok, { once: true });
    img.addEventListener("error", ok, { once: true });
  });
  Promise.race([Promise.all(shown.map(arrived)), new Promise((ok) => setTimeout(ok, REVEAL_WAIT_MS))]).then(() => {
    const fadeIn = (img) => {
      Object.assign(img.style, { transitionDelay: `${Math.round(Math.random() * REVEAL_MS)}ms`, transitionDuration: ".6s" });
      img.classList.add("loaded");
      setTimeout(() => { img.style.transitionDelay = img.style.transitionDuration = ""; }, REVEAL_MS + 700);
    };
    for (const img of shown) {
      if (!img.isConnected) continue; // the grid was drawn again meanwhile
      // one still downloading (a slow connection) gets a random delay of its own when it arrives, so the
      // stragglers don't fill in top to bottom
      if (img.complete) fadeIn(img);
      else img.addEventListener("load", () => fadeIn(img), { once: true });
    }
  });
}

// Each video is laid out like a clip on an editing timeline: each extracted frame starts at a black vertical
// marker at its timestamp and runs until the next frame's marker. Its image sits in the middle of that stretch,
// and its edges are slit-scanned out to the markers: the image's outermost columns stretched sideways, shading
// into the neighbouring frame's edge so the streaks blend from one image to the next. No text.
// Frames outside the current search/filters leave an empty stretch of strip. All videos
// share one time scale so lengths compare; pinching stretches it. A video longer than the page width
// wraps onto more lines below, like text, so nothing runs off screen.
// Clicking a strip opens it: the timeline spreads apart there, and that frame's strip grows until its
// image shows whole.
let tlVideos = [];          // [{ dur, times: [[frame_id, t]], shown: Map frame_id -> [item, index], order }]
// Time stretch, separate from the grid's density: 1 fits the longest video to the width. It reaches far
// enough in that the shortest video spans a couple of widths, so short clips (up to 100 frames in a
// minute or two) spread out too.
// The subtitles view keeps its own stretch: reading needs far more room than seeing.
const zoomKey = () => (subs ? "subtitleZoom" : "timelineZoom");
const readZoom = () => { try { return Number(localStorage.getItem(zoomKey())) || 1; } catch { return 1; } };
let tlScale = readZoom();
let tlLive = 1;             // live pinch factor on top of tlScale
const segEls = new Map();   // "index:line" -> segment element, reused across re-layouts (see layoutTimeline)
const spreads = new Map();  // frame_id -> { p, from, to, start }: how far the timeline is spread open there (0..1)
const TL_GAP = 10, TL_PAD = 12; // px between lines; room above/below a video for the markers
const SPREAD_MS = 650;
const GLIDE_MS = 320;      // an opened image gliding to the line its marker wrapped onto
const SETTLE_MS = 420;     // an opened image gliding into its slot once a zoom stops

function renderTimeline(groups) {
  tlVideos = [];
  segEls.clear();
  let i = 0;
  for (const frames of groups.values()) {
    const v = videos.get(frames[0].video_id);
    const times = [...(v?.frame_times?.length ? v.frame_times : frames.map((it) => [it.frame_id, it.timestamp_s]))]
      .sort((a, b) => a[1] - b[1]);
    const dur = Math.max(frames[0].duration_s || v?.duration_s || 0, times.at(-1)[1] + 1);
    // frames are in time order, like items
    const r = { id: frames[0].video_id, dur, times, shown: new Map(frames.map((it) => [it.frame_id, [it, i++]])), order: v?.order };
    tlVideos.push(r);
    // a transcript fetched ahead of time (prewarm) is drawn with the first layout; one still arriving draws only
    // its own lines, once a frame, however many arrive together
    if (subs) r.subs = subtitleReady.get(r.id) ?? (loadSubtitles(r.id).then((d) => { r.subs = d; wordsSoon(); }, () => {}), null);
  }
  const wrap = document.createElement("div");
  wrap.className = "tl";
  main.append(wrap);
  tlFresh = true;
  layoutTimeline();
  tlFresh = false;
}
// A newly drawn strip dresses only what comes near the screen (the observer), not every strip at once: thousands of
// images in one style pass is the stall. It fades in (.tl), so the first frame before the observer runs never shows.
let tlFresh = false;

function tlRange() {
  const durs = tlVideos.map((r) => r.dur), longest = Math.max(1, ...durs);
  const hi = Math.max(6, (2 * longest) / Math.max(1, Math.min(...durs)));
  // subtitles: until quick speech (about 3 words a second) has room for every word
  if (subs) return [0.5, Math.max(hi, (READ_PPS * longest) / (main.querySelector(".tl")?.clientWidth || innerWidth))];
  return [0.5, hi];
}
const clampScale = (s) => { const [lo, hi] = tlRange(); return Math.min(hi, Math.max(lo, s)); };
const clamp01 = (x) => Math.min(1, Math.max(0, x));

// Re-layout (every frame of a pinch or a spread) moves and resizes the existing elements instead of
// rebuilding them: fresh elements paint blank until their thumbnail is drawn, which flashes the track
// through. Edges are whole pixels, so neighbouring strips meet without a hairline gap. Lines run the full
// width, so the strip reflows smoothly as it stretches. A video's height doesn't jump when it gains or
// loses a line: it eases there (tlTick), growing downward over the new line.
function layoutTimeline() {
  const wrap = main.querySelector(".tl");
  if (!wrap) return;
  const W = wrap.clientWidth;
  // The strip is thin: each image keeps the width it would have at full height (IH) and is squashed
  // down to the track height H. An opened frame shows its image undistorted.
  const IH = Math.round(Math.min(84, Math.max(44, innerWidth * 0.055)));      // unsquashed image height
  const H = subs ? SUB_H : Math.round(IH * 0.4);                              // track height
  const HF = Math.round(Math.min(IH * 3.2, 280, innerHeight * 0.4));          // height of a line spread open
  const longest = Math.max(1, ...tlVideos.map((r) => r.dur));
  const pps = (W / longest) * clampScale(tlScale * tlLive); // pixels per second
  const pin = pinned === null ? -1 : items.findIndex((it) => it.frame_id === pinned);
  const used = new Set();
  tlVideos.forEach((r, v) => {
    // Where time t sits along the unwrapped strip, in px. An opened frame's image gets a slot of its own in
    // the strip that shares a border with its marker, on the marker's line: the image never moves to another
    // line and the timeline never grows backwards. A frame in the left half of its line opens to the right:
    // the slot starts at its marker and the strip after it slides on (onto the next line if it has to). One in
    // the right half (or whose image doesn't fit to the right) opens to the left: its marker stays put, the
    // slot ends at it, and the strip before it on that line squeezes into the room left of the image, still
    // in order. Nothing is drawn under the image. The slot grows with the spread p.
    // The side is chosen when the image opens, and again when a zoom stops (its marker may have moved to the
    // other half): then the slot on the old side closes as the one on the new side opens (SETTLE_MS) while the
    // image glides into it (releaseImages). During a zoom the side is kept. Where a side has less room than the
    // image needs, the image is shown smaller (`fit`).
    const bends = [], slots = []; // bends: [from t, to t, px] (a ramp over [from, to], then held); slots: [t at the slot's end, px, frame index, p, fit]
    const settled = new Map();    // frame index -> its image's width and side once any change of side is over
    const now = performance.now();
    r.times.forEach(([id, t]) => {
      const s = spreads.get(id), hit = r.shown.get(id);
      if (!s || !hit) return;
      const it = hit[0];
      const fw = Math.min(W, HF * (it.width && it.height ? it.width / it.height : 16 / 9));
      const x = t * pps, l = Math.floor(x / W + 1e-6), c = x - l * W; // where its marker sits with nothing open
      const side = c < W / 2 && c + fw <= W ? "right" : "left";
      if (!s.side) s.side = side;
      else if (s.rechoose) {
        s.rechoose = false;
        if (side !== s.side) Object.assign(s, { side, sideAt: now });
      }
      const k = s.sideAt ? easeOut(clamp01((now - s.sideAt) / SETTLE_MS)) : 1; // how far across a change of side (as the image glides)
      const slot = (side, weight) => {
        const room = side === "right" ? W - c : c, fit = clamp01(room / fw), g = fw * fit * s.p * weight;
        if (g <= 0) return;
        if (side === "right") { // everything after the marker moves on by g
          bends.push([t + 1e-6, t + 1e-6, g]);
          slots.push([t + 1e-6, g, hit[1], s.p, fit]);
        } else { // the line before the marker squeezes by g
          bends.push([(l * W) / pps, t, -g], [t, t, g]);
          slots.push([t, g, hit[1], s.p, fit]);
        }
      };
      slot(s.side, k);
      if (k < 1) slot(s.side === "right" ? "left" : "right", 1 - k);
      settled.set(hit[1], { width: fw * clamp01((s.side === "right" ? W - c : c) / fw) * s.p, side: s.side });
    });
    const X = (t) => bends.reduce((x, [a, b, e]) => x + e * (b > a ? clamp01((t - a) / (b - a)) : +(t >= b)), t * pps);
    // where each image sits, unwrapped: its slots on either side of the marker (both while it changes side)
    const byFrame = new Map();
    for (const [at, g, i, p, fit] of slots) {
      const a = X(at) - g, b = X(at), h = byFrame.get(i);
      byFrame.set(i, h ? [Math.min(h[0], a), Math.max(h[1], b), i, p, Math.max(h[4], fit)] : [a, b, i, p, fit]);
    }
    const holes = [...byFrame.values()].sort((u, v) => u[0] - v[0]);
    const total = X(r.dur);
    const n = Math.max(1, Math.ceil(total / W - 1e-6));
    Object.assign(r, { X, W, holes, heights: null, sec: null });
    // An opened frame makes its line taller.
    const heights = Array.from({ length: n }, (_, l) => Math.round(Math.min(HF, H + (HF - H) * holes.reduce((sum, [a, b, , p, fit]) =>
      sum + p * fit * Math.max(0, Math.min(b, (l + 1) * W) - Math.max(a, l * W)) / Math.max(1, b - a), 0))));

    let sec = wrap.children[v];
    if (!sec) {
      sec = wrap.appendChild(Object.assign(document.createElement("section"), { className: "tl-video" }));
      sec.fresh = true;
    }
    while (sec.children.length > n) sec.lastChild.remove();
    while (sec.children.length < n) sec.append(Object.assign(document.createElement("div"), { className: "tl-track" }));
    for (let l = 0; l < n; l++) {
      const tr = sec.children[l];
      tr.style.width = `${Math.round(Math.min(W, total - l * W))}px`;
      // a line's height eases to its target (tlTick), so an opened image moving to another line doesn't
      // make the lines jump; a new line starts at its height
      tr.target = heights[l];
      tr.ih = IH;
      if (tr.h === undefined || reduced()) tr.h = tr.target;
      else if (tr.h !== tr.target) { easing.add(tr); tlAnimate(); }
      tr.style.height = `${tr.h}px`;
      tr.style.setProperty("--ih", `${Math.max(IH, tr.h)}px`); // images squash only on a thin line
    }
    r.sec = sec;
    r.heights = heights;
    sec.target = heights.reduce((a, b) => a + b, 0) + TL_GAP * (n - 1) + 2 * TL_PAD;
    if (sec.fresh || reduced()) { sec.fresh = false; sec.h = sec.target; sec.style.height = `${sec.h}px`; }
    else if (sec.h !== sec.target) tlAnimate();

    r.times.forEach(([id, t], k) => {
      const hit = r.shown.get(id);
      if (!hit) return; // outside the search/filters: an empty stretch, no marker
      const end = k + 1 < r.times.length ? r.times[k + 1][1] : r.dur;
      const x0 = X(t), x1 = X(end);
      const near = (j) => r.shown.get(r.times[j]?.[0])?.[0].thumb_url ?? ""; // the neighbouring frames, when shown
      // A frame's strip runs until the next marker, continuing on the next line if it crosses the edge.
      for (let l = Math.min(n - 1, Math.floor(x0 / W + 1e-6)); l < n && l * W < x1 - 0.01; l++) {
        const a = l * W, left = Math.round(Math.max(x0, a) - a), right = Math.round(Math.min(x1, a + W) - a);
        const key = `${hit[1]}:${l}`;
        used.add(key);
        let seg = segEls.get(key);
        if (!seg) {
          seg = document.createElement("div");
          seg.dataset.i = hit[1];
          seg.dataset.bg = hit[0].thumb_url;
          seg.dataset.prev = near(k - 1);
          seg.dataset.next = near(k + 1);
          const it = hit[0];
          seg.style.setProperty("--ar", it.width && it.height ? it.width / it.height : 16 / 9);
          if (subs); // the Transcript shows words, not the strips' images: nothing to dress
          else if (dressed.has(dressKey(seg)) && !tlFresh) dress(seg);
          else thumbs.observe(seg);
          segEls.set(key, seg);
        }
        const split = a > x0 + 0.01 || a + W < x1 - 0.01; // the frame's stretch wraps onto another line
        seg.className = `tile seg${a > x0 + 0.01 ? " cont" : ""}${split ? " split" : ""}` +
          `${hit[1] === current ? " on" : ""}${hit[1] === pin ? " pinned" : ""}`;
        seg.style.left = `${left}px`;
        seg.style.width = `${Math.max(0, right - left)}px`;
        // A wrapped frame's pieces: its whole stretch and its middle, from this piece's left edge. A piece that is
        // the whole stretch needs none (the CSS centres its image), so a zoom doesn't restyle every strip.
        if (split) {
          const o = a + left;
          seg.style.setProperty("--fx0", `${x0 - o}px`);
          seg.style.setProperty("--fx1", `${x1 - o}px`);
          seg.style.setProperty("--cx", `${(x0 + x1) / 2 - o}px`);
        }
        if (seg.parentNode !== sec.children[l]) sec.children[l].append(seg);
      }
    });
    // The opened images, each in its slot (never across two lines: the slot is chosen to fit).
    for (const [a, b, i] of holes) {
      const it = items[i], l = Math.min(n - 1, Math.floor((a + b) / 2 / W)), key = `img:${i}`;
      used.add(key);
      let el = segEls.get(key);
      if (!el) {
        el = Object.assign(document.createElement("div"), { className: "tile seg image" });
        el.dataset.i = i;
        el.style.setProperty("--img", `url("${it.thumb_url}")`);
        sharpen(el, it.web_url);
        segEls.set(key, el);
      }
      el.className = `tile seg image${i === current ? " on" : ""}${i === pin ? " pinned" : ""}`;
      // its slot moved onto another line (a re-layout other than a zoom): the image glides there (tlTick)
      if (el.parentNode && el.parentNode !== sec.children[l] && !held.has(el) && !reduced()) {
        glides.set(el, { from: el.getBoundingClientRect(), start: performance.now(), ms: GLIDE_MS });
        tlAnimate();
      }
      el.slotBox = { left: `${Math.round(a - l * W)}px`, width: `${Math.round(b - a)}px` };
      el.settled = settled.get(i);
      if (!held.has(el)) Object.assign(el.style, el.slotBox); // a held image stays where it is on screen (holdImages)
      if (el.parentNode !== sec.children[l]) sec.children[l].append(el);
    }
  });
  while (wrap.children.length > tlVideos.length) wrap.lastChild.remove();
  for (const [key, seg] of segEls) if (!used.has(key)) { thumbs.unobserve(seg); seg.remove(); segEls.delete(key); }
  if (subs) drawWords();
  syncSlider();
}

// Zoom slider, in every view; right is bigger. Timeline and subtitles: the same stretch as a pinch, on a log
// scale over its whole range. Gallery: one step per column count (zoom.js LEVELS), fewest columns on the right,
// snapping with the same glide as a pinch.
const SLIDER_MAX = 1000;
let gridLevel = 0; // the gallery's column level (zoom.js), kept by its onChange
// Reconstruction: the same slider, there for consistency, is the page's vertical scroll (top at the left).
const scrollRoom = () => Math.max(0, document.documentElement.scrollHeight - innerHeight);
function syncSlider(animate = false) {
  const el = $("tlzoom");
  el.title = el.ariaLabel = documentView ? "Scroll" : "Zoom (or pinch, or + / −)";
  if (documentView) return setSlider(SLIDER_MAX, scrollRoom() ? (SLIDER_MAX * scrollY) / scrollRoom() : 0, animate);
  if (!timeline) return setSlider(LEVELS.length - 1, LEVELS.length - 1 - gridLevel, animate);
  const [lo, hi] = tlRange(), s = clampScale(tlScale * tlLive);
  setSlider(SLIDER_MAX, SLIDER_MAX * Math.log(s / lo) / Math.log(hi / lo), animate);
}
// Switching views, the slider's dot glides from where it was to where the new view puts it (a range input can't be
// eased by CSS, so its value is). It chases its target each frame, closing most of the gap in about 0.4 s and
// slowing as it arrives, so a target that moves while it glides (Reconstruction resetting its scroll and loading its
// pages) only bends its path, never makes it jump. A timeline's position is known only once it is laid out
// (layoutTimeline), so switching to one the dot waits for that (at most HOLD_MS) rather than set off the wrong way.
// Grabbing the slider ends the glide.
const SLIDE_TAU = 110, HOLD_MS = 500;
let slide = null;  // { pos, to, last, hold }: dot positions as fractions of the track; hold: time it may set off
let dotWas = null; // where the dot was when a view switch began (the old view's teardown may move the slider first)
function setSlider(max, value, animate) {
  const el = $("tlzoom"), to = max ? Math.min(1, Math.max(0, value / max)) : 0;
  const at = slide ? slide.pos : animate && dotWas !== null ? dotWas : +el.value / (+el.max || 1);
  if (animate) dotWas = null;
  el.max = max;
  if (animate && !reduced() && el.offsetParent && Math.abs(at - to) > 0.002) {
    const first = !slide, now = performance.now();
    slide = { pos: at, to, last: now, hold: timeline ? now + HOLD_MS : 0 };
    el.value = at * max;
    if (first) requestAnimationFrame(glideDot);
  } else if (slide) Object.assign(slide, { to, hold: 0 }); // under way (or waiting): aim it here, and go
  else el.value = to * max;
}
function glideDot(now) {
  if (!slide) return;
  // at most a frame's worth per step: after the page stalls (a timeline laying out) the dot still glides, not leaps
  const el = $("tlzoom"), dt = Math.min(34, Math.max(0, now - slide.last));
  slide.last = now;
  if (now < slide.hold) return requestAnimationFrame(glideDot);
  slide.pos += (slide.to - slide.pos) * (1 - Math.exp(-dt / SLIDE_TAU));
  if (Math.abs(slide.to - slide.pos) < 0.001) { el.value = slide.to * +el.max; slide = null; return; }
  el.value = slide.pos * +el.max;
  requestAnimationFrame(glideDot);
}
$("tlzoom").addEventListener("pointerdown", () => {
  if (slide) { $("tlzoom").value = slide.to * +$("tlzoom").max; slide = null; }
});
$("tlzoom").addEventListener("input", (e) => {
  if (documentView) return scrollTo(0, (scrollRoom() * e.target.value) / SLIDER_MAX);
  if (!timeline) { // (the dot moves freely while dragged; the gallery steps to the nearest column count)
    const i = LEVELS.length - 1 - Math.round(+e.target.value);
    if (i !== zoom.level) zoom.set(i);
    return;
  }
  holdImages("slider", 3000); // until it is let go (change)
  const [lo, hi] = tlRange();
  zoom.stretchBy(lo * (hi / lo) ** (e.target.value / SLIDER_MAX) / tlScale);
});

// An opened frame swaps its thumbnail for the full image once that has loaded (no blank in between).
function sharpen(seg, url) {
  if (!url || seg.dataset.sharp) return;
  seg.dataset.sharp = url;
  const img = new Image();
  img.src = url;
  img.decode().then(() => seg.style.setProperty("--sharp", `url("${url}")`), () => {});
}

// Open the timeline at frame_id (closing any other), or close it (null). Two images in the same video never
// move at once: each image's slot moves the strip after it, so one still closing would push the new frame
// along (even onto the next line). The open one closes as usual, and the new one opens once it has; while
// an image is closing, its video's other frames can't be opened (see the click handler).
const frameVideo = (fid) => items.find((it) => it.frame_id === fid)?.video_id;
const closingIn = (v) => [...spreads].some(([key, s]) => s.to === 0 && frameVideo(key) === v);
function spreadTo(id) {
  const now = performance.now();
  const v = id !== null ? frameVideo(id) : null;
  let wait = 0; // until the other images in this video have closed
  let changed = false; // nothing opens or closes (unpinning with nothing open, as each view draws): no re-layout
  for (const [key, s] of spreads) {
    if (key === id) continue;
    if (s.to !== 0) { Object.assign(s, { from: s.p, to: 0, start: now }); changed = true; }
    if (v !== null && frameVideo(key) === v) wait = Math.max(wait, s.start + SPREAD_MS - now);
  }
  if (id !== null && timeline) {
    const s = spreads.get(id);
    if (!s) { spreads.set(id, { p: 0, from: 0, to: 1, start: now + wait }); changed = true; }
    else if (s.to !== 1) { Object.assign(s, { from: s.p, to: 1, start: now + wait, settled: false }); changed = true; }
  }
  if (!changed) return;
  layoutTimeline();
  tlAnimate();
}

// One animation loop for the timeline: spreads opening/closing and video heights easing to their new
// size. The video under the pointer (or the pinned one) keeps its place on screen while things move.
let tlRaf = 0, tlLast = 0;
const easing = new Set();   // lines easing to a new height
const glides = new Map();   // opened image -> { from: the box it glides from, start, ms }

// While zooming (pinch, slider or + / -) the opened images stay where they are on screen, while the
// timeline zooms under them and their slots move with their markers; when the zoom stops, each glides
// from where it was into its slot. A held image lets the pointer through, so the zoom keeps the frame
// under the pointer in place, not the image.
const held = new Map();     // opened image -> its box on screen when the zoom began
let holdTimer = 0, holdBy = null;
function holdImages(by, idleMs) {
  if (!holding() && timeline) {
    holdBy = by;
    for (const el of main.querySelectorAll(".seg.image")) {
      el.style.transform = "";
      glides.delete(el);
      const r = el.getBoundingClientRect();
      held.set(el, r);
      Object.assign(el.style, { position: "fixed", left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${r.height}px`, pointerEvents: "none" });
    }
    if (!held.size) holdBy = by; // nothing open: still a zoom, so nothing else needs doing
  }
  clearTimeout(holdTimer);
  holdTimer = setTimeout(releaseImages, idleMs); // the end of a zoom with no end event (or one that never came)
}
const holding = () => holdBy !== null;
function releaseImages() {
  clearTimeout(holdTimer);
  if (!holding()) return;
  holdBy = null;
  for (const s of spreads.values()) if (s.to === 1) s.rechoose = true; // its marker may now be in the other half
  layoutTimeline();
  const now = performance.now();
  for (const [el, r] of held) {
    Object.assign(el.style, { position: "", top: "", height: "", pointerEvents: "" }, el.slotBox);
    if (el.isConnected && !reduced()) glides.set(el, { from: r, start: now, ms: SETTLE_MS });
  }
  held.clear();
  tlAnimate();
}
const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const easeInOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2);
const easeOut = (x) => 1 - (1 - x) ** 3; // moves at once and slows into place: no wind-up, no overshoot
function tlAnimate() {
  if (!tlRaf) tlRaf = requestAnimationFrame(tlTick);
}
function tlTick(now) {
  tlRaf = 0;
  const dt = tlLast ? Math.min(64, now - tlLast) : 16;
  const anchor = tlAnchor(), top = anchor?.getBoundingClientRect().top;
  let busy = false, spreading = false, opened = null;
  for (const [id, s] of spreads) {
    const x = reduced() ? 1 : clamp01((now - s.start) / SPREAD_MS);
    const p = s.from + (s.to - s.from) * easeInOut(x);
    if (p !== s.p) { s.p = p; spreading = true; }
    if (s.sideAt && now - s.sideAt < SETTLE_MS + 32) { spreading = true; busy = true; } // changing side
    if (x < 1) busy = true;
    else if (s.to === 0) spreads.delete(id);
    else if (!s.settled) { s.settled = true; opened = id; }
  }
  if (spreading) layoutTimeline();
  const k = 1 - Math.exp(-dt / 70);
  for (const tr of easing) {
    tr.h = Math.abs(tr.target - tr.h) < 0.5 ? tr.target : tr.h + (tr.target - tr.h) * k;
    tr.style.height = `${tr.h}px`;
    tr.style.setProperty("--ih", `${Math.max(tr.ih, tr.h)}px`);
    if (tr.h === tr.target || !tr.isConnected) easing.delete(tr);
    else busy = true;
  }
  for (const sec of main.querySelectorAll(".tl-video")) {
    if (sec.h === sec.target) continue;
    sec.h = Math.abs(sec.target - sec.h) < 0.5 ? sec.target : sec.h + (sec.target - sec.h) * k;
    sec.style.height = `${sec.h}px`;
    busy = true;
  }
  const drift = anchor?.isConnected ? anchor.getBoundingClientRect().top - top : 0;
  if (Math.abs(drift) >= 0.5) scrollBy(0, drift); // (a no-op scrollBy would cancel a smooth scroll)
  // Once open, make sure the whole opened frame is on screen.
  if (opened !== null) {
    const i = items.findIndex((it) => it.frame_id === opened);
    const pieces = [...main.querySelectorAll(`.seg[data-i="${i}"]`)].map((e) => e.getBoundingClientRect());
    if (pieces.length && (pieces.at(-1).bottom > innerHeight - 110 || pieces[0].top < 0)) {
      scrollBy({ top: pieces[0].top - Math.max(40, (innerHeight - (pieces.at(-1).bottom - pieces[0].top)) / 2), behavior: "smooth" });
    }
  }
  // A gliding image blends, every frame, from the box it had on its old line to where it belongs now (which
  // moves while the lines ease), in place and in size, so it starts exactly where it was and ends in place.
  for (const [el, g] of glides) {
    el.style.transform = "";
    const x = reduced() ? 1 : clamp01((now - g.start) / g.ms);
    if (x >= 1 || !el.isConnected) { glides.delete(el); el.style.transformOrigin = ""; continue; }
    // It heads for its final size (not its slot's size part-way through a change of side, which would make it
    // shrink and grow back), kept against its marker on the side it settles on.
    const to = el.getBoundingClientRect(), e = 1 - easeOut(x), f = g.from;
    // Its edge heads straight for its marker (an image left of the marker by its right edge).
    const fw = el.settled?.width || to.width, fh = el.parentNode.target ?? to.height, byRight = el.settled?.side === "left";
    const w = fw + (f.width - fw) * e, h = fh + (f.height - fh) * e;
    const marker = main.querySelector(`.seg:not(.cont):not(.image)[data-i="${el.dataset.i}"]`)?.getBoundingClientRect();
    const edge = marker ? marker.left : byRight ? to.right : to.left;
    const dx = byRight ? edge + (f.right - edge) * e - to.right : edge + (f.left - edge) * e - to.left;
    el.style.transformOrigin = byRight ? "100% 0" : "0 0";
    el.style.transform = `translate(${dx}px, ${(f.top - to.top) * e}px) scale(${w / Math.max(1, to.width)}, ${h / Math.max(1, to.height)})`;
    busy = true;
  }
  if (subs && busy) drawWords(false); // lines may have come into view
  tlLast = busy ? now : 0;
  if (busy) tlAnimate();
}
function tlAnchor() {
  const pinnedSeg = main.querySelector(".seg.pinned");
  if (pinnedSeg) return pinnedSeg.closest(".tl-video");
  const [x, y] = pointerXY.split(",").map(Number);
  const under = pointerXY && document.elementFromPoint(x, y)?.closest?.(".tl-video");
  return under || [...main.querySelectorAll(".tl-video")].find((s) => s.getBoundingClientRect().bottom > 0);
}

// Filmstrip thumbnails load when their segment scrolls into view.
// A strip's slit-scanned edges. Each thumbnail gives its left and right edge slits (2% of its width, just
// inside the border, averaged to one column of SLIT_ROWS pixels). The stretch either side of an image is a
// small image shading from one column to the other, which the CSS stretches across it: from the middle of
// this edge and the neighbour's (where the marker is) to this image's own edge.
// Made once per thumbnail and neighbour pair, in a worker (edges.js) so the page never stalls on them: ahead of
// time while the page is idle (prewarm), and first for the strips coming near the screen.
const SLIT_ROWS = 48, SHADE_COLS = 16;
const edges = new Map();   // thumbnail URL -> the promise of its { l, r } edge columns (RGBA); without a worker only
function edgesOf(url) {
  if (!url) return Promise.resolve(null);
  if (!edges.has(url)) edges.set(url, (async () => {
    const img = new Image();
    img.src = url;
    await img.decode();
    const w = img.naturalWidth, h = img.naturalHeight, k = Math.max(1, Math.round(w / 50)), in1 = Math.round(w / 100);
    const c = Object.assign(document.createElement("canvas"), { width: 2, height: SLIT_ROWS });
    const g = c.getContext("2d", { willReadFrequently: true });
    g.drawImage(img, in1, 0, k, h, 0, 0, 1, SLIT_ROWS);
    g.drawImage(img, w - in1 - k, 0, k, h, 1, 0, 1, SLIT_ROWS);
    const d = g.getImageData(0, 0, 2, SLIT_ROWS).data, col = (x) => d.filter((_, j) => (j >> 2) % 2 === x);
    return { l: col(0), r: col(1) };
  })());
  return edges.get(url);
}
const mix = (a, b) => (b ? a.map((v, j) => (v + b[j]) >> 1) : a);
function shade(a, b) { // column a shading into column b, as a CSS url
  const c = Object.assign(document.createElement("canvas"), { width: SHADE_COLS, height: SLIT_ROWS });
  const px = new Uint8ClampedArray(4 * SHADE_COLS * SLIT_ROWS);
  for (let y = 0; y < SLIT_ROWS; y++)
    for (let x = 0; x < SHADE_COLS; x++)
      for (let ch = 0, f = x / (SHADE_COLS - 1); ch < 4; ch++)
        px[4 * (y * SHADE_COLS + x) + ch] = a[4 * y + ch] + (b[4 * y + ch] - a[4 * y + ch]) * f;
  c.getContext("2d").putImageData(new ImageData(px, SHADE_COLS, SLIT_ROWS), 0, 0);
  return `url("${c.toDataURL()}")`;
}
const dressed = new Map(); // "prev|own|next" thumbnail URLs -> { bl, br }: a strip's two edge shadings
const dressKey = (seg) => `${seg.dataset.prev}|${seg.dataset.bg}|${seg.dataset.next}`;
const edgeWorker = (() => {
  try { return typeof OffscreenCanvas === "function" ? new Worker(new URL("edges.js", import.meta.url), { type: "module" }) : null; }
  catch { return null; }
})();
const shadings = new Map(); // key -> the promise of its entry in `dressed`
const edgeQueue = [];       // jobs not yet sent to the worker: the strips near the screen first, then the prewarm
const edgeWaiting = new Map(); // key -> job sent and not yet answered
const EDGE_JOBS = 8;        // in flight at once, so a strip coming into view never queues behind the whole library
function shading(prev, own, next, urgent) {
  const key = `${prev}|${own}|${next}`;
  if (!shadings.has(key)) {
    shadings.set(key, new Promise((ok, no) => {
      const job = { key, prev, own, next, ok, no };
      urgent ? edgeQueue.unshift(job) : edgeQueue.push(job);
    }));
    pumpEdges();
  } else if (urgent) { // asked for again by a strip near the screen: move it to the front if it is still waiting
    const k = edgeQueue.findIndex((j) => j.key === key);
    if (k > 0) edgeQueue.unshift(...edgeQueue.splice(k, 1));
  }
  return shadings.get(key);
}
function pumpEdges() {
  while (edgeQueue.length && edgeWaiting.size < EDGE_JOBS) {
    const job = edgeQueue.shift();
    if (edgeWorker) {
      edgeWaiting.set(job.key, job);
      edgeWorker.postMessage({ key: job.key, prev: job.prev, own: job.own, next: job.next });
    } else { // no worker (an old browser): on the page, as before
      edgeWaiting.set(job.key, job);
      Promise.all([edgesOf(job.prev), edgesOf(job.own), edgesOf(job.next)]).then(([p, o, n]) => {
        dressed.set(job.key, { bl: shade(mix(o.l, p?.r), o.l), br: shade(o.r, mix(o.r, n?.l)) });
        job.ok();
      }, job.no).finally(() => { edgeWaiting.delete(job.key); pumpEdges(); });
    }
  }
}
if (edgeWorker) edgeWorker.onmessage = ({ data: { key, bl, br, error } }) => {
  const job = edgeWaiting.get(key);
  edgeWaiting.delete(key);
  if (job) {
    if (error) { shadings.delete(key); job.no(); }
    else {
      dressed.set(key, { bl, br });
      job.ok();
    }
  }
  pumpEdges();
};
function dress(seg) {
  seg.style.setProperty("--img", `url("${seg.dataset.bg}")`);
  const key = dressKey(seg), done = dressed.get(key);
  if (done) { seg.style.setProperty("--bl", done.bl); seg.style.setProperty("--br", done.br); return; }
  shading(seg.dataset.prev, seg.dataset.bg, seg.dataset.next, true).then(() => dress(seg), () => {});
}
const thumbs = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    dress(e.target);
    thumbs.unobserve(e.target);
  }
}, { rootMargin: "300px" });

addEventListener("resize", () => { if (timeline) layoutTimeline(); });

// Ahead of time, while the page is idle: what the Filmstrip and Transcript need that the gallery doesn't, so
// switching to them draws at once. Every shown strip's edge shadings (in the worker, top of the page first) and
// every video's transcript. Each is made once (shading, loadSubtitles), so asking again costs nothing. The first
// time waits for the gallery's fade-in to finish, so it never competes with it.
let warmTimer = 0, warmedOnce = false;
function warmSoon() {
  clearTimeout(warmTimer);
  const wait = warmedOnce ? 300 : REVEAL_MS + 700;
  warmTimer = setTimeout(() => (window.requestIdleCallback ?? ((f) => f()))(prewarm, { timeout: 2000 }), wait);
}
function prewarm() {
  if (documentView || mapView || !items.length) return;
  warmedOnce = true;
  const thumb = new Map(items.map((it) => [it.frame_id, it.thumb_url]));
  for (const id of new Set(items.map((it) => it.video_id))) {
    loadSubtitles(id).catch(() => {});
    // the strips' neighbours as layoutTimeline finds them: the video's frames in time order, those shown
    const times = [...(videos.get(id)?.frame_times ?? [])].sort((a, b) => a[1] - b[1]);
    times.forEach(([fid], k) => {
      const own = thumb.get(fid);
      if (own) shading(thumb.get(times[k - 1]?.[0]) ?? "", own, thumb.get(times[k + 1]?.[0]) ?? "", false).catch(() => {});
    });
  }
}

function setView(view) {
  dotWas = slide ? slide.pos : +$("tlzoom").value / (+$("tlzoom").max || 1);
  ++loadSeq; // discard any frame request still loading from the previous view
  documentView = view === "document";
  mapView = view === "map";
  if (!mapView) leaveMap();
  timeline = view === "timeline" || view === "subtitles";
  subs = view === "subtitles";
  tlScale = readZoom();
  try { localStorage.setItem("view", view); } catch {}
  if (documentView || mapView) {
    thumbs.disconnect();
    endPeek();
    setPin(-1);
    current = -1;
    tlVideos = [];
    intro();
    main.classList.remove("sorted", "timeline", "subtitles");
  }
  showView(true);
  scrollTo(0, 0);
  drawWords(); // clears the words when leaving the subtitles view
  load(true);
}
// Four views, one selected at a time. Existing stored view names remain compatible.
const currentView = () => (mapView ? "map" : documentView ? "document" : subs ? "subtitles" : timeline ? "timeline" : "grid");
function showView(animate = false) {
  const takeover = documentView || mapView; // views that bring their own left panel
  main.classList.toggle("document", documentView);
  main.classList.toggle("map", mapView);
  panel.hidden = takeover;
  $("research").hidden = !takeover;
  $("corner").hidden = takeover;
  $("tlzoom").hidden = mapView; // (the Temporal Map grows its timeline out of it: map.js)
  syncSlider(animate);
  for (const b of document.querySelectorAll("button.view")) {
    const on = b.dataset.view === currentView();
    b.classList.toggle("set", on);
    b.setAttribute("aria-pressed", on);
  }
}
$("tlzoom").addEventListener("change", () => {
  releaseImages();
  if (!timeline && !documentView) syncSlider(); // let go in the gallery: the dot settles on its column count
});
// the Reconstruction's scroll slider follows the page: scrolling, and pages loading (which changes the room to scroll)
addEventListener("scroll", () => { if (documentView) syncSlider(); }, { passive: true });
new ResizeObserver(() => { if (documentView) syncSlider(); }).observe(main);
// + / - zoom the timeline (zoom.js); the images hold until the keys have stopped for a moment
addEventListener("keydown", (e) => {
  if (timeline && /^[-+=_]$/.test(e.key) && !e.metaKey && !e.ctrlKey && !e.target.matches?.("input, select, textarea")) holdImages("keys", 350);
}, { capture: true });

// Light/dark: follows the system until chosen here, then remembered per browser. The button names the other one.
const isDark = () => (document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
// an icon only (after the zoom slider): its tooltip and label say which theme it switches to
const themeLabel = () => { const t = `Switch to ${isDark() ? "light" : "dark"}`; $("theme").title = t; $("theme").setAttribute("aria-label", t); };
$("theme").onclick = () => {
  const t = isDark() ? "light" : "dark";
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem("theme", t); } catch {}
  themeLabel();
  drawWords(); // the subtitles are drawn with the theme's colours
};
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { themeLabel(); drawWords(); });
themeLabel();
for (const b of document.querySelectorAll("button.view")) {
  b.onclick = () => { if (b.dataset.view !== currentView()) setView(b.dataset.view); };
  // pointing at Filmstrip or Transcript is a head start on what they need, in case the idle time hasn't done it yet
  if (b.dataset.view === "timeline" || b.dataset.view === "subtitles") b.addEventListener("pointerenter", prewarm);
}

// ---------------------------------------------------------------- subtitles
// The subtitles view is the timeline with the words instead of the images: every word of a video's
// captions sits where it is spoken, on the same lines, time scale and frame markers as the filmstrip,
// with the English below it (the uploader's English subtitles, or a local machine translation spread
// over each phrase). Where a word has no room it is drawn as a dash as long as the room it has, so
// zoomed out a video reads as a line of speech with its pauses, and the words appear as a pinch spreads
// them apart. Place names (matched in the original, never in a translation) are bold, or a heavy dash;
// words about the land (water, terrain, roads, directions, distances: spatial.py) are black, or a medium
// dash; the rest of the speech is faint, so the eye lands on what can place the footage.
// The words are drawn on canvases inside the lines near the screen (see drawWords). Frames still sit
// under their markers: hover, pin and spread work.
const subtitleData = new Map(); // video_id -> Promise<subtitles>
const subtitleReady = new Map(); // video_id -> subtitles, once arrived
function loadSubtitles(id) {
  if (!subtitleData.has(id)) {
    subtitleData.set(id, fetch(`/api/videos/${encodeURIComponent(id)}/subtitles`).then((r) => {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then((d) => { subtitleReady.set(id, d); return d; }).catch((e) => { subtitleData.delete(id); throw e; }));
  }
  return subtitleData.get(id);
}
let wordsRaf = 0;
const wordsSoon = () => { wordsRaf ||= requestAnimationFrame(() => { wordsRaf = 0; drawWords(false); }); };

const LANGS = { uk: "Ukrainian", ru: "Russian", en: "English" };
function subtitleNote(d) {
  if (!d.words.length) return d.fetched ? "No captions on YouTube" : "Captions not fetched yet (evidence relocate)";
  const orig = `${LANGS[d.lang] ?? d.lang} ${d.kind === "auto" ? "auto-captions" : "captions"} from YouTube`;
  const en = d.english?.kind === "manual" ? "English subtitles by the uploader"
    : d.english?.kind === "machine" ? `English: machine translation on this computer (${d.english.model.split("/").pop()}), a reading aid`
    : d.lang === "en" ? "" : "no English yet";
  return [orig, en].filter(Boolean).join(" · ");
}

const SUB_H = 44;       // line height in the subtitles view: the original above, the English below
const READ_PPS = 170;   // px per second at the far end of the subtitles stretch
const WORD_GAP = 5;     // px kept clear after a word before the next one
// Place names, words about the land and search matches show as text first (see drawLines). To compare
// with the plain rule (every word shows only once it fits before the next), run in the browser console:
//   localStorage.wordPriority = "off"   (and reload; delete it to switch priority back on)
const WORD_PRIORITY = (() => { try { return localStorage.getItem("wordPriority") !== "off"; } catch { return true; } })();
// Opacity of words about the land (both rows) and of the English, a step below place names (full),
// so the places stand out most. An opacity, so light and dark mode drop by the same proportion.
const SECOND = 0.8;
const NUDGE_PX = 120;  // how far a priority word may move along to follow the one before it
const widths = new Map(); // font + word -> px
// Each line near the screen (a screen's height either side) has its own canvas inside the line, so the
// words scroll with it natively and can't lag behind. Canvases are recycled as lines leave that range:
// a long video at reading width wraps onto a thousand lines.
const lineCanvas = new Map(); // .tl-track -> canvas
const canvasPool = [];
let wordsVersion = 0;         // bumped by every re-layout: each canvas in use is drawn again
let drawRaf = 0;
addEventListener("scroll", () => {
  if (subs && !drawRaf) drawRaf = requestAnimationFrame(() => { drawRaf = 0; drawWords(false); });
}, { passive: true });

// relayout: the words moved, so redraw every line; otherwise only draw lines that came into range.
function drawWords(relayout = true) {
  if (relayout) wordsVersion++;
  const keep = new Set(), h = innerHeight, margin = h;
  const dpr = Math.min(2, devicePixelRatio || 1);
  for (const r of subs && timeline ? tlVideos : []) {
    if (!r.sec?.isConnected || !r.heights) continue;
    const b = r.sec.getBoundingClientRect();
    if (b.bottom < -margin || b.top > h + margin) continue;
    const todo = new Map(); // line -> context, for lines to draw now
    let y = b.top + TL_PAD;
    r.heights.forEach((lh, l) => {
      const tr = r.sec.children[l];
      if (tr && y + lh > -margin && y < h + margin) {
        keep.add(tr);
        let cv = lineCanvas.get(tr);
        if (!cv) {
          cv = canvasPool.pop() || Object.assign(document.createElement("canvas"), { className: "words" });
          cv.v = -1;
          lineCanvas.set(tr, cv);
        }
        if (cv.parentNode !== tr) tr.append(cv);
        cv.style.top = `${Math.round(((tr.h ?? lh) - SUB_H) / 2)}px`; // centred in a line grown for an opened frame
        if (cv.v !== wordsVersion && r.subs) {
          cv.v = wordsVersion;
          if (cv.width !== Math.round(r.W * dpr) || cv.height !== SUB_H * dpr) {
            Object.assign(cv, { width: Math.round(r.W * dpr), height: SUB_H * dpr });
            Object.assign(cv.style, { width: `${r.W}px`, height: `${SUB_H}px` });
          }
          const ctx = cv.getContext("2d");
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          ctx.clearRect(0, 0, r.W, SUB_H);
          todo.set(l, ctx);
        }
      }
      y += (tr?.h ?? lh) + TL_GAP;
    });
    if (todo.size && r.subs.words.length) drawLines(r, todo);
    else if (todo.has(0)) noSubtitles(r, todo.get(0));
  }
  for (const [tr, cv] of lineCanvas) {
    if (keep.has(tr)) continue;
    cv.remove();
    canvasPool.push(cv);
    lineCanvas.delete(tr);
  }
}

// A video without captions says so at the start of its first line, in the shortest wording that fits
// inside its timeblock (nothing when even that doesn't).
function noSubtitles(r, ctx) {
  const hole = r.holes.find(([a]) => a > r.X(0) - 0.01); // and stops before an opened image
  const room = Math.round(Math.min(r.W, r.X(r.dur), hole ? hole[0] : Infinity)) - r.X(0) - 12;
  ctx.font = `12px ${getComputedStyle(document.body).fontFamily}`;
  const text = ["No subtitles detected", "No subtitles", "None"].find((t) => ctx.measureText(t).width <= room);
  if (!text) return;
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();
  ctx.fillText(text, r.X(0) + 6, 26);
}

// Draw a video's words on the given lines (line -> 2d context).
function drawLines(r, todo) {
  const css = getComputedStyle(document.documentElement), family = getComputedStyle(document.body).fontFamily;
  const fg = css.getPropertyValue("--fg").trim(), muted = css.getPropertyValue("--muted").trim();
  const q = $("q").value.trim().split(/\s+/).filter((x) => x.length > 1).map((x) => x.toLowerCase());
  const hit = (word) => q.length > 0 && q.some((x) => word.toLowerCase().includes(x));
  const font = { orig: `12px ${family}`, place: `bold 12px ${family}`, en: `italic 11px ${family}`, enPlace: `italic bold 11px ${family}` };
  const any = todo.values().next().value;
  // where each line's strip ends: the full width, except the video's last line (as wide as its track)
  const total = r.X(r.dur), end = (l) => Math.round(Math.min(r.W, total - l * r.W));
  const width = (f, word) => {
    const key = f + "\u0000" + word;
    if (!widths.has(key)) { any.font = f; widths.set(key, any.measureText(word).width); }
    return widths.get(key);
  };
  const row = (words, kind) => {
    const laid = [];
    for (let k = 0; k < words.length; k++) {
      const [t, word, flag] = words[k];
      if (/^>+$/.test(word)) continue; // ">>" marks a new speaker in captions
      let x = r.X(t);
      const inside = r.holes.find(([a, b]) => x >= a - 0.5 && x < b); // said right at an opened frame's marker:
      if (inside) x = inside[1];                                       // it follows the image
      const l = Math.floor(x / r.W + 1e-6);
      // the priority pass needs every line of the video (a word can move onto the next line), so that a
      // line looks the same whichever lines are being drawn with it
      if (!todo.has(l) && !WORD_PRIORITY) continue;
      const hole = r.holes.find(([a]) => a > x - 0.01); // an opened image after it: the word stops before it
      const room = Math.min(k + 1 < words.length ? r.X(words[k + 1][0]) : r.X(r.dur) + WORD_GAP, hole ? hole[0] : Infinity) - x - WORD_GAP;
      const f = kind === "en" ? (flag === 1 ? font.enPlace : font.en) : flag === 1 ? font.place : font.orig, marked = hit(word);
      laid.push({ word, flag, l, lx: x - l * r.W, room, f, tw: (words[k].tw ??= width(f, word)), marked,
                  strong: flag === 1 || marked, land: flag === 3 });
    }
    // Priority (each row on its own): place names, words about the land and search matches claim room for their text first, in
    // time order, even over the words said just after them; one that would overlap the priority word before
    // it moves along to just after it (up to NUDGE_PX), so "лівому березі" reads as a phrase. One that
    // would run past the line's end ends there instead, or, if the words before it hold that spot, starts
    // the next line, like wrapped text (else it would blink to a dash at the zooms that put it at the edge).
    const claims = new Map(); // line -> [[from, to], ...] in order
    const claim = (w, l, at) => {
      const taken = claims.get(l) ?? [];
      taken.push([at, at + w.tw + WORD_GAP]);
      claims.set(l, taken);
      Object.assign(w, { at, dl: l });
    };
    if (WORD_PRIORITY) {
      for (const w of laid) {
        if (!w.strong && !w.land) continue;
        const last = claims.get(w.l)?.at(-1);
        let at = last && last[1] > w.lx ? last[1] : w.lx;
        if (at + w.tw > end(w.l)) at = end(w.l) - w.tw;
        const lh = r.holes.map(([a, b]) => [a - w.l * r.W, b - w.l * r.W]);
        if (lh.some(([a, b]) => at < b && at + w.tw > a)) continue; // it would run under an opened image
        if (at >= 0 && w.lx - at <= NUDGE_PX && at - w.lx <= NUDGE_PX && !(last && at < last[1] - 0.01)) { claim(w, w.l, at); continue; }
        const next = w.l + 1, start = claims.get(next)?.at(-1)?.[1] ?? 0;
        if (next < r.heights.length && r.W - w.lx + start <= NUDGE_PX && start + w.tw <= end(next)) claim(w, next, start);
      }
    }
    // Then every other word in the room left: text if it fits before the next word (or claim), else a dash.
    for (const w of laid) {
      const ctx = todo.get(w.at !== undefined ? w.dl : w.l);
      if (!ctx) continue; // a line not being drawn now
      const { f, tw, lx, marked, strong, land, flag } = w, W = end(w.l);
      // three levels, in both rows: place names (bold), words about the land (black), the rest of the
      // speech (faint; the English grey and italic); sounds such as "[музика]" / "[music]" are fainter still
      const noise = flag === 2 || /^\[.*\]$/.test(w.word);
      ctx.fillStyle = noise || (kind === "en" && !strong && !land) ? muted : fg;
      ctx.globalAlpha = noise ? 0.5 : strong ? 1 : land || kind === "en" ? SECOND : 0.4;
      const base = kind === "en" ? 34 : 18;
      const text = (px) => {
        if (marked) { ctx.save(); ctx.globalAlpha = 0.14; ctx.fillStyle = fg; ctx.fillRect(px - 2, base - 11, tw + 4, 15); ctx.restore(); }
        ctx.font = f;
        ctx.fillText(w.word, px, base);
      };
      if (w.at !== undefined) { text(w.at); continue; }
      const taken = claims.get(w.l) ?? [];
      if (taken.some(([a, b]) => lx >= a - 0.5 && lx < b)) continue; // said under a priority word: it steps aside
      const next = taken.find(([a]) => a > lx);
      if (next && next[0] - lx < 1) continue;
      const room = next ? Math.min(w.room, next[0] - lx - WORD_GAP) : w.room;
      if (tw <= room && lx + tw <= W) text(lx);
      else {
        // no room: a dash as long as the room it has (the word's share of the line)
        const thick = kind === "en" ? (strong ? 2 : land ? 1.5 : 1) : strong ? 3 : land ? 2 : 1.5;
        if (W - lx < 0.5) continue;
        ctx.fillRect(lx, base - 4 - thick / 2, Math.min(W - lx, Math.max(1, Math.min(tw, room, next ? next[0] - lx - 1 : Infinity))), thick);
      }
    }
  };
  row(r.subs.words, "orig");
  row(r.subs.en, "en");
  for (const ctx of todo.values()) ctx.globalAlpha = 1;
}

// ------------------------------------------------------------ left panel

// The original title, with the uploader's own English title below it when they set one (from the
// YouTube API `localizations`; never a machine translation).
function showTitle(it) {
  const v = videos.get(it.video_id), el = $("title"), en = $("title-en");
  if (!el) return;
  el.textContent = it.video_title;
  const t = v?.title_en?.source === "uploader" && v.title_en.text !== it.video_title ? v.title_en.text : "";
  en.textContent = t;
  en.hidden = !t;
}

// With nothing selected the panel shows the Video panel (also on load).
function intro() {
  if (!panelMode) openPanel("video");
}

// Pin frame i (or unpin with -1). Pinning also shows it in the panel.
function setPin(i) {
  for (const t of main.querySelectorAll(".tile.pinned")) t.classList.remove("pinned");
  pinned = items[i]?.frame_id ?? null;
  main.classList.toggle("has-pin", pinned !== null);
  spreadTo(pinned);
  zoomTo(timeline || documentView || mapView ? -1 : i);
  if (pinned === null) return;
  for (const t of main.querySelectorAll(`.tile[data-i="${i}"]`)) t.classList.add("pinned"); // a wrapped timeline frame has several pieces
  select(i);
}

// Gallery: a pinned frame opens out of its tile to fill the gallery side, whole (its own aspect, not the tile's
// crop), over the page background; unpinning shrinks it back into its tile (or fades it, if the tile has
// scrolled away). The arrow keys and the tally step through frames in place. Clicking it or the space around
// it unpins, like clicking a pinned tile.
const ZOOM_MS = 380, ZOOM_EASE = "cubic-bezier(.2, .9, .25, 1)";
const zoomBox = Object.assign(document.createElement("div"), { id: "zoom", hidden: true, innerHTML: `<div class="zimg"></div>` });
document.body.append(zoomBox);
let zoomed = null; // frame_id of the frame shown
zoomBox.addEventListener("click", () => unpin());
zoomBox.addEventListener("wheel", (e) => e.preventDefault(), { passive: false }); // the grid stays put underneath
addEventListener("resize", () => { const i = items.findIndex((it) => it.frame_id === zoomed); if (i >= 0) Object.assign(zoomBox.firstChild.style, px(fitRect(items[i]))); });
const px = (r) => ({ left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${r.height}px` });
// The gallery's room on screen: inside main's padding, below the panel on a narrow screen, above the controls.
function fitRect(it) {
  const m = main.getBoundingClientRect(), cs = getComputedStyle(main);
  const left = m.left + parseFloat(cs.paddingLeft), right = m.right - parseFloat(cs.paddingRight);
  const top = Math.max(parseFloat(cs.paddingTop), matchMedia("(max-width: 800px)").matches ? panel.getBoundingClientRect().bottom + 16 : 0);
  const bottom = $("controls").getBoundingClientRect().top + 20;
  const W = right - left, H = bottom - top, ar = it.width && it.height ? it.width / it.height : 16 / 9;
  const w = Math.min(W, H * ar), h = w / ar;
  return { left: left + (W - w) / 2, top: top + (H - h) / 2, width: w, height: h };
}
function tileRect(id) {
  const r = main.querySelector(`.tile[data-i="${items.findIndex((it) => it.frame_id === id)}"] img`)?.getBoundingClientRect();
  return r && r.bottom > 0 && r.top < innerHeight ? r : null;
}
function zoomTo(i) {
  const it = items[i], img = zoomBox.firstChild, opts = { duration: ZOOM_MS, easing: ZOOM_EASE, fill: "forwards" };
  if (!it) {
    if (zoomed === null) return;
    const from = img.getBoundingClientRect(), to = tileRect(zoomed);
    zoomed = null;
    if (reduced()) { zoomBox.hidden = true; return; }
    const fade = zoomBox.animate([{ opacity: 1 }, { opacity: 0 }], opts);
    if (to) img.animate([px(from), px(to)], opts);
    fade.finished.then(() => { if (zoomed === null) zoomBox.hidden = true; }, () => {});
    return;
  }
  if (zoomed === it.frame_id) return;
  img.style.setProperty("--img", `url("${it.thumb_url}")`);
  img.style.removeProperty("--sharp");
  img.dataset.want = it.web_url;
  if (it.web_url) {
    const full = new Image();
    full.src = it.web_url;
    full.decode().then(() => { if (img.dataset.want === it.web_url) img.style.setProperty("--sharp", `url("${it.web_url}")`); }, () => {});
  }
  const to = fitRect(it);
  if (zoomed === null) { // opening out of its tile (or catching an image still closing)
    const from = zoomBox.hidden ? tileRect(it.frame_id) : img.getBoundingClientRect();
    for (const a of [...zoomBox.getAnimations(), ...img.getAnimations()]) a.cancel();
    zoomBox.hidden = false;
    if (!reduced()) {
      zoomBox.animate([{ opacity: 0 }, { opacity: 1 }], opts);
      if (from) img.animate([px(from), px(to)], opts);
    }
  }
  Object.assign(img.style, px(to));
  zoomed = it.frame_id;
}

// Explicit navigation (tally scrub, arrow keys) moves the pin along when there is one.
function go(i) {
  if (!items[i]) return;
  if (pinned !== null) setPin(i);
  select(i, true);
}

function hover(tile) {
  if (pinned !== null) return;
  if (!panelMode) { if (tile) select(+tile.dataset.i); return; }
  if (!tile) return;
  // not while a folder is being renamed: the field would lose what was typed
  if (!peek && panel.querySelector(".folders input")) return;
  if (!peek) {
    const focus = panel.contains(document.activeElement) ? document.activeElement : null;
    peek = { nodes: [...panel.childNodes], focus };
    panel.dataset.video = "";
  }
  select(+tile.dataset.i);
}

// The pointer left the images: show the Video or Evidence panel again, as it was (typed text and focus kept).
function endPeek() {
  if (!peek) return;
  const { nodes, focus } = peek;
  peek = null;
  for (const t of main.querySelectorAll(".tile.on")) t.classList.remove("on");
  current = -1;
  panel.dataset.video = "";
  panel.replaceChildren(...nodes);
  focus?.focus({ preventScroll: true });
}

function select(i, scroll = false) {
  if (!items[i] || (panelMode && !peek)) return;
  if (i === current) {
    if (scroll) main.querySelector(`.tile[data-i="${i}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    return;
  }
  for (const t of main.querySelectorAll(".tile.on")) t.classList.remove("on");
  current = i;
  const tile = main.querySelector(`.tile[data-i="${i}"]`);
  for (const t of main.querySelectorAll(`.tile[data-i="${i}"]`)) t.classList.add("on");
  if (scroll && tile) {
    hoverPaused = true;
    tile.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
  showFrame(items[i]);
}

function showFrame(it) {
  const v = videos.get(it.video_id);
  const times = v?.frame_times ?? [];
  if (panel.dataset.video !== it.video_id) {
    // New video: rebuild the header and tally. Within a video only the playhead moves, so it glides.
    const dur = it.duration_s || v?.duration_s || Math.max(it.timestamp_s, ...times.map((ft) => ft[1])) || 1;
    panel.dataset.video = it.video_id;
    panel.dur = dur;
    panel.innerHTML = `
      <div class="head"><div>
        <div class="title" id="title"></div>
        <div class="sub" id="title-en" lang="en" hidden></div>
        <div class="sub">${esc(it.channel_title ?? "YouTube")}, ${it.published_at.slice(0, 4)}</div>
      </div></div>
      <div class="tally" title="Where each extracted frame sits in the video">
        <div class="now"><span id="now"></span></div>
        <div class="track" id="track">${times.map(([id, t]) => `<i data-id="${esc(id)}" style="--x:${Math.min(1, t / dur)}"></i>`).join("")}<b class="playhead" id="playhead"></b></div>
        <div class="ends"><span>0:00</span><span>${clock(dur)}</span></div>
      </div>
      <p class="small" id="frameline"></p>
      <div class="details" id="details"></div>`;
  }
  showTitle(it);
  const x = Math.min(1, it.timestamp_s / panel.dur);
  $("now").style.setProperty("--x", x);
  $("now").textContent = clock(it.timestamp_s);
  $("playhead").style.setProperty("--x", x);
  $("track").querySelector("i.here")?.classList.remove("here");
  $("track").querySelector(`i[data-id="${CSS.escape(it.frame_id)}"]`)?.classList.add("here");
  const pos = v?.order.get(it.frame_id);
  $("frameline").innerHTML =
    `Frame ${pos ?? "?"} of ${times.length || "?"} · ${clock(it.timestamp_s)} · ${it.width}×${it.height} · ${it.selection.replace("_", " ")}<br>` +
    `<span class="muted">Published on YouTube ${it.published_at.slice(0, 10)}, not the capture date</span>` +
    (it.sort_note ? `<br><span class="sortnote">${esc(it.sort_note)}</span>` : "") +
    (subs ? `<br><span class="muted" id="subsline"></span>` : "");
  if (subs) loadSubtitles(it.video_id).then((d) => { if ($("subsline")) $("subsline").textContent = `Transcript: ${subtitleNote(d)}`; }, () => {});
  showDetails(it);
}

async function showDetails(it) {
  const box = $("details");
  box.classList.add("loading");
  let f;
  try { f = await detail(it.frame_id); } catch { return; }
  if (items[current]?.frame_id !== it.frame_id) return; // moved on while loading
  const cats = f.derived.categories.map((c) => `${esc(c.label)} ${pct(c.confidence)}`).join(", ") || "—";
  // Each candidate says where it came from; frame-level clues quote their evidence.
  const locs = f.inferred.locations.slice(0, 8).map((l) => {
    const m = l.provenance.method, frameLevel = FRAME_CLUES.has(m);
    return `${esc(l.place_name ?? "?")}${l.latitude != null ? ` (${l.latitude}, ${l.longitude})` : ""} · ${pct(l.confidence)} · ` +
      `<span class="src" title="${esc(l.provenance.evidence)}">${SOURCE[m] ?? esc(m)}</span>` +
      (frameLevel ? `<span class="note">${esc(l.provenance.evidence.slice(0, 150))}</span>` : "");
  }).join("<br>") || "Unknown";
  const dates = f.inferred.capture_date.map((d) => {
    const when = d.value ?? (d.earliest ? `${d.earliest} – ${d.latest}` : `on or before ${d.latest}`);
    const m = d.provenance.method;
    return `${when} · ${pct(d.confidence)} · <span class="src" title="${esc(d.provenance.evidence)}">${SOURCE[m] ?? esc(m)}</span>`;
  }).join("<br>");
  box.innerHTML = `
    <dl class="fields">
      <dt>Categories</dt><dd>${cats}<span class="note">derived by an image model</span></dd>
      <dt>Location</dt><dd>${locs}<span class="note">inferred candidates; a place named in the video is not necessarily where this frame was shot</span></dd>
      <dt>Captured</dt><dd>${dates}<span class="note">inferred; publication is only the upper bound, and footage may predate 2022</span></dd>
      ${visualFields(f.derived.features)}
    </dl>
    <p class="small"><a href="${f.source.timestamped_url}" target="_blank" rel="noopener">Watch at ${clock(f.frame.timestamp_s)} ↗</a> &nbsp;
      ${f.urls.original ? `<a href="${f.urls.original}" target="_blank">Original</a> &nbsp;` : ""}
      <a href="/api/frames/${encodeURIComponent(f.frame_id)}" target="_blank">JSON</a></p>
    <p class="small muted">${esc(f.frame_id)}</p>`;
  box.classList.remove("loading");
}

const SOURCE = {
  frame_onscreen_text: "on screen", description_chapter: "chapter", speech_captions: "speech",
  source_text_gazetteer: "video text", youtube_recording_details_geotag: "uploader geotag",
  youtube_recording_details_text: "uploader location", discovery_query_context: "search query", scope_check: "country check",
  publication_upper_bound: "upload date", youtube_recording_details_date: "uploader date", source_text_year_mention: "year in text",
  source_text_archival_keyword: "archive hint", frame_onscreen_year: "on screen", frame_onscreen_date: "on screen",
};
const FRAME_CLUES = new Set(["frame_onscreen_text", "description_chapter", "speech_captions"]);

const VIEW_NAMES = { top_down: "top-down", oblique_aerial: "oblique aerial", elevated: "elevated",
                     street_level: "ground level", close_up: "close-up" };
function visualFields(x) {
  if (!x) return "";
  const angle = x.viewpoint ? `${VIEW_NAMES[x.viewpoint] ?? x.viewpoint} ${pct(x.viewpoint_scores[x.viewpoint])}` : "—";
  const damage = x.damage == null ? "few or no buildings" : `${Math.round(x.damage * 100)} / 100`;
  return `
      <dt>Camera</dt><dd>${angle}</dd>
      <dt>Damage</dt><dd>${damage}</dd>
      <dt>Colour</dt><dd><span class="swatch" style="background:${esc(x.color_hex)}"></span>${esc(x.color_hex)} · light ${pct(x.lightness)}</dd>
      <dt>Season</dt><dd>vegetation ${pct(x.greenness)} · snow ${pct(x.snow)}<span class="note">derived from pixels; cues, not measurements</span></dd>`;
}

// Scrub the tally: pick the nearest frame of this video that's in the current grid.
function scrub(e) {
  const track = $("track");
  if (!track || !(e.buttons || e.pointerType === "mouse")) return;
  const r = track.getBoundingClientRect();
  const t = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)) * panel.dur;
  let best = -1, dist = Infinity;
  items.forEach((it, i) => {
    if (it.video_id !== panel.dataset.video) return;
    const d = Math.abs(it.timestamp_s - t);
    if (d < dist) { dist = d; best = i; }
  });
  if (best >= 0) go(best);
}

// ---------------------------------------------------------------- input

// Hovering a tile shows it in the panel, unless a frame is pinned.
main.addEventListener("pointerover", (e) => {
  if (!hoverPaused) hover(e.target.closest(".tile"));
});
window.addEventListener("pointermove", (e) => {
  const xy = `${e.clientX},${e.clientY}`;
  if (xy !== pointerXY && !e.target.closest?.("#track")) hoverPaused = false; // browsers resend the old position after scrolling
  pointerXY = xy;
  if (!e.target.closest?.("#main")) endPeek();
  else if (!hoverPaused) hover(e.target.closest?.(".tile"));
}, { passive: true });
document.documentElement.addEventListener("pointerleave", endPeek);
// Click a tile to pin it; click it again (or empty space, or Esc) to unpin and resume hover.
main.addEventListener("click", (e) => {
  const tile = e.target.closest(".tile");
  if (!tile) return pinned !== null && unpin(null);
  const i = +tile.dataset.i;
  // a frame clicked while a panel is open: show it (and after Sort & filter, come back to it when let go)
  if (panelMode) { backTo = panelMode === "filters" ? "filters" : null; closePanel(); current = -1; }
  // in the timeline, a video's frames wait while one of its images is closing (it would push them along)
  if (timeline && items[i].frame_id !== pinned && closingIn(items[i].video_id)) return;
  items[i].frame_id === pinned ? unpin(tile) : setPin(i);
});
let backTo = null;
function unpin() {
  setPin(-1);
  current = -1;
  openPanel(backTo ?? "video"); // nothing selected: back to the Video panel (or to Sort & filter, if it was open)
  backTo = null;
}
panel.addEventListener("pointermove", (e) => { if (e.target.closest("#track")) scrub(e); });
panel.addEventListener("pointerdown", (e) => {
  if (!e.target.closest("#track")) return;
  e.target.closest("#track").setPointerCapture(e.pointerId);
  scrub(e);
});


// The live count, at the top of the Evidence and Sort & filter panels: how much the folder holds ("20 uploaded ·
// 1019 images"), or what the search and filters leave of it ("120 of 1019 images · 10 of 20 videos"). Polls so it
// keeps up while a job is adding videos.
let library = { videos: 0, frames: 0 };
function showStats(list = items) {
  const vids = new Set(list.map((it) => it.video_id)).size;
  const filtered = list.length !== library.frames;
  const near = $("sort").value.startsWith("near:") && !timeline ? $("sort").value.slice(5) : null;
  if (near) {
    // how many images the site places at or near the chosen place (it may be none)
    const here = list.filter((it) => it.sort_group === "at" || it.sort_group === "near");
    statsEl.textContent = here.length ? `${here.length} image${here.length === 1 ? "" : "s"} near ${near}` : `None near ${near}`;
    return;
  }
  statsEl.textContent = filtered ? `${list.length} of ${library.frames} images · ${vids} of ${library.videos} videos`
                                 : `${library.videos} uploaded · ${library.frames} images`;
}
async function pollStats() {
  try {
    const s = await (await fetch("/api/stats")).json();
    const grew = s.frames !== library.frames || s.videos !== library.videos;
    library = s;
    if (grew) showStats();
  } catch {}
}
setInterval(pollStats, 10000);

// The study areas' places (discovery.focus in config/) as "Near ..." sorts.
fetch("/api/study-places").then((r) => r.json()).then((list) => {
  const group = $("near");
  for (const p of list) group.append(new Option(`Near ${p.name}`, p.sort));
  group.hidden = !list.length;
  showFilters(); // (when open)
}, () => {});

let t;
$("q").oninput = () => { clearTimeout(t); t = setTimeout(load, 250); };

// Sort & filter: the button beside Evidence opens it in the left panel (held like Evidence: hovering frames
// shows them, and closing it goes back to Video), over the gallery, where sorting works: it switches the view
// to the Gallery. Search, every sort with what it does, categories (a frame must have every one chosen) and
// the year published, each applied at once so the grid changes beside it. The button says how many are set
// ("Sort & filter · 2").
const SORTS = [
  ["", "Video & time", "Each video's frames in the order they were filmed"],
  ["place", "Place", "Grouped by the most likely place named for each frame; inferred, not verified. Unknown last"],
  ["similar", "Similar view", "Frames that look alike side by side, so one site filmed in different videos meets"],
  ["angle", "Camera angle", "From top-down to ground level, as an image model sees it"],
  ["damage", "Damage", "Most visible damage first; frames with few buildings last"],
  ["scale", "Scale", "Close-up first, wide aerial last"],
  ["color", "Colour", "Around the colour wheel by mean colour; greys last"],
  ["light", "Light", "Darkest first: a cue for time of day and weather"],
  ["season", "Season cues", "Snow, bare, some green, green: cues, not a date"],
  ["published", "Published", "Newest YouTube upload first (not the capture date)"],
  ["detail", "Detail", "Sharpest first: more measurable detail"],
];
function syncFilters() {
  const n = ($("sort").value || queryImage ? 1 : 0) + cats.size + ($("year").value ? 1 : 0);
  $("filters").lastChild.textContent = n ? `Sort & filter · ${n}` : "Sort & filter";
  $("filters").classList.toggle("set", n > 0);
  syncFilterPanel(n);
}
function showFilters() {
  if (panelMode !== "filters" || peek) return;
  const opt = ([v, name, note]) =>
    `<button type="button" data-sort="${esc(v)}"><span class="nm">${esc(name)}</span><span class="note">${esc(note)}</span></button>`;
  const near = [...$("near").children].map((o) => `<button type="button" data-sort="${esc(o.value)}">${esc(o.text.replace(/^Near /, ""))}</button>`);
  const chips = (key, counts) => Object.entries(counts).map(([k, n]) =>
    `<button type="button" data-${key}="${esc(k)}">${esc(k)} <span class="n">${n}</span></button>`).join("");
  panel.innerHTML = `
    <div class="sf">
      <input type="search" class="sf-q" placeholder="Search words, places or what is in view" aria-label="Search" autocomplete="off" spellcheck="false">
      <h3>Sort</h3>
      <div class="sf-sorts">${(queryImage ? [[IMAGE_SORT, "Like your image", "Most like the image you dropped or pasted first"]] : []).concat(SORTS).map(opt).join("")}</div>
      ${near.length ? `<h4>Near a study-area place</h4>
        <p class="note">Frames placed at it (within 3 km) first, then near it, then the rest; from inferred places, never a verified location</p>
        <div class="sf-chips">${near.join("")}</div>` : ""}
      <h3>Category <span class="note">a frame must have every one chosen</span></h3>
      <div class="sf-chips">${chips("cat", facets.category)}</div>
      <h3>Published on YouTube</h3>
      <div class="sf-chips"><button type="button" data-year="">All</button>${chips("year", facets.year)}</div>
      <button type="button" class="sf-clear">Clear all</button>
    </div>`;
  panel.prepend(statsEl); // the live count, at the top
  panel.querySelector(".sf-q").addEventListener("input", (e) => {
    $("q").value = e.target.value;
    $("q").dispatchEvent(new Event("input")); // the search, as if typed at the bottom
  });
  syncFilters();
}
// which choices are on (the panel isn't redrawn, so typing in its search keeps the focus)
function syncFilterPanel(n) {
  const box = panelMode === "filters" && panel.querySelector(".sf");
  if (!box) return;
  for (const b of box.querySelectorAll("[data-sort]")) b.classList.toggle("on", b.dataset.sort === $("sort").value);
  for (const b of box.querySelectorAll("[data-cat]")) b.classList.toggle("on", cats.has(b.dataset.cat));
  for (const b of box.querySelectorAll("[data-year]")) b.classList.toggle("on", b.dataset.year === $("year").value);
  box.querySelector(".sf-clear").classList.toggle("on", !!(n || $("q").value));
  const q = box.querySelector(".sf-q");
  if (document.activeElement !== q) q.value = $("q").value;
}
panel.addEventListener("click", (e) => {
  const b = e.target.closest?.(".sf button");
  if (!b) return;
  if (b.classList.contains("sf-clear")) return clearAll();
  if ("sort" in b.dataset) {
    if (queryImage && b.dataset.sort !== IMAGE_SORT) setQueryImage(null);
    $("sort").value = b.dataset.sort;
  } else if ("cat" in b.dataset) cats.has(b.dataset.cat) ? cats.delete(b.dataset.cat) : cats.add(b.dataset.cat);
  else if ("year" in b.dataset) $("year").value = b.dataset.year === $("year").value ? "" : b.dataset.year;
  syncFilters();
  load();
});
$("filters").onclick = () => {
  if (panelMode === "filters") return leavePanel();
  if (currentView() !== "grid") setView("grid"); // sorting works in the gallery
  openPanel("filters");
};
// Search by image: drop or paste an image anywhere; the grid is ordered by visual similarity to it, shown
// as the sort "Like your image" (pick another sort, or Clear all, to stop). The image is only held in
// memory by the local server, never added to the library.
const IMAGE_SORT = "__image";
let queryImage = null; // { id }
async function useImage(file) {
  if (documentView || mapView) return;
  if (!file || !file.type.startsWith("image/")) return;
  // the image becomes a sort: show it in Sort & filter, over the gallery
  if (currentView() !== "grid") setView("grid");
  if (panelMode !== "filters") openPanel("filters");
  statsEl.textContent = "Reading image…";
  try {
    const r = await fetch("/api/query-image", { method: "POST", body: file, headers: { "Content-Type": file.type } });
    if (!r.ok) throw new Error((await r.json()).detail ?? r.status);
    setQueryImage({ id: (await r.json()).id });
    load();
  } catch (err) {
    statsEl.textContent = `Couldn't use that image: ${err.message}`;
  }
}
function setQueryImage(q) {
  queryImage = q;
  $("sort").querySelector(`option[value="${IMAGE_SORT}"]`)?.remove();
  if (q) {
    $("sort").add(new Option("Sort: Like your image", IMAGE_SORT), 1);
    $("sort").value = IMAGE_SORT;
  } else if ($("sort").value === IMAGE_SORT || !$("sort").value) $("sort").value = "";
  $("sort").classList.toggle("set", !!$("sort").value);
  syncFilters();
  showFilters(); // (when open) "Like your image" joins or leaves the sorts
}
window.addEventListener("dragover", (e) => { if ([...e.dataTransfer.items].some((i) => i.type.startsWith("image/"))) e.preventDefault(); });
window.addEventListener("drop", (e) => {
  const file = [...e.dataTransfer.files].find((f) => f.type.startsWith("image/"));
  if (file) { e.preventDefault(); useImage(file); }
});
window.addEventListener("paste", (e) => {
  const file = [...(e.clipboardData?.files ?? [])].find((f) => f.type.startsWith("image/"));
  if (file && !e.target.matches?.("input, textarea")) { e.preventDefault(); useImage(file); }
});
$("q").addEventListener("input", syncFilters);
// Clear all: sort, filters, search and the image
function clearAll() {
  $("q").value = $("sort").value = $("year").value = "";
  cats.clear();
  setQueryImage(null);
  load();
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && panelMode && e.target.matches?.("input, textarea, select")) { e.target.blur(); return; }
  if (e.key === "Escape" && panelMode) { leavePanel(); return; }
  if (documentView || mapView || e.target.matches?.("select, input, button, textarea")) return;
  if (e.key === "/") { // search: in Sort & filter, over the gallery
    e.preventDefault();
    if (currentView() !== "grid") setView("grid");
    if (panelMode !== "filters") openPanel("filters");
    panel.querySelector(".sf-q")?.focus();
  }
  if (e.key === "Escape" && pinned !== null) unpin(null);
  if (e.key === "ArrowRight") { e.preventDefault(); go(Math.min(items.length - 1, current + 1)); }
  if (e.key === "ArrowLeft") { e.preventDefault(); go(Math.max(0, current - 1)); }
});

// Grid density: pinch or +/- (see zoom.js).
// In the timeline view a pinch stretches time instead, re-wrapping the timelines as it goes.
const zoom = setupZoom({
  root: main,
  enabled: () => !documentView && !mapView,
  axis: () => (timeline ? "x" : "both"),
  stretch: {
    clamp: (s) => clampScale(tlScale * s) / tlScale,
    preview: (s) => { holdImages("pinch", 3000); tlLive = s; layoutTimeline(); },
    commit: (s) => {
      tlScale = clampScale(tlScale * s);
      tlLive = 1;
      try { localStorage.setItem(zoomKey(), tlScale); } catch {}
      layoutTimeline();
      if (holdBy === "pinch") releaseImages(); // the fingers lifted
    },
  },
  onChange: (i, cols) => {
    document.documentElement.toggleAttribute("data-dense", cols >= 8);
    gridLevel = i;
    syncSlider();
  },
});

// ------------------------------------------------------------ Video and Evidence: the two panel buttons

// Two buttons at the bottom left turn the panel into something other than a frame. Each deselects any frame
// and keeps the panel until it is clicked again, Esc, or a frame is clicked.
// - Video: a form. Links to add, a description to search YouTube for (an LLM turns it into searches when
//   it has a token), the tokens, the search's place and years, and Save to: an evidence folder, new by
//   default ("Evidence folder <n>", named in the form). Jobs run on the local server (jobs.py); the tokens
//   are sent with each job and kept only in this browser (this tab, unless "Remember" is ticked).
// - Evidence: the evidence folders, each its own library on disk: open one in the grid, show it in the
//   file browser, rename it. The site shows one folder at a time (the `lib` cookie).
// A folder keeps one place and range of years, set by the job that made it (the scope rules, jobs.py).
let videoForm = null, jobTimer = null, folders = [], nextFolder = { title: "Evidence folder 1" };
// Published: whole years, from YouTube's first (2005) to this one; the default is the main library's 2022–2026.
const DEFAULT_START = 2022, DEFAULT_END = 2026, LAST_YEAR = Math.max(DEFAULT_END, new Date().getFullYear());
const yearOptions = (sel) => Array.from({ length: LAST_YEAR - 2004 }, (_, k) => 2005 + k)
  .map((y) => `<option${y === sel ? " selected" : ""}>${y}</option>`).join("");
const store = (remember) => { try { return remember ? localStorage : sessionStorage; } catch { return null; } };
const readToken = (k) => { try { return sessionStorage.getItem(k) ?? localStorage.getItem(k) ?? ""; } catch { return ""; } };
const isMac = /Mac/.test(navigator.platform);
const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
  .then(async (r) => { const d = await r.json(); if (!r.ok) throw new Error(d.detail ?? r.status); return d; });

async function loadFolders() {
  try {
    const d = await (await fetch("/api/folders")).json();
    folders = d.folders;
    nextFolder = d.next;
    const cur = folders.find((f) => f.current) ?? folders[0];
    currentLib = cur.slug;
    // remember the folder the server opened, so a job filling another folder later doesn't switch the page
    if (!/(^|; )lib=/.test(document.cookie)) setLibCookie(cur.slug);
    document.title = `${cur.title} · Image Evidence`;
  } catch {}
  return folders;
}

function openPanel(mode) {
  peek = null;
  if (pinned !== null) setPin(-1);
  for (const t of main.querySelectorAll(".tile.on")) t.classList.remove("on");
  current = -1;
  panelMode = mode;
  for (const id of ["video", "evidence"]) $(id).classList.toggle("set", id === mode);
  for (const id of ["video", "evidence", "filters"]) $(id).setAttribute("aria-expanded", id === mode);
  panel.dataset.video = "";
  if (mode === "video") {
    panel.replaceChildren(videoForm ??= buildVideoForm());
    refreshVideoForm();
  } else if (mode === "filters") showFilters();
  else showEvidence();
}
// Closing Evidence goes back to Video; closing Video (its button, Esc) leaves the panel empty, so hovering a
// frame shows it, until a frame is pinned and let go again. A frame clicked meanwhile just closes it (to the frame).
function closePanel() {
  peek = null;
  panelMode = null;
  for (const id of ["video", "evidence"]) $(id).classList.remove("set");
  for (const id of ["video", "evidence", "filters"]) $(id).setAttribute("aria-expanded", "false");
  panel.dataset.video = "";
  panel.replaceChildren();
}
const leavePanel = () => (panelMode === "evidence" || panelMode === "filters" ? openPanel("video") : closePanel());
for (const id of ["video", "evidence"]) $(id).onclick = () => (panelMode === id ? leavePanel() : openPanel(id));
const setLibCookie = (slug) => { document.cookie = `lib=${encodeURIComponent(slug)}; path=/; max-age=31536000; samesite=strict`; };
function switchLibrary(slug) {
  setLibCookie(slug);
  location.reload();
}

// ---- Evidence: the folders

async function showEvidence() {
  if (panelMode !== "evidence" || peek) return;
  await loadFolders();
  if (panelMode !== "evidence" || peek) return;
  const reveal = isMac ? "Show in Finder" : "Open folder";
  panel.innerHTML = `
    <ul class="folders">${folders.map((f) => `
      <li class="${f.current ? "on" : ""}" data-slug="${esc(f.slug)}">
        <button type="button" class="name" data-act="open" title="${f.current ? "Shown now" : "Show this folder"}">${esc(f.title)}</button>
        <span class="count">${f.videos} video${f.videos === 1 ? "" : "s"} · ${f.frames} image${f.frames === 1 ? "" : "s"}</span>
        <span class="meta">${esc(f.scope)}</span>
        <span class="path">${esc(f.path)}</span>
        <span class="acts"><button type="button" data-act="reveal">${reveal}</button><button type="button" data-act="rename">Rename</button></span>
      </li>`).join("")}
    </ul>`;
  panel.prepend(statsEl); // the live count, at the top
}
// live: the counts follow jobs while the list is open (not while a name is being edited)
setInterval(() => { if (panelMode === "evidence" && !panel.querySelector(".folders input")) showEvidence(); }, 10000);
panel.addEventListener("click", async (e) => {
  const b = e.target.closest?.(".folders button");
  if (!b) return;
  const li = b.closest("li"), slug = li.dataset.slug;
  if (b.dataset.act === "open") return li.classList.contains("on") ? leavePanel() : switchLibrary(slug);
  if (b.dataset.act === "reveal") return post("/api/folders/reveal", { slug }).catch(() => {});
  if (b.dataset.act === "rename") {
    // the name becomes a field: Enter saves, Esc or leaving it puts the old name back
    const name = li.querySelector(".name"), old = name.textContent;
    const input = Object.assign(document.createElement("input"), { value: old, className: "name", spellcheck: false });
    input.setAttribute("aria-label", "Folder name");
    name.replaceWith(input);
    input.select();
    let done = false;
    const finish = async (save) => {
      if (done) return;
      done = true;
      const title = input.value.trim();
      if (save && title && title !== old) {
        try { await post("/api/folders/rename", { slug, title }); } catch {}
        if (slug === currentLib) document.title = `${title} · Image Evidence`;
      }
      showEvidence();
    };
    input.addEventListener("keydown", (k) => {
      if (k.key === "Enter") { k.preventDefault(); finish(true); }
      if (k.key === "Escape") { k.preventDefault(); k.stopPropagation(); finish(false); }
    });
    input.addEventListener("blur", () => finish(true));
  }
});

// ---- Video: the form

// The Search field's placeholder cycles through these while it is empty.
const SEARCH_EXAMPLES = [
  "drone footage of the Kakhovka reservoir",
  "the Dnipro riverbank near Nikopol",
  "aerial views of Kharkiv after shelling",
  "bridges over the Irpin river",
  "the Carpathian mountains from above",
  "flooded villages in Kherson Oblast",
  "the Enerhodar shoreline across the river",
  "sunflower fields in the southern steppe",
  "the Odesa coastline and port",
  "Kyiv's left bank at dusk",
];
// Drawn over the field rather than as its placeholder, so it can glide: the old example lifts and fades, the next
// rises into its place. One line like the other fields (cut with an ellipsis); the field grows as you type.
const EXAMPLE_MS = 6000;
function cycleExamples(el, ex) {  // the form is built once and kept, so one timer serves it
  let i = 0;
  const fit = () => {  // empty, it is one line like the fields below it
    el.style.height = "";
    if (el.value) el.style.height = el.scrollHeight + "px";
    ex.hidden = !!el.value;
  };
  el.addEventListener("input", fit);
  el.setAttribute("aria-label", "Search, for example: " + SEARCH_EXAMPLES[0]);
  setInterval(() => {
    if (el.value || !el.isConnected) return;
    ex.classList.add("out");
    setTimeout(() => {
      ex.textContent = SEARCH_EXAMPLES[(i = (i + 1) % SEARCH_EXAMPLES.length)];
      ex.classList.replace("out", "in");
      void ex.offsetWidth;  // start the rise from below
      ex.classList.remove("in");
    }, 450);
  }, EXAMPLE_MS);
}

function buildVideoForm() {
  const f = document.createElement("form");
  f.className = "addvideo";
  f.noValidate = true;
  f.innerHTML = `
    <div class="head">
      <input id="v-url" class="title" type="text" placeholder="Paste a YouTube link, links" aria-label="YouTube links" autocomplete="off" spellcheck="false">
    </div>
    <dl class="settings">
      <dt><label for="v-prompt">Search</label></dt><dd class="prompt"><textarea id="v-prompt" rows="1"></textarea><span class="example" aria-hidden="true">${SEARCH_EXAMPLES[0]}</span></dd>
      <dt><label for="v-yt">YouTube key</label></dt><dd><input id="v-yt" type="password" placeholder="required" autocomplete="off" spellcheck="false"></dd>
      <dt><label for="v-llm">Anthropic key</label></dt><dd><input id="v-llm" type="password" placeholder="optional" autocomplete="off" spellcheck="false"></dd>
      <dt></dt><dd><label class="check"><input id="v-remember" type="checkbox"> Remember keys on this browser</label></dd>
      <dt><label for="v-country">Place</label></dt><dd><input id="v-country" value="Ukraine" autocomplete="off"></dd>
      <dt><label for="v-places">Near</label></dt><dd><input id="v-places" placeholder="towns or regions" autocomplete="off"></dd>
      <dt>Published</dt><dd class="range"><select id="v-start" aria-label="Published from">${yearOptions(DEFAULT_START)}</select><span>–</span><select id="v-end" aria-label="Published until">${yearOptions(DEFAULT_END)}</select></dd>
      <dt><label for="v-max">Max videos</label></dt><dd><input id="v-max" type="number" min="1" max="25" value="5"></dd>
      <dt><label for="v-licence">Licence</label></dt><dd><select id="v-licence">
        <option value="creativeCommon">Creative Commons only</option>
        <option value="any">Any public video</option></select></dd>
      <dt class="saveto"><label for="v-folder">Save to</label></dt><dd class="saveto"><select id="v-folder"></select></dd>
      <dt></dt><dd id="v-name-row"><input id="v-folder-name" aria-label="New folder's name" autocomplete="off" spellcheck="false"></dd>
    </dl>
    <p class="small" id="v-scope"></p>
    <p><button id="v-start-job" type="submit">Start</button></p>
    <div id="v-job" class="small" aria-live="polite"></div>`;
  const q = (id) => f.querySelector("#" + id);
  cycleExamples(q("v-prompt"), f.querySelector(".prompt .example"));
  q("v-yt").value = readToken("ytKey");
  q("v-llm").value = readToken("llmKey");
  try { q("v-remember").checked = !!localStorage.getItem("ytKey") || !!localStorage.getItem("llmKey"); } catch {}
  const saveTokens = () => {
    const keep = q("v-remember").checked;
    for (const [k, id] of [["ytKey", "v-yt"], ["llmKey", "v-llm"]]) {
      try { localStorage.removeItem(k); sessionStorage.removeItem(k); } catch {}
      const v = q(id).value.trim();
      if (v) try { store(keep)?.setItem(k, v); } catch {}
    }
  };
  for (const id of ["v-yt", "v-llm", "v-remember"]) q(id).addEventListener("change", saveTokens);
  for (const id of ["v-country", "v-folder-name"]) q(id).addEventListener("input", showSaveTo);
  for (const id of ["v-start", "v-end"]) q(id).addEventListener("change", showSaveTo);
  // an existing folder keeps one place and range of years: choosing it fills them in
  q("v-folder").addEventListener("change", () => {
    const fo = folders.find((x) => x.slug === $("v-folder").value);
    if (fo) { $("v-country").value = fo.place; $("v-start").value = fo.start; $("v-end").value = fo.end; }
    showSaveTo();
  });
  f.addEventListener("submit", (e) => { e.preventDefault(); startJob(); });
  return f;
}

// the two years in order (picking a later "from" than "until" just swaps them)
function years() {
  const a = +$("v-start").value, b = +$("v-end").value;
  return [Math.min(a, b), Math.max(a, b)];
}
const sameName = (a, b) => {
  const u = ["ukraine", "україна", "украина", "ukrajina"], x = a.trim().toLowerCase(), y = b.trim().toLowerCase();
  return x === y || (u.includes(x) && u.includes(y));
};

function fillFolders(pick) {
  const sel = $("v-folder"), keep = pick ?? (sel.options.length ? sel.value : "new"); // new by default ("" is the main library)
  sel.innerHTML = `<option value="new">New folder</option>` +
    folders.map((f) => `<option value="${esc(f.slug)}">${esc(f.title)}</option>`).join("");
  sel.value = [...sel.options].some((o) => o.value === keep) ? keep : "new";
  if (!$("v-folder-name").dataset.typed) $("v-folder-name").value = nextFolder.title;
}
// Save to: what the chosen folder keeps, and whether this search fits it (the server checks it too).
function showSaveTo() {
  const name = $("v-folder-name");
  if (document.activeElement === name) name.dataset.typed = name.value && name.value !== nextFolder.title ? "1" : "";
  const fo = folders.find((x) => x.slug === $("v-folder").value);
  const place = $("v-country").value.trim() || "Ukraine", [a, b] = years();
  $("v-name-row").hidden = !!fo;
  $("v-name-row").previousElementSibling.hidden = !!fo;
  const note = $("v-scope");
  note.classList.remove("warn");
  if (!fo) {
    note.textContent = "";
  } else if (!sameName(place, fo.place) || a < fo.start || b > fo.end) {
    note.classList.add("warn");
    note.textContent = `“${fo.title}” keeps only ${fo.scope}. Save this to a new folder instead.`;
  } else {
    note.textContent = `Adds to “${fo.title}”: ${fo.scope}, ${fo.videos} video${fo.videos === 1 ? "" : "s"} so far.`;
  }
}

let setup = null;
async function refreshVideoForm() {
  setup ??= await fetch("/api/ingest/setup").then((r) => r.json()).catch(() => ({}));
  await loadFolders();
  fillFolders();
  showSaveTo();
  if (!jobTimer) {
    const last = (await fetch("/api/jobs").then((r) => r.json()).catch(() => [])).at(-1);
    if (last) showJob(last);
    if (last && (last.status === "running" || last.status === "queued")) watchJob(last.id);
  }
}
document.addEventListener("click", (e) => {
  const a = e.target.closest?.("a[data-lib]");
  if (!a) return;
  e.preventDefault();
  switchLibrary(a.dataset.lib);
});

async function startJob() {
  const yt = $("v-yt").value.trim(), llm = $("v-llm").value.trim(), [a, b] = years();
  const body = {
    urls: $("v-url").value, prompt: $("v-prompt").value, country: $("v-country").value, places: $("v-places").value,
    start: `${a}-01-01`, end: `${b}-12-31`, max_videos: +$("v-max").value || 5, licence: $("v-licence").value,
    folder: $("v-folder").value, folder_name: $("v-folder-name").value, youtube_key: yt, llm_key: llm,
  };
  if (!body.urls.trim() && !body.prompt.trim() && !body.places.trim()) {
    $("v-job").textContent = "Paste a link, or describe what to search for.";
    return $("v-url").focus();
  }
  if (!yt) {
    $("v-job").textContent = "Paste your YouTube Data API key first.";
    return $("v-yt").focus();
  }
  $("v-start-job").disabled = true;
  try {
    const job = await post("/api/jobs", body);
    // the next search goes into the same folder unless another is chosen
    $("v-folder-name").dataset.typed = "";
    await loadFolders();
    fillFolders(job.library);
    showSaveTo();
    showJob(job);
    watchJob(job.id);
  } catch (err) {
    $("v-job").textContent = `Couldn't start: ${err.message}`;
  } finally {
    $("v-start-job").disabled = false;
  }
}

function watchJob(id) {
  clearInterval(jobTimer);
  let seen = 0;
  jobTimer = setInterval(async () => {
    let job;
    try { job = await (await fetch(`/api/jobs/${id}`)).json(); } catch { return; }
    showJob(job);
    const added = job.results.filter((r) => r.status === "processed").length;
    if ((added > seen || job.status === "done") && job.library === currentLib) { seen = added; await loadVideos(); load(); }
    if (job.status === "done" || job.status === "failed") { clearInterval(jobTimer); jobTimer = null; }
  }, 2000);
}

const STATUS = { processed: "added", skipped_existing: "already here", rejected: "out of scope", failed: "failed" };
function showJob(job) {
  const box = $("v-job");
  if (!box) return;
  const head = { queued: "Waiting…", running: "Working…", done: "Done", failed: "Stopped" }[job.status];
  // a video saved without frames (not downloaded: its licence, or unavailable) says why
  const rows = job.results.map((r) => {
    const bare = r.status === "processed" && !r.frames;
    return `<li>${bare ? "no images" : esc(STATUS[r.status] ?? r.status)}${r.frames ? ` · ${r.frames} frames` : ""} · ${esc((r.title ?? r.youtube_id).slice(0, 70))}` +
      (r.reason && (bare || r.status !== "processed") ? `<span class="note">${esc(r.reason.slice(0, 160))}</span>` : "") + "</li>";
  }).join("");
  const other = job.library !== currentLib && job.results.some((r) => r.status === "processed");
  box.innerHTML = `<p><b>${head}</b> · ${esc(job.folder || job.scope)}${job.error ? `<span class="note">${esc(job.error)}</span>` : ""}</p>` +
    (rows ? `<ul class="results">${rows}</ul>` : "") +
    (other ? `<p><a href="#" data-lib="${esc(job.library)}">Show “${esc(job.folder)}”</a></p>` : "") +
    (job.status === "done" || job.status === "failed" ? "" : `<pre class="log">${esc(job.log.slice(-6).join("\n"))}</pre>`);
}

showView(); // here, once the whole module is defined (the slider's range needs the subtitles' constants)
intro(); // the Video panel shows at once, before the folder's images have loaded
if (documentView || mapView) load(); // views with their own left panel don't wait for the folder's frames
await Promise.allSettled([loadVideos(), pollStats(), loadFolders()]);
if (!documentView && !mapView) load();
