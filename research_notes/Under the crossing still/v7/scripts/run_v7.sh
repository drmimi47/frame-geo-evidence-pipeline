#!/bin/bash
# v7: the drowning's frames: 3 workers drawing composite_v7.py frames into $FRAMES, each skipping frames already on disk
# (whole files only: written to a temp name, then renamed), so a killed run resumes where it stopped.
# Usage (from anywhere): nohup bash run_v7.sh > ../render.log 2>&1 &   (writes its PID to ../render.pid)
ROOT=/Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
SP=/private/tmp/claude-501/-Users-patrickrodriguez-dev-sandbox-frame-geo-evidence-pipeline/1a0b7111-211b-446e-85aa-40a4418b76a9/scratchpad
R=$SP/v6/render; V5=$SP/proto/v5; ANIM=$SP/v7/anim_render; FRAMES=$SP/v7/frames
S="$ROOT/research_notes/Under the crossing still/v7"
echo $$ > "$S/render.pid"
cd "$ROOT"
# the moving parts must be on disk first (run_anim_v7.sh): wait for all 450 and for that render to end
until [ "$(ls "$ANIM"/anim/anim_*.exr 2>/dev/null | wc -l | tr -d ' ')" = "450" ] && ! pgrep -f "still_v5.py.*anim_render" >/dev/null; do sleep 10; done
date; echo "start"
pids=()
for w in 0 1 2; do
  # worker w starts at its own third so they rarely meet; each still checks every frame on disk first
  .venv/bin/python -I "$S/scripts/composite_v7.py" frames "$R" "$V5" "$ANIM" "$FRAMES" $((w*150)):450 &
  pids+=($!)
  sleep 1
done
for p in "${pids[@]}"; do wait $p; done
# a final pass picks up anything a worker left (e.g. after a kill)
.venv/bin/python -I "$S/scripts/composite_v7.py" frames "$R" "$V5" "$ANIM" "$FRAMES" 0:450
n=$(ls "$FRAMES"/f_*.png 2>/dev/null | wc -l | tr -d ' ')
date; echo "done: $n of 450 frames in $FRAMES"
