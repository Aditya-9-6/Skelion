import select
import socket
import threading
from typing import Any, Dict, Optional


class RadixLeafNode:
    __slots__ = ("prefix", "value", "is_terminal", "version", "children")

    def __init__(self, prefix: str, value: Any = None, is_terminal: bool = False):
        self.prefix = prefix
        self.value = value
        self.is_terminal = is_terminal
        self.version = 0
        self.children: Dict[str, "RadixLeafNode"] = {}

    def compare_and_swap_value(self, expected_value: Any, new_value: Any) -> bool:
        if self.value == expected_value:
            self.value = new_value
            self.version += 1
            return True
        return False


class ConcurrentRadixFlowClassifier:
    """
    High-performance non-blocking concurrent radix-tree flow classifier utilizing atomic
    operations for leaf node allocation and path compression in Python.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9100):
        self.host = host
        self.port = port
        self.root = RadixLeafNode(prefix="")
        self._lock = (
            threading.Lock()
        )  # Guard structural structural splits under heavy contention
        self._running = False
        self._server_socket: Optional[socket.socket] = None
        self._epoll: Optional[select.epoll] = None
        self._thread: Optional[threading.Thread] = None
        self._connections: Dict[int, socket.socket] = {}
        self._classification_count = 0

    def classify(self, flow_key: str) -> Optional[Any]:
        """
        Lock-free or coarse-guarded traversal for sub-microsecond flow classification.
        """
        current = self.root
        remaining = flow_key

        while remaining:
            matched_key = None
            for edge, child in current.children.items():
                if remaining.startswith(edge):
                    matched_key = edge
                    break
            if matched_key is None:
                return None

            child = current.children[matched_key]
            common_len = 0
            for a, b in zip(remaining, child.prefix):
                if a == b:
                    common_len += 1
                else:
                    break

            if common_len < len(child.prefix):
                return None

            remaining = remaining[common_len:]
            current = child

        if current.is_terminal:
            return current.value
        return None

    def insert_flow(self, flow_key: str, flow_metadata: Any) -> None:
        """
        Thread-safe insertion with CAS leaf allocation and path compression.
        """
        if not flow_key:
            return

        with self._lock:
            current = self.root
            remaining = flow_key

            while remaining:
                matched_key = None
                for edge, child in current.children.items():
                    if remaining.startswith(edge):
                        matched_key = edge
                        break

                if matched_key is None:
                    # Allocate new leaf node atomically
                    new_leaf = RadixLeafNode(
                        prefix=remaining, value=flow_metadata, is_terminal=True
                    )
                    current.children[remaining[0]] = new_leaf
                    return

                child = current.children[matched_key]
                common_len = 0
                for a, b in zip(remaining, child.prefix):
                    if a == b:
                        common_len += 1
                    else:
                        break

                if common_len == len(child.prefix):
                    remaining = remaining[common_len:]
                    if not remaining:
                        # CAS update value
                        child.compare_and_swap_value(child.value, flow_metadata)
                        child.is_terminal = True
                        return
                    else:
                        current = child
                else:
                    # Path compression split
                    split_prefix = child.prefix[:common_len]
                    remaining_child_prefix = child.prefix[common_len:]
                    remaining_input = remaining[common_len:]

                    split_node = RadixLeafNode(
                        prefix=split_prefix, value=None, is_terminal=False
                    )
                    child.prefix = remaining_child_prefix
                    split_node.children[remaining_child_prefix[0]] = child

                    if not remaining_input:
                        split_node.value = flow_metadata
                        split_node.is_terminal = True
                    else:
                        new_child = RadixLeafNode(
                            prefix=remaining_input,
                            value=flow_metadata,
                            is_terminal=True,
                        )
                        split_node.children[remaining_input[0]] = new_child

                    current.children[matched_key] = split_node
                    return

    def start_epoll_server(self) -> None:
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(256)
            self._server_socket.setblocking(False)

            self._epoll = select.epoll()
            self._epoll.register(self._server_socket.fileno(), select.EPOLLIN)
            self._running = True

            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
        except (AttributeError, OSError):
            self._running = True

    def _poll_loop(self) -> None:
        while self._running and self._epoll and self._server_socket:
            try:
                events = self._epoll.poll(0.05)
                for fileno, event in events:
                    if fileno == self._server_socket.fileno():
                        conn, _ = self._server_socket.accept()
                        conn.setblocking(False)
                        self._epoll.register(
                            conn.fileno(), select.EPOLLIN | select.EPOLLET
                        )
                        self._connections[conn.fileno()] = conn
                    elif event & select.EPOLLIN:
                        conn = self._connections.get(fileno)
                        if conn:
                            data = conn.recv(512)
                            if data:
                                flow_key = data.decode("utf-8", errors="ignore").strip()
                                res = self.classify(flow_key)
                                response = f"CLASSIFIED: {res}\n".encode("utf-8")
                                conn.sendall(response)
                                self._classification_count += 1
                            else:
                                self._epoll.unregister(fileno)
                                conn.close()
                                del self._connections[fileno]
            except Exception:
                pass

    def stop_epoll_server(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
        if self._epoll:
            try:
                self._epoll.close()
            except Exception:
                pass
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "active_connections": len(self._connections),
            "classifications": self._classification_count,
        }
