const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:8000/admin/runs', { waitUntil: 'networkidle', timeout: 60000 });
  await page.screenshot({ path: 'artifacts/ux-pass/10-runs-page-for-create.png', fullPage: true });
  const text = await page.locator('body').innerText();
  console.log(text.split('\n').slice(0,120).join('\n'));
  const links = await page.locator('a,button').evaluateAll(ns => ns.map(n => ({tag:n.tagName, text:(n.innerText||'').trim(), href:n.getAttribute('href')||''})).filter(x=>x.text));
  console.log('---ACTIONS---');
  for (const l of links.slice(0,80)) console.log(`${l.tag} | ${l.text} | ${l.href}`);
  await browser.close();
})();
