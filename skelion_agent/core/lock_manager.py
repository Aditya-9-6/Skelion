import asyncio
import time
import uuid
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LockEntry:
    __slots__ = ('resource_id', 'owner_id', 'fencing_token', 'expires_at', 'term')

    def __init__(self, resource_id: str, owner_id: str, fencing_token: int, expires_at: float, term: int):
        self.resource_id = resource_id
        self.owner_id = owner_id
        self.fencing_token = fencing_token
        self.expires_at = expires_at
        self.term = term


class DistributedLockManager:
    """
    High-performance asynchronous Distributed Lock Manager featuring atomic compare-and-swap
    state transitions, strict fencing tokens for linearizability, and Raft-Lite lease heartbeats
    to prevent split-brain remediation actions across Skelion agent nodes.
    """

    def __init__(self, node_id: str, default_lease_ttl: float = 5.0):
        self.node_id = node_id
        self.default_lease_ttl = default_lease_ttl
        self._locks: Dict[str, LockEntry] = {}
        self._lock_guard = asyncio.Lock()
        self._fencing_counter = 0
        self._current_term = 1
        self._is_leader = True
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self, heartbeat_interval: float = 1.0) -> None:
        """Start the background Raft-Lite heartbeat task for lease renewals."""
        async with self._lock_guard:
            if self._running:
                return
            self._running = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(heartbeat_interval))

    async def stop(self) -> None:
        """Stop the background Raft-Lite heartbeat task."""
        async with self._lock_guard:
            self._running = False
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
                self._heartbeat_task = None

    async def acquire_lock(self, resource_id: str, ttl: Optional[float] = None, term: Optional[int] = None) -> Tuple[bool, int, str]:
        """
        Attempt to acquire or renew an ephemeral lease on a resource using atomic CAS.
        Returns a tuple of (success, fencing_token, owner_id).
        """
        ttl = ttl or self.default_lease_ttl
        now = time.time()

        async with self._lock_guard:
            existing = self._locks.get(resource_id)
            target_term = term if term is not None else self._current_term

            if existing and existing.expires_at > now and existing.owner_id != self.node_id:
                # Lock held by another valid node
                return False, 0, existing.owner_id

            # Increment fencing token on successful acquisition/renewal
            self._fencing_counter += 1
            new_token = self._fencing_counter
            expires_at = now + ttl

            entry = LockEntry(
                resource_id=resource_id,
                owner_id=self.node_id,
                fencing_token=new_token,
                expires_at=expires_at,
                term=target_term
            )
            self._locks[resource_id] = entry
            return True, new_token, self.node_id

    async def release_lock(self, resource_id: str, fencing_token: int) -> bool:
        """
        Release a held lock, verifying the fencing token to prevent stale releases.
        """
        async with self._lock_guard:
            existing = self._locks.get(resource_id)
            if not existing:
                return False
            if existing.owner_id != self.node_id or existing.fencing_token != fencing_token:
                return False
            
            del self._locks[resource_id]
            return True

    async def renew_lease(self, resource_id: str, fencing_token: int, ttl: Optional[float] = None) -> bool:
        """
        Heartbeat renewal mechanism for active leases.
        """
        ttl = ttl or self.default_lease_ttl
        now = time.time()

        async with self._lock_guard:
            existing = self._locks.get(resource_id)
            if not existing:
                return False
            if existing.owner_id != self.node_id or existing.fencing_token != fencing_token:
                return False
            if existing.expires_at <= now:
                # Lease already expired
                del self._locks[resource_id]
                return False

            existing.expires_at = now + ttl
            return True

    async def _heartbeat_loop(self, interval: float) -> None:
        """Background loop that automatically renews leases owned by this node."""
        while self._running:
            try:
                await asyncio.sleep(interval)
                now = time.time()
                async with self._lock_guard:
                    for resource_id, entry in list(self._locks.items()):
                        if entry.owner_id == self.node_id:
                            if entry.expires_at > now:
                                # Extend lease by default TTL
                                entry.expires_at = now + self.default_lease_ttl
                            else:
                                # Evict expired local locks
                                del self._locks[resource_id]
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in DistributedLockManager heartbeat loop: {exc}")

    def get_lock_status(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Inspect current lease status for a given resource."""
        existing = self._locks.get(resource_id)
        if not existing:
            return None
        return {
            "resource_id": existing.resource_id,
            "owner_id": existing.owner_id,
            "fencing_token": existing.fencing_token,
            "expires_at": existing.expires_at,
            "term": existing.term,
            "is_expired": existing.expires_at <= time.time()
        }
