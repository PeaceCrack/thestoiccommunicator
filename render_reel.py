"""Render a post's reel: 1080x1920 animated frames + neural voiceover + procedural score + captions.

  .venv/bin/python render_reel.py posts/2026-10-20-amor-fati.json
  .venv/bin/python render_reel.py posts/2026-10-20-amor-fati.json --keep-work

Writes out/<slug>/reel.mp4 (the Instagram Reel and the YouTube Short) and reel_cover.jpg.
Each beat: entrance animation frames from headless Chrome, held under a slow push or pull,
joined to the next beat with an xfade transition. Audio: one narration clip per beat, the
score ducked under the voice, and randomized sound design: a hit on the hook, a different sound
(or none) on each cut, and a thud or tick under each punch-in zoom.
"""

import argparse
import os
import random
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from media.captions import CAPTION_FONTS, CAPTION_STYLES, build_ass, punctuate, shift
from media.music import score
from media.sfx import plan_cuts
from media.voice import Narration, duration, narrate
from render import find_chrome, load_json, overflow, run_ffmpeg, screenshot, to_jpeg
from slides.motion import T_STILL
from slides.reel_frame import HEIGHT, WIDTH, plan_beat, render_frames
from slides.theme import PALETTES, styled_brand
from validate import validate_reel

ROOT = Path(__file__).resolve().parent
FPS = 24
FRAMES_PER_SHOT = 8          # 8 x 1920 px stays under Chrome's screenshot height limit
ENTRANCE_S = 2.2             # animate this long, then hold the last frame
HOOK_T0 = 0.45               # the hook's first frame is already mid-reveal: no blank opening
LEAD_S, PAD_S, TAIL_S = 0.12, 0.30, 1.4
XFADE_S = 0.4
VOICE_IN_S = XFADE_S * 0.6   # a beat's line starts once its card is mostly in
ZOOM = 0.035
PUNCH = 0.075             # punch-in zoom on an emphasised word
PUNCH_S = 0.12           # how fast the punch lands
PUNCH_CHANCE = 0.3       # beats without an explicit emphasis word get a punch this often
PUNCH_MIN_LETTERS = 6
MAX_SECONDS = 59.0            # keep Shorts and Reels under a minute
MAX_BYTES = 19 * 1024 * 1024  # jsDelivr serves files up to 20 MB, and Instagram fetches the reel there
BITRATES_K = (2800, 2100, 1500)
# Instagram's Reels ingest rejects some valid H.264 files with a bare "ERROR" (high levels,
# 24 fps, untagged colour). These settings match its published spec and are safe for YouTube too.
OUT_FPS = 30
IG_VIDEO_ARGS = ("-r", str(OUT_FPS), "-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-level:v", "4.1",
                 "-crf", "21", "-g", str(OUT_FPS * 2), "-keyint_min", str(OUT_FPS * 2), "-sc_threshold", "0",
                 "-bf", "2", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                 "-colorspace", "bt709", "-tag:v", "avc1", "-movflags", "+faststart")
IG_AUDIO_ARGS = ("-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2")
TRANSITIONS = ("fade", "fadeblack", "smoothleft", "smoothup", "circleopen", "slideup", "wipeleft", "radial",
               "dissolve", "zoomin", "hblur", "squeezev")


@dataclass(frozen=True)
class Slot:
    start: float      # when this beat's clip starts on the timeline (its transition in begins)
    length: float     # clip length, including the transition overlap out
    voice_at: float   # when its narration starts


def timeline(narrations: list[Narration]) -> list[Slot]:
    slots, start, last = [], 0.0, len(narrations) - 1
    for i, n in enumerate(narrations):
        lead_in = LEAD_S + (VOICE_IN_S if i else 0.0)
        length = lead_in + n.duration + PAD_S + (TAIL_S if i == last else XFADE_S)
        slots.append(Slot(start, length, start + lead_in))
        start += length - XFADE_S
    return slots


def total_length(slots: list[Slot]) -> float:
    return slots[-1].start + slots[-1].length


def beat_frames(chrome: str, beat: dict, brand: dict, post: dict, index: int, slot: Slot,
                progress: float, work: Path) -> list[Path]:
    t0 = HOOK_T0 if beat["kind"] == "hook" else 0.0
    count = max(1, round(min(slot.length, ENTRANCE_S) * FPS))
    times = [t0 + k / FPS for k in range(count)]
    frames = []
    for c in range(0, count, FRAMES_PER_SHOT):
        chunk = times[c:c + FRAMES_PER_SHOT]
        page = work / f"b{index:02d}-{c:03d}.html"
        page.write_text(render_frames(beat, brand, post["theme"], int(post["seed"]), index, progress, chunk),
                        encoding="utf-8")
        tall = work / f"b{index:02d}-{c:03d}.png"
        screenshot(chrome, page, tall, height=HEIGHT * len(chunk))
        pattern = work / f"b{index:02d}-f{c:03d}-%02d.png"
        run_ffmpeg(["-i", str(tall), "-vf", f"untile=1x{len(chunk)}", "-start_number", "0", str(pattern)])
        tall.unlink()
        frames.extend(work / f"b{index:02d}-f{c:03d}-{k:02d}.png" for k in range(len(chunk)))
    return frames


