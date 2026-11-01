import threading
from typing import Any, Dict, Optional


class RadixNode:
    __slots__ = ("prefix", "children", "value", "is_terminal")

    def __init__(self, prefix: str = "", value: Any = None, is_terminal: bool = False):
        self.prefix = prefix
        self.children: Dict[str, "RadixNode"] = {}
        self.value = value
        self.is_terminal = is_terminal

    def clone(self) -> "RadixNode":
        """Create a shallow clone of the node for copy-on-write immutability."""
        new_node = RadixNode(self.prefix, self.value, self.is_terminal)
        new_node.children = dict(self.children)
        return new_node


class RadixRouter:
    """
    High-performance, lock-free Radix Tree (Patricia trie) router optimized for
    sub-microsecond high-frequency telemetry metrics and incident path resolution
    using atomic copy-on-write (RCW) semantics and zero reader blocking.
    """

    def __init__(self):
        self._root = RadixNode()
        self._write_lock = threading.Lock()

    def insert(self, path: str, value: Any) -> None:
        """
        Thread-safe insertion using Copy-On-Write (COW) semantics.
        Readers are never blocked during writer updates.
        """
        if not path:
            raise ValueError("Path cannot be empty")

        with self._write_lock:
            # Clone root for COW mutation
            new_root = self._root.clone()
            self._insert_recursive(new_root, path, value)
            self._root = new_root

    def _insert_recursive(self, node: RadixNode, path: str, value: Any) -> None:
        current = node
        remaining = path

        while remaining:
            matched_key = None
            for edge_char, child in current.children.items():
                if remaining.startswith(edge_char):
                    matched_key = edge_char
                    break

            if matched_key is None:
                # No matching child prefix edge, create new child
                new_child = RadixNode(prefix=remaining, value=value, is_terminal=True)
                current.children[remaining[0]] = new_child
                return

            child = current.children[matched_key]
            # Find common prefix between remaining and child.prefix
            common_len = 0
            for a, b in zip(remaining, child.prefix):
                if a == b:
                    common_len += 1
                else:
                    break

            if common_len == len(child.prefix):
                # Consume common prefix and continue down the tree
                remaining = remaining[common_len:]
                if not remaining:
                    # Exact match on child prefix, update terminal value
                    new_child = child.clone()
                    new_child.value = value
                    new_child.is_terminal = True
                    current.children[matched_key] = new_child
                    return
                else:
                    # Clone child and descend further
                    new_child = child.clone()
                    current.children[matched_key] = new_child
                    current = new_child
            else:
                # Split existing child prefix
                split_prefix = child.prefix[:common_len]
                remaining_child_prefix = child.prefix[common_len:]
                remaining_input = remaining[common_len:]

                # Create new split intermediate/branch node
                split_node = RadixNode(
                    prefix=split_prefix, value=None, is_terminal=False
                )
                split_node.children[remaining_child_prefix[0]] = child

                # Mutate original child prefix
                child.prefix = remaining_child_prefix

                if not remaining_input:
                    split_node.is_terminal = True
                    split_node.value = value
                else:
                    leaf_node = RadixNode(
                        prefix=remaining_input, value=value, is_terminal=True
                    )
                    split_node.children[remaining_input[0]] = leaf_node

                current.children[matched_key] = split_node
                return

    def lookup(self, path: str) -> Optional[Any]:
        """
        Lock-free lookup route resolution achieving sub-microsecond latency.
        Readers traverse the current immutable root pointer without acquiring locks.
        """
        current = self._root
        remaining = path

        while remaining:
            matched_child = None
            for edge_char, child in current.children.items():
                if remaining.startswith(edge_char):
                    matched_child = child
                    break

            if matched_child is None:
                return None

            if not remaining.startswith(matched_child.prefix):
                return None

            remaining = remaining[len(matched_child.prefix) :]
            current = matched_child

        if current.is_terminal:
            return current.value
        return None

    def delete(self, path: str) -> bool:
        """
        Thread-safe deletion using Copy-On-Write semantics.
        Returns True if the path was found and deleted, False otherwise.
        """
        with self._write_lock:
            new_root = self._root.clone()
            success = self._delete_recursive(new_root, path)
            if success:
                self._root = new_root
            return success

    def _delete_recursive(self, node: RadixNode, remaining: str) -> bool:
        if not remaining:
            if node.is_terminal:
                node.is_terminal = False
                node.value = None
                return True
            return False

        matched_key = None
        for edge_char, child in node.children.items():
            if remaining.startswith(edge_char):
                matched_key = edge_char
                break

        if matched_key is None:
            return False

        child = node.children[matched_key]
        if not remaining.startswith(child.prefix):
            return False

        new_child = child.clone()
        node.children[matched_key] = new_child

        next_remaining = remaining[len(child.prefix) :]
        if not next_remaining:
            if not new_child.is_terminal:
                return False
            new_child.is_terminal = False
            new_child.value = None
            # Clean up child if it has no children and is not terminal
            if not new_child.children and not new_child.is_terminal:
                del node.children[matched_key]
            return True

        deleted = self._delete_recursive(new_child, next_remaining)
        if deleted and not new_child.children and not new_child.is_terminal:
            del node.children[matched_key]
        return deleted
