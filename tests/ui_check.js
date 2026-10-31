// UI gate: no horizontal overflow at 375 / 320 / 768 / 1280 px, no console errors, text >= 16px (.badge/.updated >= 14px),
// touch targets >= 44x44 on the home pages at 375px, screenshots.
//   NODE_PATH=<dir containing playwright> node tests/ui_check.js [outDir]
// Serves the repo root on a random local port (static, like GitHub Pages: /dir/ -> /dir/index.html).
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const ROOT = path.join(__dirname, '..');
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
function pagesToCheck() {
  const base = ['/', '/about/', '/privacy/', '/contact/'];
  const out = [...base, '/404.html'];
  for (const b of base) out.push(b === '/' ? '/ko/' : '/ko' + b);
  return out;
}
const SHOT = new Set(['/', '/about/', '/privacy/', '/contact/', '/ko/', '/ko/about/']);
(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const origin = 'http://127.0.0.1:' + server.address().port;
  const b = await chromium.launch();
  const bad = [];
  let n = 0;
  for (const [w, h] of WIDTHS) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    for (const pth of pagesToCheck()) {
      const page = await ctx.newPage();
      const errs = [];
      page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
      page.on('pageerror', e => errs.push(String(e)));
      page.on('requestfailed', r => { errs.push('request failed: ' + r.url()); });
      const resp = await page.goto(origin + pth, { waitUntil: 'load' });
      if (resp.status() !== 200) bad.push(`${w}px ${pth}: HTTP ${resp.status()}`);
      const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth,
        wide: [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > window.innerWidth + 1 && !e.closest('.cmp-wide') && getComputedStyle(e).position !== 'fixed')
          .slice(0, 3).map(e => e.tagName + '.' + e.className) }));
      const clipped = await page.evaluate(() => [...document.querySelectorAll('body *')].filter(e => { const c = getComputedStyle(e); return (c.overflowX !== 'visible' && !e.closest('.cmp-wide') && e.tagName !== 'PRE' && e.scrollWidth > e.clientWidth + 1) || (c.textOverflow === 'ellipsis'); }).slice(0, 3).map(e => e.tagName + '.' + e.className));
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
      for (const e of small) bad.push(`${w}px ${pth}: text smaller than the 16px floor: ${e}`);
      // touch targets >= 44x44 on the home pages at phone width
      if (w === 375 && (pth === '/' || pth === '/ko/')) {
        const tiny = await page.evaluate(() => [...document.querySelectorAll('a[href], button')].map(e => {
          const r = e.getBoundingClientRect(), c = getComputedStyle(e);
          if (c.display === 'none' || c.visibility === 'hidden' || r.width <= 1 || r.height <= 1 || r.right <= 0) return null;
          return (r.width < 43.9 || r.height < 43.9) ? `${e.tagName}.${e.className} ${Math.round(r.width)}x${Math.round(r.height)} "${(e.textContent || '').trim().slice(0, 20)}"` : null;
        }).filter(Boolean));
        for (const e of tiny) bad.push(`${w}px ${pth}: touch target under 44x44: ${e}`);
      }
      if (clipped.length) bad.push(`${w}px ${pth}: clipped content (${clipped.join(', ')})`);
      if (m.sw > m.iw) bad.push(`${w}px ${pth}: horizontal overflow scrollWidth ${m.sw} > ${m.iw} (${m.wide.join(', ')})`);
      for (const e of errs) bad.push(`${w}px ${pth}: console: ${e}`);
      n++;
      if (SHOT.has(pth)) await page.screenshot({ path: path.join(OUT, `${w}-${pth.replace(/\//g, '_') || '_'}.png`), fullPage: true });
      await page.close();
    }
    await ctx.close();
  }
  await b.close(); server.close();
  console.log(`ui_check: ${n} page views, screenshots in ${OUT}`);
  if (bad.length) { console.error('ui_check FAILED:\n  ' + bad.join('\n  ')); process.exit(1); }
  console.log('ui_check: OK — no horizontal overflow or clipped content at 375/320/768/1280, no console errors');
})();
