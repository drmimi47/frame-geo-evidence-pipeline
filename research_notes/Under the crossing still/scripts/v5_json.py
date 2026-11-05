"""Gather the v5 shots' record into v5/v5.json (from the project root, the project's venv):

    python -I v5_json.py <render_dir> <out.json>

The render dir holds still_v5.py's logs, birds_check.json, compare_*.json, the encoders' *_encode.json (copied in),
and reprise_sound.json.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import birds_v5  # noqa: E402,F401
import birds_v4 as BI  # noqa: E402
from v4_json import FAMILY, SOURCES  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, ".."))


def load(p):
    return json.load(open(p)) if os.path.exists(p) else None


def main(rdir, out):
    view = next(v for v in json.load(open(f"{HERE}/views_v5.json"))["views"] if v["id"] == "f")
    pl = json.load(open(f"{ROOT}/v3/plants/plants_f.json"))
    logs = {n: load(f"{rdir}/log_{n}.json") for n in ("mask", "static", "matte", "full", "anim_0-900", "contour", "world")}
    ct = logs["contour"]
    doc = {
        "what": "v5 (5 November 2026): the shot under-the-crossing again as v3's view f by day (the user: 'i prefer "
                "the composition of the original \"f day\" still ... re-render the video so it is like the original "
                "\"f day\" proposal ... during the day'), 30 s, and a separate short, waterline-reprise: the same "
                "view held with the proposed refilled level drawn as a line where the scene's surfaces cross it. "
                "Storyboard material, not frames of the film.",
        "said_so": [
            "The plants are modelled (procedural, representative shapes), placed by v3's rule from the 28 August "
            "2025 Sentinel-2 pass (v3/plants/plants_f.npz, unchanged); the lane toward the tower is kept open, a "
            "framing choice (v3's gap).",
            "The towers, wires and fittings are the flight south's scene (positions OpenStreetMap's, shapes "
            "representative); the flow dashes are a drawing convention, held at the record's state of 11 "
            "September 2026 (Ferosplavna-1 connected, Dniprovska cut).",
            "The birds are drawn: species recorded on or over the bed and at these crossings, shapes and flight "
            "representative, paths composed for the frame.",
            "The sound is a montage (the speculative soundscape): nothing was recorded at the crossing; the line is "
            "synthesized.",
            "The waterline is inferred x proposed: the level is a proposal (Vyshnevskyi & Shevchuk 2024, p. 286), "
            "the bed's heights it is drawn on are inferred (FABDEM's bare earth over the old reservoir is flat water: "
            "the drained bed's relief in the scene is the waterline method's, scene3d/bed.py), and the plants it "
            "crosses are modelled. It is a line, not water: no surface, fill or tint.",
        ],
        "camera": {"view": view, "location_m": logs["static"]["camera"]["location"],
                   "ground_m": logs["static"]["camera"]["ground_m"], "on": logs["static"]["camera"]["on"],
                   "heading_deg": view["heading"], "pitch_deg": view["pitch"], "roll_deg": 0, "lens_mm": view["lens"],
                   "sensor_mm": 36, "eye_m": view["eye"], "still": True,
                   "note": "exactly v3's view f (scripts/views.json), the scene's frame 4001"},
        "light": {"what": "the film's day: its fixed sun (0.35, -0.61, 0.71), its haze (linear 0.62, 0.66, 0.70) and "
                          "its overcast world, one flat colour (EEVEE's world render: sRGB 207, 213, 218); as v3's "
                          "f_day.png",
                  "first_frame_vs_v3_f_day": load(f"{rdir}/compare_v3.json")},
        "plants": {"file": "v3/plants/plants_f.npz (v3's, unchanged)", "count": pl["plants"],
                   "by_layer": pl["by_layer"],
                   "by_family": {FAMILY[int(k)]: v for k, v in pl["by_family"].items() if v},
                   "note": "laid on the scene's ground as v3; the scatter named 'plants f' as v3 named it, since the "
                           "name seeds each plant's Object Info random brightness"},
        "birds": {"module": "scripts/birds_v5.py (birds_v4's species and flight, paths composed again for this "
                            "framing, all in the open sky right of the span)",
                  "groups": [dict(id=g["id"], species=g["species"], t0_s=g["t0"], birds=len(g["members"]),
                                  screen_path_px_m=g["screen"]) for g in BI.GROUPS],
                  "species": {k: dict(v, source=SOURCES[k]) for k, v in BI.SPECIES.items()},
                  "haze_srgb": list(BI.HAZE),
                  "check": load(f"{rdir}/birds_check.json")},
        "render": {"engine": "EEVEE (Blender 5.2.2), 32 samples, 1920x1080, 30 fps (a test; the final would be 60)",
                   "method": "still_v4.py's passes (run by still_v5.py): the static picture once, the moving parts "
                             "(lit wires, glow, fittings, birds) per frame over nothing, the wires' matte once (A/B), "
                             "composited over the flat day sky (composite_v5.py, composite_v4's maths) with a "
                             "one-step triangular dither",
                   "logs": {k: v for k, v in logs.items() if v},
                   "composite_vs_full": {k: load(f"{rdir}/compare_{k}.json") for k in ("0000", "0450", "0899")},
                   "encode": {"under_the_crossing_f_day": load(f"{rdir}/under_the_crossing_f_day_encode.json"),
                              "waterline_reprise": load(f"{rdir}/waterline_reprise_encode.json")}},
        "waterline": {
            "level": {"value_m": 12.7, "datum": "Baltic (the Ukrainian levels' system)",
                      "what": "the dead-volume level, proposed for a temporary dam (refilling the reservoir to it)",
                      "source": "Vyshnevskyi & Shevchuk 2024, p. 286 (reports/ZNPP speculative ending and ecology.md)",
                      "note": "the reports also give 12.7 m as IAEA Update 162's reservoir figure; the project config "
                              "cites Update 163 for a measured level of about 12.7 m at the plant on 8 June 2023 "
                              "(Update 162: 14.03 m on 7 June). Not checked again here."},
            "datum_conversion": {"baltic_to_egm2008_m": ct["baltic_to_egm2008_m"],
                                 "source": "config/conductive-seam.yaml crossing3d.bed baltic_m (Baltic +0.4 m to "
                                           "EGM2008); the scene's z is FABDEM's metres above EGM2008",
                                 "level_scene_m": ct["level_scene_m"]},
            "eye": {"ground_m": ct["camera"]["ground_m"], "eye_m": ct["camera"]["eye_m"],
                    "eye_below_level_m": ct["camera"]["eye_below_level_m"],
                    "note": "the camera stands 2.25 m below the proposed level: at that level the view would be "
                            "under water. The camera is not moved; so the level's plane lies above the eye and the "
                            "line falls above the horizon, on whatever stands taller than it."},
            "drawn_on": ["the caisson of tower 23: a clean line round its foot, about 0.5 m above the ground there",
                         "the reeds, tall grasses and young willows of the meadow in the distance: a broken line of "
                         "dashes across their stems near the horizon (the level's plane seen from below)",
                         "the willow crown at the top left (near): patches across the leaves that lie at the level",
                         "not on tower 23 or the wires (they stand above it on the caisson), not on the sky"],
            "how": {"pass": "still_v5.py contour: every surface drawn flat black (view_layer material override) but "
                            "a band where |world z - 13.1| is under h, h = the eye distance x (36 mm / 18 mm / 1920 px) "
                            "x 3.5 px x max(sin(slope), 0.15), at least 1 mm: about 7 px wide on screen; the glows "
                            "left out; film-transparent; the band's red channel is the line's matte",
                    "px": ct["line_px"], "min_slope_sin": ct["min_slope_sin"], "floor_half_m": ct["floor_half_m"],
                    "composite": "a saturated mid blue, sRGB (40, 110, 230), opaque, over a 1 px darker edge, sRGB (12, 34, "
                                 "80) (the matte grown by 1 px), laid on the static plate, under the moving wires (they "
                                 "pass in front of it where nearer); plain for 2 s, faded in over 2 s (smoothstep), "
                                 "held. Blue at the user's request (5 November 2026: 'thicker and blue so it stands "
                                 "out'); a first version was white, about 2 px wide, at 0.9",
                    "render_s": ct["render_s"]},
            "label": "PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI & SHEVCHUK 2024 · THE BED'S HEIGHTS INFERRED (white "
                     "capitals, Helvetica Neue 16 px, a black box at half opacity, bottom left, fading in with the "
                     "line; a short stroke of the line's blue before the text, its key)",
            "tier": "inferred x proposed"},
        "reprise_sound": load(f"{rdir}/reprise_sound.json"),
        "files": {"under_the_crossing_f_day.mp4": "30 s, 900 frames, the soundscape "
                                                  "(../Speculative crossing soundscape/under_the_crossing.wav)",
                  "waterline_reprise.mp4": "9 s, 270 frames (the moving pass of the 30 s shot, its frames 630-899: the far cormorants and gull only, checked clear of the line), waterline_reprise.wav (waterline_reprise_sound.json)",
                  "stills": sorted(f for f in os.listdir(os.path.dirname(out)) if f.endswith(".png"))},
    }
    json.dump(doc, open(out, "w"), indent=1, ensure_ascii=False, default=float)
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
