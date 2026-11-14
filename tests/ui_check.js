// UI gate: no horizontal overflow at 375 / 320 / 768 / 1280 px, no console errors, text >= 16px (.badge/.updated >= 14px),
// touch targets >= 44x44 on the home and journal pages at 375px, screenshots, in all three themes (light, dark, noir).
// Theme checks: data-theme + aria-pressed match the saved choice, the 3 switch buttons are 44x44, the page background is the theme's --bg,
// a click switches theme and persists it, and the device setting is followed when nothing is saved (also with JS off, where the switch is hidden).
// Languages: home + about/privacy/contact of all 11 languages (decision 0087); the language menu (<details>) opens inside the viewport
// at every width with 44px items, closes on Escape and on a click outside.
// Focus: the keyboard focus ring of the selected and an unselected cell of the theme switch and of the language select is >= 3:1 against its own background
// (all 3 themes); in forced-colors mode the selected cell and the focus ring are both visible and differ.
//   NODE_PATH=<dir containing playwright> node tests/ui_check.js [outDir]
// PLAY_ROOT=<dir> serves another repo-shaped folder (e.g. python3 tests/demo_site.py DIR: the site with test-only journal posts).
// Serves the repo root on a random local port (static, like GitHub Pages: /dir/ -> /dir/index.html).
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const ROOT = process.env.PLAY_ROOT ? path.resolve(process.env.PLAY_ROOT) : path.join(__dirname, '..');
const OUT = process.argv[2] || path.join(require('os').tmpdir(), 'play-ui');
const WIDTHS = [[375, 812], [320, 568], [768, 1024], [1280, 800]];
const TYPES = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.xml': 'application/xml', '.txt': 'text/plain' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  let f = path.join(ROOT, p);
  if (!f.startsWith(ROOT)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end('404'); }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});
