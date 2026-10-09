import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def synthetic_video(tmp_path_factory) -> Path:
    """18s 720p30 H.264 video with hard cuts at 6s and 12s."""
    out = tmp_path_factory.mktemp("media") / "synth.mp4"
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=6",
            "-f", "lavfi", "-i", "smptebars=size=1280x720:rate=30:duration=6",
            "-f", "lavfi", "-i", "mandelbrot=size=1280x720:rate=30",
            "-filter_complex", "[2]trim=duration=6[m];[0][1][m]concat=n=3:v=1[v]",
            "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
        ],
        check=True,
    )
    return out


@pytest.fixture(scope="session")
def panning_video(tmp_path_factory) -> Path:
    """12s 720p25 video: one still shot for 4s, then (no cut) the camera pans 2.5 frame widths across a wide view."""
    d = tmp_path_factory.mktemp("media")
    wide = d / "wide.png"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "mandelbrot=size=4480x720:start_scale=0.5", "-frames:v", "1", str(wide)], check=True)
    out = d / "pan.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "25", "-i", str(wide),
         "-vf", "crop=1280:720:x='if(lt(t,4),0,min((t-4)*400,3200))':y=0", "-t", "12",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
        check=True,
    )
    return out
