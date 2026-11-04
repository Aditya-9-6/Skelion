import { z } from 'zod';
import {
  Block,
  BlockSchema,
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
} from './chat.js';

export interface BlockDefinition<T extends Block = Block> {
  type: T['type'];
  label: string;
  schema: z.ZodType<T>;
  isLazy?: boolean;
  supportedExports?: ('csv' | 'json' | 'markdown' | 'png' | 'svg')[];
  allowsWideView?: boolean;
}

export class BlockRegistry {
  private static definitions = new Map<string, BlockDefinition>();

  public static register<T extends Block>(def: BlockDefinition<T>): void {
    this.definitions.set(def.type, def as BlockDefinition);
  }

  public static get(type: string): BlockDefinition | undefined {
    return this.definitions.get(type);
  }

  public static has(type: string): boolean {
    return this.definitions.has(type);
  }

  public static validate(rawBlock: unknown): { success: true; data: Block } | { success: false; fallback: Block; error: string } {
    const parseResult = BlockSchema.safeParse(rawBlock);
    if (parseResult.success) {
      return { success: true, data: parseResult.data };
    }

    const fallbackId = (rawBlock && typeof rawBlock === 'object' && 'id' in rawBlock && typeof (rawBlock as any).id === 'string')
      ? (rawBlock as any).id
      : `unsupported_${Date.now()}`;

    const fallback: Block = {
      type: 'unsupported',
      id: fallbackId,
      raw: rawBlock,
    };

    return {
      success: false,
      fallback,
      error: (parseResult as any).error?.message || 'Validation error',
    };
  }

  public static listTypes(): string[] {
    return Array.from(this.definitions.keys());
  }
}

// Initialize all block definitions
BlockRegistry.register({ type: 'markdown', label: 'Markdown', schema: MarkdownBlockSchema as any, supportedExports: ['markdown'] });
BlockRegistry.register({ type: 'code', label: 'Code Snippet', schema: CodeBlockSchema as any, supportedExports: ['markdown', 'json'] });
BlockRegistry.register({ type: 'table', label: 'Data Table', schema: TableBlockSchema as any, supportedExports: ['csv', 'json', 'markdown'], allowsWideView: true });
BlockRegistry.register({ type: 'chart', label: 'Metric Chart', schema: ChartBlockSchema as any, isLazy: true, supportedExports: ['png', 'svg', 'csv', 'json'], allowsWideView: true });
BlockRegistry.register({ type: 'stat_tiles', label: 'Stat Tiles', schema: StatTilesBlockSchema as any, supportedExports: ['json'] });
BlockRegistry.register({ type: 'diagram', label: 'Architecture Diagram', schema: DiagramBlockSchema as any, isLazy: true, supportedExports: ['svg', 'png', 'markdown'], allowsWideView: true });
BlockRegistry.register({ type: 'diff', label: 'Code Diff', schema: DiffBlockSchema as any, supportedExports: ['markdown'], allowsWideView: true });
BlockRegistry.register({ type: 'file_ref', label: 'File Reference', schema: FileRefBlockSchema as any });
BlockRegistry.register({ type: 'file_tree', label: 'File Tree', schema: FileTreeBlockSchema as any });
BlockRegistry.register({ type: 'link_card', label: 'Link Card', schema: LinkCardBlockSchema as any });
BlockRegistry.register({ type: 'timeline', label: 'Event Timeline', schema: TimelineBlockSchema as any, supportedExports: ['json'] });
BlockRegistry.register({ type: 'log_viewer', label: 'Log Stream', schema: LogViewerBlockSchema as any, isLazy: true, supportedExports: ['csv', 'json'], allowsWideView: true });
BlockRegistry.register({ type: 'request_inspector', label: 'Request Inspector', schema: RequestInspectorBlockSchema as any, allowsWideView: true });
BlockRegistry.register({ type: 'json', label: 'JSON Data', schema: JsonBlockSchema as any, supportedExports: ['json'] });
BlockRegistry.register({ type: 'callout', label: 'Callout Alert', schema: CalloutBlockSchema as any });
BlockRegistry.register({ type: 'steps', label: 'Plan Steps', schema: StepsBlockSchema as any });
BlockRegistry.register({ type: 'incident_card', label: 'Incident Card', schema: IncidentCardBlockSchema as any, allowsWideView: true });
BlockRegistry.register({ type: 'fix_card', label: 'Fix Proposal & Replay Card', schema: FixCardBlockSchema as any, allowsWideView: true });
BlockRegistry.register({ type: 'replay_evidence', label: 'Replay Evidence', schema: ReplayEvidenceBlockSchema as any, allowsWideView: true });
BlockRegistry.register({ type: 'credit_estimate', label: 'Credit Estimate', schema: CreditEstimateBlockSchema as any });
BlockRegistry.register({ type: 'actions', label: 'Action Bar', schema: ActionsBlockSchema as any });
BlockRegistry.register({ type: 'image', label: 'Image', schema: ImageBlockSchema as any });
BlockRegistry.register({ type: 'sources', label: 'Sources & Provenance', schema: SourcesBlockSchema as any });
BlockRegistry.register({ type: 'pr_card', label: 'Autonomous PR Card', schema: PrCardBlockSchema as any, allowsWideView: true, supportedExports: ['json', 'markdown'] });
BlockRegistry.register({ type: 'unsupported', label: 'Unsupported Block', schema: UnsupportedBlockSchema as any });
