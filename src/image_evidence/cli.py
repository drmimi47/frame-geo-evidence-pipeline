"""Command-line interface: `evidence <command>`."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path

from .config import Config

log = logging.getLogger("image_evidence")

_YT_ID = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([\w-]{11})|^([\w-]{11})$")


def parse_youtube_id(value: str) -> str:
    m = _YT_ID.search(value.strip())
    if not m:
        raise argparse.ArgumentTypeError(f"not a YouTube URL or id: {value!r}")
    return m.group(1) or m.group(2)


def load_dotenv(path: Path = Path(".env")) -> None:
    """Load KEY=value lines from ./.env into the environment. Real env vars take precedence."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _load(args: argparse.Namespace) -> Config:
    cfg = Config.load(args.config)
    if args.library:
        cfg.library_dir = Path(args.library).resolve()
    if getattr(args, "policy", None):
        cfg.acquisition.policy = args.policy
    if getattr(args, "max_videos", None):
        cfg.discovery.max_videos_total = args.max_videos
    if getattr(args, "classifier", None):
        cfg.classification.backend = args.classifier
    return cfg


def _print_report(report) -> None:
    for r in report.results:
        detail = (r.acquisition or "-") + (f" ({r.reason})" if r.reason else "")
        print(f"  {r.youtube_id}  {r.status:<17} frames={r.frames:<4} {detail}  {(r.title or '')[:60]}")


# ---------------------------------------------------------------- commands


def cmd_doctor(args: argparse.Namespace) -> int:
    from .acquisition import TOOL, _js_runtimes
    from .classify import classify_available

    cfg = _load(args)
    checks = [
        ("ffmpeg", bool(shutil.which("ffmpeg")), shutil.which("ffmpeg") or "install ffmpeg (brew install ffmpeg)"),
        ("ffprobe", bool(shutil.which("ffprobe")), shutil.which("ffprobe") or "ships with ffmpeg"),
        ("yt-dlp", True, TOOL),
        ("js runtime", bool(_js_runtimes()), ", ".join(_js_runtimes()) or "install deno or node (needed by yt-dlp for YouTube)"),
        (f"${cfg.discovery.api_key_env}", bool(os.environ.get(cfg.discovery.api_key_env)), "set" if os.environ.get(cfg.discovery.api_key_env) else "missing (needed for discovery)"),
        ("classifier", classify_available(), "SigLIP available" if classify_available() else "pip install -e '.[classify]' for visual categories"),
    ]
    for name, ok, detail in checks:
        print(f"  {'ok ' if ok else '-- '} {name:<18} {detail}")
    print(f"  library: {cfg.library_dir}")
    return 0 if all(ok for name, ok, _ in checks[:4]) else 1


