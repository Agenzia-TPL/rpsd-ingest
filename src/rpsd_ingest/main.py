# SPDX-FileCopyrightText: 2026 AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA
# SPDX-License-Identifier: EUPL-1.2
"""
FastAPI application demonstrating HTTPCarrier with IngestProcessor.

This example shows how to:
- Use HTTPCarrier.receive() to parse incoming messages
- Use IngestProcessor to save content to storage
- Optionally forward to Kafka/RabbitMQ after storage
- Optionally invoke a Prefect Flow after storage
- Support both inline (JSON) and outline (headers/query) metadata formats
- Validate API keys
- Configure storage providers (FS or S3) via settings
- Use transformers to enrich message metadata
"""

import hashlib
import logging
import os
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx
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
from rpsd_ingest.models.exchange_agreement import ContractFlowProfileResponse
from rpsd_ingest.settings import ProjectSettings

_CONTRACT_CODE_RE = re.compile(r"^[A-Z]+-\d+$")

# Configure the module logger directly — never touch the root logger.
# basicConfig and root-logger setup are no-ops when uvicorn has already
# configured logging, so we own our handler explicitly.  propagate=False
# prevents double-printing when a root handler also exists (e.g. uvicorn's).
_log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(_log_level)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(_handler)
    logger.propagate = False

# Initialize settings and dependencies
settings = ProjectSettings()
storage_provider = get_storage_provider(settings.storage)
carrier = HTTPCarrier(timeout=30)

# Create forward carrier if configured
forward_carrier = None
if settings.forward.carrier:
    forward_settings = TransportSettings(
        carrier=settings.forward.carrier,
        kafka=settings.forward.kafka,
        rabbitmq=settings.forward.rabbitmq,
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


def resolve_compare_before_save(what: str) -> bool | None:
    """Determine per-call deduplication behaviour based on content category.

    In production this would typically be a config mapping or a database
    lookup. Here it is a simple hard-coded classification:

    - True  → deduplicate: periodic reports / snapshots that change rarely.
              Identical re-submissions are silently skipped.
    - False → always write: audit-style records that must never be dropped,
              even when content is identical.
    - None  → defer to the storage provider's instance-level
              compare_before_save setting (the default).

    Args:
        what: Content category identifier from the transport message.

    Returns:
        True, False, or None to pass as compare_before_save to process_async.
    """
    # Deduplicate: skip identical re-submissions for these categories
    dedup_what = {"gtfs"}
    # Always write: every submission must be stored, even if identical
    force_save_what = {"siri"}

    if what in dedup_what:
        return True
    if what in force_save_what:
        return False
    return None  # use instance-level default


async def fetch_flow_profile(who: str, what: str) -> str:
    """Fetch the Prefect flow name for a contract/content-type pair from Config.

    Args:
        who: Contract code (e.g. "CTR-001").
        what: Content category (e.g. "netex", "gtfs", "siri_pt").

    Returns:
        Flow name to use for Prefect invocation.

    Raises:
        ValueError: If who is malformed, contract is unknown (404),
                    what is not listed, or what is inactive.
    """
    if not _CONTRACT_CODE_RE.match(who):
        raise ValueError(f"Invalid contract code: {who!r}")

    flow_profile_url = settings.exchange_agreement.flow_profile_url
    if not flow_profile_url:
        raise ValueError("EXCHANGE_AGREEMENT__FLOW_PROFILE_URL is not configured")

    url = flow_profile_url.format(contract_code=quote(who, safe=""))

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)

    if response.status_code == 404:
        raise ValueError(f"Unknown contract code: {who!r}")

    response.raise_for_status()

    data = ContractFlowProfileResponse.model_validate(response.json())

    if data.flow_profile is None:
        raise ValueError(f"No flow profile assigned for contract {who!r}")

    ingestion = data.flow_profile.options.data_ingestion

    if what not in ingestion:
        raise ValueError(
            f"Content category {what!r} not supported for contract {who!r}"
        )

    entry = ingestion[what]
    if not entry.active:
        raise ValueError(f"Content category {what!r} is inactive for contract {who!r}")

    return entry.flow


