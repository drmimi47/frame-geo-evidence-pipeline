// Temporal Map: a video's inferred camera path (`evidence track`, /api/videos/{id}/track) on a tilted map, in step
// with the video. The video plays in the left panel; the dot moves along the road as it plays; the frames taken from
// it stand up along the route where they are placed, as the playhead passes them. Bottom right: a distance–time chart
// (Marey's train schedule: video time across, distance along the road up) over a scrubber with one tick per frame.
//
// Everything here is inferred and says so: the dot carries its uncertainty as a stretch of road (sigma_m), cuts in the
// footage (the dashcam clock jumps) leave the road driven meanwhile dashed, "not filmed", and the panel lists where
// each part of the path came from. The map tiles are only a backdrop; nothing is read off them.

const MAPLIBRE = "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl";
// Keyless tiles. The street map is OpenStreetMap's own, drawn grey (and inverted for dark) so it stays a backdrop.
const BASES = {
  osm: { tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" },
  sat: { tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], tileSize: 256,
         attribution: "Imagery © Esri, Maxar, Earthstar Geographics (recent: not of the filming date)" },
  satlabels: { tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"],
               tileSize: 256, attribution: "" },
};
const FOLLOW_PITCH = 62, OVERVIEW_PITCH = 52;
// Ride along: the camera low behind the dashcam, looking down the road, close in, so the frames pass like screens
const RIDE_PITCH = 74, RIDE_ZOOM = 15.4, RIDE_TURN = 0.1; // RIDE_TURN: how quickly it turns with the road (Follow: 0.04)
const OVERVIEW_PAD = { top: 140, bottom: 260, left: 80, right: 80 }; // clear of the key (top) and the chart (bottom)
const CONE_DEG = 55, CONE_M = 650;      // the dashcam's view: about 110° wide, drawn 650 m out
const TICK_M = 110;                     // half-length of a frame's tick across the road
const JUMP_M = 400;                     // samples further apart than this are a cut: don't slide between them

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const clock = (s) => {
  s = Math.max(0, Math.round(s));
  const m = Math.floor(s / 60), sec = String(s % 60).padStart(2, "0");
  return `${m}:${sec}`;
};
const km = (m) => `${(m / 1000).toFixed(1)} km`;
const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
const compass = (deg) => COMPASS[Math.round(((deg % 360) + 360) % 360 / 45) % 8];
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const isDark = () => (document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

let state = null; // everything belonging to the mounted view; null when another view is shown

// ------------------------------------------------------------ loading

let libPromise = null;
function loadMapLibre() {
  libPromise ??= new Promise((resolve, reject) => {
    if (!document.querySelector(`link[href="${MAPLIBRE}.css"]`)) {
      document.head.append(Object.assign(document.createElement("link"), { rel: "stylesheet", href: `${MAPLIBRE}.css` }));
    }
    const s = Object.assign(document.createElement("script"), { src: `${MAPLIBRE}.js`, async: true });
    s.onload = () => resolve(window.maplibregl);
    s.onerror = () => { libPromise = null; reject(new Error("The map library couldn't be loaded (offline?).")); };
    document.head.append(s);
  });
  return libPromise;
}
let ytPromise = null;
function loadYouTube() {
  ytPromise ??= new Promise((resolve, reject) => {
    if (window.YT?.Player) return resolve(window.YT);
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => { prev?.(); resolve(window.YT); };
    const s = Object.assign(document.createElement("script"), { src: "https://www.youtube.com/iframe_api", async: true });
    s.onerror = () => { ytPromise = null; reject(new Error("YouTube player unavailable")); };
    document.head.append(s);
  });
  return ytPromise;
}
if (!document.querySelector('link[href="/static/map.css"]')) {
  document.head.append(Object.assign(document.createElement("link"), { rel: "stylesheet", href: "/static/map.css" }));
}

// ------------------------------------------------------------ geometry (on the route, by distance along it)

function lerpAlong(route, m) {
  const a = route.along_m, c = route.coordinates;
  m = Math.min(Math.max(m, 0), a.at(-1));
  let lo = 0, hi = a.length - 1;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; (a[mid] <= m ? (lo = mid) : (hi = mid)); }
  const f = (m - a[lo]) / ((a[hi] - a[lo]) || 1);
  return [c[lo][0] + (c[hi][0] - c[lo][0]) * f, c[lo][1] + (c[hi][1] - c[lo][1]) * f];
}
function slice(route, m0, m1) { // the route between two distances, as a coordinate list
  const a = route.along_m, out = [lerpAlong(route, m0)];
  for (let k = 0; k < a.length; k++) if (a[k] > m0 && a[k] < m1) out.push(route.coordinates[k]);
  out.push(lerpAlong(route, m1));
  return out;
}
const M_PER_DEG = 111320;
function offset([lon, lat], bearingDeg, meters) {
  const b = (bearingDeg * Math.PI) / 180;
  return [lon + (Math.sin(b) * meters) / (M_PER_DEG * Math.cos((lat * Math.PI) / 180)), lat + (Math.cos(b) * meters) / M_PER_DEG];
}
function headingAt(route, m) {
  const [a, b] = [lerpAlong(route, m - 100), lerpAlong(route, m + 100)];
  const y = (b[0] - a[0]) * Math.cos((a[1] * Math.PI) / 180), x = b[1] - a[1];
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}
const line = (coords) => ({ type: "Feature", geometry: { type: "LineString", coordinates: coords }, properties: {} });
const multi = (lines, props = {}) => ({ type: "Feature", geometry: { type: "MultiLineString", coordinates: lines }, properties: props });
const fc = (features) => ({ type: "FeatureCollection", features });

