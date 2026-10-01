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
