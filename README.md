# Skelion 🚀

![Verification](https://github.com/Aditya-9-6/Skelion/actions/workflows/verification.yml/badge.svg)
[![PyPI version](https://img.shields.io/pypi/v/skelion.svg)](https://pypi.org/project/skelion/)
[![npm version](https://img.shields.io/npm/v/skelion-node.svg)](https://www.npmjs.com/package/skelion-node)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/AdityaDnyaneshwarDahale.skelion-vscode?label=VS%20Code%20Marketplace)](https://marketplace.visualstudio.com/items?itemName=AdityaDnyaneshwarDahale.skelion-vscode)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**Skelion** is an autonomous SaaS incident intelligence, resilience proxy, and edge telemetry engine with a native VS Code Extension and multi-language SDKs.

## Client SDKs & VS Code Extension

- **Python SDK**: `pip install skelion` ([PyPI Package](https://pypi.org/project/skelion/))
- **Node.js SDK**: `npm install skelion-node` ([npm Package](https://www.npmjs.com/package/skelion-node))
- **VS Code Extension**: [Install from Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=AdityaDnyaneshwarDahale.skelion-vscode) (`AdityaDnyaneshwarDahale.skelion-vscode`)

## Quick Start (Linux/macOS/Windows)

```bash
# Clone the repository
git clone https://github.com/yourorg/skelion.git
cd skelion

# Set up a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy the example env file and fill in your values
cp .env.skelion.example .env.skelion
# Edit .env.skelion – set OPENAI_API_KEYS, DATABASE_URI, REDIS_URI, etc.

# Run the FastAPI control plane locally
uvicorn gossipmesh_engine.api.main:app --reload --port 8002
```

## Docker Compose

```bash
docker compose -f docker-compose.skelion.yml up --build
```

The stack provides:
- **skelion-control** – FastAPI control plane (exposes LLM endpoints).
- **skelion-edge** – Proxy that fail‑opens on any internal exception.
- **redis** – In‑memory cache for rate‑limit counters.

## Environment Variables & Dotenv Configuration

Skelion configuration is read from environment variables or a local `.env` / `.env.skelion` file. Keep your `.env` file private and add it to `.gitignore`.

### 1. Example Configuration (`.env` or `.env.skelion`)
```env
# Comma‑separated list of Gemini API keys (or multi-provider pools)
GEMINI_KEY_POOL=AQ.Ab8RN6...,AIzaSy...

# Comma‑separated list of OpenAI (or other) API keys used by the key‑pool
OPENAI_API_KEYS=sk-xxxxxx,sk-yyyyyy

# Database (SQLModel) connection string
DATABASE_URI=sqlite:///./skelion.db

# Redis connection URL
REDIS_URI=redis://localhost:6379/0

# Optional Provider-Specific Keys
# ANTHROPIC_API_KEYS=...
# GROQ_API_KEYS=...
```

### 2. Loading `.env` with `dotenv`

#### In Python Applications (`python-dotenv`)
Install the dependency:
```bash
pip install python-dotenv
```

Load variables before initializing Skelion services:
```python
import os
from dotenv import load_dotenv

# Load from default .env file in current working directory or search parent directories
load_dotenv()

# Or load from an explicit path (e.g. .env.skelion)
# load_dotenv(dotenv_path=".env.skelion")

database_uri = os.getenv("DATABASE_URI", "sqlite:///./skelion.db")
gemini_keys = os.getenv("GEMINI_KEY_POOL", "")
```

#### In Node.js Applications (`dotenv`)
Install the dependency:
```bash
npm install dotenv
```

Load environment variables at the top of your application entry point:
```javascript
// CommonJS
require('dotenv').config({ path: '.env' });

// ES Modules
import 'dotenv/config';
// Or with custom path:
// import dotenv from 'dotenv';
// dotenv.config({ path: '.env.skelion' });

const databaseUri = process.env.DATABASE_URI;
```

#### Automated Loading in Skelion Control Plane
When launching the Skelion control plane via `python run_control_plane.py` or `start_server.bat`, `python-dotenv` and SQLModel settings automatically load the `.env` file from the repository root.


## Security & Resilience
- **Fail‑open proxy** – any unhandled exception bypasses Skelion, returning the original request.
- **PII redaction** – `skelion_agent.utils.redact` masks `Authorization`, `Cookie`, `X-Api-Key`, etc.
- **Key‑pool with exponential back‑off** – on HTTP 429 the request retries with increasing delays; each event increments the Prometheus metric `rate_limits_saved_total`.
- **Prometheus metrics** – exposed at `/metrics` on the control plane.

## Running Tests
```bash
pytest -q
```
(There are currently no test files; add tests under `tests/` as needed.)

See [`docs/LAUNCH_READINESS.md`](docs/LAUNCH_READINESS.md) for the production payment, secret rotation, and deployment checklist.
See [`docs/ENTERPRISE_SAAS_PLAN.md`](docs/ENTERPRISE_SAAS_PLAN.md) for the enterprise architecture, delivery phases, and acceptance gates.

## License
MIT
