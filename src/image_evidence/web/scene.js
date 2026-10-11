// Scene Viewer: 3D reconstructions made from a video's own footage (`derived/scene/`, /api/videos/{id}/scene), shown
// like a 3D viewer: one take at a time on a dark ground, orbited with the pointer, with a ring where the camera stood
// each second. A Gaussian splat (Spark, a three.js renderer) when one was trained, else the reconstruction's points.
// Clicking a ring flies to that camera, so the place is seen as the footage saw it; Previous/Next view step through a
// take's chosen views (scene.json `views`: moments in the video, each seen from a few metres behind and above where
// the camera stood, looking where it looked, so it can be found in the footage), else through every camera. It takes
// over main and #research, like the Route Map. three.js and Spark come from the import map in index.html.
let state = null; // the shown scene: { renderer, raf, ... }; renderScene replaces it, leaveScene clears it
const FLY_MS = 900;
const INTRO_MS = 4200; // on load: from far out, in to the take's opening camera (`open_t`)
const INTRO_FAR = 3.2; // how many times the overview's distance it starts from
const INTRO_HOLD_MS = 700; // a still moment far out first, while the splats are drawn for the first time
const RING_EVERY_S = 1; // a ring per second of footage, so a take reads as a dotted path
// the land around a take (`terrain.json`, scripts/scene/terrain.py): on load the view starts over the whole area, the
// land fades in as the flight starts, and the flight comes down to the take, its distance shrinking at an even rate
const LAND_MS = 9000;
const LAND_FADE_MS = 1800;
const LAND_TILT = 36; // degrees above the horizon the whole area is seen from
const LAND_SWING = 60; // at most this far round from north it looks (from the south-east or south-west), so the map is never upside down
const LAND_LINES_M = [40, 220]; // the view's distance over which the lines come in
const LAND_SINK = 0.3; // m the land is set below the take's ground
const LAND_CONTOURS = true; // contour lines on the land
const LAND_MAP = 0.75; // how strongly the Route Map's street map (terrain_osm.webp) shows on the land; 0: not at all
// the splat with the map: its rim fades out (at these times the take's radius from its middle), so its loose edge
// splats melt into the land; it is in its own colours, its shadows a little cooler (SPLAT_GRADE, said in the panel) and what lies well beyond what the view looks at hazed toward the dark land
const SPLAT_FEATHER = [0.9, 1.45]; // its splats reach about 1.4 times the radius (the trees round it), the loose ones beyond
const SPLAT_GRADE = 0.12; // how far its shadows shift cool (and lose a little colour); highlights and the ice untouched; 0: none
const SPLAT_HAZE = [1.2, 12, 2.2, 45]; // haze from 1.2× the view's distance + 12 m to 2.2× + 45 m beyond the eye
// the take's footprint on the land (where its splats lie, seen from above): the land dimmed under it, not in a round patch
const FOOT_M = 40, FOOT_N = 160, FOOT_LEVEL = 5; // ±m round its middle, cells a side, opacity per m² at its edge
// W A S D move the view (forward, left, back, right, level with the ground), Q E down and up, Shift faster: the eye and
// what it looks at go together, at a speed that follows the view's distance (walking pace in the take, faster from afar)
const MOVE_KEYS = { w: [0, 0, 1], s: [0, 0, -1], a: [-1, 0, 0], d: [1, 0, 0], q: [0, -1, 0], e: [0, 1, 0] };
const MOVE_SPEED = [0.6, 1.5, 3000]; // m/s per m of the view's distance, at least, at most
const MOVE_FAST = 3;
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

