# A take's splats to and from the standard 3D Gaussian splatting .ply, for cleaning by hand in an editor
# (SuperSplat: delete floaters, never move, turn or scale the model: the viewer places it by the take's `world`).
#   splat_ply.py out IN.splat OUT.ply
#   splat_ply.py in IN.ply OUT.splat [CAP]   (CAP: most kept, default 1200000, the faintest and smallest dropped as in compose.py)
import sys
import numpy as np

SH0 = 0.28209479177387814
dt = np.dtype([("p", "<f4", 3), ("s", "<f4", 3), ("c", "u1", 4), ("q", "u1", 4)])
names = ["x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]


def to_ply(src, dst):
    a = np.fromfile(src, dtype=dt)
    c = a["c"].astype(np.float32) / 255
    alpha = np.clip(c[:, 3], 1e-4, 1 - 1e-4)
    q = (a["q"].astype(np.float32) - 128) / 128
    q[np.linalg.norm(q, axis=1) < 1e-6] = [1, 0, 0, 0]  # a few are stored as all zero: no rotation
    # left unnormalised, as stored (renderers normalise), so a file that comes back unedited is the same bytes
    cols = [a["p"], (c[:, :3] - 0.5) / SH0, np.log(alpha / (1 - alpha))[:, None], np.log(np.maximum(a["s"], 1e-8)), q]
    v = np.hstack(cols).astype("<f4")
    with open(dst, "wb") as f:
        f.write(("ply\nformat binary_little_endian 1.0\n" f"element vertex {len(v)}\n"
                 + "".join(f"property float {n}\n" for n in names) + "end_header\n").encode())
        v.tofile(f)
    print(f"{len(v)} splats -> {dst}")


def from_ply(src, dst, cap=1_200_000):
    with open(src, "rb") as f:
        head = []
        while (line := f.readline().decode().strip()) != "end_header":
            head.append(line)
        assert "format binary_little_endian 1.0" in head, "not a binary little-endian .ply (export an uncompressed .ply)"
        n = next(int(h.split()[2]) for h in head if h.startswith("element vertex"))
        props = [h.split() for h in head if h.startswith("property")]
        types = {"float": "<f4", "double": "<f8", "uchar": "u1", "int": "<i4", "uint": "<u4", "short": "<i2", "ushort": "<u2"}
        v = np.fromfile(f, dtype=np.dtype([(p[2], types[p[1]]) for p in props]), count=n)
    a = np.zeros(n, dtype=dt)
    a["p"] = np.stack([v["x"], v["y"], v["z"]], 1)
    a["s"] = np.exp(np.stack([v[f"scale_{i}"] for i in range(3)], 1))
    rgb = 0.5 + SH0 * np.stack([v[f"f_dc_{i}"] for i in range(3)], 1)
    alpha = 1 / (1 + np.exp(-v["opacity"].astype(np.float64)))
    a["c"] = np.clip(np.hstack([rgb, alpha[:, None]]) * 255, 0, 255).round().astype("u1")
    q = np.stack([v[f"rot_{i}"] for i in range(4)], 1).astype(np.float64)
    q[np.linalg.norm(q, axis=1) < 1e-9] = [1, 0, 0, 0]
    q /= np.maximum(1, np.abs(q).max(1, keepdims=True))  # into the byte range, the same rotation
    a["q"] = np.clip(q * 128 + 128, 0, 255).round().astype("u1")
    if len(a) > cap:
        w = a["c"][:, 3] / 255 * np.prod(a["s"].astype(np.float64), axis=1) ** (2 / 3)
        a = a[np.sort(np.argsort(-w)[:cap])]
    a.tofile(dst)
    print(f"{n} splats in, {len(a)} -> {dst}")


if __name__ == "__main__":
    mode, src, dst, *rest = sys.argv[1:]
    to_ply(src, dst) if mode == "out" else from_ply(src, dst, *map(int, rest))
