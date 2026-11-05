"""Gate candidate videos with the project's scope check, then download the accepted ones (video only, no audio).

Run with `python -I` from the repository root:

    python -I "research_notes/Tower cut opener/scripts/gate_download.py" META_DIR DOWNLOAD_DIR GATE_JSON ids...

For each id: yt-dlp metadata (META_DIR/<id>.json, fetched if missing), `acquisition.source_from_info` and
`scope.check_scope` against the Ukraine 2022-2026 scope (the same call `ingest` makes, before anything is written).
Rejected videos are only listed in GATE_JSON. An accepted one is downloaded into its own new, empty folder
DOWNLOAD_DIR/<id>/ (<= 1080p, video stream only: the opener is silent) and marked `done` when complete.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from image_evidence.acquisition import source_from_info
from image_evidence.scope import UKRAINE, check_scope

YTDLP = str(Path(sys.executable).with_name("yt-dlp"))


def main() -> None:
    meta, dl, gate_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    gate = json.loads(gate_path.read_text()) if gate_path.exists() else {}
    for yid in sys.argv[4:]:
        mpath = meta / f"{yid}.json"
        if not mpath.exists() or mpath.stat().st_size < 10:
            r = subprocess.run([YTDLP, "-J", "--skip-download", "--", yid], capture_output=True, text=True)
            mpath.write_text(r.stdout)
        try:
            info = json.loads(mpath.read_text())
            assert isinstance(info, dict)
        except Exception:
            gate[yid] = {"accepted": False, "reason": "no metadata (unavailable)"}
            continue
        source = source_from_info(info)
        verdict = check_scope(source, 0.5, UKRAINE)
        gate[yid] = {
            "accepted": verdict.accepted, "reason": verdict.reason,
            "title": source.title, "channel": info.get("channel") or info.get("uploader"),
            "channel_id": info.get("channel_id"), "published": source.published_at.date().isoformat(),
            "license": info.get("license") or "standard YouTube licence",
            "duration_s": info.get("duration"), "url": f"https://www.youtube.com/watch?v={yid}",
            "scope_check": verdict.check.model_dump(mode="json") if verdict.check else None,
        }
        gate_path.write_text(json.dumps(gate, ensure_ascii=False, indent=1))
        print(f"{yid}: {'IN ' if verdict.accepted else 'OUT'} {verdict.reason}", flush=True)
        if not verdict.accepted:
            continue
        folder = dl / yid
        if (folder / "done").exists():
            continue
        folder.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([YTDLP, "-q", "--no-warnings", "-f", "bv*[height<=1080][vcodec^=avc1]/bv*[height<=1080]",
                            "-o", str(folder / f"{yid}.%(ext)s"), "--", yid], capture_output=True, text=True)
        files = [f for f in folder.iterdir() if f.suffix in (".mp4", ".webm", ".mkv")]
        if r.returncode == 0 and files:
            (folder / "done").write_text(files[0].name)
            print(f"  downloaded {files[0].name} ({files[0].stat().st_size / 1e6:.0f} MB)", flush=True)
        else:
            print(f"  download failed: {r.stderr.strip()[:200]}", flush=True)


if __name__ == "__main__":
    main()
