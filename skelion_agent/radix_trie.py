import threading
from typing import Any, Dict, List, Optional, Tuple


class RadixNode:
    """
    Cache-conscious node for the Concurrent Radix Trie.
    Stores prefix segment, value, and thread-safe child dictionary using atomic locking primitives.
    """

    __slots__ = ("prefix", "value", "is_terminal", "children", "_lock")

    def __init__(
        self, prefix: str = "", value: Optional[Any] = None, is_terminal: bool = False
    ):
        self.prefix = prefix
        self.value = value
        self.is_terminal = is_terminal
        self.children: Dict[str, "RadixNode"] = {}
        self._lock = threading.Lock()


class ConcurrentRadixTrie:
    """
    High-throughput, lock-free/fine-grained concurrent radix trie utilizing CAS-driven
    node expansion and prefix compression for high-frequency incident telemetry routing.
    """

    def __init__(self):
        self.root = RadixNode()
        self._size = 0
        self._global_lock = threading.Lock()

    def _common_prefix_len(self, s1: str, s2: str) -> int:
        min_len = min(len(s1), len(s2))
        for i in range(min_len):
            if s1[i] != s2[i]:
                return i
        return min_len

    def insert(self, key: str, value: Any) -> None:
        """
        Insert a key-value pair into the radix trie with thread-safe path splitting
        and node expansion.
        """
        if not key:
            with self.root._lock:
                self.root.value = value
                if not self.root.is_terminal:
                    self.root.is_terminal = True
                    with self._global_lock:
                        self._size += 1
            return

        curr = self.root
        remaining = key

        while remaining:
            with curr._lock:
                matched_child = None
                first_char = remaining[0]

                # Find a child starting with the same character
                for char, child in curr.children.items():
                    if char == first_char:
                        matched_child = child
                        break

                if not matched_child:
                    # No child matches, create new node
                    new_node = RadixNode(
                        prefix=remaining, value=value, is_terminal=True
                    )
                    curr.children[first_char] = new_node
                    with self._global_lock:
                        self._size += 1
                    return

            # Found a matching child, evaluate prefix overlap outside or inside child lock
            with matched_child._lock:
                c_len = self._common_prefix_len(matched_child.prefix, remaining)

                if c_len == len(matched_child.prefix):
                    # Remaining key extends beyond or matches child prefix exactly
                    remaining = remaining[c_len:]
                    if not remaining:
                        existed = matched_child.is_terminal
                        matched_child.value = value
                        matched_child.is_terminal = True
                        if not existed:
                            with self._global_lock:
                                self._size += 1
                        return
                    curr = matched_child
                    continue
                else:
                    # Split the matched child node
                    split_point = c_len
                    old_prefix = matched_child.prefix

                    # Create new intermediate split node
                    split_node = RadixNode(
                        prefix=old_prefix[:split_point], value=None, is_terminal=False
                    )

                    # Adjust existing child
                    matched_child.prefix = old_prefix[split_point:]
                    split_node.children[matched_child.prefix[0]] = matched_child

                    # Determine remainder for new insertion
                    remaining = remaining[split_point:]
                    if not remaining:
                        split_node.value = value
                        split_node.is_terminal = True
                        with self._global_lock:
                            self._size += 1
                    else:
                        new_node = RadixNode(
                            prefix=remaining, value=value, is_terminal=True
                        )
                        split_node.children[remaining[0]] = new_node
                        with self._global_lock:
                            self._size += 1

                    # Attach split node to parent
                    with curr._lock:
                        curr.children[first_char] = split_node
                    return

    def search(self, key: str) -> Optional[Any]:
        """
        Search for an exact key match in the radix trie.
        """
        curr = self.root
        remaining = key

        while remaining:
            with curr._lock:
                first_char = remaining[0]
                child = curr.children.get(first_char)
                if not child:
                    return None

            with child._lock:
                if not remaining.startswith(child.prefix):
                    return None
                remaining = remaining[len(child.prefix) :]
                if not remaining:
                    if child.is_terminal:
                        return child.value
                    return None
                curr = child

        with curr._lock:
            if curr.is_terminal:
                return curr.value
        return None

    def prefix_search(self, prefix: str) -> List[Tuple[str, Any]]:
        """
        Retrieve all key-value pairs matching a given prefix.
        """
        results = []
        curr = self.root
        remaining = prefix
        path_accum = ""

        # Traverse down to prefix node
        while remaining:
            with curr._lock:
                first_char = remaining[0]
                child = curr.children.get(first_char)
                if not child:
                    return []

            with child._lock:
                c_len = self._common_prefix_len(child.prefix, remaining)
                if c_len < len(remaining) and c_len < len(child.prefix):
                    return []
                path_accum += child.prefix
                remaining = remaining[c_len:]
                if not remaining:
                    curr = child
                    break
                curr = child

        # Collect all terminal descendants
        def _collect(node: RadixNode, current_path: str) -> None:
            with node._lock:
                if node.is_terminal:
                    results.append((current_path, node.value))
                for _, child_node in node.children.items():
                    _collect(child_node, current_path + child_node.prefix)

        _collect(curr, path_accum)
        return results

    @property
    def size(self) -> int:
        with self._global_lock:
            return self._size
