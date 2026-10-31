"""Language picker: on every built page of every language the picker shows that page's own language
(aria-current, <html lang>), and a saved choice ("play-lang") sends "/" to that language."""
import json
import re
import shutil
import subprocess
import unittest

from helpers import REPO, bs

LANG_DIRS = [l for l in bs.LANGS if l != "en"]


def pages():
    out = []
    for p in REPO.rglob("index.html"):
        rel = p.relative_to(REPO).parts
        if rel[0] in ("tests", "scripts", "docs", "ops", "content", "assets"):
            continue
        lang = rel[0] if rel[0] in LANG_DIRS else "en"
        out.append((lang, str(p.relative_to(REPO)), p.read_text(encoding="utf-8")))
    return out


class Picker(unittest.TestCase):
    def test_both_languages_have_pages(self):
        self.assertEqual({l for l, _, _ in pages()}, set(bs.LANGS))

    def test_picker_shows_the_pages_own_language(self):
        for lang, f, h in pages():
            name = bs.LANGS[lang][0]
            self.assertEqual(re.search(r'<html lang="([\w-]+)"', h).group(1), lang, f)
            menu = re.search(r'<span class="langsw".*?</span>', h, re.S).group(0)
            cur = re.findall(r'<a href="[^"]*" hreflang="(\w+)"[^>]*aria-current', menu)
            self.assertEqual(cur, [lang], f)
            self.assertEqual(len(re.findall(r'<a ', menu)), len(bs.LANGS), f)

    def test_picker_links_stay_on_the_same_page(self):
        for lang, f, h in pages():
            menu = re.search(r'<span class="langsw".*?</span>', h, re.S).group(0)
            for href, l in re.findall(r'<a href="([^"]*)" hreflang="(\w+)"', menu):
                self.assertEqual(href.startswith("/" + l + "/") or (l == "en" and not href.startswith(tuple("/" + x + "/" for x in LANG_DIRS))), True, (f, href))

    @unittest.skipUnless(shutil.which("node"), "node required")
    def test_choice_is_remembered_for_each_language(self):
        """click a language -> play.js stores it -> langpick.js on '/' goes to it (en + ko)."""
        js = (REPO / "assets" / "play.js").read_text(encoding="utf-8")
        pick = (REPO / "assets" / "langpick.js").read_text(encoding="utf-8").replace("/*SUPPORTED*/[]", json.dumps(list(bs.LANGS)))
        prog = r"""
const store={};let hrefs=[];
function run(src,pathname,navLangs){
  let listener=null,to=null;
  const ctx={localStorage:{getItem:k=>store[k]===undefined?null:store[k],setItem:(k,v)=>{store[k]=String(v)}},
    navigator:{languages:navLangs,language:navLangs[0]},
    location:{pathname,search:'',hash:'',replace:u=>{to=u}},
    document:{querySelector:()=>null,addEventListener:(t,f)=>{if(t==='click'&&!listener)listener=f}},window:{}};
  new Function('localStorage','navigator','location','document','window',src)(ctx.localStorage,ctx.navigator,ctx.location,ctx.document,ctx.window);
  return {listener,to};
}
const out=[];
for(const l of %s){
  for(const k in store)delete store[k];
  const a={getAttribute:n=>n==='hreflang'?l:null};
  const {listener}=run(%s,'/%s/',['en-US']);
  listener({target:{closest:()=>a}});
  const r=run(%s,'/',['en-US']);
  out.push([l,store['play-lang'],r.to]);
}
console.log(JSON.stringify(out));
""" % (json.dumps(list(bs.LANGS)), json.dumps(js), "x", json.dumps(pick))
        res = subprocess.run(["node", "-e", prog], capture_output=True, text=True, timeout=30)
        self.assertEqual(res.returncode, 0, res.stderr)
        for l, saved, to in json.loads(res.stdout):
            self.assertEqual(saved, l)
            self.assertEqual(to, None if l == "en" else "/%s/" % l, l)


if __name__ == "__main__":
    unittest.main()
