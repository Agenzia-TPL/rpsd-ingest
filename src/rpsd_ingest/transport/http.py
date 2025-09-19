import base64
import gzip
import io
import logging
import os
import re
import urllib.request
import urllib.parse
import zipfile

from rpsd_ingest.storage import storage_provider
from rpsd_ingest.config import config


logger = logging.getLogger()


def validate_request(event):
    """
    Validates the incoming request, checking API key and HTTP method.
    Raises an exception if validation fails.
    """
    headers = event.get('headers', {})
    api_key = None
    auth_header = headers.get('authorization') or headers.get('Authorization')
    if auth_header:
        if auth_header.startswith('Bearer '):
            api_key = auth_header.split('Bearer ')[1]
        elif auth_header.startswith('Token '):
            api_key = auth_header.split('Token ')[1]

    if not api_key:
        api_key = headers.get('x-api-key') or headers.get('X-API-Key')

    expected_key = config['api_key']

    if not expected_key or api_key != expected_key:
        raise PermissionError('Unauthorized - Invalid API key')

    method = event.get('httpMethod') or event.get(
        'requestContext', {}).get('http', {}).get('method')
    if method != 'POST':
        raise ValueError('Method not allowed')


def sanitize_value(value):
    """
    Sanitizes a value to prevent malicious usage.
    Allows alphanumeric characters, dashes, and underscores.
    """
    if not value:
        return None
    # Remove any characters that are not alphanumeric, a dash, or an underscore
    return re.sub(r'[^a-zA-Z0-9_-]', '', value)


def route_request(event):
    """
    Routes the request to the appropriate handler based on headers or body content.
    """
    headers = event.get('headers', {})
    query_params = event.get('queryStringParameters') or {}
    content_type = headers.get(
        'content-type') or headers.get('Content-Type', '')
    is_attachment = content_type.startswith('multipart/form-data')

    where_header = headers.get(
        'x-raps-ingest_where') or headers.get('X-RAPS-INGEST_WHERE')
    where_query = query_params.get('where')

    what_header = headers.get(
        'x-raps-ingest_what') or headers.get('X-RAPS-INGEST_WHAT')
    what_query = query_params.get('what')

    who_header = headers.get(
        'x-raps-ingest_who') or headers.get('X-RAPS-INGEST_WHO')
    who_query = query_params.get('who')

    if where_header and where_query:
        raise ValueError(
            "Cannot specify 'where' in both query parameter and header.")

    if what_header and what_query:
        raise ValueError(
            "Cannot specify 'what' in both query parameter and header.")

    if who_header and who_query:
        raise ValueError(
            "Cannot specify 'who' in both query parameter and header.")

    what = what_header or what_query
    if not what:
        raise ValueError("Must provide 'what' in query parameter or header.")

    who = who_header or who_query
    if not who:
        raise ValueError("Must provide 'who' in query parameter or header.")

    sanitized_what = sanitize_value(what)
    if not sanitized_what:
        raise ValueError("Invalid 'what' value provided.")

    sanitized_who = sanitize_value(who)
    if not sanitized_who:
        raise ValueError("Invalid 'who' value provided.")

    where_url = where_header or where_query
    body = event.get('body')

    # Prioritize attachment if content-type indicates multipart/form-data
    if is_attachment:
        if where_url:
            raise ValueError(
                'Cannot provide both attachment and a where clause')
        return handle_attachment(event, who=sanitized_who, what=sanitized_what)

    # If not an attachment, then check for where_url or body
    provided_options = [bool(where_url), bool(body)]
    if provided_options.count(True) != 1:
        raise ValueError(
            'Must provide exactly one of: a where clause or a request body')

    if where_url:
        return handle_url(where_url, who=sanitized_who, what=sanitized_what)
    elif body:
        return handle_body(event, who=sanitized_who, what=sanitized_what)
    else:
        # This case should not be reached due to the check above, but is kept for safety
        raise ValueError(
            'Must provide an attachment, an X-RAPS-INGEST_WHERE header, or a request body')


