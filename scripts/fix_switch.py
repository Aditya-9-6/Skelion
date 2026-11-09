for p in [
    r'g:\My Drive\helios\skelion_vscode_extension\src\extension.ts',
    r'g:\My Drive\helios\skelion_vscode_extension\out\extension.js'
]:
    with open(p, 'r', encoding='utf-8') as f:
        t = f.read()

    # The buggy replacement was:
    # case 'webviewReady': {
    #                case 'syncLiveProfile': {
    # ...
    #                    break;
    #                }
    #                     await this.checkExistingSession(webview);
    #                     break;
    #                 }
    
    bad_part = """case 'webviewReady': {
                case 'syncLiveProfile': {"""
    good_part = """case 'syncLiveProfile': {"""
    t = t.replace(bad_part, good_part)

    bad_end = """                    break;
                }

                    await this.checkExistingSession(webview);"""
    good_end = """                    break;
                }
                case 'webviewReady': {
                    await this.checkExistingSession(webview);"""
    t = t.replace(bad_end, good_end)

    with open(p, 'w', encoding='utf-8') as f:
        f.write(t)

print("Fixed switch statements successfully!")
