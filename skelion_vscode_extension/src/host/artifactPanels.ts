import * as vscode from 'vscode';

export class ArtifactPanels {
  private static panels = new Map<string, vscode.WebviewPanel>();

  public static openWideView(
    extensionUri: vscode.Uri,
    title: string,
    bodyHtml: string,
    panelId: string = `artifact_${Date.now()}`
  ): vscode.WebviewPanel {
    let panel = this.panels.get(panelId);

    if (panel) {
      panel.reveal(vscode.ViewColumn.Active);
      return panel;
    }

    panel = vscode.window.createWebviewPanel(
      'skelionArtifactWide',
      `Skelion: ${title}`,
      vscode.ViewColumn.Active,
      {
        enableScripts: true,
        localResourceRoots: [extensionUri],
        retainContextWhenHidden: true,
      }
    );

    panel.webview.html = this.getHtmlForWideView(title, bodyHtml);

    panel.onDidDispose(() => {
      this.panels.delete(panelId);
    });

    this.panels.set(panelId, panel);
    return panel;
  }

  private static getHtmlForWideView(title: string, bodyHtml: string): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)}</title>
  <style>
    :root {
      --bg: var(--vscode-editor-background, #0d1117);
      --fg: var(--vscode-editor-foreground, #c9d1d9);
      --border: var(--vscode-editorWidget-border, rgba(212, 175, 55, 0.3));
      --accent: #d4af37;
    }
    html, body {
      background: var(--bg);
      color: var(--fg);
      font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, sans-serif);
      margin: 0;
      padding: 16px 24px;
      line-height: 1.5;
    }
    .wide-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 12px;
      margin-bottom: 16px;
    }
    .wide-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--accent);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .wide-btn {
      background: rgba(255, 255, 255, 0.08);
      color: var(--fg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 4px 10px;
      font-size: 11px;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.15s ease;
    }
    .wide-btn:hover {
      background: rgba(212, 175, 55, 0.2);
      border-color: #f6e27a;
    }
    .wide-body {
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }
    th, td {
      padding: 8px 12px;
      border: 1px solid var(--border);
      text-align: left;
    }
    th {
      background: rgba(212, 175, 55, 0.15);
      color: #f6e27a;
    }
    pre {
      background: rgba(0, 0, 0, 0.3);
      padding: 12px;
      border-radius: 6px;
      overflow-x: auto;
    }
  </style>
</head>
<body>
  <div class="wide-header">
    <div class="wide-title">📊 ${escapeHtml(title)}</div>
    <div style="display:flex; gap:6px; align-items:center;">
      <button class="wide-btn" onclick="navigator.clipboard.writeText(document.querySelector('.wide-body').innerText); alert('Copied content to clipboard!');">📋 Copy Content</button>
      <div style="font-size: 11px; color: var(--vscode-descriptionForeground, #888); margin-left:8px;">Skelion Wide View Artifact</div>
    </div>
  </div>
  <div class="wide-body">
    ${bodyHtml}
  </div>
</body>
</html>`;
  }
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
