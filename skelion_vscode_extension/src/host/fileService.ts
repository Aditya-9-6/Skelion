import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

export class FileService {
  public static resolveWorkspacePath(relativePath: string): vscode.Uri | null {
    const cleanPath = relativePath.replace(/^[/\\]+/, '');
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
      return null;
    }

    for (const folder of workspaceFolders) {
      const fullPath = path.join(folder.uri.fsPath, cleanPath);
      if (fs.existsSync(fullPath)) {
        return vscode.Uri.file(fullPath);
      }
    }

    // Default to first workspace folder even if file is new
    return vscode.Uri.file(path.join(workspaceFolders[0].uri.fsPath, cleanPath));
  }

  public static async openFileAtLocation(filePath: string, line?: number, col?: number): Promise<boolean> {
    try {
      const uri = this.resolveWorkspacePath(filePath);
      if (!uri) {
        vscode.window.showWarningMessage(`Could not resolve workspace path for "${filePath}".`);
        return false;
      }

      if (!fs.existsSync(uri.fsPath)) {
        vscode.window.showWarningMessage(`File not found: ${filePath}`);
        return false;
      }

      const doc = await vscode.workspace.openTextDocument(uri);
      const editor = await vscode.window.showTextDocument(doc, { preview: true });

      if (line !== undefined && line > 0) {
        const targetLine = Math.max(0, line - 1);
        const targetCol = Math.max(0, (col || 1) - 1);
        const pos = new vscode.Position(targetLine, targetCol);
        editor.selection = new vscode.Selection(pos, pos);
        editor.revealRange(new vscode.Range(pos, pos), vscode.TextEditorRevealType.InCenter);
      }

      return true;
    } catch (err: any) {
      vscode.window.showErrorMessage(`Error opening file: ${err?.message || err}`);
      return false;
    }
  }

  public static async openNativeDiff(filePath: string, patch: string): Promise<boolean> {
    try {
      const uri = this.resolveWorkspacePath(filePath);
      let originalContent = '';
      if (uri && fs.existsSync(uri.fsPath)) {
        originalContent = fs.readFileSync(uri.fsPath, 'utf-8');
      }

      // Generate patched representation
      let patchedContent = originalContent;
      if (patch && originalContent) {
        patchedContent = this.applyUnifiedPatch(originalContent, patch);
      } else if (patch) {
        patchedContent = patch;
      }

      const tempDir = path.join(os.tmpdir(), 'skelion-diffs');
      if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir, { recursive: true });
      }

      const baseName = path.basename(filePath || 'patch.diff');
      const leftPath = path.join(tempDir, `original_${baseName}`);
      const rightPath = path.join(tempDir, `proposed_${baseName}`);

      fs.writeFileSync(leftPath, originalContent, 'utf-8');
      fs.writeFileSync(rightPath, patchedContent, 'utf-8');

      const leftUri = vscode.Uri.file(leftPath);
      const rightUri = vscode.Uri.file(rightPath);
      const title = `${baseName} (Working Tree ⟷ Skelion Replay Patch)`;

      await vscode.commands.executeCommand('vscode.diff', leftUri, rightUri, title);
      return true;
    } catch (err: any) {
      vscode.window.showErrorMessage(`Failed to open native diff: ${err?.message || err}`);
      return false;
    }
  }

  private static applyUnifiedPatch(original: string, patch: string): string {
    const lines = original.split(/\r?\n/);
    const patchLines = patch.split(/\r?\n/);

    const hunkHeader = /@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/;
    let currentHunk: { origStart: number; lines: string[] } | null = null;
    const hunks: Array<{ origStart: number; lines: string[] }> = [];

    for (const pLine of patchLines) {
      const m = pLine.match(hunkHeader);
      if (m) {
        if (currentHunk) hunks.push(currentHunk);
        currentHunk = { origStart: parseInt(m[1], 10), lines: [] };
      } else if (currentHunk) {
        if (pLine.startsWith('+') || pLine.startsWith('-') || pLine.startsWith(' ')) {
          currentHunk.lines.push(pLine);
        }
      }
    }
    if (currentHunk) hunks.push(currentHunk);

    if (hunks.length === 0) {
      return original + '\n' + patch;
    }

    const resultLines = [...lines];
    for (let i = hunks.length - 1; i >= 0; i--) {
      const hunk = hunks[i];
      const lineIdx = Math.max(0, hunk.origStart - 1);
      let deleteCount = 0;
      const insertLines: string[] = [];

      for (const hl of hunk.lines) {
        if (hl.startsWith('+')) {
          insertLines.push(hl.substring(1));
        } else if (hl.startsWith('-')) {
          deleteCount++;
        } else if (hl.startsWith(' ')) {
          insertLines.push(hl.substring(1));
          deleteCount++;
        }
      }
      resultLines.splice(lineIdx, deleteCount, ...insertLines);
    }

    return resultLines.join('\n');
  }

  public static async revealInExplorer(filePath: string): Promise<boolean> {
    try {
      const uri = this.resolveWorkspacePath(filePath);
      if (!uri || !fs.existsSync(uri.fsPath)) {
        return false;
      }
      await vscode.commands.executeCommand('revealInExplorer', uri);
      return true;
    } catch (err) {
      return false;
    }
  }

  public static async insertAtCursor(text: string): Promise<boolean> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage('No active editor to insert code into.');
      return false;
    }

    return editor.edit(editBuilder => {
      editBuilder.insert(editor.selection.active, text);
    });
  }
}
