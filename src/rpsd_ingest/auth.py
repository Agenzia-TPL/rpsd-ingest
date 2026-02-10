"""
API key validation for FastAPI requests.
"""

from fastapi import Request


def validate_api_key(request: Request, expected_api_key: str | None) -> None:
    """
    Validates API key from Authorization or x-api-key headers.

    Extracts API key from (in priority order):
    1. Authorization header: "Bearer <key>" or "Token <key>"
    2. x-api-key or X-API-Key header

    Args:
        request: FastAPI Request object
        expected_api_key: Expected API key to validate against

    Raises:
        PermissionError: If API key is missing or invalid
    """
    api_key = None

    # Try Authorization header first
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if auth_header:
        if auth_header.startswith("Bearer "):
            api_key = auth_header.split("Bearer ", 1)[1]
        elif auth_header.startswith("Token "):
            api_key = auth_header.split("Token ", 1)[1]

    # Fall back to x-api-key header
    if not api_key:
        api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")

    # Validate
    if not expected_api_key or api_key != expected_api_key:
        raise PermissionError("Unauthorized - Invalid API key")
