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
exports.FileService = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
class FileService {
    static resolveWorkspacePath(relativePath) {
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
    static async openFileAtLocation(filePath, line, col) {
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
        }
        catch (err) {
            vscode.window.showErrorMessage(`Error opening file: ${err?.message || err}`);
            return false;
        }
    }
    static async openNativeDiff(filePath, patch) {
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
            }
            else if (patch) {
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
        }
        catch (err) {
            vscode.window.showErrorMessage(`Failed to open native diff: ${err?.message || err}`);
            return false;
        }
    }
    static applyUnifiedPatch(original, patch) {
        const lines = original.split(/\r?\n/);
        const patchLines = patch.split(/\r?\n/);
        const hunkHeader = /@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/;
        let currentHunk = null;
        const hunks = [];
        for (const pLine of patchLines) {
            const m = pLine.match(hunkHeader);
            if (m) {
                if (currentHunk)
                    hunks.push(currentHunk);
                currentHunk = { origStart: parseInt(m[1], 10), lines: [] };
            }
            else if (currentHunk) {
                if (pLine.startsWith('+') || pLine.startsWith('-') || pLine.startsWith(' ')) {
                    currentHunk.lines.push(pLine);
                }
            }
        }
        if (currentHunk)
            hunks.push(currentHunk);
        if (hunks.length === 0) {
            return original + '\n' + patch;
        }
        const resultLines = [...lines];
        for (let i = hunks.length - 1; i >= 0; i--) {
            const hunk = hunks[i];
            const lineIdx = Math.max(0, hunk.origStart - 1);
            let deleteCount = 0;
            const insertLines = [];
            for (const hl of hunk.lines) {
                if (hl.startsWith('+')) {
                    insertLines.push(hl.substring(1));
                }
                else if (hl.startsWith('-')) {
                    deleteCount++;
                }
                else if (hl.startsWith(' ')) {
                    insertLines.push(hl.substring(1));
                    deleteCount++;
                }
            }
            resultLines.splice(lineIdx, deleteCount, ...insertLines);
        }
        return resultLines.join('\n');
    }
    static async revealInExplorer(filePath) {
        try {
            const uri = this.resolveWorkspacePath(filePath);
            if (!uri || !fs.existsSync(uri.fsPath)) {
                return false;
            }
            await vscode.commands.executeCommand('revealInExplorer', uri);
            return true;
        }
        catch (err) {
            return false;
        }
    }
    static async insertAtCursor(text) {
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
exports.FileService = FileService;
//# sourceMappingURL=fileService.js.map