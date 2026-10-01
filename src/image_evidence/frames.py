"""Frame selection and extraction.

Pass 1 (FFmpeg, one downscaled decode of the whole video): select frames that are
either a scene change (``scene > threshold``) or the first frame after ``interval_s``
seconds without a selection. Each one's exact presentation timestamp, scene score, and
a small RGB preview are recorded. Blank and near-duplicate candidates are dropped using
the previews, which the pipeline also classifies to choose which frames to keep.

Pass 2 (FFmpeg, full resolution): decode only the chosen frames as lossless RGB and
compute their quality metrics before anything is written.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from fractions import Fraction
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
    selection: str  # "scene_change" | "interval"
    preview: np.ndarray | None = field(default=None, repr=False, compare=False)  # RGB, longest side PREVIEW_PX


@dataclass
class ExtractedFrame:
    timestamp_s: float
    frame_number: int
    selection: str
    scene_score: float | None
    rgb: np.ndarray
    quality: FrameQuality


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True)
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
    """One pass over the video: timestamps, scene scores, and a small preview of every selected frame."""
    pw, ph = preview_size(info or probe(path))
    expr = f"gt(scene\\,{cfg.scene_threshold})+isnan(prev_selected_t)+gte(t-prev_selected_t\\,{cfg.interval_s})"
    vf = f"scale={pw}:{ph},setsar=1,select='{expr}',metadata=mode=print"
    proc = _run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-an", "-sn", "-dn", "-vf", vf,
        "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ])
    marks: list[tuple[float, float | None]] = []
    for line in proc.stderr.decode(errors="replace").splitlines():
        if "Parsed_metadata" not in line:
            continue
        if m := _PTS.search(line):
            marks.append((float(m.group(1)), None))
        elif (m := _SCENE.search(line)) and marks:
            marks[-1] = (marks[-1][0], float(m.group(1)))
    size = pw * ph * 3
    if len(proc.stdout) != size * len(marks):
        raise ExtractionError(f"preview size mismatch: {len(proc.stdout)} bytes for {len(marks)} frames")
    pixels = np.frombuffer(proc.stdout, np.uint8).reshape(len(marks), ph, pw, 3)
    out = []
    for (pts, score), px in zip(marks, pixels):
        is_scene = score is not None and score > cfg.scene_threshold
        out.append(Candidate(pts, score, "scene_change" if is_scene else "interval", px))
    return out


def thin_candidates(cands: list[Candidate], cfg: ExtractionConfig, limit: int | None = None) -> list[Candidate]:
    """Enforce min_gap_s (scene changes win ties), then cap to ``limit`` (default max_frames_per_video)."""
    kept: list[Candidate] = []
    for c in sorted(cands, key=lambda c: c.pts_time):
        if kept and c.pts_time - kept[-1].pts_time < cfg.min_gap_s:
            if c.selection == "scene_change" and kept[-1].selection == "interval":
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