// The state at video time t, from the per-second samples: [t, along_m, lon, lat, heading, sigma_m].
function at(track, t) {
  const S = track.samples, i = Math.min(S.length - 2, Math.max(0, Math.floor(t)));
  const a = S[i], b = S[i + 1], f = Math.min(1, Math.max(0, t - a[0]));
  if (Math.abs(b[1] - a[1]) > JUMP_M) {
    // a cut between these samples: on its near side until the cut's own time (not the next whole second)
    const cut = track.segments.find((x) => x.video_start > a[0] && x.video_start <= b[0]);
    const s = t >= (cut ? cut.video_start : b[0]) ? b : a;
    return { t, along: s[1], lonlat: [s[2], s[3]], heading: s[4], sigma: s[5] };
  }
  return { t, along: a[1] + (b[1] - a[1]) * f, lonlat: [a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f], heading: a[4], sigma: a[5] + (b[5] - a[5]) * f };
}
const segmentAt = (track, t) => track.segments.findIndex((s) => t >= s.video_start && t < s.video_end);

// ------------------------------------------------------------ view

export async function renderMap(main, research) {
  leaveMap();
  openScrub(); // grows out of the zoom slider at once, while the track loads
  const st = state = { bornAt: performance.now(), main, research, t: 0, playing: false, follow: false, base: "map", raf: 0, glideUntil: 0 };
  main.replaceChildren();
  research.replaceChildren(Object.assign(document.createElement("p"), { className: "empty", textContent: "Loading…" }));
  let list;
  try {
    const r = await fetch("/api/tracks");
    if (!r.ok) throw new Error(r.status);
    list = await r.json();
  } catch {
    if (state !== st) return;
    // the page is newer than the running server (its Python is loaded at start; the page is read fresh)
    closeScrub();
    research.innerHTML = `<div class="tm-empty"><p>The server doesn't know the Temporal Map yet.</p>
      <p class="small muted">Restart it (<code>evidence serve</code>) and reload this page.</p></div>`;
    return;
  }
  if (state !== st) return;
  if (!list.length) {
    closeScrub();
    research.innerHTML = `<div class="tm-empty"><p>No video in this folder has an inferred path yet.</p>
      <p class="small muted">Make one with <code>evidence track &lt;video&gt; --start lat,lon --end lat,lon --note "…"</code>:
      the road between a start and an end the video itself shows, timed by a clock burned into its frames.</p></div>`;
    return;
  }
  st.list = list;
  let pick;
  try { pick = localStorage.getItem("mapVideo"); } catch {}
  await show(list.find((x) => x.video_id === pick) ?? list[0]);
}

async function show(entry) {
  const st = state;
  const track = await (await fetch(`/api/videos/${encodeURIComponent(entry.video_id)}/track`)).json();
  if (state !== st) return;
  try { localStorage.setItem("mapVideo", entry.video_id); } catch {}
  st.track = track;
  st.t = track.segments[0]?.video_start ?? 0;
  buildPanel(st);
  buildStage(st);
  try {
    const gl = await loadMapLibre();
    await scrubGrown; // building the map stalls the page: let the scrubber finish growing first
    if (state !== st) return;
    buildMap(st, gl);
  } catch (e) {
    st.mapEl.innerHTML = `<p class="empty tm-msg">${esc(e.message)}</p>`;
  }
  buildPlayer(st);
  st.raf = requestAnimationFrame(function tick() {
    if (state !== st) return;
    if (st.player?.getCurrentTime && st.playing) st.t = st.player.getCurrentTime();
    else if (st.playing && !st.player?.getCurrentTime) st.t = Math.min(track.duration_s, st.t + 1 / 60); // no player: run our own clock
    update(st);
    st.raf = requestAnimationFrame(tick);
  });
}

export function leaveMap() {
  const st = state;
  if (!st) return;
  state = null;
  cancelAnimationFrame(st.raf);
  removeEventListener("keydown", st.onKey, true);
  st.themeObs?.disconnect();
  st.resizeObs?.disconnect();
  try { st.player?.destroy?.(); } catch {}
  st.caption?.remove();
  st.map?.remove();
  st.main.replaceChildren();
  closeScrub();
}

// The scrubber: the zoom slider at the end of the bottom controls (a thin line with a dot) stretches up and to the
// left into the timeline, its bottom-right corner staying put; being in the same row, the buttons slide left to make
// room, and the other views fold into the Temporal Map button (#controls.tm-wide) to give it more. Clicking Temporal
// Map again folds the scrubber back into the slider and brings the views back out; clicking it (or the folded slider)
// once more opens it again. Leaving the view shrinks it back into the slider. (map.css: #controls .tm-scrub)
const SCRUB_MS = 700;
let scrub = null, scrubTimer = 0, scrubGrown = Promise.resolve();
function openScrub() {
  const footer = document.getElementById("controls");
  clearTimeout(scrubTimer);
  if (!scrub) {
    scrub = Object.assign(document.createElement("div"), { className: "tm-scrub" });
    const slider = document.getElementById("tlzoom");
    slider ? slider.after(scrub) : footer.append(scrub); // in the zoom slider's place (it is hidden in this view)
    footer.classList.add("tm-on");
    scrub.getBoundingClientRect(); // start from the slider's size, so the growth animates
  }
  if (!scrub.classList.contains("open")) scrubGrown = new Promise((r) => setTimeout(r, reduced() ? 0 : SCRUB_MS));
  scrub.classList.add("open");
  footer.classList.add("tm-wide");
  mapButton()?.setAttribute("title", "Temporal Map · click to fold the timeline and show the other views");
  return scrub;
}
const mapButton = () => document.querySelector('#controls button.view[data-view="map"]');
const MAP_TITLE = mapButton()?.title ?? ""; // its own tooltip, given back when the view is left
// fold the scrubber into the slider and bring the other views out, or the other way round
function foldScrub(open) {
  if (!scrub) return;
  if (open) return openScrub();
  scrub.classList.remove("open");
  document.getElementById("controls").classList.remove("tm-wide");
  mapButton()?.setAttribute("title", "Temporal Map · click to open the timeline again");
}
// A click on Temporal Map while it is shown folds or opens the timeline. (The click that switches to it is ignored:
// the view was made by that same click, after it happened.)
mapButton()?.addEventListener("click", (e) => {
  if (!state || !scrub || e.timeStamp < state.bornAt) return;
  foldScrub(!scrub.classList.contains("open"));
});
function closeScrub() {
  if (!scrub) return;
  const el = scrub, footer = document.getElementById("controls");
  el.classList.remove("open");
  footer.classList.remove("tm-wide");
  mapButton()?.setAttribute("title", MAP_TITLE);
  // shrinking back, its dot glides to where the zoom slider's dot will be (once the new view has set the slider),
  // so when the slider takes its place nothing jumps; the slider stays hidden until then (map.css #controls.tm-on)
  requestAnimationFrame(() => {
    const s = document.getElementById("tlzoom");
    if (s && scrub === el && !el.classList.contains("open")) el.style.setProperty("--x", s.value / (s.max || 1));
  });
  scrubTimer = setTimeout(() => {
    if (scrub !== el || el.classList.contains("open")) return;
    el.remove();
    scrub = null;
    footer.classList.remove("tm-on");
  }, reduced() ? 0 : SCRUB_MS);
}

