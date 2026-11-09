import React, { useState } from 'react';
import {
  FolderGit2,
  AlertCircle,
  GitPullRequest,
  Search,
  Plus,
  KeyRound,
  Check,
  X,
  Lock,
  Globe,
  Star,
  ExternalLink,
  ChevronDown,
  Loader2,
  CheckCircle2,
  XCircle,
  GitMerge,
  Eye,
  EyeOff,
  GitBranch,
  ShieldCheck
} from 'lucide-react';
import {
  GitHubRepoItem,
  GitHubIssueItem,
  GitHubPullRequestItem,
  getGitHubToken,
  setGitHubToken,
  removeGitHubToken
} from '../../utils/github';

interface GitHubSidebarProps {
  owner: string;
  selectedRepo: string;
  repos: GitHubRepoItem[];
  issues: GitHubIssueItem[];
  pullRequests: GitHubPullRequestItem[];
  selectedIssue: GitHubIssueItem | null;
  selectedPR: GitHubPullRequestItem | null;
  onSelectRepo: (repoName: string, repoOwner?: string) => void;
  onSelectIssue: (issue: GitHubIssueItem) => void;
  onSelectPR?: (pr: GitHubPullRequestItem) => void;
  branches?: string[];
  currentBranch?: string;
  onSelectBranch?: (branchName: string) => void;
  onCreateBranch?: (branchName: string) => Promise<void> | void;
  isLoadingBranches?: boolean;
  onCreateIssue?: (payload: { title: string; body?: string; labels?: string[] }) => Promise<void>;
  onCreatePR?: (payload: { title: string; head: string; base: string; body?: string }) => Promise<void>;
  onCloseIssue?: (number: number) => Promise<void>;
  onMergePR?: (number: number, commitMsg?: string) => Promise<void>;
  isLoadingRepos?: boolean;
  isLoadingIssues?: boolean;
  isLoadingPRs?: boolean;
  onTokenSaved?: () => void;
  onNotify?: (msg: string, variant?: 'success' | 'error' | 'info') => void;
}

