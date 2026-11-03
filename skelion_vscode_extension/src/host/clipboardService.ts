import * as vscode from 'vscode';

export class ClipboardService {
  public static async copyText(text: string, format: 'text' | 'markdown' | 'csv' | 'json' = 'text'): Promise<boolean> {
    try {
      await vscode.env.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.error('[ClipboardService] Failed to copy to clipboard:', err);
      return false;
    }
  }

  public static formatTableAsCsv(columns: { key: string; label: string }[], rows: Record<string, unknown>[]): string {
    const headers = columns.map(c => `"${c.label.replace(/"/g, '""')}"`).join(',');
    const dataLines = rows.map(r => {
      return columns.map(c => {
        const val = r[c.key] !== undefined && r[c.key] !== null ? String(r[c.key]) : '';
        return `"${val.replace(/"/g, '""')}"`;
      }).join(',');
    });
    return [headers, ...dataLines].join('\n');
  }

  public static formatTableAsMarkdown(columns: { key: string; label: string }[], rows: Record<string, unknown>[]): string {
    const headerLine = '| ' + columns.map(c => c.label).join(' | ') + ' |';
    const separatorLine = '| ' + columns.map(() => '---').join(' | ') + ' |';
    const dataLines = rows.map(r => {
      return '| ' + columns.map(c => {
        const val = r[c.key] !== undefined && r[c.key] !== null ? String(r[c.key]) : '';
        return val.replace(/\|/g, '\\|');
      }).join(' | ') + ' |';
    });
    return [headerLine, separatorLine, ...dataLines].join('\n');
  }
}
