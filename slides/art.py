"""Seeded generative background art. Same seed, same picture, so renders are reproducible.

Every generator returns SVG markup W wide and h tall (1350 for carousel slides, 1920 for
reel frames) that uses the surface's CSS variables, so the art follows whichever surface
it sits on. Elements with class "drift" or "spin" move when the frame is animated.
"""

import math
import random

W = 1080
SLIDE_H = 1350


def _svg(body: str, h: int, defs: str = "") -> str:
    return (f'<svg class="art-svg" viewBox="0 0 {W} {h}" preserveAspectRatio="xMidYMid slice" '
            f'xmlns="http://www.w3.org/2000/svg"><defs>{defs}</defs>{body}</svg>')


def glow(rng: random.Random, h: int) -> str:
    defs = ('<radialGradient id="g1"><stop offset="0" stop-color="var(--accent)" stop-opacity=".34"/>'
            '<stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="g2"><stop offset="0" stop-color="var(--accent2)" stop-opacity=".26"/>'
            '<stop offset="1" stop-color="var(--accent2)" stop-opacity="0"/></radialGradient>')
    body = "".join(
        f'<circle class="drift" style="--i:{i}" cx="{rng.randint(-100, W + 100)}" cy="{rng.randint(-100, h + 100)}" '
        f'r="{rng.randint(380, 720)}" fill="url(#g{1 + i % 2})"/>'
        for i in range(rng.randint(2, 3)))
    return _svg(body, h, defs)


def waves(rng: random.Random, h: int) -> str:
    defs = ('<linearGradient id="wv" x1="0" x2="1"><stop offset="0" stop-color="var(--accent)"/>'
            '<stop offset="1" stop-color="var(--accent2)"/></linearGradient>')
    base = rng.randint(int(h * .78), int(h * .88))  # low, so the bands never run through copy
    amp, phase = rng.randint(50, 110), rng.random() * math.tau
    paths = []
    for i in range(rng.randint(5, 9)):
        y = base + i * 26
        points = " ".join(f"{x},{y + amp * math.sin(x / 210 + phase + i * .22):.0f}" for x in range(-40, W + 80, 40))
        paths.append(f'<polyline class="drift" style="--i:{i}" points="{points}" fill="none" stroke="url(#wv)" '
                     f'stroke-width="{rng.choice([3, 4, 6])}" stroke-opacity="{.75 - i * .06:.2f}"/>')
    return _svg("".join(paths), h, defs)


def rings(rng: random.Random, h: int) -> str:
    cx, cy = rng.choice([(W + 80, -60), (-80, h + 60), (W + 40, h * .7)])
    body = "".join(
        f'<circle class="spin" style="--i:{i}" cx="{cx}" cy="{cy}" r="{160 + i * 95}" fill="none" '
        f'stroke="var(--accent)" stroke-opacity="{.32 - i * .03:.2f}" stroke-width="2" '
        f'stroke-dasharray="{rng.choice(["0", "8 14", "2 10"])}"/>'
        for i in range(8))
    return _svg(body, h)