export const GitHubSidebar: React.FC<GitHubSidebarProps> = ({
  owner,
  selectedRepo,
  repos,
  issues,
  pullRequests,
  selectedIssue,
  selectedPR,
  onSelectRepo,
  onSelectIssue,
  onSelectPR,
  branches = ['main', 'feat/circuit-breaker', 'patch/waf-auth', 'dev'],
  currentBranch = 'main',
  onSelectBranch,
  onCreateBranch,
  isLoadingBranches = false,
  onCreateIssue,
  onCreatePR,
  onCloseIssue,
  onMergePR,
  isLoadingRepos = false,
  isLoadingIssues = false,
  isLoadingPRs = false,
  onTokenSaved,
  onNotify,
}) => {
  const [activeTab, setActiveTab] = useState<'repos' | 'branches' | 'issues' | 'prs'>('repos');
  const [showNewBranchModal, setShowNewBranchModal] = useState(false);
  const [newBranchInput, setNewBranchInput] = useState('');
  const [isCreatingBranch, setIsCreatingBranch] = useState(false);

  // Token Management State
  const [tokenInput, setTokenInput] = useState(() => getGitHubToken() || '');
  const [hasToken, setHasToken] = useState(() => Boolean(getGitHubToken()));
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [isTokenVisible, setIsTokenVisible] = useState(false);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'open' | 'closed'>('open');

  // Create Issue Modal State
  const [showNewIssueModal, setShowNewIssueModal] = useState(false);
  const [newIssueTitle, setNewIssueTitle] = useState('');
  const [newIssueBody, setNewIssueBody] = useState('');
  const [newIssueLabels, setNewIssueLabels] = useState('bug, resilience');
  const [isCreatingIssue, setIsCreatingIssue] = useState(false);

  // Create PR Modal State
  const [showNewPRModal, setShowNewPRModal] = useState(false);
  const [newPRTitle, setNewPRTitle] = useState('');
  const [newPRHead, setNewPRHead] = useState('patch/resilience-failover');
  const [newPRBase, setNewPRBase] = useState('main');
  const [newPRBody, setNewPRBody] = useState('');
  const [isCreatingPR, setIsCreatingPR] = useState(false);

  // Save Token Handler
  const handleSaveToken = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = tokenInput.trim();
    if (!trimmed) {
      removeGitHubToken();
      setHasToken(false);
      onNotify?.('GitHub token removed. Switched to public access mode.', 'info');
    } else {
      setGitHubToken(trimmed);
      setHasToken(true);
      onNotify?.('GitHub PAT saved to localStorage. Private repos & actions enabled!', 'success');
    }
    setShowTokenInput(false);
    onTokenSaved?.();
  };

  const handleClearToken = () => {
    removeGitHubToken();
    setTokenInput('');
    setHasToken(false);
    onNotify?.('GitHub token cleared.', 'info');
    onTokenSaved?.();
  };

  // Create Issue Submit Handler
  const handleSubmitIssue = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newIssueTitle.trim() || isCreatingIssue) return;
    setIsCreatingIssue(true);
    try {
      const labels = newIssueLabels
        .split(',')
        .map((l) => l.trim())
        .filter(Boolean);
      await onCreateIssue?.({
        title: newIssueTitle.trim(),
        body: newIssueBody.trim(),
        labels,
      });
      setNewIssueTitle('');
      setNewIssueBody('');
      setShowNewIssueModal(false);
      if (!onCreateIssue) {
        onNotify?.('Issue created successfully!', 'success');
      }
    } catch (err: any) {
      onNotify?.(`Failed to create issue: ${err.message}`, 'error');
    } finally {
      setIsCreatingIssue(false);
    }
  };

  // Create PR Submit Handler
  const handleSubmitPR = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPRTitle.trim() || isCreatingPR) return;
    setIsCreatingPR(true);
    try {
      await onCreatePR?.({
        title: newPRTitle.trim(),
        head: newPRHead.trim(),
        base: newPRBase.trim(),
        body: newPRBody.trim(),
      });
      setNewPRTitle('');
      setNewPRBody('');
      setShowNewPRModal(false);
      if (!onCreatePR) {
        onNotify?.('Pull request created successfully!', 'success');
      }
    } catch (err: any) {
      onNotify?.(`Failed to create PR: ${err.message}`, 'error');
    } finally {
      setIsCreatingPR(false);
    }
  };

  // Filter Repos
  const filteredRepos = repos.filter(
    (r) =>
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.description && r.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  // Filter Issues
  const filteredIssues = issues.filter((i) => {
    const matchesSearch =
      i.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      String(i.number).includes(searchQuery);
    if (statusFilter === 'all') return matchesSearch;
    return matchesSearch && i.state === statusFilter;
  });

  // Filter PRs
  const filteredPRs = pullRequests.filter((pr) => {
    const matchesSearch =
      pr.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      String(pr.number).includes(searchQuery);
    if (statusFilter === 'all') return matchesSearch;
    return matchesSearch && pr.state === statusFilter;
  });

  return (
    <div className="flex flex-col h-full overflow-hidden select-none font-sans">
      {/* 1. Top PAT Token Banner / Settings */}
      <div className="border-b border-slate-200/90 bg-slate-50/80 p-2.5 space-y-1.5 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <KeyRound className="w-3.5 h-3.5 text-cyan-600" />
            <span className="text-[11px] font-bold text-slate-800 font-mono">GitHub Access</span>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setShowTokenInput((prev) => !prev)}
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition flex items-center gap-1 border cursor-pointer ${
                hasToken
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-300 hover:bg-emerald-100'
                  : 'bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100'
              }`}
              title="Configure Personal Access Token"
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${hasToken ? 'bg-emerald-500' : 'bg-amber-500'}`}
              />
              <span>{hasToken ? 'PAT Active' : 'Set Token'}</span>
              <ChevronDown
                className={`w-3 h-3 transition-transform ${showTokenInput ? 'rotate-180' : ''}`}
              />
            </button>
          </div>
        </div>

        {/* Collapsible Token Input Field */}
        {showTokenInput && (
          <form
            onSubmit={handleSaveToken}
            className="p-2 rounded-xl bg-white border border-slate-200 shadow-sm space-y-1.5 animate-fade-in"
          >
            <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
              <span>Personal Access Token (PAT):</span>
              <button
                type="button"
                onClick={() => setIsTokenVisible((v) => !v)}
                className="text-slate-400 hover:text-slate-700 flex items-center gap-0.5"
              >
                {isTokenVisible ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                <span>{isTokenVisible ? 'Hide' : 'Show'}</span>
              </button>
            </div>

            <div className="relative">
              <input
                type={isTokenVisible ? 'text' : 'password'}
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="ghp_... or github_pat_..."
                className="w-full pl-2 pr-7 py-1 text-xs font-mono bg-slate-50 border border-slate-200 rounded-md text-slate-900 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
              {tokenInput && (
                <button
                  type="button"
                  onClick={() => setTokenInput('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            <p className="text-[9px] text-slate-400 font-sans leading-tight">
              Stored securely in localStorage. Token requires <code className="text-cyan-700 font-mono">repo</code> scope for private repos and PR merging.
            </p>

            <div className="flex items-center justify-end gap-1.5 pt-1">
              {hasToken && (
                <button
                  type="button"
                  onClick={handleClearToken}
                  className="px-2 py-0.5 rounded text-[10px] font-sans font-semibold text-rose-600 hover:bg-rose-50"
                >
                  Clear
                </button>
              )}
              <button
                type="submit"
                className="px-2.5 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-[11px] font-sans font-bold transition shadow-2xs cursor-pointer flex items-center gap-1"
              >
                <Check className="w-3 h-3" />
                <span>Save</span>
              </button>
            </div>
          </form>
        )}
      </div>

      {/* 2. Three Tabs: Repos, Issues, PRs */}
      <div className="border-b border-slate-200/90 bg-white/70 px-2 py-1 flex items-center gap-1 shrink-0">
        <button
          onClick={() => setActiveTab('repos')}
          className={`flex-1 py-1 px-2 rounded-lg text-xs font-mono transition flex items-center justify-center gap-1.5 ${
            activeTab === 'repos'
              ? 'bg-cyan-50 text-cyan-900 font-bold border border-cyan-200 shadow-2xs'
              : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
          }`}
        >
          <FolderGit2 className={`w-3.5 h-3.5 ${activeTab === 'repos' ? 'text-cyan-600' : 'text-slate-400'}`} />
          <span>Repos</span>
          <span className="text-[10px] px-1 rounded-full bg-slate-200/70 text-slate-700">
            {repos.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('branches')}
          className={`flex-1 py-1 px-2 rounded-lg text-xs font-mono transition flex items-center justify-center gap-1.5 ${
            activeTab === 'branches'
              ? 'bg-cyan-50 text-cyan-900 font-bold border border-cyan-200 shadow-2xs'
              : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
          }`}
        >
          <GitBranch className={`w-3.5 h-3.5 ${activeTab === 'branches' ? 'text-cyan-600' : 'text-slate-400'}`} />
          <span>Branches</span>
          <span className="text-[10px] px-1 rounded-full bg-slate-200/70 text-slate-700">
            {branches.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('issues')}
          className={`flex-1 py-1 px-2 rounded-lg text-xs font-mono transition flex items-center justify-center gap-1.5 ${
            activeTab === 'issues'
              ? 'bg-cyan-50 text-cyan-900 font-bold border border-cyan-200 shadow-2xs'
              : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
          }`}
        >
          <AlertCircle className={`w-3.5 h-3.5 ${activeTab === 'issues' ? 'text-emerald-600' : 'text-slate-400'}`} />
          <span>Issues</span>
          <span className="text-[10px] px-1 rounded-full bg-slate-200/70 text-slate-700">
            {issues.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('prs')}
          className={`flex-1 py-1 px-2 rounded-lg text-xs font-mono transition flex items-center justify-center gap-1.5 ${
            activeTab === 'prs'
              ? 'bg-cyan-50 text-cyan-900 font-bold border border-cyan-200 shadow-2xs'
              : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
          }`}
        >
          <GitPullRequest className={`w-3.5 h-3.5 ${activeTab === 'prs' ? 'text-purple-600' : 'text-slate-400'}`} />
          <span>PRs</span>
          <span className="text-[10px] px-1 rounded-full bg-slate-200/70 text-slate-700">
            {pullRequests.length}
          </span>
        </button>
      </div>

      {/* 3. Search Bar & Status Filters */}
      <div className="p-2 border-b border-slate-100 bg-white/50 space-y-1.5 shrink-0">
        <div className="relative">
          <Search className="w-3 h-3 text-slate-400 absolute left-2 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={
              activeTab === 'repos'
                ? 'Filter repositories...'
                : activeTab === 'branches'
                ? 'Filter branches in repo...'
                : activeTab === 'issues'
                ? 'Filter issues in repo...'
                : 'Filter pull requests...'
            }
            className="w-full pl-6 pr-6 py-1 text-[11px] bg-slate-50 border border-slate-200 rounded-md text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-mono"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Filter Pills & Create Button for Branches / Issues / PRs */}
        {activeTab === 'branches' && (
          <div className="flex items-center justify-between text-[10px] font-mono">
            <span className="text-slate-500 text-[10px]">
              Active: <strong className="text-cyan-800">{currentBranch}</strong>
            </span>
            <button
              onClick={() => setShowNewBranchModal(true)}
              className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold transition shadow-2xs cursor-pointer font-sans"
            >
              <Plus className="w-3 h-3" />
              <span>New Branch</span>
            </button>
          </div>
        )}

        {(activeTab === 'issues' || activeTab === 'prs') && (
          <div className="flex items-center justify-between text-[10px] font-mono">
            <div className="inline-flex rounded-md p-0.5 bg-slate-100 border border-slate-200">
              {(['open', 'closed', 'all'] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setStatusFilter(filter)}
                  className={`px-1.5 py-0.5 rounded capitalize ${
                    statusFilter === filter
                      ? 'bg-white text-slate-900 font-bold shadow-2xs'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>

            {activeTab === 'issues' && (
              <button
                onClick={() => setShowNewIssueModal(true)}
                className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold transition shadow-2xs cursor-pointer font-sans"
              >
                <Plus className="w-3 h-3" />
                <span>New Issue</span>
              </button>
            )}

            {activeTab === 'prs' && (
              <button
                onClick={() => setShowNewPRModal(true)}
                className="flex items-center gap-1 px-2 py-0.5 rounded bg-purple-600 hover:bg-purple-500 text-white font-bold transition shadow-2xs cursor-pointer font-sans"
              >
                <Plus className="w-3 h-3" />
                <span>New PR</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* 4. Scrollable List Content for Active Tab */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-1 text-xs">
        {/* ======================= TAB: REPOS ======================= */}
        {activeTab === 'repos' && (
          <>
            {isLoadingRepos ? (
              <div className="text-center py-6 text-xs text-slate-400 font-mono flex flex-col items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-cyan-600" />
                <span>Loading repositories...</span>
              </div>
            ) : filteredRepos.length > 0 ? (
              filteredRepos.map((r) => {
                const isSelected = r.name === selectedRepo;
                return (
                  <button
                    key={r.name}
                    onClick={() => onSelectRepo(r.name, r.owner?.login || owner)}
                    className={`w-full text-left p-2 rounded-xl border transition flex flex-col gap-1 ${
                      isSelected
                        ? 'bg-cyan-50/90 text-cyan-950 font-bold border-cyan-300 shadow-2xs'
                        : 'bg-white/60 hover:bg-slate-100 text-slate-800 border-slate-200/70'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center gap-1.5 truncate">
                        <FolderGit2
                          className={`w-3.5 h-3.5 shrink-0 ${
                            isSelected ? 'text-cyan-600' : 'text-slate-400'
                          }`}
                        />
                        <span className="truncate font-semibold text-xs">{r.name}</span>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {r.private ? (
                          <span
                            className="px-1 py-0.2 rounded text-[9px] font-mono bg-amber-100 text-amber-800 border border-amber-200 flex items-center gap-0.5"
                            title="Private repository"
                          >
                            <Lock className="w-2.5 h-2.5" />
                            <span>priv</span>
                          </span>
                        ) : (
                          <span
                            className="px-1 py-0.2 rounded text-[9px] font-mono bg-slate-100 text-slate-600 border border-slate-200 flex items-center gap-0.5"
                            title="Public repository"
                          >
                            <Globe className="w-2.5 h-2.5" />
                            <span>pub</span>
                          </span>
                        )}
                      </div>
                    </div>

                    {r.description && (
                      <p className="text-[10px] text-slate-500 font-sans line-clamp-1 text-left">
                        {r.description}
                      </p>
                    )}

                    <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-0.5">
                      <span>{r.language || 'TypeScript'}</span>
                      <div className="flex items-center gap-2">
                        {typeof r.stars === 'number' && r.stars > 0 && (
                          <span className="flex items-center gap-0.5 text-amber-600">
                            <Star className="w-2.5 h-2.5 fill-amber-500" />
                            {r.stars}
                          </span>
                        )}
                        <span>{r.default_branch || 'main'}</span>
                      </div>
                    </div>
                  </button>
                );
              })
            ) : (
              <div className="text-center py-6 text-xs text-slate-400 font-mono">
                No repositories found
              </div>
            )}
          </>
        )}

        {/* ======================= TAB: BRANCHES ======================= */}
        {activeTab === 'branches' && (
          <>
            {isLoadingBranches ? (
              <div className="text-center py-6 text-xs text-slate-400 font-mono flex flex-col items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-cyan-600" />
                <span>Loading branches for {selectedRepo}...</span>
              </div>
            ) : branches.filter((b) => b.toLowerCase().includes(searchQuery.toLowerCase())).length > 0 ? (
              branches
                .filter((b) => b.toLowerCase().includes(searchQuery.toLowerCase()))
                .map((branch) => {
                  const isActive = branch === currentBranch;
                  return (
                    <button
                      key={branch}
                      type="button"
                      onClick={() => onSelectBranch?.(branch)}
                      className={`w-full text-left p-2 rounded-xl border transition flex items-center justify-between gap-2 cursor-pointer ${
                        isActive
                          ? 'bg-cyan-50 text-cyan-950 font-bold border-cyan-300 shadow-2xs'
                          : 'bg-white/70 hover:bg-slate-100 text-slate-800 border-slate-200/70'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <GitBranch
                          className={`w-3.5 h-3.5 shrink-0 ${
                            isActive ? 'text-cyan-600' : 'text-slate-400'
                          }`}
                        />
                        <span className="font-mono text-xs truncate">{branch}</span>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {isActive ? (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                            <Check className="w-2.5 h-2.5" />
                            <span>active</span>
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-400 font-sans hover:text-cyan-700">
                            Switch →
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })
            ) : (
              <div className="text-center py-6 text-xs text-slate-400 font-mono space-y-2">
                <p>No branches matching "{searchQuery}"</p>
                <button
                  onClick={() => {
                    setNewBranchInput(searchQuery.trim());
                    setShowNewBranchModal(true);
                  }}
                  className="px-3 py-1 rounded-lg bg-cyan-50 text-cyan-700 hover:bg-cyan-100 border border-cyan-200 font-sans font-semibold text-xs"
                >
                  + Create "{searchQuery.trim()}"
                </button>
              </div>
            )}
          </>
        )}

        {/* ======================= TAB: ISSUES ======================= */}
        {activeTab === 'issues' && (
          <>
            {isLoadingIssues ? (
              <div className="text-center py-6 text-xs text-slate-400 font-mono flex flex-col items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-cyan-600" />
                <span>Loading issues for {selectedRepo}...</span>
              </div>
            ) : filteredIssues.length > 0 ? (
              filteredIssues.map((issue) => {
                const isSelected = selectedIssue?.number === issue.number;
                const isOpen = issue.state === 'open';

                return (
                  <div
                    key={issue.number}
                    onClick={() => onSelectIssue(issue)}
                    className={`w-full text-left p-2 rounded-xl border transition flex flex-col gap-1 cursor-pointer ${
                      isSelected
                        ? 'bg-cyan-50 text-cyan-950 font-bold border-cyan-300 shadow-2xs'
                        : 'bg-white/70 hover:bg-slate-100 text-slate-800 border-slate-200/70'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-1.5">
                      <div className="flex items-start gap-1.5 truncate">
                        {isOpen ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                        ) : (
                          <CheckCircle2 className="w-3.5 h-3.5 text-purple-400 shrink-0 mt-0.5" />
                        )}
                        <div className="truncate">
                          <div className="text-xs font-semibold leading-tight line-clamp-2">
                            {issue.title}
                          </div>
                        </div>
                      </div>

                      <span className="text-[10px] font-mono text-slate-400 shrink-0">
                        #{issue.number}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-0.5">
                      <span>by @{issue.user?.login || 'user'}</span>
                      <div className="flex items-center gap-1.5">
                        {isOpen && onCloseIssue && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onCloseIssue(issue.number);
                            }}
                            className="px-1.5 py-0.2 rounded bg-slate-100 hover:bg-rose-50 text-slate-500 hover:text-rose-600 text-[9px] font-sans font-semibold transition"
                            title="Quick close issue"
                          >
                            Close
                          </button>
                        )}
                        <span
                          className={`px-1 py-0.2 rounded text-[9px] uppercase font-bold ${
                            isOpen
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {issue.state}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-6 text-xs text-slate-400 font-mono space-y-2">
                <p>No {statusFilter !== 'all' ? statusFilter : ''} issues in {selectedRepo}</p>
                <button
                  onClick={() => setShowNewIssueModal(true)}
                  className="px-3 py-1 rounded-lg bg-cyan-50 text-cyan-700 hover:bg-cyan-100 border border-cyan-200 font-sans font-semibold text-xs"
                >
                  + Create First Issue
                </button>
              </div>
            )}
          </>
        )}

        {/* ======================= TAB: PRS ======================= */}
        {activeTab === 'prs' && (
          <>
            {isLoadingPRs ? (
              <div className="text-center py-6 text-xs text-slate-400 font-mono flex flex-col items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-purple-600" />
                <span>Loading pull requests for {selectedRepo}...</span>
              </div>
            ) : filteredPRs.length > 0 ? (
              filteredPRs.map((pr) => {
                const isSelected = selectedPR?.number === pr.number;
                const isMerged = Boolean(pr.merged || pr.merged_at);
                const isOpen = pr.state === 'open';

                return (
                  <div
                    key={pr.number}
                    onClick={() => onSelectPR?.(pr)}
                    className={`w-full text-left p-2 rounded-xl border transition flex flex-col gap-1 cursor-pointer ${
                      isSelected
                        ? 'bg-purple-50 text-purple-950 font-bold border-purple-300 shadow-2xs'
                        : 'bg-white/70 hover:bg-slate-100 text-slate-800 border-slate-200/70'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-1.5">
                      <div className="flex items-start gap-1.5 truncate">
                        {isMerged ? (
                          <GitMerge className="w-3.5 h-3.5 text-purple-500 shrink-0 mt-0.5" />
                        ) : isOpen ? (
                          <GitPullRequest className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                        )}
                        <div className="truncate">
                          <div className="text-xs font-semibold leading-tight line-clamp-2">
                            {pr.title}
                          </div>
                        </div>
                      </div>

                      <span className="text-[10px] font-mono text-slate-400 shrink-0">
                        #{pr.number}
                      </span>
                    </div>

                    {pr.head?.ref && (
                      <div className="flex items-center gap-1 text-[10px] font-mono text-slate-500">
                        <GitBranch className="w-2.5 h-2.5 text-purple-500" />
                        <span className="truncate">{pr.head.ref}</span>
                        <span>➔</span>
                        <span>{pr.base?.ref || 'main'}</span>
                      </div>
                    )}

                    <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-0.5">
                      <span>by @{pr.user?.login || 'user'}</span>
                      <div className="flex items-center gap-1.5">
                        {isOpen && onMergePR && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onMergePR(pr.number);
                            }}
                            className="px-1.5 py-0.2 rounded bg-purple-100 hover:bg-purple-200 text-purple-800 text-[9px] font-sans font-semibold transition"
                            title="Quick merge pull request"
                          >
                            Merge
                          </button>
                        )}
                        <span
                          className={`px-1 py-0.2 rounded text-[9px] uppercase font-bold ${
                            isMerged
                              ? 'bg-purple-100 text-purple-800'
                              : isOpen
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {isMerged ? 'merged' : pr.state}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-6 text-xs text-slate-400 font-mono space-y-2">
                <p>No {statusFilter !== 'all' ? statusFilter : ''} PRs in {selectedRepo}</p>
                <button
                  onClick={() => setShowNewPRModal(true)}
                  className="px-3 py-1 rounded-lg bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 font-sans font-semibold text-xs"
                >
                  + Create First PR
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* 5. Create New Issue Modal */}
      {showNewIssueModal && (
        <div className="p-3 bg-cyan-50/90 border-t border-cyan-200 space-y-2 animate-fade-in shrink-0">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-cyan-900 font-mono">+ New Issue in {selectedRepo}</span>
            <button
              onClick={() => setShowNewIssueModal(false)}
              className="text-slate-400 hover:text-slate-700 p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <form onSubmit={handleSubmitIssue} className="space-y-1.5 text-xs">
            <input
              type="text"
              value={newIssueTitle}
              onChange={(e) => setNewIssueTitle(e.target.value)}
              placeholder="Issue title..."
              required
              className="w-full px-2.5 py-1 bg-white border border-cyan-300 rounded-md text-slate-900 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-sans"
            />
            <textarea
              rows={2}
              value={newIssueBody}
              onChange={(e) => setNewIssueBody(e.target.value)}
              placeholder="Description (markdown supported)..."
              className="w-full px-2.5 py-1 bg-white border border-cyan-300 rounded-md text-slate-900 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-sans resize-none text-[11px]"
            />
            <input
              type="text"
              value={newIssueLabels}
              onChange={(e) => setNewIssueLabels(e.target.value)}
              placeholder="Labels (comma separated)..."
              className="w-full px-2.5 py-1 bg-white border border-cyan-300 rounded-md text-slate-700 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-mono text-[10px]"
            />
            <div className="flex items-center justify-end gap-1.5 pt-1">
              <button
                type="button"
                onClick={() => setShowNewIssueModal(false)}
                className="px-2.5 py-1 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isCreatingIssue || !newIssueTitle.trim()}
                className="px-3 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold transition flex items-center gap-1 shadow-2xs"
              >
                {isCreatingIssue && <Loader2 className="w-3 h-3 animate-spin" />}
                <span>Create Issue</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 6. Create New Pull Request Modal */}
      {showNewPRModal && (
        <div className="p-3 bg-purple-50/90 border-t border-purple-200 space-y-2 animate-fade-in shrink-0">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-purple-900 font-mono">+ New PR in {selectedRepo}</span>
            <button
              onClick={() => setShowNewPRModal(false)}
              className="text-slate-400 hover:text-slate-700 p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <form onSubmit={handleSubmitPR} className="space-y-1.5 text-xs">
            <input
              type="text"
              value={newPRTitle}
              onChange={(e) => setNewPRTitle(e.target.value)}
              placeholder="PR title (e.g. feat: add failover circuit breaker)..."
              required
              className="w-full px-2.5 py-1 bg-white border border-purple-300 rounded-md text-slate-900 focus:outline-none focus:ring-1 focus:ring-purple-500 font-sans"
            />
            <div className="grid grid-cols-2 gap-1.5 font-mono text-[10px]">
              <div>
                <span className="text-slate-500 text-[9px]">Head branch:</span>
                <input
                  type="text"
                  value={newPRHead}
                  onChange={(e) => setNewPRHead(e.target.value)}
                  placeholder="head branch"
                  className="w-full px-2 py-1 bg-white border border-purple-300 rounded text-slate-900"
                />
              </div>
              <div>
                <span className="text-slate-500 text-[9px]">Base branch:</span>
                <input
                  type="text"
                  value={newPRBase}
                  onChange={(e) => setNewPRBase(e.target.value)}
                  placeholder="base branch"
                  className="w-full px-2 py-1 bg-white border border-purple-300 rounded text-slate-900"
                />
              </div>
            </div>
            <textarea
              rows={2}
              value={newPRBody}
              onChange={(e) => setNewPRBody(e.target.value)}
              placeholder="PR summary & resolution details..."
              className="w-full px-2.5 py-1 bg-white border border-purple-300 rounded-md text-slate-900 focus:outline-none focus:ring-1 focus:ring-purple-500 font-sans resize-none text-[11px]"
            />
            <div className="flex items-center justify-end gap-1.5 pt-1">
              <button
                type="button"
                onClick={() => setShowNewPRModal(false)}
                className="px-2.5 py-1 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isCreatingPR || !newPRTitle.trim()}
                className="px-3 py-1 rounded bg-purple-600 hover:bg-purple-500 text-white font-bold transition flex items-center gap-1 shadow-2xs"
              >
                {isCreatingPR && <Loader2 className="w-3 h-3 animate-spin" />}
                <span>Create PR</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 7. Create New Branch Modal */}
      {showNewBranchModal && (
        <div className="p-3 bg-cyan-50/90 border-t border-cyan-200 space-y-2 animate-fade-in shrink-0">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-cyan-900 font-mono">
              + New Branch in {selectedRepo}
            </span>
            <button
              onClick={() => setShowNewBranchModal(false)}
              className="text-slate-400 hover:text-slate-700 p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const trimmed = newBranchInput.trim();
              if (!trimmed || isCreatingBranch) return;
              setIsCreatingBranch(true);
              try {
                await onCreateBranch?.(trimmed);
                setNewBranchInput('');
                setShowNewBranchModal(false);
                onNotify?.(`Created and switched to branch "${trimmed}"`, 'success');
              } catch (err: any) {
                onNotify?.(`Failed to create branch: ${err.message}`, 'error');
              } finally {
                setIsCreatingBranch(false);
              }
            }}
            className="space-y-1.5 text-xs"
          >
            <div>
              <span className="text-[10px] font-mono text-slate-500">
                Source: <strong>{currentBranch}</strong>
              </span>
              <input
                type="text"
                value={newBranchInput}
                onChange={(e) => setNewBranchInput(e.target.value)}
                placeholder="e.g. feat/circuit-breaker-v2"
                required
                className="w-full mt-1 px-2.5 py-1 bg-white border border-cyan-300 rounded-md text-slate-900 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-mono text-xs"
              />
            </div>

            <div className="flex items-center justify-end gap-1.5 pt-1">
              <button
                type="button"
                onClick={() => setShowNewBranchModal(false)}
                className="px-2.5 py-1 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isCreatingBranch || !newBranchInput.trim()}
                className="px-3 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold transition flex items-center gap-1 shadow-2xs"
              >
                {isCreatingBranch && <Loader2 className="w-3 h-3 animate-spin" />}
                <span>Create &amp; Switch</span>
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
