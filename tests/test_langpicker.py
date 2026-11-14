"""Language select: on every built page the header select shows that page's own language and each option is that
page in that language; "/" follows a saved choice ("ipe_lang", once copied from "play-lang") or the browser language,
never for bots, for "?lang=en" or for other pages. The select is visible from the first paint and works without play.js."""
import json
import re
import shutil
import subprocess
import unittest

from helpers import REPO, bs

LANG_DIRS = [l for l in bs.LANGS if l != "en"]

NODE = r"""
const fs = require('fs');
const job = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = job.ops.map(o => {
  const store = Object.assign({}, o.store || {});
  const off = !!o.blocked;
  const ls = {
    getItem: k => { if (off) throw new Error('blocked'); return k in store ? store[k] : null; },
    setItem: (k, v) => { if (off) throw new Error('blocked'); store[k] = String(v); },
    removeItem: k => { if (off) throw new Error('blocked'); delete store[k]; },
  };
  const langs = o.langs || ['en-US'];
  const nav = { userAgent: o.ua || 'Mozilla/5.0', languages: langs, language: langs[0] };
  const loc = { pathname: o.pathname || '/', search: o.search || '', hash: '', href: '', to: null, replace(u) { this.to = u; } };
  const win = { addEventListener() {} };
  let sel = null;
  if (o.kind === 'choose') {
    const opt = { defaultSelected: o.lang === o.current, selected: o.lang === o.current, getAttribute: n => (n === 'data-lang' ? o.lang : null) };
    sel = { value: o.value, options: [opt], selectedIndex: 0, addEventListener(t, f) { this.change = f; } };
  }
  const doc = { getElementById: id => (id === 'lang-select' ? sel : null) };
  new Function('localStorage', 'navigator', 'location', 'document', 'window', o.kind === 'choose' ? job.sel : job.pick)(ls, nav, loc, doc, win);
  if (sel) sel.change.call(sel);
  return { to: loc.to, href: loc.href, store };
});
console.log(JSON.stringify(out));
"""


def run(ops):
    job = {"pick": bs.inline_js(REPO, "langpick.js", list(bs.LANGS)), "sel": bs.inline_js(REPO, "langsel.js"), "ops": ops}
    res = subprocess.run(["node", "-e", NODE], input=json.dumps(job), capture_output=True, text=True, timeout=60)
    if res.returncode:
        raise AssertionError(res.stderr)
    return json.loads(res.stdout)


def detect(**kw):
    return run([dict(kind="detect", **kw)])[0]


def pages():
    out = []
    for p in REPO.rglob("index.html"):
        rel = p.relative_to(REPO).parts
        if rel[0] in ("tests", "scripts", "docs", "ops", "content", "assets", "pt", "zh", "ru"):
            continue
        lang = rel[0] if rel[0] in LANG_DIRS else "en"
        out.append((lang, str(p.relative_to(REPO)), p.read_text(encoding="utf-8")))
    return out


