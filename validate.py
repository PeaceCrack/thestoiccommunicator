"""Checks a post file (carousel, reel, captions, YouTube metadata) before anything renders."""

from pathlib import Path

from history import repeats
from slides.theme import FONT_PAIRS, PALETTES, THEMES
from slides.visuals import VISUALS, render_visual

ROOT = Path(__file__).resolve().parent
MIN_SLIDES = 6
MAX_SLIDES = 12
MAX_ANIMATED = 3
COVER_MAX_WORDS = 6
HEADLINE_MIN_WORDS = 2
HEADLINE_MAX_WORDS = 8
BODY_MAX_WORDS = 25
CAPTION_MAX_CHARS = 2200
CAPTION_MAX_HASHTAGS = 5
KINDS = {"cover", "stake", "content", "step", "recap", "cta"}
MIDDLE_KINDS = {"stake", "content", "step"}


def _words(text: str) -> int:
    return len(text.split())


def _check_visual(label: str, visual: dict) -> list[str]:
    kind = visual.get("type")
    if kind not in VISUALS:
        return [f"{label}: unknown visual {kind!r}. Use one of: {', '.join(sorted(VISUALS))}"]
    if kind == "image":
        src = ROOT / visual.get("src", "")
        if not str(visual.get("src", "")).startswith("assets/") or not src.is_file():
            return [f"{label}: image src must be an existing file under assets/"]
    try:
        render_visual(visual)
    except (KeyError, TypeError, ValueError, IndexError) as err:
        return [f"{label}: {kind} visual is missing or has a bad field ({err})"]
    return []


def _check_slide(index: int, slide: dict) -> list[str]:
    label = f"slide {index + 1}"
    kind = slide.get("kind")
    if kind not in KINDS:
        return [f"{label}: unknown kind {kind!r}"]

    errors = []
    headline = slide.get("headline", "")
    body = slide.get("body", "")

    if kind == "cover":
        if not headline:
            errors.append(f"{label}: cover needs a headline")
        elif _words(headline) > COVER_MAX_WORDS:
            errors.append(f"{label}: cover is {_words(headline)} words, max {COVER_MAX_WORDS}")
    if kind in ("step", "content") and not HEADLINE_MIN_WORDS <= _words(headline) <= HEADLINE_MAX_WORDS:
        errors.append(
            f"{label}: headline is {_words(headline)} words, want {HEADLINE_MIN_WORDS}-{HEADLINE_MAX_WORDS}"
        )
    if _words(body) > BODY_MAX_WORDS:
        errors.append(f"{label}: body is {_words(body)} words, max {BODY_MAX_WORDS}. Split it")
    if kind == "recap" and not (slide.get("items") or slide.get("visual")):
        errors.append(f"{label}: recap needs items or a visual")
    if slide.get("visual"):
        errors.extend(_check_visual(label, slide["visual"]))
    return errors


def validate_post(post: dict) -> list[str]:
    """Return a list of human-readable problems. Empty means the post is good to render."""
    slides = post.get("slides", [])
    errors = []

    if not MIN_SLIDES <= len(slides) <= MAX_SLIDES:
        errors.append(f"{len(slides)} slides, want {MIN_SLIDES}-{MAX_SLIDES}")
    if slides and slides[0].get("kind") != "cover":
        errors.append("first slide must be the cover")
    if slides and slides[-1].get("kind") != "cta":
        errors.append("last slide must be the CTA")
    if post.get("theme") not in THEMES:
        errors.append(f"unknown theme {post.get('theme')!r}. Use one of: {', '.join(THEMES)}")
    animated = sum(1 for s in slides if s.get("animate"))
    if animated > MAX_ANIMATED:
        errors.append(f"{animated} animated slides, max {MAX_ANIMATED}")

    if post.get("theme"):
        middle = [s for s in slides if s.get("kind") in MIDDLE_KINDS]
        with_visual = sum(1 for s in middle if s.get("visual"))
        if middle and with_visual * 2 < len(middle):
            errors.append(f"only {with_visual} of {len(middle)} middle slides have a visual, want at least half")

    for index, slide in enumerate(slides):
        errors.extend(_check_slide(index, slide))

    caption = post.get("caption", "")
    if not caption:
        errors.append("caption is empty")
    if len(caption) > CAPTION_MAX_CHARS:
        errors.append(f"caption is {len(caption)} chars, max {CAPTION_MAX_CHARS}")
    hashtags = [w for w in caption.split() if w.startswith("#")]
    if len(hashtags) > CAPTION_MAX_HASHTAGS:
        errors.append(f"{len(hashtags)} hashtags, max {CAPTION_MAX_HASHTAGS}")
    if not post.get("alt_text"):
        errors.append("alt_text is missing for the cover")
    if post.get("palette") not in PALETTES:
        errors.append(f"unknown palette {post.get('palette')!r}. Use one of: {', '.join(PALETTES)}")
    if post.get("fonts") not in FONT_PAIRS:
        errors.append(f"unknown fonts {post.get('fonts')!r}. Use one of: {', '.join(FONT_PAIRS)}")
    if post.get("pillar") not in PILLARS:
        errors.append(f"pillar must be one of {', '.join(PILLARS)}")
    for field in ("topic", "philosopher", "story"):
        if not post.get(field):
            errors.append(f"{field} is missing (it is how history.py stops repeats)")
    for fact in post.get("facts", []):
        if not fact.get("source"):
            errors.append(f"fact {fact.get('claim', '')[:40]!r} needs a source")
    errors.extend(repeats(post))
    return errors


