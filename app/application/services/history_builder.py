from app.domain.entities.message import ChatMessage


def build_prompt_history(
    history: list[ChatMessage],
    user_message: str,
    max_turns: int,
) -> list[ChatMessage]:
    max_messages = max_turns * 2
    recent = history[-max_messages:] if max_messages > 0 else []
    return [*recent, ChatMessage(role="user", content=user_message)]
