#!/usr/bin/env python3
"""Build auditable, frame-level film geolocation records from transcript clues.

This script deliberately separates a mentioned place from a verified filming
location. It accepts timestamped transcript segments as JSON, finds explicit
place-name mentions from a project gazetteer, associates nearby mentions with
the sampled landscape frames, and writes a reviewable JSON file. Visual
geo-sleuth evidence can later promote a candidate from "mentioned" to
"visually_supported" or "verified".
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREDICTIONS = ROOT / "outputs/landscape/predictions.json"
DEFAULT_OUT = ROOT / "outputs/landscape/geolocation/predictions.json"

# Seed terms relevant to the two films. Add aliases without changing the
# output schema; longer aliases win when names overlap.
DEFAULT_PLACES = {
    "Ukraine": {"aliases": ["ukraine", "україна", "украине", "украина"], "level": "country"},
    "Crimea": {"aliases": ["crimea", "крим", "крыму", "крым"], "level": "region"},
    "Dnipro River": {"aliases": ["dnipro", "dnieper", "дніпро", "днепр"], "level": "feature"},
    "Kherson": {"aliases": ["kherson", "херсон"], "level": "city"},
    "Nova Kakhovka": {"aliases": ["nova kakhovka", "новая каховка", "нова каховка"], "level": "city"},
    "Kakhovka Reservoir": {"aliases": ["kakhovka reservoir", "каховское водохранилище", "каховське водосховище"], "level": "feature"},
    "Zaporizhzhia": {"aliases": ["zaporizhzhia", "zaporizhya", "zaporozhye", "запорожье", "запоріжжя"], "level": "city"},
    "Nikopol": {"aliases": ["nikopol", "нікополь", "никополь"], "level": "city"},
    "Kyiv": {"aliases": ["kyiv", "kiev", "київ", "киев"], "level": "city"},
    "Odesa": {"aliases": ["odesa", "odessa", "одеса", "одесса"], "level": "city"},
}


def load_segments(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    rows = data.get("segments", data) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("Transcript JSON must be a list or contain a segments list.")
    clean = []
    for row in rows:
        clean.append({"start": float(row["start"]), "end": float(row["end"]), "text": str(row["text"]).strip()})
    return clean


def mentions(text: str, places: dict) -> list[dict]:
    found = []
    folded = text.casefold()
    for canonical, details in places.items():
        for alias in sorted(details["aliases"], key=len, reverse=True):
            if re.search(r"(?<!\w)" + re.escape(alias.casefold()) + r"(?!\w)", folded):
                found.append({"place": canonical, "matched_text": alias, "level": details["level"]})
                break
    return found


def build(video: str, segments: list[dict], window: float, places: dict) -> list[dict]:
    frames = [r for r in json.loads(DEFAULT_PREDICTIONS.read_text()) if r["video"] == video]
    detected = []
    for segment in segments:
        for match in mentions(segment["text"], places):
            detected.append({**match, **segment})
    output = []
    for frame in frames:
        timestamp = float(frame["requested_seek_seconds"])
        nearby = []
        for item in detected:
            distance = 0.0 if item["start"] <= timestamp <= item["end"] else min(abs(timestamp-item["start"]), abs(timestamp-item["end"]))
            if distance <= window:
                nearby.append({**item, "distance_seconds": round(distance, 3), "evidence_type": "spoken_or_subtitle_mention"})
        nearby.sort(key=lambda x: (x["distance_seconds"], x["place"]))
        output.append({
            "filename": frame["filename"],
            "video": video,
            "timestamp_seconds": timestamp,
            "status": "mentioned_place_nearby" if nearby else "unlocated",
            "location": None,
            "coordinates": None,
            "uncertainty_radius_m": None,
            "confidence": "none",
            "candidates": nearby,
            "method_note": "A nearby mention is narrative context, not proof of camera location. Visual corroboration is required.",
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, choices=["1.mp4", "3.mp4"])
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--window", type=float, default=90.0, help="Seconds on either side of a frame")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows = build(args.video, load_segments(args.transcript), args.window, DEFAULT_PLACES)
    existing = json.loads(args.out.read_text()) if args.out.exists() else []
    merged = [r for r in existing if r.get("video") != args.video] + rows
    merged.sort(key=lambda r: (r["video"], r["timestamp_seconds"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(rows)} frame records ({sum(bool(r['candidates']) for r in rows)} with nearby mentions) to {args.out}")


if __name__ == "__main__":
    main()
