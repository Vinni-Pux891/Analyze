// API/DOM integration smoke test; run with node tests/dashboard_smoke.cjs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
    constructor() {
        this.children = [];
        this.value = '0';
        this.style = {};
        this.files = [{}];
        this.listeners = {};
        this.classList = { add() {}, remove() {}, toggle() {} };
    }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    replaceChildren() { this.children = []; }
    appendChild(child) { this.children.push(child); return child; }
    append(...children) { this.children.push(...children); }
    setAttribute() {}
}
const elements = new Map();
const get = id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
};
const analysis = score => ({
    rows: 1, columns: 8, missing_values: 0, duplicates: 0,
    risk_score: score, anomalies: [], statistics: {}, note: 'v2',
});
const result = {
    success: true,
    dataset_analysis: { rows: 2, missing_values: 1, duplicates: 0, anomalies: [] },
    results: [
        { row: 2, company: { id: 11, name: 'Первая' }, analysis: analysis(77), ai_report: 'Локальный анализ' },
        { row: 3, company: { id: 12, name: 'Вторая' }, analysis: analysis(0), ai_report: 'Локальный анализ' },
    ],
};
const context = vm.createContext({
    document: { getElementById: get, createElement: () => new Element() },
    window: { riskBands: { medium: 30, high: 71 }, matchMedia: () => ({ matches: true }), scrollTo() {} },
    cancelAnimationFrame() {},
    FormData: class { append() {} },
    Chart: class { destroy() {} },
    alert(message) { throw new Error(message); },
    fetch: async url => ({ ok: true, json: async () => url === '/api/analyze' ? result
        : url === '/api/graph' ? { nodes: [], edges: [] } : { success: true, regions: [] } }),
});
vm.runInContext(fs.readFileSync('static/app.js', 'utf8'), context);
(async () => {
    await vm.runInContext('analyzeData()', context);
    assert.equal(get('companyResultSelect').children.length, 2);
    assert.equal(get('riskScore').textContent, 77);
    assert.equal(vm.runInContext('currentCompanyId', context), 11);
    get('companyResultSelect').value = '1';
    get('companyResultSelect').listeners.change();
    assert.equal(get('riskScore').textContent, 0);
    assert.equal(vm.runInContext('currentCompanyId', context), 12);
    assert.match(get('datasetQuality').textContent, /Строк: 2/);
    console.log('Batch selection updates company score and report download ID: OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
