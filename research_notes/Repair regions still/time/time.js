// The repairs in time (repair_time.py): option 1 arcs, 2 calendar, 3 deficit. One still each, 1920×1080.
window.ERRS = [];
window.addEventListener("error", e => window.ERRS.push(String(e.message)));

const W = 1920, H = 1080, D = window.DATA, OPT = new URLSearchParams(location.search).get("opt") || "arcs";
const rgb = a => `rgb(${a.join(",")})`;
const Y750 = rgb(D.rgb["750"]), Y330 = rgb(D.rgb["330"]);
const GROUND = "rgb(34,34,35)", UNLIT = "#0b0b0c", STEEL = "#4a4d52", GREY = "#96969a", FAINT = "#6e6e70";
const pd = d3.utcParse("%Y-%m-%d");
const DAY = 864e5;
const days = D.record.days.map(x => ({...x, t: pd(x.d)}));
const reps = D.repairs.map(r => ({...r, t: pd(r.when), c: r.cut ? pd(r.cut) : null}));
const NAMES = {fero: "FEROSPLAVNA-1", dnip: "DNIPROVSKA", yards: "THE SWITCHYARDS' LINKS", kakh: "A 750 KV LINE, NOT NAMED"};
const fmt = d3.utcFormat("%-d %B %Y");

const svg = d3.select("body").append("svg").attr("width", W).attr("height", H);
const defs = svg.append("defs");
// unreported: which lines were cut isn't said (hatched, the zoom-out's dotted)
defs.append("pattern").attr("id", "hatch").attr("patternUnits", "userSpaceOnUse").attr("width", 6).attr("height", 6)
  .attr("patternTransform", "rotate(45)")
  .append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", 6).attr("stroke", "#9a9a9c").attr("stroke-width", 1.4);

function head(text, sub) {
  svg.append("text").attr("class", "head").attr("x", 40).attr("y", 82).text(text);
  if (sub) svg.append("text").attr("class", "tiny").attr("x", 42).attr("y", 116).text(sub);
}
function foot(text) {
  svg.append("rect").attr("x", 0).attr("y", H - 46).attr("width", W).attr("height", 46).attr("fill", "#000");
  svg.append("text").attr("class", "foot").attr("x", 24).attr("y", H - 18).text(text);
}
function tag(text, x, y, anchor = "start") {
  const g = svg.append("g");
  const t = g.append("text").attr("class", "tag").attr("x", x).attr("y", y).attr("text-anchor", anchor).text(text);
  const b = t.node().getBBox();
  g.insert("rect", "text").attr("x", b.x - 6).attr("y", b.y - 3).attr("width", b.width + 12).attr("height", b.height + 6).attr("fill", "#000");
  return g;
}
function tiny(text, x, y, anchor = "start", cls = "tiny") {
  return svg.append("text").attr("class", cls).attr("x", x).attr("y", y).attr("text-anchor", anchor).text(text);
}
// who did the work: white Ukrainian crews, grey the Russian side, half and half both, a faint ring not said;
// a ring round it: under an IAEA-brokered ceasefire
function who(g, r, x, y, s = 4.2) {
  if (r.truce) g.append("circle").attr("cx", x).attr("cy", y).attr("r", s + 4).attr("fill", "none").attr("stroke", "#fff").attr("stroke-width", 1.1);
  if (r.side === "ukrainian") g.append("circle").attr("cx", x).attr("cy", y).attr("r", s).attr("fill", "#fff");
  else if (r.side === "russian") g.append("circle").attr("cx", x).attr("cy", y).attr("r", s).attr("fill", GREY);
  else if (r.side === "both") {
    g.append("circle").attr("cx", x).attr("cy", y).attr("r", s).attr("fill", GREY);
    g.append("path").attr("d", `M${x},${y - s}A${s},${s} 0 0 0 ${x},${y + s}Z`).attr("fill", "#fff");
  } else g.append("circle").attr("cx", x).attr("cy", y).attr("r", s - 0.6).attr("fill", GROUND).attr("stroke", FAINT).attr("stroke-width", 1.4);
}
function whoKey(x, y) {      // the marks' key, in a row
  const g = svg.append("g");
  const items = [["ukrainian", "UKRAINIAN CREWS"], ["russian", "THE RUSSIAN SIDE"], ["both", "BOTH"], ["unknown", "NOT SAID"]];
  let cx = x;
  for (const [side, label] of items) {
    who(g, {side}, cx, y - 4);
    const t = tiny(label, cx + 11, y);
    cx += 11 + t.node().getComputedTextLength() + 26;
  }
  who(g, {side: "ukrainian", truce: true}, cx + 4, y - 4);
  tiny("UNDER AN IAEA-BROKERED CEASEFIRE", cx + 19, y);
}
function recordEnd(x, y0, y1) {
  const last = days[days.length - 1], xe = x(+last.t + DAY);
  svg.append("line").attr("x1", xe).attr("x2", xe).attr("y1", y0).attr("y2", y1).attr("stroke", "#8c8c8e").attr("stroke-dasharray", "1 3");
  tiny("THE RECORD'S LAST REPORT · " + fmt(last.t).toUpperCase(), xe - 4, y0 + 10, "end", "tiny dim")
    .attr("stroke", GROUND).attr("stroke-width", 6).attr("paint-order", "stroke");
}
function years(x, y0, y1, label = true) {
  for (let yr = 2023; yr <= 2026; yr++) {
    const xx = x(Date.UTC(yr, 0, 1));
    svg.append("line").attr("x1", xx).attr("x2", xx).attr("y1", y0).attr("y2", y1).attr("stroke", "#5a5a5c").attr("stroke-dasharray", "3 3");
    if (label) tiny(String(yr), xx + 4, y0 + 10, "start", "tiny dim");
  }
}
const stats = (() => {
  const all10 = days.filter(d => d.on === 10).length, none = days.filter(d => d.on === 0 && d.unk === 0).length;
  const oneTwo = days.filter(d => d.unk === 0 && (d.on === 1 || d.on === 2)).length;
  const unk = days.filter(d => d.unk > 0).length;
  const last = days.findIndex(d => d.d >= "2022-12-29");
  const maxAfter = d3.max(days.slice(last), d => d.on + d.unk);
  return {n: days.length, all10, none, oneTwo, unk, maxAfter, lossN: D.record.losses.length};
})();

// ---- 1: arcs
function arcs() {
  const x = d3.scaleUtc().domain([pd("2022-02-24"), pd(D.axis_end)]).range([200, 1860]);
  const y0 = 600, rib = 5, base = 13;
  head("42 repairs: from the cut to the line back");
  years(x, 150, 960);
  recordEnd(x, 176, 960);
  tiny("24 FEBRUARY 2022", 200, 160, "start", "tiny dim");
  // the two lines' record as ribbons: lit while connected, dark while cut, dotted where unreported
  const ribbon = (key, ya, col) => {
    let i = 0;
    while (i < days.length) {
      let j = i;
      while (j + 1 < days.length && days[j + 1][key] === days[i][key]) j++;
      const xa = x(days[i].t), xb = x(+days[j].t + DAY), s = days[i][key];
      if (s === "on") svg.append("rect").attr("x", xa).attr("y", ya).attr("width", xb - xa).attr("height", rib).attr("fill", col);
      else if (s === "off") svg.append("rect").attr("x", xa).attr("y", ya + rib / 2 - 0.75).attr("width", xb - xa).attr("height", 1.5).attr("fill", STEEL);
      else svg.append("line").attr("x1", xa).attr("x2", xb).attr("y1", ya + rib / 2).attr("y2", ya + rib / 2)
        .attr("stroke", GREY).attr("stroke-width", 1.6).attr("stroke-dasharray", "1.6 3.4");
      i = j + 1;
    }
  };
  ribbon("fero", y0 - 2 - rib, Y330);
  ribbon("dnip", y0 + 2, Y750);
  for (const l of D.record.losses) {        // a complete loss of off-site power: a tick through both
    const xa = x(pd(l.at)), xb = l.until ? x(+pd(l.until) + DAY) : xa;
    svg.append("rect").attr("x", xa - 0.6).attr("y", y0 - 10).attr("width", Math.max(1.2, xb - xa)).attr("height", 20)
      .attr("fill", "#fff").attr("opacity", 0.55);
  }
  const g = svg.append("g");
  const above = r => r.line === "fero" || r.line === "yards";
  const col = r => r.line === "fero" ? Y330 : r.line === "dnip" ? Y750 : "#bdbdc0";
  const K = 2.6;
  const labels = [];
  for (const r of reps) {
    const up = above(r) ? -1 : 1, yb = y0 + up * base, x2 = x(r.t);
    if (r.c) {
      const x1 = x(r.c), rx = Math.max((x2 - x1) / 2, 1.5), ry = Math.max(rx * K, 7);
      g.append("path").attr("d", `M${x1},${yb}A${rx},${ry} 0 0 ${up < 0 ? 1 : 0} ${x1 + 2 * rx},${yb}`)
        .attr("fill", "none").attr("stroke", col(r)).attr("stroke-width", 2).attr("stroke-linecap", "round")
        .attr("stroke-dasharray", r.cut_month_only ? "5 4" : null);
      const ndays = Math.round((r.t - r.c) / DAY);
      if (ndays >= 45) labels.push({r, x: x1 + rx, y: yb + up * ry, up, ndays});
    } else {
      g.append("line").attr("x1", x2).attr("x2", x2).attr("y1", yb).attr("y2", yb + up * 9).attr("stroke", col(r)).attr("stroke-width", 1.4);
    }
  }
  for (const r of reps) {       // the marks on top of every arc
    const up = above(r) ? -1 : 1;
    who(g, r, x(r.t), y0 + up * base + (r.c ? 0 : up * 9) + up * 5);
  }
  for (const l of labels) {
    const extra = l.r.never ? " · REPAIRED, NEVER RECONNECTED" : "";
    const about = l.r.cut_month_only ? "ABOUT " : "";
    tiny(`${NAMES[l.r.line]} · ${about}${l.ndays} DAYS${extra}`, l.x, l.y + (l.up < 0 ? -10 : 20), "middle");
  }
  tag("FEROSPLAVNA-1 · 330 KV", 24, y0 - 64);
  tiny("AND THE LINKS TO IT AT THE SWITCHYARDS (GREY)", 24, y0 - 40, "start", "tiny dim");
  tag("DNIPROVSKA · 750 KV", 24, y0 + 72);
  tiny("ALONG THE AXIS EACH LINE'S RECORD: LIT WHILE CONNECTED;", 24, y0 + 96, "start", "tiny dim");
  tiny("WHERE ONE IS DARK, THE PLANT HUNG ON THE OTHER", 24, y0 + 114, "start", "tiny dim");
  const nc = reps.filter(r => r.c).length;
  tiny(`${nc} WITH A PUBLISHED CUT DATE: AN ARC · ${reps.length - nc} WITHOUT: A MARK ONLY`, 1880, 116, "end");
  whoKey(1000, 990);
  foot("EACH ARC FROM THE CUT TO THE REPAIR AS THE SOURCES GIVE THEM: ITS WIDTH IS THE WAIT (DASHED: ONLY THE MONTH OF THE CUT GIVEN) · " +
       "DOTTED: THE REPORTS DON'T SAY WHICH LINE · PALE TICKS: COMPLETE LOSSES OF OFF-SITE POWER · NO PLACES SHOWN");
}

