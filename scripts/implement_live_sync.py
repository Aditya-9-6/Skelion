import re

for filepath in [
    r'g:\My Drive\helios\skelion_vscode_extension\src\extension.ts',
    r'g:\My Drive\helios\skelion_vscode_extension\out\extension.js'
]:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add syncLiveProfile case to attachMessageListener
    sync_handler = '''
                case 'syncLiveProfile': {
                    const token = await this.getValidToken();
                    if (token) {
                        try {
                            const apiBase = await resolveApiBase();
                            const meRes = await safeFetch(`${apiBase}/v1/auth/me`, {
                                headers: { 'Authorization': `Bearer ${token}` }
                            });
                            if (meRes.ok) {
                                const meData = await meRes.json();
                                const user = {
                                    ...meData,
                                    username: meData.github_username || meData.name || 'Aditya-9-6'
                                };
                                const limitsRes = await safeFetch(`${apiBase}/v1/limits/status`, {
                                    headers: { 'Authorization': `Bearer ${token}` }
                                });
                                const limits = limitsRes.ok ? await limitsRes.json() : null;
                                webview.postMessage({
                                    type: 'liveProfileUpdated',
                                    user,
                                    limits
                                });
                            }
                        } catch (_) {}
                    }
                    break;
                }
'''
    if "case 'syncLiveProfile':" not in content:
        content = content.replace("case 'webviewReady': {", "case 'webviewReady': {" + sync_handler, 1)
        print(f"Added syncLiveProfile handler to {filepath}")

    # 2. Add Sync button to the header
    sync_btn_html = '<button id="sync-btn" data-action="syncLiveProfile" style="background:transparent; border:none; color:#58a6ff; cursor:pointer; font-size:11px; display:inline-flex; align-items:center; gap:3px;" title="Sync Live Tokens & Plan">🔄 Sync</button>'
    if 'id="sync-btn"' not in content:
        content = content.replace('<button id="signout-btn"', sync_btn_html + ' <button id="signout-btn"')
        print(f"Added sync-btn to header in {filepath}")

    # 3. Add token balance card to Limits tab
    balance_card_html = '''
      <div class="card" style="border-left: 3px solid #58a6ff; background: rgba(88, 166, 255, 0.05); margin-bottom: 12px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <b>Organization Token Balance</b>
            <div style="font-size:10.5px; color:#888;">Live pooled enterprise credits</div>
          </div>
          <button id="sync-limits-btn" data-action="syncLiveProfile" style="background:#238636; border:none; border-radius:4px; padding:3px 8px; font-size:10.5px; color:#fff; cursor:pointer; font-weight:600;">🔄 Sync</button>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:8px; font-size:12px;">
          <span>Available Coding Tokens:</span>
          <b id="total-tokens-balance" style="color:#58a6ff; font-size:13px;">0</b>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:2px; font-size:10.5px; color:#888;">
          <span>Monthly Quota: <span id="monthly-tokens-balance">0</span></span>
          <span>Purchased / Top-up: <span id="purchased-tokens-balance">0</span></span>
        </div>
      </div>
'''
    if 'id="total-tokens-balance"' not in content:
        content = content.replace('<div id="tab-limits" class="tab-content">', '<div id="tab-limits" class="tab-content">' + balance_card_html)
        print(f"Added balance card to Limits tab in {filepath}")

    # 4. Update renderLimitsUI to display coding_tokens and plan
    render_tokens_logic = '''
        if (limits.coding_tokens) {
          const tot = limits.coding_tokens.total_remaining != null ? limits.coding_tokens.total_remaining : 0;
          const mon = limits.coding_tokens.monthly_remaining != null ? limits.coding_tokens.monthly_remaining : 0;
          const pur = limits.coding_tokens.purchased_remaining != null ? limits.coding_tokens.purchased_remaining : 0;
          setElText('total-tokens-balance', tot.toLocaleString());
          setElText('monthly-tokens-balance', mon.toLocaleString());
          setElText('purchased-tokens-balance', pur.toLocaleString());
        }
        if (limits.plan) {
          const pb = document.getElementById('plan-badge');
          if (pb) pb.textContent = String(limits.plan).toUpperCase();
        }
'''
    if "setElText('total-tokens-balance'" not in content:
        content = content.replace("function renderLimitsUI(limits) {", "function renderLimitsUI(limits) {" + render_tokens_logic)
        print(f"Updated renderLimitsUI in {filepath}")

    # 5. Add liveProfileUpdated handler and auto-sync intervals in webview JS
    live_profile_msg = '''
        } else if (msg.type === 'liveProfileUpdated') {
          if (msg.user) {
            currentUser = msg.user;
            const uDisp = document.getElementById('user-display');
            if (uDisp) uDisp.textContent = msg.user.username || msg.user.name || 'Aditya-9-6';
            const pBadge = document.getElementById('plan-badge');
            if (pBadge && msg.user.plan) pBadge.textContent = String(msg.user.plan).toUpperCase();
          }
          if (msg.limits) {
            try { renderLimitsUI(msg.limits); } catch(e) {}
          }
          const sBtn = document.getElementById('sync-btn');
          if (sBtn) {
            sBtn.textContent = '✓ Live';
            setTimeout(() => { if (sBtn) sBtn.innerHTML = '🔄 Sync'; }, 1500);
          }
'''
    if "msg.type === 'liveProfileUpdated'" not in content:
        content = content.replace("} else if (msg.type === 'limitsData') {", live_profile_msg + "} else if (msg.type === 'limitsData') {")
        print(f"Added liveProfileUpdated message handler in {filepath}")

    # 6. Add background heartbeat & window focus listeners to webview
    heartbeat_code = '''
    // Real-time live sync (No restart needed on purchase or quota update)
    window.addEventListener('focus', () => {
      vscode.postMessage({ type: 'syncLiveProfile' });
    });
    setInterval(() => {
      vscode.postMessage({ type: 'syncLiveProfile' });
    }, 15000);
'''
    if "vscode.postMessage({ type: 'syncLiveProfile' });" not in content:
        content = content.replace("window.addEventListener('message',", heartbeat_code + "\n    window.addEventListener('message',")
        print(f"Added heartbeat and focus listeners in {filepath}")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done implementing live sync!")
