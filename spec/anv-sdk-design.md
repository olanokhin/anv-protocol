# ANV SDK — Architecture and Implementation Roadmap
## Status: Design concept | Not part of protocol specification
## Date: April 2026

This document captures the SDK design intent for the ANV protocol.
SDK concerns are separate from the protocol specification and do not
affect draft-anokhin-anv-00 or any IETF submission.

---

## Core Architecture Principle

The ANV SDK is layered. The Rust core library provides the
performance-critical implementation. All other language SDKs
wrap the Rust core via FFI or provide independent implementations
where the ecosystem demands it.

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│         (MCP agents, A2A pipelines, SIP stacks)         │
├──────────┬──────────┬──────────┬────────────────────────┤
│  Python  │ Kotlin/  │  Elixir  │   C# / .NET   │ Swift  │
│   SDK    │   JVM    │   SDK    │      SDK      │  SDK   │
├──────────┴──────────┴──────────┴────────────────────────┤
│                      Go SDK                              │
│          (cloud native, WIMSE, service mesh)             │
├─────────────────────────────────────────────────────────┤
│                   Rust Core Library                      │
│         ANV TLS extension + EAT token + crypto           │
│              C FFI for legacy C/C++ stacks               │
├─────────────────────────────────────────────────────────┤
│              Protocol Layer (ANV draft-00)               │
│         TLS 1.3 extension | QUIC | RATS/EAT              │
└─────────────────────────────────────────────────────────┘
```

---

## Language Strategy

### Stage 1 — PoC (Q2 2026)

**Python**

Target: AI/ML engineers, MCP/A2A community, researchers.

```
Ecosystem    MCP official Python SDK, A2A Python SDK
Speed        Fastest to iterate PoC design
Community    First adopters are Python AI engineers
```

Deliverables:
- Mock ANV TLS extension
- Mock EAT token generation
- MCP server with ANV authorization type logging
- Latency benchmark vs baseline

---

### Stage 2 — MVP (Q3 2026)

**Go**

Target: Cloud native infrastructure, WIMSE WG, service mesh.

```
Ecosystem    Kubernetes, Envoy, Istio, gRPC
TLS          crypto/tls — one of best TLS implementations
WIMSE        Go is dominant language in WIMSE reference impls
Performance  Sufficient for handshake (once per session)
```

Deliverables:
- Production-ready TLS extension
- Real EAT token with CBOR encoding
- MCP + A2A adapters
- Docker image for easy deployment

---

### Stage 3 — Enterprise (2027)

**Kotlin/JVM**

Target: Enterprise backend, Android, Spring Boot ecosystem, banks.

```
JVM          Runs everywhere Java runs — no separate Java SDK needed
Android      Native Kotlin — covers mobile clients
Spring Boot  Native Kotlin support — enterprise adoption path
JNI          Wraps Rust core for performance-critical paths
             Same pattern as Whisper-JNI (proven approach)
Banking      Spring + JVM = standard enterprise stack
```

Deliverables:
- Spring Boot ANV starter
- Android ANV client library
- Hyperledger Besu blockchain provider
- Enterprise audit trail integration

**C# / .NET**

Target: Microsoft ecosystem, Azure, Teams.

```
Azure        Major AI provider infrastructure
Teams        Direct AI2H use case
.NET         Standard for Microsoft-stack enterprise
```

Deliverables:
- Azure ANV middleware
- Teams ANV integration
- .NET BlockchainProvider for Azure

---

### Stage 4 — Performance & Real-time (2027+)

**Rust Core Library**

Target: Telecom, WebRTC, embedded, C/C++ legacy stacks.

```
Telecom      SIP/RTP stacks — microsecond latency matters
WebRTC       Per-packet MAC verification on hot path
Embedded     No GC, no runtime — IoT and edge AI
C FFI        Legacy C/C++ telecom stacks integrate via FFI
Performance  Phase 2 per-packet AES-GCM — Rust advantage
```

```rust
// C FFI surface for legacy stacks
#[no_mangle]
pub extern "C" fn anv_create_session(
    config: *const ANVConfig
) -> *mut ANVSession { ... }

#[no_mangle]
pub extern "C" fn anv_export_token(
    session: *mut ANVSession
) -> *mut EATToken { ... }

#[no_mangle]
pub extern "C" fn anv_verify_token(
    token: *const EATToken,
    provider_cert: *const u8,
    cert_len: usize
) -> bool { ... }
```

**Elixir**

Target: Wire, WhatsApp-style messaging, telecom OTP stacks.

```
Wire         Direct MVP messenger target — Elixir backend
WhatsApp     Erlang/OTP — 2B users, proven real-time scale
BEAM VM      Millions of lightweight processes
             Each ANV session = isolated Erlang process
             Perfect concurrency model for session-per-connection
