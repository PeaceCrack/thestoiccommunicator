# The Stoic Communicator pipeline

*Think like Plato. Speak like a leader. Influence like a CEO.* Ancient philosophy for modern dominance.

One JSON file per post becomes one narrated vertical video, posted as an **Instagram Reel** and a
**YouTube Short**. (No carousel: `render.py` still renders carousels by hand, but nothing posts them.)

```
posts/<date>-<slug>.json   the copy: reel beats + narration, reel caption, YouTube title, sources
brand.json                 name, handle, motto, logo, narrator voice
creative_brief.py          rolls theme, palette, fonts, music mood, transitions, story format, hook, wildcard
history.py                 every past topic, story, quote and look; validate.py refuses repeats
render.py                  carousel renderer, kept for manual use; not part of posting
fetch_media.py             finds each shot's public-domain art (Wikimedia, The Met) or Pexels video
render_reel.py             reel → out/<slug>/reel.mp4 + reel_cover.jpg (footage, hard cuts, voice, score, captions)
publish.py                 posts the Reel and the Short (dry run by default), records each in published.json
watch_run.py               waits for the GitHub run after a push and reports each platform
youtube_auth.py            one-time Google sign-in that stores the YouTube secrets in GitHub
.github/workflows/publish.yml   runs publish.py when a new file lands in posts/
```

**Setup (Meta app, Google Cloud, GitHub secrets): see [SETUP.md](SETUP.md).**
**What a slide or reel beat can contain: see [slides/CATALOG.md](slides/CATALOG.md).**

## Make a post

The easy way is `/stoic-communicator-post` in Claude Code. By hand:

```bash
python3 creative_brief.py
.venv/bin/python render_reel.py posts/2026-10-20-amor-fati.json
python3 publish.py posts/2026-10-20-amor-fati.json        # dry run
git add posts out && git commit -m "feat: add amor fati post" && git push
```

**Pushing a new file in `posts/` to main publishes it as a Reel and a Short.** Only push when it's ready.

## How the reel is made

- **Frames**: each beat is a 1080x1920 card (themes, generative art and infographics),
  animated in headless Chrome at 24 fps, then held under a slow push or pull.
- **Cuts**: ffmpeg `xfade` transitions (the brief picks 3-5 of 12), plus film grain and a vignette.
- **Voice**: Microsoft neural voice via `edge-tts` (free, no key), EQ'd for chest and presence.
  Change the narrator in `brand.json` → `voice`.
- **Captions**: word-by-word karaoke captions from the voice's word timings.
- **Score**: synthesized from scratch by ffmpeg (5 moods, random key and texture), ducked under
  the voice, plus a boom on the hook and a whoosh on every cut. Royalty-free by construction.

## Requirements

Google Chrome, ffmpeg (`brew install ffmpeg`), Python 3.11+, and for reels a venv with edge-tts:

```bash
python3 -m venv .venv && .venv/bin/pip install edge-tts
```

## Tests

```bash
python3 -m unittest discover -s tests
```
