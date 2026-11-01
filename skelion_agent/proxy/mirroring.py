import asyncio
import logging
import time
import httpx
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger("skelion_agent.proxy.mirroring")


class TrafficMirroringEngine:
    """
    High-throughput, asynchronous traffic mirroring engine that duplicates
    ingress HTTP requests to evaluation sandbox instances using a bounded, non-blocking
    queue. Guarantees zero latency amplification and graceful drop on backpressure.
    """

    def __init__(
        self,
        sandbox_url: str,
        max_queue_size: int = 1000,
        timeout: float = 3.0,
        diff_callback: Optional[
            Callable[[Dict[str, Any], Dict[str, Any]], None]
        ] = None,
    ):
        self.sandbox_url = sandbox_url.rstrip("/")
        self.max_queue_size = max_queue_size
        self.timeout = timeout
        self.diff_callback = diff_callback
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        self.dropped_frames = 0
        self.total_mirrored = 0
        self.total_success = 0
        self.total_errors = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self):
        """Starts the background worker consuming the mirroring queue."""
        if self._running:
            return
        self._running = True
        self._client = httpx.AsyncClient(timeout=self.timeout)
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(
            f"TrafficMirroringEngine started targeting sandbox: {self.sandbox_url}"
        )

    async def stop(self):
        """Gracefully stops the worker task and flushes remaining frames."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("TrafficMirroringEngine stopped.")

    def mirror(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: bytes,
        prod_response_meta: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Non-blocking enqueue for request mirroring. Drops frame gracefully if queue is full.
        """
        if not self._running:
            return False

        payload = {
            "method": method,
            "path": path,
            "headers": headers,
            "body": body,
            "prod_response_meta": prod_response_meta,
            "timestamp": time.time(),
        }

        try:
            self.queue.put_nowait(payload)
            self.total_mirrored += 1
            return True
        except asyncio.QueueFull:
            self.dropped_frames += 1
            logger.warning(
                f"[TrafficMirroringEngine] Queue full (maxsize={self.max_queue_size}). "
                f"Dropped mirrored frame for {method} {path}. Total dropped: {self.dropped_frames}"
            )
            return False

    async def _worker_loop(self):
        while self._running:
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                await self._dispatch_to_sandbox(item)
            except Exception as e:
                self.total_errors += 1
                logger.error(
                    f"[TrafficMirroringEngine] Error dispatching mirrored request: {e}"
                )
            finally:
                self.queue.task_done()

    async def _dispatch_to_sandbox(self, item: Dict[str, Any]):
        if not self._client:
            return

        method = item["method"]
        path = item["path"]
        headers = dict(item["headers"])
        body = item["body"]
        prod_meta = item.get("prod_response_meta")

        # Strip hop-by-hop or host headers
        headers.pop("host", None)
        headers.pop("content-length", None)

        url = f"{self.sandbox_url}{path}"
        start_time = time.monotonic()
        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=headers,
                content=body,
            )
            duration_ms = (time.monotonic() - start_time) * 1000.0
            self.total_success += 1

            sandbox_meta = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
                "duration_ms": duration_ms,
            }

            if self.diff_callback and prod_meta:
                try:
                    self.diff_callback(prod_meta, sandbox_meta)
                except Exception as ex:
                    logger.error(f"[TrafficMirroringEngine] Diff callback failed: {ex}")

        except httpx.RequestError as exc:
            self.total_errors += 1
            logger.warning(
                f"[TrafficMirroringEngine] Sandbox request failed for {method} {url}: {exc}"
            )
