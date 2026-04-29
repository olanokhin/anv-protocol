"""Integration tests for the MCP server, demo agent, and ANV enforcement flow."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from agent import create_agent_app
from anv import ANVPolicy
from mcp_server import create_mcp_app


async def _run_case(policy: ANVPolicy, anv_enabled: bool) -> tuple[httpx.Response, object]:
    server_app = create_mcp_app(policy=policy, port=9001, anv_enabled=True)
    transport = ASGITransport(app=server_app)
    agent_app = create_agent_app(server_url="http://mcp-server", anv_enabled=anv_enabled, transport=transport)
    async with httpx.AsyncClient(transport=ASGITransport(app=agent_app), base_url="http://agent") as client:
        response = await client.post("/run", json={"task": "Calculate 42 * 7"})
    return response, server_app


@pytest.mark.asyncio
async def test_case_a_signed_ai_warn() -> None:
    response, _ = await _run_case(ANVPolicy.WARN, True)
    assert response.status_code == 200
    assert response.json()["result"] == 294
    assert response.json()["anv_status"] == "SIGNED_AI"


@pytest.mark.asyncio
async def test_case_b_signed_ai_require() -> None:
    response, _ = await _run_case(ANVPolicy.REQUIRE, True)
    assert response.status_code == 200
    assert response.json()["result"] == 294
    assert response.json()["anv_status"] == "SIGNED_AI"


@pytest.mark.asyncio
async def test_case_c_unsigned_warn() -> None:
    response, _ = await _run_case(ANVPolicy.WARN, False)
    assert response.status_code == 200
    assert response.json()["result"] == 294
    assert response.json()["anv_status"] == "UNSIGNED"
    assert "anv_warning" in response.json()


@pytest.mark.asyncio
async def test_case_d_unsigned_require() -> None:
    response, _ = await _run_case(ANVPolicy.REQUIRE, False)
    assert response.status_code == 403
    body = response.json()
    assert body["error"] == "anv_attestation_required"
    assert body["received"] == "UNSIGNED"
    assert "SIGNED_AI" in body["required"]
    assert "docs" in body


@pytest.mark.asyncio
async def test_anv_stats() -> None:
    server_app = create_mcp_app(policy=ANVPolicy.WARN, port=9001, anv_enabled=True)
    server_transport = ASGITransport(app=server_app)
    signed_agent = create_agent_app(server_url="http://mcp-server", anv_enabled=True, transport=server_transport)
    unsigned_agent = create_agent_app(server_url="http://mcp-server", anv_enabled=False, transport=server_transport)

    async with httpx.AsyncClient(transport=ASGITransport(app=signed_agent), base_url="http://signed") as client:
        await client.post("/run", json={"task": "Calculate 42 * 7"})

    async with httpx.AsyncClient(transport=ASGITransport(app=unsigned_agent), base_url="http://unsigned") as client:
        await client.post("/run", json={"task": "Calculate 42 * 7"})

    async with httpx.AsyncClient(transport=server_transport, base_url="http://mcp-server") as client:
        stats = await client.get("/anv/stats")

    assert stats.status_code == 200
    assert stats.json()["SIGNED_AI"] == 1
    assert stats.json()["UNSIGNED"] == 1
    assert stats.json()["rejected"] == 0
