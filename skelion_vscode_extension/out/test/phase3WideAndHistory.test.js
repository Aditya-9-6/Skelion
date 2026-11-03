"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const chat_js_1 = require("../shared/chat.js");
const chatExport_js_1 = require("../shared/chatExport.js");
function assert(condition, msg) {
    if (!condition) {
        console.error(`FAILED: ${msg}`);
        process.exit(1);
    }
    console.log(`✓ PASS: ${msg}`);
}
async function runPhase3Tests() {
    console.log('--- Running Phase 3: Wide View, Artifacts & History Tests ---');
    // Load golden conversation fixture
    const fixturePath = path.resolve(__dirname, '../../fixtures/golden_conversations.json');
    assert(fs.existsSync(fixturePath), 'Golden conversations fixture exists');
    const rawJson = fs.readFileSync(fixturePath, 'utf-8');
    const conversations = JSON.parse(rawJson);
    const goldenConv = chat_js_1.ConversationSchema.parse(conversations[0]);
    // Test 1: Export to Markdown
    const mdExport = (0, chatExport_js_1.exportConversationAsMarkdown)(goldenConv);
    assert(typeof mdExport === 'string' && mdExport.length > 200, 'Markdown export generated non-empty string');
    assert(mdExport.includes('# Incident Triage & Checkout 429 Storm'), 'Markdown export contains conversation title');
    assert(mdExport.includes('### Top Active Incidents'), 'Markdown export contains table title');
    assert(mdExport.includes('| Issue | Route | Affected % | Type |'), 'Markdown export formats table headers');
    assert(mdExport.includes('```diff'), 'Markdown export formats diff code blocks');
    assert(mdExport.includes('### 📈 Chart: Error rate by minute (last 24h)'), 'Markdown export contains chart summary');
    // Test 2: Export to JSON
    const jsonExport = (0, chatExport_js_1.exportConversationAsJson)(goldenConv);
    const reParsed = JSON.parse(jsonExport);
    const validation = chat_js_1.ConversationSchema.safeParse(reParsed);
    assert(validation.success, 'JSON export roundtrips cleanly through ConversationSchema');
    // Test 3: Extract Artifacts from Conversation
    const artifacts = (0, chatExport_js_1.extractArtifactsFromConversation)(goldenConv);
    assert(artifacts.length >= 4, `Extracted ${artifacts.length} artifacts (expected >= 4)`);
    const chartArtifact = artifacts.find(a => a.type === 'chart');
    assert(!!chartArtifact, 'Chart artifact successfully extracted');
    assert(chartArtifact?.title === 'Error rate by minute (last 24h)', 'Chart artifact title matches');
    const tableArtifact = artifacts.find(a => a.type === 'table');
    assert(!!tableArtifact, 'Table artifact successfully extracted');
    assert(tableArtifact?.title === 'Top Active Incidents', 'Table artifact title matches');
    const diffArtifact = artifacts.find(a => a.type === 'diff');
    assert(!!diffArtifact, 'Diff artifact successfully extracted');
    assert(diffArtifact?.title === 'gossipmesh/p2p/congestion.py', 'Diff artifact filename matches');
    const incidentArtifact = artifacts.find(a => a.type === 'incident');
    assert(!!incidentArtifact, 'Incident artifact successfully extracted');
    const prConv = chat_js_1.ConversationSchema.parse(conversations[3]);
    const prArtifacts = (0, chatExport_js_1.extractArtifactsFromConversation)(prConv);
    const prArtifact = prArtifacts.find(a => a.type === 'pr');
    assert(!!prArtifact, 'PR artifact successfully extracted');
    assert(Boolean(prArtifact && prArtifact.title.includes('PR #190')), 'PR artifact title includes #190');
    // Test 4: Parse Slash Commands
    const cmdIncident = (0, chatExport_js_1.parseSlashCommand)('/incident 190');
    assert(cmdIncident?.command === 'incident' && cmdIncident?.args === '190', 'Parses /incident 190 correctly');
    const cmdFix = (0, chatExport_js_1.parseSlashCommand)('/fix checkout_429 --replay');
    assert(cmdFix?.command === 'fix' && cmdFix?.args === 'checkout_429 --replay', 'Parses /fix with flags correctly');
    const cmdExplain = (0, chatExport_js_1.parseSlashCommand)('/explain');
    assert(cmdExplain?.command === 'explain' && cmdExplain?.args === '', 'Parses zero-arg command /explain correctly');
    const cmdAudit = (0, chatExport_js_1.parseSlashCommand)('/audit full');
    assert(cmdAudit?.command === 'audit' && cmdAudit?.args === 'full', 'Parses /audit command correctly');
    const notCmd = (0, chatExport_js_1.parseSlashCommand)('regular user question');
    assert(notCmd === null, 'Non-slash input returns null');
    // Test 5: Parse @ Mentions
    const mentions1 = (0, chatExport_js_1.parseMentions)('Check @congestion.py and @incident_190 for details');
    assert(mentions1.includes('congestion.py') && mentions1.includes('incident_190'), 'Parses multiple mentions cleanly');
    const mentionsPath = (0, chatExport_js_1.parseMentions)('See path @gossipmesh/p2p/congestion.py:260 for fix');
    assert(mentionsPath.includes('gossipmesh/p2p/congestion.py:260'), 'Parses path-style mentions cleanly');
    console.log('\nPhase 3 Tests: All passed successfully!');
}
runPhase3Tests().catch(err => {
    console.error('Phase 3 test suite failed:', err);
    process.exit(1);
});
//# sourceMappingURL=phase3WideAndHistory.test.js.map