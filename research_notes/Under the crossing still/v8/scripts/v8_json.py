"""Gather the v8 shot's record into v8/v8.json (from the project root, the project's venv):

    python -I v8_json.py <out.json> <pass_dir>

Reads, beside the output: drowning_encode.json, join_check.json, render.log, ../v7/drowning_sound.json; and in the
pass dir: plan.json, plants_laid.npz, log_frames_*.json.
"""
import glob
import hashlib
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import composite_v8 as CV  # noqa: E402
import dieoff_v8 as DO  # noqa: E402
V7 = CV.V7


def load(p):
    return json.load(open(p)) if os.path.exists(p) else None


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def blender_times(pdir):
    fr = {}
    for p in glob.glob(f"{pdir}/log_frames_*.json"):
        fr.update(json.load(open(p))["frames"])
    if not fr:
        return None
    two = [v for v in fr.values() if v.get("static_scale") == 2]
    one = [v for v in fr.values() if v.get("static_scale") == 1]
    mean = lambda xs: round(sum(xs) / max(len(xs), 1), 2)  # noqa: E731
    return {"frames_rendered": len(fr),
            "static_2x_s_mean": mean([v["static_s"] for v in two]), "static_1x_s_mean": mean([v["static_s"] for v in one]),
            "pos_s_mean": mean([v["pos_s"] for v in fr.values()]),
            "matte_s_mean": mean([v["matte_s"] for v in fr.values() if "matte_s" in v]),
            "mattes": sum(1 for v in fr.values() if "matte_s" in v),
            "total_s_sum": round(sum(v["total_s"] for v in fr.values()), 1)}


def frame_times(log):
    if not os.path.exists(log):
        return None
    txt = open(log).read()
    ts = [float(m.group(1)) for m in re.finditer(r"^frame \d+ level [\d.]+ s ([\d.]+)$", txt, re.M)]
    dates = re.findall(r"^\w{3} \w{3} +\d+ [\d:]+ \w+ \d{4}$", txt, re.M)
    return {"frames_logged": len(ts), "mean_s": round(sum(ts) / max(len(ts), 1), 2), "max_s": max(ts or [0]),
            "workers": 3, "wall_clock": dates}


