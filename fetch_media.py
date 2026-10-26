"""Find and download the real image or video for every reel shot that asks for one.

  python3 fetch_media.py posts/2026-10-27-burned-boats.json            fetch what's missing
  python3 fetch_media.py posts/2026-10-27-burned-boats.json --refresh  fetch every shot again
  python3 fetch_media.py posts/2026-10-27-burned-boats.json --list 3   show candidates for shot 3

A shot asks with "media": {"type": "art" | "video", "query": "...", "source": "any|wikimedia|met",
"pick": 0}. The chosen file, its credit, licence and page are written back into the shot, and
every credit is collected in the post's "credits". Files land in out/<slug>/media/ (git-ignored:
only the finished reel is published). A contact sheet goes to out/<slug>/review/media_sheet.png.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from media.footage import MediaError, download, find

ROOT = Path(__file__).resolve().parent
SHEET_COLS = 5
TIMEOUT_S = 120
SHOT_SECONDS_GUESS = 5.0


def _thumb(path: Path, out: Path) -> Path:
    seek = ["-ss", "1"] if path.suffix == ".mp4" else []
    subprocess.run(["ffmpeg", "-y", "-v", "error", *seek, "-i", str(path), "-frames:v", "1",
                    "-vf", "scale=216:384:force_original_aspect_ratio=increase,crop=216:384", str(out)],
                   check=True, timeout=TIMEOUT_S)
    return out


def contact_sheet(files: list[Path], out: Path) -> None:
    if not files:
        return
    thumbs_dir = out.parent / "media_thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    thumbs = [_thumb(f, thumbs_dir / f"{i:02d}.png") for i, f in enumerate(files)]
    rows = (len(thumbs) + SHEET_COLS - 1) // SHEET_COLS
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "1", "-i", str(thumbs_dir / "%02d.png"),
                    "-vf", f"tile={SHEET_COLS}x{rows}:padding=6:color=white", "-frames:v", "1", str(out)],
                   check=True, timeout=TIMEOUT_S)


def fetch(post: dict, refresh: bool) -> dict:
    media_dir = ROOT / "out" / post["slug"] / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    beats, credits = [], []
    for i, beat in enumerate(post["reel"]["beats"], start=1):
        spec = beat.get("media")
        if not spec:
            beats.append(beat)
            continue
        if spec.get("file") and (ROOT / spec["file"]).exists() and not refresh:
            credits.append(spec["credit"])
            beats.append(beat)
            continue
        candidates = find(spec, SHOT_SECONDS_GUESS)
        if not candidates:
            raise SystemExit(f"shot {i}: nothing free found for {spec['query']!r}. Try a broader query.")
        item = candidates[min(spec.get("pick", 0), len(candidates) - 1)]
        path = download(item, media_dir / f"{i:02d}")
        print(f"  shot {i:02d} {item.kind:<5} {item.credit[:70]}  [{item.license}]")
        credits.append(item.credit)
        beats.append({**beat, "media": {**spec, "type": "video" if item.kind == "video" else "art",
                                        "file": str(path.relative_to(ROOT)), "credit": item.credit,
                                        "license": item.license, "page": item.page}})
    unique = list(dict.fromkeys(credits))
    return {**post, "reel": {**post["reel"], "beats": beats}, "credits": unique}


def list_candidates(post: dict, shot: int) -> None:
    spec = post["reel"]["beats"][shot - 1].get("media")
    if not spec:
        raise SystemExit(f"shot {shot} has no media spec")
    for k, item in enumerate(find(spec, SHOT_SECONDS_GUESS)):
        print(f"  pick {k}: {item.kind} {item.credit}  [{item.license}]  {item.page}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("post", type=Path)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--list", type=int, metavar="SHOT", help="print the candidates for one shot")
    args = parser.parse_args()
    post = json.loads(args.post.read_text(encoding="utf-8"))
    try:
        if args.list:
            list_candidates(post, args.list)
            return
        updated = fetch(post, args.refresh)
    except MediaError as err:
        raise SystemExit(f"Media fetch failed: {err}") from err
    args.post.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    files = [ROOT / b["media"]["file"] for b in updated["reel"]["beats"] if b.get("media", {}).get("file")]
    sheet = ROOT / "out" / post["slug"] / "review" / "media_sheet.png"
    contact_sheet(files, sheet)
    print(f"{len(files)} shots have media. Review: {sheet.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
