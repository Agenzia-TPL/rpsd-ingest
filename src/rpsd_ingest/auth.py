# SPDX-FileCopyrightText: 2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA
# SPDX-License-Identifier: EUPL-1.2
"""
API key validation for FastAPI requests.
"""

import jwt
from fastapi import Request
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError


def validate_api_key(request: Request, expected_api_key: str | None) -> str | None:
    """
    Validates API key or JWT from Authorization or x-api-key headers.

    Extracts the credential from (in priority order):
    1. Authorization header: "Bearer <value>" or "Token <value>"
    2. x-api-key or X-API-Key header

    If the Bearer value looks like a JWT (three dot-separated parts), a
    structural/claims-only check is performed without signature verification.
    This catches malformed tokens, expired tokens, and missing claims at no
    network cost. The expected_api_key comparison is skipped in this case.

    Args:
        request: FastAPI Request object
        expected_api_key: Expected API key to validate against (plain key path only)

    Returns:
        The raw JWT string if a JWT was accepted, None if a plain API key was accepted.

    Raises:
        PermissionError: If the credential is missing, invalid, expired, or malformed
    """
    api_key = None
    bearer_value = None

    # Try Authorization header first
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if auth_header:
        if auth_header.startswith("Bearer "):
            bearer_value = auth_header.split("Bearer ", 1)[1]
            api_key = bearer_value
        elif auth_header.startswith("Token "):
            api_key = auth_header.split("Token ", 1)[1]

    # Fall back to x-api-key header
    if not api_key:
        api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")

    # JWT path: Bearer value with three dot-separated parts
    if bearer_value is not None and bearer_value.count(".") == 2:
        try:
            jwt.decode(
                bearer_value,
                options={"verify_signature": False, "verify_exp": True},
                algorithms=[],
            )
        except ExpiredSignatureError:
            raise PermissionError("Unauthorized - Token expired")
        except (DecodeError, InvalidTokenError):
            raise PermissionError("Unauthorized - Invalid token")
        return bearer_value

    # Plain API key path
    if not expected_api_key or api_key != expected_api_key:
        raise PermissionError("Unauthorized - Invalid API key")

    return None
