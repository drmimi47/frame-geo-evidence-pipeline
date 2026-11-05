"""The crossing in 3D (docs/crossing-3d-plan.txt, planned with the user 25 October 2026).

From the zoom-out's close-up on the plant the map tilts and the camera flies north between the last two lines,
Dniprovska (750 kV) and Ferosplavna-1 (330 kV), over the water to the Nikopol bank. Everything is in the zoom-out's
plane (`zoomout.Plane`: metres east and north of the plant = Blender X, Y; Z up), so the cut between them is exact.

- `export.py`: what the scenes are built from. Pass 0 (`survey`): the two lines in the window, their towers (OSM
  nodes), where they cross, the water along them before and after the dam broke, the flight path between them, and
  the FABDEM heights under it; written to `satellite/networks/<id>/scenes/crossing3d/survey.json` with a check image.

On disk: satellite/networks/<id>/scenes/crossing3d/ (survey.json, survey.webp).
"""
