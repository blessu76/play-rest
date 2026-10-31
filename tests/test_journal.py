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
        self.assertEqual(sm.count("<url>"), 4 * len(bs.LANGS) + 2 + 2 * 4)
        self.assertIn("<loc>https://play.ipe.rest/journal/</loc><lastmod>2026-11-02</lastmod>", sm)
        self.assertIn("<loc>https://play.ipe.rest/ko/journal/why-rounds-end/</loc><lastmod>2026-10-31</lastmod>", sm)
        self.assertIn('hreflang="ko" href="https://play.ipe.rest/ko/journal/why-rounds-end/"', sm)
        self.assertIn("<loc>https://play.ipe.rest/</loc><lastmod>2026-11-02</lastmod>", sm)  # home shows the cards
        errs, urls = cs.check(self.root, NOW)
        self.assertEqual(errs, [])
        self.assertEqual(len(urls), 4 * len(bs.LANGS) + 2 + 2 * 4)

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


class DateGate(Reader):
    """a post dated after the build date (KST) is on no page, list, card, feed, sitemap or llms.txt; a post dated the build day is"""

    def setUp(self):
        self.root = make_site_with_posts(("one-more-old-post", "why-rounds-end", "turn-based-in-a-break", "killing-time-honestly"))
        self.addCleanup(shutil.rmtree, self.root, True)

    def build(self, now):
        ctx, errs = bs.make_ctx(self.root, now)
        self.assertEqual(errs, [])
        bs.clean(self.root)
        for rel, text in bs.build_all(ctx).items():
            f = self.root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")
        return ctx

    def everywhere(self):
        return "\n".join(f.read_text(encoding="utf-8") for f in sorted(self.root.rglob("*")) if f.is_file() and "content" not in f.parts and "assets" not in f.parts)

    def test_future_posts_are_left_out_of_everything(self):
        ctx = self.build("2026-10-31")  # fixtures: 10-30 and 10-31 are out, 11-01 and 11-02 are still in the future
        self.assertEqual([p["slug"] for p in ctx.posts], ["why-rounds-end", "one-more-old-post"])
        self.assertEqual(ctx.scheduled, 2)
        for slug in ("turn-based-in-a-break", "killing-time-honestly"):
            for pre in ("", "ko/"):
                self.assertFalse((self.root / pre / "journal" / slug).exists(), (slug, pre))
        blob = self.everywhere()
        for slug, title in (("turn-based-in-a-break", "Turn-based games that fit in a break"), ("killing-time-honestly", "Killing time, honestly")):
            self.assertNotIn(slug, blob)
            self.assertNotIn(title, blob)
        self.assertNotIn("2026-11-0", self.read("sitemap.xml"))  # not even as a lastmod
        self.assertIn("<loc>https://play.ipe.rest/journal/why-rounds-end/</loc>", self.read("sitemap.xml"))
        self.assertIn("why-rounds-end", self.read("journal/feed.xml"))
        self.assertEqual(self.read("journal/feed.xml").count("<item>"), 2)

    def test_a_post_dated_today_is_included_even_late_in_the_day(self):
        # why-rounds-end is published 2026-10-31T23:40+09:00: it is live for a build on 10-31 (any hour), not for 10-30
        self.assertEqual([p["slug"] for p in self.build("2026-10-31").posts][0], "why-rounds-end")
        ctx = self.build("2026-10-30")
        self.assertEqual([p["slug"] for p in ctx.posts], ["one-more-old-post"])
        self.assertFalse((self.root / "journal" / "why-rounds-end").exists())
        self.assertNotIn("why-rounds-end", self.everywhere())

    def test_the_day_after_brings_the_next_post(self):
        ctx = self.build("2026-11-01")
        self.assertEqual(ctx.posts[0]["slug"], "turn-based-in-a-break")
        self.assertTrue((self.root / "journal/turn-based-in-a-break/index.html").is_file())
        self.assertIn("/journal/turn-based-in-a-break/", self.read("sitemap.xml"))
        self.assertNotIn("killing-time-honestly", self.everywhere())
        self.assertEqual(self.build("2026-11-02").scheduled, 0)

    def test_a_site_whose_posts_are_all_in_the_future_is_the_empty_site(self):
        ctx = self.build("2026-10-01")
        self.assertEqual((ctx.posts, ctx.scheduled), ([], 4))
        self.assertIn("noindex", self.read("journal/index.html"))
        self.assertNotIn('id="journal"', self.read("index.html"))
        self.assertNotIn("/journal/", self.read("sitemap.xml"))
        self.assertEqual(cs.check(self.root, NOW)[0], [])

    def test_future_posts_are_still_validated(self):
        add_post(self.root, "killing-time-honestly", description=None)  # a broken draft must fail today, not on the day it goes live
        _, errs = bs.make_ctx(self.root, "2026-10-31")
        self.assertTrue(any("missing description" in e for e in errs), errs)

    def test_the_reference_date_comes_from_the_argument_then_the_environment_then_the_clock(self):
        import datetime as dt
        import os
        self.assertEqual(bs.resolve_today("2026-11-01"), dt.date(2026, 11, 1))
        self.assertEqual(bs.resolve_today(dt.date(2026, 11, 2)), dt.date(2026, 11, 2))
        # an aware instant is turned into its KST date: 2026-10-31 16:00 UTC is already 11-01 in Seoul
        self.assertEqual(bs.resolve_today(dt.datetime(2026, 10, 31, 16, 0, tzinfo=dt.timezone.utc)), dt.date(2026, 11, 1))
        self.assertEqual(bs.resolve_today(), dt.date(2026, 11, 3))  # helpers pins $PLAY_NOW
        old = os.environ.pop("PLAY_NOW")
        try:
            self.assertEqual(bs.resolve_today(), dt.datetime.now(bs.KST).date())
        finally:
            os.environ["PLAY_NOW"] = old
        for bad in ("2026-13-01", "tomorrow", "2026-11-1"):
            with self.assertRaises(ValueError):
                bs.resolve_today(bad)

    def test_the_command_line_takes_now(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = bs.main(["--root", str(self.root), "--now", "2026-11-01"])
        self.assertEqual(rc, 0)
        self.assertIn("3 journal post(s) live, 1 scheduled (as of 2026-11-01)", out.getvalue())
        self.assertTrue((self.root / "journal/turn-based-in-a-break/index.html").is_file())
        self.assertFalse((self.root / "journal/killing-time-honestly").exists())
        self.assertEqual(bs.main(["--root", str(self.root), "--now", "2026-02-30"]), 2)


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
        self.assertEqual((errs, len(urls)), ([], 4 * len(bs.LANGS)))

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
            self.assertEqual((root / "sitemap.xml").read_text().count("<url>"), 4 * len(bs.LANGS) + 2 + 2 * n)


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

    def test_calendar_dates_are_validated(self):
        for bad in ("2026-13-45", "2026-02-30", "2026-00-10", "2026-1-5", "26-11-01"):
            add_post(self.root, "why-rounds-end", updated=bad)
            self.assertIn("updated must look like", self.errors(), bad)
        for bad in ("2026-02-30T09:30+09:00", "2026-11-01T25:00+09:00", "2026-11-01T09:61+09:00", "2026-13-45T09:30+09:00"):
            add_post(self.root, "why-rounds-end", published=bad, updated=None)
            self.assertIn("published must be a KST time", self.errors(), bad)
        self.assertTrue(bs.valid_date("2028-02-29"))
        self.assertFalse(bs.valid_date("2027-02-29"))
        self.assertIsNone(bs.parse_published("2026-02-30T09:30+09:00"))
        self.assertEqual(bs.parse_published("2026-11-01T09:30+09:00").isoformat(), "2026-11-01T09:30:00+09:00")

    def test_page_updated_must_be_a_real_date(self):
        f = self.root / "content" / "pages" / "en" / "about.md"
        text = f.read_text(encoding="utf-8")
        f.write_text(re.sub(r"(?m)^updated:.*$", "updated: 2026-13-45", text, count=1), encoding="utf-8")
        self.assertIn("updated must look like", self.errors())


class MarkdownSubset(unittest.TestCase):
    def test_blockquote_markdown(self):
        self.assertEqual(bs.markdown("> one\n> two\n\nafter"), "<blockquote><p>one two</p></blockquote>\n<p>after</p>")

    def test_code_fence_renders_a_pre_code_block_with_escaped_text(self):
        out = bs.markdown("Before\n\n```\n// play();\n\n  rest(); <b>&</b>\n```\n\nAfter")
        self.assertEqual(out, "<p>Before</p>\n<pre><code>// play();\n\n  rest(); &lt;b&gt;&amp;&lt;/b&gt;</code></pre>\n<p>After</p>")
        self.assertEqual(bs.markdown("```js\nlet a = `x`; **no** [l](/a/)\n```"), "<pre><code>let a = `x`; **no** [l](/a/)</code></pre>")
        self.assertEqual(bs.markdown("````\n```\nnested\n```\n````"), "<pre><code>```\nnested\n```</code></pre>")
        self.assertEqual(bs.markdown("```\n## not a heading\n- not a list"), "<pre><code>## not a heading\n- not a list</code></pre>")  # unclosed: runs to the end

    def test_code_fence_signature_block_at_the_end_of_a_post(self):
        out = bs.markdown("Last line.\n\n```\n// play(); rest();\n```")
        self.assertTrue(out.endswith("<pre><code>// play(); rest();</code></pre>"), out)
        self.assertNotIn("``", out)

    def test_ordered_list_split_by_a_blank_line_keeps_counting(self):
        out = bs.markdown("1. one\n2. two\n\n3. three\n4. four")
        self.assertEqual(out, "<ol><li>one</li><li>two</li></ol>\n<ol start=\"3\"><li>three</li><li>four</li></ol>")

    def test_link_href_allowlist(self):
        for ok in ("https://e.com/a?b=1", "http://e.com", "/about/", "#top", "mailto:hi@e.com", "HTTPS://E.COM"):
            self.assertIn('<a href="%s"' % ok, bs.markdown("[x](%s)" % ok), ok)
        self.assertIn('rel="noopener"', bs.markdown("[x](https://e.com)"))
        self.assertNotIn("rel=", bs.markdown("[x](/about/)"))
        for bad in ("javascript:alert(1)", "JavaScript:alert(1)", " javascript:alert(1)", "data:text/html,<b>", "vbscript:x", "//evil.com/x",
                    "/\\evil.com", "file:///etc/passwd", "ftp://e.com", "relative/path", "java\tscript:alert(1)", "https://", "javascript&#58;alert(1)"):
            out = bs.markdown("[click](%s)" % bad)
            self.assertNotIn("<a ", out, bad)
            self.assertNotIn("href", out, bad)
        self.assertEqual(bs.markdown("[click](javascript:alert(1))"), "<p>click</p>")

    def test_link_url_with_parentheses_is_kept_whole(self):
        self.assertEqual(bs.markdown("[Go](https://en.wikipedia.org/wiki/Go_(game)) now"),
                         '<p><a href="https://en.wikipedia.org/wiki/Go_(game)" rel="noopener">Go</a> now</p>')
        self.assertEqual(bs.markdown("(see [a](/a/))"), '<p>(see <a href="/a/">a</a>)</p>')

    def test_link_cannot_break_out_of_the_attribute_or_forge_code_markers(self):
        out = bs.markdown('[x](/a"onmouseover="alert(1))')
        self.assertNotIn('"onmouseover', out)
        self.assertIn("&quot;onmouseover", out)
        out = bs.markdown("[x](/a`b`) and \x000\x00 `c`")
        self.assertEqual(out, "<p>[x](/a<code>b</code>) and 0 <code>c</code></p>")  # no link, no forged code marker, no NUL left


class Escaping(Reader):
    """a post whose title, excerpt, body and links are full of <, ", & and script text must come out inert everywhere"""
    TITLE = 'A <script>alert(1)</script> "quoted" & <b>bold</b> title'
    DESC = "Tags <img src=x onerror=alert(1)> and \"quotes\" & ampersands"
    BODY = ("## Heading <script>alert(2)</script>\n\nRaw <script>alert(3)</script> & \"q\" and [bad](javascript:alert(4)) and "
            "[quote](/a\"onmouseover=\"alert(5)) and [fine](https://e.com/?a=1&b=2) and `<script>alert(6)</script>`.\n\n"
            "> <script>alert(7)</script>\n\n- <script>alert(8)</script>\n\n```\n<script>alert(9)</script> & \"x\"\n```\n")

    @classmethod
    def setUpClass(cls):
        cls.root = make_site()
        d = cls.root / "content" / "journal"
        d.mkdir(parents=True, exist_ok=True)
        for lang in ("en", "ko"):
            (d / ("hostile-post.%s.md" % lang)).write_text(
                "---\ntitle: %s\ndescription: %s\nexcerpt: %s\npublished: 2026-11-01T09:30+09:00\n---\n%s" % (cls.TITLE, cls.DESC, cls.DESC, cls.BODY), encoding="utf-8")
        cls.ctx = build(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def pages(self):
        return ["index.html", "ko/index.html", "journal/index.html", "ko/journal/index.html", "journal/hostile-post/index.html",
                "ko/journal/hostile-post/index.html", "journal/feed.xml", "ko/journal/feed.xml", "sitemap.xml", "llms.txt"]

    def test_no_live_script_or_handler_from_the_post_in_any_output(self):
        for f in self.pages():
            if f == "llms.txt":
                continue  # plain text, not HTML
            # JSON-LD is data (JSON string, "</" escaped) and is checked on its own below
            t = re.sub(r'<script type="application/ld\+json">.*?</script>', "", self.read(f), flags=re.S)
            self.assertNotRegex(t, r"<script>alert", f)
            self.assertNotRegex(t, r"(?i)<img src=x", f)
            self.assertNotRegex(t, r"(?i)<b>bold", f)
            self.assertNotIn("javascript:", t.lower(), f)
            self.assertNotIn('"onmouseover', t, f)
            # every <script> in the page is one of ours (ld+json, the inline localtime/langpick modules), never from the post
            for m in re.finditer(r"<script([^>]*)>(.*?)</script>", t, re.S):
                self.assertNotIn("alert(", m.group(2), f)

    def test_post_page_escapes_title_excerpt_and_body(self):
        h = self.read("journal/hostile-post/index.html")
        self.assertIn("<h1>A &lt;script&gt;alert(1)&lt;/script&gt; &quot;quoted&quot; &amp; &lt;b&gt;bold&lt;/b&gt; title</h1>", h)
        self.assertIn("<h2>Heading &lt;script&gt;alert(2)&lt;/script&gt;</h2>", h)
        self.assertIn("Raw &lt;script&gt;alert(3)&lt;/script&gt; &amp; &quot;q&quot;", h)
        self.assertIn("<code>&lt;script&gt;alert(6)&lt;/script&gt;</code>", h)
        self.assertIn("<blockquote><p>&lt;script&gt;alert(7)&lt;/script&gt;</p></blockquote>", h)
        self.assertIn("<li>&lt;script&gt;alert(8)&lt;/script&gt;</li>", h)
        self.assertIn("<pre><code>&lt;script&gt;alert(9)&lt;/script&gt; &amp; &quot;x&quot;</code></pre>", h)
        self.assertIn('<p>Raw', h)
        self.assertIn("and bad and <a", h)  # the javascript: link keeps its text only
        self.assertNotIn('href="javascript', h.lower())
        self.assertIn('<a href="https://e.com/?a=1&amp;b=2" rel="noopener">fine</a>', h)
        # meta tags: the attribute values are escaped, so the quotes cannot close them
        for m in re.finditer(r'<meta [^>]*content="([^"]*)"', h):
            self.assertNotIn("<", m.group(1))
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", h)

    def test_list_and_home_card_escape_title_and_excerpt(self):
        for f in ("journal/index.html", "ko/journal/index.html", "index.html", "ko/index.html"):
            h = self.read(f)
            self.assertIn("A &lt;script&gt;alert(1)&lt;/script&gt; &quot;quoted&quot; &amp; &lt;b&gt;bold&lt;/b&gt; title", h, f)
            self.assertIn("Tags &lt;img src=x onerror=alert(1)&gt; and &quot;quotes&quot; &amp; ampersands", h, f)

    def test_json_ld_stays_valid_json_and_cannot_close_its_script(self):
        for f in ("journal/hostile-post/index.html", "ko/journal/hostile-post/index.html", "journal/index.html"):
            h = self.read(f)
            blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
            self.assertTrue(blocks, f)
            for b in blocks:
                self.assertNotIn("</", b, f)
                json.loads(b)
        post = [n for n in jsonld(self.read("journal/hostile-post/index.html"))[0]["@graph"] if n["@type"] == "BlogPosting"][0]
        self.assertEqual(post["headline"], self.TITLE)

    def test_feeds_are_well_formed_xml_and_carry_the_text_literally(self):
        for f in ("journal/feed.xml", "ko/journal/feed.xml"):
            root = ET.fromstring(self.read(f).encode("utf-8"))  # raises on malformed XML
            titles = [e.text for e in root.iter("title")]
            self.assertIn(self.TITLE, titles, f)
            descs = [e.text for e in root.iter("description")]
            self.assertIn(self.DESC, descs, f)

    def test_sitemap_and_llms_are_not_polluted(self):
        ET.fromstring(self.read("sitemap.xml").encode("utf-8"))
        self.assertIn("/journal/hostile-post/", self.read("llms.txt"))


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
