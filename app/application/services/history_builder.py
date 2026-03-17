from app.domain.entities.message import ChatMessage


def build_prompt_history(
    history: list[ChatMessage],
    user_message: str,
    max_turns: int,
) -> list[ChatMessage]:
    max_messages = max_turns * 2
    recent = history[-max_messages:] if max_messages > 0 else []
    return [*recent, ChatMessage(role="user", content=user_message)]


def trim_history_for_storage(history: list[ChatMessage], max_turns: int) -> list[ChatMessage]:
    max_messages = max_turns * 2
    if max_messages <= 0:
        return []
    return history[-max_messages:]
