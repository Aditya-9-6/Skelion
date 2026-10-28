import os

file_path = r'skelion_vscode_extension/src/extension.ts'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

idx1 = text.find('function formatMarkdown')
idx2 = text.find('function newChat')

if idx1 == -1 or idx2 == -1:
    print(f"Could not find indices: idx1={idx1}, idx2={idx2}")
    exit(1)

new_func = """function formatMarkdown(raw) {
      if (!raw) return '';
      let s = escapeHtml(raw);
      const b3 = String.fromCharCode(96) + String.fromCharCode(96) + String.fromCharCode(96);
      const b1 = String.fromCharCode(96);
      const codeBlockRe = new RegExp(b3 + '([a-zA-Z0-9_-]*)[\\\\r\\\\n]+([\\\\s\\\\S]*?)' + b3, 'g');
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
      const inlineCodeRe = new RegExp(b1 + '([^' + b1 + '\\\\r\\\\n]+)' + b1, 'g');
      s = s.replace(inlineCodeRe, '<code style="background:rgba(255,255,255,0.1); padding:1px 4px; border-radius:3px; font-size:11px; font-family:monospace;">$1</code>');
      s = s.replace(/^### (.*$)/gim, '<div style="font-weight:bold; font-size:12px; color:#a78bfa; margin:6px 0 2px;">$1</div>');
      s = s.replace(/^## (.*$)/gim, '<div style="font-weight:bold; font-size:12.5px; color:#fff; margin:8px 0 3px;">$1</div>');
      s = s.replace(/^# (.*$)/gim, '<div style="font-weight:bold; font-size:13px; color:#fff; margin:10px 0 4px;">$1</div>');
      s = s.replace(/\\\\*\\\\*([^\\\\*]+)\\\\*\\\\*/g, '<b>$1</b>');
      s = s.replace(/\\\\*([^\\\\*]+)\\\\*/g, '<i>$1</i>');
      s = s.replace(/^- (.*$)/gim, '&bull; $1');
      s = s.split(String.fromCharCode(10)).join('<br>');
      return s;
    }

    """

text = text[:idx1] + new_func + text[idx2:]
with open(file_path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(text)

print("Updated formatMarkdown successfully!")
