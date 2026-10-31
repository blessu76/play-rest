"""Themes: light / dark / noir. Every built page carries the first-paint script, the switch and the noir tokens."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import helpers
from helpers import REPO, bs, build, make_site_with_posts

THEMES = ("light", "dark", "noir")
COLORS = {"light": "#fbfcfe", "dark": "#0c1118", "noir": "#0a0810"}


class Theme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = make_site_with_posts()
        build(cls.root)
        cls.pages = sorted(p for p in Path(cls.root).rglob("*.html") if "content" not in p.parts and "assets" not in p.parts)
        cls.css = (REPO / "assets" / "play.css").read_text(encoding="utf-8")
        cls.js = (REPO / "assets" / "play.js").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def test_pages_found(self):
        names = {str(p.relative_to(self.root)) for p in self.pages}
        for n in ("index.html", "ko/index.html", "404.html", "journal/index.html", "journal/turn-based-in-a-break/index.html", "ko/journal/turn-based-in-a-break/index.html"):
            self.assertIn(n, names)

    def test_every_page_has_inline_theme_script_before_stylesheet(self):
        for p in self.pages:
            h = p.read_text(encoding="utf-8")
            self.assertEqual(h.count("localStorage.getItem('play-theme')"), 1, p)
            i_meta = h.rindex('name="theme-color"')
            i_script = h.index("localStorage.getItem('play-theme')")
            i_css = h.index('rel="stylesheet"')
            self.assertTrue(i_meta < i_script < i_css, p)
            self.assertEqual(len(re.findall(r'<meta name="theme-color"', h)), 2, p)
            for c in COLORS.values():
                self.assertIn(c, h, p)

    def test_every_page_has_three_pressable_buttons(self):
        for p in self.pages:
            h = p.read_text(encoding="utf-8")
            grp = re.search(r'<div class="themesw" role="group" aria-label="([^"]+)">(.*?)</div>', h, re.S)
            self.assertIsNotNone(grp, p)
            self.assertEqual(grp.group(1), "테마" if 'lang="ko"' in h[:300] else "Theme", p)
            btns = re.findall(r'<button type="button" data-theme-set="(\w+)" aria-pressed="false" aria-label="([^"]+)" title="\2">(<svg.*?</svg>)</button>', grp.group(2), re.S)
            self.assertEqual([b[0] for b in btns], list(THEMES), p)
            for _, label, svg in btns:
                self.assertTrue(label)
                self.assertIn('aria-hidden="true"', svg)
                self.assertIn('focusable="false"', svg)

    def test_labels_in_both_languages(self):
        want = {"en": ("Light", "Dark", "Noir"), "ko": ("화이트", "다크", "누아르")}
        for lang, labels in want.items():
            h = (Path(self.root) / ("index.html" if lang == "en" else "ko/index.html")).read_text(encoding="utf-8")
            for l in labels:
                self.assertIn('aria-label="%s"' % l, h)

    def test_css_tokens_for_all_three(self):
        for t, c in COLORS.items():
            if t != "light":
                self.assertRegex(self.css, r':root\[data-theme="%s"\]\{--bg:%s;' % (t, c))
        self.assertIn('--cobalt:#b9a2f2', self.css)
        self.assertIn(':root:not([data-theme])', self.css)  # JS-off fallback follows the device
        self.assertIn('[data-theme="noir"] .game', self.css)
        self.assertIn('[data-theme="noir"] .journal-card', self.css)
        self.assertIn('[data-theme="noir"] body{background-image:radial-gradient', self.css)
        self.assertIn('[data-theme="noir"] ::selection', self.css)
        # the old unscoped dark override and the hard-coded button colour are gone
        self.assertNotIn(".game .btn{color:#0c1118}", self.css)
        self.assertIsNone(re.search(r'@media \(prefers-color-scheme:dark\)\{:root\{', self.css))

    def test_switch_css_is_44px(self):
        self.assertRegex(self.css, r"\.themesw button\{[^}]*width:44px;height:44px")

    def test_asset_version_in_pages(self):
        for p in self.pages:
            h = p.read_text(encoding="utf-8")
            self.assertIn("play.css?v=%s" % bs.ASSET_V, h, p)
            self.assertIn("play.js?v=%s" % bs.ASSET_V, h, p)

    @unittest.skipUnless(shutil.which("node"), "node required")
    def test_head_script_and_switch_behaviour(self):
        h = (Path(self.root) / "index.html").read_text(encoding="utf-8")
        head_js = re.search(r"<script>(\(function\(\)\{var t,C=.*?)</script>", h, re.S).group(1)
        theme_js = "(function(){\n  /* theme switch" + self.js.split("/* theme switch", 1)[1]
        prog = r"""