def cmd_discover(args: argparse.Namespace) -> int:
    from .pipeline import Pipeline

    p = Pipeline(_load(args))
    report = p.run(discover_only=True)
    for c in report.candidates:
        score = f"{'*' if c['picked'] else ' '}{c['score']:>5.1f}  " if "score" in c else ""
        print(f"  {score}{c['youtube_id']}  {c['published_at'][:10]}  {c['license'] or '?':<14} {int(c['duration_s'] or 0):>5}s  {c['title'][:70]}")
        if c.get("reasons") and args.why:
            print("          " + "; ".join(c["reasons"]))
    picked = sum(c["picked"] for c in report.candidates)
    print(f"{len(report.candidates)} candidates, {picked} would be ingested (*) -> {p.lib.runs / (report.run_id + '.json')}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    from .pipeline import Pipeline

    p = Pipeline(_load(args))
    report = p.run(force=args.force)
    _print_report(report)
    print(f"library: {p.lib.root}")
    return 0 if all(r.status != "failed" for r in report.results) else 1


def cmd_ingest_video(args: argparse.Namespace) -> int:
    from .pipeline import Pipeline

    p = Pipeline(_load(args))
    report = p.ingest_ids(args.videos, force=args.force)
    _print_report(report)
    print(f"library: {p.lib.root}")
    return 0 if all(r.status != "failed" for r in report.results) else 1


def _service(args: argparse.Namespace):
    from .layout import Library
    from .service import EvidenceService
    from .store import SQLiteRepository

    cfg = _load(args)
    return EvidenceService(SQLiteRepository(Library(cfg.library_dir).db_path), media_base=str(cfg.library_dir) + "/")


def cmd_search(args: argparse.Namespace) -> int:
    res = _service(args).search(args.query, args.category, args.year, args.video, args.min_confidence, args.limit, args.offset)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0
    for it in res["items"]:
        place = f" @{it['inferred_place']['name']}?" if it["inferred_place"] else ""
        print(f"  {it['frame_id']}  {it['published_at'][:10]}  t={it['timestamp_s']:>7.2f}s  [{', '.join(it['categories'])}]{place}  {(it['video_title'] or '')[:40]}")
    print(f"{len(res['items'])} of {res['total']}  facets: {json.dumps(res['facets'])}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    f = _service(args).frame(args.frame_id)
    if f is None:
        print("not found", file=sys.stderr)
        return 1
    print(json.dumps(f, indent=2))
    return 0


def cmd_related(args: argparse.Namespace) -> int:
    for r in _service(args).related(args.frame_id, args.radius_km, args.limit):
        extra = f" {r['distance_km']}km" if "distance_km" in r else ""
        print(f"  {r['frame_id']}  {r['relation']}{extra}  [{', '.join(r['categories'])}]")
    return 0


def cmd_reindex(args: argparse.Namespace) -> int:
    from .layout import Library
    from .pipeline import reindex
    from .store import SQLiteRepository

    lib = Library(_load(args).library_dir)
    if args.fresh and lib.db_path.exists():
        lib.db_path.unlink()
    n_v, n_f = reindex(lib, SQLiteRepository(lib.db_path))
    print(f"indexed {n_v} videos, {n_f} frames -> {lib.db_path}")
    return 0


def cmd_relocate(args: argparse.Namespace) -> int:
    from .layout import Library
    from .pipeline import relocate_video
    from .store import SQLiteRepository

    cfg = _load(args)
    lib = Library(cfg.library_dir)
    repo = SQLiteRepository(lib.db_path)
    for video_dir in sorted(lib.videos.glob(args.video or "*")):
        if (video_dir / "video.json").exists():
            r = relocate_video(lib, repo, video_dir, fetch_captions=not args.offline,
                               refetch_captions=args.refetch_captions and not args.offline,
                               translate_en=not args.no_translate, retranslate=args.retranslate, run_ocr=True, force_ocr=args.force_ocr)
            print(f"  {video_dir.name}  frames={r['frames']:<4} ocr={r['ocr']:<4} chapters={r['chapters']:<3} "
                  f"captions={r['captions']:<4} translated={r['translated']:<4} "
                  f"speech_mentions={r['speech_mentions']:<4} frames_with_clues={r['with_frame_clues']}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    from .classify import make_classifier
    from .layout import Library
    from .pipeline import analyze
    from .store import SQLiteRepository

    cfg = _load(args)
    lib = Library(cfg.library_dir)
    n = analyze(lib, SQLiteRepository(lib.db_path), make_classifier(cfg.classification), args.video, args.force)
    print(f"analyzed {n} frames")
    return 0


def cmd_reclassify(args: argparse.Namespace) -> int:
    from .classify import make_classifier
    from .layout import Library
    from .pipeline import reclassify
    from .store import SQLiteRepository

    cfg = _load(args)
    lib = Library(cfg.library_dir)
    n = reclassify(lib, SQLiteRepository(lib.db_path), make_classifier(cfg.classification), args.video)
    print(f"reclassified {n} frames")
    return 0


def cmd_rescope(args: argparse.Namespace) -> int:
    from .layout import Library
    from .pipeline import rescope
    from .store import SQLiteRepository

    cfg = _load(args)
    lib = Library(cfg.library_dir)
    results = rescope(lib, SQLiteRepository(lib.db_path), cfg.scope.min_confidence, purge=args.purge)
    for yid, ok, reason in results:
        print(f"  {yid}  {'in scope ' if ok else 'OUT     '}  {reason}")
    print(f"{sum(ok for _, ok, _ in results)} in scope, {sum(not ok for _, ok, _ in results)} out of scope")
    return 0


def cmd_refresh_titles(args: argparse.Namespace) -> int:
    from .discovery import YouTubeClient
    from .layout import Library
    from .pipeline import refresh_titles
    from .store import SQLiteRepository

    cfg = _load(args)
    key = os.environ.get(cfg.discovery.api_key_env)
    if not key:
        print(f"needs ${cfg.discovery.api_key_env}")
        return 1
    lib = Library(cfg.library_dir)
    for yid, locs in refresh_titles(lib, SQLiteRepository(lib.db_path), YouTubeClient(key)):
        print(f"  {yid}  {', '.join(sorted(locs)) or '(original title only)'}")
    return 0


def _study_areas(cfg: Config) -> list:
    """The study areas the site offers "Near ..." sorts for: the given config's, else every config in config/."""
    if cfg.discovery.focus:
        return [cfg.discovery.focus]
    out = []
    for d in dict.fromkeys([Path.cwd() / "config", Path(__file__).resolve().parents[2] / "config"]):
        for path in sorted(d.glob("*.yaml")):
            try:
                focus = Config.load(path).discovery.focus
            except Exception:
                continue
            if focus and focus not in out:
                out.append(focus)
    return out


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn

        from .api import create_app
    except ImportError:
        print("install the [api] extra: pip install -e '.[api]'", file=sys.stderr)
        return 1
    cfg = _load(args)
    uvicorn.run(create_app(cfg.library_dir, _study_areas(cfg)), host=args.host, port=args.port)
    return 0


# ------------------------------------------------------------------ parser


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-c", "--config", type=Path, help="YAML config (default: built-in defaults)")
    common.add_argument("--library", help="library directory (overrides config)")
    common.add_argument("-v", "--verbose", action="store_true")

    parser = argparse.ArgumentParser(prog="evidence", description="YouTube visual evidence ingestion pipeline.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", parents=[common], help="check external tools and configuration").set_defaults(fn=cmd_doctor)

    s = sub.add_parser("discover", parents=[common], help="run configured YouTube searches; list candidates only")
    s.add_argument("--why", action="store_true", help="print each candidate's ranking reasons (study-area configs)")
    s.add_argument("--max-videos", type=int)
    s.set_defaults(fn=cmd_discover)

    policies = ["none", "creative_commons", "public"]
    s = sub.add_parser("ingest", parents=[common], help="discover + acquire + extract + classify + index")
    s.add_argument("--max-videos", type=int)
    s.add_argument("--policy", choices=policies, help="override acquisition.policy")
    s.add_argument("--classifier", choices=["auto", "siglip", "none"])
    s.add_argument("--force", action="store_true", help="re-extract already processed videos")
    s.set_defaults(fn=cmd_ingest)

    s = sub.add_parser("ingest-video", parents=[common], help="ingest specific YouTube videos by URL or id")
    s.add_argument("videos", nargs="+", type=parse_youtube_id)
    s.add_argument("--policy", choices=policies, help="override acquisition.policy")
    s.add_argument("--classifier", choices=["auto", "siglip", "none"])
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_ingest_video)

    s = sub.add_parser("search", parents=[common], help="search indexed frames")
    s.add_argument("query", nargs="?")
    s.add_argument("--category", action="append", default=[])
    s.add_argument("--year", type=int)
    s.add_argument("--video", help="youtube id")
    s.add_argument("--min-confidence", type=float, default=0.0)
    s.add_argument("--limit", type=int, default=30)
    s.add_argument("--offset", type=int, default=0)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_search)

    s = sub.add_parser("show", parents=[common], help="print a frame's full record")
    s.add_argument("frame_id")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("related", parents=[common], help="related frames (geo proximity, place, same video)")
    s.add_argument("frame_id")
    s.add_argument("--radius-km", type=float, default=5.0)
    s.add_argument("--limit", type=int, default=24)
    s.set_defaults(fn=cmd_related)

    s = sub.add_parser("reindex", parents=[common], help="rebuild the SQLite index from JSON sidecars")
    s.add_argument("--fresh", action="store_true", help="delete the existing database first")
    s.set_defaults(fn=cmd_reindex)

    s = sub.add_parser("reclassify", parents=[common], help="re-run visual classification on existing frames")
    s.add_argument("--video", help="youtube id (default: all)")
    s.add_argument("--classifier", choices=["auto", "siglip", "none"])
    s.set_defaults(fn=cmd_reclassify)

    s = sub.add_parser("relocate", parents=[common], help="frame-level place clues: on-screen text, chapters, captions")
    s.add_argument("--video", help="youtube id (default: all)")
    s.add_argument("--offline", action="store_true", help="don't fetch captions")
    s.add_argument("--force-ocr", action="store_true", help="re-run OCR on frames that already have it")
    s.add_argument("--refetch-captions", action="store_true", help="fetch captions again (and re-translate them)")
    s.add_argument("--no-translate", action="store_true", help="don't machine-translate captions into English")
    s.add_argument("--retranslate", action="store_true", help="machine-translate captions again (e.g. after a model change)")
    s.set_defaults(fn=cmd_relocate)

    s = sub.add_parser("analyze", parents=[common], help="compute sorting features (colour, angle, damage, similarity) for stored frames")
    s.add_argument("--video", help="youtube id (default: all)")
    s.add_argument("--force", action="store_true", help="recompute frames that already have features")
    s.add_argument("--classifier", choices=["auto", "siglip", "none"])
    s.set_defaults(fn=cmd_analyze)

    s = sub.add_parser("rescope", parents=[common], help="re-check stored videos against the Ukraine/2022-2026 scope")
    s.add_argument("--purge", action="store_true", help="delete out-of-scope videos (files + index)")
    s.set_defaults(fn=cmd_rescope)

    s = sub.add_parser("refresh-titles", parents=[common], help="fetch uploader title translations (YouTube localizations)")
    s.set_defaults(fn=cmd_refresh_titles)

    s = sub.add_parser("serve", parents=[common], help="serve the read-only image-evidence HTTP API")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname).1s %(message)s",
        datefmt="%H:%M:%S",
    )
    if not args.verbose:
        for noisy in ("httpx", "httpcore", "urllib3", "transformers"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
    try:
        return args.fn(args)
    except Exception as e:  # noqa: BLE001 - surface a clean error at the CLI boundary
        if args.verbose:
            raise
        log.error("%s: %s", type(e).__name__, e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
