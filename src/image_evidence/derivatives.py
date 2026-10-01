"""Write original-quality frames and web/thumbnail derivatives."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from .config import ExtractionConfig


def original_format(cfg: ExtractionConfig, n_frames: int) -> str:
    if cfg.original_format != "auto":
        return cfg.original_format
    return "png" if n_frames <= cfg.lossless_max_frames else "jpg"


def write_original(rgb: np.ndarray, dest_stem: Path, fmt: str, cfg: ExtractionConfig) -> tuple[Path, str]:
    """Returns (path, sha256). PNG is lossless; JPEG uses 4:4:4 chroma at high quality."""
    img = Image.fromarray(rgb)
    path = dest_stem.with_suffix(f".{fmt}")
    if fmt == "png":
        img.save(path, "PNG", compress_level=6)
    else:
        img.save(path, "JPEG", quality=cfg.jpeg_quality, subsampling=0, optimize=True)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _resized(rgb: np.ndarray, max_px: int) -> Image.Image:
    img = Image.fromarray(rgb)
    img.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
    return img


def write_derivative(rgb: np.ndarray, dest: Path, max_px: int, quality: int) -> Image.Image:
    img = _resized(rgb, max_px)
    img.save(dest, "WEBP", quality=quality, method=5)
    return img
