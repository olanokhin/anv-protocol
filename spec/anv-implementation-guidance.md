# ANV Implementation Guidance
## draft-anokhin-anv-ig-00 | April 2026

This document provides implementation guidance for the ANV protocol
as defined in draft-anokhin-anv-00. It describes required changes per
affected protocol, a complete applicability matrix, and an adoption
roadmap by stakeholder category.

This document is informational. It does not define normative requirements.

---

## 1. Affected Protocols and Required Changes

Protocols are classified by satisfaction of the ANV applicability
criteria defined in draft-anokhin-anv-00 Section 4:

```
(1) Real-time bidirectional channel
(2) Recipient can act on authorization information before or during interaction
(3) Authorizing party type is material to the recipient's decision
```

---

### 1.1 Fully Compatible Protocols

---

#### 1.1.1 TLS 1.3 [RFC8446]

**Change type:** New extension in ClientHello / ServerHello

```
Extension Type: anv_authorization
  (experimental value during PoC/MVP; IANA assignment at standardization)

ClientHello:
  anv_supported: boolean
  anv_attestation_offer: EAT token (optional)

ServerHello:
  anv_accepted: boolean
  anv_attestation_response: EAT token (optional)
  anv_peer_level: { SIGNED_HUMAN | SIGNED_AI | UNSIGNED }
```

Backward compatible. Sessions without ANV proceed as standard TLS 1.3.

Payload size note: EAT tokens may be several kilobytes. Two mitigations
under evaluation for draft-01: (a) deferred attestation — ANV handshake
as post-TLS message avoiding ClientHello size constraints; (b) TLS ECH
(Encrypted ClientHello) — attestation_payload inside ECH concealing
organizational metadata from passive observers.

Middlebox note: Unknown TLS extension types may be dropped by corporate
proxies. GREASE-style probing and fallback negotiation to be addressed
in draft-01.

---

#### 1.1.2 MCP (Model Context Protocol)

**Change type:** TLS extension on existing HTTPS transport only

MCP operates over standard HTTPS. ANV requires no changes to the MCP
protocol itself. The TLS ANV extension (Section 1.1.1) is applied to
the underlying TLS connection. The MCP server receives authorization
type before any MCP messages are exchanged.

ANV and OAuth 2.1 are complementary within MCP:
- OAuth 2.1: establishes what the agent is permitted to do
- ANV: establishes which hardware-bound provider instance is acting

PoC implementation note: use vendor-neutral provider identifier
(e.g., "Example AI Provider") not a specific vendor name, to
demonstrate protocol-agnostic applicability.

---

#### 1.1.3 A2A (Agent2Agent Protocol)

**Change type:** TLS extension on existing HTTPS transport +
optional Agent Card field

A2A operates over HTTPS (JSON-RPC 2.0). ANV requires no changes
to A2A itself. Signed agent cards (A2A v0.3) and ANV are complementary:
cards establish content integrity; ANV adds session-layer hardware
attestation.

Optional Agent Card ANV field:
```json
{
  "name": "Example Agent",
  "url": "https://agent.example.com",
  "anv": {
    "supported": true,
    "attestation_level": "AI_ATTESTED",
    "provider_cert_url": "https://agent.example.com/.well-known/anv-cert"
  }
}
```

The Agent Card ANV field is informational. The authoritative
attestation is the TLS-layer handshake.

---

#### 1.1.4 QUIC [RFC9000]

**Change type:** New transport parameter in Initial packet

```
Transport Parameter: anv_authorization
  (experimental value during PoC/MVP)
  Carried in Initial packet (encrypted)
  Contains: EAT attestation token
  Result: anv_session_level at connection establishment
```

Backward compatible per RFC9000 Section 7.4.

---

#### 1.1.5 MLS [RFC9420]

**Change type:** New KeyPackage + GroupContext extensions

```
KeyPackage extension: anv_credential
  EAT token bound to leaf node key
  Per-member authorization level within a group

GroupContext extension: anv_policy
  { REQUIRE_SIGNED_HUMAN | REQUIRE_SIGNED_AI | ALLOW_UNSIGNED | MIXED }
```

---

#### 1.1.6 WebRTC / DTLS [RFC6347]

**Change type:** New DTLS extension in ClientHello

```
DTLS Extension: anv_authorization
  Mirrors TLS 1.3 extension structure
  Negotiated before media establishment
  Result: anv_session_level before first media packet
```

