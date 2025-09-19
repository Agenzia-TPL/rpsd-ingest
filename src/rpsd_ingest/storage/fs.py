import os
import uuid
from datetime import datetime, timezone
import logging
import json

from rpsd_ingest.storage.provider import StorageProvider

logger = logging.getLogger()

class FSStorageProvider(StorageProvider):
    def __init__(self, base_path):
        if not base_path:
            raise Exception('FS base path not configured')
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def save(self, content, filename, content_type='application/xml', source_url=None, who=None, what=None):
        """
        Saves content to the file system.
        """
        object_id = str(uuid.uuid4())
        if who:
            object_id = f"{who}-{object_id}"
        if what:
            object_id = f"{what}-{object_id}"
            
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        
        file_extension = os.path.splitext(filename)[1] if filename else '.xml'
        if not file_extension:
            file_extension = '.xml'
            
        file_path = os.path.join(self.base_path, f"{object_id}{file_extension}")
        
        metadata = {
            'object_id': object_id,
            'original_filename': filename or 'unknown',
            'ingestion_timestamp': timestamp,
            'content_type': content_type
        }
        if source_url:
            metadata['source_url'] = source_url
        if who:
            metadata['who'] = who
        if what:
            metadata['what'] = what

        with open(file_path, 'wb') as f:
            f.write(content)
        
        with open(f"{file_path}.meta", 'w') as f:
            json.dump(metadata, f)
        
        logger.info(f"Saved to file system: {file_path}")
        return object_id
