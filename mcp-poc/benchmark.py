"""Benchmark ANV overhead against a true baseline server and a warn-mode server."""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from typing import Sequence

import httpx
from rich.console import Console
from rich.table import Table

from anv import generate_token

console = Console()


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


async def _measure_mode(
    client: httpx.AsyncClient,
    requests_count: int,
    headers: dict[str, str] | None = None,
) -> list[float]:
    timings: list[float] = []
    payload = {"tool": "calculator", "params": {"a": 42, "b": 7}}
    for _ in range(requests_count):
        started = time.perf_counter()
        response = await client.post("/tools/call", json=payload, headers=headers)
        response.raise_for_status()
        timings.append((time.perf_counter() - started) * 1000)
    return timings


def _build_signed_headers() -> dict[str, str]:
    provider = "example-ai-provider.com"
    level = "AI_ATTESTED"
    return {
        "X-ANV-Authorization": "SIGNED_AI",
        "X-ANV-Provider": provider,
        "X-ANV-Attestation-Level": level,
        "X-ANV-Token": generate_token(provider=provider, auth_type="SIGNED_AI", level=level),
    }


async def run_benchmark(server: str, baseline_server: str, requests_count: int) -> None:
    """Measure baseline, signed, and unsigned request latencies."""

    async with httpx.AsyncClient(base_url=baseline_server.rstrip("/"), timeout=10.0) as baseline_client:
        baseline = await _measure_mode(baseline_client, requests_count)

    signed_headers = _build_signed_headers()
    async with httpx.AsyncClient(base_url=server.rstrip("/"), timeout=10.0) as warn_client:
        signed = await _measure_mode(warn_client, requests_count, headers=signed_headers)
        unsigned = await _measure_mode(warn_client, requests_count)

    _render_results(baseline, signed, unsigned, server, baseline_server)


def _render_results(
    baseline: Sequence[float],
    signed: Sequence[float],
    unsigned: Sequence[float],
    server: str,
    baseline_server: str,
) -> None:
    table = Table(title="ANV PoC Benchmark")
    table.add_column("Mode")
    table.add_column("Median")
    table.add_column("p95")
    table.add_column("p99")

    def metrics(values: Sequence[float]) -> tuple[str, str, str]:
        return (
            f"{statistics.median(values):.2f}ms",
            f"{_percentile(values, 0.95):.2f}ms",
            f"{_percentile(values, 0.99):.2f}ms",
        )

    baseline_metrics = metrics(baseline)
    signed_metrics = metrics(signed)
    unsigned_metrics = metrics(unsigned)
    overhead = statistics.median(signed) - statistics.median(baseline)

    table.add_row("Baseline", *baseline_metrics)
    table.add_row("SIGNED_AI", *signed_metrics)
    table.add_row("UNSIGNED (warn)", *unsigned_metrics)
    table.add_row("ANV overhead", f"{overhead:.2f}ms", "", "")

    console.print(table)
    if server.rstrip("/") == baseline_server.rstrip("/"):
        console.print(
            "[yellow]Baseline server matches ANV server. Use --baseline-server with an --anv-enabled=false instance for a true baseline.[/yellow]"
        )
    console.print(
        "Note: overhead reflects mock HTTP header parsing and HMAC validation, not production TLS extension latency."
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANV PoC Benchmark")
    parser.add_argument("--server", default="http://localhost:8001")
    parser.add_argument("--baseline-server", default="http://localhost:8000")
    parser.add_argument("--n", type=int, default=100)
    return parser


def main() -> None:
    """CLI entrypoint for the benchmark script."""

    args = _build_arg_parser().parse_args()
    asyncio.run(run_benchmark(args.server, args.baseline_server, args.n))


if __name__ == "__main__":
    main()
