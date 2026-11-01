import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from skelion_agent.proxy.mirroring import TrafficMirroringEngine


@pytest.mark.asyncio
async def test_mirroring_engine_lifecycle():
    engine = TrafficMirroringEngine(sandbox_url="http://test-sandbox", max_queue_size=5)
    assert not engine._running
    await engine.start()
    assert engine._running
    assert engine._client is not None

    success = engine.mirror(
        "POST",
        "/api/v1/agents",
        {"content-type": "application/json"},
        b'{"test": true}',
    )
    assert success
    assert engine.total_mirrored == 1

    await engine.stop()
    assert not engine._running
    assert engine._client is None


@pytest.mark.asyncio
async def test_mirroring_engine_backpressure_drop():
    engine = TrafficMirroringEngine(sandbox_url="http://test-sandbox", max_queue_size=2)
    await engine.start()

    # Fill up queue beyond capacity without worker consuming fast enough
    # Pause worker by not letting it process immediately or setting queue manually
    engine.queue._queue.append(
        {"method": "GET", "path": "/1", "headers": {}, "body": b"", "timestamp": 0}
    )
    engine.queue._queue.append(
        {"method": "GET", "path": "/2", "headers": {}, "body": b"", "timestamp": 0}
    )

    # Queue is now at max_queue_size (2)
    success = engine.mirror("GET", "/overflow", {}, b"")
    assert not success
    assert engine.dropped_frames == 1

    await engine.stop()


@pytest.mark.asyncio
async def test_mirroring_engine_dispatch_with_diff():
    diff_results = []

    def mock_diff_cb(prod, sand):
        diff_results.append((prod, sand))

    engine = TrafficMirroringEngine(
        sandbox_url="http://test-sandbox", max_queue_size=10, diff_callback=mock_diff_cb
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"status": "ok"}'

    with patch.object(engine, "_client", new_callable=AsyncMock) as mock_client:
        mock_client.request.return_value = mock_response
        await engine.start()

        prod_meta = {"status_code": 200, "body": '{"status": "ok"}'}
        engine.mirror("GET", "/health", {}, b"", prod_response_meta=prod_meta)

        # Wait briefly for worker consumption
        for _ in range(20):
            if engine.total_success > 0:
                break
            await asyncio.sleep(0.05)

        await engine.stop()
        assert engine.total_success == 1
        assert len(diff_results) == 1