// ---- 2: calendar
function calendar() {
  head("Every day of the war: the plant's lines connected");
  const P = 21, C = 18, X0 = 130, Y0 = 150, BH = 7 * P + 22;
  const lit = d => {          // a day's colour: how many of the ten lines were connected at its end
    if (d.on === 0) return UNLIT;
    const f = d.on >= 10 ? 1 : d.on === 2 ? 0.66 : 0.36;
    const base = d.on >= 10 ? [255, 241, 170] : D.rgb["750"];
    return rgb(base.map((c, i) => Math.round(18 + (c - 18) * f)));
  };
  const byDay = new Map(days.map(d => [d.d, d]));
  const end = pd(D.axis_end), first = days[0].t;
  const fmtD = d3.utcFormat("%Y-%m-%d");
  const cell = t => {         // weeks from Monday, the year's first week holding 1 January
    const yr = t.getUTCFullYear(), jan1 = Date.UTC(yr, 0, 1), dow0 = (new Date(jan1).getUTCDay() + 6) % 7;
    const n = Math.round((t - jan1) / DAY) + dow0;
    return {x: X0 + Math.floor(n / 7) * P, y: Y0 + (yr - 2022) * BH + (n % 7) * P};
  };
  const g = svg.append("g");
  for (let yr = 2022; yr <= 2026; yr++) svg.append("text").attr("class", "year").attr("x", 40).attr("y", Y0 + (yr - 2022) * BH + 16).text(yr);
  const months = d3.utcFormat("%b");
  for (let m = 0; m < 12; m++) {
    const c = cell(new Date(Date.UTC(2022, m, 1)));
    tiny(months(new Date(Date.UTC(2022, m, 1))), c.x, Y0 - 12, "start", "tiny dim");
  }
  for (let t = new Date(Date.UTC(2022, 0, 1)); t <= Date.UTC(2026, 11, 31); t = new Date(+t + DAY)) {
    const c = cell(t), d = byDay.get(fmtD(t));
    if (d) {
      g.append("rect").attr("x", c.x).attr("y", c.y).attr("width", C).attr("height", C).attr("fill", lit(d));
      if (d.unk) g.append("rect").attr("x", c.x).attr("y", c.y).attr("width", C).attr("height", C).attr("fill", "url(#hatch)").attr("opacity", d.on ? 0.55 : 0.8);
      if (d.loss && d.on > 0) g.append("rect").attr("x", c.x + 5).attr("y", c.y + 5).attr("width", 8).attr("height", 8).attr("fill", UNLIT);
    } else if (t >= first && t <= end) {   // after the record's last report, to the last repair
      g.append("rect").attr("x", c.x + 0.5).attr("y", c.y + 0.5).attr("width", C - 1).attr("height", C - 1).attr("fill", "none").attr("stroke", "#4a4a4c");
    } else {
      g.append("rect").attr("x", c.x).attr("y", c.y).attr("width", C).attr("height", C).attr("fill", "#2a2a2b");
    }
  }
  for (const r of reps) { const c = cell(r.t); who(g, r, c.x + C / 2, c.y + C / 2, 4); }
  // the right column: the key and the counts
  const KX = 1370;
  let ky = 190;
  tiny("LINES CONNECTED AT THE END OF THE DAY", KX, ky);
  ky += 22;
  for (const [n, label] of [[10, "ALL TEN"], [2, "TWO"], [1, "ONE"], [0, "NONE: A COMPLETE LOSS OF OFF-SITE POWER, OR ISLAND MODE"]]) {
    svg.append("rect").attr("x", KX).attr("y", ky).attr("width", C).attr("height", C).attr("fill", lit({on: n}));
    tiny(label, KX + C + 12, ky + 14);
    ky += 28;
  }
  svg.append("rect").attr("x", KX).attr("y", ky).attr("width", C).attr("height", C).attr("fill", lit({on: 1}));
  svg.append("rect").attr("x", KX).attr("y", ky).attr("width", C).attr("height", C).attr("fill", "url(#hatch)").attr("opacity", 0.55);
  tiny("LINES CUT AND REPAIRED; THE REPORTS DON'T SAY WHICH", KX + C + 12, ky + 14);
  ky += 28;
  svg.append("rect").attr("x", KX).attr("y", ky).attr("width", C).attr("height", C).attr("fill", lit({on: 1}));
  svg.append("rect").attr("x", KX + 5).attr("y", ky + 5).attr("width", 8).attr("height", 8).attr("fill", UNLIT);
  tiny("A COMPLETE LOSS RESTORED WITHIN THE DAY", KX + C + 12, ky + 14);
  ky += 28;
  svg.append("rect").attr("x", KX + 0.5).attr("y", ky + 0.5).attr("width", C - 1).attr("height", C - 1).attr("fill", "none").attr("stroke", "#4a4a4c");
  tiny("AFTER THE RECORD'S LAST REPORT", KX + C + 12, ky + 14);
  ky += 52;
  tiny("A DOT: A REPAIR, BY WHO DID THE WORK", KX, ky);
  const kg = svg.append("g");
  for (const [side, label, truce] of [["ukrainian", "UKRAINIAN CREWS"], ["russian", "THE RUSSIAN SIDE"], ["both", "BOTH"],
                                       ["unknown", "NOT SAID"], ["ukrainian", "RINGED: UNDER AN IAEA-BROKERED CEASEFIRE", true]]) {
    ky += 26;
    who(kg, {side, truce}, KX + C / 2, ky - 4, 4);
    tiny(label, KX + C + 12, ky);
  }
  ky += 64;
  const big = (n, label) => {
    svg.append("text").attr("x", KX).attr("y", ky).attr("fill", "#fff").style("font-size", "40px").text(n.toLocaleString("en-GB"));
    tiny(label, KX + 4, ky + 22);
    ky += 78;
  };
  big(stats.n, "DAYS IN THE RECORD, 24 FEBRUARY 2022 TO " + fmt(days[days.length - 1].t).toUpperCase());
  big(stats.all10, "WITH ALL TEN LINES");
  big(stats.oneTwo, "WITH ONLY ONE OR TWO");
  big(reps.length, "REPAIRS");
  foot("ONE SQUARE PER DAY, A ROW PER WEEKDAY · LIT BY HOW MANY OF THE PLANT'S TEN LINES WERE CONNECTED AT THE END OF THE DAY, AS THE " +
       "IAEA AND ENERGOATOM REPORTED · NO PLACES SHOWN");
}

// ---- 3: deficit
function deficit() {
  head("Ten lines, and what 42 repairs kept connected");
  const x = d3.scaleUtc().domain([pd("2022-02-24"), pd(D.axis_end)]).range([200, 1860]);
  const y = d3.scaleLinear().domain([0, 10]).range([930, 200]);
  const step = (acc) => {     // a step area: each day's value held to the next day
    const pts = [];
    for (const d of days) { const v = acc(d); pts.push([x(d.t), v], [x(+d.t + DAY), v]); }
    return pts;
  };
  const last = x(+days[days.length - 1].t + DAY);
  const area = (lo, hi) => d3.area().x(p => p[0]).y0((p, i) => y(lo[i][1])).y1((p, i) => y(hi[i][1]))(lo);
  const on = step(d => d.on), top = step(d => d.on + d.unk), ten = step(() => 10), zero = step(() => 0);
  // the deficit: lines cut off, from what was connected (or might have been) up to ten
  svg.append("path").attr("d", area(top, ten)).attr("fill", "#121213");
  svg.append("path").attr("d", area(on, top)).attr("fill", "url(#hatch)").attr("opacity", 0.6);
  svg.append("path").attr("d", area(zero, on)).attr("fill", Y750).attr("opacity", 0.9);
  for (let v = 1; v < 10; v++) svg.append("line").attr("x1", 200).attr("x2", last).attr("y1", y(v)).attr("y2", y(v))
    .attr("stroke", "#2c2c2e").attr("stroke-width", 1);
  svg.append("line").attr("x1", 200).attr("x2", last).attr("y1", y(10)).attr("y2", y(10)).attr("stroke", "#fff").attr("stroke-dasharray", "4 4");
  tiny("THE PLANT'S TEN LINES: FOUR 750 KV, SIX 330 KV", 204, y(10) - 10);
  for (const v of [0, 1, 2, 5, 10]) tiny(String(v), 188, y(v) + 4, "end", "tiny dim");
  years(x, y(10) + 16, y(0), false);
  for (let yr = 2022; yr <= 2026; yr++) tiny(String(yr), x(Date.UTC(yr, yr === 2022 ? 1 : 0, yr === 2022 ? 24 : 1)) + 4, y(0) + 22, "start", "tiny dim");
  // a complete loss restored within the day: a notch down to none
  for (const d of days) if (d.loss && d.on > 0) svg.append("rect").attr("x", x(d.t)).attr("y", y(d.on)).attr("width", Math.max(1.4, x(+d.t + DAY) - x(d.t)))
    .attr("height", y(0) - y(d.on)).attr("fill", "#121213");
  const g = svg.append("g");
  const byDay = new Map(days.map(d => [d.d, d]));
  for (const r of reps) {
    const d = byDay.get(r.when);
    const v = d ? d.on + d.unk * 0 : 0;
    who(g, r, x(r.t), y(Math.max(v, 0)) - 12, 3.8);
  }
  tag("LINES CUT OFF", x(pd("2024-06-01")), y(6.2), "middle");
  tiny(`SINCE 29 DECEMBER 2022 NEVER MORE THAN ${stats.maxAfter} OF THE TEN CONNECTED`, x(pd("2024-06-01")), y(6.2) + 30, "middle");
  tag("MARCH TO DECEMBER 2022", x(pd("2022-03-04")) + 8, y(9.2));
  tag("LINES CUT AND REPAIRED; THE REPORTS", x(pd("2022-03-04")) + 8, y(9.2) + 24);
  tag("DON'T SAY WHICH (HATCHED)", x(pd("2022-03-04")) + 8, y(9.2) + 48);
  recordEnd(x, y(10) + 16, y(0));
  whoKey(200, 1000);
  foot("HOW MANY OF THE PLANT'S TEN LINES WERE CONNECTED AT THE END OF EACH DAY, AS THE IAEA AND ENERGOATOM REPORTED (HATCHED: UNREPORTED; " +
       "NOTCHES: COMPLETE LOSSES RESTORED WITHIN THE DAY) · A DOT PER REPAIR ON ITS DAY · NO PLACES SHOWN");
}


