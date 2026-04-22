# rpsd-ingest — Ingest service of the Rapsodia project

**rpsd-ingest** is the data ingestion component of the
[Rapsodia](https://github.com/Agenzia-TPL) platform, a system for collecting,
storing, and processing public transport data on behalf of Italian transport
agencies.

## Description

Rapsodia is a platform that automates the acquisition and processing of
scheduled and real-time public transport data (GTFS, NeTEx, SIRI PT) exchanged
between transport operators and the controlling authority.

rpsd-ingest is the entry point of the pipeline: it exposes an HTTP API that
operators use to submit data files. Upon receipt, the service:

1. Authenticates the request using API key or JWT bearer token.
2. When JWT is used, validates token signature and claims
   (`iss`, `aud`, `exp`) via Keycloak JWKS.
3. Delegates contract-scoped authorization to `rpsd-config` through the
   internal endpoint `/internal/authz/check`.
4. Saves the content to the configured storage backend (filesystem or S3).
5. Optionally forwards a reference to the stored content to a message broker
   (Kafka or RabbitMQ) for downstream processing.
6. Optionally triggers a Prefect Flow deployment to process the data.

The service is built on top of the shared **rpsd-commons** library, which
provides reusable transport, storage, and flow components.

## Repository structure

```
rpsd-ingest/
├── src/
│   └── rpsd_ingest/
│       ├── main.py                    # FastAPI application and endpoints
│       ├── auth.py                    # API key/JWT validation
│       ├── settings.py                # Pydantic-settings configuration
│       └── models/
│           └── exchange_agreement.py  # API response models for rpsd-config
├── tests/                             # Test suite (pytest)
├── Dockerfile                         # Container image definition
├── docker-compose.yml                 # Local development orchestration
├── entrypoint.sh                      # Container entrypoint
├── pyproject.toml                     # Project metadata and dependencies
├── .env.development                   # Development environment defaults
└── .env.production                    # Production environment template
```

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.13+ |
| [uv](https://docs.astral.sh/uv/) | latest |
| rpsd-commons | checked out alongside this repo (see below) |
| Kafka or RabbitMQ | optional — required only when forwarding is enabled |
| Prefect | optional — required only when flow invocation is enabled |
| AWS S3 or compatible | optional — required only when `STORAGE__PROVIDER=s3` |

rpsd-commons must be checked out as a sibling directory:

```
parent/
├── rpsd-commons/   # provides rpsd-transport, rpsd-storage, rpsd-flow
└── rpsd-ingest/    # this repository
```

## Installation

### Development environment

```bash
# Clone the repositories side by side
git clone https://github.com/Agenzia-TPL/rpsd-commons.git
git clone https://github.com/Agenzia-TPL/rpsd-ingest.git

cd rpsd-ingest

# Install all dependencies (including rpsd-commons packages as editable installs)
uv sync

# Copy the development defaults
cp .env.development .env

# Start the service (listens on port 8000)
uv run server
```

### Docker

```bash
docker compose up
```

The service is reachable at `http://localhost:20000` (mapped from container
port 8000 via the `EXTERNAL_PORT` setting).

### Production

Build and run the container image:

```bash
docker build -t rpsd-ingest .
docker run --env-file .env.production -p 8000:8000 rpsd-ingest
```

All configuration is supplied through environment variables (see below).

## Configuration

Configuration is loaded from environment variables. Copy `.env.development` to
`.env` and adjust values for your environment.

| Variable | Default | Description |
|---|---|---|
| `EXTERNAL_SCHEME` | `http` | Scheme reported in external URLs |
| `EXTERNAL_HOST` | `localhost` | Hostname reported in external URLs |
| `EXTERNAL_PORT` | `20000` | Port reported in external URLs |
| `TRANSPORT__API_KEY` | *(required)* | API key for request authentication |
| `STORAGE__PROVIDER` | `fs` | Storage backend: `fs` or `s3` |
| `STORAGE__COMPARE_BEFORE_SAVE` | `true` | Skip saving identical content |
| `STORAGE__FS__BASE_PATH` | `/tmp/rpsd-storage` | Filesystem storage root |
| `STORAGE__S3__BUCKET_NAME` | — | S3 bucket name (when `PROVIDER=s3`) |
| `FORWARD__CARRIER` | — | Forwarding broker: `kafka` or `rabbitmq` |
| `FORWARD__RECIPIENT` | — | Kafka topic or RabbitMQ queue |
| `FORWARD__MODE` | `fatheavy` | `fatheavy` (URL ref) or `slimfast` (inline) |
| `FORWARD__KAFKA__BOOTSTRAP_SERVERS` | — | Kafka broker address(es) |
| `FORWARD__RABBITMQ__URL` | — | RabbitMQ connection URL |
| `FLOW__DEPLOYMENT` | — | Prefect deployment (`flow/deployment`) |
| `FLOW__TIMEOUT` | `0` | `0` = fire-and-forget; positive = wait seconds |
| `PREFECT_API_URL` | — | Prefect API URL (required when flow enabled) |
| `EXCHANGE_AGREEMENT__TOKEN_URL` | — | Upstream token endpoint used by `/token` proxy |
| `EXCHANGE_AGREEMENT__FLOW_PROFILE_URL` | — | rpsd-config contract API URL template |
| `JWT_AUTH__ENABLED` | `false` | Enable strict JWT validation for bearer tokens |
| `JWT_AUTH__ISSUER_URL` | — | Expected token issuer (`iss`) |
| `JWT_AUTH__AUDIENCE` | — | Expected token audience (`aud`) for ingest |
| `JWT_AUTH__JWKS_URL` | — | JWKS URL used for signature verification |
| `CONFIG_AUTHZ__URL` | — | Internal authz endpoint in `rpsd-config` |
| `CONFIG_AUTHZ__TOKEN_URL` | — | Token endpoint for ingest→config service account |
| `CONFIG_AUTHZ__CLIENT_ID` | — | Service client id for ingest→config |
| `CONFIG_AUTHZ__CLIENT_SECRET` | — | Service client secret for ingest→config |
| `CONFIG_AUTHZ__AUDIENCE` | — | Audience requested for ingest→config token |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

See `.env.development` for full documentation of every variable.

## API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/token` | Proxy OAuth2 `client_credentials` token request |
| `POST` | `/ingest` | Submit a data file for ingestion |
| `GET` | `/health` | Service health check |

Authentication modes:

1. API key mode (legacy/compatibility): `Authorization: Bearer <api-key>` or
   `X-API-Key: <api-key>`.
2. JWT mode (recommended for M2M): `Authorization: Bearer <jwt>`, with strict
   validation and internal contract-scoped authz check.

`POST /token` accepts only `grant_type=client_credentials`.

## Running tests

```bash
uv run pytest
```

## Project status

**Beta.** The service is deployed in a controlled environment and under active
development. The HTTP API and configuration interface may change between minor
versions.

Known limitations:

- Actual Prefect Flow invocation after ingestion is partially implemented;
  flow routing from rpsd-config is functional, but flow execution is not yet
  triggered in all cases.

## Copyright and licence

Copyright © 2026
AGENZIA TPL BACINO CITTA' METROPOLITANA MILANO, MONZA E BRIANZA, LODI, PAVIA

This software is released under the
[European Union Public Licence v. 1.2 (EUPL-1.2)](LICENSE).

## Maintainer

Maintained by **Agenzia TPL**.
Bug reports and feature requests: [GitHub Issues](https://github.com/Agenzia-TPL/rpsd-ingest/issues).
