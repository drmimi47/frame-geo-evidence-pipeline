# Scene Viewer reconstruction, step 2: COLMAP models of single takes -> `derived/scene/` (scene.json, a splat and
# the points for each take), each shown on its own, stood upright and sized (an assumption, said in its notes).
# Takes already in scene.json and not named here are kept as they are.
#   compose.py TRACK_JSON OUT NAME:WORK:START:END:LABEL[:key=value...] [...]
# keys: iters (splat training steps; -1 keeps the splat already trained, the default), level (ice: the frozen water
# is level, so its plane is horizontal; else the best of four estimates), eye (camera height above the ground he
# walks on, m), source (the footage, e.g. "480p"), keep (percentile of the points kept by distance, default 97),
# splats (most kept, default 1200000: more and the viewer stutters), open (the moment, s into the video, whose camera the viewer flies in to on load; else it stops at the overview),
# also (PREFIX@START@FPS: a later stretch of the same place, its frames named PREFIX0001... from START s at FPS, solved
# together with the take; START:END stay the first stretch, named f0001...), fit (a factor on the size, set by the user
# against the map), radius and reach (m: override the take's radius and reach, worked out from its points, when the
# splats reach otherwise: the viewer fades the splats' rim from the radius).
import json, math, shutil, sys, pathlib
import numpy as np, pycolmap

track_path, out = sys.argv[1], pathlib.Path(sys.argv[2])
takes = []
for a in sys.argv[3:]:
    name, work, start, end, label, *kv = a.split(":")
    takes.append((name, work, start, end, label, dict(x.split("=", 1) for x in kv)))
tr = json.load(open(track_path))
dt = np.dtype([("p", "<f4", 3), ("s", "<f4", 3), ("c", "u1", 4), ("q", "u1", 4)])


def quat(M):
    w = math.sqrt(max(1e-9, 1 + M[0, 0] + M[1, 1] + M[2, 2])) / 2
    return [(M[2, 1] - M[1, 2]) / (4 * w), (M[0, 2] - M[2, 0]) / (4 * w), (M[1, 0] - M[0, 1]) / (4 * w), w]


def plane(P, rng, tol, near=None, tries=3000):
    """The plane through most of P (RANSAC, refined by least squares), its normal within 40° of `near` if given."""
    best = (0, None, None)
    for _ in range(tries):
        a, b, c = P[rng.choice(len(P), 3, replace=False)]; n = np.cross(b - a, c - a)
        if np.linalg.norm(n) < 1e-12: continue
        n /= np.linalg.norm(n)
        if near is not None and abs(n @ near) < math.cos(math.radians(40)): continue
        k = int((abs((P - a) @ n) < tol).sum())
        if k > best[0]: best = (k, n, a)
    if best[1] is None:
        return None, 0
    I = P[abs((P - best[2]) @ best[1]) < tol]
    return np.linalg.svd(I - I.mean(axis=0))[2][2], best[0]


