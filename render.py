"""Render a post's carousel to 1080x1350 JPEGs (and MP4s for animated slides) with headless Chrome.
The reel is rendered separately by render_reel.py.

  python3 render.py posts/2026-10-20-amor-fati.json
  python3 render.py posts/2026-10-20-amor-fati.json --html-only
"""

import argparse
import json
import os
import shutil
import re
import subprocess
import sys
from pathlib import Path

from slides.compose import render_slide
from slides.motion import FPS, LOOP_S
from slides.theme import DEFAULT_THEME, styled_brand
from validate import validate_carousel

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
WIDTH, HEIGHT = 1080, 1350
FONT_WAIT_MS = 4000
CHROME_TIMEOUT_S = 60
JPEG_QUALITY = 92
FRAMES_PER_SHOT = 12
PAGE_TIMEOUT_MS = 20000
# A persistent profile lets Chrome cache Google Fonts, so each page load stops re-fetching them.
CHROME_PROFILE = ROOT / ".chrome-cache"
VIDEO_LOOPS = 2
CHROME_CANDIDATES = (
    os.environ.get("CHROME_PATH", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
)


def chrome_flags(height: int = HEIGHT) -> list[str]:
    return ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
            f"--user-data-dir={CHROME_PROFILE}", "--no-first-run", f"--timeout={PAGE_TIMEOUT_MS}",
            f"--window-size={WIDTH},{height}", f"--virtual-time-budget={FONT_WAIT_MS}"]


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    raise SystemExit("Chrome not found. Install it or set CHROME_PATH.")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise SystemExit(f"Could not read {path}: {err}") from err


def slide_numbers(slides: list[dict]) -> list[int]:
    """Running number for content/step slides, 0 for everything else."""
    numbers, count = [], 0
    for slide in slides:
        count += slide["kind"] in ("step", "content")
        numbers.append(count if slide["kind"] in ("step", "content") else 0)
    return numbers


def prepare_html_dir(post: dict, brand: dict, html_dir: Path) -> None:
    html_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / brand["logo"], html_dir / Path(brand["logo"]).name)
    for slide in post["slides"]:
        visual = slide.get("visual") or {}
        if visual.get("type") == "image":
            target = html_dir / visual["src"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / visual["src"], target)


def write_html(post: dict, brand: dict, html_dir: Path) -> list[Path]:
    prepare_html_dir(post, brand, html_dir)
    slides, numbers = post["slides"], slide_numbers(post["slides"])
    theme, seed = post.get("theme", DEFAULT_THEME), int(post.get("seed", 0))
    pages = []
    for position, (slide, number) in enumerate(zip(slides, numbers), start=1):
        page = html_dir / f"{position:02d}.html"
        page.write_text(render_slide(slide, brand, position, len(slides), number, theme, seed, probe=True),
                        encoding="utf-8")
        pages.append(page)
    return pages


def overflow(chrome: str, page: Path) -> str:
    """Ask the page's probe which elements spill outside the safe area. Empty means clean."""
    cmd = [chrome, *chrome_flags(), "--dump-dom", page.as_uri()]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=CHROME_TIMEOUT_S)
    match = re.search(r'<html[^>]*data-overflow="([^"]*)"', result.stdout)
    return match.group(1) if match else ""


def render_video(chrome: str, post: dict, brand: dict, position: int, number: int, post_dir: Path) -> Path:
    """Animated slide -> looping MP4 (Instagram carousels take video, not GIF)."""
    work = post_dir / "frames" / f"{position:02d}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    slides = post["slides"]
    times = [k / FPS for k in range(int(LOOP_S * FPS))]
    for chunk_index in range(0, len(times), FRAMES_PER_SHOT):
        chunk = times[chunk_index:chunk_index + FRAMES_PER_SHOT]
        page = post_dir / "html" / f"{position:02d}-frames-{chunk_index:03d}.html"
        page.write_text(render_slide(slides[position - 1], brand, position, len(slides), number,
                                     post.get("theme", DEFAULT_THEME), int(post.get("seed", 0)), times=chunk),
                        encoding="utf-8")
        tall = work / f"chunk-{chunk_index:03d}.png"
        screenshot(chrome, page, tall, height=HEIGHT * len(chunk))
        run_ffmpeg(["-i", str(tall), "-vf", f"untile=1x{len(chunk)}", str(work / f"f{chunk_index:03d}-%02d.png")])
        tall.unlink()
    video = post_dir / f"{position:02d}.mp4"
    run_ffmpeg(["-framerate", str(FPS), "-pattern_type", "glob", "-i", str(work / "f*.png"),
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                "-vf", f"loop=loop={VIDEO_LOOPS - 1}:size={len(times)},fps=30,format=yuv420p",
                "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-c:a", "aac", "-b:a", "64k",
                "-shortest", "-movflags", "+faststart", str(video)])
    shutil.rmtree(work)
    return video


