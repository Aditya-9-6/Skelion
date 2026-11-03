# Skelion Software Development Platform – GitHub Tool Integration

## Overview
The Skelion VS Code extension now includes a **generic GitHub connector** that lets developers import any MCP‑compatible tool repository directly from GitHub. This enables seamless integration of third‑party tools such as **REA (Reverse Engineer Anything)**, Claude‑code plugins, ChatGPT‑driven agents, or any custom CLI/MCP server published on GitHub.

## How it works
1. **Backend** – `skelion_agent/mcp_manager.py` provides the method `import_github_tool_repo(repo_url: str, command: Optional[str] = None)`. It clones the repository to a temporary location, installs the tool (via `npm`, `npx`, or a custom command), and registers an `MCPPlugin` entry.
2. **API** – A new POST endpoint `/v1/plugins/connect-github-repo` in `skelion_agent/plugin_routes.py` triggers the import logic and returns a success payload with the generated plugin ID.
3. **Frontend** – The VS Code extension adds a **"Connect GitHub Repo…"** button to the Plugins pane (`extension.ts`). When clicked, it prompts the user for a GitHub repository URL (and optionally a custom install command). The UI displays success/failure notifications and automatically adds the new plugin to the list.
4. **RE A Example** – The REA tools are pre‑registered under the plugin ID `github_repo_rea`. Clicking the **"Connect REA Tool Repo"** button runs the same generic flow using the built‑in command `npx -y rea‑agents`.

## Adding a new GitHub‑hosted tool
1. **Ensure the repo contains an MCP server** – The repository must expose a command that prints a JSON description of its MCP tools (e.g., `npx rea‑agents`, `python -m mytool --mcp`).
2. **Open the Plugins pane** in VS Code (⇧⌘P → *Skelion: Show Plugins*).
3. Click **"Connect GitHub Repo…"**.
4. Enter the repository URL, e.g. `https://github.com/username/my-mcp-tool`.
5. If the tool requires a custom command, specify it in the optional prompt (otherwise the default inference tries `npx -y <repo-name>`).
6. After a short loading period, the plugin appears in the list and can be activated like any built‑in plugin.

## Compatibility with VS Code tools
- The connector does **not depend on any specific VS Code extension**. Once a tool is registered as an MCP plugin, the Skelion framework can invoke its methods from any VS Code UI component (commands, sidebars, or custom webviews). This means developers can bring in **any VS Code‑compatible tool** that follows the MCP protocol.

## Error handling & feedback
- Invalid URLs, missing `package.json`, or failure to produce an MCP descriptor result in a toast notification with the error details.
- The API returns HTTP 400 with a message describing the issue; the frontend surfaces the same message.

## Future enhancements (optional)
- UI for bulk importing multiple repositories.
- Automatic version checking and updates for connected GitHub plugins.
- Ability to specify a custom install script (e.g., `pip install -r requirements.txt`).

---
*Documentation generated on 2026‑11‑03. For the latest changes, refer to the commit `0490d6ac`.*