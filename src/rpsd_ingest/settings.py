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
