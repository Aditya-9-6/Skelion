import re
import subprocess
import os

with open('skelion_vscode_extension/src/extension.ts', 'r', encoding='utf-8') as f:
    text = f.read()

m = re.search(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
if not m:
    print('No script found')
    exit(1)

code = m.group(1)
# Replace interpolations
code = re.sub(r'let currentToken = \$\{.*?\};', 'let currentToken = "tok";', code)
code = re.sub(r'let currentUser = \$\{.*?\};', 'let currentUser = {"plan": "hosted_developer"};', code)
code = re.sub(r'let initialLimits = \$\{.*?\};', '''let initialLimits = {
    "plan": "hosted_developer",
    "coding_tokens": {"limit_enforcement_enabled": true},
    "windows": {
        "five_hour": {"used": 0, "limit": 500, "percentage_used": 0, "resets_in_human": "5h"},
        "weekly": {"used": 0, "limit": 1500, "percentage_used": 0, "resets_in_human": "7d"}
    },
    "autofix_tokens": {"remaining": 60000}
};''', code)

header = '''
const acquireVsCodeApi = () => ({ postMessage: () => {} });
const document = {
  readyState: "complete",
  getElementById: (id) => ({ id, style: {}, classList: { add: ()=>{}, remove: ()=>{} }, innerHTML: "", textContent: "", value: "100", checked: true, addEventListener: ()=>{}, focus: ()=>{} }),
  querySelectorAll: () => [],
  querySelector: () => null,
  addEventListener: () => {}
};
const window = { addEventListener: () => {}, activeSuggestions: {}, activeDiffPatches: {} };
const alert = () => {};
'''

with open('temp_eval.js', 'w', encoding='utf-8') as f:
    f.write(header + '\n' + code)

res = subprocess.run(['node', 'temp_eval.js'], capture_output=True, text=True)
print("Node STDOUT:", res.stdout)
print("Node STDERR:", res.stderr)
print("Exit code:", res.returncode)
if os.path.exists('temp_eval.js'):
    os.remove('temp_eval.js')
