# Historical-film study state

The active website uses two historical films, `1.mp4` and `3.mp4`. Its Gallery filters film frames by video, landscape category, and geolocation potential. Editing saves multi-label reviews to local `outputs/landscape/manual_annotations.json`. History shows the Dnipro hydropower timeline and two tables of important film locations linked to Gallery frames.

`data/landscape/predictions.json` contains the versioned B0 frame-level labels and human corrections. `data/landscape/manual_annotations.json` is the versioned baseline of website edits. `data/landscape/geolocation/predictions.json` stores geolocation assessments, while `suitability.json` and `zainali/results.csv` support filtering and clearly marked fallback predictions. A place name or a predicted pin is not treated as an exact filming position without independent evidence.

Run `python3 scripts/prepare_local_gallery.py --media-from PATH/TO/outputs/landscape` to restore these text records and copy local film-frame and overlay JPEGs into ignored `outputs/`. Run `./start_landscape.command` and open <http://127.0.0.1:8765>. The website regenerates its HTML and CSV projections from the records. Context MP4 clips and detailed evidence pages are optional local artifacts and are not in Git.

The original videos, model weights, generated images, archival aerial material, and snapshots remain outside this repository. The model is SegFormer B0 (`nvidia/segformer-b0-finetuned-ade-512-512`), using the combined `plants` label. It was used as a pretrained model without custom training. Segmentation boundaries are model predictions; saved human labels correct image-level tags, not the masks.

This study is isolated from the parent repository's Ukraine 2022–2026 YouTube ingestion libraries. The archival films' capture dates are distinct from any YouTube upload dates.
