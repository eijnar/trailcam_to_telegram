import shutil
import os
from datetime import datetime
from config import PROCESSED_DIRECTORY, FAILED_DIRECTORY
from utils import logger

def get_file_timestamp(filepath):
    """
    Retrieves the file's modification time.
    """
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime)
    except Exception as e:
        logger.error(f"Error getting timestamp for {filepath}: {e}")
        return None

def organize_file(filepath, processed=True):
    """
    Moves the file to the processed or failed directory, organized by year-month.
    """
    timestamp = get_file_timestamp(filepath)
    if not timestamp:
        # Use current time if timestamp retrieval failed
        timestamp = datetime.utcnow()
    year_month = timestamp.strftime('%Y-%m')
    destination_dir = os.path.join(PROCESSED_DIRECTORY if processed else FAILED_DIRECTORY, year_month)
    os.makedirs(destination_dir, exist_ok=True)
    destination = os.path.join(destination_dir, os.path.basename(filepath))
    try:
        shutil.move(filepath, destination)
        status = "Processed" if processed else "Failed"
        logger.info(f"{status} file moved to {destination_dir}.")
    except Exception as e:
        logger.error(f"Error moving file {filepath} to {destination}: {e}")
