// Satellite (bottom left, beside Video): a form in the panel that adds satellite passes along a power line to "The
// Conductive Seam" and renders its film. Held like Video. Jobs run on the local server in the same line as video jobs
// (/api/satellite/jobs, /api/seam/films; satellite/ in the package), polled at /api/jobs/{id}.
// - Area: a study area of config/conductive-seam.yaml, or a corridor already made (to add another date), or a new one
//   (a box, then the OpenStreetMap power lines in it to follow). A corridor's box, lines and grid never change once
//   made, so every pass, of any year, lies on the same grid and the film's camera path fits them all.
// - Fetch: the clearest pass of the sensor between the dates that covers the whole corridor.
// - Film: the corridor's passes, oldest first: one overhead travelling shot, dissolving between them at held stops.

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
  .then(async (r) => { const d = await r.json(); if (!r.ok) throw new Error(d.detail ?? r.status); return d; });
const km = (m) => `${(m / 1000).toFixed(1)} km`;
const slug = (s) => s.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40);

let setup = null, form = null, timer = null, hooks = {};

export function buildSatelliteForm(h) {
  hooks = h;
  const f = form = document.createElement("form");
  f.className = "addvideo satellite";
  f.noValidate = true;
  f.innerHTML = `
    <div class="head"><select id="s-area" class="title" aria-label="Area"></select></div>
    <dl class="settings">
      <dt class="new">Name</dt><dd class="new"><input id="s-name" placeholder="a new corridor" autocomplete="off" spellcheck="false"></dd>
      <dt class="new">Box</dt><dd class="new"><input id="s-bbox" placeholder="west, south, east, north" autocomplete="off" spellcheck="false"></dd>
      <dt class="new"></dt><dd class="new"><button type="button" id="s-find" class="link">Find power lines</button></dd>
      <dt>Line</dt><dd id="s-line" class="line"></dd>
      <dt><label for="s-sensor">Sensor</label></dt><dd><select id="s-sensor"></select></dd>
      <dt>Between</dt><dd class="range"><input id="s-start" type="date" aria-label="From"><span>–</span><input id="s-end" type="date" aria-label="Until"></dd>
      <dt><label for="s-cloud">Max cloud</label></dt><dd class="unit"><input id="s-cloud" type="number" min="0" max="100" step="1"><span>%</span></dd>
      <dt>Save to</dt><dd id="s-folder"></dd>
    </dl>
    <p class="small" id="s-note"></p>
    <p><button id="s-fetch" type="submit" class="go">Fetch the clearest pass</button></p>
    <div id="s-film" hidden>
      <h3 class="tm-h">Film</h3>
      <dl class="settings">
        <dt>Passes</dt><dd id="s-passes" class="passes"></dd>
        <dt><label for="s-view">View</label></dt><dd class="unit"><input id="s-view" type="number" min="1" max="30" step="0.5"><span>km wide</span></dd>
        <dt><label for="s-speed">Speed</label></dt><dd class="unit"><input id="s-speed" type="number" min="10" max="2000" step="10"><span>m a second</span></dd>
        <dt></dt><dd><label class="check"><input id="s-trace" type="checkbox"> Draw the line (OpenStreetMap)</label></dd>
      </dl>
      <p><button id="s-make" type="button" class="go">Make film</button></p>
    </div>
    <div id="s-job" class="small" aria-live="polite"></div>`;
  const q = (id) => f.querySelector("#" + id);
  q("s-area").addEventListener("change", showArea);
  q("s-name").addEventListener("input", showArea);
  q("s-find").addEventListener("click", findLines);
  f.addEventListener("submit", (e) => { e.preventDefault(); fetchPass(); });
  q("s-make").addEventListener("click", makeFilm);
  return f;
}

