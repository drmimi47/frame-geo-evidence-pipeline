#!/bin/bash
# v9: the drowning with the water already back. The passes are rendered once (still_v9.py passes, about 1 min); then
# three numpy workers draw the 450 frames (composite_v9.py, about 2 s a frame), resumable (frames on disk skipped).
# Usage: nohup bash run_v9.sh > ../render.log 2>&1 &
ROOT=/Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
SP=/private/tmp/claude-501/-Users-patrickrodriguez-dev-sandbox-frame-geo-evidence-pipeline/1a0b7111-211b-446e-85aa-40a4418b76a9/scratchpad
PD=$SP/v9/render; V5=$SP/v8/in/v5; P8=$SP/v8/render; ANIM=$SP/v8/in/v7anim; FRAMES=$SP/v9/frames
V="$ROOT/research_notes/Under the crossing still"
S="$V/v9"
B=libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south.blend
cd "$ROOT"
if [ ! -f "$PD/matte.exr" ]; then
  blender -b --factory-startup "$B" -P "$S/scripts/still_v9.py" -- "$V/scripts/views_v5.json" "$V/v3/plants/plants_f.npz" \
    "$P8/plants_laid.npz" "$PD" passes 2>&1 | grep --line-buffered -E "PREPARED|DONE|Error|Traceback"
fi
[ -f "$PD/perch.json" ] || blender -b --factory-startup "$B" -P "$S/scripts/still_v9.py" -- "$V/scripts/views_v5.json" \
  "$V/v3/plants/plants_f.npz" "$P8/plants_laid.npz" "$PD" perch 109,101 2>&1 | grep -E "PERCH|Error|Traceback"
date
pids=()
for w in 0 1 2; do
  nice -n 10 .venv/bin/python -I "$S/scripts/composite_v9.py" frames "$PD" "$V5" "$P8" "$ANIM" "$FRAMES" $((w*150)):450 &
  pids+=($!)
  sleep 1
done
for p in "${pids[@]}"; do wait $p; done
.venv/bin/python -I "$S/scripts/composite_v9.py" frames "$PD" "$V5" "$P8" "$ANIM" "$FRAMES" 0:450
date; echo "done: $(ls "$FRAMES"/f_*.png 2>/dev/null | wc -l | tr -d ' ') of 450 frames in $FRAMES"
