"""Roll a random creative brief for the next post, so no two posts look or sound alike.

  python3 creative_brief.py            # random
  python3 creative_brief.py --seed 7   # reproducible

Avoids the last post's theme, font pairing and reel mood and the last three palettes; leans
toward the pillar and thinkers used least so far; picks the reel's length, visuals, motion,
transitions and caption face, a story format, a hook formula and one wildcard constraint.
"""

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from history import all_posts
from media.captions import CAPTION_STYLES, STYLE_FONTS
from media.music import MOODS
from render_reel import TRANSITIONS
from slides.theme import FONT_PAIRS, PALETTES, THEMES
from slides.visuals import VISUALS

PILLARS = {
    "think": "Think like Plato: clarity, first principles, mental models, judgement under pressure",
    "speak": "Speak like a leader: rhetoric, presence, persuasion, silence, storytelling, hard conversations",
    "influence": "Influence like a CEO: power, negotiation, reputation, decisions, leading people",
}
THINKERS = ["Marcus Aurelius", "Seneca", "Epictetus", "Plato", "Socrates", "Aristotle", "Zeno of Citium",
            "Cicero", "Musonius Rufus", "Heraclitus", "Diogenes", "Cato the Younger", "Demosthenes",
            "Quintilian", "Pericles", "Chrysippus", "Sun Tzu", "Lao Tzu", "Confucius", "Machiavelli"]
# Every format tells ONE story with ONE takeaway. No stacking facts and studies.
FORMATS = [
    "cold open: drop the viewer into the most tense second of the story, then rewind",
    "the twist: tell the story straight, then reveal the detail that flips its meaning",
    "the choice: the hero faces two options; make the viewer guess before the reveal",
    "the cost: show what the hero lost by getting it wrong, then what they learned",
    "underdog: the weakest person in the room wins, and the viewer learns exactly how",
    "the line: build the whole story toward one sentence the thinker actually said",
    "rise and fall: the same habit that made someone powerful later destroyed them",
]
HOOKS = [
    "contrarian claim that sounds wrong but is true",
    "a date and a place: 'Rome, 65 AD...' then a cliffhanger",
    "a number that shocks, with its real source",
    "'You are losing every argument because of one habit'",
    "'A 2000-year-old trick CEOs still use'",
    "a direct question the viewer cannot ignore",
    "start mid-story at the most dramatic second",
    "'Stop doing this in meetings' with a visible mistake",
]
WILDCARDS = [
    "Draw one original inline-SVG illustration (an `svg` visual): a scene or diagram from the story, not clip art.",
    "Make the reel's second beat a single giant `quote` card, no body text.",
    "Give one reel beat a different surface from the rest, using the `surface` field.",
    "Open the hook on a single `emblem` graphic of the story's key object, no other visual.",
    "Make the turn beat a `compare`: what anyone would have done vs what the hero did.",
    "Tell the whole story in present tense, as if it is happening right now.",
    "Name one sound or object in every story beat, so the viewer can picture the scene.",
    "End the reel with a one-line challenge the viewer can try in their next conversation today.",
    "Use a `timeline` visual to show the story across years or a single tense day.",
]
BEAT_COUNTS = [7, 8, 8, 9, 9, 10, 11]
FEATURED = 2
# Graphics that serve a story. Data charts (bars, donut, stat) invite fact-stacking, so they're out.
STORY_VISUALS = ("emblem", "story", "quote", "timeline", "compare", "icons", "chips", "flow", "checklist")


def _recent(posts: list[dict], key, n: int) -> list:
    return [key(p) for p in posts[-n:] if key(p)]


def _least_used(rng: random.Random, options: list[str], used: Counter) -> str:
    low = min(used.get(o, 0) for o in options)
    return rng.choice([o for o in options if used.get(o, 0) == low])


IDEAS = Path(__file__).resolve().parent / "ideas.json"


def mental_models() -> list[dict]:
    return json.loads(IDEAS.read_text(encoding="utf-8"))["mental_models"]


def suggest_models(rng: random.Random, posts: list[dict], n: int = 3) -> list[dict]:
    """The mental models used least so far (ties broken at random)."""
    used = Counter(p.get("mental_model") for p in posts)
    return sorted(mental_models(), key=lambda m: (used.get(m["name"], 0), rng.random()))[:n]


def roll(rng: random.Random) -> dict:
    posts = all_posts()
    avoid_theme = _recent(posts, lambda p: p.get("theme"), 1)
    avoid_palettes = _recent(posts, lambda p: p.get("palette"), 3)
    avoid_fonts = _recent(posts, lambda p: p.get("fonts"), 1)
    avoid_mood = _recent(posts, lambda p: (p.get("reel_style") or {}).get("mood"), 1)
    pillar = _least_used(rng, list(PILLARS), Counter(p.get("pillar") for p in posts))
    thinker_use = Counter(p.get("philosopher") for p in posts)
    thinkers = sorted(THINKERS, key=lambda t: (thinker_use.get(t, 0), rng.random()))[:4]
    palette = rng.choice([p for p in PALETTES if p not in avoid_palettes])
    visual_pool = [v for v in STORY_VISUALS if v in VISUALS]
    theme = rng.choice([t for t in THEMES if t not in avoid_theme])
    caption_style = rng.choice(CAPTION_STYLES)
    return {
        "suggested_mental_models": suggest_models(rng, posts),
        "pillar": pillar,
        "pillar_meaning": PILLARS[pillar],
        "suggested_thinkers": thinkers,
        "format": rng.choice(FORMATS),
        "hook_formula": rng.choice(HOOKS),
        "theme": theme,
        "theme_mood": THEMES[theme]["mood"],
        "palette": palette,
        "fonts": rng.choice([f for f in FONT_PAIRS if f not in avoid_fonts]),
        "seed": rng.randint(1, 99999),
        "feature_visuals": rng.sample(visual_pool, FEATURED),
        "reel_style": {
            "beats": rng.choice(BEAT_COUNTS),
            "mood": rng.choice([m for m in MOODS if m not in avoid_mood]),
            "transitions": rng.sample(TRANSITIONS, rng.randint(3, 5)),
            "motions": rng.sample(["push", "pull", "still"], rng.randint(2, 3)),
            "caption_style": caption_style,
            "caption_font": rng.choice(STYLE_FONTS[caption_style]),
        },
        "wildcard": rng.choice(WILDCARDS),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    print(json.dumps(roll(random.Random(args.seed)), indent=2))


if __name__ == "__main__":
    main()