---

#### 1.1.7 SIP [RFC3261]

**Change type:** New SIP header field

```
ANV-Authorization: SIGNED_AI; provider="example.com";
                   cert-fingerprint=sha-256:AA:BB:...;
                   attestation-level=AI_ATTESTED
```

Inspectable at INVITE time — criterion (2) satisfied before call answer.

---

### 1.2 Conditionally Compatible Protocols

Full specification deferred to future draft.

---

#### 1.2.1 WebSocket [RFC6455]

Criterion (2) satisfied only as explicit wssa:// scheme.

```
wssa://   ANV handshake MUST complete before first WebSocket frame
```

ANV via HTTP upgrade within existing https:// session does not
satisfy criterion (2) and is out of scope for this draft.

---

#### 1.2.2 XMPP [RFC6120]

Criterion (2) satisfied only if ANV stream feature is negotiated
before first content stanza. Session MUST be classified UNSIGNED
if content precedes ANV negotiation.

---

### 1.3 Out of Scope

```
Email (SMTP/SMTPS)     Async — C2PA, DKIM, S/MIME
RSS / Atom             No bidirectional session
Webhooks               Async
Push notifications     Async
DNS                    No bidirectional session — DNSSEC
NTP                    No bidirectional session
CDN delivery           No authorizing party in ANV sense
Code signing           Content signing — GPG, Authenticode
Package registries     Content signing
Git commits            Content signing — GPG
```

---

## 2. Applicability Matrix

### 2.1 H2H — Human to Human

**Scenario A: Organizational employee, verified device**
```
Initiator:  SIGNED_HUMAN | org device cert — Example Bank — DigiCert
Recipient:  Observable: human principal, organizational affiliation
```

**Scenario B: Unaffiliated individual**
```
Initiator:  SIGNED_HUMAN | personal device, no org cert
Recipient:  Detectable: certificate issuer mismatch — no content analysis
```

**Scenario C: No ANV**
```
Initiator:  UNSIGNED — policy: recipient determines
```

---

### 2.2 H2AI — Human to AI

**Scenario A: Institutional AI service**
```
Human  →  SIGNED_AI | AI_ATTESTED — Example Bank — DigiCert
          Observable: provider cert matches known institution
```

**Scenario B: Unaffiliated AI service**
```
Human  →  SIGNED_AI — unaffiliated party
          Detectable: certificate issuer mismatch — no content analysis
```

**Scenario C: Legacy**
```
Human  →  UNSIGNED — policy: recipient determines
```

---

### 2.3 AI2H — AI to Human (Primary Gap)

**Scenario A: Institutional AI initiates**
```
SIGNED_AI | AI_ATTESTED — Example Bank — DigiCert
  Observable before content delivery:
    Authorization type: SIGNED_AI
    Provider: Example Bank
    Certificate issuer: DigiCert
  Policy: accept — known institution, attested AI
```

**Scenario B: Unaffiliated AI initiates**
```
SIGNED_AI — unaffiliated party
  Detectable before content: certificate issuer not recognized
  No content analysis required
```

**Scenario C: Unattested AI initiates**
```
UNSIGNED — observable before content delivery
  Policy: recipient determines
```

---

### 2.4 AI2AI — Agent Pipeline (MCP / A2A)

**Scenario A: Fully attested MCP tool call chain**
```
Orchestrator:  SIGNED_AI | AI_ATTESTED — Provider A — DigiCert
MCP server:    SIGNED_AI | AI_ATTESTED — Provider B — DigiCert
  Each hop: provider cert verified before tool call processed
  Full authorization chain verifiable
```

**Scenario B: Broken chain — A2A pipeline injection**
```
Agent 1:  SIGNED_AI | AI_ATTESTED — Org A — DigiCert
Agent 2:  SIGNED_AI — unaffiliated party
       OR UNSIGNED
  Detectable at injection point: issuer mismatch or UNSIGNED
  No content analysis required
  Pipeline policy: reject unrecognized provider
```

**Scenario C: Pre-authorized cross-org delegation**
```
Agent 1:  SIGNED_AI | AI_ATTESTED — Org A — DigiCert
Agent 2:  SIGNED_AI | AI_ATTESTED — Authorized Partner — DigiCert
  Org A pre-authorizes specific partner certs
  Cert not in pre-authorized list triggers policy review
```

---

## 3. Adoption Roadmap by Stakeholder

### 3.1 Certificate Authorities

