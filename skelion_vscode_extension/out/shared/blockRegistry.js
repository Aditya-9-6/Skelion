"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.BlockRegistry = void 0;
const chat_js_1 = require("./chat.js");
class BlockRegistry {
    static definitions = new Map();
    static register(def) {
        this.definitions.set(def.type, def);
    }
    static get(type) {
        return this.definitions.get(type);
    }
    static has(type) {
        return this.definitions.has(type);
    }
    static validate(rawBlock) {
        const parseResult = chat_js_1.BlockSchema.safeParse(rawBlock);
        if (parseResult.success) {
            return { success: true, data: parseResult.data };
        }
        const fallbackId = (rawBlock && typeof rawBlock === 'object' && 'id' in rawBlock && typeof rawBlock.id === 'string')
            ? rawBlock.id
            : `unsupported_${Date.now()}`;
        const fallback = {
            type: 'unsupported',
            id: fallbackId,
            raw: rawBlock,
        };
        return {
            success: false,
            fallback,
            error: parseResult.error.message,
        };
    }
    static listTypes() {
        return Array.from(this.definitions.keys());
    }
}
exports.BlockRegistry = BlockRegistry;
// Initialize all block definitions
BlockRegistry.register({ type: 'markdown', label: 'Markdown', schema: chat_js_1.MarkdownBlockSchema, supportedExports: ['markdown'] });
BlockRegistry.register({ type: 'code', label: 'Code Snippet', schema: chat_js_1.CodeBlockSchema, supportedExports: ['markdown', 'json'] });
BlockRegistry.register({ type: 'table', label: 'Data Table', schema: chat_js_1.TableBlockSchema, supportedExports: ['csv', 'json', 'markdown'], allowsWideView: true });
BlockRegistry.register({ type: 'chart', label: 'Metric Chart', schema: chat_js_1.ChartBlockSchema, isLazy: true, supportedExports: ['png', 'svg', 'csv', 'json'], allowsWideView: true });
BlockRegistry.register({ type: 'stat_tiles', label: 'Stat Tiles', schema: chat_js_1.StatTilesBlockSchema, supportedExports: ['json'] });
BlockRegistry.register({ type: 'diagram', label: 'Architecture Diagram', schema: chat_js_1.DiagramBlockSchema, isLazy: true, supportedExports: ['svg', 'png', 'markdown'], allowsWideView: true });
BlockRegistry.register({ type: 'diff', label: 'Code Diff', schema: chat_js_1.DiffBlockSchema, supportedExports: ['markdown'], allowsWideView: true });
BlockRegistry.register({ type: 'file_ref', label: 'File Reference', schema: chat_js_1.FileRefBlockSchema });
BlockRegistry.register({ type: 'file_tree', label: 'File Tree', schema: chat_js_1.FileTreeBlockSchema });
BlockRegistry.register({ type: 'link_card', label: 'Link Card', schema: chat_js_1.LinkCardBlockSchema });
BlockRegistry.register({ type: 'timeline', label: 'Event Timeline', schema: chat_js_1.TimelineBlockSchema, supportedExports: ['json'] });
BlockRegistry.register({ type: 'log_viewer', label: 'Log Stream', schema: chat_js_1.LogViewerBlockSchema, isLazy: true, supportedExports: ['csv', 'json'], allowsWideView: true });
BlockRegistry.register({ type: 'request_inspector', label: 'Request Inspector', schema: chat_js_1.RequestInspectorBlockSchema, allowsWideView: true });
BlockRegistry.register({ type: 'json', label: 'JSON Data', schema: chat_js_1.JsonBlockSchema, supportedExports: ['json'] });
BlockRegistry.register({ type: 'callout', label: 'Callout Alert', schema: chat_js_1.CalloutBlockSchema });
BlockRegistry.register({ type: 'steps', label: 'Plan Steps', schema: chat_js_1.StepsBlockSchema });
BlockRegistry.register({ type: 'incident_card', label: 'Incident Card', schema: chat_js_1.IncidentCardBlockSchema, allowsWideView: true });
BlockRegistry.register({ type: 'fix_card', label: 'Fix Proposal & Replay Card', schema: chat_js_1.FixCardBlockSchema, allowsWideView: true });
BlockRegistry.register({ type: 'replay_evidence', label: 'Replay Evidence', schema: chat_js_1.ReplayEvidenceBlockSchema, allowsWideView: true });
BlockRegistry.register({ type: 'credit_estimate', label: 'Credit Estimate', schema: chat_js_1.CreditEstimateBlockSchema });
BlockRegistry.register({ type: 'actions', label: 'Action Bar', schema: chat_js_1.ActionsBlockSchema });
BlockRegistry.register({ type: 'image', label: 'Image', schema: chat_js_1.ImageBlockSchema });
BlockRegistry.register({ type: 'sources', label: 'Sources & Provenance', schema: chat_js_1.SourcesBlockSchema });
BlockRegistry.register({ type: 'pr_card', label: 'Autonomous PR Card', schema: chat_js_1.PrCardBlockSchema, allowsWideView: true, supportedExports: ['json', 'markdown'] });
BlockRegistry.register({ type: 'unsupported', label: 'Unsupported Block', schema: chat_js_1.UnsupportedBlockSchema });
//# sourceMappingURL=blockRegistry.js.map