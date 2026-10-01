import { setupZoom } from "./zoom.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const pct = (x) => `${Math.round(x * 100)}%`;
const clock = (s) => {
  s = Math.max(0, Math.round(s));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
};

const panel = $("panel"), main = $("main");
const videos = new Map();   // video_id -> { duration_s, frame_times: [[frame_id, t], ...], ... }
const details = new Map();  // frame_id -> Promise<full frame record>
let items = [], total = 0, current = -1, facetsLoaded = false;
// Scrubbing / arrow keys scroll the grid under a still cursor. Ignore the hovers that causes
// until the pointer really moves.
let hoverPaused = false, pointerXY = "";
// A clicked frame is pinned: the panel sticks to it and the other tiles dim, until it's clicked again.
let pinned = null;          // frame_id
// Clicking the panel title switches every title between the original and YouTube's English title.
// Timeline view: each video drawn as an editing timeline, with a marker at every extracted frame.
// Its subtitles mode shows each video's captions instead of the filmstrip.
const savedView = (() => { try { return localStorage.getItem("view"); } catch { return null; } })();
let timeline = savedView === "timeline" || savedView === "subtitles";
let subs = savedView === "subtitles";

// ---------------------------------------------------------------- data

async function loadVideos() {
  for (const v of await (await fetch("/api/videos?limit=1000")).json()) {
    v.order = new Map(v.frame_times.map(([id], k) => [id, k + 1])); // 1-based position in the video
    videos.set(v.video_id, v);
  }
}

let loadSeq = 0;
async function load() {
  const seq = ++loadSeq;
  const keep = items[current]?.frame_id;
  const p = new URLSearchParams({ limit: 500 });
  if ($("q").value) p.set("q", $("q").value);
  if ($("category").value) p.append("category", $("category").value);
  if ($("year").value) p.set("year", $("year").value);
  if (queryImage) { p.set("sort", "image"); p.set("image", queryImage.id); }
  else if ($("sort").value) p.set("sort", $("sort").value);
  // The API returns at most 500 frames per request: page through all of them, or the grid silently
  // drops whole videos and the numbering stops matching the timeline tally.
  const res = await (await fetch("/api/frames?" + p)).json();
  while (res.items.length < res.total) {
    p.set("offset", res.items.length);
    const page = await (await fetch("/api/frames?" + p)).json();
    if (!page.items.length) break;
    res.items.push(...page.items);
  }
  if (seq !== loadSeq) return; // a newer search started while this one was loading
  if (!facetsLoaded) {
    for (const [k, n] of Object.entries(res.facets.category)) $("category").add(new Option(`${k} (${n})`, k));
    for (const [k, n] of Object.entries(res.facets.year)) $("year").add(new Option(`Published ${k} (${n})`, k));
    total = res.total;
    facetsLoaded = true;
    fitControls();
  }
  render(res.items);
  showStats(res.items);
  current = -1;
  const pin = items.findIndex((it) => it.frame_id === pinned);
  if (pin >= 0) return setPin(pin);
  setPin(-1);
  const again = items.findIndex((it) => it.frame_id === keep);
  again >= 0 ? select(again) : intro();
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
  main.innerHTML = items.length ? "" : `<p class="empty">No frames match${q ? ` “${esc(q)}”` : ""}${
    $("category").value || $("year").value ? " with these filters" : ""}.</p>`;
  if (timeline) return items.length && renderTimeline(groups);
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
  for (const img of main.querySelectorAll("img")) {
    if (img.complete) img.classList.add("loaded");
    else img.addEventListener("load", () => img.classList.add("loaded"), { once: true });
  }
}

