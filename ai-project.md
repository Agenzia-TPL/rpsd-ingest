# AI Project analysis

## Name

Rapsodia Ingest

## Overview

Ingest component of the Rapsodia project.

Uses packages from the rpsd-commons component:
- rpsd-transport
- rpsd-storage
- rpsd-flow

It's heavily inspired by its **FastAPI Ingest Example**. 

## Retrieve Flow configurations from Config

In main.oy method resolve_flow_deployment should decide which Prefect Flow to invoke to process the received file.
To that avail it has to call the Config service upon the URL specified by:

    settings.exchange_agreement.flow_profile_url

This variable is retrieved from env and is something like:

    EXCHANGE_AGREEMENT__FLOW_PROFILE_URL=http://rpsd-config:8000/exchange_agreement/api/v1/contracts/{contract_code}/flow-profile

where "contract_code" is the "who" value of the received message.

To protect from injections a safetize method could be used, such as:

import re
from urllib.parse import quote

CONTRACT_CODE_RE = re.compile(r"^[A-Z]+-\d+$")  # or whatever the actual pattern is

def flow_profile_url(contract_code: str) -> str:
    if not CONTRACT_CODE_RE.match(contract_code):
        raise ValueError(f"Invalid contract code: {contract_code}")
    return settings.exchange_agreement.flow_profile_url.format(
        contract_code=quote(contract_code, safe="")
    )

The call to rhis API must be made before line 252 of main.py, that is, right after the message is received, or even before the message is retrieved at all, because all that's needed is the "who" value.
If the API call returns an error, for example an error of unknown contract (404), the received message must be refused.
If, instead, it returns a success, it will be a response such as:
{
  "contract_code": "CTR-001",
  "flow_profile": {
    "code": "standard-it-v1",
    "name": "Standard IT v1",
    "schema_version": "1.0",
    "is_active": true,
    "description": "Profilo standard per import e retention base.",
    "options": {
      "data_ingestion": {
        "gtfs": {
          "flow": "plnd-002",
          "active": false,
          "description": "Carica GTFS con step di trasformazione."
        },
        "netex": {
          "flow": "plnd-001",
          "active": true,
          "description": "Carica il programmato da NeTEx."
        },
        "siri_pt": {
          "flow": "rltm-spt-001",
          "active": true,
          "description": "Acquisisce real time SIRI PT."
        }
      },
      "data_retention": {
        "plnd": {
          "days": 100,
          "flow": "plnd-clr-001",
          "description": "Pulizia storico programmato."
        },
        "rltm": {
          "days": 3,
          "flow": "rltm-clr-001",
          "description": "Pulizia storico real time."
        }
      },
      "planned_master": {
        "gtfs": {
          "flow": "master-002",
          "active": true,
          "description": "Importa GTFS e lo converte in NeTEx."
        },
        "netex": {
          "flow": "master-001",
          "active": true,
          "description": "Carica il programmato master in formato NeTEx."
        }
      },
      "general_profile": "it"
    }
  }
}

Here, we're interested in values inside "flow_profile"/"options"/"data_ingestion", but this path is not strictly defined yet...
Then, we have to look for a key corresponding to the "what" value of the received message, that should be one of the listed values, such as: "gtfs", "netex", "siri_pt", etc.
If the "what" value is not listed, the message must be rejected, otherwise the "flow" field contains the name of the Prefect Flow to invoke.
As a start, we just have to magae the call to Config, the check of the "who" and "what" values, we'll implement the actual invocation later.
