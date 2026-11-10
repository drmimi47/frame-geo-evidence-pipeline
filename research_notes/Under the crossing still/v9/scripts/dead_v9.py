"""The plants in the v9 shot `drowning` (the user, 8 November 2026: the cut from under-the-crossing straight to the
water fully back; "all the very little plants to be gone, a few of the bigger plants to remain with no leaves, just
the stems, and the trees to remain but without any leaves and only the biggest, strongest branches remaining (to
signify that they are dead but still standing)"). One still state, no physics: plain numpy, used by still_v9.py
inside Blender and by the notes outside it.

Per plant (v8's instancer attributes, still_v8.py):
  herbs (7-12)     gone (fade past 1 + the leaf width)
  reeds (5, 6)     gone, but for a few of the tallest: their bare culms (leaves and blades gone)
  shrubs (2-4)     gone, but for a few of the taller: bare stems, the finest dropped
  trees (0, 1)     all standing, bare: every leaf gone, only the thickest branches kept (stems ranked by radius,
                   thinnest dropped first, 72%, 85% for the trees within 15 m; trunks rising from the ground always kept)
  all kept ones    the dead colour (grey-brown), upright as they grew: no tilt, slump or sinking
All of it is drawn: which plants stand is a random pick among the taller ones, not a survey of what would survive.
"""
import numpy as np

HERBS = (7, 8, 9, 10, 11, 12)
REEDS = (5, 6)
SHRUBS = (2, 3, 4)
TREES = (0, 1)
GONE = 1.12                     # past 1 + still_v8.LEAF_W: every element gone
TWIG_TREE = 0.72                # the share of a tree's stems (by radius rank) dropped: the thickest ~30% stay
TWIG_NEAR = (15.0, 0.85)        # trees nearer than this (m) drop more: their models (the finest level of detail) have
                                # many more fine stems, and 0.72 left them twiggy; the farther ones at 0.85 were bare poles
TWIG_SHRUB = 0.45
KEEP_SHRUB = (0.5, 0.25)         # shrubs at or above this height quantile of their kind, and this share of them
KEEP_REED = (0.7, 0.08)


class Dead:
    def __init__(self, npz, seed=9, twig_tree=TWIG_TREE, twig_near=TWIG_NEAR):
        self.P = np.asarray(npz["P"], float)
        self.fam = np.asarray(npz["fam"], int)
        self.h = np.asarray(npz["h"], float)
        n = len(self.P)
        rng = np.random.default_rng(seed)
        u = rng.uniform(0, 1, n)
        self.kind = np.full(n, "herb", object)
        self.keep = np.zeros(n, bool)
        self.twig = np.zeros(n)
        tree = np.isin(self.fam, TREES)
        self.kind[tree] = "tree"
        self.keep[tree] = True
        eye = np.asarray(npz["eye"], float)
        near = np.hypot(self.P[:, 0] - eye[0], self.P[:, 1] - eye[1]) < twig_near[0]
        self.twig[tree] = np.where(near[tree], twig_near[1], twig_tree)
        for fams, (q, share), name, tw in ((SHRUBS, KEEP_SHRUB, "shrub", TWIG_SHRUB), (REEDS, KEEP_REED, "reed", 0.0)):
            m = np.isin(self.fam, fams)
            self.kind[m] = name
            tall = m & (self.h >= np.quantile(self.h[m], q))
            k = tall & (u < share)
            self.keep[k] = True
            self.twig[k] = tw

    def state(self):
        n = len(self.P)
        s = self.P[:, 4]
        return dict(co=self.P[:, :3].copy(), rx=np.zeros(n), ry=np.zeros(n), rz=self.P[:, 3].copy(),
                    sx=s, sy=s, sz=s, dead=np.ones(n), leaf=np.full(n, GONE), twig=self.twig,
                    fade=np.where(self.keep, 0.0, GONE))

    def summary(self):
        out = {}
        for k in ("tree", "shrub", "reed", "herb"):
            m = self.kind == k
            out[k] = {"plants": int(m.sum()), "standing": int((m & self.keep).sum())}
        return out
