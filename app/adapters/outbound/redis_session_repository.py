import redis.asyncio as redis

from app.domain.entities.message import ChatMessage
from app.domain.exceptions.errors import SessionRepositoryError
from app.ports.outbound.session_repository import SessionRepositoryPort


class RedisSessionRepository(SessionRepositoryPort):
    def __init__(self, redis_url: str, ttl_sec: int) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._ttl_sec = ttl_sec

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        key = self._key(session_id)
        try:
            values = await self._client.lrange(key, 0, -1)
            return [ChatMessage.model_validate_json(item) for item in values]
        except Exception as exc:
            raise SessionRepositoryError("failed to load session history") from exc

    async def append_messages(self, session_id: str, messages: list[ChatMessage]) -> None:
        key = self._key(session_id)
        try:
            encoded = [msg.model_dump_json() for msg in messages]
            if encoded:
                await self._client.rpush(key, *encoded)
                await self._client.expire(key, self._ttl_sec)
        except Exception as exc:
            raise SessionRepositoryError("failed to append session history") from exc

    async def set_history(self, session_id: str, messages: list[ChatMessage]) -> None:
        key = self._key(session_id)
        try:
            encoded = [msg.model_dump_json() for msg in messages]
            pipe = self._client.pipeline()
            pipe.delete(key)
            if encoded:
                pipe.rpush(key, *encoded)
                pipe.expire(key, self._ttl_sec)
            await pipe.execute()
        except Exception as exc:
            raise SessionRepositoryError("failed to set session history") from exc

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _key(session_id: str) -> str:
        return f"chat:session:{session_id}"
