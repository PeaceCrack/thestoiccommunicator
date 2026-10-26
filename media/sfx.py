"""Procedural sound effects, synthesized with ffmpeg, randomized per reel and per cut.

Each kind (whoosh, swish, riser, shimmer, tick, thud, impact) takes random parameters (noise
colour, sweep, pitch, length), so no two cuts sound alike. plan_cuts() decides which sound
lands on which cut: never the same kind twice in a row, and some cuts left silent, so the
edit breathes instead of thumping on every transition.
"""

import random
import subprocess
from dataclasses import dataclass
from pathlib import Path

RATE = 48000
TIMEOUT_S = 120
CUT_KINDS = ("whoosh", "swish", "riser", "shimmer", "tick")
SILENT_CUT_CHANCE = 0.3
HIT_KINDS = ("impact", "thud", "shimmer")


@dataclass(frozen=True)
class Cue:
    at: float        # seconds on the reel timeline
    path: Path
    gain: float      # linear volume


def _ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], capture_output=True, text=True, timeout=TIMEOUT_S)
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg (sfx) failed:\n{result.stderr[-800:]}")


def _noise(out: Path, color: str, length: float, chain: str) -> Path:
    _ffmpeg(["-f", "lavfi", "-i", f"anoisesrc=color={color}:r={RATE}:d={length:.3f}:a=0.6",
             "-af", f"{chain},aformat=channel_layouts=stereo", str(out)])
    return out


def _tone(out: Path, expr: str, length: float, chain: str) -> Path:
    _ffmpeg(["-f", "lavfi", "-i", f"aevalsrc='{expr}|{expr}':s={RATE}:d={length:.3f}", "-af", chain, str(out)])
    return out


def make(kind: str, rng: random.Random, out: Path) -> Path:
    """Synthesize one sound of this kind with random parameters."""
    if kind == "whoosh":
        length, freq = rng.uniform(0.45, 0.8), rng.choice([700, 1000, 1400, 1900])
        rise = rng.uniform(0.55, 0.75) * length
        return _noise(out, rng.choice(["pink", "brown", "white"]), length,
                      f"bandpass=f={freq}:width_type=o:w={rng.uniform(1.0, 2.2):.2f},"
                      f"afade=t=in:d={rise:.3f}:curve=exp,afade=t=out:st={rise:.3f}:d={length - rise:.3f},"
                      f"volume={rng.uniform(5, 8):.1f}")
    if kind == "swish":
        length = rng.uniform(0.18, 0.3)
        return _noise(out, "white", length,
                      f"highpass=f={rng.choice([2500, 3500, 4500])},afade=t=in:d={length * .3:.3f},"
                      f"afade=t=out:st={length * .3:.3f}:d={length * .7:.3f},volume={rng.uniform(0.7, 1.2):.2f}")
    if kind == "riser":
        length, f0 = rng.uniform(0.6, 1.0), rng.choice([180, 240, 320])
        expr = f"0.55*sin(2*PI*({f0}*t+{f0 * 1.5:.0f}*t*t/{length:.2f}))*t/{length:.2f}"
        return _tone(out, expr, length, f"aecho=0.8:0.6:40|80:0.3|0.2,afade=t=out:st={length - .08:.3f}:d=0.08")
    if kind == "shimmer":
        length, f0 = rng.uniform(0.8, 1.4), rng.choice([1320, 1568, 1760, 2093])
        expr = (f"0.3*sin(2*PI*{f0}*t)*exp(-3*t)+0.2*sin(2*PI*{f0 * 1.5:.0f}*t)*exp(-4*t)"
                f"+0.12*sin(2*PI*{f0 * 2:.0f}*t)*exp(-5*t)")
        return _tone(out, expr, length, "aecho=0.8:0.7:60|120:0.35|0.25")
    if kind == "tick":
        f0 = rng.choice([900, 1200, 1800])
        return _tone(out, f"0.4*sin(2*PI*{f0}*t)*exp(-60*t)", 0.15, "highpass=f=400")
    if kind == "thud":
        f0 = rng.choice([55, 65, 80])
        return _tone(out, f"0.8*sin(2*PI*({f0}+40*exp(-25*t))*t)*exp(-9*t)", 0.6, "lowpass=f=600")
    if kind == "impact":
        f0, decay = rng.choice([34, 38, 44]), rng.uniform(1.8, 2.8)
        expr = f"0.9*sin(2*PI*({f0}+{rng.choice([70, 90, 120])}*exp(-7*t))*t)*exp(-{decay:.2f}*t)"
        return _tone(out, expr, 2.4, f"lowpass=f={rng.choice([700, 900, 1200])},aecho=0.8:0.5:90:0.25")
    raise ValueError(f"unknown sfx kind {kind!r}")


def plan_cuts(cut_times: list[float], punch_times: list[float], rng: random.Random, work: Path) -> list[Cue]:
    """Pick a sound for the hook, each cut and each punch-in, all different from their neighbours."""
    work.mkdir(parents=True, exist_ok=True)
    cues = [Cue(0.0, make(rng.choice(HIT_KINDS[:2]), rng, work / "hit.wav"), rng.uniform(0.6, 0.85))]
    last = None
    for k, at in enumerate(cut_times):
        if rng.random() < SILENT_CUT_CHANCE:
            last = None
            continue
        kind = rng.choice([c for c in CUT_KINDS if c != last])
        lead = {"whoosh": 0.3, "riser": 0.55, "swish": 0.1}.get(kind, 0.0)
        cues.append(Cue(max(0.0, at - lead), make(kind, rng, work / f"cut{k:02d}-{kind}.wav"), rng.uniform(0.55, 1.0)))
        last = kind
    for k, at in enumerate(punch_times):
        kind = rng.choice(["thud", "tick"])
        cues.append(Cue(at, make(kind, rng, work / f"punch{k:02d}-{kind}.wav"), rng.uniform(0.4, 0.7)))
    return cues
