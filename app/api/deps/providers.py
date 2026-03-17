from fastapi import Request

from app.application.services.chat_orchestration_service import ChatOrchestrationService
from app.bootstrap import AppContainer


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_chat_service(request: Request) -> ChatOrchestrationService:
    return get_container(request).chat_service
