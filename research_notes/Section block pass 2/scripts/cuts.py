"""Section block pass 2: the cuts and the 2D section's layout (gfilm.py's, without the key plan), as numbers, shared by
the Blender scripts and the composer (numpy only).

The layout: each piece rendered alone (profile2.py / profile3.py, its camera at the middle of the piece, 6.46875 m a
pixel, the world height 672 m at its middle row), then pasted side by side: the dike piece from x = M, a GAP, the
crossing piece; both 60 rows up (DY). So the layout's column for a point s metres along a piece is
    X = 960 + (s - s_mid) / PX + shift            (shift = M - round(x0) of that piece)
and its row for a world height z (z = true height x ex_g) is 540 - (z - (672 - 60 PX)) / PX. The block's last frame
puts its camera so that the same formulas hold, which is what makes the hand-over exact."""
import math

import numpy as np

CUTS = {"0": ((3632.0, 3233.0), (5386.0, 9027.0), 500.0),        # Dniprovska: towers 21 to 27, 500 m on each end
        "1": ((3298.0, 3332.0), (5073.0, 9199.0), 500.0),        # Ferosplavna: 18 to 26
        "dike": ((-3000.0, 600.0), (-3000.0, 4400.0), 0.0)}      # the pond's north part, its dike, the bed
W, H, PX, ZC, DY, GAP = 1920, 1080, 12420.0 / 1920, 672.0, -60, 120   # gfilm.py's section frame and layout
DEPTH = 250.0           # the block's slices: as deep behind each cut as the section draws towers from it (NEAR)


def geom(piece):
    P0, P1, pad = CUTS[piece]
    P0, P1 = np.array(P0), np.array(P1)
    L = float(np.linalg.norm(P1 - P0)); U = (P1 - P0) / L; N = np.array([U[1], -U[0]])
    S = np.arange(-pad, L + pad, 10.0)
    return P0, U, N, L, pad, S


def layout(line):
    """gfilm.py's layout for a line ("0" or "1"): each piece's s_mid, shift, and where things are."""
    out = {}
    for piece in ("dike", line):
        P0, U, N, L, pad, S = geom(piece)
        mid = L / 2
        x0, x1 = 960 + (S[0] - mid) / PX, 960 + (S[-1] - mid) / PX
        out[piece] = dict(P0=P0, U=U, N=N, L=L, pad=pad, mid=mid, x0=round(x0), x1=round(x1), S0=S[0], S1=S[-1])
    d, c = out["dike"], out[line]
    M = (W - (d["x1"] - d["x0"]) - GAP - (c["x1"] - c["x0"])) // 2
    d["shift"] = M - d["x0"]; c["oxc"] = M + (d["x1"] - d["x0"]) + GAP; c["shift"] = c["oxc"] - c["x0"]
    out["M"] = M; out["gx"] = M + (d["x1"] - d["x0"]) + GAP // 2
    out["zc_layout"] = ZC + DY * PX            # the world height at the layout's middle row
    # the block's single camera at the end (prototype B): centred on the crossing's frame
    c["s_cam"] = c["mid"] - c["shift"] * PX
    d["sigma"] = c["s_cam"] - d["mid"] + d["shift"] * PX   # the dike's s, plus sigma, is its s along the crossing
    d["s_cam"] = d["mid"] - d["shift"] * PX                # prototype A: the dike's own camera
    out["jog_km"] = float(np.linalg.norm((c["P0"] - c["pad"] * c["U"]) - (d["P0"] + d["L"] * d["U"]))) / 1000
    return out


def az_of(v):
    return math.degrees(math.atan2(v[1], v[0]))


def ease(u):
    u = min(1.0, max(0.0, u)); return 0.5 - 0.5 * math.cos(math.pi * u)


def ramp(t, t0, t1):
    return ease((t - t0) / (t1 - t0)) if t1 > t0 else float(t >= t0)


START = dict(az=az_of((1.0, -0.62)), el=math.degrees(math.atan2(0.95, math.hypot(1.0, 0.62))), w=30000.0,
             L=(-300.0, 5200.0, 150.0))          # the S1 block's opening view (xfilm.py), its target lowered for x3


def end_cam(line, which):
    """The block camera's last pose: looking square at a cut (the crossing's for B and A's right half, the dike's
    for A's left half), framed so the layout's formulas hold."""
    lay = layout(line); p = lay[which]
    Lp = p["P0"] + p["s_cam"] * p["U"]
    return dict(az=az_of(p["N"]), el=0.0, w=PX * W, L=(float(Lp[0]), float(Lp[1]), lay["zc_layout"]))


def mix_cam(a, b, u):
    """Between two poses: heading and elevation linear, width on a log scale, the target linear (all eased by u)."""
    return dict(az=a["az"] + (b["az"] - a["az"]) * u, el=a["el"] + (b["el"] - a["el"]) * u,
                w=math.exp(math.log(a["w"]) + (math.log(b["w"]) - math.log(a["w"])) * u),
                L=tuple(a["L"][i] + (b["L"][i] - a["L"][i]) * u for i in range(3)))


# ---- the block's timelines (seconds). Both: hold the whole block, trace the cut, the rest of the block drops away and
# fades, leaving the two slices the section is cut through; then B swings the dike's slice beside the crossing's and
# brings one camera square to them; A keeps both slices where they are and gives each its own camera, the frame split
# at the section's break. Then the slices' tops fade, leaving only the cut faces: the section's first frame.
T = dict(hold=2.2, c1=(2.2, 3.2), jog=(3.2, 3.9), c2=(3.9, 5.2), faces=5.3, drop=(5.4, 7.4), swing=(7.0, 10.6),
         jog_out=(6.8, 7.8), cam=(6.4, 12.4), ghost_out=(9.4, 10.8), trace_out=(10.4, 11.6), tops_out=(10.8, 12.0),
         end=13.0)
TA = dict(T, cam=(7.2, 13.2), ghost_out=(10.2, 11.6), tops_out=(11.6, 12.8), trace_out=(11.2, 12.4), end=13.8)
GHOST = 0.28


def block_state(proto, line, t):
    tl = TA if proto == "A" else T
    # the rest drops a little and fades to a ghost (the region kept as context while the slices move), then goes
    s = dict(t=t, rest_a=(1 - (1 - GHOST) * ramp(t, *tl["drop"])) * (1 - ramp(t, *tl["ghost_out"])),
             rest_dz=-200.0 * ramp(t, *tl["drop"]),
             faces_a=float(t >= tl["faces"]), tops_a=1 - ramp(t, *tl["tops_out"]),
             c1=ramp(t, *tl["c1"]), jog=ramp(t, *tl["jog"]), c2=ramp(t, *tl["c2"]),
             trace_a=1 - ramp(t, *tl["trace_out"]), jog_a=1 - ramp(t, *tl["jog_out"]),
             s1_u=ramp(t, *tl["swing"]) if proto == "B" else 0.0)
    u = ramp(t, *tl["cam"])
    if proto == "B":
        s["cams"] = [dict(mix_cam(START, end_cam(line, line), u), show=["S1", "S2"])]
    elif u <= 0:
        s["cams"] = [dict(START, show=["S1", "S2"])]
    else:
        s["cams"] = [dict(mix_cam(START, end_cam(line, "dike"), u), show=["S1"]),
                     dict(mix_cam(START, end_cam(line, line), u), show=["S2"])]
    return s
