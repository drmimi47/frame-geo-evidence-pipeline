"""Gather the v4 shot's record into v4/v4.json (from the project root, the project's venv):

    python -I v4_json.py <views_v4.json> <plants_f4.json> <render_dir> <birds_check.json> <compare.json> <encode.json> <out.json>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import birds_v4 as BI  # noqa: E402

FAMILY = {0: "white willow (Salix alba, S. x rubens)", 1: "black poplar (Populus nigra)",
          2: "willow and poplar saplings", 3: "false indigo (Amorpha fruticosa)", 4: "tamarisk (Tamarix ramosissima)",
          5: "common reed (Phragmites australis)", 6: "cattail (Typha)", 7: "tall grasses", 8: "Xanthium, Chenopodium",
          9: "wormwood (Artemisia)", 10: "flowering herbs (Lythrum, Melilotus, Epilobium)", 11: "dry stalks",
          12: "low grasses"}

SOURCES = {
    "bee-eater": ["iNaturalist observation 361466739 (Merops apiaster, European bee-eater), Oleksii Vasyliuk, "
                  "Mar'ianske, on the drained bed, 14 May 2026, CC BY: https://www.inaturalist.org/observations/361466739 "
                  "(heard in the soundscape's reeds layer, sound 1950258)"],
    "cormorant": ["Sidorenko & Siokhin 2016, Biosystems Diversity: 1,240 great cormorant nests on six towers of the "
                  "Enerhodar crossings in 2012 (https://cyberleninka.ru/article/n/nesting-of-great-cormorants-"
                  "phalacrocorax-carbo-on-man-made-structures-in-ukraine); nothing counted since the drainage "
                  "(reports/Kakhovka bed nature sounds.md). Drawn far off, flying away, never at a tower: no colony "
                  "is shown or implied"],
    "gull": ["Sidorenko & Siokhin 2016 (the same survey): Caspian gulls nested on the crossing in 2012; Rostyslav "
             "Romanyshyn's winter gulls on the Dnipro at Zaporizhzhia, xeno-canto, Jan-Feb 2025 "
             "(reports/Kakhovka bed nature sounds.md)"],
}


def main(views_json, plants_json, rdir, birds_json, compare_json, encode_json, out):
    view = next(v for v in json.load(open(views_json))["views"] if v["id"] == "f4")
    pl = json.load(open(plants_json))
    logs = {}
    for name in ("static", "matte", "full", "anim_0-900"):
        p = f"{rdir}/log_{name}.json"
        if os.path.exists(p):
            logs[name] = json.load(open(p))
    st = logs.get("static", {})
    birds = json.load(open(birds_json))
    comp = json.load(open(compare_json)) if os.path.exists(compare_json) else None
    enc = json.load(open(encode_json)) if os.path.exists(encode_json) else {}
    by_family = {FAMILY[int(k)]: v for k, v in pl["by_family"].items() if v}
    by_origin = {o: {"plants": d["plants"],
                     "by_family": {FAMILY[int(k)]: n for k, n in d["by_family"].items()},
                     "habitat_of_the_2025_pass_at_their_spots": d["habitat_at_spot"]}
                 for o, d in pl["by_origin"].items()}
    doc = {
        "what": "The v4 shot under-the-crossing (30 s, still camera): view f re-framed on Ferosplavna-1's axis, the "
                "plants mirrored about it with a young forest composed round tower 23, distant birds drawn, the flow "
                "dashes running on the lit wires. Storyboard material, not a frame of the film. Made 5 November 2026.",
        "said_so": [
            "The plants are modelled (procedural, representative shapes; species from the sources; tree heights "
            "sourced: willows 4-9 m, poplars 6.5-9.5 m; other heights typical).",
            "Where they stand is composed: the left of the axis is placed by the v3 rule from the 28 August 2025 "
            "pass; the right is that side mirrored and jittered, and the forest round tower 23's caisson is "
            "composed; neither reads the pass there (their habitat in the pass is recorded below). The symmetry is "
            "a framing choice, as are the lane toward the tower and the low growth in front of it.",
            "The birds are drawn: species recorded on or over the bed or at these crossings; shapes, sizes, "
            "wingbeats, speeds and paths representative and composed for the frame.",
            "The light is drawn: v3's dawn (a mid-May sunrise, the fixed sun and haze warmed, a drawn gradient sky "
            "and sun glow), while the record state is 11 September 2026. The flow dashes are the film's drawing "
            "convention. The towers are modelled by type at OSM's positions; the bed's heights are inferred.",
        ],
        "scene": {"file": "libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/"
                          "ZNPP-last-two-lines-3D-south.blend (opened read-only, never saved)",
                  "frame": 4001, "record_state": "11 September 2026: Ferosplavna-1 connected (lit, flow toward the "
                                                  "plant), Dniprovska cut",
                  "lines_running": st.get("running"),
                  "flow": "each line material's keyed 'flow time' replaced by an unkeyed twin set to "
                          "(4001 - 1) / 30 + K / 30 s at frame K of the shot (the film's own pace); every other key "
                          "held at frame 4001"},
        "camera": {"on_axis": "the vertical plane through the centres of Ferosplavna-1's towers 22 (4185, 6275) and "
                              "23 (4426.2, 7062.3), scene metres",
                   "position_m": st.get("camera", {}).get("location"),
                   "behind_tower_23_m": view["back_m"], "heading_deg": st.get("camera", {}).get("heading"),
                   "pitch_deg": view["pitch"], "roll_deg": 0.0, "lens_mm": view["lens"], "sensor_mm": 36.0,
                   "eye_above_ground_m": view["eye"], "ground_m": st.get("camera", {}).get("ground_m"),
                   "symmetry": "the tower and its conductors are symmetric about the tower's axis (phases at +-7.5 m "
                               "(z 109 m), +-11 m (98 m) and +-9.5 m (87 m) on both towers, measured on the wire "
                               "curves; the lattice +-12.2 m), so on the axis with zero roll tower 23 stands on the "
                               "frame's vertical centre line and the wires fall away symmetrically",
                   "still": "the camera does not move in the 30 s"},
        "plants": {"total": pl["plants"], "by_family": by_family, "by_origin": by_origin,
                   "composed_trees_not_on_woody_ground": pl["composed_trees_not_on_woody_ground"],
                   "kept_after_ground_rays": st.get("plants", {}).get("plants"),
                   "caisson_clear_m": view["caisson_clear_m"],
                   "caisson_clear_note": "nothing within this of any caisson's centre (the concrete is 22.5 m in "
                                         "radius, so 1 m off its widest edge; v3 kept 26 m); a plant whose ground "
                                         "ray meets the caisson first is dropped too",
                   "mirroring": {"rule": "plants placed by the v3 rule on the left of the axis are mirrored across "
                                         "it; each mirrored plant is moved by a normal jitter of sigma 0.25 m + 2% of "
                                         "its distance (at most 3 m), given a height x0.88-1.12 within its family's "
                                         "range, a new rotation and variant; 12% swap to a kindred family (willow and "
                                         "poplar; saplings, Amorpha and Tamarix; the herbs), recomputing the height; "
                                         "5% are left out",
                                 "seed": 4004},
                   "lane": {"gap": view["gap"], "low_wedge": view["low_wedge"],
                            "note": "gap [half-angle deg, from m, to m]: no trees, shrubs or reeds toward the tower; "
                                    "low_wedge [half-angle, from, to, max height m]: only growth under that height "
                                    "between the meadow's edge and the base, so the young forest at the base shows"},
                   "base_forest": view["base_forest"],
                   "lod": view["lod"]},
        "birds": {"drawn": True, "groups": birds["groups"], "keep_clear_px": birds["pad_px"],
                  "frames_near_wires_or_tower": birds["frames_near_wires_or_tower"],
                  "species": {k: {kk: v[kk] for kk in ("span", "body", "hz", "amp", "speed", "pattern")}
                              for k, v in BI.SPECIES.items()},
                  "paths": {g["id"]: {"species": g["species"], "t0_s": g["t0"], "birds": len(g["members"]),
                                      "screen_control_points_x_y_px_distance_m": g["screen"]} for g in BI.GROUPS},
                  "sources": SOURCES,
                  "shading": "flat emission silhouettes, tinted toward the dawn haze with distance (a drawn aerial "
                             "haze: 10% + 45% x (1 - exp(-d / 900 m)))"},
        "render": {"engine": "EEVEE (Blender 5.2.2)", "size": [1920, 1080], "fps": 30, "frames": 900,
                   "samples": 32, "test": "30 fps, a test as the project's rules say; the final would be 60",
                   "method": "the static picture once (static.exr: everything that does not move), the moving parts "
                             "per frame alone (the lit wires, their glow and fittings, the birds) in one animation "
                             "render, and a matte once (the moving wires' footprint with every other object as a "
                             "holdout, over the same alone); composite_v4.py lays moving x matte over static over the "
                             "sky, the birds occluded by the static plate's alpha",
                   "sky": "v3's dawn world evaluated per pixel in float (composite_v4.py), its colour ramp made "
                          "C1 (a monotone cubic through v3's stops, level at both ends): Blender's linear ramp has "
                          "kinks at its stops that showed as faint curved bands across the wide lens's sky; a "
                          "triangular dither of one 8-bit step",
                   "times_s": {"static": st.get("render_static_s"),
                               "matte": [logs.get("matte", {}).get("render_matte_A_s"),
                                         logs.get("matte", {}).get("render_matte_B_s")],
                               "moving_per_frame": logs.get("anim_0-900", {}).get("render_anim_s", {}).get("mean"),
                               "moving_total": logs.get("anim_0-900", {}).get("render_anim_s", {}).get("total"),
                               "full_check_frames": {k: v for k, v in logs.get("full", {}).items()
                                                     if k.startswith("render_full")}},
                   "composite_vs_full_render": comp,
                   "encode": enc},
    }
    json.dump(doc, open(out, "w"), indent=1, default=float)
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:])
