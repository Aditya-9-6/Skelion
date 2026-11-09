import React, { useEffect, useRef, useState } from 'react';
import { Code2, Sparkles, Copy, Check } from 'lucide-react';

export interface MonacoEditorProps {
  value: string;
  onChange?: (value: string) => void;
  language?: string;
  theme?: 'vs-dark' | 'vs';
  readOnly?: boolean;
  minimap?: boolean;
  onSave?: () => void;
  className?: string;
  path?: string;
}

declare global {
  interface Window {
    monaco?: any;
    require?: any;
  }
}

let isMonacoScriptLoading = false;
let monacoLoadPromise: Promise<any> | null = null;

function loadMonacoFromCDN(): Promise<any> {
  if (typeof window === 'undefined') return Promise.reject(new Error('Window not available'));
  if (window.monaco) return Promise.resolve(window.monaco);
  if (monacoLoadPromise) return monacoLoadPromise;

  monacoLoadPromise = new Promise((resolve, reject) => {
    const existingScript = document.getElementById('monaco-loader-script');
    if (existingScript && window.require) {
      window.require.config({
        paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' },
      });
      window.require(
        ['vs/editor/editor.main'],
        () => resolve(window.monaco),
        (err: any) => {
          monacoLoadPromise = null;
          reject(err);
        }
      );
      return;
    }

    if (isMonacoScriptLoading) {
      const interval = setInterval(() => {
        if (window.monaco) {
          clearInterval(interval);
          resolve(window.monaco);
        }
      }, 50);
      return;
    }

    isMonacoScriptLoading = true;
    const script = document.createElement('script');
    script.id = 'monaco-loader-script';
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.min.js';
    script.async = true;
    script.onload = () => {
      if (window.require) {
        window.require.config({
          paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' },
        });
        window.require(
          ['vs/editor/editor.main'],
          () => resolve(window.monaco),
          (err: any) => {
            monacoLoadPromise = null;
            isMonacoScriptLoading = false;
            reject(err);
          }
        );
      } else {
        monacoLoadPromise = null;
        isMonacoScriptLoading = false;
        reject(new Error('Monaco loader require not found'));
      }
    };
    script.onerror = (err) => {
      monacoLoadPromise = null;
      isMonacoScriptLoading = false;
      reject(err);
    };
    document.head.appendChild(script);
  });

  return monacoLoadPromise;
}

