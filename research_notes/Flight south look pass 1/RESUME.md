# What is running (started 7 November 2026, 02:03 EST)

The full render of the new variant `south_look1` (the flight south, look pass 1), detached so it runs on its own:

```sh
cd /Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
nohup caffeinate -i .venv/bin/evidence satellite crossing3d --pass animatic --variant south_look1 \
  > "research_notes/Flight south look pass 1/render.log" 2>&1 &
```

- PIDs: `render.pid` holds the one `$!` gave; the process tree is `caffeinate -i ...` → `.venv/bin/python
  .venv/bin/evidence ...` → `blender -b --factory-startup -P build.py ...`. Find them with
  `pgrep -fl "south_look1|build.py"`. `caffeinate` keeps the Mac awake until the command ends.
- Frames land in `libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/south_look1/f_0001.png`
  ... `f_4577.png` as they are rendered (Blender's stdout is discarded by the pipeline, so count the PNGs to follow it):
  `ls .../animatic/south_look1/f_*.png | wc -l`.
- Measured on the final settings: about 5.3 s a frame at 960x540, EEVEE 64 samples, motion blur, full-resolution
  screen-space reflections (4,577 frames: about 6.7 h of Blender, plus 2.5 min to build the scene). Blender started
  writing frames at 02:06; the first 90 (over the north bank) took 4.2 s each. Expected to finish Blender between
  about 07:30 and 08:50 EST, the whole command (grade, overlay, Hum, mp4) about 30 min later.

## After Blender, the same command goes on by itself

1. `_grade`: the raw frames are copied to `animatic/south_look1/raw/` and the grade (saturation, tint, vignette, film
   grain; `look.grade`) laid on `f_*.png`. To regrade without rendering, change `look.grade` in the config and run the
   render command with `--resume`: with every frame on disk Blender only rebuilds the scene (about 2.5 min) and skips
   all frames, then the grade (always from `raw/`, so safe to repeat), captions, Hum and mp4 are made again. (Untested
   end to end: the parts were tested on their own.)
2. `_overlay`: the date, island mode and the two lines' names; `_hum`: `ZNPP-last-two-lines-3D-south-look1.wav`;
   `_fade`: the white fades in and out.
3. FFmpeg: `animatic/ZNPP-last-two-lines-3D-south-look1.mp4` (with the Hum), the contact sheet
   `ZNPP-last-two-lines-3D-south-look1_contact.webp`, and the scene file `ZNPP-last-two-lines-3D-south-look1.blend`
   (saved by Blender before it renders).

The old film (`ZNPP-last-two-lines-3D-south.mp4`, `south_record`) is untouched.

## Pause, resume

- Pause: `kill -STOP $(pgrep -f "build.py.*south_look1")` (Blender) and `kill -CONT ...` to go on. Pausing only
  Blender is enough; the Python parent just waits.
- If it stopped (crash, reboot): delete the newest `f_*.png` (it may be cut short), then
  `nohup caffeinate -i .venv/bin/evidence satellite crossing3d --pass animatic --variant south_look1 --resume > "research_notes/Flight south look pass 1/render.log" 2>&1 &`
  `--resume` (new, 7 November 2026) keeps the frames on disk and renders the rest (Blender's `use_overwrite` off,
  build.py `--keep-existing`); then the post steps and the mp4 as above. The grade restarts from `raw/` for frames
  already graded, so nothing is graded or captioned twice.
- To stop for good: `kill $(pgrep -f "south_look1")`.

## What is left for the morning

- Watch the mp4 against the old one; make a contact sheet of the finished film (`_contact.webp` is made for you).
- Add it to the storyboard pool as a separate source for comparison (not done here: the storyboard files were left
  alone).
- See README.md here for what changed, what wasn't done and what to look at.
