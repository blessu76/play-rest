"""GA4: one snippet per generated page, game-card event hook, and the privacy / FAQ / llms.txt text that must match it."""
import re
import shutil
import unittest

from helpers import build, bs, make_site

LANGS = ["en", "ko", "ja", "zh", "es", "pt", "id", "ru", "vi", "fr", "de"]
GA_ID = "G-XG4BH800J0"


class Ga4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = make_site()
        cls.ctx = build(cls.root)
        cls.pages = {str(p.relative_to(cls.root)): p.read_text(encoding="utf-8")
                     for p in cls.root.rglob("*.html")}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def page(self, lang, rel):
        return self.pages[(lang + "/" if lang != "en" else "") + rel + "index.html"]

    def test_constant_is_the_ipe_rest_property(self):
        self.assertEqual(bs.GA_MEASUREMENT_ID, GA_ID)

    def test_every_generated_page_has_the_snippet_once(self):
        self.assertGreater(len(self.pages), 40)
        for rel, text in self.pages.items():
            with self.subTest(rel):
                self.assertEqual(text.count(GA_ID), 1)
                self.assertEqual(text.count("googletagmanager.com/gtag/js"), 1)
                self.assertLess(text.index(GA_ID), text.index("</body>"))
                self.assertEqual(text.count("window.gtag('config',GA_ID)"), 1)

    def test_no_snippet_outside_html(self):
        for rel in ("assets/play.js", "assets/play.css"):
            self.assertNotIn(GA_ID, (self.root / rel).read_text(encoding="utf-8"))

    def test_game_visit_buttons_carry_the_game_id(self):
        for lang in LANGS:
            home = self.page(lang, "")
            ids = re.findall(r'<a class="btn" href="https://[^"]+" rel="noopener" data-game="([a-z]+)"', home)
            with self.subTest(lang):
                self.assertEqual(sorted(ids), sorted(g["id"] for g in self.ctx.games))
        self.assertIn("'select_game'", self.page("en", ""))

    def test_privacy_matches_the_tracking(self):
        for lang in LANGS:
            text = self.page(lang, "privacy/")
            with self.subTest(lang):
                self.assertIn("Google Analytics", text)
                self.assertIn("_ga", text)
                self.assertIn("https://tools.google.com/dlpage/gaoptout", text)
                self.assertIn("play-lang", text)
                self.assertIn("play-theme", text)
                self.assertIn(bs.EFFECTIVE, text)
                main = text[text.index("<main"):text.index("</main>")]
                self.assertEqual(len(re.findall(r"<h2[ >]", main)), 10)

    def test_privacy_sources_are_dated_with_effective(self):
        for lang in LANGS:
            src = (self.root / "content/pages" / lang / "privacy.md").read_text(encoding="utf-8")
            with self.subTest(lang):
                self.assertIn("updated: " + bs.EFFECTIVE, src)

    def test_no_stale_no_tracking_claims_about_the_site(self):
        stale = re.compile(r"no analytics|no tracking tags|uses no cookies|accounts, ads or tracking|"
                           r"추적이 없|쿠키를 사용하지 않|분석 도구나 광고 태그를 넣지|추적 태그가 포함", re.I)
        for rel in ("privacy/", "contact/"):
            for lang in LANGS:
                with self.subTest(lang + rel):
                    self.assertIsNone(stale.search(self.page(lang, rel)))
        self.assertIsNone(stale.search((self.root / "llms.txt").read_text(encoding="utf-8")))

    def test_contact_faq_mentions_google_analytics(self):
        for lang in LANGS:
            with self.subTest(lang):
                self.assertIn("Google Analytics", self.page(lang, "contact/"))

    def test_llms_txt_says_so(self):
        text = (self.root / "llms.txt").read_text(encoding="utf-8")
        self.assertIn("collects only basic visit statistics through Google Analytics", text)

    def test_home_card_limits_no_tracking_to_the_games(self):
        for lang in LANGS:
            card = self.ctx.i18n[lang]["p3_p"]
            with self.subTest(lang):
                self.assertNotEqual(card, {"en": "No streak nagging, no ads, no accounts, no tracking."}.get(lang))
        self.assertTrue(self.ctx.i18n["en"]["p3_p"].endswith("inside the games."))


if __name__ == "__main__":
    unittest.main()