def main(out, pdir):
    v8 = os.path.dirname(os.path.abspath(out))
    v7 = os.path.join(v8, "..", "v7")
    plan = load(os.path.join(pdir, "plan.json"))
    D = DO.DieOff(np.load(os.path.join(pdir, "plants_laid.npz"), allow_pickle=True))
    kinds = {}
    for k, K in DO.KINDS.items():
        kinds[k] = {"families": [f"{f} {DO_FAM[f]}" for f in K["fams"]],
                    "lag_after_the_water_reaches_the_base_s": K["lag"], "stretch": K["stretch"],
                    "phases_in_the_kinds_seconds (x stretch)": {
                        "colour (as modelled -> yellow-brown -> grey-brown)": K["dead"],
                        "leaves gone (start, end, share)": K["leaf"],
                        "finer stems gone (start, end, share)": K["twig"],
                        "lean and fall (start, end, degrees)": K["tilt"],
                        "slump (start, end, height x, width x)": K["slump"],
                        "settling into the bed (start, end)": K["sink"],
                        "the rest dissolved (start, end)": K["fade"]},
                    "deadline_s": K["deadline"]}
    near = D.dist < 60
    near_gone = {}
    for k, K in DO.KINDS.items():
        m = (D.kind == k) & near & ~D.never
        g = D.t0[m] + K["fade"][1] * D.scale[m]
        near_gone[k] = {"plants_within_60m": int(m.sum()),
                        "start_median_s": round(float(np.median(D.t0[m])), 2),
                        "gone_s_5_50_95_100_pct": [round(float(x), 2) for x in np.percentile(g, [5, 50, 95, 100])]}
    doc = {
        "what": "v8 (8 November 2026, the user): \"another pass where the plants and stuff die off as the water rises "
                "so at the end of the animation it will only show the tower and the powerlines in the background\"; "
                "asked where the eye ends: \"Stay put, end underwater\". v7 (and v6, v5) are kept as they were. "
                "Storyboard material, not frames of the film.",
        "statement": {
            "on_screen": "nothing: no caption or key on the picture (as v7)",
            "to_be_said_elsewhere": CV.STATEMENT + "; and that the view under the water, its silt and the plants' "
                                    "dying are drawn. Where (the shot's caption field, a card or the credits) is the "
                                    "user's decision.",
        },
        "said_so": [
            "SPECULATIVE AND DRAWN: the water, its rise, ripples, reflections and murk, the silt, the lens crossing, "
            "the view from under the surface, and now the plants' dying (their browning, leaf and twig loss, slumping, "
            "falling, settling into the bed and dissolving) and its pace. Nothing is observed and nothing is generated "
            "by an AI tool: the plants are v3's procedural models, the scene the flight south's.",
            "TIME IS COMPRESSED FROM YEARS, NOT MONTHS: the rise is drawn in 10 s and the dying in about 12 s. As "
            "general knowledge, to be checked against a source before it is said in the film (no source was read for "
            "this shot): herbs and grasses of dry ground die within weeks under water; white willow tolerates long "
            "flooding of its roots, and permanent deep flooding kills it over one to a few growing seasons; drowned "
            "trunks often stand for years or decades in reservoirs. So the shot draws years in seconds, and the "
            "trunks' disappearance (fallen, settled into the bed, dissolved into the silt) is a drawing "
            "simplification, so the end can hold on the tower and the wires (the user's ask).",
            "The order is a drawing of how these plants die under water, not a simulation: the herbs and grasses "
            "first (they go under first: they wilt, brown, slump and dissolve into the silt), then the reeds (brown, "
            "lean, break and fall), the shrubs and saplings, and the willows and poplars last (leaves yellow-brown and "
            "thinning, bare branches, the trunks leaning over and settling into the bed). Each plant starts when the "
            "drawn water reaches its base, in the shot's compressed time.",
            "Plants whose ground lies above the proposed level are left alive (" + str(int(D.never.sum())) + " far "
            "trees on higher ground, 600 m and more off; they are not seen at the end: the view through the surface "
            "near the horizon is absorbed).",
            "The silt settling as the dying ends (the absorption toward the bottom lengthening a little from "
            f"{CV.MURK_SETTLE[0]} s to {CV.MURK_SETTLE[1]} s, the bed greyed toward silt up to {CV.SILT_MAX_SETTLED}) "
            "is drawn.",
            "The level is a proposal: 12.7 m Baltic (Vyshnevskyi & Shevchuk 2024, p. 286), 13.1 m in the scene "
            "(EGM2008, Baltic +0.4 m). The bed's heights it rises through are inferred (scene3d/bed.py).",
            "The view through the surface is a drawn convention (Snell's window not drawn; the water above the eye "
            "drawn clear enough for the tower and the lit wires to stay readable). The flow dashes are the film's "
            "drawing convention (the record's state of 11 September 2026); the far birds are v5's drawn birds.",
            "The sound is v7's, unchanged (the same 15 s, the same lens crossing): the soundscape continued, only the "
            "synthesized line, muffled under water (drawn). The dying has no sound of its own: no sound effects.",
        ],
        "approach": {
            "why": "the plants are dense and layered: removing them per pixel against one plate without plants would "
                   "also remove plants hidden behind them and never show what each dying plant uncovers. So the "
                   "plants change in Blender, per frame, and the picture, the heights and the wire matte are rendered "
                   "per frame; v7's compositor draws its water on them unchanged.",
            "blender": "still_v8.py: v3's models and placement and v5's camera f exactly; the instancer (Geometry Nodes, "
                       "Instance on Points) takes per plant a rotation (its own turn and its fall), a scale (slump), a "
                       "position (settling) and four values the plant material reads as instancer attributes: dead "
                       "(colour), leaf, twig and fade (losses, against one random number per leaf, blade, card or "
                       "stem, and a stem's thickness order, added to the models as face attributes: the models' "
                       "geometry and colours untouched). Losses are a transparency (dithered at 32 samples in the "
                       "picture; a hard cut in the one-sample height pass).",
            "dieoff": "dieoff_v8.py (plain numpy): each plant's start = when v7's drawn level reaches its base (at least "
                      f"{DO.WATER_IN} s, when v7 has the water fully drawn) + its kind's lag; its kind's phases; the "
                      "kind's deadline (a plant reached late dies faster, down to 0.45x); fall directions random, those "
                      f"within {DO.NEAR_M} m of the eye away from it (never into the lens); per-plant jitter of lag "
                      f"({DO.JITTER_LAG} s) and pace ({DO.JITTER_PACE}).",
            "passes_per_frame": "static_K.exr (the picture without the moving parts: 2x until frame "
                                f"{plan and plan.get('one_x_from')}, from above the water; 1x after, under it), "
                                "pos_K.exr (heights and distances, 2x, one exact sample), matte_K.exr (the lit wires "
                                "white over everything else black, 1x, every 5th frame and the last, linear between)",
            "frames_with_passes": plan,
            "composite": "composite_v8.py: v7's composite_v7.py imported unchanged; per frame its plate, heights and "
                         "matte replaced by the frame's (v5's 1080p plate plus the 2x plate's change from v6's, so "
                         "unchanged pixels are v5's exactly, as in v7)",
            "frame_0": "the plants' state at frame 0 is v6's exactly (checked: the per-frame plate at frame 0 against v6's "
                       "static2x.exr, 23 of 8.3 million values over 0.01 linear; the matte against v5's, at most 0.014)",
        },
        "timeline": {"water": V7.timeline(), "dying_by_kind_all_plants": D.summary(),
                     "dying_in_view_within_60m": near_gone, "kinds": kinds,
                     "clear_from_s": round(max(v["gone_s_5_50_95_100_pct"][3] for v in near_gone.values()), 2),
                     "held_clear_to_s": CV.SECONDS},
        "continuity": {"check": load(os.path.join(v8, "join_check.json")),
                       "how": "as v7: frame 0 is the frame after under_the_crossing_f_day.mp4's last; the plants only "
                              "change once the water has reached them (from frame " + str(plan and plan.get("first")) +
                              "), so v8's first 25 frames are v7's"},
        "under_the_water": {"as_v7": True, "settling": {"from_to_s": CV.MURK_SETTLE,
                                                        "absorb_toward_the_bottom_m_rgb": [CV.ABSORB_SILT_V7.tolist(),
                                                                                           CV.ABSORB_SILT_SETTLED.tolist()],
                                                        "silt_max": [CV.SILT_MAX_V7, CV.SILT_MAX_SETTLED]}},
        "level": {"value_m": V7.LEVEL_BALTIC, "datum": "Baltic", "baltic_to_egm2008_m": V7.BALTIC_TO_EGM2008,
                  "level_scene_m": V7.LEVEL, "source": "Vyshnevskyi & Shevchuk 2024, p. 286",
                  "eye_m": round(float(V7.EYE[2]), 3)},
        "render": {"blender": blender_times(pdir), "frames": frame_times(os.path.join(v8, "render.log")),
                   "moving_parts": "v7's moving pass (still_v5.py anim 900:1350), reused",
                   "output": "1920x1080, 30 fps (a storyboard test), 450 frames",
                   "encode": load(os.path.join(v8, "drowning_encode.json"))},
        "sound": {"files": {"drowning.wav": sha(os.path.join(v8, "drowning.wav")),
                            "alt/drowning_continuous.wav": sha(os.path.join(v8, "alt", "drowning_continuous.wav"))},
                  "same_as_v7": sha(os.path.join(v8, "drowning.wav")) == sha(os.path.join(v7, "drowning.wav")),
                  "v7_record": load(os.path.join(v7, "drowning_sound.json"))},
        "seen": [
            "0-4.2 s (over the water): the herbs, reeds and willows turn yellow-brown and grey-brown as the water "
            "climbs them; the herbs at the waterline slump; the reed blades thin.",
            "4.2-9 s (under): the herbs and reeds collapse and settle, the willows lose their leaves, stand bare, lean "
            "and settle; the crowns above the surface die with them, wavering through it.",
            "From about 9.5 s the view reads clear: the last stages of the far plants (settling, dissolving) happen "
            "in the murk. The mean change between frames falls to the ripples' alone from 9 s (0.4 of 255 at a "
            "quarter size, against 2.4-6.4 while the plants fall). So the clear hold is about 5.5 s, longer than the "
            "2-3 s aimed for: trim the shot's out to about 12.5 s, or slow the trees' pace and render again.",
            "The bed under the water is barely seen: v7's murk and depth darkening leave it a dark floor (lengthening "
            "the absorption at the end, tried at up to 2.3x, changed little).",
            "No flicker found: the largest step between frames is at the lens crossing (frame 124); the 2x-to-1x "
            "switch at frame 140 and the matte's 5-frame steps show no jump.",
        ],
        "files": {"drowning.mp4": "15 s, for the cut as it stands (sound rising from the cut's silence, v7's)",
                  "alt/drowning_continuous.mp4": "the same picture with the hum unbroken through the cut; with "
                                                 "../v7/alt/under_the_crossing_f_day_continuous.mp4",
                  "join_test.mp4": "the last 3 s of under-the-crossing and the first 3 s of the drowning",
                  "contact_sheet.png": "a frame every second, and the last",
                  "stills": sorted(f for f in os.listdir(v8) if f.endswith(".png"))},
    }
    json.dump(doc, open(out, "w"), indent=1, ensure_ascii=False, default=float)
    print("wrote", out)


DO_FAM = {0: "white willow", 1: "black poplar", 2: "saplings", 3: "Amorpha fruticosa", 4: "Tamarix ramosissima",
          5: "Phragmites australis", 6: "Typha", 7: "tall grasses", 8: "Xanthium, Chenopodium", 9: "Artemisia",
          10: "Lythrum, Melilotus, Epilobium", 11: "dry stalks", 12: "low grasses"}

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
