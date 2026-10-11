# Scene Viewer reconstruction, step 1 of 2 (then compose.py). Needs its own Python 3.12 venv (macOS arm64):
#   python3.12 -m venv .venv-scene && .venv-scene/bin/pip install pycolmap msplat pillow numpy
# Frames of one continuous take (from a downloaded copy of the video), e.g. for cSThxR6dXpc (Bandura river):
#   ice pools, 4:38-5:28, from a 1080p download of 4:36-5:30 (yt-dlp --download-sections "*4:36-5:30"), 5 fps:
#     ffmpeg -ss 2.1 -to 52.9 -i bandura_pools.mp4 -vf fps=5 -q:v 2 pools/images/f%04d.jpg
#     .venv-scene/bin/python scripts/scene/reconstruct.py pools 1750 30 1880 170
#   then (one take at a time; the others in scene.json are kept):
#     .venv-scene/bin/python scripts/scene/compose.py library/videos/cSThxR6dXpc/inferred/track.json \
#       library/videos/cSThxR6dXpc/derived/scene "pools:pools:278.1:328.9:Ice pools:iters=15000:level=ice:eye=1.3:source=1080p:keep=99:open=295.3"
import pycolmap, sys, pathlib, time
from PIL import Image
w = pathlib.Path(sys.argv[1]); box = tuple(int(v) for v in sys.argv[2:6])
imgs = sorted((w / "images").glob("*.jpg")); W, H = Image.open(imgs[0]).size
(w / "masks").mkdir(exist_ok=True); (w / "sparse").mkdir(exist_ok=True)
for p in imgs:
    m = Image.new("L", (W, H), 255); m.paste(0, box); m.save(w / "masks" / (p.name + ".png"))
db = w / "database.db"; db.unlink(missing_ok=True)
t = time.time()
ext = pycolmap.FeatureExtractionOptions(); ext.sift.max_num_features = 8192
pycolmap.extract_features(db, w / "images", camera_mode=pycolmap.CameraMode.SINGLE,
    reader_options=pycolmap.ImageReaderOptions(camera_model="SIMPLE_RADIAL", mask_path=str(w / "masks")), extraction_options=ext)
print("features", round(time.time() - t), flush=True); t = time.time()
pycolmap.match_exhaustive(db)
print("matching", round(time.time() - t), flush=True); t = time.time()
maps = pycolmap.incremental_mapping(db, w / "images", w / "sparse")
print("mapping", round(time.time() - t), flush=True)
for k, r in maps.items():
    print(w.name, k, r.num_reg_images(), "of", len(imgs), "images", r.num_points3D(), "points", flush=True)
