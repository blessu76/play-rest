"""Journal: sources -> list / posts / RSS / home cards / sitemap / llms, KST time rules, the shared localtime module,
validation, and the empty state (a site with no posts must stay whole). Posts here are test-only fixtures."""
import hashlib
import json
import re
import shutil
import unittest
import xml.etree.ElementTree as ET

from helpers import JOURNAL_FIXTURES, NOW, REPO, add_post, bs, build, jsonld, make_site, make_site_with_posts, post_md

import check_sitemap as cs  # noqa: E402

JS = REPO / "content" / "shared" / "ipe-localtime.js"
SHA = REPO / "content" / "shared" / "ipe-localtime.sha256"
# newest first: killing-time-honestly (11-02), turn-based-in-a-break (11-01), why-rounds-end (10-31), one-more-old-post (10-30)
ORDER = ["killing-time-honestly", "turn-based-in-a-break", "why-rounds-end", "one-more-old-post"]
TIME_RE = r'<time datetime="(\d{4}-\d\d-\d\dT\d\d:\d\d\+09:00)" data-ipe-time dir="ltr">(\d{4}-\d\d-\d\d \d\d:\d\d) KST</time>'


class Reader(unittest.TestCase):
    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")


class WithPosts(Reader):
    @classmethod
    def setUpClass(cls):
        cls.root = make_site_with_posts()
        cls.ctx = build(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def test_pages_exist_in_both_languages(self):
        for pre in ("", "ko/"):
            self.assertTrue((self.root / (pre + "journal/index.html")).is_file())
            self.assertTrue((self.root / (pre + "journal/feed.xml")).is_file())
            for slug in ORDER:
                self.assertTrue((self.root / (pre + "journal/%s/index.html" % slug)).is_file(), (pre, slug))
        self.assertEqual([p["slug"] for p in self.ctx.posts], ORDER)

    def test_list_is_newest_first_with_titles_and_excerpts(self):
        for pre, i in (("", 2), ("ko/", 4)):
            h = self.read(pre + "journal/index.html")
            hrefs = re.findall(r'<li class="jitem">.*?<h2><a href="([^"]+)">', h, re.S)
            self.assertEqual(hrefs, ["/%sjournal/%s/" % (pre, s) for s in ORDER])
            self.assertIn(JOURNAL_FIXTURES["killing-time-honestly"][i], h)
            self.assertIn(JOURNAL_FIXTURES["killing-time-honestly"][i + 1], h)
            self.assertNotIn("noindex", h)
            self.assertIn('<meta name="robots" content="index,follow', h)
            self.assertEqual(h.count("<h1>"), 1)

    def test_home_shows_exactly_the_newest_three_cards(self):
        for pre, i in (("", 2), ("ko/", 4)):
            h = self.read(pre + "index.html")
            sec = re.search(r'<section class="sec tint" id="journal">.*?</section>', h, re.S).group(0)
            self.assertEqual(sec.count('class="journal-card"'), 3)
            self.assertEqual(re.findall(r'class="journal-card__link" href="([^"]+)"', sec), ["/%sjournal/%s/" % (pre, s) for s in ORDER[:3]])
            self.assertNotIn(JOURNAL_FIXTURES[ORDER[3]][i], sec)
            self.assertIn('href="/%sjournal/"' % pre, sec)
            ids = re.findall(r'<section class="(?:hero|sec(?: tint)?)"(?: id="(\w+)")?', h)
            self.assertEqual(ids, ["", "philosophy", "games", "compare", "choose", "made", "journal", "studio"])
            nums = re.findall(r'<span class="sn mono">(\d\d)</span>', h)
            self.assertEqual(nums, ["01", "02", "03", "04", "05", "06", "07"])

    def test_every_time_is_kst_with_data_ipe_time_and_static_kst_text(self):
        pages = ["index.html", "ko/index.html", "journal/index.html", "ko/journal/index.html"] + [
            "%sjournal/%s/index.html" % (pre, s) for pre in ("", "ko/") for s in ORDER]
        for f in pages:
            h = self.read(f)
            times = re.findall(r"<time [^>]*>[^<]*</time>", h)
            stamps = [t for t in times if "data-ipe-time" in t]
            self.assertTrue(stamps, f)
            for t in stamps:
                m = re.fullmatch(TIME_RE, t)
                self.assertTrue(m, (f, t))
                self.assertEqual(m.group(1)[:10], m.group(2)[:10])
                self.assertEqual(m.group(1)[11:16], m.group(2)[11:16])
        h = self.read("journal/killing-time-honestly/index.html")
        self.assertIn('<time datetime="2026-11-02T08:05+09:00" data-ipe-time dir="ltr">2026-11-02 08:05 KST</time>', h)

    def test_localtime_module_is_inlined_byte_for_byte_and_pinned(self):
        canon = JS.read_bytes()
        self.assertEqual(hashlib.sha256(canon).hexdigest(), SHA.read_text().split()[0])
        self.assertTrue(canon.decode("utf-8").startswith("/* ipe-localtime v2 "))
        want = hashlib.sha256(canon).hexdigest()
        for f in ("index.html", "ko/index.html", "journal/index.html", "journal/why-rounds-end/index.html", "ko/journal/why-rounds-end/index.html"):
            h = self.read(f)
            inline = [s for s in re.findall(r"<script>(.*?)</script>", h, re.S) if "ipe-localtime" in s[:40]]
            self.assertEqual(len(inline), 1, f)
            self.assertEqual(hashlib.sha256(inline[0].encode("utf-8")).hexdigest(), want, f)
            self.assertTrue(h.rstrip().endswith("</script></body></html>"), f)
            self.assertNotIn('src="/assets/ipe-localtime', h)

    def test_post_page(self):
        h = self.read("journal/turn-based-in-a-break/index.html")
        k = self.read("ko/journal/turn-based-in-a-break/index.html")
        self.assertIn("<h1>Turn-based games that fit in a break</h1>", h)
        self.assertIn("<h1>쉬는 시간에 끝나는 턴제 게임</h1>", k)
        self.assertIn('<html lang="ko"', k)
        for frag in ("<h2>First point</h2>", "<strong>bold</strong>", "<blockquote><p>A quiet quote.</p></blockquote>", "<li>two</li>", "<code>code</code>"):
            self.assertIn(frag, h)
        self.assertIn('<link rel="canonical" href="https://play.ipe.rest/journal/turn-based-in-a-break/">', h)
        self.assertIn('<link rel="canonical" href="https://play.ipe.rest/ko/journal/turn-based-in-a-break/">', k)
        for l, pth in (("en", "/journal/turn-based-in-a-break/"), ("ko", "/ko/journal/turn-based-in-a-break/"), ("x-default", "/journal/turn-based-in-a-break/")):
            self.assertIn('hreflang="%s" href="https://play.ipe.rest%s"' % (l, pth), h)
        self.assertIn('<meta property="og:type" content="article">', h)
        self.assertIn('href="/journal/"', h)
        self.assertIn("Back to the journal", h)
        self.assertIn("저널로 돌아가기", k)
        self.assertRegex(h, r'<p class="updated mono">[^<]+: <time datetime="2026-11-01">2026-11-01</time></p>')

    def test_post_json_ld(self):
        for pre, lang in (("", "en"), ("ko/", "ko")):
            g = jsonld(self.read(pre + "journal/turn-based-in-a-break/index.html"))[0]["@graph"]
            post = [n for n in g if n["@type"] == "BlogPosting"][0]
            self.assertEqual(post["datePublished"], "2026-11-01T09:30+09:00")
            self.assertEqual(post["dateModified"], "2026-11-01T09:30+09:00")
            self.assertEqual(post["inLanguage"], lang)
            self.assertEqual(post["author"], {"@id": bs.ORG_ID})
            self.assertEqual(post["url"], "https://play.ipe.rest/%sjournal/turn-based-in-a-break/" % pre)
            crumbs = [n for n in g if n["@type"] == "BreadcrumbList"][0]["itemListElement"]
            self.assertEqual([c["position"] for c in crumbs], [1, 2, 3])
            self.assertNotIn("item", crumbs[-1])
        lst = [n for n in jsonld(self.read("journal/index.html"))[0]["@graph"] if n["@type"] == "CollectionPage"][0]
        self.assertEqual(len(lst["mainEntity"]["itemListElement"]), 4)

    def test_rss_feeds(self):
        for pre, lang, title in (("", "en", "ipe() Games Journal"), ("ko/", "ko", "ipe() Games 저널")):
            root = ET.fromstring(self.read(pre + "journal/feed.xml"))
            ch = root.find("channel")
            self.assertEqual(ch.findtext("title"), title)
            self.assertEqual(ch.findtext("language"), lang)
            items = ch.findall("item")
            self.assertEqual([i.findtext("link") for i in items], ["https://play.ipe.rest/%sjournal/%s/" % (pre, s) for s in ORDER])
            self.assertEqual(items[0].findtext("pubDate"), "Mon, 02 Nov 2026 08:05:00 +0900")
            self.assertEqual(ch.findtext("lastBuildDate"), "Mon, 02 Nov 2026 08:05:00 +0900")
            self.assertTrue(all(i.findtext("description") for i in items))
            h = self.read(pre + "index.html")
            self.assertIn('<link rel="alternate" type="application/rss+xml" title="%s" href="/%sjournal/feed.xml">' % (title, pre), h)

    def test_nav_and_footer_link_to_the_journal(self):
        for pre, label in (("", "Journal"), ("ko/", "저널")):
            for f in ("index.html", "about/index.html", "journal/index.html", "journal/why-rounds-end/index.html"):
                h = self.read(pre + f)
                nav = re.search(r'<nav class="nav".*?</nav>', h, re.S).group(0)
                self.assertIn('<a href="/%sjournal/"' % pre, nav, (pre, f))
                self.assertIn(">%s</a>" % label, nav)
                foot = re.search(r"<footer.*</footer>", h, re.S).group(0)
                self.assertIn('<li><a href="/%sjournal/">%s</a></li>' % (pre, label), foot)
        self.assertIn('<a href="/journal/" aria-current="page">Journal</a>', self.read("journal/why-rounds-end/index.html"))
        self.assertIn('<link rel="alternate" type="application/rss+xml"', self.read("404.html"))

    def test_sitemap_with_hreflang_and_lastmod(self):
        sm = self.read("sitemap.xml")
        self.assertEqual(sm.count("<url>"), 8 + 2 + 2 * 4)
        self.assertIn("<loc>https://play.ipe.rest/journal/</loc><lastmod>2026-11-02</lastmod>", sm)
        self.assertIn("<loc>https://play.ipe.rest/ko/journal/why-rounds-end/</loc><lastmod>2026-10-31</lastmod>", sm)
        self.assertIn('hreflang="ko" href="https://play.ipe.rest/ko/journal/why-rounds-end/"', sm)
        self.assertIn("<loc>https://play.ipe.rest/</loc><lastmod>2026-11-02</lastmod>", sm)  # home shows the cards
        errs, urls = cs.check(self.root, NOW)
        self.assertEqual(errs, [])
        self.assertEqual(len(urls), 8 + 2 + 2 * 4)

    def test_sitemap_check_catches_a_missing_post(self):
        (self.root / "journal/why-rounds-end/index.html").rename(self.root / "journal/why-rounds-end/x.html")
        self.addCleanup((self.root / "journal/why-rounds-end/x.html").rename, self.root / "journal/why-rounds-end/index.html")
        self.assertTrue(any("no file" in e for e in cs.check(self.root, NOW)[0]))

    def test_sitemap_check_catches_a_post_missing_from_the_sitemap(self):
        sm = self.root / "sitemap.xml"
        text = sm.read_text()
        self.addCleanup(sm.write_text, text)
        start = text.index("<url><loc>https://play.ipe.rest/journal/why-rounds-end/</loc>")
        sm.write_text(text[:start] + text[text.index("</url>", start) + 6:])
        self.assertTrue(any("missing from sitemap: https://play.ipe.rest/journal/why-rounds-end/" in e for e in cs.check(self.root, NOW)[0]))

    def test_llms_lists_the_journal(self):
        t = self.read("llms.txt")
        self.assertIn("## Journal", t)
        self.assertIn("https://play.ipe.rest/journal/feed.xml", t)
        for s in ORDER:
            self.assertIn("https://play.ipe.rest/journal/%s/" % s, t)
        self.assertNotIn("no journal", t)
        self.assertIn("[Journal](https://play.ipe.rest/journal/)", t)

    def test_title_limits_and_policy_still_hold(self):
        for f in ("journal/index.html", "ko/journal/index.html", "journal/turn-based-in-a-break/index.html", "ko/journal/killing-time-honestly/index.html"):
            h = self.read(f)
            self.assertLessEqual(len(re.search(r"<title>(.*?)</title>", h).group(1)), bs.TITLE_MAX, f)
            self.assertEqual(bs.text_problems("x", re.sub(r"<script[^>]*>.*?</script>", "", h, flags=re.S)), [])
            self.assertNotIn("googletagmanager", h)

    def test_build_is_deterministic(self):
        a = bs.build_all(self.ctx)
        ctx2, errs = bs.make_ctx(self.root)
        self.assertEqual(errs, [])
        self.assertEqual(a, bs.build_all(ctx2))


class EmptyJournal(Reader):
    """no posts at all: the list says so, the feed is valid, the home page and sitemap carry no journal parts"""

    @classmethod
    def setUpClass(cls):
        cls.root = make_site()
        cls.ctx = build(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def test_list_shows_an_empty_state_and_is_noindex(self):
        for pre, text in (("", "No posts yet."), ("ko/", "아직 올라온 글이 없습니다.")):
            h = self.read(pre + "journal/index.html")
            self.assertIn(text, h)
            self.assertIn("noindex", h)
            self.assertNotIn("<ol", h)
            self.assertIn('class="jempty"', h)
            self.assertIn("<h1>", h)

    def test_feed_is_valid_with_no_items(self):
        for pre in ("", "ko/"):
            ch = ET.fromstring(self.read(pre + "journal/feed.xml")).find("channel")
            self.assertEqual(ch.findall("item"), [])
            self.assertIsNone(ch.find("lastBuildDate"))

    def test_home_has_no_journal_section_and_keeps_its_numbers(self):
        for pre in ("", "ko/"):
            h = self.read(pre + "index.html")
            self.assertNotIn('id="journal"', h)
            self.assertNotIn("journal-card", h)
            self.assertEqual(re.findall(r'<span class="sn mono">(\d\d)</span>', h), ["01", "02", "03", "04", "05", "06"])
            self.assertNotIn("ipe-localtime", h)

    def test_sitemap_and_llms_have_no_journal(self):
        self.assertNotIn("/journal/", self.read("sitemap.xml"))
        self.assertNotIn("## Journal", self.read("llms.txt"))
        errs, urls = cs.check(self.root, NOW)
        self.assertEqual((errs, len(urls)), ([], 8))

    def test_nav_still_links_the_journal(self):
        self.assertIn('<a href="/journal/">Journal</a>', self.read("index.html"))
        self.assertIn('<a href="/ko/journal/">저널</a>', self.read("ko/index.html"))

    def test_one_post_and_two_posts_do_not_break_the_cards(self):
        for n in (1, 2):
            root = make_site_with_posts(ORDER[:n])
            self.addCleanup(shutil.rmtree, root, True)
            build(root)
            h = (root / "index.html").read_text(encoding="utf-8")
            self.assertEqual(h.count('class="journal-card"'), n)
            self.assertEqual((root / "sitemap.xml").read_text().count("<url>"), 8 + 2 + 2 * n)


class Validation(unittest.TestCase):
    def setUp(self):
        self.root = make_site()
        self.addCleanup(shutil.rmtree, self.root, True)

    def errors(self):
        return "\n".join(bs.make_ctx(self.root)[1])

    def test_a_good_pair_has_no_errors(self):
        add_post(self.root, "why-rounds-end")
        self.assertEqual(self.errors(), "")

    def test_missing_language_is_reported(self):
        add_post(self.root, "why-rounds-end", langs=("en",))
        self.assertIn("missing the ko version", self.errors())

    def test_published_must_be_a_kst_time(self):
        for bad in ("2026-11-01", "2026-11-01T09:30Z", "2026-11-01T09:30-05:00", "2026-11-01T09:30:00+09:00", "2026-13-01T09:30+09:00", "2026-11-01 09:30 KST"):
            add_post(self.root, "why-rounds-end", published=bad)
            self.assertIn("published must be a KST time", self.errors(), bad)

    def test_published_at_is_an_alias_for_published(self):
        add_post(self.root, "why-rounds-end", published=None, published_at="2026-11-01T09:30+09:00")
        self.assertEqual(self.errors(), "")
        posts = bs.make_ctx(self.root)[0].posts
        self.assertEqual(posts[0]["published"], "2026-11-01T09:30+09:00")
        add_post(self.root, "why-rounds-end", published=None, published_at="2026-11-01")
        self.assertIn("published must be a KST time", self.errors())

    def test_missing_required_fields(self):
        add_post(self.root, "why-rounds-end", description=None)
        self.assertIn("missing description", self.errors())
        add_post(self.root, "why-rounds-end", title=None)
        self.assertIn("missing title", self.errors())

    def test_published_must_match_across_languages(self):
        add_post(self.root, "why-rounds-end")
        (self.root / "content/journal/why-rounds-end.ko.md").write_text(post_md("ko", "why-rounds-end", published="2026-10-31T23:41+09:00"), encoding="utf-8")
        self.assertIn("same published time", self.errors())

    def test_slug_and_file_name_rules(self):
        d = self.root / "content" / "journal"
        d.mkdir(parents=True, exist_ok=True)
        for name in ("feed.en.md", "Bad_Slug.en.md", "two--hyphens.en.md", "no-language.md", "x.fr.md"):
            (d / name).write_text(post_md("en", "why-rounds-end"), encoding="utf-8")
        blob = self.errors()
        self.assertIn("journal/feed.en.md: slug", blob)
        self.assertIn("Bad_Slug", blob)
        self.assertIn("two--hyphens", blob)
        self.assertIn("no-language.md: file name", blob)
        self.assertIn("x.fr.md: file name", blob)

    def test_body_and_text_rules(self):
        d = self.root / "content" / "journal"
        add_post(self.root, "why-rounds-end")
        (d / "why-rounds-end.en.md").write_text("---\ntitle: T\ndescription: D\npublished: 2026-10-31T23:40+09:00\n---\n# Another h1\n\nLike Suika, only $4.99\n", encoding="utf-8")
        blob = self.errors()
        self.assertIn("must not contain a '# ' heading", blob)
        self.assertIn("banned word", blob)
        self.assertIn("prices", blob)

    def test_updated_and_length_rules(self):
        add_post(self.root, "why-rounds-end", updated="2026-10-01")
        self.assertIn("not be before published", self.errors())
        add_post(self.root, "why-rounds-end", description="x" * (bs.DESC_MAX + 1))
        self.assertIn("description longer", self.errors())
        add_post(self.root, "why-rounds-end", title="t" * (bs.TITLE_MAX + 1))
        self.assertIn("title longer", self.errors())
        add_post(self.root, "why-rounds-end", excerpt="e" * (bs.EXCERPT_MAX + 1))
        self.assertIn("excerpt longer", self.errors())

    def test_long_title_falls_back_to_the_bare_title_tag(self):
        long = "A long title that is exactly fifty characters wide"
        add_post(self.root, "why-rounds-end", title=long)
        ctx = build(self.root)
        h = (self.root / "journal/why-rounds-end/index.html").read_text(encoding="utf-8")
        self.assertIn("<title>%s</title>" % long, h)
        self.assertEqual(ctx.posts[0]["langs"]["en"]["title"], long)

    def test_optional_updated_changes_modified_date_and_lastmod(self):
        add_post(self.root, "why-rounds-end", updated="2026-11-02")
        build(self.root)
        h = (self.root / "journal/why-rounds-end/index.html").read_text(encoding="utf-8")
        ld = [n for n in jsonld(h)[0]["@graph"] if n["@type"] == "BlogPosting"][0]
        self.assertEqual((ld["datePublished"], ld["dateModified"]), ("2026-10-31T23:40+09:00", "2026-11-02"))
        self.assertIn("<loc>https://play.ipe.rest/journal/why-rounds-end/</loc><lastmod>2026-11-02</lastmod>", (self.root / "sitemap.xml").read_text())

    def test_blockquote_markdown(self):
        self.assertEqual(bs.markdown("> one\n> two\n\nafter"), "<blockquote><p>one two</p></blockquote>\n<p>after</p>")


class Repo(unittest.TestCase):
    def test_no_fixture_posts_are_committed(self):
        found = sorted(p.name for p in (REPO / "content" / "journal").glob("*.md"))
        for s in JOURNAL_FIXTURES:
            self.assertFalse([f for f in found if f.startswith(s)], found)

    def test_sources_are_not_deployed(self):
        wf = (REPO / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("--exclude='content'", wf)
        self.assertFalse((REPO / "assets" / "ipe-localtime.js").exists())

    def test_journal_css_reading_text_floor(self):
        css = re.sub(r"/\*.*?\*/", "", (REPO / "assets" / "play.css").read_text(encoding="utf-8"), flags=re.S)
        for sel in (".journal-card h3", ".journal-card p", ".jitem h2", ".post-meta"):
            m = re.search(r"(?m)(?:^|,)%s(?:,[^{]*)?\{[^}]*font-size:(\d+)px" % re.escape(sel), css)
            self.assertTrue(m, sel)
            self.assertGreaterEqual(int(m.group(1)), 16, sel)
        self.assertNotRegex(css, r"journal[^{]*\{[^}]*font-size:(?:1[0-5]|[0-9])px")


if __name__ == "__main__":
    unittest.main()
