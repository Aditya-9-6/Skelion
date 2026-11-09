import React, { useState } from 'react';
import { 
  GitPullRequest, 
  Check, 
  Copy, 
  CheckCircle2, 
  Terminal, 
  ExternalLink, 
  FileCode, 
  ArrowRight, 
  Sparkles,
  GitBranch,
  ShieldCheck,
  Zap,
  Download,
  Columns,
  Rows
} from 'lucide-react';

interface FixesTabProps {
  onOpenPRUrl?: (url: string) => void;
}

interface PatchCandidate {
  id: string;
  incidentRef: string;
  title: string;
  branch: string;
  filename: string;
  unitTestsStatus: string;
  diffStats: { additions: number; deletions: number };
  originalCode: string[];
  patchedCode: string[];
  prUrl: string;
}

export const FixesTab: React.FC<FixesTabProps> = ({ onOpenPRUrl }) => {
  const [selectedPatchId, setSelectedPatchId] = useState<string>('PATCH-304');
  const [viewMode, setViewMode] = useState<'unified' | 'side-by-side'>('side-by-side');
  const [copiedPatch, setCopiedPatch] = useState(false);
  const [exportedPatch, setExportedPatch] = useState(false);
  const [prCreated, setPrCreated] = useState<string | null>(null);

  const patches: PatchCandidate[] = [
    {
      id: 'PATCH-304',
      incidentRef: 'INC-8921',
      title: 'Fix currency ISO fallback in checkout route to prevent 500 error',
      branch: 'skelion/fix-checkout-currency-500',
      filename: 'src/services/payment.ts',
      unitTestsStatus: '14/14 Unit Tests Passed (Pytest & Vitest)',
      diffStats: { additions: 7, deletions: 2 },
      originalCode: [
        'export function validateCurrency(currency?: string): string {',
        '  // Unhandled undefined causes TypeError',
        '  const normalized = currency.toUpperCase();',
        '  if (!SUPPORTED_CURRENCIES.includes(normalized)) {',
        '    throw new Error(`Unsupported currency: ${normalized}`);',
        '  }',
        '  return normalized;',
        '}'
      ],
      patchedCode: [
        'export function validateCurrency(currency?: string): string {',
        '  // Safe fallback to default USD if currency is undefined or blank',
        '  const cleanCurrency = (currency || "USD").trim();',
        '  const normalized = cleanCurrency.toUpperCase();',
        '  if (!SUPPORTED_CURRENCIES.includes(normalized)) {',
        '    console.warn(`[Skelion Interceptor] Unsupported currency ${normalized}, falling back to USD`);',
        '    return "USD";',
        '  }',
        '  return normalized;',
        '}'
      ],
      prUrl: 'https://github.com/Aditya-9-6/Skelion/pull/42'
    },
    {
      id: 'PATCH-302',
      incidentRef: 'INC-8919',
      title: 'Add exponential backoff & secondary key circuit breaker on 429 response',
      branch: 'skelion/circuit-breaker-429-fallback',
      filename: 'src/mesh/circuitBreaker.ts',
      unitTestsStatus: '9/9 Unit Tests Passed (Mock Throttler)',
      diffStats: { additions: 9, deletions: 3 },
      originalCode: [
        'export async function callUpstreamLLM(req: LLMRequest) {',
        '  const response = await fetch(req.endpoint, { headers: req.headers });',
        '  return await response.json();',
        '}'
      ],
      patchedCode: [
        'export async function callUpstreamLLM(req: LLMRequest) {',
        '  try {',
        '    return await primaryPool.dispatchWithBackoff(req, { maxRetries: 3 });',
        '  } catch (error: any) {',
        '    if (error?.status === 429) {',
        '      console.warn("[Skelion] Shifting traffic to secondary standby node");',
        '      return await secondaryPool.dispatch(req);',
        '    }',
        '    throw error;',
        '  }',
        '}'
      ],
      prUrl: 'https://github.com/Aditya-9-6/Skelion/pull/41'
    }
  ];

  const currentPatch = patches.find((p) => p.id === selectedPatchId) || patches[0];

  const handleCopyDiff = () => {
    const patchText = currentPatch.patchedCode.join('\n');
    navigator.clipboard.writeText(patchText);
    setCopiedPatch(true);
    setTimeout(() => setCopiedPatch(false), 2000);
  };

  const handleExportPatch = () => {
    const patchHeader = `From 0000000000000000000000000000000000000000 Mon Sep 17 00:00:00 2001
From: Skelion Agent <agent@skelion.ai>
Date: ${new Date().toUTCString()}
Subject: [PATCH] ${currentPatch.title}

---
 ${currentPatch.filename} | ${currentPatch.diffStats.additions + currentPatch.diffStats.deletions} +${currentPatch.diffStats.additions}/-${currentPatch.diffStats.deletions}
 1 file changed, ${currentPatch.diffStats.additions} insertions(+), ${currentPatch.diffStats.deletions} deletions(-)

diff --git a/${currentPatch.filename} b/${currentPatch.filename}
--- a/${currentPatch.filename}
+++ b/${currentPatch.filename}
@@ -1,8 +1,10 @@
${currentPatch.originalCode.map((l) => `-${l}`).join('\n')}
${currentPatch.patchedCode.map((l) => `+${l}`).join('\n')}
-- 
Skelion Autonomous Resilience Agent v0.1.4
`;
    const blob = new Blob([patchHeader], { type: 'text/x-diff;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${currentPatch.id.toLowerCase()}-${currentPatch.branch.replace(/[^a-zA-Z0-9_-]/g, '_')}.patch`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setExportedPatch(true);
    setTimeout(() => setExportedPatch(false), 2500);
  };

  const handleCreatePR = () => {
    setPrCreated(currentPatch.id);
    if (onOpenPRUrl) {
      onOpenPRUrl(currentPatch.prUrl);
    } else {
      window.open(currentPatch.prUrl, '_blank');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl p-5 shadow-[0_8px_32px_0_rgba(31,38,135,0.07)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">Synthesized PR Fixes &amp; AST Diffs</h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-cyan-50 text-cyan-700 border border-cyan-200">
              {patches.length} Patches Ready
            </span>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Verified in isolated test sandboxes before commit. Red/green diff review with one-click GitHub PR creation.
          </p>
        </div>

        {/* Patch Selector Buttons */}
        <div className="flex items-center gap-2">
          {patches.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedPatchId(p.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition ${
                selectedPatchId === p.id
                  ? 'bg-slate-900 text-white border-slate-900 shadow-xs'
                  : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
              }`}
            >
              <span>{p.id}</span>
              <span className="ml-1.5 opacity-70 font-mono">({p.incidentRef})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Diff Viewer Card */}
      <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-2xl shadow-xs overflow-hidden">
        {/* Diff Top Metadata Bar */}
        <div className="p-4 sm:p-5 border-b border-slate-200/80 bg-slate-50/70 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-bold text-slate-900">{currentPatch.id}</span>
              <span className="text-slate-400 font-mono text-xs">/</span>
              <span className="font-mono text-xs text-cyan-700 font-semibold flex items-center gap-1">
                <FileCode className="w-3.5 h-3.5" />
                {currentPatch.filename}
              </span>
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <ShieldCheck className="w-3 h-3 text-emerald-600" />
                {currentPatch.unitTestsStatus}
              </span>
            </div>

            <h3 className="text-sm font-bold text-slate-900">
              {currentPatch.title}
            </h3>

            <div className="flex items-center gap-3 text-[11px] font-mono text-slate-500 pt-0.5">
              <span className="flex items-center gap-1">
                <GitBranch className="w-3 h-3 text-slate-400" />
                {currentPatch.branch}
              </span>
              <span>·</span>
              <span className="text-emerald-600 font-semibold">+{currentPatch.diffStats.additions}</span>
              <span className="text-rose-600 font-semibold">-{currentPatch.diffStats.deletions}</span>
            </div>
          </div>

          {/* Action Buttons & View Mode Toggle */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            {/* View Mode Toggle */}
            <div className="flex items-center bg-slate-200/80 p-0.5 rounded-xl text-xs font-semibold">
              <button
                onClick={() => setViewMode('side-by-side')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg transition ${
                  viewMode === 'side-by-side' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Side-by-side split diff"
              >
                <Columns className="w-3 h-3" />
                <span>Side-by-Side</span>
              </button>
              <button
                onClick={() => setViewMode('unified')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg transition ${
                  viewMode === 'unified' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Unified line-by-line diff"
              >
                <Rows className="w-3 h-3" />
                <span>Unified</span>
              </button>
            </div>

            <button
              onClick={handleCopyDiff}
              className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition shadow-2xs"
            >
              {copiedPatch ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedPatch ? 'Copied' : 'Copy'}</span>
            </button>

            <button
              onClick={handleExportPatch}
              className="px-3.5 py-1.5 rounded-xl border border-cyan-200 bg-cyan-50/80 hover:bg-cyan-100 text-cyan-800 text-xs font-bold flex items-center gap-1.5 transition shadow-2xs"
              title="Download standard unified .patch file"
            >
              {exportedPatch ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Download className="w-3.5 h-3.5" />}
              <span>{exportedPatch ? 'Exported!' : 'Export Patch'}</span>
            </button>

            <button
              onClick={handleCreatePR}
              className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-md shadow-emerald-600/20 flex items-center gap-1.5 transition"
            >
              <GitPullRequest className="w-3.5 h-3.5" />
              <span>{prCreated === currentPatch.id ? 'PR Created' : 'Create GitHub PR'}</span>
              <ExternalLink className="w-3 h-3 opacity-80" />
            </button>
          </div>
        </div>

        {/* Visual Code Diff Display */}
        {viewMode === 'side-by-side' ? (
          /* Side-by-Side Split Diff */
          <div className="bg-slate-950 font-mono text-xs overflow-x-auto text-slate-200 grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-800">
            {/* Original Left Column */}
            <div className="p-4 sm:p-5 space-y-1">
              <div className="text-[11px] text-slate-400 font-bold mb-2 pb-1.5 border-b border-slate-800 flex items-center justify-between">
                <span className="text-rose-400">Original (--- a/{currentPatch.filename})</span>
                <span className="text-slate-500 text-[10px]">BEFORE</span>
              </div>
              {currentPatch.originalCode.map((line, idx) => (
                <div key={`side-del-${idx}`} className="flex items-start gap-2 bg-rose-950/30 text-rose-200 px-2 py-0.5 rounded-xs border-l-2 border-rose-500">
                  <span className="text-slate-500 select-none w-5 text-right shrink-0">{idx + 1}</span>
                  <span className="text-rose-400 select-none font-bold shrink-0">-</span>
                  <span className="whitespace-pre overflow-x-auto">{line}</span>
                </div>
              ))}
            </div>

            {/* Patched Right Column */}
            <div className="p-4 sm:p-5 space-y-1 bg-slate-950/70">
              <div className="text-[11px] text-slate-400 font-bold mb-2 pb-1.5 border-b border-slate-800 flex items-center justify-between">
                <span className="text-emerald-400">Patched (+++ b/{currentPatch.filename})</span>
                <span className="text-emerald-500 text-[10px] font-bold">SKELION VERIFIED</span>
              </div>
              {currentPatch.patchedCode.map((line, idx) => (
                <div key={`side-add-${idx}`} className="flex items-start gap-2 bg-emerald-950/30 text-emerald-200 px-2 py-0.5 rounded-xs border-l-2 border-emerald-500">
                  <span className="text-slate-500 select-none w-5 text-right shrink-0">{idx + 1}</span>
                  <span className="text-emerald-400 select-none font-bold shrink-0">+</span>
                  <span className="whitespace-pre overflow-x-auto">{line}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Unified Line-by-Line Code Diff */
          <div className="p-4 sm:p-6 bg-slate-950 font-mono text-xs overflow-x-auto text-slate-200">
            <div className="text-[11px] text-slate-500 mb-3 pb-2 border-b border-slate-800 flex items-center justify-between">
              <span>--- a/{currentPatch.filename} (Original)</span>
              <span>+++ b/{currentPatch.filename} (Skelion Patch)</span>
            </div>

            <div className="space-y-0.5">
              {currentPatch.originalCode.map((line, idx) => (
                <div key={`del-${idx}`} className="flex items-start gap-3 bg-rose-950/40 text-rose-200 px-2 py-0.5 rounded-xs border-l-2 border-rose-500">
                  <span className="text-slate-500 select-none w-6 text-right shrink-0">{idx + 1}</span>
                  <span className="text-rose-400 select-none font-bold shrink-0">-</span>
                  <span className="whitespace-pre">{line}</span>
                </div>
              ))}

              <div className="py-1 text-slate-600 select-none text-[10px]">@@ -1,8 +1,10 @@</div>

              {currentPatch.patchedCode.map((line, idx) => (
                <div key={`add-${idx}`} className="flex items-start gap-3 bg-emerald-950/40 text-emerald-200 px-2 py-0.5 rounded-xs border-l-2 border-emerald-500">
                  <span className="text-slate-500 select-none w-6 text-right shrink-0">{idx + 1}</span>
                  <span className="text-emerald-400 select-none font-bold shrink-0">+</span>
                  <span className="whitespace-pre">{line}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
