"""Frame selection and extraction.

Pass 1 (FFmpeg, one downscaled decode of the whole video): select frames that are
a scene change (``scene > threshold``), the first frame after ``interval_s``
seconds without a selection, or, within a shot, a frame once the camera has moved on
(a pan or flight shows a new stretch of landscape). Each one's exact presentation timestamp, scene score, and
a small RGB preview are recorded. Blank and near-duplicate candidates are dropped using
the previews, which the pipeline also classifies to choose which frames to keep.

Pass 2 (FFmpeg, full resolution): decode only the chosen frames as lossless RGB and
compute their quality metrics before anything is written.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
import threading
from collections import deque
from dataclasses import dataclass, field
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

from .config import ExtractionConfig
from .schema import FrameQuality

log = logging.getLogger(__name__)


class ExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Probe:
    width: int
    height: int
    fps: float
    duration: float
    start_time: float
    codec: str
    rotation: int = 0  # display rotation from side data (phone videos); FFmpeg applies it when decoding

    @property
    def display_size(self) -> tuple[int, int]:
        return (self.height, self.width) if abs(self.rotation) % 180 == 90 else (self.width, self.height)


@dataclass(frozen=True)
class Candidate:
    pts_time: float  # absolute container timestamp
    scene_score: float | None
    selection: str  # "scene_change" | "interval" | "camera_move"
    preview: np.ndarray | None = field(default=None, repr=False, compare=False)  # RGB, longest side PREVIEW_PX


@dataclass
class ExtractedFrame:
    timestamp_s: float
    frame_number: int
    selection: str
    scene_score: float | None
    rgb: np.ndarray
    quality: FrameQuality


def _low(cmd: list[str]) -> list[str]:
    """Run FFmpeg at low priority: it still uses every idle core, but the browser and the site's server come first,
    so pages stay smooth while videos are added."""
    return ["nice", "-n", "10", *cmd] if shutil.which("nice") else cmd


@cache
def _hwaccel() -> tuple[str, ...]:
    """Hardware video decoding for the whole-video scan on macOS (VideoToolbox: the same pixels, about a third of the
    CPU). FFmpeg falls back to software for a codec the hardware can't decode."""
    if sys.platform != "darwin":
        return ()
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-hwaccels"], capture_output=True, text=True).stdout
    except OSError:
        return ()
    return ("-hwaccel", "videotoolbox") if "videotoolbox" in out.split() else ()


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(_low(cmd), capture_output=True)
    if proc.returncode != 0:
        raise ExtractionError(f"{cmd[0]} failed ({proc.returncode}): {proc.stderr.decode(errors='replace')[-800:]}")
    return proc


def probe(path: Path) -> Probe:
    proc = _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,r_frame_rate,codec_name,start_time,duration:stream_side_data=rotation:format=duration,start_time",
        "-of", "json", str(path),
    ])
    data = json.loads(proc.stdout)
    if not data.get("streams"):
        raise ExtractionError(f"no video stream in {path}")
    s, fmt = data["streams"][0], data.get("format", {})
    rate = s.get("avg_frame_rate") if s.get("avg_frame_rate") not in (None, "0/0") else s.get("r_frame_rate")
    return Probe(
        width=int(s["width"]),
        height=int(s["height"]),
        fps=float(Fraction(rate)),
        duration=float(s.get("duration") or fmt.get("duration") or 0),
        start_time=float(s.get("start_time") or fmt.get("start_time") or 0),
        codec=s.get("codec_name", "?"),
        rotation=int(next((d["rotation"] for d in s.get("side_data_list", []) if "rotation" in d), 0)),
    )


PREVIEW_PX = 384  # longest side of a preview: enough for dHash and SigLIP (384px input)


def preview_size(info: Probe) -> tuple[int, int]:
    """Preview (w, h) with the video's own aspect ratio. No letterboxing: black bars around a
    vertical video would make different frames hash alike and look 'mostly black'."""
    w, h = info.display_size
    k = PREVIEW_PX / max(w, h)
    return max(2, round(w * k / 2) * 2), max(2, round(h * k / 2) * 2)

_PTS = re.compile(r"\bpts_time:(-?[\d.]+)")
_SCENE = re.compile(r"lavfi\.scene_score=([\d.]+)")


