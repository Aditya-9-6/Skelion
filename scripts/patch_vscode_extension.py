import os

ext_path = r'g:\My Drive\helios\skelion_vscode_extension\src\extension.ts'
with open(ext_path, 'r', encoding='utf-8') as f:
    ts = f.read()

# 1. Update formatMarkdown
old_format = '''    function formatMarkdown(raw) {
      if (!raw) return '';
      let s = escapeHtml(raw);
      const b3 = String.fromCharCode(96) + String.fromCharCode(96) + String.fromCharCode(96);
      const b1 = String.fromCharCode(96);
      const codeBlockRe = new RegExp(b3 + '([a-zA-Z0-9_-]*)[\\r\\n]+([\\s\\S]*?)' + b3, 'g');
      s = s.replace(codeBlockRe, function(_, lang, code) {
        return '<pre style="background:rgba(0,0,0,0.35); padding:8px; border-radius:4px; font-size:11px; overflow-x:auto; margin:6px 0; border:1px solid rgba(255,255,255,0.06); font-family:monospace;"><code>' + code + '</code></pre>';
      });
      const inlineCodeRe = new RegExp(b1 + '([^' + b1 + '\\r\\n]+)' + b1, 'g');
      s = s.replace(inlineCodeRe, '<code style="background:rgba(255,255,255,0.1); padding:1px 4px; border-radius:3px; font-size:11px; font-family:monospace;">$1</code>');
      s = s.replace(/^### (.*$)/gim, '<div style="font-weight:bold; font-size:12px; color:#a78bfa; margin:6px 0 2px;">$1</div>');
      s = s.replace(/^## (.*$)/gim, '<div style="font-weight:bold; font-size:12.5px; color:#fff; margin:8px 0 3px;">$1</div>');
      s = s.replace(/^# (.*$)/gim, '<div style="font-weight:bold; font-size:13px; color:#fff; margin:10px 0 4px;">$1</div>');
      s = s.replace(/\\*\\*([^\\*]+)\\*\\*/g, '<b>$1</b>');
      s = s.replace(/\\*([^\\*]+)\\*/g, '<i>$1</i>');
      s = s.replace(/^- (.*$)/gim, '&bull; $1');
      s = s.split(String.fromCharCode(10)).join('<br>');
      return s;
    }'''

