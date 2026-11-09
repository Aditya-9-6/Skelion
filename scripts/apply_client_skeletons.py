import os

ext_file = os.path.abspath('skelion_vscode_extension/src/extension.ts')
with open(ext_file, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Overlay removal in authenticated
old_auth_overlay = """          if (appEl) { appEl.classList.add('active');
          // Remove loading overlay once UI is ready
          const overlay = document.getElementById('loading-overlay');
          if (overlay) overlay.remove(); appEl.style.display = 'flex'; }"""

new_auth_overlay = """          if (appEl) {
            appEl.classList.add('active');
            const overlay = document.getElementById('loading-overlay');
            if (overlay) {
              overlay.setAttribute('aria-busy', 'false');
              overlay.style.opacity = '0';
              setTimeout(() => overlay.remove(), 250);
            }
            appEl.style.display = 'flex';
          }"""

if old_auth_overlay in text:
    text = text.replace(old_auth_overlay, new_auth_overlay, 1)
    print('[1/6] Updated authenticated overlay removal')

# 2. Overlay removal in unauthenticated
old_unauth_overlay = """          const signinEl = document.getElementById('screen-signin');

          if (signinEl) { signinEl.classList.add('active'); signinEl.style.display = 'block'; }"""

new_unauth_overlay = """          const signinEl = document.getElementById('screen-signin');
          const overlay = document.getElementById('loading-overlay');
          if (overlay) {
            overlay.setAttribute('aria-busy', 'false');
            overlay.style.opacity = '0';
            setTimeout(() => overlay.remove(), 250);
          }
          if (signinEl) { signinEl.classList.add('active'); signinEl.style.display = 'block'; }"""

if old_unauth_overlay in text:
    text = text.replace(old_unauth_overlay, new_unauth_overlay, 1)
    print('[2/6] Updated unauthenticated overlay removal')

# 3. Add Skeleton & Error Helper Functions before renderLimitsUI
helpers_code = """
    function showIncidentsSkeleton() {
      const list = document.getElementById('incidents-list');
      if (list) {
        list.innerHTML = '<div id="skeleton-incidents">' +
          '<div class="skeleton-card" style="height:76px; margin-bottom:8px;"></div>' +
          '<div class="skeleton-card" style="height:76px; margin-bottom:8px;"></div>' +
          '<div class="skeleton-card" style="height:76px; margin-bottom:8px;"></div>' +
        '</div>';
      }
    }

    function showSuggestionsSkeleton() {
      const list = document.getElementById('autofix-list');
      if (list) {
        list.innerHTML = '<div id="skeleton-autofix">' +
          '<div class="skeleton-card" style="height:100px; margin-bottom:8px;"></div>' +
          '<div class="skeleton-card" style="height:100px; margin-bottom:8px;"></div>' +
        '</div>';
      }
    }

    function showLimitsSkeleton() {
      const sk = document.getElementById('skeleton-limits');
      const lc = document.getElementById('limits-content');
      if (sk) sk.style.display = 'block';
      if (lc) lc.style.display = 'none';
    }

    function showHistorySkeleton() {
      const list = document.getElementById('history-list');
      if (list) {
        list.innerHTML = '<div id="skeleton-history">' +
          '<div class="skeleton-card" style="height:48px; margin-bottom:6px;"></div>' +
          '<div class="skeleton-card" style="height:48px; margin-bottom:6px;"></div>' +
          '<div class="skeleton-card" style="height:48px; margin-bottom:6px;"></div>' +
        '</div>';
      }
    }

    function showPluginsSkeleton() {
      const container = document.getElementById('plugins-list-container');
      if (container) {
        container.innerHTML = '<div id="skeleton-plugins">' +
          '<div class="skeleton-card" style="height:90px; margin-bottom:8px;"></div>' +
          '<div class="skeleton-card" style="height:80px; margin-bottom:8px;"></div>' +
          '<div class="skeleton-card" style="height:80px; margin-bottom:8px;"></div>' +
        '</div>';
      }
    }

    function showPanelError(containerId, errorText, retryAction) {
      const container = document.getElementById(containerId);
      if (!container) return;
      container.innerHTML = '<div class="card fade-in" style="border-left: 3px solid #f85149; background: rgba(248,81,73,0.06); text-align:center; padding:16px 12px;">' +
        '<div style="font-weight:bold; color:#f85149; font-size:12px; margin-bottom:4px;">⚠️ Connection Notice</div>' +
        '<div style="font-size:11px; color:#888; margin-bottom:10px;">' + escapeHtml(errorText || 'Unable to reach Skelion edge service.') + '</div>' +
        '<button class="action-btn" data-action="' + retryAction + '" style="width:auto; padding:5px 14px; font-size:11px; display:inline-block;">🔄 Retry</button>' +
      '</div>';
    }
"""

old_render_limits = "    function renderLimitsUI(limits) {"
new_render_limits = helpers_code + "\n    function renderLimitsUI(limits) {\n      const skLimits = document.getElementById('skeleton-limits');\n      if (skLimits) skLimits.style.display = 'none';\n      const limitsContent = document.getElementById('limits-content');\n      if (limitsContent) { limitsContent.style.display = 'block'; limitsContent.classList.add('fade-in'); }\n"

if old_render_limits in text:
    text = text.replace(old_render_limits, new_render_limits, 1)
    print('[3/6] Injected skeleton and error helper functions & updated renderLimitsUI')

# 4. Update switchTab with skeletons
old_switch_post = """        if (tab === 'incidents') vscode.postMessage({ type: 'fetchIncidents' });

        if (tab === 'autofix') vscode.postMessage({ type: 'fetchSuggestions' });

        if (tab === 'limits') vscode.postMessage({ type: 'fetchLimits' });

        if (tab === 'history') vscode.postMessage({ type: 'fetchConversations' });"""

new_switch_post = """        if (tab === 'incidents') {
          showIncidentsSkeleton();
          vscode.postMessage({ type: 'fetchIncidents' });
        }
        if (tab === 'autofix') {
          showSuggestionsSkeleton();
          vscode.postMessage({ type: 'fetchSuggestions' });
        }
        if (tab === 'limits') {
          showLimitsSkeleton();
          vscode.postMessage({ type: 'fetchLimits' });
        }
        if (tab === 'history') {
          showHistorySkeleton();
          vscode.postMessage({ type: 'fetchConversations' });
        }
        if (tab === 'plugins') {
          showPluginsSkeleton();
          vscode.postMessage({ type: 'fetchPlugins' });
        }"""

if old_switch_post in text:
    text = text.replace(old_switch_post, new_switch_post, 1)
    print('[4/6] Updated switchTab with skeleton display triggers')

# 5. Update click handlers for refresh & sync
old_clicks = """        case 'refreshIncidents': {

          vscode.postMessage({ type: 'fetchIncidents' });

          break;

        }

        case 'refreshSuggestions': {

          vscode.postMessage({ type: 'fetchSuggestions' });

          break;

        }"""

new_clicks = """        case 'syncLiveProfile': {
          const sBtn = document.getElementById('sync-btn');
          const syncIcon = sBtn ? sBtn.querySelector('.sync-icon') : null;
          if (syncIcon) syncIcon.classList.add('spinning');
          vscode.postMessage({ type: 'syncLiveProfile' });
          break;
        }

        case 'refreshIncidents': {
          showIncidentsSkeleton();
          vscode.postMessage({ type: 'fetchIncidents' });
          break;
        }

        case 'refreshSuggestions': {
          showSuggestionsSkeleton();
          vscode.postMessage({ type: 'fetchSuggestions' });
          break;
        }"""

if old_clicks in text:
    text = text.replace(old_clicks, new_clicks, 1)
    print('[5/6] Updated click handlers for syncLiveProfile, refreshIncidents, and refreshSuggestions')

old_history_click = """        case 'refreshHistory': {

          vscode.postMessage({ type: 'fetchConversations' });

          break;

        }"""

new_history_click = """        case 'refreshHistory': {
          showHistorySkeleton();
          vscode.postMessage({ type: 'fetchConversations' });
          break;
        }"""

if old_history_click in text:
    text = text.replace(old_history_click, new_history_click, 1)
    print('[5b] Updated refreshHistory click handler')

# 6. Message handler updates (liveProfileUpdated spinner stop, pluginsLoaded, fetchError)
old_live_msg = """          const sBtn = document.getElementById('sync-btn');
          if (sBtn) {
            sBtn.textContent = '✓ Live';
            setTimeout(() => { if (sBtn) sBtn.innerHTML = '🔄 Sync'; }, 1500);
          }"""

new_live_msg = """          const sBtn = document.getElementById('sync-btn');
          if (sBtn) {
            const syncIcon = sBtn.querySelector('.sync-icon');
            if (syncIcon) syncIcon.classList.remove('spinning');
            sBtn.innerHTML = '✓ Live';
            setTimeout(() => { if (sBtn) sBtn.innerHTML = '<span class="sync-icon">🔄</span> Sync'; }, 1500);
          }"""

if old_live_msg in text:
    text = text.replace(old_live_msg, new_live_msg, 1)
    print('[6a] Updated liveProfileUpdated sync button restore')

old_limits_msg = "} else if (msg.type === 'limitsData') {"
new_plugins_and_error_msg = """        } else if (msg.type === 'fetchError') {
          console.warn('Fetch error received:', msg);
          if (msg.panel === 'incidents') showPanelError('incidents-list', msg.error, 'refreshIncidents');
          else if (msg.panel === 'suggestions') showPanelError('autofix-list', msg.error, 'refreshSuggestions');
          else if (msg.panel === 'conversations') showPanelError('history-list', msg.error, 'refreshHistory');
          else if (msg.panel === 'plugins') showPanelError('plugins-list-container', msg.error, 'fetchPlugins');
        } else if (msg.type === 'pluginsLoaded') {
          const d = msg.data || {};
          const container = document.getElementById('plugins-list-container');
          if (container && d.plugins && Array.isArray(d.plugins)) {
            container.classList.remove('fade-in');
            void container.offsetWidth;
            container.classList.add('fade-in');
            container.innerHTML = d.plugins.map(function(p) {
              const toolsHtml = (p.tools || []).map(function(t) {
                return '<span style="font-size:10px; background:#f1f5f9; padding:2px 6px; border-radius:4px; font-family:monospace;">🔧 ' + escapeHtml(t.name) + '</span>';
              }).join(' ');
              return '<div class="card" style="border:1px solid rgba(0,0,0,0.08); padding:10px;">' +
                '<div style="display:flex; justify-content:space-between; align-items:center;">' +
                  '<div>' +
                    '<div style="display:flex; align-items:center; gap:6px;">' +
                      '<b style="font-size:13px; color:#1e293b;">' + escapeHtml(p.name) + '</b>' +
                      '<span style="font-size:10px; background:#e0e7ff; color:#3730a3; padding:1px 6px; border-radius:8px;">' + escapeHtml(p.type || 'MCP') + '</span>' +
                    '</div>' +
                    '<div style="font-size:11px; color:#64748b; margin-top:2px;">Status: <b style="color:#10b981;">' + escapeHtml(p.status || 'Connected') + '</b></div>' +
                  '</div>' +
                  '<label style="display:flex; align-items:center; gap:4px; font-size:11px; cursor:pointer;">' +
                    '<input type="checkbox" ' + (p.enabled ? 'checked' : '') + ' data-action="togglePlugin" data-plugin-id="' + escapeHtml(p.id) + '" style="cursor:pointer;" />' +
                    '<span style="color:#059669; font-weight:600;">Active</span>' +
                  '</label>' +
                '</div>' +
                (toolsHtml ? '<div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;">' + toolsHtml + '</div>' : '') +
              '</div>';
            }).join('');
          }
        } else if (msg.type === 'limitsData') {"""

if old_limits_msg in text:
    text = text.replace(old_limits_msg, new_plugins_and_error_msg, 1)
    print('[6b] Injected pluginsLoaded and fetchError message handlers')

with open(ext_file, 'w', encoding='utf-8', newline='') as f:
    f.write(text)

print('Phase 2 client skeleton & error wiring complete!')
