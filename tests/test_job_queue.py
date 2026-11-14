import json

import pytest

from skelion_agent.job_queue import DurableJobQueue, Job


class FakeRedis:
    def __init__(self):
        self.calls = []

    async def xgroup_create(self, *args, **kwargs):
        self.calls.append(("xgroup_create", args, kwargs))

    async def xadd(self, *args, **kwargs):
        self.calls.append(("xadd", args, kwargs))
        return "1-0"

    async def xack(self, *args, **kwargs):
        self.calls.append(("xack", args, kwargs))
        return 1


@pytest.mark.asyncio
async def test_enqueue_and_retry_dead_letters_after_limit():
    redis = FakeRedis()
    queue = DurableJobQueue(redis)
    job = Job("job_1", "agent.run", {"org_id": "org_1"}, attempts=4)

    await queue.enqueue("agent.run", {"org_id": "org_1"})
    assert any(call[0] == "xadd" for call in redis.calls)
    assert await queue.retry("1-0", job, max_attempts=5) is False
    dead_letter_call = redis.calls[-1]
    assert dead_letter_call[0] == "xadd"
    assert "skelion:jobs:dead" in dead_letter_call[1]
    payload = json.loads(dead_letter_call[1][1]["job"])
    assert payload["attempts"] == 5


@pytest.mark.asyncio
async def test_process_once_acknowledges_successful_handler():
    redis = FakeRedis()
    queue = DurableJobQueue(redis)
    queue.claim = lambda *args, **kwargs: None
    processed = []

    async def handler(payload):
        processed.append(payload["id"])

    async def fake_claim(*args, **kwargs):
        return [("1-0", Job("job_1", "test", {"id": "item-1"}))]

    queue.claim = fake_claim
    assert await queue.process_once("worker-1", {"test": handler}) == 1
    assert processed == ["item-1"]
    assert any(call[0] == "xack" for call in redis.calls)
