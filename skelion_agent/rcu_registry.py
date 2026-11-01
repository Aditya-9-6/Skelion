import threading
from typing import Any, Dict, Optional


class RCURegistry:
    """
    Read-Copy-Update (RCU) Registry for dynamic agent route tables.
    Provides lock-free concurrent reads and copy-on-write updates with epoch reclamation.
    """

    def __init__(self) -> None:
        self._routes: Dict[str, Any] = {}
        self._registry_lock = threading.Lock()
        self._reader_epochs: Dict[int, int] = {}
        self._current_epoch = 0

    def read(self, route_key: str) -> Optional[Any]:
        """
        Lock-free read hot-path avoiding mutex acquisition for optimal RCU performance.
        """
        routes = self._routes
        return routes.get(route_key)

    def write(self, route_key: str, value: Any) -> None:
        """
        Copy-on-write update protected by registry lock.
        """
        with self._registry_lock:
            new_routes = dict(self._routes)
            new_routes[route_key] = value
            self._routes = new_routes
            self._current_epoch += 1

    def delete(self, route_key: str) -> None:
        with self._registry_lock:
            if route_key in self._routes:
                new_routes = dict(self._routes)
                del new_routes[route_key]
                self._routes = new_routes
                self._current_epoch += 1
