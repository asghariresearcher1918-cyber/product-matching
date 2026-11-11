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
  // ONLY_HOST=example.com: abort every request to other hosts (trackers on blocked hosts otherwise stall each page)
  if (process.env.ONLY_HOST) {
    await pg.route('**/*', r => { try { return new URL(r.request().url()).hostname.endsWith(process.env.ONLY_HOST) ? r.continue() : r.abort(); } catch (e) { return r.abort(); } });
  }
  const a = process.argv.slice(2);
  for (let i = 0; i < a.length; i += 2) {
    const out = a[i], url = a[i + 1];
    if (fs.existsSync(out)) { console.log('cached', out); continue; }
    try {
      await pg.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      try { await pg.waitForLoadState('networkidle', { timeout: Number(process.env.IDLE_MS || 15000) }); } catch (e) { /* trackers on blocked hosts never go idle */ }
      await pg.waitForTimeout(Number(process.env.RENDER_WAIT_MS || 2000));
      fs.mkdirSync(path.dirname(out), { recursive: true });
      fs.writeFileSync(out, `<!-- ref-url: ${url} | final-url: ${pg.url()} | rendered | ${new Date().toISOString()} -->\n` + await pg.content());
      console.log('ok', out);
    } catch (e) { console.log('FAIL', url, e.message); }
    await pg.waitForTimeout(1000);
  }
  await b.close();
})();