def select_candidates(path: Path, cfg: ExtractionConfig, info: Probe | None = None) -> list[Candidate]:
    """One pass over the video: timestamps, scene scores, and a small preview of every selected frame.

    Selected: scene changes, the first frame after ``interval_s`` without one, and, within a shot (looked at every
    ``view_step_s``), a frame once the camera has moved on from the last selected one (``view_overlap``): a pan or a
    flight over a landscape gives a frame for each new stretch of it, a static shot still gives one. Previews are
    read as FFmpeg makes them and only the selected ones are kept, so the dense look doesn't hold the whole video.
    """
    pw, ph = preview_size(info or probe(path))
    step = min(cfg.interval_s, cfg.view_step_s) if cfg.view_step_s else cfg.interval_s
    expr = f"gt(scene\\,{cfg.scene_threshold})+isnan(prev_selected_t)+gte(t-prev_selected_t\\,{step})"
    vf = f"scale={pw}:{ph},setsar=1,select='{expr}',metadata=mode=print"
    cmd = ["ffmpeg", "-hide_banner", "-nostats", *_hwaccel(), "-i", str(path), "-an", "-sn", "-dn", "-vf", vf,
           "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(_low(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    marks: list[list] = []  # [pts_time, scene score], one per frame FFmpeg passes on, in order
    tail: deque[str] = deque(maxlen=20)
    ready = threading.Condition()
    finished = False

    def read_marks() -> None:  # stderr on its own thread, so neither pipe can fill up and stall FFmpeg
        nonlocal finished
        for raw in proc.stderr:
            line = raw.decode(errors="replace")
            tail.append(line)
            if "Parsed_metadata" not in line:
                continue
            with ready:
                if m := _PTS.search(line):
                    marks.append([float(m.group(1)), None])
                elif (m := _SCENE.search(line)) and marks:
                    marks[-1][1] = float(m.group(1))
                ready.notify_all()
        with ready:
            finished = True
            ready.notify_all()

    reader = threading.Thread(target=read_marks, daemon=True)
    reader.start()
    size, n, out = pw * ph * 3, 0, []
    last: _View | None = None  # the last selected frame, which a frame within the same shot is compared with
    try:
        while buf := proc.stdout.read(size):
            if len(buf) != size:
                raise ExtractionError(f"preview size mismatch: a frame of {len(buf)} bytes, not {size}")
            with ready:  # a frame's scene score is printed before the next frame's time
                ready.wait_for(lambda: len(marks) > n + 1 or finished)
                if len(marks) <= n:
                    raise ExtractionError(f"preview size mismatch: frame {n + 1} without a timestamp")
                pts, score = marks[n]
            n += 1
            px = np.frombuffer(buf, np.uint8).reshape(ph, pw, 3)
            if score is not None and score > cfg.scene_threshold:
                selection = "scene_change"
            elif last is None or pts - last.pts_time >= cfg.interval_s - 1e-6:
                selection = "interval"
            elif last.moved_from(view := _View(pts, px), cfg):
                selection = "camera_move"
            else:
                continue
            last = view if selection == "camera_move" else _View(pts, px)
            out.append(Candidate(pts, score, selection, px))
    finally:
        proc.stdout.close()
        proc.wait()
        reader.join()
    if proc.returncode != 0:
        raise ExtractionError(f"ffmpeg failed ({proc.returncode}): {''.join(tail)[-800:]}")
    if n != len(marks):
        raise ExtractionError(f"preview size mismatch: {n} frames for {len(marks)} timestamps")
    return out


class _View:
    """A preview's grey image and (lazily) its ORB features, for telling whether the camera has moved on."""

    _orb = None

    def __init__(self, pts_time: float, rgb: np.ndarray):
        self.pts_time = pts_time
        self.gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        self.hash = dhash(self.gray)
        self._features = None

    @property
    def features(self):
        if self._features is None:
            if _View._orb is None:
                _View._orb = cv2.ORB_create(1000)
            self._features = _View._orb.detectAndCompute(self.gray, None)
        return self._features

    def moved_from(self, other: "_View", cfg: ExtractionConfig) -> bool:
        if bin(self.hash ^ other.hash).count("1") <= cfg.dedup_hamming:
            return False  # a near-duplicate: certainly the same view
        shared = view_overlap(self, other)
        return shared is not None and shared < cfg.view_overlap


def view_overlap(a: _View, b: _View) -> float | None:
    """Share of view two frames have in common (0..1). Their ORB features are matched and a similarity transform
    (shift, turn, zoom) fitted; each frame's outline is mapped into the other and the smaller covered share is
    returned, so a zoom or a flight forward counts as well as a pan. 0 when nothing matches (the camera has moved
    on); None when a frame has too little texture to tell (sky, water, fog)."""
    (ka, da), (kb, db) = a.features, b.features
    if da is None or db is None or len(ka) < 20 or len(kb) < 20:
        return None
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    if len(matches) < 15:
        return 0.0
    pa = np.float32([ka[m.queryIdx].pt for m in matches])
    pb = np.float32([kb[m.trainIdx].pt for m in matches])
    M, inliers = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=4)
    if M is None or inliers is None or int(inliers.sum()) < 12:
        return 0.0
    h, w = a.gray.shape
    outline = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)

    def covered(m) -> float:
        mask = np.zeros((h, w), np.uint8)
        cv2.fillConvexPoly(mask, cv2.transform(outline, m).reshape(-1, 2).round().astype(np.int32), 1)
        return float(mask.mean())

    return min(covered(M), covered(cv2.invertAffineTransform(M)))