export const MonacoEditor: React.FC<MonacoEditorProps> = ({
  value,
  onChange,
  language = 'typescript',
  theme = 'vs-dark',
  readOnly = false,
  minimap = true,
  onSave,
  className = '',
  path,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorInstanceRef = useRef<any>(null);
  const [isMonacoReady, setIsMonacoReady] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);
  const previousPathRef = useRef<string | undefined>(path);

  // Normalize language for Monaco
  const monacoLanguage =
    language === 'ts' || language === 'tsx' ? 'typescript' :
    language === 'js' || language === 'jsx' ? 'javascript' :
    language === 'py' ? 'python' :
    language === 'json' ? 'json' :
    language === 'md' ? 'markdown' :
    language === 'sql' ? 'sql' :
    language === 'html' ? 'html' :
    language === 'css' ? 'css' :
    language || 'plaintext';

  // Initialize Monaco Editor
  useEffect(() => {
    let isCancelled = false;

    loadMonacoFromCDN()
      .then((monaco) => {
        if (isCancelled || !containerRef.current) return;

        if (editorInstanceRef.current) {
          editorInstanceRef.current.dispose();
          editorInstanceRef.current = null;
        }

        const editor = monaco.editor.create(containerRef.current, {
          value,
          language: monacoLanguage,
          theme,
          readOnly,
          minimap: { enabled: minimap },
          fontSize: 12,
          fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, Monaco, Consolas, monospace",
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          cursorBlinking: 'smooth',
          smoothScrolling: true,
          padding: { top: 10, bottom: 10 },
          bracketPairColorization: { enabled: true },
        });

        editor.onDidChangeModelContent(() => {
          const updatedValue = editor.getValue();
          onChange?.(updatedValue);
        });

        // Add save command Ctrl+S / Cmd+S
        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
          onSave?.();
        });

        editorInstanceRef.current = editor;
        setIsMonacoReady(true);
      })
      .catch((_) => {
        if (!isCancelled) {
          setLoadError(true);
        }
      });

    return () => {
      isCancelled = true;
      if (editorInstanceRef.current) {
        editorInstanceRef.current.dispose();
        editorInstanceRef.current = null;
      }
    };
  }, []);

  // Update editor value if changed externally
  useEffect(() => {
    if (editorInstanceRef.current) {
      const currentValue = editorInstanceRef.current.getValue();
      if (currentValue !== value) {
        const isDifferentFile = previousPathRef.current !== path;
        previousPathRef.current = path;
        const position = isDifferentFile ? null : editorInstanceRef.current.getPosition();
        editorInstanceRef.current.setValue(value);
        if (position) {
          editorInstanceRef.current.setPosition(position);
        } else {
          editorInstanceRef.current.setPosition({ lineNumber: 1, column: 1 });
          editorInstanceRef.current.revealPosition({ lineNumber: 1, column: 1 });
        }
      }
    }
  }, [value, path]);

  // Update theme dynamically
  useEffect(() => {
    if (editorInstanceRef.current && window.monaco) {
      window.monaco.editor.setTheme(theme);
    }
  }, [theme]);

  // Update language dynamically
  useEffect(() => {
    if (editorInstanceRef.current && window.monaco) {
      const model = editorInstanceRef.current.getModel();
      if (model) {
        window.monaco.editor.setModelLanguage(model, monacoLanguage);
      }
    }
  }, [monacoLanguage]);

  // Update readOnly dynamically
  useEffect(() => {
    if (editorInstanceRef.current) {
      editorInstanceRef.current.updateOptions({ readOnly, minimap: { enabled: minimap } });
    }
  }, [readOnly, minimap]);

  // Synchronized scroll for fallback textarea
  const handleScrollFallback = () => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  const handleKeyDownFallback = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const val = textarea.value;
      const updated = val.substring(0, start) + '  ' + val.substring(end);
      onChange?.(updated);
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2;
      }, 0);
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      onSave?.();
    }
  };

  const isDark = theme === 'vs-dark';

  return (
    <div className={`relative w-full h-full flex flex-col overflow-hidden ${className}`}>
      {/* Real Monaco Editor Mount Point */}
      <div
        ref={containerRef}
        className={`w-full h-full ${isMonacoReady && !loadError ? 'block' : 'hidden'}`}
      />

      {/* Pristine Glassmorphic Embedded Editor with Minimap Fallback (Shown while loading or if CDN blocked) */}
      {(!isMonacoReady || loadError) && (
        <div
          className={`flex-1 flex overflow-hidden ${
            isDark ? 'bg-[#0b1120] text-slate-100' : 'bg-slate-50 text-slate-900'
          }`}
        >
          {/* Synchronized Line Numbers */}
          <div
            ref={lineNumbersRef}
            className={`w-12 py-3 pr-3 text-right select-none border-r font-mono text-[11px] overflow-hidden shrink-0 ${
              isDark ? 'border-slate-800 text-slate-600 bg-slate-950/40' : 'border-slate-200 text-slate-400 bg-white/50'
            }`}
          >
            {(value || '').split('\n').map((_, i) => (
              <div key={i} className="leading-6">
                {i + 1}
              </div>
            ))}
          </div>

          {/* Editable Code Area */}
          <div className="flex-1 relative overflow-hidden">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange?.(e.target.value)}
              onScroll={handleScrollFallback}
              onKeyDown={handleKeyDownFallback}
              readOnly={readOnly}
              spellCheck={false}
              wrap="off"
              placeholder="// Type or paste code here..."
              className={`w-full h-full p-3 font-mono text-[12px] leading-6 bg-transparent resize-none focus:outline-none overflow-auto ${
                isDark
                  ? 'text-slate-200 selection:bg-cyan-900/60 placeholder-slate-600'
                  : 'text-slate-900 selection:bg-cyan-200 placeholder-slate-400'
              }`}
            />
          </div>

          {/* Glassmorphic Minimap Sidebar Preview */}
          {minimap && (
            <div
              className={`w-28 py-2 px-1.5 border-l overflow-hidden select-none shrink-0 hidden md:block opacity-75 ${
                isDark
                  ? 'bg-slate-950/60 border-slate-800/80 text-slate-500'
                  : 'bg-white/70 border-slate-200 text-slate-400'
              }`}
            >
              <div className="text-[7px] font-mono leading-[9px] pointer-events-none transform scale-90 origin-top-left overflow-hidden h-full">
                {(value || '').split('\n').slice(0, 80).map((line, idx) => (
                  <div key={idx} className="truncate">
                    <span
                      className={
                        line.trim().startsWith('//')
                          ? 'text-slate-500'
                          : line.includes('function') || line.includes('const') || line.includes('export')
                          ? 'text-cyan-400'
                          : line.includes('return')
                          ? 'text-purple-400'
                          : ''
                      }
                    >
                      {line.slice(0, 36) || ' '}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
