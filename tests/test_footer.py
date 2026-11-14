"""Footer and nav: privacy and terms sit in the footer only (never in the nav); the language select lives in the
header and holds every language's version of the same page, with a no-JS link list."""
import re
import unittest

from helpers import bs
from test_langpicker import pages


def block(h, tag):
    return re.search(r"<%s[ >].*?</%s>" % (tag, tag), h, re.S).group(0)


class FooterNav(unittest.TestCase):
    def test_nav_has_no_privacy_or_terms(self):
        for lang, f, h in pages():
            hrefs = re.findall(r'href="([^"]*)"', re.search(r'<nav class="nav".*?</nav>', h, re.S).group(0))
            self.assertFalse([x for x in hrefs if "privacy" in x or "terms" in x], f)

    def test_footer_has_privacy(self):
        for lang, f, h in pages():
            self.assertIn('href="%s"' % bs.path_page(lang, "privacy"), block(h, "footer"), f)

    def test_footer_has_terms_link(self):
        for lang, f, h in pages():
            foot = block(h, "footer")
            self.assertEqual(len(re.findall(r'<a href="https://ipe\.rest/legal/terms/"', foot)), 1, f)

    def test_footer_has_no_language_select(self):
        for lang, f, h in pages():
            foot = block(h, "footer")
            self.assertNotIn("<select", foot, f)
            self.assertNotIn("foot-lang", h, f)

    def test_header_language_select(self):
        for lang, f, h in pages():
            head = block(h, "header")
            self.assertEqual(len(re.findall(r"<select ", head)), 1, f)
            self.assertIn('<select id="lang-select" class="langsel" autocomplete="off"', head, f)
            opts = re.findall(r'<option value="([^"]*)" data-lang="([\w-]+)"', head)
            self.assertEqual([l for _, l in opts], list(bs.LANGS), f)
            for href, l in opts:
                if l == "en":
                    self.assertFalse(href.startswith(tuple("/%s/" % x for x in bs.LANGS if x != "en")), (f, href))
                else:
                    self.assertTrue(href.startswith("/%s/" % l), (f, href))
            self.assertEqual(re.findall(r'<option value="[^"]*" data-lang="([\w-]+)"[^>]* selected', head), [lang], f)

    def test_header_nojs_links_match_select(self):
        for lang, f, h in pages():
            nojs = re.search(r"<noscript>(.*?)</noscript>", block(h, "header"), re.S).group(1)
            self.assertEqual(re.findall(r'<a href="([^"]*)"', nojs), [v for v, _ in re.findall(r'<option value="([^"]*)" data-lang="([\w-]+)"', block(h, "header"))], f)


if __name__ == "__main__":
    unittest.main()
