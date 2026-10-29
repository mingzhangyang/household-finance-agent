// Execute the actual report script with a minimal DOM for status and exports.
// This is a handler regression test, not a browser layout/acceptance test.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
let raw = html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const payload = JSON.parse(raw);
const script = html.match(/<script>\s*('use strict';[\s\S]*?)<\/script>/)[1];
const invalidMode = process.argv[3];
if (invalidMode === 'empty') raw = JSON.stringify({plans:[],results:[],labels:[],verification:[]});
if (invalidMode === 'invalid-json') raw = '{';
if (invalidMode === 'failed-verification') raw = JSON.stringify({...payload,verification:payload.verification.map(v=>({...v,passed:false}))});
if (invalidMode === 'second-scenario') {
  const broken=JSON.parse(raw);broken.results[1].deterministic_annual_ledger.rows[0].tax.federal_income_tax='invalid';
  raw=JSON.stringify(broken);
}
if (['invalid-notice','duplicate-notice-year','notice-year-outside-ledger',
     'invalid-skipped-conversion','invalid-rmd-record'].includes(invalidMode)) {
  const broken=JSON.parse(raw), ledger=broken.results[2].deterministic_annual_ledger;
  const notice=(year,id)=>({year,blocks:[`${id}: early distributions before 60 not modeled`]});
  if(invalidMode==='invalid-notice')ledger.notices=[{year:ledger.rows[0].year,blocks:[1]}];
  // The year audit shows one notice per ledger year; others would be hidden.
  else if(invalidMode==='duplicate-notice-year')ledger.notices=[notice(ledger.rows[0].year,'ira_a'),notice(ledger.rows[0].year,'roth_a')];
  else if(invalidMode==='notice-year-outside-ledger')ledger.notices=[notice(ledger.rows.at(-1).year+1,'ira_a')];
  else if(invalidMode==='invalid-skipped-conversion')ledger.rows[0].skipped_conversions=[{from:'ira_a',amount:'1',reason:'test'}];
  else ledger.rows[0].rmd=[{account:'ira_a',required:1,taken:'1',unmet:0}];
  raw=JSON.stringify(broken);
}
if (['missing-plan-json','invalid-plan-json','mismatched-plan-json'].includes(invalidMode)) {
  const broken=JSON.parse(raw);
  if(invalidMode==='missing-plan-json')delete broken.plan_json;
  else if(invalidMode==='invalid-plan-json')broken.plan_json[3]='{';
  else {const changed=JSON.parse(broken.plan_json[3]);changed.living_expenses_annual_real+=1;broken.plan_json[3]=JSON.stringify(changed);}
  raw=JSON.stringify(broken);
}
function boot(raw) {
const downloads = [];
const blobs = new Map();
let nextUrl = 0;
class Element {
  constructor(tag) {
    this.tag = tag; this.children = []; this.dataset = {}; this.style = {};
    this.classList = {toggle() {}};
  }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(name, value) { this[name] = value; }
  addEventListener(name, handler) { this['on' + name] = handler; }
  querySelectorAll() { return this.children; }
  click() {
    if (this.tag === 'a') downloads.push({name: this.download, blob: blobs.get(this.href)});
    else this.onclick();
  }
}
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, new Element('div'));
  return elements.get(id);
};
element('data').textContent = raw;
// The print labels reuse the real account table headings.
const accountHead=html.match(/class="table account-ledger"><thead>([\s\S]*?)<\/thead>/)[1];
element('account-rows').closest=()=>({tHead:{rows:[{cells:[...accountHead.matchAll(/<th>(.*?)<\/th>/g)].map(m=>({textContent:m[1]}))}]}});
const context = vm.createContext({
  document: {
    getElementById: element,
    createElement: tag => new Element(tag),
    createElementNS: (_, tag) => new Element(tag),
  },
  window: {print() {}}, Blob, Intl,
  URL: {createObjectURL(blob) {const url = String(nextUrl++); blobs.set(url, blob); return url;},
        revokeObjectURL(url) {blobs.delete(url);}},
  setTimeout() {},
});
vm.runInContext(script, context);
return {element,context,downloads};
}
function assertRejected(raw, beforeRender=false) {
  const {element,context,downloads}=boot(raw);
  assert.equal(context.window.__financialAudit.error, 'invalid_report');
  assert.equal(element('report-error').hidden, false);
  assert.equal(element('report-content').style.display, 'none');
  for (const id of ['download-plan','download-json','download-csv','print']) assert.equal(element(id).disabled,true);
  assert.equal(downloads.length,0);
  if(beforeRender) {
    assert.equal(element('scenario-buttons').children.length,0);
    assert.equal(element('asset-chart').children.length,0);
  }
}
if (invalidMode === 'numeric-mutations') {
  let cases=0;
  const paths=[
    ...['p10','p50','p90','year'].map(key=>['annual_real_percentiles',0,key]),
    ...['ordinary_tax','capital_gains_tax','adjusted_gross_income','taxable_social_security',
        'standard_plus_age_deduction','enhanced_senior_deduction','ordinary_taxable',
        'long_term_gain_taxable','niit_due','niit_tax_base'].map(key=>['deterministic_annual_ledger','rows',0,'tax',key]),
    ...['wages_gross','social_security_gross','pension_gross','pretax_contributions',
        'other_after_tax_income','investment_growth_total','living_expenses_due','living_expenses_paid',
        'opening_total','closing_total','closing_total_real','rmd_total','roth_converted',
        'tax_paid','unpaid_tax','unmet_spending','reconciliation_residual'].map(key=>['deterministic_annual_ledger','rows',0,key]),
    ['deterministic_annual_ledger','rows',0,'payroll_tax','total'],
    ['deterministic_annual_ledger','rows',0,'account_flows','cash','contribution'],
    ['deterministic_annual_ledger','rows',0,'account_reconciliation_residuals','cash'],
    ['deterministic_annual_ledger','rows',0,'tax','capital_gain_rate_lines',0,'taxable'],
    ['deterministic_annual_ledger','rows',0,'tax','ordinary_bracket_lines',0,'rate'],
  ];
  for(const scenario of payload.results.keys()) for(const lastYear of [false,true]) {
    for(const path of paths) for(const value of ['invalid',null,true]) {
      const broken=JSON.parse(raw), parts=path.slice();
      if(lastYear) parts[parts[0]==='annual_real_percentiles'?1:2]=broken.results[scenario].deterministic_annual_ledger.rows.length-1;
      let target=broken.results[scenario];
      for(const part of parts.slice(0,-1))target=target[part];
      target[parts.at(-1)]=value;
      try {assertRejected(JSON.stringify(broken),true);}
      catch(error){error.message=`scenario ${scenario}, ${parts.join('.')}, ${JSON.stringify(value)}: ${error.message}`;throw error;}
      cases++;
    }
  }
  console.log(`PASS: ${cases} malformed numeric fields rejected before any scenario rendering`);
  process.exit(0);
}
if (invalidMode === 'rule-basis-mutations') {
  // A projection may never be shown as published law; malformed labels fail closed.
  let cases=0;
  const mutations=[
    basis=>{basis.income_tax_tables.status='published';basis.income_tax_tables.multiplier=1},
    basis=>{basis.oasdi_wage_base.status='projected'},
    basis=>{basis.income_tax_tables.status='enacted'},
    basis=>{basis.income_tax_tables.base_year='2026'},
    basis=>{basis.income_tax_tables.base_year=2099},
    basis=>{basis.elective_deferral_limit.multiplier='1.02'},
    basis=>{basis.elective_deferral_limit.multiplier=0},
    basis=>{basis.oasdi_wage_base.source_id=''},
    basis=>{delete basis.elective_deferral_limit},
    basis=>{basis.state_tax_tables=basis.income_tax_tables},
  ];
  for(const scenario of payload.results.keys()) for(const [index,mutate] of mutations.entries()) {
    const broken=JSON.parse(raw);
    mutate(broken.results[scenario].deterministic_annual_ledger.rows[0].rule_basis);
    try {assertRejected(JSON.stringify(broken),true);}
    catch(error){error.message=`scenario ${scenario}, mutation ${index}: ${error.message}`;throw error;}
    cases++;
  }
  const missing=JSON.parse(raw);delete missing.results[0].deterministic_annual_ledger.rows.at(-1).rule_basis;
  assertRejected(JSON.stringify(missing),true);cases++;
  console.log(`PASS: ${cases} malformed or overstated rule-basis labels rejected before rendering`);
  process.exit(0);
}
if (invalidMode === 'tax-method-text') {
  for(const method of ['ordinary_rate_cap','stacked_capital_gains']) {
    const changed=JSON.parse(raw);changed.results[0].deterministic_annual_ledger.rows[0].tax.income_tax_method=method;
    const {element,context}=boot(JSON.stringify(changed));
    assert.equal(context.window.__financialAudit.getActive(),0);
    assert.equal(element('tax-details').children[1].textContent,
      method==='ordinary_rate_cap'?'普通税率上限（较低税额）':'资本利得优惠税率叠加');
  }
  console.log('PASS: explicit text-valued tax method remains supported');
  process.exit(0);
}
if (invalidMode === 'notices') {
  // Fictional blocked early retirees: every scenario discloses the four skipped
  // retirement accounts and the conversion that could not execute in 2027.
  const {element,context}=boot(raw);
  const notes=()=>element('year-notices').children.map(li=>li.textContent);
  for (let i = 0; i < payload.plans.length; i++) {
    element('scenario-buttons').children[i].click();
    assert.equal(context.window.__financialAudit.getActive(), i);
    assert.equal(element('year-status').textContent, '出现资金/规则缺口');
    assert.deepEqual(notes(), [...['ira_a','401k_a','401k_b','roth_a'].map(id=>
      `未满 60 岁账户未用于支付：${id}: early distributions before 60 not modeled`),
      'Roth 转换未执行：ira_a 计划转出 $1,000,000.00（insufficient source balance after RMD）']);
  }
  console.log('PASS: blocked accounts and skipped conversions disclosed in every scenario');
  process.exit(0);
}
if (invalidMode && invalidMode !== 'export-files') {
  assertRejected(raw,true);
  console.log('PASS: invalid report hides conclusions and disables exports: '+invalidMode);
  process.exit(0);
}
const {element,context,downloads}=boot(raw);
(async () => {
  for (let i = 0; i < payload.plans.length; i++) {
    element('scenario-buttons').children[i].click();
    assert.equal(context.window.__financialAudit.getActive(), i);
    if (invalidMode === 'export-files') {
      element('download-plan').click();element('download-json').click();
      const [plan,audit]=downloads.slice(-2);
      fs.writeFileSync(`${process.argv[4]}/plan-${i}.json`,await plan.blob.text());
      fs.writeFileSync(`${process.argv[4]}/audit-${i}.json`,await audit.blob.text());
      continue;
    }
    assert.equal(element('year-status').textContent, '出现资金/规则缺口');
    const notes=()=>element('year-notices').children.map(li=>li.textContent);
    assert.deepEqual(notes(), ['Roth 转换未执行：ira_a 计划转出 $1,000,000.00（insufficient source balance after RMD）']);
    const basis=()=>element('year-rule-basis').children.map(li=>li.textContent);
    const index=payload.plans[i].tax_policy.future_bracket_inflation;
    assert.deepEqual(basis(), [
      `所得税税阶、标准扣除与资本利得门槛：2026 年已公布数值 × ${(1+index).toFixed(8)}，按方案假设指数推算到 2027 年，不是已公布的 2027 年数值（brackets_standard_senior）`,
      '社保工资上限：2027 年已公布数值（payroll_2027）',
      `401(k) 基本缴款限额：2026 年已公布数值 × ${(1+index).toFixed(8)}，按方案假设指数推算到 2027 年，不是已公布的 2027 年数值（401k_elective_limit_2026）`]);
    // The fixture has only a skipped conversion in 2027 and is funded in 2028.
    element('year-select').value = '2028';
    element('year-select').onchange();
    assert.equal(element('year-status').textContent, '对账通过');
    assert.deepEqual(notes(), ['本年度没有提款限制、未执行的转换或 RMD 缺口。']);
    assert.match(basis()[1], /^社保工资上限：2027 年已公布数值 × [0-9.]{10}，按方案假设指数推算到 2028 年，不是已公布的 2028 年数值（payroll_2027）$/);
    element('download-plan').click();
    element('download-json').click();
    const [plan, audit] = downloads.slice(-2);
    assert.equal(plan.name, 'financial-plan.json');
    assert.deepEqual(JSON.parse(await plan.blob.text()), payload.plans[i]);
    assert.equal(audit.name, 'financial-audit.json');
    assert.deepEqual(JSON.parse(await audit.blob.text()), {
      plan: payload.plans[i], result: payload.results[i], verification: payload.verification[i],
    });
  }
  console.log(invalidMode==='export-files'?'PASS: exported four actual plan/audit download blobs':
    'PASS: yearly skipped-conversion status and four scenario plan/audit downloads');
})().catch(error => { console.error(error); process.exitCode = 1; });
