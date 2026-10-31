"""The 11 languages of decision 0087: every language is built whole, hreflang is symmetric, no link points at a page that
does not exist, the nine AI translations say so and link to the English original, and the journal stays en + ko only."""
import html
import json
import re
import shutil
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from helpers import NOW, REPO, add_post, bs, build, jsonld, make_site, make_site_with_posts

import check_sitemap as cs  # noqa: E402

SLUGS = ("", "about/", "privacy/", "contact/")
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}


def pre(lang):
    return "" if lang == "en" else lang + "/"


def html_files(root):
    return sorted(p for p in Path(root).rglob("*.html") if not {"content", "assets"} & set(p.relative_to(root).parts))


def head_alternates(h):
    return dict(re.findall(r'<link rel="alternate" hreflang="([\w-]+)" href="([^"]+)">', h))


class AllLanguages(unittest.TestCase):
    """built with real journal fixtures (en + ko posts), so the journal rules are checked with posts present"""

    @classmethod
    def setUpClass(cls):
        cls.root = make_site_with_posts()
        cls.ctx = build(cls.root)
        cls.i18n = cls.ctx.i18n

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")

    def test_the_eleven_languages(self):
        self.assertEqual(list(bs.LANGS), ["en", "ko", "ja", "zh", "es", "pt", "id", "ru", "vi", "fr", "de"])
        self.assertNotIn("ar", bs.LANGS)  # Arabic is not on this portal
        self.assertEqual(self.ctx.langs, list(bs.LANGS))
        self.assertEqual(bs.MT_LANGS, ("ja", "zh", "es", "pt", "id", "ru", "vi", "fr", "de"))
        for l in bs.LANGS:
            for s in SLUGS:
                h = self.read(pre(l) + s + "index.html")
                self.assertIn('<html lang="%s" dir="ltr">' % l, h, (l, s))
                self.assertIn('<meta property="og:locale" content="%s">' % bs.LANGS[l][1], h, (l, s))

    def test_jsonld_in_language(self):
        for l in bs.LANGS:
            for s in SLUGS:
                for block in jsonld(self.read(pre(l) + s + "index.html")):
                    for node in block.get("@graph", [block]):
                        if "inLanguage" in node:
                            self.assertEqual(node["inLanguage"], l, (l, s, node.get("@type")))

    def test_hreflang_is_symmetric_with_x_default(self):
        pages = {}
        for f in html_files(self.root):
            h = f.read_text(encoding="utf-8")
            if 'name="robots" content="noindex' in h:
                continue
            canon = re.search(r'<link rel="canonical" href="([^"]+)">', h).group(1)
            pages[canon] = (re.search(r'<html lang="([\w-]+)"', h).group(1), head_alternates(h))
        self.assertGreaterEqual(len(pages), 4 * 11 + 2 * 5)
        for canon, (lang, alts) in pages.items():
            self.assertEqual(alts.get(lang), canon, canon)  # lists itself
            self.assertIn("x-default", alts, canon)
            self.assertEqual(alts["x-default"], alts.get("en"), canon)
            for l, target in alts.items():
                if l == "x-default":
                    continue
                self.assertIn(target, pages, (canon, l))  # the target exists and is indexable
                self.assertEqual(pages[target][0], l, (canon, target))
                self.assertEqual(pages[target][1].get(lang), canon, ("not reciprocal", canon, target))
        for l in bs.LANGS:  # home and the three pages list all 11 languages
            self.assertEqual(set(pages[bs.url(bs.path_home(l))][1]) - {"x-default"}, set(bs.LANGS), l)

    def test_no_link_to_a_missing_page(self):
        for f in html_files(self.root):
            h = f.read_text(encoding="utf-8")
            for href in re.findall(r'href="(/[^"]*)"', h):
                p = html.unescape(href).split("#")[0].split("?")[0]
                target = self.root / p.lstrip("/")
                ok = target.is_file() or (target / "index.html").is_file()
                self.assertTrue(ok, (str(f.relative_to(self.root)), href))

    def test_language_menu(self):
        for l in bs.LANGS:
            for s in SLUGS:
                h = self.read(pre(l) + s + "index.html")
                menu = re.search(r'<details class="langsw"><summary aria-label="([^"]+)">.*?</summary><ul class="langsw__list"[^>]*>(.*?)</ul></details>', h, re.S)
                self.assertIsNotNone(menu, (l, s))
                self.assertEqual(menu.group(1), "%s: %s" % (self.i18n[l]["lang_label"], bs.LANGS[l][0]))
                items = re.findall(r'<li><a href="([^"]+)" hreflang="(\w+)" lang="\2"( aria-current="true")?>([^<]+)</a></li>', menu.group(2))
                self.assertEqual([i[1] for i in items], list(bs.LANGS), (l, s))
                self.assertEqual([i[1] for i in items if i[2]], [l])
                self.assertEqual({i[1]: i[0] for i in items}, {x: "/" + pre(x) + s for x in bs.LANGS})  # same page in each language
                self.assertEqual([i[3] for i in items], [html.escape(v[0]) for v in bs.LANGS.values()])

    def test_ai_translation_label_and_original_link(self):
        for l in bs.LANGS:
            for s in SLUGS:
                h = self.read(pre(l) + s + "index.html")
                note = re.search(r'<div class="mtnote" role="note"><div class="wrap"><p>(.*?) <a href="([^"]+)" hreflang="en">(.*?)</a></p></div></div>', h)
                if l in bs.MAIN_LANGS:
                    self.assertNotIn("mtnote", h, (l, s))
                    continue
                self.assertIsNotNone(note, (l, s))
                self.assertEqual(html.unescape(note.group(1)), self.i18n[l]["ai_note"])
                self.assertEqual(note.group(2), "/" + s)  # the English original of this very page
                self.assertEqual(html.unescape(note.group(3)), self.i18n[l]["ai_original"])
                self.assertLess(h.index("mtnote"), h.index("<h1"), (l, s))  # said before the content starts

    def test_ai_strings_are_translated(self):
        en = self.i18n["en"]
        for l in bs.MT_LANGS:
            for k in bs.MT_KEYS:
                self.assertNotEqual(self.i18n[l][k], en[k], (l, k))

    def test_game_names_stay_in_latin_letters(self):
        for l in ("en",) + bs.MT_LANGS:  # the translations keep the English names (ko has its own Korean names, written by ipe())
            h = self.read(pre(l) + "index.html")
            for name in ("Iltonggi", "Inkisle", "Sunmeld", "Claimball"):
                self.assertIn("<h3>%s</h3>" % name, h, (l, name))
        ja = self.read("ja/index.html")
        self.assertNotIn(self.read("index.html").split('<p class="tagline">')[1].split("<")[0], ja)  # the tagline is translated

    def test_game_site_links_use_the_language_when_it_exists(self):
        ja, vi = self.read("ja/index.html"), self.read("vi/index.html")
        self.assertIn('href="https://iltonggi.ipe.rest/ja/terms/"', ja)
        self.assertIn('href="https://iltonggi.ipe.rest/ja/blog/"', ja)
        self.assertIn('href="https://inkisle.ipe.rest/ja/journal/"', ja)
        self.assertIn('href="https://inkisle.ipe.rest/journal/"', vi)  # no vi journal on inkisle: English
        self.assertIn('href="https://sunmeld.ipe.rest/terms/"', ja)

    def test_journal_is_en_and_ko_only(self):
        for l in bs.MT_LANGS:
            self.assertFalse((self.root / l / "journal").exists(), l)
            for s in SLUGS:
                h = self.read(pre(l) + s + "index.html")
                nav = re.search(r'<nav class="nav".*?</nav>', h, re.S).group(0)
                self.assertIn('<a href="/journal/" hreflang="en">%s</a>' % html.escape(self.i18n[l]["nav_journal"]), nav, (l, s))
                foot = re.search(r"<footer.*</footer>", h, re.S).group(0)
                self.assertIn('<li><a href="/journal/" hreflang="en">%s</a></li>' % html.escape(self.i18n[l]["journal_en"]), foot, (l, s))
                self.assertIn('<link rel="alternate" type="application/rss+xml" title="ipe() Games Journal" href="/journal/feed.xml">', h)
                self.assertNotIn("journal-card", h, (l, s))  # no English cards inside a page in another language
                self.assertNotIn('id="journal"', h)
            self.assertEqual(re.findall(r'<span class="sn mono">(\d\d)</span>', self.read(l + "/index.html")), ["01", "02", "03", "04", "05", "06"])
        for l in bs.MAIN_LANGS:
            self.assertIn('id="journal"', self.read(pre(l) + "index.html"))
        post = self.read("journal/why-rounds-end/index.html")
        self.assertEqual(set(head_alternates(post)), {"en", "ko", "x-default"})
        menu = re.search(r'<details class="langsw">.*?</details>', post, re.S).group(0)
        self.assertIn('<a href="/ja/" hreflang="ja" lang="ja">', menu)  # no ja version -> the ja home, never /ja/journal/...

    def test_sitemap(self):
        errs, urls = cs.check(self.root, NOW)
        self.assertEqual(errs, [])
        self.assertEqual(len(urls), 4 * 11 + 2 + 2 * 4)
        tree = ET.parse(self.root / "sitemap.xml")
        for u in tree.getroot().findall("s:url", NS):
            loc = u.findtext("s:loc", namespaces=NS)
            alts = {l.get("hreflang"): l.get("href") for l in u.findall("x:link", NS)}
            self.assertEqual(alts["x-default"], alts["en"], loc)
            if "/journal/" in loc:
                self.assertEqual(set(alts), {"en", "ko", "x-default"}, loc)
                self.assertFalse(any("/%s/journal/" % l in loc for l in bs.MT_LANGS), loc)
            else:
                self.assertEqual(set(alts) - {"x-default"}, set(bs.LANGS), loc)
        for l in bs.MT_LANGS:
            for s in SLUGS:
                self.assertIn(bs.SITE + "/" + l + "/" + s, urls)

    def test_llms_and_langpick(self):
        llms = self.read("llms.txt")
        for l in bs.LANGS:
            self.assertIn("%s (%s)" % (bs.EN_NAMES[l], l), llms)
        self.assertIn("AI translations", llms)
        self.assertIn("The journal is written in English and Korean only.", llms)
        self.assertIn("S=%s" % json.dumps(list(bs.LANGS)), self.read("index.html"))

    def test_feed_is_en_and_ko_only(self):
        self.assertEqual(sorted(str(p.relative_to(self.root)) for p in self.root.rglob("feed.xml")), ["journal/feed.xml", "ko/journal/feed.xml"])


