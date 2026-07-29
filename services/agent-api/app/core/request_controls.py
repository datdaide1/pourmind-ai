import asyncio
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import HTTPException
from app.core.config import settings

class ChatRequestControls:
    """Per-process guard; scaled deployments also need a gateway limiter."""

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._active: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, key: str):
        now = time.monotonic()
        async with self._lock:
            recent = self._requests[key]
            cutoff = now - settings.CHAT_RATE_LIMIT_WINDOW_SECONDS
            while recent and recent[0] <= cutoff:
                recent.popleft()
            if len(recent) >= settings.CHAT_RATE_LIMIT_REQUESTS:
                raise HTTPException(status_code=429, detail="Chat rate limit exceeded")
            if self._active[key] >= settings.CHAT_MAX_CONCURRENCY:
                raise HTTPException(status_code=429, detail="Too many concurrent chat requests")
            recent.append(now)
            self._active[key] += 1
        try:
            yield
        finally:
            async with self._lock:
                self._active[key] = max(0, self._active[key] - 1)

chat_request_controls = ChatRequestControls()