def thin_candidates(cands: list[Candidate], cfg: ExtractionConfig, limit: int | None = None) -> list[Candidate]:
    """Enforce min_gap_s (scene changes win ties), then cap to ``limit`` (default max_frames_per_video)."""
    kept: list[Candidate] = []
    for c in sorted(cands, key=lambda c: c.pts_time):
        if kept and c.pts_time - kept[-1].pts_time < cfg.min_gap_s:
            if c.selection == "scene_change" and kept[-1].selection != "scene_change":
                kept[-1] = c
            continue
        kept.append(c)
    return cap(kept, cfg.max_frames_per_video if limit is None else limit)


def cap(cands: list[Candidate], limit: int) -> list[Candidate]:
    """Keep at most ``limit`` candidates, spread uniformly in time."""
    if len(cands) <= limit:
        return cands
    idx = np.unique(np.linspace(0, len(cands) - 1, limit).round().astype(int))
    return [cands[i] for i in idx]


def prefilter(cands: list[Candidate], cfg: ExtractionConfig) -> list[Candidate]:
    """Drop near-black and near-duplicate candidates, judged on their previews."""
    hashes: list[int] = []
    out = []
    for c in cands:
        gray = cv2.cvtColor(c.preview, cv2.COLOR_RGB2GRAY)
        if gray.mean() < cfg.drop_dark_below or (gray < 14).mean() > cfg.drop_black_fraction:
            log.debug("    drop dark frame @%.2fs", c.pts_time)
            continue
        h = dhash(gray)
        if any(bin(h ^ other).count("1") <= cfg.dedup_hamming for other in hashes):
            log.debug("    drop near-duplicate @%.2fs", c.pts_time)
            continue
        hashes.append(h)
        out.append(c)
    return out


def decode_frame(path: Path, pts_time: float, fps: float) -> np.ndarray:
    """Decode the single frame at pts_time at full resolution as RGB (lossless PNG over a pipe)."""
    seek = max(0.0, pts_time - 0.5 / fps)  # land on the frame, not the one after it
    proc = _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-copyts", "-ss", f"{seek:.6f}", "-i", str(path),
        "-frames:v", "1", "-an", "-f", "image2pipe", "-vcodec", "png", "-pix_fmt", "rgb24", "-",
    ])
    bgr = cv2.imdecode(np.frombuffer(proc.stdout, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ExtractionError(f"could not decode frame at {pts_time}s")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def dhash(gray: np.ndarray) -> int:
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def quality(rgb: np.ndarray) -> tuple[FrameQuality, int]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h = dhash(gray)
    q = FrameQuality(
        sharpness=round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2),
        brightness=round(float(gray.mean()), 2),
        contrast=round(float(gray.std()), 2),
        dhash=f"{h:016x}",
    )
    return q, h


def extract(path: Path, cfg: ExtractionConfig) -> tuple[Probe, list[Candidate], Iterator[ExtractedFrame]]:
    """Probe, select candidates (capped uniformly), and lazily decode those that survive the prefilter."""
    info = probe(path)
    cands = thin_candidates(select_candidates(path, cfg, info), cfg)
    return info, cands, (ef for _, ef in decode_frames(path, info, prefilter(cands, cfg)))


def decode_frames(path: Path, info: Probe, cands: list[Candidate]) -> Iterator[tuple[int, ExtractedFrame]]:
    """Full-resolution decode of the given candidates. Yields (index into cands, frame)."""
    seen_numbers: set[int] = set()
    for i, c in enumerate(cands):
        ts = max(0.0, c.pts_time - info.start_time)
        number = round(ts * info.fps)
        if number in seen_numbers:
            continue
        seen_numbers.add(number)
        rgb = decode_frame(path, c.pts_time, info.fps)
        q, _ = quality(rgb)
        score = None if c.scene_score is None else round(c.scene_score, 4)
        yield i, ExtractedFrame(round(ts, 3), number, c.selection, score, rgb, q)