class Sources(unittest.TestCase):
    def setUp(self):
        self.root = make_site()
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_half_a_translation_is_an_error(self):
        (self.root / "content/pages/ja/about.md").unlink()
        ctx, errs = bs.make_ctx(self.root)
        self.assertTrue(any(e.startswith("ja: translation is incomplete") and "pages" in e for e in errs), errs)
        self.assertNotIn("ja", ctx.langs)

    def test_missing_game_text_is_an_error(self):
        f = self.root / "content/i18n/games/de.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        del d["sunmeld"]["compare"]["offline"]
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        _, errs = bs.make_ctx(self.root)
        self.assertTrue(any("games/de.json sunmeld" in e and "compare.offline" in e for e in errs), errs)
        self.assertTrue(any(e.startswith("de: translation is incomplete") for e in errs), errs)

    def test_ai_note_is_required_in_a_translation(self):
        f = self.root / "content/i18n/fr.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        del d["ai_note"]
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        _, errs = bs.make_ctx(self.root)
        self.assertTrue(any("i18n/fr.json: missing ai_note" in e for e in errs), errs)

    def test_policy_words_are_checked_in_translations(self):
        f = self.root / "content/i18n/games/es.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        d["iltonggi"]["tagline"] = "Como Suika"
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        _, errs = bs.make_ctx(self.root)
        self.assertTrue(any("games/es.json iltonggi" in e for e in errs), errs)

    def test_a_journal_post_in_another_language_is_rejected(self):
        add_post(self.root, "why-rounds-end")
        src = self.root / "content/journal/why-rounds-end.en.md"
        (self.root / "content/journal/why-rounds-end.ja.md").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        _, errs = bs.make_ctx(self.root)
        self.assertTrue(any("why-rounds-end.ja.md" in e for e in errs), errs)


