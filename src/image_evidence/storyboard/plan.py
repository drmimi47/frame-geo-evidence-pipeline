"""The storyboard outside Blender: the pool of shots, the cuts, their media, the layout and the read-back.

- The pool (`config/storyboard.yaml`, written by hand): `sources` (the films and figures shots point at: the newest
  zoom-out of a network, a crossing3d render by title, the newest film of a corridor, or a file) and `shots`, each with
  an id, a title, a status (good, draft, still, missing, idea; `new` for one made in Blender), what it tells, what it
  needs, where it comes from in the research, tags, and either a source with `in`/`out` seconds or a `duration`.
  A card may carry the film's own words (`card`: the text as it would read on screen, an intertitle) and a `chapter`
  (its number, drawn small above); without them a card is a placeholder of what is still to make.
  A shot is never deleted by a read-back: taken out of a cut, it is parked; deleted from the parked shots, it is hidden.
- The cuts (`config/storyboard-cuts.yaml`, rewritten by `sync`): each a list of shot ids in order; an entry may carry
  its own `in`, `out` or `duration` (a trim in Blender), or a whole shot of its own (one made in Blender); `hidden`
  lists the pool's shots left out of the parked ones (take an id off it to park the shot again).
- On disk (The Conductive Seam's `storyboard/`): `<cut>.blend`, `<cut>.built.json` (what the .blend was built from,
  so a rebuild never overwrites a rearrangement that hasn't been read back), and `media/` (the films at the
  storyboard's frame rate and preview size, made once per source version).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from ..satellite import store
from ..satellite.network import network_dir
from ..satellite.scene3d.export import scene_dir

log = logging.getLogger(__name__)

POOL = Path("config/storyboard.yaml")
CUTS = Path("config/storyboard-cuts.yaml")
BLEND = Path(__file__).with_name("blend.py")
STATUSES = ("good", "draft", "still", "missing", "idea", "new")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")
PREVIEW_H = 720            # the films' preview height (the storyboard is laid out at the pool's `size`)
PARK_GAP_S = 3             # black between the cut's END and the parked shots
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
DUPLICATE = re.compile(r"\.\d{3}$")   # Blender's suffix on a copied strip: the same shot used again
CUTS_HEADER = """\
# The storyboard's cuts (src/image_evidence/storyboard; the shots are in config/storyboard.yaml). Rewritten by
# `evidence storyboard sync` from the cut's .blend: the order as arranged in Blender, trims as `in`/`out`/`duration`,
# shots made in Blender as entries of their own. Comments after each shot are written from the pool.
"""


# ------------------------------------------------------------------ the pool and the cuts

def load(pool: Path = POOL, cuts: Path = CUTS) -> tuple[dict[str, Any], dict[str, Any]]:
    p = yaml.safe_load(Path(pool).read_text()) or {}
    c = (yaml.safe_load(Path(cuts).read_text()) or {}) if Path(cuts).exists() else {}
    for sid, sh in (p.get("shots") or {}).items():
        _check(sid, sh, p.get("sources") or {})
    for name, cut in c.items():
        for e in entries(cut):
            if e["shot"] not in p["shots"] and DUPLICATE.sub("", e["shot"]) not in p["shots"]:
                _check(e["shot"], e, p.get("sources") or {})
    return p, c


def _check(sid: str, sh: dict[str, Any], sources: dict[str, Any]) -> None:
    if not ID.match(sid):
        raise ValueError(f"storyboard: shot id {sid!r}: lower case, digits and hyphens, at most 48")
    if sh.get("status") not in STATUSES:
        raise ValueError(f"storyboard: {sid}: status {sh.get('status')!r} is not one of {', '.join(STATUSES)}")
    if sh.get("source") and sh["source"] not in sources:
        raise ValueError(f"storyboard: {sid}: no source {sh['source']!r}")
    f = (sources.get(sh["source"], {}) if sh.get("source") else {"file": sh.get("file")}).get("file") or ""
    if (not (sh.get("source") or sh.get("file")) or f.lower().endswith(IMAGE_SUFFIXES)) and not sh.get("duration"):
        raise ValueError(f"storyboard: {sid}: a card or a figure needs a duration")


def entries(cut: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"shot": e} if isinstance(e, str) else dict(e) for e in cut.get("shots") or []]


def shot(pool: dict[str, Any], e: dict[str, Any]) -> dict[str, Any]:
    """A cut's entry as a whole shot: the pool's (by id, a copy's suffix dropped) with the entry's own on top."""
    base = pool["shots"].get(DUPLICATE.sub("", e["shot"]), {})
    return {**base, **{k: v for k, v in e.items() if k != "shot"}, "id": e["shot"]}


def parked(pool: dict[str, Any], cut: dict[str, Any]) -> list[str]:
    used = {DUPLICATE.sub("", e["shot"]) for e in entries(cut)} | set(cut.get("hidden") or [])
    return [sid for sid in pool["shots"] if sid not in used]


def write_cuts(pool: dict[str, Any], cuts: dict[str, Any], path: Path = CUTS) -> None:
    out = [CUTS_HEADER]
    for name, cut in cuts.items():
        out.append(f"{name}:")
        for k, v in cut.items():
            if k != "shots":
                out.append(f"  {k}: {json.dumps(v, ensure_ascii=False)}")
        out.append("  shots:")
        for e in entries(cut):
            sh = shot(pool, e)
            body = e["shot"] if len(e) == 1 else yaml.safe_dump(e, default_flow_style=True, width=10 ** 6,
                                                                  allow_unicode=True, sort_keys=False).strip()
            note = f"{sh.get('title', '')} ({sh.get('status', '?')})"
            out.append(f"    - {body}{' ' * max(1, 30 - len(body))}# {note}")
        out.append("")
    Path(path).write_text("\n".join(out))


# ------------------------------------------------------------------ media

def source_path(root: Path, src: dict[str, Any]) -> Path:
    """The file a source points at (the newest render, so a re-render is picked up)."""
    if "network" in src:
        made = sorted((f["made_at"], p.parent / f["files"]["video"])
                      for p in (network_dir(root, src["network"]) / "films").glob("*/film.json")
                      for f in [json.loads(p.read_text())])
        if not made:
            raise FileNotFoundError(f"no zoom-out film of {src['network']} yet")
        return made[-1][1]
    if "crossing3d" in src:
        return scene_dir(root, src.get("network_of", "znpp")) / "animatic" / f"{src['crossing3d']}.mp4"
    if "corridor" in src:
        made = [f for f in store.films(root) if f["corridor_id"] == src["corridor"]]
        if not made:
            raise FileNotFoundError(f"no film of {src['corridor']} yet")
        return store.corridor_dir(root, src["corridor"]) / "films" / made[0]["film_id"] / "film.mp4"
    return Path(src["file"]).resolve()


def _probe(path: Path) -> dict[str, Any]:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json",
                        str(path)], check=True, capture_output=True, text=True)
    d = json.loads(r.stdout)
    return {"seconds": float(d["format"]["duration"]),
            "audio": any(s["codec_type"] == "audio" for s in d.get("streams", []))}


def media(root: Path, key: str, path: Path, fps: int) -> dict[str, Any]:
    """A film at the storyboard's frame rate and preview size (made once for each version of its source); a figure as
    it is."""
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return {"kind": "image", "path": str(path)}
    d = out_dir(root) / "media"
    d.mkdir(parents=True, exist_ok=True)
    proxy, meta = d / f"{key}.mp4", d / f"{key}.json"
    st = path.stat()
    want = {"source": str(path), "size": st.st_size, "mtime_ns": st.st_mtime_ns, "fps": fps, "height": PREVIEW_H}
    have = json.loads(meta.read_text()) if meta.exists() else None
    if not (proxy.exists() and have and have.get("made_from") == want):
        log.info("Preview of %s at %d fps, %d px high", path.name, fps, PREVIEW_H)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-vf", f"fps={fps},scale=-2:{PREVIEW_H}",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-g", "15", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "160k", str(proxy)], check=True)
        have = {"made_from": want, **_probe(proxy)}
        meta.write_text(json.dumps(have, indent=1))
    return {"kind": "movie", "path": str(proxy), "frames": int(round(have["seconds"] * fps)), "audio": have["audio"]}


def out_dir(root: Path) -> Path:
    return Path(root) / "storyboard"


# ------------------------------------------------------------------ layout

def layout(pool: dict[str, Any], name: str, cut: dict[str, Any], resolve) -> dict[str, Any]:
    """The cut's shots end to end from frame 1, then the parked ones after its END. `resolve(shot)` gives a shot's
    media (`media()`), or None for a card."""
    fps = int(pool.get("fps", 30))

    def place(sh: dict[str, Any], at: int) -> dict[str, Any]:
        m = resolve(sh)
        p = {"id": sh["id"], "title": sh.get("title", sh["id"]), "status": sh["status"], "tells": sh.get("tells"),
             "needs": sh.get("needs"), "card": sh.get("card"), "chapter": sh.get("chapter"),
             "label": pool.get("labels", True), "start": at}
        if m and m["kind"] == "movie":
            a = max(0, round(float(sh.get("in", 0)) * fps))
            b = min(m["frames"], round(float(sh["out"]) * fps) if sh.get("out") is not None else m["frames"])
            if b <= a:
                raise ValueError(f"storyboard: {sh['id']}: out ({sh.get('out')}) not after in ({sh.get('in', 0)})")
            p.update(kind="movie", path=m["path"], audio=m["audio"], **{"in": a}, frames=b - a)
        else:
            p.update(kind=m["kind"] if m else "card", frames=max(1, round(float(sh["duration"]) * fps)))
            if m:
                p["path"] = m["path"]
        return p

    shots, at = [], 1
    for e in entries(cut):
        shots.append(place(shot(pool, e), at))
        at += shots[-1]["frames"]
    end, rest = at, []
    at += PARK_GAP_S * fps
    for sid in parked(pool, cut):
        rest.append(place({**pool["shots"][sid], "id": sid}, at))
        at += rest[-1]["frames"]
    return {"cut": name, "fps": fps, "size": list(pool.get("size", [1920, 1080])), "end": end, "shots": shots,
            "parked": rest}


# ------------------------------------------------------------------ reading a rearrangement back

def merge(pool: dict[str, Any], cut: dict[str, Any], rb: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """The cut as arranged in Blender (read by blend.py `read`): its order by where each shot starts (before the END
    marker, not muted), trims as `in`/`out`/`duration`, strips added in Blender as shots of their own (status new).
    Returns the new cut and a report of what changed."""
    fps = float(rb["fps"])
    end = rb["markers"].get("END", rb["frame_end"] + 1)
    own = {e["shot"]: e for e in entries(cut) if DUPLICATE.sub("", e["shot"]) not in pool["shots"]}
    report, taken, used_ids = [], [], set(pool["shots"]) | set(own)

    def fresh(name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "new-shot"
        sid, i = base, 2
        while sid in used_ids:
            sid, i = f"{base}-{i}", i + 1
        used_ids.add(sid)
        return sid

    for st in rb["strips"]:
        if st["type"] == "SOUND":
            report.append(f"left out: a sound strip on its own ({st['name']}); sound comes with its shot for now")
            continue
        sid = st["name"]
        base = DUPLICATE.sub("", sid)
        known = base in pool["shots"] or sid in own
        e: dict[str, Any] = {"shot": sid if known else None}
        pic = st.get("picture") or ({"type": st["type"], "content_start": st["content_start"], "left": st["left"],
                                     "right": st["right"], "path": st.get("path")}
                                    if st["type"] in ("MOVIE", "IMAGE") else None)
        if not known:   # made in Blender: a shot of its own
            title = (st.get("text") or st["name"]).strip().splitlines()[0][:80]
            e = {"shot": fresh(title), "title": title, "status": "new"}
            if pic and pic.get("path"):
                e["file"] = pic["path"]
            report.append(f"new: {e['shot']} ({st['type'].lower()} strip '{st['name']}')")
        sh = shot(pool, {**own.get(sid, {}), **e})
        if pic is not None and pic["type"] == "MOVIE":
            a = (max(st["left"], pic["left"]) - pic["content_start"]) / fps
            b = (min(st["right"], pic["right"]) - pic["content_start"]) / fps
            for k, v in (("in", a), ("out", b)):
                if sh.get(k) is None and k == "in" and abs(v) < 0.5 / fps:
                    continue
                if sh.get(k) is None or abs(float(sh[k]) - v) >= 0.5 / fps:
                    e[k] = round(v, 2)
            e.pop("duration", None)
        else:
            dur = (st["right"] - st["left"]) / fps
            if abs(float(sh.get("duration") or 0) - dur) >= 0.5 / fps:
                e["duration"] = round(dur, 2)
        if known and sid in own:   # a shot made in Blender earlier keeps what it carried
            e = {**own[sid], **e}
        in_cut = st["left"] < end and not st["mute"]
        if st["mute"] and st["left"] < end:
            report.append(f"parked (muted): {e['shot']}")
        if in_cut:
            taken.append((st["left"], st["channel"], e))
    taken.sort(key=lambda x: (x[0], x[1]))
    new_cut = {k: v for k, v in cut.items() if k not in ("shots", "hidden")}
    new_cut["shots"] = [e["shot"] if len(e) == 1 else e for _, _, e in taken]
    # a parked shot deleted in Blender is hidden from the parked ones (kept in the pool); one put back shows again
    present = {DUPLICATE.sub("", st["name"]) for st in rb["strips"]}
    was_hidden, was_parked = set(cut.get("hidden") or []), set(parked(pool, cut))
    hidden = [sid for sid in pool["shots"] if sid not in present and (sid in was_hidden or sid in was_parked)]
    if hidden:
        new_cut["hidden"] = hidden
    report += [f"hidden: {sid} (deleted from the parked shots; kept in the pool)" for sid in hidden
               if sid not in was_hidden]

    before = [e["shot"] for e in entries(cut)]
    after = [e["shot"] if isinstance(e, dict) else e for e in new_cut["shots"]]
    if before != after:
        report.append("order: " + " → ".join(after))
    for sid in before:
        if sid not in after:
            report.append(f"parked: {sid}")
    for sid in after:
        if sid not in before:
            report.append(f"into the cut: {sid}")
    for e in new_cut["shots"]:
        if isinstance(e, dict):
            trims = {k: e[k] for k in ("in", "out", "duration") if k in e}
            if trims:
                report.append(f"timing: {e['shot']} " + ", ".join(f"{k} {v}" for k, v in trims.items()))
    return new_cut, report


# ------------------------------------------------------------------ build, sync, show

def _hash(cut: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(entries(cut), sort_keys=True).encode()).hexdigest()


def _blender() -> str:
    b = shutil.which("blender")
    if not b:
        raise RuntimeError("blender isn't on PATH (docs/crossing-3d-plan.txt: a wrapper script in ~/.local/bin)")
    return b


def _read(path: Path) -> dict[str, Any]:
    tmp = path.with_suffix(".read.json")
    subprocess.run([_blender(), "-b", str(path), "-P", str(BLEND), "--", "read", str(tmp)], check=True,
                   stdout=subprocess.DEVNULL)
    rb = json.loads(tmp.read_text())
    tmp.unlink()
    return rb


def _built(path: Path) -> dict[str, Any] | None:
    b = path.with_suffix(".built.json")
    return json.loads(b.read_text()) if b.exists() else None


def _mark(path: Path, cut: dict[str, Any]) -> None:
    path.with_suffix(".built.json").write_text(json.dumps({"blend_mtime_ns": path.stat().st_mtime_ns,
                                                           "cut_sha256": _hash(cut)}, indent=1))


def edited(path: Path) -> bool:
    b = _built(path)
    return path.exists() and (b is None or path.stat().st_mtime_ns != b["blend_mtime_ns"])


def sync(root: Path, name: str, pool_path: Path = POOL, cuts_path: Path = CUTS) -> list[str]:
    """The cut's .blend read back into the cuts file."""
    pool, cuts = load(pool_path, cuts_path)
    path = out_dir(root) / f"{name}.blend"
    if not path.exists():
        raise FileNotFoundError(f"no storyboard for {name} yet: `evidence storyboard build --cut {name}`")
    new, report = merge(pool, cuts.get(name, {}), _read(path))
    cuts[name] = new
    write_cuts(pool, cuts, cuts_path)
    _mark(path, new)
    return report


def build(root: Path, name: str, discard_edits: bool = False, pool_path: Path = POOL,
          cuts_path: Path = CUTS) -> dict[str, Any]:
    """The cut's .blend made again from the pool and the cut. A rearrangement saved in Blender since the last build or
    sync is read back first; if the cut was also changed in the file, nothing is overwritten unless `discard_edits`."""
    pool, cuts = load(pool_path, cuts_path)
    if name not in cuts:
        raise KeyError(f"no cut {name!r} in {cuts_path} (cuts: {', '.join(cuts)})")
    d = out_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{name}.blend"
    report: list[str] = []
    if edited(path) and not discard_edits:
        b = _built(path)
        if b and b["cut_sha256"] != _hash(cuts[name]):
            raise RuntimeError(f"{path.name} was rearranged in Blender and {cuts_path} changed too: run `evidence "
                               f"storyboard sync --cut {name}` and merge by hand, or build with --discard-edits")
        report = sync(root, name, pool_path, cuts_path)
        pool, cuts = load(pool_path, cuts_path)
    fps = int(pool.get("fps", 30))
    sources = pool.get("sources") or {}

    def resolve(sh: dict[str, Any]) -> dict[str, Any] | None:
        if sh.get("source"):
            return media(root, sh["source"], source_path(root, sources[sh["source"]]), fps)
        if sh.get("file"):
            p = Path(sh["file"]).resolve()
            return media(root, f"file-{hashlib.sha1(str(p).encode()).hexdigest()[:10]}", p, fps)
        return None

    spec = layout(pool, name, cuts[name], resolve)
    used = {Path(s["path"]).stem for s in spec["shots"] + spec["parked"] if s["kind"] == "movie"}
    for f in (d / "media").glob("*"):   # previews of sources renamed or gone
        if f.stem not in used:
            log.info("Removing unused preview %s", f.name)
            f.unlink()
    tmp = d / f"{name}.building.blend"
    spec["out"] = str(tmp)
    sp = d / f"{name}.spec.json"
    sp.write_text(json.dumps(spec, indent=1))
    subprocess.run([_blender(), "-b", "--factory-startup", "-P", str(BLEND), "--", "build", str(sp)], check=True,
                   stdout=subprocess.DEVNULL)
    tmp.replace(path)
    sp.unlink()
    _mark(path, cuts[name])
    for f in [*d.glob("*.blend1"), *(f for f in d.glob("*.blend") if f.stem not in cuts)]:
        log.info("Removing old storyboard file %s", f.name)
        f.unlink()
        if f.suffix == ".blend":  # (a .blend1's with_suffix would name the current cut's record)
            f.with_suffix(".built.json").unlink(missing_ok=True)
    return {"path": str(path), "spec": spec, "synced": report}


def show(pool: dict[str, Any], name: str, cut: dict[str, Any]) -> list[str]:
    """The cut as a table: start, length, status, id, title; then the totals and what is parked."""
    fps = int(pool.get("fps", 30))

    def secs(sh: dict[str, Any]) -> float:
        if sh.get("duration") is not None:   # a card or a figure
            return float(sh["duration"])
        if sh.get("out") is None:
            return float("nan")
        return float(sh["out"]) - float(sh.get("in", 0))

    lines, t, by = [], 0.0, {}
    for e in entries(cut):
        sh = shot(pool, e)
        s = secs(sh)
        lines.append(f"  {int(t // 60)}:{t % 60:04.1f}  {s:5.1f} s  {sh['status']:<7}  {sh['id']:<24} {sh.get('title', '')}")
        t += 0 if s != s else s
        by[sh["status"]] = by.get(sh["status"], 0.0) + (0 if s != s else s)
    lines.append(f"  {name}: {int(t // 60)}:{t % 60:04.1f} in all · "
                 + " · ".join(f"{k} {v:.0f} s" for k, v in sorted(by.items(), key=lambda x: STATUSES.index(x[0]))))
    rest = parked(pool, cut)
    if rest:
        lines.append(f"  parked ({len(rest)}): " + ", ".join(rest))
    return lines