def run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], capture_output=True, text=True,
                            timeout=CHROME_TIMEOUT_S * 3)
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg failed:\n{result.stderr[-800:]}")


def screenshot(chrome: str, page: Path, png: Path, height: int = HEIGHT) -> None:
    cmd = [chrome, *chrome_flags(height), f"--screenshot={png}", page.as_uri()]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=CHROME_TIMEOUT_S)
    if result.returncode != 0 or not png.exists():
        raise SystemExit(f"Chrome failed on {page.name}:\n{result.stderr[-800:]}")


def to_jpeg(png: Path) -> Path:
    """The Instagram publishing API only accepts JPEG, so convert and drop the PNG."""
    jpg = png.with_suffix(".jpg")
    if shutil.which("sips"):
        cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(JPEG_QUALITY), str(png), "--out", str(jpg)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=CHROME_TIMEOUT_S)
        if result.returncode != 0:
            raise SystemExit(f"JPEG conversion failed on {png.name}:\n{result.stderr[-800:]}")
    else:
        try:
            from PIL import Image
        except ImportError as err:
            raise SystemExit("Need sips (macOS) or Pillow (pip install pillow) to write JPEGs.") from err
        with Image.open(png) as image:
            image.convert("RGB").save(jpg, "JPEG", quality=JPEG_QUALITY)
    png.unlink()
    return jpg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("post", type=Path)
    parser.add_argument("--brand", type=Path, default=ROOT / "brand.json")
    parser.add_argument("--html-only", action="store_true", help="write the HTML, skip the images")
    parser.add_argument("--allow-overflow", action="store_true", help="render even if text spills off a slide")
    args = parser.parse_args()

    post = load_json(args.post)
    brand = styled_brand(load_json(args.brand), post)
    problems = validate_carousel(post)
    if problems:
        print("Post failed validation:", *problems, sep="\n  - ", file=sys.stderr)
        raise SystemExit(1)

    post_dir = OUT / post["slug"]
    pages = write_html(post, brand, post_dir / "html")
    (post_dir / "caption.txt").write_text(post["caption"], encoding="utf-8")
    (post_dir / "alt_text.txt").write_text(post["alt_text"], encoding="utf-8")

    if args.html_only:
        print(f"HTML written to {post_dir / 'html'}")
        return

    chrome = find_chrome()
    spills = {page.stem: found for page in pages if (found := overflow(chrome, page))}
    if spills and not args.allow_overflow:
        print("Text spills outside the safe area. Shorten the copy or change the visual:", file=sys.stderr)
        for stem, found in spills.items():
            print(f"  - slide {stem}: {found}", file=sys.stderr)
        raise SystemExit(1)

    numbers = slide_numbers(post["slides"])
    for position, page in enumerate(pages, start=1):
        png = post_dir / f"{page.stem}.png"
        screenshot(chrome, page, png)
        jpg = to_jpeg(png)
        video = post_dir / f"{page.stem}.mp4"
        if post["slides"][position - 1].get("animate"):
            video = render_video(chrome, post, brand, position, numbers[position - 1], post_dir)
            print(f"  {jpg.relative_to(ROOT)} + {video.name} (animated)")
        else:
            video.unlink(missing_ok=True)
            print(f"  {jpg.relative_to(ROOT)}")
    print(f"{len(pages)} slides rendered to {post_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
