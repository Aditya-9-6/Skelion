// Skelion VS Code Control Center - Updated with Authentication, Billing, Plans, Credits

// ==== Configuration ==========================================================
const API_BASE_URL = "http://127.0.0.1:8002"; // adjust if needed
// ===========================================================================

// VS Code API for messaging between webview and extension host
const vscode = acquireVsCodeApi();

// Store auth token in localStorage (fallback) and request extension to persist securely
function getStoredToken() {
  return localStorage.getItem("skelionAuthToken") || "";
}
function setStoredToken(token) {
  localStorage.setItem("skelionAuthToken", token);
  vscode.postMessage({ type: "saveToken", token }); // Extension can persist via secret storage
}
function clearStoredToken() {
  localStorage.removeItem("skelionAuthToken");
  vscode.postMessage({ type: "clearToken" });
}

// Helper: fetch wrapper that includes Authorization if token present
async function api(path, opts = {}) {
  const token = getStoredToken();
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE_URL}${path}`, { headers, ...opts });
  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`API ${path} failed: ${resp.status} ${err}`);
  }
  // Some endpoints (e.g., billing) may return no JSON; handle gracefully
  const contentType = resp.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) return resp.json();
  return resp.text();
}

// ---- Tab navigation --------------------------------------------------------
const TABS = [
  { id: "incidents", label: "⚡ Incidents" },
  { id: "chat", label: "🤖 Skelion Chat" },
  { id: "gossip", label: "🛡️ GossipMesh" },
  { id: "billing", label: "💳 Billing" },
  { id: "settings", label: "⚙️ Settings" },
];

function renderTabs(active) {
  const container = document.createElement("div");
  container.className = "flex border-b border-[color:var(--vscode-editorGroup-border)]";
  TABS.forEach((tab) => {
    const btn = document.createElement("button");
    btn.textContent = tab.label;
    btn.dataset.tab = tab.id;
    btn.className = `flex-1 py-2 ${tab.id === active
      ? "bg-[color:var(--vscode-button-background)] text-[color:var(--vscode-button-foreground)]"
      : "bg-[color:var(--vscode-editor-background)] text-[color:var(--vscode-editor-foreground)]"}`;
    btn.onclick = () => switchTab(tab.id);
    container.appendChild(btn);
  });
  return container;
}

let currentTab = "incidents";
function switchTab(tabId) {
  currentTab = tabId;
  renderApp();
}

// ==== INCIDENTS TAB =========================================================
async function renderIncidents() {
  const container = document.createElement("div");
  container.className = "p-4 space-y-4";

  const header = document.createElement("div");
  header.className = "flex justify-between items-center";
  header.innerHTML = `<h2 class="text-lg font-medium">Active Incidents</h2>`;
  const refreshBtn = document.createElement("button");
  refreshBtn.textContent = "Refresh";
  refreshBtn.className = "px-3 py-1 bg-blue-600 text-white rounded";
  refreshBtn.onclick = async () => { refreshBtn.disabled = true; await loadIncidents(container); refreshBtn.disabled = false; };
  header.appendChild(refreshBtn);
  container.appendChild(header);

  const listDiv = document.createElement("div");
  listDiv.textContent = "Loading incidents…";
  container.appendChild(listDiv);

  await loadIncidents(container);
  return container;
}

async function loadIncidents(rootDiv) {
  const listDiv = rootDiv.lastElementChild;
  try {
    const data = await api("/v1/panel/");
    if (!Array.isArray(data) || data.length === 0) {
      listDiv.textContent = "No active incidents.";
      return;
    }
    listDiv.innerHTML = "";
    data.forEach((inc) => {
      const card = document.createElement("div");
      card.className = "border rounded p-3 bg-[color:var(--vscode-editorWidget-background)]";
      const title = document.createElement("div");
      title.className = "flex justify-between items-center";
      const incidentId = document.createElement("span");
      incidentId.textContent = `#${inc.id.slice(0, 8)}`;
      incidentId.className = "font-semibold";
      const badge = document.createElement("span");
      badge.textContent = inc.status === "patch_ready" ? "✅ Ready" : "❌ Pending";
      badge.className = `px-2 py-0.5 rounded ${inc.status === "patch_ready" ? "bg-green-500" : "bg-red-500"} text-white text-sm`;
      title.append(incidentId, badge);
      card.appendChild(title);

      const diffToggle = document.createElement("button");
      diffToggle.textContent = "Show Diff";
      diffToggle.className = "mt-2 text-blue-600 underline";
      const diffBox = document.createElement("pre");
      diffBox.className = "mt-2 p-2 bg-[color:var(--vscode-editor-background)] rounded overflow-x-auto hidden whitespace-pre-wrap";
      diffBox.textContent = inc.generated_diff || "No diff generated.";
      diffToggle.onclick = () => diffBox.classList.toggle("hidden");
      card.append(diffToggle, diffBox);

      const applyBtn = document.createElement("button");
      applyBtn.textContent = "⚡ Apply Fix & Replay";
      applyBtn.className = "mt-2 px-3 py-1 bg-indigo-600 text-white rounded";
      applyBtn.disabled = inc.status !== "patch_ready";
      applyBtn.onclick = async () => {
        applyBtn.disabled = true;
        applyBtn.textContent = "Applying…";
        try {
          await api(`/v1/panel/apply_fix/${inc.id}`, { method: "POST" });
          badge.textContent = "✅ Applied";
          badge.className = "px-2 py-0.5 rounded bg-green-500 text-white text-sm";
        } catch (e) {
          badge.textContent = "❌ Failed";
          badge.className = "px-2 py-0.5 rounded bg-red-500 text-white text-sm";
        } finally {
          applyBtn.textContent = "⚡ Apply Fix & Replay";
        }
      };
      card.appendChild(applyBtn);
      listDiv.appendChild(card);
    });
  } catch (e) {
    listDiv.textContent = `Error loading incidents: ${e.message}`;
  }
}

