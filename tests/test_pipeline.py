"""Pipeline tests. Run: python3 -m unittest discover -s tests (no network, no Chrome, no edge-tts)."""

import copy
import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import creative_brief  # noqa: E402
import history  # noqa: E402
import publish  # noqa: E402
from media.captions import Timed, ass_color, build_ass, phrases, punctuate, shift  # noqa: E402
from media.voice import Narration, Word  # noqa: E402
from render_reel import XFADE_S, timeline, total_length  # noqa: E402
from slides.art import GENERATORS, art_layer  # noqa: E402
from slides.compose import fonts_query, render_slide  # noqa: E402
from slides.reel_frame import render_frames  # noqa: E402
from slides.theme import FONT_AXES, FONT_PAIRS, PALETTES, SURFACES, THEMES, styled_brand, surfaces  # noqa: E402
from validate import validate_post, validate_reel  # noqa: E402

EXAMPLE = json.loads((ROOT / "examples" / "burn-the-letters.json").read_text())
BRAND = json.loads((ROOT / "brand.json").read_text())


def with_changes(**changes) -> dict:
    return {**copy.deepcopy(EXAMPLE), **changes}


class EmptyHistory(unittest.TestCase):
    """Validate against an empty posts/ folder so the example is never compared with real posts."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(history, "POSTS", Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def add_post(self, post: dict, name: str = "2026-01-01-other.json") -> None:
        (Path(self.tmp.name) / name).write_text(json.dumps(post), encoding="utf-8")


class ValidatePostTest(EmptyHistory):
    def test_example_passes(self):
        self.assertEqual(validate_post(EXAMPLE), [])
        self.assertEqual(validate_reel(EXAMPLE), [])

    def test_rejects_unknown_palette_fonts_and_pillar(self):
        errors = validate_post(with_changes(palette="neon", fonts="comic", pillar="eat"))
        self.assertTrue(any("unknown palette" in e for e in errors))
        self.assertTrue(any("unknown fonts" in e for e in errors))
        self.assertTrue(any("pillar must be" in e for e in errors))

    def test_fact_needs_source(self):
        errors = validate_post(with_changes(facts=[{"claim": "Leaders who pause win"}]))
        self.assertTrue(any("needs a source" in e for e in errors))

    def test_requires_tracking_fields(self):
        post = copy.deepcopy(EXAMPLE)
        del post["story"]
        self.assertTrue(any("story is missing" in e for e in validate_post(post)))

    def test_does_not_mutate_input(self):
        before = copy.deepcopy(EXAMPLE)
        validate_post(EXAMPLE)
        validate_reel(EXAMPLE)
        self.assertEqual(EXAMPLE, before)


class RepeatsTest(EmptyHistory):
    def other(self, **changes) -> dict:
        base = {"slug": "other", "topic": "Something unrelated about negotiation anchors",
                "story": {"title": "Cicero's speech against Catiline"}, "quotes": ["Unrelated line here."],
                "slides": [{"kind": "cover", "headline": "THE FIRST NUMBER WINS"}]}
        return {**base, **changes}

    def test_no_repeat_with_unrelated_post(self):
        self.add_post(self.other())
        self.assertEqual(history.repeats(EXAMPLE), [])

    def test_catches_reused_story_quote_topic_and_cover(self):
        self.add_post(self.other(topic=EXAMPLE["topic"], story=EXAMPLE["story"],
                                 quotes=["The best revenge is not to be like your enemy!"],
                                 slides=[{"kind": "cover", "headline": "He burned the letters"}]))
        problems = " | ".join(history.repeats(EXAMPLE))
        for word in ("topic repeats", "story repeats", "quote already used", "cover line repeats"):
            self.assertIn(word, problems)

    def test_own_file_is_not_a_repeat(self):
        self.add_post(EXAMPLE, "2026-10-20-example.json")
        self.assertEqual(history.repeats(EXAMPLE), [])

    def test_digest_counts_pillars(self):
        self.add_post(self.other(pillar="speak", philosopher="Cicero"))
        data = history.digest()
        self.assertEqual(data["pillars"]["speak"], 1)
        self.assertEqual(data["posts"][0]["live"], [])


class ValidateReelTest(EmptyHistory):
    def reel_with(self, beats) -> dict:
        post = copy.deepcopy(EXAMPLE)
        post["reel"]["beats"] = beats
        return post

    def test_hook_first_cta_last(self):
        beats = list(reversed(EXAMPLE["reel"]["beats"]))
        errors = validate_reel(self.reel_with(beats))
        self.assertIn("first reel beat must be the hook", errors)
        self.assertIn("last reel beat must be the cta", errors)

    def test_rejects_long_beat_and_long_reel(self):
        beats = copy.deepcopy(EXAMPLE["reel"]["beats"])
        beats[1]["voice"] = "word " * 40
        errors = validate_reel(self.reel_with(beats))
        self.assertTrue(any("Split the beat" in e for e in errors))
        self.assertTrue(any("reel narration is" in e for e in errors))

    def test_youtube_needs_shorts_tag(self):
        post = copy.deepcopy(EXAMPLE)
        post["youtube"] = {"title": "No tag", "description": "none", "tags": []}
        self.assertTrue(any("#Shorts" in e for e in validate_reel(post)))

    def test_rejects_angle_brackets_in_title(self):
        post = copy.deepcopy(EXAMPLE)
        post["youtube"]["title"] = "<b>bad</b> #Shorts"
        self.assertTrue(any("no < or >" in e for e in validate_reel(post)))


class ThemeTest(unittest.TestCase):
    def test_every_palette_builds_every_surface(self):
        for name, palette in PALETTES.items():
            built = surfaces(palette)
            self.assertEqual(tuple(built), SURFACES, name)

    def test_theme_roles_and_art_exist(self):
        for name, theme in THEMES.items():
            for surface in theme["roles"].values():
                self.assertIn(surface, SURFACES, name)
            for styles in theme["art"].values():
                for style in styles:
                    self.assertTrue(style == "none" or style in GENERATORS, f"{name}: {style}")

    def test_every_font_has_axis_spec(self):
        for pair in FONT_PAIRS.values():
            self.assertIn(pair["display"], FONT_AXES)
            self.assertIn(pair["body"], FONT_AXES)

    def test_styled_brand_does_not_mutate(self):
        before = copy.deepcopy(BRAND)
        styled = styled_brand(BRAND, EXAMPLE)
        self.assertEqual(BRAND, before)
        self.assertEqual(styled["display_font"], "Cinzel")
        self.assertIn("family=Cinzel:wght@400..900", fonts_query(styled))

    def test_art_is_seeded_and_sized(self):
        for style in GENERATORS:
            self.assertEqual(art_layer(style, 7), art_layer(style, 7), style)
            self.assertIn('viewBox="0 0 1080 1920"', art_layer(style, 7, 1920), style)


class RenderHtmlTest(unittest.TestCase):
    def test_carousel_slides_render(self):
        brand = styled_brand(BRAND, EXAMPLE)
        for i, slide in enumerate(EXAMPLE["slides"], start=1):
            html = render_slide(slide, brand, i, len(EXAMPLE["slides"]), 0, EXAMPLE["theme"], EXAMPLE["seed"])
            self.assertIn("@thestoiccommunicator", html)

    def test_reel_frames_render_one_section_per_time(self):
        brand = styled_brand(BRAND, EXAMPLE)
        for i, beat in enumerate(EXAMPLE["reel"]["beats"]):
            html = render_frames(beat, brand, EXAMPLE["theme"], EXAMPLE["seed"], i, 0.5, [0.0, 0.5, 1.0])
            self.assertEqual(html.count('<section class="frame'), 3)

    def test_copy_is_escaped(self):
        beat = {"kind": "lesson", "headline": "<script>x</script> now", "voice": "x"}
        html = render_frames(beat, styled_brand(BRAND, EXAMPLE), "temple", 1, 0, 0.5, [0.0])
        self.assertNotIn("<script>x", html)


class CaptionsTest(unittest.TestCase):
    def test_ass_colour_is_bgr(self):
        self.assertEqual(ass_color("#112233"), "&H00332211")

    def test_punctuation_restored_and_phrases_break_at_sentences(self):
        words = tuple(Word(i * .3, i * .3 + .25, w) for i, w in enumerate("But Marcus was alive Within months".split()))
        timed = shift(punctuate(words, "But Marcus was alive. Within months,"), 0)
        groups = [[w.text for w in g] for g in phrases(timed)]
        self.assertEqual(groups, [["But", "Marcus", "was"], ["alive."], ["Within", "months,"]])

    def test_one_event_per_word(self):
        timed = [Timed(0, .3, "One"), Timed(.3, .6, "two."), Timed(.7, 1, "Three")]
        ass = build_ass(timed, "#ffcc00", "Impact")
        self.assertEqual(ass.count("Dialogue:"), 3)
        self.assertIn("Style: Cap,Impact", ass)
        self.assertIn("\\1c&H00CCFF&", ass)


class TimelineTest(unittest.TestCase):
    def test_beats_overlap_by_the_transition(self):
        narrations = [Narration(Path("a"), d, ()) for d in (2.0, 3.0, 1.5)]
        slots = timeline(narrations)
        for prev, nxt in zip(slots, slots[1:]):
            self.assertAlmostEqual(nxt.start, prev.start + prev.length - XFADE_S)
            self.assertGreater(nxt.voice_at, nxt.start)
            self.assertGreaterEqual(nxt.voice_at, prev.voice_at + 2.0)
        self.assertAlmostEqual(total_length(slots), sum(s.length for s in slots) - 2 * XFADE_S)


class BriefTest(EmptyHistory):
    def test_brief_values_are_valid(self):
        for seed in range(30):
            brief = creative_brief.roll(random.Random(seed))
            self.assertIn(brief["theme"], THEMES)
            self.assertIn(brief["palette"], PALETTES)
            self.assertIn(brief["fonts"], FONT_PAIRS)
            self.assertIn(brief["pillar"], creative_brief.PILLARS)
            self.assertEqual(len(set(brief["feature_visuals"])), 3)

    def test_avoids_last_look_and_balances_pillars(self):
        self.add_post({"slug": "x", "theme": "temple", "palette": "bloodstone", "fonts": "bebas",
                       "pillar": "think", "reel_style": {"mood": "epic"}})
        for seed in range(30):
            brief = creative_brief.roll(random.Random(seed))
            self.assertNotEqual(brief["theme"], "temple")
            self.assertNotEqual(brief["palette"], "bloodstone")
            self.assertNotEqual(brief["fonts"], "bebas")
            self.assertNotEqual(brief["reel_style"]["mood"], "epic")
            self.assertNotEqual(brief["pillar"], "think")


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(publish, "LEDGER", Path(self.tmp.name) / "published.json")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_record_keeps_each_platform(self):
        publish.record("a", "ig_carousel", "1")
        publish.record("a", "ig_reel", "2")
        publish.record("b", "youtube", "y")
        self.assertEqual(publish.missing("a"), ["youtube"])
        self.assertEqual(publish.missing("b"), ["ig_carousel", "ig_reel"])
        self.assertEqual(publish.entry_for("a")["ig_reel"], "2")

    def test_video_base_switches_raw_to_jsdelivr(self):
        raw = "https://raw.githubusercontent.com/PeaceCrack/thestoiccommunicator/abc123/out/{slug}"
        self.assertEqual(publish.video_base(raw),
                         "https://cdn.jsdelivr.net/gh/PeaceCrack/thestoiccommunicator@abc123/out/{slug}")
        self.assertEqual(publish.video_base("https://cdn.example.com/x"), "https://cdn.example.com/x")

    def test_carousel_items_use_video_only_when_rendered(self):
        post = {"slug": "zz-none", "slides": [{}, {}]}
        items = publish.carousel_items(post, "https://h/out/{slug}", "https://v/out/{slug}")
        self.assertEqual(items[0], {"image": "https://h/out/zz-none/01.jpg", "video": None})

    def test_youtube_metadata(self):
        with mock.patch.dict(os.environ, {"YT_PRIVACY": "unlisted"}):
            meta = publish.youtube_metadata(EXAMPLE)
        self.assertEqual(meta["status"]["privacyStatus"], "unlisted")
        self.assertFalse(meta["status"]["selfDeclaredMadeForKids"])
        with mock.patch.dict(os.environ, {"YT_PRIVACY": "everyone"}):
            with self.assertRaises(publish.PublishError):
                publish.youtube_metadata(EXAMPLE)

    def test_token_is_trimmed_and_reported_safely(self):
        self.assertEqual(publish.clean_token(' "IGAAabc123"\n'), "IGAAabc123")
        self.assertEqual(publish.clean_token("Bearer IGAAx"), "IGAAx")
        report = publish.token_report("IGAAsecretvalue\n")
        self.assertIn("15 chars (16 before trimming)", report)
        self.assertNotIn("secretvalue", report)

    def test_ig_config_requires_env(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(publish.PublishError):
                publish.ig_config()

    def test_failure_on_one_platform_keeps_the_others(self):
        post = {"slug": "p", "caption": "c", "reel_caption": "r", "slides": []}
        with mock.patch.object(publish, "ig_config", return_value={}), \
                mock.patch.object(publish, "publish_carousel", return_value=("c1", [])), \
                mock.patch.object(publish, "publish_reel", side_effect=publish.PublishError("boom")), \
                mock.patch.object(publish, "publish_youtube", return_value=("y1", "public")):
            errors = publish.publish_all(post, list(publish.PLATFORMS))
        self.assertEqual(errors, ["ig_reel: boom"])
        self.assertEqual(publish.missing("p"), ["ig_reel"])


if __name__ == "__main__":
    unittest.main()
