# What is running (started 7 November 2026, 14:38 EST)

The full render of the variant `south_look3` (the flight south, look pass 3: selected dates, straight lift, the river,
its edge, the plants), detached:

```sh
cd /Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
nohup caffeinate -i .venv/bin/evidence satellite crossing3d --pass animatic --variant south_look3 \
  > "research_notes/Flight south look pass 3/render.log" 2>&1 &
```

- PIDs: `render.pid` holds the one `$!` gave (`caffeinate`); the tree is `caffeinate -i ...` → `.venv/bin/python
  .venv/bin/evidence ...` → `blender -b --factory-startup -P build.py ...`. Find them with
  `pgrep -fl "south_look3|build.py"`.
- Frames land in `libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/south_look3/f_0001.png`
  ... `f_2790.png` (Blender's stdout is discarded, so count the PNGs: `ls .../animatic/south_look3/f_*.png | wc -l`).
- Expected: see Timing at the end of this file.
- Afterwards the same command grades (raw frames kept in `animatic/south_look3/raw/`), adds the date and names, the
  Hum (`ZNPP-last-two-lines-3D-south-look3.wav`) and the fades, and writes
  `animatic/ZNPP-last-two-lines-3D-south-look3.mp4`, `_contact.webp` and the scene `ZNPP-last-two-lines-3D-south-look3.blend`
  (saved before rendering).

The approved films (`ZNPP-last-two-lines-3D-south.mp4`, `-south-look1.mp4`, `-south-look2.mp4`) are untouched.

## Pause, resume

- Pause: `kill -STOP $(pgrep -f "build.py.*south_look3")` and `kill -CONT ...` to go on.
- If it stopped (crash, reboot): delete the newest `f_*.png` (it may be cut short), then
  `nohup caffeinate -i .venv/bin/evidence satellite crossing3d --pass animatic --variant south_look3 --resume > "research_notes/Flight south look pass 3/render.log" 2>&1 &`
  (keeps the frames on disk, renders the rest, then the post steps).
- The plants are look2's (`vegetation.track_from: south_look2`, the same cache); the water's edge fields and colour
  variation are cached in `scenes/crossing3d/look/` (`water_edge_<day>_v1.png`, `<pass>_watervar_v1.png` + .json), so
  a resume re-places nothing.
- To stop for good: `kill $(pgrep -f "south_look3")`.

## Test a stretch or stills again

- Stills (no post steps): build the scene json and run Blender with `--frames`, as in the look-dev (the scratch
  scripts aren't kept); or `--seconds A:B` on the command above for a short mp4 of that stretch.
- The comparison sheets: `scripts/sheet.py`; the Hum alone with its switches and partials: `.venv/bin/python
  "research_notes/Flight south look pass 3/scripts/hum_check.py" <out dir>`.

## Timing (measured)

Export and scene build about 2.5 min (first frame 14:40:39). Frames 1-40: 7.5 s a frame (14:40:39 to 14:45:31; the
look-dev stills averaged about 6 s across the film). 2790 frames: Blender done about 19:20-20:30 EST, then about
10 min for the grade, captions, Hum and mp4.
