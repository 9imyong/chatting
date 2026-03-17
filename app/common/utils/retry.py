import asyncio
import random
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


async def run_with_retry(
    operation: Callable[[], Awaitable[T]],
    retry_count: int,
    base_delay_sec: float,
    max_delay_sec: float,
    jitter_sec: float,
    retry_exceptions: tuple[type[Exception], ...],
) -> T:
    for attempt in range(retry_count + 1):
        try:
            return await operation()
        except retry_exceptions:
            if attempt >= retry_count:
                raise
            delay = min(max_delay_sec, base_delay_sec * (2**attempt))
            jitter = random.uniform(0.0, jitter_sec)
            await asyncio.sleep(delay + jitter)
