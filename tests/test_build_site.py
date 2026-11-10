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
         "patchland": "https://patchland.ipe.rest"}


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

    def test_five_games_link_to_their_own_sites_and_no_stores(self):
        for lang_dir in ("", "ko/"):
            h = self.read(lang_dir + "index.html")
            for gid, u in GAMES.items():
                self.assertIn('href="%s"' % u, h, (lang_dir, gid))
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

    def test_upcoming_cards_have_full_card_copy_in_all_11_languages(self):
        up = {x["id"]: x for x in self.ctx.upcoming}
        self.assertEqual(sorted(up), ["mossgarden", "tottertop"])
        for gid, u in up.items():
            self.assertNotIn("url", u)  # no bare url field (no store); the site, once it exists, is site {url, live}
            self.assertEqual(u["icon"], gid + ".png")  # the game-card icon, same naming rule as the games array
            self.assertEqual(len(u["accent"]), 2)
            for c in u["accent"]:
                self.assertRegex(c, r"^#[0-9a-fA-F]{6}$", gid)
            self.assertEqual(set(u["site"]), {"url", "live"})
            self.assertEqual(u["site"]["url"], {"tottertop": "https://tottertop.ipe.rest",
                                                "mossgarden": "https://mossgarden.ipe.rest"}[gid])
            self.assertEqual(u["site"]["live"], gid == "tottertop")  # tottertop.ipe.rest is up; mossgarden.ipe.rest is not yet
            self.assertEqual(u["status"]["en"], "Coming soon")
            self.assertEqual(u["status"]["ko"], "출시 예정")
            for lang in bs.LANGS:
                for field in ("status", "platform", "pricing", "tagline"):
                    self.assertTrue(u[field][lang].strip(), (gid, lang, field))
                for key, want in (("pros", 3), ("cons", 2)):
                    self.assertEqual(len(u[key]), want, (gid, key))
                    for i, it in enumerate(u[key]):
                        for k in ("h", "p"):
                            self.assertTrue(it[k][lang].strip(), (gid, lang, key, i, k))
                for row in bs.COMPARE_ROWS:
                    self.assertTrue(u["compare"][row][lang].strip(), (gid, lang, row))

    def test_upcoming_cards_render_like_the_game_cards_with_the_coming_soon_badge(self):
        # the same card markup and classes as the games (icon, accent, badge); the site button only while site.live is true
        names = {"": ("Tottertop", "Moss Garden"), "ko/": ("기우뚱탑", "이끼정원")}
        badge = {"": "Coming soon", "ko/": "출시 예정"}
        visit = {"": "Official site", "ko/": "공식 사이트"}
        for lang_dir in ("", "ko/"):
            h = self.read(lang_dir + "index.html")
            self.assertNotIn('class="game upcoming"', h, lang_dir)
            for gid, name in zip(("tottertop", "mossgarden"), names[lang_dir]):
                i = h.index('<article class="game" id="%s"' % gid)
                card = h[i:h.index("</article>", i)]
                self.assertIn('style="--a:#', card, (lang_dir, gid))  # the accent drives the card border and badge
                self.assertIn('<img class="game-icon" src="/assets/games/%s.png" width="64" height="64" alt="">' % gid, card, (lang_dir, gid))
                self.assertIn("<h3>%s</h3>" % name, card, (lang_dir, gid))
                self.assertIn(badge[lang_dir], card, (lang_dir, gid))  # the "Coming soon" display is kept
                self.assertIn('class="tagline"', card, (lang_dir, gid))
                self.assertIn('class="price', card, (lang_dir, gid))
                if gid == "tottertop":  # tottertop.ipe.rest is up: the site link, same button as the game cards' visit link
                    self.assertIn('<a class="btn" href="https://tottertop.ipe.rest" rel="noopener" data-game="tottertop" '
                                  'data-placement="card">%s: %s' % (visit[lang_dir], name), card, (lang_dir, gid))
                else:  # mossgarden.ipe.rest is not up yet: the url is in the data, but no link on the card
                    self.assertNotRegex(card, r"<a[ >]", (lang_dir, gid))
                    self.assertNotIn("mossgarden.ipe.rest", card, (lang_dir, gid))
        self.assertNotIn("Tottertop", self.read("llms.txt"))  # llms.txt lists the games with their own sites only
        self.assertNotIn("Moss Garden", self.read("llms.txt"))

    def test_hero_strip_has_an_icon_for_every_card_including_upcoming(self):
        names = {"": {"iltonggi": "Iltonggi", "inkisle": "Inkisle", "sunmeld": "Sunmeld", "claimball": "Claimball",
                      "patchland": "Patchland", "tottertop": "Tottertop", "mossgarden": "Moss Garden"},
                 "ko/": {"iltonggi": "일통기", "inkisle": "잉크아일", "sunmeld": "Sunmeld", "claimball": "Claimball",
                         "patchland": "Patchland", "tottertop": "기우뚱탑", "mossgarden": "이끼정원"}}
        for lang_dir in ("", "ko/"):
            strip = self.read(lang_dir + "index.html").split('<ul class="strip"')[1].split("</ul>")[0]
            self.assertEqual(strip.count("<li>"), 7, lang_dir)
            for gid, name in names[lang_dir].items():
                self.assertIn('<a href="#%s"><img src="/assets/games/%s.png" width="64" height="64" alt="%s"></a>' % (gid, gid, name),
                              strip, (lang_dir, gid))

    def test_principle_chips_keep_both_upcoming_games(self):
        # principle 01 (Tottertop is about a minute a round, Moss Garden a short drop-in tending), 02 few rules and 04 say
        # what's true keep both; 03 (both have optional rewarded ads) and 05 (no AI rival) do not
        names = {"": {"tottertop": "Tottertop", "mossgarden": "Moss Garden"},
                 "ko/": {"tottertop": "기우뚱탑", "mossgarden": "이끼정원"}}
        chip = lambda gid, name: '<li><img src="/assets/games/%s.png" width="24" height="24" alt="">%s</li>' % (gid, name)
        for lang_dir in ("", "ko/"):
            parts = self.read(lang_dir + "index.html").split('<ol class="principles">')[1].split("</ol>")[0]
            parts = parts.split('<li class="principle">')[1:]
            self.assertEqual(len(parts), 5, lang_dir)
            for n in (1, 2, 4):
                for gid in ("tottertop", "mossgarden"):
                    self.assertIn(chip(gid, names[lang_dir][gid]), parts[n - 1], (lang_dir, n, gid))
            for n in (3, 5):
                for gid in ("tottertop", "mossgarden"):
                    self.assertNotIn(chip(gid, names[lang_dir][gid]), parts[n - 1], (lang_dir, n, gid))

    def test_upcoming_site_link_turns_on_with_one_flag(self):
        # mossgarden.ipe.rest is not up yet; when it goes live, site.live in games.json is the only change needed
        root = make_site()
        self.addCleanup(shutil.rmtree, root, True)
        f = root / "content" / "games.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        for u in d["upcoming"]:
            if u["id"] == "mossgarden":
                u["site"]["live"] = True
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        build(root)
        h = (root / "index.html").read_text(encoding="utf-8")
        card = h.partition('id="mossgarden"')[2].split("</article>")[0]
        self.assertIn('<a class="btn" href="https://mossgarden.ipe.rest" rel="noopener" data-game="mossgarden" '
                      'data-placement="card">Official site: Moss Garden', card)
        self.assertIn("Coming soon", card)  # still the pre-release display, no store link
        self.assertNotIn("apps.apple.com", h)
        self.assertNotIn("play.google.com", h)

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

    def test_upcoming_site_url_must_stay_on_ipe_rest(self):
        root = make_site()
        self.addCleanup(shutil.rmtree, root, True)
        f = root / "content" / "games.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        for u in d["upcoming"]:
            if u["id"] == "tottertop":
                u["site"]["url"] = "https://apps.apple.com/app/tottertop"  # no store links
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        _, errs = bs.make_ctx(root)
        self.assertTrue(any("site url must be" in e for e in errs), errs)

    def test_upcoming_site_needs_a_url_and_the_live_flag(self):
        root = make_site()
        self.addCleanup(shutil.rmtree, root, True)
        f = root / "content" / "games.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        for u in d["upcoming"]:
            if u["id"] == "mossgarden":
                u["site"] = {"url": "https://mossgarden.ipe.rest"}  # no live flag
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        _, errs = bs.make_ctx(root)
        self.assertTrue(any("site must be" in e for e in errs), errs)

    def test_upcoming_needs_an_icon_file_and_an_accent(self):
        root = make_site()
        self.addCleanup(shutil.rmtree, root, True)
        f = root / "content" / "games.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        for u in d["upcoming"]:
            if u["id"] == "mossgarden":
                u["icon"] = "no-such-icon.png"
                u["accent"] = ["#4f7c3a"]  # needs two colors
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        _, errs = bs.make_ctx(root)
        self.assertTrue(any("icon file missing" in e for e in errs), errs)
        self.assertTrue(any("accent must be" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