function env(stored,dark,throws){
  const attrs={},cls=new Set(),metas=[{content:''},{content:''}],btns=THEMES.map(t=>{const a={'data-theme-set':t,'aria-pressed':'false'};return {a,getAttribute:k=>a[k],setAttribute:(k,v)=>{a[k]=v},addEventListener:(e,f)=>{a.fn=f}}});
  const store=stored===undefined?{}:{'play-theme':stored};
  return {attrs,cls,metas,btns,store,
    localStorage:{getItem:k=>{if(throws)throw new Error('blocked');return k in store?store[k]:null},setItem:(k,v)=>{if(throws)throw new Error('blocked');store[k]=String(v)}},
    document:{documentElement:{setAttribute:(k,v)=>{attrs[k]=v},getAttribute:k=>attrs[k]===undefined?null:attrs[k],classList:{add:c=>cls.add(c),remove:c=>cls.delete(c)}},
      querySelectorAll:s=>s.startsWith('meta')?metas:s.startsWith('.themesw')?btns:[]},
    matchMedia:q=>({matches:q.includes('dark')?dark:false,addEventListener(){}})};
}
const THEMES=%s,HEAD=%s,JS=%s,out={};
function run(src,e){new Function('localStorage','document','matchMedia','window','setTimeout',src)(e.localStorage,e.document,e.matchMedia,{matchMedia:e.matchMedia},()=>{})}
for(const [name,stored,dark,throws] of [['saved-noir','noir',false,false],['saved-dark','dark',false,false],['junk','constructor',true,false],['none-dark',undefined,true,false],['none-light',undefined,false,false],['blocked-dark',undefined,true,true]]){
  const e=env(stored,dark,throws);run(HEAD,e);out[name]=[e.attrs['data-theme'],e.metas[0].content];
}
// click flow
const e=env(undefined,false,false);run(HEAD,e);
new Function('localStorage','document','matchMedia','window','setTimeout',JS)(e.localStorage,e.document,e.matchMedia,{matchMedia:e.matchMedia},()=>{});
out.pressedAfterLoad=e.btns.map(b=>b.a['aria-pressed']);
e.btns[2].a.fn.call(e.btns[2]);
out.afterClick=[e.attrs['data-theme'],e.store['play-theme'],e.metas[1].content,e.btns.map(b=>b.a['aria-pressed'])];
console.log(JSON.stringify(out));
""" % (json.dumps(list(THEMES)), json.dumps(head_js), json.dumps(theme_js))
        res = subprocess.run(["node", "-e", prog], capture_output=True, text=True, timeout=30)
        self.assertEqual(res.returncode, 0, res.stderr)
        o = json.loads(res.stdout)
        self.assertEqual(o["saved-noir"], ["noir", "#0a0810"])
        self.assertEqual(o["saved-dark"], ["dark", "#0c1118"])
        self.assertEqual(o["junk"], ["dark", "#0c1118"])          # bad stored value -> device setting
        self.assertEqual(o["none-dark"], ["dark", "#0c1118"])
        self.assertEqual(o["none-light"], ["light", "#fbfcfe"])
        self.assertEqual(o["blocked-dark"], ["dark", "#0c1118"])  # localStorage blocked -> device setting
        self.assertEqual(o["pressedAfterLoad"], ["true", "false", "false"])
        self.assertEqual(o["afterClick"], ["noir", "noir", "#0a0810", ["false", "false", "true"]])


if __name__ == "__main__":
    unittest.main()
