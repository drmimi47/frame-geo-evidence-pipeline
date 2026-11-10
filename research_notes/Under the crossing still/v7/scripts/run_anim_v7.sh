#!/bin/bash
# v7: the moving parts (lit wires' flow, the drawn birds) continued past the 30 s shot's end, frames 900-1349 of the
# same timeline, by v5's own still_v5.py (unchanged) in its anim mode, headless, the south scene opened read-only and
# never saved. Resumable: starts at the first frame not yet on disk (a frame being written when killed is redone:
# the last file on disk is dropped first, in case it is partial).
# Usage: nohup bash run_anim_v7.sh > ../render_anim.log 2>&1 &     (PID in ../render.pid)
ROOT=/Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
SP=/private/tmp/claude-501/-Users-patrickrodriguez-dev-sandbox-frame-geo-evidence-pipeline/1a0b7111-211b-446e-85aa-40a4418b76a9/scratchpad
OUT=$SP/v7/anim_render
V="$ROOT/research_notes/Under the crossing still"
B=libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south.blend
echo $$ > "$V/v7/render.pid"
mkdir -p "$OUT/anim"
cd "$ROOT"
date
last=$(ls "$OUT"/anim/anim_*.exr 2>/dev/null | tail -1)
[ -n "$last" ] && rm -f "$last"
A=900
while [ -f "$OUT/anim/anim_$(printf %04d $A).exr" ] && [ $A -lt 1350 ]; do A=$((A+1)); done
echo "from frame $A"
if [ $A -lt 1350 ]; then
  blender -b --factory-startup "$B" -P "$V/scripts/still_v5.py" -- "$V/scripts/views_v5.json" "$V/v3/plants/plants_f.npz" "$OUT" anim $A:1350
fi
date; echo "done: $(ls "$OUT"/anim/anim_*.exr | wc -l | tr -d ' ') of 450"
