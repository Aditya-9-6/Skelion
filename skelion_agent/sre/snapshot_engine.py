import asyncio
import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional
from skelion_agent.sre.channel_tracker import BoundedFIFOChannelTracker


class ChandyLamportSnapshotEngine:
    """Asynchronous Chandy-Lamport distributed snapshot engine capturing globally consistent state checkpoints."""

    def __init__(self, node_id: str, state_provider: Callable[[], Dict[str, Any]]) -> None:
        self.node_id = node_id
        self.state_provider = state_provider
        self.channels: Dict[str, BoundedFIFOChannelTracker] = {}
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self._marker_received: Dict[str, bool] = {}
        self._lock = asyncio.Lock()

    def register_channel(self, channel_id: str, tracker: BoundedFIFOChannelTracker) -> None:
        self.channels[channel_id] = tracker

    async def initiate_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        async with self._lock:
            local_state = self.state_provider()
            timestamp = time.time()
            
            # Start recording on all incoming/outgoing channels
            for tracker in self.channels.values():
                await tracker.start_recording()

            snapshot = {
                "snapshot_id": snapshot_id,
                "node_id": self.node_id,
                "timestamp": timestamp,
                "local_state": local_state,
                "in_flight_messages": {},
            }
            self._snapshots[snapshot_id] = snapshot
            return snapshot

    async def receive_marker(self, snapshot_id: str, from_channel: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            if snapshot_id not in self._snapshots:
                # First time seeing marker, take local snapshot and start recording on other channels
                local_state = self.state_provider()
                timestamp = time.time()
                for cid, tracker in self.channels.items():
                    if cid != from_channel:
                        await tracker.start_recording()
                
                # Stop recording on the channel the marker arrived from
                recorded = []
                if from_channel in self.channels:
                    recorded = await self.channels[from_channel].stop_recording()

                snapshot = {
                    "snapshot_id": snapshot_id,
                    "node_id": self.node_id,
                    "timestamp": timestamp,
                    "local_state": local_state,
                    "in_flight_messages": {from_channel: recorded},
                }
                self._snapshots[snapshot_id] = snapshot
                self._marker_received[snapshot_id] = True
                return snapshot
            else:
                # Already took snapshot, stop recording on this channel
                recorded = []
                if from_channel in self.channels:
                    recorded = await self.channels[from_channel].stop_recording()
                
                self._snapshots[snapshot_id]["in_flight_messages"][from_channel] = recorded
                return self._snapshots[snapshot_id]

    def get_serialized_manifest(self, snapshot_id: str) -> str:
        if snapshot_id not in self._snapshots:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        snapshot_data = self._snapshots[snapshot_id]
        raw = json.dumps(snapshot_data, sort_keys=True).encode("utf-8")
        checksum = hashlib.sha256(raw).hexdigest()
        
        manifest = {
            "snapshot": snapshot_data,
            "checksum": checksum,
        }
        return json.dumps(manifest, sort_keys=True)