// ---- shared by the new options
const litOf = n => {          // the calendar's shade: how many of the ten lines were connected
  if (n === 0) return UNLIT;
  const f = n >= 10 ? 1 : n === 2 ? 0.66 : 0.36;
  const base = n >= 10 ? [255, 241, 170] : D.rgb["750"];
  return rgb(base.map((c, i) => Math.round(18 + (c - 18) * f)));
};
const SIDES = [["ukrainian", "UKRAINIAN CREWS"], ["russian", "THE RUSSIAN SIDE"], ["both", "BOTH"], ["unknown", "NOT SAID"]];
const SIDE_FILL = {ukrainian: "#f2f2f2", russian: "#6a6a6e", both: "#b0b0b4", unknown: "#5a5a5c"};
const LINES4 = [["fero", "FEROSPLAVNA-1 · 330 KV"], ["dnip", "DNIPROVSKA · 750 KV"], ["yards", "THE SWITCHYARDS' LINKS"], ["kakh", "A 750 KV LINE, NOT NAMED"]];
const byDayAll = new Map(days.map(d => [d.d, d]));
const lastDay = days[days.length - 1];
function keyRows(KX, ky, rows) {   // [fill or fn(g, x, y), label]
  for (const [paint, label] of rows) {
    if (typeof paint === "function") paint(svg, KX, ky);
    else svg.append("rect").attr("x", KX).attr("y", ky).attr("width", 18).attr("height", 18).attr("fill", paint);
    tiny(label, KX + 30, ky + 13);
    ky += 27;
  }
  return ky;
}
function sideKey(KX, ky) {
  tiny("A DOT: A REPAIR, BY WHO DID THE WORK", KX, ky);
  for (const [side, label, truce] of [...SIDES, ["ukrainian", "RINGED: UNDER AN IAEA-BROKERED CEASEFIRE", true]]) {
    ky += 26;
    who(svg, {side, truce}, KX + 9, ky - 4, 4);
    tiny(label, KX + 30, ky);
  }
  return ky;
}
const hatchCell = (g, x, y, w, h, op = 0.6) => g.append("rect").attr("x", x).attr("y", y).attr("width", w).attr("height", h)
  .attr("fill", "url(#hatch)").attr("opacity", op);

// ---- 4: parallel sets
function parsets() {
  head("42 repairs, five ways at once");
  const yr = r => r.when.slice(0, 4);
  const cols = [
    {name: "WHO DID THE WORK", get: r => r.side, cats: SIDES},
    {name: "THE YEAR", get: yr, cats: ["2022", "2023", "2024", "2025", "2026"].map(y => [y, y])},
    {name: "WHICH LINE", get: r => r.line, cats: LINES4},
    {name: "UNDER AN IAEA-BROKERED CEASEFIRE?", get: r => r.truce ? "t" : "n", cats: [["t", "YES"], ["n", "NO"]]},
    {name: "A PLACE PUBLISHED?", get: r => r.placed ? "p" : "n", cats: [["p", "A SIDE, BANK OR STRETCH"], ["n", "NONE"]]},
  ];
  const X = [150, 560, 970, 1380, 1790], TOP = 190, BOT = 930, GAP = 16, BW = 10;
  const unit = (BOT - TOP - GAP * 4) / reps.length;
  // each column's categories stacked, in order
  const seg = cols.map(c => {
    const m = new Map(); let y = TOP;
    const gap = (BOT - TOP - unit * reps.length) / Math.max(1, c.cats.filter(([k]) => reps.some(r => c.get(r) === k)).length - 1);
    for (const [k, label] of c.cats) {
      const n = reps.filter(r => c.get(r) === k).length;
      if (!n) continue;
      m.set(k, {y, n, label, h: n * unit});
      y += n * unit + gap;
    }
    return m;
  });
  const sideOrder = Object.fromEntries(SIDES.map(([k], i) => [k, i]));
  const ribbons = svg.append("g");
  for (let i = 0; i < cols.length - 1; i++) {
    const a = cols[i], b = cols[i + 1], ia = Object.fromEntries(a.cats.map(([k], j) => [k, j])), ib = Object.fromEntries(b.cats.map(([k], j) => [k, j]));
    // left ends ordered by the right category (then who), right ends by the left category (then who): few crossings
    const L = [...reps].sort((p, q) => ia[a.get(p)] - ia[a.get(q)] || ib[b.get(p)] - ib[b.get(q)] || sideOrder[p.side] - sideOrder[q.side] || p.when.localeCompare(q.when));
    const R = [...reps].sort((p, q) => ib[b.get(p)] - ib[b.get(q)] || ia[a.get(p)] - ia[a.get(q)] || sideOrder[p.side] - sideOrder[q.side] || p.when.localeCompare(q.when));
    const yl = new Map(), yr2 = new Map(), off = {};
    for (const r of L) { const k = a.get(r); off[k] = off[k] || 0; yl.set(r, seg[i].get(k).y + off[k]); off[k] += unit; }
    const off2 = {};
    for (const r of R) { const k = b.get(r); off2[k] = off2[k] || 0; yr2.set(r, seg[i + 1].get(k).y + off2[k]); off2[k] += unit; }
    const x0 = X[i] + BW / 2, x1 = X[i + 1] - BW / 2, xm = (x0 + x1) / 2;
    for (const r of reps) {
      const y0 = yl.get(r), y1 = yr2.get(r), h = unit - 0.6;
      ribbons.append("path").attr("d", `M${x0},${y0}C${xm},${y0} ${xm},${y1} ${x1},${y1}L${x1},${y1 + h}C${xm},${y1 + h} ${xm},${y0 + h} ${x0},${y0 + h}Z`)
        .attr("fill", SIDE_FILL[r.side]).attr("opacity", {ukrainian: 0.34, russian: 0.75, both: 0.6, unknown: 0.3}[r.side]);
    }
  }
  cols.forEach((c, i) => {
    tiny(c.name, X[i], TOP - 26, i === 0 ? "start" : i === cols.length - 1 ? "end" : "middle");
    for (const [k, s] of seg[i]) {
      svg.append("rect").attr("x", X[i] - BW / 2).attr("y", s.y).attr("width", BW).attr("height", s.h - 0.6).attr("fill", "#fff");
      const right = i < 4;
      const t = tiny(`${s.label} · ${s.n}`, right ? X[i] + BW / 2 + 8 : X[i] - BW / 2 - 8, s.y + Math.min(s.h / 2, 30) + 4, right ? "start" : "end")
        .attr("stroke", GROUND).attr("stroke-width", 5).attr("paint-order", "stroke");
    }
  });
  foot("EACH REPAIR A RIBBON THROUGH FIVE COLUMNS, SHADED BY WHO DID THE WORK · THE LINE AS THE SOURCE NAMES IT (\"THE 330 KV LINE\": " +
       "FEROSPLAVNA-1) · WHERE: ONLY AS COARSE AS THE SOURCE, NEVER A TOWER OR A POINT · NO PLACES SHOWN");
}

// ---- 5: a dot per repair along time, a row per line, swarmed
function swarm() {
  head("42 repairs, one dot each");
  const x = d3.scaleUtc().domain([pd("2022-02-24"), pd(D.axis_end)]).range([300, 1860]);
  const rows = {fero: 330, dnip: 560, yards: 760, kakh: 900}, R = 8;
  years(x, 170, 960);
  tiny("24 FEBRUARY 2022", 300, 180, "start", "tiny dim");
  for (const [k, label] of LINES4) {
    svg.append("line").attr("x1", 300).attr("x2", 1860).attr("y1", rows[k]).attr("y2", rows[k]).attr("stroke", "#3c3c3e");
    tag(label, 24, rows[k] + 4);
  }
  const nodes = reps.map(r => ({r, x: x(r.t), y: rows[r.line], tx: x(r.t), ty: rows[r.line]}));
  const sim = d3.forceSimulation(nodes).force("x", d3.forceX(d => d.tx).strength(1)).force("y", d3.forceY(d => d.ty).strength(0.06))
    .force("c", d3.forceCollide(R + 2.5)).stop();
  for (let i = 0; i < 400; i++) sim.tick();
  const g = svg.append("g");
  for (const n of nodes) who(g, n.r, n.x, n.y, R);
  // the clusters, named by what the record says
  const note = (t0, t1, y, lines) => {
    const xa = x(pd(t0)), xb = x(pd(t1));
    svg.append("line").attr("x1", xa).attr("x2", xb).attr("y1", y).attr("y2", y).attr("stroke", "#8c8c8e");
    lines.forEach((l, i) => tiny(l, Math.min((xa + xb) / 2, 1860 - l.length * 4.6), y - 10 - (lines.length - 1 - i) * 17, "middle"));
  };
  const n22 = reps.filter(r => r.when < "2023-01-01").length, nTr = reps.filter(r => r.truce).length;
  note("2022-08-10", "2022-12-31", 236, [`AUGUST TO DECEMBER 2022: ${reps.filter(r => r.when >= "2022-08-01" && r.when < "2023-01-01").length} REPAIRS`]);
  const firstTr = reps.filter(r => r.truce).map(r => r.when).sort()[0];
  note(firstTr, D.axis_end, 236, [`FROM ${fmt(pd(firstTr)).toUpperCase()}: ${nTr} OF ${reps.filter(r => r.when >= firstTr).length} UNDER CEASEFIRES`]);
  whoKey(300, 1000);
  foot("A DOT PER REPAIR ON THE DAY THE LINE CAME BACK (OR THE WORK WAS DONE), IN ITS LINE'S ROW, NUDGED APART WHERE DAYS ARE CLOSE · " +
       "SHADED BY WHO DID THE WORK · NO PLACES SHOWN");
}

