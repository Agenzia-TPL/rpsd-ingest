from rpsd_ingest.config import config
from rpsd_ingest.storage.s3 import S3StorageProvider
from rpsd_ingest.storage.fs import FSStorageProvider

def get_storage_provider():
    """
    Returns the configured storage provider.
    """
    provider = config['storage']['provider']
    if provider == 's3':
        return S3StorageProvider(config['storage']['s3']['bucket_name'])
    elif provider == 'fs':
        return FSStorageProvider(config['storage']['fs']['base_path'])
    else:
        raise Exception(f"Unknown storage provider: {provider}")

storage_provider = get_storage_provider()
