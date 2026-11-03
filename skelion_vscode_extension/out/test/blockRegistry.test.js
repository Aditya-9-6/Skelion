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
exports.runTests = runTests;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const blockRegistry_js_1 = require("../shared/blockRegistry.js");
const chat_js_1 = require("../shared/chat.js");
function runTests() {
    console.log('--- Running BlockRegistry & Fixture Validation Tests ---');
    let passed = 0;
    let failed = 0;
    function assert(condition, name) {
        if (condition) {
            console.log(`✓ PASS: ${name}`);
            passed++;
        }
        else {
            console.error(`✗ FAIL: ${name}`);
            failed++;
        }
    }
    // 1. Check all registered types
    const types = blockRegistry_js_1.BlockRegistry.listTypes();
    assert(types.length >= 20, `BlockRegistry has ${types.length} types registered (expected >= 20)`);
    assert(blockRegistry_js_1.BlockRegistry.has('markdown'), 'BlockRegistry has markdown');
    assert(blockRegistry_js_1.BlockRegistry.has('chart'), 'BlockRegistry has chart');
    assert(blockRegistry_js_1.BlockRegistry.has('table'), 'BlockRegistry has table');
    assert(blockRegistry_js_1.BlockRegistry.has('fix_card'), 'BlockRegistry has fix_card');
    assert(blockRegistry_js_1.BlockRegistry.has('pr_card'), 'BlockRegistry has pr_card');
    assert(blockRegistry_js_1.BlockRegistry.has('stat_tiles'), 'BlockRegistry has stat_tiles');
    // 2. Validate Golden Fixtures from JSON file
    const fixturesPath = path.resolve(__dirname, '../../fixtures/golden_conversations.json');
    assert(fs.existsSync(fixturesPath), `Golden fixtures file exists at ${fixturesPath}`);
    const rawJson = fs.readFileSync(fixturesPath, 'utf-8');
    const conversations = JSON.parse(rawJson);
    assert(Array.isArray(conversations), 'Golden fixtures is an array');
    for (const conv of conversations) {
        const parseResult = chat_js_1.ConversationSchema.safeParse(conv);
        assert(parseResult.success, `Conversation "${conv.id}" parsed cleanly with ConversationSchema`);
        if (!parseResult.success) {
            console.error('Validation error:', parseResult.error);
        }
    }
    // 3. Test Unsupported Block Fallback
    const unknownBlock = {
        type: 'hyper_dimensional_matrix',
        id: 'unknown_1',
        data: [1, 2, 3],
    };
    const valResult = blockRegistry_js_1.BlockRegistry.validate(unknownBlock);
    assert(!valResult.success, 'Unknown block flagged as non-standard');
    if (!valResult.success) {
        assert(valResult.fallback.type === 'unsupported', 'Unknown block normalized to unsupported fallback');
    }
    // 4. Test Valid Block Parse via BlockRegistry
    const validMd = {
        type: 'markdown',
        id: 'md_test',
        text: 'Hello world',
    };
    const validResult = blockRegistry_js_1.BlockRegistry.validate(validMd);
    assert(validResult.success, 'Valid markdown block passes BlockRegistry validation');
    console.log(`\nTest Summary: ${passed} passed, ${failed} failed.`);
    return failed === 0;
}
if (require.main === module) {
    const success = runTests();
    process.exit(success ? 0 : 1);
}
//# sourceMappingURL=blockRegistry.test.js.map