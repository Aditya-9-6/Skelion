import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Dashboard state
  const [dashboardData, setDashboardData] = useState(null);
  
  // Org search state
  const [searchQuery, setSearchQuery] = useState('');
  const [orgResults, setOrgResults] = useState([]);
  
  // Audit log state
  const [auditLogs, setAuditLogs] = useState([]);
  
  // Step-up modal state
  const [showStepUpModal, setShowStepUpModal] = useState(false);
  const [totpCode, setTotpCode] = useState('');
  const [stepUpError, setStepUpError] = useState('');
  const [pendingAction, setPendingAction] = useState(null);

  // Write action form states
  const [actionMessage, setActionMessage] = useState('');
  const [creditForm, setCreditForm] = useState({ user_id: '00000000-0000-0000-0000-000000000001', amount: 100, reason: 'Grant bonus credits' });
  const [adjustForm, setAdjustForm] = useState({ user_id: '00000000-0000-0000-0000-000000000001', delta: 50, reason: 'Adjustment' });
  const [tierForm, setTierForm] = useState({ user_id: '00000000-0000-0000-0000-000000000001', new_tier: 'enterprise', reason: 'Upgrade plan' });
  const [reconcileForm, setReconcileForm] = useState({ order_id: '00000000-0000-0000-0000-000000000002', reason: 'Manual reconcile' });
  const [refundForm, setRefundForm] = useState({ order_id: '00000000-0000-0000-0000-000000000002', amount: 500, reason: 'Customer refund' });
  const [killForm, setKillForm] = useState({ name: 'emergency_switch', enable: true, reason: 'Security incident' });

  // Check authentication & fetch dashboard
  const fetchDashboard = async () => {
    try {
      const res = await fetch('/dashboard', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setDashboardData(data);
        setSession(data);
      } else {
        setSession(null);
      }
    } catch (err) {
      setSession(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  // Fetch audit logs when tab selected
  useEffect(() => {
    if (activeTab === 'audit' && session) {
      fetch('/audit', { credentials: 'include' })
        .then(r => r.json())
        .then(data => setAuditLogs(data.audit || []))
        .catch(() => setAuditLogs([]));
    }
  }, [activeTab, session]);

  const handleLogin = () => {
    window.location.href = '/auth/github';
  };

  const handleOrgSearch = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`/orgs/search?q=${encodeURIComponent(searchQuery)}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setOrgResults(data.results || []);
      }
    } catch (err) {
      setOrgResults([]);
    }
  };

  const executeWriteAction = async (endpoint, bodyData) => {
    setActionMessage('');
    const idempotencyKey = crypto.randomUUID();
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify(bodyData),
        credentials: 'include',
      });

      if (res.status === 403) {
        // Step-up required! Open step-up modal
        setShowStepUpModal(true);
        setPendingAction({ endpoint, bodyData });
        setActionMessage('Step-up authentication required (403). Please verify 2FA.');
        return;
      }

      const data = await res.json();
      if (res.ok) {
        setActionMessage(`Action successful! Audit ID: ${data.audit_id || 'N/A'}`);
      } else {
        setActionMessage(data.detail || 'Action failed');
      }
    } catch (err) {
      setActionMessage('Network error during action execution');
    }
  };

  const handleVerifyStepUp = async (e) => {
    e.preventDefault();
    setStepUpError('');
    try {
      const res = await fetch('/factor/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ factor_type: 'totp', code: totpCode }),
        credentials: 'include',
      });
      const data = await res.json();
      if (res.ok) {
        // Store token in cookie/state if returned
        if (data.token) {
          document.cookie = `admin_step_up=${data.token}; path=/; max-age=900; samesite=lax`;
        }
        setShowStepUpModal(false);
        setTotpCode('');
        setActionMessage('Step-up verified successfully. You may retry your action.');
        if (pendingAction) {
          const { endpoint, bodyData } = pendingAction;
          setPendingAction(null);
          executeWriteAction(endpoint, bodyData);
        }
      } else {
        setStepUpError(data.detail || 'Verification failed');
      }
    } catch (err) {
      setStepUpError('Verification network error');
    }
  };

  if (loading) {
    return <div className="loading">Loading Skelion Admin Dashboard...</div>;
  }

  if (!session) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h1>Skelion Admin Panel</h1>
          <p>Secure owner authentication required via GitHub OAuth and Cloudflare Access.</p>
          <button className="btn-primary" onClick={handleLogin}>
            Login with GitHub
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-layout">
      <header className="navbar">
        <div className="brand">
          <span className="logo">🛡️</span>
          <h2>Skelion Admin Dashboard</h2>
          <span className="badge">Owner</span>
        </div>
        <div className="user-info">
          <span>GitHub ID: {session.github_user_id}</span>
          <button className="btn-outline" onClick={() => { setSession(null); window.location.href = '/'; }}>Logout</button>
        </div>
      </header>

      <nav className="tabs">
        <button className={activeTab === 'dashboard' ? 'tab active' : 'tab'} onClick={() => setActiveTab('dashboard')}>Dashboard & KPIs</button>
        <button className={activeTab === 'orgs' ? 'tab active' : 'tab'} onClick={() => setActiveTab('orgs')}>Organization Profile</button>
        <button className={activeTab === 'audit' ? 'tab active' : 'tab'} onClick={() => setActiveTab('audit')}>Audit Log Viewer</button>
        <button className={activeTab === 'actions' ? 'tab active' : 'tab'} onClick={() => setActiveTab('actions')}>Write Actions</button>
      </nav>

      <main className="content">
        {activeTab === 'dashboard' && (
          <div className="panel">
            <h3>System Key Performance Indicators (KPIs)</h3>
            <div className="kpi-grid">
              <div className="kpi-card">
                <h4>Monthly Recurring Revenue (MRR)</h4>
                <p className="kpi-value">${dashboardData?.kpis?.mrr || 0}</p>
              </div>
              <div className="kpi-card">
                <h4>Active Organizations</h4>
                <p className="kpi-value">{dashboardData?.kpis?.active_orgs || 0}</p>
              </div>
              <div className="kpi-card">
                <h4>Failed Payments</h4>
                <p className="kpi-value">{dashboardData?.kpis?.failed_payments || 0}</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'orgs' && (
          <div className="panel">
            <h3>Organization Profile Search</h3>
            <form onSubmit={handleOrgSearch} className="search-form">
              <input
                type="text"
                placeholder="Search repository or organization full name..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              <button type="submit" className="btn-primary">Search</button>
            </form>
            <div className="results-list">
              {orgResults.map((org, i) => (
                <div key={i} className="result-item">
                  <strong>{org.full_name || org.name}</strong> (ID: {org.id})
                </div>
              ))}
              {orgResults.length === 0 && <p className="muted">No organizations found.</p>}
            </div>
          </div>
        )}

        {activeTab === 'audit' && (
          <div className="panel">
            <h3>Immutable Audit Log Viewer</h3>
            <div className="table-responsive">
              <table className="audit-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Actor (GH ID)</th>
                    <th>Action</th>
                    <th>Target Type</th>
                    <th>Target ID</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((log, i) => (
                    <tr key={i}>
                      <td>{log.ts}</td>
                      <td>{log.actor_github_id}</td>
                      <td><code>{log.action}</code></td>
                      <td>{log.target_type}</td>
                      <td>{log.target_id || '-'}</td>
                      <td>{log.reason}</td>
                    </tr>
                  ))}
                  {auditLogs.length === 0 && (
                    <tr><td colSpan="6" className="muted">No audit logs recorded yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'actions' && (
          <div className="panel">
            <h3>Administrative Write Actions (Idempotent & Step-Up Protected)</h3>
            {actionMessage && <div className="alert">{actionMessage}</div>}

            <div className="actions-grid">
              {/* Grant Credits */}
              <div className="action-card">
                <h4>Grant Credits</h4>
                <input type="text" placeholder="User ID" value={creditForm.user_id} onChange={e => setCreditForm({...creditForm, user_id: e.target.value})} />
                <input type="number" placeholder="Amount" value={creditForm.amount} onChange={e => setCreditForm({...creditForm, amount: Number(e.target.value)})} />
                <input type="text" placeholder="Reason" value={creditForm.reason} onChange={e => setCreditForm({...creditForm, reason: e.target.value})} />
                <button className="btn-action" onClick={() => executeWriteAction('/credits/grant', creditForm)}>Grant Credits</button>
              </div>

              {/* Adjust Credits */}
              <div className="action-card">
                <h4>Adjust Credits</h4>
                <input type="text" placeholder="User ID" value={adjustForm.user_id} onChange={e => setAdjustForm({...adjustForm, user_id: e.target.value})} />
                <input type="number" placeholder="Delta (+/-)" value={adjustForm.delta} onChange={e => setAdjustForm({...adjustForm, delta: Number(e.target.value)})} />
                <input type="text" placeholder="Reason" value={adjustForm.reason} onChange={e => setAdjustForm({...adjustForm, reason: e.target.value})} />
                <button className="btn-action" onClick={() => executeWriteAction('/credits/adjust', adjustForm)}>Adjust Credits</button>
              </div>

              {/* Change Tier */}
              <div className="action-card">
                <h4>Change Tier</h4>
                <input type="text" placeholder="User ID" value={tierForm.user_id} onChange={e => setTierForm({...tierForm, user_id: e.target.value})} />
                <input type="text" placeholder="New Tier (basic/enterprise)" value={tierForm.new_tier} onChange={e => setTierForm({...tierForm, new_tier: e.target.value})} />
                <input type="text" placeholder="Reason" value={tierForm.reason} onChange={e => setTierForm({...tierForm, reason: e.target.value})} />
                <button className="btn-action" onClick={() => executeWriteAction('/tier/change', tierForm)}>Change Tier</button>
              </div>

              {/* Order Reconcile */}
              <div className="action-card">
                <h4>Order Reconcile</h4>
                <input type="text" placeholder="Order ID" value={reconcileForm.order_id} onChange={e => setReconcileForm({...reconcileForm, order_id: e.target.value})} />
                <input type="text" placeholder="Reason" value={reconcileForm.reason} onChange={e => setReconcileForm({...reconcileForm, reason: e.target.value})} />
                <button className="btn-action" onClick={() => executeWriteAction('/order/reconcile', reconcileForm)}>Reconcile Order</button>
              </div>

              {/* Refund Payment */}
              <div className="action-card">
                <h4>Refund Payment</h4>
                <input type="text" placeholder="Order ID" value={refundForm.order_id} onChange={e => setRefundForm({...refundForm, order_id: e.target.value})} />
                <input type="number" placeholder="Amount" value={refundForm.amount} onChange={e => setRefundForm({...refundForm, amount: Number(e.target.value)})} />
                <input type="text" placeholder="Reason" value={refundForm.reason} onChange={e => setRefundForm({...refundForm, reason: e.target.value})} />
                <button className="btn-action" onClick={() => executeWriteAction('/payment/refund', refundForm)}>Refund Payment</button>
              </div>

              {/* Kill Switch Toggle */}
              <div className="action-card">
                <h4>Kill Switch Toggle</h4>
                <input type="text" placeholder="Switch Name" value={killForm.name} onChange={e => setKillForm({...killForm, name: e.target.value})} />
                <label className="checkbox-label">
                  <input type="checkbox" checked={killForm.enable} onChange={e => setKillForm({...killForm, enable: e.target.checked})} />
                  Enable Switch
                </label>
                <input type="text" placeholder="Reason" value={killForm.reason} onChange={e => setKillForm({...killForm, reason: e.target.value})} />
                <button className="btn-action danger" onClick={() => executeWriteAction('/kill-switch/toggle', killForm)}>Toggle Kill Switch</button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Step-up Modal */}
      {showStepUpModal && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>🔒 Step-up Authentication Required</h3>
            <p>Mutating admin operations require 2FA verification (TOTP or Passkey).</p>
            <form onSubmit={handleVerifyStepUp}>
              <input
                type="text"
                placeholder="Enter 6-digit TOTP code"
                value={totpCode}
                onChange={e => setTotpCode(e.target.value)}
                maxLength={6}
                required
              />
              {stepUpError && <p className="error">{stepUpError}</p>}
              <div className="modal-actions">
                <button type="submit" className="btn-primary">Verify & Authorize</button>
                <button type="button" className="btn-outline" onClick={() => setShowStepUpModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
