# Changelog

All notable changes to the Skelion VS Code Extension and Autonomous Platform.

## [0.1.2] - 2026-11-03

### Added
- **GitHub Tool Connector**: Generic GitHub tool repository importer with full REA (Reverse Engineer Anything) support and MCP tooling.
- **Error Handling UI**: Toast error and fallback notifications in `extension.ts` for all GitHub repository connection events.
- **Automated Test Suite**: Added `test_connect_generic_github_tool_repo` verifying generic repository tools registration in `tests/test_mcp_plugins.py`.
- **TypeScript 5 & Zod Fixes**: Upgraded schema definitions in `chat.ts` to support modern Zod object records.
- **Production VSIX**: Packaged `skelion-vscode-0.1.2.vsix` with complete webview, assets, and compiled host controllers.

## [0.1.1] - 2026-11-02

### Added
- Universal Plugin & MCP System with Claude Desktop config importer and OpenAPI / ChatGPT actions importer.
- User documentation for GitHub tool repository connection (`docs/user/CONNECT_GITHUB.md`).

## [0.1.0] - 2026-11-01

### Added
- Initial Skelion VS Code extension release with authentication, billing quotas, and master control dashboard.
