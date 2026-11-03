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
exports.ActionRouter = void 0;
const vscode = __importStar(require("vscode"));
const chat_js_1 = require("../shared/chat.js");
const fileService_js_1 = require("./fileService.js");
const clipboardService_js_1 = require("./clipboardService.js");
const linkService_js_1 = require("./linkService.js");
class ActionRouter {
    ctx;
    constructor(ctx) {
        this.ctx = ctx;
    }
    async execute(actionId, args) {
        const validated = chat_js_1.AllowedActionSchema.safeParse(actionId);
        if (!validated.success) {
            vscode.window.showErrorMessage(`[Skelion Security] Blocked unallowed action: "${actionId}"`);
            return false;
        }
        switch (actionId) {
            case 'open_file': {
                const filePath = typeof args?.path === 'string' ? args.path : '';
                const line = typeof args?.line === 'number' ? args.line : undefined;
                const col = typeof args?.col === 'number' ? args.col : undefined;
                if (!filePath)
                    return false;
                return fileService_js_1.FileService.openFileAtLocation(filePath, line, col);
            }
            case 'reveal_file': {
                const filePath = typeof args?.path === 'string' ? args.path : '';
                if (!filePath)
                    return false;
                return fileService_js_1.FileService.revealInExplorer(filePath);
            }
            case 'copy': {
                const payload = typeof args?.payload === 'string' ? args.payload : '';
                const format = args?.format || 'text';
                if (!payload)
                    return false;
                return clipboardService_js_1.ClipboardService.copyText(payload, format);
            }
            case 'open_url': {
                const url = typeof args?.url === 'string' ? args.url : '';
                if (!url)
                    return false;
                return linkService_js_1.LinkService.openLink(url, this.ctx.extensionContext);
            }
            case 'approve_fix': {
                const fixId = typeof args?.fix_id === 'string' ? args.fix_id : 'default';
                if (this.ctx.triggerAutofixPr) {
                    await this.ctx.triggerAutofixPr(args || { fix_id: fixId });
                }
                else {
                    vscode.window.showInformationMessage(`Skelion: Approving fix [${fixId}] and generating GitHub PR...`);
                }
                return true;
            }
            case 'trigger_pr_cycle': {
                const prNumber = typeof args?.pr_number === 'number' ? args.pr_number : 190;
                if (this.ctx.triggerPrCycle) {
                    await this.ctx.triggerPrCycle(prNumber);
                }
                else {
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
                if (!filePath)
                    return false;
                return fileService_js_1.FileService.openNativeDiff(filePath, patch);
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
exports.ActionRouter = ActionRouter;
//# sourceMappingURL=actionRouter.js.map