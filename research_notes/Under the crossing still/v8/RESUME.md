# v8 `drowning` (the plants dying): how to resume (8 November 2026)

One detached driver, resumable (it skips what is on disk; files are written under a temp name, then renamed):
`scripts/run_v8.sh`
1. Blender, headless (`still_v8.py frames`, the south scene opened read-only and never saved): per frame from the
   die-off's first change to its last (`$PD/plan.json`: 25..402) the plate (`static_K.exr`, 2x to frame 139, 1x
   after), the heights and distances (`pos_K.exr`, 2x) and every 5th frame and the last the wire matte
   (`matte_K.exr`). About 20 s a frame at 2x (40 s with a matte), less at 1x.
2. Three numpy workers draw the 450 frames into `$FRAMES` (`composite_v8.py`, 1-3 s a frame).

```sh
ROOT=/Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
SP=/private/tmp/claude-501/-Users-patrickrodriguez-dev-sandbox-frame-geo-evidence-pipeline/1a0b7111-211b-446e-85aa-40a4418b76a9/scratchpad
PD=$SP/v8/render; R=$SP/v8/in/v6render; V5=$SP/v8/in/v5; ANIM=$SP/v8/in/v7anim; FRAMES=$SP/v8/frames
S="$ROOT/research_notes/Under the crossing still/v8"
B=libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south.blend
```

- Inputs (copied into `$SP/v8/in/` on 8 November so the cleaner of /private/tmp does not take them): v6's passes
  (`v6render/static2x.exr`, `pos2x.exr`), v5's render dir (`v5/`: `static.exr`, `matte_A.exr`, `matte_B.exr`, its
  anim frames 0-899 for the join check), v7's moving pass (`v7anim/anim/anim_0900..1349.exr`). If they are gone, make
  them again first (`../v7/RESUME.md`, `../v6/RESUME.md`, the README's v5 commands).
- The plants laid (`$PD/plants_laid.npz`): `blender -b --factory-startup "$B" -P "$S/scripts/still_v8.py" --
  "$ROOT/research_notes/Under the crossing still/scripts/views_v5.json" "$ROOT/research_notes/Under the crossing still/v3/plants/plants_f.npz" "$PD" prep`
  (10 s). `plan.json` is first/last from `dieoff_v8.DieOff` (see v8.json `approach.frames_with_passes`).
- Start or resume: `cd "$S/scripts" && nohup bash run_v8.sh > ../render.log 2>&1 &` (`render.pid` holds its PID).
- Progress: `ls $PD/pos_*.exr | wc -l` (379 when the passes are done: frame 0 and 25-402) and
  `ls $FRAMES/f_*.png | wc -l` (450).
- Pause: `pkill -STOP -f "still_v8.py"; pkill -STOP -f composite_v8.py`; continue with `-CONT`. Stop for good:
  `pkill -f run_v8.sh; pkill -f still_v8.py; pkill -f composite_v8.py`, then start again.
- A quick look at the dying alone (no water, 960x540, 8 samples): `still_v8.py ... <dir> preview 0:450:3`.

## After the frames (from `$ROOT`, the project's venv)

1. Sound: v7's, copied unchanged (`drowning.wav`, `alt/drowning_continuous.wav`; the same 15 s and lens crossing).
2. Video: `.venv/bin/python -I "$S/scripts/composite_v8.py" video "$FRAMES" "$S/drowning.wav" "$S/drowning.mp4"`
   and `... video "$FRAMES" "$S/alt/drowning_continuous.wav" "$S/alt/drowning_continuous.mp4"`.
3. Stills and sheet: frames 0, 75, 126, 165, 240, 449 as drowning_{first,dying,lens,under_dying,under_clearing,last}.png;
   `composite_v8.py sheet "$FRAMES" "$S/contact_sheet.png" 4 1.0`.
4. Join: `.venv/bin/python -I "$S/scripts/check_join_v8.py" $SP/v8/in/v5 "$FRAMES" "$S" $SP/v7/frames`.
5. `.venv/bin/python -I "$S/scripts/v8_json.py" "$S/v8.json" "$PD"`.
6. Not added to the storyboard (the main session does that).

## Status

- DONE 8 November 2026: passes (frames 25-402, 2 h 13 min), 450 frames, drowning.mp4 and the alt/ pair, stills,
  contact sheet, join checks, v8.json. Nothing left to run. Not added to the storyboard.
