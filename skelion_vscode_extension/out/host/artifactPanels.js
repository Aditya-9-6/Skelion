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
exports.ArtifactPanels = void 0;
const vscode = __importStar(require("vscode"));
class ArtifactPanels {
    static panels = new Map();
    static openWideView(extensionUri, title, bodyHtml, panelId = `artifact_${Date.now()}`) {
        let panel = this.panels.get(panelId);
        if (panel) {
            panel.reveal(vscode.ViewColumn.Active);
            return panel;
        }
        panel = vscode.window.createWebviewPanel('skelionArtifactWide', `Skelion: ${title}`, vscode.ViewColumn.Active, {
            enableScripts: true,
            localResourceRoots: [extensionUri],
            retainContextWhenHidden: true,
        });
        panel.webview.html = this.getHtmlForWideView(title, bodyHtml);
        panel.onDidDispose(() => {
            this.panels.delete(panelId);
        });
        this.panels.set(panelId, panel);
        return panel;
    }
    static getHtmlForWideView(title, bodyHtml) {
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
exports.ArtifactPanels = ArtifactPanels;
function escapeHtml(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
//# sourceMappingURL=artifactPanels.js.map