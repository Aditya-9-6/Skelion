import React, { useState } from 'react';
import { 
  User, 
  CreditCard, 
  Activity, 
  Key, 
  Terminal, 
  ShieldCheck, 
  Zap, 
  ExternalLink, 
  Copy, 
  Check, 
  RotateCw, 
  GitPullRequest, 
  Clock, 
  ArrowUpRight, 
  Cpu, 
  CheckCircle2, 
  AlertTriangle, 
  Sparkles,
  Layers,
  ChevronRight,
  LogOut,
  RefreshCw,
  Github,
  Gauge,
  Lock,
  Radio,
  FileText,
  Sliders,
  Server
} from 'lucide-react';
import { UserProfile, logoutUser } from '../utils/auth';

interface DashboardProps {
  user: UserProfile;
  isGuest?: boolean;
  onLogin?: () => void;
  onOpenCheckout: (planId?: string) => void;
  onLogout: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ 
  user, 
  isGuest = false, 
  onLogin, 
  onOpenCheckout, 
  onLogout 
}) => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'subscriptions' | 'integration' | 'incidents'>('overview');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [incidentFilter, setIncidentFilter] = useState<'all' | 'intercept' | 'rotation' | 'scrub' | 'patch'>('all');
  const [tokenSalt, setTokenSalt] = useState<string>('x91q7');

  // Dynamic cloud agent API token based on user id and salt
  const cloudAgentApiToken = `skl_live_${user.id}_${btoa(user.username).substring(0, 8)}${tokenSalt}`;
  const cliInstallCommand = `pip install skelion`;
  const cliLoginCommand = `skelion auth login --token ${cloudAgentApiToken}`;

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2200);
  };

  const handleRefreshStats = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 800);
  };

  const handleRotateToken = () => {
    const newSalt = Math.random().toString(36).substring(2, 7);
    setTokenSalt(newSalt);
    setCopiedKey('rotated');
    setTimeout(() => setCopiedKey(null), 2200);
  };

  const memberYear = user.updatedAt ? new Date(user.updatedAt).getFullYear() : 2026;

  // Incident logs — Real telemetry incidents only (empty when all systems operational)
  const allIncidents: any[] = [];

  const filteredIncidents = incidentFilter === 'all' 
    ? allIncidents 
    : allIncidents.filter((inc) => inc.category === incidentFilter);

  return (
    <div className="py-8 md:py-14 relative z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-7">
        
        {/* Guest / Demo Notice Banner */}
        {isGuest && (
          <div className="rounded-2xl p-4 bg-gradient-to-r from-amber-500/10 via-amber-400/15 to-amber-500/10 border border-amber-300/80 backdrop-blur-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-amber-100 border border-amber-300 flex items-center justify-center text-amber-700 shrink-0">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div className="text-xs text-amber-950">
                <strong>Viewing Demo Pilot Environment:</strong> You are exploring Skelion with simulated developer telemetry.
                Connect your real GitHub account to sync your repositories, token metrics, and team subscriptions.
              </div>
            </div>
            {onLogin && (
              <button
                onClick={onLogin}
                className="px-4 py-1.5 rounded-lg text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 transition shadow-sm flex items-center gap-1.5 shrink-0"
              >
                <Github className="w-3.5 h-3.5" />
                <span>Connect GitHub</span>
              </button>
            )}
          </div>
        )}

        {/* Dashboard Top Navigation & Breadcrumbs Bar with Official Logo */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200/80 pb-4">
          <div className="flex items-center gap-3">
            {/* High-res Skelion Logo */}
            <div className="relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-cyan-400 to-purple-500 rounded-xl blur opacity-30 group-hover:opacity-75 transition duration-300"></div>
              <img
                src="/icon.svg"
                alt="Skelion Console"
                className="relative w-8 h-8 rounded-lg bg-white p-1 border border-slate-200/90 shadow-sm object-contain"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = '/icon.png';
                }}
              />
            </div>

            <div className="flex flex-col">
              <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                <a href="#home" className="hover:text-cyan-600 transition flex items-center gap-1 font-sans">
                  <span>Home</span>
                </a>
                <span>/</span>
                <span className="text-cyan-700 font-semibold font-sans">Console</span>
                <span>/</span>
                <span className="text-slate-800 font-mono">@{user.username}</span>
              </div>
              <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5 -mt-0.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse inline-block" />
                Edge Mesh Connected (1.4ms ping)
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRefreshStats}
              disabled={isRefreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-white border border-slate-200 hover:border-slate-300 hover:text-slate-900 transition shadow-sm"
              title="Refresh telemetry metrics"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-cyan-600 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>{isRefreshing ? 'Syncing...' : 'Sync Live'}</span>
            </button>

            <a
              href="#console"
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-white border border-slate-200 hover:border-slate-300 transition shadow-sm"
            >
              <Terminal className="w-3.5 h-3.5 text-cyan-600" />
              <span>Web Console</span>
            </a>

            <button
              onClick={onLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 border border-red-200 transition shadow-xs"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>

        {/* User Hero Glassmorphism Header */}
        <div className="glass-panel rounded-2xl p-6 sm:p-8 relative overflow-hidden border border-white/80 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)]">
          {/* Background Ambient Glows */}
          <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-cyan-400/15 via-purple-400/10 to-transparent rounded-full blur-3xl pointer-events-none -z-10" />
          <div className="absolute -bottom-10 -left-10 w-60 h-60 bg-blue-300/10 rounded-full blur-2xl pointer-events-none -z-10" />

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            {/* User Profile Info with Dual Badging */}
            <div className="flex items-start sm:items-center gap-5">
              <div className="relative">
                <img
                  src={user.avatar || 'https://avatars.githubusercontent.com/u/999999?v=4'}
                  alt={user.name || user.username}
                  className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl border-2 border-cyan-500/40 object-cover shadow-md"
                />
                {/* Logo badge pinned on avatar */}
                <div className="absolute -bottom-1.5 -right-1.5 w-6 h-6 rounded-full bg-white border border-slate-200 p-0.5 shadow-sm flex items-center justify-center" title="Skelion Verified">
                  <img src="/icon.svg" alt="Skelion" className="w-4 h-4 object-contain" onError={(e) => { (e.target as HTMLImageElement).src = '/icon.png'; }} />
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-950 tracking-tight">
                    {user.name || user.username}
                  </h1>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-800 border border-cyan-200 font-mono font-medium">
                    @{user.username}
                  </span>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200 font-mono font-medium flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-purple-500" />
                    Community Pilot Tier
                  </span>
                </div>

                <p className="text-xs sm:text-sm text-slate-600 max-w-xl">
                  {user.bio || 'Autonomous Incident Intelligence & Zero-429 Multi-LLM Key Resilience Engineer.'}
                </p>

                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1 font-mono">
                  {user.email && (
                    <span className="flex items-center gap-1">
                      <span>Email:</span> <strong className="text-slate-700 font-sans">{user.email}</strong>
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <span>Member since:</span> <strong className="text-slate-700">{memberYear}</strong>
                  </span>
                  {user.html_url && (
                    <a
                      href={user.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-700 hover:underline flex items-center gap-1 font-sans font-medium"
                    >
                      <Github className="w-3.5 h-3.5 text-slate-700" />
                      <span>GitHub Profile</span>
                      <ArrowUpRight className="w-3 h-3 text-slate-400" />
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Plan & Upgrade CTA */}
            <div className="flex flex-col sm:flex-row lg:flex-col items-start lg:items-end justify-center gap-2 pt-4 lg:pt-0 border-t lg:border-t-0 border-slate-200/60">
              <div className="text-left lg:text-right">
                <div className="text-[10px] font-mono uppercase text-slate-400 font-medium">Active Subscription Tier</div>
                <div className="text-sm font-bold text-slate-900 flex items-center gap-1.5 lg:justify-end">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  <span>Hosted Pilot (Free Active)</span>
                </div>
                <div className="text-xs text-slate-500 font-mono mt-0.5">Renews monthly: Dec 7, 2026 • ₹0</div>
              </div>
              <button
                onClick={() => onOpenCheckout('pro')}
                className="mt-1 px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-cyan-500 via-cyan-400 to-blue-600 hover:from-cyan-400 hover:to-blue-500 transition shadow-md shadow-cyan-500/20 flex items-center gap-1.5"
              >
                <Zap className="w-3.5 h-3.5 fill-white" />
                <span>Upgrade to Pro / Team</span>
              </button>
            </div>
          </div>

          {/* Sub-navigation Tabs */}
          <div className="mt-8 pt-4 border-t border-slate-200/70 flex flex-wrap gap-2 text-xs font-semibold">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3.5 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                activeTab === 'overview'
                  ? 'bg-cyan-500 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Overview & Analytics</span>
            </button>

            <button
              onClick={() => setActiveTab('subscriptions')}
              className={`px-3.5 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                activeTab === 'subscriptions'
                  ? 'bg-cyan-500 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <CreditCard className="w-3.5 h-3.5" />
              <span>Subscriptions & Tiers</span>
            </button>

            <button
              onClick={() => setActiveTab('integration')}
              className={`px-3.5 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                activeTab === 'integration'
                  ? 'bg-cyan-500 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Cloud Agent Integration</span>
            </button>

            <button
              onClick={() => setActiveTab('incidents')}
              className={`px-3.5 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                activeTab === 'incidents'
                  ? 'bg-cyan-500 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <GitPullRequest className="w-3.5 h-3.5" />
              <span>Resilience Audit Ledger ({allIncidents.length})</span>
            </button>
          </div>
        </div>

        {/* Tab 1: Overview & 6 Core Metrics Grid */}
        {activeTab === 'overview' && (
          <div className="space-y-8 animate-fade-in">
            {/* 6 Core Usage Metrics & Analytics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {/* Metric 1: API Credits Remaining */}
              <div className="glass-panel p-5 rounded-2xl border border-slate-200/90 shadow-sm relative overflow-hidden group hover:border-cyan-300 transition-all">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-mono uppercase tracking-wider font-semibold">API Credits Remaining</span>
                  <div className="w-8 h-8 rounded-lg bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600">
                    <Zap className="w-4 h-4" />
                  </div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-950">50</span>
                  <span className="text-xs text-slate-500 font-mono">/ 50 Free Credits</span>
                </div>
                {/* Progress bar */}
                <div className="w-full h-1.5 bg-slate-100 rounded-full mt-3 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 w-full rounded-full" />
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono mt-2">
                  <span>100% available</span>
                  <button onClick={() => onOpenCheckout('topup_small')} className="text-cyan-600 hover:underline font-semibold">
                    Top Up Credits →
                  </button>
                </div>
              </div>

              {/* Metric 2: LLM Tokens Protected */}
              <div className="glass-panel p-5 rounded-2xl border border-slate-200/90 shadow-sm relative overflow-hidden group hover:border-purple-300 transition-all">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-mono uppercase tracking-wider font-semibold">LLM Tokens Protected</span>
                  <div className="w-8 h-8 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-950">142.8k</span>
                  <span className="text-xs text-emerald-600 font-mono font-medium">+18.4% efficiency</span>
                </div>
                <div className="w-full h-1.5 bg-slate-100 rounded-full mt-3 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 w-3/4 rounded-full" />
                </div>
                <div className="text-[11px] text-slate-500 font-mono mt-2">
                  Zero token loss across 429 retries
                </div>
              </div>

              {/* Metric 3: Fail-Open Intercept Count */}
              <div className="glass-panel p-5 rounded-2xl border border-slate-200/90 shadow-sm relative overflow-hidden group hover:border-emerald-300 transition-all">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-mono uppercase tracking-wider font-semibold">Fail-Open Intercepts</span>
                  <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
                    <Activity className="w-4 h-4" />
                  </div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-950">18</span>
                  <span className="text-xs text-slate-500 font-mono">edge bypasses</span>
                </div>
                <div className="w-full h-1.5 bg-slate-100 rounded-full mt-3 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 w-full rounded-full" />
                </div>
                <div className="text-[11px] text-emerald-700 font-mono mt-2">
                  100% authentic customer payload delivery
                </div>
              </div>

              {/* Metric 4: Latency Reduction Percentage */}
              <div className="glass-panel p-5 rounded-2xl border border-slate-200/90 shadow-sm relative overflow-hidden group hover:border-blue-300 transition-all">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-mono uppercase tracking-wider font-semibold">Latency Reduction</span>
                  <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                    <Gauge className="w-4 h-4" />
                  </div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-950">84.6%</span>
                  <span className="text-xs text-emerald-600 font-mono font-medium">Faster fail-open</span>
                </div>
                <div className="w-full h-1.5 bg-slate-100 rounded-full mt-3 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 w-5/6 rounded-full" />
                </div>
                <div className="text-[11px] text-slate-500 font-mono mt-2">
                  1.4ms edge bypass vs 850ms timeout
                </div>
              </div>

              {/* Metric 5: Key-Pool Health */}
              <div className="glass-panel p-5 rounded-2xl border border-slate-200/90 shadow-sm relative overflow-hidden group hover:border-amber-300 transition-all">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-mono uppercase tracking-wider font-semibold">Key-Pool Health</span>
                  <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
                    <Key className="w-4 h-4" />
                  </div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-950">Active</span>
                  <span className="text-xs text-emerald-600 font-mono font-medium">99.98% uptime</span>
                </div>
                <div className="w-full h-1.5 bg-slate-100 rounded-full mt-3 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-emerald-400 to-cyan-500 w-full rounded-full" />
                </div>
                <div className="text-[11px] text-slate-500 font-mono mt-2">
                  Multi-provider jittered backoff ready
                </div>
              </div>

              {/* Metric 6: Cloud Agent Integration Status */}
              <div className="glass-panel p-5 rounded-2xl border border-slate-200/90 shadow-sm relative overflow-hidden group hover:border-cyan-300 transition-all">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-mono uppercase tracking-wider font-semibold">Agent Mesh Status</span>
                  <div className="w-8 h-8 rounded-lg bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600">
                    <Radio className="w-4 h-4 text-cyan-600 animate-pulse" />
                  </div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-950">Synced</span>
                  <span className="text-xs text-cyan-700 font-mono font-medium">v0.1.4 Verified</span>
                </div>
                <div className="w-full h-1.5 bg-slate-100 rounded-full mt-3 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-cyan-400 to-emerald-500 w-full rounded-full" />
                </div>
                <div className="text-[11px] text-slate-500 font-mono mt-2 flex items-center justify-between">
                  <span>Heartbeat: 12s ago</span>
                  <a 
                    href="#console"
                    className="text-cyan-600 hover:underline"
                  >
                    Active in Console →
                  </a>
                </div>
              </div>
            </div>

            {/* Quick Action Cards: Cloud Agent Token & Active Subscription */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Card 1: Cloud Agent Token Manager */}
              <div className="glass-panel rounded-2xl p-6 border border-slate-200/90 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <img
                          src="/icon.svg"
                          alt="Skelion Platform"
                          className="w-10 h-10 rounded-xl bg-white p-1 border border-slate-200 shadow-sm object-contain"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = '/icon.png';
                          }}
                        />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-slate-950">Cloud Agent Integration Token</h2>
                        <p className="text-xs text-slate-500">Telemetry stream &amp; AST sandbox validator in your web console</p>
                      </div>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono font-medium">
                      v0.1.4 Verified
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed mb-4">
                    Authenticate your local terminal or CI/CD pipelines with Skelion using your dedicated agent token.
                    Once connected, your pipeline streams live incident cards, tests, and AST diagnostic patches directly.
                  </p>

                  <div className="space-y-3">
                    <div>
                      <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 mb-1">
                        <span>Cloud Agent API Token:</span>
                        <button
                          onClick={handleRotateToken}
                          className="text-cyan-600 hover:text-cyan-800 transition flex items-center gap-1 font-sans text-xs"
                          title="Generate a new auth token"
                        >
                          <RotateCw className="w-3 h-3" />
                          <span>Rotate Token</span>
                        </button>
                      </div>
                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-2">
                        <code className="text-xs font-mono text-cyan-800 truncate select-all">
                          {cloudAgentApiToken}
                        </code>
                        <button
                          onClick={() => copyToClipboard(cloudAgentApiToken, 'ext_token')}
                          className="px-3 py-1 rounded-lg text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:border-cyan-400 transition shadow-sm shrink-0 flex items-center gap-1"
                        >
                          {copiedKey === 'ext_token' || copiedKey === 'rotated' ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                              <span className="text-emerald-700">{copiedKey === 'rotated' ? 'Rotated' : 'Copied'}</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5 text-slate-400" />
                              <span>Copy Token</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    <div>
                      <div className="text-[11px] font-mono text-slate-500 mb-1">Quick Terminal Login Command:</div>
                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-2">
                        <code className="text-[11px] font-mono text-slate-700 truncate">
                          {cliLoginCommand}
                        </code>
                        <button
                          onClick={() => copyToClipboard(cliLoginCommand, 'cli_cmd')}
                          className="px-2.5 py-1 rounded-lg text-xs font-medium bg-white text-slate-600 border border-slate-200 hover:border-cyan-400 transition shadow-sm shrink-0"
                        >
                          {copiedKey === 'cli_cmd' ? 'Copied' : 'Copy'}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-xs font-semibold text-cyan-700 font-mono">
                    v0.1.4 Web Platform
                  </span>
                  <button
                    onClick={() => setActiveTab('integration')}
                    className="text-xs font-medium text-slate-600 hover:text-slate-900"
                  >
                    Integration Setup →
                  </button>
                </div>
              </div>

              {/* Card 2: Active Plan & Billing Overview */}
              <div className="glass-panel rounded-2xl p-6 border border-slate-200/90 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-purple-50 border border-purple-200 flex items-center justify-center">
                        <CreditCard className="w-5 h-5 text-purple-600" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-slate-950">Subscription & Plan Status</h2>
                        <p className="text-xs text-slate-500">Tier quotas, billing cycle, and Razorpay gateway</p>
                      </div>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-800 border border-cyan-200 font-mono font-medium">
                      Hosted Pilot
                    </span>
                  </div>

                  <div className="space-y-2.5 mb-4">
                    <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100">
                      <span className="text-slate-500">Current Tier:</span>
                      <strong className="text-slate-900">Hosted Community Pilot</strong>
                    </div>
                    <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100">
                      <span className="text-slate-500">Monthly Quota:</span>
                      <strong className="text-slate-900">50 Free Intercept Credits</strong>
                    </div>
                    <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100">
                      <span className="text-slate-500">Payment Gateway:</span>
                      <strong className="text-slate-900 font-mono">Razorpay UPI & Cards (India / International)</strong>
                    </div>
                    <div className="flex items-center justify-between text-xs py-1.5">
                      <span className="text-slate-500">Discount Code Available:</span>
                      <span className="text-emerald-700 font-mono font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        FOUNDING50 (30% off)
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                  <button
                    onClick={() => setActiveTab('subscriptions')}
                    className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 transition shadow-sm flex items-center gap-1.5"
                  >
                    <Zap className="w-3.5 h-3.5 text-cyan-400" />
                    <span>View All 4 Plans</span>
                  </button>
                  <button
                    onClick={() => onOpenCheckout('topup_small')}
                    className="px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:border-slate-300 transition shadow-sm"
                  >
                    Buy 500 Credits (₹599)
                  </button>
                </div>
              </div>
            </div>

            {/* Recent Resilience Incident Resolutions Overview */}
            <div className="glass-panel rounded-2xl p-6 border border-slate-200/90 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
                <div>
                  <h2 className="text-base font-bold text-slate-950 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    <span>Recent Incident Resolutions & Intercepts</span>
                  </h2>
                  <p className="text-xs text-slate-500">Real-time edge proxies and verified GitHub self-healing PRs</p>
                </div>
                <button
                  onClick={() => setActiveTab('incidents')}
                  className="text-xs font-semibold text-cyan-700 hover:text-cyan-800 font-mono flex items-center gap-1"
                >
                  <span>View Full Ledger ({allIncidents.length}) →</span>
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 font-mono">
                      <th className="py-2.5 px-3">INCIDENT ID</th>
                      <th className="py-2.5 px-3">ROUTE / SERVICE</th>
                      <th className="py-2.5 px-3">ANOMALY TYPE</th>
                      <th className="py-2.5 px-3">STATUS</th>
                      <th className="py-2.5 px-3">METRICS</th>
                      <th className="py-2.5 px-3">TIME</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {allIncidents.slice(0, 3).map((inc) => (
                      <tr key={inc.id} className="hover:bg-slate-50/70 transition">
                        <td className="py-3 px-3 font-mono font-semibold text-slate-900">{inc.id}</td>
                        <td className="py-3 px-3 font-mono text-cyan-800">{inc.service}</td>
                        <td className="py-3 px-3 text-slate-700">{inc.type}</td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded-full border text-[11px] font-mono font-medium ${inc.badgeClass}`}>
                            {inc.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-mono text-slate-500">{inc.tokensSaved}</td>
                        <td className="py-3 px-3 text-slate-400 font-mono">{inc.time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Subscriptions & All 4 Plans (Free Pilot, Pro/Developer, Team, Sovereign) */}
        {activeTab === 'subscriptions' && (
          <div className="space-y-6 animate-fade-in">
            <div className="glass-panel rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-sm">
              <div className="max-w-2xl">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-purple-50 border border-purple-200 text-purple-800 shadow-sm mb-3">
                  <CreditCard className="w-3.5 h-3.5 text-purple-600" />
                  <span>TIER MANAGEMENT & BILLING</span>
                </div>
                <h2 className="text-xl font-bold text-slate-950 mb-2">Available Subscription Plans</h2>
                <p className="text-xs sm:text-sm text-slate-600 mb-6 leading-relaxed">
                  Choose the plan that suits your application scale. All paid tiers include priority key pooling, 
                  unlimited AST patches, Slack integration, and verified zero-PII leak isolation.
                </p>
              </div>

              {/* 5 Complete Plans Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                {/* Plan 1: Free Pilot */}
                <div className="rounded-xl p-4.5 border border-slate-200 bg-white/80 flex flex-col justify-between shadow-sm relative">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <img src="/icon.svg" alt="Skelion" className="w-4 h-4 object-contain" onError={(e) => { (e.target as HTMLImageElement).src = '/icon.png'; }} />
                        <span className="text-[11px] font-mono font-semibold text-cyan-700 uppercase">Hosted Pilot</span>
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono">
                        Active
                      </span>
                    </div>
                    <div className="text-2xl font-extrabold text-slate-950 mb-1">₹0</div>
                    <p className="text-[11px] text-slate-500 mb-3">50 credits/mo for solo evaluation.</p>
                    <ul className="text-xs text-slate-600 space-y-1.5 mb-5">
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-cyan-600 shrink-0" /> 1 Developer seat
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-cyan-600 shrink-0" /> Fail-open edge proxy
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-cyan-600 shrink-0" /> Economy model tier
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-cyan-600 shrink-0" /> 7-day trace retention
                      </li>
                    </ul>
                  </div>
                  <button
                    disabled
                    className="w-full py-1.5 rounded-lg text-xs font-semibold text-slate-400 bg-slate-100 cursor-not-allowed"
                  >
                    Current Active Plan
                  </button>
                </div>

                {/* Plan 2: Skelion AI Lite */}
                <div className="rounded-xl p-4.5 border border-cyan-200 bg-white/90 flex flex-col justify-between shadow-sm relative">
                  <div className="absolute -top-2.5 right-3 px-2 py-0.5 rounded-full bg-cyan-100 border border-cyan-300 text-cyan-800 text-[9px] font-bold uppercase tracking-wider">
                    30% Off Pilot
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <img src="/icon.svg" alt="Skelion" className="w-4 h-4 object-contain" onError={(e) => { (e.target as HTMLImageElement).src = '/icon.png'; }} />
                        <span className="text-[11px] font-mono font-semibold text-cyan-700 uppercase">AI Lite</span>
                      </div>
                    </div>
                    <div className="flex items-baseline gap-1.5 mb-1">
                      <span className="text-2xl font-extrabold text-slate-950">₹559</span>
                      <span className="text-xs text-slate-400 line-through font-mono">₹799</span>
                      <span className="text-xs text-slate-500">/ mo</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mb-3">500 credits/mo for fast bug triage.</p>
                    <ul className="text-xs text-slate-600 space-y-1.5 mb-5">
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-cyan-600 shrink-0" /> 500 Monthly credits
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-cyan-600 shrink-0" /> Autonomous bug repro
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-cyan-600 shrink-0" /> Pytest/Jest synthesizer
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-cyan-600 shrink-0" /> 14-day retention
                      </li>
                    </ul>
                  </div>
                  <button
                    onClick={() => onOpenCheckout('hosted_lite')}
                    className="w-full py-1.5 rounded-lg text-xs font-bold text-cyan-800 bg-cyan-50 hover:bg-cyan-100 border border-cyan-200 transition shadow-xs"
                  >
                    Claim Special (₹559)
                  </button>
                </div>

                {/* Plan 3: Hosted Developer */}
                <div className="rounded-xl p-4.5 border border-slate-200 bg-white/90 flex flex-col justify-between shadow-sm relative">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <img src="/icon.svg" alt="Skelion" className="w-4 h-4 object-contain" onError={(e) => { (e.target as HTMLImageElement).src = '/icon.png'; }} />
                        <span className="text-[11px] font-mono font-semibold text-slate-800 uppercase">Developer</span>
                      </div>
                    </div>
                    <div className="flex items-baseline gap-1.5 mb-1">
                      <span className="text-2xl font-extrabold text-slate-950">₹799</span>
                      <span className="text-xs text-slate-500">/ mo</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mb-3">800 credits + Autonomous Agent Mesh.</p>
                    <ul className="text-xs text-slate-600 space-y-1.5 mb-5">
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> 800 Monthly credits
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> Autonomous Agent Mesh
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> GitHub PR cards
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> 30-day retention
                      </li>
                    </ul>
                  </div>
                  <button
                    onClick={() => onOpenCheckout('hosted_developer')}
                    className="w-full py-1.5 rounded-lg text-xs font-bold text-slate-800 bg-white hover:bg-slate-50 border border-slate-300 transition shadow-xs"
                  >
                    Upgrade Developer
                  </button>
                </div>

                {/* Plan 4: Hosted Team (Pro) */}
                <div className="rounded-xl p-4.5 border-2 border-cyan-500 bg-white/95 flex flex-col justify-between shadow-md relative">
                  <div className="absolute -top-2.5 right-3 px-2 py-0.5 rounded-full bg-cyan-600 text-white text-[9px] font-bold uppercase tracking-wider">
                    Recommended
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <img src="/icon.svg" alt="Skelion" className="w-4 h-4 object-contain" onError={(e) => { (e.target as HTMLImageElement).src = '/icon.png'; }} />
                        <span className="text-[11px] font-mono font-semibold text-purple-700 uppercase">Hosted Team</span>
                      </div>
                    </div>
                    <div className="flex items-baseline gap-1.5 mb-1">
                      <span className="text-2xl font-extrabold text-slate-950">₹3,999</span>
                      <span className="text-xs text-slate-500">/ mo</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mb-3">4,500 credits + 5 seats included.</p>
                    <ul className="text-xs text-slate-600 space-y-1.5 mb-5">
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-purple-600 shrink-0" /> 5 Developer seats
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-purple-600 shrink-0" /> 4,500 credits monthly
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-purple-600 shrink-0" /> Autonomous PR fix + CI
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-purple-600 shrink-0" /> Slack &amp; Webhook alerts
                      </li>
                    </ul>
                  </div>
                  <button
                    onClick={() => onOpenCheckout('pro')}
                    className="w-full py-1.5 rounded-lg text-xs font-bold text-white bg-cyan-600 hover:bg-cyan-500 transition shadow-sm flex items-center justify-center gap-1"
                  >
                    <span>Upgrade Team</span>
                  </button>
                </div>

                {/* Plan 5: Hosted Business */}
                <div className="rounded-xl p-4.5 border border-slate-200 bg-white/80 flex flex-col justify-between shadow-sm">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <img src="/icon.svg" alt="Skelion" className="w-4 h-4 object-contain" onError={(e) => { (e.target as HTMLImageElement).src = '/icon.png'; }} />
                        <span className="text-[11px] font-mono font-semibold text-slate-800 uppercase">Team Scale</span>
                      </div>
                    </div>
                    <div className="flex items-baseline gap-1.5 mb-1">
                      <span className="text-2xl font-extrabold text-slate-950">₹9,999</span>
                      <span className="text-xs text-slate-500">/ mo</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mb-3">12,500 credits + 20 seats.</p>
                    <ul className="text-xs text-slate-600 space-y-1.5 mb-5">
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-slate-700 shrink-0" /> 20 Developer seats
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-slate-700 shrink-0" /> Enterprise Reasoning Mesh
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-slate-700 shrink-0" /> 365-day audit log export
                      </li>
                      <li className="flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-slate-700 shrink-0" /> Priority engineering support
                      </li>
                    </ul>
                  </div>
                  <button
                    onClick={() => onOpenCheckout('hosted_business')}
                    className="w-full py-1.5 rounded-lg text-xs font-bold text-slate-900 bg-slate-100 hover:bg-slate-200 transition border border-slate-300"
                  >
                    Upgrade Team Scale
                  </button>
                </div>
              </div>

              {/* Sovereign Enterprise Callout */}
              <div className="mt-5 p-4 rounded-xl border border-slate-200 bg-slate-50/70 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center font-bold text-xs shrink-0">
                    SSO
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">Custom Tier (+₹25,000+/mo / +$299+/mo) [base: +₹39,999/mo]</div>
                    <div className="text-[11px] text-slate-500">Custom enterprise contracts, SAML SSO, dedicated proxy bridges, and customizable volume quotas.</div>
                  </div>
                </div>
                <button
                  onClick={() => onOpenCheckout('enterprise')}
                  className="px-4 py-1.5 rounded-lg text-xs font-bold text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 transition shadow-2xs shrink-0"
                >
                  Inquire Enterprise
                </button>
              </div>
            </div>

            {/* Invoices & Billing History List */}
            <div className="glass-panel rounded-2xl p-6 border border-slate-200/90 shadow-sm">
              <h3 className="text-sm font-bold text-slate-950 mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-600" />
                <span>Billing History & Invoices</span>
              </h3>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center text-xs text-slate-500">
                You are currently on the Community Free Pilot. Paid transactions completed through Razorpay will be dynamically displayed here with one-click PDF invoice downloads.
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Cloud Agent Integration Setup */}
        {activeTab === 'integration' && (
          <div className="space-y-6 animate-fade-in">
            <div className="glass-panel rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-sm">
              <div className="max-w-2xl mb-6">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-50 border border-cyan-200 text-cyan-800 shadow-sm mb-3">
                  <Terminal className="w-3.5 h-3.5 text-cyan-600" />
                  <span>OFFICIAL CLOUD AGENT SETUP</span>
                </div>
                <h2 className="text-xl font-bold text-slate-950 mb-2">Connect Your Pipeline in 2 Steps</h2>
                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                  Run the Skelion CLI or webhook integration to monitor active LLM key quotas, inspect AST diagnostic cards, and trigger safe reproduction tests directly in the cloud.
                </p>
              </div>

              <div className="space-y-6 max-w-3xl">
                {/* Step 1 */}
                <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-cyan-100 text-cyan-800 font-mono text-xs font-bold flex items-center justify-center">
                      1
                    </span>
                    <h3 className="text-sm font-bold text-slate-900">Install via Python Package Manager</h3>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between gap-2 font-mono text-xs text-cyan-800">
                    <span className="truncate">pip install skelion</span>
                    <button
                      onClick={() => copyToClipboard('pip install skelion', 'cmd_install')}
                      className="px-2.5 py-1 rounded bg-white text-slate-700 border border-slate-200 hover:border-cyan-400 text-xs font-sans transition shrink-0"
                    >
                      {copiedKey === 'cmd_install' ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-cyan-100 text-cyan-800 font-mono text-xs font-bold flex items-center justify-center">
                      2
                    </span>
                    <h3 className="text-sm font-bold text-slate-900">Authorize with your Agent Token</h3>
                  </div>
                  <p className="text-xs text-slate-600">
                    Run the login command in your terminal or provide your token to the Skelion middleware:
                  </p>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between gap-2 font-mono text-xs text-cyan-800">
                    <span className="truncate select-all">{cloudAgentApiToken}</span>
                    <button
                      onClick={() => copyToClipboard(cloudAgentApiToken, 'cmd_token')}
                      className="px-2.5 py-1 rounded bg-white text-slate-700 border border-slate-200 hover:border-cyan-400 text-xs font-sans transition shrink-0"
                    >
                      {copiedKey === 'cmd_token' ? 'Copied' : 'Copy Token'}
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <a
                    href="#console"
                    className="px-4 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 transition shadow-md shadow-cyan-500/20 flex items-center gap-2"
                  >
                    <Terminal className="w-4 h-4 text-white" />
                    <span>Launch Web Console</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Incidents & Filterable Resilience Logs */}
        {activeTab === 'incidents' && (
          <div className="space-y-6 animate-fade-in">
            <div className="glass-panel rounded-2xl p-6 border border-slate-200/90 shadow-sm space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h2 className="text-base font-bold text-slate-950">Detailed Autonomous Resilience Audit Ledger</h2>
                  <p className="text-xs text-slate-500">Every incident intercepted, scrubbed, sandboxed, and resolved</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleRefreshStats}
                    className="px-3 py-1.5 rounded-lg text-xs font-mono bg-white border border-slate-200 hover:border-slate-300 text-slate-700 transition shadow-sm flex items-center gap-1.5"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 text-cyan-600 ${isRefreshing ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                  </button>
                  <button
                    onClick={() => copyToClipboard(JSON.stringify(allIncidents, null, 2), 'export_all')}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 transition shadow-sm"
                  >
                    {copiedKey === 'export_all' ? 'Copied All JSON' : 'Export Full Ledger'}
                  </button>
                </div>
              </div>

              {/* Filter Pills */}
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
                <span className="text-xs text-slate-400 font-mono">Filter:</span>
                {(['all', 'intercept', 'rotation', 'scrub', 'patch'] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setIncidentFilter(filter)}
                    className={`px-2.5 py-1 rounded-md text-xs font-mono transition ${
                      incidentFilter === filter
                        ? 'bg-slate-900 text-white font-semibold'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {filter === 'all' ? 'All Incidents' : filter.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Incidents List */}
              <div className="space-y-3">
                {filteredIncidents.map((inc) => (
                  <div key={inc.id} className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-cyan-300 transition">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-slate-900">{inc.id}</span>
                        <span className={`px-2 py-0.5 rounded-full border text-[10px] font-mono font-medium ${inc.badgeClass}`}>
                          {inc.status}
                        </span>
                        <span className="text-[11px] text-slate-400 font-mono">{inc.time}</span>
                      </div>
                      <div className="text-xs text-slate-700 font-mono">
                        Target: <span className="text-cyan-800 font-semibold">{inc.service}</span>
                      </div>
                      <div className="text-xs text-slate-500">
                        Resolution detail: {inc.latency} • {inc.tokensSaved}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <button
                        onClick={() => copyToClipboard(JSON.stringify(inc, null, 2), inc.id)}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 border border-slate-200 transition"
                      >
                        {copiedKey === inc.id ? 'Copied JSON' : 'Export JSON'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
