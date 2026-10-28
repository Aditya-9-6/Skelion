# run_control_plane.py
import os
import socket
import uvicorn
from skelion_agent.control_plane import app

PORT = int(os.getenv("SKELION_PORT", "8003"))

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', PORT))
    sock.listen(128)
    sock.setblocking(False)

    print(f"[WAF] Skelion Control Plane Server with Spryzen WAF Shield starting on http://127.0.0.1:{PORT}...", flush=True)
    config = uvicorn.Config(app=app, log_level="info")
    server = uvicorn.Server(config)
    server.run(sockets=[sock])

if __name__ == "__main__":
    main()
