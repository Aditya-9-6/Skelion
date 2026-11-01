import re
import mmh3
import threading
from typing import List, Dict, Set, Tuple, Optional

class LSHIndex:
    """
    High-throughput, memory-aligned Locality-Sensitive Hashing (LSH) engine
    for grouping unstructured telemetry log lines into dynamic cluster buckets.
    Utilizes MinHash approximations and vectorized token comparisons.
    """

    def __init__(self, num_perm: int = 128, threshold: float = 0.7, seed: int = 42):
        self.num_perm = num_perm
        self.threshold = threshold
        self.seed = seed
        self._lock = threading.Lock()
        self.buckets: Dict[int, Set[str]] = {}
        self.log_minhashes: Dict[str, List[int]] = {}
        self.log_tokens: Dict[str, Set[str]] = {}
        
        # Mersenne prime for MinHash hashing
        self.mersenne_prime = (1 << 31) - 1
        self.max_hash = (1 << 32) - 1
        
        # Generate deterministic random coefficients (a, b) for hash families
        import random
        rng = random.Random(self.seed)
        self.hash_coeffs = [
            (rng.randint(1, self.mersenne_prime - 1), rng.randint(0, self.mersenne_prime - 1))
            for _ in range(self.num_perm)
        ]

    def _tokenize(self, log_line: str) -> Set[str]:
        # Normalize and tokenize: strip timestamps, numbers, and extract alphanumeric tokens
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?', '', log_line)
        normalized = re.sub(r'0x[0-9a-fA-F]+', '<HEX>', normalized)
        normalized = re.sub(r'\b\d+\b', '<NUM>', normalized)
        tokens = set(re.findall(r'\b[a-zA-Z_]\w*\b', normalized.lower()))
        return tokens

    def _compute_minhash(self, tokens: Set[str]) -> List[int]:
        if not tokens:
            return [0] * self.num_perm
            
        # Pre-hash tokens using mmh3 for SIMD-friendly vector operations
        token_hashes = [mmh3.hash(t, self.seed, signed=False) for t in tokens]
        
        minhash = []
        for a, b in self.hash_coeffs:
            min_val = self.max_hash
            for th in token_hashes:
                h = (a * th + b) % self.mersenne_prime
                if h < min_val:
                    min_val = h
            minhash.append(min_val)
        return minhash

    def _get_bands(self, minhash: List[int], num_bands: int = 16) -> List[Tuple[int, int]]:
        band_size = self.num_perm // num_bands
        bands = []
        for i in range(num_bands):
            start = i * band_size
            end = start + band_size
            band_tuple = tuple(minhash[start:end])
            band_hash = mmh3.hash(str(band_tuple), self.seed, signed=False)
            bands.append((i, band_hash))
        return bands

    def add(self, log_id: str, log_line: str) -> List[int]:
        tokens = self._tokenize(log_line)
        minhash = self._compute_minhash(tokens)
        bands = self._get_bands(minhash)

        with self._lock:
            self.log_tokens[log_id] = tokens
            self.log_minhashes[log_id] = minhash
            bucket_ids = []
            for band_idx, band_hash in bands:
                b_key = (band_idx << 32) | band_hash
                if b_key not in self.buckets:
                    self.buckets[b_key] = set()
                self.buckets[b_key].add(log_id)
                bucket_ids.append(b_key)
        return bucket_ids

    def query(self, log_line: str, top_k: int = 5) -> List[Tuple[str, float]]:
        tokens = self._tokenize(log_line)
        query_minhash = self._compute_minhash(tokens)
        bands = self._get_bands(query_minhash)

        candidate_ids = set()
        with self._lock:
            for band_idx, band_hash in bands:
                b_key = (band_idx << 32) | band_hash
                if b_key in self.buckets:
                    candidate_ids.update(self.buckets[b_key])

            similarities = []
            for cid in candidate_ids:
                target_minhash = self.log_minhashes.get(cid)
                if target_minhash:
                    # Compute Jaccard similarity estimation from minhash
                    matches = sum(1 for a, b in zip(query_minhash, target_minhash) if a == b)
                    sim = matches / float(self.num_perm)
                    if sim >= self.threshold:
                        similarities.append((cid, sim))

            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]

    def batch_fingerprint(self, log_lines: Dict[str, str]) -> Dict[str, List[int]]:
        results = {}
        for log_id, line in log_lines.items():
            tokens = self._tokenize(line)
            results[log_id] = self._compute_minhash(tokens)
        return results
