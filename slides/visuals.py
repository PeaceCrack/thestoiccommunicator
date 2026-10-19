"""Infographic blocks for carousel slides. Each takes the slide's "visual" dict and returns HTML.

The catalog (VISUALS) is what post files may use; validate.py checks against it and the
rerole-post skill documents it. Elements carry motion classes from motion.py, with --i
setting the stagger order, so the same markup works as a still or an animated slide.
"""

import re
from html import escape

from .icons import ICONS, icon

CSS = """
.v { display: flex; flex-direction: column; gap: 18px; width: 100%; }
.v-chips { flex-direction: row; flex-wrap: wrap; gap: 16px; }
.v-chips span { position: relative; font-size: 38px; font-weight: 700; padding: 14px 28px; border-radius: 999px;
  background: var(--panel); border: 2px solid var(--line); }
.v-chips.strike span { color: var(--muted); }
.v-chips .strike-line { position: absolute; left: 18px; right: 18px; top: 50%; height: 5px; border-radius: 3px; background: #f87171; }
.v-steps div { display: flex; align-items: center; gap: 26px; font-size: 44px; font-weight: 750; padding: 22px 28px;
  border-radius: 22px; background: var(--panel); border: 2px solid var(--line); }
.v-steps b, .v-check b { flex: none; width: 72px; height: 72px; border-radius: 20px; display: grid; place-items: center;
  font-size: 36px; color: #fff; background: var(--grad); }
.v-check div { display: flex; align-items: center; gap: 24px; font-size: 42px; font-weight: 650; padding: 14px 0;
  border-bottom: 2px solid var(--line); }
.v-check b { background: transparent; border: 3px solid var(--line); color: var(--accent2); }
.v-check b.on { background: var(--accent2); border-color: transparent; color: #fff; }
.v-stat .big { font-size: 230px; line-height: .9; font-weight: 900; letter-spacing: -0.04em; display: flex; align-items: baseline;
  background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
.v-stat .big small { font-size: 120px; }
.v-stat .label { font-size: 48px; font-weight: 800; }
.v-stat .note { font-size: 34px; color: var(--muted); }
.v-bars .row { display: grid; grid-template-columns: 230px 1fr; align-items: center; gap: 20px; font-size: 34px; font-weight: 700; }
.v-bars .track { height: 64px; border-radius: 14px; background: var(--panel); border: 2px solid var(--line); overflow: hidden; }
.v-bars .fill { height: 100%; border-radius: 12px; background: var(--grad); display: flex; align-items: center;
  justify-content: flex-end; padding-right: 18px; color: #fff; font-size: 30px; font-weight: 800; }
.v-donut { flex-direction: row; align-items: center; gap: 44px; }
.v-donut .ring { --to: 0; width: 330px; height: 330px; flex: none; border-radius: 50%; display: grid; place-items: center;
  background: conic-gradient(var(--accent2) calc(var(--p) * 1%), var(--panel) 0); }
.v-donut .ring span { width: 238px; height: 238px; border-radius: 50%; background: var(--bg); display: grid; place-items: center;
  font-size: 84px; font-weight: 900; }
.v-donut .side { font-size: 42px; font-weight: 700; line-height: 1.25; }
.v-donut .side small { display: block; margin-top: 12px; font-size: 32px; color: var(--muted); font-weight: 500; }
.v-compare { flex-direction: row; gap: 20px; }
.v-compare.stack { flex-direction: column; }
.v-compare .side { flex: 1; padding: 28px; border-radius: 26px; border: 3px solid var(--line); background: var(--panel); }
.v-compare .side.bad { border-color: rgba(248,113,113,.7); }
.v-compare .side.good { border-color: var(--accent2); }
.v-compare h4 { font-size: 30px; font-weight: 900; letter-spacing: .05em; margin-bottom: 14px; display: flex; align-items: center; gap: 10px; }
.v-compare .bad h4 { color: #f87171; } .v-compare .good h4 { color: var(--accent2); }
.v-compare p { font-size: 34px; line-height: 1.3; font-weight: 600; margin-top: 10px; }
.v-code, .v-term { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 31px; line-height: 1.55; padding: 30px 32px;
  border-radius: 24px; background: #020617; color: #e2e8f0; border: 2px solid var(--line); gap: 2px; }
.v-code div { white-space: pre-wrap; } .v-code .hl { color: #7dd3fc; background: rgba(56,189,248,.16); border-radius: 6px; }
.v-code .dim { color: #64748b; }
.v-term div { display: flex; gap: 18px; }
.v-term b { flex: none; padding: 0 10px; border-radius: 8px; font-weight: 700; }
.v-term .ok b { color: #6ee7b7; background: rgba(52,211,153,.14); } .v-term .bad { color: #fecaca; }
.v-term .bad b { color: #fff; background: #b91c1c; } .v-term .info b { color: #7dd3fc; background: rgba(56,189,248,.14); }
.v-flow { gap: 0; }
.v-flow .node { display: flex; align-items: center; gap: 22px; padding: 22px 28px; border-radius: 22px; font-size: 40px; font-weight: 750;
  background: var(--panel); border: 2px solid var(--line); }
.v-flow .node .icon { color: var(--accent); flex: none; }
.v-flow svg.arrow { display: block; margin-left: 58px; }
.v-time { gap: 0; }
.v-time div { position: relative; padding: 0 0 26px 58px; border-left: 4px solid var(--line); margin-left: 18px; }
.v-time div::before { content: ''; position: absolute; left: -16px; top: 6px; width: 28px; height: 28px; border-radius: 50%; background: var(--grad); }
.v-time b { display: block; font-size: 30px; font-weight: 900; letter-spacing: .05em; color: var(--accent); }
.v-time span { font-size: 40px; font-weight: 650; }
.v-decode .head, .v-decode .row { display: grid; grid-template-columns: 1fr 64px 1fr; align-items: center; gap: 10px; }
.v-decode .head { font-size: 26px; font-weight: 900; letter-spacing: .08em; color: var(--muted); }
.v-decode .row { padding: 18px 0; border-top: 2px solid var(--line); }
.v-decode .say { font-size: 34px; font-weight: 600; color: var(--muted); font-style: italic; }
.v-decode .mean { font-size: 36px; font-weight: 800; }
.v-decode .row .icon { color: var(--accent2); justify-self: center; }
.v-quote { padding: 10px 0; }
.v-quote .mark { font-size: 220px; line-height: .5; font-weight: 900; height: 110px; background: var(--grad);
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.v-quote p { font-size: 60px; line-height: 1.15; font-weight: 800; letter-spacing: -0.02em; }
.v-quote small { font-size: 32px; color: var(--muted); font-weight: 600; }
.v-story { padding: 40px 44px; border-radius: 30px; background: var(--panel); border: 2px solid var(--line); gap: 22px;
  box-shadow: 0 30px 70px rgba(0,0,0,.18); }
.v-story .when { font-size: 28px; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); }
.v-story p { font-size: 42px; line-height: 1.3; font-weight: 600; font-style: italic; }
.v-story small { font-size: 30px; color: var(--muted); font-weight: 600; }
.v-matrix { display: grid; gap: 10px; font-size: 28px; font-weight: 800; }
.v-matrix .h { text-align: center; color: var(--muted); letter-spacing: .04em; }
.v-matrix .r { display: flex; align-items: center; font-size: 32px; }
.v-matrix .c { height: 74px; border-radius: 14px; background: var(--panel); border: 2px dashed var(--line); display: grid; place-items: center; }
.v-matrix .c.on { background: var(--grad); border: none; color: #fff; }
.v-search .bar { display: flex; align-items: center; gap: 22px; padding: 28px 36px; border-radius: 999px; background: #fff;
  color: #0f172a; font-size: 44px; font-weight: 600; box-shadow: 0 20px 50px rgba(2,6,23,.25); }
.v-search .res { height: 26px; border-radius: 13px; background: var(--panel); border: 2px solid var(--line); }
.v-icons { display: grid; grid-template-columns: repeat(var(--cols), 1fr); gap: 18px; }
.v-icons div { display: flex; flex-direction: column; align-items: flex-start; gap: 16px; padding: 26px; border-radius: 26px;
  background: var(--panel); border: 2px solid var(--line); font-size: 34px; font-weight: 750; line-height: 1.2; }
.v-icons .icon { color: var(--accent); }
.v-image img { width: 100%; max-height: 640px; object-fit: cover; border-radius: 30px; box-shadow: 0 30px 70px rgba(2,6,23,.35); }
.v-image.circle img { width: 520px; height: 520px; border-radius: 50%; align-self: center; }
.v-image.tilt img { transform: rotate(-3deg); border: 14px solid #fff; }
.v-image small { font-size: 30px; color: var(--muted); font-weight: 600; }
.v-svg svg { width: 100%; height: auto; max-height: 700px; }
"""


