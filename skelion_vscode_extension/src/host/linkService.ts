import * as vscode from 'vscode';

export class LinkService {
  private static confirmedDomains = new Set<string>();

  public static async openLink(url: string, context?: vscode.ExtensionContext): Promise<boolean> {
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
        const choice = await vscode.window.showInformationMessage(
          `Skelion: Do you want to open this external link in your browser?\n\n${domain}`,
          { modal: false },
          'Open Link',
          'Always Allow Domain'
        );

        if (!choice) {
          return false;
        }

        if (choice === 'Always Allow Domain') {
          this.confirmedDomains.add(domain);
        }
      }

      await vscode.env.openExternal(vscode.Uri.parse(url));
      return true;
    } catch (err: any) {
      vscode.window.showErrorMessage(`Failed to open link: ${err?.message || err}`);
      return false;
    }
  }

  private static handleInternalLink(url: URL): boolean {
    const route = url.hostname || url.pathname.replace(/^\/\//, '');
    vscode.window.showInformationMessage(`[Skelion Nav] Internal route: ${route}`);
    return true;
  }
}