**PoC:** Self-signed mock cert. No CA required.

**MVP:** One CA issues AI provider endpoint cert via existing OV
process. No new cert profile required.

**Product v1:** CA/Browser Forum defines AI provider endpoint
certificate profile. CT log publication on same basis as domain certs.

---

### 3.2 AI Providers

Required at MVP:
1. Obtain AI provider endpoint cert from one CA
2. Implement ANV TLS extension in HTTPS service
3. Present SIGNED_AI on outbound MCP and A2A sessions

Hardware: no new procurement for providers on TEE-capable
infrastructure (Intel TXT, AMD SEV, ARM TrustZone).

PoC: self-signed cert with vendor-neutral provider identifier.

---

### 3.3 Agentic Protocol Communities

**MCP:** No protocol changes required. ANV operates at TLS layer.
Reference implementation to be submitted to MCP community after PoC.

**A2A:** No protocol changes required. Optional Agent Card ANV field
to be proposed to A2A working group after PoC. ANV complements signed
agent cards without replacing them.

---

### 3.4 Browsers

**PoC/MVP:** No changes required.

**Product v1:** ANV authorization type indicator in connection
information panel over https://.

**Standardization:** httpsa:// URI scheme IANA registration.

```
🟢  SIGNED_HUMAN   human authorized [org if present]
🔵  SIGNED_AI      AI authorized — provider: [cert subject]
⚪  UNSIGNED       no ANV data
```

---

### 3.5 Messaging Platforms

**MVP:** ANV indicator in one messenger over existing DTLS connection.

**Product v1:** MLS+ANV KeyPackage and GroupContext extensions.

---

### 3.6 VoIP and Call Center Infrastructure

**MVP:** SIP ANV-Authorization header. AI endpoints obtain provider
endpoint certificates. Recipient device displays authorization type
before call answer.

EU AI Act Article 52 alignment: ANV provides cryptographic mechanism
for verifiable AI disclosure at protocol layer.

---

### 3.7 Regulators

No protocol changes required. ANV produces session-level audit trail
admissible as technical evidence of disclosure or non-disclosure.

EU AI Act Article 52 candidate mechanism: cryptographically verifiable
disclosure that a communication was authorized by an AI provider,
before content delivery.

Engagement at Product v1 stage when reference implementations available.

---

## 4. Adoption Sequence

Each phase relies only on deliverables from preceding phases.
No forward dependencies.

```
PoC Stage 1 — MCP (Q2 2026)
  TLS ANV extension, vendor-neutral mock attestation (EAT format)
  Single AI provider → single MCP server
  Demonstrate: SIGNED_AI visible before first tool call
  Measure: Phase 1 latency overhead
  Artifact: open source + benchmark
  Dependencies: none

PoC Stage 2 — A2A (Q2 2026)
  Same TLS ANV extension on A2A HTTPS transport
  Broken chain detection: UNSIGNED agent at hop 3 flagged
  Optional Agent Card ANV field
  Artifact: cross-protocol demo
  Dependencies: PoC Stage 1 complete

MVP (Q3 2026)
  One CA issues real AI provider endpoint cert (OV process)
  SIP ANV-Authorization — AI call center use case
  ANV indicator in one messenger (DTLS layer, no MLS changes)
  IETF draft-01: TLS extension wire format + KDF + EAT payload spec
  Community outreach: MCP, A2A, IETF RATS WG, IETF WIMSE WG, IRTF
  WIMSE WG is directly relevant: Workload Identity in Multi-System
  Environments covers the AI2AI pipeline attestation use case
  Dependencies: PoC Stage 1 and 2 complete

Product v1 (2027)
  CA/Browser Forum AI provider cert profile adopted
  MLS+ANV, MCP+ANV, A2A+ANV extensions ratified
  Browser ANV indicator over https://
  Production handshake at scale
  Dependencies: MVP demonstrated, working group formed

Standardization (2027+)          ← IANA here, not earlier
  IANA extension type assignments
  httpsa:// and wssa:// registration
  RFC publication
  Dependencies: Product v1 operational, working group consensus

Regulatory (parallel with Product v1)
  EU AI Act Article 52 alignment
  Reference implementation for regulators
  Dependencies: MVP demonstrated
```

---

**Author:** Alex Anokhin
**Contact:** olanokhin@gmail.com
**GitHub:** github.com/olanokhin/anv-protocol
**Date:** April 2026
