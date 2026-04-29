"""Thin FastAPI demo agent that forwards a parsed task to the MCP server."""

from __future__ import annotations

import argparse
import re
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from rich.console import Console
from starlette.responses import JSONResponse

from anv import generate_token

console = Console()
TASK_PATTERN = re.compile(r"Calculate\s+(-?\d+)\s*\*\s*(-?\d+)", re.IGNORECASE)


def parse_bool_flag(value: str) -> bool:
    """Parse a CLI boolean flag from a human-readable string."""

    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


def create_agent_app(
    server_url: str = "http://localhost:8001",
    anv_enabled: bool = True,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Create the demo agent app for production or tests."""

    app = FastAPI(title="ANV PoC Agent")
    app.state.server_url = server_url.rstrip("/")
    app.state.anv_enabled = anv_enabled
    app.state.transport = transport

    @app.post("/run")
    async def run_task(payload: dict[str, Any]) -> Any:
        task = payload.get("task")
        if not isinstance(task, str):
            raise HTTPException(status_code=400, detail="task must be a string.")

        parsed = _parse_task(task)
        if parsed is None:
            raise HTTPException(status_code=400, detail="Only 'Calculate <int> * <int>' is supported.")
        a, b = parsed

        headers = _build_headers(app.state.anv_enabled)
        console.print(f"[AGENT] -> Calling MCP server: {app.state.server_url}", style="cyan")
        async with httpx.AsyncClient(
            base_url=app.state.server_url,
            transport=app.state.transport,
            timeout=10.0,
        ) as client:
            response = await client.post("/tools/call", json={"tool": "calculator", "params": {"a": a, "b": b}}, headers=headers)

        body = response.json()
        if response.status_code == 200:
            console.print(
                f"[AGENT] + Result: {body.get('result')} | ANV: {body.get('anv_status')}",
                style="green",
            )
        else:
            console.print(
                f"[AGENT] x Rejected: {response.status_code} {body.get('error', 'request_failed')}",
                style="bold red",
            )
        return JSONResponse(status_code=response.status_code, content=body)

    return app


def _parse_task(task: str) -> tuple[int, int] | None:
    match = TASK_PATTERN.fullmatch(task.strip())
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _build_headers(anv_enabled: bool) -> dict[str, str]:
    if not anv_enabled:
        return {}

    provider = "example-ai-provider.com"
    level = "AI_ATTESTED"
    token = generate_token(provider=provider, auth_type="SIGNED_AI", level=level)
    return {
        "X-ANV-Authorization": "SIGNED_AI",
        "X-ANV-Provider": provider,
        "X-ANV-Attestation-Level": level,
        "X-ANV-Token": token,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANV PoC Agent")
    parser.add_argument("--anv", type=parse_bool_flag, default=True)
    parser.add_argument("--server", default="http://localhost:8001")
    parser.add_argument("--port", type=int, default=8003)
    return parser


def main() -> None:
    """CLI entrypoint for the demo agent service."""

    args = _build_arg_parser().parse_args()
    app = create_agent_app(server_url=args.server, anv_enabled=args.anv)
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