@unittest.skipUnless(shutil.which("node"), "node required")
class Picker(unittest.TestCase):
    def test_every_language_has_pages(self):
        self.assertEqual({l for l, _, _ in pages()}, set(bs.LANGS))

    def test_header_select_is_the_only_picker_and_shows_the_pages_own_language(self):
        for lang, f, h in pages():
            head = re.search(r"<header.*?</header>", h, re.S).group(0)
            self.assertEqual(re.search(r'<html lang="([\w-]+)"', h).group(1), lang, f)
            sel = re.search(r"<select [^>]*>", head).group(0)
            self.assertNotIn("hidden", sel, f)
            self.assertNotIn("onchange", sel, f)
            self.assertNotIn("form", sel, f)
            self.assertEqual(re.findall(r'<option value="[^"]*" data-lang="([\w-]+)"[^>]* selected', head), [lang], f)
            self.assertEqual(len(re.findall(r'<option ', head)), len(bs.LANGS), f)
            self.assertIn("<noscript><style>.langsel{display:none}</style>", head, f)
            menu = re.search(r'<noscript><style>.*?</details></noscript>', head, re.S).group(0)
            self.assertEqual(re.findall(r'<a href="[^"]*" hreflang="([\w-]+)"[^>]*aria-current', menu), [lang], f)

    def test_choice_saves_and_opens_that_language(self):
        for l in bs.LANGS:
            value = "/" if l == "en" else "/%s/" % l
            r = run([dict(kind="choose", value=value, lang=l, current="en", store={})])[0]
            self.assertEqual(r["store"].get("ipe_lang"), l, l)
            self.assertEqual(r["href"], "/?lang=en" if l == "en" else value, l)

    def test_root_follows_the_choice(self):
        for l in bs.LANGS:
            value = "/" if l == "en" else "/%s/" % l
            saved = run([dict(kind="choose", value=value, lang=l, current="en", store={})])[0]
            to = detect(pathname="/", langs=["ja-JP"], store=saved["store"])["to"]
            self.assertEqual(to, None if l == "en" else "/%s/" % l, l)

    def test_english_choice_is_not_sent_back_when_storage_is_blocked(self):
        r = run([dict(kind="choose", value="/", lang="en", current="ko", blocked=True)])[0]
        self.assertEqual(r["href"], "/?lang=en")
        self.assertIsNone(detect(pathname="/", search="?lang=en", langs=["ko-KR"], blocked=True)["to"])
        self.assertIsNone(detect(pathname="/", search="?lang=en", langs=["ko-KR"])["to"])
        self.assertEqual(detect(pathname="/", langs=["ko-KR"], blocked=True)["to"], "/ko/")

    def test_other_choice_still_opens_its_page_when_storage_is_blocked(self):
        r = run([dict(kind="choose", value="/ja/", lang="ja", current="en", blocked=True)])[0]
        self.assertEqual(r["href"], "/ja/")

    def test_old_play_lang_is_copied_once_and_removed(self):
        r = detect(pathname="/", langs=["ko-KR"], store={"play-lang": "ja"})
        self.assertEqual(r["to"], "/ja/")
        self.assertEqual(r["store"], {"ipe_lang": "ja"})

    def test_old_play_lang_values_are_aliased(self):
        cases = {"pt": "/pt-BR/", "pt-PT": "/pt-BR/", "zh": "/zh-Hant/", "zh-TW": "/zh-Hant/", "zh-HK": "/zh-Hant/",
                 "zh-CN": None, "zh-SG": None, "en": None}
        for old, want in cases.items():
            r = detect(pathname="/", langs=["ko-KR"], store={"play-lang": old})
            self.assertEqual(r["to"], want, old)
            self.assertNotIn("play-lang", r["store"], old)

    def test_saved_ipe_lang_wins_over_old_key(self):
        r = detect(pathname="/", langs=["ja-JP"], store={"play-lang": "ja", "ipe_lang": "ko"})
        self.assertEqual(r["to"], "/ko/")
        self.assertNotIn("play-lang", r["store"])

    def test_saved_aliases_for_the_site_languages(self):
        self.assertEqual(detect(pathname="/", langs=["ko-KR"], store={"ipe_lang": "pt-PT"})["to"], "/pt-BR/")
        self.assertEqual(detect(pathname="/", langs=["ko-KR"], store={"ipe_lang": "zh-hk"})["to"], "/zh-Hant/")
        self.assertIsNone(detect(pathname="/", langs=["ko-KR"], store={"ipe_lang": "zh-CN"})["to"])

    def test_unsupported_saved_value_falls_back_to_the_browser_language(self):
        self.assertEqual(detect(pathname="/", langs=["ja-JP"], store={"ipe_lang": "xx"})["to"], "/ja/")
        self.assertIsNone(detect(pathname="/", langs=["en-US"], store={"ipe_lang": "xx"})["to"])
        self.assertIsNone(detect(pathname="/", langs=["ko-KR"], store={"ipe_lang": "en"})["to"])

    def test_bots_and_headless_are_never_redirected(self):
        for ua in ["Mozilla/5.0 (compatible; Googlebot/2.1)", "facebookexternalhit/1.1", "Mozilla/5.0 (compatible; Google-InspectionTool/1.0)",
                   "Mozilla/5.0 HeadlessChrome/120.0", "Mozilla/5.0 (compatible; bingpreview/2.0)"]:
            self.assertIsNone(detect(pathname="/", langs=["ko-KR"], ua=ua)["to"], ua)
        self.assertEqual(detect(pathname="/", langs=["ko-KR"], ua="Mozilla/5.0 (Macintosh)")["to"], "/ko/")

    def test_other_pages_are_never_redirected(self):
        self.assertIsNone(detect(pathname="/ko/", langs=["ja-JP"])["to"])

    def test_root_picker_is_inlined_only_on_the_root(self):
        for lang, f, h in pages():
            self.assertEqual("localStorage.getItem('play-lang')" in h, f == "index.html", f)


if __name__ == "__main__":
    unittest.main()