def dots(rng: random.Random, h: int) -> str:
    step = rng.choice([36, 44, 54])
    fx, fy = rng.randint(0, W), rng.randint(0, h)
    out = []
    for x in range(step // 2, W, step):
        for y in range(step // 2, h, step):
            fade = 1 - min(1, math.hypot(x - fx, y - fy) / 900)
            if fade > .05:
                out.append(f'<circle cx="{x}" cy="{y}" r="3" fill="var(--accent)" opacity="{fade * .45:.2f}"/>')
    return _svg("".join(out), h)


def rules(rng: random.Random, h: int) -> str:
    y = rng.randint(80, 140)
    lines = [f'<line x1="120" x2="{W - 120}" y1="{y}" y2="{y}" stroke="var(--fg)" stroke-opacity=".5" stroke-width="2"/>',
             f'<line x1="120" x2="{W - 120}" y1="{y + 10}" y2="{y + 10}" stroke="var(--fg)" stroke-opacity=".25"/>',
             f'<line x1="120" x2="{W - 120}" y1="{h - 130}" y2="{h - 130}" stroke="var(--fg)" stroke-opacity=".2"/>']
    return _svg("".join(lines), h)


def grid(rng: random.Random, h: int) -> str:
    minor = "".join(f'<line x1="{x}" x2="{x}" y1="0" y2="{h}"/>' for x in range(0, W, 45))
    minor += "".join(f'<line y1="{y}" y2="{y}" x1="0" x2="{W}"/>' for y in range(0, h, 45))
    major = "".join(f'<line x1="{x}" x2="{x}" y1="0" y2="{h}"/>' for x in range(0, W, 225))
    major += "".join(f'<line y1="{y}" y2="{y}" x1="0" x2="{W}"/>' for y in range(0, h, 225))
    cx, cy, r = rng.randint(650, 1000), rng.randint(150, h - 150), rng.randint(140, 300)
    construct = (f'<circle class="spin" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="var(--accent)" '
                 f'stroke-opacity=".55" stroke-width="2" stroke-dasharray="10 10"/>'
                 f'<line x1="{cx - r - 60}" x2="{cx + r + 60}" y1="{cy}" y2="{cy}" stroke="var(--accent)" stroke-opacity=".4"/>'
                 f'<line y1="{cy - r - 60}" y2="{cy + r + 60}" x1="{cx}" x2="{cx}" stroke="var(--accent)" stroke-opacity=".4"/>')
    return _svg(f'<g stroke="var(--fg)" stroke-opacity=".06">{minor}</g>'
                f'<g stroke="var(--fg)" stroke-opacity=".13">{major}</g>{construct}', h)


def shapes(rng: random.Random, h: int) -> str:
    """Fresco-style overlapping translucent shapes, plus grain."""
    defs = ('<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="'
            f'{rng.randint(1, 999)}"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .22 0"/></filter>')
    out = []
    for i in range(rng.randint(3, 5)):
        color = rng.choice(["var(--accent)", "var(--accent2)"])
        x, y, s = rng.randint(-150, W), rng.randint(-150, h), rng.randint(180, 420)
        kind = rng.choice(["circle", "rect", "tri"])
        attrs = f'class="drift" style="--i:{i};mix-blend-mode:multiply" fill="{color}" opacity=".16"'
        if kind == "circle":
            out.append(f'<circle {attrs} cx="{x}" cy="{y}" r="{s // 2}"/>')
        elif kind == "rect":
            out.append(f'<rect {attrs} x="{x}" y="{y}" width="{s}" height="{s * .7:.0f}" rx="40" '
                       f'transform="rotate({rng.randint(-25, 25)} {x} {y})"/>')
        else:
            out.append(f'<polygon {attrs} points="{x},{y} {x + s},{y + s // 3} {x + s // 4},{y + s}"/>')
    out.append(f'<rect width="{W}" height="{h}" filter="url(#grain)"/>')
    return _svg("".join(out), h, defs)


def marble(rng: random.Random, h: int) -> str:
    """Soft marble veining from turbulence, tinted with the accent."""
    seed = rng.randint(1, 999)
    freq = rng.choice([".004 .012", ".006 .016", ".003 .009"])
    defs = (f'<filter id="mv" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" '
            f'baseFrequency="{freq}" numOctaves="5" seed="{seed}"/>'
            '<feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -2.6 1.5"/>'
            '<feComposite in2="SourceGraphic" operator="in"/></filter>')
    return _svg(f'<rect width="{W}" height="{h}" fill="var(--accent)" opacity=".2" filter="url(#mv)"/>', h, defs)


def meander(rng: random.Random, h: int) -> str:
    """Greek-key bands across the top and bottom edges."""
    unit = rng.choice([36, 44])
    key = (f'M0 {unit} V0 H{unit} V{unit * .75:.0f} H{unit * .25:.0f} V{unit * .25:.0f} H{unit * .5:.0f} '
           f'V{unit * .5:.0f}')
    def band(y: int) -> str:
        return "".join(f'<path d="{key}" transform="translate({x} {y})"/>' for x in range(0, W + unit, unit))
    top, bottom = rng.randint(40, 70), h - unit - 12
    return _svg(f'<g fill="none" stroke="var(--accent)" stroke-opacity=".5" stroke-width="4">'
                f'{band(top)}{band(bottom)}</g>', h)


def laurel(rng: random.Random, h: int) -> str:
    """Two laurel branches curving around a large off-centre circle."""
    cx, cy, r = rng.choice([(W * .82, h * .3), (W * .2, h * .78), (W * .85, h * .8)]) + (rng.randint(330, 460),)
    leaves = []
    for side in (-1, 1):
        for k in range(14):
            a = math.pi / 2 + side * (0.25 + k * 0.17)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            rot = math.degrees(a) + side * 40
            leaves.append(f'<ellipse class="drift" style="--i:{k % 4}" cx="{x:.0f}" cy="{y:.0f}" rx="34" ry="13" '
                          f'transform="rotate({rot:.0f} {x:.0f} {y:.0f})"/>')
    stem = f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="none" stroke="var(--accent)" stroke-opacity=".3" stroke-width="3"/>'
    return _svg(f'{stem}<g fill="var(--accent)" opacity=".32">{"".join(leaves)}</g>', h)


def geometry(rng: random.Random, h: int) -> str:
    """Sacred geometry: a golden spiral of squares or a platonic wireframe."""
    cx, cy = rng.randint(620, 960), rng.choice([rng.randint(160, 420), rng.randint(h - 520, h - 220)])
    if rng.random() < .5:
        out, size, x, y = [], 420.0, cx - 260, cy - 260
        for k in range(7):
            out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{size:.0f}" height="{size:.0f}"/>')
            start = [(x, y + size), (x, y), (x + size, y), (x + size, y + size)][k % 4]
            end = [(x + size, y), (x + size, y + size), (x, y + size), (x, y)][k % 4]
            out.append(f'<path d="M{start[0]:.0f} {start[1]:.0f} A{size:.0f} {size:.0f} 0 0 1 {end[0]:.0f} {end[1]:.0f}"/>')
            nxt = size / 1.618
            x, y = [(x + size, y), (x + size - nxt, y + size), (x - nxt, y + size - nxt), (x, y - nxt)][k % 4]
            size = nxt
        body = "".join(out)
    else:
        pts = [(cx + 300 * math.cos(math.tau * k / 6 + .5), cy + 300 * math.sin(math.tau * k / 6 + .5)) for k in range(6)]
        body = "".join(f'<line x1="{a[0]:.0f}" y1="{a[1]:.0f}" x2="{b[0]:.0f}" y2="{b[1]:.0f}"/>'
                       for i, a in enumerate(pts) for b in pts[i + 1:])
        body += f'<circle cx="{cx}" cy="{cy}" r="300"/>'
    return _svg(f'<g class="spin" fill="none" stroke="var(--accent)" stroke-opacity=".38" stroke-width="2">{body}</g>', h)


def columns(rng: random.Random, h: int) -> str:
    """A colonnade silhouette along the bottom, with a pediment line."""
    count = rng.choice([4, 5, 6])
    gap = W / count
    col_h = rng.randint(int(h * .26), int(h * .34))
    base = h - 40
    out = []
    for k in range(count):
        x = gap * k + gap * .28
        wcol = gap * .44
        out.append(f'<rect x="{x:.0f}" y="{base - col_h}" width="{wcol:.0f}" height="{col_h}"/>')
        out.append(f'<rect x="{x - 14:.0f}" y="{base - col_h - 22}" width="{wcol + 28:.0f}" height="22"/>')
        for f in range(1, 4):
            fx = x + wcol * f / 4
            out.append(f'<line x1="{fx:.0f}" x2="{fx:.0f}" y1="{base - col_h + 10}" y2="{base - 10}" '
                       f'stroke="var(--bg)" stroke-opacity=".35" stroke-width="3"/>')
    out.append(f'<rect x="0" y="{base - col_h - 60}" width="{W}" height="26"/>')
    out.append(f'<rect x="0" y="{base}" width="{W}" height="40"/>')
    return _svg(f'<g fill="var(--accent)" opacity=".16">{"".join(out)}</g>', h)


GENERATORS = {"glow": glow, "waves": waves, "rings": rings, "dots": dots, "rules": rules, "grid": grid,
              "shapes": shapes, "marble": marble, "meander": meander, "laurel": laurel,
              "geometry": geometry, "columns": columns}


def art_layer(style: str, seed: int, height: int = SLIDE_H) -> str:
    if style == "none" or style not in GENERATORS:
        return ""
    return GENERATORS[style](random.Random(seed), height)
