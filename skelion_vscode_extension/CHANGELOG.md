# Changelog

All notable changes to the Skelion VS Code Extension and Autonomous Platform.

## [0.1.2] - 2026-11-04

### Added
- **Skeleton Loading UX**: Added YouTube-style pulsating shimmer placeholder structures across all primary panels (Incidents, Autofix, Limits, History, Plugins, Chat).
- **Zero-Restart Live Sync**: Synchronize developer profiles, tier upgrades, and token quotas dynamically with live-spinning sync indicators without requiring a VS Code window reload.
- **Error Diagnostics & Retry Actions**: Contextual error cards with connection diagnostics, server status checks, and one-click retry triggers for all data feeds.
- **WCAG 2.1 AA Accessibility**: Enhanced screen-reader support with `role="tablist"`, `role="tab"`, `aria-busy`, and high-contrast color scheme definitions.
- **GitHub Tool Connector**: Generic GitHub tool repository importer with full REA (Reverse Engineer Anything) support and MCP tooling.
- **Automated Test Suite & CI/CD**: Unified test runner across 5 comprehensive test suites with GitHub Actions workflow automation for cross-platform validation.
- **TypeScript 5 & Zod 3.22**: Upgraded strict schema definitions and downsampling algorithms for guaranteed type safety.

## [0.1.1] - 2026-11-02

### Added
- Universal Plugin & MCP System with Claude Desktop config importer and OpenAPI / ChatGPT actions importer.
- User documentation for GitHub tool repository connection (`docs/user/CONNECT_GITHUB.md`).

## [0.1.0] - 2026-11-01

### Added
- Initial Skelion VS Code extension release with authentication, billing quotas, and master control dashboard.
