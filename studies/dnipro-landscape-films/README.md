# Dnipro historical-film landscape study

This self-contained study examines landscape frames from two historical films (`1.mp4` and `3.mp4`). Its read-only HTML page has Gallery and History views, including broad SegFormer B0 vegetation and landscape labels, graded geolocation claims, and a Dnipro hydropower timeline. It opens as a local file without a server. It is separate from the repository's YouTube collection and does not write to `library/` or `libraries/`.

The repository includes source code and small, curated text data in `data/`: 102 frame records, saved human label edits, geolocation assessments, screening decisions, and the two film-location tables. It excludes the original videos, extracted images, segmentation overlays, context clips, downloaded model weights, historical aerial images, snapshots, credentials, and generated research files. These remain in the original local project. A fresh clone therefore needs local film images before its gallery can display them.

To use the local film images already generated in the original project:

```sh
cd studies/dnipro-landscape-films
python3 scripts/prepare_local_gallery.py --media-from /Users/xmy/Desktop/adv5/outputs/landscape
```

Open `outputs/landscape/index.html` in a browser. The preparation command copies only film-frame JPEGs and B0 overlay JPEGs into this study's ignored `outputs/` directory. It restores versioned text data without replacing local changes. The gallery works without context clips; frames with supported geolocations then show the segmentation overlay in the right panel. To show those clips locally, copy the original `outputs/landscape/geolocation/clips/` directory into this study's ignored `outputs/landscape/geolocation/` directory and rebuild the page.

When the parent app runs with `evidence serve`, its **Films** link also opens this prepared gallery at `/film-study/`. This is navigation between two separate studies; the film frames are not ingested into the parent collection.

The reviewed labels are historical records, not editable controls. This GitHub study has no label-saving endpoint or localhost requirement.

`scripts/process_landscapes.py` documents the original B0 production process. A full rerun also requires the original MP4s, the local model weights, and the screened input frames named by `data/landscape/screening/decisions.json`. None are distributed in this repository. The model is the public `nvidia/segformer-b0-finetuned-ade-512-512` checkpoint; this project did not train a custom model.

See [project state](docs/PROJECT_STATE.md) for the data layout and evidence limits. The historical-film study does not relax the parent repository's video publication-date gate.
