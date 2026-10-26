"""Burned-in, word-by-word captions as an ASS subtitle file for ffmpeg's libass.

Words are grouped into short phrases (most viewers watch muted). The phrase stays on screen
while it is spoken and the current word lights up in the accent colour and grows slightly,
the karaoke style that holds attention on Reels and Shorts.
"""

from dataclasses import dataclass

from .voice import Word

MAX_WORDS = 3
MAX_CHARS = 18
CAPTION_Y = 1450  # centre of the caption band, below the card and above the app's UI
# System fonts libass can find on macOS. The brief picks a style, then a font that suits it.
CAPTION_FONTS = ("Arial Black", "Impact", "Futura", "Avenir Next Condensed")
SERIF_FONTS = ("Georgia", "Didot", "Baskerville")
# karaoke: the phrase, current word lit. single: one big word at a time (the "talking-head" look).
# pill: the phrase, current word on a solid accent block.
CAPTION_STYLES = ("karaoke", "single", "pill")
STYLE_FONTS = {"karaoke": CAPTION_FONTS, "single": SERIF_FONTS, "pill": CAPTION_FONTS}


@dataclass(frozen=True)
class Timed:
    start: float
    end: float
    text: str


def ass_color(hex_color: str) -> str:
    """#RRGGBB -> &H00BBGGRR (ASS colours are BGR)."""
    h = hex_color.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def _clock(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def phrases(words: list[Timed]) -> list[list[Timed]]:
    groups, current = [], []
    for word in words:
        too_long = len(" ".join(w.text for w in [*current, word])) > MAX_CHARS
        if current and (len(current) >= MAX_WORDS or too_long or current[-1].text[-1:] in ".,!?;:"):
            groups.append(current)
            current = []
        current.append(word)
    if current:
        groups.append(current)
    return groups


def _escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def _cue_text(group: list[Timed], k: int, style: str, hot: str, white: str) -> str:
    if style == "single":
        word = _escape(group[k].text.rstrip(".,;:"))  # as spoken, like the talking-head look
        return "{\\fscx70\\fscy70\\t(0,110,\\fscx100\\fscy100)}" + word
    parts = []
    for j, other in enumerate(group):
        text = _escape(other.text.upper().rstrip(".,;:"))
        if j != k:
            parts.append(text)
        elif style == "pill":
            parts.append(f"{{\\3c{hot[3:]}\\bord18\\shad0}}{text}{{\\3c&H000000&\\bord7\\shad3}}")
        else:
            parts.append(f"{{{hot}\\fscx112\\fscy112}}{text}{{{white}\\fscx100\\fscy100}}")
    pop = "{\\t(0,90,\\fscx104\\fscy104)\\t(90,180,\\fscx100\\fscy100)}" if k == 0 else ""
    return pop + " ".join(parts)


def build_ass(words: list[Timed], accent: str, font: str, style: str = "karaoke") -> str:
    """One dialogue event per spoken word, drawn in the chosen caption style."""
    if style not in CAPTION_STYLES:
        raise ValueError(f"caption style must be one of {CAPTION_STYLES}")
    size = 112 if style == "single" else 84
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Cap,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,7,3,5,60,60,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    hot = "\\1c&H" + ass_color(accent)[4:] + "&"
    white = "\\1c&HFFFFFF&"
    cues = []  # (start, end, text): one per spoken word, the phrase with that word lit
    for group in phrases(words):
        for k, word in enumerate(group):
            end = group[k + 1].start if k + 1 < len(group) else word.end + 0.18
            if style == "single":
                end = min(end, word.end + 0.25)
            cues.append((word.start, end, _cue_text(group, k, style, hot, white)))
    # Captions share one position, so two cues on screen at once would print over each other.
    events = []
    for i, (start, end, text) in enumerate(cues):
        if i + 1 < len(cues):
            end = min(end, cues[i + 1][0])
        if end - start < 0.02:
            continue
        events.append(f"Dialogue: 0,{_clock(start)},{_clock(end)},Cap,,0,0,0,,{{\\an5\\pos(540,{CAPTION_Y})}}{text}")
    return header + "\n".join(events) + "\n"


def _bare(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def punctuate(words: tuple[Word, ...], script: str) -> list[Word]:
    """edge-tts word events drop punctuation. Walk the script's tokens in order to restore the
    trailing punctuation each spoken word had, so phrases break where sentences do."""
    tokens, k, out = script.split(), 0, []
    for word in words:
        bare, text = _bare(word.text), word.text
        for j in range(k, min(k + 4, len(tokens))):
            if _bare(tokens[j]).startswith(bare) and bare:
                tail = tokens[j][len(tokens[j].rstrip(".,!?;:")):]
                text, k = word.text + (tail if _bare(tokens[j]) == bare else ""), j + 1
                break
        out.append(Word(word.start, word.end, text))
    return out


def shift(words: list[Word], offset: float) -> list[Timed]:
    """Move a beat's words onto the reel timeline. The last word ends its phrase."""
    timed = [Timed(w.start + offset, w.end + offset, w.text) for w in words]
    if timed and timed[-1].text[-1:] not in ".,!?;:":
        timed[-1] = Timed(timed[-1].start, timed[-1].end, timed[-1].text + ".")
    return timed
