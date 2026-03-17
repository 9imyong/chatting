from app.domain.entities.message import ChatMessage
from app.ports.outbound.llm_client import LLMClientPort


class VLLMStubClient(LLMClientPort):
    async def generate(self, messages: list[ChatMessage]) -> str:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return f"stub-vllm-reply: {last_user}"

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None
