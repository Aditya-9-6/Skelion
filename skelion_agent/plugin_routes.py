# skelion_agent/plugin_routes.py — REST API for Universal Plugin & MCP Management
"""
REST Endpoints for:
- Listing and toggling MCP, Claude Code, and ChatGPT plugins
- 1-Click importing from Claude Code & Claude Desktop (claude_desktop_config.json)
- Importing ChatGPT Custom Action (OpenAPI 3.1) JSON specs
- Executing active tools from the VS Code extension webview
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter
from pydantic import BaseModel

from skelion_agent.mcp_manager import plugin_registry, MCPPlugin, ClaudeConfigImporter

router = APIRouter(prefix="/v1/plugins", tags=["Universal Plugins & MCP"])


class AddPluginRequest(BaseModel):
    id: str
    name: str
    type: str  # "mcp_stdio", "mcp_sse", "openapi"
    command: Optional[str] = ""
    args: Optional[List[str]] = []
    env: Optional[Dict[str, str]] = {}
    url: Optional[str] = ""
    tools: Optional[List[Dict[str, Any]]] = []


class TogglePluginRequest(BaseModel):
    plugin_id: str
    enabled: bool


class ImportClaudeRequest(BaseModel):
    config_path: Optional[str] = None


class ConnectGitHubRepoRequest(BaseModel):
    repo_url: str
    command: Optional[str] = None


class ImportOpenApiRequest(BaseModel):
    spec: Dict[str, Any]
    title: Optional[str] = None


class ExecuteToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


@router.get("")
async def list_plugins():
    """Returns all registered plugins with their tools and connection status."""
    plugins = plugin_registry.list_plugins()
    claude_config_found = ClaudeConfigImporter.find_config()
    return {
        "status": "ok",
        "total_plugins": len(plugins),
        "plugins": plugins,
        "claude_config_detected": claude_config_found is not None,
        "claude_config_path": claude_config_found,
    }


@router.post("")
async def add_plugin(req: AddPluginRequest):
    """Registers a new custom MCP or OpenAPI plugin."""
    plugin = MCPPlugin(
        id=req.id,
        name=req.name,
        type=req.type,
        command=req.command or "",
        args=req.args or [],
        env=req.env or {},
        url=req.url or "",
        tools=req.tools or [],
        source="custom",
        status="connected",
        enabled=True,
    )
    return plugin_registry.add_plugin(plugin)


@router.post("/toggle")
async def toggle_plugin(req: TogglePluginRequest):
    """Enables or disables an installed plugin."""
    return plugin_registry.toggle_plugin(req.plugin_id, req.enabled)


@router.delete("/{plugin_id}")
async def remove_plugin(plugin_id: str):
    """Uninstalls a plugin from the registry."""
    return plugin_registry.remove_plugin(plugin_id)


@router.post("/import-claude")
async def import_claude_plugins(req: Optional[ImportClaudeRequest] = None):
    """Scans and imports all MCP servers defined in Claude Code or Claude Desktop."""
    path = req.config_path if req else None
    return plugin_registry.import_claude_plugins(path)


@router.post("/import-openapi")
async def import_openapi_action(req: ImportOpenApiRequest):
    """Imports OpenAPI 3.0/3.1 specs used in ChatGPT Custom Actions."""
    return plugin_registry.import_openapi_action(req.spec, title=req.title)


@router.post("/connect-github-repo")
async def connect_github_repo(req: ConnectGitHubRepoRequest):
    """Connects any open-source GitHub tool repo (e.g. morluto/rea) as an active MCP server."""
    return plugin_registry.import_github_tool_repo(
        req.repo_url, custom_command=req.command
    )


@router.get("/active-tools")
async def get_active_tools():
    """Lists all tools enabled across active plugins ready for LLM invocation."""
    tools = plugin_registry.get_all_active_tools()
    return {"status": "ok", "active_tool_count": len(tools), "tools": tools}


@router.post("/execute-tool")
async def execute_tool(req: ExecuteToolRequest):
    """Executes a tool from an active plugin."""
    return plugin_registry.execute_tool(req.tool_name, req.arguments)
