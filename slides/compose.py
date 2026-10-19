"""Compose a full 1080x1350 carousel slide: theme surface + generative art + layout + copy + visual.

Randomness is seeded: a post's "seed" picks each slide's art style and, where the post
doesn't say, its layout. Same post file, same pixels.
"""

import random
from html import escape

from .art import art_layer
from .motion import CSS as MOTION_CSS, T_STILL
from .theme import DEFAULT_THEME, THEMES, surface_css
from .visuals import CSS as VISUAL_CSS, render_visual

LAYOUTS = {
    "cover": ["left", "center", "poster"],
    "stake": ["left", "center"],
    "content": ["stack", "stack", "visual-first", "number", "center"],
    "recap": ["stack"],
    "cta": ["left", "center"],
}

BASE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 1080px; background: #020617; }
body { -webkit-font-smoothing: antialiased; }
.slide { position: relative; width: 1080px; height: 1350px; padding: 110px 120px 150px; overflow: hidden;
  display: flex; flex-direction: column; background: var(--bg); color: var(--fg); letter-spacing: -0.02em; }
.art { position: absolute; inset: 0; z-index: 0; pointer-events: none; }
.art-svg { width: 100%; height: 100%; }
.brand { position: relative; z-index: 1; display: flex; align-items: center; gap: 16px; font-weight: 700; font-size: 32px; }
.brand img { width: 60px; height: 60px; border-radius: 50%; }
.foot { position: absolute; left: 120px; right: 120px; bottom: 60px; z-index: 1; display: flex; justify-content: space-between;
  font-size: 30px; font-weight: 650; opacity: .75; }
.content { position: relative; z-index: 1; flex: 1; min-height: 0; display: flex; flex-direction: column; justify-content: center; gap: 36px; }
.card-surface .content { background: var(--panel); color: var(--fg); border-radius: 44px; padding: 64px 60px;
  margin: 10px -40px 0; box-shadow: 0 40px 90px rgba(2,6,23,.35); justify-content: flex-start; }