export function leaveScene() {
  if (!state) return;
  cancelAnimationFrame(state.raf);
  state.ro?.disconnect();
  removeEventListener("keydown", state.onKey, true);
  removeEventListener("keyup", state.onKeyUp, true);
  removeEventListener("blur", state.onBlur);
  state.controls?.dispose();
  state.renderer?.dispose();
  state.renderer?.forceContextLoss(); // hand the GPU memory back at once, not whenever the page is collected
  state = null;
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const ease = (x) => 1 - (1 - x) ** 3;
const easeInOut = (x) => (x < 0.5 ? 4 * x ** 3 : 1 - (-2 * x + 2) ** 3 / 2);
const clock = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

export async function renderScene(main, research) {
  leaveScene();
  const st = state = {};
  main.replaceChildren();
  research.innerHTML = `<p class="empty">Loading…</p>`;
  let list;
  try {
    const r = await fetch("/api/scenes");
    if (!r.ok) throw new Error(r.status);
    list = await r.json();
  } catch {
    if (state === st) research.innerHTML = `<div class="tm-empty"><p>The server doesn't know the Scene Viewer yet.</p>
      <p class="small muted">Restart it (<code>evidence serve</code>) and reload this page.</p></div>`;
    return;
  }
  if (state !== st) return;
  if (!list.length) {
    research.innerHTML = `<div class="tm-empty"><p>No video in this folder has a 3D reconstruction yet.</p></div>`;
    return;
  }
  let pick;
  try { pick = localStorage.getItem("sceneVideo"); } catch {}
  const v = list.find((x) => x.video_id === pick) ?? list[0];
  const sc = await (await fetch(`/api/videos/${encodeURIComponent(v.video_id)}/scene`)).json();
  if (state !== st) return;
  st.scene = sc;
  panel(st, research, list, v);
  try {
    await view(st, main, research);
  } catch (e) {
    if (state === st) main.innerHTML = `<p class="empty">The 3D view couldn't load (${esc(e.message)}).</p>`;
  }
}

function panel(st, research, list, v) {
  const sc = st.scene;
  const pick = list.length > 1 ? `<select class="tm-pick" id="sc-pick">${list.map((x) => `<option value="${esc(x.video_id)}"${x.video_id === v.video_id ? " selected" : ""}>${esc(x.title)}</option>`).join("")}</select>` : "";
  const takes = (sc.pieces ?? []).map((x, k) => `<li><button type="button" data-piece="${k}">${esc(x.label)}, ${clock(x.start)}–${clock(x.end)}</button>
    <span class="muted">· ${x.registered} of ${x.frames} frames placed${x.gaussians ? ` · ${x.gaussians.toLocaleString()} splats` : ""}</span></li>`).join("");
  research.innerHTML = `
    <div class="head">
      ${pick || `<div class="title">${esc(sc.title)}</div>`}
      <div class="sub">${esc(sc.channel_title ?? "")} · ${esc(sc.published_at?.slice(0, 4))} · <a href="${esc(sc.source_url)}" target="_blank" rel="noopener">YouTube ↗</a></div>
    </div>
    <p class="tm-transport"><button type="button" id="sc-prev">Previous camera</button><button type="button" id="sc-next">Next camera</button>
      <button type="button" id="sc-home">Whole take</button><button type="button" id="sc-area" hidden>Whole area</button></p>
    <dl class="fields tm-now">
      <dt>Take</dt><dd id="sc-take"></dd>
      <dt>Shown</dt><dd id="sc-shown"></dd>
      <dt>View</dt><dd id="sc-cam"></dd>
      <dt>Move</dt><dd>W A S D, Q E down and up<span class="note">Shift for faster; drag to look round, scroll to come closer</span></dd>
    </dl>
    <p class="tm-summary">${esc(sc.summary)}</p>
    <h3 class="tm-h">Takes</h3><ul class="tm-list">${takes}</ul>
    <dl class="fields tm-prov" id="sc-notes"></dl>
    <div id="sc-land" hidden></div>
    <dl class="fields tm-prov">
      ${(sc.provenance ?? []).map((p) => `<dt>${esc(p.label)}</dt><dd>${esc(p.evidence)}</dd>`).join("")}
      ${sc.confidence != null ? `<dt>Confidence</dt><dd>${Math.round(sc.confidence * 100)}%<span class="note">inferred: an attempt at the place's shape from the footage, not a survey</span></dd>` : ""}
    </dl>
    <p class="small muted tm-credit">Reconstructed with COLMAP and msplat · splats drawn by Spark</p>`;
  research.querySelector("#sc-pick")?.addEventListener("change", (e) => {
    try { localStorage.setItem("sceneVideo", e.target.value); } catch {}
    renderScene(document.getElementById("main"), research);
  });
}

async function view(st, main, research) {
  const THREE = await import("three");
  const { OrbitControls } = await import("three/addons/controls/OrbitControls.js");
  const sc = st.scene, base = sc.base_url, pieces = sc.pieces ?? [];
  const wrap = Object.assign(document.createElement("div"), { className: "scene-view" });
  main.replaceChildren(wrap);
  const renderer = st.renderer = new THREE.WebGLRenderer({ antialias: false });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  renderer.setClearColor(0x000000);
  wrap.append(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, 1, 0.05, sc.terrain ? 40000 : 2000);
  const landData = sc.terrain ? fetch(base + sc.terrain).then((r) => (r.ok ? r.json() : null)).catch(() => null) : null;
  const controls = st.controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.screenSpacePanning = true;
  // draw only while something moves (and a little after, for the splats' sort to catch up): a still view costs nothing
  st.awake = 0;
  const wake = (ms = 800) => { st.awake = Math.max(st.awake, performance.now() + ms); };
  controls.addEventListener("change", () => wake());
  const spark = pieces.some((x) => x.splat) && await import("@sparkjsdev/spark").catch(() => null);
  if (spark) scene.add(new spark.SparkRenderer({ renderer }));
  const { PLYLoader } = await import("three/addons/loaders/PLYLoader.js");
  const ringGeo = new THREE.RingGeometry(0.11, 0.14, 24).rotateX(-Math.PI / 2);
  const $ = (id) => research.querySelector("#" + id);

  // each take is its own group (its own place and scale), shown one at a time; its model loads when first shown
  const groups = pieces.map(() => Object.assign(new THREE.Group(), { visible: false }));
  groups.forEach((g) => scene.add(g));
  const loaded = new Map();
  const lineMats = []; // the land's wide lines: their width is in CSS pixels of the view, so they follow its size
  // the rim fade, the cooler shadows and the haze, per splat on the GPU (a Spark world modifier: the take's own coordinates);
  // nothing in the model changes
  const dress = (x, m) => {
    const { dyno } = spark, r = x.radius_m ?? 25, c = x.centre ?? [0, 0, 0];
    const u = Object.fromEntries(["ex", "ey", "ez", "h0", "h1"].map((k) => [k, dyno.dynoFloat(k === "h0" || k === "h1" ? 1e9 : 0)]));
    const f = (v) => v.toFixed(3);
    m.worldModifier = dyno.dynoBlock({ gsplat: dyno.Gsplat }, { gsplat: dyno.Gsplat }, ({ gsplat }) => ({
      gsplat: dyno.dyno({ inTypes: { gsplat: dyno.Gsplat, ...Object.fromEntries(Object.keys(u).map((k) => [k, "float"])) },
        outTypes: { gsplat: dyno.Gsplat }, inputs: { gsplat, ...u },
        statements: ({ inputs: i, outputs: o }) => [
          `${o.gsplat} = ${i.gsplat};`,
          `float rim = length(${i.gsplat}.center.xz - vec2(${f(c[0])}, ${f(c[2])}));`,
          `${o.gsplat}.rgba.a *= 1.0 - smoothstep(${f(r * SPLAT_FEATHER[0])}, ${f(r * SPLAT_FEATHER[1])}, rim);`,
          `vec3 col = clamp(${i.gsplat}.rgba.rgb, 0.0, 1.0);`,
          `float lum = dot(col, vec3(0.3, 0.59, 0.11));`,
          // its shadows a little cooler and greyer; highlights (the ice) as they are
          `col = mix(col, mix(vec3(lum), col, 0.8) + lum * vec3(-0.25, 0.0, 0.35), ${f(SPLAT_GRADE * 4)} * (1.0 - smoothstep(0.3, 0.75, lum)));`,
          // haze: what lies well beyond what the view looks at sinks toward the dark land
          `float haze = smoothstep(${i.h0}, ${i.h1}, distance(${i.gsplat}.center, vec3(${i.ex}, ${i.ey}, ${i.ez})));`,
          `col = mix(col, vec3(0.055), 0.8 * haze);`,
          `${o.gsplat}.rgba.rgb = col;`,
        ] }).outputs.gsplat }));
    m.updateGenerator();
    // set each frame: the haze from where the eye is; regenerated only on a change
    let last = "";
    x.dress = (far, eye) => {
      const q = Math.max(0.02, far * 0.01), key = [...eye.toArray().map((v) => Math.round(v / q)), Math.round(Math.log(far + 1) * 50)].join();
      if (key === last) return;
      last = key;
      [u.ex.value, u.ey.value, u.ez.value] = eye.toArray();
      u.h0.value = SPLAT_HAZE[0] * far + SPLAT_HAZE[1];
      u.h1.value = SPLAT_HAZE[2] * far + SPLAT_HAZE[3];
      m.updateVersion();
    };
  };
  // where the take's splats lie on the ground (opacity per m², in its own coordinates round its middle, rim fade
  // included), blurred about 2 m: a texture the land reads for the dimming under the take
  const footprint = (x, m) => {
    const N = FOOT_N, cell = (2 * FOOT_M) / N, g = new Float32Array(N * N), c = x.centre ?? [0, 0, 0], r = x.radius_m ?? 25;
    const v = new THREE.Vector3();
    m.updateMatrix();
    m.forEachSplat((_i, p, _s, _q, opacity) => {
      v.copy(p).applyMatrix4(m.matrix);
      const dx = v.x - c[0], dz = v.z - c[2], i = Math.floor((dx + FOOT_M) / cell), j = Math.floor((dz + FOOT_M) / cell);
      if (i < 0 || j < 0 || i >= N || j >= N) return;
      g[j * N + i] += opacity * (1 - smooth(r * SPLAT_FEATHER[0], r * SPLAT_FEATHER[1], Math.hypot(dx, dz)));
    });
    // a gaussian blur, σ 4 cells, across then down
    const k = Array.from({ length: 25 }, (_, i) => Math.exp(-((i - 12) ** 2) / 32)), ks = k.reduce((a, b) => a + b);
    const blur = (src, dx, dy) => {
      const out = new Float32Array(N * N);
      for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
        let a = 0;
        for (let t = 0; t < 25; t++) {
          const ii = i + (t - 12) * dx, jj = j + (t - 12) * dy;
          if (ii >= 0 && jj >= 0 && ii < N && jj < N) a += src[jj * N + ii] * k[t];
        }
        out[j * N + i] = a / ks;
      }
      return out;
    };
    const b = blur(blur(g, 1, 0), 0, 1), data = new Uint8Array(N * N);
    // stored as a log scale, so the edge (FOOT_LEVEL per m²) sits at FOOT_EDGE and the dense middle still fits
    for (let n = 0; n < N * N; n++) data[n] = Math.min(255, Math.round(255 * Math.log1p(b[n] / cell ** 2) / Math.log1p(1000)));
    const tex = new THREE.DataTexture(data, N, N, THREE.RedFormat, THREE.UnsignedByteType);
    tex.minFilter = tex.magFilter = THREE.LinearFilter;
    tex.needsUpdate = true;
    return tex;
  };
  const load = (k) => {
    if (!loaded.has(k)) loaded.set(k, (async () => {
      const x = pieces[k], g = groups[k];
      if (spark && x.splat) {
        const m = new spark.SplatMesh({ url: base + x.splat });
        // trained in the take's own frame: placed upright and sized by the same similarity as its points
        new THREE.Matrix4().fromArray(x.world).decompose(m.position, m.quaternion, m.scale);
        dress(x, m);
        g.add(m);
        await m.initialized?.catch(() => {});
        if (m.initialized) x.foot = footprint(x, m);
        wake(1500);
      } else {
        const geo = await new PLYLoader().loadAsync(base + x.points);
        g.add(new THREE.Points(geo, new THREE.PointsMaterial({ size: 2, sizeAttenuation: false, vertexColors: true })));
      }
      const fps = x.cameras.length > 1 ? (x.cameras.length - 1) / Math.max(1e-6, x.cameras.at(-1).t - x.cameras[0].t) : 1;
      const step = Math.max(1, Math.round(fps * RING_EVERY_S));
      x.rings = x.cameras.map((c, j) => {
        if (j % step) return null;
        const r = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.4, side: THREE.DoubleSide, depthWrite: false }));
        r.position.set(c.position[0], c.position[1] - (x.eye_height ?? 1.5), c.position[2]);
        r.userData.j = j;
        g.add(r);
        return r;
      }).filter(Boolean);
      const T = await landData;
      if (T && T.piece === x.name) await addLand(k, T);
    })());
    return loaded.get(k);
  };

  // the land around a take: heights on a grid in metres around it (x east, z south), true to size, turned and set on
  // its ground as terrain.json says; drawn as a map in greys, no colour (terrain_layers: open water darkest, and
  // where the drained bed stays wet, its old channels, lighter), shaded from the north-west, with contour lines every
  // metre, dimmed round the take. Round the take it is drawn as if at the far end of the view, so the take's own model
  // always shows over it (its ice lies lower than the land's flat old water) and the land only where it has none
  const addLand = async (k, T) => {
    const x = pieces[k], { nx, ny } = T.grid, hole = (T.hole_m ?? 25) * 1.2;
    const land = new THREE.Group();
    land.position.set(x.centre[0], -LAND_SINK, x.centre[2]);
    land.rotation.y = THREE.MathUtils.degToRad(T.bearing_deg);
    const pos = new Float32Array(nx * ny * 3), uv = new Float32Array(nx * ny * 2);
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const n = j * nx + i, u = i / (nx - 1), v = j / (ny - 1);
      pos.set([T.grid.x[0] + (T.grid.x[1] - T.grid.x[0]) * u, T.grid.heights_dm[n] / 10 - T.base_m,
        T.grid.z[0] + (T.grid.z[1] - T.grid.z[0]) * v], n * 3);
      uv.set([u, 1 - v], n * 2);
    }
    const idx = new Uint32Array((nx - 1) * (ny - 1) * 6);
    for (let j = 0, o = 0; j < ny - 1; j++) for (let i = 0; i < nx - 1; i++, o += 6) {
      const a = j * nx + i;
      idx.set([a, a + nx, a + 1, a + 1, a + nx, a + nx + 1], o);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
    geo.setIndex(new THREE.BufferAttribute(idx, 1));
    geo.computeVertexNormals();
    const layers = await new THREE.TextureLoader().loadAsync(base + T.layers);
    layers.colorSpace = THREE.NoColorSpace; // data, not colour: r open water, g how wet the ground stays
    layers.anisotropy = renderer.capabilities.getMaxAnisotropy();
    // the Route Map's street map, laid over the heights like a blanket (the river and roads it draws; today's map)
    const map = T.map && LAND_MAP > 0 ? await new THREE.TextureLoader().loadAsync(base + T.map).catch(() => null) : null;
    if (map) { map.colorSpace = THREE.NoColorSpace; map.anisotropy = renderer.capabilities.getMaxAnisotropy(); }
    const uniforms = { layers: { value: layers }, osm: { value: map ?? layers }, fade: { value: 0 }, base: { value: T.base_m }, hole: { value: hole },
      foot: { value: x.foot ?? new THREE.DataTexture(new Uint8Array(1), 1, 1, THREE.RedFormat) },
      turn: { value: new THREE.Vector2(Math.cos(THREE.MathUtils.degToRad(T.bearing_deg)), Math.sin(THREE.MathUtils.degToRad(T.bearing_deg))) } };
    uniforms.foot.value.needsUpdate = true;
    const mat = new THREE.ShaderMaterial({ uniforms, vertexShader: `
      varying vec2 vUv; varying vec3 vP; varying vec3 vN;
      void main() { vUv = uv; vP = position; vN = normal; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `
      uniform sampler2D layers, osm, foot; uniform float fade, base, hole; uniform vec2 turn;
      varying vec2 vUv; varying vec3 vP; varying vec3 vN;
      float line(float f, float w) { // one pixel wide wherever f crosses a whole number; gone where they crowd
        return (1.0 - smoothstep(0.0, w * 1.2, abs(fract(f - 0.5) - 0.5))) * (1.0 - smoothstep(0.15, 0.45, w));
      }
      void main() {
        vec4 L = texture2D(layers, vUv);
        float h = vP.y + base, d = length(vP.xz); // the real height, m above sea level; how far from the take
        // black and white, no colour (decided with the user): every tone a grey from near-black to light grey (t, 0 to 1)
        const vec3 INK0 = vec3(0.02), INK1 = vec3(0.77);
        // the ground: darker low (the bed and islands), lighter high (the bank), shaded from the north-west;
        // the shading steepened 4 times so a gentle land still reads (the heights themselves are true to size)
        vec3 n = normalize(vec3(vN.x * 4.0, vN.y, vN.z * 4.0));
        float g = mix(0.11, 0.2, smoothstep(13.0, 24.0, h)) + 0.1 * smoothstep(24.0, 80.0, h);
        float t = g * (0.62 + 0.62 * max(dot(n, normalize(vec3(-1.0, 1.3, -1.0))), 0.0));
        // where the drained bed stays wet (its old channels): lighter
        t = mix(t, 0.4, 0.85 * smoothstep(0.12, 0.6, L.g));
        ${map ? `// the street map in the same greys: its water darkest (the river and the channels it draws), its roads and
        // tracks lightest, its land and wetland as mid tones by their lightness; shaded by the relief, so it lies on the heights
        vec3 o = texture2D(osm, vUv).rgb;
        float lum = dot(o, vec3(0.3, 0.59, 0.11)), ow = smoothstep(0.04, 0.1, o.b - o.r) * smoothstep(0.0, 0.05, o.b - o.g);
        float ot = mix(0.07 + 0.5 * pow(lum, 5.0), 0.04, ow) * (0.62 + 0.62 * max(dot(n, normalize(vec3(-1.0, 1.3, -1.0))), 0.0));
        t = mix(t, ot, ${LAND_MAP.toFixed(2)});` : ""}
        // contour lines: every metre faint, every 5 m stronger
        t += ${LAND_CONTOURS ? "0.07 * line(h, fwidth(h)) + 0.16 * line(h / 5.0, fwidth(h / 5.0))" : "0.0"};
        // open water: darkest, with a fine light shoreline; no contours on it
        float w = L.r, shore = 1.0 - smoothstep(0.0, fwidth(w) * 1.5 + 1e-4, abs(w - 0.5));
        t = mix(t, 0.05, smoothstep(0.35, 0.65, w)) + 0.35 * shore;
        float edge = min(min(vUv.x, 1.0 - vUv.x), min(vUv.y, 1.0 - vUv.y));
        // the take's footprint (its own coordinates: the land is turned round its middle): the land a little dimmer under it
        vec2 tp = vec2(vP.x * turn.x + vP.z * turn.y, -vP.x * turn.y + vP.z * turn.x);
        float fp = texture2D(foot, (tp + ${FOOT_M.toFixed(1)}) / ${(2 * FOOT_M).toFixed(1)}).r;
        float fedge = ${(Math.log1p(FOOT_LEVEL) / Math.log1p(1000)).toFixed(4)};
        t *= mix(1.0, 0.75, smoothstep(fedge, fedge + 0.15, fp));
        vec3 col = mix(INK0, INK1, clamp(t, 0.0, 1.0));
        gl_FragColor = vec4(col * smoothstep(0.0, 0.07, edge) * fade, 1.0);
        gl_FragDepth = d < hole ? 1.0 : gl_FragCoord.z;
      }` });
    land.add(new THREE.Mesh(geo, mat));
    if (map) wrap.append(Object.assign(document.createElement("div"), { className: "scene-credit", textContent: "Street map © OpenStreetMap contributors" }));
    // the Route Map's lines on it: the river (the user's nine points) in blue; the walk as the Route Map draws it,
    // solid where filmed, dashed where a cut skips it, a dot per frame, A and B at its ends; a ring round the take
    const lift = (p) => [p[0], p[1] - T.base_m + 0.6, p[2]];
    const lines = []; // [material, its opacity once the land has faded in]
    const RIVER = 0x9fd3ff;
    // lines some pixels wide, like the Route Map's (WebGL's own are one pixel, lost among the contours)
    const [{ Line2 }, { LineGeometry }, { LineMaterial }] = await Promise.all(["Line2", "LineGeometry", "LineMaterial"]
      .map((n) => import(`three/addons/lines/${n}.js`)));
    const line = (to, pts, opacity, { loop = false, color = 0xffffff, dashed = false, width = 2, order = 0 } = {}) => {
      if (loop) pts = [...pts, pts[0]];
      const m = new LineMaterial({ color, linewidth: width, dashed, dashSize: 14, gapSize: 10, transparent: true, opacity: 0, depthWrite: false });
      m.resolution.set(wrap.clientWidth, wrap.clientHeight);
      const l = new Line2(new LineGeometry().setPositions(pts.flat()), m);
      if (dashed) l.computeLineDistances();
      l.renderOrder = order;
      to.add(l);
      lines.push([m, opacity]);
      lineMats.push(m);
    };
    // the route over the river where they share a way: white within a blue edge
    const style = { river: [0.95, { color: RIVER, width: 4.5 }], filmed: [0.95, { width: 2, order: 2 }], unfilmed: [0.65, { dashed: true, width: 2, order: 1 }], route: [0.3, {}] };
    for (const l of T.lines ?? []) for (const run of l.runs) line(land, run.map(lift), ...(style[l.kind] ?? style.route));
    line(land, Array.from({ length: 64 }, (_, i) => [Math.cos(i / 32 * Math.PI) * hole * 1.4, 0.6, Math.sin(i / 32 * Math.PI) * hole * 1.4]), 0.7, { loop: true, width: 1.5 });
    const dots = (pts, size, color, opacity) => {
      const m = new THREE.PointsMaterial({ color, size, sizeAttenuation: false, transparent: true, opacity: 0, depthWrite: false });
      land.add(Object.assign(new THREE.Points(new THREE.BufferGeometry().setFromPoints(pts.map((p) => new THREE.Vector3(...lift(p)))), m), { renderOrder: 3 }));
      lines.push([m, opacity]);
    };
    dots(T.frames ?? [], 3, 0xffffff, 0.7);
    dots((T.marks ?? []).map((m) => m.xyz), 5, RIVER, 0.95);
    dots((T.ends ?? []).map((e) => e.xyz), 8, 0xffffff, 1);
    // A and B: a letter beside each end, the same size on screen however far the view is
    for (const e of T.ends ?? []) {
      const c = Object.assign(document.createElement("canvas"), { width: 64, height: 64 }), g = c.getContext("2d");
      g.font = "600 40px system-ui, sans-serif"; g.fillStyle = "#fff"; g.textAlign = "center"; g.textBaseline = "middle";
      g.fillText(e.label, 32, 34);
      const m = new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), sizeAttenuation: false, transparent: true, opacity: 0, depthWrite: false });
      const sp = new THREE.Sprite(m);
      sp.scale.set(0.035, 0.035, 1);
      sp.center.set(-0.15, -0.1); // up and to the right of its dot
      sp.position.set(...lift(e.xyz));
      land.add(sp);
      lines.push([m, 1]);
    }
    groups[k].add(land);
    land.updateMatrixWorld(true);
    // the whole area, seen from above, from the south, looking at the take: north up, as on a map, but turned (from
    // the south-east or south-west, at most LAND_SWING) toward the way the opening view looks, so the flight down has
    // little left to turn, and keeps the take in the middle
    const mid = new THREE.Vector3(...x.centre);
    const j = x.open_t == null ? -1 : x.cameras.reduce((b, c, i) => (Math.abs(c.t - x.open_t) < Math.abs(x.cameras[b].t - x.open_t) ? i : b), 0);
    const opening = x.open_view ? { position: new THREE.Vector3(...x.open_view.position), target: new THREE.Vector3(...x.open_view.target) } : j >= 0 ? camPose(x, j) : null;
    const ahead = opening ? opening.target.clone().sub(opening.position).setY(0) : new THREE.Vector3();
    const north = new THREE.Vector3(0, 0, -1).applyQuaternion(land.quaternion), east = new THREE.Vector3(1, 0, 0).applyQuaternion(land.quaternion);
    const swing = THREE.MathUtils.degToRad(LAND_SWING);
    const turnTo = ahead.lengthSq() > 1e-6 ? Math.atan2(ahead.dot(east), ahead.dot(north)) : 0; // compass, -π..π
    const h = Math.max(-swing, Math.min(swing, turnTo));
    const look = north.clone().multiplyScalar(Math.cos(h)).addScaledVector(east, Math.sin(h));
    const span = Math.max(...T.grid.x.map(Math.abs), ...T.grid.z.map(Math.abs)); // the take to the land's farthest edge
    const dist = (span * 0.72) / Math.tan(THREE.MathUtils.degToRad((x.fov_deg ?? 60) / 2));
    const tilt = THREE.MathUtils.degToRad(LAND_TILT);
    x.land = { T, uniforms, lines,
      area: { target: mid, position: mid.clone().addScaledVector(look, -dist * Math.cos(tilt)).add(new THREE.Vector3(0, dist * Math.sin(tilt), 0)) } };
    landNotes(T);
  };
  // the lines show with the land, and only from above: down in the take (the view within LAND_LINES_M of what it looks
  // at) they go, since the splats' trees don't hide what is behind them and a route would cut through the scene
  const setFade = (x, f = x.land.uniforms.fade.value, far = x.land.far ?? Infinity) => {
    x.land.uniforms.fade.value = f;
    x.land.far = far;
    const near = smooth(LAND_LINES_M[0], LAND_LINES_M[1], far);
    x.land.lines.forEach(([m, o]) => (m.opacity = o * f * near));
  };
  const landNotes = (T) => {
    const el = $("sc-land");
    el.hidden = false;
    el.innerHTML = `<h3 class="tm-h">Around it</h3><p class="tm-summary">${esc(T.summary)}</p>
      <dl class="fields tm-prov">${(T.provenance ?? []).map((p) => `<dt>${esc(p.label)}</dt><dd>${esc(p.evidence)}</dd>`).join("")}
      ${T.confidence != null ? `<dt>Confidence</dt><dd>${Math.round(T.confidence * 100)}%<span class="note">inferred: where the take sits in the land is an estimate</span></dd>` : ""}</dl>`;
    $("sc-area").hidden = false;
  };

  let cur = -1, at = -1, vi = -1, fly = null, moved = false; // moved: the pointer took over, so the intro doesn't start
  const flyTo = (to, ms = FLY_MS, curve = ease) => { fly = { t0: performance.now(), ms, curve, p0: camera.position.clone(), q0: controls.target.clone(), p1: to.position, q1: to.target }; };
  // a take seen whole: from above and to one side of the reconstruction's middle, far enough to take it all in
  const overview = (x) => {
    const c = new THREE.Vector3(...(x.centre ?? [0, 0, 0])), r = Math.max(2, x.reach ?? x.radius_m ?? 10);
    return { position: c.clone().add(new THREE.Vector3(r * 1.1, r * 1.3, r * 1.1)), target: c };
  };
  const show = async (k, glide = true) => {
    cur = k; at = -1; vi = -1;
    $("sc-prev").textContent = pieces[k].views?.length ? "Previous view" : "Previous camera";
    $("sc-next").textContent = pieces[k].views?.length ? "Next view" : "Next camera";
    groups.forEach((g, j) => (g.visible = j === k));
    wake(1500);
    research.querySelectorAll("button[data-piece]").forEach((b) => b.classList.toggle("set", +b.dataset.piece === k));
    const x = pieces[k];
    $("sc-take").textContent = `${x.label}, ${clock(x.start)}–${clock(x.end)}`;
    $("sc-shown").innerHTML = `${x.gaussians ? `${x.gaussians.toLocaleString()} Gaussian splats` : `${x.point_count.toLocaleString()} points`}<span class="note">${x.registered} of ${x.frames} frames placed${x.gaussians && SPLAT_GRADE ? "; its shadows drawn a little cooler, and what is far off hazed, to sit with the map (the model's colours are as filmed)" : ""}</span>`;
    $("sc-cam").textContent = "drag to turn, right-drag or shift-drag to move, scroll to zoom";
    // this take's own notes: its footage, how it was levelled and sized
    $("sc-notes").innerHTML = (x.provenance ?? []).map((p) => `<dt>${esc(p.label)}</dt><dd>${esc(p.evidence)}</dd>`).join("");
    camera.fov = x.fov_deg ?? 60;
    camera.updateProjectionMatrix();
    const o = overview(x);
    const intro = !glide && x.open_t != null;
    if (glide) flyTo(o);
    else if (intro) { // start far out along the overview's line, then fly in once the model is there
      camera.position.copy(o.target).addScaledVector(o.position.clone().sub(o.target), INTRO_FAR);
      // with land, high above it instead (nothing to see yet) until it is built and the view can start over it
      if (sc.terrain) camera.position.copy(o.target).add(new THREE.Vector3(0, 30000, 1));
      controls.target.copy(o.target);
    } else { camera.position.copy(o.position); controls.target.copy(o.target); }
    await load(k);
    if (cur !== k || state !== st) return;
    if (x.land && intro && !moved) { camera.position.copy(x.land.area.position); controls.target.copy(x.land.area.target); wake(); }
    else if (x.land && x.land.uniforms.fade.value < 1) fadeLand(x);
    if (intro) await new Promise((r) => setTimeout(r, INTRO_HOLD_MS));
    if (intro && cur === k && !fly && !moved && state === st) {
      const j = x.cameras.reduce((b, c, i) => (Math.abs(c.t - x.open_t) < Math.abs(x.cameras[b].t - x.open_t) ? i : b), 0);
      if (x.land) { fadeLand(x); landTo(x, j); } else introTo(x, j, o.target);
    } else if (intro && x.land) fadeLand(x);
  };
  const fadeLand = (x) => { if (!st.fading) st.fading = { x, t0: performance.now() }; };
  // the fly-in over land: from the whole area down to the take's opening view. The distance to what it looks at
  // shrinks at an even rate (an evenly paced zoom across a few thousand times) with the take in the middle all the
  // way. The camera comes round and down behind the opening view gradually over the whole descent (on a great circle
  // that stays above the ground), and only near the end does the look settle the few metres onto the opening view's
  const landTo = (x, j) => {
    const v = x.open_view, { position: p1, target: q1 } = v ? { position: new THREE.Vector3(...v.position), target: new THREE.Vector3(...v.target) } : camPose(x, j);
    const q0 = controls.target.clone(), o0 = camera.position.clone().sub(q0), o1 = p1.clone().sub(q1);
    const d0 = o0.length(), d1 = Math.max(1e-3, o1.length()), u0 = o0.normalize(), u1 = o1.normalize();
    const turn = u0.angleTo(u1), axis = new THREE.Vector3().crossVectors(u0, u1);
    if (axis.lengthSq() < 1e-9) axis.set(0, 1, 0); else axis.normalize();
    fly = { t0: performance.now(), ms: LAND_MS, curve: easeInOut, p1, q1, path: (e) => {
      controls.target.lerpVectors(q0, q1, smooth(0.4, 1, e));
      camera.position.copy(controls.target).addScaledVector(u0.clone().applyAxisAngle(axis, turn * smooth(0.1, 1, e)), d0 * (d1 / d0) ** e);
    } };
    label(x, j);
    if (v) opened(x, j);
  };
  // the fly-in: a curve from far out that comes down behind the camera and glides forward into its view (a straight
  // line would dive through the ground), looking from the take's middle round to where the camera looked
  const introTo = (x, j, centre) => {
    // it ends on the take's saved opening view when it has one, else on the camera's own view
    const v = x.open_view, { position: p1, target: q1 } = v ? { position: new THREE.Vector3(...v.position), target: new THREE.Vector3(...v.target) } : camPose(x, j);
    const fwd = q1.clone().sub(p1).normalize(), flat = new THREE.Vector3(fwd.x, 0, fwd.z).normalize();
    const r = Math.max(2, x.reach ?? 10), look = p1.clone().addScaledVector(fwd, r * 0.4);
    const p0 = camera.position.clone(), w = p1.clone().addScaledVector(flat, -r * 0.9).add(new THREE.Vector3(0, r * 0.5, 0));
    fly = { t0: performance.now(), ms: INTRO_MS, curve: easeInOut, p1, q1, path: (e) => {
      const u = 1 - e;
      camera.position.copy(p0).multiplyScalar(u * u).addScaledVector(w, 2 * u * e).addScaledVector(p1, e * e);
      const s = Math.min(1, e / 0.7); // turns to look ahead over the first 70% of the way, starting and ending gently
      controls.target.lerpVectors(centre, look, s * s * (3 - 2 * s));
    } };
    label(x, j);
    if (v) opened(x, j);
  };
  const opened = (x, j) => {
    const i = x.views?.findIndex((w) => w.opening) ?? -1;
    if (i >= 0) viewLabel(x, i);
    else $("sc-cam").textContent = `opening view, just behind camera ${j + 1} of ${x.cameras.length} · as filmed at ${clock(x.cameras[j].t)}`;
  };
  const nearest = (x, t) => x.cameras.reduce((b, c, i) => (Math.abs(c.t - t) < Math.abs(x.cameras[b].t - t) ? i : b), 0);
  // a chosen view: from `back` m behind (level) and `rise` m above where the camera stood at that moment, looking at
  // `look` m ahead along its view (what it filmed); the opening one is the take's open_view, set by the user
  const viewPose = (x, w) => {
    if (w.opening && x.open_view) return { position: new THREE.Vector3(...x.open_view.position), target: new THREE.Vector3(...x.open_view.target) };
    const { position: p, target } = camPose(x, nearest(x, w.t));
    const fwd = target.clone().sub(p).normalize(), flat = new THREE.Vector3(fwd.x, 0, fwd.z).normalize();
    return { position: p.clone().addScaledVector(flat, -(w.back ?? 3)).add(new THREE.Vector3(0, w.rise ?? 0.6, 0)),
      target: p.clone().addScaledVector(fwd, w.look ?? 6) };
  };
  const viewLabel = (x, i) => {
    const w = x.views[i];
    label(x, nearest(x, w.t));
    vi = i;
    const url = `${sc.source_url}${sc.source_url.includes("?") ? "&" : "?"}t=${Math.floor(w.t)}s`;
    $("sc-cam").innerHTML = `view ${i + 1} of ${x.views.length} · ${esc(w.label)}<span class="note">as filmed at <a href="${esc(url)}" target="_blank" rel="noopener">${clock(w.t)} ↗</a>, seen from a little behind and above the camera</span>`;
  };
  const toView = (i) => {
    const x = pieces[cur], n = x.views.length;
    i = (i + n) % n;
    flyTo(viewPose(x, x.views[i]), FLY_MS * 1.5);
    viewLabel(x, i);
  };
  // Previous/Next: the chosen views when the take has them (from a camera, the next one after it in the video)
  const step = (d) => {
    const x = pieces[cur];
    if (!x) return;
    if (!x.views?.length) return toCam(at + d);
    if (vi >= 0) return toView(vi + d);
    const t = at >= 0 ? x.cameras[at].t : d > 0 ? -Infinity : Infinity;
    const i = d > 0 ? x.views.findIndex((w) => w.t > t) : x.views.findLastIndex((w) => w.t < t);
    toView(i < 0 ? (d > 0 ? 0 : -1) : i);
  };
  const toCam = (j, ms = FLY_MS, curve = ease) => {
    const x = pieces[cur];
    if (!x) return;
    at = (j + x.cameras.length) % x.cameras.length;
    flyTo(camPose(x, at), ms, curve);
    label(x, at);
  };
  // where camera j stood, looking 2 units ahead along its view
  const camPose = (x, j) => {
    const c = x.cameras[j], p = new THREE.Vector3(...c.position);
    const fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(new THREE.Quaternion(...c.quaternion));
    return { position: p, target: p.clone().add(fwd.multiplyScalar(2)) };
  };
  const label = (x, j) => {
    at = j; vi = -1;
    const c = x.cameras[at];
    $("sc-cam").textContent = `camera ${at + 1} of ${x.cameras.length} · as filmed at ${clock(c.t)}`;
    x.rings?.forEach((r) => (r.material.opacity = Math.abs(r.userData.j - at) < 2 ? 1 : 0.4));
    wake();
  };
  $("sc-home").addEventListener("click", () => { if (cur >= 0) show(cur); });
  $("sc-area").addEventListener("click", () => { const l = pieces[cur]?.land; if (l) { at = -1; vi = -1; flyTo(l.area, FLY_MS * 2); } });
  $("sc-next").addEventListener("click", () => step(1));
  $("sc-prev").addEventListener("click", () => step(-1));
  research.querySelectorAll("button[data-piece]").forEach((b) => b.addEventListener("click", () => show(+b.dataset.piece)));

  // a click (not a drag) on a ring flies to that camera
  const ray = new THREE.Raycaster();
  let down = null;
  // W A S D (see MOVE_KEYS): held keys move the view each frame; typing in a field doesn't
  const keys = new Set();
  let fast = false;
  st.onKey = (e) => {
    const k = e.key.toLowerCase();
    fast = e.shiftKey;
    if (!(k in MOVE_KEYS) || e.metaKey || e.ctrlKey || e.altKey || e.target.matches?.("input, select, textarea")) return;
    e.preventDefault();
    keys.add(k);
    fly = null; moved = true;
    wake();
  };
  st.onKeyUp = (e) => { keys.delete(e.key.toLowerCase()); fast = e.shiftKey; };
  st.onBlur = () => { keys.clear(); fast = false; };
  addEventListener("keydown", st.onKey, true);
  addEventListener("keyup", st.onKeyUp, true);
  addEventListener("blur", st.onBlur);
  let lastNow = 0;
  const walk = (now) => {
    const dt = Math.min(0.1, (now - lastNow) / 1000);
    lastNow = now;
    if (!keys.size) return;
    const fwd = controls.target.clone().sub(camera.position).setY(0);
    if (fwd.lengthSq() < 1e-9) fwd.set(0, 0, -1).applyQuaternion(camera.quaternion).setY(0);
    fwd.normalize();
    const right = new THREE.Vector3(-fwd.z, 0, fwd.x), m = new THREE.Vector3();
    for (const k of keys) { const [x, y, z] = MOVE_KEYS[k]; m.addScaledVector(right, x).addScaledVector(fwd, z).y += y; }
    if (m.lengthSq() < 1e-9) return;
    const far = camera.position.distanceTo(controls.target);
    const v = Math.min(MOVE_SPEED[2], Math.max(MOVE_SPEED[1], far * MOVE_SPEED[0])) * (fast ? MOVE_FAST : 1);
    m.normalize().multiplyScalar(v * dt);
    camera.position.add(m);
    controls.target.add(m);
    wake();
  };
  renderer.domElement.addEventListener("pointerdown", (e) => { down = [e.clientX, e.clientY]; fly = null; moved = true; });
  renderer.domElement.addEventListener("wheel", () => { fly = null; moved = true; }, { passive: true });
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4 || cur < 0) return;
    const r = renderer.domElement.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
    const hit = ray.intersectObjects(pieces[cur].rings ?? [])[0];
    if (hit) toCam(hit.object.userData.j);
  });

  const fit = () => {
    const w = wrap.clientWidth, h = wrap.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / Math.max(1, h);
    camera.updateProjectionMatrix();
    lineMats.forEach((m) => m.resolution.set(w, h));
    wake();
  };
  st.ro = new ResizeObserver(fit);
  st.ro.observe(wrap);
  fit();
  const frame = (now) => {
    if (state !== st) return;
    if (fly) {
      const f = Math.min(1, (now - fly.t0) / fly.ms), e = fly.curve(f);
      if (fly.path && f < 1) fly.path(e);
      else { camera.position.lerpVectors(fly.p0 ?? fly.p1, fly.p1, e); controls.target.lerpVectors(fly.q0 ?? fly.q1, fly.q1, e); }
      if (f === 1) fly = null;
      wake();
    }
    if (st.fading) {
      const f = Math.min(1, (now - st.fading.t0) / LAND_FADE_MS);
      setFade(st.fading.x, f * f * (3 - 2 * f));
      if (f === 1) st.fading = null;
      wake();
    }
    walk(now);
    controls.update();
    // from a few metres to a few kilometres: the near plane follows the distance, so the depth stays sharp at both
    const far = camera.position.distanceTo(controls.target), L = pieces[cur]?.land;
    if (L && Math.abs(Math.log((far + 1) / ((L.far ?? 0) + 1))) > 0.02) setFade(pieces[cur], undefined, far);
    pieces[cur]?.dress?.(far, camera.position);
    const near = Math.min(20, Math.max(0.03, far * 0.002));
    if (Math.abs(near / camera.near - 1) > 0.1) { camera.near = near; camera.updateProjectionMatrix(); }
    if (now < st.awake) renderer.render(scene, camera);
    st.raf = requestAnimationFrame(frame);
  };
  st.raf = requestAnimationFrame(frame);
  if (pieces.length) await show(0, false);
}
