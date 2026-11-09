import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  AlertTriangle, 
  GitPullRequest, 
  History, 
  Gauge, 
  Repeat, 
  Puzzle, 
  CreditCard, 
  LogOut, 
  ExternalLink, 
  Sparkles, 
  Eye, 
  ShieldCheck,
  ChevronRight,
  Terminal,
  Activity,
  Layers,
  LayoutDashboard
} from 'lucide-react';
import { UserProfile } from '../../utils/auth';
import { Dashboard } from '../Dashboard';
import { AskTab } from './tabs/AskTab';
import { IncidentsTab, IncidentDeepDivePayload } from './tabs/IncidentsTab';
import { FixesTab } from './tabs/FixesTab';
import { HistoryTab } from './tabs/HistoryTab';
import { LimitsTab } from './tabs/LimitsTab';
import { LoopTab } from './tabs/LoopTab';
import { PluginsTab } from './tabs/PluginsTab';
import { PricingTab } from './tabs/PricingTab';

export type ConsoleTab = 
  | 'ask' 
  | 'dashboard'
  | 'incidents' 
  | 'fixes' 
  | 'history' 
  | 'limits' 
  | 'loop' 
  | 'plugins' 
  | 'pricing';

interface ConsoleWorkspaceProps {
  user: UserProfile;
  isGuest?: boolean;
  onLogout: () => void;
  onOpenCheckout: (planId?: string, coupon?: string, currency?: 'INR' | 'USD', customData?: { customAmount: number; customCredits: number }) => void;
  onViewLandingPage: () => void;
}