// ------------------------------------------------------------ left panel: the video and what the path rests on

function buildPanel(st) {
  const tr = st.track, year = tr.published_at?.slice(0, 4);
  const pick = st.list.length > 1
    ? `<select class="tm-pick" aria-label="Video">${st.list.map((x) => `<option value="${esc(x.video_id)}"${x.video_id === tr.video_id ? " selected" : ""}>${esc(x.title)}</option>`).join("")}</select>`
    : "";
  const LABEL = { uploader_route_map: "Ends", openstreetmap_route: "Road", frame_onscreen_clock: "Timing", average_speed_model: "Between" };
  const prov = tr.provenance.map((p) => `<dt>${LABEL[p.method] ?? esc(p.method)}</dt><dd>${esc(p.evidence)}</dd>`).join("");
  const passes = tr.settlements.map((s) => {
    const t = timeAtAlong(tr, s.along_m);
    return `<li>${t == null
      ? `<span>${esc(s.name)}</span> <span class="muted">· ${km(s.along_m)} · not filmed (in a cut)</span>`
      : `<button type="button" data-t="${t}">${esc(s.name)}</button> <span class="muted">· ${km(s.along_m)} · ${clock(t)}</span>`}</li>`;
  }).join("");
  const cuts = tr.segments.slice(1).map((s, k) => {
    const prev = tr.segments[k], gapS = (new Date(s.clock_start) - new Date(prev.clock_end)) / 1000;
    return `<li><button type="button" data-t="${s.video_start}">Cut at ${clock(s.video_start)}</button>
      <span class="muted">· clock jumps ${Math.round(gapS / 60)} min · ${km(s.along_start_m - prev.along_end_m)} of road not filmed</span></li>`;
  }).join("");
  st.research.innerHTML = `
    <div class="tm-video"><div id="tm-player"></div></div>
    <div class="head">
      ${pick || `<div class="title">${esc(tr.title)}</div>`}
      <div class="sub">${esc(tr.channel_title ?? "")}${year ? ` · ${year}` : ""} · <a href="${esc(tr.source_url)}" target="_blank" rel="noopener">YouTube ↗</a></div>
    </div>
    <p class="tm-transport"><button type="button" id="tm-play">Play</button>
      <button type="button" id="tm-follow" aria-pressed="false">Follow</button>
      <button type="button" id="tm-overview">Whole route</button></p>
    <dl class="fields tm-now">
      <dt>Video</dt><dd id="tm-t"></dd>
      <dt>Clock</dt><dd id="tm-clock"></dd>
      <dt>Road</dt><dd id="tm-along"></dd>
      <dt>Facing</dt><dd id="tm-heading"></dd>
    </dl>
    <p class="tm-summary">${esc(tr.summary)}</p>
    <dl class="fields tm-prov">
      ${prov}
      <dt>Filmed</dt><dd>${esc(tr.capture.clock_start.replace("T", " "))} – ${esc(tr.capture.clock_end.slice(11))}<span class="note">${esc(tr.capture.note)}</span></dd>
      <dt>Confidence</dt><dd>${Math.round(tr.confidence * 100)}%<span class="note">inferred, not a GPS track: the dot is where the road and the clock put the camera, give or take the shaded stretch</span></dd>
    </dl>
    <h3 class="tm-h">Cuts</h3><ul class="tm-list">${cuts || "<li class='muted'>None: one continuous take</li>"}</ul>
    <h3 class="tm-h">Passes</h3><ul class="tm-list">${passes}</ul>
    <p class="small muted tm-credit">Road © OpenStreetMap contributors (ODbL), routed by OSRM · places: GeoNames (CC BY 4.0)</p>`;
  const $ = (id) => st.research.querySelector("#" + id);
  st.ui = { t: $("tm-t"), clock: $("tm-clock"), along: $("tm-along"), heading: $("tm-heading"), play: $("tm-play"), follow: $("tm-follow") };
  st.ui.play.onclick = () => togglePlay(st);
  st.ui.follow.onclick = () => { st.followTouched = true; setFollow(st, !st.follow); };
  $("tm-overview").onclick = () => { st.followTouched = true; setFollow(st, false); overview(st); };
  st.research.querySelector(".tm-pick")?.addEventListener("change", (e) => {
    try { localStorage.setItem("mapVideo", e.target.value); } catch {}
    renderMap(st.main, st.research); // remount on the chosen video
  });
  st.research.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-t]");
    if (b) seek(st, Number(b.dataset.t), true);
  });
  st.onKey = (e) => {
    if (e.target.matches?.("input, select, textarea")) return;
    if (e.key === " ") { e.preventDefault(); e.stopPropagation(); togglePlay(st); }
    else if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault(); e.stopPropagation();
      seek(st, st.t + (e.key === "ArrowRight" ? 5 : -5) * (e.shiftKey ? 6 : 1), true);
    }
  };
  addEventListener("keydown", st.onKey, true);
}