// ---- 5b: the same, stacked by month (a dot histogram)
function dots() {
  head("42 repairs, month by month");
  const m0 = pd("2022-02-01"), months = d3.utcMonth.range(m0, pd("2026-11-01"));
  const x = d3.scaleBand().domain(months.map(m => +m)).range([120, 1860]).padding(0.08);
  const base = 700, R = Math.min(x.bandwidth() / 2 - 1, 11);
  const byM = d3.group([...reps].sort((a, b) => ["fero", "dnip", "yards", "kakh"].indexOf(a.line) - ["fero", "dnip", "yards", "kakh"].indexOf(b.line)), r => +d3.utcMonth.floor(r.t));
  // under it each month's connected lines, from the record: the darkest day of the month
  for (const m of months) {
    const ds = days.filter(d => +d3.utcMonth.floor(d.t) === +m);
    if (!ds.length) { svg.append("rect").attr("x", x(+m)).attr("y", base + 14).attr("width", x.bandwidth()).attr("height", 40).attr("fill", "none").attr("stroke", "#4a4a4c"); continue; }
    const lo = d3.min(ds, d => d.on), unk = ds.some(d => d.unk);
    svg.append("rect").attr("x", x(+m)).attr("y", base + 14).attr("width", x.bandwidth()).attr("height", 40).attr("fill", litOf(d3.median(ds, d => d.on)));
    if (unk) hatchCell(svg, x(+m), base + 14, x.bandwidth(), 40);
    if (lo === 0 && ds.some(d => d.loss || d.island)) svg.append("rect").attr("x", x(+m)).attr("y", base + 58).attr("width", x.bandwidth()).attr("height", 4).attr("fill", "#fff").attr("opacity", 0.6);
  }
  const g = svg.append("g");
  for (const [m, rs] of byM) rs.forEach((r, i) => {
    const cx = x(m) + x.bandwidth() / 2, cy = base - R - 2 - i * (2 * R + 4);
    const lc = r.line === "fero" ? Y330 : r.line === "dnip" ? Y750 : "#bdbdc0";
    g.append("rect").attr("x", cx - R).attr("y", cy + R + 1).attr("width", 2 * R).attr("height", 2).attr("fill", lc);
    who(g, r, cx, cy, R - 2);
  });
  for (let yr = 2022; yr <= 2026; yr++) {
    const m = Date.UTC(yr, yr === 2022 ? 1 : 0, 1);
    tiny(String(yr), x(m), base + 84, "start", "tiny dim");
    svg.append("line").attr("x1", x(m) - 2).attr("x2", x(m) - 2).attr("y1", 420).attr("y2", base + 66).attr("stroke", "#4a4a4c").attr("stroke-dasharray", "3 3");
  }
  tiny("UNDER EACH MONTH: THE LINES CONNECTED ON MOST OF ITS DAYS (THE CALENDAR'S SHADES) · A PALE BAR: A COMPLETE LOSS OR ISLAND MODE THAT MONTH", 120, base + 116, "start", "tiny dim");
  const lk = [[Y330, "FEROSPLAVNA-1"], [Y750, "DNIPROVSKA"], ["#bdbdc0", "THE SWITCHYARDS' LINKS OR ANOTHER LINE"]];
  let lx = 120;
  for (const [c, l] of lk) { svg.append("rect").attr("x", lx).attr("y", base + 140).attr("width", 18).attr("height", 3).attr("fill", c); const t = tiny("UNDERLINED: " + l, lx + 26, base + 145); lx += 26 + t.node().getComputedTextLength() + 24; }
  whoKey(120, 1000);
  foot("A DOT PER REPAIR, STACKED IN THE MONTH THE LINE CAME BACK (OR THE WORK WAS DONE), UNDERLINED IN ITS LINE'S COLOUR · NO PLACES SHOWN");
}

// ---- 2b: the calendar, each day split: Ferosplavna-1 above, Dniprovska below
function cal_split() {
  head("Every day of the war: the last two lines");
  const P = 21, C = 18, X0 = 130, Y0 = 150, BH = 7 * P + 22, fmtD = d3.utcFormat("%Y-%m-%d");
  const cell = t => {
    const yr = t.getUTCFullYear(), jan1 = Date.UTC(yr, 0, 1), dow0 = (new Date(jan1).getUTCDay() + 6) % 7;
    const n = Math.round((t - jan1) / DAY) + dow0;
    return {x: X0 + Math.floor(n / 7) * P, y: Y0 + (yr - 2022) * BH + (n % 7) * P};
  };
  const half = (g, x, y, st, col) => {
    g.append("rect").attr("x", x).attr("y", y).attr("width", C).attr("height", C / 2 - 0.5).attr("fill", st === "on" ? col : UNLIT);
    if (st === "unknown") hatchCell(g, x, y, C, C / 2 - 0.5, 0.8);
  };
  const g = svg.append("g");
  for (let yr = 2022; yr <= 2026; yr++) svg.append("text").attr("class", "year").attr("x", 40).attr("y", Y0 + (yr - 2022) * BH + 16).text(yr);
  for (let m = 0; m < 12; m++) { const c = cell(new Date(Date.UTC(2022, m, 1))); tiny(d3.utcFormat("%b")(new Date(Date.UTC(2022, m, 1))), c.x, Y0 - 12, "start", "tiny dim"); }
  for (let t = new Date(Date.UTC(2022, 0, 1)); t <= Date.UTC(2026, 11, 31); t = new Date(+t + DAY)) {
    const c = cell(t), d = byDayAll.get(fmtD(t));
    if (d) {
      if (d.on >= 10) g.append("rect").attr("x", c.x).attr("y", c.y).attr("width", C).attr("height", C).attr("fill", litOf(10));
      else { half(g, c.x, c.y, d.fero, Y330); half(g, c.x, c.y + C / 2 + 0.5, d.dnip, Y750); }
      if (d.loss && d.on > 0) g.append("rect").attr("x", c.x + 6).attr("y", c.y + 6).attr("width", 6).attr("height", 6).attr("fill", "#fff");
    } else if (t >= days[0].t && t <= pd(D.axis_end)) g.append("rect").attr("x", c.x + 0.5).attr("y", c.y + 0.5).attr("width", C - 1).attr("height", C - 1).attr("fill", "none").attr("stroke", "#4a4a4c");
    else g.append("rect").attr("x", c.x).attr("y", c.y).attr("width", C).attr("height", C).attr("fill", "#2a2a2b");
  }
  for (const r of reps) { const c = cell(r.t); who(g, r, c.x + C / 2, c.y + C / 2, 4); }
  const KX = 1370;
  let ky = keyRows(KX, 200, [
    [(s, x, y) => { half(s, x, y, "on", Y330); half(s, x, y + C / 2 + 0.5, "off", Y750); }, "TOP HALF LIT: FEROSPLAVNA-1 CONNECTED"],
    [(s, x, y) => { half(s, x, y, "off", Y330); half(s, x, y + C / 2 + 0.5, "on", Y750); }, "BOTTOM HALF LIT: DNIPROVSKA CONNECTED"],
    [(s, x, y) => { half(s, x, y, "on", Y330); half(s, x, y + C / 2 + 0.5, "on", Y750); }, "BOTH"],
    [UNLIT, "NEITHER"],
    [litOf(10), "ALL TEN OF THE PLANT'S LINES"],
    [(s, x, y) => { half(s, x, y, "unknown", Y330); half(s, x, y + C / 2 + 0.5, "unknown", Y750); }, "THE REPORTS DON'T SAY WHICH"],
    [(s, x, y) => { half(s, x, y, "on", Y330); half(s, x, y + C / 2 + 0.5, "on", Y750); s.append("rect").attr("x", x + 6).attr("y", y + 6).attr("width", 6).attr("height", 6).attr("fill", "#fff"); }, "A COMPLETE LOSS RESTORED WITHIN THE DAY"],
  ]);
  ky = sideKey(KX, ky + 30);
  const both = days.filter(d => d.fero === "on" && d.dnip === "on" && d.on < 10).length;
  const one = days.filter(d => (d.fero === "on") !== (d.dnip === "on") && d.unk === 0).length;
  ky += 70;
  for (const [n, l] of [[both, "DAYS WITH BOTH"], [one, "WITH ONE OF THE TWO"]]) {
    svg.append("text").attr("x", KX).attr("y", ky).attr("fill", "#fff").style("font-size", "40px").text(n.toLocaleString("en-GB"));
    tiny(l, KX + 4, ky + 22); ky += 78;
  }
  foot("ONE SQUARE PER DAY, A ROW PER WEEKDAY · EACH SPLIT: FEROSPLAVNA-1 (330 KV) ABOVE, DNIPROVSKA (750 KV) BELOW, LIT WHILE CONNECTED AT THE " +
       "END OF THE DAY, AS THE IAEA AND ENERGOATOM REPORTED · NO PLACES SHOWN");
}

