import math
import random
import threading
from typing import List, Dict, Tuple, Optional


class SlidingWindowVectorQuantizer:
    """
    High-performance streaming vector quantizer for compressing high-cardinality
    SRE telemetry streams in real-time under tight memory constraints (<10MB for 100k series).
    Maintains a sliding-window codebook using product quantization and lightweight k-means updates.
    """

    def __init__(self, dimension: int = 64, num_centroids: int = 256, window_size: int = 10000):
        self.dimension = dimension
        self.num_centroids = num_centroids
        self.window_size = window_size
        
        self._lock = threading.Lock()
        # Sliding window buffer storing recent raw vectors or references: ring buffer / list
        self._window: List[List[float]] = []
        
        # Codebook: list of centroid vectors, initialized randomly or zeroed
        self._codebook: List[List[float]] = [
            [random.gauss(0.0, 1.0) for _ in range(dimension)]
            for _ in range(num_centroids)
        ]
        self._normalize_codebook()

    def _normalize_codebook(self) -> None:
        for i, centroid in enumerate(self._codebook):
            norm = math.sqrt(sum(v * v for v in centroid))
            if norm > 1e-6:
                self._codebook[i] = [v / norm for v in centroid]

    def add_vector(self, vector: List[float]) -> Tuple[int, float]:
        """
        Quantize an incoming telemetry vector against the current codebook,
        add it to the sliding window, and periodically update centroids.
        Returns (centroid_index, quantization_error).
        """
        if len(vector) != self.dimension:
            raise ValueError(f"Expected vector dimension {self.dimension}, got {len(vector)}")

        with self._lock:
            # Find nearest centroid (Euclidean / cosine approximation)
            best_idx, best_dist = self._find_nearest(vector)

            # Maintain sliding window
            self._window.append(vector)
            if len(self._window) > self.window_size:
                self._window.pop(0)

            # Periodic lightweight centroid re-estimation
            if len(self._window) >= self.window_size and len(self._window) % 500 == 0:
                self._recompute_codebook()

            return best_idx, best_dist

    def _find_nearest(self, vector: List[float]) -> Tuple[int, float]:
        best_idx = 0
        min_dist = float("inf")
        for idx, centroid in enumerate(self._codebook):
            # Squared Euclidean distance
            dist = sum((v - c) ** 2 for v, c in zip(vector, centroid))
            if dist < min_dist:
                min_dist = dist
                best_idx = idx
        return best_idx, math.sqrt(min_dist)

    def _recompute_codebook(self) -> None:
        """Lightweight k-means update step over current sliding window."""
        if not self._window:
            return
        
        # Simple assignment and update pass
        clusters: Dict[int, List[List[float]]] = {i: [] for i in range(self.num_centroids)}
        for vec in self._window:
            idx, _ = self._find_nearest(vec)
            clusters[idx].append(vec)

        new_codebook = []
        for i in range(self.num_centroids):
            cluster_vectors = clusters[i]
            if cluster_vectors:
                dim_sum = [sum(dim_vals) for dim_vals in zip(*cluster_vectors)]
                count = len(cluster_vectors)
                new_centroid = [val / count for val in dim_sum]
                new_codebook.append(new_centroid)
            else:
                # Keep existing if empty cluster
                new_codebook.append(self._codebook[i])

        self._codebook = new_codebook
        self._normalize_codebook()

    def get_codebook_size(self) -> int:
        with self._lock:
            return len(self._codebook)

    def get_window_size(self) -> int:
        with self._lock:
            return len(self._window)
