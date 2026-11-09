import React, { useState } from 'react';
import type { LegalDocument } from '../types/legal';
import {
  Scale,
  ShieldCheck,
  RefreshCcw,
  Lock,
  Code,
  Mail,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  BookOpen,
  FileText,
  Sparkles,
} from 'lucide-react';

interface LegalSectionProps {
  document: LegalDocument;
}

export const LegalSection: React.FC<LegalSectionProps> = ({ document }) => {
  const [expandedClauses, setExpandedClauses] = useState<Record<string, boolean>>(() => {
    // Default first 2 clauses expanded
    const initial: Record<string, boolean> = {};
    document.clauses.forEach((c, idx) => {
      initial[c.id] = idx < 2;
    });
    return initial;
  });

  const [copiedClauseId, setCopiedClauseId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'both' | 'summary' | 'legal'>('both');

  const toggleClause = (id: string) => {
    setExpandedClauses((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const toggleAll = (expand: boolean) => {
    const updated: Record<string, boolean> = {};
    document.clauses.forEach((c) => {
      updated[c.id] = expand;
    });
    setExpandedClauses(updated);
  };

  const handleCopyLink = (clauseId: string) => {
    const url = `${window.location.origin}${window.location.pathname}#${document.slug}-${clauseId}`;
    navigator.clipboard.writeText(url);
    setCopiedClauseId(clauseId);
    setTimeout(() => setCopiedClauseId(null), 2500);
  };

  // Icon mapping
  const renderIcon = () => {
    switch (document.iconName) {
      case 'Scale':
        return <Scale className="w-6 h-6 text-cyan-400" />;
      case 'ShieldCheck':
        return <ShieldCheck className="w-6 h-6 text-emerald-400" />;
      case 'RefreshCcw':
        return <RefreshCcw className="w-6 h-6 text-amber-400" />;
      case 'Lock':
        return <Lock className="w-6 h-6 text-blue-400" />;
      case 'Code':
        return <Code className="w-6 h-6 text-purple-400" />;
      case 'Mail':
        return <Mail className="w-6 h-6 text-cyan-400" />;
      default:
        return <FileText className="w-6 h-6 text-cyan-400" />;
    }
  };

  const getAccentBorder = () => {
    switch (document.accentColor) {
      case 'cyan':
        return 'border-cyan-500/30';
      case 'emerald':
        return 'border-emerald-500/30';
      case 'amber':
        return 'border-amber-500/30';
      case 'purple':
        return 'border-purple-500/30';
      case 'blue':
        return 'border-blue-500/30';
      default:
        return 'border-white/10';
    }
  };

  return (
    <section
      id={document.slug}
      className="relative min-h-screen py-24 px-4 sm:px-6 lg:px-8 flex items-center justify-center z-10"
    >
      <div className="max-w-5xl w-full mx-auto space-y-8">
        {/* Main Glassmorphic Container */}
        <div
          className={`glass-panel p-6 sm:p-10 lg:p-12 rounded-3xl border ${getAccentBorder()} shadow-glass relative overflow-hidden backdrop-blur-2xl bg-[#090e1c]/80`}
        >
          {/* Subtle Ambient Radial Highlight */}
          <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

          {/* Section Header */}
          <div className="relative z-10 space-y-6 pb-8 border-b border-white/10">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-white/5 border border-white/10 shadow-inner">
                  {renderIcon()}
                </div>
                <div>
                  <span className="text-[11px] font-mono uppercase tracking-widest px-2.5 py-0.5 rounded-full bg-white/5 text-cyan-300 border border-white/10">
                    {document.categoryBadge}
                  </span>
                  <div className="text-xs font-mono text-slate-400 mt-1">
                    Last Revised: {document.lastUpdated}
                  </div>
                </div>
              </div>

              {/* View Mode Controls */}
              <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 text-xs font-mono">
                <button
                  onClick={() => setViewMode('both')}
                  className={`px-3 py-1 rounded-lg transition-all ${
                    viewMode === 'both' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Both
                </button>
                <button
                  onClick={() => setViewMode('summary')}
                  className={`px-3 py-1 rounded-lg transition-all ${
                    viewMode === 'summary' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  TL;DR Only
                </button>
                <button
                  onClick={() => setViewMode('legal')}
                  className={`px-3 py-1 rounded-lg transition-all ${
                    viewMode === 'legal' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Legal Text
                </button>
              </div>
            </div>

            <div>
              <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
                {document.title}
              </h2>
              <p className="mt-2 text-sm sm:text-base text-slate-300 leading-relaxed max-w-3xl">
                {document.subtitle}
              </p>
            </div>

            {/* Summary Quote Glass Banner */}
            <div className="glass-card-accent p-4 sm:p-5 rounded-2xl border border-cyan-500/20 flex items-start gap-3.5">
              <Sparkles className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs sm:text-sm text-slate-200 font-medium italic leading-relaxed">
                "{document.summaryQuote}"
              </p>
            </div>

            {/* Expand / Collapse All Controls */}
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 pt-2">
              <span>{document.clauses.length} Formal Provisions</span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => toggleAll(true)}
                  className="hover:text-cyan-400 transition-colors"
                >
                  Expand All
                </button>
                <span>•</span>
                <button
                  onClick={() => toggleAll(false)}
                  className="hover:text-cyan-400 transition-colors"
                >
                  Collapse All
                </button>
              </div>
            </div>
          </div>

          {/* Clauses List */}
          <div className="relative z-10 divide-y divide-white/10 mt-6 space-y-6">
            {document.clauses.map((clause) => {
              const isExpanded = !!expandedClauses[clause.id];
              const isCopied = copiedClauseId === clause.id;

              return (
                <article
                  key={clause.id}
                  id={`${document.slug}-${clause.id}`}
                  className="pt-6 first:pt-0 space-y-4 group"
                >
                  {/* Clause Header Bar */}
                  <div
                    onClick={() => toggleClause(clause.id)}
                    className="flex items-center justify-between cursor-pointer py-1"
                  >
                    <div className="flex items-center gap-3">
                      <span className="clause-number text-sm sm:text-base text-cyan-400 bg-cyan-950/40 px-2.5 py-1 rounded-lg border border-cyan-500/30">
                        § {clause.number}
                      </span>
                      <h3 className="text-base sm:text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">
                        {clause.title}
                      </h3>
                      {clause.badge && (
                        <span className="hidden sm:inline-block clause-badge bg-white/5 border border-white/10 text-slate-300">
                          {clause.badge}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCopyLink(clause.id);
                        }}
                        className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-all"
                        title="Copy permalink to this clause"
                      >
                        {isCopied ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>

                      <div className="p-1.5 rounded-lg bg-white/5 text-slate-400 group-hover:text-white transition-all">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Plain English Summary Pill */}
                  {(viewMode === 'both' || viewMode === 'summary') && (
                    <div className="bg-cyan-950/20 border-l-2 border-cyan-400 p-3.5 rounded-r-xl">
                      <div className="flex items-center gap-2 text-[11px] font-mono font-bold text-cyan-400 uppercase tracking-wider mb-1">
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>Plain-English Summary (TL;DR)</span>
                      </div>
                      <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-sans">
                        {clause.summary}
                      </p>
                    </div>
                  )}

                  {/* Full Legal Text (Collapsible) */}
                  {(viewMode === 'both' || viewMode === 'legal') && isExpanded && (
                    <div className="space-y-3 pt-2 text-xs sm:text-sm text-slate-300 leading-relaxed font-sans">
                      {clause.content.map((paragraph, pIdx) => (
                        <p key={pIdx} className="text-slate-300/90">
                          {paragraph}
                        </p>
                      ))}

                      {clause.highlights && (
                        <div className="flex flex-wrap items-center gap-2 pt-2">
                          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                            Key Guarantees:
                          </span>
                          {clause.highlights.map((highlight, hIdx) => (
                            <span
                              key={hIdx}
                              className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-white/5 border border-white/10 text-cyan-300"
                            >
                              ✓ {highlight}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>

          {/* Bottom Action Footer for Document */}
          <div className="relative z-10 mt-10 pt-6 border-t border-white/10 flex flex-wrap items-center justify-between gap-4 text-xs font-mono text-slate-400">
            <div>
              Governed under laws of India & DPDP Act 2023. Valid for Skelion v0.1.4+.
            </div>
            <a
              href="#overview"
              className="hover:text-cyan-400 transition-colors flex items-center gap-1"
            >
              <span>↑ Back to Trust Hub</span>
            </a>
          </div>
        </div>
      </div>
    </section>
  );
};