new_format = '''    function formatMarkdown(raw) {
      if (!raw) return '';
      let s = escapeHtml(raw);
      const b3 = String.fromCharCode(96) + String.fromCharCode(96) + String.fromCharCode(96);
      const b1 = String.fromCharCode(96);
      const codeBlockRe = new RegExp(b3 + '([a-zA-Z0-9_-]*)[\\r\\n]+([\\s\\S]*?)' + b3, 'g');
      s = s.replace(codeBlockRe, function(_, lang, code) {
        let detectedPath = '';
        const lines = code.split(String.fromCharCode(10));
        const firstLine = lines[0] ? lines[0].trim() : '';
        const m = firstLine.match(/^(?:(?:\\/\\/|#|\\/\\*)\\s*(?:File:\\s*)?([a-zA-Z0-9_\\-\\.\\/\\\\]+\\.[a-zA-Z0-9]+))/i);
        if (m && m[1]) {
          detectedPath = m[1].trim();
        }
        let headerHtml = '';
        if (detectedPath) {
          headerHtml = 
            '<div style="display:flex; justify-content:space-between; align-items:center; background:#181825; padding:5px 8px; border-top-left-radius:4px; border-top-right-radius:4px; border:1px solid rgba(255,255,255,0.08); border-bottom:none; font-size:11px;">' +
              '<span style="color:#a78bfa; font-weight:bold;">📄 ' + escapeHtml(detectedPath) + '</span>' +
              '<div>' +
                '<button class="action-btn" data-action="applyDiffFromCode" data-path="' + escapeHtml(detectedPath) + '" style="padding:2px 8px; font-size:10px; background:#22c55e; color:#fff; border:none; border-radius:3px; cursor:pointer; font-weight:bold; margin-right:4px;">⚡ Apply to File</button>' +
                '<button class="action-btn" data-action="copyCode" style="padding:2px 6px; font-size:10px; background:rgba(255,255,255,0.1); color:#ccc; border:none; border-radius:3px; cursor:pointer;">📋 Copy</button>' +
              '</div>' +
            '</div>';
        } else {
          headerHtml = 
            '<div style="display:flex; justify-content:space-between; align-items:center; background:#181825; padding:4px 8px; border-top-left-radius:4px; border-top-right-radius:4px; border:1px solid rgba(255,255,255,0.08); border-bottom:none; font-size:10px; color:#888;">' +
              '<span>' + (lang ? escapeHtml(lang) : 'code') + '</span>' +
              '<button class="action-btn" data-action="copyCode" style="padding:2px 6px; font-size:10px; background:rgba(255,255,255,0.1); color:#ccc; border:none; border-radius:3px; cursor:pointer;">📋 Copy</button>' +
            '</div>';
        }
        return '<div class="code-block-container" style="margin:8px 0;">' + headerHtml + 
               '<pre style="background:rgba(0,0,0,0.35); padding:8px; border-bottom-left-radius:4px; border-bottom-right-radius:4px; font-size:11px; overflow-x:auto; margin:0; border:1px solid rgba(255,255,255,0.06); font-family:monospace;"><code>' + code + '</code></pre>' +
               '</div>';
      });
      const inlineCodeRe = new RegExp(b1 + '([^' + b1 + '\\r\\n]+)' + b1, 'g');
      s = s.replace(inlineCodeRe, '<code style="background:rgba(255,255,255,0.1); padding:1px 4px; border-radius:3px; font-size:11px; font-family:monospace;">$1</code>');
      s = s.replace(/^### (.*$)/gim, '<div style="font-weight:bold; font-size:12px; color:#a78bfa; margin:6px 0 2px;">$1</div>');
      s = s.replace(/^## (.*$)/gim, '<div style="font-weight:bold; font-size:12.5px; color:#fff; margin:8px 0 3px;">$1</div>');
      s = s.replace(/^# (.*$)/gim, '<div style="font-weight:bold; font-size:13px; color:#fff; margin:10px 0 4px;">$1</div>');
      s = s.replace(/\\*\\*([^\\*]+)\\*\\*/g, '<b>$1</b>');
      s = s.replace(/\\*([^\\*]+)\\*/g, '<i>$1</i>');
      s = s.replace(/^- (.*$)/gim, '&bull; $1');
      s = s.split(String.fromCharCode(10)).join('<br>');
      return s;
    }'''

# 2. Update Click handler for applyDiffFromCode, copyCode, openExternalPR
old_click = '''        case 'applyPatch': {
          const key = target.getAttribute('data-patch-key');
          if (key) triggerApplyPatch(key);
          break;
        }'''

new_click = '''        case 'applyPatch': {
          const key = target.getAttribute('data-patch-key');
          if (key) triggerApplyPatch(key);
          break;
        }
        case 'applyDiffFromCode': {
          const pathParam = target.getAttribute('data-path');
          const container = target.closest('.code-block-container');
          const codeEl = container ? container.querySelector('pre code') : null;
          const patch = codeEl ? codeEl.textContent : '';
          if (pathParam && patch) {
            vscode.postMessage({ type: 'applyDiff', patch: patch, path: pathParam });
            target.textContent = '✓ Applied!';
            target.style.background = '#388bfd';
          }
          break;
        }
        case 'copyCode': {
          const container = target.closest('.code-block-container');
          const codeEl = container ? container.querySelector('pre code') : null;
          if (codeEl) {
            navigator.clipboard.writeText(codeEl.textContent);
            target.textContent = '✓ Copied!';
            setTimeout(() => { target.textContent = '📋 Copy'; }, 2000);
          }
          break;
        }
        case 'openExternalPR': {
          const url = target.getAttribute('data-url');
          if (url) {
            vscode.postMessage({ type: 'openExternal', url: url });
          }
          break;
        }'''

