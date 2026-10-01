"""Derived visual features used to sort frames for spatial / forensic-architecture style review.

Two kinds, both computed from the frame's pixels (thumbnail), both descriptive rather than claims
about the world:

* pixel statistics (NumPy/OpenCV): colour, lightness, warmth, vegetation and snow cover;
* SigLIP zero-shot shares for camera angle and visible building damage, plus the image embedding
  itself (stored separately) for "similar view" ordering across videos.
"""

from __future__ import annotations

import colorsys

import cv2
import numpy as np
from PIL import Image

from .schema import Provenance, VisualFeatures

# Camera angle, ordered from straight down to eye level on a wall.
VIEWPOINTS: dict[str, list[str]] = {
    "top_down": ["a drone photo looking straight down from high above at roofs and roads",
                 "a vertical aerial photograph of the ground seen from high altitude, like a map"],
    "oblique_aerial": ["an oblique aerial drone view over a city toward the horizon", "a drone view looking across buildings from high above",
                       "an aerial view of a landscape from a drone"],
    "elevated": ["a view from a rooftop or an upper floor window", "a view from a hill or cliff over the landscape below"],
    "street_level": ["a photo taken standing on the ground at eye level", "a view along a street at eye level",
                     "a person standing in a field photographed at eye level"],
    "close_up": ["a close-up photo of an object held in hands", "a macro photo of plants, leaves or stones", "a close-up of a wall surface"],
}
# Captions tuned on this library (contact sheets per label); avoid subject words like "damaged" here,
# they pull drone shots of ruins into the close-up class.
VIEW_ORDER = list(VIEWPOINTS)
VIEW_NAMES = {"top_down": "top-down", "oblique_aerial": "oblique aerial", "elevated": "elevated",
              "street_level": "ground level", "close_up": "close-up"}

# Scale: how much of the world the frame takes in, ordered from a macro shot to a high aerial view. The score is
# the expected position over these groups (0 close-up .. 1 aerial), so frames between two groups sort between them.
# Captions tuned on this library's contact sheets: "a whole building seen from across the street" keeps ruined
# facades out of the close-ups, and "smoke on the horizon" moves distant ground views up to wide.
SCALE: dict[str, list[str]] = {
    "detail": ["a macro photo of a flower, an insect or leaves", "a close-up of a small object, stones or soil"],
    "object": ["a photo of one tree, one car or a doorway up close", "a close-up of part of a wall or a window"],
    "near": ["a yard, a courtyard or a short stretch of street", "a few metres of a path, a riverbank or bushes"],
    "street": ["a street with buildings on both sides", "a whole building seen from across the street",
               "a view across a field or a river to the trees beyond"],
    "wide": ["a wide landscape stretching to the horizon", "a panorama over a town from a hill",
             "a view far into the distance, with smoke or buildings on the horizon"],
    "aerial": ["an aerial photo of a whole town or district from high above", "a high drone view over fields, roads and rivers"],
}
SCALE_ORDER = list(SCALE)

DAMAGE: dict[str, list[str]] = {
    "intact": ["intact buildings in good condition", "an undamaged residential street"],
    "damaged": ["buildings with broken windows and shell damage", "a partly damaged building"],
    "destroyed": ["completely destroyed buildings and rubble", "burned-out ruins of buildings"],
    "no_buildings": ["a natural landscape with no buildings", "open water or fields without buildings"],
}


def pixel_features(img: Image.Image) -> dict:
    rgb = np.asarray(img.convert("RGB").resize((160, 90)), np.float32) / 255.0
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)  # H in degrees 0..360, S/V 0..1 for float input
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    w = s * v  # weight colourful, lit pixels
    hue = None
    if w.mean() > 0.06:
        ang = np.deg2rad(h)
        hue = float(np.rad2deg(np.arctan2((np.sin(ang) * w).sum(), (np.cos(ang) * w).sum())) % 360)
    mean = rgb.reshape(-1, 3).mean(0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    green = (g > r + 0.04) & (g > b + 0.02) & (v > 0.15)
    lower = slice(rgb.shape[0] // 2, None)  # ground half: bright sky shouldn't count as snow
    snow = (v[lower] > 0.78) & (s[lower] < 0.12)
    return {
        "color_hex": "#%02x%02x%02x" % tuple(int(c * 255) for c in mean),
        "hue": None if hue is None else round(hue, 1),
        "saturation": round(float(s.mean()), 3),
        "lightness": round(float(colorsys.rgb_to_hls(*mean)[1]), 3),
        "warmth": round(float((r - b).mean()), 3),
        "greenness": round(float(green.mean()), 3),
        "snow": round(float(snow.mean()), 3),
    }


def features(images: list[Image.Image], classifier=None, emb: np.ndarray | None = None) -> tuple[list[VisualFeatures], np.ndarray | None]:
    """Features for each image. With a SigLIP classifier, also camera angle, damage, and embeddings
    (reusing ``emb`` when the caller already has them)."""
    px = [pixel_features(im) for im in images]
    if classifier is None or not hasattr(classifier, "embed"):
        return [VisualFeatures(**p) for p in px], None
    if emb is None:
        emb = classifier.embed(images)
    views = classifier.zero_shot(emb, VIEWPOINTS)
    damage = classifier.zero_shot(emb, DAMAGE)
    scale = classifier.zero_shot(emb, SCALE)
    prov = Provenance(method="siglip_zero_shot", model=classifier.cfg.model,
                      evidence="camera angle, damage and scale: softmax share over caption groups (visual.py)")
    out = []
    for p, vs, ds, ss in zip(px, views, damage, scale):
        built = 1.0 - ds["no_buildings"]
        out.append(VisualFeatures(
            **p,
            viewpoint=max(vs, key=vs.get),
            viewpoint_scores=vs,
            # expected damage among frames that show buildings: 0 intact .. 1 destroyed
            damage=None if built < 0.35 else round((0.5 * ds["damaged"] + ds["destroyed"]) / built, 3),
            damage_scores=ds,
            scale=round(sum(i * ss[k] for i, k in enumerate(SCALE_ORDER)) / (len(SCALE_ORDER) - 1), 3),
            scale_scores=ss,
            provenance=prov,
        ))
    return out, emb


def save_embeddings(path, rows: dict[str, np.ndarray], model: str) -> None:
    """Merge rows into the video's embeddings sidecar (frames/embeddings.npz, float16)."""
    old = load_embeddings(path)[0] if path.exists() else {}
    old.update(rows)
    ids = sorted(old)
    np.savez_compressed(path, ids=np.array(ids), vecs=np.stack([old[i] for i in ids]).astype(np.float16), model=np.array(model))


def load_embeddings(path) -> tuple[dict[str, np.ndarray], str]:
    with np.load(path) as z:
        return {str(i): v.astype(np.float32) for i, v in zip(z["ids"], z["vecs"])}, str(z["model"])