// the video time the dot reaches a distance along the road, or null when that stretch wasn't filmed
function timeAtAlong(tr, m) {
  for (const s of tr.segments) {
    if (m < s.along_start_m - 1 || m > s.along_end_m + 1) continue;
    const S = tr.samples;
    for (let i = Math.floor(s.video_start); i < S.length && S[i][0] <= s.video_end; i++) if (S[i][1] >= m) return S[i][0];
  }
  return null;
}

function buildPlayer(st) {
  loadYouTube().then((YT) => {
    if (state !== st) return;
    st.player = new YT.Player("tm-player", {
      videoId: st.track.youtube_id,
      playerVars: { rel: 0, modestbranding: 1, playsinline: 1, start: Math.floor(st.t) },
      events: {
        onStateChange: (e) => {
          st.playing = e.data === YT.PlayerState.PLAYING;
          st.ui.play.textContent = st.playing ? "Pause" : "Play";
          if (!st.playing && st.player.getCurrentTime) st.t = st.player.getCurrentTime();
        },
      },
    });
  }, () => { st.research.querySelector(".tm-video").classList.add("off"); });
}

function togglePlay(st) {
  if (!st.playing && !st.followTouched && !st.follow) setFollow(st, true); // the first Play follows the dot
  if (st.player?.getPlayerState) {
    st.playing ? st.player.pauseVideo() : st.player.playVideo();
  } else {
    st.playing = !st.playing;
    st.ui.play.textContent = st.playing ? "Pause" : "Play";
  }
}

function seek(st, t, andFollow = false) {
  st.t = Math.min(Math.max(0, t), st.track.duration_s);
  st.player?.seekTo?.(st.t, true);
  if (andFollow && !st.follow) setFollow(st, true);
  st.lastCut = segmentAt(st.track, st.t); // a seek is not a cut to fly over
  update(st, true);
}

function setRide(st, on) {
  st.ride = on;
  st.main.querySelector(".tmap")?.classList.toggle("riding", on);
  st.ui.ride?.classList.toggle("set", on);
  st.ui.ride?.setAttribute("aria-pressed", on);
  setFollow(st, true); // either way the camera follows: low (riding) or high (Follow)
}

function setFollow(st, on) {
  if (!on && st.ride) {
    st.ride = false;
    st.ui.ride?.classList.remove("set");
    st.ui.ride?.setAttribute("aria-pressed", false);
    st.main.querySelector(".tmap")?.classList.remove("riding");
  }
  st.follow = on;
  st.ui.follow.classList.toggle("set", on);
  st.ui.follow.setAttribute("aria-pressed", on);
  if (on && st.map) {
    const now = at(st.track, st.t);
    st.bearing = now.heading;
    glide(st, 900);
    st.map.easeTo({ center: now.lonlat, bearing: now.heading, ...camera(st), duration: reduced() ? 0 : 900 });
  }
}

// ------------------------------------------------------------ stage: map + distance–time chart + scrubber

function buildStage(st) {
  st.main.innerHTML = `
    <div class="tmap">
      <div class="tmap-canvas"></div>
      <div class="tmap-tools">
        <button type="button" data-base="map" class="set">Map</button>
        <button type="button" data-base="sat">Satellite</button>
        <button type="button" id="tm-all" aria-pressed="false" title="Show every frame along the route at once, not only those near the playhead">All frames</button>
        <button type="button" id="tm-ride" aria-pressed="false" title="Ride along: the camera follows the videographer down the road, low behind the dashcam, and the frames pass in front of it as the video plays">Ride along</button>
      </div>
      <div class="tmap-key" aria-hidden="true">
        <span><i class="k-filmed"></i>filmed</span><span><i class="k-cut"></i>not filmed (cut)</span>
        <span><i class="k-band"></i>where the camera may be</span><span><i class="k-tick"></i>a frame</span>
      </div>
    </div>`;
  st.mapEl = st.main.querySelector(".tmap-canvas");
  st.scrubEl = openScrub();
  st.scrubEl.innerHTML = `
    <svg class="marey" role="img" aria-label="Distance along the road against video time"></svg>
    <div class="bar"><div class="ticks"></div><div class="head"></div></div>
    <div class="ends"><span>0:00</span><span class="now"></span><span>${clock(st.track.duration_s)}</span></div>`;
  for (const b of st.main.querySelectorAll(".tmap-tools button[data-base]")) b.onclick = () => setBase(st, b.dataset.base);
  // All frames: every plane stands at once (the current one still solid); off again, they follow the playhead
  const all = st.main.querySelector("#tm-all");
  all.onclick = () => {
    st.allFrames = !st.allFrames;
    all.classList.toggle("set", st.allFrames);
    all.setAttribute("aria-pressed", st.allFrames);
    if (st.map) frames(st);
  };
  // Ride along: follow the dot from low behind it (and play, so the camera moves); off again, back up to Follow
  st.ui.ride = st.main.querySelector("#tm-ride");
  st.ui.ride.onclick = () => {
    st.followTouched = true;
    setRide(st, !st.ride);
    if (st.ride && !st.playing) togglePlay(st);
  };
  // frame ticks on the scrubber
  st.scrubEl.querySelector(".ticks").innerHTML = st.track.frames
    .map((f) => `<i style="--x:${f.t / st.track.duration_s}"></i>`).join("") +
    st.track.segments.slice(1).map((s) => `<b class="cut" style="--x:${s.video_start / st.track.duration_s}"></b>`).join("");
  // scrub by dragging on the chart or the bar
  const toT = (e) => {
    const r = st.scrubEl.getBoundingClientRect();
    return Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)) * st.track.duration_s;
  };
  st.scrubEl.addEventListener("pointerdown", (e) => {
    if (!st.scrubEl.classList.contains("open")) { foldScrub(true); return; } // folded: a click opens it, doesn't seek
    e.preventDefault(); // a drag along it is a scrub, not a text selection (of its times, or the page beside it)
    st.scrubEl.setPointerCapture(e.pointerId);
    st.scrubbing = true;
    seek(st, toT(e));
  });
  st.scrubEl.addEventListener("pointermove", (e) => { if (st.scrubbing) seek(st, toT(e)); });
  const end = () => { st.scrubbing = false; };
  st.scrubEl.addEventListener("pointerup", end);
  st.scrubEl.addEventListener("pointercancel", end);
  st.resizeObs = new ResizeObserver(() => drawMarey(st));
  st.resizeObs.observe(st.scrubEl);
  st.themeObs = new MutationObserver(() => { drawMarey(st); paint(st); });
  st.themeObs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (state === st) { drawMarey(st); paint(st); } });
}

