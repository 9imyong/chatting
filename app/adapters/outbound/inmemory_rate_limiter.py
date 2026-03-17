from __future__ import annotations

import asyncio
import time

from app.ports.outbound.rate_limiter import RateLimitDecision, RateLimiterPort


class InMemoryRateLimiter(RateLimiterPort):
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._counters: dict[str, tuple[int, int]] = {}

    async def consume(self, tenant_id: str, route: str, limit: int, window_sec: int) -> RateLimitDecision:
        now = int(time.time())
        window_start = now - (now % window_sec)
        reset_at = window_start + window_sec
        key = f"{tenant_id}:{route}:{window_start}"

        async with self._lock:
            count, _ = self._counters.get(key, (0, reset_at))
            count += 1
            self._counters[key] = (count, reset_at)

        remaining = max(0, limit - count)
        return RateLimitDecision(
            allowed=count <= limit,
            limit=limit,
            remaining=remaining,
            reset_at_epoch_sec=reset_at,
        )

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._counters.clear()

