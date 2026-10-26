"""Turn a shot's real image or video into a moving, graded 1080x1920 background clip.

Stills get a documentary camera move (a slow pan, tilt, push or pull). It's rendered at 2x and
scaled down, so the motion is smooth rather than stepping a pixel at a time. Video is trimmed
from a random point and cropped to fill the frame. Everything gets the post's colour grade, so
footage from different sources looks like one film.
"""

import random
import subprocess
from pathlib import Path

W, H = 1080, 1920
FPS = 24
OVERSCAN = 1.18          # how much bigger than the frame a still is, leaving room to move
TIMEOUT_S = 300
MOVES = ("pan-left", "pan-right", "tilt-up", "tilt-down", "push", "pull")
GRADES = {
    "warm-film": "eq=contrast=1.08:saturation=0.85:gamma=0.97,colorbalance=rs=0.06:gs=0.01:bs=-0.06:rh=0.04:bh=-0.04",
    "cold-steel": "eq=contrast=1.12:saturation=0.7,colorbalance=rs=-0.05:bs=0.07:bm=0.03",
    "golden-hour": "eq=contrast=1.05:saturation=1.05:gamma=0.95,colorbalance=rs=0.09:gs=0.04:bs=-0.09",
    "bleach": "eq=contrast=1.22:saturation=0.55:brightness=-0.02",
    "noir-tint": "eq=contrast=1.18:saturation=0.22:gamma=0.92,colorbalance=rs=0.05:bs=-0.03",
    "marble": "eq=contrast=1.04:saturation=0.75:brightness=0.02,colorbalance=bs=0.03:bh=0.02",
}


def _ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], capture_output=True, text=True, timeout=TIMEOUT_S)
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg (shot) failed:\n{result.stderr[-800:]}")


def _probe_seconds(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, timeout=60).stdout.strip()
    return float(out or 0)


def _still_filter(move: str, length: float) -> str:
    w2, h2 = 2 * W, 2 * H
    bw, bh = int(w2 * OVERSCAN) // 2 * 2, int(h2 * OVERSCAN) // 2 * 2
    p = f"(t/{length:.3f})"
    ease = f"(0.5-0.5*cos(PI*{p}))"   # starts and ends gently, like a camera operator
    cover = f"scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh}"
    dx, dy = bw - w2, bh - h2
    if move in ("push", "pull"):
        z = f"(1+0.12*{ease})" if move == "push" else f"(1.12-0.12*{ease})"
        return (f"{cover},scale=w='trunc({w2}*{z}/2)*2':h=-2:eval=frame,crop={w2}:{h2},"
                f"scale={W}:{H}:flags=lanczos")
    x = {"pan-left": f"{dx}*(1-{ease})", "pan-right": f"{dx}*{ease}"}.get(move, f"{dx}/2")
    y = {"tilt-up": f"{dy}*(1-{ease})", "tilt-down": f"{dy}*{ease}"}.get(move, f"{dy}/2")
    return f"{cover},crop={w2}:{h2}:x='{x}':y='{y}',scale={W}:{H}:flags=lanczos"


def background_clip(file: Path, kind: str, length: float, move: str, grade: str, rng: random.Random,
                    out: Path) -> Path:
    grade_filter = GRADES[grade]
    if kind == "video":
        spare = max(0.0, _probe_seconds(file) - length - 0.2)
        start = rng.uniform(0, spare) if spare else 0.0
        vf = (f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"scale=w='trunc({W}*(1+0.04*t/{length:.3f})/2)*2':h=-2:eval=frame,crop={W}:{H},{grade_filter},format=yuv420p")
        _ffmpeg(["-ss", f"{start:.2f}", "-t", f"{length:.3f}", "-i", str(file), "-an", "-vf", vf,
                 "-t", f"{length:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", str(out)])
        if _probe_seconds(out) < length - 0.1:  # short source: loop it to fill the shot
            looped = out.with_name(out.stem + "-loop.mp4")
            _ffmpeg(["-stream_loop", "-1", "-i", str(out), "-t", f"{length:.3f}", "-c", "copy", str(looped)])
            looped.replace(out)
        return out
    vf = f"fps={FPS},{_still_filter(move, length)},{grade_filter},format=yuv420p"
    _ffmpeg(["-loop", "1", "-framerate", str(FPS), "-t", f"{length:.3f}", "-i", str(file), "-vf", vf,
             "-t", f"{length:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", str(out)])
    return out