// ==== SKELION CHAT TAB ======================================================
function renderChat() {
  const container = document.createElement("div");
  container.className = "p-4 flex flex-col h-full";

  const messagesDiv = document.createElement("div");
  messagesDiv.className = "flex-1 overflow-y-auto space-y-2 mb-2";

  const inputDiv = document.createElement("div");
  inputDiv.className = "flex space-x-2";

  const textarea = document.createElement("textarea");
  textarea.className = "flex-1 p-2 border rounded resize-none";
  textarea.rows = 2;
  textarea.placeholder = "Ask Skelion anything…";

  const sendBtn = document.createElement("button");
  sendBtn.textContent = "Send";
  sendBtn.className = "px-3 py-1 bg-blue-600 text-white rounded";

  const injectBtn = document.createElement("button");
  injectBtn.textContent = "📡 Inject Incident Telemetry";
  injectBtn.className = "px-3 py-1 bg-purple-600 text-white rounded";

  inputDiv.append(textarea, sendBtn, injectBtn);
  container.append(messagesDiv, inputDiv);

  function addMessage(text, from = "user") {
    const bubble = document.createElement("div");
    bubble.textContent = text;
    bubble.className = `p-2 rounded max-w-xs ${from === "user" ? "bg-blue-200 self-end" : "bg-gray-200 self-start"}`;
    messagesDiv.appendChild(bubble);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  sendBtn.onclick = async () => {
    const prompt = textarea.value.trim();
    if (!prompt) return;
    addMessage(prompt, "user");
    textarea.value = "";
    try {
      const resp = await api("/v1/chat/", { method: "POST", body: JSON.stringify({ message: prompt }) });
      addMessage(resp.reply || "…", "bot");
    } catch (e) {
      addMessage(`Error: ${e.message}`, "bot");
    }
  };

  injectBtn.onclick = async () => {
    try {
      const incidents = await api("/v1/panel/");
      if (incidents.length === 0) { addMessage("No incident to inject.", "bot"); return; }
      const latest = incidents[0];
      const payload = JSON.stringify({ incident_id: latest.id, captured_body: latest.captured_body, captured_headers: latest.captured_headers });
      addMessage(`📡 Injected telemetry for ${latest.id.slice(0,8)}`, "user");
      const resp = await api("/v1/chat/", { method: "POST", body: JSON.stringify({ message: payload }) });
      addMessage(resp.reply || "…", "bot");
    } catch (e) {
      addMessage(`Error injecting telemetry: ${e.message}`, "bot");
    }
  };

  return container;
}

// ==== GOSSIPMESH TAB ========================================================
async function renderGossip() {
  const container = document.createElement("div");
  container.className = "p-4 space-y-4";
  const title = document.createElement("h2");
  title.textContent = "GossipMesh Sandbox Status";
  title.className = "text-lg font-medium";
  container.appendChild(title);
  const statusDiv = document.createElement("div");
  statusDiv.textContent = "Loading…";
  container.appendChild(statusDiv);
  try {
    const data = await api("/v1/gossip/status");
    statusDiv.innerHTML = `
      <p><strong>PR Status:</strong> ${data.pr_status || "N/A"}</p>
      <p><strong>rate_limits_saved_total:</strong> ${data.metrics?.rate_limits_saved_total ?? "—"}</p>
    `;
  } catch (e) {
    statusDiv.textContent = `Error: ${e.message}`;
  }
  return container;
}

// ==== BILLING TAB ===========================================================
async function renderBilling() {
  const container = document.createElement("div");
  container.className = "p-4 space-y-4";
  const title = document.createElement("h2");
  title.textContent = "Billing & Credits";
  title.className = "text-lg font-medium";
  container.appendChild(title);

  const token = getStoredToken();
  if (!token) {
    // Show login form
    const loginDiv = document.createElement("div");
    const emailInput = document.createElement("input");
    emailInput.type = "email";
    emailInput.placeholder = "Email";
    emailInput.className = "p-2 border rounded w-full mb-2";
    const passwordInput = document.createElement("input");
    passwordInput.type = "password";
    passwordInput.placeholder = "Password";
    passwordInput.className = "p-2 border rounded w-full mb-2";
    const loginBtn = document.createElement("button");
    loginBtn.textContent = "Login";
    loginBtn.className = "px-4 py-2 bg-green-600 text-white rounded";
    loginBtn.onclick = async () => {
      loginBtn.disabled = true;
      try {
        const resp = await api("/v1/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: emailInput.value, password: passwordInput.value }),
        });
        // Expect response { token: "..." }
        setStoredToken(resp.token);
        renderApp(); // re‑render now that we have a token
      } catch (e) {
        alert(`Login failed: ${e.message}`);
      } finally {
        loginBtn.disabled = false;
      }
    };
    loginDiv.append(emailInput, passwordInput, loginBtn);
    container.appendChild(loginDiv);
    return container;
  }

  // Authenticated: show plan, credits, usage, upgrade link, logout
  const planDiv = document.createElement("div");
  const creditsDiv = document.createElement("div");
  const usageDiv = document.createElement("div");
  container.append(planDiv, creditsDiv, usageDiv);

  try {
    const planInfo = await api("/v1/billing/plan"); // { name, price, quota }
    planDiv.innerHTML = `<p><strong>Current Plan:</strong> ${planInfo.name} – $${planInfo.price}/mo (Quota: ${planInfo.quota} units)</p>`;
    const creditsInfo = await api("/v1/billing/credits"); // { remaining, total }
    creditsDiv.innerHTML = `<p><strong>Credits:</strong> ${creditsInfo.remaining} / ${creditsInfo.total}</p>`;
    const usageInfo = await api("/v1/metrics/usage"); // custom endpoint – adjust as needed
    usageDiv.innerHTML = `<p><strong>Usage this month:</strong> ${usageInfo.used} units</p>`;
  } catch (e) {
    container.appendChild(document.createTextNode(`Error retrieving billing data: ${e.message}`));
  }

  const actionsDiv = document.createElement("div");
  actionsDiv.className = "mt-4 flex space-x-2";
  const upgradeBtn = document.createElement("button");
  upgradeBtn.textContent = "Upgrade Plan";
  upgradeBtn.className = "px-4 py-2 bg-blue-600 text-white rounded";
  upgradeBtn.onclick = () => {
    // Open Stripe Checkout – backend should provide a hosted URL
    api("/v1/billing/checkout", { method: "POST" }).then((url) => {
      // Open in external browser – VS Code webview can't navigate, so postMessage to extension
      vscode.postMessage({ type: "openUrl", url });
    }).catch((e) => alert(`Checkout error: ${e.message}`));
  };
  const logoutBtn = document.createElement("button");
  logoutBtn.textContent = "Logout";
  logoutBtn.className = "px-4 py-2 bg-gray-600 text-white rounded";
  logoutBtn.onclick = () => { clearStoredToken(); renderApp(); };
  actionsDiv.append(upgradeBtn, logoutBtn);
  container.appendChild(actionsDiv);
  return container;
}

