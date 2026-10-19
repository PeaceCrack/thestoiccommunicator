"""Art directions, colour palettes and type pairings for The Stoic Communicator.

Every post rolls a theme (which surface each slide role sits on, and its background art),
a palette (the colours those surfaces are built from) and a font pairing. Mixing the three
keeps the feed varied while the motto, voice and marks stay constant.
"""

THEMES = {
    "temple": {
        "mood": "dark temple at night: candle glows, sacred geometry, marble paper slides between",
        "roles": {"cover": "night", "stake": "paper", "content": "paper", "recap": "night", "cta": "gradient"},
        "art": {"night": ["glow", "geometry", "rings"], "paper": ["marble", "dots", "none"],
                "gradient": ["laurel", "rings"]},
        "headline": "heavy",
    },
    "codex": {
        "mood": "ancient manuscript turned magazine: paper, ink, Greek-key rules, huge numerals",
        "roles": {"cover": "paper", "stake": "ink", "content": "paper", "recap": "paper", "cta": "ink"},
        "art": {"paper": ["rules", "marble", "meander"], "ink": ["meander", "glow"]},
        "headline": "tight",
    },
    "academy": {
        "mood": "Plato's academy: stone surface, geometer's grid, compass construction lines",
        "roles": {"cover": "stone", "stake": "stone", "content": "stone", "recap": "stone", "cta": "gradient"},
        "art": {"stone": ["grid", "geometry"], "gradient": ["geometry", "rings"]},
        "headline": "heavy",
    },
    "colosseum": {
        "mood": "arena drama: near-black, column silhouettes, hard light, a gladiator's poster",
        "roles": {"cover": "night", "stake": "ink", "content": "night", "recap": "ink", "cta": "gradient"},
        "art": {"night": ["columns", "glow", "rings"], "ink": ["columns", "meander"], "gradient": ["columns"]},
        "headline": "heavy",
    },
    "oracle": {
        "mood": "Delphi at dawn: full-bleed gradients with floating cards, laurel arcs",
        "roles": {"cover": "gradient", "stake": "gradient", "content": "card", "recap": "gradient", "cta": "night"},
        "art": {"gradient": ["laurel", "waves", "rings"], "card": ["glow"], "night": ["glow", "geometry"]},
        "headline": "heavy",
    },
    "fresco": {
        "mood": "weathered fresco print: grain, overlapping translucent shapes, bold pigment",
        "roles": {"cover": "paper", "stake": "paper", "content": "paper", "recap": "paper", "cta": "gradient"},
        "art": {"paper": ["shapes", "shapes", "marble"], "gradient": ["shapes"]},
        "headline": "tight",
    },
}

DEFAULT_THEME = "temple"

# dark = night background, ink = text on paper, paper = light background, a1/a2 = the two
# accents (deep for light surfaces, light for dark ones), mid = the middle of gradients.
PALETTES = {
    "imperial-gold": dict(dark="#160c26", ink="#1d1230", muted="#6b5f80", paper="#f6f1e7", a1="#9a6b12",
                          a1_light="#f2c95c", a2="#7b1e3a", a2_light="#e58aa3", mid="#4a1f5c"),
    "marble-bronze": dict(dark="#1b1a18", ink="#1b1a18", muted="#6f6a61", paper="#f3f0ea", a1="#8f4f24",
                          a1_light="#e0a36b", a2="#2f5d62", a2_light="#8cc7c4", mid="#5a4632"),
    "obsidian-ember": dict(dark="#0c0b0a", ink="#151311", muted="#7a6f66", paper="#f5efe8", a1="#c2410c",
                           a1_light="#ff8a4c", a2="#a16207", a2_light="#facc15", mid="#7c2d12"),
    "aegean-sand": dict(dark="#081a2c", ink="#0b2238", muted="#5b6f82", paper="#f4efe4", a1="#1d6fb8",
                        a1_light="#7cc4ff", a2="#a8742c", a2_light="#f0c987", mid="#164e7a"),
    "olive-grove": dict(dark="#151b10", ink="#1c2416", muted="#66705a", paper="#f2f0e3", a1="#5f6f1f",
                        a1_light="#c5d46a", a2="#9b6a1b", a2_light="#f1d18a", mid="#3f4d1a"),
    "bloodstone": dict(dark="#120707", ink="#1a0b0b", muted="#7b6060", paper="#f3ebe0", a1="#a3161f",
                       a1_light="#ff5a5f", a2="#7a6448", a2_light="#e9dcc7", mid="#5e0f15"),
    "verdigris": dict(dark="#0b1716", ink="#102120", muted="#5c7472", paper="#eef3ef", a1="#1f7a6c",
                      a1_light="#6fe0cc", a2="#9c5e28", a2_light="#e8a565", mid="#145a52"),
    "parchment-oxblood": dict(dark="#1f150d", ink="#2a1f14", muted="#76654f", paper="#efe5cf", a1="#7a1f1f",
                              a1_light="#e0786c", a2="#946b17", a2_light="#e8c25a", mid="#5c2a12"),
    "midnight-ivory": dict(dark="#0a0e18", ink="#0f1422", muted="#64708a", paper="#f7f4ec", a1="#8a6d1c",
                           a1_light="#e9cf7a", a2="#3a4a7a", a2_light="#aab8f0", mid="#24305a"),
    "electric-stoic": dict(dark="#07070c", ink="#0d0d16", muted="#6b6b85", paper="#f1f1f6", a1="#4338ca",
                           a1_light="#7dd3fc", a2="#be185d", a2_light="#f472b6", mid="#3b1d6e"),
    "emerald-empire": dict(dark="#06140f", ink="#0a1f17", muted="#5a7268", paper="#f1f4ee", a1="#047857",
                           a1_light="#34d399", a2="#a67c00", a2_light="#ffd65a", mid="#065f46"),
    "terracotta-agora": dict(dark="#1e0f0a", ink="#26140d", muted="#7d6255", paper="#f6ece2", a1="#b4471f",
                             a1_light="#ff9b6b", a2="#35607a", a2_light="#93c8e8", mid="#7a2e14"),
}