// Each video is laid out like a clip on an editing timeline: a filmstrip in which each extracted frame
// starts at a black vertical marker at its timestamp and repeats until the next frame's marker. No text.
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
    if (subs) loadSubtitles(r.id).then((d) => { r.subs = d; drawWords(); }, () => {});
  }
  const wrap = document.createElement("div");
  wrap.className = "tl";
  main.append(wrap);
  layoutTimeline();
}

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
    // Where time t sits along the unwrapped strip, in px. An opened frame bends it: its strip gains width
    // (bend over [t, end]), and if it would break across the edge, the strip before it stretches to push
    // it to the start of the next line (bend over [previous marker, t]). Both grow with the spread p.
    const bends = [];
    const X = (t) => bends.reduce((x, [a, b, e]) => x + e * (b > a ? clamp01((t - a) / (b - a)) : +(t >= b)), t * pps);
    const opened = []; // [x0, x1, p]
    r.times.forEach(([id, t], k) => {
      const s = spreads.get(id), hit = r.shown.get(id);
      if (!s || !hit) return;
      const end = k + 1 < r.times.length ? r.times[k + 1][1] : r.dur;
      const it = hit[0];
      const fw = Math.min(W, HF * (it.width && it.height ? it.width / it.height : 16 / 9));
      const x0 = X(t), col = x0 - Math.floor(x0 / W + 1e-6) * W;
      if (col > 0.5 && col + fw > W) bends.push([k ? r.times[k - 1][1] : 0, t, (W - col) * s.p]);
      const w = (end - t) * pps;
      if (fw > w) bends.push([t, end, (fw - w) * s.p]);
      opened.push([X(t), subs ? Math.min(X(end), X(t) + fw) : X(end), s.p]); // subtitles: the image shows once
    });
    const total = X(r.dur);
    const n = Math.max(1, Math.ceil(total / W - 1e-6));
    Object.assign(r, { X, W, heights: null, sec: null });
    // An opened frame makes its line taller, shared between two lines while it moves across.
    const heights = Array.from({ length: n }, (_, l) => Math.round(Math.min(HF, H + (HF - H) * opened.reduce((sum, [a, b, p]) =>
      sum + p * Math.max(0, Math.min(b, (l + 1) * W) - Math.max(a, l * W)) / Math.max(1, b - a), 0))));

    let sec = wrap.children[v];
    if (!sec) {
      sec = wrap.appendChild(Object.assign(document.createElement("section"), { className: "tl-video" }));
      sec.fresh = true;
    }
    while (sec.children.length > n) sec.lastChild.remove();
    while (sec.children.length < n) sec.append(Object.assign(document.createElement("div"), { className: "tl-track" }));
    for (let l = 0; l < n; l++) {
      sec.children[l].style.width = `${Math.round(Math.min(W, total - l * W))}px`;
      sec.children[l].style.height = `${heights[l]}px`;
      sec.children[l].style.setProperty("--ih", `${Math.max(IH, heights[l])}px`); // images squash only on a thin line
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
      const x0 = X(t), x1 = X(end), open = spreads.get(id)?.to === 1;
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
          const it = hit[0];
          seg.style.setProperty("--ar", it.width && it.height ? it.width / it.height : 16 / 9);
          if (seen.has(seg.dataset.bg)) seg.style.setProperty("--img", `url("${seg.dataset.bg}")`);
          else thumbs.observe(seg);
          segEls.set(key, seg);
        }
        if (open) sharpen(seg, hit[0].web_url);
        seg.className = `tile seg${a > x0 + 0.01 ? " cont" : ""}${open ? " open" : ""}` +
          `${hit[1] === current ? " on" : ""}${hit[1] === pin ? " pinned" : ""}`;
        seg.style.left = `${left}px`;
        seg.style.width = `${Math.max(0, right - left)}px`;
        if (seg.parentNode !== sec.children[l]) sec.children[l].append(seg);
      }
    });
  });
  while (wrap.children.length > tlVideos.length) wrap.lastChild.remove();
  for (const [key, seg] of segEls) if (!used.has(key)) { thumbs.unobserve(seg); seg.remove(); segEls.delete(key); }
  if (subs) drawWords();
}

// An opened frame swaps its thumbnail for the full image once that has loaded (no blank in between).
function sharpen(seg, url) {
  if (!url || seg.dataset.sharp) return;
  seg.dataset.sharp = url;
  const img = new Image();
  img.src = url;
  img.decode().then(() => seg.style.setProperty("--sharp", `url("${url}")`), () => {});
}