// ---- 2c: every line, every day: a band of ten rows per year
function cal_ten() {
  head("Every line, every day");
  const X0 = 300, X1 = 1860, DW = (X1 - X0) / 366, RH = 9, Y0 = 170, BH = 10 * RH + 62;
  const keys = D.record.keys;          // [record name, drawn, kV]
  const col = k => (k[2] === 750 ? D.rgb["750"] : D.rgb["330"]);
  const g = svg.append("g");
  for (let yr = 2022; yr <= 2026; yr++) {
    const yb = Y0 + (yr - 2022) * BH;
    svg.append("text").attr("class", "year").attr("x", 40).attr("y", yb + 16).text(yr);
    keys.forEach((k, i) => {
      if (yr === 2022 || yr === 2026) tiny(k[0].replace("-", "-").toUpperCase() + " · " + k[2], X0 - 12, yb + i * RH + 8, "end", "tiny dim").style("font-size", "9.5px");
    });
    const jan1 = Date.UTC(yr, 0, 1);
    for (let n = 0; n < 366; n++) {
      const t = new Date(jan1 + n * DAY);
      if (t.getUTCFullYear() !== yr) break;
      const d = byDayAll.get(t.toISOString().slice(0, 10)), xx = X0 + n * DW;
      if (!d) {
        if (t >= days[0].t && t <= pd(D.axis_end)) g.append("rect").attr("x", xx).attr("y", yb).attr("width", DW).attr("height", 10 * RH).attr("fill", "#2c2c2e");
        continue;
      }
      // runs of one state down the column drawn as one rect
      [...d.s].forEach((c, i) => {
        const fill = c === "o" ? rgb(col(keys[i])) : c === "x" ? UNLIT : "#3a3a3c";
        g.append("rect").attr("x", xx).attr("y", yb + i * RH).attr("width", DW + 0.4).attr("height", RH - 1).attr("fill", fill);
      });
      if (d.unk) [...d.s].forEach((c, i) => { if (c === "u") hatchCell(g, xx, yb + i * RH, DW + 0.4, RH - 1, 0.5); });
      if (d.loss) g.append("rect").attr("x", xx).attr("y", yb + 10 * RH + 2).attr("width", Math.max(DW, 1.5)).attr("height", 5).attr("fill", "#fff").attr("opacity", 0.7);
    }
    for (let m = 0; m < 12; m++) {
      const xm = X0 + Math.round((Date.UTC(yr, m, 1) - jan1) / DAY) * DW;
      if (yr === 2022) tiny(d3.utcFormat("%b")(new Date(Date.UTC(yr, m, 1))), xm, yb - 12, "start", "tiny dim");
    }
  }
  // the repairs: a dot above their line's row
  const rowOf = {fero: 4, dnip: 0};
  for (const r of reps) {
    const yr = r.t.getUTCFullYear(), yb = Y0 + (yr - 2022) * BH, n = Math.round((r.t - Date.UTC(yr, 0, 1)) / DAY);
    who(g, r, X0 + (n + 0.5) * DW, yb + 10 * RH + 19, 4);
  }
  const KX = X0;
  tiny("LIT: CONNECTED AT THE END OF THE DAY (750 KV THE BRIGHTER YELLOW) · DARK: CUT · GREY, HATCHED: THE REPORTS DON'T SAY WHICH · " +
       "A PALE MARK UNDER A DAY: A COMPLETE LOSS OF OFF-SITE POWER · A DOT UNDER IT: A REPAIR", KX, 990, "start", "tiny dim");
  foot("A BAND PER YEAR, A ROW PER LINE (THE FOUR 750 KV ABOVE, THE SIX 330 KV BELOW), A COLUMN PER DAY, AS THE IAEA AND ENERGOATOM REPORTED · " +
       "NO PLACES SHOWN");
}

// ---- 2d: the calendar as a spiral, a turn a year
function cal_spiral() {
  head("Every day of the war, a turn a year");
  const CX = 800, CY = 585, R0 = 120, RING = 56, TH = 47;
  const t0 = Date.UTC(2022, 0, 1), YEAR = 365.2425 * DAY;
  const pos = (t, f) => {            // f: 0 inner edge .. 1 outer edge of the band
    const u = (t - t0) / YEAR, a = 2 * Math.PI * u - Math.PI / 2, r = R0 + u * RING + (f - 0.5) * TH;
    return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
  };
  const g = svg.append("g");
  for (let t = t0; t < Date.UTC(2027, 0, 1); t += DAY) {
    const d = byDayAll.get(new Date(t).toISOString().slice(0, 10));
    let fill = null;
    if (d) fill = litOf(d.on);
    else if (t >= +days[0].t && t <= +pd(D.axis_end)) fill = "none";
    else fill = "#2a2a2b";
    const p = [pos(t, 0), pos(t + DAY, 0), pos(t + DAY, 1), pos(t, 1)];
    const path = g.append("path").attr("d", "M" + p.map(q => q.join(",")).join("L") + "Z").attr("fill", fill === "none" ? "none" : fill)
      .attr("stroke", fill === "none" ? "#4a4a4c" : fill).attr("stroke-width", fill === "none" ? 0.6 : 0.35);
    if (d && d.unk) g.append("path").attr("d", path.attr("d")).attr("fill", "url(#hatch)").attr("opacity", d.on ? 0.55 : 0.8);
    if (d && d.loss && d.on > 0) { const [a, b] = [pos(t + DAY / 2, 0.3), pos(t + DAY / 2, 0.7)]; g.append("line").attr("x1", a[0]).attr("y1", a[1]).attr("x2", b[0]).attr("y2", b[1]).attr("stroke", UNLIT).attr("stroke-width", 2.2); }
  }
  for (const r of reps) { const [x, y] = pos(+r.t + DAY / 2, 0.5); who(g, r, x, y, 4); }
  for (let m = 0; m < 12; m++) {     // the months round the outside
    const a = 2 * Math.PI * (m / 12) - Math.PI / 2, rr = R0 + 5 * RING + 46;
    tiny(d3.utcFormat("%b")(new Date(Date.UTC(2022, m, 1))), CX + rr * Math.cos(a + 0.26), CY + rr * Math.sin(a + 0.26) + 4, "middle", "tiny dim");
    const r1 = R0 - TH / 2 - 6, r2 = R0 + 5 * RING;
    svg.append("line").attr("x1", CX + r1 * Math.cos(a)).attr("y1", CY + r1 * Math.sin(a)).attr("x2", CX + (r2 + 4) * Math.cos(a)).attr("y2", CY + (r2 + 4) * Math.sin(a))
      .attr("stroke", "#5a5a5c").attr("stroke-width", 0.6).attr("stroke-dasharray", "2 3").lower();
  }
  for (let yr = 2022; yr <= 2026; yr++) {
    const [x, y] = pos(Date.UTC(yr, 0, 1), 0.5);
    svg.append("text").attr("class", "tiny").attr("x", x - 8).attr("y", y + 4).attr("text-anchor", "end").text(yr)
      .attr("stroke", GROUND).attr("stroke-width", 5).attr("paint-order", "stroke");
  }
  const KX = 1460;
  let ky = keyRows(KX, 200, [[litOf(10), "ALL TEN LINES"], [litOf(2), "TWO"], [litOf(1), "ONE"], [UNLIT, "NONE"],
    [(s, x, y) => { s.append("rect").attr("x", x).attr("y", y).attr("width", 18).attr("height", 18).attr("fill", litOf(1)); hatchCell(s, x, y, 18, 18, 0.55); }, "THE REPORTS DON'T SAY WHICH"]]);
  sideKey(KX, ky + 30);
  foot("ONE STEP ALONG THE SPIRAL PER DAY, A TURN PER YEAR FROM 1 JANUARY 2022 AT THE TOP · LIT BY HOW MANY OF THE PLANT'S TEN LINES WERE CONNECTED AT " +
       "THE END OF THE DAY · NO PLACES SHOWN");
}

// ---- 2e: the days counted, grouped by how many lines were connected
function cal_waffle() {
  head("1,661 days, counted");
  const groups = [
    ["ALL TEN LINES", d => d.on >= 10],
    ["LINES CUT AND REPAIRED; THE REPORTS DON'T SAY WHICH", d => d.unk > 0],
    ["TWO", d => d.unk === 0 && d.on === 2],
    ["ONE", d => d.unk === 0 && d.on === 1],
    ["NONE: A COMPLETE LOSS OF OFF-SITE POWER, OR ISLAND MODE", d => d.unk === 0 && d.on === 0],
  ];
  const PER = 60, P = 17, C = 14, X0 = 120;
  let y = 170;
  const g = svg.append("g"), repDay = d3.group(reps, r => r.when);
  for (const [label, f] of groups) {
    const ds = days.filter(f);
    ds.forEach((d, i) => {
      const x = X0 + (i % PER) * P, yy = y + Math.floor(i / PER) * P;
      g.append("rect").attr("x", x).attr("y", yy).attr("width", C).attr("height", C).attr("fill", litOf(d.on));
      if (d.unk) hatchCell(g, x, yy, C, C, d.on ? 0.55 : 0.8);
      for (const r of repDay.get(d.d) || []) who(g, r, x + C / 2, yy + C / 2, 3.4);
    });
    const rows = Math.ceil(ds.length / PER);
    const ly = y + Math.min(rows * P, 60) / 2;
    const num = svg.append("text").attr("x", X0 + PER * P + 40).attr("y", ly + 8).attr("fill", "#fff").style("font-size", "40px").text(ds.length.toLocaleString("en-GB"));
    tiny(`DAYS · ${label}`, X0 + PER * P + 40 + num.node().getComputedTextLength() + 14, ly + 2);
    y += rows * P + 30;
  }
  whoKey(X0, 990);
  foot("EVERY DAY OF THE RECORD, 24 FEBRUARY 2022 TO " + fmt(lastDay.t).toUpperCase() + ", A SQUARE IN DATE ORDER WITHIN ITS GROUP (" + PER +
       " A ROW), SHADED BY HOW MANY OF THE TEN LINES WERE CONNECTED AT ITS END · A DOT: A REPAIR THAT DAY · NO PLACES SHOWN");
}

