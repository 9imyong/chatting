from __future__ import annotations

import time

import redis.asyncio as redis

from app.ports.outbound.rate_limiter import RateLimitDecision, RateLimiterPort


class RedisRateLimiter(RateLimiterPort):
    def __init__(self, redis_url: str, key_prefix: str = "rate-limit") -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix

    async def consume(self, tenant_id: str, route: str, limit: int, window_sec: int) -> RateLimitDecision:
        now = int(time.time())
        window_start = now - (now % window_sec)
        reset_at = window_start + window_sec
        key = f"{self._key_prefix}:{tenant_id}:{route}:{window_start}"

        value = await self._client.incr(key)
        if value == 1:
            await self._client.expire(key, window_sec)

        remaining = max(0, limit - int(value))
        return RateLimitDecision(
            allowed=int(value) <= limit,
            limit=limit,
            remaining=remaining,
            reset_at_epoch_sec=reset_at,
        )

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()

