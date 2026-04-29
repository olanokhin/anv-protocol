"""ANV MCP tool server for validating authorization type before tool execution."""

from __future__ import annotations

import argparse
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from rich.console import Console

from anv import ANVContext, ANVMiddleware, ANVPolicy, AuthorizationType

console = Console()


def parse_bool_flag(value: str) -> bool:
    """Parse a CLI boolean flag from a human-readable string."""

    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


def create_mcp_app(
    policy: ANVPolicy = ANVPolicy.WARN,
    port: int = 8001,
    anv_enabled: bool = True,
) -> FastAPI:
    """Create the MCP server app for production or tests."""

    app = FastAPI(title="ANV MCP PoC Server")
    app.state.stats = {
        AuthorizationType.SIGNED_AI.value: 0,
        AuthorizationType.SIGNED_HUMAN.value: 0,
        AuthorizationType.UNSIGNED.value: 0,
        "rejected": 0,
    }
    app.state.anv_policy = policy
    app.state.anv_enabled = anv_enabled
    app.state.port = port

    if anv_enabled:
        app.add_middleware(ANVMiddleware, policy=policy)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "anv_policy": policy.value,
            "anv_enabled": anv_enabled,
            "port": port,
        }

    @app.get("/tools")
    async def list_tools() -> dict[str, Any]:
        return {
            "tools": [
                {
                    "name": "calculator",
                    "description": "Multiply two integers a and b",
                    "parameters": {"a": "int", "b": "int"},
                }
            ]
        }

    @app.post("/tools/call")
    async def call_tool(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        tool_name = payload.get("tool")
        params = payload.get("params")
        if tool_name != "calculator":
            raise HTTPException(status_code=400, detail="Unknown tool: calculator expected.")
        if not isinstance(params, dict):
            raise HTTPException(status_code=400, detail="params must be an object.")

        a = params.get("a")
        b = params.get("b")
        if not _is_int_value(a) or not _is_int_value(b):
            raise HTTPException(status_code=400, detail="calculator params a and b must be integers.")

        result = a * b
        ctx = getattr(request.state, "anv", None)
        if isinstance(ctx, ANVContext):
            app.state.stats[ctx.authorization_type.value] += 1
            response: dict[str, Any] = {"result": result, "anv_status": ctx.authorization_type.value}
            if ctx.authorization_type == AuthorizationType.UNSIGNED:
                response["anv_warning"] = "No ANV attestation present. Consider requiring ANV for this endpoint."
            elif ctx.provider:
                response["anv_provider"] = ctx.provider
        else:
            response = {"result": result, "anv_status": "ANV_DISABLED"}

        console.print(f"[MCP] + Tool: calculator({a}, {b}) -> {result}", style="green")
        return response

    @app.get("/anv/stats")
    async def anv_stats() -> dict[str, int]:
        return dict(app.state.stats)

    return app


def _is_int_value(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANV MCP Tool Server")
    parser.add_argument("--anv-policy", choices=[mode.value for mode in ANVPolicy], default=ANVPolicy.WARN.value)
    parser.add_argument("--anv-enabled", type=parse_bool_flag, default=True)
    parser.add_argument("--port", type=int, default=8001)
    return parser


def main() -> None:
    """CLI entrypoint for the MCP server."""

    args = _build_arg_parser().parse_args()
    app = create_mcp_app(
        policy=ANVPolicy(args.anv_policy),
        port=args.port,
        anv_enabled=args.anv_enabled,
    )
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
