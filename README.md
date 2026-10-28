# Skelion 🚀

**Skelion** is a fault‑tolerant edge proxy and autonomous LLM orchestration engine.

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

## Environment Variables
Create a `.env.skelion` file (copy from the example) containing:
```
# Comma‑separated list of OpenAI (or other) API keys used by the key‑pool
OPENAI_API_KEYS=sk-xxxxxx,sk-yyyyyy

# Database (SQLModel) connection string
DATABASE_URI=sqlite:///./skelion.db

# Redis connection URL
REDIS_URI=redis://localhost:6379/0

# Add any additional provider‑specific keys if you diverge from the shared pool
# ANTHROPIC_API_KEYS=...
# GEMINI_API_KEYS=...
```

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

## License
MIT
