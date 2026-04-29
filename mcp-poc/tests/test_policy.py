"""Unit tests for policy behavior."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport

from anv import ANVMiddleware, ANVPolicy, AuthorizationType, generate_token


def _build_app(policy: ANVPolicy = ANVPolicy.WARN) -> FastAPI:
    app = FastAPI()
    app.state.stats = {
        AuthorizationType.SIGNED_AI.value: 0,
        AuthorizationType.SIGNED_HUMAN.value: 0,
        AuthorizationType.UNSIGNED.value: 0,
        "rejected": 0,
    }
    app.add_middleware(ANVMiddleware, policy=policy)

    @app.post("/tools/call")
    async def tools_call(request: Request) -> dict[str, str]:
        return {
            "authorization_type": request.state.anv.authorization_type.value,
            "policy": request.state.anv.policy.value,
        }

    return app


def _signed_headers() -> dict[str, str]:
    provider = "example-ai-provider.com"
    level = "AI_ATTESTED"
    return {
        "X-ANV-Authorization": "SIGNED_AI",
        "X-ANV-Provider": provider,
        "X-ANV-Attestation-Level": level,
        "X-ANV-Token": generate_token(provider=provider, auth_type="SIGNED_AI", level=level),
    }


def test_warn_is_default() -> None:
    assert ANVPolicy.WARN.value == "warn"


@pytest.mark.asyncio
async def test_require_rejects_unsigned() -> None:
    app = _build_app(ANVPolicy.REQUIRE)
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tools/call")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_warn_accepts_unsigned() -> None:
    app = _build_app(ANVPolicy.WARN)
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tools/call")
    assert response.status_code == 200
    assert response.json()["authorization_type"] == "UNSIGNED"


@pytest.mark.asyncio
async def test_signed_ai_accepted_in_both_modes() -> None:
    for policy in (ANVPolicy.WARN, ANVPolicy.REQUIRE):
        app = _build_app(policy)
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/tools/call", headers=_signed_headers())
        assert response.status_code == 200
        assert response.json()["authorization_type"] == "SIGNED_AI"
