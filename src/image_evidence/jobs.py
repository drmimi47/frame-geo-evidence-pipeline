"""Ingest jobs started from the site's Video panel: pasted video links and/or a search prompt.

- Tokens: a YouTube Data API key (required: to search, and to read a video's licence) and, optionally, an
  Anthropic API key that turns the prompt into YouTube searches. Both come from the page with each request
  (the server has no key of its own for jobs), are held in this job's memory while it runs and are never
  written to disk, logged or sent back.
- Folders: each job saves into an evidence folder, a library of its own: the main library (`library/`,
  Ukraine 2022..2026) or a project folder (`libraries/folder-<n>/`, named "Evidence folder <n>" until renamed;
  the name is in its `folder.json`). A folder's scope (`scope.json`) is fixed by the job that made it; a later
  job may only save into it with the same place and years within it. Every video passes its folder's gate.
- One job runs at a time (frame extraction and the image model are heavy); others wait in line.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

from .scope import HARD_END, HARD_START, SCOPE_FILE, UKRAINE, Scope, library_scope

log = logging.getLogger(__name__)

LLM_MODEL = "claude-opus-5-5"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MAX_QUERIES = 5        # each YouTube search costs 100 of the default 10,000 daily quota units
MAX_VIDEOS = 25
_UKRAINE_NAMES = {"ukraine", "україна", "украина", "ukrajina"}
_YT_ID = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([\w-]{11})|^([\w-]{11})$")


def youtube_ids(text: str) -> list[str]:
    """Video ids from pasted links or ids (any separator); raises on anything that isn't one."""
    out = []
    for token in re.split(r"[\s,]+", text.strip()):
        if not token:
            continue
        m = _YT_ID.search(token)
        if not m:
            raise ValueError(f"not a YouTube link or video id: {token[:80]!r}")
        out.append(m.group(1) or m.group(2))
    return list(dict.fromkeys(out))


@dataclass
class JobRequest:
    urls: list[str]
    prompt: str
    country: str
    places: list[str]
    start: date
    end: date
    max_videos: int
    licence: str            # "creativeCommon" | "any"
    folder: str | None = None    # an existing folder's slug ("" = the main library), or None: a new folder
    folder_name: str = ""        # the new folder's name ("Evidence folder <n>" when empty)
    youtube_key: str | None = field(default=None, repr=False)
    llm_key: str | None = field(default=None, repr=False)

    @classmethod
    def parse(cls, d: dict[str, Any]) -> "JobRequest":
        start = date.fromisoformat(d.get("start") or HARD_START.isoformat())
        end = date.fromisoformat(d.get("end") or HARD_END.isoformat())
        if start > end:
            raise ValueError("the date range starts after it ends")
        if end.year > date.today().year + 1 or start.year < 2005:
            raise ValueError("YouTube dates run from 2005 to now")
        req = cls(
            urls=youtube_ids(d.get("urls") or ""),
            prompt=(d.get("prompt") or "").strip()[:1000],
            country=(d.get("country") or "Ukraine").strip()[:80] or "Ukraine",
            places=[p.strip() for p in re.split(r"[,;\n]+", d.get("places") or "") if p.strip()][:10],
            start=start, end=end,
            max_videos=max(1, min(MAX_VIDEOS, int(d.get("max_videos") or 5))),
            licence="any" if d.get("licence") == "any" else "creativeCommon",
            youtube_key=(d.get("youtube_key") or "").strip() or None,
            llm_key=(d.get("llm_key") or "").strip() or None,
            folder=None if d.get("folder") in (None, "new") else str(d["folder"]),
            folder_name=" ".join(str(d.get("folder_name") or "").split())[:80],
        )
        if req.country.lower() in _UKRAINE_NAMES:
            req.country = "Ukraine"
        if not req.urls and not req.prompt and not req.places:
            raise ValueError("paste a video link, or describe what to search for")
        if not req.youtube_key:
            raise ValueError("paste your YouTube Data API key")
        return req


# ------------------------------------------------------------------ libraries


def libraries_dir(main_root: Path) -> Path:
    return Path(main_root).parent / "libraries"


FOLDER_FILE = "folder.json"
MAIN_TITLE = "Ukraine collection"
_FOLDER_DIR = re.compile(r"folder-(\d+)$")


