const { chromium } = require('playwright');
(async()=>{
  const b=await chromium.launch({headless:true});
  const p=await b.newPage();
  const run='cb17dd77-5b3b-489a-aea1-edc66861701e';
  const url=`http://localhost:8000/admin/runs/${run}/synonym-review`;
  await p.goto(url,{waitUntil:'networkidle',timeout:60000});
  const body=await p.locator('body').innerText();
  const m=body.match(/(\d+) pending of (\d+) proposal\(s\)/i);
  console.log('url',url);
  console.log('match',m?m[0]:'none');
  await p.screenshot({path:'artifacts/ux-pass/11-current-run-synonym-review.png',fullPage:true});
  await b.close();
})();
