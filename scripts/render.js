// Render JS-only pages (official references such as MHRA/emc search, or JS supplier pages) and cache them.
// Usage: node scripts/render.js OUTFILE URL [OUTFILE URL ...]   (existing OUTFILEs are never overwritten)
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
const UA = 'Mozilla/5.0 (compatible; product-catalogue-research/1.0)';
(async () => {
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const b = await chromium.launch(proxy ? { proxy: { server: proxy } } : {});
  const ctx = await b.newContext({ userAgent: UA });
  const pg = await ctx.newPage();
  const a = process.argv.slice(2);
  for (let i = 0; i < a.length; i += 2) {
    const out = a[i], url = a[i + 1];
    if (fs.existsSync(out)) { console.log('cached', out); continue; }
    try {
      await pg.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
      await pg.waitForTimeout(2000);
      fs.mkdirSync(path.dirname(out), { recursive: true });
      fs.writeFileSync(out, `<!-- ref-url: ${url} | final-url: ${pg.url()} | rendered | ${new Date().toISOString()} -->\n` + await pg.content());
      console.log('ok', out);
    } catch (e) { console.log('FAIL', url, e.message); }
    await pg.waitForTimeout(1000);
  }
  await b.close();
})();
