# ANV: Artificial-Nature Verification Protocol

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Status](https://img.shields.io/badge/Status-Concept_v0.3-orange.svg)]()

> *TLS secured the channel. ANV verifies who is on it.*

ANV is a proposed transport-layer extension that cryptographically 
verifies the biological or artificial **nature** of communication 
participants in real-time. Conceptually: adding the letter "A" 
(Authentic/Attested) to existing protocols — `httpsa://`, `MLS+ANV`, 
`QUIC+ANV`.

---

## The Crisis of Entity Trust

Existing protocols (HTTPS, WebRTC, MLS) verify that data securely 
reached a specific endpoint. They cannot verify **the nature** of the 
entity generating it.

Deepfake voice calls, undisclosed AI agents, and automated scams all 
exploit the implicit Human-to-Human trust assumption. Detection 
heuristics (CAPTCHA, AI-detectors) are an unwinnable arms race.

**ANV's core principle:**
> We cannot win the war against fakes by detecting them.  
> We must cryptographically protect the original.

Unverified ≠ fake. Unverified = no guarantees.

---

## The 4-State Communication Matrix

```
H2H   human  → human    deepfake exploits this assumption
H2AI  human  → AI       CAPTCHA is a heuristic, not a protocol
AI2H  AI     → human    ← PRIMARY UNADDRESSED GAP (no standard exists)
AI2AI AI     → AI       no attestation standard
```

---

## Graduated Nature Attestation Model

ANV replaces binary Human/AI with a cryptographically verifiable scale:

| Level | Description | Root of Trust |
|---|---|---|
| 🟢 HUMAN_STRONG | Biometric + Device attestation | FIDO2 + Secure Enclave |
| 🟡 HUMAN_WEAK | Device attestation only | Secure Enclave |
| 🔵 AI_ATTESTED | Hardware attestation of model instance | TPM / Confidential Computing |
| ⚪ AI_DECLARED | Self-claim without hardware proof | API-level |
| ❓ UNVERIFIED | No ANV data (legacy fallback) | — |

---

## Architecture

ANV uses Control Plane / Data Plane separation:

**Phase 1 — Nature Handshake** (once per session, port 443):
- Human: device-bound biometry → symmetric session key
- AI: hardware attestation → symmetric session key
- Result: mutual nature verification + attestation level

**Phase 2 — Data Stream** (every packet):
- AES-GCM encryption + MAC signature with session key
- Latency ≈ 0 (hardware AES-NI acceleration)
- Forged packet → MAC mismatch → silently dropped

---

## Why Now

- Deepfake CEO fraud: $25M+ per incident (Hong Kong 2024, Europe 2025-2026)
- 1 in 4 Americans received a deepfake voice call in the past year (Hiya, March 2026)
- Projected $40B global deepfake losses by 2027 (Deloitte)
- NIST AI Agent Standards Initiative launched February 2026
- EU AI Act disclosure requirements incoming

**The gap no one closed:**  
Graduated nature attestation in real-time messaging (voice/video/group chats).  
MLS + WebRTC + QUIC — all without an ANV layer.

---

## Relation to Existing Standards

| Standard | What it does | What it doesn't do |
|---|---|---|
| TLS 1.3 | Verifies server certificate | Not participant nature |
| MLS | Verifies device group membership | Not participant nature |
| FIDO2 | Human-device binding | Partial H-side only |
| C2PA | Signs content post-creation | Not real-time |
| CAPTCHA | H2AI heuristic gate | Not a protocol |
| SPIFFE | Workload identity (cloud/K8s) | Not real-time messaging |
| World ID | Human proof behind agent | Iris scan, not messaging layer |

ANV is orthogonal to all of the above and composable with each.

---

## Known Open Problems

1. **AI attestation registry** — who runs it? Centralization risk.
2. **Model identity** across versions, fine-tuning, quantization
3. **Proxy/relay attack** — AI routing through a HUMAN_STRONG endpoint
4. **Device coercion** — physical security outside protocol scope
5. **Hybrid cases** — real-time AI assist, AAC devices, future implants

---

## Roadmap

```
March 2026   Concept v0.3 + IETF Draft-00  ← you are here
Q2 2026      PoC implementation (QUIC + mock attestation)
Q2 2026      arXiv preprint
Q3 2026      IETF submission + Wire/Signal outreach
2027+        Working group formation
```

---

## Contributing

Feedback, edge case critique, and reference implementations welcome.  
This is draft-00. There are known holes. That's the point.

**Author:** Alex Anokhin  
**Contact:** olanokhin@gmail.com  
**Date:** March 2026
