from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass

from fastapi import Request

from app.api.deps.providers import get_container
from app.common.logging.logger import log_event
from app.common.metrics.metrics import observe_auth_result, observe_rate_limit
from app.domain.exceptions.errors import ForbiddenError, RateLimitExceededError, UnauthorizedError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TenantAccessContext:
    tenant_id: str
    authenticated: bool


def _parse_tenant_api_keys(raw: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in raw.split(","):
        part = item.strip()
        if not part or ":" not in part:
            continue
        tenant, token = part.split(":", 1)
        tenant = tenant.strip()
        token = token.strip()
        if tenant and token:
            mapping[tenant] = token
    return mapping


def _parse_tenant_overrides(raw: str) -> dict[str, int]:
    overrides: dict[str, int] = {}
    for item in raw.split(","):
        part = item.strip()
        if not part or ":" not in part:
            continue
        tenant, limit_text = part.split(":", 1)
        tenant = tenant.strip()
        limit_text = limit_text.strip()
        if not tenant:
            continue
        try:
            value = int(limit_text)
        except ValueError:
            continue
        if value > 0:
            overrides[tenant] = value
    return overrides


def auth_dependency(route_id: str):
    async def _dep(request: Request) -> TenantAccessContext:
        container = get_container(request)
        settings = container.settings
        token_to_validate = request.headers.get("authorization", "").strip()
        tenant = settings.AUTH_DEFAULT_TENANT
        authenticated = False

        if settings.AUTH_ENABLED:
            if not token_to_validate:
                observe_auth_result("missing")
                raise UnauthorizedError("missing authorization header")

            if not token_to_validate.lower().startswith("bearer "):
                observe_auth_result("invalid_scheme")
                raise UnauthorizedError("authorization header must use bearer scheme")

            bearer_token = token_to_validate.split(" ", 1)[1].strip()
            key_map = _parse_tenant_api_keys(settings.AUTH_TENANT_API_KEYS)
            matched = next(
                (
                    tenant_id
                    for tenant_id, expected_token in key_map.items()
                    if secrets.compare_digest(expected_token, bearer_token)
                ),
                None,
            )
            if matched is None:
                observe_auth_result("forbidden")
                raise ForbiddenError("invalid tenant api key")

            tenant = matched
            authenticated = True
            observe_auth_result("success")
        else:
            observe_auth_result("bypass")

        request.state.tenant_id = tenant

        if settings.RATE_LIMIT_ENABLED:
            overrides = _parse_tenant_overrides(settings.RATE_LIMIT_TENANT_OVERRIDES)
            limit = overrides.get(tenant, settings.RATE_LIMIT_REQUESTS_PER_WINDOW)

            try:
                decision = await container.rate_limiter.consume(
                    tenant_id=tenant,
                    route=route_id,
                    limit=limit,
                    window_sec=settings.RATE_LIMIT_WINDOW_SEC,
                )
            except Exception:
                if settings.RATE_LIMIT_FAIL_OPEN:
                    observe_rate_limit(tenant, "bypass_on_error")
                    log_event(
                        logger,
                        logging.WARNING,
                        "rate limit backend error, fail-open",
                        tenant_id=tenant,
                        path=request.url.path,
                        result="success",
                        status="bypass_on_error",
                    )
                    return TenantAccessContext(tenant_id=tenant, authenticated=authenticated)
                observe_rate_limit(tenant, "backend_error")
                raise RateLimitExceededError("rate limiter backend unavailable")

            request.state.rate_limit_limit = decision.limit
            request.state.rate_limit_remaining = decision.remaining
            request.state.rate_limit_reset = decision.reset_at_epoch_sec

            if not decision.allowed:
                observe_rate_limit(tenant, "rejected")
                log_event(
                    logger,
                    logging.WARNING,
                    "rate limit exceeded",
                    tenant_id=tenant,
                    path=request.url.path,
                    result="failure",
                    status="rate_limited",
                )
                raise RateLimitExceededError("tenant rate limit exceeded")

            observe_rate_limit(tenant, "allowed")
            log_event(
                logger,
                logging.INFO,
                "access granted with rate limit",
                tenant_id=tenant,
                path=request.url.path,
                result="success",
                status="ok",
            )

        return TenantAccessContext(tenant_id=tenant, authenticated=authenticated)

    return _dep
