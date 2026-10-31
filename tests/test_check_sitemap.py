import shutil
import unittest

from helpers import NOW, build, make_site

import check_sitemap as cs  # noqa: E402


class Sitemap(unittest.TestCase):
    def setUp(self):
        self.root = make_site()
        build(self.root)
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_ok(self):
        errs, urls = cs.check(self.root, NOW)
        self.assertEqual(errs, [])
        self.assertIn("https://play.ipe.rest/", urls)
        self.assertEqual(len(urls), 8)

    def test_missing_file_detected(self):
        (self.root / "about/index.html").unlink()
        self.assertTrue(any("no file" in e for e in cs.check(self.root, NOW)[0]))

    def test_missing_page_detected(self):
        sm = self.root / "sitemap.xml"
        text = sm.read_text()
        start = text.index("<url><loc>https://play.ipe.rest/contact/</loc>")
        sm.write_text(text[:start] + text[text.index("</url>", start) + 6:])
        self.assertTrue(any("missing from sitemap" in e for e in cs.check(self.root, NOW)[0]))

    def test_broken_reciprocity_detected(self):
        sm = self.root / "sitemap.xml"
        sm.write_text(sm.read_text().replace('hreflang="ko" href="https://play.ipe.rest/ko/about/"', 'hreflang="ko" href="https://play.ipe.rest/ko/nowhere/"', 1))
        self.assertTrue(cs.check(self.root, NOW)[0])

    def test_future_lastmod_detected(self):
        sm = self.root / "sitemap.xml"
        sm.write_text(sm.read_text().replace("2026-10-31", "2099-01-01", 1))
        self.assertTrue(any("future" in e for e in cs.check(self.root, NOW)[0]))


if __name__ == "__main__":
    unittest.main()