# 3. Update sendPrompt for create_file and open_pr
old_stream = '''                } else if (data.name === 'edit_file' && data.args) {
                  const pKey = 'patch_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
                  window.activeDiffPatches[pKey] = { patch: data.args.patch, path: data.args.path };
                  const card = document.createElement('div');
                  card.className = 'diff-card';
                  card.innerHTML = '<b>🛠️ Proposed Diff:</b> <code>' + escapeHtml(data.args.path) + '</code><br><small style="color:#8b949e;">' + escapeHtml(data.args.description) + '</small><br><button class="action-btn" style="margin-top:6px; font-size:11px;" data-action="applyPatch" data-patch-key="' + pKey + '">Accept & Apply</button>';
                  chatBox.appendChild(card);'''

new_stream = '''                } else if ((data.name === 'edit_file' || data.name === 'create_file') && data.args) {
                  const pKey = 'patch_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
                  window.activeDiffPatches[pKey] = { patch: data.args.patch, path: data.args.path };
                  const card = document.createElement('div');
                  card.className = 'diff-card';
                  const title = data.name === 'create_file' ? '📁 Created File:' : '🛠️ Modified File:';
                  card.innerHTML = '<b>' + title + '</b> <code>' + escapeHtml(data.args.path) + '</code><br><small style="color:#8b949e;">' + escapeHtml(data.args.description || 'Verified execution') + '</small><br><button class="action-btn" style="margin-top:6px; font-size:11px; background:#22c55e;" data-action="applyPatch" data-patch-key="' + pKey + '">✓ Open / Apply in Editor</button>';
                  chatBox.appendChild(card);
                } else if (data.name === 'open_pr' && data.args) {
                  const card = document.createElement('div');
                  card.className = 'diff-card';
                  card.style.borderColor = '#388bfd';
                  card.innerHTML = '<b>🚀 GitHub PR Created:</b> <a href="' + escapeHtml(data.args.pr_url) + '" target="_blank" style="color:#58a6ff; font-weight:bold;">' + escapeHtml(data.args.pr_url) + '</a><br><small style="color:#8b949e;">Branch: <code>' + escapeHtml(data.args.branch) + '</code> | 0 regressions</small><br><button class="action-btn" style="margin-top:6px; font-size:11px; background:#238636; color:#fff;" data-action="openExternalPR" data-url="' + escapeHtml(data.args.pr_url) + '">🔗 Open Pull Request on GitHub</button>';
                  chatBox.appendChild(card);'''

# 4. Update extension host message handler for openExternal
old_host = '''                case 'openCheckout': {'''
new_host = '''                case 'openExternal': {
                    if (msg.url) {
                        vscode.env.openExternal(vscode.Uri.parse(msg.url));
                    }
                    break;
                }

                case 'openCheckout': {'''

norm_ts = ts.replace('\r\n', '\n')
old_format = old_format.replace('\r\n', '\n')
new_format = new_format.replace('\r\n', '\n')
old_click = old_click.replace('\r\n', '\n')
new_click = new_click.replace('\r\n', '\n')
old_stream = old_stream.replace('\r\n', '\n')
new_stream = new_stream.replace('\r\n', '\n')
old_host = old_host.replace('\r\n', '\n')
new_host = new_host.replace('\r\n', '\n')

if old_format in norm_ts:
    norm_ts = norm_ts.replace(old_format, new_format, 1)
    print("1. Replaced formatMarkdown")
else:
    print("Failed to find old_format!")

if old_click in norm_ts:
    norm_ts = norm_ts.replace(old_click, new_click, 1)
    print("2. Replaced click handler")
else:
    print("Failed to find old_click!")

if old_stream in norm_ts:
    norm_ts = norm_ts.replace(old_stream, new_stream, 1)
    print("3. Replaced sendPrompt stream handler")
else:
    print("Failed to find old_stream!")

if old_host in norm_ts:
    norm_ts = norm_ts.replace(old_host, new_host, 1)
    print("4. Replaced extension host handler")
else:
    print("Failed to find old_host!")

with open(ext_path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(norm_ts.replace('\n', '\r\n'))

print("Updated extension.ts successfully.")
