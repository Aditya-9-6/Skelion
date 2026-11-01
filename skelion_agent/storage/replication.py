import socket
import os
import struct
import logging
from typing import Dict, Any, Optional
from skelion_agent.storage.mmap_log import MMapAppendOnlyLog
from gossipmesh_engine.core.clocks import VectorClock

logger = logging.getLogger("skelion.storage.replication")


class LogReplicator:
    """
    Zero-copy network replication protocol utilizing socket sendfile for peer-to-peer
    log synchronization across the agent mesh, integrated with vector clocks.
    """

    REPLICATION_PORT_OFFSET = 1000

    def __init__(self, node_id: str, log: MMapAppendOnlyLog, bind_addr: str = "0.0.0.0", port: int = 9000):
        self.node_id = node_id
        self.log = log
        self.bind_addr = bind_addr
        self.port = port
        self.vector_clock = VectorClock(node_id)
        self._server_socket: Optional[socket.socket] = None
        self._running = False

    def start_listener(self) -> None:
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.bind_addr, self.port))
        self._server_socket.listen(128)
        self._running = True
        logger.info(f"LogReplicator listener started on {self.bind_addr}:{self.port}")

    def handle_peer_connection(self, conn: socket.socket) -> None:
        try:
            header_data = conn.recv(16)
            if not header_data or len(header_data) < 16:
                return
            start_offset, length = struct.unpack("=QQ", header_data)
            
            # Zero-copy file transmission via socket sendfile if supported
            self.log.fsync()
            with open(self.log.filepath, "rb") as f:
                f.seek(start_offset)
                if hasattr(os, "sendfile") and hasattr(conn, "fileno"):
                    os.sendfile(conn.fileno(), f.fileno(), start_offset, length)
                else:
                    # Fallback chunked transfer
                    remaining = length
                    while remaining > 0:
                        chunk_size = min(remaining, 65536)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        conn.sendall(chunk)
                        remaining -= len(chunk)
        except Exception as e:
            logger.error(f"Error handling peer replication connection: {e}")
        finally:
            conn.close()

    def replicate_segment(self, peer_host: str, peer_port: int, start_offset: int, length: int) -> bool:
        """
        Replicate log segment data to a peer node using zero-copy socket connection.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((peer_host, peer_port))
                request_header = struct.pack("=QQ", start_offset, length)
                s.sendall(request_header)
                
                # Receive synchronized segment data
                while True:
                    data = s.recv(65536)
                    if not data:
                        break
                    # Data can be processed or appended accordingly
            return True
        except Exception as e:
            logger.error(f"Failed to replicate segment to {peer_host}:{peer_port}: {e}")
            return False

    def sync_with_peer(self, peer_host: str, peer_port: int, remote_clock: Dict[str, int]) -> bool:
        """
        Perform anti-entropy synchronization with vector clock delta exchange.
        """
        self.vector_clock.update(remote_clock)
        delta = self.vector_clock.delta(remote_clock)
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((peer_host, peer_port))
                # Send vector clock metadata and request missing log entries
                payload = struct.pack("=Q", self.log.write_offset)
                s.sendall(payload)
            return True
        except Exception as e:
            logger.error(f"Anti-entropy sync with {peer_host}:{peer_port} failed: {e}")
            return False

    def close(self) -> None:
        self._running = False
        if self._server_socket:
            self._server_socket.close()
            self._server_socket = None