export async function refreshSatelliteForm() {
  if (!form) return;
  try { setup = await (await fetch("/api/satellite/setup")).json(); } catch { setup = null; }
  if (!setup || !form.isConnected) {
    if (form.isConnected) $("s-note").textContent = "The server doesn't know the Satellite panel yet: restart it (evidence serve).";
    return;
  }
  const sel = $("s-area"), keep = sel.value;
  const made = new Set(setup.corridors.map((c) => c.corridor_id));
  sel.innerHTML = setup.corridors.map((c) => `<option value="${esc(c.corridor_id)}">${esc(c.name)}</option>`).join("") +
    setup.areas.filter((a) => !made.has(a.id)).map((a) => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join("") +
    `<option value="__new">New area…</option>`;
  sel.value = [...sel.options].some((o) => o.value === keep) ? keep : sel.options[0].value;
  $("s-sensor").innerHTML = setup.sensors.map((x) => `<option value="${esc(x.name)}">${esc(x.label)} · ${x.gsd_m} m · from ${x.first_year}</option>`).join("");
  $("s-sensor").value ||= setup.fetch.sensor ?? "sentinel-2";
  $("s-start").value ||= setup.fetch.start ?? "2023-07-01";
  $("s-end").value ||= setup.fetch.end ?? "2023-09-30";
  $("s-cloud").value ||= setup.fetch.max_cloud ?? 5;
  $("s-view").value ||= (setup.film.view_m ?? 6000) / 1000;
  $("s-speed").value ||= setup.film.speed_mps ?? 150;
  $("s-trace").checked = !!setup.film.trace;
  $("s-folder").textContent = setup.folder.title;
  showArea();
  if (!timer) {
    const last = (await fetch("/api/jobs").then((r) => r.json()).catch(() => [])).filter((j) => j.kind === "satellite" || j.kind === "film").at(-1);
    if (last) showJob(last);
    if (last && (last.status === "running" || last.status === "queued")) watch(last.id);
  }
}

const corridorOf = (id) => setup?.corridors.find((c) => c.corridor_id === id);
const areaOf = (id) => setup?.areas.find((a) => a.id === id);

// The chosen area: what it follows, how many passes it has, and (a corridor already made) its film's passes.
function showArea() {
  if (!setup) return;
  const id = $("s-area").value, c = corridorOf(id), a = areaOf(id), isNew = id === "__new";
  for (const el of form.querySelectorAll(".new")) el.hidden = !isNew;
  const note = $("s-note");
  if (c) {
    $("s-line").innerHTML = `${esc(c.line)}<span class="note">${km(c.length_m)} · OpenStreetMap · fixed with the corridor</span>`;
    note.textContent = c.passes.length
      ? `${c.passes.length} pass${c.passes.length === 1 ? "" : "es"} so far: ${c.passes.map((p) => p.title).join(", ")}. Another date lands on the same grid.`
      : "No pass yet.";
  } else if (a) {
    $("s-line").innerHTML = `OpenStreetMap way${a.lines.length === 1 ? "" : "s"} ${a.lines.map(esc).join(", ")}<span class="note">joined end to end; the corridor is made with the first pass</span>`;
    note.textContent = a.note || "";
  } else if (isNew && !$("s-line").querySelector("input")) {
    $("s-line").innerHTML = `<span class="muted">a box, then Find power lines</span>`;
    note.textContent = "A corridor's box and lines are fixed once it is made. Keep the line at least 3.5 km inside the box, so a turned frame stays on the imagery.";
  }
  const film = $("s-film");
  film.hidden = !c?.passes.length;
  if (c) {
    $("s-passes").innerHTML = c.passes.map((p) => `<label class="check"><input type="checkbox" value="${esc(p.pass_id)}" checked> ${esc(p.title)}</label>`).join("");
  }
}

async function findLines() {
  const box = $("s-bbox").value.split(/[\s,]+/).filter(Boolean).map(Number);
  if (box.length !== 4 || box.some(isNaN)) { $("s-note").textContent = "The box is four numbers: west, south, east, north (degrees)."; return; }
  $("s-line").innerHTML = `<span class="muted">Asking OpenStreetMap…</span>`;
  try {
    const r = await fetch(`/api/satellite/lines?bbox=${box.join(",")}`);
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail ?? r.status);
    $("s-line").innerHTML = d.length ? d.slice(0, 40).map((x) =>
      `<label class="check"><input type="checkbox" value="${x.id}"> ${esc(x.label)} <span class="muted">· ${km(x.length_m)}</span></label>`).join("")
      + `<span class="note">ticked lines are joined end to end in this order</span>` : `<span class="muted">No line of 110 kV or more in the box.</span>`;
  } catch (e) {
    $("s-line").innerHTML = `<span class="muted">${esc(e.message)}</span>`;
  }
}

