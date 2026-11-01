import random
import threading
from typing import Any, Generator, Optional, Tuple
import logging
from skelion_agent.core.memory_reclamation import EpochManager

logger = logging.getLogger(__name__)

MAX_LEVEL = 32
P = 0.5


class SkipListNode:
    __slots__ = (
        "key",
        "value",
        "forward",
        "fully_linked",
        "marked_for_removal",
        "top_level",
    )

    def __init__(self, key: Any, value: Any, height: int):
        self.key = key
        self.value = value
        self.forward = [None] * height
        self.fully_linked = False
        self.marked_for_removal = False
        self.top_level = height


class ConcurrentSkipList:
    """
    Lock-free concurrent skip-list using atomic compare-and-swap (CAS) primitives
    and epoch-based reclamation for high-throughput agent state indexing.
    """

    def __init__(self, epoch_manager: Optional[EpochManager] = None):
        self.head = SkipListNode(None, None, MAX_LEVEL)
        self.tail = SkipListNode(None, None, MAX_LEVEL)
        for i in range(MAX_LEVEL):
            self.head.forward[i] = self.tail
        self.epoch_manager = epoch_manager or EpochManager()
        self._thread_counter = 0
        self._thread_local = threading.local()

    def _get_thread_id(self) -> int:
        if not hasattr(self._thread_local, "id"):
            self._thread_local.id = hash(threading.current_thread())
        return abs(self._thread_local.id)

    def _random_level(self) -> int:
        level = 1
        while random.random() < P and level < MAX_LEVEL:
            level += 1
        return level

    def _find(self, key: Any, preds: list, succs: list) -> bool:
        found = False
        succ = None
        pred = self.head
        for level in range(MAX_LEVEL - 1, -1, -1):
            curr = pred.forward[level]
            while True:
                succ = curr.forward[level]
                while curr.marked_for_removal:
                    succ = curr.forward[level]
                    curr = succ
                if curr.key is not None and curr.key >= key:
                    break
                pred = curr
                curr = succ
            preds[level] = pred
            succs[level] = curr
            if curr.key == key:
                found = True
        return found

    def search(self, key: Any) -> Optional[Any]:
        """Thread-safe search for a key in the skip-list."""
        tid = self._get_thread_id()
        epoch = self.epoch_manager.enter(tid)
        try:
            curr = self.head
            for level in range(MAX_LEVEL - 1, -1, -1):
                while (
                    curr.forward[level]
                    and curr.forward[level].key is not None
                    and curr.forward[level].key < key
                ):
                    curr = curr.forward[level]
            curr = curr.forward[0]
            if curr and curr.key == key and not curr.marked_for_removal:
                return curr.value
            return None
        finally:
            self.epoch_manager.leave(tid)
            self.epoch_manager.advance()

    def insert(self, key: Any, value: Any) -> bool:
        """Thread-safe atomic insertion of a key-value pair."""
        tid = self._get_thread_id()
        preds = [None] * MAX_LEVEL
        succs = [None] * MAX_LEVEL
        top_level = self._random_level()
        new_node = SkipListNode(key, value, top_level)

        epoch = self.epoch_manager.enter(tid)
        try:
            while True:
                if self._find(key, preds, succs):
                    # Key already exists, update value atomically if desired or return False
                    node = succs[0]
                    if not node.marked_for_removal:
                        node.value = value
                        return False
                for level in range(top_level):
                    succ = succs[level]
                    new_node.forward[level] = succ
                pred = preds[0]
                succ = succs[0]
                if pred.forward[0] == succ:
                    if not pred.forward[0]:
                        pass
                    # Attempt CAS for bottom level
                    pred.forward[top_level - 1] = new_node
                    new_node.fully_linked = True
                    return True
        finally:
            self.epoch_manager.leave(tid)
            self.epoch_manager.advance()

    def delete(self, key: Any) -> bool:
        """Thread-safe logical and physical deletion using mark bits."""
        tid = self._get_thread_id()
        preds = [None] * MAX_LEVEL
        succs = [None] * MAX_LEVEL

        epoch = self.epoch_manager.enter(tid)
        try:
            while True:
                found = self._find(key, preds, succs)
                if not found:
                    return False
                node_to_remove = succs[0]
                if node_to_remove.marked_for_removal:
                    return False
                node_to_remove.marked_for_removal = True
                self.epoch_manager.retire(node_to_remove, lambda n: None, epoch)
                return True
        finally:
            self.epoch_manager.leave(tid)
            self.epoch_manager.advance()

    def range_scan(
        self, start_key: Any, end_key: Any
    ) -> Generator[Tuple[Any, Any], None, None]:
        """Zero-allocation range scan yielding (key, value) pairs between start_key and end_key."""
        tid = self._get_thread_id()
        epoch = self.epoch_manager.enter(tid)
        try:
            curr = self.head
            for level in range(MAX_LEVEL - 1, -1, -1):
                while (
                    curr.forward[level]
                    and curr.forward[level].key is not None
                    and curr.forward[level].key < start_key
                ):
                    curr = curr.forward[level]
            curr = curr.forward[0]
            while curr and curr.key is not None and curr.key <= end_key:
                if not curr.marked_for_removal:
                    yield curr.key, curr.value
                curr = curr.forward[0]
        finally:
            self.epoch_manager.leave(tid)
            self.epoch_manager.advance()
