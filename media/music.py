"""Procedural, royalty-free score and sound design, synthesized with ffmpeg alone.

A mood picks the chord progression, tempo pulse and brightness; the post's seed picks the key
and texture, so every reel gets its own bed. Sound design adds an impact boom under the hook
and a whoosh on every cut. Nothing here is sampled from anyone else's recording.
"""

import random
import subprocess
from pathlib import Path

RATE = 48000
TIMEOUT_S = 300
ROOTS_HZ = {"G": 49.0, "A": 55.0, "B": 61.74, "C": 65.41, "D": 73.42, "E": 82.41}
# Chords as semitones above the root.
I, IV, V, VI, III, VII = [0, 7, 12, 15], [5, 12, 17, 20], [7, 14, 19, 22], [-4, 3, 8, 12], [3, 10, 15, 19], [-2, 5, 10, 14]
MOODS = {
    "epic": {"chords": [I, VI, III, VII], "bar_s": 4.0, "pulse": "kick", "bpm": 72, "cutoff": 2200},
    "contemplative": {"chords": [I, IV, I, V], "bar_s": 6.0, "pulse": None, "bpm": 0, "cutoff": 1600},
    "tension": {"chords": [I, [0, 7, 13, 15], I, [0, 6, 12, 15]], "bar_s": 5.0, "pulse": "heart", "bpm": 64,
                "cutoff": 1300},
    "triumphant": {"chords": [I, VII, VI, VII], "bar_s": 4.0, "pulse": "kick", "bpm": 84, "cutoff": 2600},
    "noir": {"chords": [I, VI, IV, V], "bar_s": 5.0, "pulse": "tick", "bpm": 90, "cutoff": 1800},
}


def run(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], capture_output=True, text=True, timeout=TIMEOUT_S)
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg (music) failed:\n{result.stderr[-800:]}")


def _chord_expr(root: float, chord: list[int], shimmer: bool) -> str:
    terms = []
    for k, semis in enumerate(chord):
        f = root * 2 ** (semis / 12)
        amp = 0.16 / (1 + k * 0.35)
        terms.append(f"{amp:.3f}*sin(2*PI*{f:.3f}*t)+{amp * .55:.3f}*sin(2*PI*{f * 1.004:.3f}*t+{k + 1.3:.1f})")
    if shimmer:
        f = root * 8 * 2 ** (chord[1] / 12)
        terms.append(f"0.012*sin(2*PI*{f:.2f}*t)*(0.5+0.5*sin(2*PI*0.21*t))")
    return f"({'+'.join(terms)})*(0.82+0.18*sin(2*PI*0.08*t))"


def _pulse_expr(kind: str | None, bpm: int) -> str:
    if not kind:
        return "0"
    beat = 60 / bpm
    m = f"mod(t,{beat:.4f})"
    if kind == "kick":
        return f"0.32*sin(2*PI*(42+70*exp(-28*{m}))*{m})*exp(-7*{m})"
    if kind == "heart":
        m2 = f"mod(t+{beat * .72:.4f},{beat:.4f})"
        return (f"0.30*sin(2*PI*48*{m})*exp(-14*{m})+0.18*sin(2*PI*44*{m2})*exp(-16*{m2})")
    return f"0.05*sin(2*PI*1800*{m})*exp(-90*{m})"  # tick: a clock under the narration


def score(mood: str, seed: int, length: float, out: Path) -> Path:
    """Write a stereo wav bed of `length` seconds."""
    spec = MOODS[mood]
    rng = random.Random(seed)
    root = rng.choice(list(ROOTS_HZ.values()))
    shimmer = rng.random() < .6
    bar = spec["bar_s"]
    bars = int(length / bar) + 2
    chords = spec["chords"]
    pulse = _pulse_expr(spec["pulse"], spec["bpm"])
    seg_dir = out.parent / "music-parts"
    seg_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    for k in range(min(bars, len(chords))):
        expr = f"{_chord_expr(root, chords[k], shimmer)}+{pulse}"
        part = seg_dir / f"{k}.wav"
        run(["-f", "lavfi", "-i", f"aevalsrc='{expr}|{expr.replace('sin(2*PI*', 'sin(0.02+2*PI*', 1)}':s={RATE}:d={bar + 1.5}",
             "-af", f"lowpass=f={spec['cutoff']},afade=t=in:d=0.8,afade=t=out:st={bar + 0.7}:d=0.8", str(part)])
        parts.append(part)
    # Cycle the progression to cover the reel, crossfading bar to bar.
    sequence = [parts[k % len(parts)] for k in range(bars)]
    inputs = [arg for p in sequence for arg in ("-i", str(p))]
    chain, last = [], "[0:a]"
    for k in range(1, len(sequence)):
        label = f"[x{k}]"
        chain.append(f"{last}[{k}:a]acrossfade=d=1.5:c1=tri:c2=tri{label}")
        last = label
    chain.append(f"{last}aecho=0.8:0.82:110|230|370:0.32|0.22|0.14,atrim=0:{length:.3f},"
                 f"afade=t=in:d=1.2,afade=t=out:st={max(0.0, length - 2.5):.3f}:d=2.5[m]")
    run([*inputs, "-filter_complex", ";".join(chain), "-map", "[m]", "-ar", str(RATE), "-ac", "2", str(out)])
    return out


def boom(out: Path) -> Path:
    """Sub-bass impact for the hook."""
    expr = "0.9*sin(2*PI*(38+90*exp(-7*t))*t)*exp(-2.4*t)"
    run(["-f", "lavfi", "-i", f"aevalsrc='{expr}|{expr}':s={RATE}:d=2.4", "-af", "lowpass=f=900", str(out)])
    return out


def whoosh(out: Path) -> Path:
    """Filtered noise swell for transitions."""
    run(["-f", "lavfi", "-i", f"anoisesrc=color=pink:r={RATE}:d=0.7:a=0.5",
         "-af", "bandpass=f=1400:width_type=o:w=1.6,afade=t=in:d=0.45:curve=exp,afade=t=out:st=0.45:d=0.25,"
                "volume=7,aformat=channel_layouts=stereo", str(out)])
    return out
