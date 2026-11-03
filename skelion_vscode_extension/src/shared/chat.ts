import { z } from 'zod';

// ============================================================================
// PROVENANCE & COMMON SCHEMAS
// ============================================================================

export const ProvenanceSchema = z.object({
  source: z.enum(['incident_store', 'proxy_capture', 'replay', 'tool', 'user_file']),
  query_id: z.string(),
  asOf: z.string(),
  range: z.string().optional(),
  redaction: z.enum(['applied', 'partial', 'none']),
  rowCount: z.number().optional(),
});
export type Provenance = z.infer<typeof ProvenanceSchema>;

export const AllowedActionSchema = z.enum([
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
export type AllowedAction = z.infer<typeof AllowedActionSchema>;

// ============================================================================
// BLOCK SCHEMAS
// ============================================================================

export const MarkdownBlockSchema = z.object({
  type: z.literal('markdown'),
  id: z.string(),
  text: z.string(),
});

export const CodeBlockSchema = z.object({
  type: z.literal('code'),
  id: z.string(),
  lang: z.string().optional(),
  filename: z.string().optional(),
  text: z.string(),
  actions: z.array(z.enum(['copy', 'insert', 'apply', 'run'])).optional(),
});

export const TableColumnSchema = z.object({
  key: z.string(),
  label: z.string(),
  kind: z.enum(['text', 'number', 'percent', 'duration', 'timestamp', 'badge', 'path', 'link', 'code', 'sparkline']).optional(),
  width: z.number().optional(),
  align: z.enum(['left', 'center', 'right']).optional(),
});

export const TableBlockSchema = z.object({
  type: z.literal('table'),
  id: z.string(),
  title: z.string().optional(),
  columns: z.array(TableColumnSchema),
  data_ref: z.string().optional(),
  rows: z.array(z.record(z.string(), z.unknown())).optional(),
  provenance: ProvenanceSchema.optional(),
  actions: z.array(AllowedActionSchema).optional(),
});

export const ChartAxisSchema = z.object({
  field: z.string(),
  type: z.enum(['time', 'category', 'linear']).optional(),
  label: z.string().optional(),
  unit: z.string().optional(),
});

export const ChartSeriesSchema = z.object({
  name: z.string(),
  field: z.string(),
  color: z.string().optional(),
  strokeWidth: z.number().optional(),
});

export const LiveSpecSchema = z.object({
  intervalMs: z.number().optional(),
  windowSeconds: z.number().optional(),
  paused: z.boolean().optional(),
});

export const ChartBlockSchema = z.object({
  type: z.literal('chart'),
  id: z.string(),
  title: z.string().optional(),
  kind: z.enum(['line', 'bar', 'area', 'pie', 'scatter', 'stacked_bar']),
  x: ChartAxisSchema,
  y: z.array(ChartAxisSchema),
  series: z.array(ChartSeriesSchema),
  data_ref: z.string().optional(),
  live: LiveSpecSchema.optional(),
  provenance: ProvenanceSchema.optional(),
});

export const StatTileItemSchema = z.object({
  label: z.string(),
  value: z.union([z.string(), z.number()]),
  unit: z.string().optional(),
  delta: z.string().optional(),
  trend: z.enum(['up', 'down', 'flat']).optional(),
  severity: z.enum(['info', 'warn', 'crit']).optional(),
  data_ref: z.string().optional(),
});

export const StatTilesBlockSchema = z.object({
  type: z.literal('stat_tiles'),
  id: z.string(),
  tiles: z.array(StatTileItemSchema),
});

export const DiagramBlockSchema = z.object({
  type: z.literal('diagram'),
  id: z.string(),
  syntax: z.literal('mermaid'),
  text: z.string(),
});

export const DiffBlockSchema = z.object({
  type: z.literal('diff'),
  id: z.string(),
  filename: z.string(),
  patch: z.string(),
  stats: z.object({ added: z.number(), removed: z.number() }).optional(),
  fix_id: z.string().optional(),
});

export const FileRefBlockSchema = z.object({
  type: z.literal('file_ref'),
  id: z.string(),
  path: z.string(),
  line: z.number().optional(),
  endLine: z.number().optional(),
  label: z.string().optional(),
});

export const TreeNodeSchema: z.ZodType<any> = z.lazy(() =>
  z.object({
    name: z.string(),
    path: z.string(),
    type: z.enum(['file', 'dir']),
    children: z.array(TreeNodeSchema).optional(),
  })
);

export const FileTreeBlockSchema = z.object({
  type: z.literal('file_tree'),
  id: z.string(),
  root: z.string(),
  nodes: z.array(TreeNodeSchema),
});

export const LinkCardBlockSchema = z.object({
  type: z.literal('link_card'),
  id: z.string(),
  url: z.string().url(),
  title: z.string().optional(),
  description: z.string().optional(),
});

export const TimelineEventSchema = z.object({
  ts: z.string(),
  label: z.string(),
  severity: z.enum(['info', 'warn', 'danger', 'success']).optional(),
  detail: z.string().optional(),
});

export const TimelineBlockSchema = z.object({
  type: z.literal('timeline'),
  id: z.string(),
  events: z.array(TimelineEventSchema),
});

export const LogViewerBlockSchema = z.object({
  type: z.literal('log_viewer'),
  id: z.string(),
  data_ref: z.string(),
  filters: z.record(z.string(), z.unknown()).optional(),
});

export const RequestInspectorBlockSchema = z.object({
  type: z.literal('request_inspector'),
  id: z.string(),
  data_ref: z.string(),
});

export const JsonBlockSchema = z.object({
  type: z.literal('json'),
  id: z.string(),
  data_ref: z.string().optional(),
  value: z.unknown().optional(),
  collapsed: z.number().optional(),
});

export const CalloutBlockSchema = z.object({
  type: z.literal('callout'),
  id: z.string(),
  level: z.enum(['info', 'warn', 'danger', 'success']),
  title: z.string().optional(),
  text: z.string(),
});

export const StepItemSchema = z.object({
  label: z.string(),
  status: z.enum(['pending', 'running', 'done', 'failed', 'skipped']),
  detail: z.string().optional(),
});

export const StepsBlockSchema = z.object({
  type: z.literal('steps'),
  id: z.string(),
  items: z.array(StepItemSchema),
});

export const IncidentCardBlockSchema = z.object({
  type: z.literal('incident_card'),
  id: z.string(),
  incident_id: z.string(),
});

export const FixCardBlockSchema = z.object({
  type: z.literal('fix_card'),
  id: z.string(),
  fix_id: z.string(),
});

export const ReplayEvidenceBlockSchema = z.object({
  type: z.literal('replay_evidence'),
  id: z.string(),
  fix_id: z.string(),
});

export const CreditEstimateBlockSchema = z.object({
  type: z.literal('credit_estimate'),
  id: z.string(),
  credits: z.number(),
  detail: z.string().optional(),
  requires_confirm: z.boolean().optional(),
});

export const ActionItemSchema = z.object({
  action_id: AllowedActionSchema,
  label: z.string(),
  args: z.record(z.string(), z.unknown()).optional(),
  style: z.enum(['primary', 'secondary', 'danger']).optional(),
});

export const ActionsBlockSchema = z.object({
  type: z.literal('actions'),
  id: z.string(),
  items: z.array(ActionItemSchema),
});

export const ImageBlockSchema = z.object({
  type: z.literal('image'),
  id: z.string(),
  data_uri: z.string().optional(),
  artifact_id: z.string().optional(),
  alt: z.string(),
});

export const SourcesBlockSchema = z.object({
  type: z.literal('sources'),
  id: z.string(),
  items: z.array(z.object({ label: z.string(), ref: z.string() })),
});

export const PrStageStatusSchema = z.enum([
  'pending',
  'running',
  'passed',
  'failed',
  'clean',
  'conflict',
  'resolved',
]);
export type PrStageStatus = z.infer<typeof PrStageStatusSchema>;

export const PrTimelineStageSchema = z.object({
  key: z.string(),
  title: z.string(),
  status: PrStageStatusSchema,
  detail: z.string().optional(),
  icon: z.string().optional(),
});
export type PrTimelineStage = z.infer<typeof PrTimelineStageSchema>;

export const PrCardBlockSchema = z.object({
  type: z.literal('pr_card'),
  id: z.string(),
  pr_number: z.number(),
  pr_url: z.string(),
  title: z.string(),
  branch: z.string(),
  author: z.string().optional(),
  target_branch: z.string().optional(),
  stages: z.array(PrTimelineStageSchema),
  ci_status: z.object({
    state: z.string(),
    passed: z.number(),
    total: z.number(),
  }).optional(),
  merge_status: z.object({
    mergeable: z.boolean(),
    state: z.string(),
  }).optional(),
  review_status: z.object({
    comments_count: z.number(),
    actions_count: z.number(),
  }).optional(),
  actions: z.array(AllowedActionSchema).optional(),
});
export type PrCardBlock = z.infer<typeof PrCardBlockSchema>;

export const UnsupportedBlockSchema = z.object({
  type: z.literal('unsupported'),
  id: z.string(),
  raw: z.unknown(),
});

export const BlockSchema = z.discriminatedUnion('type', [
  MarkdownBlockSchema,
  CodeBlockSchema,
  TableBlockSchema,
  ChartBlockSchema,
  StatTilesBlockSchema,
  DiagramBlockSchema,
  DiffBlockSchema,
  FileRefBlockSchema,
  FileTreeBlockSchema,
  LinkCardBlockSchema,
  TimelineBlockSchema,
  LogViewerBlockSchema,
  RequestInspectorBlockSchema,
  JsonBlockSchema,
  CalloutBlockSchema,
  StepsBlockSchema,
  IncidentCardBlockSchema,
  FixCardBlockSchema,
  ReplayEvidenceBlockSchema,
  CreditEstimateBlockSchema,
  ActionsBlockSchema,
  ImageBlockSchema,
  SourcesBlockSchema,
  PrCardBlockSchema,
  UnsupportedBlockSchema,
]);

export type Block = z.infer<typeof BlockSchema>;

// ============================================================================
// MESSAGE & CONVERSATION SCHEMAS
// ============================================================================

export const MessageUsageSchema = z.object({
  credits: z.number().optional(),
  tokensIn: z.number().optional(),
  tokensOut: z.number().optional(),
  costEstimate: z.boolean().optional(),
});

export const MessageSchema = z.object({
  id: z.string(),
  role: z.enum(['user', 'assistant', 'system']),
  createdAt: z.string(),
  status: z.enum(['streaming', 'done', 'error', 'stopped']),
  blocks: z.array(BlockSchema),
  model: z.string().optional(),
  usage: MessageUsageSchema.optional(),
  parentId: z.string().optional(),
});
export type Message = z.infer<typeof MessageSchema>;

export const ConversationSchema = z.object({
  id: z.string(),
  title: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  messages: z.array(MessageSchema),
  model: z.string().optional(),
  pinned: z.boolean().optional(),
});
export type Conversation = z.infer<typeof ConversationSchema>;

// ============================================================================
// STREAMING PROTOCOL SCHEMAS
// ============================================================================

export const MessageStartEventSchema = z.object({
  event: z.literal('message.start'),
  messageId: z.string(),
  model: z.string().optional(),
});

export const BlockStartEventSchema = z.object({
  event: z.literal('block.start'),
  messageId: z.string(),
  block: BlockSchema,
});

export const BlockDeltaEventSchema = z.object({
  event: z.literal('block.delta'),
  messageId: z.string(),
  blockId: z.string(),
  op: z.enum(['append', 'replace', 'patch']),
  text: z.string().optional(),
  json: z.unknown().optional(),
});

export const BlockEndEventSchema = z.object({
  event: z.literal('block.end'),
  messageId: z.string(),
  blockId: z.string(),
});

export const ToolStartEventSchema = z.object({
  event: z.literal('tool.start'),
  id: z.string(),
  name: z.string(),
  argsPreview: z.string().optional(),
});

export const ToolProgressEventSchema = z.object({
  event: z.literal('tool.progress'),
  id: z.string(),
  pct: z.number().optional(),
  note: z.string().optional(),
});

export const ToolEndEventSchema = z.object({
  event: z.literal('tool.end'),
  id: z.string(),
  status: z.enum(['ok', 'error']),
  elapsedMs: z.number(),
  resultRef: z.string().optional(),
});

export const ActivityUpdateEventSchema = z.object({
  event: z.literal('activity.update'),
  steps: z.array(StepItemSchema),
});

export const LiveTickEventSchema = z.object({
  event: z.literal('live.tick'),
  blockId: z.string(),
  data_ref: z.string(),
  patch: z.unknown(),
});

export const UsageEventSchema = z.object({
  event: z.literal('usage'),
  credits: z.number().optional(),
  tokensIn: z.number().optional(),
  tokensOut: z.number().optional(),
});

export const MessageEndEventSchema = z.object({
  event: z.literal('message.end'),
  messageId: z.string(),
  status: z.enum(['done', 'error', 'stopped']),
});

export const ErrorEventSchema = z.object({
  event: z.literal('error'),
  code: z.string(),
  message: z.string(),
  requestId: z.string().optional(),
});

export const StreamingEventSchema = z.discriminatedUnion('event', [
  MessageStartEventSchema,
  BlockStartEventSchema,
  BlockDeltaEventSchema,
  BlockEndEventSchema,
  ToolStartEventSchema,
  ToolProgressEventSchema,
  ToolEndEventSchema,
  ActivityUpdateEventSchema,
  LiveTickEventSchema,
  UsageEventSchema,
  MessageEndEventSchema,
  ErrorEventSchema,
]);
export type StreamingEvent = z.infer<typeof StreamingEventSchema>;

// ============================================================================
// WEBVIEW <-> HOST PROTOCOL SCHEMAS
// ============================================================================

export const ContextChipSchema = z.object({
  type: z.enum(['file', 'selection', 'incident', 'service']),
  label: z.string(),
  value: z.string(),
});
export type ContextChip = z.infer<typeof ContextChipSchema>;

export const WebviewToHostMessageSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('ready') }),
  z.object({
    type: z.literal('sendMessage'),
    text: z.string(),
    model: z.string().optional(),
    mode: z.enum(['ask', 'agent']).optional(),
    conversationId: z.string().optional(),
    contextChips: z.array(ContextChipSchema).optional(),
  }),
  z.object({
    type: z.literal('stop'),
    conversationId: z.string().optional(),
    messageId: z.string().optional(),
  }),
  z.object({ type: z.literal('regenerate'), messageId: z.string() }),
  z.object({ type: z.literal('editMessage'), messageId: z.string(), text: z.string() }),
  z.object({ type: z.literal('selectModel'), model: z.string() }),
  z.object({ type: z.literal('setMode'), mode: z.enum(['ask', 'agent']) }),
  z.object({ type: z.literal('loadConversation'), conversationId: z.string() }),
  z.object({ type: z.literal('listConversations') }),
  z.object({ type: z.literal('renameConversation'), conversationId: z.string(), title: z.string() }),
  z.object({ type: z.literal('deleteConversation'), conversationId: z.string() }),
  z.object({
    type: z.literal('requestData'),
    data_ref: z.string(),
    range: z.string().optional(),
    page: z.number().optional(),
  }),
  z.object({ type: z.literal('subscribeLive'), data_ref: z.string() }),
  z.object({ type: z.literal('unsubscribeLive'), data_ref: z.string() }),
  z.object({
    type: z.literal('action'),
    action_id: AllowedActionSchema,
    args: z.record(z.string(), z.unknown()).optional(),
  }),
  z.object({
    type: z.literal('copy'),
    format: z.enum(['text', 'markdown', 'csv', 'json']),
    payload: z.string(),
  }),
  z.object({
    type: z.literal('export'),
    kind: z.enum(['csv', 'json', 'png', 'svg', 'md', 'html']),
    payload: z.string(),
    filename: z.string().optional(),
  }),
  z.object({ type: z.literal('openArtifact'), id: z.string() }),
  z.object({ type: z.literal('setContext'), chips: z.array(ContextChipSchema) }),
  z.object({
    type: z.literal('feedback'),
    messageId: z.string(),
    vote: z.enum(['up', 'down']),
    reason: z.string().optional(),
  }),
]);
export type WebviewToHostMessage = z.infer<typeof WebviewToHostMessageSchema>;

