"""Unit tests for ANV middleware classification and enforcement."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport

from anv import ANVMiddleware, ANVPolicy, AuthorizationType, generate_token


def _build_app(policy: ANVPolicy) -> FastAPI:
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
        return {"authorization_type": request.state.anv.authorization_type.value}

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


@pytest.mark.asyncio
async def test_signed_ai_headers_parsed() -> None:
    app = _build_app(ANVPolicy.WARN)
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tools/call", headers=_signed_headers())
    assert response.status_code == 200
    assert response.json()["authorization_type"] == "SIGNED_AI"


@pytest.mark.asyncio
async def test_unsigned_no_headers() -> None:
    app = _build_app(ANVPolicy.WARN)
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tools/call")
    assert response.status_code == 200
    assert response.json()["authorization_type"] == "UNSIGNED"


@pytest.mark.asyncio
async def test_invalid_token_treated_as_unsigned() -> None:
    app = _build_app(ANVPolicy.WARN)
    headers = _signed_headers()
    headers["X-ANV-Token"] = "not-a-real-token"
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tools/call", headers=headers)
    assert response.status_code == 200
    assert response.json()["authorization_type"] == "UNSIGNED"


@pytest.mark.asyncio
async def test_warn_policy_accepts_unsigned() -> None:
    app = _build_app(ANVPolicy.WARN)
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tools/call")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_require_policy_rejects_unsigned() -> None:
    app = _build_app(ANVPolicy.REQUIRE)
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/tools/call")
    assert response.status_code == 403
    assert response.json()["error"] == "anv_attestation_required"
    assert app.state.stats["rejected"] == 1