def _e(value) -> str:
    return escape(str(value))


def chips(v: dict) -> str:
    strike = v.get("strike", False)
    line = '<i class="strike-line" style="--i:{i}"></i>' if strike else ""
    items = "".join(f'<span style="--i:{i}">{_e(t)}{line.format(i=i + 2)}</span>' for i, t in enumerate(v["items"]))
    return f'<div class="v v-chips seq {"strike" if strike else ""}">{items}</div>'


def steps(v: dict) -> str:
    rows = "".join(f'<div style="--i:{i}"><b>{i + 1}</b>{_e(t)}</div>' for i, t in enumerate(v["items"]))
    return f'<div class="v v-steps seq">{rows}</div>'


def checklist(v: dict) -> str:
    done = v.get("done", len(v["items"]))
    rows = "".join(
        f'<div><b class="{"on pop" if i < done else ""}" style="--i:{i}">{"✓" if i < done else ""}</b>{_e(t)}</div>'
        for i, t in enumerate(v["items"]))
    return f'<div class="v v-check">{rows}</div>'


def stat(v: dict) -> str:
    value = str(v["value"])
    number = (f'<span class="count" style="--to:{int(value)}"></span>' if value.isdigit() and int(value) < 100000
              else _e(value))
    big = f'<div class="big"><small>{_e(v.get("prefix", ""))}</small>{number}<small>{_e(v.get("suffix", ""))}</small></div>'
    note = f'<div class="note">{_e(v["note"])}</div>' if v.get("note") else ""
    return f'<div class="v v-stat">{big}<div class="label">{_e(v["label"])}</div>{note}</div>'