def folder_title(root: Path, main: bool) -> str:
    try:
        return json.loads((Path(root) / FOLDER_FILE).read_text())["title"]
    except (OSError, ValueError, KeyError):
        return MAIN_TITLE if main else Path(root).name


def list_libraries(main_root: Path) -> list[dict[str, Any]]:
    """Every evidence folder: the main library first, then the project folders in the order they were made."""
    out = [{"slug": "", "root": Path(main_root), "scope": UKRAINE, "title": folder_title(main_root, True)}]
    d = libraries_dir(main_root)
    if d.is_dir():
        roots = [r for r in d.iterdir() if (r / SCOPE_FILE).is_file()]
        for root in sorted(roots, key=lambda r: (int(m.group(1)) if (m := _FOLDER_DIR.match(r.name)) else 10**9, r.name)):
            out.append({"slug": root.name, "root": root, "scope": library_scope(root), "title": folder_title(root, False)})
    return out


def next_folder(main_root: Path) -> tuple[str, str]:
    """(slug, default name) of the next new folder."""
    d = libraries_dir(main_root)
    used = [int(m.group(1)) for r in (d.iterdir() if d.is_dir() else []) if (m := _FOLDER_DIR.match(r.name))]
    n = max(used, default=0) + 1
    return f"folder-{n}", f"Evidence folder {n}"


def scope_label(scope: Scope) -> str:
    return f"{scope.name} {scope.start.year}–{scope.end.year}"


def resolve_folder(main_root: Path, req: JobRequest) -> tuple[Path, Scope, bool, str]:
    """(folder root, its scope, is new, its name) for a request. An existing folder keeps its scope: the request
    must be for the same place within its years. A new folder's scope is the request's place over whole years."""
    if req.folder is not None:
        x = next((x for x in list_libraries(main_root) if x["slug"] == req.folder), None)
        if x is None:
            raise ValueError("that folder no longer exists")
        sc = x["scope"]
        if req.country.lower() != sc.name.lower():
            raise ValueError(f"“{x['title']}” keeps only {sc.name}: save {req.country} to a new folder")
        if req.start < sc.start or req.end > sc.end:
            raise ValueError(f"“{x['title']}” keeps only videos published {sc.start.year}–{sc.end.year}: "
                             "choose years within it, or a new folder")
        return x["root"], sc, False, x["title"]
    slug, default = next_folder(main_root)
    start, end = date(req.start.year, 1, 1), date(req.end.year, 12, 31)
    if req.country == "Ukraine":
        scope = replace(UKRAINE, start=start, end=end, made_by="user")
    else:
        scope = Scope(name=req.country, start=start, end=end, spellings=tuple(req.places))
    return libraries_dir(main_root) / slug, scope, True, req.folder_name or default


def rename_folder(main_root: Path, slug: str, title: str) -> str:
    from .layout import write_json

    title = " ".join(title.split())[:80]
    x = next((x for x in list_libraries(main_root) if x["slug"] == slug), None)
    if x is None or not title:
        raise ValueError("no such folder" if x is None else "a folder needs a name")
    write_json(x["root"] / FOLDER_FILE, {"title": title})
    return title


# ------------------------------------------------------------------ the LLM step


def _plan_prompt(req: JobRequest, new_scope: bool) -> str:
    want = {
        "queries": f"up to {MAX_QUERIES} YouTube search strings, in the languages local uploaders use, that find videos showing "
                   "the places the user describes",
        "relevance_language": "ISO 639-1 code of the language most such videos are in, or null",
    }
    if new_scope:
        want["spellings"] = (f"how {req.country} and its main regions and cities are written in titles: English and local "
                             "spellings and scripts, up to 40 short strings (non-Latin ones as word stems that cover case endings)")
        want["bbox"] = f"[lon_min, lat_min, lon_max, lat_max] around {req.country}, or null if it isn't one area"
        want["language"] = f"ISO 639-1 code of {req.country}'s main language, or null"
    return (
        "You plan YouTube searches for a research collection of video frames of places: landscapes, architecture, "
        "infrastructure, nature, damage; not people or interiors.\n"
        f"Place (the collection's scope): {req.country}\n"
        f"Narrower places: {', '.join(req.places) or 'none'}\n"
        f"Published between {req.start} and {req.end}\n"
        f"What the user wants: {req.prompt or '(nothing more specific)'}\n\n"
        "Reply with one JSON object and nothing else, with these keys:\n"
        + "\n".join(f'- "{k}": {v}' for k, v in want.items())
    )


