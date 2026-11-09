# helios_edge/proxy_server.py – Compatibility forwarding shim
from skelion_edge.proxy_server import HOST, PORT, TARGET_BASE, app, health

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
