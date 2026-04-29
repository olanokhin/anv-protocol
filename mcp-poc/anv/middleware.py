"""ANV FastAPI middleware for mock header validation and policy enforcement."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from rich.console import Console
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .policy import ANVPolicy, AuthorizationType
from .token import MockEATToken, validate_token

console = Console()


@dataclass
class ANVContext:
    """Per-request ANV classification result."""

    authorization_type: AuthorizationType
    provider: str | None
    attestation_level: str | None
    token: MockEATToken | None
    policy: ANVPolicy
    accepted: bool
    rejection_reason: str | None


class ANVMiddleware(BaseHTTPMiddleware):
    """Validate ANV headers for tool calls before the tool handler runs."""

    def __init__(self, app, policy: ANVPolicy = ANVPolicy.WARN):
        super().__init__(app)
        self.policy = policy

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "POST" and request.url.path == "/tools/call":
            ctx = self._parse_anv_headers(request)
            request.state.anv = ctx
            self._log(ctx)
            if not ctx.accepted:
                self._increment_rejected(request)
                return self._reject(ctx)
        return await call_next(request)

    def _parse_anv_headers(self, request: Request) -> ANVContext:
        auth_header = request.headers.get("x-anv-authorization")
        provider_header = request.headers.get("x-anv-provider")
        level_header = request.headers.get("x-anv-attestation-level")
        token_header = request.headers.get("x-anv-token")

        token = validate_token(token_header) if token_header else None
        authorization_type = AuthorizationType.UNSIGNED
        provider = provider_header
        attestation_level = level_header
        rejection_reason: str | None = None

        if auth_header:
            try:
                claimed_type = AuthorizationType(auth_header)
            except ValueError:
                claimed_type = AuthorizationType.UNSIGNED
                rejection_reason = "invalid_authorization_type"

            if claimed_type != AuthorizationType.UNSIGNED and token is not None:
                provider_matches = provider_header in (None, token.provider_cert)
                level_matches = level_header in (None, token.attestation_level)
                token_type_matches = token.authorization_type == claimed_type.value
                if provider_matches and level_matches and token_type_matches:
                    authorization_type = claimed_type
                    provider = token.provider_cert
                    attestation_level = token.attestation_level
                else:
                    rejection_reason = "header_token_mismatch"
            elif claimed_type != AuthorizationType.UNSIGNED and token is None:
                rejection_reason = "invalid_or_missing_token"

        accepted = authorization_type != AuthorizationType.UNSIGNED or self.policy == ANVPolicy.WARN
        if not accepted and rejection_reason is None:
            rejection_reason = "anv_attestation_required"

        return ANVContext(
            authorization_type=authorization_type,
            provider=provider,
            attestation_level=attestation_level,
            token=token if authorization_type != AuthorizationType.UNSIGNED else None,
            policy=self.policy,
            accepted=accepted,
            rejection_reason=rejection_reason,
        )

    def _log(self, ctx: ANVContext) -> None:
        if not ctx.accepted:
            style = "bold red"
            icon = "x"
            outcome = "rejected"
        elif ctx.authorization_type == AuthorizationType.UNSIGNED:
            style = "yellow"
            icon = "!"
            outcome = "accepted with warning"
        else:
            style = "green"
            icon = "+"
            outcome = "accepted"

        provider = ctx.provider or "-"
        console.print(
            f"[ANV] {icon} Type: {ctx.authorization_type.value} | "
            f"Provider: {provider} | Policy: {ctx.policy.value} -> {outcome}",
            style=style,
        )

    def _reject(self, ctx: ANVContext) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={
                "error": "anv_attestation_required",
                "message": "This endpoint requires ANV attestation.",
                "received": ctx.authorization_type.value,
                "required": [
                    AuthorizationType.SIGNED_AI.value,
                    AuthorizationType.SIGNED_HUMAN.value,
                ],
                "hint": "Attach X-ANV-* headers to your request.",
                "docs": "https://github.com/olanokhin/anv-protocol",
            },
        )

    @staticmethod
    def _increment_rejected(request: Request) -> None:
        stats = getattr(request.app.state, "stats", None)
        if isinstance(stats, dict):
            stats["rejected"] = stats.get("rejected", 0) + 1
