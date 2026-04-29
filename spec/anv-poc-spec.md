# ANV Protocol — PoC Stage 1: MCP Demo
## Status: Implementation ready | April 2026

---

## Objective

Demonstrate that ANV authorization type is visible to an MCP server
before any tool call is processed. Show that policy enforcement
(warn vs require) works correctly for both SIGNED_AI and UNSIGNED
agents. Measure latency overhead.

Single proof statement:

> An MCP server can cryptographically identify the authorization
> type of the calling agent before executing any tool — and enforce
> policy accordingly — with approximately zero latency overhead.

---

## Architecture

```
┌─────────────────────────────┐
│        AI Agent             │
│     agent.py (FastAPI)      │
│                             │
│  Task: "Calculate 42 * 7"  │
│                             │
│  Mode A: with ANV headers   │
│  Mode B: without ANV        │
└──────────┬──────────────────┘
           │ HTTP POST /tools/call
           │ X-ANV-Authorization: SIGNED_AI
           │ X-ANV-Provider: example-ai-provider.com
           │ X-ANV-Token: <mock EAT token>
           ▼
┌─────────────────────────────┐
│      MCP Tool Server        │
│    mcp_server.py (FastAPI)  │
│                             │
│  ANV Middleware             │
│  ├── reads ANV headers      │
│  ├── validates mock token   │
│  └── applies policy         │
│                             │
│  --anv-policy=warn          │
│  --anv-policy=require       │
│                             │
│  Tool: calculator           │
│  Input:  {"a": 42, "b": 7} │
│  Output: {"result": 294}    │
└─────────────────────────────┘
```

---

## Components

### Server: mcp_server.py

FastAPI server exposing one MCP tool: `calculator`.

Startup flags:
```bash
python mcp_server.py --anv-policy=warn     # default
python mcp_server.py --anv-policy=require  # strict
```

Endpoints:
```
GET  /health              server status + current policy
GET  /tools               list available tools
POST /tools/call          execute tool call (ANV enforced here)
GET  /anv/stats           session statistics by authorization type
```

ANV Middleware runs on every POST /tools/call:
1. Read X-ANV-* headers
2. Validate mock EAT token signature
3. Determine authorization type: SIGNED_AI | SIGNED_HUMAN | UNSIGNED
4. Apply policy
5. Log result
6. Pass to tool handler or reject

---

### Agent: agent.py

FastAPI server simulating an AI agent. Receives a task via HTTP,
calls the MCP tool server, returns the result.

Startup flags:
```bash
python agent.py --anv=true    # sends ANV headers (SIGNED_AI)
python agent.py --anv=false   # sends no ANV headers (UNSIGNED)
```

Endpoints:
```
POST /run    {"task": "Calculate 42 * 7"}
             → calls MCP server
             → returns result or error
```

---

### ANV Module: anv/

```
anv/
  __init__.py
  token.py        Mock EAT token generation and validation
  middleware.py   FastAPI middleware — ANV header parsing + policy
  policy.py       Policy definitions: warn | require
```

**token.py** — mock EAT token (not production crypto):
```python
@dataclass
class MockEATToken:
    provider_cert: str      # "example-ai-provider.com"
    session_id: str         # uuid4
    authorization_type: str # "SIGNED_AI"
    attestation_level: str  # "AI_ATTESTED"
    timestamp: int          # unix timestamp
    signature: str          # mock HMAC-SHA256

def generate_token(provider: str) -> MockEATToken: ...
def validate_token(token_str: str) -> MockEATToken | None: ...
```

**middleware.py** — FastAPI middleware:
```python
class ANVMiddleware(BaseHTTPMiddleware):
    """
    Reads X-ANV-* headers on every request.
    Validates mock EAT token.
    Attaches ANVContext to request.state.
    Applies policy: warn or require.
    """
```

**policy.py** — policy definitions:
```python
class ANVPolicy(Enum):
    WARN    = "warn"     # accept UNSIGNED with warning
    REQUIRE = "require"  # reject UNSIGNED with 403
```

---

## Four Test Cases

### Case A — SIGNED_AI + policy=warn

```
Agent:   --anv=true
Server:  --anv-policy=warn

Request headers:
  X-ANV-Authorization: SIGNED_AI
  X-ANV-Provider: example-ai-provider.com
  X-ANV-Attestation-Level: AI_ATTESTED
  X-ANV-Token: <valid mock token>

Server log:
  [ANV] ✓ Type     : SIGNED_AI
  [ANV] ✓ Provider : example-ai-provider.com
  [ANV] ✓ Level    : AI_ATTESTED (mock)
  [ANV] ✓ Policy   : WARN → accepted
  [MCP] ✓ Tool     : calculator(42, 7) → 294

Response: HTTP 200
  {"result": 294, "anv_status": "SIGNED_AI"}
```

---

### Case B — SIGNED_AI + policy=require

```
Agent:   --anv=true
Server:  --anv-policy=require

Same as Case A.
SIGNED_AI satisfies REQUIRE policy.

Response: HTTP 200
  {"result": 294, "anv_status": "SIGNED_AI"}
```

---

### Case C — UNSIGNED + policy=warn

