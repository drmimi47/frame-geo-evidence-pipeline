"""Restore versioned film metadata and optional local images into the ignored workspace."""

import argparse
import json
import shutil
from pathlib import Path

from render_landscape_gallery import page

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"


def copy_missing(source, destination):
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media-from", type=Path, help="Existing local outputs/landscape directory")
    args = parser.parse_args()

    for source in DATA.rglob("*"):
        if source.is_file():
            copy_missing(source, OUTPUTS / source.relative_to(DATA))

    landscape = OUTPUTS / "landscape"
    if args.media_from:
        media = args.media_from.expanduser().resolve()
        if not media.is_dir():
            parser.error(f"Media directory does not exist: {media}")
        for folder in ("frames", "overlays"):
            for source in (media / folder).glob("*.jpg"):
                copy_missing(source, landscape / folder / source.name)

    rows = json.loads((landscape / "predictions.json").read_text())
    missing = [row["filename"] for row in rows if not (landscape / "frames" / row["filename"]).is_file()]
    if missing:
        print(f"Restored metadata. {len(missing)} film frames are missing; supply --media-from to view the gallery.")
        return
    (landscape / "index.html").write_text(page(rows, "Landscape frames"))
    uncertain = landscape / "uncertain"
    uncertain.mkdir(exist_ok=True)
    flagged = [row for row in rows if row["review_reasons"]]
    (uncertain / "index.html").write_text(page(flagged, "Uncertain landscape frames", True))
    print(f"Gallery ready: {len(rows)} film frames. Open {landscape / 'index.html'}")


if __name__ == "__main__":
    main()
