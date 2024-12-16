import os
import time
from datetime import datetime
from utils import logger, get_file_type
from metadata_extractor import extract_gps, extract_timestamp
from elasticsearch_client import ingest_metadata
from telegram_client import send_file
from file_organizer import organize_file
from config import FILES_DIRECTORY, MAX_RETRIES

def process_file(filepath):
    """
    Processes a single file:
    - For JPG files: extracts GPS and timestamp, ingests metadata into Elasticsearch.
    - Sends the file via Telegram.
    - Organizes the file based on the success of sending.
    """
    filename = os.path.basename(filepath)
    device_id = filename.split("-")[0]  # Extract device ID from filename
    file_type = get_file_type(filename)

    if not file_type:
        logger.warning(f"Unsupported file type for file {filename}. Skipping.")
        return

    if file_type == 'jpg':
        # Extract GPS metadata and timestamp for JPG files
        gps_coords = extract_gps(filepath)
        timestamp_taken = extract_timestamp(filepath)

        # Ensure timestamp_taken has a value
        if not timestamp_taken:
            timestamp_taken = datetime.utcnow()

        # Ingest metadata into Elasticsearch
        ingest_metadata(device_id, gps_coords, timestamp_taken, filename)
    elif file_type in ['video']:
        logger.info(f"Skipping metadata ingestion for video file: {filename}")
    else:
        # This case should not occur due to get_file_type restrictions
        logger.warning(f"Unhandled file type for file {filename}. Skipping metadata extraction.")
    
    # Attempt to send the file via Telegram with retries
    retries = 0
    success = False
    while retries < MAX_RETRIES and not success:
        success = send_file(filepath, file_type, filename)
        if not success:
            retries += 1
            logger.warning(f"Retrying ({retries}/{MAX_RETRIES}) for file {filename}...")
            time.sleep(2)  # Wait before retrying

    # Organize the file based on success or failure
    if success:
        organize_file(filepath, processed=True)
    else:
        organize_file(filepath, processed=False)

def scan_and_send():
    """
    Scans the FILES_DIRECTORY for files, sorts them from oldest to newest, and processes them.
    """
    try:
        files = os.listdir(FILES_DIRECTORY)
        if not files:
            logger.info("No files to process.")
            return

        # Sort files by modification time (oldest first)
        files_sorted = sorted(files, key=lambda x: os.path.getmtime(os.path.join(FILES_DIRECTORY, x)))

        for file in files_sorted:
            filepath = os.path.join(FILES_DIRECTORY, file)
            if os.path.isfile(filepath):
                logger.info(f"Processing file: {file}")
                process_file(filepath)
    except Exception as e:
        logger.error(f"Error scanning directory {FILES_DIRECTORY}: {e}")