DEFAULT_PALETTE = "imperial-gold"

# display = headline face, body = text face, caps_em = average width of the display face's
# capitals (used to size headlines so the longest word fits), weight = headline weight.
FONT_PAIRS = {
    "cinzel": dict(display="Cinzel", body="Lato", caps_em=0.96, weight=900),
    "playfair": dict(display="Playfair Display", body="Inter", caps_em=0.76, weight=900),
    "bodoni": dict(display="Bodoni Moda", body="Manrope", caps_em=0.78, weight=900),
    "dm-serif": dict(display="DM Serif Display", body="DM Sans", caps_em=0.72, weight=400),
    "bebas": dict(display="Bebas Neue", body="Inter", caps_em=0.46, weight=400),
    "anton": dict(display="Anton", body="Source Serif 4", caps_em=0.56, weight=400),
}

DEFAULT_FONTS = "cinzel"

# Google Fonts axis spec per family. Asking for a weight a family lacks makes the request fail.
FONT_AXES = {
    "Cinzel": "wght@400..900", "Playfair Display": "wght@400..900", "Bodoni Moda": "wght@400..900",
    "DM Serif Display": "", "Bebas Neue": "", "Anton": "",
    "Lato": "wght@400;700;900", "Inter": "wght@400..900", "Manrope": "wght@400..800",
    "DM Sans": "wght@400..900", "Source Serif 4": "wght@400..900",
}


def surfaces(c: dict) -> dict:
    return {
        "night": dict(bg=c["dark"], fg="#ffffff", muted="rgba(255,255,255,.72)", accent=c["a1_light"],
                      accent2=c["a2_light"], panel="rgba(255,255,255,.06)", line="rgba(255,255,255,.14)",
                      card="#ffffff", card_fg=c["dark"],
                      grad=f"linear-gradient(100deg,{c['a1_light']},{c['a2_light']})"),
        "paper": dict(bg=c["paper"], fg=c["ink"], muted=c["muted"], accent=c["a1"], accent2=c["a2"],
                      panel="#ffffff", line="rgba(0,0,0,.1)", card=c["dark"], card_fg="#ffffff",
                      grad=f"linear-gradient(100deg,{c['a1']},{c['a2']})"),
        "ink": dict(bg=c["ink"], fg=c["paper"], muted="rgba(255,255,255,.62)", accent=c["a1_light"],
                    accent2=c["a2_light"], panel="rgba(255,255,255,.05)", line="rgba(255,255,255,.12)",
                    card=c["paper"], card_fg=c["ink"],
                    grad=f"linear-gradient(100deg,{c['a1_light']},{c['a2_light']})"),
        "stone": dict(bg=f"linear-gradient(170deg,{c['mid']},{c['dark']})", fg="#ffffff",
                      muted="rgba(255,255,255,.7)", accent=c["a1_light"], accent2=c["a2_light"],
                      panel="rgba(255,255,255,.07)", line="rgba(255,255,255,.2)", card=c["paper"],
                      card_fg=c["ink"], grad=f"linear-gradient(100deg,{c['paper']},{c['a1_light']})"),
        "gradient": dict(bg=f"linear-gradient(150deg,{c['a1']} 0%,{c['mid']} 50%,{c['a2']} 100%)", fg="#ffffff",
                         muted="rgba(255,255,255,.88)", accent="#ffffff", accent2=c["a1_light"],
                         panel="rgba(255,255,255,.14)", line="rgba(255,255,255,.3)", card="#ffffff",
                         card_fg=c["dark"], grad=f"linear-gradient(100deg,#ffffff,{c['a1_light']})"),
        "card": dict(bg=f"linear-gradient(160deg,{c['a1']},{c['a2']})", fg=c["ink"], muted=c["muted"],
                     accent=c["a1"], accent2=c["a2"], panel=c["paper"], line="rgba(0,0,0,.1)", card=c["dark"],
                     card_fg="#ffffff", grad=f"linear-gradient(100deg,{c['a1']},{c['a2']})"),
    }


SURFACES = tuple(surfaces(PALETTES[DEFAULT_PALETTE]))


def surface_css(name: str, colors: dict) -> str:
    v = surfaces(colors)[name]
    return (f"--bg:{v['bg']};--fg:{v['fg']};--muted:{v['muted']};--accent:{v['accent']};--accent2:{v['accent2']};"
            f"--panel:{v['panel']};--line:{v['line']};--card:{v['card']};--card-fg:{v['card_fg']};--grad:{v['grad']};")


def styled_brand(brand: dict, post: dict) -> dict:
    """The brand with this post's palette and fonts applied. Returns a new dict."""
    fonts = FONT_PAIRS[post.get("fonts", DEFAULT_FONTS)]
    return {**brand, "colors": PALETTES[post.get("palette", DEFAULT_PALETTE)], "font": fonts["body"],
            "display_font": fonts["display"], "caps_em": fonts["caps_em"], "display_weight": fonts["weight"]}
