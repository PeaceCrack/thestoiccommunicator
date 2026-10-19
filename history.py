"""What has already been made and posted, so nothing repeats.

  python3 history.py            digest of every post: pillar, philosopher, topic, story, quotes, look
  python3 history.py --json     the same as JSON

validate.py calls repeats(post) to refuse a post whose topic, story, quote or cover line is
already used by another post file. published.json says which posts went live on which platform.
"""

import argparse
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "posts"
LEDGER = ROOT / "published.json"
SIMILAR = 0.82


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _similar(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    return bool(a and b) and (a == b or SequenceMatcher(None, a, b).ratio() >= SIMILAR)


def all_posts() -> list[dict]:
    posts = []
    for path in sorted(POSTS.glob("*.json")):
        try:
            posts.append({**json.loads(path.read_text(encoding="utf-8")), "_file": path.name})
        except json.JSONDecodeError as err:
            raise SystemExit(f"{path.name} is not valid JSON: {err}") from err
    return posts


def ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def _cover(post: dict) -> str:
    slides = post.get("slides") or [{}]
    return slides[0].get("headline", "")


def repeats(post: dict) -> list[str]:
    """Problems if this post reuses another post's slug, topic, story, quote or cover line."""
    problems = []
    for other in all_posts():
        if other.get("slug") == post.get("slug"):
            continue  # this post's own file
        name = other["_file"]
        if _similar(post.get("topic", ""), other.get("topic", "")):
            problems.append(f"topic repeats {name}: {other.get('topic')!r}")
        story, theirs = post.get("story") or {}, other.get("story") or {}
        if _similar(story.get("title", ""), theirs.get("title", "")):
            problems.append(f"story repeats {name}: {theirs.get('title')!r}")
        for quote in post.get("quotes", []):
            if any(_similar(quote, q) for q in other.get("quotes", [])):
                problems.append(f"quote already used in {name}: {quote[:60]!r}")
        if _similar(_cover(post), _cover(other)):
            problems.append(f"cover line repeats {name}: {_cover(other)!r}")
    return problems


def digest() -> dict:
    posts = all_posts()
    live = {e["slug"]: e for e in ledger()}
    rows = [{
        "date": p.get("date"), "slug": p.get("slug"), "pillar": p.get("pillar"), "philosopher": p.get("philosopher"),
        "topic": p.get("topic"), "story": (p.get("story") or {}).get("title"), "quotes": p.get("quotes", []),
        "cover": _cover(p), "look": f"{p.get('theme')}/{p.get('palette')}/{p.get('fonts')}",
        "mood": (p.get("reel_style") or {}).get("mood"),
        "live": sorted(k for k in ("ig_carousel", "ig_reel", "youtube") if live.get(p.get("slug"), {}).get(k)),
    } for p in posts]
    return {"posts": rows, "pillars": Counter(r["pillar"] for r in rows),
            "philosophers": Counter(r["philosopher"] for r in rows)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = digest()
    if args.json:
        print(json.dumps(data, indent=2))
        return
    if not data["posts"]:
        print("No posts yet.")
        return
    for r in data["posts"]:
        print(f"{r['date']}  [{r['pillar']}] {r['philosopher']}: {r['topic']}")
        print(f"    story: {r['story']}  |  cover: {r['cover']}  |  look: {r['look']}  mood: {r['mood']}")
        print(f"    quotes: {' / '.join(r['quotes'])}")
        print(f"    live: {', '.join(r['live']) or 'not posted'}")
    print("\npillars:", dict(data["pillars"]), "\nphilosophers:", dict(data["philosophers"]))


if __name__ == "__main__":
    main()
