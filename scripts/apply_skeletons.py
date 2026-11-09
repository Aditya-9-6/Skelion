import os

ext_file = os.path.abspath('skelion_vscode_extension/src/extension.ts')
with open(ext_file, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update Backend fetch error handling
old_incidents = """                            if (res.ok) {

                                const data: any = await res.json();

                                const incidentsList = Array.isArray(data) ? data : (data.incidents || []);

                                webview.postMessage({ type: 'incidentsData', incidents: incidentsList });

                            }

                        } catch (e) {}"""

new_incidents = """                            if (res.ok) {
                                const data: any = await res.json();
                                const incidentsList = Array.isArray(data) ? data : (data.incidents || []);
                                webview.postMessage({ type: 'incidentsData', incidents: incidentsList });
                            } else {
                                webview.postMessage({ type: 'fetchError', panel: 'incidents', error: `Server returned HTTP ${res.status}` });
                            }
                        } catch (e: any) {
                            webview.postMessage({ type: 'fetchError', panel: 'incidents', error: e?.message || 'Failed to fetch incidents' });
                        }"""

if old_incidents in text:
    text = text.replace(old_incidents, new_incidents, 1)
    print('[1/8] Updated backend incidents fetcher')
else:
    print('[!] Note: old_incidents not matched directly')

old_suggestions = """                            if (res.ok) {

                                const data: any = await res.json();

                                const suggestionsList = Array.isArray(data) ? data : (data.suggestions || []);

                                webview.postMessage({

                                    type: 'suggestionsData',

                                    suggestions: suggestionsList,

                                    autofix_tokens_remaining: data.autofix_tokens_remaining

                                });

                            }

                        } catch (e) {}"""

new_suggestions = """                            if (res.ok) {
                                const data: any = await res.json();
                                const suggestionsList = Array.isArray(data) ? data : (data.suggestions || []);
                                webview.postMessage({
                                    type: 'suggestionsData',
                                    suggestions: suggestionsList,
                                    autofix_tokens_remaining: data.autofix_tokens_remaining
                                });
                            } else {
                                webview.postMessage({ type: 'fetchError', panel: 'suggestions', error: `Server returned HTTP ${res.status}` });
                            }
                        } catch (e: any) {
                            webview.postMessage({ type: 'fetchError', panel: 'suggestions', error: e?.message || 'Failed to fetch autofix suggestions' });
                        }"""

if old_suggestions in text:
    text = text.replace(old_suggestions, new_suggestions, 1)
    print('[2/8] Updated backend suggestions fetcher')

old_conversations = """                            if (res.ok) {

                                const data: any = await res.json();

                                webview.postMessage({ type: 'conversationsData', conversations: data.conversations || [] });

                            }

                        } catch (e) {}"""

new_conversations = """                            if (res.ok) {
                                const data: any = await res.json();
                                webview.postMessage({ type: 'conversationsData', conversations: data.conversations || [] });
                            } else {
                                webview.postMessage({ type: 'fetchError', panel: 'conversations', error: `Server returned HTTP ${res.status}` });
                            }
                        } catch (e: any) {
                            webview.postMessage({ type: 'fetchError', panel: 'conversations', error: e?.message || 'Failed to fetch conversations' });
                        }"""

if old_conversations in text:
    text = text.replace(old_conversations, new_conversations, 1)
    print('[3/8] Updated backend conversations fetcher')

old_limits = """                            if (res.ok) {

                                const limits = await res.json();

                                webview.postMessage({ type: 'limitsData', limits });

                            }

                        } catch (e) {}"""

new_limits = """                            if (res.ok) {
                                const limits = await res.json();
                                webview.postMessage({ type: 'limitsData', limits });
                            } else {
                                webview.postMessage({ type: 'fetchError', panel: 'limits', error: `Server returned HTTP ${res.status}` });
                            }
                        } catch (e: any) {
                            webview.postMessage({ type: 'fetchError', panel: 'limits', error: e?.message || 'Failed to fetch limits' });
                        }"""

if old_limits in text:
    text = text.replace(old_limits, new_limits, 1)
    print('[4/8] Updated backend limits fetcher')

# 2. Loading overlay
target_overlay = text[text.find('<body>'):text.find('<!-- SIGN IN SCREEN -->')]
new_overlay_block = """<body>
    <div id="loading-overlay" class="loading-overlay" aria-busy="true" aria-label="Loading Skelion Agent">
      <div class="skeleton-circle" style="width:48px; height:48px;"></div>
      <div class="skeleton-text" style="width:130px; height:12px;"></div>
    </div>

"""
text = text[:text.find('<body>')] + new_overlay_block + text[text.find('<!-- SIGN IN SCREEN -->'):]
print('[5/8] Updated loading overlay in HTML')

# 3. Header Sync button
old_sync_btn = '<button id="sync-btn" data-action="syncLiveProfile" style="background:transparent; border:none; color:#58a6ff; cursor:pointer; font-size:11px; display:inline-flex; align-items:center; gap:3px;" title="Sync Live Tokens & Plan">🔄 Sync</button>'
new_sync_btn = '<button id="sync-btn" data-action="syncLiveProfile" aria-label="Sync Live Tokens & Plan" style="background:transparent; border:none; color:#58a6ff; cursor:pointer; font-size:11px; display:inline-flex; align-items:center; gap:3px;" title="Sync Live Tokens & Plan"><span class="sync-icon">🔄</span> Sync</button>'
if old_sync_btn in text:
    text = text.replace(old_sync_btn, new_sync_btn, 1)
    print('[6/8] Updated sync button with icon span and aria-label')

# 4. Tab navigation accessibility
old_tabs = """    <div class="tabs">

      <button class="tab-btn active" data-tab="chat">💬 Ask</button>

      <button class="tab-btn" data-tab="incidents">🚨 Incidents</button>

      <button class="tab-btn" data-tab="autofix">⚡ Fixes</button>

      <button class="tab-btn" data-tab="history">📜 History</button>

      <button class="tab-btn" data-tab="limits">⏱️ Limits</button>

      <button class="tab-btn" data-tab="autonomous">🚀 Loop</button>

      <button class="tab-btn" data-tab="plugins">🔌 Plugins</button>

      <button class="tab-btn" data-tab="billing">💳 Pricing</button>

    </div>"""

new_tabs = """    <div class="tabs" role="tablist">

      <button class="tab-btn active" role="tab" data-tab="chat" aria-label="Ask Skelion AI Chat" title="Ask Skelion AI Chat">💬 Ask</button>

      <button class="tab-btn" role="tab" data-tab="incidents" aria-label="Live Production Incidents" title="Live Production Incidents">🚨 Incidents</button>

      <button class="tab-btn" role="tab" data-tab="autofix" aria-label="Skelion Autofix Patches" title="Skelion Autofix Patches">⚡ Fixes</button>

      <button class="tab-btn" role="tab" data-tab="history" aria-label="Saved Conversation History" title="Saved Conversation History">📜 History</button>

      <button class="tab-btn" role="tab" data-tab="limits" aria-label="Antigravity Pacing Limits" title="Antigravity Pacing Limits">⏱️ Limits</button>

      <button class="tab-btn" role="tab" data-tab="autonomous" aria-label="Autonomous DevOps Loop" title="Autonomous DevOps Loop">🚀 Loop</button>

      <button class="tab-btn" role="tab" data-tab="plugins" aria-label="Universal Plugins and MCP Hub" title="Universal Plugins and MCP Hub">🔌 Plugins</button>

      <button class="tab-btn" role="tab" data-tab="billing" aria-label="Pricing and Token Top-ups" title="Pricing and Token Top-ups">💳 Pricing</button>

    </div>"""

if old_tabs in text:
    text = text.replace(old_tabs, new_tabs, 1)
    print('[7/8] Updated tabs with roles and aria-labels')

# 5. Panel-specific Skeletons

# Incidents panel skeleton
old_incidents_panel = '<div id="incidents-list"><div class="skeleton-card" style="height:80px;"></div><div class="skeleton-card" style="height:80px;"></div><div class="skeleton-card" style="height:80px;"></div></div>'
new_incidents_panel = """<div id="incidents-list">
        <div id="skeleton-incidents">
          <div class="skeleton-card" style="height:76px; margin-bottom:8px;"></div>
          <div class="skeleton-card" style="height:76px; margin-bottom:8px;"></div>
          <div class="skeleton-card" style="height:76px; margin-bottom:8px;"></div>
        </div>
      </div>"""
if old_incidents_panel in text:
    text = text.replace(old_incidents_panel, new_incidents_panel, 1)
    print('[8a] Updated incidents skeleton panel')

# Autofix panel skeleton
old_autofix_list = '<div id="autofix-list">${suggestionsHtml}</div>'
new_autofix_list = """<div id="autofix-list">
        <div id="skeleton-autofix">
          <div class="skeleton-card" style="height:100px; margin-bottom:8px;"></div>
          <div class="skeleton-card" style="height:100px; margin-bottom:8px;"></div>
        </div>
      </div>"""
if old_autofix_list in text:
    text = text.replace(old_autofix_list, new_autofix_list, 1)
    print('[8b] Updated autofix skeleton panel')

# Limits panel skeleton
limits_start = text.find('<!-- TAB 3: LIMITS (ANTIGRAVITY-STYLE 5H & WEEKLY LIMITS) -->')
limits_end = text.find('<!-- TAB 4: HISTORY -->')
if limits_start != -1 and limits_end != -1:
    limits_block = text[limits_start:limits_end]
    new_limits_block = """<!-- TAB 3: LIMITS (ANTIGRAVITY-STYLE 5H & WEEKLY LIMITS) -->

    <div id="tab-limits" class="tab-content" style="display:none;">

      <div id="skeleton-limits">
        <div class="skeleton-card" style="height:55px; margin-bottom:8px;"></div>
        <div class="skeleton-card" style="height:75px; margin-bottom:8px;"></div>
        <div class="skeleton-card" style="height:75px; margin-bottom:8px;"></div>
        <div class="skeleton-card" style="height:48px; margin-bottom:8px;"></div>
      </div>

      <div id="limits-content" style="display:none;">

        <div class="card">

          <b>⏱️ Antigravity-Style Rate Pacing</b>

          <div style="font-size:11px; color:#888; margin-top:4px;">Protects provider capacity with 5-hour burst and weekly quotas.</div>

        </div>



        <div class="card">

          <div style="display:flex; justify-content:space-between;">

            <b>5-Hour Pacing Window</b>

            <span id="limit-5h-resets" style="color:#888; font-size:11px;">Resets in: 5h 0m</span>

          </div>

          <div style="display:flex; justify-content:space-between; margin-top:4px; font-size:11px;">

            <span>Tokens Used:</span>

            <b id="limit-5h-count">0 / 500</b>

          </div>

          <div class="progress-bar-container"><div id="limit-5h-bar" class="progress-bar-fill" style="width:0%;"></div></div>

        </div>



        <div class="card">

          <div style="display:flex; justify-content:space-between;">

            <b>Weekly Quota Window</b>

            <span id="limit-weekly-resets" style="color:#888; font-size:11px;">Resets in: 7d 0h</span>

          </div>

          <div style="display:flex; justify-content:space-between; margin-top:4px; font-size:11px;">

            <span>Tokens Used:</span>

            <b id="limit-weekly-count">0 / 1500</b>

          </div>

          <div class="progress-bar-container"><div id="limit-weekly-bar" class="progress-bar-fill" style="width:0%;"></div></div>

        </div>



        <div class="card">

          <div style="display:flex; justify-content:space-between; align-items:center;">

            <div>

              <b>Enforce Rate Limits</b>

              <div style="font-size:10.5px; color:#888;">Disable to burn purchased tokens at maximum speed</div>

            </div>

            <input type="checkbox" id="limit-toggle" style="width:auto;" checked />

          </div>

        </div>

      </div>

    </div>

"""
    text = text[:limits_start] + new_limits_block + text[limits_end:]
    print('[8c] Updated limits panel with skeleton and limits-content wrapper')

# History panel skeleton
old_history = '<div id="history-list">${conversationsHistoryHtml}</div>'
new_history = """<div id="history-list">
        <div id="skeleton-history">
          <div class="skeleton-card" style="height:48px; margin-bottom:6px;"></div>
          <div class="skeleton-card" style="height:48px; margin-bottom:6px;"></div>
          <div class="skeleton-card" style="height:48px; margin-bottom:6px;"></div>
        </div>
      </div>"""
if old_history in text:
    text = text.replace(old_history, new_history, 1)
    print('[8d] Updated history panel skeleton')

# Plugins panel skeleton
old_plugins_container = '<div id="plugins-list-container" style="display:flex; flex-direction:column; gap:10px;">'
new_plugins_container = """<div id="plugins-list-container" style="display:flex; flex-direction:column; gap:10px;">
        <div id="skeleton-plugins" style="display:none;">
          <div class="skeleton-card" style="height:90px; margin-bottom:8px;"></div>
          <div class="skeleton-card" style="height:80px; margin-bottom:8px;"></div>
          <div class="skeleton-card" style="height:80px; margin-bottom:8px;"></div>
        </div>"""
if old_plugins_container in text:
    text = text.replace(old_plugins_container, new_plugins_container, 1)
    print('[8e] Updated plugins container with skeleton')

# Chat drawer skeleton
old_drawer = '<div id="chat-drawer-list" style="font-size:11px; color:#888;">${conversationsDrawerHtml}</div>'
new_drawer = """<div id="chat-drawer-list" style="font-size:11px; color:#888;">
          <div id="skeleton-drawer">
            <div class="skeleton-text" style="width:85%; height:14px; margin-bottom:8px;"></div>
            <div class="skeleton-text" style="width:65%; height:14px; margin-bottom:8px;"></div>
            <div class="skeleton-text" style="width:75%; height:14px; margin-bottom:8px;"></div>
          </div>
        </div>"""
if old_drawer in text:
    text = text.replace(old_drawer, new_drawer, 1)
    print('[8f] Updated chat drawer skeleton')

with open(ext_file, 'w', encoding='utf-8', newline='') as f:
    f.write(text)

print('Phase 1 skeleton markup applied!')
