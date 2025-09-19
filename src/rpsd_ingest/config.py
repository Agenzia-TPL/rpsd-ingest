import os
import yaml
from pathlib import Path

def load_config():
    """
    Loads configuration from a YAML file or environment variables.
    """
    config = {
        'storage': {
            'provider': os.environ.get('STORAGE_PROVIDER', 'fs'),
            's3': {
                'bucket_name': os.environ.get('S3_BUCKET_NAME')
            },
            'fs': {
                'base_path': os.environ.get('FS_BASE_PATH', '/tmp/ingested')
            }
        },
        'api_key': os.environ.get('API_KEY')
    }

    # Default config path is settings.yaml in the project root
    default_config_path = Path(__file__).parent.parent.parent / 'settings.yaml'
    config_path = os.environ.get('CONFIG_PATH', default_config_path)
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                # Deep merge YAML config into the default config
                for key, value in yaml_config.items():
                    if isinstance(value, dict) and key in config:
                        config[key].update(value)
                    else:
                        config[key] = value
    return config

config = load_config()
