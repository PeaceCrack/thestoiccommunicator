"""Narration with word timings: Microsoft neural voices through edge-tts (free, no key), then
an EQ and compression chain that adds chest, presence and a little room, so the read sounds
like a narrator in a hall rather than a phone assistant.

edge-tts is imported lazily so the publishing workflow and tests never need it.
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

RETRIES = 3
TIMEOUT_S = 120
TICKS_PER_S = 10_000_000  # edge-tts reports offsets in 100 ns ticks
# Warmth at 120 Hz, mud cut at 350 Hz, presence at 3.2 kHz, gentle compression, a short room.
VOICE_FX = ("highpass=f=65,equalizer=f=120:t=q:w=0.9:g=4,equalizer=f=350:t=q:w=1.2:g=-2,"
            "equalizer=f=3200:t=q:w=1.4:g=2.5,acompressor=threshold=-20dB:ratio=3:attack=6:release=90:makeup=2,"
            "aecho=0.85:0.5:28|52:0.14|0.08,aresample=48000")


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Narration:
    wav: Path
    duration: float
    words: tuple[Word, ...]


async def _stream(text: str, voice: dict, mp3: Path) -> list[Word]:
    import edge_tts  # noqa: PLC0415  (render-only dependency)

    communicate = edge_tts.Communicate(text, voice["name"], rate=voice.get("rate", "+0%"),
                                       pitch=voice.get("pitch", "+0Hz"), boundary="WordBoundary")
    words = []
    with mp3.open("wb") as out:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                out.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / TICKS_PER_S
                words.append(Word(start, start + chunk["duration"] / TICKS_PER_S, chunk["text"]))
    return words


def synthesize(text: str, voice: dict, mp3: Path) -> list[Word]:
    last_error: Exception | None = None
    for _ in range(RETRIES):
        try:
            words = asyncio.run(_stream(text, voice, mp3))
            if mp3.stat().st_size and words:
                return words
            last_error = RuntimeError("edge-tts returned no audio")
        except Exception as err:  # network errors surface as several aiohttp/edge-tts types
            last_error = err
    raise SystemExit(f"Voice synthesis failed after {RETRIES} tries ({voice['name']}): {last_error}")


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S)
    if result.returncode != 0:
        raise SystemExit(f"{Path(cmd[0]).name} failed:\n{result.stderr[-800:]}")
    return result.stdout


def duration(path: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))


def narrate(text: str, voice: dict, out_dir: Path, name: str) -> Narration:
    """Synthesize one line, polish it, and return the wav with word timings. Cached by content."""
    out_dir.mkdir(parents=True, exist_ok=True)
    wav, meta = out_dir / f"{name}.wav", out_dir / f"{name}.json"
    key = {"text": text, "voice": voice, "fx": VOICE_FX}
    if wav.exists() and meta.exists():
        cached = json.loads(meta.read_text(encoding="utf-8"))
        if cached.get("key") == key:
            return Narration(wav, cached["duration"], tuple(Word(*w) for w in cached["words"]))
    mp3 = out_dir / f"{name}.mp3"
    words = synthesize(text, voice, mp3)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-af", VOICE_FX, "-ac", "2", str(wav)])
    mp3.unlink()
    length = duration(wav)
    meta.write_text(json.dumps({"key": key, "duration": length,
                                "words": [[w.start, w.end, w.text] for w in words]}), encoding="utf-8")
    return Narration(wav, length, tuple(words))
