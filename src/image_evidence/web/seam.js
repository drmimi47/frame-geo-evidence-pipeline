// The Conductive Seam (the view after Scene Viewer): the films rendered from the satellite passes along a power line
// (/api/seam/films; satellite/film.py), on a black ground whatever the theme. Under the film a thin strip says what
// each stretch of it is: observed (one pass, resampled: solid), a dissolve between two passes (an interpolation
// between two dates, never a date of its own: hatched); the part played lights up as the playhead moves along it, and
// a click or drag seeks.
// Under the strip, the film's notes (film.json `notes`, satellite/notes.py): a line or two of context at a time (what
// the plant is, how many lines it had, what happened when), each with its sources; text beside the film, not read from
// the imagery. The left panel follows the playhead: which pass is shown, where the camera is on the line, and the
// film's sources.
// Click the film or press Space to play and pause, ← → to step 5 s. It takes over main and #research, like the Scene
// Viewer.

let state = null; // { video, raf, onKey, film }
let pendingStart = null; // a time to start at (a film frame's "Play the film from here")

export function seamStart(filmId, t) {
  try { localStorage.setItem("seamFilm", filmId); } catch {}
  pendingStart = t;
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const clock = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;
const km = (m) => `${(m / 1000).toFixed(1)} km`;
const day = (iso) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

export function leaveSeam() {
  if (!state) return;
  cancelAnimationFrame(state.raf);
  removeEventListener("keydown", state.onKey, true);
  state.video?.pause();
  state.video?.removeAttribute("src");
  state.video?.load(); // let go of the file
  state = null;
}

export async function renderSeam(main, research, { openSatellite } = {}) {
  leaveSeam();
  const st = state = {};
  main.replaceChildren();
  research.innerHTML = `<p class="empty">Loading…</p>`;
  let films;
  try {
    const r = await fetch("/api/seam/films");
    if (!r.ok) throw new Error(r.status);
    films = await r.json();
  } catch {
    if (state === st) research.innerHTML = `<div class="tm-empty"><p>The server doesn't know The Conductive Seam yet.</p>
      <p class="small muted">Restart it (<code>evidence serve</code>) and reload this page.</p></div>`;
    return;
  }
  if (state !== st) return;
  if (!films.length) {
    research.innerHTML = `<div class="tm-empty"><p>No film yet: make one in Satellite.</p>
      <p class="tm-transport"><button type="button" id="seam-open">Open Satellite</button></p></div>`;
    research.querySelector("#seam-open").onclick = () => openSatellite?.();
    main.innerHTML = `<div class="seam-view"></div>`;
    return;
  }
  let pick;
  try { pick = localStorage.getItem("seamFilm"); } catch {}
  const film = st.film = films.find((f) => f.film_id === pick) ?? films[0];
  panel(st, research, films, film);
  view(st, main, research, film);
}

function panel(st, research, films, f) {
  // The picker is the title, so it names the film (a select can't wrap); the rest goes in the line under it.
  const made = (x) => x.created_at.slice(0, 16).replace("T", " ");
  const twin = (x) => films.some((y) => y !== x && y.corridor === x.corridor);
  const pick = films.length > 1 ? `<select class="tm-pick" id="seam-pick">${films.map((x) =>
    `<option value="${esc(x.film_id)}"${x.film_id === f.film_id ? " selected" : ""}>${esc(x.corridor)}${twin(x) ? ` · ${esc(made(x).slice(5))}` : ""}</option>`).join("")}</select>` : "";
  const about = `${f.passes.length} pass${f.passes.length === 1 ? "" : "es"}${f.options.trace ? " · line drawn" : ""} · made ${made(f)}`;
  const passes = f.passes.map((p) => `<li>${esc(p.title)} <span class="muted">· ${p.gsd_m} m · ${(p.cloud_share * 100).toFixed(1)}% cloud</span>
    <span class="note">${p.item_ids.map((id, k) => `<a href="${esc(p.item_urls[k])}" target="_blank" rel="noopener">${esc(id)}</a>`).join("<br>")}</span></li>`).join("");
  research.innerHTML = `
    <div class="head">
      ${pick || `<div class="title">${esc(f.corridor)}</div>`}
      <div class="sub">${esc(f.line.label)} · ${km(f.line.length_m)} · ${clock(f.duration_s)} · ${esc(about)}</div>
    </div>
    <p class="tm-transport"><button type="button" id="seam-play">Play</button>
      <a href="${esc(f.urls.contact)}" target="_blank">Contact sheet</a><a href="${esc(f.urls.video)}" download>Download</a></p>
    <dl class="fields tm-now">
      <dt>Shown</dt><dd id="seam-shown"></dd>
      <dt>Along</dt><dd id="seam-along"></dd>
      <dt>Camera</dt><dd id="seam-cam"></dd>
    </dl>
    <p class="seam-legend"><span><i class="obs"></i>observed: one pass, resampled</span><span><i class="dis"></i>dissolve: two dates mixed</span>${f.insets?.length ? `<span><i class="ins"></i>inset: a supplied image on top</span>` : ""}</p>
    <p class="tm-summary">${esc(f.statement)}${f.notes?.length ? ` ${esc(f.notes_statement)}` : ""}</p>
    <h3 class="tm-h">Passes</h3><ul class="tm-list seam-passes">${passes}</ul>
    <dl class="fields tm-prov">${f.provenance.map((p) => `<dt>${esc(p.label)}</dt><dd>${esc(p.evidence)}</dd>`).join("")}
      <dt>Record</dt><dd><a href="${esc(f.urls["video"].replace(/film\.mp4$/, "film.json"))}" target="_blank">film.json</a><span class="note">every segment's passes and weights, the camera each second; sha256 ${esc(f.sha256.slice(0, 16))}…</span></dd>
    </dl>
    <p class="small muted tm-credit">${esc([...new Set(f.passes.map((p) => p.attribution))].join(" · "))}</p>`;
  research.querySelector("#seam-pick")?.addEventListener("change", (e) => {
    try { localStorage.setItem("seamFilm", e.target.value); } catch {}
    renderSeam(document.getElementById("main"), research);
  });
}

function view(st, main, research, f) {
  const dur = f.duration_s;
  main.innerHTML = `
    <div class="seam-view">
      <video class="seam-film" playsinline preload="auto" poster="${esc(f.urls.poster)}" src="${esc(f.urls.video)}"></video>
      <div class="seam-strip" title="What each stretch of the film is: solid observed, hatched a dissolve between two dates">
        ${f.segments.map((s) => `<i class="${s.kind === "dissolve" ? "dis" : s.shot === "inset" ? "ins" : "obs"}" style="left:${(s.t0 / dur) * 100}%;width:${((s.t1 - s.t0) / dur) * 100}%"></i>`).join("")}
        <b class="done"></b><b class="playhead"></b>
      </div>
      ${f.notes?.length ? `<div class="seam-note" aria-live="polite"><p></p><span class="src"></span></div>` : ""}
    </div>`;
  const video = st.video = main.querySelector("video"), strip = main.querySelector(".seam-strip");
  const noteEl = main.querySelector(".seam-note");
  let noteOn = null, noteTimer = 0;
  if (pendingStart != null) {
    const at = pendingStart;
    pendingStart = null;
    video.addEventListener("loadedmetadata", () => { video.currentTime = Math.min(dur, at); show(); }, { once: true });
  }
  // the note under the film: the old one fades out, the new one in
  function showNote(t) {
    if (!noteEl) return;
    const n = f.notes.find((x) => x.t0 <= t && t < x.t1) ?? null;
    if (n === noteOn) return;
    noteOn = n;
    clearTimeout(noteTimer);
    noteEl.classList.add("out");
    noteTimer = setTimeout(() => {
      noteEl.querySelector("p").textContent = n?.text ?? "";
      noteEl.querySelector(".src").innerHTML = n ? n.sources.map((x) => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a>`).join(" · ") : "";
      if (n) noteEl.classList.remove("out");
    }, 220);
  }
  const play = research.querySelector("#seam-play");
  const toggle = () => { if (video.paused) video.play().catch(() => {}); else video.pause(); };
  video.addEventListener("click", toggle);
  play.addEventListener("click", toggle);
  video.addEventListener("play", () => { play.textContent = "Pause"; tick(); });
  video.addEventListener("pause", () => { play.textContent = "Play"; show(); });
  video.addEventListener("seeked", show);
  video.addEventListener("ended", () => { play.textContent = "Play again"; });
  const seek = (e) => {
    const r = strip.getBoundingClientRect();
    video.currentTime = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)) * dur;
    show();
  };
  strip.addEventListener("pointerdown", (e) => { strip.setPointerCapture(e.pointerId); seek(e); });
  strip.addEventListener("pointermove", (e) => { if (e.buttons) seek(e); });
  st.onKey = (e) => {
    if (e.target.matches?.("input, select, textarea") || e.metaKey || e.ctrlKey) return;
    if (e.key === " ") { e.preventDefault(); toggle(); }
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      video.currentTime = Math.min(dur, Math.max(0, video.currentTime + (e.key === "ArrowRight" ? 5 : -5)));
    }
  };
  addEventListener("keydown", st.onKey, true);

  const cam = f.camera, fi = Object.fromEntries(cam.fields.map((k, i) => [k, i]));
  const titles = Object.fromEntries(f.passes.map((p) => [p.pass_id, p]));
  function show() {
    if (state !== st) return;
    const t = video.currentTime || 0;
    strip.style.setProperty("--x", t / dur);
    showNote(t);
    const seg = f.segments.find((s) => t < s.t1) ?? f.segments.at(-1);
    // the camera sample just before t, and the next (one a second)
    const k = Math.max(0, Math.min(cam.samples.length - 1, cam.samples.findIndex((s) => s[0] > t) - 1));
    const a = cam.samples[k] ?? cam.samples.at(-1), b = cam.samples[k + 1] ?? a;
    const w = b[0] > a[0] ? Math.min(1, Math.max(0, (t - a[0]) / (b[0] - a[0]))) : 0;
    const at = (name) => a[fi[name]] + (b[fi[name]] - a[fi[name]]) * w;
    if (seg.kind === "dissolve") {
      const [p, q] = seg.passes.map((x) => titles[x.pass_id]);
      const mix = Math.round(at("dissolve_weight") * 100);
      research.querySelector("#seam-shown").innerHTML = `Dissolve, ${esc(day(p.acquired_at))} → ${esc(day(q.acquired_at))} (${mix}% the later)` +
        `<span class="note">interpolated: two passes mixed, not imagery of any date between them</span>`;
    } else {
      const p = titles[seg.passes[0].pass_id];
      const ins = seg.inset && (f.insets || []).find((z) => z.image === seg.inset);
      const on = ins && t >= ins.shown_s[0] && t < ins.shown_s[1] ? `; on top, a supplied image (${esc(ins.source)}), placed by ${ins.pins.length} OpenStreetMap towers: not satellite imagery from these passes` : "";
      research.querySelector("#seam-shown").innerHTML = `${esc(p.title)}<span class="note">observed: this pass, resampled${seg.shot === "track" ? "; the camera moves over one still moment" : ""}${on}</span>`;
    }
    const before = seg.shot === "open" || seg.shot === "pan";  // the opening: on the plants, not yet on the line
    research.querySelector("#seam-along").textContent = `${before ? "Before the line, at the plants" : `${km(at("along_m"))} of ${km(f.line.length_m)}`} · ${clock(t)} of ${clock(dur)}`;
    research.querySelector("#seam-cam").innerHTML = `${at("lat").toFixed(4)} N, ${at("lon").toFixed(4)} E · heading ${Math.round(a[fi.heading_deg])}°` +
      `<span class="note">${at("m_per_px").toFixed(1)} m a pixel · ${(at("m_per_px") * f.width / 1000).toFixed(1)} km across; a path along the line, not where anything was observed from</span>`;
  }
  function tick() {
    show();
    if (!video.paused && state === st) st.raf = requestAnimationFrame(tick);
  }
  show();
}
