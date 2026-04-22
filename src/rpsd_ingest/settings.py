# SPDX-FileCopyrightText: 2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA
# SPDX-License-Identifier: EUPL-1.2
"""
Unified application settings combining transport and storage configuration.
"""

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rpsd_storage.settings import StorageSettings
from rpsd_transport.settings import (
    ForwardSettings,
    KafkaSettings,
    RabbitMQSettings,
    TransportSettings,
)


class ExchangeAgreementSettings(BaseModel):
    """Settings for rpsd-config Exchange Agreement API integration.

    URL templates may contain {placeholders} for dynamic path segments.
    Always validate and URL-encode dynamic values before substitution.

    Environment variables:
    - EXCHANGE_AGREEMENT__TOKEN_URL=http://idp:8080/realms/rpsd/protocol/openid-connect/token
    - EXCHANGE_AGREEMENT__FLOW_PROFILE_URL=http://rpsd-config:8000/exchange_agreement/api/v1/contracts/{contract_code}/flow-profile
    """

    token_url: str | None = None
    flow_profile_url: str | None = None


class FlowInvokeSettings(BaseModel):
    """Settings for optional Prefect Flow invocation after ingest.

    When ``deployment`` is set, the app invokes a Prefect Flow
    after saving to storage. When ``None`` (default), flow
    invocation is disabled.

    Environment variables:
    - FLOW__DEPLOYMENT=ingest-flow/ingest-deployment
    - FLOW__TIMEOUT=0      # 0 = fire-and-forget (default)
    - FLOW__TIMEOUT=60.0   # wait up to 60 s for the flow to finish
    """

    deployment: str | None = None
    timeout: float | None = 0


class ConsumerSettings(BaseModel):
    """Consumer settings for the message broker consumer (consumer.py).

    Separate from ForwardSettings to demonstrate proper separation of
    concerns: publishing vs. consuming are different responsibilities.

    Environment variables:
    - CONSUMER__CARRIER=kafka
    - CONSUMER__TOPIC=enriched-events
    - CONSUMER__KAFKA__BOOTSTRAP_SERVERS=...
    - CONSUMER__KAFKA__GROUP_ID=demo-consumer
    - CONSUMER__RABBITMQ__URL=...
    """

    carrier: Literal["kafka", "rabbitmq"] | None = None
    topic: str | None = None
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)


class JwtAuthSettings(BaseModel):
    """JWT validation settings for bearer-token ingest authentication.

    Environment variables:
    - JWT_AUTH__ENABLED=true
    - JWT_AUTH__ISSUER_URL=http://keycloak:8080/realms/rpsd
    - JWT_AUTH__AUDIENCE=rpsd-ingest
    - JWT_AUTH__JWKS_URL=http://keycloak:8080/realms/rpsd/protocol/openid-connect/certs
    - JWT_AUTH__ALGORITHMS=[\"RS256\"]
    - JWT_AUTH__LEEWAY_SECONDS=0
    """

    enabled: bool = False
    issuer_url: str | None = None
    audience: str | None = None
    jwks_url: str | None = None
    algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    leeway_seconds: int = 0


class ConfigAuthzSettings(BaseModel):
    """Settings for internal authz check calls from ingest to rpsd-config.

    Environment variables:
    - CONFIG_AUTHZ__URL=http://rpsd-config:8000/internal/authz/check
    - CONFIG_AUTHZ__TIMEOUT_SECONDS=5
    - CONFIG_AUTHZ__VERIFY_TLS=true
    - CONFIG_AUTHZ__TOKEN_URL=http://keycloak:8080/realms/rpsd/protocol/openid-connect/token
    - CONFIG_AUTHZ__CLIENT_ID=rpsd-ingest
    - CONFIG_AUTHZ__CLIENT_SECRET=...
    - CONFIG_AUTHZ__AUDIENCE=rpsd-config-internal
    """

    url: str | None = None
    timeout_seconds: float = 5.0
    verify_tls: bool = True
    token_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    audience: str | None = None


class AppSettings(BaseSettings):
    """
    Unified application settings.

    Configuration via environment variables:
        EXTERNAL_SCHEME=http
        EXTERNAL_HOST=localhost
        EXTERNAL_PORT=20000
        TRANSPORT__API_KEY=secret123
        STORAGE__PROVIDER=fs
        STORAGE__FS__BASE_PATH=/tmp/storage
        STORAGE__S3__BUCKET_NAME=my-bucket
        FORWARD__CARRIER=kafka
        FORWARD__RECIPIENT=enriched-events
        FORWARD__MODE=fatheavy
        FORWARD__KAFKA__BOOTSTRAP_SERVERS=host.docker.internal:9092
        CONSUMER__CARRIER=kafka
        CONSUMER__TOPIC=enriched-events
        CONSUMER__KAFKA__GROUP_ID=demo-consumer
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # External access configuration
    EXTERNAL_SCHEME: str = Field(default="http")
    EXTERNAL_HOST: str = Field(default="localhost")
    EXTERNAL_PORT: int = Field(default=20000)

    # Internal application settings
    transport: TransportSettings = TransportSettings()
    storage: StorageSettings = StorageSettings()
    forward: ForwardSettings = Field(default_factory=ForwardSettings)
    flow: FlowInvokeSettings = Field(default_factory=FlowInvokeSettings)
    consumer: ConsumerSettings = Field(default_factory=ConsumerSettings)
    exchange_agreement: ExchangeAgreementSettings = Field(
        default_factory=ExchangeAgreementSettings
    )
    jwt_auth: JwtAuthSettings = Field(default_factory=JwtAuthSettings)
    config_authz: ConfigAuthzSettings = Field(default_factory=ConfigAuthzSettings)


class ProjectSettings(AppSettings):
    """Top-level settings with env file configuration.

    Use this class when running the application (reads from .env file).
    Use AppSettings directly for testing or programmatic configuration.
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