// Marey chart: x video time, y distance along the road (A at the bottom, B at the top). The settlements the road
// passes are faint rules; cuts are dashed risers (the road driven while the camera was off); the shaded band is sigma.
function drawMarey(st) {
  const svg = st.scrubEl.querySelector(".marey"), tr = st.track;
  const W = svg.clientWidth, H = svg.clientHeight;
  if (!W || !H) return;
  const L = tr.route.length_m, D = tr.duration_s;
  const X = (t) => (t / D) * W, Y = (m) => H - 4 - (m / L) * (H - 8);
  let g = "";
  for (const s of tr.settlements) {
    g += `<line class="rule" x1="0" x2="${W}" y1="${Y(s.along_m)}" y2="${Y(s.along_m)}"/>` +
         `<text class="lbl" x="2" y="${Y(s.along_m) - 3}">${esc(s.name)}</text>`;
  }
  for (const seg of tr.segments) {
    const pts = tr.samples.filter((p) => p[0] >= seg.video_start && p[0] <= seg.video_end);
    if (!pts.length) continue;
    const top = pts.map((p) => `${X(p[0]).toFixed(1)},${Y(Math.min(L, p[1] + p[5])).toFixed(1)}`);
    const bot = pts.map((p) => `${X(p[0]).toFixed(1)},${Y(Math.max(0, p[1] - p[5])).toFixed(1)}`).reverse();
    g += `<polygon class="band" points="${top.concat(bot).join(" ")}"/>`;
    g += `<polyline class="path" points="${pts.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" ")}"/>`;
  }
  tr.segments.slice(1).forEach((s, k) => {
    const prev = tr.segments[k], x = X(s.video_start);
    g += `<line class="riser" x1="${x}" x2="${x}" y1="${Y(prev.along_end_m)}" y2="${Y(s.along_start_m)}"/>`;
    g += `<text class="lbl cutlbl" x="${x + 4}" y="${(Y(prev.along_end_m) + Y(s.along_start_m)) / 2 + 4}">cut · ${km(s.along_start_m - prev.along_end_m)} unseen</text>`;
  });
  g += `<line class="now" x1="0" x2="0" y1="0" y2="${H}"/><circle class="dot" r="3.5" cx="0" cy="0"/>`;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.innerHTML = g;
  st.mareyNow = svg.querySelector("line.now");
  st.mareyDot = svg.querySelector("circle.dot");
  st.mareyXY = { X, Y };
  update(st, true);
}

// ------------------------------------------------------------ the map

function palette(st) {
  if (st.base === "sat") return { ink: "#ffffff", halo: "#000000", muted: "rgba(255,255,255,.75)", faint: "rgba(255,255,255,.18)" };
  return { ink: css("--fg") || "#111", halo: css("--bg") || "#fff", muted: css("--muted") || "#8a8a8a",
           faint: isDark() ? "rgba(255,255,255,.14)" : "rgba(0,0,0,.12)" };
}

