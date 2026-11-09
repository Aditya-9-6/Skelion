import React, { useState } from 'react';
import { Terminal, Copy, Check, Code, Box, Sparkles } from 'lucide-react';

export const SdkQuickstart: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'python' | 'node' | 'docker' | 'cli'>('python');
  const [copied, setCopied] = useState(false);

  const snippets = {
    python: {
      lang: 'Python (FastAPI / Starlette)',
      cmd: 'pip install skelion',
      code: `# main.py
from fastapi import FastAPI
from skelion import SkelionMiddleware

app = FastAPI(title="My High-Scale Service")

# Attach Skelion fail-open resilience proxy
app.add_middleware(
    SkelionMiddleware,
    api_key="skl_live_xxxxxxxxxxxxxx",
    fail_open=True,              # Guarantees zero downtime
    redact_pii=True,             # Masks auth tokens & cookies
    error_threshold=0.25,        # Triggers automated PR fix
)

@app.get("/checkout/pay")
async def checkout():
    # If this raises an unhandled exception, Skelion intercepts,
    # reproduces it in a sandbox, and opens a self-healing PR!
    return {"status": "ok"}`,
    },
    node: {
      lang: 'Node.js (Express / Fastify)',
      cmd: 'npm install skelion-node',
      code: `// server.js
import express from 'express';
import { skelionMiddleware } from 'skelion-node';

const app = express();

// Enable autonomous resilience & PII scrubbing
app.use(skelionMiddleware({
  apiKey: process.env.SKELION_API_KEY,
  failOpen: true,
  autoRemediate: true,
  endpoint: 'http://localhost:8080'
}));

app.post('/api/order', (req, res) => {
  res.json({ success: true });
});

app.listen(3000, () => console.log('Server online with Skelion'));`,
    },
    docker: {
      lang: 'Docker Compose (Full Production Stack)',
      cmd: 'docker compose -f docker-compose.skelion.yml up -d',
      code: `# docker-compose.skelion.yml
version: '3.8'

services:
  # Edge Proxy (Fail-open reverse proxy)
  skelion-edge:
    image: skelion/edge:latest
    ports:
      - "8080:8080"
    environment:
      - UPSTREAM_URL=http://app:8000
      - FAIL_OPEN=true
      - PROMETHEUS_METRICS=true

  # Control Plane (Autonomous Fix Engine & Key-Pool)
  skelion-control:
    image: skelion/control:latest
    ports:
      - "8002:8002"
    environment:
      - RAZORPAY_KEY_ID=rzp_test_TwvOwcT2gnvSnv
      - RAZORPAY_KEY_SECRET=u0SYjUylpWoR3bUuiDno4KCs
      - REDIS_URL=redis://redis:6379/0

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"`,
    },
    cli: {
      lang: 'Skelion CLI (Terminal Tooling)',
      cmd: 'curl -fsSL https://skelion.dev/install.sh | sh',
      code: `# Run autonomous diagnostic scan on active repo
skelion scan --deep --auto-test

# Launch local fail-open edge proxy on port 8080
skelion edge --port 8080 --upstream http://localhost:8000

# Inspect active token quota and Razorpay subscription tier
skelion quota --status

# Stream live incident telemetry
skelion logs --follow --tail 50`,
    },
  };

  const current = snippets[activeTab];

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="docs" className="py-24 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-50 border border-cyan-200 text-cyan-800 mb-3 shadow-sm">
            <Code className="w-3.5 h-3.5 text-cyan-600" />
            <span>DEVELOPER QUICKSTART</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-slate-950 tracking-tight">
            Integrate in 60 Seconds
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-600">
            Native multi-language SDKs, zero code refactors, and simple drop-in middleware.
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="max-w-4xl mx-auto">
          <div className="flex flex-wrap items-center justify-center gap-2 mb-6">
            {(['python', 'node', 'docker', 'cli'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition flex items-center gap-2 ${
                  activeTab === tab
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold shadow-md shadow-cyan-500/20'
                    : 'bg-white/80 backdrop-blur-md text-slate-700 hover:text-slate-900 border border-slate-200 hover:border-slate-300 shadow-sm'
                }`}
              >
                {tab === 'python' && <Code className="w-4 h-4" />}
                {tab === 'node' && <Sparkles className="w-4 h-4" />}
                {tab === 'docker' && <Box className="w-4 h-4" />}
                {tab === 'cli' && <Terminal className="w-4 h-4" />}
                <span>{tab.toUpperCase()}</span>
              </button>
            ))}
          </div>

          {/* Quick Install Bar */}
          <div className="p-3.5 rounded-xl bg-white/90 border border-slate-200 shadow-sm flex items-center justify-between gap-3 mb-4 font-mono text-xs">
            <span className="text-slate-800 font-semibold">{current.cmd}</span>
            <button
              onClick={() => handleCopy(current.cmd)}
              className="px-3 py-1 rounded bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200 hover:border-slate-300 transition flex items-center gap-1.5 shadow-sm"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
              <span>Copy</span>
            </button>
          </div>

          {/* Code Sandbox View */}
          <div className="rounded-2xl border border-slate-800 overflow-hidden bg-slate-950 shadow-2xl">
            <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <span className="text-xs font-mono text-slate-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                {current.lang}
              </span>
              <button
                onClick={() => handleCopy(current.code)}
                className="text-xs text-slate-400 hover:text-white transition flex items-center gap-1 font-mono"
              >
                <Copy className="w-3.5 h-3.5" />
                <span>Copy Code</span>
              </button>
            </div>
            <pre className="p-6 text-xs sm:text-sm font-mono text-cyan-300 overflow-x-auto leading-relaxed">
              <code>{current.code}</code>
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
};