export const ConsoleWorkspace: React.FC<ConsoleWorkspaceProps> = ({
  user,
  isGuest = false,
  onLogout,
  onOpenCheckout,
  onViewLandingPage,
}) => {
  const getTabFromHash = (): ConsoleTab => {
    const raw = (window.location.hash || '').replace('#', '').toLowerCase();
    if (raw === 'dashboard') return 'dashboard';
    if (raw === 'incidents') return 'incidents';
    if (raw === 'fixes') return 'fixes';
    if (raw === 'history') return 'history';
    if (raw === 'limits') return 'limits';
    if (raw === 'loop') return 'loop';
    if (raw === 'plugins') return 'plugins';
    if (raw === 'pricing') return 'pricing';
    return 'ask';
  };

  const [activeTab, setActiveTab] = useState<ConsoleTab>(getTabFromHash);
  const [deepDivePayload, setDeepDivePayload] = useState<IncidentDeepDivePayload | null>(null);
  const [currentRepo, setCurrentRepo] = useState<string>(() => localStorage.getItem('skelion_selected_repo') || 'Skelion');
  const [currentRepoOwner, setCurrentRepoOwner] = useState<string>(() => localStorage.getItem('skelion_selected_repo_owner') || user?.username || 'Aditya-9-6');

  const handleSelectRepo = async (repoName: string, repoOwner?: string) => {
    const owner = repoOwner || currentRepoOwner;
    setCurrentRepo(repoName);
    if (repoOwner) setCurrentRepoOwner(repoOwner);
    localStorage.setItem('skelion_selected_repo', repoName);
    if (repoOwner) localStorage.setItem('skelion_selected_repo_owner', repoOwner);

    // Immediately trigger the autonomous loop on repo selection
    try {
      const fullRepo = `${owner}/${repoName}`;
      await fetch('/v1/autonomous/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo: fullRepo }),
      });
    } catch {
      // Graceful local handling
    }
  };

  useEffect(() => {
    const syncTab = () => {
      const tab = getTabFromHash();
      setActiveTab(tab);
    };
    window.addEventListener('hashchange', syncTab);
    return () => window.removeEventListener('hashchange', syncTab);
  }, []);

  const handleTabSelect = (tab: ConsoleTab) => {
    setActiveTab(tab);
    window.location.hash = `#${tab}`;
  };

  const handleDeepDiveIncident = (payload: IncidentDeepDivePayload) => {
    setDeepDivePayload(payload);
    handleTabSelect('ask');
  };

  const tabItems: { id: ConsoleTab; label: string; icon: React.FC<{ className?: string }>; badge?: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'ask', label: 'Ask (IDE)', icon: Bot },
    { id: 'incidents', label: 'Incidents', icon: AlertTriangle, badge: '3' },
    { id: 'fixes', label: 'Fixes', icon: GitPullRequest, badge: '2' },
    { id: 'history', label: 'History', icon: History },
    { id: 'limits', label: 'Limits', icon: Gauge },
    { id: 'loop', label: 'Loop', icon: Repeat },
    { id: 'plugins', label: 'Plugins', icon: Puzzle },
    { id: 'pricing', label: 'Pricing', icon: CreditCard },
  ];

  const handleSynthesizePatch = (_incidentId: string) => {
    handleTabSelect('fixes');
  };

  const handleNavigateToFixes = () => {
    handleTabSelect('fixes');
  };

  return (
    <div className="py-6 md:py-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6 relative z-10">
      {/* Top Jules-Style Command Bar */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-4 sm:p-5 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        {/* User Identity & Mesh Connection Status */}
        <div className="flex items-center gap-3.5">
          <div className="relative">
            <img
              src={user.avatar}
              alt={user.name || user.username}
              className="w-11 h-11 rounded-2xl border-2 border-cyan-500/70 shadow-sm object-cover"
            />
            <span className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-white" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-extrabold text-slate-900 tracking-tight">
                {user.name || user.username}
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-50 text-cyan-800 border border-cyan-200">
                PRO ACTIVE
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500 font-mono mt-0.5">
              <span className="flex items-center gap-1 text-emerald-600 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Edge Mesh Connected
              </span>
              <span>·</span>
              <span>1.4ms latency</span>
              <span>·</span>
              <span>Zero-restart engine</span>
            </div>
          </div>
        </div>

        {/* Global Action CTAs: View Landing Page & Logout */}
        <div className="flex flex-wrap items-center gap-2.5 self-stretch sm:self-auto justify-end">
          <button
            onClick={onViewLandingPage}
            className="px-3.5 py-2 rounded-xl border border-slate-200 hover:border-slate-300 bg-white/90 text-slate-700 hover:text-slate-900 text-xs font-semibold flex items-center gap-1.5 transition shadow-2xs"
            title="Preview public landing page with 3D animations"
          >
            <Eye className="w-3.5 h-3.5 text-cyan-600" />
            <span>View Public Site</span>
          </button>


          <button
            onClick={onLogout}
            className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-sm"
            title="Log out and return to landing page"
          >
            <LogOut className="w-3.5 h-3.5 text-rose-400" />
            <span>Log Out</span>
          </button>
        </div>
      </div>

      {/* Jules-Style Sleek Navigation Tabs */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-2 shadow-xs flex items-center gap-1.5 overflow-x-auto scrollbar-none">
        {tabItems.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => handleTabSelect(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                isActive
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
              <span>{tab.label}</span>
              {tab.badge && (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                  isActive ? 'bg-cyan-500 text-slate-950' : 'bg-slate-200/80 text-slate-700'
                }`}>
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div className="transition-all duration-300">
        {activeTab === 'dashboard' && (
          <Dashboard
            user={user}
            isGuest={isGuest}
            onOpenCheckout={(plan) => onOpenCheckout(plan)}
            onLogout={onLogout}
          />
        )}

        {activeTab === 'ask' && (
          <AskTab
            user={user}
            onNavigateToFixes={handleNavigateToFixes}
            deepDivePayload={deepDivePayload}
            onClearDeepDive={() => setDeepDivePayload(null)}
            currentRepo={currentRepo}
            currentRepoOwner={currentRepoOwner}
            onSelectRepo={handleSelectRepo}
          />
        )}

        {activeTab === 'incidents' && (
          <IncidentsTab
            onSynthesizePatch={handleSynthesizePatch}
            onDeepDive={handleDeepDiveIncident}
          />
        )}

        {activeTab === 'fixes' && (
          <FixesTab />
        )}

        {activeTab === 'history' && (
          <HistoryTab />
        )}

        {activeTab === 'limits' && (
          <LimitsTab onOpenCheckout={onOpenCheckout} />
        )}

        {activeTab === 'loop' && (
          <LoopTab
            currentRepo={currentRepo}
            currentRepoOwner={currentRepoOwner}
            onSelectRepo={handleSelectRepo}
          />
        )}

        {activeTab === 'plugins' && (
          <PluginsTab user={user} />
        )}

        {activeTab === 'pricing' && (
          <PricingTab onSelectPlan={onOpenCheckout} />
        )}
      </div>
    </div>
  );
};
