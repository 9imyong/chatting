import redis.asyncio as redis

from app.domain.entities.message import ChatMessage
from app.domain.exceptions.errors import SessionStoreError
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
            raise SessionStoreError("failed to load session history") from exc

    async def append_messages(
        self,
        session_id: str,
        messages: list[ChatMessage],
        max_messages: int | None = None,
    ) -> None:
        key = self._key(session_id)
        encoded = [msg.model_dump_json() for msg in messages]
        if not encoded:
            return
        try:
            # RPUSH/LTRIM/EXPIRE 를 한 트랜잭션으로 묶는다. 나눠 보내면 중간에 끊겼을 때
            # TTL 없는 키가 남거나 트림이 누락된다.
            pipe = self._client.pipeline(transaction=True)
            pipe.rpush(key, *encoded)
            if max_messages is not None:
                if max_messages <= 0:
                    pipe.delete(key)
                else:
                    pipe.ltrim(key, -max_messages, -1)
            pipe.expire(key, self._ttl_sec)
            await pipe.execute()
        except Exception as exc:
            raise SessionStoreError("failed to append session history") from exc

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
            raise SessionStoreError("failed to set session history") from exc

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
