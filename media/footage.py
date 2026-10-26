"""Real imagery for reel shots: public-domain art and photos, and free stock video.

Sources, all free:
  - Wikimedia Commons: paintings, statues, ruins. Only Public Domain / CC0 files are accepted,
    so no attribution or share-alike terms attach to the reel.
  - The Met Open Access: public-domain artworks (isPublicDomain=true).
  - Pexels: real cinematic stock video (free licence, no attribution required). Needs a free API
    key, read from $PEXELS_API_KEY or the macOS keychain item "pexels-api-key". Never a file.

HTTP goes through curl because python.org builds on macOS often lack CA certificates.
"""

import json
import os
import subprocess
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

UA = "StoicCommunicatorBot/1.0 (https://github.com/PeaceCrack/thestoiccommunicator)"
TIMEOUT_S = 120
MIN_SIDE = 1000          # reject images whose short side is smaller (they'd look soft at 1080x1920)
MIN_VIDEO_H = 1280
FREE_LICENSES = ("public domain", "cc0", "pd")
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
MET_API = "https://collectionapi.metmuseum.org/public/collection"
PEXELS_API = "https://api.pexels.com/videos/search"
KEYCHAIN_ITEM = "pexels-api-key"


@dataclass(frozen=True)
class Found:
    url: str
    kind: str        # "image" or "video"
    credit: str
    license: str
    page: str


class MediaError(Exception):
    pass


def _curl(url: str, headers: dict | None = None, out: Path | None = None) -> str:
    cmd = ["curl", "-sSL", "--fail", "--max-time", str(TIMEOUT_S), "-A", UA]
    for name, value in (headers or {}).items():
        cmd += ["-H", f"{name}: {value}"]
    cmd += (["-o", str(out)] if out else []) + [url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaError(f"request failed for {url.split('?')[0]}: {result.stderr.strip()}")
    return result.stdout


def pexels_key() -> str | None:
    if os.environ.get("PEXELS_API_KEY"):
        return os.environ["PEXELS_API_KEY"].strip()
    result = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_ITEM, "-w"],
                            capture_output=True, text=True)
    return result.stdout.strip() or None if result.returncode == 0 else None


def _free(license_name: str) -> bool:
    name = license_name.lower()
    return any(name.startswith(ok) for ok in FREE_LICENSES)


IMAGEINFO = {"prop": "imageinfo", "iiprop": "url|size|extmetadata|mime", "iiurlwidth": "1800",
             "iiextmetadatafilter": "LicenseShortName|Artist"}


def commons_by_title(title: str) -> list[Found]:
    """One exact Commons file, e.g. "File:Jean-Léon Gérôme - The Death of Caesar.jpg"."""
    params = {"action": "query", "format": "json", "titles": title, **IMAGEINFO}
    return _commons_found(json.loads(_curl(f"{COMMONS_API}?{urllib.parse.urlencode(params)}")))


def search_commons(query: str, limit: int = 12) -> list[Found]:
    params = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": "6",
              "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": str(limit), **IMAGEINFO}
    return _commons_found(json.loads(_curl(f"{COMMONS_API}?{urllib.parse.urlencode(params)}")))


def _commons_found(data: dict) -> list[Found]:
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    found = []
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        license_name = meta.get("LicenseShortName", {}).get("value", "")
        if not _free(license_name) or min(info.get("width", 0), info.get("height", 0)) < MIN_SIDE:
            continue
        if info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        found.append(Found(info.get("thumburl") or info["url"], "image", f"{page['title']} (Wikimedia Commons)",
                           license_name, info.get("descriptionurl", "")))
    return found


def search_met(query: str, limit: int = 8) -> list[Found]:
    params = {"hasImages": "true", "isPublicDomain": "true", "q": query, "limit": str(limit)}
    ids = json.loads(_curl(f"{MET_API}/v1.1/search?{urllib.parse.urlencode(params)}")).get("objectIDs") or []
    found = []
    for object_id in ids[:limit]:
        try:
            obj = json.loads(_curl(f"{MET_API}/v1/objects/{object_id}"))
        except MediaError:
            continue  # the search index lists some objects the object endpoint no longer serves
        if obj.get("isPublicDomain") and obj.get("primaryImage"):
            who = obj.get("artistDisplayName") or "unknown artist"
            found.append(Found(obj["primaryImage"], "image", f"{obj.get('title', 'Untitled')}, {who} (The Met)",
                               "Public domain (Met Open Access)", obj.get("objectURL", "")))
    return found


def search_pexels(query: str, min_seconds: float, limit: int = 12) -> list[Found]:
    key = pexels_key()
    if not key:
        raise MediaError("no Pexels API key (set PEXELS_API_KEY or the keychain item 'pexels-api-key')")
    params = {"query": query, "orientation": "portrait", "per_page": str(limit)}
    data = json.loads(_curl(f"{PEXELS_API}?{urllib.parse.urlencode(params)}", {"Authorization": key}))
    found = []
    for video in data.get("videos", []):
        if video.get("duration", 0) < min_seconds:
            continue
        files = [f for f in video.get("video_files", [])
                 if f.get("file_type") == "video/mp4" and (f.get("height") or 0) >= MIN_VIDEO_H]
        if not files:
            continue
        best = min(files, key=lambda f: abs((f.get("height") or 0) - 1920))
        found.append(Found(best["link"], "video", f"Video by {video['user']['name']} on Pexels",
                           "Pexels License", video.get("url", "")))
    return found


def find(spec: dict, min_seconds: float) -> list[Found]:
    """Candidates for one shot's media spec: {"type": "art"|"video", "query": ..., "source": ...}."""
    query = spec["query"]
    if spec.get("title"):
        found = commons_by_title(spec["title"])
        if not found:
            raise MediaError(f"{spec['title']} is missing, too small, or not public domain / CC0")
        return found
    if spec["type"] == "video":
        try:
            return search_pexels(query, min_seconds)
        except MediaError as err:
            print(f"    video unavailable ({err}); using art instead")
    source = spec.get("source", "any")
    results = []
    if source in ("any", "wikimedia"):
        results += search_commons(query)
    if source in ("any", "met") and len(results) < 3:
        try:
            results += search_met(query)
        except MediaError as err:
            print(f"    The Met search failed ({err}); using what Wikimedia found")
    return results


def download(item: Found, out_stem: Path) -> Path:
    ext = ".mp4" if item.kind == "video" else (".png" if item.url.lower().endswith(".png") else ".jpg")
    path = out_stem.with_suffix(ext)
    _curl(item.url, out=path)
    if path.stat().st_size < 10_000:
        raise MediaError(f"download too small, probably an error page: {item.url}")
    return path
