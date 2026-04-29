"""Mock EAT token generation and validation for the Stage 1 PoC."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

SECRET_KEY = b"anv-mock-secret-do-not-use-in-production"
TOKEN_TTL_SECONDS = 300


@dataclass
class MockEATToken:
    """Mock token payload used for ANV header validation."""

    provider_cert: str
    session_id: str
    authorization_type: str
    attestation_level: str
    timestamp: int
    signature: str


def _serialize_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _signature_for_payload(payload: dict[str, Any]) -> str:
    return hmac.new(SECRET_KEY, _serialize_payload(payload), hashlib.sha256).hexdigest()


def generate_token(
    provider: str = "example-ai-provider.com",
    auth_type: str = "SIGNED_AI",
    level: str = "AI_ATTESTED",
) -> str:
    """Generate a base64-encoded JSON token for the X-ANV-Token header."""

    payload = {
        "provider_cert": provider,
        "session_id": str(uuid.uuid4()),
        "authorization_type": auth_type,
        "attestation_level": level,
        "timestamp": int(time.time()),
    }
    token = MockEATToken(signature=_signature_for_payload(payload), **payload)
    token_json = json.dumps(asdict(token), sort_keys=True, separators=(",", ":"))
    return base64.b64encode(token_json.encode("utf-8")).decode("ascii")


def validate_token(token_str: str) -> MockEATToken | None:
    """Validate a mock token, returning the parsed dataclass on success."""

    try:
        decoded = base64.b64decode(token_str.encode("ascii"), validate=True).decode("utf-8")
        raw_token = json.loads(decoded)
    except (ValueError, TypeError, binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        return None

    required_fields = {
        "provider_cert",
        "session_id",
        "authorization_type",
        "attestation_level",
        "timestamp",
        "signature",
    }
    if not isinstance(raw_token, dict) or not required_fields.issubset(raw_token):
        return None

    timestamp = raw_token.get("timestamp")
    if not isinstance(timestamp, int):
        return None

    signature = raw_token.get("signature")
    if not isinstance(signature, str):
        return None

    payload = {key: raw_token[key] for key in required_fields if key != "signature"}
    if not all(isinstance(payload[key], str) for key in payload if key != "timestamp"):
        return None

    if not hmac.compare_digest(signature, _signature_for_payload(payload)):
        return None

    now = int(time.time())
    if timestamp < now - TOKEN_TTL_SECONDS or timestamp > now + TOKEN_TTL_SECONDS:
        return None

    try:
        return MockEATToken(**raw_token)
    except TypeError:
        return None
