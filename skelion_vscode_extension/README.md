# Skelion Agent for VS Code

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Visual Studio Marketplace Version](https://img.shields.io/badge/VS%20Code-v1.88%2B-blue)](https://marketplace.visualstudio.com/)
[![CI](https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen.svg)]()

> **Autonomous AI Engineering & Incident Remediation directly within VS Code.**  
> Zero-restart live sync, real-time telemetry, automated replay fixes, and Universal MCP plugins.

---

## 🌟 Key Features

### 🔄 Zero-Restart Live Profile & Quota Sync
Purchase upgrades or modify settings without ever needing `Developer: Reload Window`. Skelion syncs live quotas, tiers, and credentials in the background with animated status indicators.

### ⚡ Smooth Skeleton Shimmer Loading
Enjoy seamless UX inspired by modern web platforms like YouTube. Shimmering skeleton placeholders maintain layout stability while fetching real-time telemetry, incidents, or plugin manifests.

### 🛡️ Autonomous Incident Detection & Autofix
- **Real-Time Sparklines**: LTTB-downsampled metrics tracking error rates, latency spikes, and 429 throttling.
- **Automated Root Cause**: Pinpoint offending endpoints, stack traces, and commit diffs.
- **Replay Verification**: Test patches against recorded production traffic with confidence scores before merging.

### 🔌 Universal Plugin & MCP Architecture
- Import Model Context Protocol (MCP) servers and Claude Desktop configurations in one click.
- Connect generic GitHub repositories as active tools with Reverse Engineer Anything (REA).

### ♿ Accessibility & Theme Compliance
- Compliant with **WCAG 2.1 AA** accessibility standards.
- Full support for VS Code Dark, Light, High Contrast, and Custom Themes.

---

## 🚀 Getting Started

### 1. Installation
Install directly from the VS Code Marketplace or from a packaged `.vsix` file:
```bash
code --install-extension skelion-vscode-0.1.2.vsix
```

### 2. Opening the Dashboard
- Click the **Skelion** icon on the Activity Bar.
- Or open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and type:
  ```
  Skelion: Open Dashboard
  ```

### 3. Connect to Skelion Engine
Skelion automatically detects local instances (default `http://127.0.0.1:8003`).  
To connect to a remote or cloud backend (e.g. Render), set the URL in VS Code Settings:
```json
{
  "skelion.serverUrl": "https://your-skelion-instance.onrender.com"
}
```

---

## 🛠️ Panel Overview

| Panel | Description |
| :--- | :--- |
| **Incidents** | Real-time production alerts with severity badges, affected routes, and telemetry sparklines. |
| **Autofix** | Generated diffs, regression test passes, replay evidence, and one-click PR generation. |
| **Limits & Billing** | Live token quotas, usage bars, tier upgrades, and transaction history. |
| **Plugins** | MCP servers, custom tools, and connected GitHub repositories. |
| **History & Audit** | Chronological log of all autonomous actions, resolutions, and system diagnostics. |

---

## 🧪 Development & Testing

Run the full automated test suite:
```bash
npm install
npm run lint
npm test
```

Package the extension:
```bash
npm run package
```

---

## 📄 License

This extension is licensed under the [MIT License](LICENSE).  
Copyright (c) 2026 Aditya Dnyaneshwar Dahale.
