# SPDX-FileCopyrightText: 2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA
# SPDX-License-Identifier: EUPL-1.2
"""
Pydantic models for the rpsd-config Exchange Agreement API responses.

The ``options`` field in the Config service's FlowProfileSchema is an untyped
dict. The structure here is derived from the validation logic in
``FlowProfile.clean()`` in
``rpsd-config/src/rpsd_config/exchange_agreement/models.py``.
"""

from pydantic import BaseModel


class DataIngestionEntry(BaseModel):
    """Single data-ingestion flow entry for one content type."""

    flow: str
    active: bool
    description: str


class DataRetentionEntry(BaseModel):
    """Single data-retention flow entry for one content category."""

    days: int
    flow: str
    description: str


class FlowProfileOptions(BaseModel):
    """Typed view of FlowProfile.options from the Config service."""

    data_ingestion: dict[str, DataIngestionEntry]
    data_retention: dict[str, DataRetentionEntry]
    planned_master: dict[str, DataIngestionEntry]
    general_profile: str


class FlowProfile(BaseModel):
    """Flow profile metadata and options."""

    code: str
    name: str
    schema_version: str
    is_active: bool
    description: str
    options: FlowProfileOptions


class ContractFlowProfileResponse(BaseModel):
    """Top-level response from the Config flow-profile endpoint.

    Matches ``ContractFlowProfileResponse`` in
    ``rpsd-config/src/rpsd_config/exchange_agreement/api.py``.
    ``flow_profile`` is ``None`` when the contract has no profile assigned.
    """

    contract_code: str
    flow_profile: FlowProfile | None
