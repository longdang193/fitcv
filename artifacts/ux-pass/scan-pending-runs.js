const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:8000/admin/runs', { waitUntil: 'networkidle', timeout: 60000 });
  const links = await page.locator('a[href^="/admin/runs/"]').evaluateAll(ns => ns.map(n => n.getAttribute('href')).filter(Boolean));
  const unique = [...new Set(links)].filter(h => /^\/admin\/runs\/[\w-]+$/.test(h));
  let found = [];
  for (const href of unique.slice(0, 30)) {
    const url = `http://localhost:8000${href}/synonym-review`;
    const p = await browser.newPage();
    try {
      await p.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      const text = await p.locator('body').innerText();
      const m = text.match(/(\d+) pending of (\d+) proposal\(s\)/i);
      if (m) {
        const pending = Number(m[1]);
        const total = Number(m[2]);
        if (pending > 0) found.push({ run: href.split('/').pop(), pending, total, url });
      }
    } catch {}
    await p.close();
  }
  console.log(JSON.stringify({ scanned: unique.length, found }, null, 2));
  await browser.close();
})();
