"""build_site: structure, policy rules (no store links / prices / ratings / emoji / banned words), SEO output."""
import html
import json
import re
import shutil
import unittest

from helpers import REPO, bs, build, jsonld, make_site

PAGES = ["", "about/", "privacy/", "contact/"]
GAMES = {"iltonggi": "https://iltonggi.ipe.rest", "inkisle": "https://inkisle.ipe.rest",
         "sunmeld": "https://sunmeld.ipe.rest", "claimball": "https://claimball.ipe.rest"}


CLAIMBALL_PRICE_EN = "Free to try. One purchase unlocks everything. No ads, no subscription."
CLAIMBALL_PRICE_KO = "무료로 해 보고, 한 번 결제하면 전부 열려요. 광고도 구독도 없어요."


class Built(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = make_site()
        cls.ctx = build(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")

    def all_html(self):
        for lang_dir in ("", "ko/"):
            for p in PAGES:
                yield lang_dir + p, self.read(lang_dir + p + "index.html")
        yield "404.html", self.read("404.html")

    def test_required_pages_in_both_languages(self):
        for lang_dir in ("", "ko/"):
            for p in PAGES:
                self.assertTrue((self.root / (lang_dir + p) / "index.html").is_file(), lang_dir + p)
        for gone in ("terms", "releases", "support", "feed.xml"):
            self.assertFalse((self.root / gone).exists(), gone)
        self.assertEqual(self.ctx.langs, list(bs.LANGS))  # all 11 languages of decision 0087 are built

    def test_repo_basics(self):
        self.assertEqual((REPO / "CNAME").read_text().strip(), "play.ipe.rest")
        self.assertTrue((REPO / ".nojekyll").is_file())
        self.assertFalse((REPO / "docs").exists())

    def test_footer_and_last_updated_everywhere(self):
        for name, h in self.all_html():
            self.assertRegex(h, r'<p class="updated mono">[^<]+: <time datetime="\d{4}-\d{2}-\d{2}">\d{4}-\d{2}-\d{2}</time></p>', name)
            self.assertIn("Davy Kim (ipe Studio)", h, name)
            self.assertIn('href="https://ipe.rest/"', h, name)

    def test_title_and_description_lengths(self):
        for name, h in self.all_html():
            self.assertLessEqual(len(re.search(r"<title>(.*?)</title>", h).group(1)), bs.TITLE_MAX, name)
            self.assertLessEqual(len(re.search(r'<meta name="description" content="([^"]*)"', h).group(1)), bs.DESC_MAX, name)

    def test_hreflang_canonical_and_404(self):
        h = self.read("index.html")
        self.assertIn('<link rel="canonical" href="https://play.ipe.rest/">', h)
        for l, pth in (("en", "/"), ("ko", "/ko/"), ("x-default", "/")):
            self.assertIn('hreflang="%s" href="https://play.ipe.rest%s"' % (l, pth), h)
        self.assertIn('<html lang="ko"', self.read("ko/index.html"))
        self.assertIn('<link rel="canonical" href="https://play.ipe.rest/ko/about/">', self.read("ko/about/index.html"))
        n = self.read("404.html")
        self.assertIn("noindex", n)
        self.assertNotIn('rel="canonical"', n)

    def test_home_section_order(self):
        ids = re.findall(r'<section class="(?:hero|sec(?: tint)?)"(?: id="(\w+)")?', self.read("index.html"))
        self.assertEqual(ids, ["", "philosophy", "games", "compare", "choose", "made", "studio"])

    def test_hero_copy_is_the_confirmed_one(self):
        self.assertIn("<h1>When the round ends, that&#x27;s enough for today.</h1>", self.read("index.html"))
        self.assertIn("<h1>한 판이 끝나면, 오늘은 여기까지</h1>", self.read("ko/index.html"))

    def test_four_games_link_to_their_own_sites_and_no_stores(self):
        for lang_dir in ("", "ko/"):
            h = self.read(lang_dir + "index.html")
            for gid, u in GAMES.items():
                self.assertIn('href="%s"' % u, h, (lang_dir, gid))
            for store in ("apps.apple.com", "play.google.com", "itunes.apple.com", "testflight.apple.com"):
                self.assertNotIn(store, h.lower())

    def test_terms_links_only_for_games_that_have_terms(self):
        h = self.read("index.html")
        for gid in ("iltonggi", "sunmeld", "claimball"):
            self.assertRegex(h, r'href="https://%s\.ipe\.rest/(en/)?terms/"' % gid)
        self.assertNotIn("inkisle.ipe.rest/terms", h)
        self.assertNotIn("inkisle.ipe.rest/en/terms", h)
        self.assertNotIn('href="/terms/"', h)

    def test_claimball_card_follows_the_brief(self):
        g = {x["id"]: x for x in self.ctx.games}["claimball"]
        blob = json.dumps(g, ensure_ascii=False)
        self.assertNotIn("Paid", blob)
        self.assertEqual(g["pricing"]["en"], CLAIMBALL_PRICE_EN)
        self.assertEqual(g["pricing"]["ko"], CLAIMBALL_PRICE_KO)
        self.assertIn("90", g["compare"]["length"]["en"])
        inkisle = {x["id"]: x for x in self.ctx.games}["inkisle"]
        self.assertIn("광고 없음", inkisle["pricing"]["ko"])

    def test_claimball_pricing_is_the_free_to_try_one_purchase_wording_everywhere(self):
        pages = [(d + "index.html", CLAIMBALL_PRICE_EN if d == "" else CLAIMBALL_PRICE_KO) for d in ("", "ko/")]
        for f, want in pages:
            h = html.unescape(self.read(f))
            self.assertIn(want, h, f)
            self.assertGreaterEqual(h.count(want), 3, f)  # card line, third pro, compare table/card
        llms = self.read("llms.txt")
        self.assertIn("Pricing: " + CLAIMBALL_PRICE_EN, llms)
        for _, h in self.all_html():
            self.assertNotIn("Pricing will be announced", h)
            self.assertNotIn("가격은 출시 전에 공지", h)
        self.assertNotIn("Pricing will be announced", llms)
        # the 90 seconds / 6 rivals / 2 leagues figures keep their "may change" caveat
        en = html.unescape(self.read("index.html"))
        self.assertGreaterEqual(en.count("pre-launch proposal"), 3)
        self.assertGreaterEqual(html.unescape(self.read("ko/index.html")).count("출시 전 제안값"), 3)

    def test_inkisle_pricing_is_marked_as_a_plan_in_all_11_languages_and_nothing_else_changed(self):
        # inkisle.ipe.rest says "Not announced yet ... the current plan": the card and compare cell say it is planned, in every language
        games = {x["id"]: x for x in self.ctx.games}
        lead = {"en": "Planned: ", "ko": "출시 전 계획: ", "de": "Geplant: ", "es": "Planeado: ", "fr": "Prévu : ", "id": "Rencana: ",
                "ja": "予定：", "pt": "Planejado: ", "ru": "В планах: ", "vi": "Dự kiến: ", "zh": "计划："}
        self.assertEqual(len(lead), 11)
        for lang, word in lead.items():
            for text in (games["inkisle"]["pricing"][lang], games["inkisle"]["compare"]["pricing"][lang]):
                self.assertTrue(text.startswith(word), (lang, text))
        self.assertEqual(games["inkisle"]["pricing"]["en"], "Planned: every round free · no ads · optional help items")
        self.assertEqual(games["inkisle"]["pricing"]["ko"], "출시 전 계획: 모든 판 무료 · 광고 없음 · 선택형 도움 아이템")
        for gid in ("iltonggi", "sunmeld", "claimball"):  # the other cards are not touched
            for lang, word in lead.items():
                self.assertFalse(games[gid]["pricing"][lang].startswith(word), (gid, lang))
                self.assertFalse(games[gid]["compare"]["pricing"][lang].startswith(word), (gid, lang))

    def test_compare_lead_does_not_claim_only_stated_facts(self):
        for lang in ("en", "ko"):
            lead = json.loads((REPO / "content" / "i18n" / (lang + ".json")).read_text(encoding="utf-8"))["compare_lead"]
            self.assertNotIn("already state", lead)
            self.assertNotIn("이미 적힌", lead)
        self.assertIn("current plans", self.read("index.html"))
        self.assertIn("현재 계획", self.read("ko/index.html"))

    def test_css_reading_text_is_at_least_16px(self):
        css = (REPO / "assets" / "play.css").read_text(encoding="utf-8")
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        sizes = {}  # selector -> font-size px (plain px declarations only; base rules, not media overrides)
        for sel, body in re.findall(r"(?m)^([^@{}\n][^{}]*)\{([^{}]*)\}", css):
            m = re.search(r"(?:^|;)font-size:(\d+(?:\.\d+)?)px", body)
            if m:
                for one in sel.split(","):
                    sizes[one.strip()] = float(m.group(1))
        short_labels = {".badge", ".updated"}  # may be 14px
        for sel, px in sizes.items():
            if sel in short_labels:
                self.assertGreaterEqual(px, 14, sel)
            else:
                self.assertGreaterEqual(px, 16, sel)
        for sel in (".cols ol", ".cmp", ".cmp-card dl div", ".btn", ".textlink", ".nav", ".price", ".note", ".meta", ".small",
                    ".foot-h", ".foot-langs", ".foot-brand p", ".cols h4", ".site-footer li a", ".sub", ".crumbs"):
            self.assertIn(sel, sizes, sel)
        for sel in (".badge", ".updated"):
            self.assertLessEqual(sizes[sel], 16)
        self.assertNotRegex(css, r"font-size:\.\d+em")

    def test_og_source_is_not_deployed(self):
        self.assertFalse((REPO / "assets" / "og-source.html").exists())
        self.assertTrue((REPO / "scripts" / "og-source.html").exists())

    def test_no_leftovers_from_the_template_in_scripts(self):
        for f in ("assets/langpick.js", "assets/play.js"):
            t = (REPO / f).read_text(encoding="utf-8")
            self.assertNotIn("cb-lang", t)
            self.assertNotIn("Sunmeld", t)

    def test_no_prices_ratings_emoji_banned_words_anywhere(self):
        texts = [h for _, h in self.all_html()] + [self.read("llms.txt")]
        for t in texts:
            self.assertEqual(bs.text_problems("x", re.sub(r"<script[^>]*>.*?</script>", "", t, flags=re.S)), [])
        self.assertEqual(bs.text_problems("x", "see the Suika game"), ["x: banned word 'Suika'"])
        self.assertTrue(bs.text_problems("x", "only $4.99"))

    def test_json_ld_has_one_video_game_per_game_and_no_offers(self):
        for lang_dir in ("", "ko/"):
            graph = jsonld(self.read(lang_dir + "index.html"))[0]["@graph"]
            games = [n for n in graph if n["@type"] == "VideoGame"]
            self.assertEqual(sorted(n["url"] for n in games), sorted(GAMES.values()))
            for n in games:
                for bad in ("offers", "aggregateRating", "datePublished", "review"):
                    self.assertNotIn(bad, n)
                self.assertEqual(n["creator"], {"@id": bs.ORG_ID})
            self.assertEqual({n["@type"] for n in graph} - {"VideoGame"}, {"Organization", "WebSite"})

    def test_cache_busting_and_assets_exist(self):
        h = self.read("index.html")
        self.assertIn("/assets/play.css?v=%s" % bs.ASSET_V, h)
        self.assertIn("/assets/play.js?v=%s" % bs.ASSET_V, h)
        for a in ("play.css", "play.js", "favicon.svg", "icon-180.png", "icon-512.png", "og-image.png", "fonts/inter-400.woff2"):
            self.assertTrue((REPO / "assets" / a).is_file(), a)
        self.assertNotIn("fonts.googleapis", h)
        self.assertEqual(h.count("googletagmanager.com/gtag/js"), 1)  # GA4 only (test_ga4.py); no other tag or tracker
        self.assertNotIn("doubleclick", h)

    def test_robots_llms_sitemap(self):
        r = self.read("robots.txt")
        self.assertIn("Sitemap: https://play.ipe.rest/sitemap.xml", r)
        self.assertIn("GPTBot", r)
        l = self.read("llms.txt")
        for gid, u in GAMES.items():
            self.assertIn(u, l)
        self.assertEqual(self.read("sitemap.xml").count("<url>"), 4 * len(bs.LANGS))  # home + about + privacy + contact

    def test_i18n_keys_match(self):
        for l in bs.LANGS:  # ko has no AI-translation strings; en carries them as the source of the nine translations
            data = json.loads((REPO / "content" / "i18n" / (l + ".json")).read_text(encoding="utf-8"))
            self.assertEqual(sorted(data), sorted(tuple(bs.KEYS) + (() if l == "ko" else bs.MT_KEYS)), l)

    def test_markdown_and_front_matter(self):
        meta, body = bs.parse_front("---\ntitle: T\ndescription: \"D\"\n---\n## H\n\nA **b** [l](https://x.y) `c`\n\n- one\n- two\n")
        self.assertEqual(meta, {"title": "T", "description": "D"})
        out = bs.markdown(body)
        for frag in ("<h2>H</h2>", "<strong>b</strong>", '<a href="https://x.y" rel="noopener">l</a>', "<code>c</code>", "<li>two</li>"):
            self.assertIn(frag, out)


class Validation(unittest.TestCase):
    def test_source_problems_are_reported(self):
        root = make_site()
        self.addCleanup(shutil.rmtree, root, True)
        en = root / "content" / "i18n" / "en.json"
        d = json.loads(en.read_text(encoding="utf-8"))
        d["hero_h1"] = "Like Suika, but calm"
        del d["nf_p"]
        en.write_text(json.dumps(d), encoding="utf-8")
        _, errs = bs.make_ctx(root)
        blob = "\n".join(errs)
        self.assertIn("banned word", blob)
        self.assertIn("missing nf_p", blob)

    def test_game_link_off_site_is_rejected(self):
        root = make_site()
        self.addCleanup(shutil.rmtree, root, True)
        f = root / "content" / "games.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        d["games"][0]["url"] = "https://example.com/"
        f.write_text(json.dumps(d), encoding="utf-8")
        _, errs = bs.make_ctx(root)
        self.assertTrue(any("url must be" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
