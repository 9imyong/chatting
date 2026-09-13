from __future__ import annotations

import time

import redis.asyncio as redis

from app.ports.outbound.rate_limiter import RateLimitDecision, RateLimiterPort


# INCR 과 EXPIRE 를 따로 보내면 그 사이에 연결이 끊겼을 때 TTL 없는 키가 영구히 남는다.
# 두 명령을 한 스크립트로 묶어 원자적으로 실행한다.
_CONSUME_SCRIPT = """
local value = redis.call('INCR', KEYS[1])
if value == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return value
"""


class RedisRateLimiter(RateLimiterPort):
    def __init__(self, redis_url: str, key_prefix: str = "rate-limit") -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix
        self._consume = self._client.register_script(_CONSUME_SCRIPT)

    async def consume(self, tenant_id: str, route: str, limit: int, window_sec: int) -> RateLimitDecision:
        now = int(time.time())
        window_start = now - (now % window_sec)
        reset_at = window_start + window_sec
        key = f"{self._key_prefix}:{tenant_id}:{route}:{window_start}"

        value = await self._consume(keys=[key], args=[window_sec])

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

