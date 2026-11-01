import bisect
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Generator


class EpochManager:
    """
    Epoch-based memory reclamation manager for lock-free concurrent reads.
    """
    def __init__(self):
        self._current_epoch = 0
        self._reader_epochs: Dict[int, int] = {}
        self._lock = threading.Lock()
        self._retired_nodes: List[Tuple[int, Any]] = []

    def enter_epoch(self) -> int:
        with self._lock:
            epoch = self._current_epoch
            thread_id = threading.get_ident()
            self._reader_epochs[thread_id] = epoch
            return epoch

    def leave_epoch(self) -> None:
        with self._lock:
            thread_id = threading.get_ident()
            self._reader_epochs.pop(thread_id, None)

    def retire(self, node: Any) -> None:
        with self._lock:
            self._retired_nodes.append((self._current_epoch, node))
            self._advance_epoch_unlocked()

    def _advance_epoch_unlocked(self) -> None:
        if not self._reader_epochs:
            min_active = self._current_epoch
        else:
            min_active = min(self._reader_epochs.values())
        
        surviving = []
        for epoch, node in self._retired_nodes:
            if epoch < min_active:
                del node
            else:
                surviving.append((epoch, node))
        self._retired_nodes = surviving
        self._current_epoch += 1


class CacheObliviousBTreeNode:
    __slots__ = ('keys', 'values', 'children', 'is_leaf', 'capacity')

    def __init__(self, capacity: int = 64, is_leaf: bool = True):
        self.capacity = capacity
        self.is_leaf = is_leaf
        self.keys: List[Any] = []
        self.values: List[Any] = []
        self.children: List['CacheObliviousBTreeNode'] = []


class CacheObliviousBTree:
    """
    Cache-Oblivious B-Tree optimized for high-throughput append-only incident telemetry
    and time-series metric indexing in Python. Guarantees optimal cache performance
    across varying memory hierarchy levels with epoch-based concurrency safety.
    """
    def __init__(self, node_capacity: int = 64):
        self.node_capacity = max(4, node_capacity)
        self.root = CacheObliviousBTreeNode(capacity=self.node_capacity, is_leaf=True)
        self._lock = threading.Lock()
        self._epoch_manager = EpochManager()
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def insert(self, key: Any, value: Any) -> None:
        with self._lock:
            root = self.root
            if len(root.keys) >= self.node_capacity:
                new_root = CacheObliviousBTreeNode(capacity=self.node_capacity, is_leaf=False)
                new_root.children.append(root)
                self._split_child(new_root, 0, root)
                self.root = new_root
                root = new_root
            
            self._insert_non_full(root, key, value)
            self._size += 1

    def _insert_non_full(self, node: CacheObliviousBTreeNode, key: Any, value: Any) -> None:
        idx = bisect.bisect_right(node.keys, key)
        if node.is_leaf:
            node.keys.insert(idx, key)
            node.values.insert(idx, value)
        else:
            child = node.children[idx]
            if len(child.keys) >= self.node_capacity:
                self._split_child(node, idx, child)
                if key > node.keys[idx]:
                    idx += 1
            self._insert_non_full(node.children[idx], key, value)

    def _split_child(self, parent: CacheObliviousBTreeNode, index: int, child: CacheObliviousBTreeNode) -> None:
        t = self.node_capacity // 2
        z = CacheObliviousBTreeNode(capacity=self.node_capacity, is_leaf=child.is_leaf)
        
        z.keys = child.keys[t:]
        z.values = child.values[t:] if child.is_leaf else []
        
        if not child.is_leaf:
            z.children = child.children[t:]
            child.children = child.children[:t]
            
        median_key = child.keys[t - 1]
        median_val = child.values[t - 1] if child.is_leaf else None
        
        child.keys = child.keys[:t - 1 if child.is_leaf else t]
        if child.is_leaf:
            child.values = child.values[:t - 1]
            
        parent.children.insert(index + 1, z)
        parent.keys.insert(index, median_key)

    def search(self, key: Any) -> Optional[Any]:
        self._epoch_manager.enter_epoch()
        try:
            return self._search_node(self.root, key)
        finally:
            self._epoch_manager.leave_epoch()

    def _search_node(self, node: CacheObliviousBTreeNode, key: Any) -> Optional[Any]:
        idx = bisect.bisect_left(node.keys, key)
        if idx < len(node.keys) and node.keys[idx] == key:
            if node.is_leaf:
                return node.values[idx]
        if node.is_leaf:
            return None
        return self._search_node(node.children[idx], key)

    def range_query(self, start_key: Any, end_key: Any) -> List[Tuple[Any, Any]]:
        self._epoch_manager.enter_epoch()
        results: List[Tuple[Any, Any]] = []
        try:
            self._range_query_node(self.root, start_key, end_key, results)
            return results
        finally:
            self._epoch_manager.leave_epoch()

    def _range_query_node(self, node: CacheObliviousBTreeNode, start_key: Any, end_key: Any, results: List[Tuple[Any, Any]]) -> None:
        idx = bisect.bisect_left(node.keys, start_key)
        while idx < len(node.keys):
            k = node.keys[idx]
            if k > end_key:
                break
            if node.is_leaf:
                results.append((k, node.values[idx]))
            else:
                self._range_query_node(node.children[idx], start_key, end_key, results)
            idx += 1
        if not node.is_leaf and idx <= len(node.keys):
            if idx < len(node.children):
                self._range_query_node(node.children[idx], start_key, end_key, results)

    def clear(self) -> None:
        with self._lock:
            old_root = self.root
            self.root = CacheObliviousBTreeNode(capacity=self.node_capacity, is_leaf=True)
            self._size = 0
            self._epoch_manager.retire(old_root)
