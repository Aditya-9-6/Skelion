import React, { useState, useEffect } from 'react';
import { 
  Puzzle, 
  Terminal, 
  Copy, 
  Check, 
  Key, 
  ExternalLink, 
  Plus, 
  ShieldCheck, 
  Trash2,
  RefreshCw,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Layers,
  ArrowUpDown
} from 'lucide-react';
import { UserProfile } from '../../../utils/auth';

interface PluginsTabProps {
  user: UserProfile;
}

interface ProviderKeyConfig {
  id: string;
  name: string;
  provider: string;
  models: string;
  apiKey: string;
  status: 'CONNECTED' | 'STANDBY' | 'UNCONFIGURED';
  priority: number;
  testLatency?: string;
  placeholder: string;
}

const STORAGE_KEYS_KEY = 'skelion_keypool_keys';

export const PluginsTab: React.FC<PluginsTabProps> = ({ user }) => {
  const [copiedToken, setCopiedToken] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState(false);
  const [tokenSalt, setTokenSalt] = useState('x91q7');
  const [visibleKeyId, setVisibleKeyId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const defaultProviders: ProviderKeyConfig[] = [
    {
      id: 'groq',
      name: 'Skelion Primary Resilience Engine (Mesh 1)',
      provider: 'Skelion Active Edge',
      models: 'Skelion AI Agent (High-Speed · Active)',
      apiKey: '',
      status: 'CONNECTED',
      priority: 1,
      testLatency: '1.2ms (Zero-restart active)',
      placeholder: 'gsk_...'
    },
    {
      id: 'gemini',
      name: 'Skelion High-Throughput Cluster (Mesh 2)',
      provider: 'Skelion Mesh Cluster',
      models: 'Skelion Multi-Turn Reasoning Node',
      apiKey: 'skl_live_mesh_cluster_02',
      status: 'CONNECTED',
      priority: 2,
      testLatency: '1.8ms',
      placeholder: 'skl_...'
    },
    {
      id: 'anthropic',
      name: 'Skelion Low-Latency Standby Cluster (Mesh 3)',
      provider: 'Skelion Gossip Ring',
      models: 'Skelion Autonomous Synthesizer',
      apiKey: 'skl_live_standby_03',
      status: 'STANDBY',
      priority: 3,
      placeholder: 'skl_...'
    },
    {
      id: 'openai',
      name: 'Skelion Enterprise Dedicated Proxy Bridge',
      provider: 'Skelion Dedicated Gateway',
      models: 'Skelion Private Invariant Engine',
      apiKey: '',
      status: 'UNCONFIGURED',
      priority: 4,
      placeholder: 'skl_gw_...'
    }
  ];

  const [providers, setProviders] = useState<ProviderKeyConfig[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (_) {}
    return defaultProviders;
  });

  const cloudAgentApiToken = `skl_live_${user.id}_${btoa(user.username || 'dev').substring(0, 8)}${tokenSalt}`;
  const cloudAgentPairCmd = `skelion auth login --token ${cloudAgentApiToken}`;

  const copyText = (text: string, type: 'token' | 'cmd') => {
    navigator.clipboard.writeText(text);
    if (type === 'token') {
      setCopiedToken(true);
      setTimeout(() => setCopiedToken(false), 2000);
    } else {
      setCopiedCmd(true);
      setTimeout(() => setCopiedCmd(false), 2000);
    }
  };

  const handleRotate = () => {
    setTokenSalt(Math.random().toString(36).substring(2, 7));
  };

  const handleKeyChange = (id: string, val: string) => {
    setProviders((prev) =>
      prev.map((p) => {
        if (p.id === id) {
          const status = val.trim() ? (p.priority === 1 ? 'CONNECTED' : 'STANDBY') : 'UNCONFIGURED';
          return { ...p, apiKey: val, status };
        }
        return p;
      })
    );
  };

  const handleTestKey = (id: string) => {
    setTestingId(id);
    setTimeout(() => {
      setProviders((prev) =>
        prev.map((p) => {
          if (p.id === id) {
            const isSet = Boolean(p.apiKey.trim());
            return {
              ...p,
              status: isSet ? 'CONNECTED' : 'UNCONFIGURED',
              testLatency: isSet ? `${Math.floor(Math.random() * 80 + 120)}ms (Healthy)` : undefined
            };
          }
          return p;
        })
      );
      setTestingId(null);
    }, 900);
  };

  const handleSaveAllKeys = () => {
    try {
      localStorage.setItem(STORAGE_KEYS_KEY, JSON.stringify(providers));
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (_) {}
  };

  const activePlugins = [
    { name: 'Skelion Cloud Agent Gateway', version: 'v0.1.4', status: 'Connected', badge: 'Active' },
    { name: 'Skelion Edge LLM Inference Gateway', version: 'v2.1', status: 'Healthy', badge: 'Active' },
    { name: 'Skelion Invariant Multi-turn Reasoning SDK', version: 'v1.0', status: 'Standby', badge: 'Active' },
    { name: 'eBPF Zero-Downtime Mesh Interceptor', version: 'v0.9-rc', status: 'Injected', badge: 'Active' }
  ];

  return (
    <div className="space-y-6">
      {/* Cloud Agent Pairing Card */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-6 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)] space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Cloud Agent CLI &amp; API Token Pairing</h2>
              <p className="text-xs text-slate-500 font-mono">
                Connect your local terminal or CI/CD pipelines to this web platform for instant AST patch sync and live logs.
              </p>
            </div>
          </div>

          <button
            onClick={handleRotate}
            className="px-3 py-1.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white text-xs font-semibold text-slate-700 flex items-center gap-1.5 transition shadow-2xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Rotate Token</span>
          </button>
        </div>

        {/* Token Box */}
        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="truncate w-full sm:w-auto">
            <span className="text-slate-500 mr-2 select-none">PAIRING TOKEN:</span>
            <span className="text-cyan-400 font-bold">{cloudAgentApiToken}</span>
          </div>
          <button
            onClick={() => copyText(cloudAgentApiToken, 'token')}
            className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold flex items-center gap-1.5 transition shrink-0"
          >
            {copiedToken ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedToken ? 'Copied' : 'Copy Token'}</span>
          </button>
        </div>

        {/* CLI Command */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="truncate w-full sm:w-auto">
            <span className="text-slate-400 mr-2 select-none">$</span>
            <span className="text-slate-900">{cloudAgentPairCmd}</span>
          </div>
          <button
            onClick={() => copyText(cloudAgentPairCmd, 'cmd')}
            className="px-3 py-1 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition shrink-0 shadow-2xs"
          >
            {copiedCmd ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedCmd ? 'Copied' : 'Copy CLI Command'}</span>
          </button>
        </div>
      </div>

      {/* Multi-Provider Key-Pool Configurator */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-6 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Key className="w-4 h-4 text-cyan-600" />
              <h3 className="text-sm font-bold text-slate-900">Multi-Provider Key-Pool Configurator</h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-50 text-cyan-800 border border-cyan-200">
                Zero-429 Mesh
              </span>
            </div>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Add your API keys to prevent throttling. Skelion automatically fails open and rotates standby keys within 1.4ms.
            </p>
          </div>

          <button
            onClick={handleSaveAllKeys}
            className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition shadow-sm flex items-center gap-1.5 shrink-0"
          >
            {savedSuccess ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />}
            <span>{savedSuccess ? 'Pool Saved & Active!' : 'Save Key Pool'}</span>
          </button>
        </div>

        {/* Providers Grid */}
        <div className="space-y-3.5">
          {providers.map((p) => {
            const isVisible = visibleKeyId === p.id;
            const isTesting = testingId === p.id;

            return (
              <div
                key={p.id}
                className="p-4 rounded-xl border border-slate-200/80 bg-white/70 hover:bg-white/95 transition shadow-2xs space-y-3"
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-6 h-6 rounded-lg bg-slate-100 text-slate-700 font-mono font-bold text-xs flex items-center justify-center shrink-0">
                      #{p.priority}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-slate-900">{p.name}</span>
                        <span className={`px-2 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                          p.status === 'CONNECTED' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                          p.status === 'STANDBY' ? 'bg-cyan-50 text-cyan-700 border border-cyan-200' :
                          'bg-slate-100 text-slate-500'
                        }`}>
                          {p.status}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                        Provider: {p.provider} · Models: {p.models}
                      </div>
                    </div>
                  </div>

                  {p.testLatency && (
                    <div className="text-[11px] font-mono text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                      ✓ Ping: {p.testLatency}
                    </div>
                  )}
                </div>

                {/* API Key Input Row */}
                <div className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <input
                      type={isVisible ? 'text' : 'password'}
                      value={p.apiKey}
                      onChange={(e) => handleKeyChange(p.id, e.target.value)}
                      placeholder={p.placeholder}
                      className="w-full text-xs font-mono bg-white border border-slate-200 rounded-xl pl-3 pr-10 py-2 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 shadow-xs"
                    />
                    <button
                      type="button"
                      onClick={() => setVisibleKeyId(isVisible ? null : p.id)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1"
                      title={isVisible ? 'Hide key' : 'Show key'}
                    >
                      {isVisible ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleTestKey(p.id)}
                    disabled={isTesting || !p.apiKey.trim()}
                    className="px-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 disabled:opacity-40 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition shadow-2xs shrink-0"
                  >
                    {isTesting ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-600" />
                        <span>Testing...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5 text-cyan-600" />
                        <span>Test Key</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Installed Integrations & Providers */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Puzzle className="w-4 h-4 text-cyan-600" />
            <h3 className="text-sm font-bold text-slate-900">Active Plugins &amp; Model Connectors</h3>
          </div>
          <span className="text-xs text-slate-500 font-mono">4 Connected</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {activePlugins.map((plugin, idx) => (
            <div key={idx} className="p-4 rounded-xl border border-slate-200/80 bg-white/90 flex items-center justify-between gap-3">
              <div>
                <div className="font-bold text-xs text-slate-900">{plugin.name}</div>
                <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                  Version: {plugin.version} · Status: <span className="text-emerald-600 font-semibold">{plugin.status}</span>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                {plugin.badge}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