// theme -> [device colour scheme, page background]. noir is checked with a *light* device to prove a saved choice beats the device setting.
const THEMES = { light: ['light', 'rgb(251, 252, 254)'], dark: ['dark', 'rgb(12, 17, 24)'], noir: ['light', 'rgb(10, 8, 16)'] };
const NEXT = { light: 'noir', dark: 'light', noir: 'dark' };
// journal list for both languages + the first post found on disk (en and ko)
function journalPages() {
  const out = ['/journal/', '/ko/journal/'];
  for (const pre of ['', '/ko']) {
    const dir = path.join(ROOT, pre, 'journal');
    if (!fs.existsSync(dir)) continue;
    const post = fs.readdirSync(dir).filter(n => fs.existsSync(path.join(dir, n, 'index.html'))).sort()[0];
    if (post) out.push(`${pre}/journal/${post}/`);
  }
  return out;
}
// every language directory that has a built home page (en is the root)
const LANGS = ['ko', 'ja', 'zh-Hant', 'es', 'pt-BR', 'id', 'vi', 'fr', 'de', 'th', 'tr'].filter(l => fs.existsSync(path.join(ROOT, l, 'index.html')));
function pagesToCheck() {
  const base = ['/', '/about/', '/privacy/', '/contact/'];
  const out = [...base, '/404.html', ...journalPages()];
  for (const l of LANGS) for (const b of base) out.push('/' + l + b);
  return out;
}
const isHome = p => p === '/' || LANGS.some(l => p === '/' + l + '/');
const isTouchPage = p => isHome(p) || p.includes('/journal/');
const SHOT = new Set(['/', '/about/', '/privacy/', '/contact/', '/ko/', '/ko/about/', '/ja/', '/zh-Hant/', '/de/', '/th/', '/tr/', '/pt-BR/about/', '/vi/', ...journalPages()]);
(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const origin = 'http://127.0.0.1:' + server.address().port;
  const b = await chromium.launch();
  const bad = [];
  let n = 0;
  for (const scheme of Object.keys(THEMES)) for (const [w, h] of WIDTHS) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, colorScheme: THEMES[scheme][0] });
    await ctx.addInitScript(t => { try { localStorage.setItem('play-theme', t); } catch (e) {} }, scheme);
    for (const pth of pagesToCheck()) {
      const page = await ctx.newPage();
      const errs = [];
      page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
      page.on('pageerror', e => errs.push(String(e)));
      page.on('requestfailed', r => { errs.push('request failed: ' + r.url()); });
      const resp = await page.goto(origin + pth, { waitUntil: 'load' });
      if (resp.status() !== 200) bad.push(`${scheme} ${w}px ${pth}: HTTP ${resp.status()}`);
      const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth,
        wide: [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > window.innerWidth + 1 && !e.closest('.cmp-wide') && getComputedStyle(e).position !== 'fixed')
          .slice(0, 3).map(e => e.tagName + '.' + e.className) }));
      const clipped = await page.evaluate(() => [...document.querySelectorAll('body *')].filter(e => { const c = getComputedStyle(e); return (c.overflowX !== 'visible' && !e.closest('.cmp-wide') && e.tagName !== 'PRE' && e.scrollWidth > e.clientWidth + 1) || (c.textOverflow === 'ellipsis'); }).slice(0, 3).map(e => e.tagName + '.' + e.className));
      // theme: applied before first paint, buttons reflect it, switch is 44x44, page background is the theme's --bg
      const th = await page.evaluate(() => ({ attr: document.documentElement.getAttribute('data-theme'), bg: getComputedStyle(document.body).backgroundColor,
        meta: [...document.querySelectorAll('meta[name=theme-color]')].map(m => m.content),
        pressed: [...document.querySelectorAll('.themesw button')].map(x => x.getAttribute('data-theme-set') + ':' + x.getAttribute('aria-pressed')),
        sizes: [...document.querySelectorAll('.themesw button')].map(x => { const r = x.getBoundingClientRect(); return Math.round(r.width) + 'x' + Math.round(r.height); }) }));
      if (th.attr !== scheme) bad.push(`${scheme} ${w}px ${pth}: data-theme is ${th.attr}`);
      if (th.bg !== THEMES[scheme][1]) bad.push(`${scheme} ${w}px ${pth}: body background ${th.bg}, expected ${THEMES[scheme][1]}`);
      if (th.pressed.join() !== ['light', 'dark', 'noir'].map(x => x + ':' + (x === scheme)).join()) bad.push(`${scheme} ${w}px ${pth}: aria-pressed ${th.pressed.join()}`);
      if (th.sizes.some(x => x !== '44x44')) bad.push(`${scheme} ${w}px ${pth}: theme buttons ${th.sizes.join()}`);
      if (new Set(th.meta).size !== 1 || th.meta.length !== 2) bad.push(`${scheme} ${w}px ${pth}: theme-color metas ${th.meta.join()}`);
      // readable text >= 16px (short labels .badge / .updated >= 14px)
      const small = await page.evaluate(() => {
        const out = [], seen = new Set(), w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        for (let n = w.nextNode(); n; n = w.nextNode()) {
          if (!n.nodeValue.trim()) continue;
          const el = n.parentElement;
          if (!el || ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName) || el.closest('svg')) continue;
          const r = el.getBoundingClientRect(), c = getComputedStyle(el);
          if (c.display === 'none' || c.visibility === 'hidden' || r.width <= 1 || r.height <= 1 || r.right <= 0) continue;
          const min = el.closest('.badge, .updated') ? 14 : 16;
          const fs = parseFloat(c.fontSize);
          if (fs < min && !seen.has(el)) { seen.add(el); out.push(`${el.tagName}.${el.className} ${fs}px "${n.nodeValue.trim().slice(0, 24)}"`); }
        }
        return out.slice(0, 5);
      });
      for (const e of small) bad.push(`${scheme} ${w}px ${pth}: text smaller than the 16px floor: ${e}`);
      // touch targets >= 44x44 on the home and journal pages at phone width
      if (w === 375 && isTouchPage(pth)) {
        const tiny = await page.evaluate(() => [...document.querySelectorAll('a[href], button')].map(e => {
          const r = e.getBoundingClientRect(), c = getComputedStyle(e);
          if (c.display === 'none' || c.visibility === 'hidden' || r.width <= 1 || r.height <= 1 || r.right <= 0) return null;
          if (e.closest('details:not([open]) > :not(summary)')) return null; // inside the closed language menu: not shown
          if (e.closest('.prose p, .prose li, .prose blockquote, .mtnote p')) return null; // links inside running text (WCAG 2.5.8 inline exception)
          return (r.width < 43.9 || r.height < 43.9) ? `${e.tagName}.${e.className} ${Math.round(r.width)}x${Math.round(r.height)} "${(e.textContent || '').trim().slice(0, 20)}"` : null;
        }).filter(Boolean));
        for (const e of tiny) bad.push(`${scheme} ${w}px ${pth}: touch target under 44x44: ${e}`);
      }
      // header language select: visible, inside the viewport, 44px tall, header not overflowing, current language selected (every page)
      {
        const ls = await page.evaluate(() => { const s = document.querySelector('#lang-select'), hd = document.querySelector('header');
          const r = s.getBoundingClientRect(), cs = getComputedStyle(s);
          return { shown: cs.display !== 'none' && r.width > 0, l: r.left, r: r.right, h: r.height, iw: window.innerWidth,
            val: s.options[s.selectedIndex].getAttribute('data-lang'), cur: document.documentElement.lang, hdrOver: hd.scrollWidth > hd.clientWidth + 1, footSel: !!document.querySelector('footer select') }; });
        if (!ls.shown) bad.push(`${scheme} ${w}px ${pth}: header language select not shown`);
        if (ls.l < 0 || ls.r > ls.iw) bad.push(`${scheme} ${w}px ${pth}: header language select outside the viewport (${Math.round(ls.l)}..${Math.round(ls.r)} of ${ls.iw})`);
        if (ls.h < 43.9) bad.push(`${scheme} ${w}px ${pth}: header language select ${Math.round(ls.h)}px tall`);
        if (ls.hdrOver) bad.push(`${scheme} ${w}px ${pth}: header overflows horizontally`);
        if (ls.footSel) bad.push(`${scheme} ${w}px ${pth}: footer has a select`);
        if (ls.val !== ls.cur) bad.push(`${scheme} ${w}px ${pth}: select shows ${ls.val}, page is ${ls.cur}`);
        const fit = await page.evaluate(() => { const s = document.querySelector('#lang-select'), cs = getComputedStyle(s), cv = document.createElement('canvas').getContext('2d');
          cv.font = cs.fontSize + ' ' + cs.fontFamily;
          return { need: Math.ceil(cv.measureText(s.options[s.selectedIndex].text).width), have: Math.floor(s.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - 16) }; });
        if (fit.need > fit.have) bad.push(`${scheme} ${w}px ${pth}: language name ${fit.need}px does not fit in ${fit.have}px`);
        if (SHOT.has(pth) && (w === 320 || w === 1280)) await page.screenshot({ path: path.join(OUT, `${scheme}-${w}-${pth.replace(/\//g, '_')}-langsel.png`), clip: { x: 0, y: 0, width: w, height: 90 } });
      }
      if (clipped.length) bad.push(`${scheme} ${w}px ${pth}: clipped content (${clipped.join(', ')})`);
      if (m.sw > m.iw) bad.push(`${scheme} ${w}px ${pth}: horizontal overflow scrollWidth ${m.sw} > ${m.iw} (${m.wide.join(', ')})`);
      for (const e of errs) bad.push(`${scheme} ${w}px ${pth}: console: ${e}`);
      n++;
      if (SHOT.has(pth)) await page.screenshot({ path: path.join(OUT, `${scheme}-${w}-${pth.replace(/\//g, '_') || '_'}.png`), fullPage: true });
      await page.close();
    }
    await ctx.close();
  }
  // behaviour: click switches + persists + survives reload and a language switch; no saved choice follows the device (also with JS off)
  {
    let k = 0;
    for (const [dev, want] of [['dark', 'dark'], ['light', 'light']]) {
      const ctx = await b.newContext({ viewport: { width: 375, height: 812 }, colorScheme: dev });
      const page = await ctx.newPage();
      await page.goto(origin + '/', { waitUntil: 'load' });
      const a = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
      if (a !== want) bad.push(`no saved theme, device ${dev}: data-theme ${a}, expected ${want}`);
      for (const t of ['noir', 'dark', 'light', 'noir']) {
        await page.click(`.themesw [data-theme-set=${t}]`);
        const r = await page.evaluate(() => ({ a: document.documentElement.getAttribute('data-theme'), s: localStorage.getItem('play-theme'),
          p: [...document.querySelectorAll('.themesw button[aria-pressed=true]')].map(x => x.getAttribute('data-theme-set')), m: document.querySelector('meta[name=theme-color]').content }));
        if (r.a !== t || r.s !== t || r.p.join() !== t) bad.push(`click ${t}: ${JSON.stringify(r)}`);
        k++;
      }
      await page.reload({ waitUntil: 'load' });
      if (await page.evaluate(() => document.documentElement.getAttribute('data-theme')) !== 'noir') bad.push('reload lost the chosen theme');
      await Promise.all([page.waitForNavigation({ waitUntil: 'load' }), page.selectOption('#lang-select', '/ko/')]);
      if (await page.evaluate(() => document.documentElement.getAttribute('data-theme')) !== 'noir') bad.push('language switch lost the chosen theme');
      await ctx.close();
      const nj = await b.newContext({ viewport: { width: 375, height: 812 }, colorScheme: dev, javaScriptEnabled: false });
      const np = await nj.newPage();
      await np.goto(origin + '/', { waitUntil: 'load' });
      const bg = await np.evaluate(() => getComputedStyle(document.body).backgroundColor);
      const shown = await np.evaluate(() => getComputedStyle(document.querySelector('.themesw')).display);
      await nj.close();
      const wantBg = THEMES[want][1]; // JS off: no data-theme, the device setting alone decides
      if (bg !== wantBg) bad.push(`JS off, device ${dev}: body background ${bg}, expected ${wantBg}`);
      if (shown !== 'none') bad.push(`JS off, device ${dev}: theme switch should be hidden, display is ${shown}`);
      k++;
    }
    // focus ring contrast on the switches, per theme (keyboard focus), and forced-colors
    const lum = c => { const [r, g, bl] = c.match(/[\d.]+/g).slice(0, 3).map(v => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * bl; };
    const ratio = (a, c) => { const x = lum(a), y = lum(c); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
    const focusInfo = async (page, sel) => { await page.keyboard.press('Tab'); await page.focus(sel);
      return page.evaluate(sel => { const e = document.querySelector(sel), c = getComputedStyle(e); return { fg: c.color, bg: c.backgroundColor, oc: c.outlineColor, ow: c.outlineWidth, os: c.outlineStyle, sel: e.matches(':focus-visible') }; }, sel); };
    for (const theme of Object.keys(THEMES)) {
      const ctx = await b.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: THEMES[theme][0] });
      await ctx.addInitScript(t => { try { localStorage.setItem('play-theme', t); } catch (e) {} }, theme);
      const page = await ctx.newPage();
      await page.goto(origin + '/', { waitUntil: 'load' });
      const other = theme === 'light' ? 'dark' : 'light';
      { const f = await focusInfo(page, '#lang-select');  // the language select sits on the page background
        if (f.os === 'none' || f.ow === '0px' || ratio(f.oc, THEMES[theme][1]) < 3) bad.push(`${theme}: language select focus ring ${f.os} ${f.ow} ${f.oc}`); k++; }
      for (const [name, sel] of [[`selected theme cell`, `.themesw [data-theme-set=${theme}]`], [`unselected theme cell`, `.themesw [data-theme-set=${other}]`]]) {
        const f = await focusInfo(page, sel);
        const under = /unselected/.test(name) ? THEMES[theme][1] : f.bg;  // the ring sits on the cell's own background when that is filled
        if (f.os === 'none' || f.ow === '0px') bad.push(`${theme}: ${name} has no focus ring`);
        else if (ratio(f.oc, under) < 3) bad.push(`${theme}: ${name} focus ring ${f.oc} on ${under} is ${ratio(f.oc, under).toFixed(2)}:1 (< 3)`);
        k++;
      }
      await ctx.close();
    }
    {
      const ctx = await b.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: 'light', forcedColors: 'active' });
      await ctx.addInitScript(() => { try { localStorage.setItem('play-theme', 'noir'); } catch (e) {} });
      const page = await ctx.newPage();
      await page.goto(origin + '/', { waitUntil: 'load' });
      const sel = await page.evaluate(() => ({ s: getComputedStyle(document.querySelector('.themesw [aria-pressed=true]')).backgroundColor, u: getComputedStyle(document.querySelector('.themesw [aria-pressed=false]')).backgroundColor }));
      if (sel.s === sel.u) bad.push(`forced-colors: selected theme cell looks like an unselected one (${sel.s})`);
      const f = await focusInfo(page, '.themesw [aria-pressed=true]');
      if (f.ow !== '3px' || f.oc === f.bg) bad.push(`forced-colors: focus ring on the selected cell ${f.ow} ${f.oc} on ${f.bg}`);
      await ctx.close();
      k++;
    }
    n += k;
  }
  await b.close(); server.close();
  console.log(`ui_check: ${n} page views, screenshots in ${OUT}`);
  if (bad.length) { console.error('ui_check FAILED:\n  ' + bad.join('\n  ')); process.exit(1); }
  console.log('ui_check: OK — no horizontal overflow or clipped content at 375/320/768/1280 (light + dark + noir), theme switch works, no console errors');
})();
