# ANV PoC Stage 1

This PoC demonstrates that an MCP server can identify the caller's ANV authorization type before executing any tool and can enforce `warn` or `require` policy accordingly. The implementation is intentionally mock-only and uses JSON-over-HTTP headers plus HMAC validation rather than real TLS extensions or CBOR EAT tokens.

## Quick Start

```bash
cd mcp-poc
pip install -r requirements.txt
python mcp_server.py --anv-policy=warn --port=8001
python mcp_server.py --anv-policy=require --port=8002
python agent.py --anv=true --server=http://localhost:8001 --port=8003
python agent.py --anv=false --server=http://localhost:8002 --port=8004
```

## Run Tests

```bash
cd mcp-poc
pytest tests/
```

## Docker

```bash
cd mcp-poc
docker-compose up --build
```

## Four Cases

```bash
curl -X POST http://localhost:8003/run -H "content-type: application/json" -d '{"task":"Calculate 42 * 7"}'
curl -X POST http://localhost:8004/run -H "content-type: application/json" -d '{"task":"Calculate 42 * 7"}'
```

For a true latency baseline, start a separate server with `python mcp_server.py --anv-enabled=false --port=8000` and run:

```bash
python benchmark.py --server=http://localhost:8001 --baseline-server=http://localhost:8000 --n=100
```

Full protocol and PoC details live in [../spec/anv-poc-spec.md](../spec/anv-poc-spec.md).
