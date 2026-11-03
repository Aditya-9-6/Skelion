# Skelion — Full Autonomous Software Development Platform (VS Code)

## Master Architecture & Implementation Blueprint

> **Goal:** Transform the Skelion VS Code extension from a chat assistant into an end-to-end Autonomous Software Development Platform (SDP) — unifying multi-file coding, terminal & testing workflows, Claude Code & ChatGPT plugin compatibility via MCP, and Google Jules-style autonomous PR & CI repair.

---

## 1. The 5 Core Pillars of Skelion SDP

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SKELION SOFTWARE DEVELOPMENT PLATFORM                     │
│                        (VS Code Extension Cockpit)                           │
├──────────────┬────────────────┬───────────────┬──────────────┬──────────────┤
│ 💬 Chat &    │ 🔌 Plugins &   │ 🚀 Jules PR   │ 🧪 Test &    │ 📊 Incident  │
│ Copilot      │ MCP Hub        │ & CI Control  │ Workspace    │ & Replay     │
│ (Antigravity/│ (Claude/OpenAI │ (5-stage auto │ (TDD runner, │ (Sandbox,    │
│ Codex blocks)│ compatibility) │ cycle & merge)│ lint, fixes) │ 0-regression)│
└──────────────┴────────────────┴───────────────┴──────────────┴──────────────┘
                               ▲ postMessage protocol ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EXTENSION HOST CORE                              │
│  ├─ PluginManager (stdio/SSE MCP client, Claude & ChatGPT config loader)    │
│  ├─ WorkspaceEngine (multi-file read/edit/diff, symbol search, AST patcher) │
│  ├─ TerminalOrchestrator (dev server, test runner, background watcher)      │
│  ├─ PRController (GitHub Git Data API, check run watcher, review loops)     │
│  └─ SecuritySandboxing (strict CSP, credential redaction, user approvals)   │
└─────────────────────────────────────────────────────────────────────────────┘
                               ▲ HTTP / SSE / REST ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SKELION LOCAL/HOSTED DAEMON                         │
│  ├─ Universal MCP Host (routes tool calls between LLM & active plugins)     │
│  ├─ Model Orchestrator (Claude 3.7/3.5, GPT-4o, Gemini 2.0/Pro, Local Ollama)│
│  ├─ Replay Sandbox (verifies fixes against traffic before PR creation)      │
│  └─ Autonomous Repair Engine (diagnoses failures, synthesizes code patches) │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pillar Breakdown & Feature Targets

### Pillar 1: Universal Plugin & MCP Hub (Claude Code & ChatGPT Compatible)
- **Model Context Protocol (MCP) Standard**: Connects to any `stdio` or `sse` MCP server (PostgreSQL, SQLite, Docker, GitHub, Sentry, Brave Search, Slack, Linear, Filesystem).
- **1-Click Claude Code Import**: Reads `claude_desktop_config.json` and `.claude.json` to automatically activate all tools the developer already configured for Claude.
- **ChatGPT Action Ingestion**: Accepts OpenAPI 3.0/3.1 JSON or URL and auto-binds endpoints as callable tools.
- **Plugin UI in Extension**: Tab with active status indicators, tool counts, test execution, environment variable storage via VS Code `SecretStorage`.

### Pillar 2: Autonomous Workspace & Code Engine
- **Multi-File Creation & Editing**: Safely propose changes across multiple repository files with native VS Code diff previews.
- **In-Place File Actions**: `[Apply Patch]`, `[Insert at Cursor]`, `[Copy Section]`, `[Discard]`.
- **AST Patcher**: Targeted syntax-tree modifications preventing formatting breaks.

### Pillar 3: Google Jules Autonomous PR & CI Engine
- **Remote PR Creation**: Pure GitHub API branch creation and commit authoring without mutating the developer's local checkout.
- **5-Stage Real-Time Lifecycle**: Branch creation ➔ CI checks ➔ Merge conflicts ➔ Review feedback ➔ Merge readiness.
- **Autonomous Repair Loops**: Ingest review comments, diagnose failing check runs, commit patches, and merge when clean.

### Pillar 4: Terminal, Test & TDD Orchestrator
- **Integrated Test Runner**: Run `pytest`, `vitest`, `jest`, `cargo test`, `go test` with real-time UI status cards.
- **Autonomous Fix-on-Failure**: When tests fail, Skelion reads tracebacks, locates faulty files, and synthesizes candidate fixes.
- **Dev Server Monitor**: Background streaming of build logs and container states.

### Pillar 5: Production Incident & Replay Sandbox
- **Incident Telemetry**: Sparklines, error rates, and route degradation alerts.
- **Transaction Replay Verification**: Replays captured production requests against candidate patches in an isolated sandbox to ensure zero regressions before opening PRs.

---

## 3. Phased Roadmap

1. **Phase 1: Universal Plugin & MCP Manager**
   - Built-in MCP client in extension host + backend daemon.
   - Claude Code `claude_desktop_config.json` importer.
   - ChatGPT OpenAPI action generator.
   - Webview **🔌 Plugins** tab with toggle controls and live tool registry.

2. **Phase 2: Full Workspace Navigation & Testing Engine**
   - Webview **🧪 Test & Workspace** tab.
   - Native test runner integration (pytest/vitest) with failure diagnosis cards.
   - Multi-file batch patch composer.

3. **Phase 3: Multi-Tab Platform Cockpit**
   - Seamless top tab-bar navigation (`💬 Chat`, `🔌 Plugins`, `🚀 Jules PRs`, `🧪 Tests`, `⚙️ Settings`).
   - Dynamic Model Switcher (Anthropic Claude, OpenAI GPT, Google Gemini, Local Ollama).

4. **Phase 4: Unified Autonomous Autopilot (Devin/Jules Mode)**
   - End-to-end task runner: User gives ticket ➔ Spec generation ➔ Multi-file implementation ➔ Test verification ➔ Jules PR creation ➔ CI auto-repair ➔ Merge.