class Styles(unittest.TestCase):
    css = (REPO / "assets" / "play.css").read_text(encoding="utf-8")

    def test_cjk_line_breaking_and_system_fonts(self):
        self.assertIn(":lang(ja),:lang(zh){line-break:strict", self.css)
        self.assertRegex(self.css, r'html:lang\(ja\)\{--font:Inter,"Hiragino Sans"')
        self.assertRegex(self.css, r'html:lang\(zh\)\{--font:Inter,"PingFang SC"')
        self.assertEqual(re.findall(r"@font-face\{font-family:([^;]+);", self.css), ["Inter", '"JetBrains Mono"', '"JetBrains Mono"'])  # no new web fonts
        self.assertNotRegex(self.css, r"@import|fonts\.googleapis")

    def test_long_words_do_not_overflow(self):
        self.assertIn("overflow-wrap:anywhere", re.search(r"\nbody\{[^}]*\}", self.css).group(0))
        self.assertIn(":is(:lang(de),:lang(ru)) :is(h3,h4,.btn,.badge", self.css)
        self.assertIn("max-width:100%", re.search(r"\n\.btn\{[^}]*\}", self.css).group(0))

    def test_language_menu_fits_a_small_screen(self):
        rule = re.search(r"\.langsw__list\{[^}]*\}", self.css).group(0)
        self.assertIn("position:absolute", rule)
        self.assertIn("width:min(360px,calc(100% - 2 * var(--gutter)))", rule)
        self.assertIn(".bar{position:relative}", self.css)


if __name__ == "__main__":
    unittest.main()
