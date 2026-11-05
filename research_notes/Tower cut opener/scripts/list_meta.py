"""One line per video's yt-dlp metadata: id, upload date, licence, duration, channel, title."""
import json, sys, pathlib
for f in sorted(pathlib.Path(sys.argv[1]).glob("*.json")):
    try:
        m = json.loads(f.read_text())
        assert isinstance(m, dict)
    except Exception:
        print(f.stem, "NO METADATA"); continue
    print(f'{m["id"]}  {m.get("upload_date")}  {(m.get("license") or "standard")[:22]:<22} {int(m.get("duration") or 0):>5}s {m.get("height")}p [{(m.get("channel") or "")[:26]}] {m.get("title","")[:70]}')
