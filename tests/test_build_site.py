"""build_site: structure, policy rules (no store links / prices / ratings / emoji / banned words), SEO output."""
import html
import json
import re
import shutil
import unittest

from helpers import REPO, bs, build, jsonld, make_site

PAGES = ["", "about/", "privacy/", "contact/"]
GAMES = {"iltonggi": "https://iltonggi.ipe.rest", "inkisle": "https://inkisle.ipe.rest",
         "sunmeld": "https://sunmeld.ipe.rest", "claimball": "https://claimball.ipe.rest",
         "patchland": "https://patchland.ipe.rest", "tottertop": "https://tottertop.ipe.rest",
         "mossgarden": "https://mossgarden.ipe.rest", "duskblocks": "https://duskblocks.ipe.rest",
         "bottledmarbles": "https://bottledmarbles.ipe.rest"}
NOT_LIVE = ()
LIVE = [gid for gid in GAMES if gid not in NOT_LIVE]
NOT_RELEASED_PHRASES = {
    "*": ("None is released", "None of them is released", "none is released"),
    "en": ("not released yet",),
    "ja": ("まだどれも公開されて", "公開されておらず"),
    "ko": ("아직 출시된 게임은 없", "출시 전", "출시되지 않", "출시 안 됨"),
    "de": ("Noch ist keines erschienen", "bisher erschienen"),
    "es": ("Ninguno ha salido", "Aún no ha salido", "ha salido todavía"),
    "fr": ("Aucun n’est encore sorti", "Aucun des jeux n’est sorti", "Pas encore."),
    "id": ("Belum ada yang dirilis", "Belum dirilis", "Belum ada satu pun dari game ini yang dirilis"),
    "pt": ("Nenhum foi lançado ainda", "Ainda não lançado", "Nenhum dos jogos foi lançado"),
    "ru": ("Ни одна пока не вышла", "Ни одна из пяти игр", "Пока не вышла"),
    "vi": ("Chưa trò nào được phát hành", "Chưa phát hành", "Chưa trò nào trong các trò chơi được phát hành"),
    "zh": ("目前都尚未发布", "都尚未发布", "尚未发布"),
}


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

    def test_nine_games_listed_and_live_ones_link_to_their_own_sites_and_no_stores(self):
        self.assertEqual([g["id"] for g in self.ctx.games], list(GAMES))
        for lang_dir in ("", "ko/"):
            h = self.read(lang_dir + "index.html")
            for gid in LIVE:
                self.assertIn('href="%s"' % GAMES[gid], h, (lang_dir, gid))
            for store in ("apps.apple.com", "play.google.com", "itunes.apple.com", "testflight.apple.com"):
                self.assertNotIn(store, h.lower())

    def test_patchland_has_no_terms_and_no_journal_yet(self):
        g = {x["id"]: x for x in self.ctx.games}["patchland"]
        self.assertIsNone(g["terms"])
        self.assertIsNone(g["journal"])
        for l in bs.LANGS:
            h = self.read(("" if l == "en" else l + "/") + "index.html")
            card = h.split('id="patchland"')[1].split("</article>")[0]
            self.assertIn('href="https://patchland.ipe.rest"', card, l)
            self.assertNotIn("patchland.ipe.rest/", card.replace('href="https://patchland.ipe.rest"', ""), l)  # no terms, no journal link
            self.assertNotIn("patchland.ipe.rest/", h.split('id="made"')[1].split("</section>")[0], l)  # no making-of row
            self.assertIn('<h3>Patchland</h3>', h, l)

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

    def test_nine_cards_have_full_copy_in_all_11_languages(self):
        for g in self.ctx.games:
            gid = g["id"]
            self.assertEqual(set(g["site"]), {"url", "live"}, gid)
            self.assertEqual(g["site"]["url"], GAMES[gid])
            self.assertEqual(g["site"]["live"], gid not in NOT_LIVE, gid)
            for lang in bs.LANGS:
                for field in ("status", "platform", "pricing", "tagline"):
                    self.assertTrue(g[field][lang].strip(), (gid, lang, field))
                for key, want in (("pros", 3), ("cons", 2)):
                    self.assertEqual(len(g[key]), want, (gid, key))
                    for i, it in enumerate(g[key]):
                        for k in ("h", "p"):
                            self.assertTrue(it[k][lang].strip(), (gid, lang, key, i, k))
                for row in bs.COMPARE_ROWS:
                    self.assertTrue(g["compare"][row][lang].strip(), (gid, lang, row))

    def test_live_cards_never_say_coming_soon_or_in_development(self):
        for g in self.ctx.games:
            if not g["site"]["live"]:
                continue
            for lang in bs.LANGS:
                lang_dir = "" if lang == "en" else lang + "/"
                card = html.unescape(self.read(lang_dir + "index.html")).partition('id="%s"' % g["id"])[2].split("</article>")[0]
                self.assertNotIn("coming soon", card.lower(), (lang_dir, g["id"]))
                self.assertNotIn("in development", card.lower(), (lang_dir, g["id"]))
                self.assertNotIn('class="badge pre"', card, (lang_dir, g["id"]))
                self.assertIn('<span class="badge">%s</span>' % self.ctx.t(lang, "g_live"), card, (lang_dir, g["id"]))

    def test_each_language_lists_all_nine_games_and_only_live_sites_get_a_visit_link(self):
        for lang in bs.LANGS:
            lang_dir = "" if lang == "en" else lang + "/"
            h = self.read(lang_dir + "index.html")
            for g in self.ctx.games:
                gid = g["id"]
                before, _, card = h.partition('id="%s"' % gid)
                self.assertTrue(before.endswith('<article class="game" '), (lang_dir, gid))
                card = card.split("</article>")[0]
                self.assertIn("<h3>%s</h3>" % g["name"][lang], card, (lang_dir, gid))
                self.assertIn('class="tagline"', card, (lang_dir, gid))
                if g["site"]["live"]:
                    self.assertIn('<a class="btn" href="%s" rel="noopener" data-game="%s" data-placement="card">' % (GAMES[gid], gid),
                                  card, (lang_dir, gid))
                else:
                    self.assertNotIn('class="btn"', card, (lang_dir, gid))
                    self.assertNotIn(GAMES[gid], card, (lang_dir, gid))
        self.assertEqual(h.count('data-placement="card"'), len(LIVE))

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
            self.assertEqual(len(games), 9)
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
        for g in self.ctx.games:
            if g["site"]["live"]:
                self.assertIn(g["site"]["url"], l)
            else:
                self.assertNotIn(g["site"]["url"], l)
                self.assertIn(g["name"]["en"], l)
        self.assertEqual(self.read("sitemap.xml").count("<url>"), 4 * len(bs.LANGS))  # home + about + privacy + contact

    def test_no_not_released_wording_once_a_game_is_live(self):
        if not any(g["site"]["live"] for g in json.loads((REPO / "content" / "games.json").read_text(encoding="utf-8"))["games"]):
            self.skipTest("no live game")
        for lang in bs.LANGS:
            data = json.loads((REPO / "content" / "i18n" / (lang + ".json")).read_text(encoding="utf-8"))
            texts = [data[k] for k in ("home_desc", "games_lead", "made_now") if k in data]
            for name in ("about", "contact"):
                texts.append((REPO / "content" / "pages" / lang / (name + ".md")).read_text(encoding="utf-8"))
            for text in texts:
                for phrase in NOT_RELEASED_PHRASES.get(lang, ()) + NOT_RELEASED_PHRASES["*"]:
                    self.assertNotIn(phrase, text, (lang, phrase))

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
        d["games"][0]["site"]["url"] = "https://example.com/"
        f.write_text(json.dumps(d), encoding="utf-8")
        _, errs = bs.make_ctx(root)
        self.assertTrue(any("url must be" in e for e in errs), errs)

    def test_site_url_must_stay_on_ipe_rest(self):
        root = make_site()
        self.addCleanup(shutil.rmtree, root, True)
        f = root / "content" / "games.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        for g in d["games"]:
            if g["id"] == "tottertop":
                g["site"]["url"] = "https://apps.apple.com/app/tottertop"  # no store links
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        _, errs = bs.make_ctx(root)
        self.assertTrue(any("site url must be" in e for e in errs), errs)

    def test_site_needs_a_url_and_the_live_flag(self):
        root = make_site()
        self.addCleanup(shutil.rmtree, root, True)
        f = root / "content" / "games.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        for g in d["games"]:
            if g["id"] == "mossgarden":
                g["site"] = {"url": "https://mossgarden.ipe.rest"}  # no live flag
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        _, errs = bs.make_ctx(root)
        self.assertTrue(any("site must be" in e for e in errs), errs)

if __name__ == "__main__":
    unittest.main()
