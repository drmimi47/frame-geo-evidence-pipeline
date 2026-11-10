# v7 `drowning`: how to resume (6 November 2026)

Two detached steps, each resumable (they skip what is on disk):
1. `scripts/run_anim_v7.sh`: Blender, headless (v5's own `still_v5.py` anim mode, the south scene opened read-only):
   the moving parts continued past the 30 s shot, frames 900-1349, into `$ANIM/anim/`. About 1.3 s a frame.
2. `scripts/run_v7.sh`: waits for step 1 to finish, then three numpy workers draw the 450 frames into `$FRAMES`
   (`composite_v7.py`, about 1-2 s a frame). No network is needed for either.

```sh
ROOT=/Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
SP=/private/tmp/claude-501/-Users-patrickrodriguez-dev-sandbox-frame-geo-evidence-pipeline/1a0b7111-211b-446e-85aa-40a4418b76a9/scratchpad
R=$SP/v6/render; V5=$SP/proto/v5; ANIM=$SP/v7/anim_render; FRAMES=$SP/v7/frames
S="$ROOT/research_notes/Under the crossing still/v7"
```

- Start or resume: `cd "$S/scripts" && nohup bash run_anim_v7.sh > ../render_anim.log 2>&1 &` then
  `nohup bash run_v7.sh > ../render.log 2>&1 &` (the second waits for the first). `render.pid` holds the PID of the
  driver started last.
- Progress: `ls $ANIM/anim/*.exr | wc -l` and `ls $FRAMES/f_*.png | wc -l` (450 each when done).
- Pause: `pkill -STOP -f "still_v5.py.*anim_render"; pkill -STOP -f composite_v7.py`.
  Continue: the same with `-CONT`. Stop for good: `pkill -f run_anim_v7.sh; pkill -f run_v7.sh;
  pkill -f "still_v5.py.*anim_render"; pkill -f composite_v7.py` (then resume with the start commands).
- If `/private/tmp` was cleared, make v6's passes again first (`../v6/RESUME.md`) and v5's matte and static passes
  (README v5 commands).

## After the frames (from `$ROOT`, the project's venv)

1. Sound (already made if `drowning.wav` exists):
   `.venv/bin/python -I "$S/scripts/drowning_sound_v7.py" "research_notes/Speculative crossing soundscape" "research_notes/Line sound proxies/raw/xc/XC1016141/XC1016141.mp3" "$S" $SP/v7/sound`
2. Video: `.venv/bin/python -I "$S/scripts/composite_v7.py" video "$FRAMES" "$S/drowning.wav" "$S/drowning.mp4"`,
   and the continuous pair: `... video "$FRAMES" "$S/alt/drowning_continuous.wav" "$S/alt/drowning_continuous.mp4"`;
   `ffmpeg -i "$ROOT/research_notes/Under the crossing still/v5/under_the_crossing_f_day.mp4" -i "$S/alt/under_the_crossing_continuous.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest "$S/alt/under_the_crossing_f_day_continuous.mp4"`
3. Stills: frames 0, 60, 110, 122, 180, 449 copied as drowning_{first,rising,near_the_lens,lens,under,last}.png; then `check_join_v7.py $V5 $FRAMES "$S"` (join_check.json, join_test.mp4, join_contact.png).
4. `.venv/bin/python -I "$S/scripts/v7_json.py" "$S/v7.json"`
5. config/storyboard.yaml: the source `drowning` points to v7 (done if it does). Do not build or sync.

## Status

- Sound made. Test frames looked at (0, 110, 140, 180); frame 0 checked against under-the-crossing's last frame.
- DONE 6 November 2026: moving pass (900-1349), 450 frames (the 333 from the lens redrawn once, the water above
  the eye a little clearer), drowning.mp4 and the alt/ pair, stills, join checks, v7.json, storyboard.yaml source.
  Nothing left to run.