```
Agent:   --anv=false
Server:  --anv-policy=warn

Request headers: (no ANV headers)

Server log:
  [ANV] ⚠ Type   : UNSIGNED
  [ANV] ⚠ Policy : WARN → accepted with warning
  [MCP] ✓ Tool   : calculator(42, 7) → 294

Response: HTTP 200
  {
    "result": 294,
    "anv_status": "UNSIGNED",
    "anv_warning": "No ANV attestation present. \
                    Consider requiring ANV for this endpoint."
  }
```

---

### Case D — UNSIGNED + policy=require

```
Agent:   --anv=false
Server:  --anv-policy=require

Request headers: (no ANV headers)

Server log:
  [ANV] ✗ Type   : UNSIGNED
  [ANV] ✗ Policy : REQUIRE → rejected

Response: HTTP 403
  {
    "error": "anv_attestation_required",
    "message": "This endpoint requires ANV attestation.",
    "received": "UNSIGNED",
    "required": ["SIGNED_AI", "SIGNED_HUMAN"],
    "hint": "Attach X-ANV-* headers to your request.",
    "docs": "https://github.com/olanokhin/anv-protocol"
  }

Agent log:
  [AGENT] ✗ Tool call rejected: 403 anv_attestation_required
  [AGENT] ✗ Task failed: ANV attestation required by server
```

---

## Benchmark: benchmark.py

100 requests each mode. Measure ANV middleware overhead.

```
python benchmark.py --server=http://localhost:8001

Running benchmark...
  Mode: SIGNED_AI (100 requests)
  Mode: UNSIGNED  (100 requests)
  Mode: baseline  (100 requests, ANV disabled)

Results:
┌─────────────────┬────────┬────────┬────────┐
│ Mode            │ Median │ p95    │ p99    │
├─────────────────┼────────┼────────┼────────┤
│ Baseline        │ 1.2ms  │ 1.8ms  │ 2.1ms  │
│ SIGNED_AI       │ 3.3ms  │ 4.1ms  │ 5.4ms  │
│ UNSIGNED (warn) │ 1.4ms  │ 2.0ms  │ 2.3ms  │
├─────────────────┼────────┼────────┼────────┤
│ ANV overhead    │ ~2.1ms │ ~2.3ms │ ~3.3ms │
└─────────────────┴────────┴────────┴────────┘

ANV overhead: ~2ms median (mock token validation)
Production estimate: <1ms (hardware AES-NI)
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/olanokhin/anv-protocol
cd anv-protocol/mcp-poc

# Install
pip install fastapi uvicorn httpx pytest

# Terminal 1 — MCP Server (warn mode)
python mcp_server.py --anv-policy=warn --port=8001

# Terminal 2 — Agent with ANV
python agent.py --anv=true --server=http://localhost:8001

# Terminal 3 — Agent without ANV
python agent.py --anv=false --server=http://localhost:8001

# Terminal 4 — Switch server to require mode
python mcp_server.py --anv-policy=require --port=8001

# Run benchmark
python benchmark.py --server=http://localhost:8001
```

---

## Docker Compose (optional)

```yaml
version: "3.9"
services:
  mcp-server-warn:
    build: .
    command: python mcp_server.py --anv-policy=warn --port=8001
    ports: ["8001:8001"]

  mcp-server-require:
    build: .
    command: python mcp_server.py --anv-policy=require --port=8002
    ports: ["8002:8002"]

  agent-signed:
    build: .
    command: python agent.py --anv=true --server=http://mcp-server-warn:8001
    depends_on: [mcp-server-warn]

  agent-unsigned:
    build: .
    command: python agent.py --anv=false --server=http://mcp-server-require:8002
    depends_on: [mcp-server-require]
```

---

## What This PoC Is NOT

- Not production cryptography (mock EAT token)
- Not a real TLS extension (HTTP headers as mock)
- Not a complete MCP implementation

The mock layer is explicitly documented. Real TLS extension
and CBOR EAT tokens are draft-01 scope after community review.

## Benchmark Disclaimer

The 2ms overhead measured in this PoC reflects:
- HTTP header parsing in FastAPI middleware
- Mock HMAC-SHA256 token validation
- JSON serialization

This does NOT represent production ANV overhead. Real TLS
extension latency depends on:
- RATS Verifier round-trip (external service call)
- CBOR EAT parsing (not JSON)
- TLS stack integration (crypto/tls or OpenSSL C bindings)
- Hardware AES-NI availability

Production benchmark requires real TLS extension implementation
and is deferred to PoC Stage 2 (Go SDK, draft-01 scope).

---

## Success Criteria

```
✓ Case A: SIGNED_AI accepted, tool executes, result returned
✓ Case B: SIGNED_AI accepted in require mode
✓ Case C: UNSIGNED accepted with warning in warn mode
✓ Case D: UNSIGNED rejected with 403 + structured body in require mode
✓ Benchmark: ANV overhead measured and documented
✓ All four cases reproducible with docker-compose up
```

---

## Repository Structure

```
anv-protocol/
  mcp-poc/
    anv/
      __init__.py
      token.py
      middleware.py
      policy.py
    mcp_server.py
    agent.py
    benchmark.py
    docker-compose.yml
    requirements.txt
    README.md
```

---

**Author:** Alex Anokhin
**GitHub:** github.com/olanokhin/anv-protocol
**Date:** April 2026
