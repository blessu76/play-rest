"""GA4: one snippet per generated page, game-card event hook, and the privacy / FAQ / llms.txt text that must match it."""
import re
import shutil
import unittest

from helpers import build, bs, make_site

LANGS = ["en", "ko", "ja", "zh", "es", "pt", "id", "ru", "vi", "fr", "de"]
GA_ID = "G-XG4BH800J0"
# home-card sentence p3_p as on origin/main before the GA4 commit (it said "no tracking" without limiting it to the games)
OLD_P3_P = {
    'en': 'No streak nagging, no ads, no accounts, no tracking.',
    'ko': '매일 접속하라고 재촉하지 않고, 광고로 끊지 않고, 계정과 추적으로 붙잡지 않습니다.',
    'ja': '連続ログインの催促も、広告も、アカウントも、トラッキングもありません。',
    'zh': '没有连续登录的催促，没有广告，没有账号，没有追踪。',
    'es': 'Sin insistencia con rachas, sin anuncios, sin cuentas, sin seguimiento.',
    'pt': 'Sem insistência por sequências, sem anúncios, sem contas, sem rastreamento.',
    'id': 'Tanpa desakan main setiap hari, tanpa iklan, tanpa akun, tanpa pelacakan.',
    'ru': 'Никаких напоминаний о сериях, никакой рекламы, аккаунтов и слежки.',
    'vi': 'Không thúc giục giữ chuỗi ngày chơi, không quảng cáo, không tài khoản, không theo dõi.',
    'fr': 'Pas de relances pour garder une série, pas de publicité, pas de compte, pas de pistage.',
    'de': 'Kein Drängen wegen Serien, keine Werbung, keine Konten, kein Tracking.',
}


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
                self.assertNotEqual(card, OLD_P3_P[lang])  # the claim was rewritten in every language
                self.assertGreater(len(card), 10)
                self.assertIn(card, self.page(lang, ""))
        self.assertTrue(self.ctx.i18n["en"]["p3_p"].endswith("inside the games."))
        self.assertIn("게임 안에서는", self.ctx.i18n["ko"]["p3_p"])

    def test_footer_game_links_are_tracked_like_the_cards(self):
        ids = sorted(g["id"] for g in self.ctx.games)
        for lang in LANGS:
            foot = re.search(r"<footer.*</footer>", self.page(lang, ""), re.S).group(0)
            found = re.findall(r'<li><a href="https://[^"]+" rel="noopener" data-game="([a-z]+)" data-placement="footer">', foot)
            with self.subTest(lang):
                self.assertEqual(sorted(found), ids)
        self.assertIn("a.getAttribute('data-placement')||'card'", self.page("en", ""))
        self.assertEqual(self.page("en", "").count('data-placement="card"'), len(ids))

    def test_snippet_skips_local_previews(self):
        text = self.page("en", "")
        guard = "var H=location.hostname;if(!H||H==='localhost'||H==='127.0.0.1')return;"
        self.assertEqual(text.count(guard), 1)
        # the guard comes before the gtag loader and before any event listener
        self.assertLess(text.index(guard), text.index("googletagmanager.com/gtag/js"))
        self.assertLess(text.index(guard), text.index("addEventListener('click',track)"))

if __name__ == "__main__":
    unittest.main()
