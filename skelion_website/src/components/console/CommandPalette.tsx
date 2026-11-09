import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  FileCode, 
  FolderGit2, 
  GitBranch, 
  Sun, 
  Moon, 
  Play, 
  Save, 
  GitCommit, 
  Plus, 
  X, 
  Command, 
  ArrowRight,
  Terminal
} from 'lucide-react';
import { GitHubRepoItem } from '../../utils/github';

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  files: { path: string; type: 'file' | 'dir' }[];
  onOpenFile: (path: string) => void;
  repos: GitHubRepoItem[];
  currentRepo: string;
  onSelectRepo: (repoName: string) => void;
  branches?: string[];
  currentBranch?: string;
  onSelectBranch?: (branchName: string) => void;
  onCreateBranch?: (branchName: string) => void;
  onToggleTheme: () => void;
  isDarkTheme: boolean;
  onRunTests: () => void;
  onSaveFile: () => void;
  onCommitPatch: () => void;
  onNewConversation: () => void;
}

interface PaletteItem {
  id: string;
  category: 'Actions' | 'Files' | 'Repositories' | 'Branches';
  title: string;
  subtitle?: string;
  icon: React.FC<{ className?: string }>;
  action: () => void;
  badge?: string;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  files,
  onOpenFile,
  repos,
  currentRepo,
  onSelectRepo,
  branches = ['main', 'feat/circuit-breaker', 'patch/waf-auth', 'dev'],
  currentBranch = 'main',
  onSelectBranch,
  onCreateBranch,
  onToggleTheme,
  isDarkTheme,
  onRunTests,
  onSaveFile,
  onCommitPatch,
  onNewConversation,
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Global Ctrl+K / Cmd+K and Esc listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Trigger open via parent or event
        }
      } else if (e.key === 'Escape' && isOpen) {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Build items list based on query
  const items: PaletteItem[] = [];

  // Actions
  const actionItems: PaletteItem[] = [
    {
      id: 'act-tests',
      category: 'Actions',
      title: 'Run All Test Suites',
      subtitle: 'Execute live AST & chaos resilience test runners',
      icon: Play,
      badge: 'Test Runner',
      action: () => {
        onRunTests();
        onClose();
      },
    },
    {
      id: 'act-theme',
      category: 'Actions',
      title: `Switch to ${isDarkTheme ? 'Light' : 'Dark'} IDE Theme`,
      subtitle: `Currently using ${isDarkTheme ? 'Dark IDE' : 'Light Glassmorphic'} theme`,
      icon: isDarkTheme ? Sun : Moon,
      badge: 'Appearance',
      action: () => {
        onToggleTheme();
        onClose();
      },
    },
    {
      id: 'act-save',
      category: 'Actions',
      title: 'Save Active File',
      subtitle: 'Persist changes to local memory and verify AST invariants',
      icon: Save,
      badge: 'Ctrl+S',
      action: () => {
        onSaveFile();
        onClose();
      },
    },
    {
      id: 'act-commit',
      category: 'Actions',
      title: 'Commit Active Patch to Git',
      subtitle: 'Commit changes to current branch with signed telemetry',
      icon: GitCommit,
      badge: 'Git',
      action: () => {
        onCommitPatch();
        onClose();
      },
    },
    {
      id: 'act-new-chat',
      category: 'Actions',
      title: 'Start New Conversation',
      subtitle: `Fresh incident investigation session in ${currentRepo}`,
      icon: Plus,
      badge: 'Ask Agent',
      action: () => {
        onNewConversation();
        onClose();
      },
    },
  ];

  const filteredActions = actionItems.filter(
    (a) =>
      a.title.toLowerCase().includes(query.toLowerCase()) ||
      (a.subtitle && a.subtitle.toLowerCase().includes(query.toLowerCase()))
  );
  items.push(...filteredActions);

  // Files
  const onlyFiles = files.filter((f) => f.type === 'file');
  const filteredFiles = onlyFiles
    .filter((f) => f.path.toLowerCase().includes(query.toLowerCase()))
    .slice(0, 15)
    .map((f) => ({
      id: `file-${f.path}`,
      category: 'Files' as const,
      title: f.path.split('/').pop() || f.path,
      subtitle: f.path,
      icon: FileCode,
      badge: f.path.split('.').pop() || 'file',
      action: () => {
        onOpenFile(f.path);
        onClose();
      },
    }));
  items.push(...filteredFiles);

  // Repositories
  const filteredRepos = repos
    .filter((r) => r.name.toLowerCase().includes(query.toLowerCase()))
    .slice(0, 6)
    .map((r) => ({
      id: `repo-${r.name}`,
      category: 'Repositories' as const,
      title: r.name,
      subtitle: r.description || 'GitHub Repository',
      icon: FolderGit2,
      badge: r.name === currentRepo ? 'Active Repo' : 'Switch',
      action: () => {
        onSelectRepo(r.name);
        onClose();
      },
    }));
  items.push(...filteredRepos);

  // Branches
  const filteredBranches = branches
    .filter((b) => b.toLowerCase().includes(query.toLowerCase()))
    .slice(0, 6)
    .map((b) => ({
      id: `branch-${b}`,
      category: 'Branches' as const,
      title: b,
      subtitle: `Git Branch in ${currentRepo}`,
      icon: GitBranch,
      badge: b === currentBranch ? 'Active Branch' : 'Checkout',
      action: () => {
        onSelectBranch?.(b);
        onClose();
      },
    }));
  items.push(...filteredBranches);

  // Auto-scroll selected item into view
  useEffect(() => {
    if (listRef.current && listRef.current.children[selectedIndex]) {
      (listRef.current.children[selectedIndex] as HTMLElement).scrollIntoView?.({
        block: 'nearest',
      });
    }
  }, [selectedIndex]);

  // If query is a valid git branch candidate and doesn't match an existing branch, offer to create it
  const trimmedQuery = query.trim();
  const isValidBranchCandidate =
    trimmedQuery.length > 0 &&
    trimmedQuery.length <= 60 &&
    /^[a-zA-Z0-9_\-\.\/]+$/.test(trimmedQuery) &&
    !trimmedQuery.endsWith('/') &&
    !trimmedQuery.startsWith('/') &&
    !branches.includes(trimmedQuery);

  if (isValidBranchCandidate && onCreateBranch) {
    items.push({
      id: `create-branch-${trimmedQuery}`,
      category: 'Branches',
      title: `Create branch "${trimmedQuery}"`,
      subtitle: `Create new branch from ${currentBranch}`,
      icon: Plus,
      badge: 'New Branch',
      action: () => {
        onCreateBranch(trimmedQuery);
        onClose();
      },
    });
  }

  // Handle arrow key navigation & enter
  const handleKeyDownList = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (items.length > 0 ? (prev + 1) % items.length : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (items.length > 0 ? (prev - 1 + items.length) % items.length : 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (items[selectedIndex]) {
        items[selectedIndex].action();
      }
    }
  };

  return (
    <div
      onClick={onClose}
      className={`fixed inset-0 z-[9999999] bg-slate-950/60 backdrop-blur-md flex items-start justify-center pt-16 sm:pt-24 p-4 animate-fade-in select-none ${isDarkTheme ? "dark" : ""}`}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-xl bg-white/95 dark:bg-slate-900/95 backdrop-blur-2xl border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[540px] text-slate-800 dark:text-slate-100"
      >
        {/* Search Input Bar */}
        <div className="p-3.5 border-b border-slate-200/80 dark:border-slate-800 flex items-center gap-3 shrink-0 bg-slate-50/50 dark:bg-slate-950/50">
          <Command className="w-4 h-4 text-cyan-600 dark:text-cyan-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDownList}
            placeholder="Type a command, search files, switch repos, or branches... (Ctrl+K)"
            className="w-full bg-transparent text-sm font-sans focus:outline-none placeholder-slate-400 dark:placeholder-slate-500 text-slate-900 dark:text-white"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono rounded bg-slate-200/70 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-300 dark:border-slate-700">
            Esc
          </kbd>
        </div>

        {/* Scrollable Results List */}
        <div ref={listRef} className="flex-1 overflow-y-auto p-2 space-y-1">
          {items.length > 0 ? (
            items.map((item, index) => {
              const isSelected = index === selectedIndex;
              const Icon = item.icon;

              return (
                <div
                  key={item.id}
                  onClick={item.action}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`px-3 py-2 rounded-xl flex items-center justify-between text-xs cursor-pointer transition ${
                    isSelected
                      ? 'bg-cyan-50 dark:bg-cyan-950/60 text-cyan-950 dark:text-cyan-200 font-semibold border border-cyan-200/80 dark:border-cyan-800/80 shadow-2xs'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <div
                      className={`p-1.5 rounded-lg shrink-0 ${
                        isSelected
                          ? 'bg-cyan-500 text-white'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </div>

                    <div className="truncate">
                      <div className="truncate font-medium">{item.title}</div>
                      {item.subtitle && (
                        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-mono truncate">
                          {item.subtitle}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {item.badge && (
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                        {item.badge}
                      </span>
                    )}
                    {isSelected && <ArrowRight className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="text-center py-8 text-xs text-slate-400 dark:text-slate-500 font-mono">
              No matching commands or files found for "{query}"
            </div>
          )}
        </div>

        {/* Footer Shortcut Hints */}
        <div className="p-2.5 border-t border-slate-200/80 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/70 text-[10px] font-mono text-slate-500 dark:text-slate-400 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>Esc Close</span>
          </div>
          <div className="flex items-center gap-1 text-cyan-600 dark:text-cyan-400">
            <span>Skelion Fast Command Mesh</span>
          </div>
        </div>
      </div>
    </div>
  );
};