function buildMap(st, gl) {
  const tr = st.track, r = tr.route;
  const raster = (k) => ({ type: "raster", tiles: BASES[k].tiles, tileSize: BASES[k].tileSize, attribution: BASES[k].attribution, maxzoom: 19 });
  const map = st.map = new gl.Map({
    container: st.mapEl,
    style: {
      version: 8,
      sources: { osm: raster("osm"), sat: raster("sat"), satlabels: raster("satlabels") },
      layers: [
        { id: "osm", type: "raster", source: "osm", paint: { "raster-saturation": -1, "raster-contrast": -0.25, "raster-opacity": 0.75 } },
        { id: "sat", type: "raster", source: "sat", layout: { visibility: "none" }, paint: { "raster-saturation": -0.35, "raster-brightness-max": 0.85 } },
        { id: "satlabels", type: "raster", source: "satlabels", layout: { visibility: "none" } },
      ],
    },
    bounds: boundsOf(r.coordinates),
    fitBoundsOptions: { padding: OVERVIEW_PAD },
    pitch: OVERVIEW_PITCH,
    maxPitch: 75,
    attributionControl: { compact: true },
  });
  map.addControl(new gl.NavigationControl({ visualizePitch: true, showZoom: false }), "top-right");
  // a drag or rotate by hand stops following, until Follow is clicked again (or the video is seeked from the panel)
  for (const ev of ["dragstart", "rotatestart", "pitchstart"]) map.on(ev, (e) => { if (e.originalEvent) setFollow(st, false); });

  map.on("load", () => {
    const filmed = tr.segments.map((s) => slice(r, s.along_start_m, s.along_end_m));
    const unfilmed = tr.segments.slice(1).map((s, k) => slice(r, tr.segments[k].along_end_m, s.along_start_m));
    const ticks = tr.frames.map((f) => {
      const p = [f.lon, f.lat], h = headingAt(r, f.along_m);
      return { type: "Feature", properties: { id: f.frame_id, t: f.t }, geometry: { type: "LineString", coordinates: [offset(p, h - 90, TICK_M), offset(p, h + 90, TICK_M)] } };
    });
    const add = (id, data) => map.addSource(id, { type: "geojson", data });
    add("unfilmed", fc([multi(unfilmed)]));
    add("filmed", fc([multi(filmed)]));
    add("done", fc([]));
    add("band", fc([]));
    add("cone", fc([]));
    add("ticks", fc(ticks));
    add("here", fc([]));
    // Line weights, one family: the road filmed and not filmed share a weight (dashed where it wasn't filmed), each on
    // a light halo; the road travelled so far is heaviest; frame ticks are lighter, the current one as heavy as the road.
    map.addLayer({ id: "route-halo", type: "line", source: "filmed", layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-width": 7 } });
    map.addLayer({ id: "unfilmed-halo", type: "line", source: "unfilmed", layout: { "line-join": "round" }, paint: { "line-width": 6 } });
    map.addLayer({ id: "unfilmed", type: "line", source: "unfilmed", layout: { "line-join": "round" }, paint: { "line-width": 2.6, "line-dasharray": [1.4, 1.2] } });
    map.addLayer({ id: "filmed", type: "line", source: "filmed", layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-width": 2.6 } });
    map.addLayer({ id: "band", type: "line", source: "band", layout: { "line-cap": "butt", "line-join": "round" }, paint: { "line-width": 16 } });
    map.addLayer({ id: "cone", type: "fill", source: "cone", paint: {} });
    map.addLayer({ id: "cone-edge", type: "line", source: "cone", paint: { "line-width": 0.8 } });
    map.addLayer({ id: "done", type: "line", source: "done", layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-width": 4.2 } });
    map.addLayer({ id: "ticks", type: "line", source: "ticks", paint: { "line-width": 1.5 } });
    map.addLayer({ id: "tick-on", type: "line", source: "ticks", filter: ["==", ["get", "id"], ""], paint: { "line-width": 4.2 } });
    map.addLayer({ id: "here-halo", type: "circle", source: "here", paint: { "circle-radius": 9, "circle-opacity": 0.9 } });
    map.addLayer({ id: "here", type: "circle", source: "here", paint: { "circle-radius": 5 } });
    // a frame's tick: click to go to it
    map.on("click", "ticks", (e) => { const t = e.features?.[0]?.properties?.t; if (t != null) seek(st, Number(t), true); });
    map.on("mouseenter", "ticks", () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", "ticks", () => { map.getCanvas().style.cursor = ""; });
    // A and B, and each cut's unseen stretch, as small labels on the map
    const label = (lonlat, html, cls) => {
      const el = Object.assign(document.createElement("div"), { className: `tm-label ${cls}`, innerHTML: html });
      return new gl.Marker({ element: el, anchor: "bottom" }).setLngLat(lonlat).addTo(map);
    };
    st.fixed = [
      label([tr.start.lon, tr.start.lat], `<b>A</b> start · ${clock(tr.segments[0].video_start)}`, "end"),
      label([tr.end.lon, tr.end.lat], `<b>B</b> end · ${clock(tr.duration_s)}`, "end"),
      ...tr.segments.slice(1).map((s, k) => {
        const prev = tr.segments[k], mid = lerpAlong(r, (prev.along_end_m + s.along_start_m) / 2);
        const gap = Math.round((new Date(s.clock_start) - new Date(prev.clock_end)) / 60000);
        return label(mid, `not filmed · ${gap} min · ${km(s.along_start_m - prev.along_end_m)}`, "cut");
      }),
    ];
    st.ready = true;
    st.gl = gl;
    paint(st);
    update(st, true);
    addPlanes(st);
  });
}

function boundsOf(coords) {
  let w = 180, s = 90, e = -180, n = -90;
  for (const [x, y] of coords) { w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); n = Math.max(n, y); }
  return [[w, s], [e, n]];
}

function overview(st) {
  if (!st.map) return;
  const b = boundsOf(st.track.route.coordinates);
  st.map.fitBounds(b, { padding: OVERVIEW_PAD, pitch: OVERVIEW_PITCH, bearing: -20, duration: reduced() ? 0 : 1200 });
}

function setBase(st, base) {
  st.base = base;
  for (const b of st.main.querySelectorAll(".tmap-tools button[data-base]")) b.classList.toggle("set", b.dataset.base === base);
  st.main.querySelector(".tmap").classList.toggle("sat", base === "sat");
  paint(st);
}

// colours follow the theme (and turn white on the satellite image)
function paint(st) {
  const map = st.map;
  if (!map || !st.ready) return;
  const dark = isDark(), sat = st.base === "sat", p = palette(st);
  map.setLayoutProperty("osm", "visibility", sat ? "none" : "visible");
  // grey street map; for dark, swapping the brightness range inverts it
  map.setPaintProperty("osm", "raster-brightness-min", dark ? 0.92 : 0);
  map.setPaintProperty("osm", "raster-brightness-max", dark ? 0.08 : 1);
  map.setLayoutProperty("sat", "visibility", sat ? "visible" : "none");
  map.setLayoutProperty("satlabels", "visibility", sat ? "visible" : "none");
  map.setPaintProperty("route-halo", "line-color", p.halo);
  map.setPaintProperty("route-halo", "line-opacity", sat ? 0.35 : 0.8);
  map.setPaintProperty("unfilmed-halo", "line-color", p.halo);
  map.setPaintProperty("unfilmed-halo", "line-opacity", sat ? 0.35 : 0.8);
  map.setPaintProperty("unfilmed", "line-color", p.muted);
  map.setPaintProperty("filmed", "line-color", p.muted);
  map.setPaintProperty("band", "line-color", p.ink);
  map.setPaintProperty("band", "line-opacity", 0.16);
  map.setPaintProperty("cone", "fill-color", p.ink);
  map.setPaintProperty("cone", "fill-opacity", 0.09);
  map.setPaintProperty("cone-edge", "line-color", p.ink);
  map.setPaintProperty("cone-edge", "line-opacity", 0.35);
  map.setPaintProperty("done", "line-color", p.ink);
  map.setPaintProperty("ticks", "line-color", p.ink);
  map.setPaintProperty("ticks", "line-opacity", 0.55);
  map.setPaintProperty("tick-on", "line-color", p.ink);
  map.setPaintProperty("here-halo", "circle-color", p.halo);
  map.setPaintProperty("here", "circle-color", p.ink);
  paintPlanes(st);
}

// ------------------------------------------------------------ every frame

function update(st, force = false) {
  const tr = st.track;
  if (!tr) return;
  const now = at(tr, st.t), seg = segmentAt(tr, st.t), L = tr.route.length_m;
  if (!force && st.drawnT === st.t) return;
  st.drawnT = st.t;
  // panel readout
  const s = tr.segments[seg];
  if (st.ui) {
    st.ui.t.textContent = `${clock(st.t)} / ${clock(tr.duration_s)}`;
    st.ui.clock.textContent = s ? new Date(new Date(s.clock_start).getTime() + (st.t - s.video_start) * 1000).toTimeString().slice(0, 8) +
      ` · stretch ${seg + 1} of ${tr.segments.length}` : "before the drive (the uploader's route map)";
    st.ui.along.innerHTML = `${km(now.along)} of ${km(L)} <span class="muted">± ${km(now.sigma)}</span>`;
    st.ui.heading.textContent = `${compass(now.heading)} · ${Math.round(now.heading)}°`;
  }
  // scrubber + chart
  if (st.scrubEl) {
    st.scrubEl.style.setProperty("--x", st.t / tr.duration_s);
    st.scrubEl.querySelector(".now").textContent = clock(st.t);
    if (st.mareyXY) {
      const x = st.mareyXY.X(st.t), y = st.mareyXY.Y(now.along);
      st.mareyNow.setAttribute("x1", x); st.mareyNow.setAttribute("x2", x);
      st.mareyDot.setAttribute("cx", x); st.mareyDot.setAttribute("cy", y);
    }
  }
  if (!st.map || !st.ready) return;
  const map = st.map, r = tr.route;
  // travelled: the filmed road up to here
  // (only stretches the dot has reached: one it hasn't would run from its start back to the dot, across the cut)
  const done = tr.segments.filter((x) => x.video_start <= st.t && now.along > x.along_start_m)
    .map((x) => slice(r, x.along_start_m, Math.min(x.along_end_m, now.along)));
  map.getSource("done").setData(fc([multi(done)]));
  map.getSource("band").setData(fc([line(slice(r, Math.max(0, now.along - now.sigma), Math.min(L, now.along + now.sigma)))]));
  const cone = [now.lonlat];
  for (let a = -CONE_DEG; a <= CONE_DEG; a += 5) cone.push(offset(now.lonlat, now.heading + a, CONE_M));
  cone.push(now.lonlat);
  map.getSource("cone").setData(fc([{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [cone] } }]));
  map.getSource("here").setData(fc([{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: now.lonlat } }]));
  frames(st);
  // the camera: follow the dot, turning with the road; fly over a cut rather than snapping across it
  if (st.follow && !st.scrubbing) {
    const cutJump = st.lastCut !== undefined && seg !== st.lastCut && st.playing;
    st.bearing = st.bearing == null ? now.heading : st.bearing + angleDiff(now.heading, st.bearing) * (st.ride ? RIDE_TURN : 0.04);
    if (cutJump) {
      st.bearing = now.heading;
      glide(st, 1600);
      map.flyTo({ center: now.lonlat, bearing: now.heading, ...camera(st), duration: reduced() ? 0 : 1600, essential: true });
    } else if (performance.now() > st.glideUntil) {
      map.jumpTo({ center: now.lonlat, bearing: st.bearing });
    }
  } else if (st.follow && st.scrubbing) {
    // dragging the timeline: the same camera as playing (heading, and riding's tilt and zoom), snapped rather than
    // eased so it keeps up with the drag; easing picks up from here when the drag ends
    st.bearing = now.heading;
    map.stop();
    map.jumpTo({ center: now.lonlat, bearing: now.heading, ...(st.ride ? camera(st) : {}) });
  }
  st.lastCut = seg;
}
// the following camera's tilt and zoom: riding along, or Follow (the viewer's zoom, held between 13 and 14.8, so
// leaving Ride along also lifts the camera back out)
const camera = (st) => (st.ride ? { pitch: RIDE_PITCH, zoom: RIDE_ZOOM }
                                : { pitch: FOLLOW_PITCH, zoom: Math.min(14.8, Math.max(13, st.map.getZoom())) });
const angleDiff = (a, b) => ((a - b + 540) % 360) - 180;
// while the camera eases somewhere on its own (into Follow, over a cut), following waits for it
function glide(st, ms) { st.glideUntil = performance.now() + (reduced() ? 0 : ms); }

// The frames as objects on the map: each a thin upright plane standing on the road where the track puts the camera
// when it was taken, square to the road (facing back along it, so looking down the road you see the image as the
// dashcam saw it). Seen at an angle they foreshorten, and in a row they stack into a block, like a video given volume:
// the current frame is solid and outlined; the frames still to come recede ahead of it, fainter with time; passed
// frames drop away while following (they would stand between the view and the dot), and stay faint otherwise.
// Drawn by three.js in a MapLibre custom layer, in metres around a local origin.
const THREE_URL = "https://unpkg.com/three@0.160.0/build/three.module.js";
const PLANE_PX = 230;                   // a frame's width on screen at the follow zoom ...
const PLANE_M = [150, 900];             // ... held within these widths in metres, so it stays an object of the place
const AHEAD_S = 150;                    // frames up to this far ahead stand in the stack
const ALL_ALPHA = 0.55;                 // with All frames on, every frame but the current one
let threePromise = null;
const loadThree = () => (threePromise ??= import(THREE_URL).catch((e) => { threePromise = null; throw e; }));

async function addPlanes(st) {
  let THREE;
  try { THREE = await loadThree(); } catch { return; } // offline: the ticks still mark the frames
  if (state !== st || !st.map) return;
  const gl = st.gl, map = st.map, tr = st.track;
  const mid = tr.route.coordinates[Math.floor(tr.route.coordinates.length / 2)];
  const oc = gl.MercatorCoordinate.fromLngLat(mid, 0), u = oc.meterInMercatorCoordinateUnits();
  const scene = new THREE.Scene(), camera = new THREE.Camera();
  // a 16:9 plane, 1 unit wide, standing on its bottom edge; x east, y up, z south (see `world` below)
  const geo = new THREE.PlaneGeometry(1, 9 / 16).translate(0, 9 / 32, 0);
  const edges = new THREE.EdgesGeometry(geo);
  const loader = new THREE.TextureLoader();
  st.planes = tr.frames.filter((f) => f.thumb_url).map((f) => {
    const tex = loader.load(f.thumb_url, () => map.triggerRepaint());
    tex.colorSpace = THREE.SRGBColorSpace;
    const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false }));
    const outline = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
    const g = new THREE.Group();
    g.add(mesh, outline);
    const c = gl.MercatorCoordinate.fromLngLat([f.lon, f.lat], 0);
    g.position.set((c.x - oc.x) / u, 0, (c.y - oc.y) / u);
    g.rotation.y = (-headingAt(tr.route, f.along_m) * Math.PI) / 180; // face back along the road
    g.visible = false;
    scene.add(g);
    return { f, g, mesh, outline };
  });
  // scene metres -> map: translate to the origin, scale to mercator units (mercator y runs south), stand y up
  const world = new THREE.Matrix4().makeTranslation(oc.x, oc.y, oc.z)
    .scale(new THREE.Vector3(u, -u, u)).multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
  map.addLayer({
    id: "frames3d", type: "custom", renderingMode: "3d",
    onAdd(m, ctx) {
      this.renderer = new THREE.WebGLRenderer({ canvas: m.getCanvas(), context: ctx, antialias: true });
      this.renderer.autoClear = false;
    },
    render(ctx, matrix) {
      // the planes keep a readable size as the map zooms, within PLANE_M
      const mpp = (40075016.686 * Math.cos((mid[1] * Math.PI) / 180)) / (512 * 2 ** map.getZoom());
      const w = Math.min(PLANE_M[1], Math.max(PLANE_M[0], PLANE_PX * mpp));
      for (const p of st.planes) p.g.scale.setScalar(w);
      camera.projectionMatrix = new THREE.Matrix4().fromArray(matrix).multiply(world);
      this.renderer.resetState();
      this.renderer.render(scene, camera);
    },
  }, "here-halo"); // under the dot
  st.caption = new gl.Marker({ element: Object.assign(document.createElement("div"), { className: "tm-label tm-cap" }), anchor: "top" });
  paintPlanes(st);
  update(st, true);
}

function paintPlanes(st) {
  const ink = palette(st).ink;
  for (const p of st.planes ?? []) p.outline.material.color.set(ink);
  st.map?.triggerRepaint();
}

function frames(st) {
  const tr = st.track;
  const current = tr.frames.filter((f) => f.t <= st.t + 0.05).at(-1);
  st.map.setFilter("tick-on", ["==", ["get", "id"], current?.frame_id ?? ""]);
  if (!st.planes) return;
  for (const p of st.planes) {
    const dt = p.f.t - st.t;
    let a, line;
    if (p.f === current) { a = 1; line = 0.9; }
    else if (st.allFrames) { a = ALL_ALPHA; line = 0.5; }                                              // All frames
    else if (dt > 0) { a = dt > AHEAD_S ? 0 : 0.06 + 0.3 * (1 - dt / AHEAD_S) ** 2; line = a * 0.8; } // ahead: the stack
    else { a = st.follow ? 0 : 0.18; line = a; }                                                       // passed
    p.g.visible = a > 0.01;
    p.mesh.material.opacity = a;
    p.outline.material.opacity = line;
    p.mesh.renderOrder = p.f === current ? 2 : 1;
  }
  if (current) {
    st.caption.getElement().textContent = `${clock(current.t)} · ${km(current.along_m)} ± ${km(current.sigma_m)}`;
    st.caption.getElement().title = current.onscreen_text?.length ? `On screen: ${current.onscreen_text.join(" / ")}` : "";
    st.caption.setLngLat([current.lon, current.lat]).addTo(st.map);
  } else st.caption.remove();
  st.map.triggerRepaint();
}
