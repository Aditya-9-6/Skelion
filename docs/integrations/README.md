# Skelion MCP Server Integration Guide

Skelion provides a **Model Context Protocol (MCP)** server (`skelion-mcp`) allowing coding agents (Cursor, Claude Code, Antigravity) to query real production incidents, service health, and run replay verifications directly from their coding workflow.

---

## 1. Quick Setup for Cursor

1. In Cursor, open **Settings** &rarr; **Features** &rarr; **MCP Servers**.
2. Click **Add New MCP Server**.
3. Use the following configuration (or paste from `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "skelion": {
      "command": "python",
      "args": ["-m", "skelion_mcp.server"],
      "env": {
        "SKELION_API_URL": "http://127.0.0.1:8002"
      }
    }
  }
}
```

Now you can ask Cursor:
- *"What production incidents happened on `/api/checkout` in the last 24h?"*
- *"Propose a fix for incident `inc_886e4933` and verify with replay test."*

---

## 2. Quick Setup for Claude Code

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skelion": {
      "command": "python",
      "args": ["-m", "skelion_mcp.server"],
      "env": {
        "SKELION_API_URL": "http://127.0.0.1:8002"
      }
    }
  }
}
```

---

## 3. Available MCP Tools

| Tool | Purpose | Safe for Local / Offline? |
| :--- | :--- | :--- |
| `list_incidents` | Returns recent production errors and fingerprints | ✅ Redacted & safe |
| `get_incident` | Gets full stack trace & route context | ✅ Redacted & safe |
| `get_service_health` | Queries error rate, p95 latency, 5xx counts | ✅ Safe |
| `get_fix_status` | Checks status of autonomous fixes | ✅ Safe |
| `run_replay_test` | Sandboxed test execution of captured requests | ✅ Idempotent only |
| `propose_fix` | Autonomous minimal patch + verification proof | ✅ Sandboxed |

---

## 4. Privacy & Egress Guarantee
Skelion MCP adheres to the strict **allow-list egress schema**. Raw customer authorization tokens, credit cards, passwords, and private PII are stripped at the edge prior to entering the incident index.
