import * as vscode from 'vscode';
import { AllowedAction, AllowedActionSchema } from '../shared/chat.js';
import { FileService } from './fileService.js';
import { ClipboardService } from './clipboardService.js';
import { LinkService } from './linkService.js';

export interface ActionContext {
  extensionContext: vscode.ExtensionContext;
  apiBase: string;
  getToken: () => Promise<string | null>;
  openEditorTab?: (title: string, contentHtml: string) => void;
  triggerAutofixPr?: (args: Record<string, unknown>) => Promise<void>;
  triggerPrCycle?: (prNumber: number) => Promise<void>;
}

export class ActionRouter {
  constructor(private readonly ctx: ActionContext) {}

  public async execute(actionId: AllowedAction, args?: Record<string, unknown>): Promise<boolean> {
    const validated = AllowedActionSchema.safeParse(actionId);
    if (!validated.success) {
      vscode.window.showErrorMessage(`[Skelion Security] Blocked unallowed action: "${actionId}"`);
      return false;
    }

    switch (actionId) {
      case 'open_file': {
        const filePath = typeof args?.path === 'string' ? args.path : '';
        const line = typeof args?.line === 'number' ? args.line : undefined;
        const col = typeof args?.col === 'number' ? args.col : undefined;
        if (!filePath) return false;
        return FileService.openFileAtLocation(filePath, line, col);
      }

      case 'reveal_file': {
        const filePath = typeof args?.path === 'string' ? args.path : '';
        if (!filePath) return false;
        return FileService.revealInExplorer(filePath);
      }

      case 'copy': {
        const payload = typeof args?.payload === 'string' ? args.payload : '';
        const format = (args?.format as any) || 'text';
        if (!payload) return false;
        return ClipboardService.copyText(payload, format);
      }

      case 'open_url': {
        const url = typeof args?.url === 'string' ? args.url : '';
        if (!url) return false;
        return LinkService.openLink(url, this.ctx.extensionContext);
      }

      case 'approve_fix': {
        const fixId = typeof args?.fix_id === 'string' ? args.fix_id : 'default';
        if (this.ctx.triggerAutofixPr) {
          await this.ctx.triggerAutofixPr(args || { fix_id: fixId });
        } else {
          vscode.window.showInformationMessage(`Skelion: Approving fix [${fixId}] and generating GitHub PR...`);
        }
        return true;
      }

      case 'trigger_pr_cycle': {
        const prNumber = typeof args?.pr_number === 'number' ? args.pr_number : 190;
        if (this.ctx.triggerPrCycle) {
          await this.ctx.triggerPrCycle(prNumber);
        } else {
          vscode.window.showInformationMessage(`Skelion: Triggering autonomous PR cycle for PR #${prNumber}...`);
        }
        return true;
      }

      case 'reject_fix': {
        const fixId = typeof args?.fix_id === 'string' ? args.fix_id : 'default';
        vscode.window.showInformationMessage(`Skelion: Rejected fix proposal [${fixId}].`);
        return true;
      }

      case 'revert_fix': {
        const fixId = typeof args?.fix_id === 'string' ? args.fix_id : 'default';
        vscode.window.showWarningMessage(`Skelion: Reverting patch [${fixId}].`);
        return true;
      }

      case 'run_replay': {
        const fixId = typeof args?.fix_id === 'string' ? args.fix_id : 'default';
        vscode.window.showInformationMessage(`Skelion: Initiating sandbox replay verification for [${fixId}]...`);
        return true;
      }

      case 'open_incident': {
        const incId = typeof args?.id === 'string' ? args.id : '190';
        vscode.window.showInformationMessage(`Skelion: Inspecting incident #${incId} telemetry and root cause.`);
        return true;
      }

      case 'open_in_editor': {
        const title = typeof args?.title === 'string' ? args.title : 'Skelion Wide View';
        const content = typeof args?.content === 'string' ? args.content : '';
        if (this.ctx.openEditorTab) {
          this.ctx.openEditorTab(title, content);
        }
        return true;
      }

      case 'open_native_diff': {
        const filePath = typeof args?.path === 'string' ? args.path : (typeof args?.filename === 'string' ? args.filename : '');
        const patch = typeof args?.patch === 'string' ? args.patch : '';
        if (!filePath) return false;
        return FileService.openNativeDiff(filePath, patch);
      }

      case 'confirm_credit_estimate': {
        const credits = typeof args?.credits === 'number' ? args.credits : 42;
        vscode.window.showInformationMessage(`Skelion: Confirmed execution of task (${credits} credits).`);
        return true;
      }

      case 'upgrade':
      case 'buy_credits': {
        vscode.window.showInformationMessage('Skelion: Opening pricing & subscription top-up.');
        return true;
      }

      default:
        return false;
    }
  }
}
