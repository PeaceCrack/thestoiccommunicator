"""HTML for one 1080x1920 reel frame: the same surfaces, art, type and visuals as the carousel.

Copy stays inside the safe zone that Instagram Reels and YouTube Shorts leave clear: y 230-1300
for the card, the right 150px free of copy (the like/comment rail), and y 1340-1540 reserved
for the burned-in captions that ffmpeg adds later. A progress bar along the top shows where
the viewer is, which keeps people watching to the end.
"""

import random
from html import escape

from .art import art_layer
from .compose import DEFAULT_CAPS_EM, font_css, font_link
from .motion import CSS as MOTION_CSS
from .theme import DEFAULT_THEME, THEMES, surface_css
from .visuals import CSS as VISUAL_CSS, render_visual

WIDTH, HEIGHT = 1080, 1920
BEAT_ROLES = {"hook": "cover", "story": "stake", "fact": "content", "lesson": "content", "quote": "recap",
              "takeaway": "recap", "cta": "cta"}
LAYOUTS = ["top", "center", "low"]

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 1080px; background: #000; }
body { -webkit-font-smoothing: antialiased; }
.frame { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: var(--bg); color: var(--fg);
  letter-spacing: -0.02em; }
.art { position: absolute; inset: 0; z-index: 0; }
.art-svg { width: 100%; height: 100%; }
.shade { position: absolute; left: 0; right: 0; bottom: 0; height: 760px; z-index: 0;
  background: linear-gradient(to top, rgba(0,0,0,.55), transparent); }
.progress { position: absolute; z-index: 2; left: 60px; right: 60px; top: 150px; height: 8px; border-radius: 4px;
  background: rgba(255,255,255,.18); overflow: hidden; }
.progress i { display: block; height: 100%; background: var(--grad); border-radius: 4px; }
.brand { position: absolute; z-index: 2; left: 90px; top: 186px; display: flex; align-items: center; gap: 14px;
  font-size: 30px; font-weight: 700; opacity: .9; }
.brand img { width: 50px; height: 50px; border-radius: 50%; }
.card { position: absolute; z-index: 1; left: 90px; width: 840px; top: 300px; height: 1000px; display: flex;
  flex-direction: column; gap: 34px; justify-content: flex-start; }
.l-center .card { justify-content: center; }
.l-low .card { justify-content: flex-end; }
.card-surface .card, .paper-surface.boxed .card { background: var(--panel); border-radius: 44px; padding: 56px 52px;
  box-shadow: 0 40px 90px rgba(0,0,0,.35); height: auto; max-height: 1000px; }
