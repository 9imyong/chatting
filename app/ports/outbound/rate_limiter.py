from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_at_epoch_sec: int


class RateLimiterPort(Protocol):
    async def consume(self, tenant_id: str, route: str, limit: int, window_sec: int) -> RateLimitDecision:
        ...

    async def ping(self) -> bool:
        ...

    async def close(self) -> None:
        ...

