import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from rpsd_ingest.transport.http import validate_request, route_request


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = FastAPI()


@app.post("/ingest")
async def ingest_data(request: Request):
    """
    FastAPI endpoint to ingest compressed XML files.
    """
    try:
        # Construct an event dictionary similar to what AWS Lambda would provide.
        headers = dict(request.headers)
        query_params = dict(request.query_params)
        body = await request.body()

        # Attempt to parse JSON, but fall back to raw body if it fails
        try:
            json_body = await request.json()
        except Exception:
            json_body = None

        event = {
            "headers": headers,
            "queryStringParameters": query_params,
            "body": json_body if json_body is not None else body,
            "isBase64Encoded": False,  # FastAPI handles decoding
            "requestContext": {
                "http": {
                    "method": request.method
                }
            }
        }

        validate_request(event)
        object_id = route_request(event)

        return JSONResponse(
            status_code=201,
            content={
                'success': True,
                'object_id': object_id
            }
        )
    except PermissionError as pe:
        logger.error(f"Permission Error: {str(pe)}")
        raise HTTPException(status_code=401, detail=str(pe))
    except ValueError as ve:
        logger.error(f"Value Error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Internal server error',
                'message': str(e)
            }
        )


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == '__main__':
    main()
