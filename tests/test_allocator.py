import concurrent.futures
from skelion_agent.allocator import EpollSlabAllocator


def test_allocator_basic_allocation():
    allocator = EpollSlabAllocator(block_size=1024, total_blocks=10)
    stats = allocator.stats()
    assert stats["total_blocks"] == 10
    assert stats["free"] == 10
    assert stats["allocated"] == 0

    block = allocator.allocate()
    assert block is not None
    assert block.in_use is True
    assert len(block.borrow_slice()) == 1024

    stats_after = allocator.stats()
    assert stats_after["allocated"] == 1
    assert stats_after["free"] == 9

    allocator.release(block)
    assert block.in_use is False
    assert allocator.stats()["free"] == 10


def test_allocator_exhaustion():
    allocator = EpollSlabAllocator(block_size=512, total_blocks=2)
    b1 = allocator.allocate()
    b2 = allocator.allocate()
    b3 = allocator.allocate()

    assert b1 is not None
    assert b2 is not None
    assert b3 is None

    allocator.release(b1)
    b4 = allocator.allocate()
    assert b4 is not None


def test_zero_copy_memoryview_slice():
    allocator = EpollSlabAllocator(block_size=256, total_blocks=4)
    block = allocator.allocate()
    mv = block.borrow_slice(64)
    assert isinstance(mv, memoryview)
    assert len(mv) == 64

    # Write data into memoryview and verify buffer update
    mv[:5] = b"HELLO"
    assert block.buffer[block.offset : block.offset + 5] == b"HELLO"
    allocator.release(block)


def test_concurrent_slab_allocation():
    allocator = EpollSlabAllocator(block_size=128, total_blocks=256)
    num_threads = 16
    iterations_per_thread = 100

    def worker():
        for _ in range(iterations_per_thread):
            blk = allocator.allocate()
            if blk:
                mv = blk.borrow_slice(32)
                mv[:4] = b"TEST"
                allocator.release(blk)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker) for _ in range(num_threads)]
        concurrent.futures.wait(futures)

    stats = allocator.stats()
    assert stats["allocated"] == 0
    assert stats["free"] == 256
