# What is running (started 7 November 2026, 07:08 EST)

The full render of the variant `south_look2` (the flight south, look pass 2: vegetation, tower detail, finer
fittings), detached:

```sh
cd /Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline
nohup caffeinate -i .venv/bin/evidence satellite crossing3d --pass animatic --variant south_look2 \
  > "research_notes/Flight south look pass 2/render.log" 2>&1 &
```

- PIDs: `render.pid` holds the one `$!` gave (`caffeinate`); the tree is `caffeinate -i ...` → `.venv/bin/python
  .venv/bin/evidence ...` → `blender -b --factory-startup -P build.py ...`. Find them with
  `pgrep -fl "south_look2|build.py"`.
- Frames land in `libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/south_look2/f_0001.png`
  ... `f_4577.png` (Blender's stdout is discarded, so count the PNGs: `ls .../animatic/south_look2/f_*.png | wc -l`).
- Measured in the look-dev stills: about 4.0-5.5 s a frame at 960x540 (look1 averaged 3.8 s over the whole film), plus
  about 2.5 min to build the scene. Expected: Blender done about 13:00-14:30 EST, the whole command (grade, captions,
  Hum, mp4) about 10 min later.
- Afterwards the same command grades (raw frames kept in `animatic/south_look2/raw/`), adds the date and names, the
  Hum (`ZNPP-last-two-lines-3D-south-look2.wav`) and the fades, and writes
  `animatic/ZNPP-last-two-lines-3D-south-look2.mp4`, `_contact.webp` and the scene `ZNPP-last-two-lines-3D-south-look2.blend`
  (saved before rendering).

The approved films (`ZNPP-last-two-lines-3D-south.mp4`, `ZNPP-last-two-lines-3D-south-look1.mp4`) are untouched.

## Pause, resume

- Pause: `kill -STOP $(pgrep -f "build.py.*south_look2")` and `kill -CONT ...` to go on.
- If it stopped (crash, reboot): delete the newest `f_*.png` (it may be cut short), then
  `nohup caffeinate -i .venv/bin/evidence satellite crossing3d --pass animatic --variant south_look2 --resume > "research_notes/Flight south look pass 2/render.log" 2>&1 &`
  (keeps the frames on disk, renders the rest, then the post steps).
- The vegetation is cached (`scenes/crossing3d/vegetation.npz`, keyed by the seed, spacing, track and towers), so a
  resume doesn't re-place it. Changing `gain`, `lod_m`, `thin_m`, `cone_cos` or `min_scale` in the config takes effect
  on the next render without re-placing; changing `seed` or `spacing` re-places (about 1 min).
- To stop for good: `kill $(pgrep -f "south_look2")`.