out.mkdir(parents=True, exist_ok=True)
# takes not named here are kept as they are (each is rebuilt on its own)
old = json.loads((out / "scene.json").read_text()).get("pieces", []) if (out / "scene.json").exists() else []
pieces = []
for name, work, start, end, label, opt in takes:
    work, start, end = pathlib.Path(work), float(start), float(end)
    iters, eye, keep_pct = int(opt.get("iters", -1)), float(opt.get("eye", 1.5)), float(opt.get("keep", 97))
    names = sorted(p.name for p in (work / "images").glob("*.jpg"))
    first = [n for n in names if n.startswith("f")]
    fps = (len(first) - 1) / (end - start)
    later = dict(zip(("prefix", "start", "fps"), opt["also"].split("@"))) if "also" in opt else None
    time_of = lambda n: round(float(later["start"]) + (int(n[1:5]) - 1) / float(later["fps"]) if later and n.startswith(later["prefix"])
                              else start + (int(n[1:5]) - 1) / fps, 2)
    rec = max((pycolmap.Reconstruction(p) for p in (work / "sparse").iterdir() if p.is_dir()), key=lambda r: r.num_reg_images())
    # a take is one continuous path: where a camera jumps far from the frame before (100x the usual step), the
    # mapper has placed it wrongly; keep the longest run between such jumps. (A stray camera hundreds of units out
    # also wrecks the splats: msplat sizes its scene to all the cameras.)
    imgs = sorted(rec.images.values(), key=lambda i: i.name)
    C0 = np.array([-(i.cam_from_world().rotation.matrix().T @ i.cam_from_world().translation) for i in imgs])
    step = np.linalg.norm(np.diff(C0, axis=0), axis=1)
    cuts = [0] + [k + 1 for k in np.where(step > 100 * np.median(step))[0]] + [len(imgs)]
    a0, a1 = max(zip(cuts, cuts[1:]), key=lambda r: r[1] - r[0])
    for i in imgs[:a0] + imgs[a1:]:
        rec.deregister_frame(i.frame_id)
    dropped = int(len(imgs) - (a1 - a0))
    imgs = imgs[a0:a1]
    Rs = np.array([i.cam_from_world().rotation.matrix() for i in imgs])
    Cs = np.array([-R.T @ i.cam_from_world().translation for R, i in zip(Rs, imgs)])
    P = np.array([p.xyz for p in rec.points3D.values()]); col = np.array([p.color for p in rec.points3D.values()])
    c0 = Cs.mean(axis=0)
    rng = np.random.default_rng(0); tol = 0.02 * float(np.median(np.linalg.norm(P - c0, axis=1)))
    image_up = np.mean([R.T @ [0, -1, 0] for R in Rs], axis=0); image_up /= np.linalg.norm(image_up)
    oriented = lambda u: (u / np.linalg.norm(u)) * (1 if image_up @ u >= 0 else -1)

    def rel_heights(u):
        """Each point's height relative to the camera nearest it across, and how far across that is."""
        hc, hp = (Cs - c0) @ u, (P - c0) @ u
        fp, fc = (P - c0) - np.outer(hp, u), (Cs - c0) - np.outer(hc, u)
        k = np.argmin(((fp[:, None, :] - fc[None, ::4, :]) ** 2).sum(-1), axis=1) * 4
        return hp - hc[k], np.linalg.norm(fp - fc[k], axis=1)

    if opt.get("level") == "ice":
        # frozen water is level: the plane through the ice (bright, colourless points) is horizontal
        bright = (col.min(axis=1) > 165) & (col.max(axis=1) - col.min(axis=1).astype(int) < 50)
        n, k = plane(P[bright], rng, tol, near=image_up)
        up = oriented(n)
        level_note = (f"Frozen water is level: up is square to the plane through the ice ({k:,} of {int(bright.sum()):,} "
                      f"bright, colourless points), {math.degrees(math.acos(min(1, abs(up @ image_up)))):.0f}° from the phone's mean image-up.")
    else:
        # of four estimates, the one under which the ground around the cameras is flattest, near and far
        def flatness(u):
            rel, dist = rel_heights(u)
            bands = np.percentile(dist, [0, 25, 50, 75, 95])
            lows = [np.percentile(rel[(dist >= lo) & (dist < hi)], 10) for lo, hi in zip(bands, bands[1:])]
            return float(np.std(lows) / max(1e-9, abs(np.mean(lows))))
        cands = {"sideways": np.linalg.svd(np.array([R.T @ [1, 0, 0] for R in Rs]))[2][2],
                 "path": np.linalg.svd(Cs - c0)[2][2], "image-up": image_up}
        gp, _ = plane(P, rng, tol, near=oriented(cands["sideways"]), tries=2000)
        if gp is not None: cands["ground plane"] = gp
        up_from, up = min(((nm, oriented(u)) for nm, u in cands.items()), key=lambda x: flatness(x[1]))
        level_note = (f"Of four estimates of up (the phone's sideways axis, the plane its path keeps to, its mean image-up, "
                      f"the dominant plane of the points), the one under which the ground around the cameras is flattest: {up_from}.")
    # the ground he walks on: right beside the cameras (the nearest tenth across), the commonest level below them
    rel, dist = rel_heights(up)
    near = rel[(dist <= np.percentile(dist, 10)) & (rel < 0)]
    hist, e = np.histogram(near, bins=40, range=(float(np.percentile(near, 2)), 0.0))
    cam_h = -float(e[np.argmax(hist)] + (e[1] - e[0]) / 2)
    fit = float(opt.get("fit", 1))
    scale = eye / cam_h * fit
    hc0 = float(np.median((Cs - c0) @ up))
    # viewer axes: y up; x, z on the ground, -z the way the camera first looks; origin on the ground under the cameras
    f0 = Rs[0].T @ [0, 0, 1]; f0 = f0 - up * (f0 @ up); f0 /= np.linalg.norm(f0)
    A = np.stack([np.cross(f0, up), up, -f0])
    origin = c0 + up * (hc0 - cam_h)
    to_view = lambda X: (scale * (A @ (np.asarray(X) - origin).T)).T
    M4 = np.eye(4); M4[:3, :3] = scale * A; M4[:3, 3] = -scale * A @ origin

    # a camera under the ground (points right above it, none below) has been placed wrongly, e.g. a stretch the
    # mapper flipped: leave it out too
    Vall, Cv = to_view(P), to_view(Cs)
    under_ground = []
    for k, c in enumerate(Cv):
        near_c = np.linalg.norm(Vall[:, [0, 2]] - c[[0, 2]], axis=1) < 1.5
        above, below = int((near_c & (Vall[:, 1] > c[1])).sum()), int((near_c & (Vall[:, 1] < c[1])).sum())
        if above > 200 and above > 4 * below:
            under_ground.append(k)
    for k in under_ground:
        rec.deregister_frame(imgs[k].frame_id)
    ok = np.setdiff1d(np.arange(len(imgs)), under_ground)
    imgs, Rs, Cs = [imgs[k] for k in ok], Rs[ok], Cs[ok]
    dropped += len(under_ground)
    cams = [{"t": time_of(i.name), "position": to_view(C).round(3).tolist(),
             "quaternion": [round(float(v), 5) for v in quat(A @ R.T @ np.diag([1, -1, -1]))]}
            for i, R, C in zip(imgs, Rs, Cs)]
    V = to_view(P)
    d = np.linalg.norm(V[:, [0, 2]], axis=1); keep = d <= np.percentile(d, keep_pct)
    V, col = V[keep], col[keep]
    arr = np.zeros(len(V), dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"), ("b", "u1")])
    arr["x"], arr["y"], arr["z"] = V.T; arr["r"], arr["g"], arr["b"] = col.T
    with open(out / f"{name}_points.ply", "wb") as f:
        f.write(f"ply\nformat binary_little_endian 1.0\nelement vertex {len(V)}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n".encode())
        f.write(arr.tobytes())
    cam = rec.cameras[imgs[0].camera_id]
    under = np.median([c["position"] for c in cams], axis=0) - [0, eye * fit, 0]
    piece = {"name": name, "label": label, "start": start, "end": end, "frames": len(names), "registered": len(imgs),
             **({"also": [round(min(c["t"] for c in cams if c["t"] > end), 2), round(max(c["t"] for c in cams), 2)]} if later else {}),
             "points": f"{name}_points.ply", "point_count": int(len(V)), "eye_height": round(eye * fit, 3),
             **({"open_t": float(opt["open"])} if "open" in opt else {}),
             "fov_deg": round(math.degrees(2 * math.atan(cam.height / 2 / cam.params[0])), 1),
             "world": [round(float(v), 6) for v in M4.T.flatten()], "cameras": cams,
             "radius_m": float(opt["radius"]) if "radius" in opt else round(float(np.percentile(d[keep], 90)), 1),
             # what the view looks at: the ground under where the cameras stood (a turn-around films all round
             # them), and how far the reconstruction reaches from there
             "centre": [round(float(v), 2) for v in under],
             "reach": float(opt["reach"]) if "reach" in opt else round(float(np.percentile(np.linalg.norm(V - under, axis=1), 85)), 2),
             "provenance": [
                 {"label": "Footage", "evidence": f"{opt.get('source', '480p')}, {len(names)} frames ({fps:.0f} a second){f', {len(names) - len(first)} of them from a later stretch of the same place (from {float(later["start"]):.1f} s), solved together' if later else ''}; "
                  f"{len(imgs)} placed{f', {dropped} left out (placed off the camera path, or under the ground)' if dropped else ''}."},
                 {"label": "Upright", "evidence": level_note},
                 {"label": "Size", "evidence": f"The phone taken to be {eye} m above the ground he walks on (the commonest level just "
                  "below the cameras): an assumption, not a measurement."
                  + (f" Then sized ×{fit:g} by the user, by eye against the street map under it." if fit != 1 else "")},
             ]}
    sp = out / f"{name}.splat"
    if iters > 0:
        import msplat
        ds = work / "ds"; shutil.rmtree(ds, ignore_errors=True); (ds / "sparse" / "0").mkdir(parents=True)
        rec.write(ds / "sparse" / "0"); (ds / "images").symlink_to((work / "images").resolve())
        cfg = msplat.TrainingConfig(); cfg.iterations = iters; cfg.keep_crs = True; cfg.bg_color = [0.0, 0.0, 0.0]
        cfg.densify_grad_thresh = float(opt.get("densify", 0.0003))
        data = msplat.load_dataset(str(ds)); assert data.num_train == len(imgs), (data.num_train, len(imgs))
        trainer = msplat.GaussianTrainer(data, cfg)
        trainer.train(lambda s: print("  ", name, trainer.iteration, trainer.splat_count, flush=True), 2000)
        trainer.export_splat(str(sp))
        # floaters: Gaussians well outside where the points are, or far larger than the rest
        a = np.fromfile(sp, dtype=dt)
        lo, hi = np.percentile(P, 1, axis=0), np.percentile(P, 99, axis=0); pad = 0.25 * (hi - lo)
        inside = np.all((a["p"] >= lo - pad) & (a["p"] <= hi + pad), axis=1)
        big = a["s"].max(axis=1); ok = inside & (big <= np.percentile(big[inside], 99.5)) & (a["c"][:, 3] > 8)
        a = a[ok]
        # the viewer sorts every splat each frame it moves: past ~1.2 million the browser stutters, so the faintest,
        # smallest go (they add least to the picture; 1.2M of the ice pools' 2.5M kept 97% of its weight)
        cap = int(opt.get("splats", 1_200_000))
        if len(a) > cap:
            w = a["c"][:, 3] / 255 * np.prod(a["s"].astype(np.float64), axis=1) ** (2 / 3)
            a = a[np.sort(np.argsort(-w)[:cap])]
        a.tofile(sp)
    if sp.exists():
        piece["splat"], piece["gaussians"] = sp.name, sp.stat().st_size // 32
    pieces.append(piece)
    print(f"{name}: {len(imgs)} of {len(names)} cams ({dropped} dropped), {len(V)} pts, {scale:.3f} m/unit, camera "
          f"{cam_h:.3f} units up, radius {piece['radius_m']} m, splats {piece.get('gaussians')}", flush=True)
    print("  ", level_note, flush=True)

named = {p["name"]: p for p in pieces}
for p in old:  # the chosen views are set by moments in the video (not coordinates), so a rebuild keeps them
    if p["name"] in named and "views" in p:
        named[p["name"]]["views"] = p["views"]
pieces = [named.pop(p["name"], p) for p in old] + list(named.values())
json.dump({
    "schema": "scene/3", "tier": "inferred", "confidence": 0.3, "video_id": tr["video_id"], "youtube_id": tr["youtube_id"],
    "pieces": pieces,
    "summary": ("Takes where the camera turns around a place, so it sees it from many sides: each rebuilt in 3D on its "
                "own. The shape comes from the footage; how it is levelled and sized is an estimate (each take's notes "
                "say how), so distances are approximate."),
    "provenance": [
        {"label": "Shape", "evidence": "Structure from motion (COLMAP 4.2, pycolmap): SIFT features, every frame matched with every other, incremental mapping, the uploader's logo masked. One continuous take each."},
        {"label": "Splats", "evidence": "Gaussian splatting trained on each take's cameras and frames (msplat, on the Mac's GPU); splats well outside where the cameras looked, or far larger than the rest (floaters), are dropped, and past 1.2 million the faintest and smallest, so the view moves smoothly. Where it shows a smooth surface the footage gave little to go on."},
    ],
    "stats": {"pieces": len(pieces), "frames": sum(p["frames"] for p in pieces), "registered": sum(p["registered"] for p in pieces),
              "gaussians": sum(p.get("gaussians", 0) for p in pieces) or None},
}, open(out / "scene.json", "w"), indent=1, ensure_ascii=False)
