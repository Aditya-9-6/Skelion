# tests/test_mcp_plugins.py — Test Suite for Universal Plugin & MCP System
import json
from fastapi.testclient import TestClient
from fastapi import FastAPI

from skelion_agent.mcp_manager import (
    PluginRegistry,
    ClaudeConfigImporter,
    OpenApiImporter,
)
from skelion_agent.plugin_routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_plugin_registry_defaults(tmp_path):
    storage_file = str(tmp_path / "plugins.json")
    registry = PluginRegistry(storage_path=storage_file)
    plugins = registry.list_plugins()
    assert len(plugins) >= 4
    names = [p["name"] for p in plugins]
    assert any("GitHub" in n for n in names)
    assert any("PostgreSQL" in n for n in names)
    assert any("Docker" in n for n in names)
    assert any("Brave" in n for n in names)


def test_claude_desktop_config_importer(tmp_path):
    mock_config = tmp_path / "claude_desktop_config.json"
    mock_data = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            },
            "postgres-production": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-postgres",
                    "postgresql://user:pass@db:5432/prod",
                ],
                "env": {"PGPASSWORD": "supersecretpassword"},
            },
        }
    }
    with open(mock_config, "w", encoding="utf-8") as f:
        json.dump(mock_data, f)

    imported = ClaudeConfigImporter.import_plugins(str(mock_config))
    assert len(imported) == 2
    names = [p.name for p in imported]
    assert "filesystem" in names
    assert "postgres-production" in names

    pg_plugin = next(p for p in imported if p.name == "postgres-production")
    assert pg_plugin.source == "claude_import"
    assert len(pg_plugin.tools) >= 1
    assert any("query" in t["name"] for t in pg_plugin.tools)


def test_chatgpt_openapi_importer():
    sample_openapi = {
        "openapi": "3.1.0",
        "info": {"title": "Stripe Payments Inspector", "version": "1.0.0"},
        "servers": [{"url": "https://api.stripe.com/v1"}],
        "paths": {
            "/charges": {
                "get": {
                    "operationId": "list_charges",
                    "summary": "List all recent customer charges",
                    "parameters": [
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}}
                    ],
                }
            },
            "/refunds": {
                "post": {
                    "operationId": "create_refund",
                    "summary": "Issue refund for charge ID",
                    "parameters": [
                        {
                            "name": "charge_id",
                            "in": "query",
                            "schema": {"type": "string"},
                        }
                    ],
                }
            },
        },
    }

    plugin = OpenApiImporter.import_spec(sample_openapi, source_name="Stripe Payments")
    assert plugin.id == "openapi_stripe_payments"
    assert plugin.type == "openapi"
    assert len(plugin.tools) == 2
    tool_names = [t["name"] for t in plugin.tools]
    assert "list_charges" in tool_names
    assert "create_refund" in tool_names


def test_plugin_toggle_and_tool_collection(tmp_path):
    storage_file = str(tmp_path / "plugins.json")
    registry = PluginRegistry(storage_path=storage_file)

    initial_tools = registry.get_all_active_tools()
    assert len(initial_tools) > 0

    # Toggle a plugin off
    plugins = registry.list_plugins()
    first_id = plugins[0]["id"]
    registry.toggle_plugin(first_id, False)

    updated_tools = registry.get_all_active_tools()
    assert len(updated_tools) < len(initial_tools)

    # Execute tool
    active_tool_name = updated_tools[0]["name"]
    res = registry.execute_tool(active_tool_name, {"query": "SELECT 1"})
    assert res["status"] == "ok"
    assert res["tool_name"] == active_tool_name


def test_plugin_rest_api_endpoints(tmp_path):
    # Test GET /v1/plugins
    res = client.get("/v1/plugins")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["total_plugins"] >= 4

    # Test GET /v1/plugins/active-tools
    tools_res = client.get("/v1/plugins/active-tools")
    assert tools_res.status_code == 200
    tools_data = tools_res.json()
    assert tools_data["active_tool_count"] > 0

    # Test POST /v1/plugins/toggle
    first_id = data["plugins"][0]["id"]
    toggle_res = client.post(
        "/v1/plugins/toggle", json={"plugin_id": first_id, "enabled": False}
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["enabled"] is False

    # Test POST /v1/plugins/execute-tool
    active_tool = tools_data["tools"][-1]["name"]
    exec_res = client.post(
        "/v1/plugins/execute-tool", json={"tool_name": active_tool, "arguments": {}}
    )
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "ok"


def test_connect_github_tool_repo_rea(tmp_path):
    storage_file = str(tmp_path / "plugins.json")
    registry = PluginRegistry(storage_path=storage_file)

    # Test connecting morluto/rea repository directly
    res = registry.import_github_tool_repo("https://github.com/morluto/rea")
    assert res["status"] == "ok"
    plugin = res["plugin"]
    assert "REA" in plugin["name"]
    assert plugin["type"] == "mcp_stdio"
    assert plugin["source"] == "github_repo"
    assert len(plugin["tools"]) >= 3
    tool_names = [t["name"] for t in plugin["tools"]]
    assert "rea_open_binary" in tool_names
    assert "rea_decompile" in tool_names
    assert "rea_search_strings" in tool_names

    # Test via REST API endpoint
    api_res = client.post(
        "/v1/plugins/connect-github-repo", json={"repo_url": "github.com/morluto/rea"}
    )
    assert api_res.status_code == 200
    assert api_res.json()["status"] == "ok"
    assert "REA" in api_res.json()["plugin"]["name"]


def test_connect_generic_github_tool_repo(tmp_path):
    storage_file = str(tmp_path / "plugins.json")
    registry = PluginRegistry(storage_path=storage_file)

    # Test connecting a generic GitHub tool repo
    repo_url = "https://github.com/example/simple-mcp-tool"
    res = registry.import_github_tool_repo(repo_url)
    assert res["status"] == "ok"
    plugin = res["plugin"]
    assert plugin["id"] == "github_repo_simple_mcp_tool"
    assert "simple-mcp-tool" in plugin["name"]
    assert plugin["source"] == "github_repo"
    assert plugin["status"] == "connected"
    assert plugin["enabled"] is True

    # Assert plugin appears in the registry list
    all_plugins = registry.list_plugins()
    matching = [p for p in all_plugins if p["id"] == "github_repo_simple_mcp_tool"]
    assert len(matching) == 1
    assert matching[0]["name"] == "GitHub Tool: simple-mcp-tool"