// ==== SETTINGS TAB ==========================================================
async function renderSettings() {
  const container = document.createElement("div");
  container.className = "p-4 space-y-4";
  const title = document.createElement("h2");
  title.textContent = "Organization Settings";
  title.className = "text-lg font-medium";
  container.appendChild(title);
  let org;
  try {
    const orgs = await api("/admin/orgs");
    org = orgs?.[0] ?? null;
  } catch (e) {
    container.appendChild(document.createTextNode(`Error loading orgs: ${e.message}`));
    return container;
  }
  const tokenLabel = document.createElement("label");
  tokenLabel.textContent = "Org Token (skl_live_…)";
  tokenLabel.className = "block font-medium";
  const tokenInput = document.createElement("input");
  tokenInput.type = "text";
  tokenInput.value = org?.token ?? "";
  tokenInput.className = "w-full p-2 border rounded";
  const saveBtn = document.createElement("button");
  saveBtn.textContent = "Save Settings";
  saveBtn.className = "mt-2 px-3 py-1 bg-green-600 text-white rounded";
  saveBtn.onclick = async () => {
    try {
      await api(`/admin/orgs/${org.id}`, { method: "PUT", body: JSON.stringify({ token: tokenInput.value.trim() }) });
      alert("Settings saved.");
    } catch (e) {
      alert(`Save failed: ${e.message}`);
    }
  };
  container.append(tokenLabel, tokenInput, saveBtn);
  return container;
}

// ==== MAIN RENDERER =========================================================
function renderApp() {
  const root = document.getElementById("root");
  root.innerHTML = "";
  root.appendChild(renderTabs(currentTab));
  const contentDiv = document.createElement("div");
  contentDiv.className = "h-[calc(100%-2.5rem)] overflow-auto";
  switch (currentTab) {
    case "incidents":
      contentDiv.appendChild(renderIncidents());
      break;
    case "chat":
      contentDiv.appendChild(renderChat());
      break;
    case "gossip":
      contentDiv.appendChild(renderGossip());
      break;
    case "billing":
      contentDiv.appendChild(renderBilling());
      break;
    case "settings":
      contentDiv.appendChild(renderSettings());
      break;
  }
  root.appendChild(contentDiv);
}

// Initial render
renderApp();

// Listen for messages from extension (e.g., token persisted externally)
window.addEventListener("message", (event) => {
  const msg = event.data;
  if (msg.type === "tokenUpdated") {
    setStoredToken(msg.token);
    renderApp();
  }
});
