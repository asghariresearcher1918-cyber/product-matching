// Phase 1b: render JS-only (SPA/custom) pharmacy product pages with a headless browser and extract name / price /
// image straight from the rendered DOM, so pharmacies that expose no JSON-LD or og:image in static HTML still get
// authoritative data (above all a product IMAGE, which they currently lack on the site).
// Resumable: ids already in catalogue/final/rendered_data.csv are skipped. On-hold shops (Refine, DermaFocus) are
// not in the queue, so their anti-bot is never touched.
// Usage: node scripts/render_extract.js [limit]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'catalogue/final/rendered_data.csv');
const QUEUE = path.join(ROOT, 'catalogue/final/render_queue.json');
const LIMIT = process.argv[2] ? parseInt(process.argv[2]) : 1e9;
const WORKERS = 5;

function csvEsc(s){ s = (s==null?'':String(s)); return /[",\n]/.test(s) ? '"'+s.replace(/"/g,'""')+'"' : s; }

(async () => {
  const queue = JSON.parse(fs.readFileSync(QUEUE,'utf8'));
  const done = new Set();
  if (fs.existsSync(OUT)) for (const line of fs.readFileSync(OUT,'utf8').split('\n').slice(1)) { const id=line.split(',')[0]; if(id) done.add(id.replace(/"/g,'')); }
  else fs.writeFileSync(OUT, 'id,supplier,r_name,r_price,r_image\n');
  const todo = queue.filter(q=>!done.has(q.id)).slice(0, LIMIT);

  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const browser = await chromium.launch({ args:['--no-sandbox'], proxy: proxy?{server:proxy}:undefined });
  const ctx = await browser.newContext({ userAgent:'Mozilla/5.0 (compatible; catalogue-render/1.0)', ignoreHTTPSErrors:true, javaScriptEnabled:true });
  ctx.route('**/*', r => { const t=r.request().resourceType(); (t==='image'||t==='media'||t==='font')? r.abort():r.continue(); }); // skip heavy assets, keep DOM/XHR

  let i=0, ok=0, err=0;
  async function worker(){
    while (i < todo.length){
      const q = todo[i++];
      const p = await ctx.newPage();
      let rec = {name:'',price:'',image:''};
      try{
        await p.goto(q.url, {waitUntil:'domcontentloaded', timeout:30000});
        await p.waitForTimeout(3800);   // let the SPA fill in product content
        rec = await p.evaluate(() => {
          const pick = sels => { for (const s of sels){ const e=document.querySelector(s); if(e){ const v=(e.content||e.getAttribute('content')||e.textContent||'').trim(); if(v) return v; } } return ''; };
          // name: JSON-LD > og:title > h1 > <title> (minus shop suffix)
          let name='';
          for (const s of document.querySelectorAll('script[type="application/ld+json"]')){ try{ const d=JSON.parse(s.textContent); const arr=Array.isArray(d)?d:(d['@graph']||[d]); for(const o of arr){ const t=[].concat(o['@type']||'').join(' '); if(/Product/.test(t)&&o.name){ name=o.name; break; } } }catch(e){} if(name)break; }
          if(!name) name = pick(['meta[property="og:title"]','h1','[itemprop="name"]','.product-title','.product-name']);
          if(!name) name = (document.title||'').replace(/\s*[|\-–—].*$/,'').trim();
          // price: first £ amount greater than zero
          let price=''; for(const m of (document.body.innerText||'').matchAll(/£\s?(\d{1,4}(?:\.\d{2})?)/g)){ if(parseFloat(m[1])>0){ price=m[1]; break; } }
          // image: og:image > largest product-context img (exclude logos/banners/awards)
          const bad=/logo|sprite|icon|placeholder|payment|award|banner|badge|flag|rating|star|trustpilot|visa|mastercard|maestro|amex|paypal|apple-?pay|google-?pay|\/_next\/static/i;
          let image = pick(['meta[property="og:image"]']);
          if(image && bad.test(image)) image='';
          if(!image){ let best=null,area=0; const scope=document.querySelector('main, .product, [class*="product"]')||document; for(const im of (scope.querySelectorAll?scope.querySelectorAll('img'):document.querySelectorAll('img'))){ const s=im.currentSrc||im.src||''; if(!/^https?:/.test(s)||bad.test(s)) continue; const a=(im.naturalWidth||im.width||0)*(im.naturalHeight||im.height||0); if(a>area){area=a;best=s;} } if(best)image=best; }
          return {name, price, image};
        });
        ok++;
      }catch(e){ err++; }
      fs.appendFileSync(OUT, [q.id,q.supplier,rec.name,rec.price,rec.image].map(csvEsc).join(',')+'\n');
      await p.close();
      if ((ok+err)%100===0) console.log(`  ${ok+err}/${todo.length} | ok=${ok} err=${err}`);
    }
  }
  await Promise.all(Array.from({length:WORKERS}, worker));
  await browser.close();
  console.log(`DONE: processed ${ok+err} (ok=${ok}, err=${err}); output ${OUT}`);
})();
