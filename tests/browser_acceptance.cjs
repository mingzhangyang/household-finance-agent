// Real Chromium, offline file:// input. Not the minimal-DOM handler regression.
// npm ci --ignore-scripts && npx --no-install playwright install chromium
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {spawnSync} = require('node:child_process');
const output = path.resolve(process.argv[3]);
const reportPath = path.resolve(process.argv[2]);
let browser;
const status = {status:'running', checks:[], limitations:['Mobile viewport emulation is not a physical iOS/Safari test.']};
// JSON.stringify turns -0 into 0. They have the same monetary value; retain
// every other value/type/key and keep the separate plan byte comparison below.
function signedZero(value) {
  if(typeof value==='number')return Object.is(value,-0)?0:value;
  if(Array.isArray(value))return value.map(signedZero);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,signedZero(v)]));
  return value;
}
const dollars=(value,digits)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:digits,maximumFractionDigits:digits}).format(value);
async function record(name, fn) {await fn(); status.checks.push({name,status:'passed'});}
// Engine records the year audit must disclose verbatim; the page derives no amounts.
function expectedNotices(result,row) {
  const items=[];
  const notice=result.deterministic_annual_ledger.notices.find(n=>n.year===row.year);
  if(notice)for(const block of notice.blocks)items.push('未满 60 岁账户未用于支付：'+block);
  for(const s of row.skipped_conversions)items.push(`Roth 转换未执行：${s.from} 计划转出 ${dollars(s.amount,2)}（${s.reason}）`);
  for(const item of row.rmd)if(Math.round(item.unmet*100)>0)items.push(`RMD 未足额：${item.account} 应提 ${dollars(item.required,2)}，实提 ${dollars(item.taken,2)}`);
  return items.length?items:['本年度没有提款限制、未执行的转换或 RMD 缺口。'];
}
function expectedRuleBasis(row) {
  const names={income_tax_tables:'所得税税阶、标准扣除与资本利得门槛',oasdi_wage_base:'社保工资上限',elective_deferral_limit:'401(k) 基本缴款限额'};
  return Object.entries(names).map(([family,name])=>{const b=row.rule_basis[family];
    return b.status==='published'?`${name}：${b.base_year} 年已公布数值（${b.source_id}）`
      :`${name}：${b.base_year} 年已公布数值 × ${b.multiplier.toFixed(8)}，按方案假设指数推算到 ${row.year} 年，不是已公布的 ${row.year} 年数值（${b.source_id}）`});
}
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
    await record(`${name}: Chinese glyphs have a CJK font`,async()=>{
      const cdp=await context.newCDPSession(page);
      await cdp.send('DOM.enable'); await cdp.send('CSS.enable');
      const {root}=await cdp.send('DOM.getDocument');
      const {nodeId}=await cdp.send('DOM.querySelector',{nodeId:root.nodeId,selector:'h1'});
      const {fonts}=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});
      assert.ok(fonts.some(f=>f.glyphCount>0&&/CJK|PingFang|Heiti|SimSun|YaHei|WenQuanYi/i.test(f.familyName)),
        'Chinese font unavailable; install fonts-noto-cjk before visual acceptance');
      status.cjk_fonts=fonts.map(f=>f.familyName); await cdp.detach();
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
        const table=await page.locator('#cashflow-rows tr').evaluateAll(trs=>trs.map(tr=>[...tr.cells].map(td=>td.textContent)));
        assert.deepEqual(table,rows.map(row=>[String(row.year),...[row.wages_gross,row.pretax_contributions,
          row.social_security_gross+row.pension_gross,row.living_expenses_due,row.tax_due_total,
          row.closing_total,row.unmet_spending+row.unpaid_tax+row.unmet_rmd].map(v=>dollars(v,0))]));
        await page.screenshot({path:path.join(output,`${name}-scenario-${i}.png`),fullPage:true});
        // Visit every year: a valid first year cannot hide broken later details.
        for(const row of rows) {
          await page.selectOption('#year-select',String(row.year));
          const ui=await page.evaluate(()=>({
            heading:document.querySelector('#year-heading').textContent,
            tax:[...document.querySelectorAll('#tax-details dd')].map(x=>x.textContent),
            notices:[...document.querySelectorAll('#year-notices li')].map(x=>x.textContent),
            basis:[...document.querySelectorAll('#year-rule-basis li')].map(x=>x.textContent),
            accounts:[...document.querySelectorAll('#account-rows tr')].map(tr=>[...tr.cells].map(td=>td.textContent))
          }));
          assert.equal(ui.heading,`${row.year} 年度逐项审计`);
          assert.deepEqual(ui.notices,expectedNotices(result,row));
          assert.deepEqual(ui.basis,expectedRuleBasis(row));
          assert.deepEqual(ui.tax.slice(1),[row.wages_taxable,row.tax.taxable_social_security,
            row.realized_ltcg,row.ira_extra_taxable,row.tax.adjusted_gross_income,
            row.tax.standard_plus_age_deduction,row.tax.enhanced_senior_deduction,row.tax.ordinary_taxable,
            row.tax.long_term_gain_taxable,row.tax.ordinary_tax,row.tax.capital_gains_tax,
            row.tax.niit_due,row.tax.niit_tax_base,row.payroll_tax.total,row.tax_due_total].map(v=>dollars(v,2)));
          assert.deepEqual(ui.accounts,Object.keys(row.closing_accounts).map(id=>{
            const f=row.account_flows[id];
            return [id,...[row.opening_accounts[id],row.growth_by_account[id],f.contribution,
              f.required_distribution,f.roth_conversion_out,f.roth_conversion_in,f.optional_draw,
              f.cash_external_inflow,f.cash_received_rmd,f.cash_received_draws,f.cash_tax_and_spending_outflow,
              row.closing_accounts[id],row.account_reconciliation_residuals[id]].map(v=>dollars(v,2))];
          }));
        }
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
          if(button==='download-json') {
            assert.ok(text.startsWith('{\n"plan":'+payload.plan_json[i]+',\n"result":'));
            assert.deepEqual(signedZero(JSON.parse(text)),signedZero({plan:payload.plans[i],result,verification:payload.verification[i]}));
          }
          if(button==='download-csv') {
            const lines=text.trim().split('\n'), keys=lines.shift().split(',');
            assert.equal(lines.length,rows.length);
            lines.forEach((line,j)=>assert.deepEqual(signedZero(line.split(',').map(Number)),signedZero(keys.map(key=>rows[j][key]))));
          }
        }
        // Replay the actual downloaded files, not merely the original payload.
        const exported=JSON.parse(await fs.readFile(path.join(output,`${name}-${i}-audit.json`),'utf8'));
        const resultFile=path.join(output,`${name}-${i}-result.json`);
        await fs.writeFile(resultFile,JSON.stringify(exported.result));
        const replay=spawnSync(process.env.PYTHON||'python3',['scripts/verify_replay.py',resultFile,'--plan',path.join(output,`${name}-${i}-plan.json`)],{cwd:path.resolve(__dirname,'..'),encoding:'utf8'});
        assert.equal(replay.status,0,replay.stdout+replay.stderr);
        const bundleReplay=spawnSync(process.env.PYTHON||'python3',['-c',
          'import json,sys; sys.path.insert(0,"scripts"); from verify_replay import verify_replay; b=json.load(open(sys.argv[1])); print(verify_replay(b["result"],b["plan"]))',
          path.join(output,`${name}-${i}-audit.json`)],{cwd:path.resolve(__dirname,'..'),encoding:'utf8',timeout:60000});
        assert.equal(bundleReplay.status,0,bundleReplay.stdout+bundleReplay.stderr);
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
      // A4 content width after the template's 12mm margins, independent of
      // desktop/mobile screen width. Catch the old clipped 14-column ledger.
      await page.setViewportSize({width:703,height:1000});
      assert.equal(await page.locator('.actionrow').isVisible(),false);
      assert.equal(await page.locator('#sources').isVisible(),true);
      assert.equal(await page.locator('#path-audit').isVisible(),false);
      const print=await page.evaluate(()=>({
        clipped:[...document.querySelectorAll('.scrolltable')].filter(x=>x.getClientRects().length).some(x=>x.scrollHeight>x.clientHeight+1),
        wide:[...document.querySelectorAll('.table')].some(x=>x.getBoundingClientRect().right>innerWidth+1),
        labels:[...document.querySelectorAll('#account-rows tr:first-child td')].map(x=>getComputedStyle(x,'::before').content)
      }));
      assert.equal(print.clipped,false,'print must include every row of visible tables');
      assert.equal(print.wide,false,'print tables must fit the paper');
      assert.ok(print.labels.includes('"期末"')&&print.labels.includes('"残差"'),'closing balances and residual labels must print');
      await page.pdf({path:path.join(output,`${name}-print.pdf`),format:'A4',preferCSSPageSize:true});
    });
    assert.deepEqual(errors,[]); assert.deepEqual(external,[]);
    await context.close();
  }
  const context=await browser.newContext({offline:true}), page=await context.newPage();
  const invalidCases=[['invalid-json','{'],['empty',JSON.stringify({plans:[],results:[],verification:[],labels:[]})],['failed-verification',JSON.stringify({...payload,verification:payload.verification.map(v=>({...v,passed:false}))})]];
  for(const scenario of payload.results.keys()) for(const laterYear of [false,true]) {
    for(const target of ['chart','tax-detail','rule-basis']) {
      const broken=JSON.parse(JSON.stringify(payload));
      const result=broken.results[scenario], year=laterYear?result.deterministic_annual_ledger.rows.length-1:0;
      if(target==='chart')result.annual_real_percentiles[year].p50='invalid';
      else if(target==='tax-detail')result.deterministic_annual_ledger.rows[year].tax.ordinary_tax='invalid';
      // A projected year coherently relabeled as its own published year must not render.
      else {
        const row=result.deterministic_annual_ledger.rows[year];
        Object.assign(row.rule_basis.income_tax_tables,{status:'published',base_year:row.year,multiplier:1});
        Object.assign(row.tax,{tax_law_year:row.year,rule_multiplier:1,policy:`${row.year} published federal tables`});
      }
      invalidCases.push([`${target}-${scenario}-${year}`,JSON.stringify(broken)]);
    }
  }
  await record('notice records render in a real browser',async()=>{
    // Rendering only: inject one engine-shaped notice and skipped conversion.
    const shaped=JSON.parse(JSON.stringify(payload)), result=shaped.results[0], row=result.deterministic_annual_ledger.rows[0];
    result.deterministic_annual_ledger.notices=[{year:row.year,blocks:['ira: early distributions before 60 not modeled']}];
    row.skipped_conversions=[{year:row.year,from:'ira',amount:1000,reason:'insufficient source balance after RMD'}];
    const file=path.join(output,'notice-rendering.html');
    await fs.writeFile(file,html.replace(/(<script id="data" type="application\/json">)[\s\S]*?(<\/script>)/,(_,start,end)=>start+JSON.stringify(shaped)+end));
    await page.goto(pathToFileURL(file).href);
    assert.equal(await page.locator('#report-error').isVisible(),false);
    assert.deepEqual(await page.locator('#year-notices li').allTextContents(),expectedNotices(result,row));
    assert.equal(await page.locator('#year-status').textContent(),'出现资金/规则缺口');
  });
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