.kicker { font-size: 32px; font-weight: 900; letter-spacing: .12em; color: var(--accent); text-transform: uppercase; }
h1, h2 { line-height: .98; letter-spacing: -0.02em; }
.g { background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
.body { font-size: 46px; line-height: 1.3; font-weight: 500; color: var(--muted); }
.card > .v { zoom: 1.22; width: calc(100% / 1.22); }
.card > .v-quote, .card > .v-story { zoom: 1.08; width: calc(100% / 1.08); }
.card .v-quote p { font-size: 64px; }
.l-top .card { padding-top: 70px; }
.card-surface .v-donut .ring span { background: var(--panel); }
.gradient-surface .v-donut .ring span { background: rgba(0,0,0,.28); }
.handle { position: absolute; z-index: 2; left: 90px; bottom: 300px; font-size: 30px; font-weight: 700; opacity: 0; }
.beat-cta .handle { opacity: .9; }
.rise { animation: rise 4s linear infinite both paused; animation-delay: calc(var(--i, 0) * 0.32s - var(--t) * 1s); }
"""

OVERFLOW_PROBE = """<script>
addEventListener('load', () => setTimeout(() => {
  const bad = []; const card = document.querySelector('.card');
  const limit = card.getBoundingClientRect();
  card.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    // Inline runs report the font's full ascent/descent, taller than the glyphs: check them sideways only.
    const inline = getComputedStyle(el).display === 'inline';
    const tall = !inline && (r.bottom > 1305 || r.top < 290 || r.bottom > limit.bottom + 4);
    if (r.width && (tall || r.right > 935 || r.left < 80))
      bad.push(el.tagName.toLowerCase() + '.' + (el.className.baseVal ?? el.className).split(' ')[0]);
  });
  document.documentElement.dataset.overflow = [...new Set(bad)].slice(0, 6).join(' ');
}, 300));
</script>"""


def headline_size(text: str, kind: str, caps_em: float) -> int:
    longest = max((len(w) for w in text.split()), default=1)
    cap = 132 if kind in ("hook", "cta") else 104
    if len(text) > 24:
        cap -= 18
    return int(min(cap, 820 / (longest * caps_em)))


def plan_beat(beat: dict, theme_name: str, seed: int, index: int) -> dict:
    theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    rng = random.Random(seed * 7919 + index)
    role = BEAT_ROLES[beat["kind"]]
    surface = beat.get("surface") or theme["roles"][role]
    return {"role": role, "surface": surface, "layout": beat.get("layout") or rng.choice(LAYOUTS),
            "art": beat.get("art") or rng.choice(theme["art"].get(surface, ["none"])),
            "art_seed": rng.randint(1, 10**6)}


def _copy(beat: dict, brand: dict) -> str:
    parts = []
    if beat.get("kicker"):
        parts.append(f'<div class="kicker rise" style="--i:0">{escape(beat["kicker"])}</div>')
    if beat.get("headline"):
        text = beat["headline"].replace("-", "‑")
        head, _, last = text.rpartition(" ")
        inner = f'{escape(head)} <span class="g">{escape(last)}</span>' if head else f'<span class="g">{escape(text)}</span>'
        size = headline_size(text, beat["kind"], brand.get("caps_em", DEFAULT_CAPS_EM))
        tag = "h1" if beat["kind"] in ("hook", "cta") else "h2"
        parts.append(f'<{tag} class="rise" style="--i:1;font-size:{size}px">{inner}</{tag}>')
    if beat.get("body"):
        parts.append(f'<p class="body rise" style="--i:2">{escape(beat["body"])}</p>')
    parts.append(render_visual(beat.get("visual")))
    return "".join(parts)


def frame_section(beat: dict, brand: dict, plan: dict, progress: float, t: float) -> str:
    classes = f'frame l-{plan["layout"]} {plan["surface"]}-surface beat-{beat["kind"]}'
    style = surface_css(plan["surface"], brand["colors"]) + f"--t:{t:.3f};"
    logo = escape(brand["logo"].rsplit("/", 1)[-1])
    return (f'<section class="{classes}" style="{style}">'
            f'<div class="art">{art_layer(plan["art"], plan["art_seed"], HEIGHT)}</div><div class="shade"></div>'
            f'<div class="progress"><i style="width:{progress * 100:.1f}%"></i></div>'
            f'<div class="brand"><img src="{logo}" alt="">{escape(brand["name"])}</div>'
            f'<div class="card">{_copy(beat, brand)}</div>'
            f'<div class="handle">{escape(brand["handle"])}</div></section>')


def render_frames(beat: dict, brand: dict, theme: str, seed: int, index: int, progress: float,
                  times: list[float], probe: bool = False) -> str:
    """One HTML page stacking one copy of the beat per frame time."""
    plan = plan_beat(beat, theme, seed, index)
    sections = "".join(frame_section(beat, brand, plan, progress, t) for t in times)
    return (f'<!doctype html><html><head><meta charset="utf-8">{font_link(brand)}'
            f'<style>{CSS}{VISUAL_CSS}{MOTION_CSS}{font_css(brand)}</style></head>'
            f'<body>{sections}{OVERFLOW_PROBE if probe else ""}</body></html>')
