"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const assert_1 = __importDefault(require("assert"));
const chat_js_1 = require("../shared/chat.js");
const blockRegistry_js_1 = require("../shared/blockRegistry.js");
const dataBridge_js_1 = require("../host/dataBridge.js");
async function runPhase4Tests() {
    console.log('--- Running Phase 4: Advanced Blocks & Data Resolvers Tests ---');
    // 1. Diagram Block Schema
    const validDiagram = {
        type: 'diagram',
        id: 'b_diag_1',
        syntax: 'mermaid',
        text: 'graph TD\n  Client --> Proxy\n  Proxy --> Throttler',
    };
    const parsedDiag = chat_js_1.DiagramBlockSchema.safeParse(validDiagram);
    assert_1.default.strictEqual(parsedDiag.success, true);
    console.log('✓ PASS: DiagramBlockSchema parses valid mermaid diagram');
    const invalidDiagSyntax = {
        type: 'diagram',
        id: 'b_diag_inv',
        syntax: 'graphviz', // only mermaid allowed
        text: 'digraph { a -> b; }',
    };
    const parsedInvDiag = chat_js_1.DiagramBlockSchema.safeParse(invalidDiagSyntax);
    assert_1.default.strictEqual(parsedInvDiag.success, false);
    console.log('✓ PASS: DiagramBlockSchema strictly rejects non-mermaid syntax');
    // 2. Timeline Block Schema
    const validTimeline = {
        type: 'timeline',
        id: 'b_timeline_1',
        events: [
            { ts: '14:15:00 UTC', label: 'Deploy 2.1 Initiated', severity: 'info', detail: 'Tag deployed' },
            { ts: '14:20:12 UTC', label: 'HTTP 429 Surge Detected', severity: 'danger', detail: 'SLO breached' },
            { ts: '14:22:45 UTC', label: 'Incident #190 Auto-Triaged', severity: 'warn' },
            { ts: '14:25:30 UTC', label: 'Replay Sandbox Verified', severity: 'success' },
        ],
    };
    const parsedTimeline = chat_js_1.TimelineBlockSchema.safeParse(validTimeline);
    assert_1.default.strictEqual(parsedTimeline.success, true);
    console.log('✓ PASS: TimelineBlockSchema parses valid multi-event timeline');
    // 3. Log Viewer Block Schema
    const validLogViewer = {
        type: 'log_viewer',
        id: 'b_logs_1',
        data_ref: 'q_incident_190_logs',
        filters: { level: 'ERROR', route: '/v1/checkout' },
    };
    const parsedLogs = chat_js_1.LogViewerBlockSchema.safeParse(validLogViewer);
    assert_1.default.strictEqual(parsedLogs.success, true);
    console.log('✓ PASS: LogViewerBlockSchema parses valid log viewer spec');
    // 4. Request Inspector Block Schema
    const validReqInspector = {
        type: 'request_inspector',
        id: 'b_req_1',
        data_ref: 'q_sample_request_190',
    };
    const parsedReq = chat_js_1.RequestInspectorBlockSchema.safeParse(validReqInspector);
    assert_1.default.strictEqual(parsedReq.success, true);
    console.log('✓ PASS: RequestInspectorBlockSchema parses valid request inspector spec');
    // 5. JSON Block Schema
    const validJsonBlock = {
        type: 'json',
        id: 'b_json_1',
        value: {
            incident_id: 190,
            metrics: { error_rate_pct: 4.2 },
            redacted: true,
        },
        collapsed: 1,
    };
    const parsedJson = chat_js_1.JsonBlockSchema.safeParse(validJsonBlock);
    assert_1.default.strictEqual(parsedJson.success, true);
    console.log('✓ PASS: JsonBlockSchema parses valid interactive JSON tree spec');
    // 6. Block Registry verification
    assert_1.default.strictEqual(blockRegistry_js_1.BlockRegistry.has('diagram'), true);
    assert_1.default.strictEqual(blockRegistry_js_1.BlockRegistry.has('timeline'), true);
    assert_1.default.strictEqual(blockRegistry_js_1.BlockRegistry.has('log_viewer'), true);
    assert_1.default.strictEqual(blockRegistry_js_1.BlockRegistry.has('request_inspector'), true);
    assert_1.default.strictEqual(blockRegistry_js_1.BlockRegistry.has('json'), true);
    console.log('✓ PASS: BlockRegistry has all Phase 4 block types registered');
    // 7. DataBridge Resolvers for Logs and Request Inspector
    const bridge = new dataBridge_js_1.DataBridge('https://api.skelion.dev', async () => null);
    const logsRes = await bridge.resolveDataRef('q_incident_190_logs');
    assert_1.default.notStrictEqual(logsRes, null);
    assert_1.default.strictEqual(logsRes?.provenance.source, 'proxy_capture');
    assert_1.default.strictEqual(logsRes?.provenance.redaction, 'applied');
    const logEntries = logsRes?.data;
    assert_1.default.strictEqual(Array.isArray(logEntries), true);
    assert_1.default.strictEqual(logEntries.length, 4);
    assert_1.default.strictEqual(logEntries[0].level, 'ERROR');
    assert_1.default.strictEqual(logEntries[0].msg.includes('429 Too Many Requests'), true);
    console.log('✓ PASS: DataBridge resolves q_incident_190_logs with redacted entries');
    const reqRes = await bridge.resolveDataRef('q_sample_request_190');
    assert_1.default.notStrictEqual(reqRes, null);
    assert_1.default.strictEqual(reqRes?.provenance.source, 'proxy_capture');
    assert_1.default.strictEqual(reqRes?.provenance.redaction, 'applied');
    const reqData = reqRes?.data;
    assert_1.default.strictEqual(reqData.request.method, 'POST');
    assert_1.default.strictEqual(reqData.request.url.includes('/v1/checkout'), true);
    assert_1.default.strictEqual(reqData.response.status, 429);
    assert_1.default.strictEqual(reqData.response.latency_ms, 840);
    assert_1.default.strictEqual(reqData.request.headers.Authorization, 'Bearer [REDACTED:token]');
    console.log('✓ PASS: DataBridge resolves q_sample_request_190 with 429 payload and redacted auth headers');
    console.log('\nPhase 4 Tests: All 12 assertions passed successfully!');
}
runPhase4Tests().catch((err) => {
    console.error('Phase 4 Tests Failed:', err);
    process.exit(1);
});
//# sourceMappingURL=phase4AdvancedBlocks.test.js.map