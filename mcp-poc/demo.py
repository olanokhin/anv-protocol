"""One-command ANV PoC demo runner for terminal and README GIF capture."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import httpx

from anv import generate_token

SCRIPT_DIR = Path(__file__).resolve().parent
TASK_BODY = {"task": "Calculate 42 * 7"}
TOOL_BODY = {"tool": "calculator", "params": {"a": 42, "b": 7}}


@dataclass(frozen=True)
class CaseSpec:
    """Definition of a single demo case."""

    key: str
    title: str
    request_url: str
    expected_status: int
    expectation: str
    request_body: dict[str, Any]
    headers: dict[str, str] | None = None
    exact_fields: tuple[tuple[str, Any], ...] = ()
    contains_fields: tuple[tuple[str, str], ...] = ()
    list_contains: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True)
class CaseResult:
    """Execution result for one demo case."""

    spec: CaseSpec
    ok: bool
    status_code: int
    body: dict[str, Any]
    details: tuple[str, ...]


def build_signed_headers() -> dict[str, str]:
    """Create signed ANV headers for direct MCP calls."""

    provider = "example-ai-provider.com"
    level = "AI_ATTESTED"
    return {
        "X-ANV-Authorization": "SIGNED_AI",
        "X-ANV-Provider": provider,
        "X-ANV-Attestation-Level": level,
        "X-ANV-Token": generate_token(provider=provider, auth_type="SIGNED_AI", level=level),
    }


def build_case_specs() -> list[CaseSpec]:
    """Create the four canonical demo cases."""

    return [
        CaseSpec(
            key="A",
            title="SIGNED_AI + warn",
            request_url="http://127.0.0.1:8003/run",
            expected_status=200,
            expectation="HTTP 200, result=294, anv_status=SIGNED_AI",
            request_body=TASK_BODY,
            exact_fields=(("result", 294), ("anv_status", "SIGNED_AI")),
        ),
        CaseSpec(
            key="B",
            title="SIGNED_AI + require",
            request_url="http://127.0.0.1:8002/tools/call",
            expected_status=200,
            expectation="HTTP 200, result=294, anv_status=SIGNED_AI",
            request_body=TOOL_BODY,
            headers=build_signed_headers(),
            exact_fields=(("result", 294), ("anv_status", "SIGNED_AI")),
        ),
        CaseSpec(
            key="C",
            title="UNSIGNED + warn",
            request_url="http://127.0.0.1:8001/tools/call",
            expected_status=200,
            expectation="HTTP 200, result=294, anv_status=UNSIGNED, warning present",
            request_body=TOOL_BODY,
            exact_fields=(("result", 294), ("anv_status", "UNSIGNED")),
            contains_fields=(("anv_warning", "No ANV attestation present."),),
        ),
        CaseSpec(
            key="D",
            title="UNSIGNED + require",
            request_url="http://127.0.0.1:8004/run",
            expected_status=403,
            expectation="HTTP 403, anv_attestation_required, received=UNSIGNED",
            request_body=TASK_BODY,
            exact_fields=(("error", "anv_attestation_required"), ("received", "UNSIGNED")),
            list_contains=(("required", "SIGNED_AI"), ("required", "SIGNED_HUMAN")),
        ),
    ]


def summarize_body(body: dict[str, Any], record_mode: bool = False) -> str:
    """Create a compact human-readable summary for demo output."""

    parts: list[str] = []
    keys = ("result", "anv_status", "error", "received")
    if not record_mode:
        keys = ("result", "anv_status", "anv_provider", "error", "received")
    for key in keys:
        if key in body:
            parts.append(f"{key}={body[key]}")
    if "anv_warning" in body:
        parts.append("anv_warning=present")
    if "required" in body and isinstance(body["required"], list):
        parts.append(f"required={','.join(str(item) for item in body['required'])}")
    if not parts:
        return json.dumps(body, sort_keys=True)
    return ", ".join(parts)


def evaluate_case(spec: CaseSpec, status_code: int, body: dict[str, Any]) -> CaseResult:
    """Evaluate a live response against the expected demo case."""

    details: list[str] = []
    if status_code != spec.expected_status:
        details.append(f"expected HTTP {spec.expected_status}, got HTTP {status_code}")

    for key, expected in spec.exact_fields:
        if body.get(key) != expected:
            details.append(f"expected {key}={expected!r}, got {body.get(key)!r}")

    for key, fragment in spec.contains_fields:
        value = body.get(key)
        if not isinstance(value, str) or fragment not in value:
            details.append(f"expected {key} to contain {fragment!r}")

    for key, expected_item in spec.list_contains:
        value = body.get(key)
        if not isinstance(value, list) or expected_item not in value:
            details.append(f"expected {key} to contain {expected_item!r}")

    return CaseResult(spec=spec, ok=not details, status_code=status_code, body=body, details=tuple(details))


def pause(seconds: float) -> None:
    """Sleep only when a positive delay is requested."""

    if seconds > 0:
        time.sleep(seconds)


def print_banner(record_mode: bool) -> None:
    """Print the opening banner."""

    print("ANV PoC Stage 1 Demo")
    print("Signed vs unsigned behavior before tool execution")
    if record_mode:
        print("Record mode enabled")
    print()


def print_case_result(result: CaseResult, record_mode: bool) -> None:
    """Render one case result for either regular or GIF-friendly output."""

    if record_mode:
        print(f"Case {result.spec.key}  {result.spec.title}")
        print(f"Expect: {result.spec.expectation}")
        print(f"Actual: HTTP {result.status_code}, {summarize_body(result.body, record_mode=True)}")
        print("PASS" if result.ok else "FAIL")
        if result.details:
            for detail in result.details:
                print(f"Detail: {detail}")
        print()
        return

    status = "PASS" if result.ok else "FAIL"
    print(
        f"[{status}] Case {result.spec.key} {result.spec.title}: "
        f"HTTP {result.status_code}, {summarize_body(result.body)}"
    )
    for detail in result.details:
        print(f"  - {detail}")


def print_summary(results: Iterable[CaseResult], record_mode: bool = False) -> None:
    """Print the final pass/fail summary."""

    print("Summary")
    all_ok = True
    for result in results:
        outcome = "PASS" if result.ok else "FAIL"
        print(f"{result.spec.key} {outcome}")
        all_ok &= result.ok
    if record_mode:
        return

    print()
    print("PoC ready for demo" if all_ok else "PoC needs fixes before demo")


def run_compose(compose_args: list[str], capture_output: bool = True) -> None:
    """Run docker compose from the PoC directory."""

    command = ["docker", "compose", *compose_args]
    completed = subprocess.run(
        command,
        cwd=SCRIPT_DIR,
        capture_output=capture_output,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return

    if completed.stdout:
        print(completed.stdout)
    if completed.stderr:
        print(completed.stderr, file=sys.stderr)
    raise RuntimeError(f"docker compose {' '.join(compose_args)} failed with exit code {completed.returncode}")


def wait_for_http(url: str, startup_timeout: float) -> None:
    """Wait until an HTTP endpoint responds with status 200."""

    deadline = time.time() + startup_timeout
    last_error = "service did not become reachable"
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code == 200:
                return
            last_error = f"unexpected status {response.status_code}"
        except httpx.HTTPError as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def wait_for_stack(startup_timeout: float) -> None:
    """Wait until the compose demo stack is ready for requests."""

    wait_for_http("http://127.0.0.1:8001/health", startup_timeout)
    wait_for_http("http://127.0.0.1:8002/health", startup_timeout)
    wait_for_http("http://127.0.0.1:8003/openapi.json", startup_timeout)
    wait_for_http("http://127.0.0.1:8004/openapi.json", startup_timeout)


def execute_case(client: httpx.Client, spec: CaseSpec) -> CaseResult:
    """Execute one case against the live demo stack."""

    response = client.post(spec.request_url, json=spec.request_body, headers=spec.headers, timeout=10.0)
    body = response.json()
    return evaluate_case(spec, response.status_code, body)


def maybe_print_stats(client: httpx.Client) -> None:
    """Print final ANV stats from both servers."""

    warn_stats = client.get("http://127.0.0.1:8001/anv/stats", timeout=10.0).json()
    require_stats = client.get("http://127.0.0.1:8002/anv/stats", timeout=10.0).json()
    print()
    print("ANV stats")
    print(f"warn    {json.dumps(warn_stats, sort_keys=True)}")
    print(f"require {json.dumps(require_stats, sort_keys=True)}")


def build_up_args(no_build: bool) -> list[str]:
    """Build the compose command for a fresh deterministic stack."""

    args = ["up", "-d", "--force-recreate"]
    if not no_build:
        args.insert(1, "--build")
    return args


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description="Run the ANV PoC A-D demo cases.")
    parser.add_argument("--record", action="store_true", help="Use GIF-friendly output and pacing.")
    parser.add_argument("--stats", action="store_true", help="Print final /anv/stats responses.")
    parser.add_argument("--keep-up", action="store_true", help="Leave the Docker Compose stack running at the end.")
    parser.add_argument("--no-build", action="store_true", help="Skip docker compose image rebuild before running.")
    parser.add_argument("--startup-timeout", type=float, default=30.0, help="Seconds to wait for services to become ready.")
    parser.add_argument("--pause-seconds", type=float, default=None, help="Pause between cases; defaults to 0.8 in record mode.")
    return parser


def main() -> int:
    """CLI entrypoint for the demo runner."""

    args = build_arg_parser().parse_args()
    pause_seconds = args.pause_seconds if args.pause_seconds is not None else (0.8 if args.record else 0.0)
    stack_started = False
    print_banner(args.record)

    try:
        print("Starting Docker Compose stack...")
        run_compose(build_up_args(args.no_build))
        stack_started = True
        wait_for_stack(args.startup_timeout)
        print("Stack is ready.")
        print()

        results: list[CaseResult] = []
        with httpx.Client() as client:
            for spec in build_case_specs():
                result = execute_case(client, spec)
                results.append(result)
                print_case_result(result, args.record)
                pause(pause_seconds)

            if args.stats:
                maybe_print_stats(client)
                if args.record:
                    print()

        print_summary(results, record_mode=args.record)
        return 0 if all(result.ok for result in results) else 1
    finally:
        if args.keep_up:
            if not args.record:
                print()
                print("Compose stack left running (--keep-up).")
        elif stack_started:
            if not args.record:
                print()
                print("Stopping Docker Compose stack...")
            run_compose(["down"])


if __name__ == "__main__":
    raise SystemExit(main())
