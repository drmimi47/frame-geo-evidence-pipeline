# v6 `drowning`: how to resume (6 November 2026)

The frames are drawn by `scripts/composite_v6.py` (numpy, no Blender, no network) from passes already rendered once:
`still_v6.py` (Blender, `static2x.exr`, `pos2x.exr`) in the render dir below, plus v5's own passes (the moving wires'
`anim/`, `matte_A/B.exr`, `contour.exr`). About 1-2 s a frame, 450 frames (15 s at 30 fps).

Paths:
```sh
ROOT=/Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
SP=/private/tmp/claude-501/-Users-patrickrodriguez-dev-sandbox-frame-geo-evidence-pipeline/1a0b7111-211b-446e-85aa-40a4418b76a9/scratchpad
R=$SP/v6/render          # static2x.exr, pos2x.exr (still_v6.py)
V5=$SP/proto/v5          # v5's passes (anim/anim_0450..0899.exr, matte_A/B.exr, static.exr, contour.exr)
FRAMES=$SP/v6/frames     # f_0000.png .. f_0449.png
S="$ROOT/research_notes/Under the crossing still/v6"
```

## The render (detached)

- Start or resume (skips every frame already on disk; a killed worker leaves no half frame):
  `cd "$S/scripts" && nohup bash run_v6.sh > ../render.log 2>&1 &`
  The driver writes its PID to `render.pid` and runs three `composite_v6.py frames` workers.
- Progress: `ls $FRAMES/f_*.png | wc -l` (450 when done); `tail render.log`.
- Pause: `pkill -STOP -f composite_v6.py` (the workers; `kill -STOP $(cat render.pid)` stops only the driver).
  Continue: `pkill -CONT -f composite_v6.py`. Stop for good: `pkill -f run_v6.sh; pkill -f composite_v6.py`
  (resume later with the start command).
- If `/private/tmp` was cleared (a reboot), the passes must be made again first (from `$ROOT`):
  ```sh
  B=libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south.blend
  V="research_notes/Under the crossing still"
  for m in pos static; do blender -b --factory-startup "$B" -P "$V/v6/scripts/still_v6.py" -- "$V/scripts/views_v5.json" "$V/v3/plants/plants_f.npz" "$R" $m 2; done
  # and v5's passes into $V5 (README v5 commands: matte, contour, static, "anim 0:900"; still_v5.py)
  ```

## After the frames (from `$ROOT`, the project's venv)

1. Sound (if `drowning.wav` is not there yet):
   `.venv/bin/python -I "$S/scripts/drowning_sound_v6.py" "research_notes/Speculative crossing soundscape" "$S/drowning.wav" "$S/drowning_sound.json"`
2. Video: `.venv/bin/python -I "$S/scripts/composite_v6.py" video "$FRAMES" "$S/drowning.wav" "$S/drowning.mp4"`
3. Stills: `cp $FRAMES/f_0000.png "$S/drowning_first.png"; cp $FRAMES/f_0150.png "$S/drowning_lens.png"`;
   `cp $FRAMES/f_0225.png "$S/drowning_mid.png"; cp $FRAMES/f_0449.png "$S/drowning_last.png"` (and f_0130 as
   `drowning_rising.png`).
4. `.venv/bin/python -I "$S/scripts/v6_json.py" "$R" "$S/v6.json"`
5. config/storyboard.yaml: the source `drowning` and the shot `drowning` (README v6 says what; already added if
   present). Do not build or sync the storyboard.

Status: see the end of this file.

## Status

- Passes rendered (static2x 15 s, pos2x 2 s). Test frames looked at (100, 130, 150, 158, 200, 420).
- DONE 6 November 2026: 450 frames (4.4 min), drowning.wav, drowning.mp4, stills, v6.json, storyboard.yaml source
  and shot `drowning`. Nothing left to run. (Not built or synced into the storyboard .blend.)
