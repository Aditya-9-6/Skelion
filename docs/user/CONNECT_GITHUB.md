# Connecting GitHub Tool Repositories in Skelion

Skelion allows you to instantly connect and import any external tool repository or MCP tool directly from GitHub.

## Overview
With the **Connect GitHub Repo...** feature:
- Any MCP server or CLI tool hosted on GitHub (e.g. `morluto/rea`, `github.com/example/simple-mcp-tool`) can be bound into Skelion's universal plugin registry.
- Tools become immediately available to Skelion's autonomous agent runtime and LLM tool calling pipeline.
- Works offline via fallback stubs if the backend control plane is temporarily unreachable.

## How to Connect a GitHub Tool Repo

### 1. Through VS Code Sidebar
1. Open the Skelion panel from the Activity Bar on the left.
2. In the **Plugins & MCP Hub** section, click **🔗 Connect GitHub Repo...**.
3. In the input prompt, enter the repository slug or URL (e.g., `morluto/rea` or `https://github.com/example/simple-mcp-tool`).
4. Toast notifications will confirm successful tool registration and how many tool endpoints were discovered.

### 2. Through Quick Action Button
- A pre-configured **⚡ Connect REA Tool Repo** button is available in the toolbar for one-click attachment of the Reverse Engineer Anything suite (170 reverse-engineering and decompilation tools).

### 3. Through REST API
Send a POST request to Skelion's agent backend:
```bash
curl -X POST http://127.0.0.1:8003/v1/plugins/connect-github-repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/morluto/rea"}'
```

Response:
```json
{
  "status": "ok",
  "plugin": {
    "id": "github_repo_rea",
    "name": "REA (Reverse Engineer Anything)",
    "type": "mcp_stdio",
    "source": "github_repo",
    "status": "connected",
    "enabled": true,
    "tools": [
      {"name": "rea_open_binary", "description": "Loads an executable binary into REA engine"},
      {"name": "rea_decompile", "description": "Decompiles a function or address range into pseudo-C"},
      {"name": "rea_search_strings", "description": "Extracts strings and symbol references from loaded binary"}
    ]
  }
}
```

## Error Handling & Offline Fallback
If the backend service is offline, Skelion displays a warning toast and smoothly transitions the tool into offline registration mode, ensuring no UI interruption occurs.