// ---- 2e in black and white (the user, 9 November 2026: "improve the graphic so that it is black and white (not yellow)")
function cal_waffle_bw() {
  const BG = "#111112", INK = "#000";
  document.body.style.background = BG;
  svg.insert("rect", ":first-child").attr("width", W).attr("height", H).attr("fill", BG);
  head("1,661 days, counted");
  const shade = {10: "#ffffff", 2: "#b4b4b6", 1: "#68686a", 0: INK};
  const groups = [
    ["ALL TEN LINES", d => d.on >= 10],
    ["LINES CUT AND REPAIRED; THE REPORTS DON'T SAY WHICH", d => d.unk > 0],
    ["TWO LINES: FEROSPLAVNA-1 AND DNIPROVSKA", d => d.unk === 0 && d.on === 2],
    ["ONE LINE", d => d.unk === 0 && d.on === 1],
    ["NONE: A COMPLETE LOSS OF OFF-SITE POWER, OR ISLAND MODE", d => d.unk === 0 && d.on === 0],
  ];
  // a repair: who did the work as before, outlined so it shows on white squares and on black ones alike
  const mark = (g, r, x, y, s = 4.4) => {
    if (r.truce) {
      g.append("circle").attr("cx", x).attr("cy", y).attr("r", s + 3.4).attr("fill", "none").attr("stroke", INK).attr("stroke-width", 3);
      g.append("circle").attr("cx", x).attr("cy", y).attr("r", s + 3.4).attr("fill", "none").attr("stroke", "#fff").attr("stroke-width", 1.2);
    }
    const c = g.append("circle").attr("cx", x).attr("cy", y).attr("r", s);
    if (r.side === "ukrainian") c.attr("fill", "#fff").attr("stroke", INK).attr("stroke-width", 1.4);
    else if (r.side === "russian") c.attr("fill", "#8c8c8e").attr("stroke", INK).attr("stroke-width", 1.4);
    else if (r.side === "both") {
      c.attr("fill", "#8c8c8e").attr("stroke", INK).attr("stroke-width", 1.4);
      g.append("path").attr("d", `M${x},${y - s}A${s},${s} 0 0 0 ${x},${y + s}Z`).attr("fill", "#fff");
    } else c.attr("fill", INK).attr("stroke", "#fff").attr("stroke-width", 1.2);
  };
  const PER = 60, P = 19, C = 16, X0 = 110;
  const fmtS = d3.utcFormat("%-d %b %Y");
  let y = 170;
  const g = svg.append("g"), repDay = d3.group(reps, r => r.when);
  for (const [label, f] of groups) {
    const ds = days.filter(f);
    ds.forEach((d, i) => {
      const x = X0 + (i % PER) * P, yy = y + Math.floor(i / PER) * P;
      if (d.unk) {
        g.append("rect").attr("x", x).attr("y", yy).attr("width", C).attr("height", C).attr("fill", d.on ? shade[d.on] : "#2c2c2e");
        hatchCell(g, x, yy, C, C, 0.75);
      } else if (d.on === 0) {   // black on near-black: an edge so the square still reads
        g.append("rect").attr("x", x + 0.5).attr("y", yy + 0.5).attr("width", C - 1).attr("height", C - 1).attr("fill", INK).attr("stroke", "#58585a");
      } else g.append("rect").attr("x", x).attr("y", yy).attr("width", C).attr("height", C).attr("fill", shade[Math.min(d.on, 10)] || shade[2]);
      if (d.loss && d.on > 0) g.append("rect").attr("x", x + 5).attr("y", yy + 5).attr("width", 6).attr("height", 6).attr("fill", INK);
      for (const r of repDay.get(d.d) || []) mark(g, r, x + C / 2, yy + C / 2);
    });
    const rows = Math.ceil(ds.length / PER), nRep = ds.reduce((n, d) => n + (repDay.get(d.d) || []).length, 0);
    const lx = X0 + PER * P + 40, ly = y + Math.min(rows * P, 60) / 2;
    const num = svg.append("text").attr("x", lx).attr("y", ly + 8).attr("fill", "#fff").style("font-size", "40px").text(ds.length.toLocaleString("en-GB"));
    const tx = lx + num.node().getComputedTextLength() + 14;
    tiny(`DAYS · ${label}`, tx, ly - 4);
    const span = ds.length > 1 ? `BETWEEN ${fmtS(ds[0].t)} AND ${fmtS(ds[ds.length - 1].t)}` : fmtS(ds[0].t);
    tiny(`${span}${nRep ? ` · ${nRep} REPAIR${nRep > 1 ? "S" : ""}` : ""}`.toUpperCase(), tx, ly + 14, "start", "tiny dim");
    y += rows * P + 34;
  }
  // the key: the marks, the inset, and the one repair the record doesn't reach
  const kg = svg.append("g");
  let kx = X0;
  for (const [r, label] of [[{side: "ukrainian"}, "UKRAINIAN CREWS"], [{side: "russian"}, "THE RUSSIAN SIDE"], [{side: "both"}, "BOTH"],
                            [{side: "unknown"}, "NOT SAID"], [{side: "ukrainian", truce: true}, "UNDER AN IAEA-BROKERED CEASEFIRE"]]) {
    kg.append("rect").attr("x", kx - 7).attr("y", 979).attr("width", 14).attr("height", 14).attr("fill", shade[2]);
    mark(kg, r, kx, 986);
    const t = tiny(label, kx + 16, 990);
    kx += 16 + t.node().getComputedTextLength() + 30;
  }
  kg.append("rect").attr("x", kx - 7).attr("y", 979).attr("width", 14).attr("height", 14).attr("fill", shade[2]);
  kg.append("rect").attr("x", kx - 3).attr("y", 983).attr("width", 6).attr("height", 6).attr("fill", INK);
  tiny("A COMPLETE LOSS RESTORED WITHIN THE DAY", kx + 16, 990);
  const late = reps.filter(r => !byDayAll.has(r.when));
  if (late.length) tiny(`NOT SHOWN: ${late.length === 1 ? "THE 42ND REPAIR" : late.length + " REPAIRS"}, ${late.map(r => fmtS(r.t).toUpperCase()).join(", ")}, AFTER THE RECORD'S LAST REPORT`,
                        X0, 1014, "start", "tiny dim");
  foot("EVERY DAY OF THE RECORD, 24 FEBRUARY 2022 TO " + fmt(lastDay.t).toUpperCase() + ", ONE SQUARE EACH, GROUPED BY HOW MANY OF THE PLANT'S TEN LINES " +
       "WERE CONNECTED AT THE DAY'S END, IN DATE ORDER WITHIN EACH GROUP (" + PER + " A ROW) · A MARK: A REPAIR THAT DAY · NO PLACES SHOWN");
}

