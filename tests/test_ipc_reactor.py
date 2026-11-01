import socket
import select
import time
from skelion_agent.ipc.reactor import EpollReactor


def test_epoll_reactor_socket_pair():
    server_sock, client_sock = socket.socketpair()
    server_sock.setblocking(False)
    client_sock.setblocking(False)

    reactor = EpollReactor()
    received = []

    def handle_read(fd, event):
        data = server_sock.recv(1024)
        if data:
            received.append(data)

    events = getattr(select, "EPOLLIN", 1)
    reactor.register(server_sock, events, handle_read)

    try:
        client_sock.send(b"ping_telemetry")
        time.sleep(0.05)
        reactor.poll(timeout=0.2)

        assert len(received) == 1
        assert received[0] == b"ping_telemetry"
    finally:
        reactor.unregister(server_sock)
        reactor.close()
        server_sock.close()
        client_sock.close()
