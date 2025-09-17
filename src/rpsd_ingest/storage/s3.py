import os
import uuid
from datetime import datetime, timezone
import boto3
import logging

logger = logging.getLogger()

# Set up AWS session
# NOOO!!! Simply create the client, it will get an IAM role automatically!!!
#session = boto3.Session(
#    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
#    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
#    aws_session_token=os.environ.get('AWS_SESSION_TOKEN'),
#    region_name=os.environ.get('AWS_REGION')
#)
#
#s3_client = session.client('s3')

s3_client = boto3.client('s3')

def save_to_s3(content, filename, content_type='application/xml', source_url=None, who=None, what=None):
    """
    Saves content to S3
    """
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        raise Exception('S3 bucket not configured')

    object_id = str(uuid.uuid4())
    if who:
        object_id = f"{who}-{object_id}"
    if what:
        object_id = f"{what}-{object_id}"
        
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    file_extension = os.path.splitext(filename)[1] if filename else '.xml'
    if not file_extension:
        file_extension = '.xml'
        
    s3_key = f"ingested/{object_id}{file_extension}"
    
    metadata = {
        'object_id': object_id,
        'original_filename': filename or 'unknown',
        'ingestion_timestamp': timestamp
    }
    if source_url:
        metadata['source_url'] = source_url
    if who:
        metadata['who'] = who
    if what:
        metadata['what'] = what

    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=content,
        ContentType=content_type,
        Metadata=metadata
    )
    
    logger.info(f"Uploaded to S3: {s3_key}")
    return object_id