// ---- 2e in black and white, pass 2 (the user, 9 November 2026: only who did the work, Ukrainian, Russian or both;
// no not-said mark, ceasefire ring or same-day loss inset; each row's first day on its left)
function cal_waffle_bw2() {
  const BG = "#111112", INK = "#000";
  document.body.style.background = BG;
  svg.insert("rect", ":first-child").attr("width", W).attr("height", H).attr("fill", BG);
  head("1,661 days, counted");
  const shade = {10: "#ffffff", 2: "#b4b4b6", 1: "#68686a", 0: INK};
  const groups = [
    ["ALL TEN LINES", d => d.on >= 10],
    ["LINES CUT AND REPAIRED; THE REPORTS DON'T SAY WHICH", d => d.unk > 0],
    ["TWO LINES: FEROSPLAVNA-1 AND DNIPROVSKA", d => d.unk === 0 && d.on === 2],
    ["ONE LINE", d => d.unk === 0 && d.on === 1],
    ["NONE: A COMPLETE LOSS OF OFF-SITE POWER, OR ISLAND MODE", d => d.unk === 0 && d.on === 0],
  ];
  const MARKED = new Set(["ukrainian", "russian", "both"]);
  const mark = (g, r, x, y, s = 4.2) => {
    const c = g.append("circle").attr("cx", x).attr("cy", y).attr("r", s).attr("stroke", INK).attr("stroke-width", 1.4);
    if (r.side === "ukrainian") c.attr("fill", "#fff");
    else {
      c.attr("fill", "#8c8c8e");
      if (r.side === "both") g.append("path").attr("d", `M${x},${y - s}A${s},${s} 0 0 0 ${x},${y + s}Z`).attr("fill", "#fff");
    }
  };
  const PER = 60, P = 18, C = 15, X0 = 190;
  const fmtS = d3.utcFormat("%-d %b %Y");
  let y = 170;
  const g = svg.append("g"), repDay = d3.group(reps.filter(r => MARKED.has(r.side)), r => r.when);
  for (const [label, f] of groups) {
    const ds = days.filter(f);
    ds.forEach((d, i) => {
      const x = X0 + (i % PER) * P, yy = y + Math.floor(i / PER) * P;
      if (i % PER === 0) tiny(fmtS(d.t).toUpperCase(), X0 - 12, yy + 12, "end", "tiny dim").style("font-size", "10.5px");
      if (d.unk) {
        g.append("rect").attr("x", x).attr("y", yy).attr("width", C).attr("height", C).attr("fill", d.on ? shade[d.on] : "#2c2c2e");
        hatchCell(g, x, yy, C, C, 0.75);
      } else if (d.on === 0) {
        g.append("rect").attr("x", x + 0.5).attr("y", yy + 0.5).attr("width", C - 1).attr("height", C - 1).attr("fill", INK).attr("stroke", "#58585a");
      } else g.append("rect").attr("x", x).attr("y", yy).attr("width", C).attr("height", C).attr("fill", shade[Math.min(d.on, 10)] || shade[2]);
      for (const r of repDay.get(d.d) || []) mark(g, r, x + C / 2, yy + C / 2);
    });
    const rows = Math.ceil(ds.length / PER), nRep = ds.reduce((n, d) => n + (repDay.get(d.d) || []).length, 0);
    const lx = X0 + PER * P + 30, ly = y + Math.min(rows * P, 60) / 2;
    const num = svg.append("text").attr("x", lx).attr("y", ly + 8).attr("fill", "#fff").style("font-size", "40px").text(ds.length.toLocaleString("en-GB"));
    const tx = lx + num.node().getComputedTextLength() + 14;
    const words = `DAYS · ${label}`.split(" ");     // wrapped to the room right of the count
    let line = "", ln = 0;
    const room = W - 30 - tx;
    const lines = [];
    for (const w of words) {
      const t = line ? line + " " + w : w;
      if (t.length * 7.6 > room && line) { lines.push(line); line = w; } else line = t;
    }
    lines.push(line);
    lines.forEach((l, k) => tiny(l, tx, ly - 4 + k * 16));
    ln = lines.length;
    if (nRep) tiny(`${nRep} MARKED REPAIR${nRep > 1 ? "S" : ""}`, tx, ly - 4 + ln * 16 + 2, "start", "tiny dim");
    y += rows * P + 34;
  }
  const kg = svg.append("g");
  let kx = X0;
  for (const [r, label] of [[{side: "ukrainian"}, "A REPAIR BY UKRAINIAN CREWS"], [{side: "russian"}, "BY THE RUSSIAN SIDE"], [{side: "both"}, "BY BOTH"]]) {
    kg.append("rect").attr("x", kx - 8).attr("y", 978).attr("width", 16).attr("height", 16).attr("fill", shade[2]);
    mark(kg, r, kx, 986);
    const t = tiny(label, kx + 18, 990);
    kx += 18 + t.node().getComputedTextLength() + 32;
  }
  const unsaid = reps.filter(r => !MARKED.has(r.side) && byDayAll.has(r.when)).length;
  const late = reps.filter(r => !byDayAll.has(r.when));
  const parts = [];
  if (unsaid) parts.push(`${unsaid} REPAIR${unsaid > 1 ? "S" : ""} WHERE THE SOURCES DON'T SAY WHO`);
  if (late.length) parts.push(`${late.length === 1 ? `THE ${ordinal(reps.length)}` : late.length + " REPAIRS"} (${late.map(r => fmtS(r.t).toUpperCase()).join(", ")}, AFTER THE RECORD'S LAST REPORT)`);
  if (parts.length) tiny(`${parts.join(", AND ")} ${unsaid + late.length > 1 ? "ARE" : "IS"} NOT MARKED`, X0 - 8, 1014, "start", "tiny dim");
  foot("EVERY DAY OF THE RECORD, 24 FEBRUARY 2022 TO " + fmt(lastDay.t).toUpperCase() + ", ONE SQUARE EACH, GROUPED BY HOW MANY OF THE PLANT'S TEN LINES " +
       "WERE CONNECTED AT THE DAY'S END, IN DATE ORDER WITHIN EACH GROUP (" + PER + " A ROW; THE DATE LEFT OF A ROW IS ITS FIRST DAY) · NO PLACES SHOWN");
}
function cal_waffle_bw3() {
  const BG = "#111112", INK = "#000";
  document.body.style.background = BG;
  svg.insert("rect", ":first-child").attr("width", W).attr("height", H).attr("fill", BG);
  head("The plant's ten lines, day by day: how many were connected",
       "EACH SQUARE IS ONE DAY, 24 FEBRUARY 2022 TO " + fmt(lastDay.t).toUpperCase() + " · EACH DOT IS A REPAIR MADE THAT DAY");
  const shade = {10: "#ffffff", 2: "#b4b4b6", 1: "#68686a", 0: INK};
  const groups = [
    ["ALL TEN LINES", d => d.on >= 10],
    ["LINES CUT AND REPAIRED; THE REPORTS DON'T SAY WHICH", d => d.unk > 0],
    ["TWO LINES: FEROSPLAVNA-1 AND DNIPROVSKA", d => d.unk === 0 && d.on === 2],
    ["ONE LINE", d => d.unk === 0 && d.on === 1],
    ["NONE: A COMPLETE LOSS OF OFF-SITE POWER, OR ISLAND MODE", d => d.unk === 0 && d.on === 0],
  ];
  const MARKED = new Set(["ukrainian", "russian", "both", "unknown"]);   // unspecified: a repair whose sources don't say who did it
  const mark = (g, r, x, y, s = 4.2) => {
    const c = g.append("circle").attr("cx", x).attr("cy", y).attr("r", s).attr("stroke", INK).attr("stroke-width", 1.4);
    if (r.side === "ukrainian") c.attr("fill", "#fff");
    else if (r.side === "unknown") c.attr("fill", INK).attr("stroke", "#fff").attr("stroke-width", 1.2);
    else {
      c.attr("fill", "#8c8c8e");
      if (r.side === "both") g.append("path").attr("d", `M${x},${y - s}A${s},${s} 0 0 0 ${x},${y + s}Z`).attr("fill", "#fff");
    }
  };
  const PER = 60, P = 18, C = 15, X0 = 190;
  const fmtS = d3.utcFormat("%-d %b %Y");
  let y = 170;
  const g = svg.append("g"), repDay = d3.group(reps.filter(r => MARKED.has(r.side)), r => r.when);
  for (const [label, f] of groups) {
    const ds = days.filter(f);
    ds.forEach((d, i) => {
      const x = X0 + (i % PER) * P, yy = y + Math.floor(i / PER) * P;
      if (i % PER === 0) tiny(fmtS(d.t).toUpperCase(), X0 - 12, yy + 12, "end", "tiny dim").style("font-size", "10.5px");
      if (d.unk) {
        g.append("rect").attr("x", x).attr("y", yy).attr("width", C).attr("height", C).attr("fill", d.on ? shade[d.on] : "#2c2c2e");
        hatchCell(g, x, yy, C, C, 0.75);
      } else if (d.on === 0) {
        g.append("rect").attr("x", x + 0.5).attr("y", yy + 0.5).attr("width", C - 1).attr("height", C - 1).attr("fill", INK).attr("stroke", "#58585a");
      } else g.append("rect").attr("x", x).attr("y", yy).attr("width", C).attr("height", C).attr("fill", shade[Math.min(d.on, 10)] || shade[2]);
      for (const r of repDay.get(d.d) || []) mark(g, r, x + C / 2, yy + C / 2);
    });
    const rows = Math.ceil(ds.length / PER), nRep = ds.reduce((n, d) => n + (repDay.get(d.d) || []).length, 0);
    const lx = X0 + PER * P + 30, ly = y + Math.min(rows * P, 60) / 2;
    const num = svg.append("text").attr("x", lx).attr("y", ly + 8).attr("fill", "#fff").style("font-size", "40px").text(ds.length.toLocaleString("en-GB"));
    const tx = lx + num.node().getComputedTextLength() + 14;
    const words = `DAYS · ${label}`.split(" ");     // wrapped to the room right of the count
    let line = "", ln = 0;
    const room = W - 30 - tx;
    const lines = [];
    for (const w of words) {
      const t = line ? line + " " + w : w;
      if (t.length * 7.6 > room && line) { lines.push(line); line = w; } else line = t;
    }
    lines.push(line);
    lines.forEach((l, k) => tiny(l, tx, ly - 4 + k * 16));
    ln = lines.length;
    if (nRep) tiny(`${nRep} REPAIR${nRep > 1 ? "S" : ""}`, tx, ly - 4 + ln * 16 + 2, "start", "tiny dim");
    y += rows * P + 34;
  }
  // the key: each mark in a white square outline, no fill, so the circle reads on its own
  const kg = svg.append("g");
  let kx = X0;
  for (const [r, label] of [[{side: "ukrainian"}, "A REPAIR BY UKRAINIAN CREWS"], [{side: "russian"}, "BY THE RUSSIAN SIDE"],
                            [{side: "both"}, "BY BOTH"], [{side: "unknown"}, "UNSPECIFIED"]]) {
    kg.append("rect").attr("x", kx - 10).attr("y", 990).attr("width", 20).attr("height", 20).attr("fill", "none")
      .attr("stroke", "#fff").attr("stroke-width", 1.2);
    mark(kg, r, kx, 1000, 5);
    const t = tiny(label, kx + 20, 1004);
    kx += 20 + t.node().getComputedTextLength() + 36;
  }
}
function ordinal(n) { const s = ["TH", "ST", "ND", "RD"], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); }

