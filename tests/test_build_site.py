"""build_site: structure, policy rules (no store links / prices / ratings / emoji / banned words), SEO output."""
import json
import re
import shutil
import unittest

from helpers import REPO, bs, build, jsonld, make_site

PAGES = ["", "about/", "privacy/", "contact/"]
GAMES = {"iltonggi": "https://iltonggi.ipe.rest", "inkisle": "https://inkisle.ipe.rest",
         "sunmeld": "https://sunmeld.ipe.rest", "claimball": "https://claimball.ipe.rest"}


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
        for gone in ("terms", "journal", "releases", "support", "feed.xml"):
            self.assertFalse((self.root / gone).exists(), gone)
        self.assertEqual(self.ctx.langs, ["en", "ko"])

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
        self.assertIn("Pricing will be announced closer to launch", g["pricing"]["en"])
        self.assertIn("90", g["compare"]["length"]["en"])
        inkisle = {x["id"]: x for x in self.ctx.games}["inkisle"]
        self.assertIn("광고 없음", inkisle["pricing"]["ko"])

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
        self.assertNotIn("googletagmanager", h)

    def test_robots_llms_sitemap(self):
        r = self.read("robots.txt")
        self.assertIn("Sitemap: https://play.ipe.rest/sitemap.xml", r)
        self.assertIn("GPTBot", r)
        l = self.read("llms.txt")
        for gid, u in GAMES.items():
            self.assertIn(u, l)
        self.assertEqual(self.read("sitemap.xml").count("<url>"), 8)

    def test_i18n_keys_match(self):
        for l in ("en", "ko"):
            data = json.loads((REPO / "content" / "i18n" / (l + ".json")).read_text(encoding="utf-8"))
            self.assertEqual(sorted(data), sorted(bs.KEYS), l)

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