def plan_with_llm(req: JobRequest, new_scope: bool, http: httpx.Client | None = None) -> dict[str, Any]:
    """Ask Claude for the searches (and, for a new library, how its place is written). Its answer only
    steers the search and the new library's scope check; it is never evidence on a frame."""
    http = http or httpx.Client(timeout=90)
    r = http.post(ANTHROPIC_URL, headers={"x-api-key": req.llm_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                  json={"model": LLM_MODEL, "max_tokens": 2000, "messages": [{"role": "user", "content": _plan_prompt(req, new_scope)}]})
    if r.status_code != 200:
        try:
            msg = r.json()["error"]["message"]
        except Exception:
            msg = r.text[:200]
        raise RuntimeError(f"Anthropic API {r.status_code}: {msg}")
    text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise RuntimeError("the LLM didn't reply with a plan")
    return json.loads(m.group(0))


def plain_queries(req: JobRequest) -> list[str]:
    """Without an LLM: the prompt as typed, once per narrower place (or with the country when it doesn't name one)."""
    base = req.prompt
    if req.places:
        return [" ".join(f"{base} {p}".split()) for p in req.places][:MAX_QUERIES]
    if base and req.country.lower() not in base.lower():
        base = f"{base} {req.country}"
    return [base or req.country]


def _bbox(v: Any) -> tuple[float, float, float, float] | None:
    try:
        lon_min, lat_min, lon_max, lat_max = (float(x) for x in v)
    except (TypeError, ValueError):
        return None
    ok = -180 <= lon_min < lon_max <= 180 and -90 <= lat_min < lat_max <= 90
    return (lon_min, lat_min, lon_max, lat_max) if ok else None


# ------------------------------------------------------------------ jobs


@dataclass
class Job:
    id: str
    library: str
    scope: str
    folder: str = ""
    status: str = "queued"  # queued | running | done | failed
    log: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def public(self) -> dict[str, Any]:
        return {"id": self.id, "library": self.library, "scope": self.scope, "folder": self.folder, "status": self.status,
                "log": self.log[-80:], "results": self.results, "error": self.error, "started_at": self.started_at}


class _JobLog(logging.Handler):
    """Copies the pipeline's log lines from the job's own thread into the job, with the tokens blanked out."""

    def __init__(self, job: Job, secrets: list[str]):
        super().__init__(logging.INFO)
        self.job, self.secrets, self.thread = job, [s for s in secrets if s], threading.get_ident()

    def emit(self, record: logging.LogRecord) -> None:
        if record.thread != self.thread:
            return
        self.job.log.append(redact(record.getMessage(), self.secrets))


def redact(text: str, secrets: list[str]) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "•••")
    return text


