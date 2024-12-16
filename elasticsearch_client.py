from elasticsearch import Elasticsearch
from datetime import datetime
from config import ELASTICSEARCH_HOST, ELASTICSEARCH_INDEX, ELASTICSEARCH_APIKEY_ID, ELASTICSEARCH_APIKEY_VALUE
from utils import logger

print(f"Loaded API Key: {ELASTICSEARCH_APIKEY_ID, ELASTICSEARCH_APIKEY_VALUE}")

# Initialize Elasticsearch client with API key authentication
es = Elasticsearch(
    hosts=ELASTICSEARCH_HOST,
    api_key=(ELASTICSEARCH_APIKEY_ID, ELASTICSEARCH_APIKEY_VALUE)
)

def create_index():
    """Create an Elasticsearch index with ECS-compatible mapping."""
    mapping = {
        "mappings": {
            "properties": {
                "device": {
                    "properties": {
                        "id": {"type": "keyword"}
                    }
                },
                "@timestamp": {"type": "date"},
                "event": {
                    "properties": {
                        "ingested": {"type": "date"}
                    }
                },
                "geo": {
                    "properties": {
                        "location": {"type": "geo_point"}
                    }
                },
                "file": {
                    "properties": {
                        "name": {"type": "keyword"}
                    }
                }
            }
        }
    }

    try:
        logger.debug(f"Checking if index '{ELASTICSEARCH_INDEX}' exists.")
        if not es.indices.exists(index=ELASTICSEARCH_INDEX):
            logger.debug(f"Creating index '{ELASTICSEARCH_INDEX}' with mapping: {mapping}")
            es.indices.create(index=ELASTICSEARCH_INDEX, body=mapping)
            logger.info(f"Created Elasticsearch index: {ELASTICSEARCH_INDEX}")
        else:
            logger.info(f"Elasticsearch index already exists: {ELASTICSEARCH_INDEX}")
    except Exception as e:
        logger.error(f"Error creating Elasticsearch index: {e}")

def ingest_metadata(device_id, gps_coords, timestamp_taken, filename):
    """Ingest ECS-compliant metadata into Elasticsearch."""
    document = {
        "device": {
            "id": device_id
        },
        "@timestamp": timestamp_taken.isoformat() if timestamp_taken else datetime.utcnow().isoformat(),
        "event": {
            "ingested": datetime.utcnow().isoformat()
        },
        "geo": {
            "location": gps_coords
        },
        "file": {
            "name": filename
        }
    }

    try:
        es.index(index=ELASTICSEARCH_INDEX, document=document)
        logger.info(f"Metadata ingested into Elasticsearch for device: {device_id}")
    except Exception as e:
        logger.error(f"Failed to ingest metadata into Elasticsearch: {e}")
