import React, { useState, useEffect, useRef } from 'react';
import { Search, X, ArrowRight } from 'lucide-react';
import { LEGAL_DOCUMENTS } from '../types/legal';
import type { LegalClause, LegalDocument } from '../types/legal';

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectClause: (documentSlug: string, clauseId: string) => void;
}

interface SearchResult {
  doc: LegalDocument;
  clause: LegalClause;
  matchedText: string;
}

export const SearchModal: React.FC<SearchModalProps> = ({ isOpen, onClose, onSelectClause }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
      setResults([]);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    const cleanQuery = query.toLowerCase().trim();
    const hits: SearchResult[] = [];

    LEGAL_DOCUMENTS.forEach((doc) => {
      doc.clauses.forEach((clause) => {
        const inTitle = clause.title.toLowerCase().includes(cleanQuery);
        const inSummary = clause.summary.toLowerCase().includes(cleanQuery);
        const inContent = clause.content.some((p) => p.toLowerCase().includes(cleanQuery));

        if (inTitle || inSummary || inContent) {
          let matchedSnippet = clause.summary;
          if (inContent) {
            const foundPara = clause.content.find((p) => p.toLowerCase().includes(cleanQuery));
            if (foundPara) matchedSnippet = foundPara;
          }
          hits.push({
            doc,
            clause,
            matchedText: matchedSnippet,
          });
        }
      });
    });

    setResults(hits);
  }, [query]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 sm:px-6">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-[#050811]/80 backdrop-blur-xl transition-opacity"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-2xl bg-[#090e1c]/95 border border-white/15 rounded-2xl shadow-2xl overflow-hidden z-10 backdrop-blur-2xl">
        {/* Search Input Bar */}
        <div className="p-4 border-b border-white/10 flex items-center gap-3">
          <Search className="w-5 h-5 text-cyan-400" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search clauses across all legal policies (e.g. refund, telemetry, code ownership, DPDP)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-transparent text-sm sm:text-base text-white placeholder-slate-400 focus:outline-none font-sans"
          />
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/5"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Results Body */}
        <div className="max-h-[60vh] overflow-y-auto p-4 space-y-3">
          {query.trim() === '' ? (
            <div className="py-8 text-center text-slate-400 text-xs font-mono space-y-2">
              <p>Type keywords to search through formal legal terms.</p>
              <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                {['zero code retention', 'refund guarantee', 'egress', 'MIT license', 'grievance officer', 'arbitration'].map(
                  (term) => (
                    <button
                      key={term}
                      onClick={() => setQuery(term)}
                      className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-cyan-400 border border-white/10 text-[11px]"
                    >
                      "{term}"
                    </button>
                  )
                )}
              </div>
            </div>
          ) : results.length === 0 ? (
            <div className="py-8 text-center text-slate-400 text-xs font-mono">
              No legal clauses matched "{query}".
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-[11px] font-mono text-slate-400 px-2 pb-1">
                {results.length} matching {results.length === 1 ? 'clause' : 'clauses'} found:
              </div>
              {results.map(({ doc, clause, matchedText }) => (
                <div
                  key={`${doc.slug}-${clause.id}`}
                  onClick={() => {
                    onSelectClause(doc.slug, clause.id);
                    onClose();
                  }}
                  className="p-3.5 rounded-xl bg-white/5 hover:bg-cyan-500/10 border border-white/5 hover:border-cyan-500/30 cursor-pointer transition-all group"
                >
                  <div className="flex items-center justify-between text-xs font-mono text-cyan-400 mb-1">
                    <span className="flex items-center gap-1.5">
                      <span className="text-slate-400">{doc.shortTitle}</span>
                      <span>›</span>
                      <span>§ {clause.number} {clause.title}</span>
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                  </div>
                  <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                    {matchedText}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="p-3 bg-white/[0.02] border-t border-white/5 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Navigate with mouse or touch</span>
          <div className="flex items-center gap-1.5">
            <kbd className="px-1.5 py-0.5 rounded bg-white/10 border border-white/10 text-[9px]">ESC</kbd>
            <span>to close</span>
          </div>
        </div>
      </div>
    </div>
  );
};
