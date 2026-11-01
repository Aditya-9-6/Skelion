import re
from typing import Any, Tuple

class PriorityQueue:
    def __init__(self):
        self._queue = []

    def push(self, item: Any, priority: int = 0) -> None:
        self._queue.append((priority, item))
        self._queue.sort(key=lambda x: x[0])

    def pop(self) -> Any:
        if not self._queue:
            return None
        return self._queue.pop(0)[1]

    def clean_text(self, text: str) -> str:
        p_clean = re.sub(r'[\?\!\.\,\s]+$', '', text.lower()).strip()
        return p_clean
