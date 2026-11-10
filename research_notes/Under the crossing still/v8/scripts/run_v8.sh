#!/bin/bash
# v8: the drowning with the plants dying. Two steps, detached and resumable (each skips what is on disk; files are
# written under a temp name and renamed, so a killed run leaves no half file):
#  1. Blender, headless (the south scene opened read-only, never saved): still_v8.py renders per frame the plate, the
#     heights/distances and (every 5th frame, and the last) the wire matte, with the plants as dieoff_v8.py has them,
#     for the frames where anything changes (plan.json: first..last); before them v6's passes stand, after them the
#     last frame's. 2x for the plate until frame 140 (from above the water), 1x after (under it).
#  2. Three numpy workers draw the 450 frames (composite_v8.py: v7's water on those passes).
# Usage: nohup bash run_v8.sh > ../render.log 2>&1 &      (PID in ../render.pid)
ROOT=/Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
SP=/private/tmp/claude-501/-Users-patrickrodriguez-dev-sandbox-frame-geo-evidence-pipeline/1a0b7111-211b-446e-85aa-40a4418b76a9/scratchpad
PD=$SP/v8/render; R=$SP/v8/in/v6render; V5=$SP/v8/in/v5; ANIM=$SP/v8/in/v7anim; FRAMES=$SP/v8/frames
V="$ROOT/research_notes/Under the crossing still"
S="$V/v8"
B=libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south.blend
echo $$ > "$S/render.pid"
cd "$ROOT"
FIRST=$(python3 -c "import json;print(json.load(open('$PD/plan.json'))['first'])")
LAST=$(python3 -c "import json;print(json.load(open('$PD/plan.json'))['last'])")
date; echo "passes $FIRST..$LAST"
for try in 1 2 3; do
  nice -n 10 blender -b --factory-startup "$B" -P "$S/scripts/still_v8.py" -- "$V/scripts/views_v5.json" \
    "$V/v3/plants/plants_f.npz" "$PD" frames $FIRST:$((LAST+1)) --one-x-from 140 --matte-every 5,$LAST 2>&1 \
    | grep --line-buffered -E "FRAME|PREPARED|DONE|Error|Traceback"
  n=$(ls "$PD"/pos_*.exr | wc -l | tr -d ' ')
  [ "$n" -ge $((LAST - FIRST + 2)) ] && break
done
date; echo "passes on disk: $(ls "$PD"/pos_*.exr | wc -l | tr -d ' ')"
pids=()
for w in 0 1 2; do
  nice -n 10 .venv/bin/python -I "$S/scripts/composite_v8.py" frames "$PD" "$R" "$V5" "$ANIM" "$FRAMES" $((w*150)):450 &
  pids+=($!)
  sleep 1
done
for p in "${pids[@]}"; do wait $p; done
.venv/bin/python -I "$S/scripts/composite_v8.py" frames "$PD" "$R" "$V5" "$ANIM" "$FRAMES" 0:450
date; echo "done: $(ls "$FRAMES"/f_*.png 2>/dev/null | wc -l | tr -d ' ') of 450 frames in $FRAMES"
