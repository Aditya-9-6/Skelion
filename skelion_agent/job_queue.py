"""Durable Redis Streams job queue for horizontally scaled workers."""

import json
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class Job:
    id: str
    kind: str
    payload: dict[str, Any]
    attempts: int = 0


class DurableJobQueue:
    def __init__(
        self,
        redis_client,
        stream: str = "skelion:jobs",
        group: str = "skelion-workers",
        dead_letter_stream: str = "skelion:jobs:dead",
    ):
        self.redis = redis_client
        self.stream = stream
        self.group = group
        self.dead_letter_stream = dead_letter_stream

    async def ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(
                self.stream, self.group, id="0", mkstream=True
            )
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def enqueue(self, kind: str, payload: dict[str, Any]) -> str:
        job_id = f"job_{uuid.uuid4().hex}"
        await self.redis.xadd(
            self.stream,
            {"job": json.dumps({"id": job_id, "kind": kind, "payload": payload})},
            maxlen=100000,
            approximate=True,
        )
        return job_id

    async def claim(
        self, consumer: str, block_ms: int = 5000, count: int = 10
    ) -> list[tuple[str, Job]]:
        await self.ensure_group()
        messages = await self.redis.xreadgroup(
            self.group,
            consumer,
            {self.stream: ">"},
            count=count,
            block=block_ms,
        )
        jobs: list[tuple[str, Job]] = []
        for _, entries in messages or []:
            for message_id, values in entries:
                raw = values.get("job") or values.get(b"job")
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                data = json.loads(raw)
                jobs.append(
                    (
                        message_id.decode() if isinstance(message_id, bytes) else message_id,
                        Job(
                            id=data["id"],
                            kind=data["kind"],
                            payload=data["payload"],
                            attempts=int(data.get("attempts", 0)),
                        ),
                    )
                )
        return jobs

    async def ack(self, message_id: str) -> int:
        return await self.redis.xack(self.stream, self.group, message_id)

    async def retry(self, message_id: str, job: Job, max_attempts: int = 5) -> bool:
        attempts = job.attempts + 1
        await self.redis.xack(self.stream, self.group, message_id)
        if attempts >= max_attempts:
            await self.redis.xadd(
                self.dead_letter_stream,
                {
                    "job": json.dumps(
                        {
                            "id": job.id,
                            "kind": job.kind,
                            "payload": job.payload,
                            "attempts": attempts,
                        }
                    )
                },
                maxlen=100000,
                approximate=True,
            )
            return False
        await self.redis.xadd(
            self.stream,
            {
                "job": json.dumps(
                    {
                        "id": job.id,
                        "kind": job.kind,
                        "payload": job.payload,
                        "attempts": attempts,
                    }
                )
            },
            maxlen=100000,
            approximate=True,
        )
        return True

    async def process_once(
        self,
        consumer: str,
        handlers: dict[str, Callable[[dict[str, Any]], Awaitable[None]]],
        block_ms: int = 1000,
        max_attempts: int = 5,
    ) -> int:
        """Claim and process one batch, acknowledging only successful jobs."""
        processed = 0
        for message_id, job in await self.claim(consumer, block_ms=block_ms, count=10):
            handler = handlers.get(job.kind)
            if handler is None:
                await self.retry(message_id, job, max_attempts=max_attempts)
                continue
            try:
                await handler(job.payload)
            except Exception:
                await self.retry(message_id, job, max_attempts=max_attempts)
                continue
            await self.ack(message_id)
            processed += 1
        return processed
