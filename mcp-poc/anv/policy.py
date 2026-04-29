"""ANV policy and authorization type definitions."""

from enum import Enum


class ANVPolicy(Enum):
    """ANV enforcement modes for the PoC."""

    WARN = "warn"
    REQUIRE = "require"


class AuthorizationType(Enum):
    """Authorization classes visible to the MCP server."""

    SIGNED_AI = "SIGNED_AI"
    SIGNED_HUMAN = "SIGNED_HUMAN"
    UNSIGNED = "UNSIGNED"
