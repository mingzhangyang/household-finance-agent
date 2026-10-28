// Execute the actual report script with a minimal DOM for status and exports.
// This is a handler regression test, not a browser layout/acceptance test.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const raw = html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const payload = JSON.parse(raw);
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
const script = html.match(/<script>\s*('use strict';[\s\S]*?)<\/script>/)[1];
vm.runInContext(script, context);
(async () => {
  for (let i = 0; i < payload.plans.length; i++) {
    element('scenario-buttons').children[i].click();
    assert.equal(context.window.__financialAudit.getActive(), i);
    assert.equal(element('year-status').textContent, '出现资金/规则缺口');
    // The fixture has only a skipped conversion in 2027 and is funded in 2028.
    element('year-select').value = '2028';
    element('year-select').onchange();
    assert.equal(element('year-status').textContent, '对账通过');
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
  console.log('PASS: yearly skipped-conversion status and four scenario plan/audit downloads');
})().catch(error => { console.error(error); process.exitCode = 1; });
