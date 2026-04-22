# SPDX-FileCopyrightText: 2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA
# SPDX-License-Identifier: EUPL-1.2
"""
API key validation for FastAPI requests.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Request
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWKClient
from jwt.exceptions import PyJWKClientError


def _is_jwt_like(value: str) -> bool:
    return value.count(".") == 2


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


@dataclass(frozen=True)
class AuthContext:
    jwt_token: str | None
    principal_id: str | None
    auth_method: str


def _decode_and_verify_jwt(token: str, jwt_auth_settings: Any) -> dict[str, Any]:
    issuer = getattr(jwt_auth_settings, "issuer_url", None)
    audience = getattr(jwt_auth_settings, "audience", None)
    jwks_url = getattr(jwt_auth_settings, "jwks_url", None)
    algorithms = getattr(jwt_auth_settings, "algorithms", None) or ["RS256"]
    leeway_seconds = getattr(jwt_auth_settings, "leeway_seconds", 0) or 0

    if not issuer or not audience or not jwks_url:
        raise PermissionError("Unauthorized - JWT auth misconfigured")

    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key=signing_key,
            algorithms=algorithms,
            issuer=issuer,
            audience=audience,
            leeway=leeway_seconds,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
        return claims
    except ExpiredSignatureError:
        raise PermissionError("Unauthorized - Token expired")
    except (PyJWKClientError, InvalidTokenError):
        raise PermissionError("Unauthorized - Invalid token")


def validate_api_key(
    request: Request,
    expected_api_key: str | None,
    *,
    jwt_auth_settings: Any = None,
) -> AuthContext:
    """
    Validates API key or JWT from Authorization or x-api-key headers.

    Extracts the credential from (in priority order):
    1. Authorization header: "Bearer <value>" or "Token <value>"
    2. x-api-key or X-API-Key header

    If the Bearer value looks like a JWT (three dot-separated parts) and JWT
    auth is enabled, the token is cryptographically validated (JWKS signature,
    issuer, audience, expiration).

    Args:
        request: FastAPI Request object
        expected_api_key: Expected API key to validate against (plain key path only)

    Returns:
        AuthContext with token + canonical principal when JWT is accepted.

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

    # JWT path: Bearer value with three dot-separated parts.
    if bearer_value is not None and _is_jwt_like(bearer_value):
        if jwt_auth_settings is not None and getattr(jwt_auth_settings, "enabled", False):
            claims = _decode_and_verify_jwt(bearer_value, jwt_auth_settings)
            principal_id = claims.get("azp") or claims.get("client_id")
            if not isinstance(principal_id, str) or not principal_id.strip():
                raise PermissionError("Unauthorized - Token principal missing")
            return AuthContext(
                jwt_token=bearer_value,
                principal_id=principal_id.strip(),
                auth_method="jwt",
            )

    # Plain API key path
    if not expected_api_key or api_key != expected_api_key:
        raise PermissionError("Unauthorized - Invalid API key")

    return AuthContext(jwt_token=None, principal_id=None, auth_method="api_key")
