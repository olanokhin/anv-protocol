Network Working Group                                         A. Anokhin
Internet-Draft                                            Independent
Intended status: Informational                            March 2026
Expires: September 2026


           The Artificial-Nature Verification (ANV) Protocol
                          draft-anokhin-anv-00

Abstract

   This document proposes the Artificial-Nature Verification (ANV)
   protocol, an extension to existing transport and session layers
   (TLS, QUIC, MLS). ANV provides a cryptographic mechanism to verify
   whether a communication participant is of biological (Human) or
   artificial (AI) nature. By utilizing hardware roots of trust
   (Secure Enclaves, FIDO2, TPM, Confidential Computing), ANV addresses
   the critical vulnerability of real-time deepfakes and undisclosed
   autonomous agents in digital communications.

Status of This Memo

   This Internet-Draft is submitted in full conformance with the
   provisions of BCP 78 and BCP 79.

   Internet-Drafts are working documents of the Internet Engineering
   Task Force (IETF). Note that other groups may also distribute
   working documents as Internet-Drafts. The list of current Internet-
   Drafts is at https://datatracker.ietf.org/drafts/current/.

   This Internet-Draft will expire on September 2026.


1.  Introduction

   Modern communication protocols (TLS, DTLS, QUIC, MLS) successfully
   secure the channel between endpoints. However, they operate under
   an implicit assumption: that the entity behind the endpoint is human.

   With the proliferation of real-time AI generation (deepfake audio/
   video) and autonomous agents, the Human-to-Human paradigm has
   fractured into a 4-state matrix:

      H2H   human → human     implicit trust assumption
      H2AI  human → AI        CAPTCHA is heuristic, not protocol
      AI2H  AI    → human     PRIMARY GAP: no standard exists
      AI2AI AI    → AI        no attestation standard

   The ANV protocol introduces a "Nature Handshake" to
   cryptographically attest the origin of the communication entity,
   moving from detecting fakes (heuristic, unwinnable) to verifying
   originals (deterministic, cryptographic).

   Core principle: An ANV-unverified participant is not necessarily
   fake. It is unattested. The protocol makes no claim about
   unverified participants beyond absence of proof.


2.  Terminology

   The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
   "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY",
   and "OPTIONAL" in this document are to be interpreted as described
   in BCP 14 [RFC2119] [RFC8174].

   Nature:         The biological or artificial origin of a
                   communication participant.

   Nature Handshake: The ANV Phase 1 process establishing mutual
                   nature attestation and deriving a session key.

   Attestation:    A cryptographically signed claim about the
                   hardware and/or biological state of a participant.


3.  Graduated Attestation Model

   ANV defines five states of nature attestation:

   HUMAN_STRONG    Biometric (FIDO2) + Secure Enclave attestation.
                   Highest guarantee of biological presence.

   HUMAN_WEAK      Secure Enclave attestation only. Biometric
                   confirmation absent or not performed.
                   Vulnerable to device theft or coercion.

   AI_ATTESTED     TPM / Confidential Computing attestation.
                   Proves specific model version executing on
                   specific verified hardware instance.

   AI_DECLARED     API-level self-disclosure without hardware proof.
                   Minimal guarantee; better than no disclosure.

   UNVERIFIED      No ANV data. Legacy fallback. Not necessarily
                   fraudulent — simply without guarantees.

   The graduated model explicitly accommodates hybrid and edge cases
   (real-time AI assistance, AAC devices) without requiring binary
   classification.


4.  Protocol Operation (High-Level)

   ANV follows Control Plane / Data Plane separation:

   Phase 1 — Nature Handshake (once per session):

      Transport: QUIC or TLS 1.3 extension (port 443)

      Human participant:
         Device-bound biometric attestation (FIDO2 / Secure Enclave)
         → Generates symmetric session key
         → Signed by biometry + hardware

      AI participant:
         Hardware attestation (TPM / Confidential Computing)
         → "This process, on this hardware, of this model version"
         → Generates symmetric session key
         → Signed by hardware attestation

      Result: Mutual nature verification + attestation level assigned

   Phase 2 — Data Stream (per packet):

      Transport: UDP / QUIC data plane
      Encryption: AES-GCM (hardware acceleration via AES-NI)
      Integrity: MAC with session key derived in Phase 1
      Latency: ≈ 0

      A packet with invalid MAC MUST be silently dropped.

   [EDITOR NOTE: Detailed structure of ANV Extension Payload,
   integration with TLS 1.3 ClientHello/ServerHello extensions,
   and formal key derivation function to be specified in draft-01.]


5.  Root of Trust Asymmetry

   Human Root of Trust: biological body.
                        Cannot be copied. Cannot run twice.
                        Unit of identity: person + device.

   AI Root of Trust:    hardware process.
                        Can be cloned by design.
                        Unit of identity: session instance, not persona.

   This asymmetry is intentional. ANV does not assign AI a persistent
   identity. ANV verifies a specific running instance. Nature, not
   identity.


6.  Relation to Existing Standards

   TLS 1.3 [RFC8446]   Authenticates server certificate.
                        Does not verify participant nature.

   MLS [RFC9420]        Verifies device group membership.
                        Does not verify participant nature.

   FIDO2 [FIDO-CTAP2]   Human-device binding.
                        Partial solution for Human-side only.

   C2PA                 Signs content after creation.
                        Not real-time. Not session-based.

   CAPTCHA              Heuristic H2AI gate.
                        Not a protocol. Detects, does not attest.

   ANV is orthogonal to all of the above and designed to be
   composable: TLS+ANV, MLS+ANV, QUIC+ANV.


7.  Security Considerations

   This draft explicitly acknowledges open attack vectors:

   7.1  Proxy/Relay Attack

      An AI_ATTESTED participant routes through a HUMAN_STRONG
      endpoint. Recipient observes HUMAN_STRONG; actual generator
      is AI. Mitigation: not defined in this draft. Open problem.

   7.2  Device Coercion

      Physical coercion to unlock device downgrades effective
      guarantee to below HUMAN_WEAK. Outside protocol scope.
      Physical security is a precondition.

   7.3  Attestation Registry Centralization

      AI_ATTESTED requires a registry of valid model attestations.
      Centralized registry creates monopoly risk (single vendor
      controls AI legitimacy). Decentralized alternatives
      (DNSSEC-style, blockchain-anchored) to be explored in
      future drafts.

   7.4  Model Identity Instability

      Model identity across versions, fine-tuning, and quantization
      is an open research problem. What constitutes the attestable
      unit: weights hash, capability set, runtime binary? To be
      defined.


8.  IANA Considerations

   URI scheme registration for httpsa:// or httpsn:// to be
   requested pending working group formation and community review.
   Conflict analysis with existing IANA registry conducted;
   httpsn:// has minimal known conflicts as of March 2026.


9.  References

   [RFC2119]  Bradner, S., "Key words for use in RFCs", BCP 14.
   [RFC8446]  Rescorla, E., "The Transport Layer Security (TLS)
              Protocol Version 1.3".
   [RFC9420]  Barnes, R. et al., "The Messaging Layer Security (MLS)
              Protocol".
   [FIDO-CTAP2] FIDO Alliance, "Client to Authenticator Protocol 2".


Author's Address

   Alex Anokhin
   Independent Researcher
   Email: olanokhin@gmail.com
   GitHub: github.com/olanokhin/anv-protocol