.card-surface .v-donut .ring span { background: var(--panel); }
.gradient-surface .v-donut .ring span { background: rgba(2,6,23,.28); }
.g { background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
h1 { font-weight: 900; line-height: .95; letter-spacing: -0.03em; }
h2 { font-weight: 850; line-height: 1.02; letter-spacing: -0.02em; }
.hs-tight h1, .hs-tight h2 { letter-spacing: -0.045em; }
.hs-mono h1, .hs-mono h2, .hs-mono .foot, .hs-mono .kicker { font-family: 'JetBrains Mono', ui-monospace, monospace; letter-spacing: -0.03em; }
.kicker { font-size: 30px; font-weight: 900; letter-spacing: .1em; color: var(--accent); text-transform: uppercase; }
.body { font-size: 44px; line-height: 1.32; font-weight: 500; color: var(--muted); }
.has-visual .body { font-size: 38px; }
.num-pill { align-self: flex-start; font-size: 30px; font-weight: 900; letter-spacing: .06em; padding: 12px 24px;
  border-radius: 999px; background: var(--grad); color: #fff; }
.l-number .content { display: grid; grid-template-columns: 220px 1fr; column-gap: 34px; align-content: center; }
.l-number .content > * { grid-column: 2; }
.l-number .bignum { grid-column: 1; grid-row: 1 / span 3; font-size: 230px; font-weight: 900; line-height: .85;
  letter-spacing: -0.06em; align-self: start; }
.l-number .content > .v { grid-column: 1 / span 2; }
.l-center .content { align-items: center; text-align: center; }
.l-center .content > .v { align-items: stretch; text-align: left; }
.l-poster .content { justify-content: flex-end; padding-bottom: 20px; }
.l-visual-first .content { justify-content: flex-start; padding-top: 30px; }
.l-visual-first .content > .v { order: -1; margin-bottom: 18px; }
.swipe { position: absolute; right: 120px; bottom: 130px; z-index: 1; font-size: 32px; font-weight: 750;
  padding: 18px 32px; border-radius: 999px; border: 3px solid var(--line); }
.recap { list-style: none; }
.recap li { display: flex; align-items: center; gap: 30px; font-size: 46px; font-weight: 750; padding: 24px 0; border-bottom: 2px solid var(--line); }
.recap li span { flex: none; width: 76px; height: 76px; border-radius: 20px; background: var(--grad); display: grid; place-items: center;
  font-size: 36px; font-weight: 900; color: #fff; }
.bookmark { width: 120px; height: 152px; }
.site { align-self: flex-start; font-size: 40px; font-weight: 800; padding: 22px 42px; border-radius: 999px; background: var(--card); color: var(--card-fg); }
.l-center .site { align-self: center; }
"""

OVERFLOW_PROBE = """<script>
addEventListener('load', () => setTimeout(() => {
  const bad = [];
  document.querySelectorAll('.slide').forEach((s, n) => {
    const box = s.getBoundingClientRect(); const foot = s.querySelector('.foot').getBoundingClientRect();
    s.querySelectorAll('.content *').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width && (r.bottom > foot.top - 8 || r.right > box.right - 60 || r.left < box.left + 60 || r.top < box.top + 40))
        bad.push(el.tagName.toLowerCase() + '.' + (el.className.baseVal ?? el.className).split(' ')[0]);
    });
  });
  document.documentElement.dataset.overflow = [...new Set(bad)].slice(0, 6).join(' ');
}, 300));
</script>"""


DEFAULT_CAPS_EM = 0.74  # average advance of a heavy sans's capitals, in em


def _headline_size(text: str, role: str, layout: str, caps_em: float = DEFAULT_CAPS_EM) -> int:
    """Largest size where the longest word still fits the column on one line."""
    longest = max((len(w) for w in text.split()), default=1)
    column = 586 if layout == "number" else 840
    cap = 150 if role in ("cover", "cta") else 96
    if role in ("cover", "cta") and len(text) > 18:
        cap = 128
    return int(min(cap, column / (longest * caps_em)))


def _headline(text: str, tag: str, role: str, layout: str = "stack", caps_em: float = DEFAULT_CAPS_EM) -> str:
    text = text.replace("-", "‑")  # non-breaking hyphen: never split MUST-HAVES across lines
    head, _, last = text.rpartition(" ")
    inner = f'{escape(head)} <span class="g">{escape(last)}</span>' if head else f'<span class="g">{escape(text)}</span>'
    return f'<{tag} style="font-size:{_headline_size(text, role, layout, caps_em)}px">{inner}</{tag}>'


def _role(kind: str) -> str:
    return "content" if kind == "step" else kind


def plan_slide(slide: dict, theme_name: str, seed: int, position: int) -> dict:
    """Decide surface, art style and layout for one slide, deterministically."""
    theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    rng = random.Random(seed * 1000 + position)
    role = _role(slide["kind"])
    surface = slide.get("surface") or theme["roles"][role]
    art = slide.get("art") or rng.choice(theme["art"].get(surface, ["none"]))
    layout = slide.get("layout") or rng.choice(LAYOUTS[role])
    if layout == "number" and slide["kind"] not in ("step", "content"):
        layout = "stack"
    return {"role": role, "surface": surface, "art": art, "layout": layout, "headline": theme["headline"],
            "art_seed": rng.randint(1, 10**6)}


def _content(slide: dict, plan: dict, brand: dict, number: int) -> str:
    role, layout = plan["role"], plan["layout"]
    parts = []
    if slide.get("kicker"):
        parts.append(f'<div class="kicker">{escape(slide["kicker"])}</div>')
    if role == "content" and number:
        if layout == "number":
            parts.append(f'<div class="bignum g">{number:02d}</div>')
        else:
            parts.append(f'<div class="num-pill">{number:02d}</div>')
    if role == "cta":
        parts.append('<svg class="bookmark" viewBox="0 0 22 28" fill="none" stroke="currentColor" stroke-width="2.4" '
                     'stroke-linejoin="round"><path d="M2 3a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v23l-9-6-9 6z"/></svg>')
    if slide.get("headline"):
        parts.append(_headline(slide["headline"], "h1" if role in ("cover", "cta") else "h2", role, layout,
                               brand.get("caps_em", DEFAULT_CAPS_EM)))
    if slide.get("body"):
        parts.append(f'<p class="body">{escape(slide["body"])}</p>')
    if role == "recap" and slide.get("items"):
        items = "".join(f'<li style="--i:{i}"><span>{i}</span>{escape(t)}</li>'
                        for i, t in enumerate(slide["items"], start=1))
        parts.append(f'<ul class="recap seq">{items}</ul>')
    parts.append(render_visual(slide.get("visual")))
    if role == "cta":
        parts.append(f'<span class="site">{escape(brand["site"])}</span>')
    return "".join(parts)


def slide_section(slide: dict, brand: dict, plan: dict, position: int, total: int, number: int, t: float) -> str:
    role = plan["role"]
    classes = (f'slide l-{plan["layout"]} hs-{plan["headline"]} {plan["surface"]}-surface'
               f'{" has-visual" if slide.get("visual") else ""}')
    style = surface_css(plan["surface"], brand["colors"]) + f"--t:{t:.3f};"
    brand_mark = (f'<div class="brand"><img src="{escape(_file_name(brand["logo"]))}" alt="">{escape(brand["name"])}</div>'
                  if role in ("cover", "cta") else "")
    swipe = '<div class="swipe">Swipe &rarr;</div>' if role == "cover" else ""
    return (f'<section class="{classes}" style="{style}"><div class="art">{art_layer(plan["art"], plan["art_seed"])}</div>'
            f'{brand_mark}<div class="content">{_content(slide, plan, brand, number)}</div>{swipe}'
            f'<div class="foot"><span>{escape(brand["handle"])}</span><span>{position}/{total}</span></div></section>')


def _file_name(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def font_link(brand: dict) -> str:
    return (f'<link href="https://fonts.googleapis.com/css2?{fonts_query(brand)}&family=JetBrains+Mono:wght@500;700'
            f'&display=block" rel="stylesheet">')


def font_css(brand: dict) -> str:
    """Body and display face rules. Goes after the base CSS so the display weight wins."""
    display = brand.get("display_font", brand["font"])
    weight = brand.get("display_weight", 900)
    return (f'body{{font-family:"{brand["font"]}",system-ui,sans-serif}}'
            f'h1,h2,.bignum,.v-stat .big,.v-quote p{{font-family:"{display}",Georgia,serif;'
            f'font-weight:{weight};letter-spacing:-0.01em}}')


def fonts_query(brand: dict) -> str:
    from .theme import FONT_AXES
    names = dict.fromkeys([brand["font"], brand.get("display_font", brand["font"])])
    parts = []
    for name in names:
        axis = FONT_AXES.get(name, "")
        parts.append(f"family={name.replace(' ', '+')}{':' + axis if axis else ''}")
    return "&".join(parts)


def document(sections: list[str], brand: dict, probe: bool = False) -> str:
    return (f'<!doctype html><html><head><meta charset="utf-8">{font_link(brand)}'
            f'<style>{BASE_CSS}{VISUAL_CSS}{MOTION_CSS}{font_css(brand)}</style>'
            f'</head><body>{"".join(sections)}{OVERFLOW_PROBE if probe else ""}</body></html>')


def render_slide(slide: dict, brand: dict, position: int, total: int, number: int,
                 theme: str = DEFAULT_THEME, seed: int = 0, times: list[float] | None = None,
                 probe: bool = False) -> str:
    """One HTML page. With `times`, the page stacks one copy of the slide per frame time."""
    plan = plan_slide(slide, theme, seed, position)
    sections = [slide_section(slide, brand, plan, position, total, number, t) for t in (times or [T_STILL])]
    return document(sections, brand, probe)
