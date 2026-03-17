class DomainError(Exception):
    error_code = "DOMAIN_ERROR"


class ExternalServiceError(DomainError):
    error_code = "EXTERNAL_SERVICE_ERROR"


class ValidationError(DomainError):
    error_code = "INVALID_ARGUMENT"


class SessionRepositoryError(DomainError):
    error_code = "SESSION_REPOSITORY_ERROR"