async function fetchPass() {
  const id = $("s-area").value;
  let area = id;
  if (id === "__new") {
    const name = $("s-name").value.trim(), lines = [...$("s-line").querySelectorAll("input:checked")].map((x) => +x.value);
    const bbox = $("s-bbox").value.split(/[\s,]+/).filter(Boolean).map(Number);
    if (!name || bbox.length !== 4 || !lines.length) { $("s-job").textContent = "Name the area, give its box and tick a line."; return; }
    area = { corridor_id: slug(name), name, bbox, lines };
  }
  $("s-fetch").disabled = true;
  try {
    const job = await post("/api/satellite/jobs", { area, sensor: $("s-sensor").value, start: $("s-start").value, end: $("s-end").value, max_cloud: +$("s-cloud").value });
    showJob(job);
    watch(job.id);
  } catch (e) {
    $("s-job").textContent = `Couldn't start: ${e.message}`;
  } finally {
    $("s-fetch").disabled = false;
  }
}

async function makeFilm() {
  const passes = [...$("s-passes").querySelectorAll("input:checked")].map((x) => x.value);
  if (!passes.length) { $("s-job").textContent = "Tick at least one pass."; return; }
  $("s-make").disabled = true;
  try {
    const job = await post("/api/seam/films", { corridor_id: $("s-area").value, passes,
      options: { view_m: +$("s-view").value * 1000, speed_mps: +$("s-speed").value, trace: $("s-trace").checked } });
    showJob(job);
    watch(job.id);
  } catch (e) {
    $("s-job").textContent = `Couldn't start: ${e.message}`;
  } finally {
    $("s-make").disabled = false;
  }
}

function watch(id) {
  clearInterval(timer);
  timer = setInterval(async () => {
    let job;
    try { job = await (await fetch(`/api/jobs/${id}`)).json(); } catch { return; }
    showJob(job);
    if (job.status === "done" || job.status === "failed") {
      clearInterval(timer);
      timer = null;
      if (job.status === "done" && job.kind === "satellite") { hooks.added?.(job); refreshSatelliteForm(); }
    }
  }, 2000);
}

function showJob(job) {
  const box = $("s-job");
  if (!box) return;
  const head = { queued: "Waiting…", running: "Working…", done: "Done", failed: "Stopped" }[job.status];
  const rows = job.results.map((r) => `<li>${r.status === "processed" ? (job.kind === "film" ? "made" : "added") : "none"} · ${esc(r.title)}` +
    (r.frames ? ` · ${r.frames} images` : "") + (r.reason ? `<span class="note">${esc(r.reason)}</span>` : "") + "</li>").join("");
  const done = job.status === "done";
  const links = done && job.kind === "film" ? `<p><a href="#" data-seam>Watch in The Conductive Seam</a></p>`
    : done && job.kind === "satellite" && hooks.currentLib?.() !== job.library ? `<p><a href="#" data-lib="${esc(job.library)}">Show “${esc(job.folder)}”</a></p>` : "";
  box.innerHTML = `<p><b>${head}</b> · ${esc(job.kind === "film" ? "film" : "satellite pass")} · ${esc(job.folder)}${job.error ? `<span class="note">${esc(job.error)}</span>` : ""}</p>` +
    (rows ? `<ul class="results">${rows}</ul>` : "") + links +
    (done || job.status === "failed" ? "" : `<pre class="log">${esc(job.log.slice(-6).join("\n"))}</pre>`);
  box.querySelector("[data-seam]")?.addEventListener("click", (e) => { e.preventDefault(); hooks.watchFilm?.(); });
}