def punch_time(beat: dict, narration: Narration, rng: random.Random) -> float | None:
    """Seconds into the beat's narration of the word to punch in on, or None for no punch."""
    if beat["kind"] == "cta":
        return None  # the outro holds still on the logo
    wanted = (beat.get("emphasis") or "").lower().strip(".,!?;:")
    if wanted:
        return next((w.start for w in narration.words if w.text.lower().strip(".,!?;:") == wanted), None)
    long_words = [w for w in narration.words if len(w.text) >= PUNCH_MIN_LETTERS]
    if long_words and rng.random() < PUNCH_CHANCE:
        return rng.choice(long_words).start
    return None


def beat_clip(frames: list[Path], slot: Slot, motion: str, punch_at: float | None, out: Path) -> Path:
    """punch_at: clip-local seconds where a quick zoom-in lands and holds, or None."""
    listing = out.with_suffix(".txt")
    hold = max(1 / FPS, slot.length - (len(frames) - 1) / FPS)
    lines = [f"file '{f.name}'\nduration {1 / FPS:.5f}\n" for f in frames[:-1]]
    lines.append(f"file '{frames[-1].name}'\nduration {hold:.5f}\nfile '{frames[-1].name}'\n")
    listing.write_text("".join(lines), encoding="utf-8")
    z0, dz = {"push": (0.0, ZOOM), "pull": (ZOOM, -ZOOM), "still": (0.0, 0.0)}[motion]
    punch = f"+{PUNCH}*clip((t-{punch_at:.3f})/{PUNCH_S},0,1)" if punch_at is not None else ""
    scale = f"trunc({WIDTH}*(1+{z0}+{dz}*t/{slot.length:.3f}{punch})/2)*2"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing),
                "-vf", f"fps={FPS},scale=w='{scale}':h=-2:eval=frame:flags=lanczos,crop={WIDTH}:{HEIGHT},format=yuv420p",
                "-t", f"{slot.length:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", str(out)])
    return out


def mix_audio(narrations: list[Narration], slots: list[Slot], mood: str, seed: int, punches: list[float],
              work: Path) -> Path:
    length = total_length(slots)
    bed = score(mood, seed, length, work / "score.wav")
    cues = plan_cuts([s.start for s in slots[1:]], punches, random.Random(seed + 1), work / "sfx")
    inputs, chains = [], []
    for i, (n, slot) in enumerate(zip(narrations, slots)):
        inputs += ["-i", str(n.wav)]
        ms = int(slot.voice_at * 1000)
        chains.append(f"[{i}:a]adelay={ms}|{ms}[v{i}]")
    k = len(narrations)
    voices = "".join(f"[v{i}]" for i in range(k))
    # Pad the voice to the full length: sidechaincompress stops when its key input ends.
    chains.append(f"{voices}amix=inputs={k}:normalize=0,apad=whole_dur={length:.3f},asplit[vox][key]")
    inputs += ["-i", str(bed)]
    chains.append(f"[{k}:a]volume=0.6[bed];[bed][key]sidechaincompress=threshold=0.025:ratio=9:attack=15:release=380[duck]")
    sfx = []
    for j, cue in enumerate(cues):
        inputs += ["-i", str(cue.path)]
        ms = int(cue.at * 1000)
        chains.append(f"[{k + 1 + j}:a]volume={cue.gain:.2f},adelay={ms}|{ms}[s{j}]")
        sfx.append(f"[s{j}]")
    chains.append(f"[vox][duck]{''.join(sfx)}amix=inputs={2 + len(sfx)}:normalize=0,"
                  f"atrim=0:{length:.3f},loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[mix]")
    out = work / "mix.wav"
    run_ffmpeg([*inputs, "-filter_complex", ";".join(chains), "-map", "[mix]", "-ac", "2", str(out)])
    return out


def final_cut(clips: list[Path], slots: list[Slot], transitions: list[str], audio: Path, ass: Path,
              out: Path, kbps: int) -> Path:
    inputs = [arg for c in clips for arg in ("-i", str(c))]
    chain, last = [], "[0:v]"
    for i in range(1, len(clips)):
        chain.append(f"{last}[{i}:v]xfade=transition={transitions[(i - 1) % len(transitions)]}:"
                     f"duration={XFADE_S}:offset={slots[i].start:.3f}[x{i}]")
        last = f"[x{i}]"
    chain.append(f"{last}ass={ass.name},noise=alls=5:allf=u,vignette=PI/5,format=yuv420p[v]")
    run_ffmpeg([*inputs, "-i", str(audio), "-filter_complex", ";".join(chain),
                "-map", "[v]", "-map", f"{len(clips)}:a", *IG_VIDEO_ARGS,
                "-maxrate", f"{kbps}k", "-bufsize", f"{kbps * 2}k", *IG_AUDIO_ARGS, "-shortest", str(out)])
    return out


