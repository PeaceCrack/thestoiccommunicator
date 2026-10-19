# Slide catalog

What a post file can use. `validate.py` enforces it and `render.py` refuses slides whose
text spills outside the safe area. See `examples/burn-the-letters.json` for a full post (carousel + reel + YouTube).

## Post level

```json
{ "slug": "...", "date": "YYYY-MM-DD", "pillar": "think|speak|influence", "philosopher": "...",
  "topic": "...", "story": {"title": "...", "who": "...", "when": "..."}, "quotes": ["..."],
  "facts": [{"claim": "...", "source": "..."}],
  "theme": "...", "palette": "...", "fonts": "...", "seed": 4127, "reel_style": { ... },
  "alt_text": "...", "caption": "...", "search_terms": ["...", "..."], "slides": [ ... ],
  "reel": {"beats": [ ... ]}, "reel_caption": "...", "youtube": {"title": "... #Shorts", "description": "...", "tags": []} }
```

- `topic`, `story.title`, `quotes` and the cover headline are checked against every other post by
  `history.py`: a repeat fails validation.

- **6 to 12 slides.** Cover first, CTA last. Pick the count from the content, not a habit.
- **theme**: `temple` · `codex` · `academy` · `colosseum` · `oracle` · `fresco` (moods in `slides/theme.py`)
- **palette**: `imperial-gold` `marble-bronze` `obsidian-ember` `aegean-sand` `olive-grove` `bloodstone` `verdigris`
  `parchment-oxblood` `midnight-ivory` `electric-stoic` `emerald-empire` `terracotta-agora`
- **fonts**: `cinzel` `playfair` `bodoni` `dm-serif` `bebas` `anton` (display + body pairs)
- **seed**: any integer. It picks the generative art and any layout you don't set. Same seed, same pixels.
- At least **half the middle slides need a visual**.
- At most **3 slides with `"animate": true`**. Each becomes an 8s looping video; its still is the fallback.

## Slide

```json
{ "kind": "content", "headline": "FIND THE MUST-HAVES", "body": "optional, max 25 words",
  "kicker": "optional small label", "visual": { "type": "checklist", ... },
  "layout": "optional", "art": "optional", "surface": "optional", "animate": false }
```

| kind | job | headline |
|---|---|---|
| `cover` | the hook | max 6 words, CAPS |
| `stake` | second cover, why it matters | optional |
| `content` | one idea per slide, auto-numbered 01, 02 … | 2–8 words |
| `recap` | the screenshot slide: `items` list or a visual | yes |
| `cta` | one ask | e.g. SAVE THIS |

**layout** (random from the seed if unset): cover `left`/`center`/`poster` · content `stack`/`visual-first`/`number`/`center` · stake and cta `left`/`center`
**art** (random from the theme if unset): `glow` `waves` `rings` `dots` `rules` `grid` `shapes` `marble` `meander` `laurel` `geometry` `columns` `none`
**surface** overrides the theme for one slide: `night` `paper` `ink` `stone` `gradient` `card`

## Visuals

| type | fields | best for | animates as |
|---|---|---|---|
| `chips` | `items`, `strike` (bool) | buzzwords, tools, myths to cross out | chips rise, strike-through draws |
| `steps` | `items` | ordered process | rows rise one by one |
| `checklist` | `items`, `done` (n ticked) | criteria, prep lists | ticks pop in |
| `stat` | `value`, `prefix`, `suffix`, `label`, `note` | one striking number (illustrative, say so in `note`) | number counts up |
| `bars` | `items`: [[label, value]], `suffix` | comparisons, rankings | bars grow |
| `donut` | `value` 0–100, `label`, `note` | a share or a score | ring fills |
| `compare` | `left`/`right`: {`title`, `lines`}, `stack` | wrong vs right, before vs after | sides rise |
| `flow` | `items`: [label] or [[label, icon]] | pipelines, cause → effect | arrows march |
| `timeline` | `items`: [[when, what]] | 30-60-90 plans, interview day | points rise |
| `decode` | `rows`: [[they say, they mean]], `left_title`, `right_title` | what a powerful person's words really signal | rows rise |
| `quote` | `text`, `who` | a verified line from a thinker, with the book and section in `who` | text rises |
| `story` | `when`, `text` (max ~30 words), `who` (source) | a historical scene, told tight | card rises |
| `matrix` | `cols`, `rows`, `filled` | coverage grids, skill maps | cells pop |
| `icons` | `items`: [[icon, label]], `cols` | 3–6 parallel ideas | cards pop |
| `image` | `src` (file under `assets/`), `caption`, `shape` (`circle`/`tilt`), `alt` | real photos the user supplied | static |
| `svg` | `markup`: inline `<svg>` | original illustration drawn for the post | static |

**Icons:** bolt brain briefcase bulb calendar chart chat check clock column compass crown cross eye
flame handshake hourglass laurel link lock mail mask mic money mountain owl rocket scale scroll
search shield star sword target team user warning

**svg art rules:** plain shapes and text only, `viewBox` around 840 wide, use `var(--accent)`,
`var(--accent2)`, `var(--fg)` and `var(--muted)` for colour so it follows the theme. No
`<script>`, event handlers, `<image>`, `<foreignObject>` or external links (rejected).

## Reel beats (1080x1920, `reel.beats`)

```json
{ "kind": "story", "kicker": "optional", "headline": "max 7 words", "body": "optional, max 25 words",
  "visual": { ... any visual above ... }, "voice": "the narration for this beat, max 34 words",
  "layout": "optional top|center|low", "surface": "optional", "art": "optional" }
```

| kind | job |
|---|---|
| `hook` | first 2 seconds: the pattern-interrupt line. Its headline is on screen from frame one |
| `story` | the historical scene, in short beats |
| `fact` | a sourced fact or study finding |
| `lesson` | the principle, often as a `compare` |
| `quote` | the thinker's verified line (`quote` visual) |
| `takeaway` | what to do today |
| `cta` | follow, with the motto |

- 6-14 beats, hook first, cta last, 60-125 narration words in total (about 28-58 s). Over 59 s fails.
- The narration is spoken by a neural voice and burned in as word-by-word captions, so write it
  to be heard: short sentences, numbers as digits, no abbreviations the voice will misread.
- `render_reel.py` refuses copy outside the safe zone (y 290-1305, x 80-935) and names the beat.