class Jobs:
    def __init__(self, main_root: Path, classifier: Callable[[], Any] | None = None, on_done: Callable[[Job], None] | None = None):
        self.main_root = Path(main_root)
        self.classifier = classifier  # shared with search-by-image, so the model loads once
        self.on_done = on_done
        self.jobs: dict[str, Job] = {}
        self.run_lock = threading.Lock()
        self.folder_lock = threading.Lock()

    def start(self, req: JobRequest) -> Job:
        """Checks the folder (ValueError when the request doesn't fit it) and makes a new one at once, so it
        is listed, and numbered, while the job waits or runs."""
        from .layout import write_json

        with self.folder_lock:
            root, scope, new, title = resolve_folder(self.main_root, req)
            if new:
                root.mkdir(parents=True)
                write_json(root / SCOPE_FILE, scope.to_json())
                write_json(root / FOLDER_FILE, {"title": title})
        job = Job(id=uuid.uuid4().hex[:12], library=root.name if root != self.main_root else "", scope=scope_label(scope), folder=title)
        self.jobs[job.id] = job
        threading.Thread(target=self._run, args=(job, req, root, library_scope(root), new), daemon=True, name=f"job-{job.id}").start()
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def _run(self, job: Job, req: JobRequest, root: Path, scope: Scope, new: bool) -> None:
        secrets = [req.youtube_key or "", req.llm_key or ""]
        handler = _JobLog(job, secrets)
        logging.getLogger("image_evidence").addHandler(handler)
        try:
            if self.run_lock.locked():
                job.log.append("Waiting for the job before this one to finish…")
            with self.run_lock:
                job.status = "running"
                self._ingest(job, req, root, scope, new)
            job.status = "done"
        except Exception as e:  # noqa: BLE001 - reported to the page
            job.status, job.error = "failed", redact(f"{type(e).__name__}: {e}", secrets)
            log.info("failed: %s", job.error)
        finally:
            logging.getLogger("image_evidence").removeHandler(handler)
            req.youtube_key = req.llm_key = None  # drop the tokens with the job
            if self.on_done:
                self.on_done(job)

    def _ingest(self, job: Job, req: JobRequest, root: Path, scope: Scope, new: bool) -> None:
        from .config import Config, DiscoveryConfig
        from .layout import write_json

        plan: dict[str, Any] = {}
        if req.prompt or req.places or new:
            if req.llm_key:
                log.info("Asking %s to plan the searches…", LLM_MODEL)
                plan = plan_with_llm(req, new and not scope.is_ukraine)
            elif new and not scope.is_ukraine:
                log.info("No LLM token: %s's scope check only knows its name%s", req.country,
                         f" and {', '.join(req.places)}" if req.places else "")
        if new and not scope.is_ukraine and plan.get("spellings"):  # before any video is checked against it
            spellings = [*req.places, *[str(s)[:60] for s in plan["spellings"]]][:60]
            lang = plan.get("language")
            write_json(root / SCOPE_FILE, replace(scope, spellings=tuple(dict.fromkeys(spellings)), bbox=_bbox(plan.get("bbox")),
                                                  language=lang if isinstance(lang, str) and len(lang) == 2 else None,
                                                  made_by=f"user + {LLM_MODEL}").to_json())
            scope = library_scope(root)
        if new:
            log.info("Saving to “%s” (%s): %s", job.folder, scope_label(scope), root)

        cfg = Config()
        cfg.library_dir = root.resolve()
        cfg.acquisition.policy = "public" if req.licence == "any" else "creative_commons"
        if req.prompt or req.places:
            queries = [q.strip()[:200] for q in plan.get("queries") or [] if isinstance(q, str) and q.strip()][:MAX_QUERIES] or plain_queries(req)
            lang = plan.get("relevance_language")
            cfg.discovery = DiscoveryConfig.model_validate({
                "published_after": max(req.start, scope.start), "published_before": min(req.end, scope.end),
                "split_by_year": False, "extra_queries": queries, "video_license": req.licence,
                "max_results_per_query": min(50, max(5, req.max_videos * 2)),
                "max_videos_total": req.max_videos * 4, "max_ingest": req.max_videos,
                "relevance_language": lang if isinstance(lang, str) and len(lang) == 2 else None,
            }, context={"scope": scope})
            log.info("Searching YouTube: %s", " · ".join(repr(q) for q in queries))
            p = self._pipeline(cfg, req)
            report = p.run()
            job.results += [r.__dict__ for r in report.results]
            if not report.results:
                log.info("No new videos in scope among %d found", len(report.candidates))
        if req.urls:
            cfg.discovery = DiscoveryConfig.model_validate({"published_after": scope.start, "published_before": scope.end},
                                                           context={"scope": scope})
            p = self._pipeline(cfg, req)
            log.info("Adding %d video%s", len(req.urls), "" if len(req.urls) == 1 else "s")
            job.results += [r.__dict__ for r in p.ingest_ids(req.urls).results]
        done = sum(r["status"] == "processed" for r in job.results)
        log.info("Finished: %d added, %d skipped or rejected", done, len(job.results) - done)

    def _pipeline(self, cfg, req: JobRequest):
        from .pipeline import Pipeline

        p = Pipeline(cfg, api_key=req.youtube_key)
        if self.classifier and cfg.classification.backend != "none":
            p.classifier_factory = self.classifier
        return p