def bars(v: dict) -> str:
    top = max(float(value) for _, value in v["items"]) or 1
    suffix = v.get("suffix", "")
    rows = "".join(
        f'<div class="row"><span>{_e(label)}</span><div class="track"><div class="fill grow" '
        f'style="--i:{i};width:{max(12, float(value) / top * 100):.0f}%">{_e(value)}{_e(suffix)}</div></div></div>'
        for i, (label, value) in enumerate(v["items"]))
    return f'<div class="v v-bars">{rows}</div>'


def donut(v: dict) -> str:
    value = max(0, min(100, int(v["value"])))
    sub = f'<small>{_e(v["note"])}</small>' if v.get("note") else ""
    return (f'<div class="v v-donut"><div class="ring" style="--to:{value}"><span>{value}%</span></div>'
            f'<div class="side">{_e(v["label"])}{sub}</div></div>')


def compare(v: dict) -> str:
    def side(data: dict, tone: str, mark: str, i: int) -> str:
        lines = "".join(f"<p>{_e(t)}</p>" for t in data.get("lines", []))
        return f'<div class="side {tone}" style="--i:{i}"><h4>{mark} {_e(data["title"])}</h4>{lines}</div>'
    longest = max(len(t) for t in v["left"].get("lines", []) + v["right"].get("lines", []) + [""])
    layout = "stack" if v.get("stack") or longest > 34 else ""
    return (f'<div class="v v-compare seq {layout}">{side(v["left"], "bad", "✗", 0)}'
            f'{side(v["right"], "good", "✓", 1)}</div>')


def code(v: dict) -> str:
    marked = set(v.get("highlight", []))
    rows = "".join(
        f'<div class="type {"hl" if i in marked else ""}" style="--i:{i}">{_e(line) or " "}</div>'
        for i, line in enumerate(v["lines"]))
    return f'<div class="v v-code">{rows}</div>'


def terminal(v: dict) -> str:
    rows = "".join(
        f'<div class="{_e(tone)}" style="--i:{i}"><b>{_e(tag)}</b>{_e(text)}</div>'
        for i, (tag, text, tone) in enumerate(v["lines"]))
    return f'<div class="v v-term seq">{rows}<div class="cursor" style="--i:0">▍</div></div>'


def flow(v: dict) -> str:
    arrow = ('<svg class="arrow" width="40" height="56" viewBox="0 0 40 56"><path class="dash" d="M20 0v42" '
             'stroke="var(--accent)" stroke-width="5" fill="none"/><path d="M8 40l12 14 12-14" fill="none" '
             'stroke="var(--accent)" stroke-width="5" stroke-linecap="round"/></svg>')
    parts = []
    for i, item in enumerate(v["items"]):
        label, name = (item if isinstance(item, list) else [item, None])
        glyph = icon(name, 52) if name else ""
        parts.append(f'<div class="node" style="--i:{i}">{glyph}{_e(label)}</div>')
    return f'<div class="v v-flow seq">{arrow.join(parts)}</div>'