Telecom      Erlang created for telecom — natural fit
```

**Swift**

Target: iOS clients, Apple Secure Enclave for SIGNED_HUMAN.

```
iOS          Native ANV client for mobile
Secure       Apple Secure Enclave = SIGNED_HUMAN root of trust
Enclave      Direct hardware binding for biometric attestation
```

---

## Blockchain Provider Architecture

Blockchain integration is optional. The default provider uses
Certificate Transparency logs requiring no blockchain dependency.

### Abstract Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class EATToken:
    provider_cert: str       # AI provider certificate subject
    session_id: str          # ANV session identifier
    authorization_type: str  # SIGNED_HUMAN | SIGNED_AI | UNSIGNED
    hardware_binding: bytes  # TPM/TEE attestation evidence
    timestamp: int           # Unix timestamp
    signature: bytes         # Hardware-bound signature

class ANVBlockchainProvider(ABC):

    @abstractmethod
    async def write_attestation(self, token: EATToken) -> str:
        """Write attestation. Returns tx_hash or log identifier."""
        pass

    @abstractmethod
    async def verify_attestation(self, token: EATToken) -> bool:
        """Verify attestation exists and is unrevoked."""
        pass

    @abstractmethod
    async def revoke_attestation(self, token_id: str) -> bool:
        """Revoke attestation on certificate compromise."""
        pass

    @abstractmethod
    async def get_attestation(
        self, session_id: str
    ) -> Optional[EATToken]:
        """Retrieve attestation by session identifier."""
        pass

    @abstractmethod
    async def get_provider_history(
        self,
        provider_cert: str,
        limit: int = 100
    ) -> list[EATToken]:
        """Audit trail for a provider certificate."""
        pass
```

### Reference Implementations

```python
class CTLogProvider(ANVBlockchainProvider):
    """
    Default. Certificate Transparency logs.
    No blockchain. No gas fees. No web3 dependency.
    Maximum compatibility. Free.
    """

class PolygonProvider(ANVBlockchainProvider):
    """
    EVM / Polygon PoS.
    Cost: ~$0.001/tx. Finality: ~2 sec.
    Public transparency. Smart contract integration.
    """

class ArbitrumProvider(ANVBlockchainProvider):
    """
    EVM L2 / Arbitrum.
    Cost: ~$0.001/tx. Finality: ~2 sec soft.
    High volume deployments.
    """

class HyperledgerProvider(ANVBlockchainProvider):
    """
    Permissioned EVM / Hyperledger Besu.
    Cost: zero. Finality: <1 sec.
    Enterprise / banking / regulated industries.
    """
```

### Multi-Provider Usage

Users instantiate any number of providers. Writes execute
in parallel. Each provider is independent — one failure
does not affect others.

```python
# Default — CT logs only
session = await anv.connect(endpoint)

# Multiple providers in parallel
session = await anv.connect(
    endpoint,
    blockchain=[
        CTLogProvider(),                           # public audit
        PolygonProvider(rpc_url="...", ...),       # public chain
        HyperledgerProvider(node_url="...", ...),  # internal audit
    ]
)

# Write to all providers simultaneously
results = await session.write_attestation(token)
# {
#     "CTLogProvider":       "leaf_hash:abc123",      # success
#     "PolygonProvider":     "0xabc...tx_hash",        # success
#     "HyperledgerProvider": TimeoutError("timeout"),  # isolated failure
# }
# Session valid. Two of three providers recorded.
```

### Recommended Chains by Use Case

| Use Case | Provider | Reason |
|---|---|---|
| Default / no web3 | CTLogProvider | Free, no dependencies |
| Public transparency | Polygon + CTLog | Low cost, EVM, public |
| High volume | Arbitrum + CTLog | Very low cost, fast |
| Enterprise / regulated | Hyperledger Besu | Permissioned, internal |
| DeFi / DAO / Web3 | Polygon or Arbitrum | EVM smart contracts |
| Maximum redundancy | CTLog + Polygon + Arbitrum | Three independent |

---

## Smart Contract Integration

EAT tokens are verifiable on-chain with standard ECDSA.
No custom cryptography required.

```solidity
contract ANVVerifier {

    mapping(bytes32 => bool) public trustedProviders;

    function verifyANVAttestation(
        bytes calldata eatToken,
        bytes calldata signature,
        bytes32 providerCertHash
    ) external view returns (bool isValid, string memory authType) {
        require(trustedProviders[providerCertHash], "Unknown provider");
        bytes32 tokenHash = keccak256(eatToken);
        address signer = recoverSigner(tokenHash, signature);
        isValid = isKnownProvider(signer, providerCertHash);
        authType = extractAuthType(eatToken);
    }
}
```

---

## Repository Structure

```
anv-protocol/
  spec/
    draft-anokhin-anv-00.txt
    anv-implementation-guidance.md
    anv-sdk-design.md              ← this document
  sdk/
    python/                        ← Stage 1, PoC
    go/                            ← Stage 2, MVP
    kotlin/                        ← Stage 3, Enterprise + Android
    dotnet/                        ← Stage 3, Microsoft/Azure
    rust/                          ← Stage 4, Telecom + C FFI
    elixir/                        ← Stage 4, Wire + messaging
    swift/                         ← Stage 4, iOS
  contracts/
    ANVVerifier.sol                ← EVM smart contract
  examples/
    mcp-poc/                       ← PoC Stage 1
    a2a-poc/                       ← PoC Stage 2
```

---

## What This Does NOT Change

- ANV protocol specification is unchanged
- TLS handshake is unchanged
- EAT token format is unchanged
- Blockchain integration does not affect session establishment
- UNSIGNED sessions remain valid regardless of SDK configuration

---

**Status:** Design concept. Not implemented.
**Next step:** Python PoC — mcp-poc/ directory.
**Author:** Alex Anokhin
**Date:** April 2026
