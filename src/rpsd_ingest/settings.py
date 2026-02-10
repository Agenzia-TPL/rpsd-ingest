"""
Unified application settings combining transport and storage configuration.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rpsd_storage.settings import StorageSettings
from rpsd_transport.settings import ForwardSettings, TransportSettings


class AppSettings(BaseSettings):
    """
    Unified application settings.

    Configuration via environment variables:
        APP__TRANSPORT__API_KEY=secret123
        APP__STORAGE__PROVIDER=fs
        APP__STORAGE__FS__BASE_PATH=/tmp/storage
        APP__STORAGE__S3__BUCKET_NAME=my-bucket
        APP__FORWARD__CARRIER=kafka
        APP__FORWARD__RECIPIENT=enriched-events
        APP__FORWARD__MODE=fatheavy
        APP__FORWARD__KAFKA__BOOTSTRAP_SERVERS=host.docker.internal:9092
    """

    model_config = SettingsConfigDict(
        env_prefix="APP__",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    transport: TransportSettings = TransportSettings()
    storage: StorageSettings = StorageSettings()
    forward: ForwardSettings = Field(default_factory=ForwardSettings)
