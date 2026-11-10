#!/bin/bash
# v11: v10's passes and crossings as they are ($SP/v10/render), then three numpy workers draw the 450 frames
# (composite_v11.py, about 4-5 s a frame), resumable (frames on disk skipped). Usage: nohup bash run_v11.sh > ../render.log 2>&1 &
ROOT=/Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
SP=/private/tmp/claude-501/-Users-patrickrodriguez-dev-sandbox-frame-geo-evidence-pipeline/1a0b7111-211b-446e-85aa-40a4418b76a9/scratchpad
PD=$SP/v10/render; V5=$SP/v8/in/v5; P8=$SP/v8/render; ANIM=$SP/v8/in/v7anim; FRAMES=$SP/v11/frames
S="$ROOT/research_notes/Under the crossing still/v11"
cd "$ROOT"
date
pids=()
for w in 0 1 2; do
  nice -n 10 .venv/bin/python -I "$S/scripts/composite_v11.py" frames "$PD" "$V5" "$P8" "$ANIM" "$FRAMES" $((w*150)):450 &
  pids+=($!)
  sleep 1
done
for p in "${pids[@]}"; do wait $p; done
.venv/bin/python -I "$S/scripts/composite_v11.py" frames "$PD" "$V5" "$P8" "$ANIM" "$FRAMES" 0:450
date; echo "done: $(ls "$FRAMES"/f_*.png 2>/dev/null | wc -l | tr -d ' ') of 450 frames in $FRAMES"
