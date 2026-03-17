class DomainError(Exception):
    def __init__(self, message: str, error_code: str = "DOMAIN_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class InfraError(DomainError):
    def __init__(self, message: str, error_code: str = "INFRA_ERROR") -> None:
        super().__init__(message, error_code=error_code)


class ExternalServiceError(InfraError):
    def __init__(self, message: str, error_code: str = "EXTERNAL_SERVICE_ERROR") -> None:
        super().__init__(message, error_code=error_code)


class ValidationError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="INVALID_ARGUMENT")


class LLMTimeoutError(ExternalServiceError):
    def __init__(self, message: str = "llm request timed out") -> None:
        super().__init__(message, error_code="LLM_TIMEOUT")


class LLMBadResponseError(ExternalServiceError):
    def __init__(self, message: str = "llm bad response") -> None:
        super().__init__(message, error_code="LLM_BAD_RESPONSE")


class TTSTimeoutError(ExternalServiceError):
    def __init__(self, message: str = "tts request timed out") -> None:
        super().__init__(message, error_code="TTS_TIMEOUT")


class TTSBadResponseError(ExternalServiceError):
    def __init__(self, message: str = "tts bad response") -> None:
        super().__init__(message, error_code="TTS_BAD_RESPONSE")


class SessionStoreError(InfraError):
    def __init__(self, message: str = "session store failure") -> None:
        super().__init__(message, error_code="SESSION_STORE_ERROR")


class UnauthorizedError(DomainError):
    def __init__(self, message: str = "authentication required") -> None:
        super().__init__(message, error_code="UNAUTHORIZED")


class ForbiddenError(DomainError):
    def __init__(self, message: str = "access forbidden") -> None:
        super().__init__(message, error_code="FORBIDDEN")


class RateLimitExceededError(DomainError):
    def __init__(self, message: str = "rate limit exceeded") -> None:
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED")