def resolve_flow_deployment(
    who: str,
    what: str,
    default_deployment: str,
) -> str:
    """Resolve which Prefect Flow deployment to invoke.

    In production, this function would determine the flow
    based on the who/what combination — e.g. via a lookup
    table, database query, or config mapping.

    For this example, it returns the configured default.

    Args:
        who: The entity identifier from the message.
        what: The content category from the message.
        default_deployment: The configured default deployment
            name (from settings).

    Returns:
        Deployment name in "flow-name/deployment-name" format.
    """
    return default_deployment


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
        t0 = time.perf_counter()
        message = await carrier.receive(request)
        t_receive = time.perf_counter() - t0
        logger.debug("carrier.receive: %.3fs", t_receive)

        # Resolve flow from Config (if configured); reject unknown contracts/categories.
        config_deployment: str | None = None
        if settings.exchange_agreement.flow_profile_url:
            config_deployment = await fetch_flow_profile(message.who, message.what)

        # Resolve deduplication policy server-side from the content category.
        # Clients never control this — the mapping lives here on the server.
        compare_before_save = resolve_compare_before_save(message.what)

        # Process: resolve heavy content + save to storage
        t1 = time.perf_counter()
        result = await processor.process_async(
            message, compare_before_save=compare_before_save
        )
        t_process = time.perf_counter() - t1
        logger.debug("processor.process_async: %.3fs", t_process)

        # Optionally invoke a Prefect Flow deployment
        flow_invoked = False
        t_flow = 0.0
        if settings.flow.deployment and not result.deduplicated:
            try:
                from rpsd_flow import run_flow_async

                deployment = config_deployment or resolve_flow_deployment(
                    message.who,
                    message.what,
                    settings.flow.deployment,
                )

                # Build message with storage URL as 'where'
                # so the flow knows where content was saved.
                flow_message = result.message.model_copy(
                    update={
                        "metadata": (
                            result.message.metadata.model_copy(
                                update={
                                    "where": result.storage_url,
                                }
                            )
                        ),
                    },
                )

                # timeout=0 (default) is fire-and-forget: a single
                # HTTP POST to the Prefect API; returns before the
                # flow even starts. timeout=None waits indefinitely;
                # a positive float waits up to that many seconds.
                t2 = time.perf_counter()
                flow_run = await run_flow_async(
                    deployment,
                    flow_message,
                    settings.flow.timeout,
                )
                t_flow = time.perf_counter() - t2
                flow_invoked = True
                logger.info(
                    "Flow invoked: %s (run id=%s, state=%s)",
                    deployment,
                    flow_run.id,
                    flow_run.state_name,
                )
                logger.debug("run_flow_async: %.3fs", t_flow)
            except Exception as e:
                logger.error(
                    "Failed to invoke flow %s: %s",
                    settings.flow.deployment,
                    e,
                )

        # Build response
        response_data = {
            "success": True,
            "message": "Content received and stored",
            "deduplicated": result.deduplicated,
            "forwarded": result.forwarded,
            "flow_invoked": flow_invoked,
            "metadata": {
                "who": message.who,
                "what": message.what,
                "content_type": message.metadata.content_type,
            },
            "storage": (
                result.storage_metadata.model_dump()
                if result.storage_metadata
                else None
            ),
        }

        t_total = time.perf_counter() - t0
        logger.info(
            "Successfully processed message: "
            "who=%s, what=%s, url=%s, "
            "deduplicated=%s, forwarded=%s, flow_invoked=%s | "
            "timing: receive=%.3fs process=%.3fs flow=%.3fs"
            " total=%.3fs",
            message.who,
            message.what,
            result.storage_url,
            result.deduplicated,
            result.forwarded,
            flow_invoked,
            t_receive,
            t_process,
            t_flow,
            t_total,
        )

        return JSONResponse(status_code=201, content=response_data)

    except ValueError as e:
        logger.warning("Message rejected: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

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
        "flow_deployment": settings.flow.deployment,
    }


def run():
    """Entry point for the fastapi-ingest-app command."""
    import uvicorn

    logger.info("Starting RPSD Ingest Example application")
    logger.info("Storage provider: %s", settings.storage.provider)
    if settings.forward.carrier:
        logger.info(
            "Forward carrier: %s -> %s",
            settings.forward.carrier,
            settings.forward.recipient,
        )
    else:
        logger.info("Forward carrier: disabled")
    if settings.flow.deployment:
        logger.info(
            "Flow invocation: %s (timeout=%s)",
            settings.flow.deployment,
            settings.flow.timeout,
        )
    else:
        logger.info("Flow invocation: disabled")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    run()
