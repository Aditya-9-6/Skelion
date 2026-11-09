import re

for filepath in [
    r'g:\My Drive\helios\skelion_vscode_extension\src\extension.ts',
    r'g:\My Drive\helios\skelion_vscode_extension\out\extension.js'
]:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove the admin button in webview
    content = re.sub(r'<button\s+data-action="openAdmin"[^>]*>.*?</button>', '', content)

    # Remove openMasterDashboard and instantDevLogin command registrations
    # In TS/JS: remove the registration blocks
    content = re.sub(r'vscode\.commands\.registerCommand\([\'"]skelion\.instantDevLogin[\'"],[\s\S]*?\),?', '', content)
    content = re.sub(r'vscode\.commands\.registerCommand\([\'"]skelion\.openMasterDashboard[\'"],[\s\S]*?\),?', '', content)
    
    # Clean up any trailing commas in registerCommand arrays
    content = re.sub(r',\s*\)', ')', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'Cleaned {filepath}')
