"""Builds a cut's storyboard in Blender's Video Sequence Editor, or reads one back. Runs inside Blender:

    blender -b --factory-startup -P blend.py -- build <spec.json>
    blender -b <cut.blend> -P blend.py -- read <out.json>

Each shot is one meta strip named by its id (dragging it moves its picture, sound and label together; its handles trim
it), coloured by status. Inside: the clip (its sound beside it) or the figure, else a card: an intertitle when the
shot has the film's own words (`card`, centred in white on black as the film's type, its chapter number above, what
it still needs faint at the foot), or a placeholder (the shot's title, what it tells, what it needs); a small label
of the id and status, top right. The cut runs from frame 1 to the END marker; the
shots not in it are parked after it, from the PARKED marker. Only bpy (Blender's own Python), so no package imports.
"""

import json
import os
import sys

import bpy

TAGS = {"good": "COLOR_04", "draft": "COLOR_03", "still": "COLOR_05", "missing": "COLOR_01", "idea": "COLOR_06",
        "new": "COLOR_07"}
CARD_RGB = {"missing": (0.09, 0.05, 0.05), "idea": (0.05, 0.06, 0.09), "new": (0.08, 0.08, 0.08)}
INK = (1.0, 1.0, 1.0, 1.0)
FAINT = (1.0, 1.0, 1.0, 0.7)
DIM = (1.0, 1.0, 1.0, 0.38)
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"   # the film's type; Blender's own where it isn't installed
_font = []


def _face():
    if not _font:
        _font.append(bpy.data.fonts.load(FONT, check_existing=True) if os.path.exists(FONT) else None)
    return _font[0]


def _text(strips, name, text, channel, start, frames, size, y, wrap=0.8, rgba=INK, box=False, right=False,
          centre=False, anchor_y="TOP"):
    t = strips.new_effect(name=name, type="TEXT", channel=channel, frame_start=start, length=frames)
    t.text, t.font_size, t.color, t.wrap_width = text, size, rgba, wrap
    t.location = (0.97 if right else 0.5 if centre else 0.5 - wrap / 2, y)
    t.anchor_x, t.anchor_y = ("RIGHT" if right else "CENTER" if centre else "LEFT"), anchor_y
    t.alignment_x = t.anchor_x
    if _face():
        t.font = _face()
    if box:
        t.use_box, t.box_color, t.box_margin = True, (0, 0, 0, 0.5), 0.01
    return t


def _shot(ed, sh):
    a, n = sh["start"], sh["frames"]
    b = a + n
    m = ed.strips.new_meta(sh["id"], 1, a)
    if sh["kind"] == "movie":
        at = a - sh["in"]   # where the clip's first frame would sit; the handles cut it to the shot
        clip = m.strips.new_movie(f"{sh['id']} picture", sh["path"], 1, at, fit_method="FIT")
        clip.right_handle, clip.left_handle = b, a
        if sh.get("audio"):
            snd = m.strips.new_sound(f"{sh['id']} sound", sh["path"], 2, at)
            snd.right_handle, snd.left_handle = b, a
    elif sh["kind"] == "image":
        im = m.strips.new_image(f"{sh['id']} picture", sh["path"], 1, a, fit_method="FIT")
        im.right_handle = b
    elif sh.get("card"):   # an intertitle: the film's own words, as they would read
        c = m.strips.new_effect(name=f"{sh['id']} card", type="COLOR", channel=1, frame_start=a, length=n)
        c.color = (0.0, 0.0, 0.0)
        if sh.get("chapter"):
            _text(m.strips, f"{sh['id']} chapter", str(sh["chapter"]), 2, a, n, 26, 0.62, rgba=FAINT, centre=True,
                  anchor_y="BOTTOM")
        _text(m.strips, f"{sh['id']} title", sh["card"].strip(), 3, a, n, 42, 0.5, 0.86, centre=True,
              anchor_y="CENTER")
        if sh.get("needs"):
            _text(m.strips, f"{sh['id']} body", f"STILL TO DO: {sh['needs']}", 4, a, n, 20, 0.08, 0.8, rgba=DIM,
                  centre=True, anchor_y="BOTTOM")
    else:
        c = m.strips.new_effect(name=f"{sh['id']} card", type="COLOR", channel=1, frame_start=a, length=n)
        c.color = CARD_RGB.get(sh["status"], CARD_RGB["missing"])   # tinted: a picture still to make, not words
        _text(m.strips, f"{sh['id']} kind", f"TO MAKE  ·  {sh['title'].upper()}", 2, a, n, 26, 0.64, rgba=FAINT,
              centre=True, anchor_y="BOTTOM")
        if sh.get("tells"):
            _text(m.strips, f"{sh['id']} body", sh["tells"], 3, a, n, 34, 0.5, 0.66, centre=True, anchor_y="CENTER")
        if sh.get("needs"):
            _text(m.strips, f"{sh['id']} needs", f"NEEDS: {sh['needs']}", 4, a, n, 20, 0.08, 0.8, rgba=DIM,
                  centre=True, anchor_y="BOTTOM")
    if sh.get("label", True):
        _text(m.strips, f"{sh['id']} label", f"{sh['id']}  ·  {sh['status'].upper()}", 6, a, n, 22, 0.97, wrap=1.0,
              rgba=FAINT, box=True, right=True)   # top right: the films keep their own date and legend top left
    m.right_handle, m.left_handle = b, a
    m.color_tag = TAGS.get(sh["status"], "NONE")
    return m


