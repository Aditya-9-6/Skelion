#!/usr/bin/env python3
"""
Helios / Skelion Agent – System‑wide health check.

- Queries all known health endpoints (WAF, DevProxy, Replay, Telemetry, VS Code, GitHub Bot).
- Normalises each response to a simple “OK/FAIL” flag.
- Prints a pretty markdown‑style table (useful in CI logs or Slack bots).

Dependencies:
    pip install httpx tabulate
"""

import asyncio
import os
from typing import List, Tuple

import httpx
from tabulate import tabulate

# ----------------------------------------------------------------------
# Configuration – replace with your real hostnames / ports if different
# ----------------------------------------------------------------------
ENDPOINTS: List[Tuple[str, str]] = [
    ("Spryzen WAF",      "https://waf.internal.example.com/healthz"),
    ("DevProxy",         "http://localhost:8080/_health"),
    ("Replay Sandbox",   "http://sandbox-svc:9090/api/v1/health"),
    ("Telemetry",        "http://telemetry-svc:9200/_cluster/health"),
    ("VS Code Agent",    "http://127.0.0.1:3000/heartbeat"),
    ("GitHub Bot",       "https://api.github.com/repos/DefaultOrg/skelion-bot/commits/main/status"),
    ("Prometheus",       "http://prometheus:9090/api/v1/query?query=up"),
]

TIMEOUT = 5.0  # seconds per request


async def fetch(client: httpx.AsyncClient, name: str, url: str) -> Tuple[str, str]:
    """Return (name, status_str)."""
    try:
        resp = await client.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return name, f"❌ error: {type(exc).__name__}"

    # Normalise a handful of known payload shapes
    status = data.get("status") or data.get("state")
    if isinstance(status, str):
        status = status.lower()
    # Heuristics for common “healthy” keys
    if status in {"ok", "ready", "open", "green", "alive", "success"}:
        return name, "✅ OK"
    if isinstance(data, dict) and data.get("up") == 1:
        return name, "✅ OK"
    # Fallback – if we got 2xx but no explicit flag, treat as OK
    if 200 <= resp.status_code < 300:
        return name, "✅ OK (no explicit flag)"
    return name, f"❌ unexpected payload"


async def main() -> None:
    async with httpx.AsyncClient(verify=False) as client:  # internal TLS may be self‑signed
        tasks = [fetch(client, n, u) for n, u in ENDPOINTS]
        results = await asyncio.gather(*tasks)

    # Render markdown table (good for CI logs)
    headers = ["Component", "Status"]
    print("\n" + tabulate(results, headers=headers, tablefmt="github") + "\n")

    # Exit code 0 if all OK, otherwise 1 (useful for CI)
    exit_code = 0 if all("✅" in s for _, s in results) else 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
