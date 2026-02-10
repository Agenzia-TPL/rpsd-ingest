"""
FastAPI application demonstrating HTTPCarrier with IngestProcessor.

This example shows how to:
- Use HTTPCarrier.receive() to parse incoming messages
- Use IngestProcessor to save content to storage
- Optionally forward to Kafka after storage
- Support both inline (JSON) and outline (headers/query) metadata formats
- Validate API keys
- Configure storage providers (FS or S3) via settings
- Use transformers to enrich message metadata
"""

import hashlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from rpsd_storage import get_storage_provider
from rpsd_transport import get_carrier
from rpsd_transport.carriers.http import HTTPCarrier
from rpsd_transport.exceptions import (
    InvalidMetadataError,
    MissingMetadataError,
    TransportError,
)
from rpsd_transport.processors.ingest import IngestProcessor
from rpsd_transport.settings import TransportSettings
from rpsd_transport.transformers import with_custom_metadata

from rpsd_ingest.auth import validate_api_key
from rpsd_ingest.settings import AppSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize settings and dependencies
settings = AppSettings()
storage_provider = get_storage_provider(settings.storage)
carrier = HTTPCarrier(timeout=30.0)

# Create forward carrier if configured
forward_carrier = None
if settings.forward.carrier:
    forward_settings = TransportSettings(
        carrier=settings.forward.carrier,
        kafka=settings.forward.kafka,
    )
    forward_carrier = get_carrier(forward_settings)
    logger.info(
        "Forward carrier configured: %s -> %s",
        settings.forward.carrier,
        settings.forward.recipient,
    )


# Define metadata enricher for adding processing information
def enrich_ingest_metadata(meta: dict[str, Any], content: bytes) -> dict[str, Any]:
    """Enrich metadata with processing details.

    Adds timestamp, app version, content hash, and size to custom_metadata.
    """
    return {
        **meta,
        "ingested_at": datetime.now(UTC).isoformat(),
        "ingested_by": "fastapi-ingest-app",
        "app_version": "1.0.0",
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "content_size": len(content),
    }


# Define metadata enricher for adding processing information before forwarding
def enrich_forward_metadata(meta: dict[str, Any], content: bytes) -> dict[str, Any]:
    """Enrich metadata with fixed details."""
    return {
        **meta,
        "pre_forward": True,
    }


# Create processor with optional forwarding and metadata enrichment
processor = IngestProcessor(
    storage=storage_provider,
    forward_carrier=forward_carrier,
    forward_recipient=settings.forward.recipient,
    forward_mode=settings.forward.mode,
    pre_save_transform=with_custom_metadata(enrich_ingest_metadata),
    pre_forward_transform=with_custom_metadata(enrich_forward_metadata),
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage forward carrier startup and shutdown."""
    if forward_carrier:
        start_method = getattr(forward_carrier, "start", None)
        if start_method is not None:
            logger.info("Starting forward carrier...")
            await start_method()
            logger.info("Forward carrier started successfully")
    yield
    if forward_carrier:
        stop_method = getattr(forward_carrier, "stop", None)
        if stop_method is not None:
            logger.info("Stopping forward carrier...")
            await stop_method()
            logger.info("Forward carrier stopped successfully")


# Create FastAPI app
app = FastAPI(
    title="RPSD Ingest Example",
    description="Example FastAPI app using HTTPCarrier and IngestProcessor",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Handle HTTP exceptions with a standard error response.

    Customize the response body shape by modifying this handler.
    """
    # To return a custom error body shape, replace the return
    # below with something like:
    # return JSONResponse(
    #     status_code=exc.status_code,
    #     content={
    #         "error": exc.detail,
    #         "message": str(exc.detail),
    #     },
    # )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.post("/ingest")
async def ingest_data(request: Request):
    """
    Receive and store data using HTTPCarrier and IngestProcessor.

    Supports both metadata formats:
    - Inline: JSON body with metadata and content fields
    - Outline: Headers/query params with separate content

    Args:
        request: FastAPI Request object

    Returns:
        JSONResponse with success status and storage details

    Raises:
        401: If API key is invalid
        400: If metadata is missing or invalid
        500: For other errors
    """
    try:
        # Validate API key
        validate_api_key(request, settings.transport.api_key)

        # Receive and parse message via carrier
        message = await carrier.receive(request)

        # Process: resolve heavy content + save to storage
        result = await processor.process_async(message)

        # Build response with storage URL and forward status
        response_data = {
            "success": True,
            "message": "Content received and stored",
            "storage_url": result.storage_url,
            "forwarded": result.forwarded,
            "metadata": {
                "who": message.who,
                "what": message.what,
                "content_type": message.metadata.content_type,
            },
        }

        if result.storage_metadata is not None:
            response_data["metadata"]["object_id"] = result.storage_metadata.object_id
            response_data["metadata"]["content_length"] = (
                result.storage_metadata.content_length
            )
            response_data["metadata"]["content_type"] = (
                result.storage_metadata.content_type
            )

        logger.info(
            "Successfully processed message: who=%s, what=%s, url=%s, forwarded=%s",
            message.who,
            message.what,
            result.storage_url,
            result.forwarded,
        )

        return JSONResponse(status_code=201, content=response_data)

    except PermissionError as e:
        logger.warning("Authentication failed: %s", e)
        raise HTTPException(status_code=401, detail=str(e))

    except (MissingMetadataError, InvalidMetadataError) as e:
        logger.warning("Invalid metadata: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    except TransportError as e:
        logger.error("Transport error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception("Unexpected error processing request")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    forward_recipient = settings.forward.recipient if settings.forward.carrier else None
    return {
        "status": "healthy",
        "storage_provider": settings.storage.provider,
        "forward_carrier": settings.forward.carrier,
        "forward_recipient": forward_recipient,
    }


def run():
    """Entry point for the fastapi-ingest-app command."""
    import uvicorn

    logger.info("Starting RPSD Ingest Example application")
    logger.info(f"Storage provider: {settings.storage.provider}")
    if settings.forward.carrier:
        logger.info(
            f"Forward carrier: {settings.forward.carrier} -> "
            f"{settings.forward.recipient}"
        )
    else:
        logger.info("Forward carrier: disabled")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    run()
