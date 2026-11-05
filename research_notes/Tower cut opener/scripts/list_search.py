"""List the yt-dlp search results (flat), one line per unique video, with the queries that found it."""
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
seen = {}
for f in sorted(d.glob("q*.jsonl")):
    q = (f.with_suffix(".query")).read_text().strip()
    for line in f.read_text().splitlines():
        it = json.loads(line)
        v = seen.setdefault(it["id"], {"id": it["id"], "title": it.get("title"), "channel": it.get("channel") or it.get("uploader"),
                                       "duration": it.get("duration"), "views": it.get("view_count"), "queries": []})
        v["queries"].append(f.stem)
for v in seen.values():
    print(f'{v["id"]}  {int(v["duration"] or 0):>5}s  {",".join(v["queries"]):<12} [{(v["channel"] or "")[:28]}]  {(v["title"] or "")[:90]}')
print(len(seen), "unique")