def timeline(v: dict) -> str:
    rows = "".join(f'<div style="--i:{i}"><b>{_e(when)}</b><span>{_e(what)}</span></div>'
                   for i, (when, what) in enumerate(v["items"]))
    return f'<div class="v v-time seq">{rows}</div>'


def decode(v: dict) -> str:
    head = (f'<div class="head"><span>{_e(v.get("left_title", "THEY SAY"))}</span><span></span>'
            f'<span>{_e(v.get("right_title", "THEY MEAN"))}</span></div>')
    rows = "".join(
        f'<div class="row" style="--i:{i}"><span class="say">“{_e(say)}”</span>{icon("bolt", 44)}'
        f'<span class="mean">{_e(mean)}</span></div>' for i, (say, mean) in enumerate(v["rows"]))
    return f'<div class="v v-decode seq">{head}{rows}</div>'


def quote(v: dict) -> str:
    who = f'<small>{_e(v["who"])}</small>' if v.get("who") else ""
    return f'<div class="v v-quote seq"><div class="mark">“</div><p style="--i:1">{_e(v["text"])}</p>{who}</div>'


def story(v: dict) -> str:
    who = f'<small style="--i:2">{_e(v["who"])}</small>' if v.get("who") else ""
    return (f'<div class="v v-story seq"><div class="when" style="--i:0">{_e(v["when"])}</div>'
            f'<p style="--i:1">{_e(v["text"])}</p>{who}</div>')


def matrix(v: dict) -> str:
    cols, rows, filled = v["cols"], v["rows"], v.get("filled", len(v["rows"]))
    cells = ['<div></div>'] + [f'<div class="h">{_e(c)}</div>' for c in cols]
    for r, row in enumerate(rows):
        cells.append(f'<div class="r">{_e(row)}</div>')
        cells.extend(f'<div class="c {"on pop" if r < filled else ""}" style="--i:{r + k * .3:.1f}">'
                     f'{"✓" if r < filled else ""}</div>' for k in range(len(cols)))
    return (f'<div class="v v-matrix" style="grid-template-columns:220px repeat({len(cols)},1fr)">'
            f'{"".join(cells)}</div>')


def search(v: dict) -> str:
    results = "".join(f'<div class="res" style="--i:{i + 1};width:{w}%"></div>'
                      for i, w in enumerate([82, 100, 64, 90, 55][:v.get("results", 4)]))
    return (f'<div class="v v-search seq"><div class="bar" style="--i:0">{icon("search", 50, "#0f172a", 2.6)}'
            f'<span class="type" style="--i:0">{_e(v["query"])}</span></div>{results}</div>')


def icons(v: dict) -> str:
    items = v["items"]
    cols = v.get("cols", 2 if len(items) <= 4 else 3)
    cards = "".join(f'<div class="pop" style="--i:{i}">{icon(name, 66)}{_e(label)}</div>'
                    for i, (name, label) in enumerate(items))
    return f'<div class="v v-icons" style="--cols:{cols}">{cards}</div>'


def image(v: dict) -> str:
    caption = f'<small>{_e(v["caption"])}</small>' if v.get("caption") else ""
    return (f'<div class="v v-image {_e(v.get("shape", ""))}"><img src="{_e(v["src"])}" alt="{_e(v.get("alt", ""))}">'
            f'{caption}</div>')


UNSAFE_SVG = re.compile(r"<\s*(script|foreignObject|iframe|image)|\son\w+\s*=|javascript:|href\s*=\s*['\"]?http",
                        re.IGNORECASE)


def svg(v: dict) -> str:
    markup = v["markup"].strip()
    if not markup.startswith("<svg") or UNSAFE_SVG.search(markup):
        raise ValueError("svg visual must be plain inline <svg> art: no scripts, event handlers or external links")
    return f'<div class="v v-svg">{markup}</div>'


VISUALS = {
    "chips": chips, "steps": steps, "checklist": checklist, "stat": stat, "bars": bars, "donut": donut,
    "compare": compare, "code": code, "terminal": terminal, "flow": flow, "timeline": timeline, "decode": decode,
    "quote": quote, "story": story, "matrix": matrix, "search": search, "icons": icons, "image": image, "svg": svg,
}

ICON_NAMES = sorted(ICONS)


def render_visual(v: dict | None) -> str:
    if not v:
        return ""
    return VISUALS[v["type"]](v)
