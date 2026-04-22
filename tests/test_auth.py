# SPDX-FileCopyrightText: 2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA
# SPDX-License-Identifier: EUPL-1.2
from types import SimpleNamespace

import pytest

from rpsd_ingest.auth import validate_api_key
from rpsd_ingest.settings import JwtAuthSettings


def _request(headers: dict[str, str]):
    return SimpleNamespace(headers=headers)


def test_plain_api_key_valid_via_x_api_key():
    request = _request({"x-api-key": "dev-api-key"})
    context = validate_api_key(request, "dev-api-key")
    assert context.auth_method == "api_key"
    assert context.jwt_token is None
    assert context.principal_id is None


def test_plain_api_key_invalid():
    request = _request({"x-api-key": "wrong"})
    with pytest.raises(PermissionError, match="Unauthorized - Invalid API key"):
        validate_api_key(request, "dev-api-key")


def test_jwt_enabled_rejects_misconfigured_settings():
    request = _request({"authorization": "Bearer aaa.bbb.ccc"})
    settings = JwtAuthSettings(enabled=True)

    with pytest.raises(PermissionError, match="Unauthorized - JWT auth misconfigured"):
        validate_api_key(request, "dev-api-key", jwt_auth_settings=settings)


def test_jwt_enabled_accepts_verified_token(monkeypatch: pytest.MonkeyPatch):
    token = "aaa.bbb.ccc"
    request = _request({"authorization": f"Bearer {token}"})
    settings = JwtAuthSettings(
        enabled=True,
        issuer_url="http://localhost:19300/realms/rpsd",
        audience="rpsd-ingest",
        jwks_url="http://keycloak:8080/realms/rpsd/protocol/openid-connect/certs",
        algorithms=["RS256"],
    )

    monkeypatch.setattr(
        "rpsd_ingest.auth._decode_and_verify_jwt",
        lambda *_args, **_kwargs: {"azp": "atm-default-prod"},
    )

    context = validate_api_key(request, "dev-api-key", jwt_auth_settings=settings)
    assert context.auth_method == "jwt"
    assert context.jwt_token == token
    assert context.principal_id == "atm-default-prod"


def test_jwt_enabled_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch):
    token = "aaa.bbb.ccc"
    request = _request({"authorization": f"Bearer {token}"})
    settings = JwtAuthSettings(
        enabled=True,
        issuer_url="http://localhost:19300/realms/rpsd",
        audience="rpsd-ingest",
        jwks_url="http://keycloak:8080/realms/rpsd/protocol/openid-connect/certs",
        algorithms=["RS256"],
    )

    def _raise_invalid(*_args, **_kwargs):
        raise PermissionError("Unauthorized - Invalid token")

    monkeypatch.setattr("rpsd_ingest.auth._decode_and_verify_jwt", _raise_invalid)

    with pytest.raises(PermissionError, match="Unauthorized - Invalid token"):
        validate_api_key(request, "dev-api-key", jwt_auth_settings=settings)


def test_jwt_disabled_does_not_accept_jwt_like_bearer():
    request = _request({"authorization": "Bearer aaa.bbb.ccc"})
    settings = JwtAuthSettings(enabled=False)

    with pytest.raises(PermissionError, match="Unauthorized - Invalid API key"):
        validate_api_key(request, "dev-api-key", jwt_auth_settings=settings)


def test_jwt_enabled_rejects_token_without_principal_claim(
    monkeypatch: pytest.MonkeyPatch,
):
    token = "aaa.bbb.ccc"
    request = _request({"authorization": f"Bearer {token}"})
    settings = JwtAuthSettings(
        enabled=True,
        issuer_url="http://localhost:19300/realms/rpsd",
        audience="rpsd-ingest",
        jwks_url="http://keycloak:8080/realms/rpsd/protocol/openid-connect/certs",
        algorithms=["RS256"],
    )

    monkeypatch.setattr(
        "rpsd_ingest.auth._decode_and_verify_jwt",
        lambda *_args, **_kwargs: {"sub": "service-account-sub-only"},
    )

    with pytest.raises(PermissionError, match="Unauthorized - Token principal missing"):
        validate_api_key(request, "dev-api-key", jwt_auth_settings=settings)


def test_jwt_enabled_uses_token_principal_not_request_spoof(
    monkeypatch: pytest.MonkeyPatch,
):
    token = "aaa.bbb.ccc"
    request = _request(
        {
            "authorization": f"Bearer {token}",
            "x-principal-id": "spoofed-principal",
        }
    )
    settings = JwtAuthSettings(
        enabled=True,
        issuer_url="http://localhost:19300/realms/rpsd",
        audience="rpsd-ingest",
        jwks_url="http://keycloak:8080/realms/rpsd/protocol/openid-connect/certs",
        algorithms=["RS256"],
    )

    monkeypatch.setattr(
        "rpsd_ingest.auth._decode_and_verify_jwt",
        lambda *_args, **_kwargs: {"client_id": "trusted-from-token"},
    )

    context = validate_api_key(request, "dev-api-key", jwt_auth_settings=settings)
    assert context.principal_id == "trusted-from-token"