// Open the timeline at frame_id (closing any other), or close it (null).
function spreadTo(id) {
  const now = performance.now();
  for (const [key, s] of spreads) if (key !== id && s.to !== 0) Object.assign(s, { from: s.p, to: 0, start: now });
  if (id !== null && timeline) {
    const s = spreads.get(id);
    if (!s) spreads.set(id, { p: 0, from: 0, to: 1, start: now });
    else if (s.to !== 1) Object.assign(s, { from: s.p, to: 1, start: now, settled: false });
  }
  layoutTimeline();
  tlAnimate();
}

// One animation loop for the timeline: spreads opening/closing and video heights easing to their new
// size. The video under the pointer (or the pinned one) keeps its place on screen while things move.
let tlRaf = 0, tlLast = 0;
const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const easeInOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2);
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
    if (x < 1) busy = true;
    else if (s.to === 0) spreads.delete(id);
    else if (!s.settled) { s.settled = true; opened = id; }
  }
  if (spreading) layoutTimeline();
  const k = 1 - Math.exp(-dt / 70);
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
const seen = new Set();     // thumbnail URLs the browser has loaded and decoded
const thumbs = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    const url = e.target.dataset.bg;
    e.target.style.setProperty("--img", `url("${url}")`);
    const img = new Image();
    img.src = url;
    img.decode().then(() => seen.add(url), () => {});
    thumbs.unobserve(e.target);
  }
}, { rootMargin: "300px" });

addEventListener("resize", () => { if (timeline) layoutTimeline(); });

