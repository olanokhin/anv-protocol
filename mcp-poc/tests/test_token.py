"""Unit tests for mock ANV token handling."""

from __future__ import annotations

import base64
import json
import time

from anv.token import TOKEN_TTL_SECONDS, generate_token, validate_token


def test_generate_returns_string() -> None:
    token = generate_token()
    assert isinstance(token, str)
    assert token


def test_validate_valid_token() -> None:
    token = generate_token()
    validated = validate_token(token)
    assert validated is not None
    assert validated.authorization_type == "SIGNED_AI"


def test_validate_wrong_signature() -> None:
    token = generate_token()
    payload = json.loads(base64.b64decode(token.encode("ascii")).decode("utf-8"))
    payload["signature"] = "deadbeef"
    tampered = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    assert validate_token(tampered) is None


def test_validate_expired_token() -> None:
    token = generate_token()
    payload = json.loads(base64.b64decode(token.encode("ascii")).decode("utf-8"))
    payload["timestamp"] = int(time.time()) - TOKEN_TTL_SECONDS - 1
    tampered = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    assert validate_token(tampered) is None


def test_validate_missing_fields() -> None:
    raw = base64.b64encode(json.dumps({"provider_cert": "example"}).encode("utf-8")).decode("ascii")
    assert validate_token(raw) is None


def test_roundtrip_signed_ai() -> None:
    token = generate_token(provider="example-ai-provider.com", auth_type="SIGNED_AI", level="AI_ATTESTED")
    validated = validate_token(token)
    assert validated is not None
    assert validated.provider_cert == "example-ai-provider.com"
    assert validated.attestation_level == "AI_ATTESTED"


def test_roundtrip_signed_human() -> None:
    token = generate_token(provider="human-device-credential", auth_type="SIGNED_HUMAN", level="HUMAN_STRONG")
    validated = validate_token(token)
    assert validated is not None
    assert validated.authorization_type == "SIGNED_HUMAN"
    assert validated.attestation_level == "HUMAN_STRONG"