// ---- 2e animated (the user, 9 November 2026: "for the animation pass of this please center the graphic ... each square
// can be animated to appear from left to right, top to bottom"): bw3's waffle, centred, every element built once and
// shown by `drawAt(t)`; the squares at one constant rate, group after group, so each group's size reads as time
function cal_waffle_anim() {
  const BG = "#111112", INK = "#000";
  document.body.style.background = BG;
  svg.insert("rect", ":first-child").attr("width", W).attr("height", H).attr("fill", BG);
  const shade = {10: "#ffffff", 2: "#b4b4b6", 1: "#68686a", 0: INK};
  const groups = [
    ["ALL TEN LINES", d => d.on >= 10],
    ["LINES CUT, THE REPORTS DON'T SAY WHICH", d => d.unk > 0],
    ["TWO LINES", d => d.unk === 0 && d.on === 2],
    ["ONE LINE", d => d.unk === 0 && d.on === 1],
    ["NO LINES: POWER LOST OR ISLAND MODE", d => d.unk === 0 && d.on === 0],
  ];
  const mark = (g, r, x, y, s = 4.4) => {
    const c = g.append("circle").attr("cx", x).attr("cy", y).attr("r", s).attr("stroke", INK).attr("stroke-width", 1.4);
    if (r.side === "ukrainian") c.attr("fill", "#fff");
    else if (r.side === "unknown") c.attr("fill", INK).attr("stroke", "#fff").attr("stroke-width", 1.2);
    else {
      c.attr("fill", "#8c8c8e");
      if (r.side === "both") g.append("path").attr("d", `M${x},${y - s}A${s},${s} 0 0 0 ${x},${y + s}Z`).attr("fill", "#fff");
    }
  };
  const PER = 60, P = 19, C = 16, GAP = 34, TITLE_PX = 50, DATE_PAD = 14, NUM_GAP = 26, NUM_PAD = 12, NUM_PX = 34, RIGHT = 64;
  // the title, then the key (so the marks are known before they appear), then the squares, then a hold to read
  const T_TITLE = [0.0, 0.8], T_KEY0 = 0.9, KEY_STEP = 0.15, KEY_FADE = 0.5, T_FILL0 = 2.2, FILL_S = 12.5,
        SQ_FADE = 0.15, MARK_POP = 0.25, TXT_FADE = 0.35, HOLD = 6.5;
  const fmtS = d3.utcFormat("%-d %b %Y");
  const repDay = d3.group(reps, r => r.when);
  const G = groups.map(([label, f]) => ({label, ds: days.filter(f)}));
  const total = d3.sum(G, g => g.ds.length), rate = total / FILL_S;
  // the squares centred in the frame (the dates in the gutter left of them, the counts right of them); the whole moved
  // only up or down, so its box sits in the middle of the frame's height
  const root = svg.append("g");
  const meas = svg.append("g").attr("opacity", 0);
  const width = (txt, cls, px) => { const t = meas.append("text").attr("class", cls).text(txt); if (px) t.style("font-size", px + "px"); return t.node().getComputedTextLength(); };
  const numW = d3.max(G, g => width(g.ds.length.toLocaleString("en-GB"), "", NUM_PX));
  const gridW = PER * P - (P - C);
  const X0 = Math.round((W - gridW) / 2);            // the grid's left edge; the title and the key start there too
  const LABEL_W = W - RIGHT - (X0 + gridW + NUM_GAP + numW + NUM_PAD);
  const wrap = txt => {
    const out = []; let line = "";
    for (const w of txt.split(" ")) {
      const tt = line ? line + " " + w : w;
      if (line && width(tt, "tiny") > LABEL_W) { out.push(line); line = w; } else line = tt;
    }
    out.push(line); return out;
  };
  G.forEach(g => { g.lines = wrap(`DAYS · ${g.label}`); });
  meas.remove();
  const title = `${total.toLocaleString("en-GB")} days of war, a square for each; a dot for each repair`;
  const rows = G.map(g => Math.ceil(g.ds.length / PER));
  const gridH = d3.sum(rows) * P - (P - C) + GAP * (G.length - 1);
  const KEY_GAP = 34, KEY_H = 20, GRID_GAP = 46;
  // the title as wide as the squares (its size fitted to their width) and the key spread across them: the three share
  // the squares' edges, centred in the frame with them
  const titleEl = root.append("text").attr("class", "head").attr("x", X0).style("font-size", TITLE_PX + "px").text(title);
  const TITLE_INK = [3, -1];   // its capitals' side bearings at this size, left and right of the ink: measured on the frame
  const titlePx = TITLE_PX * (gridW + TITLE_INK[0] + TITLE_INK[1]) / titleEl.node().getComputedTextLength();
  const titleY = Math.round(titlePx * 0.75), ky = titleY + KEY_GAP, Y0 = ky + KEY_H + GRID_GAP;
  titleEl.style("font-size", titlePx.toFixed(2) + "px").attr("x", X0 - TITLE_INK[0]).attr("y", titleY);
  // the key: each mark in a white square outline, no fill; its items fade in one after another
  const keys = [];
  for (const [r, label] of [[{side: "ukrainian"}, "REPAIR BY UKRAINIAN CREWS"], [{side: "russian"}, "REPAIR BY RUSSIAN CREWS"],
                            [{side: "both"}, "REPAIR BY BOTH"], [{side: "unknown"}, "UNSPECIFIED REPAIR"]]) {
    const kg = root.append("g").attr("opacity", 0);
    kg.append("rect").attr("x", 0).attr("y", ky).attr("width", 20).attr("height", 20).attr("fill", "none").attr("stroke", "#fff").attr("stroke-width", 1.2);
    mark(kg, r, 10, ky + 10, 5);
    const t = kg.append("text").attr("class", "tiny").attr("x", 30).attr("y", ky + 14).text(label);
    keys.push({el: kg, t: T_KEY0 + keys.length * KEY_STEP, w: 30 + t.node().getComputedTextLength()});
  }
  const keyGap = (gridW - d3.sum(keys, q => q.w)) / (keys.length - 1);
  keys.reduce((x, q) => { q.el.attr("transform", `translate(${x.toFixed(1)},0)`); return x + q.w + keyGap; }, X0);
  const sq = [], marks = [], dates = [], texts = [];
  let k = 0, y = Y0;
  const gGrid = root.append("g"), gMarks = root.append("g");
  G.forEach((g, gi) => {
    g.t0 = T_FILL0 + k / rate;
    g.ds.forEach((d, i) => {
      const x = X0 + (i % PER) * P, yy = y + Math.floor(i / PER) * P, t = T_FILL0 + k / rate;
      const c = gGrid.append("g").attr("opacity", 0);
      if (d.unk) {
        c.append("rect").attr("x", x).attr("y", yy).attr("width", C).attr("height", C).attr("fill", d.on ? shade[d.on] : "#2c2c2e");
        hatchCell(c, x, yy, C, C, 0.75);
      } else if (d.on === 0) {
        c.append("rect").attr("x", x + 0.5).attr("y", yy + 0.5).attr("width", C - 1).attr("height", C - 1).attr("fill", INK).attr("stroke", "#58585a");
      } else c.append("rect").attr("x", x).attr("y", yy).attr("width", C).attr("height", C).attr("fill", shade[Math.min(d.on, 10)] || shade[2]);
      sq.push({el: c, t});
      if (i % PER === 0) dates.push({el: root.append("text").attr("class", "tiny dim").attr("x", X0 - DATE_PAD).attr("y", yy + 12)
        .attr("text-anchor", "end").style("font-size", "10.5px").attr("opacity", 0).text(fmtS(d.t).toUpperCase()), t});
      for (const r of repDay.get(d.d) || []) {
        const m = gMarks.append("g").attr("opacity", 0);
        mark(m, r, 0, 0);
        marks.push({el: m, t, x: x + C / 2, y: yy + C / 2, side: r.side, id: r.id});
      }
      k++;
    });
    g.t1 = T_FILL0 + k / rate;
    // the count on the group's first row (its capitals' top on the row's top), the words beside it
    const nr = rows[gi];
    const lx = X0 + gridW + NUM_GAP;
    const num = root.append("text").attr("x", lx).attr("y", y + Math.round(NUM_PX * 0.71)).attr("fill", "#fff").style("font-size", NUM_PX + "px").attr("opacity", 0).text("0");
    const tx = lx + numW + NUM_PAD;
    const lab = root.append("g").attr("opacity", 0);
    g.lines.forEach((l, j) => lab.append("text").attr("class", "tiny").attr("x", tx).attr("y", y + 9 + j * 15).text(l));
    const nRep = g.ds.reduce((n, d) => n + (repDay.get(d.d) || []).length, 0);
    const rep = nRep ? root.append("text").attr("class", "tiny dim").attr("x", tx).attr("y", y + 9 + g.lines.length * 15 + 2).attr("opacity", 0)
      .text(`${nRep} REPAIR${nRep > 1 ? "S" : ""}`) : null;
    g.nRep = nRep;
    texts.push({g, num, lab, rep});
    y += nr * P + GAP;
  });
  const T_FILL1 = T_FILL0 + total / rate;
  // centre the composed block's height (its box with every text at its widest: the counts at their full values)
  texts.forEach(({g, num}) => num.text(g.ds.length.toLocaleString("en-GB")));
  const bb = root.node().getBBox();
  const INK_DY = -5;   // the title's text box rises above its capitals: measured on the frame
  const OX = 0, OY = Math.round((H - bb.height) / 2 - bb.y) + INK_DY;
  root.attr("transform", `translate(${OX},${OY})`);
  const T_KEY = [T_KEY0, keys[keys.length - 1].t + KEY_FADE], DURATION = T_FILL1 + SQ_FADE + HOLD;
  const ramp = (t, a, d) => { const x = Math.min(1, Math.max(0, (t - a) / d)); return x * x * (3 - 2 * x); };
  window.drawAt = t => {
    titleEl.attr("opacity", ramp(t, T_TITLE[0], T_TITLE[1] - T_TITLE[0]));
    for (const s of sq) s.el.attr("opacity", ramp(t, s.t, SQ_FADE));
    for (const d of dates) d.el.attr("opacity", ramp(t, d.t, TXT_FADE));
    for (const m of marks) {
      const a = ramp(t, m.t, MARK_POP), sc = a <= 0 ? 0.001 : 0.4 + 0.6 * a;
      m.el.attr("opacity", a).attr("transform", `translate(${m.x},${m.y}) scale(${sc})`);
    }
    for (const {g, num, lab, rep} of texts) {
      const a = ramp(t, g.t0, TXT_FADE);
      num.attr("opacity", a).text(Math.max(0, Math.min(g.ds.length, Math.floor((t - g.t0) * rate) + 1)).toLocaleString("en-GB"));
      lab.attr("opacity", a);
      if (rep) rep.attr("opacity", ramp(t, g.t1, TXT_FADE));
    }
    for (const q of keys) q.el.attr("opacity", ramp(t, q.t, KEY_FADE));
  };
  window.TIMELINE = {duration_s: +DURATION.toFixed(3), fps_test: 30, title: {text: title, fade_s: T_TITLE},
    fill: {start_s: T_FILL0, end_s: +T_FILL1.toFixed(3), squares: total, squares_per_s: +rate.toFixed(2), square_fade_s: SQ_FADE, mark_pop_s: MARK_POP},
    groups: G.map(g => ({label: g.label, days: g.ds.length, first_day: g.ds[0].d, last_day: g.ds[g.ds.length - 1].d, repairs: g.nRep,
                         start_s: +g.t0.toFixed(3), end_s: +g.t1.toFixed(3)})),
    key: {fade_s: T_KEY.map(v => +v.toFixed(3)), item_step_s: KEY_STEP, where: "under the title, above the squares"},
    hold: {from_s: +(T_FILL1 + SQ_FADE).toFixed(3), s: HOLD},
    marks: marks.length, layout: {block: [OX + bb.x, OY + bb.y, bb.width, bb.height].map(v => +v.toFixed(1)), align: "the squares centred in the frame; the title fitted to their width and the key spread across it; the dates in the gutter left of them, the counts right of them on each group's first row", grid_x: [X0, X0 + gridW], title_px: +titlePx.toFixed(2), pitch_px: P, square_px: C}};
  drawAt(0);
}

({arcs, calendar, deficit, parsets, swarm, dots, cal_split, cal_ten, cal_spiral, cal_waffle, cal_waffle_bw, cal_waffle_bw2, cal_waffle_bw3, cal_waffle_anim})[OPT]();
document.fonts.ready.then(() => { window.DRAWN = true; });
