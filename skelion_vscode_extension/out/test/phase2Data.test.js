"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const downsample_js_1 = require("../shared/downsample.js");
const dataBridge_js_1 = require("../host/dataBridge.js");
const blockRegistry_js_1 = require("../shared/blockRegistry.js");
const chat_js_1 = require("../shared/chat.js");
function assert(condition, msg) {
    if (!condition) {
        console.error(`FAILED: ${msg}`);
        process.exit(1);
    }
    console.log(`✓ PASS: ${msg}`);
}
async function runPhase2Tests() {
    console.log('--- Running Phase 2: Data, Downsampling & Card Tests ---');
    // Test 1: LTTB downsampling preserves endpoints and extreme spikes
    const rawData = [];
    for (let i = 0; i < 5000; i++) {
        // Normal noise around 10, with an extreme spike at i = 2500
        const val = i === 2500 ? 999.0 : 10 + Math.sin(i / 10);
        rawData.push({ x: i, y: val });
    }
    const targetThreshold = 200;
    const downsampled = (0, downsample_js_1.downsampleLTTB)(rawData, targetThreshold, d => d.x, d => d.y);
    assert(downsampled.length === targetThreshold, `Downsampled length equals target (${downsampled.length} === ${targetThreshold})`);
    assert(downsampled[0].x === 0, 'First endpoint is strictly preserved');
    assert(downsampled[downsampled.length - 1].x === 4999, 'Last endpoint is strictly preserved');
    // Verify the extreme peak (999.0) was captured by LTTB
    const maxPoint = downsampled.reduce((max, p) => (p.y > max.y ? p : max), downsampled[0]);
    assert(maxPoint.y === 999.0, `Extreme peak (999.0) was preserved by LTTB (got ${maxPoint.y})`);
    // Test 2: DataBridge resolver for q_err_rate_24h
    const dataBridge = new dataBridge_js_1.DataBridge('http://127.0.0.1:8003', async () => null);
    const errRateRes = await dataBridge.resolveDataRef('q_err_rate_24h');
    assert(errRateRes !== null, 'DataBridge resolves q_err_rate_24h');
    assert(errRateRes?.provenance.source === 'proxy_capture', 'q_err_rate_24h provenance source is proxy_capture');
    assert(Array.isArray(errRateRes?.data), 'q_err_rate_24h returns array of points');
    assert((errRateRes?.data).length <= 2000, 'q_err_rate_24h respects 2000-point performance budget');
    // Test 3: DataBridge resolver for q_incident_190
    const incRes = await dataBridge.resolveDataRef('q_incident_190');
    assert(incRes !== null, 'DataBridge resolves q_incident_190');
    const incData = incRes?.data;
    assert(incData.id === '190', 'Incident ID is 190');
    assert(incData.severity === 'CRITICAL', 'Incident severity is CRITICAL');
    assert(incData.classification === 'bug', 'Incident classification is bug');
    assert(Array.isArray(incData.routes) && incData.routes.includes('/v1/checkout'), 'Affected route is /v1/checkout');
    assert(Array.isArray(incData.sparkline) && incData.sparkline.length > 5, 'Incident has sparkline telemetry data');
    assert(incRes?.provenance.source === 'incident_store', 'Incident provenance source is incident_store');
    // Test 4: DataBridge resolver for q_fix_checkout_429
    const fixRes = await dataBridge.resolveDataRef('q_fix_checkout_429');
    assert(fixRes !== null, 'DataBridge resolves q_fix_checkout_429');
    const fixData = fixRes?.data;
    assert(fixData.fix_id === 'fix_checkout_429', 'Fix ID is fix_checkout_429');
    assert(fixData.replayed_count === 120, 'Replayed transactions count is 120');
    assert(fixData.total_count === 120, 'Total transactions count is 120');
    assert(fixData.regressions === 0, 'Zero regressions confirmed');
    assert(fixData.confidence === 99.4, 'Confidence is 99.4%');
    assert(fixRes?.provenance.source === 'replay', 'Fix provenance source is replay');
    // Test 5: BlockRegistry validation for IncidentCard
    const incBlock = {
        type: 'incident_card',
        id: 'b_inc_1',
        incident_id: '190',
    };
    const valInc = chat_js_1.IncidentCardBlockSchema.safeParse(incBlock);
    assert(valInc.success, 'IncidentCardBlockSchema parses valid incident card');
    assert(blockRegistry_js_1.BlockRegistry.has('incident_card'), 'incident_card is standard block in registry');
    // Test 6: BlockRegistry validation for FixCard & ReplayEvidence
    const fixBlock = {
        type: 'fix_card',
        id: 'b_fix_1',
        fix_id: 'fix_checkout_429',
    };
    const valFix = chat_js_1.FixCardBlockSchema.safeParse(fixBlock);
    assert(valFix.success, 'FixCardBlockSchema parses valid fix card');
    const replayBlock = {
        type: 'replay_evidence',
        id: 'b_replay_1',
        fix_id: 'fix_checkout_429',
    };
    const valReplay = chat_js_1.ReplayEvidenceBlockSchema.safeParse(replayBlock);
    assert(valReplay.success, 'ReplayEvidenceBlockSchema parses valid replay evidence');
    // Test 7: BlockRegistry validation for CreditEstimate
    const credBlock = {
        type: 'credit_estimate',
        id: 'b_cred_1',
        credits: 42,
        detail: '120 sandboxed replays + GitHub PR synthesis',
        requires_confirm: true,
    };
    const valCred = chat_js_1.CreditEstimateBlockSchema.safeParse(credBlock);
    assert(valCred.success, 'CreditEstimateBlockSchema parses valid credit estimate');
    // Test 8: BlockRegistry validation for ChartBlock
    const chartBlock = {
        type: 'chart',
        id: 'b_chart_1',
        title: 'Error rate by minute',
        kind: 'line',
        x: { field: 'ts', type: 'time' },
        y: [{ field: 'error_rate', unit: '%' }],
        series: [{ name: '/v1/checkout', field: 'error_rate', color: '#f85149' }],
        data_ref: 'q_err_rate_24h',
    };
    const valChart = chat_js_1.ChartBlockSchema.safeParse(chartBlock);
    assert(valChart.success, 'ChartBlockSchema parses valid chart');
    // Test 9: DataBridge resolver for q_pr_190 & PrCardBlockSchema
    const prRes = await dataBridge.resolveDataRef('q_pr_190');
    assert(prRes !== null, 'DataBridge resolves q_pr_190');
    const prData = prRes?.data;
    assert(prData.pr_number === 190, 'PR number is 190');
    assert(prData.author === 'Aditya-9-6', 'PR author is Aditya-9-6');
    assert(prData.stages.length === 5, 'PR card has 5 autonomous stages');
    const prBlock = {
        type: 'pr_card',
        id: 'b_pr_test',
        ...prData
    };
    const valPr = chat_js_1.PrCardBlockSchema.safeParse(prBlock);
    assert(valPr.success, 'PrCardBlockSchema parses valid PR card');
    console.log('\nPhase 2 Tests: All passed successfully!');
}
runPhase2Tests().catch(err => {
    console.error('Phase 2 test suite failed:', err);
    process.exit(1);
});
//# sourceMappingURL=phase2Data.test.js.map