PILLARS = ("think", "speak", "influence")
BEAT_KINDS = {"hook", "story", "fact", "lesson", "quote", "takeaway", "cta"}
MIN_BEATS, MAX_BEATS = 6, 14
BEAT_MAX_WORDS = 34
REEL_MIN_WORDS, REEL_MAX_WORDS = 60, 125   # about 28-58 s of narration
REEL_HEADLINE_MAX_WORDS = 7
YT_TITLE_MAX = 100
YT_DESC_MAX = 5000


def validate_reel(post: dict) -> list[str]:
    """Rules for the reel script and the YouTube Short metadata."""
    reel = post.get("reel") or {}
    beats = reel.get("beats", [])
    errors = []
    if not MIN_BEATS <= len(beats) <= MAX_BEATS:
        errors.append(f"{len(beats)} reel beats, want {MIN_BEATS}-{MAX_BEATS}")
    if beats and beats[0].get("kind") != "hook":
        errors.append("first reel beat must be the hook")
    if beats and beats[-1].get("kind") != "cta":
        errors.append("last reel beat must be the cta")
    total = 0
    for index, beat in enumerate(beats, start=1):
        label = f"beat {index}"
        if beat.get("kind") not in BEAT_KINDS:
            errors.append(f"{label}: unknown kind {beat.get('kind')!r}")
        words = _words(beat.get("voice", ""))
        total += words
        if not words:
            errors.append(f"{label}: voice line is empty")
        if words > BEAT_MAX_WORDS:
            errors.append(f"{label}: voice is {words} words, max {BEAT_MAX_WORDS}. Split the beat")
        if _words(beat.get("headline", "")) > REEL_HEADLINE_MAX_WORDS:
            errors.append(f"{label}: headline over {REEL_HEADLINE_MAX_WORDS} words")
        if _words(beat.get("body", "")) > BODY_MAX_WORDS:
            errors.append(f"{label}: body over {BODY_MAX_WORDS} words")
        if beat.get("visual"):
            errors.extend(_check_visual(label, beat["visual"]))
        if "—" in beat.get("voice", "") + beat.get("headline", ""):
            errors.append(f"{label}: no em dashes")
    if beats and not REEL_MIN_WORDS <= total <= REEL_MAX_WORDS:
        errors.append(f"reel narration is {total} words, want {REEL_MIN_WORDS}-{REEL_MAX_WORDS} (30-58 s)")
    if not post.get("reel_caption"):
        errors.append("reel_caption is empty")
    yt = post.get("youtube") or {}
    title = yt.get("title", "")
    if not title or len(title) > YT_TITLE_MAX or "<" in title or ">" in title:
        errors.append(f"youtube.title must be 1-{YT_TITLE_MAX} chars with no < or >")
    if "#shorts" not in (title + yt.get("description", "")).lower():
        errors.append("put #Shorts in the YouTube title or description")
    if len(yt.get("description", "")) > YT_DESC_MAX:
        errors.append(f"youtube.description over {YT_DESC_MAX} chars")
    if not isinstance(yt.get("tags", []), list):
        errors.append("youtube.tags must be a list")
    return errors
