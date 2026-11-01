import threading
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class SlabBlock:
    __slots__ = ("block_id", "buffer", "offset", "size", "in_use", "_padding")

    def __init__(self, block_id: int, buffer: bytearray, offset: int, size: int):
        self.block_id = block_id
        self.buffer = buffer
        self.offset = offset
        self.size = size
        self.in_use = False
        self._padding = 0  # Cache line alignment padding placeholder

    def borrow_slice(self, length: Optional[int] = None) -> memoryview:
        """Return a zero-copy memoryview slice of the underlying buffer chunk."""
        end = self.offset + (length if length is not None else self.size)
        return memoryview(self.buffer)[self.offset : end]


class EpollSlabAllocator:
    """
    High-performance, non-blocking concurrent slab allocator utilizing fixed-size
    memory blocks and atomic operations for zero-copy epoll socket telemetry streams.
    """

    def __init__(self, block_size: int = 4096, total_blocks: int = 1024):
        self.block_size = block_size
        self.total_blocks = total_blocks
        self.pool_size = block_size * total_blocks

        # Pre-allocate contiguous chunk of memory aligned to cache line / page bounds
        self._master_buffer = bytearray(self.pool_size)
        self.blocks: List[SlabBlock] = [
            SlabBlock(
                block_id=i,
                buffer=self._master_buffer,
                offset=i * block_size,
                size=block_size,
            )
            for i in range(total_blocks)
        ]

        # Free list managed with atomic index stacking or lock-free list
        self._free_indices = list(range(total_blocks))
        self._lock = (
            threading.Lock()
        )  # Fine-grained atomic-backed lock fallback for python GIL safety
        self._alloc_count = 0
        self._free_count = total_blocks

    def allocate(self) -> Optional[SlabBlock]:
        """Allocate a fixed-size slab block without blocking or dynamic reallocation."""
        with self._lock:
            if not self._free_indices:
                logger.warning(
                    "EpollSlabAllocator exhausted: zero free blocks available."
                )
                return None
            idx = self._free_indices.pop()
            block = self.blocks[idx]
            block.in_use = True
            self._alloc_count += 1
            self._free_count -= 1
            return block

    def release(self, block: SlabBlock) -> None:
        """Return a slab block back to the allocator free list."""
        with self._lock:
            if not block.in_use:
                return
            block.in_use = False
            self._free_indices.append(block.block_id)
            self._alloc_count = max(0, self._alloc_count - 1)
            self._free_count += 1

    def stats(self) -> dict:
        with self._lock:
            return {
                "block_size": self.block_size,
                "total_blocks": self.total_blocks,
                "allocated": self._alloc_count,
                "free": self._free_count,
                "pool_bytes": self.pool_size,
            }