export const HostToWebviewMessageSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('init'),
    user: z.record(z.string(), z.unknown()).nullable(),
    token: z.string().nullable(),
    plan: z.string(),
    creditsRemaining: z.number().optional(),
    models: z.array(z.object({ id: z.string(), label: z.string(), costClass: z.string() })).optional(),
  }),
  z.object({ type: z.literal('conversation'), conversation: ConversationSchema }),
  z.object({ type: z.literal('streamEvent'), event: StreamingEventSchema }),
  z.object({
    type: z.literal('data'),
    data_ref: z.string(),
    data: z.unknown(),
    provenance: ProvenanceSchema.optional(),
  }),
  z.object({
    type: z.literal('liveTick'),
    blockId: z.string(),
    data_ref: z.string(),
    patch: z.unknown(),
  }),
  z.object({ type: z.literal('toast'), message: z.string(), level: z.enum(['info', 'warn', 'error']).optional() }),
  z.object({ type: z.literal('themeChanged'), theme: z.enum(['light', 'dark', 'high-contrast']) }),
  z.object({
    type: z.literal('error'),
    code: z.string(),
    message: z.string(),
    requestId: z.string().optional(),
  }),
]);
export type HostToWebviewMessage = z.infer<typeof HostToWebviewMessageSchema>;
