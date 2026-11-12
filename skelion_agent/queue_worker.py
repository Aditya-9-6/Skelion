"""Application job handlers for the durable Redis Streams queue."""

import asyncio
import os
from typing import Any

from skelion_agent.config import get_async_redis
from skelion_agent.job_queue import DurableJobQueue, Job
from skelion_agent.worker import execute_sandboxed_autonomous_loop


async def handle_incident_process(payload: dict[str, Any]) -> None:
    org_id = payload["org_id"]
    incident_id = payload["incident_id"]
    await asyncio.to_thread(execute_sandboxed_autonomous_loop, org_id, incident_id)


async def run_worker_once(consumer: str | None = None) -> int:
    """Run one lease-aware queue pass; intended for a dedicated worker process."""
    queue = DurableJobQueue(get_async_redis())
    consumer_name = consumer or os.getenv("HOSTNAME", "worker")
    jobs = await queue.reclaim_stale(consumer_name)
    if jobs:
        processed = 0
        handlers = {"incident.process": handle_incident_process}
        for message_id, job in jobs:
            handler = handlers.get(job.kind)
            if not handler:
                await queue.retry(message_id, job)
                continue
            try:
                await handler(job.payload)
                await queue.ack(message_id)
                await queue.record_metric("processed")
                processed += 1
            except Exception:
                await queue.retry(message_id, job)
                await queue.record_metric("failed")
        return processed
    return await queue.process_once(
        consumer_name,
        {"incident.process": handle_incident_process},
    )
