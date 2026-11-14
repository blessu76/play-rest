"""Language select: on every built page the header select shows that page's own language and each option is that
page in that language; "/" follows a saved choice ("ipe_lang") or the browser language, never for bots or other pages."""
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
        if rel[0] in ("tests", "scripts", "docs", "ops", "content", "assets", "pt", "zh", "ru"):
            continue
        lang = rel[0] if rel[0] in LANG_DIRS else "en"
        out.append((lang, str(p.relative_to(REPO)), p.read_text(encoding="utf-8")))
    return out


HARNESS = r"""
const store={};
function run(src,{pathname='/',ua='Mozilla/5.0',langs=['en-US'],select=null}){
  let to=null;
  const sels=select?[select]:[];
  const ctx={
    localStorage:{getItem:k=>store[k]===undefined?null:store[k],setItem:(k,v)=>{store[k]=String(v)}},
    navigator:{userAgent:ua,languages:langs,language:langs[0]},
    location:{pathname,search:'',hash:'',replace:u=>{to=u},href:''},
    document:{querySelectorAll:q=>q.startsWith('select')?sels:[],querySelector:()=>null,documentElement:{getAttribute:()=>null,setAttribute(){},classList:{add(){},remove(){}}},addEventListener(){}},
    window:{addEventListener(){}}};
  new Function('localStorage','navigator','location','document','window',src)(ctx.localStorage,ctx.navigator,ctx.location,ctx.document,ctx.window);
  return {to,href:ctx.location.href};
}
function option(l){return {value:'/'+l+'/',selectedIndex:0,options:[{getAttribute:n=>n==='data-lang'?l:null,value:'/'+l+'/'}],getAttribute(){return null}}}
const out={choice:[],detect:{}};
for(const l of LANGS){
  for(const k in store)delete store[k];
  const sel=option(l);
  sel.addEventListener=(t,f)=>{sel.change=f};
  run(PLAY,{pathname:'/'+l+'/',select:sel});
  sel.change();
  out.choice.push([l,store.ipe_lang,run(PICK,{pathname:'/'}).to]);
}
const cases={
  zhTW:{langs:['zh-TW']},zhHK:{langs:['zh-HK']},zhHant:{langs:['zh-Hant-TW']},zhCN:{langs:['zh-CN']},
  ptPT:{langs:['pt-PT']},ptBR:{langs:['pt-BR']},koKR:{langs:['ko-KR']},frCA:{langs:['fr-CA','de']},
  ru:{langs:['ru']},enOnly:{langs:['en-US']},
  bot:{langs:['ko'],ua:'Mozilla/5.0 (compatible; Googlebot/2.1)'},
  sub:{langs:['ko'],pathname:'/ko/'},
};
for(const k in store)delete store[k];
for(const [k,c] of Object.entries(cases)) out.detect[k]=run(PICK,{pathname:'/',...c}).to;
for(const k in store)delete store[k];
store.ipe_lang='ja';
out.detect.savedWins=run(PICK,{pathname:'/',langs:['ko']}).to;
out.detect.savedEn=(()=>{store.ipe_lang='en';return run(PICK,{pathname:'/',langs:['ko']}).to})();
console.log(JSON.stringify(out));
"""


class Picker(unittest.TestCase):
    def test_every_language_has_pages(self):
        self.assertEqual({l for l, _, _ in pages()}, set(bs.LANGS))

    def test_header_select_is_the_only_picker_and_shows_the_pages_own_language(self):
        for lang, f, h in pages():
            head = re.search(r"<header.*?</header>", h, re.S).group(0)
            self.assertEqual(re.search(r'<html lang="([\w-]+)"', h).group(1), lang, f)
            self.assertEqual(re.findall(r'<option value="[^"]*" data-lang="([\w-]+)"[^>]* selected', head), [lang], f)
            self.assertEqual(len(re.findall(r'<option ', head)), len(bs.LANGS), f)
            menu = re.search(r'<noscript><details class="langsw">.*?</details></noscript>', head, re.S).group(0)
            self.assertEqual(re.findall(r'<a href="[^"]*" hreflang="([\w-]+)"[^>]*aria-current', menu), [lang], f)

    @unittest.skipUnless(shutil.which("node"), "node required")
    def test_choice_and_detection(self):
        js_play = (REPO / "assets" / "play.js").read_text(encoding="utf-8")
        js_pick = (REPO / "assets" / "langpick.js").read_text(encoding="utf-8").replace("/*SUPPORTED*/[]", json.dumps(list(bs.LANGS)))
        prog = ("const LANGS=%s;const PLAY=%s;const PICK=%s;\n" % (json.dumps(list(bs.LANGS)), json.dumps(js_play), json.dumps(js_pick))) + HARNESS
        res = subprocess.run(["node", "-e", prog], capture_output=True, text=True, timeout=30)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        for l, saved, to in data["choice"]:
            self.assertEqual(saved, l)
            self.assertEqual(to, None if l == "en" else "/%s/" % l, l)
        d = data["detect"]
        self.assertEqual(d["zhTW"], "/zh-Hant/")
        self.assertEqual(d["zhHK"], "/zh-Hant/")
        self.assertEqual(d["zhHant"], "/zh-Hant/")
        self.assertIsNone(d["zhCN"])
        self.assertEqual(d["ptPT"], "/pt-BR/")
        self.assertEqual(d["ptBR"], "/pt-BR/")
        self.assertEqual(d["koKR"], "/ko/")
        self.assertEqual(d["frCA"], "/fr/")
        self.assertIsNone(d["ru"])
        self.assertIsNone(d["enOnly"])
        self.assertIsNone(d["bot"])
        self.assertIsNone(d["sub"])
        self.assertEqual(d["savedWins"], "/ja/")
        self.assertIsNone(d["savedEn"])


if __name__ == "__main__":
    unittest.main()
