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
exports.LinkService = void 0;
const vscode = __importStar(require("vscode"));
class LinkService {
    static confirmedDomains = new Set();
    static async openLink(url, context) {
        try {
            const parsed = new URL(url);
            const scheme = parsed.protocol.replace(':', '').toLowerCase();
            // Enforce scheme allow-list
            if (scheme === 'javascript' || scheme === 'data') {
                vscode.window.showErrorMessage(`[Skelion Security] Blocked dangerous URL scheme: ${scheme}:`);
                return false;
            }
            if (scheme === 'skelion') {
                // Internal extension navigation: skelion://incident/<id>, skelion://fix/<id>
                return this.handleInternalLink(parsed);
            }
            if (scheme !== 'http' && scheme !== 'https' && scheme !== 'mailto') {
                vscode.window.showErrorMessage(`[Skelion Security] Unsupported URL protocol: ${scheme}`);
                return false;
            }
            const domain = parsed.hostname;
            if (!this.confirmedDomains.has(domain)) {
                const choice = await vscode.window.showInformationMessage(`Skelion: Do you want to open this external link in your browser?\n\n${domain}`, { modal: false }, 'Open Link', 'Always Allow Domain');
                if (!choice) {
                    return false;
                }
                if (choice === 'Always Allow Domain') {
                    this.confirmedDomains.add(domain);
                }
            }
            await vscode.env.openExternal(vscode.Uri.parse(url));
            return true;
        }
        catch (err) {
            vscode.window.showErrorMessage(`Failed to open link: ${err?.message || err}`);
            return false;
        }
    }
    static handleInternalLink(url) {
        const route = url.hostname || url.pathname.replace(/^\/\//, '');
        vscode.window.showInformationMessage(`[Skelion Nav] Internal route: ${route}`);
        return true;
    }
}
exports.LinkService = LinkService;
//# sourceMappingURL=linkService.js.map