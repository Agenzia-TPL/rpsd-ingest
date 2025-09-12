# Example project

This is an example repository useful as a template for creating a Python (micro)service using devcointainers and Dapr,
in the context of the Rapsodia project.

Copy it over with a different name and replace all occurrences of __rpsd-ingest__ with the name of the new (micro)service
(i.e.: __rpsd-another__ and __rpsd_another__).

Pay attention to dash "-" and underscore "_". It's an underscore in directory names and a dash otherwise.

## Compose files

Use __docker-compose.yml__ to run all containers for local development (i.e.: from devcontainer.json).
It runs:

    - local project service(s)
    - Dapr sidecar(s) for local service(s)
    - Dapr platform runtime (Placement, Scheduler, State store, etc.).

Use __docker-compose-run.yml__ of another project to run service(s) and Dapr sidecar(s) of the other project,
connected to already running Dapr platform runtime containers.

If needed, use __docker-compose.yml__ to run all containers for Dapr platform runtime (Placement, Scheduler, State store, etc.).

All containers communicates over the same __rpsd-dapr__ Docker Network.

In practice, once a project is opened inside its own devcontainer, 
the Dapr sidecar(s) and an an instance of the Dapr platform runtime are running.

Doing:

    docker compose -f "<ANOTHER_PROJECT> docker-compose-run.yml" up -d

will run service(s) and Daor sidecar(s) of the other project, using the Dapr platform runtime already running inside the local devcontainer.
This way, services developed inside the current project can communicate with services inside the other project.

## Local running

See __.vscode/launch.json__ for examples of debugging services.

To run a service from a terminal inside the local devcontainer (no debugging), use the following:

    uv run <SERVICE_NAME>

where <SERVICE_NAME> is an entry inside the __[project.scripts]__ section of the __pyproject.toml__ file.
