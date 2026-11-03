"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ActivityUpdateEventSchema = exports.ToolEndEventSchema = exports.ToolProgressEventSchema = exports.ToolStartEventSchema = exports.BlockEndEventSchema = exports.BlockDeltaEventSchema = exports.BlockStartEventSchema = exports.MessageStartEventSchema = exports.ConversationSchema = exports.MessageSchema = exports.MessageUsageSchema = exports.BlockSchema = exports.UnsupportedBlockSchema = exports.PrCardBlockSchema = exports.PrTimelineStageSchema = exports.PrStageStatusSchema = exports.SourcesBlockSchema = exports.ImageBlockSchema = exports.ActionsBlockSchema = exports.ActionItemSchema = exports.CreditEstimateBlockSchema = exports.ReplayEvidenceBlockSchema = exports.FixCardBlockSchema = exports.IncidentCardBlockSchema = exports.StepsBlockSchema = exports.StepItemSchema = exports.CalloutBlockSchema = exports.JsonBlockSchema = exports.RequestInspectorBlockSchema = exports.LogViewerBlockSchema = exports.TimelineBlockSchema = exports.TimelineEventSchema = exports.LinkCardBlockSchema = exports.FileTreeBlockSchema = exports.TreeNodeSchema = exports.FileRefBlockSchema = exports.DiffBlockSchema = exports.DiagramBlockSchema = exports.StatTilesBlockSchema = exports.StatTileItemSchema = exports.ChartBlockSchema = exports.LiveSpecSchema = exports.ChartSeriesSchema = exports.ChartAxisSchema = exports.TableBlockSchema = exports.TableColumnSchema = exports.CodeBlockSchema = exports.MarkdownBlockSchema = exports.AllowedActionSchema = exports.ProvenanceSchema = void 0;
exports.HostToWebviewMessageSchema = exports.WebviewToHostMessageSchema = exports.ContextChipSchema = exports.StreamingEventSchema = exports.ErrorEventSchema = exports.MessageEndEventSchema = exports.UsageEventSchema = exports.LiveTickEventSchema = void 0;
const zod_1 = require("zod");
// ============================================================================
// PROVENANCE & COMMON SCHEMAS
// ============================================================================
exports.ProvenanceSchema = zod_1.z.object({
    source: zod_1.z.enum(['incident_store', 'proxy_capture', 'replay', 'tool', 'user_file']),
    query_id: zod_1.z.string(),
    asOf: zod_1.z.string(),
    range: zod_1.z.string().optional(),
    redaction: zod_1.z.enum(['applied', 'partial', 'none']),
    rowCount: zod_1.z.number().optional(),
});
exports.AllowedActionSchema = zod_1.z.enum([
    'open_file',
    'reveal_file',
    'copy',
    'export',
    'open_in_editor',
    'open_native_diff',
    'approve_fix',
    'reject_fix',
    'revert_fix',
    'run_replay',
    'open_incident',
    'open_url',
    'upgrade',
    'buy_credits',
    'confirm_credit_estimate',
    'trigger_pr_cycle',
]);
// ============================================================================
// BLOCK SCHEMAS
// ============================================================================
exports.MarkdownBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('markdown'),
    id: zod_1.z.string(),
    text: zod_1.z.string(),
});
exports.CodeBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('code'),
    id: zod_1.z.string(),
    lang: zod_1.z.string().optional(),
    filename: zod_1.z.string().optional(),
    text: zod_1.z.string(),
    actions: zod_1.z.array(zod_1.z.enum(['copy', 'insert', 'apply', 'run'])).optional(),
});
exports.TableColumnSchema = zod_1.z.object({
    key: zod_1.z.string(),
    label: zod_1.z.string(),
    kind: zod_1.z.enum(['text', 'number', 'percent', 'duration', 'timestamp', 'badge', 'path', 'link', 'code', 'sparkline']).optional(),
    width: zod_1.z.number().optional(),
    align: zod_1.z.enum(['left', 'center', 'right']).optional(),
});
exports.TableBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('table'),
    id: zod_1.z.string(),
    title: zod_1.z.string().optional(),
    columns: zod_1.z.array(exports.TableColumnSchema),
    data_ref: zod_1.z.string().optional(),
    rows: zod_1.z.array(zod_1.z.record(zod_1.z.unknown())).optional(),
    provenance: exports.ProvenanceSchema.optional(),
    actions: zod_1.z.array(exports.AllowedActionSchema).optional(),
});
exports.ChartAxisSchema = zod_1.z.object({
    field: zod_1.z.string(),
    type: zod_1.z.enum(['time', 'category', 'linear']).optional(),
    label: zod_1.z.string().optional(),
    unit: zod_1.z.string().optional(),
});
exports.ChartSeriesSchema = zod_1.z.object({
    name: zod_1.z.string(),
    field: zod_1.z.string(),
    color: zod_1.z.string().optional(),
    strokeWidth: zod_1.z.number().optional(),
});
exports.LiveSpecSchema = zod_1.z.object({
    intervalMs: zod_1.z.number().optional(),
    windowSeconds: zod_1.z.number().optional(),
    paused: zod_1.z.boolean().optional(),
});
exports.ChartBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('chart'),
    id: zod_1.z.string(),
    title: zod_1.z.string().optional(),
    kind: zod_1.z.enum(['line', 'bar', 'area', 'pie', 'scatter', 'stacked_bar']),
    x: exports.ChartAxisSchema,
    y: zod_1.z.array(exports.ChartAxisSchema),
    series: zod_1.z.array(exports.ChartSeriesSchema),
    data_ref: zod_1.z.string().optional(),
    live: exports.LiveSpecSchema.optional(),
    provenance: exports.ProvenanceSchema.optional(),
});
exports.StatTileItemSchema = zod_1.z.object({
    label: zod_1.z.string(),
    value: zod_1.z.union([zod_1.z.string(), zod_1.z.number()]),
    unit: zod_1.z.string().optional(),
    delta: zod_1.z.string().optional(),
    trend: zod_1.z.enum(['up', 'down', 'flat']).optional(),
    severity: zod_1.z.enum(['info', 'warn', 'crit']).optional(),
    data_ref: zod_1.z.string().optional(),
});
exports.StatTilesBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('stat_tiles'),
    id: zod_1.z.string(),
    tiles: zod_1.z.array(exports.StatTileItemSchema),
});
exports.DiagramBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('diagram'),
    id: zod_1.z.string(),
    syntax: zod_1.z.literal('mermaid'),
    text: zod_1.z.string(),
});
exports.DiffBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('diff'),
    id: zod_1.z.string(),
    filename: zod_1.z.string(),
    patch: zod_1.z.string(),
    stats: zod_1.z.object({ added: zod_1.z.number(), removed: zod_1.z.number() }).optional(),
    fix_id: zod_1.z.string().optional(),
});
exports.FileRefBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('file_ref'),
    id: zod_1.z.string(),
    path: zod_1.z.string(),
    line: zod_1.z.number().optional(),
    endLine: zod_1.z.number().optional(),
    label: zod_1.z.string().optional(),
});
exports.TreeNodeSchema = zod_1.z.lazy(() => zod_1.z.object({
    name: zod_1.z.string(),
    path: zod_1.z.string(),
    type: zod_1.z.enum(['file', 'dir']),
    children: zod_1.z.array(exports.TreeNodeSchema).optional(),
}));
exports.FileTreeBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('file_tree'),
    id: zod_1.z.string(),
    root: zod_1.z.string(),
    nodes: zod_1.z.array(exports.TreeNodeSchema),
});
exports.LinkCardBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('link_card'),
    id: zod_1.z.string(),
    url: zod_1.z.string().url(),
    title: zod_1.z.string().optional(),
    description: zod_1.z.string().optional(),
});
exports.TimelineEventSchema = zod_1.z.object({
    ts: zod_1.z.string(),
    label: zod_1.z.string(),
    severity: zod_1.z.enum(['info', 'warn', 'danger', 'success']).optional(),
    detail: zod_1.z.string().optional(),
});
exports.TimelineBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('timeline'),
    id: zod_1.z.string(),
    events: zod_1.z.array(exports.TimelineEventSchema),
});
exports.LogViewerBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('log_viewer'),
    id: zod_1.z.string(),
    data_ref: zod_1.z.string(),
    filters: zod_1.z.record(zod_1.z.unknown()).optional(),
});
exports.RequestInspectorBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('request_inspector'),
    id: zod_1.z.string(),
    data_ref: zod_1.z.string(),
});
exports.JsonBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('json'),
    id: zod_1.z.string(),
    data_ref: zod_1.z.string().optional(),
    value: zod_1.z.unknown().optional(),
    collapsed: zod_1.z.number().optional(),
});
exports.CalloutBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('callout'),
    id: zod_1.z.string(),
    level: zod_1.z.enum(['info', 'warn', 'danger', 'success']),
    title: zod_1.z.string().optional(),
    text: zod_1.z.string(),
});
exports.StepItemSchema = zod_1.z.object({
    label: zod_1.z.string(),
    status: zod_1.z.enum(['pending', 'running', 'done', 'failed', 'skipped']),
    detail: zod_1.z.string().optional(),
});
exports.StepsBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('steps'),
    id: zod_1.z.string(),
    items: zod_1.z.array(exports.StepItemSchema),
});
exports.IncidentCardBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('incident_card'),
    id: zod_1.z.string(),
    incident_id: zod_1.z.string(),
});
exports.FixCardBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('fix_card'),
    id: zod_1.z.string(),
    fix_id: zod_1.z.string(),
});
exports.ReplayEvidenceBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('replay_evidence'),
    id: zod_1.z.string(),
    fix_id: zod_1.z.string(),
});
exports.CreditEstimateBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('credit_estimate'),
    id: zod_1.z.string(),
    credits: zod_1.z.number(),
    detail: zod_1.z.string().optional(),
    requires_confirm: zod_1.z.boolean().optional(),
});
exports.ActionItemSchema = zod_1.z.object({
    action_id: exports.AllowedActionSchema,
    label: zod_1.z.string(),
    args: zod_1.z.record(zod_1.z.unknown()).optional(),
    style: zod_1.z.enum(['primary', 'secondary', 'danger']).optional(),
});
exports.ActionsBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('actions'),
    id: zod_1.z.string(),
    items: zod_1.z.array(exports.ActionItemSchema),
});
exports.ImageBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('image'),
    id: zod_1.z.string(),
    data_uri: zod_1.z.string().optional(),
    artifact_id: zod_1.z.string().optional(),
    alt: zod_1.z.string(),
});
exports.SourcesBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('sources'),
    id: zod_1.z.string(),
    items: zod_1.z.array(zod_1.z.object({ label: zod_1.z.string(), ref: zod_1.z.string() })),
});
exports.PrStageStatusSchema = zod_1.z.enum([
    'pending',
    'running',
    'passed',
    'failed',
    'clean',
    'conflict',
    'resolved',
]);
exports.PrTimelineStageSchema = zod_1.z.object({
    key: zod_1.z.string(),
    title: zod_1.z.string(),
    status: exports.PrStageStatusSchema,
    detail: zod_1.z.string().optional(),
    icon: zod_1.z.string().optional(),
});
exports.PrCardBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('pr_card'),
    id: zod_1.z.string(),
    pr_number: zod_1.z.number(),
    pr_url: zod_1.z.string(),
    title: zod_1.z.string(),
    branch: zod_1.z.string(),
    author: zod_1.z.string().optional(),
    target_branch: zod_1.z.string().optional(),
    stages: zod_1.z.array(exports.PrTimelineStageSchema),
    ci_status: zod_1.z.object({
        state: zod_1.z.string(),
        passed: zod_1.z.number(),
        total: zod_1.z.number(),
    }).optional(),
    merge_status: zod_1.z.object({
        mergeable: zod_1.z.boolean(),
        state: zod_1.z.string(),
    }).optional(),
    review_status: zod_1.z.object({
        comments_count: zod_1.z.number(),
        actions_count: zod_1.z.number(),
    }).optional(),
    actions: zod_1.z.array(exports.AllowedActionSchema).optional(),
});
exports.UnsupportedBlockSchema = zod_1.z.object({
    type: zod_1.z.literal('unsupported'),
    id: zod_1.z.string(),
    raw: zod_1.z.unknown(),
});
exports.BlockSchema = zod_1.z.discriminatedUnion('type', [
    exports.MarkdownBlockSchema,
    exports.CodeBlockSchema,
    exports.TableBlockSchema,
    exports.ChartBlockSchema,
    exports.StatTilesBlockSchema,
    exports.DiagramBlockSchema,
    exports.DiffBlockSchema,
    exports.FileRefBlockSchema,
    exports.FileTreeBlockSchema,
    exports.LinkCardBlockSchema,
    exports.TimelineBlockSchema,
    exports.LogViewerBlockSchema,
    exports.RequestInspectorBlockSchema,
    exports.JsonBlockSchema,
    exports.CalloutBlockSchema,
    exports.StepsBlockSchema,
    exports.IncidentCardBlockSchema,
    exports.FixCardBlockSchema,
    exports.ReplayEvidenceBlockSchema,
    exports.CreditEstimateBlockSchema,
    exports.ActionsBlockSchema,
    exports.ImageBlockSchema,
    exports.SourcesBlockSchema,
    exports.PrCardBlockSchema,
    exports.UnsupportedBlockSchema,
]);
// ============================================================================
// MESSAGE & CONVERSATION SCHEMAS
// ============================================================================
exports.MessageUsageSchema = zod_1.z.object({
    credits: zod_1.z.number().optional(),
    tokensIn: zod_1.z.number().optional(),
    tokensOut: zod_1.z.number().optional(),
    costEstimate: zod_1.z.boolean().optional(),
});
exports.MessageSchema = zod_1.z.object({
    id: zod_1.z.string(),
    role: zod_1.z.enum(['user', 'assistant', 'system']),
    createdAt: zod_1.z.string(),
    status: zod_1.z.enum(['streaming', 'done', 'error', 'stopped']),
    blocks: zod_1.z.array(exports.BlockSchema),
    model: zod_1.z.string().optional(),
    usage: exports.MessageUsageSchema.optional(),
    parentId: zod_1.z.string().optional(),
});
exports.ConversationSchema = zod_1.z.object({
    id: zod_1.z.string(),
    title: zod_1.z.string(),
    createdAt: zod_1.z.string(),
    updatedAt: zod_1.z.string(),
    messages: zod_1.z.array(exports.MessageSchema),
    model: zod_1.z.string().optional(),
    pinned: zod_1.z.boolean().optional(),
});
// ============================================================================
// STREAMING PROTOCOL SCHEMAS
// ============================================================================
exports.MessageStartEventSchema = zod_1.z.object({
    event: zod_1.z.literal('message.start'),
    messageId: zod_1.z.string(),
    model: zod_1.z.string().optional(),
});
exports.BlockStartEventSchema = zod_1.z.object({
    event: zod_1.z.literal('block.start'),
    messageId: zod_1.z.string(),
    block: exports.BlockSchema,
});
exports.BlockDeltaEventSchema = zod_1.z.object({
    event: zod_1.z.literal('block.delta'),
    messageId: zod_1.z.string(),
    blockId: zod_1.z.string(),
    op: zod_1.z.enum(['append', 'replace', 'patch']),
    text: zod_1.z.string().optional(),
    json: zod_1.z.unknown().optional(),
});
exports.BlockEndEventSchema = zod_1.z.object({
    event: zod_1.z.literal('block.end'),
    messageId: zod_1.z.string(),
    blockId: zod_1.z.string(),
});
exports.ToolStartEventSchema = zod_1.z.object({
    event: zod_1.z.literal('tool.start'),
    id: zod_1.z.string(),
    name: zod_1.z.string(),
    argsPreview: zod_1.z.string().optional(),
});
exports.ToolProgressEventSchema = zod_1.z.object({
    event: zod_1.z.literal('tool.progress'),
    id: zod_1.z.string(),
    pct: zod_1.z.number().optional(),
    note: zod_1.z.string().optional(),
});
exports.ToolEndEventSchema = zod_1.z.object({
    event: zod_1.z.literal('tool.end'),
    id: zod_1.z.string(),
    status: zod_1.z.enum(['ok', 'error']),
    elapsedMs: zod_1.z.number(),
    resultRef: zod_1.z.string().optional(),
});
exports.ActivityUpdateEventSchema = zod_1.z.object({
    event: zod_1.z.literal('activity.update'),
    steps: zod_1.z.array(exports.StepItemSchema),
});
exports.LiveTickEventSchema = zod_1.z.object({
    event: zod_1.z.literal('live.tick'),
    blockId: zod_1.z.string(),
    data_ref: zod_1.z.string(),
    patch: zod_1.z.unknown(),
});
exports.UsageEventSchema = zod_1.z.object({
    event: zod_1.z.literal('usage'),
    credits: zod_1.z.number().optional(),
    tokensIn: zod_1.z.number().optional(),
    tokensOut: zod_1.z.number().optional(),
});
exports.MessageEndEventSchema = zod_1.z.object({
    event: zod_1.z.literal('message.end'),
    messageId: zod_1.z.string(),
    status: zod_1.z.enum(['done', 'error', 'stopped']),
});
exports.ErrorEventSchema = zod_1.z.object({
    event: zod_1.z.literal('error'),
    code: zod_1.z.string(),
    message: zod_1.z.string(),
    requestId: zod_1.z.string().optional(),
});
exports.StreamingEventSchema = zod_1.z.discriminatedUnion('event', [
    exports.MessageStartEventSchema,
    exports.BlockStartEventSchema,
    exports.BlockDeltaEventSchema,
    exports.BlockEndEventSchema,
    exports.ToolStartEventSchema,
    exports.ToolProgressEventSchema,
    exports.ToolEndEventSchema,
    exports.ActivityUpdateEventSchema,
    exports.LiveTickEventSchema,
    exports.UsageEventSchema,
    exports.MessageEndEventSchema,
    exports.ErrorEventSchema,
]);
// ============================================================================
// WEBVIEW <-> HOST PROTOCOL SCHEMAS
// ============================================================================
exports.ContextChipSchema = zod_1.z.object({
    type: zod_1.z.enum(['file', 'selection', 'incident', 'service']),
    label: zod_1.z.string(),
    value: zod_1.z.string(),
});
exports.WebviewToHostMessageSchema = zod_1.z.discriminatedUnion('type', [
    zod_1.z.object({ type: zod_1.z.literal('ready') }),
    zod_1.z.object({
        type: zod_1.z.literal('sendMessage'),
        text: zod_1.z.string(),
        model: zod_1.z.string().optional(),
        mode: zod_1.z.enum(['ask', 'agent']).optional(),
        conversationId: zod_1.z.string().optional(),
        contextChips: zod_1.z.array(exports.ContextChipSchema).optional(),
    }),
    zod_1.z.object({
        type: zod_1.z.literal('stop'),
        conversationId: zod_1.z.string().optional(),
        messageId: zod_1.z.string().optional(),
    }),
    zod_1.z.object({ type: zod_1.z.literal('regenerate'), messageId: zod_1.z.string() }),
    zod_1.z.object({ type: zod_1.z.literal('editMessage'), messageId: zod_1.z.string(), text: zod_1.z.string() }),
    zod_1.z.object({ type: zod_1.z.literal('selectModel'), model: zod_1.z.string() }),
    zod_1.z.object({ type: zod_1.z.literal('setMode'), mode: zod_1.z.enum(['ask', 'agent']) }),
    zod_1.z.object({ type: zod_1.z.literal('loadConversation'), conversationId: zod_1.z.string() }),
    zod_1.z.object({ type: zod_1.z.literal('listConversations') }),
    zod_1.z.object({ type: zod_1.z.literal('renameConversation'), conversationId: zod_1.z.string(), title: zod_1.z.string() }),
    zod_1.z.object({ type: zod_1.z.literal('deleteConversation'), conversationId: zod_1.z.string() }),
    zod_1.z.object({
        type: zod_1.z.literal('requestData'),
        data_ref: zod_1.z.string(),
        range: zod_1.z.string().optional(),
        page: zod_1.z.number().optional(),
    }),
    zod_1.z.object({ type: zod_1.z.literal('subscribeLive'), data_ref: zod_1.z.string() }),
    zod_1.z.object({ type: zod_1.z.literal('unsubscribeLive'), data_ref: zod_1.z.string() }),
    zod_1.z.object({
        type: zod_1.z.literal('action'),
        action_id: exports.AllowedActionSchema,
        args: zod_1.z.record(zod_1.z.unknown()).optional(),
    }),
    zod_1.z.object({
        type: zod_1.z.literal('copy'),
        format: zod_1.z.enum(['text', 'markdown', 'csv', 'json']),
        payload: zod_1.z.string(),
    }),
    zod_1.z.object({
        type: zod_1.z.literal('export'),
        kind: zod_1.z.enum(['csv', 'json', 'png', 'svg', 'md', 'html']),
        payload: zod_1.z.string(),
        filename: zod_1.z.string().optional(),
    }),
    zod_1.z.object({ type: zod_1.z.literal('openArtifact'), id: zod_1.z.string() }),
    zod_1.z.object({ type: zod_1.z.literal('setContext'), chips: zod_1.z.array(exports.ContextChipSchema) }),
    zod_1.z.object({
        type: zod_1.z.literal('feedback'),
        messageId: zod_1.z.string(),
        vote: zod_1.z.enum(['up', 'down']),
        reason: zod_1.z.string().optional(),
    }),
]);
exports.HostToWebviewMessageSchema = zod_1.z.discriminatedUnion('type', [
    zod_1.z.object({
        type: zod_1.z.literal('init'),
        user: zod_1.z.record(zod_1.z.unknown()).nullable(),
        token: zod_1.z.string().nullable(),
        plan: zod_1.z.string(),
        creditsRemaining: zod_1.z.number().optional(),
        models: zod_1.z.array(zod_1.z.object({ id: zod_1.z.string(), label: zod_1.z.string(), costClass: zod_1.z.string() })).optional(),
    }),
    zod_1.z.object({ type: zod_1.z.literal('conversation'), conversation: exports.ConversationSchema }),
    zod_1.z.object({ type: zod_1.z.literal('streamEvent'), event: exports.StreamingEventSchema }),
    zod_1.z.object({
        type: zod_1.z.literal('data'),
        data_ref: zod_1.z.string(),
        data: zod_1.z.unknown(),
        provenance: exports.ProvenanceSchema.optional(),
    }),
    zod_1.z.object({
        type: zod_1.z.literal('liveTick'),
        blockId: zod_1.z.string(),
        data_ref: zod_1.z.string(),
        patch: zod_1.z.unknown(),
    }),
    zod_1.z.object({ type: zod_1.z.literal('toast'), message: zod_1.z.string(), level: zod_1.z.enum(['info', 'warn', 'error']).optional() }),
    zod_1.z.object({ type: zod_1.z.literal('themeChanged'), theme: zod_1.z.enum(['light', 'dark', 'high-contrast']) }),
    zod_1.z.object({
        type: zod_1.z.literal('error'),
        code: zod_1.z.string(),
        message: zod_1.z.string(),
        requestId: zod_1.z.string().optional(),
    }),
]);
//# sourceMappingURL=chat.js.map