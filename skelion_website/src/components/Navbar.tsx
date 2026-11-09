import React, { useState, useEffect } from 'react';
import { Terminal, ExternalLink, Menu, X, Star, Sparkles, LogOut, Github, AlertCircle, ChevronRight, Zap } from 'lucide-react';
import { getUserCreditState } from '../utils/creditLedger';
import {
  UserProfile,
  getStoredUser,
  getGitHubLoginUrl,
  handleOAuthRedirect,
  logoutUser,
  initAuthConfig,
  setCustomGitHubClientId,
  getGitHubClientId,
} from '../utils/auth';

const getDisplayName = (user: UserProfile) => {
  if (user.username && user.username.length <= 15) {
    return user.username;
  }
  if (user.name) {
    const parts = user.name.trim().split(/\s+/);
    if (parts.length >= 2) {
      // If first + last name is compact, use it; otherwise first name
      const shortName = `${parts[0]} ${parts[parts.length - 1]}`;
      return shortName.length <= 16 ? shortName : parts[0];
    }
    return parts[0];
  }
  return user.username || 'Developer';
};

interface NavbarProps {
  onOpenCheckout: (planId?: string) => void;
  currentUser?: UserProfile | null;
  onUserChange?: (user: UserProfile | null) => void;
  onLogout?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenCheckout, currentUser, onUserChange, onLogout }) => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [user, setUser] = useState<UserProfile | null>(currentUser || null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [inputClientId, setInputClientId] = useState('');
  const [userCredits, setUserCredits] = useState<number>(() => getUserCreditState().balance);

  useEffect(() => {
    const handleCreditUpdate = (e: any) => {
      if (e.detail?.balance !== undefined) {
        setUserCredits(e.detail.balance);
      } else {
        setUserCredits(getUserCreditState().balance);
      }
    };
    window.addEventListener('skelion:credits-updated', handleCreditUpdate);
    return () => window.removeEventListener('skelion:credits-updated', handleCreditUpdate);
  }, []);

  useEffect(() => {
    if (currentUser !== undefined) {
      setUser(currentUser);
    }
  }, [currentUser]);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    // Initialize server auth config
    initAuthConfig();

    // Check stored user on mount
    const storedUser = getStoredUser();
    if (storedUser) {
      setUser(storedUser);
      onUserChange?.(storedUser);
    }

    // Handle OAuth callback code exchange
    if (window.location.search.includes('code=')) {
      setAuthLoading(true);
      handleOAuthRedirect()
        .then((loggedInUser) => {
          if (loggedInUser) {
            setUser(loggedInUser);
            onUserChange?.(loggedInUser);
            // After successful OAuth login, redirect directly to dashboard view
            window.location.hash = '#dashboard';
            window.dispatchEvent(new HashChangeEvent('hashchange'));
          }
        })
        .catch((err) => {
          setAuthError(err.message || 'GitHub Authentication failed');
        })
        .finally(() => {
          setAuthLoading(false);
        });
    }

    const openModalListener = () => {
      setInputClientId(getGitHubClientId() || '');
      setShowConfigModal(true);
    };
    window.addEventListener('skelion:open-oauth-modal', openModalListener);
    return () => window.removeEventListener('skelion:open-oauth-modal', openModalListener);
  }, []);

  const handleLogin = async () => {
    setAuthError(null);
    setAuthLoading(true);
    try {
      const loginUrl = await getGitHubLoginUrl();
      window.location.href = loginUrl;
    } catch (e: any) {
      setAuthLoading(false);
      setInputClientId(getGitHubClientId() || '');
      setShowConfigModal(true);
      setAuthError(e.message || 'GitHub Client ID is not configured');
    }
  };

  const handleSaveClientIdAndLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputClientId.trim()) return;
    setCustomGitHubClientId(inputClientId.trim());
    setShowConfigModal(false);
    setAuthLoading(true);
    try {
      const loginUrl = await getGitHubLoginUrl();
      window.location.href = loginUrl;
    } catch (err: any) {
      setAuthLoading(false);
      setAuthError(err.message || 'Failed to initialize GitHub login with provided Client ID');
    }
  };

  const handleLogout = () => {
    logoutUser();
    setUser(null);
    onUserChange?.(null);
    setMobileMenuOpen(false);
    window.location.hash = '#home';
    onLogout?.();
  };

  const handleAnchorClick = (e: React.MouseEvent<HTMLAnchorElement>, targetId: string) => {
    e.preventDefault();
    setMobileMenuOpen(false);
    const element = document.getElementById(targetId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
      window.history.pushState(null, '', `#${targetId}`);
    } else {
      window.location.hash = `#${targetId}`;
    }
  };

  return (
    <>
      {/* Auth Error Banner if any */}
      {authError && (
        <div className="bg-red-50 border-b border-red-200 py-1.5 px-4 text-center text-xs text-red-700 flex items-center justify-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span><strong>GitHub Login Error:</strong> {authError}</span>
          <button onClick={() => setAuthError(null)} className="ml-2 underline text-red-800 hover:text-red-950">Dismiss</button>
        </div>
      )}

      {/* Main Sticky Navigation */}
      <header
        className={`sticky top-0 z-50 transition-all duration-300 ${
          scrolled
            ? 'bg-white/85 backdrop-blur-xl border-b border-slate-200/80 shadow-sm'
            : 'bg-white/60 backdrop-blur-md border-b border-slate-200/40'
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Brand Logo */}
          <a href={user ? "#console" : "#home"} onClick={(e) => !user && handleAnchorClick(e, 'home')} className="flex items-center gap-2.5 sm:gap-3 group shrink-0">
            <div className="relative shrink-0 w-8 h-8 flex items-center justify-center">
              <div className="absolute -inset-1 bg-gradient-to-r from-cyan-400 to-purple-500 rounded-lg blur opacity-30 group-hover:opacity-75 transition duration-300"></div>
              <img
                src="/icon.svg"
                alt="Skelion Logo"
                className="relative w-8 h-8 rounded-lg bg-white p-1 border border-slate-200/90 shadow-sm object-contain shrink-0"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = '/icon.png';
                }}
              />
            </div>
            <div className="flex flex-col justify-center shrink-0">
              <div className="flex items-center gap-2 leading-none">
                <span className="text-lg sm:text-xl font-extrabold tracking-tight text-slate-900">
                  SKELION
                </span>
                <span className="text-[10px] leading-tight px-1.5 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200 font-mono font-medium shrink-0">
                  PLATFORM
                </span>
              </div>
              <span className="text-[9px] sm:text-[10px] text-slate-400 font-mono tracking-wider mt-1 hidden sm:block">
                AUTONOMOUS RESILIENCE
              </span>
            </div>
          </a>

          {/* Desktop Navigation Links */}
          <nav className="hidden lg:flex items-center gap-4 xl:gap-6 2xl:gap-7 text-xs xl:text-sm font-medium text-slate-600 shrink-0">
            {!user ? (
              <>
                <a href="#features" onClick={(e) => handleAnchorClick(e, 'features')} className="hover:text-cyan-600 transition-colors whitespace-nowrap cursor-pointer">
                  Features
                </a>
                <a href="#simulator" onClick={(e) => handleAnchorClick(e, 'simulator')} className="hover:text-cyan-600 transition-colors whitespace-nowrap cursor-pointer">
                  Live Simulator
                </a>
                <a href="#architecture" onClick={(e) => handleAnchorClick(e, 'architecture')} className="hover:text-cyan-600 transition-colors whitespace-nowrap cursor-pointer">
                  Architecture
                </a>
                <a href="#why-us" onClick={(e) => handleAnchorClick(e, 'why-us')} className="hover:text-cyan-600 transition-colors whitespace-nowrap cursor-pointer">
                  Why Skelion
                </a>
                <a href="#pricing" onClick={(e) => handleAnchorClick(e, 'pricing')} className="hover:text-cyan-600 transition-colors whitespace-nowrap cursor-pointer">
                  Pricing
                </a>
                <a href="#faq" onClick={(e) => handleAnchorClick(e, 'faq')} className="hover:text-cyan-600 transition-colors whitespace-nowrap cursor-pointer">
                  FAQ
                </a>
              </>
            ) : (
              <div className="flex items-center gap-1.5 xl:gap-2">
                <a
                  href="#console"
                  className="font-semibold text-cyan-700 hover:text-cyan-800 bg-cyan-50/90 px-2.5 py-1 rounded-md border border-cyan-200/90 transition-colors flex items-center gap-1.5 shadow-xs whitespace-nowrap"
                >
                  <Terminal className="w-3.5 h-3.5 text-cyan-600" />
                  <span>Cloud Agent Console</span>
                </a>
                <a href="#dashboard" className="hover:text-cyan-600 px-2 py-1 rounded-md transition-colors whitespace-nowrap">
                  Dashboard
                </a>
                <a href="#ask" className="hover:text-cyan-600 px-2 py-1 rounded-md transition-colors whitespace-nowrap">
                  Ask
                </a>
                <a href="#incidents" className="hover:text-cyan-600 px-2 py-1 rounded-md transition-colors whitespace-nowrap">
                  Incidents
                </a>
                <a href="#fixes" className="hover:text-cyan-600 px-2 py-1 rounded-md transition-colors whitespace-nowrap">
                  Fixes
                </a>
                <a href="#limits" className="hover:text-cyan-600 px-2 py-1 rounded-md transition-colors whitespace-nowrap">
                  Limits
                </a>
              </div>
            )}
          </nav>

          {/* Action CTAs */}
          <div className="hidden sm:flex items-center gap-2 sm:gap-2.5 lg:gap-3 shrink-0">

            {user ? (
              <>
                <a
                  href="#limits"
                  title="Available Credit Balance (1 Credit = 1,000 Tokens)"
                  className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-mono font-bold text-cyan-800 bg-cyan-50/90 hover:bg-cyan-100 border border-cyan-200/90 transition shadow-2xs shrink-0"
                >
                  <Zap className="w-3.5 h-3.5 text-cyan-600" />
                  <span>{userCredits.toLocaleString()} Cr</span>
                </a>
                <div className="flex items-center gap-2 bg-white/95 border border-slate-200/90 pl-2 pr-1.5 py-1 rounded-xl shadow-sm shrink-0">
                <a
                  href="#console"
                  title="Open Web Platform Console"
                  className="flex items-center gap-2 hover:opacity-85 transition group"
                >
                  <img
                    src={user.avatar}
                    alt={user.name || user.username}
                    className="w-6 h-6 rounded-full border border-cyan-500/70 object-cover shrink-0"
                  />
                  <div className="flex flex-col text-left leading-tight pr-1">
                    <span className="text-xs font-semibold text-slate-800 max-w-[105px] truncate group-hover:text-cyan-700 transition-colors">
                      {getDisplayName(user)}
                    </span>
                    <span className="text-[10px] text-cyan-600 font-mono font-medium flex items-center gap-0.5">
                      Console <ChevronRight className="w-2.5 h-2.5" />
                    </span>
                  </div>
                </a>
                <div className="h-4 w-[1px] bg-slate-200 shrink-0" />
                <button
                  onClick={handleLogout}
                  title="Logout"
                  className="text-slate-400 hover:text-red-500 transition-colors p-1 rounded-md hover:bg-slate-100 shrink-0"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
              </>
            ) : (
              <button
                onClick={handleLogin}
                disabled={authLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 transition-all border border-slate-800 shadow-sm shrink-0 whitespace-nowrap"
              >
                <Github className="w-3.5 h-3.5 shrink-0" />
                <span>{authLoading ? 'Signing in...' : 'Login with GitHub'}</span>
              </button>
            )}

            <button
              onClick={() => onOpenCheckout(user ? 'pro' : 'pilot')}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 transition border border-slate-200 shadow-sm shrink-0 whitespace-nowrap"
            >
              {user ? 'Upgrade' : 'Start Free'}
            </button>

            <a
              href="#console"
              className="relative group overflow-hidden px-3.5 py-1.5 rounded-lg text-xs font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 transition-all shadow-md shadow-cyan-500/20 flex items-center gap-1.5 shrink-0 whitespace-nowrap"
            >
              <Terminal className="w-3.5 h-3.5 text-white shrink-0" />
              <span>Launch Console</span>
            </a>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex lg:hidden items-center gap-2 shrink-0">
            {user && (
              <img
                src={user.avatar}
                alt={user.name}
                className="w-7 h-7 rounded-full border border-cyan-500/50 object-cover"
              />
            )}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden bg-white/95 backdrop-blur-2xl border-b border-slate-200 px-4 pt-3 pb-6 space-y-3 shadow-xl">
            {user ? (
              <div className="flex items-center justify-between bg-slate-50 p-3 rounded-lg border border-slate-200 mb-3">
                <a
                  href="#console"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 hover:opacity-80 transition"
                >
                  <img src={user.avatar} alt={user.name} className="w-8 h-8 rounded-full border border-cyan-500 object-cover" />
                  <div>
                    <div className="text-xs font-semibold text-slate-900">{user.name}</div>
                    <div className="text-[10px] text-cyan-700 font-mono">@{user.username} • View Console →</div>
                  </div>
                </a>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1 text-xs text-red-600 hover:text-red-700 bg-red-50 px-2.5 py-1 rounded border border-red-200"
                >
                  <LogOut className="w-3 h-3" /> Logout
                </button>
              </div>
            ) : (
              <button
                onClick={handleLogin}
                className="w-full flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 transition border border-slate-800 mb-3 shadow-sm"
              >
                <Github className="w-4 h-4" /> Login with GitHub
              </button>
            )}

            {user ? (
              <div className="space-y-1">
                <a
                  href="#console"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-cyan-700 bg-cyan-50/70 px-3 py-2 rounded-lg font-bold border border-cyan-200/80 mb-2"
                >
                  💻 Web Platform Console
                </a>
                <a
                  href="#dashboard"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium"
                >
                  Dashboard
                </a>
                <a
                  href="#ask"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium"
                >
                  Ask (IDE)
                </a>
                <a
                  href="#incidents"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium"
                >
                  Incidents
                </a>
                <a
                  href="#fixes"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium"
                >
                  Fixes &amp; PRs
                </a>
                <a
                  href="#limits"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium"
                >
                  Credits &amp; Limits ({userCredits.toLocaleString()} Cr)
                </a>
              </div>
            ) : (
              <>
                <a
                  href="#features"
                  onClick={(e) => handleAnchorClick(e, 'features')}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium cursor-pointer"
                >
                  Features
                </a>
                <a
                  href="#simulator"
                  onClick={(e) => handleAnchorClick(e, 'simulator')}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium cursor-pointer"
                >
                  Live Simulator
                </a>
                <a
                  href="#architecture"
                  onClick={(e) => handleAnchorClick(e, 'architecture')}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium cursor-pointer"
                >
                  Architecture
                </a>
                <a
                  href="#why-us"
                  onClick={(e) => handleAnchorClick(e, 'why-us')}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium cursor-pointer"
                >
                  Why Skelion
                </a>
                <a
                  href="#pricing"
                  onClick={(e) => handleAnchorClick(e, 'pricing')}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium cursor-pointer"
                >
                  Pricing
                </a>
                <a
                  href="#faq"
                  onClick={(e) => handleAnchorClick(e, 'faq')}
                  className="block text-slate-700 hover:text-cyan-600 py-1.5 font-medium cursor-pointer"
                >
                  FAQ
                </a>
              </>
            )}

            <div className="pt-3 border-t border-slate-200 flex flex-col gap-2.5">
              <a
                href="#console"
                onClick={() => setMobileMenuOpen(false)}
                className="w-full text-center py-2 rounded-lg text-xs font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 transition shadow-md"
              >
                Launch Web Console
              </a>
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  onOpenCheckout(user ? 'pro' : 'pilot');
                }}
                className="w-full text-center py-2 rounded-lg text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition"
              >
                {user ? 'Upgrade Subscription' : 'Start Free Pilot'}
              </button>
            </div>
          </div>
        )}
      </header>

      {/* GitHub OAuth Setup / Configuration Modal */}
      {showConfigModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="glass-panel w-full max-w-md rounded-2xl border border-slate-200/90 shadow-2xl p-6 bg-white/95">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center">
                  <Github className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-950">GitHub OAuth Setup</h3>
                  <p className="text-[11px] text-slate-500">Live authentication credentials</p>
                </div>
              </div>
              <button
                onClick={() => setShowConfigModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveClientIdAndLogin} className="mt-4 space-y-4">
              <div className="p-3 rounded-xl bg-cyan-50/70 border border-cyan-200/80 text-xs text-cyan-950 space-y-1.5">
                <p className="font-semibold text-cyan-900">Authenticate with your own GitHub OAuth App</p>
                <p className="text-[11px] text-cyan-800 leading-relaxed">
                  To log into Skelion with your real GitHub account, supply your GitHub OAuth App Client ID (or set <code className="font-mono bg-cyan-100 px-1 py-0.5 rounded text-cyan-900">GITHUB_CLIENT_ID</code> in Vercel environment variables).
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-800 mb-1">
                  GitHub OAuth Client ID:
                </label>
                <input
                  type="text"
                  value={inputClientId}
                  onChange={(e) => setInputClientId(e.target.value)}
                  placeholder="e.g. Ov23li... or 20-character Client ID"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 bg-white font-mono"
                  autoFocus
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Redirect Callback URL for your GitHub OAuth App should be:
                  <code className="block mt-0.5 p-1 bg-slate-100 rounded text-slate-800 font-mono break-all select-all">
                    {typeof window !== 'undefined' ? `${window.location.origin}${window.location.pathname}` : 'https://skelion-website-gilt.vercel.app/'}
                  </code>
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowConfigModal(false)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!inputClientId.trim()}
                  className="px-4 py-1.5 rounded-lg text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 transition shadow-sm flex items-center gap-1.5"
                >
                  <Github className="w-3.5 h-3.5" />
                  <span>Save & Continue to GitHub</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
