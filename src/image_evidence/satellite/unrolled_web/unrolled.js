// The two last lines unrolled (unrolled.py): any moment of the film drawn on demand, window.draw(t) in seconds, so
// every frame is the same however long it takes to take. Time runs left to right: each line is an upright bar (its
// switchyard at the bottom, km up it) moving right with the date, its record left behind as a ribbon. D3 for the
// scales, easing and drawing; everything is redrawn each frame from DATA (unrolled.json), nothing animates on its own.
(() => {
  const D = window.DATA, T = D.time;
  const W = 1920, H = 1080;
  const X0 = 300;                 // the bars when the date starts; left of it, the ribbons' names
  const HEAD_MAX = 1400;          // where the bars settle while the frame pans with them
  const XR = 1840;                // the overview's right edge
  const RIB = {Dniprovska: {top: 250, h: 240}, "Ferosplavna-1": {top: 600, h: 240}};   // 750 kV above, its backup below
  const COL = {750: "#ffd600", 330: "#f09c00"};         // config line_rgb: two yellows, 750 kV the brighter
  const CORE = {750: "#fffae4", 330: "#ffe8b6"};
  const STEEL = {750: "#c8ccd2", 330: "#acb0b6"};       // zoomout STEEL_RGB: the bare wire of a line cut off
  const WATER = "#3f6f8c", BED = "#8a7656", GREY = "#8c8c8c", FAINT = "#5a5a5a";
  const WHERE = {occupied: "THE OCCUPIED SIDE", held: "THE UKRAINIAN SIDE", south_bank: "THE SOUTH BANK",
                 crossing: "THE RIVER CROSSING", north_bank: "THE NORTH BANK", unknown: "PLACE NOT PUBLISHED"};
  const DAY = 86400000;
  const dn = s => Math.round(Date.parse(s + "T00:00:00Z") / DAY);
  const d0 = dn(D.start), sc = dn(D.scale_change), dam = dn(D.dam.at);
  const [pa, pb] = D.px_per_day;
  const xc = d => (Math.min(d, sc) - d0) * pa + Math.max(0, d - sc) * pb;
  const dayAt = x => (x <= (sc - d0) * pa ? d0 + x / pa : sc + (x - (sc - d0) * pa) / pb);
  const utc = d => new Date(d * DAY);
  const fmtDay = d3.utcFormat("%-d %B %Y"), fmtMon = d3.utcFormat("%B %Y");
  const clamp01 = v => Math.max(0, Math.min(1, v));
  const ramp = (t, [a, b]) => clamp01((t - a) / (b - a));
  const ease = d3.easeCubicInOut;
  const lerp = (a, b, u) => a + (b - a) * u;
  const up = s => String(s).toUpperCase();

  // ------------------------------------------------------------ time: the date eased from stop to stop
  function xNow(t) {
    const S = T.stops;
    if (t <= S[0].arrive_s) return 0;
    for (let i = 1; i < S.length; i++) {
      const leave = S[i - 1].arrive_s + S[i - 1].hold_s;
      if (t < leave) return S[i - 1].x;
      if (t < S[i].arrive_s) return lerp(S[i - 1].x, S[i].x, ease((t - leave) / (S[i].arrive_s - leave)));
    }
    return S[S.length - 1].x;
  }
  const holding = t => T.stops.find(s => t >= s.arrive_s - 0.2 && t <= s.arrive_s + s.hold_s + 0.3);
  function camera(t) {
    const x = xNow(t);
    const u = ease(ramp(t, T.overview));
    return {x, day: dayAt(x), cam: lerp(Math.max(0, x - (HEAD_MAX - X0)), 0, u), k: lerp(1, (XR - X0) / T.x_end, u), over: u};
  }
  const sx = (x, c) => X0 + (x - c.cam) * c.k;

  // ------------------------------------------------------------ the map: plan metres to the frame, north up
  const MB = D.map.box, mw = MB[2] - MB[0], mh = MB[3] - MB[1];
  const ms = Math.min((1700 - 500) / mw, (1000 - 140) / mh);
  const mcx = 1100, mcy = 570, mx0 = (MB[0] + MB[2]) / 2, my0 = (MB[1] + MB[3]) / 2;
  const mx = x => mcx + (x - mx0) * ms, my = y => mcy - (y - my0) * ms;
  const rib = ln => RIB[ln.record];
  const ky = ln => rib(ln).h / D.show_m;                       // the bar's px a metre of line
  const by = (ln, s) => rib(ln).top + rib(ln).h - s * ky(ln);   // km up the bar
  const state = (ln, day) => {
    for (const [a, b, s] of ln.states) if (day >= dn(a) && day < dn(b)) return s;
    return ln.states[ln.states.length - 1][2];
  };

  // ------------------------------------------------------------ the page
  const svg = d3.select("#film");
  const defs = svg.append("defs");
  const glow = defs.append("filter").attr("id", "glow").attr("filterUnits", "userSpaceOnUse")
    .attr("x", 0).attr("y", 0).attr("width", W).attr("height", H);
  glow.append("feGaussianBlur").attr("stdDeviation", 5).attr("result", "b");
  const fm = glow.append("feMerge");
  fm.append("feMergeNode").attr("in", "b");
  fm.append("feMergeNode").attr("in", "SourceGraphic");
  const dots = defs.append("pattern").attr("id", "dots").attr("width", 7).attr("height", 7).attr("patternUnits", "userSpaceOnUse");
  dots.append("circle").attr("cx", 3.5).attr("cy", 3.5).attr("r", 1).attr("fill", STEEL[330]).attr("opacity", 0.55);
  const hatch = defs.append("pattern").attr("id", "hatch").attr("width", 7).attr("height", 7)
    .attr("patternUnits", "userSpaceOnUse").attr("patternTransform", "rotate(45)");
  hatch.append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", 7).attr("stroke", "#fff").attr("stroke-width", 1.4).attr("opacity", 0.7);
  const fadeRight = defs.append("linearGradient").attr("id", "fadeRight");
  fadeRight.append("stop").attr("offset", 0).attr("stop-color", "#fff").attr("stop-opacity", 1);
  fadeRight.append("stop").attr("offset", 1).attr("stop-color", "#fff").attr("stop-opacity", 0);
  defs.append("mask").attr("id", "openEnd").attr("maskContentUnits", "objectBoundingBox")
    .append("rect").attr("width", 1).attr("height", 1).attr("fill", "url(#fadeRight)");
  defs.append("clipPath").attr("id", "chart").append("rect").attr("x", X0 - 1).attr("y", 0).attr("width", W).attr("height", H);
  const root = svg.append("g");

  function txt(g, x, y, s, o = {}) {
    return g.append("text").attr("x", x).attr("y", y).text(s)
      .attr("fill", o.fill || "#fff").attr("font-size", o.size || 13).attr("font-weight", o.weight || 500)
      .attr("letter-spacing", o.ls == null ? "0.06em" : o.ls).attr("text-anchor", o.anchor || "start")
      .attr("opacity", o.a == null ? 1 : o.a);
  }
  // white capitals on a black box at half opacity, as every text of the films (zoomout _boxed)
  function boxed(g, x, y, s, o = {}) {
    const gg = g.append("g").attr("opacity", o.a == null ? 1 : o.a);
    const box = gg.append("rect").attr("fill", "#000").attr("opacity", 0.5);
    txt(gg, x, y, s, {size: o.size || 14, anchor: o.anchor || "start", fill: o.fill});
    const bb = gg.node().getBBox();
    box.attr("x", bb.x - 8).attr("y", bb.y - 5).attr("width", bb.width + 16).attr("height", bb.height + 10);
    return gg;
  }

  // ------------------------------------------------------------ one frame
  window.draw = function (t) {
    root.selectAll("*").remove();
    const c = camera(t);
    const g = root.append("g");
    const chart = g.append("g").attr("clip-path", "url(#chart)");
    const tau = ramp(t, T.unroll), bandsA = ease(ramp(t, T.bands)), over = c.over;
    const mapA = 1 - ease(clamp01(tau / 0.45));
    const grown = ease(ramp(t, T.grow)) * D.show_m;
    const now = c.day, xN = c.x, head = sx(xN, c), x0 = sx(0, c);
    const hold = holding(t);

    // the map, before the unrolling: the former reservoir's shore, the two plants, the lines growing out of them
    if (mapA > 0.001) {
      const m = g.append("g").attr("opacity", mapA);
      const shoreA = ease(ramp(t, [0.4, 3.0]));
      for (const run of D.map.shore)
        m.append("path").attr("d", d3.line()(run.map(p => [mx(p[0]), my(p[1])]))).attr("fill", "none")
          .attr("stroke", WATER).attr("stroke-width", 1.2).attr("opacity", 0.75 * shoreA);
      txt(m, mx(-12500), my(12000), "THE FORMER KAKHOVKA RESERVOIR", {size: 12, fill: "#6f97ad", a: shoreA, ls: "0.14em"});
      const plantA = ease(ramp(t, [0.4, 1.4]));
      for (const [p, label, dx] of [[D.map.plant, "ZAPORIZHZHIA NPP", -12], [D.map.tpp, "THERMAL PLANT", 12]]) {
        m.append("rect").attr("x", mx(p[0]) - 4).attr("y", my(p[1]) - 4).attr("width", 8).attr("height", 8).attr("fill", "#fff").attr("opacity", plantA);
        txt(m, mx(p[0]) + dx, my(p[1]) + 22, label, {size: 12, anchor: dx < 0 ? "end" : "start", a: plantA});
      }
    }
    // the lines: on the map, then unrolled like a tape into upright bars (each span turned upright, from the
    // switchyard out, its length kept)
    if (tau < 1) D.lines.forEach(ln => {
      const n = ln.plan.filter(p => p[2] <= grown + 1e-6).length;
      if (n < 2) return;
      const e = ease(tau), k = lerp(ms, ky(ln), e);
      let x = lerp(mx(ln.plan[0][0]), X0, e), y = lerp(my(ln.plan[0][1]), by(ln, 0), e);
      const pos = [[x, y]];
      for (let j = 1; j < n; j++) {
        const [ax, ay, as] = ln.plan[j - 1], [px, py, ps] = ln.plan[j];
        const u = ease(clamp01((tau - 0.45 * as / D.show_m) / 0.55));
        const th0 = Math.atan2(py - ay, px - ax);
        const dth = Math.atan2(Math.sin(Math.PI / 2 - th0), Math.cos(Math.PI / 2 - th0));
        const th = th0 + dth * u, len = (ps - as) * k;
        x += len * Math.cos(th); y -= len * Math.sin(th);
        pos.push([x, y]);
      }
      const lg = g.append("g").attr("filter", "url(#glow)");
      lg.append("path").attr("d", d3.line()(pos)).attr("fill", "none").attr("stroke", COL[ln.kv]).attr("stroke-width", 3.2)
        .attr("stroke-linecap", "round").attr("stroke-linejoin", "round");
      lg.append("path").attr("d", d3.line()(pos)).attr("fill", "none").attr("stroke", CORE[ln.kv]).attr("stroke-width", 1.1);
      const tip = pos[pos.length - 1];
      if (mapA > 0.01) txt(g, tip[0] + 10, tip[1] - 8, ln.label, {size: 13, a: mapA * ease(ramp(t, [1.2, 2.2]))});
    });

    // each ribbon: its name, the plant and the two sides of the river, left of the record
    const lab = g.append("g").attr("opacity", bandsA);
    D.lines.forEach(ln => {
      const r = rib(ln), yf = by(ln, ln.front_m);
      txt(lab, X0 - 24, r.top - 22, ln.label, {size: 18, fill: COL[ln.kv], anchor: "end"});
      txt(lab, X0 - 24, by(ln, 0) + 4, ln.record === "Dniprovska" ? "THE PLANT" : "THE THERMAL PLANT", {size: 11, fill: GREY, anchor: "end"});
      txt(lab, X0 - 24, yf + 4, "THE DNIPRO · FRONT", {size: 11, fill: "#7fa9c0", anchor: "end"});
      txt(lab, X0 - 24, yf + 22, "OCCUPIED ↓", {size: 10, fill: FAINT, anchor: "end"});
      txt(lab, X0 - 24, yf - 12, "UKRAINIAN-HELD ↑", {size: 10, fill: FAINT, anchor: "end"});
      txt(lab, X0 - 24, by(ln, ln.shown_m) + 4, `${Math.round(ln.shown_m / 1000)} KM${ln.cut ? ", THE LINE GOES ON ↑" : ""}`, {size: 10, fill: FAINT, anchor: "end"});
    });

    // the river across each ribbon: the reservoir to the dam, then the drained bed and the Dnipro's channel (the front)
    D.lines.forEach(ln => {
      const ys = by(ln, ln.shores.south_m), yn = by(ln, ln.shores.north_m), yf = by(ln, ln.front_m);
      const xd = sx(Math.min(xN, xc(dam)), c);
      chart.append("rect").attr("x", x0).attr("y", yn).attr("width", Math.max(0, xd - x0)).attr("height", ys - yn)
        .attr("fill", WATER).attr("opacity", 0.3 * bandsA);
      if (xN > xc(dam)) {
        chart.append("rect").attr("x", xd).attr("y", yn).attr("width", head - xd).attr("height", ys - yn).attr("fill", BED).attr("opacity", 0.14);
        chart.append("line").attr("x1", xd).attr("x2", head).attr("y1", yf).attr("y2", yf).attr("stroke", "#fff")
          .attr("stroke-dasharray", "3,4").attr("opacity", 0.4);
      }
      for (const s of [0, ln.shown_m])
        chart.append("line").attr("x1", x0).attr("x2", head).attr("y1", by(ln, s)).attr("y2", by(ln, s)).attr("stroke", "#fff").attr("opacity", 0.14 * bandsA);
    });
    // the record left behind: lit while connected, dotted where unreported, dark while cut
    D.lines.forEach(ln => {
      const y1 = by(ln, ln.shown_m), y0 = by(ln, 0);
      for (const [a, b, s] of ln.states) {
        const xa = xc(dn(a)), xb = Math.min(xc(dn(b)), xN);
        if (xb <= xa || s === "off") continue;
        chart.append("rect").attr("x", sx(xa, c)).attr("y", y1).attr("width", Math.max(0.6, (xb - xa) * c.k)).attr("height", y0 - y1)
          .attr("fill", s === "on" ? COL[ln.kv] : "url(#dots)").attr("opacity", s === "on" ? 0.32 : 1);
      }
    });
    // the complete losses of off-site power: a tick through both ribbons; those lasting days a pale band
    let count = 0;
    const ytop = RIB.Dniprovska.top - 6, ybot = RIB["Ferosplavna-1"].top + RIB["Ferosplavna-1"].h + 6;
    for (const L of D.losses) {
      const a = dn(L.at);
      if (a > now) continue;
      count = Math.max(count, L.n);
      if (!L.until) {
        const x = sx(xc(a + 0.5), c);
        chart.append("line").attr("x1", x).attr("x2", x).attr("y1", ytop).attr("y2", ybot).attr("stroke", "#fff").attr("opacity", 0.4);
      } else {
        const xa = sx(xc(a), c), xb = sx(Math.min(xc(dn(L.until)), xN), c);
        chart.append("rect").attr("x", xa).attr("y", ytop).attr("width", Math.max(1, xb - xa)).attr("height", ybot - ytop).attr("fill", "#fff").attr("opacity", 0.07);
      }
    }
    // the repair truces: the stretch their sources name, hatched with a dashed edge (a region, not a point)
    for (const tr of D.truces) {
      const a = dn(tr.from);
      if (a > now) continue;
      const ln = D.lines.find(l => l.record === tr.line);
      const b = Math.min(dn(tr.until) + 1, now);
      const xa = sx(xc(a), c), xb = Math.max(xa + 3, sx(xc(b), c)), ya = by(ln, tr.to_m), yb = by(ln, tr.from_m);
      const r = chart.append("rect").attr("x", xa).attr("y", ya).attr("width", xb - xa).attr("height", yb - ya)
        .attr("fill", "url(#hatch)").attr("stroke", "#fff").attr("stroke-dasharray", "4,3").attr("stroke-width", 1.3);
      if (tr.open_end) r.attr("mask", "url(#openEnd)");
      const on = hold && hold.why.includes(`truce ${tr.n}`);
      txt(chart, xa, ya - 8, String(tr.n), {size: 13, ls: 0, a: on ? 0 : 0.85});
      if (on) {
        const u = clamp01((t - hold.arrive_s + 0.2) / 0.4);
        g.append("line").attr("x1", xb + 2).attr("x2", head + 22).attr("y1", (ya + yb) / 2).attr("y2", (ya + yb) / 2)
          .attr("stroke", "#fff").attr("opacity", 0.5 * u);
        boxed(g, head + 30, (ya + yb) / 2 + 5, `TRUCE ${tr.n} · ${up(fmtMon(utc(a)))} · ${WHERE[tr.region]}`, {size: 15, a: u});
      }
    }
    // the bars on the date: lit and glowing while connected, the bare wire while cut, dotted if unreported
    if (tau >= 1) D.lines.forEach(ln => {
      const y1 = by(ln, ln.shown_m), y0 = by(ln, 0), s = state(ln, now);
      const bar = g.append("g").attr("opacity", 1 - over);
      if (s === "on") {
        const lg = bar.append("g").attr("filter", "url(#glow)");
        lg.append("line").attr("x1", head).attr("x2", head).attr("y1", y0).attr("y2", y1).attr("stroke", COL[ln.kv]).attr("stroke-width", 4).attr("stroke-linecap", "round");
        lg.append("line").attr("x1", head).attr("x2", head).attr("y1", y0).attr("y2", y1).attr("stroke", CORE[ln.kv]).attr("stroke-width", 1.3);
      } else {
        bar.append("line").attr("x1", head).attr("x2", head).attr("y1", y0).attr("y2", y1).attr("stroke", "#000").attr("stroke-width", 3.4);
        bar.append("line").attr("x1", head).attr("x2", head).attr("y1", y0).attr("y2", y1).attr("stroke", STEEL[ln.kv])
          .attr("stroke-width", 1.4).attr("stroke-dasharray", s === "unknown" ? "2,4" : null);
      }
    });
    // the time axis under the ribbons: years, months in the last year (drawn six times larger, said once)
    const ax = g.append("g").attr("opacity", bandsA).attr("clip-path", "url(#chart)");
    const yAx = ybot + 26;
    for (let yr = 2022; yr <= 2026; yr++) for (let mo = 0; mo < 12; mo++) {
      const d = Math.round(Date.UTC(yr, mo, 1) / DAY);
      if (d < d0 || xc(d) > xN + 0.5 || (d < sc && mo !== 0)) continue;
      const x = sx(xc(d), c);
      ax.append("line").attr("x1", x).attr("x2", x).attr("y1", yAx - 12).attr("y2", yAx - 6).attr("stroke", GREY);
      const label = mo === 0 ? String(yr) : (over < 0.5 ? up(d3.utcFormat("%b")(utc(d))) : "");
      if (label) txt(ax, x, yAx + 8, label, {size: mo === 0 ? 13 : 10, fill: GREY, anchor: "middle", ls: 0});
    }
    if (xN >= xc(sc)) {
      const x = sx(xc(sc), c);
      ax.append("line").attr("x1", x).attr("x2", x).attr("y1", ytop).attr("y2", yAx - 6).attr("stroke", "#fff").attr("stroke-dasharray", "2,5").attr("opacity", 0.3);
      txt(ax, x + 6, yAx + 30, "FROM HERE, SIX TIMES THE SCALE", {size: 10, fill: GREY, a: 1 - over});
    }
    // the date over the bars, and at a held moment what happened
    if (tau >= 1 && over < 1) {
      const dl = g.append("g").attr("opacity", 1 - over);
      dl.append("line").attr("x1", head).attr("x2", head).attr("y1", 196).attr("y2", ytop).attr("stroke", "#fff").attr("opacity", 0.25);
      boxed(dl, head, 186, up(fmtDay(utc(Math.floor(now)))), {size: 22, anchor: "middle"});
      const cap = hold && (hold.why.includes("dam") ? D.dam.label : (D.captions.find(cp => dn(cp.at) === dn(hold.day)) || {}).text);
      if (cap) {
        const u = clamp01((t - hold.arrive_s + 0.2) / 0.4) * clamp01((hold.arrive_s + hold.hold_s + 0.3 - t) / 0.4);
        const cg = boxed(dl, head, yAx + 76, up(cap), {size: 18, anchor: "middle", a: u});
        const bb = cg.node().getBBox();   // kept on screen: a long caption near the start slides right
        if (bb.x < 40) cg.attr("transform", `translate(${40 - bb.x},0)`);
      }
    }
    // the count, top right
    const hud = g.append("g").attr("opacity", bandsA);
    txt(hud, XR, 70, "COMPLETE LOSSES OF OFF-SITE POWER", {size: 11, fill: GREY, anchor: "end"});
    txt(hud, XR, 116, String(count), {size: 40, weight: 400, ls: 0, anchor: "end"});
    // the legend, bottom left; the credit, bottom right
    const lg = g.append("g").attr("opacity", bandsA * 0.9);
    let x = 60;
    for (const [k, label] of [["on", "CONNECTED"], ["off", "CUT"], ["dots", "NOT REPORTED WHICH LINE"], ["hatch", "REPAIR TRUCE, WHERE ITS SOURCES SAY"], ["loss", "ALL LINES LOST"]]) {
      if (k === "on") lg.append("rect").attr("x", x).attr("y", 1026).attr("width", 22).attr("height", 12).attr("fill", COL[750]).attr("opacity", 0.45);
      if (k === "off") lg.append("line").attr("x1", x).attr("x2", x + 22).attr("y1", 1032).attr("y2", 1032).attr("stroke", STEEL[750]).attr("stroke-width", 1.4);
      if (k === "dots") lg.append("rect").attr("x", x).attr("y", 1026).attr("width", 22).attr("height", 12).attr("fill", "url(#dots)");
      if (k === "hatch") lg.append("rect").attr("x", x).attr("y", 1026).attr("width", 22).attr("height", 12).attr("fill", "url(#hatch)").attr("stroke", "#fff").attr("stroke-dasharray", "3,2");
      if (k === "loss") lg.append("line").attr("x1", x + 11).attr("x2", x + 11).attr("y1", 1024).attr("y2", 1040).attr("stroke", "#fff").attr("opacity", 0.6);
      const e = txt(lg, x + 32, 1036, label, {size: 11, fill: GREY});
      x += 32 + e.node().getComputedTextLength() + 40;
    }
    txt(g, XR, 1036, "LINES © OPENSTREETMAP CONTRIBUTORS · RECORD: IAEA, NEWS REPORTS · RIVER: COPERNICUS SENTINEL-2",
        {size: 9.5, fill: FAINT, a: bandsA, anchor: "end"});

    // fade in from black, out to black
    const black = 1 - ease(ramp(t, T.fade_in)) * (1 - ease(ramp(t, T.fade_out)));
    if (black > 0.001) g.append("rect").attr("width", W).attr("height", H).attr("fill", "#050505").attr("opacity", black);
  };

  document.fonts.ready.then(() => { window.draw(0); window.ready = true; });
})();