def parse_multipart_data(body, boundary):
    """
    Parses multipart/form-data body.
    Returns file content, filename, and content type.
    """
    try:
        parts = body.split(b'--' + boundary.encode())
        for part in parts:
            if b'Content-Disposition' in part:
                headers, content = part.split(b'\r\n\r\n', 1)
                headers = headers.decode()

                filename = None
                content_type = None

                if 'filename=' in headers:
                    filename = headers.split('filename="')[1].split('"')[0]

                if 'Content-Type:' in headers:
                    content_type = headers.split(
                        'Content-Type: ')[1].split('\r\n')[0]

                if filename:
                    return content.rstrip(b'\r\n--'), filename, content_type

        return None, None, None
    except Exception as e:
        logger.error(f"Error parsing multipart data: {str(e)}")
        return None, None, None


def decompress_content(content, filename):
    """
    Decompress content - supports GZIP and ZIP
    """
    try:
        # Check if it's GZIP (magic bytes or filename)
        if content.startswith(b'\x1f\x8b') or (filename and filename.endswith('.gz')):
            return gzip.decompress(content)

        # Check if it's ZIP
        elif filename and filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_file:
                # Get first file in zip
                files = zip_file.namelist()
                if files:
                    return zip_file.read(files[0])

        # Not compressed, return as-is
        return content

    except Exception as e:
        raise Exception(f"Failed to decompress: {str(e)}")


def handle_attachment(event, who=None, what=None):
    """
    Handles multipart/form-data attachment
    """
    headers = event.get('headers', {})
    content_type_header = headers.get(
        'content-type') or headers.get('Content-Type', '')
    boundary = content_type_header.split('boundary=')[1].strip()

    body = event.get('body', '')
    if event.get('isBase64Encoded', False):
        body = base64.b64decode(body)
    elif isinstance(body, str):
        body = body.encode('utf-8')

    file_content, filename, content_type = parse_multipart_data(body, boundary)

    if not file_content:
        raise Exception('No file found in attachment')

    decompressed_content = decompress_content(file_content, filename)
    return storage_provider.save(decompressed_content, filename, content_type or 'application/xml', who=who, what=what)


def handle_body(event, who=None, what=None):
    """
    Handles ingestion from the request body.
    """
    headers = event.get('headers', {})
    content_type = headers.get(
        'content-type') or headers.get('Content-Type', 'application/octet-stream')

    body = event.get('body', '')
    is_base64_encoded = event.get('isBase64Encoded', False)

    if is_base64_encoded:
        file_content = base64.b64decode(body)
    else:
        # If not base64, it could be plain text or binary string
        file_content = body.encode('utf-8') if isinstance(body, str) else body

    # The filename is not available directly from the body, so we generate one
    filename = "body_content"

    # Check for content-encoding header for compression
    content_encoding = headers.get(
        'content-encoding') or headers.get('Content-Encoding')
    if content_encoding == 'gzip':
        decompressed_content = gzip.decompress(file_content)
    else:
        # Attempt to decompress based on magic bytes if not specified
        decompressed_content = decompress_content(file_content, None)

    return storage_provider.save(decompressed_content, filename, content_type, who=who, what=what)


def handle_url(where_url, who=None, what=None):
    """
    Handles ingestion from a URL
    """
    parsed_url = urllib.parse.urlparse(where_url)
    if not all([parsed_url.scheme, parsed_url.netloc]):
        raise ValueError('Invalid URL in X-RAPS-INGEST_WHERE header')

    with urllib.request.urlopen(where_url) as response:
        if response.status == 200:
            file_content = response.read()
            filename = os.path.basename(parsed_url.path) or 'downloaded_file'
            content_type = response.headers.get(
                'Content-Type', 'application/xml')
            return storage_provider.save(file_content, filename, content_type, source_url=where_url, who=who, what=what)
        else:
            raise Exception(
                f'Failed to download from URL: Status {response.status}')
