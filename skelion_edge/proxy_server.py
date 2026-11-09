import os
import uvicorn
from fastapi import FastAPI
from skelion_edge.proxy import ProxyMiddleware

TARGET_BASE = os.getenv("TARGET_BASE_URL", "http://skelion-control:8002")
PORT = int(os.getenv("PORT", "8080"))
HOST = os.getenv("HOST", "0.0.0.0")

app = FastAPI(title="Skelion Edge Proxy", version="2.0.0")
app.add_middleware(ProxyMiddleware, target_base=TARGET_BASE)


@app.get("/health", tags=["System"])
def health():
    return {
        "status": "healthy",
        "service": "skelion-edge-proxy",
        "target_base": TARGET_BASE,
    }


if __name__ == "__main__":
    print(
        f"[Skelion Edge] Starting edge proxy on http://{HOST}:{PORT} forwarding to {TARGET_BASE}...",
        flush=True,
    )
    uvicorn.run(app, host=HOST, port=PORT)
