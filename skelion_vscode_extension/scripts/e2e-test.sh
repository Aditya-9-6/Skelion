#!/usr/bin/env bash
set -e

# Install VS Code test runner (if not already installed globally)
# npx @vscode/vscode-test is used to download a VS Code version and run extension tests.

# Resolve the extension root
dirname=$(dirname "${BASH_SOURCE[0]}")
ROOT=$(cd "$dirname/.." && pwd)

# Run the integration tests defined in the extension's test folder
# Ensure the compiled output exists
npm run compile

# Execute the VS Code test runner
npx @vscode/vscode-test run \
  --extensionDevelopmentPath "$ROOT" \
  --extensionTestsPath "$ROOT/out/test" \
  --version "stable"
