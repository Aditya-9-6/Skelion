import threading
from collections import deque
from typing import Dict, Any, List, Optional
import random

try:
    from .heavy_hitters import HeavyHitters
except ImportError:
    pass


class TailSampledSpanBuffer:
    """
    A memory-bounded thread-safe ring buffer for distributed OpenTelemetry spans
    implementing tail-based sampling for error spans and high-cardinality attributes.
    """

    def __init__(
        self,
        max_size: int = 10000,
        error_sample_ratio: float = 1.0,
        default_sample_ratio: float = 0.1,
    ):
        self.max_size = max_size
        self.error_sample_ratio = error_sample_ratio
        self.default_sample_ratio = default_sample_ratio
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._error_count = 0
        self._total_ingested = 0

    def ingest_span(
        self, span: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Ingest a span extracted from W3C TraceContext headers and apply tail sampling.
        Returns True if the span was retained in the buffer, False if dropped.
        """
        if headers:
            traceparent = headers.get("traceparent") or headers.get("Traceparent")
            if traceparent:
                span["w3c_traceparent"] = traceparent
            tracestate = headers.get("tracestate") or headers.get("Tracestate")
            if tracestate:
                span["w3c_tracestate"] = tracestate

        status_code = span.get("status_code", 0)
        is_error = span.get("error", False) or (
            isinstance(status_code, int) and status_code >= 400
        )

        if is_error:
            sampled = random.random() <= self.error_sample_ratio
        else:
            sampled = random.random() <= self.default_sample_ratio

        with self._lock:
            self._total_ingested += 1
            if is_error:
                self._error_count += 1
            if sampled:
                self._buffer.append(span)
                return True
        return False

    def get_spans(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
            self._error_count = 0
            self._total_ingested = 0

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_ingested": self._total_ingested,
                "error_count": self._error_count,
                "buffered_count": len(self._buffer),
                "max_size": self.max_size,
            }


global_telemetry_buffer = TailSampledSpanBuffer()
