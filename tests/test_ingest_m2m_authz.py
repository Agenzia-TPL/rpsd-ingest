# SPDX-FileCopyrightText: 2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA
# SPDX-License-Identifier: EUPL-1.2
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from rpsd_ingest.auth import AuthContext
from rpsd_ingest.main import AuthorizationDeniedError
from rpsd_ingest.main import ingest_data
from rpsd_ingest.main import settings


def _request(headers: dict[str, str] | None = None):
    return SimpleNamespace(headers=headers or {})


def _message(*, who: str = "CTR-001", what: str = "netex"):
    return SimpleNamespace(
        who=who,
        what=what,
        metadata=SimpleNamespace(content_type="application/xml"),
    )


def _process_result(message):
    return SimpleNamespace(
        deduplicated=False,
        forwarded=False,
        message=message,
        storage_metadata=None,
        storage_url="/tmp/rpsd-storage/CTR-001/netex/blob.xml",
    )


class TestIngestM2MAuthz(unittest.IsolatedAsyncioTestCase):
    async def test_ingest_returns_401_when_token_is_invalid(self):
        request = _request({"authorization": "Bearer bad.jwt.token"})
        with patch(
            "rpsd_ingest.main.validate_api_key",
            side_effect=PermissionError("Unauthorized - Invalid token"),
        ):
            with self.assertRaises(HTTPException) as raised:
                await ingest_data(request)
        self.assertEqual(raised.exception.status_code, 401)
        self.assertIn("Invalid token", str(raised.exception.detail))

    async def test_ingest_returns_403_when_authz_grant_is_missing(self):
        request = _request({"authorization": "Bearer valid.jwt.token"})
        message = _message()
        with (
            patch(
                "rpsd_ingest.main.validate_api_key",
                return_value=AuthContext(
                    jwt_token="valid.jwt.token",
                    principal_id="atm-default-prod",
                    auth_method="jwt",
                ),
            ),
            patch("rpsd_ingest.main.carrier.receive", new=AsyncMock(return_value=message)),
            patch(
                "rpsd_ingest.main._enforce_internal_contract_authz",
                new=AsyncMock(
                    side_effect=AuthorizationDeniedError(
                        "Forbidden - authz denied (grant-missing)"
                    )
                ),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await ingest_data(request)
        self.assertEqual(raised.exception.status_code, 403)
        self.assertIn("grant-missing", str(raised.exception.detail))

    async def test_ingest_returns_403_when_contract_is_inactive(self):
        request = _request({"authorization": "Bearer valid.jwt.token"})
        message = _message(what="siri")
        with (
            patch(
                "rpsd_ingest.main.validate_api_key",
                return_value=AuthContext(
                    jwt_token="valid.jwt.token",
                    principal_id="atm-default-prod",
                    auth_method="jwt",
                ),
            ),
            patch("rpsd_ingest.main.carrier.receive", new=AsyncMock(return_value=message)),
            patch(
                "rpsd_ingest.main._enforce_internal_contract_authz",
                new=AsyncMock(
                    side_effect=AuthorizationDeniedError(
                        "Forbidden - authz denied (contract-inactive)"
                    )
                ),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await ingest_data(request)
        self.assertEqual(raised.exception.status_code, 403)
        self.assertIn("contract-inactive", str(raised.exception.detail))

    async def test_ingest_returns_201_when_authz_allows_request(self):
        request = _request({"authorization": "Bearer valid.jwt.token"})
        message = _message()
        result = _process_result(message)
        with (
            patch(
                "rpsd_ingest.main.validate_api_key",
                return_value=AuthContext(
                    jwt_token="valid.jwt.token",
                    principal_id="atm-default-prod",
                    auth_method="jwt",
                ),
            ),
            patch("rpsd_ingest.main.carrier.receive", new=AsyncMock(return_value=message)),
            patch(
                "rpsd_ingest.main._enforce_internal_contract_authz",
                new=AsyncMock(return_value=None),
            ) as authz_mock,
            patch(
                "rpsd_ingest.main.processor.process_async",
                new=AsyncMock(return_value=result),
            ),
            patch.object(settings.exchange_agreement, "flow_profile_url", None),
            patch.object(settings.flow, "deployment", None),
        ):
            response = await ingest_data(request)
        self.assertEqual(response.status_code, 201)
        payload = json.loads(response.body.decode("utf-8"))
        self.assertTrue(payload["success"])
        self.assertEqual(payload["metadata"]["who"], "CTR-001")
        self.assertEqual(payload["metadata"]["what"], "netex")
        self.assertEqual(payload["metadata"]["content_type"], "application/xml")
        authz_mock.assert_awaited_once_with(
            principal_id="atm-default-prod",
            contract_code="CTR-001",
            data_category="netex",
        )