def render_reel(post: dict, brand: dict, keep_work: bool = False) -> Path:
    reel, brief = post["reel"], post.get("reel_style", {})
    post_dir = ROOT / "out" / post["slug"]
    work = post_dir / "reel-work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    shutil.copy(ROOT / brand["logo"], work / Path(brand["logo"]).name)
    rng = random.Random(int(post["seed"]))

    print("  voice:", brand["voice"]["name"])
    narrations = [narrate(b["voice"], brand["voice"], post_dir / "voice", f"{i:02d}")
                  for i, b in enumerate(reel["beats"])]
    slots = timeline(narrations)
    length = total_length(slots)
    print(f"  length {length:.1f}s over {len(slots)} beats")
    if length > MAX_SECONDS:
        raise SystemExit(f"Reel is {length:.1f}s, max {MAX_SECONDS:.0f}s. Cut a beat or tighten the lines.")

    chrome = find_chrome()
    spills = {}
    for i, beat in enumerate(reel["beats"]):
        page = work / f"probe-{i:02d}.html"
        page.write_text(render_frames(beat, brand, post["theme"], int(post["seed"]), i, 0.5, [T_STILL], probe=True),
                        encoding="utf-8")
        if found := overflow(chrome, page):
            spills[i + 1] = found
    if spills:
        details = "\n".join(f"  - beat {k}: {v}" for k, v in spills.items())
        raise SystemExit(f"Reel copy spills outside the safe zone. Shorten it or use a smaller visual:\n{details}")

    motions = brief.get("motions") or ["push", "pull", "still"]
    clips, punches = [], []
    for i, (beat, narration, slot) in enumerate(zip(reel["beats"], narrations, slots)):
        frames = beat_frames(chrome, beat, brand, post, i, slot, 0.0, work)
        word_at = punch_time(beat, narration, rng)
        local = None if word_at is None else slot.voice_at - slot.start + word_at
        if local is not None:
            punches.append(slot.start + local)
        clips.append(beat_clip(frames, slot, rng.choice(motions), local, work / f"clip{i:02d}.mp4"))
        print(f"  beat {i + 1:02d} {beat['kind']:<8} {slot.length:4.1f}s  {beat.get('headline', '')}"
              f"{'  [punch]' if local is not None else ''}")

    audio = mix_audio(narrations, slots, brief.get("mood", "epic"), int(post["seed"]), punches, work)
    words = [w for b, n, s in zip(reel["beats"], narrations, slots)
             for w in shift(punctuate(n.words, b["voice"]), s.voice_at)]
    accent = PALETTES[post["palette"]]["a1_light"]
    ass = work / "captions.ass"
    ass.write_text(build_ass(words, accent, brief.get("caption_font", CAPTION_FONTS[0]),
                             brief.get("caption_style", CAPTION_STYLES[0])), encoding="utf-8")

    transitions = brief.get("transitions") or list(TRANSITIONS)
    video = post_dir / "reel.mp4"
    for kbps in BITRATES_K:
        # libass resolves the subtitle path relative to the working directory, so run from work/.
        cwd = Path.cwd()
        try:
            os.chdir(work)
            final_cut(clips, slots, transitions, audio, ass, video, kbps)
        finally:
            os.chdir(cwd)
        if video.stat().st_size <= MAX_BYTES:
            break
        print(f"  {video.stat().st_size / 1e6:.1f} MB is over the limit, re-encoding at a lower bitrate")
    else:
        raise SystemExit(f"reel.mp4 is still over {MAX_BYTES // 2**20} MB. Shorten the script.")

    cover_png = post_dir / "reel_cover.png"
    run_ffmpeg(["-ss", f"{min(length - 0.1, slots[0].length - XFADE_S - 0.1):.2f}", "-i", str(video),
                "-frames:v", "1", str(cover_png)])
    to_jpeg(cover_png)
    (post_dir / "reel_caption.txt").write_text(post["reel_caption"], encoding="utf-8")
    if not keep_work:
        shutil.rmtree(work)
    print(f"reel: {video.relative_to(ROOT)}  {duration(video):.1f}s  {video.stat().st_size / 1e6:.1f} MB")
    return video


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("post", type=Path)
    parser.add_argument("--keep-work", action="store_true", help="keep the frames and intermediate clips")
    args = parser.parse_args()

    post = load_json(args.post)
    problems = validate_reel(post)
    if problems:
        print("Reel failed validation:", *problems, sep="\n  - ", file=sys.stderr)
        raise SystemExit(1)
    brand = styled_brand(load_json(ROOT / "brand.json"), post)
    render_reel(post, brand, args.keep_work)


if __name__ == "__main__":
    main()
