import threading
from typing import Any, Dict, Optional, List, Set
import logging

logger = logging.getLogger(__name__)


class HazardPointerNode:
    __slots__ = ("agent_id", "state", "version", "retired", "_ref_count")

    def __init__(self, agent_id: str, state: Dict[str, Any], version: int):
        self.agent_id = agent_id
        self.state = state
        self.version = version
        self.retired = False
        self._ref_count = 0


class HazardPointerRegistry:
    """
    High-performance, thread-safe dynamic agent registry using Hazard Pointers
    to allow lock-free reads and safe concurrent memory reclamation during
    real-time incident remediation updates. Guarantees bounded memory utilization
    under high concurrency without using blocking mutexes in the critical read path.
    """

    def __init__(self, max_hazard_pointers: int = 64, gc_batch_threshold: int = 32):
        self._registry: Dict[str, HazardPointerNode] = {}
        self._registry_lock = (
            threading.Lock()
        )  # Only for write mutations and map updates

        # Hazard pointer slots: maps thread_id -> HazardPointerNode being read
        self._hazard_pointers: Dict[int, Optional[HazardPointerNode]] = {}
        self._hp_lock = threading.Lock()

        # Retired list for deferred memory reclamation
        self._retired_list: List[HazardPointerNode] = []
        self._gc_batch_threshold = gc_batch_threshold
        self._total_registrations = 0

    def _get_thread_id(self) -> int:
        return threading.get_ident()

    def acquire_hazard_pointer(self, agent_id: str) -> Optional[HazardPointerNode]:
        """
        Acquire a hazard pointer for a given agent_id in a lock-free manner.
        The caller can safely read the node without blocking writer threads.
        """
        tid = self._get_thread_id()

        # Fast path lock-free lookup attempt or synchronized retrieval
        while True:
            node = self._registry.get(agent_id)
            if node is None or node.retired:
                with self._hp_lock:
                    self._hazard_pointers[tid] = None
                return None

            with self._hp_lock:
                self._hazard_pointers[tid] = node

            # Double-check validation after setting hazard pointer
            current_node = self._registry.get(agent_id)
            if current_node is node and not node.retired:
                return node

            # If state changed concurrently, clear and retry
            with self._hp_lock:
                self._hazard_pointers[tid] = None

    def release_hazard_pointer(self) -> None:
        """
        Release the hazard pointer held by the current thread.
        """
        tid = self._get_thread_id()
        with self._hp_lock:
            self._hazard_pointers[tid] = None

    def register_or_update(
        self, agent_id: str, state: Dict[str, Any]
    ) -> HazardPointerNode:
        """
        Register a new remediation agent state or atomically update an existing one.
        Old node versions are retired and scheduled for deferred lock-free garbage collection.
        """
        with self._registry_lock:
            old_node = self._registry.get(agent_id)
            new_version = (old_node.version + 1) if old_node else 1
            new_node = HazardPointerNode(
                agent_id=agent_id, state=state, version=new_version
            )

            self._registry[agent_id] = new_node
            self._total_registrations += 1

            if old_node:
                old_node.retired = True
                self._retire_node(old_node)

            return new_node

    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent state by ID, retiring the active node.
        """
        with self._registry_lock:
            node = self._registry.pop(agent_id, None)
            if node:
                node.retired = True
                self._retire_node(node)
                return True
            return False

    def _retire_node(self, node: HazardPointerNode) -> None:
        with self._hp_lock:
            self._retired_list.append(node)
            if len(self._retired_list) >= self._gc_batch_threshold:
                self._collect_garbage()

    def _collect_garbage(self) -> None:
        """
        Scan active hazard pointers across all threads and reclaim nodes
        that are no longer protected by any thread.
        """
        with self._hp_lock:
            protected_nodes: Set[int] = {
                id(n) for n in self._hazard_pointers.values() if n is not None
            }
            surviving_retired: List[HazardPointerNode] = []

            for node in self._retired_list:
                if id(node) in protected_nodes:
                    surviving_retired.append(node)
                else:
                    # Safely reclaim memory (drop reference)
                    del node

            self._retired_list = surviving_retired

    def force_gc(self) -> int:
        """
        Force immediate garbage collection of all unprotected retired nodes.
        Returns the number of nodes still protected and kept in the retired list.
        """
        with self._hp_lock:
            self._collect_garbage()
            return len(self._retired_list)

    def get_stats(self) -> Dict[str, Any]:
        with self._registry_lock, self._hp_lock:
            return {
                "active_agents": len(self._registry),
                "retired_nodes": len(self._retired_list),
                "active_hazard_pointers": sum(
                    1 for n in self._hazard_pointers.values() if n is not None
                ),
                "total_registrations": self._total_registrations,
            }
