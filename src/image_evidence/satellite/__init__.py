"""Satellite imagery along a corridor of power lines: "The Conductive Seam" evidence folder.

A corridor (`corridor.py`) is fixed once: a box in Ukraine, the OpenStreetMap power lines chosen in it (their own
coordinates, with provenance; never detected from pixels), and a grid of metres on which every pass is laid. Each
satellite pass (`stitch.py`: Sentinel-2 L2A or Landsat Collection 2 L2 from Microsoft Planetary Computer, any year)
is cropped, stitched and resampled onto that same grid, so one camera path serves every date. Passes are cut into
chips along the line (the images in the folder's grid), and `film.py` renders an overhead travelling shot from them.

Tiers as elsewhere: `source` is what the provider says (item ids, acquisition time, cloud cover), `derived` is computed
from the pixels (water, alignment shift), and nothing about the world is claimed beyond the products' own georeference.
No imagery is ever generated: a film frame is one pass resampled, or a dissolve between two passes (labelled as such).

On disk, in the folder's library root:
  satellite/corridors/<corridor_id>/
    georef.json                      the grid, the lines, chip stations and the camera path (fixed)
    raw/osm_power.json               the Overpass reply, verbatim, with the query and when it was fetched
    passes/<pass_id>/
      pass.json                      SatellitePass
      raw/stac_items.json            the STAC items, verbatim
      raw/requests.json              every crop request: URL, parameters, sha256 of the reply
      mosaic/visual.png              true colour on the grid (display stretch in pass.json)
      mosaic/bands.npz               reflectance x 10000 (blue, green, red, nir, swir) + valid and cloud masks
      chips/web|thumb/<chip_id>.webp
      chips/meta/<chip_id>.json      SatelliteChip
    films/<film_id>/film.mp4, film.json, poster.webp, contact.webp
"""

SEAM_SLUG = "conductive-seam"
SEAM_TITLE = "The Conductive Seam"
