import { Conversation, Message, Block } from './chat.js';

export interface ExtractedArtifact {
  id: string;
  type: string;
  title: string;
  block: Block;
  createdAt?: string;
}

export function exportConversationAsMarkdown(conv: Conversation): string {
  const lines: string[] = [];
  lines.push(`# ${conv.title || 'Skelion Conversation'}`);
  lines.push(`_Created: ${conv.createdAt} · Model: ${conv.model || 'default'}_\n`);

  for (const msg of conv.messages) {
    const roleName = msg.role === 'user' ? 'User' : 'Skelion Agent';
    lines.push(`## ${roleName} (${new Date(msg.createdAt).toLocaleTimeString()})\n`);

    for (const block of msg.blocks) {
      switch (block.type) {
        case 'markdown':
          lines.push(block.text);
          break;

        case 'code':
          lines.push(`\`\`\`${block.lang || ''}${block.filename ? `:${block.filename}` : ''}\n${block.text}\n\`\`\``);
          break;

        case 'diff':
          lines.push(`\`\`\`diff\n# File: ${block.filename}\n${block.patch}\n\`\`\``);
          break;

        case 'table': {
          lines.push(`### ${block.title || 'Data Table'}`);
          const cols = block.columns || [];
          lines.push(`| ${cols.map(c => c.label).join(' | ')} |`);
          lines.push(`| ${cols.map(() => '---').join(' | ')} |`);
          for (const row of block.rows || []) {
            lines.push(`| ${cols.map(c => row[c.key] !== undefined ? String(row[c.key]) : '').join(' | ')} |`);
          }
          if (block.provenance) {
            lines.push(`\n_Source: ${block.provenance.source} · Query: ${block.provenance.query_id}_\n`);
          }
          break;
        }

        case 'chart':
          lines.push(`### 📈 Chart: ${block.title || 'Metric Chart'}`);
          lines.push(`_Kind: ${block.kind} · Data Query: ${block.data_ref || 'n/a'}_\n`);
          break;

        case 'stat_tiles':
          lines.push('### Key Metrics');
          for (const t of block.tiles) {
            lines.push(`- **${t.label}:** ${t.value}${t.unit || ''}${t.delta ? ` (${t.delta})` : ''}`);
          }
          break;

        case 'incident_card':
          lines.push(`### 🚨 Incident #${block.incident_id}`);
          break;

        case 'fix_card':
          lines.push(`### 🛡️ Verified Fix [${block.fix_id}]`);
          break;

        case 'pr_card':
          lines.push(`### 🟢 Autonomous PR #${block.pr_number}: ${block.title}`);
          lines.push(`- **URL:** [GitHub PR #${block.pr_number}](${block.pr_url})`);
          lines.push(`- **Branch:** \`${block.target_branch || 'main'}\` ⟵ \`${block.branch}\` (Author: @${block.author || 'Aditya-9-6'})`);
          lines.push(`- **Zero Local Mutations:** Remote fix committed strictly via GitHub API.`);
          lines.push(`- **Lifecycle Stages:**`);
          for (const s of block.stages) {
            lines.push(`  - [x] **${s.title}** (${s.status}): ${s.detail || ''}`);
          }
          break;

        case 'callout':
          lines.push(`> [!${(block.level || 'NOTE').toUpperCase()}] ${block.title || ''}\n> ${block.text}`);
          break;

        case 'diagram':
          lines.push(`### 📐 Architecture Diagram\n\`\`\`mermaid\n${block.text}\n\`\`\``);
          break;

        case 'timeline':
          lines.push(`### ⏱️ Incident Timeline`);
          for (const ev of block.events) {
            lines.push(`- **${ev.ts}** [${ev.severity || 'info'}] ${ev.label}${ev.detail ? `: ${ev.detail}` : ''}`);
          }
          break;

        case 'log_viewer':
          lines.push(`### 📜 Incident Logs\n_Data Query: ${block.data_ref}_`);
          break;

        case 'request_inspector':
          lines.push(`### 🔍 HTTP Trace Inspector\n_Data Query: ${block.data_ref}_`);
          break;

        case 'json':
          lines.push(`### {} Telemetry JSON Payload\n\`\`\`json\n${JSON.stringify(block.value || {}, null, 2)}\n\`\`\``);
          break;

        default:
          break;
      }
      lines.push(''); // blank line between blocks
    }
    lines.push('---\n');
  }

  return lines.join('\n');
}

export function exportConversationAsJson(conv: Conversation): string {
  return JSON.stringify(conv, null, 2);
}

export function extractArtifactsFromConversation(conv: Conversation): ExtractedArtifact[] {
  const artifacts: ExtractedArtifact[] = [];

  for (const msg of conv.messages) {
    for (const block of msg.blocks) {
      if (block.type === 'chart') {
        artifacts.push({
          id: block.id,
          type: 'chart',
          title: block.title || 'Metric Chart',
          block,
          createdAt: msg.createdAt,
        });
      } else if (block.type === 'table') {
        artifacts.push({
          id: block.id,
          type: 'table',
          title: block.title || 'Data Table',
          block,
          createdAt: msg.createdAt,
        });
      } else if (block.type === 'diff') {
        artifacts.push({
          id: block.id,
          type: 'diff',
          title: block.filename,
          block,
          createdAt: msg.createdAt,
        });
      } else if (block.type === 'incident_card') {
        artifacts.push({
          id: block.id,
          type: 'incident',
          title: `Incident #${block.incident_id}`,
          block,
          createdAt: msg.createdAt,
        });
      } else if (block.type === 'fix_card') {
        artifacts.push({
          id: block.id,
          type: 'fix',
          title: `Fix [${block.fix_id}]`,
          block,
          createdAt: msg.createdAt,
        });
      } else if (block.type === 'diagram') {
        artifacts.push({
          id: block.id,
          type: 'diagram',
          title: 'Architecture Diagram',
          block,
          createdAt: msg.createdAt,
        });
      } else if (block.type === 'log_viewer') {
        artifacts.push({
          id: block.id,
          type: 'logs',
          title: 'Incident Error Logs',
          block,
          createdAt: msg.createdAt,
        });
      } else if (block.type === 'request_inspector') {
        artifacts.push({
          id: block.id,
          type: 'request',
          title: 'HTTP 429 Trace Inspector',
          block,
          createdAt: msg.createdAt,
        });
      } else if (block.type === 'pr_card') {
        artifacts.push({
          id: block.id,
          type: 'pr' as any,
          title: `PR #${block.pr_number}: ${block.title}`,
          block,
          createdAt: msg.createdAt,
        });
      }
    }
  }

  return artifacts;
}

export function parseSlashCommand(input: string): { command: string; args: string } | null {
  const trimmed = input.trim();
  if (!trimmed.startsWith('/')) return null;
  const match = trimmed.match(/^\/([a-zA-Z0-9_-]+)(?:\s+(.*))?$/);
  if (!match) return null;
  return {
    command: match[1].toLowerCase(),
    args: match[2]?.trim() || '',
  };
}

export function parseMentions(input: string): string[] {
  const matches = input.match(/@([a-zA-Z0-9_\-\.\/:]+)/g);
  if (!matches) return [];
  return Array.from(new Set(matches.map(m => m.substring(1))));
}
