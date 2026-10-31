// Render PNGs from the HTML/SVG sources with headless Chromium (Playwright). Fonts are local (assets/fonts).
//   NODE_PATH=<dir containing playwright> node scripts/render_png.js
// -> assets/og-image.png (1200x630), assets/icon-180.png, assets/icon-512.png
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const A = path.join(__dirname, '..', 'assets');
(async () => {
  const b = await chromium.launch();
  let p = await b.newPage({ viewport: { width: 1200, height: 630 } });
  await p.goto('file://' + path.join(A, 'og-source.html'), { waitUntil: 'load' });
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: path.join(A, 'og-image.png') });
  await p.close();
  for (const [out, s] of [['icon-180.png', 180], ['icon-512.png', 512]]) {
    p = await b.newPage({ viewport: { width: s, height: s } });
    const svg = fs.readFileSync(path.join(A, 'favicon.svg'), 'utf8').replace(/width="64" height="64"/, `width="${s}" height="${s}"`);
    await p.setContent(`<body style="margin:0">${svg}</body>`);
    await p.screenshot({ path: path.join(A, out) });
    await p.close();
  }
  await b.close();
  console.log('render_png: ok');
})();
