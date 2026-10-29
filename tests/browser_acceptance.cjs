// Real Chromium, offline file:// input. Not the minimal-DOM handler regression.
// npm install --no-save playwright && npx playwright install chromium
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {spawnSync} = require('node:child_process');
const output = path.resolve(process.argv[3]);
const reportPath = path.resolve(process.argv[2]);
let browser;
const status = {status:'running', checks:[], limitations:['Mobile viewport emulation is not a physical iOS/Safari test.']};
async function record(name, fn) {await fn(); status.checks.push({name,status:'passed'});}
async function main() {
  await fs.mkdir(output,{recursive:true});
  const {chromium} = require('playwright');
  browser = await chromium.launch({headless:true,
    ...(process.env.HFA_BROWSER_EXECUTABLE?{executablePath:process.env.HFA_BROWSER_EXECUTABLE}:{}),
    args:['--no-sandbox']});
  status.browser = browser.version();
  status.playwright = require('playwright/package.json').version;
  const html = await fs.readFile(reportPath,'utf8');
  const payload = JSON.parse(html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
  for (const [name,viewport,isMobile] of [['desktop',{width:1440,height:1000},false],['mobile',{width:390,height:844},true]]) {
    const context = await browser.newContext({viewport,isMobile,hasTouch:isMobile,acceptDownloads:true,offline:true});
    const page = await context.newPage();
    const errors=[], external=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('request',request=>{if(/^https?:/.test(request.url()))external.push(request.url());});
    await page.goto(pathToFileURL(reportPath).href);
    await record(`${name}: loaded valid report without external requests`,async()=>{
      assert.equal(await page.locator('#report-error').isVisible(),false);
      assert.equal(await page.locator('#scenario-buttons button').count(),4);
      assert.deepEqual(errors,[]); assert.deepEqual(external,[]);
    });
    for(let i=0;i<payload.plans.length;i++) {
      await record(`${name}: scenario ${i} numbers, details, chart and exports`,async()=>{
        await page.locator('#scenario-buttons button').nth(i).click();
        assert.equal(await page.evaluate(()=>window.__financialAudit.getActive()),i);
        const result=payload.results[i], rows=result.deterministic_annual_ledger.rows;
        assert.equal(await page.locator('#metric-success').textContent(),`${(result.modeled_all_obligations_funded_fraction*100).toFixed(1)}%`);
        assert.equal(await page.locator('#audit-status').textContent(),'账本对账通过');
        assert.match(await page.locator('#review-status').textContent(),/尚无专业复核/);
        assert.equal(await page.locator('#asset-chart path').count(),3);
        await page.selectOption('#year-select',String(rows.at(-1).year));
        assert.equal(await page.evaluate(()=>window.__financialAudit.getYear()),rows.at(-1).year);
        assert.equal(await page.locator('#account-rows tr').count(),payload.plans[i].accounts.length);
        for(const [button,filename] of [['download-plan','plan.json'],['download-json','audit.json'],['download-csv','ledger.csv']]) {
          const promise=page.waitForEvent('download'); await page.locator('#'+button).click();
          const download=await promise, file=path.join(output,`${name}-${i}-${filename}`);
          await download.saveAs(file);
          const text=await fs.readFile(file,'utf8');
          if(button==='download-plan') {
            assert.deepEqual(JSON.parse(text),payload.plans[i]);
            assert.equal(text,payload.plan_json[i]); // Preserve 143000.0, -0.0, etc.
          }
          if(button==='download-json')assert.deepEqual(JSON.parse(text),{plan:payload.plans[i],result,verification:payload.verification[i]});
          if(button==='download-csv') {
            const lines=text.trim().split('\n'), keys=lines.shift().split(',');
            assert.equal(lines.length,rows.length);
            lines.forEach((line,j)=>assert.deepEqual(line.split(',').map(Number),keys.map(key=>rows[j][key])));
          }
        }
        // Replay the actual downloaded files, not merely the original payload.
        const exported=JSON.parse(await fs.readFile(path.join(output,`${name}-${i}-audit.json`),'utf8'));
        const resultFile=path.join(output,`${name}-${i}-result.json`);
        await fs.writeFile(resultFile,JSON.stringify(exported.result));
        const replay=spawnSync(process.env.PYTHON||'python3',['scripts/verify_replay.py',resultFile,'--plan',path.join(output,`${name}-${i}-plan.json`)],{cwd:path.resolve(__dirname,'..'),encoding:'utf8'});
        assert.equal(replay.status,0,replay.stdout+replay.stderr);
      });
    }
    await record(`${name}: viewport layout`,async()=>{
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'page overflows viewport');
      await page.screenshot({path:path.join(output,`${name}.png`),fullPage:true});
    });
    await record(`${name}: print styling and print action`,async()=>{
      await page.evaluate(()=>{window.__printed=false;window.print=()=>{window.__printed=true;};});
      await page.locator('#print').click();
      assert.equal(await page.evaluate(()=>window.__printed),true);
      await page.emulateMedia({media:'print'});
      assert.equal(await page.locator('.actionrow').isVisible(),false);
      assert.equal(await page.locator('#sources').isVisible(),true);
      await page.pdf({path:path.join(output,`${name}-print.pdf`),format:'A4'});
    });
    assert.deepEqual(errors,[]); assert.deepEqual(external,[]);
    await context.close();
  }
  const context=await browser.newContext({offline:true}), page=await context.newPage();
  const invalidCases=[['invalid-json','{'],['empty',JSON.stringify({plans:[],results:[],verification:[],labels:[]})],['failed-verification',JSON.stringify({...payload,verification:payload.verification.map(v=>({...v,passed:false}))})]];
  for(const scenario of payload.results.keys()) for(const laterYear of [false,true]) {
    for(const target of ['chart','tax-detail']) {
      const broken=JSON.parse(JSON.stringify(payload));
      const result=broken.results[scenario], year=laterYear?result.deterministic_annual_ledger.rows.length-1:0;
      if(target==='chart')result.annual_real_percentiles[year].p50='invalid';
      else result.deterministic_annual_ledger.rows[year].tax.ordinary_tax='invalid';
      invalidCases.push([`${target}-${scenario}-${year}`,JSON.stringify(broken)]);
    }
  }
  for(const [name,raw] of invalidCases) {
    await record(`error state: ${name}`,async()=>{
      const broken=html.replace(/(<script id="data" type="application\/json">)[\s\S]*?(<\/script>)/,(_,start,end)=>start+raw+end);
      const file=path.join(output,`${name}.html`);await fs.writeFile(file,broken);
      await page.goto(pathToFileURL(file).href);
      assert.equal(await page.locator('#report-error').isVisible(),true);
      assert.equal(await page.locator('#report-content').isVisible(),false);
      for(const id of ['download-plan','download-json','download-csv','print']) {
        assert.equal(await page.locator('#'+id).isDisabled(),true);
      }
      assert.equal(await page.locator('#scenario-buttons button').count(),0);
      assert.equal(await page.locator('#asset-chart path').count(),0);
    });
  }
  await context.close(); status.status='passed';
}
main().catch(error=>{status.status='failed';status.error=String(error);process.exitCode=1;})
  .finally(async()=>{if(browser)await browser.close();await fs.mkdir(output,{recursive:true});await fs.writeFile(path.join(output,'browser-status.json'),JSON.stringify(status,null,2)+'\n');console.log(JSON.stringify(status));});
