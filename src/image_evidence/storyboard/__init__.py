"""The film's storyboard (decided with the user, 2 November 2026): a pool of shots (`config/storyboard.yaml`) and cuts
of them in order (`config/storyboard-cuts.yaml`), laid out as a rough animatic in Blender's Video Sequence Editor, one
.blend per cut, for the user to rearrange by hand and for the rearrangement to be read back into the cut.

`plan.py` works outside Blender (the pool, the cuts, the media, the layout, merging what was read back); `blend.py`
runs inside it (building the cut's .blend, reading one back). Nothing here is evidence: a shot points at a film,
figure or card, and its sources stay with what it points at.
"""
