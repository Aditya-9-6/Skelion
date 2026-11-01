import socket
import threading
import time
import pytest
from skelion_agent.reactor import ZeroCopyReactor

def test_reactor_lifecycle():
    reactor = ZeroCopyReactor()
    assert reactor._epoll_fd >= -1
    reactor.close()

def test_reactor_socket_registration_and_zero_copy_ingest():
    reactor = ZeroCopyReactor()
    
    received_data = []
    event_lock = threading.Lock()
    
    def on_telemetry(fd: int, data: bytes):
        with event_lock:
            received_data.append((fd, data))
            
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    server.setblocking(False)
    
    port = server.getsockname()[1]
    
    reactor.register_socket(server, on_telemetry)
    
    # Connect client
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))
    
    # Run a quick poll iteration
    start = time.time()
    while time.time() - start < 1.0:
        reactor.poll_once(timeout_ms=50)
        if received_data:
            break
            
    client.sendall(b"INCIDENT_TELEMETRY_PAYLOAD_V1")
    
    start = time.time()
    while time.time() - start < 1.0:
        reactor.poll_once(timeout_ms=50)
        with event_lock:
            if any(b"INCIDENT_TELEMETRY" in d for _, d in received_data):
                break
                
    client.close()
    server.close()
    reactor.close()
    
    with event_lock:
        payloads = [d for _, d in received_data]
    assert any(b"INCIDENT_TELEMETRY_PAYLOAD_V1" in p for p in payloads)
