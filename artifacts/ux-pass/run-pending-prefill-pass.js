const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const outDir = 'C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/synonym-row-action-hybrid/artifacts/ux-pass';
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const runId = 'cb17dd77-5b3b-489a-aea1-edc66861701e';
  const url = `http://localhost:8000/admin/runs/${runId}/synonym-review`;
  const evidence = { runId, url };
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.screenshot({ path: path.join(outDir, '20-before-prefill-pending-run.png'), fullPage: true });

    const pendingLabel = (await page.locator('body').innerText()).match(/(\d+) pending of (\d+) proposal\(s\)/i)?.[0] || null;
    evidence.pendingLabel = pendingLabel;

    const rowActionSel = page.locator('[data-synonym-row-action="true"]');
    const rowActionCount = await rowActionSel.count();
    evidence.rowActionCountBefore = rowActionCount;

    const checkedBefore = await page.locator('input[type="checkbox"][name="proposal_id"]:checked').count();
    evidence.checkedBefore = checkedBefore;

    const valuesBefore = await rowActionSel.evaluateAll(nodes => nodes.map(n => n.value));
    evidence.valuesBefore = valuesBefore;

    const prefillButton = page.locator('button:has-text("Prefill Recommendations")').first();
    evidence.prefillVisible = await prefillButton.count() > 0;
    if (evidence.prefillVisible) {
      await prefillButton.click();
      await page.waitForTimeout(1200);
    }

    await page.screenshot({ path: path.join(outDir, '21-after-prefill-pending-run.png'), fullPage: true });

    const checkedAfter = await page.locator('input[type="checkbox"][name="proposal_id"]:checked').count();
    evidence.checkedAfter = checkedAfter;

    const valuesAfter = await rowActionSel.evaluateAll(nodes => nodes.map(n => n.value));
    evidence.valuesAfter = valuesAfter;

    const counts = {};
    for (const v of valuesAfter) counts[v || ''] = (counts[v || ''] || 0) + 1;
    evidence.valueCountsAfter = counts;

    let statusText = '';
    const modeStatus = page.locator('#synonym-mode-status').first();
    if (await modeStatus.count()) {
      statusText = (await modeStatus.innerText()).trim();
    }
    evidence.statusText = statusText;

    evidence.assertions = {
      rowActionsRender: rowActionCount > 0,
      prefillChangedAnyAction: valuesAfter.some((v, i) => v !== (valuesBefore[i] || '')),
      prefillAutoCheckedRows: checkedAfter >= checkedBefore && checkedAfter > 0,
      statusHasCounts: /approve|defer|reject|no_recommendation/i.test(statusText)
    };

    fs.writeFileSync(path.join(outDir, 'pending-run-prefill-evidence.json'), JSON.stringify(evidence, null, 2));
    console.log(JSON.stringify(evidence, null, 2));
  } finally {
    await browser.close();
  }
})();
