import React, { useState, useEffect } from 'react';
import {
  Shield,
  FileText,
  Lock,
  RefreshCcw,
  Code,
  Mail,
  Search,
  ExternalLink,
  Download,
  Menu,
  X,
  CheckCircle2,
} from 'lucide-react';
import { LEGAL_DOCUMENTS } from '../types/legal';

interface HeaderProps {
  onOpenSearch: () => void;
  activeSection: string;
}

export const Header: React.FC<HeaderProps> = ({ onOpenSearch, activeSection }) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const totalScroll = window.scrollY || document.documentElement.scrollTop;
      const windowHeight =
        document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const progress = windowHeight > 0 ? (totalScroll / windowHeight) * 100 : 0;
      setScrollProgress(Math.min(100, Math.max(0, progress)));
      setIsScrolled(window.scrollY > 20);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navItems = [
    { id: 'overview', label: 'Trust Hub', icon: Shield },
    { id: 'terms', label: 'Terms', icon: FileText },
    { id: 'privacy', label: 'Privacy', icon: Lock },
    { id: 'refund', label: 'Refunds', icon: RefreshCcw },
    { id: 'security', label: 'Security', icon: Lock },
    { id: 'licenses', label: 'Licenses', icon: Code },
    { id: 'contact', label: 'Grievance', icon: Mail },
  ];

  const handleDownloadBundle = () => {
    let markdownContent = `# SKELION PLATFORM — COMPLETE LEGAL & COMPLIANCE BUNDLE\n`;
    markdownContent += `Published: November 6, 2026 | Effective Date: November 1, 2026\n`;
    markdownContent += `Publisher: Skelion Platform | DPDP Act 2023 & GDPR Aligned\n\n`;
    markdownContent += `---\n\n`;

    LEGAL_DOCUMENTS.forEach((doc) => {
      markdownContent += `## ${doc.title.toUpperCase()}\n`;
      markdownContent += `*Last Revised: ${doc.lastUpdated} | Category: ${doc.categoryBadge}*\n\n`;
      markdownContent += `> ${doc.summaryQuote}\n\n`;

      doc.clauses.forEach((c) => {
        markdownContent += `### Clause ${c.number} — ${c.title}\n`;
        markdownContent += `**Plain-English Summary:** ${c.summary}\n\n`;
        c.content.forEach((p) => {
          markdownContent += `${p}\n\n`;
        });
      });
      markdownContent += `---\n\n`;
    });

    const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'skelion-legal-and-compliance-pack.md');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 3000);
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 glass-header ${
        isScrolled
          ? 'bg-[#050811]/85 backdrop-blur-xl border-b border-white/10 shadow-[0_4px_30px_rgba(0,0,0,0.5)]'
          : 'bg-transparent border-b border-white/5 backdrop-blur-md'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo & Brand Element */}
          <a href="#overview" className="flex items-center gap-3.5 group flex-shrink-0">
            <div className="relative w-10 h-10 flex items-center justify-center rounded-xl bg-gradient-to-br from-cyan-950/60 to-slate-900/80 border border-cyan-500/40 shadow-[0_0_20px_rgba(0,242,254,0.25)] group-hover:border-cyan-400 group-hover:shadow-[0_0_25px_rgba(0,242,254,0.45)] transition-all">
              <img
                src="/skelion_logo_white.svg"
                alt="Skelion Shield Logo"
                className="w-6 h-6 object-contain filter drop-shadow-[0_0_10px_rgba(0,242,254,0.7)] group-hover:scale-110 transition-transform duration-300"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = '/icon.svg';
                }}
              />
              <span className="absolute -bottom-1 -right-1 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-[#050811] shadow-[0_0_8px_#00f5a0]" />
            </div>

            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-lg font-black tracking-wider text-white font-mono group-hover:text-cyan-300 transition-colors">
                  SKELION
                </span>
                <span className="text-[10px] uppercase font-mono font-bold tracking-widest px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  LEGAL
                </span>
              </div>
              <span className="text-[11px] text-slate-400 font-mono tracking-tight hidden sm:inline">
                Trust & Compliance Architecture
              </span>
            </div>
          </a>

          {/* Desktop Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1 bg-white/[0.04] p-1.5 rounded-full border border-white/10 backdrop-blur-md">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_15px_rgba(0,242,254,0.25)]'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </a>
              );
            })}
          </nav>

          {/* Action Tools */}
          <div className="flex items-center gap-2.5">
            {/* Quick Clause Search Trigger */}
            <button
              onClick={onOpenSearch}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 hover:border-cyan-500/30 text-slate-300 text-xs transition-all backdrop-blur-md"
              title="Search all legal clauses (Ctrl+K)"
            >
              <Search className="w-3.5 h-3.5 text-cyan-400" />
              <span className="hidden md:inline font-mono text-[11px] text-slate-400">Search Clauses</span>
              <kbd className="hidden md:inline-block px-1.5 py-0.5 text-[9px] font-mono text-slate-400 bg-white/5 border border-white/10 rounded">
                ⌘K
              </kbd>
            </button>

            {/* Download Legal Pack Button */}
            <button
              onClick={handleDownloadBundle}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs font-mono transition-all"
              title="Download full Markdown compliance bundle"
            >
              {downloadSuccess ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Saved .MD</span>
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5" />
                  <span>Legal Pack</span>
                </>
              )}
            </button>

            {/* Web Platform Console Link */}
            <a
              href="#console"
              className="hidden md:flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 text-xs font-bold font-mono tracking-tight shadow-[0_0_20px_rgba(0,242,254,0.3)] transition-all hover:scale-105"
            >
              <span>Console</span>
              <ExternalLink className="w-3 h-3" />
            </a>

            {/* Mobile Hamburger Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-xl bg-white/5 border border-white/10 text-slate-300 hover:text-white"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Reading Progress Indicator Bar */}
      <div className="w-full h-[2px] bg-white/5">
        <div
          className="h-full bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 transition-all duration-150"
          style={{ width: `${scrollProgress}%` }}
        />
      </div>

      {/* Mobile Glass Dropdown Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-[#070b14]/95 backdrop-blur-2xl border-b border-white/10 px-4 py-5 space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2 p-2.5 rounded-xl text-xs font-medium border ${
                    isActive
                      ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300'
                      : 'bg-white/5 border-white/5 text-slate-300 hover:bg-white/10'
                  }`}
                >
                  <Icon className="w-4 h-4 text-cyan-400" />
                  <span>{item.label}</span>
                </a>
              );
            })}
          </div>

          <div className="pt-3 border-t border-white/10 flex items-center justify-between gap-3">
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                handleDownloadBundle();
              }}
              className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-white/5 border border-white/10 text-xs text-slate-300"
            >
              <Download className="w-3.5 h-3.5 text-cyan-400" />
              <span>Download Pack</span>
            </button>

            <a
              href="#console"
              className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-cyan-500 text-slate-950 font-bold text-xs font-mono"
            >
              <span>Web Console</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      )}
    </header>
  );
};
