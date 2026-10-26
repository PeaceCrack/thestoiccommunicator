"""Checks a post file (look, sources, no repeats, reel script, captions, YouTube) before rendering."""

from pathlib import Path

import json

from history import repeats
from slides.theme import FONT_PAIRS, PALETTES, THEMES
from slides.visuals import VISUALS, render_visual

ROOT = Path(__file__).resolve().parent
MENTAL_MODELS = {m["name"] for m in json.loads((ROOT / "ideas.json").read_text(encoding="utf-8"))["mental_models"]}
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


def validate_carousel(post: dict) -> list[str]:
    """Carousel rules, for render.py only. Posts are reel-only now, so the skill doesn't use this."""
    slides = post.get("slides", [])
    errors = []
    if not MIN_SLIDES <= len(slides) <= MAX_SLIDES:
        errors.append(f"{len(slides)} slides, want {MIN_SLIDES}-{MAX_SLIDES}")
    if slides and slides[0].get("kind") != "cover":
        errors.append("first slide must be the cover")
    if slides and slides[-1].get("kind") != "cta":
        errors.append("last slide must be the CTA")
    animated = sum(1 for s in slides if s.get("animate"))
    if animated > MAX_ANIMATED:
        errors.append(f"{animated} animated slides, max {MAX_ANIMATED}")
    middle = [s for s in slides if s.get("kind") in MIDDLE_KINDS]
    with_visual = sum(1 for s in middle if s.get("visual"))
    if middle and with_visual * 2 < len(middle):
        errors.append(f"only {with_visual} of {len(middle)} middle slides have a visual, want at least half")
    for index, slide in enumerate(slides):
        errors.extend(_check_slide(index, slide))
    return errors


def validate_post(post: dict) -> list[str]:
    """Post-level rules: the look, the tracking fields that stop repeats, sources. Empty = good."""
    errors = []
    if post.get("theme") not in THEMES:
        errors.append(f"unknown theme {post.get('theme')!r}. Use one of: {', '.join(THEMES)}")
    if post.get("palette") not in PALETTES:
        errors.append(f"unknown palette {post.get('palette')!r}. Use one of: {', '.join(PALETTES)}")
    if post.get("fonts") not in FONT_PAIRS:
        errors.append(f"unknown fonts {post.get('fonts')!r}. Use one of: {', '.join(FONT_PAIRS)}")
    if post.get("pillar") not in PILLARS:
        errors.append(f"pillar must be one of {', '.join(PILLARS)}")
    for field in ("topic", "philosopher", "story"):
        if not post.get(field):
            errors.append(f"{field} is missing (it is how history.py stops repeats)")
    story = post.get("story") or {}
    if story and not story.get("source"):
        errors.append("story.source is missing: name the ancient author and book, or a solid history source")
    if not post.get("takeaway"):
        errors.append("takeaway is missing: the ONE sentence the viewer should remember")
    facts = post.get("facts", [])
    if len(facts) > MAX_FACTS:
        errors.append(f"{len(facts)} facts: one story per reel, not a stack of facts (max {MAX_FACTS} supporting fact)")
    for fact in facts:
        if not fact.get("source"):
            errors.append(f"fact {fact.get('claim', '')[:40]!r} needs a source")
    if post.get("mental_model") and post["mental_model"] not in MENTAL_MODELS:
        errors.append(f"mental_model {post['mental_model']!r} is not in ideas.json")
    errors.extend(repeats(post))
    return errors

PILLARS = ("think", "speak", "influence")
# One story, one takeaway: the hook opens it, story/turn beats tell it (the turn is the twist or
# climax), at most one quote is the thinker's line, ONE lesson is the takeaway, the cta closes.
BEAT_KINDS = {"hook", "story", "turn", "quote", "lesson", "cta"}
MIN_STORY_BEATS = 5
MIN_MEDIA_SHARE_X10 = 7   # 70% of scene shots must be real footage or art
MEDIA_TYPES = ("art", "video")
MAX_FACTS = 1
MIN_BEATS, MAX_BEATS = 10, 18   # a fuller storyboard of short shots, hard-cut like a film
BEAT_MAX_WORDS = 24
REEL_MIN_WORDS, REEL_MAX_WORDS = 80, 135   # about 35-58 s of narration
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
    kinds = [b.get("kind") for b in beats]
    if sum(k in ("story", "turn") for k in kinds) < MIN_STORY_BEATS:
        errors.append(f"tell the story in at least {MIN_STORY_BEATS} story/turn beats")
    if kinds.count("lesson") != 1:
        errors.append(f"{kinds.count('lesson')} lesson beats: exactly 1, the one takeaway")
    if kinds.count("quote") > 1:
        errors.append("at most 1 quote beat")
    scenes = [b for b in beats if b.get("kind") in ("hook", "story", "turn")]
    with_media = sum(1 for b in scenes if b.get("media"))
    if scenes and with_media * 10 < len(scenes) * MIN_MEDIA_SHARE_X10:
        errors.append(f"only {with_media} of {len(scenes)} hook/story/turn shots use real media, want at least "
                      f"{MIN_MEDIA_SHARE_X10 * 10}%: give them a \"media\" image or video")
    for index, beat in enumerate(beats, start=1):
        spec = beat.get("media")
        if spec and (spec.get("type") not in MEDIA_TYPES or not str(spec.get("query", "")).strip()):
            errors.append(f"beat {index}: media needs type 'art' or 'video' and a search query")
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
        errors.append(f"reel narration is {total} words, want {REEL_MIN_WORDS}-{REEL_MAX_WORDS} (35-58 s)")
    caption = post.get("reel_caption", "")
    if not caption:
        errors.append("reel_caption is empty")
    if len(caption) > CAPTION_MAX_CHARS:
        errors.append(f"reel_caption is {len(caption)} chars, max {CAPTION_MAX_CHARS}")
    hashtags = [w for w in caption.split() if w.startswith("#")]
    if len(hashtags) > CAPTION_MAX_HASHTAGS:
        errors.append(f"{len(hashtags)} hashtags in reel_caption, max {CAPTION_MAX_HASHTAGS}")
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
