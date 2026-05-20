const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const outDir = 'C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/synonym-row-action-hybrid/artifacts/ux-pass';
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const base = 'http://localhost:8000';
  const evidence = { base, steps: [] };
  try {
    await page.goto(`${base}/admin/runs`, { waitUntil: 'networkidle', timeout: 60000 });
    await page.screenshot({ path: path.join(outDir, '01-runs.png'), fullPage: true });
    evidence.steps.push({ step: 'open_runs', url: page.url() });
    let targetUrl = null;
    const synLink = page.locator('a[href*="/admin/runs/"][href*="synonym-review"]').first();
    if (await synLink.count()) {
      targetUrl = await synLink.getAttribute('href');
    } else {
      const firstRun = page.locator('a[href^="/admin/runs/"]').first();
      const href = await firstRun.getAttribute('href');
      if (!href) throw new Error('No run link found');
      targetUrl = href.endsWith('/synonym-review') ? href : `${href.replace(/\/$/, '')}/synonym-review`;
    }
    if (!targetUrl.startsWith('http')) targetUrl = `${base}${targetUrl}`;
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 60000 });
    await page.screenshot({ path: path.join(outDir, '02-synonym-review-initial.png'), fullPage: true });
    evidence.steps.push({ step: 'open_synonym_review', url: page.url() });
    const rowActionCount = await page.locator('[data-synonym-row-action="true"]').count();
    evidence.rowActionCount = rowActionCount;
    const prefillButton = page.locator('button:has-text("Prefill Recommendations")').first();
    const hasPrefill = await prefillButton.count() > 0;
    evidence.prefillButtonVisible = hasPrefill;
    if (hasPrefill) {
      await prefillButton.click();
      await page.waitForTimeout(1500);
    }
    await page.screenshot({ path: path.join(outDir, '03-after-prefill.png'), fullPage: true });
    const checkedRows = await page.locator('input[type="checkbox"][name="row_ids"]:checked').count();
    const allRows = await page.locator('input[type="checkbox"][name="row_ids"]').count();
    const selectValues = await page.locator('[data-synonym-row-action="true"]').evaluateAll(nodes => nodes.map(n => n.value));
    const counts = {};
    for (const v of selectValues) counts[v || ''] = (counts[v || ''] || 0) + 1;
    let statusText = '';
    for (const sel of ['[data-prefill-status]', '#prefill-status', '[aria-live]']) {
      const loc = page.locator(sel).first();
      if (await loc.count()) {
        const t = (await loc.innerText()).trim();
        if (t) { statusText = t; break; }
      }
    }
    evidence.prefill = { checkedRows, allRows, selectValueCounts: counts, statusText };
    fs.writeFileSync(path.join(outDir, 'evidence.json'), JSON.stringify(evidence, null, 2));
    console.log(JSON.stringify(evidence, null, 2));
  } finally {
    await browser.close();
  }
})();
