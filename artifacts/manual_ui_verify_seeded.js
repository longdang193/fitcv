const { chromium } = require('playwright');
(async()=>{
  const base='http://127.0.0.1:18016';
  const runId='11111111-2222-4333-8444-555555555555';
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage();
  const out={runId};

  await page.goto(base+'/admin/runs/'+runId+'/synonym-review',{waitUntil:'domcontentloaded',timeout:20000});
  out.reviewUrl=page.url();
  out.reviewCtaPresent=(await page.locator('text=Review Promote to Global').count())>0;
  out.batchActionPresent=(await page.locator('#synonym-batch-action-select').count())>0;
  out.selectedCounterPresent=(await page.locator('#synonym-selected-count').count())>0;
  out.reviewRowCheckboxes=await page.locator('input[type=checkbox][name=proposal_id]').count();

  await page.goto(base+'/admin/runs/'+runId+'/synonym-proposals/promote-review',{waitUntil:'domcontentloaded',timeout:20000});
  out.promoteUrl=page.url();
  out.readySection=(await page.locator('text=Ready to Promote').count())>0;
  out.alreadySection=(await page.locator('text=Already Global (No Change)').count())>0;
  out.blockedSection=(await page.locator('text=Blocked / Conflict').count())>0;
  out.promoteCheckboxes=await page.locator('input[type=checkbox][name=promote_proposal_id]').count();
  out.selectAllPresent=(await page.locator('#promote-select-all-btn').count())>0;
  out.clearAllPresent=(await page.locator('#promote-clear-all-btn').count())>0;
  out.promoteSelectedCounterPresent=(await page.locator('#promote-selected-count').count())>0;
  out.commitButtonPresent=(await page.locator('#promote-commit-form button[type=submit]').count())>0;
  out.commitDisabled=(out.commitButtonPresent? await page.locator('#promote-commit-form button[type=submit]').first().isDisabled() : null);

  await browser.close();
  console.log(JSON.stringify(out,null,2));
})();