def _video_editing(scene):
    """The Video Editing workspace, taken from Blender's own template, showing the storyboard: in Blender 5 the tab shows
    its workspace's own scene (`sequencer_scene`), and one added by hand shows nothing."""
    if "Video Editing" not in bpy.data.workspaces:
        t = os.path.join(bpy.utils.system_resource("SCRIPTS"), "startup", "bl_app_templates_system", "Video_Editing",
                         "startup.blend")
        if os.path.exists(t):
            with bpy.data.libraries.load(t) as (src, dst):
                dst.workspaces = [w for w in src.workspaces if w == "Video Editing"]
    for ws in bpy.data.workspaces:
        ws.sequencer_scene = scene


def build(spec_path):
    sp = json.loads(open(spec_path).read())
    s = bpy.context.scene
    s.name = sp["cut"]
    s.render.resolution_x, s.render.resolution_y = sp["size"]
    s.render.resolution_percentage = 100
    s.render.fps = sp["fps"]
    ed = s.sequence_editor_create()
    for sh in sp["shots"] + sp["parked"]:
        _shot(ed, sh)
    s.timeline_markers.new("END", frame=sp["end"])
    if sp["parked"]:
        s.timeline_markers.new("PARKED", frame=sp["parked"][0]["start"])
    s.frame_start, s.frame_end = 1, max(1, sp["end"] - 1)
    s.frame_current = 1
    _video_editing(s)
    bpy.context.preferences.filepaths.save_version = 0   # no .blend1: one file per cut, replaced each build
    bpy.ops.wm.save_as_mainfile(filepath=sp["out"])


def _path(st):
    if st.type == "MOVIE":
        return bpy.path.abspath(st.filepath)
    if st.type == "IMAGE" and len(st.elements):
        return bpy.path.abspath(st.directory + st.elements[0].filename)
    return None


def read(out_path):
    s = bpy.context.scene
    ed = s.sequence_editor
    strips = []
    for st in (ed.strips if ed else []):
        d = {"name": st.name, "type": st.type, "left": st.left_handle, "right": st.right_handle, "channel": st.channel,
             "mute": st.mute}
        if st.type == "META":
            pic = next((c for c in st.strips if c.type in ("MOVIE", "IMAGE")), None)
            if pic:
                d["picture"] = {"type": pic.type, "content_start": pic.content_start, "left": pic.left_handle,
                                "right": pic.right_handle, "path": _path(pic)}
        elif st.type == "TEXT":
            d["text"] = st.text
        else:
            d["path"] = _path(st)
            if st.type in ("MOVIE", "IMAGE"):
                d["content_start"] = st.content_start
        strips.append(d)
    out = {"file": bpy.data.filepath, "fps": s.render.fps / s.render.fps_base,
           "markers": {m.name: m.frame for m in s.timeline_markers}, "frame_end": s.frame_end, "strips": strips}
    open(out_path, "w").write(json.dumps(out, indent=1))


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    {"build": build, "read": read}[a[0]](a[1])


main()