function setView(view) {
  timeline = view !== "grid";
  subs = view === "subtitles";
  tlScale = readZoom();
  try { localStorage.setItem("view", view); } catch {}
  showView();
  scrollTo(0, 0);
  drawWords(); // clears the words when leaving the subtitles view
  load();
}
function showView() {
  $("timeline").classList.toggle("set", timeline && !subs);
  $("subs").classList.toggle("set", subs);
}
// Light/dark: follows the system until chosen here, then remembered per browser. The button names the other one.
const isDark = () => (document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
const themeLabel = () => { $("theme").textContent = isDark() ? "Light" : "Dark"; };
$("theme").onclick = () => {
  const t = isDark() ? "light" : "dark";
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem("theme", t); } catch {}
  themeLabel();
  drawWords(); // the subtitles are drawn with the theme's colours
};
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { themeLabel(); drawWords(); });
themeLabel();
$("timeline").onclick = () => setView(timeline && !subs ? "grid" : "timeline");
$("subs").onclick = () => setView(subs ? "timeline" : "subtitles"); // switches the timeline between images and subtitles
showView();

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
function loadSubtitles(id) {
  if (!subtitleData.has(id)) {
    subtitleData.set(id, fetch(`/api/videos/${encodeURIComponent(id)}/subtitles`).then((r) => {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).catch((e) => { subtitleData.delete(id); throw e; }));
  }
  return subtitleData.get(id);
}

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
        cv.style.top = `${Math.round((lh - SUB_H) / 2)}px`; // centred in a line grown for an opened frame
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
      y += lh + TL_GAP;
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
  const room = Math.round(Math.min(r.W, r.X(r.dur))) - 12;
  ctx.font = `12px ${getComputedStyle(document.body).fontFamily}`;
  const text = ["No subtitles detected", "No subtitles", "None"].find((t) => ctx.measureText(t).width <= room);
  if (!text) return;
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();
  ctx.fillText(text, 6, 26);
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
      const x = r.X(t), l = Math.floor(x / r.W + 1e-6);
      // the priority pass needs every line of the video (a word can move onto the next line), so that a
      // line looks the same whichever lines are being drawn with it
      if (!todo.has(l) && !WORD_PRIORITY) continue;
      const room = (k + 1 < words.length ? r.X(words[k + 1][0]) : r.X(r.dur) + WORD_GAP) - x - WORD_GAP;
      const f = kind === "en" ? (flag === 1 ? font.enPlace : font.en) : flag === 1 ? font.place : font.orig, marked = hit(word);
      laid.push({ word, flag, l, lx: x - l * r.W, room, f, tw: width(f, word), marked,
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

function intro() {
  panel.dataset.video = "";
  panel.innerHTML = `<div class="head"><div>
    <div class="title">Ukraine image evidence</div>
    <div class="sub">${items.length === total ? total : `${items.length} of ${total}`} frames · ${videos.size} video${videos.size === 1 ? "" : "s"}</div>
  </div></div>`;
}

// Pin frame i (or unpin with -1). Pinning also shows it in the panel.
function setPin(i) {
  for (const t of main.querySelectorAll(".tile.pinned")) t.classList.remove("pinned");
  pinned = items[i]?.frame_id ?? null;
  main.classList.toggle("has-pin", pinned !== null);
  spreadTo(pinned);
  if (pinned === null) return;
  for (const t of main.querySelectorAll(`.tile[data-i="${i}"]`)) t.classList.add("pinned"); // a wrapped timeline frame has several pieces
  select(i);
}

// Explicit navigation (tally scrub, arrow keys) moves the pin along when there is one.
function go(i) {
  if (!items[i]) return;
  if (pinned !== null) setPin(i);
  select(i, true);
}

function hover(tile) {
  if (tile && pinned === null) select(+tile.dataset.i);
}

function select(i, scroll = false) {
  if (!items[i]) return;
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
  if (subs) loadSubtitles(it.video_id).then((d) => { if ($("subsline")) $("subsline").textContent = `Subtitles: ${subtitleNote(d)}`; }, () => {});
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
      <a href="${f.urls.original}" target="_blank">Original</a> &nbsp;
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
  if (!hoverPaused) hover(e.target.closest?.(".tile"));
}, { passive: true });
// Click a tile to pin it; click it again (or empty space, or Esc) to unpin and resume hover.
main.addEventListener("click", (e) => {
  const tile = e.target.closest(".tile");
  if (!tile) return pinned !== null && unpin(null);
  const i = +tile.dataset.i;
  items[i].frame_id === pinned ? unpin(tile) : setPin(i);
});
function unpin(tileUnderPointer) {
  setPin(-1);
  current = -1;
  hover(tileUnderPointer);
}
panel.addEventListener("pointermove", (e) => { if (e.target.closest("#track")) scrub(e); });
panel.addEventListener("pointerdown", (e) => {
  if (!e.target.closest("#track")) return;
  e.target.closest("#track").setPointerCapture(e.pointerId);
  scrub(e);
});

// Size each bottom control to the text it shows (a <select> is otherwise as wide as its longest
// option), so the gaps between them read as equal.
const ruler = document.createElement("canvas").getContext("2d");
function textWidth(el, text) {
  const cs = getComputedStyle(el);
  ruler.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
  return Math.ceil(ruler.measureText(text).width);
}
function fitControls() {
  for (const id of ["sort", "category", "year"]) {
    const el = $(id);
    el.style.width = textWidth(el, el.selectedOptions[0]?.text ?? "") + "px";
  }
  $("q").style.setProperty("--rest", textWidth($("q"), $("q").placeholder) + 2 + "px");
}
document.fonts?.ready.then(fitControls);

// Bottom-left: how much has been analysed, live. Polls so it keeps up while an ingest is running.
let library = { videos: 0, frames: 0 };
function showStats(list = items) {
  const vids = new Set(list.map((it) => it.video_id)).size;
  const filtered = list.length !== library.frames;
  const near = $("sort").value.startsWith("near:") && !timeline ? $("sort").value.slice(5) : null;
  if (near) {
    // how many images the site places at or near the chosen place (it may be none)
    const here = list.filter((it) => it.sort_group === "at" || it.sort_group === "near");
    $("stats").textContent = here.length
      ? `${here.length} images near ${near} · ${new Set(here.map((it) => it.video_id)).size} videos`
      : `No images placed near ${near}`;
    return;
  }
  $("stats").textContent = filtered
    ? `${vids} of ${library.videos} videos · ${list.length} of ${library.frames} images`
    : `${library.videos} videos analysed · ${library.frames} images`;
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
}, () => {});

let t;
$("q").oninput = () => { clearTimeout(t); t = setTimeout(load, 250); };
const syncClear = () => $("clear").classList.toggle("on", !!($("q").value || $("category").value || $("year").value || queryImage));
$("sort").onchange = (e) => { e.target.classList.toggle("set", !!e.target.value); if (queryImage) setQueryImage(null); fitControls(); load(); };

// Search by image: pick, drop or paste an image; the grid is ordered by visual similarity to it.
// The image is only held in memory by the local server, never added to the library.
let queryImage = null; // { id, url }
async function useImage(file) {
  if (!file || !file.type.startsWith("image/")) return;
  const btn = $("byimage");
  btn.textContent = "Reading image…";
  try {
    const r = await fetch("/api/query-image", { method: "POST", body: file, headers: { "Content-Type": file.type } });
    if (!r.ok) throw new Error((await r.json()).detail ?? r.status);
    setQueryImage({ id: (await r.json()).id, url: URL.createObjectURL(file) });
    load();
  } catch (err) {
    btn.textContent = "By image";
    btn.title = `Couldn't use that image: ${err.message}`;
  }
}
function setQueryImage(q) {
  if (queryImage) URL.revokeObjectURL(queryImage.url);
  queryImage = q;
  const btn = $("byimage");
  btn.classList.toggle("set", !!q);
  btn.innerHTML = q ? `<img class="qthumb" src="${q.url}" alt="">Your image ×` : "By image";
  syncClear();
}
$("byimage").onclick = () => { if (queryImage) { setQueryImage(null); load(); } else $("imgfile").click(); };
$("imgfile").onchange = (e) => { useImage(e.target.files[0]); e.target.value = ""; };
window.addEventListener("dragover", (e) => { if ([...e.dataTransfer.items].some((i) => i.type.startsWith("image/"))) e.preventDefault(); });
window.addEventListener("drop", (e) => {
  const file = [...e.dataTransfer.files].find((f) => f.type.startsWith("image/"));
  if (file) { e.preventDefault(); useImage(file); }
});
window.addEventListener("paste", (e) => {
  const file = [...(e.clipboardData?.files ?? [])].find((f) => f.type.startsWith("image/"));
  if (file && !e.target.matches?.("input, textarea")) { e.preventDefault(); useImage(file); }
});
for (const id of ["category", "year"]) {
  $(id).onchange = (e) => { e.target.classList.toggle("set", !!e.target.value); fitControls(); syncClear(); load(); };
}
$("q").addEventListener("input", syncClear);
$("clear").onclick = () => {
  $("q").value = $("category").value = $("year").value = "";
  setQueryImage(null);
  $("category").classList.remove("set");
  $("year").classList.remove("set");
  fitControls();
  syncClear();
  load();
};

document.addEventListener("keydown", (e) => {
  if (e.target === $("q")) { if (e.key === "Escape") $("q").blur(); return; }
  if (e.target.matches?.("select, input, button")) return;
  if (e.key === "/") { e.preventDefault(); $("q").focus(); }
  if (e.key === "Escape" && pinned !== null) unpin(null);
  if (e.key === "ArrowRight") { e.preventDefault(); go(Math.min(items.length - 1, current + 1)); }
  if (e.key === "ArrowLeft") { e.preventDefault(); go(Math.max(0, current - 1)); }
});

// Grid density: pinch or +/- (see zoom.js).
// In the timeline view a pinch stretches time instead, re-wrapping the timelines as it goes.
setupZoom({
  root: main,
  axis: () => (timeline ? "x" : "both"),
  stretch: {
    clamp: (s) => clampScale(tlScale * s) / tlScale,
    preview: (s) => { tlLive = s; layoutTimeline(); },
    commit: (s) => {
      tlScale = clampScale(tlScale * s);
      tlLive = 1;
      try { localStorage.setItem(zoomKey(), tlScale); } catch {}
      layoutTimeline();
    },
  },
  onChange: (i, cols) => document.documentElement.toggleAttribute("data-dense", cols >= 8),
});

await Promise.all([loadVideos(), pollStats()]);
load();
