"""Publish a rendered post: Instagram carousel, Instagram Reel, YouTube Short.

Dry run by default: it prints exactly what it would send and posts nothing. Add --publish to
post for real. Each platform is recorded in published.json the moment it succeeds, so a rerun
after a failure only retries what is missing and never posts the same thing twice.

Needs, in the environment (never in a file):
  IG_USER_ID, IG_ACCESS_TOKEN   Instagram professional account id and its long-lived token
  MEDIA_BASE_URL                public https folder holding out/<slug>/ (may contain {slug})
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN   Google OAuth client and refresh token
Optional:
  VIDEO_BASE_URL   where .mp4 files are fetched from. Defaults to MEDIA_BASE_URL, with
                   raw.githubusercontent.com switched to jsDelivr (which serves video/mp4)
  YT_PRIVACY       public (default), unlisted or private
  GRAPH_HOST       default graph.instagram.com; GRAPH_VERSION default v23.0

  python3 publish.py posts/2026-10-20-amor-fati.json
  python3 publish.py --next --publish
  python3 publish.py --next --publish --only youtube
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "posts"
LEDGER = ROOT / "published.json"
PLATFORMS = ("ig_carousel", "ig_reel", "youtube")
IG_ENV = ("IG_USER_ID", "IG_ACCESS_TOKEN", "MEDIA_BASE_URL")
YT_ENV = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
POLL_INTERVAL_S = 5
POLL_ATTEMPTS = 120
HTTP_TIMEOUT_S = 300
RAW_PREFIX = "https://raw.githubusercontent.com/"
YT_CATEGORY_EDUCATION = "27"


class PublishError(Exception):
    pass


# ---------- ledger and queue ----------

def read_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def entry_for(slug: str) -> dict:
    return next((e for e in read_ledger() if e["slug"] == slug), {"slug": slug})


def record(slug: str, platform: str, media_id: str, extra: dict | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    entries = read_ledger()
    current = next((e for e in entries if e["slug"] == slug), {"slug": slug})
    updated = {**current, platform: media_id, f"{platform}_at": now, **(extra or {})}
    others = [e for e in entries if e["slug"] != slug]
    LEDGER.write_text(json.dumps([*others, updated], indent=2) + "\n", encoding="utf-8")


def missing(slug: str) -> list[str]:
    done = entry_for(slug)
    return [p for p in PLATFORMS if not done.get(p)]


def out_dir(post: dict) -> Path:
    return ROOT / "out" / post["slug"]


def is_rendered(post: dict) -> bool:
    folder = out_dir(post)
    slides = all((folder / f"{i:02d}.jpg").exists() for i in range(1, len(post["slides"]) + 1))
    return slides and (folder / "reel.mp4").exists() and (folder / "reel_cover.jpg").exists()


def next_post_path() -> Path | None:
    """Oldest rendered post (by file name) with a platform still unpublished."""
    for path in sorted(POSTS.glob("*.json")):
        post = json.loads(path.read_text(encoding="utf-8"))
        if missing(post["slug"]) and is_rendered(post):
            return path
    return None


# ---------- urls ----------

def video_base(base: str) -> str:
    """raw.githubusercontent.com serves .mp4 as octet-stream; jsDelivr serves the same file as video/mp4."""
    if not base.startswith(RAW_PREFIX):
        return base
    owner, repo, ref, *rest = base[len(RAW_PREFIX):].split("/")
    return "/".join([f"https://cdn.jsdelivr.net/gh/{owner}/{repo}@{ref}", *rest])


def folder_url(base: str, post: dict) -> str:
    return base.replace("{slug}", post["slug"]).rstrip("/")


def carousel_items(post: dict, image_base: str, vid_base: str) -> list[dict]:
    """One entry per slide: the still JPEG, plus the MP4 when the slide is animated."""
    images, videos = folder_url(image_base, post), folder_url(vid_base, post)
    return [{"image": f"{images}/{i:02d}.jpg",
             "video": f"{videos}/{i:02d}.mp4" if (out_dir(post) / f"{i:02d}.mp4").exists() else None}
            for i in range(1, len(post["slides"]) + 1)]


# ---------- http ----------

def http(method: str, url: str, params: dict | None = None, body: bytes | None = None,
         headers: dict | None = None) -> tuple[dict, dict]:
    if params is not None and method == "GET":
        url, data = f"{url}?{urllib.parse.urlencode(params)}", None
    elif params is not None:
        data = urllib.parse.urlencode(params).encode()
    else:
        data = body
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
            raw = response.read()
            return (json.loads(raw) if raw else {}), dict(response.headers)
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="replace")[:1500]
        raise PublishError(f"HTTP {err.code} on {url.split('?')[0]}: {detail}") from err
    except urllib.error.URLError as err:
        raise PublishError(f"Network error on {url.split('?')[0]}: {err.reason}") from err


# ---------- instagram ----------

def ig_config() -> dict:
    absent = [n for n in IG_ENV if not os.environ.get(n)]
    if absent:
        raise PublishError(f"Missing environment variables: {', '.join(absent)}")
    base = os.environ["MEDIA_BASE_URL"].rstrip("/")
    if not base.startswith("https://"):
        raise PublishError("MEDIA_BASE_URL must be a public https URL. Instagram fetches the files itself.")
    host = os.environ.get("GRAPH_HOST", "graph.instagram.com")
    return {"user_id": os.environ["IG_USER_ID"].strip(), "token": clean_token(os.environ["IG_ACCESS_TOKEN"]),
            "media_base": base,
            "video_base": os.environ.get("VIDEO_BASE_URL", "").rstrip("/") or video_base(base),
            "api": f"https://{host}/{os.environ.get('GRAPH_VERSION', 'v23.0')}"}


TOKEN_KINDS = {"IGAA": "Instagram Login token (correct)", "IG": "Instagram token",
               "EAA": "Facebook token (wrong kind for graph.instagram.com)"}


def clean_token(raw: str) -> str:
    """Strip whitespace, newlines and quotes a paste or `echo | gh secret set` can add."""
    token = raw.strip().strip('"').strip("'").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def token_report(raw: str) -> str:
    """Safe facts about the token for the log. Never the value itself."""
    token = clean_token(raw)
    kind = next((label for prefix, label in TOKEN_KINDS.items() if token.startswith(prefix)), "unknown kind")
    return (f"token: {len(token)} chars ({len(raw)} before trimming), {kind}, "
            f"inner whitespace: {any(c.isspace() for c in token)}")


def ig_wait(cfg: dict, container: str) -> None:
    for _ in range(POLL_ATTEMPTS):
        status, _ = http("GET", f"{cfg['api']}/{container}", {"fields": "status_code,status",
                                                               "access_token": cfg["token"]})
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise PublishError(f"Container {container} failed with status {code}: {status.get('status', '')}")
        time.sleep(POLL_INTERVAL_S)
    raise PublishError(f"Container {container} not ready after {POLL_ATTEMPTS * POLL_INTERVAL_S}s")


def ig_create(cfg: dict, params: dict) -> str:
    result, _ = http("POST", f"{cfg['api']}/{cfg['user_id']}/media", {**params, "access_token": cfg["token"]})
    ig_wait(cfg, result["id"])
    return result["id"]


def ig_publish(cfg: dict, container: str) -> str:
    result, _ = http("POST", f"{cfg['api']}/{cfg['user_id']}/media_publish",
                     {"creation_id": container, "access_token": cfg["token"]})
    return result["id"]


def publish_carousel(post: dict, cfg: dict) -> tuple[str, list[int]]:
    children, fallbacks = [], []
    for n, item in enumerate(carousel_items(post, cfg["media_base"], cfg["video_base"]), start=1):
        if item["video"]:
            try:
                children.append(ig_create(cfg, {"media_type": "VIDEO", "video_url": item["video"],
                                                "is_carousel_item": "true"}))
                print(f"  slide {n:02d} video")
                continue
            except PublishError as err:
                print(f"  slide {n:02d} video rejected, using the still: {err}")
                fallbacks.append(n)
        children.append(ig_create(cfg, {"image_url": item["image"], "is_carousel_item": "true"}))
        print(f"  slide {n:02d} image")
    carousel = ig_create(cfg, {"media_type": "CAROUSEL", "children": ",".join(children),
                               "caption": post["caption"]})
    return ig_publish(cfg, carousel), fallbacks


def publish_reel(post: dict, cfg: dict) -> str:
    container = ig_create(cfg, {
        "media_type": "REELS", "video_url": f"{folder_url(cfg['video_base'], post)}/reel.mp4",
        "cover_url": f"{folder_url(cfg['media_base'], post)}/reel_cover.jpg",
        "caption": post["reel_caption"], "share_to_feed": "true",
    })
    return ig_publish(cfg, container)


# ---------- youtube ----------

def yt_access_token() -> str:
    absent = [n for n in YT_ENV if not os.environ.get(n)]
    if absent:
        raise PublishError(f"Missing environment variables: {', '.join(absent)}")
    result, _ = http("POST", "https://oauth2.googleapis.com/token", {
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"})
    return result["access_token"]


def youtube_metadata(post: dict) -> dict:
    yt = post["youtube"]
    privacy = os.environ.get("YT_PRIVACY", "public")
    if privacy not in ("public", "unlisted", "private"):
        raise PublishError("YT_PRIVACY must be public, unlisted or private")
    return {"snippet": {"title": yt["title"], "description": yt["description"], "tags": yt.get("tags", []),
                        "categoryId": YT_CATEGORY_EDUCATION, "defaultLanguage": "en"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}


def publish_youtube(post: dict) -> tuple[str, str]:
    """Resumable upload of reel.mp4. Returns (video id, privacy status YouTube actually applied)."""
    token = yt_access_token()
    video = out_dir(post) / "reel.mp4"
    meta = json.dumps(youtube_metadata(post)).encode()
    _, headers = http("POST", "https://www.googleapis.com/upload/youtube/v3/videos"
                              "?uploadType=resumable&part=snippet,status", body=meta, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(video.stat().st_size), "X-Upload-Content-Type": "video/mp4"})
    location = headers.get("Location") or headers.get("location")
    if not location:
        raise PublishError("YouTube did not return an upload URL")
    result, _ = http("PUT", location, body=video.read_bytes(), headers={"Content-Type": "video/mp4"})
    return result["id"], result.get("status", {}).get("privacyStatus", "unknown")


# ---------- main ----------

def dry_run(post: dict, todo: list[str]) -> None:
    base = os.environ.get("MEDIA_BASE_URL", "<MEDIA_BASE_URL>")
    vbase = os.environ.get("VIDEO_BASE_URL", "") or video_base(base)
    print(f"DRY RUN for {post['slug']}, nothing will be posted. Add --publish to post.")
    print(f"Would publish: {', '.join(todo)}\n")
    if "ig_carousel" in todo:
        print("Carousel:", *[i["video"] or i["image"] for i in carousel_items(post, base, vbase)], sep="\n  ")
        print(f"Caption ({len(post['caption'])} chars):\n{post['caption']}\n")
    if "ig_reel" in todo:
        print(f"Reel: {folder_url(vbase, post)}/reel.mp4  cover {folder_url(base, post)}/reel_cover.jpg")
        print(f"Reel caption:\n{post['reel_caption']}\n")
    if "youtube" in todo:
        meta = youtube_metadata(post)
        print(f"YouTube Short: {meta['snippet']['title']!r} ({meta['status']['privacyStatus']})")
        print(f"  {(ROOT / 'out' / post['slug'] / 'reel.mp4').stat().st_size / 1e6:.1f} MB upload")


def publish_all(post: dict, todo: list[str]) -> list[str]:
    """Publish each missing platform, recording each success at once. Returns error lines."""
    errors = []
    cfg = None
    for platform in todo:
        try:
            if platform in ("ig_carousel", "ig_reel") and cfg is None:
                cfg = ig_config()
            if platform == "ig_carousel":
                media_id, fallbacks = publish_carousel(post, cfg)
                record(post["slug"], platform, media_id, {"video_fallbacks": fallbacks} if fallbacks else None)
            elif platform == "ig_reel":
                media_id = publish_reel(post, cfg)
                record(post["slug"], platform, media_id)
            else:
                media_id, privacy = publish_youtube(post)
                record(post["slug"], platform, media_id, {"youtube_privacy": privacy})
            print(f"POSTED {platform}: {media_id}")
        except PublishError as err:
            if "code\":190" in str(err).replace(" ", ""):
                print("  " + token_report(os.environ.get("IG_ACCESS_TOKEN", "")), file=sys.stderr)
            errors.append(f"{platform}: {err}")
            print(f"FAILED {platform}: {err}", file=sys.stderr)
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("post", type=Path, nargs="?")
    parser.add_argument("--next", action="store_true", help="the oldest post with something unpublished")
    parser.add_argument("--publish", action="store_true", help="actually post. Without it, dry run")
    parser.add_argument("--only", help=f"comma-separated subset of {','.join(PLATFORMS)}")
    args = parser.parse_args()

    path = next_post_path() if args.next else args.post
    if path is None:
        if args.next:
            print("Queue is empty: every rendered post is published on every platform.")
            return
        parser.error("give a post file or --next")
    post = json.loads(path.read_text(encoding="utf-8"))
    if not is_rendered(post):
        raise SystemExit(f"Render first: python3 render.py {path} && .venv/bin/python render_reel.py {path}")
    only = [p.strip() for p in args.only.split(",")] if args.only else list(PLATFORMS)
    unknown = [p for p in only if p not in PLATFORMS]
    if unknown:
        parser.error(f"unknown platform(s): {', '.join(unknown)}")
    todo = [p for p in missing(post["slug"]) if p in only]
    if not todo:
        print(f"{post['slug']} is already published on {', '.join(only)}.")
        return
    if not args.publish:
        dry_run(post, todo)
        return
    errors = publish_all(post, todo)
    if errors:
        raise SystemExit("Some platforms failed (the rest are recorded):\n  " + "\n  ".join(errors))
    print(f"Published {post['slug']} on {', '.join(todo)}. Add the alt text in the app: {post['alt_text']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
