import os
import time
import requests
import shutil
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, FILES_DIRECTORY, PROCESSED_DIRECTORY, FAILED_DIRECTORY, MAX_RETRIES
from utils import logger, get_file_type


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


def send_file(filepath, file_type, filename):
    """
    Sends a file via Telegram using HTTP requests.
    Returns True if successful, False otherwise.
    """
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/'

        if file_type == 'photo':
            method = 'sendPhoto'
            files = {'photo': open(filepath, 'rb')}
            data = {
                'chat_id': TELEGRAM_CHAT_ID
                # No 'caption' as per your requirement
            }
        elif file_type == 'video':
            method = 'sendVideo'
            files = {'video': open(filepath, 'rb')}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'width': 1280,   # Static width for trailcam videos
                'height': 720    # Static height for trailcam videos
            }
        else:
            logger.warning(
                f"Unsupported file type for file {filename}. Skipping.")
            return False

        response = requests.post(
            url + method, data=data, files=files, timeout=60)

        # Close the file
        files['photo'].close() if file_type == 'photo' else files['video'].close()

        if response.status_code == 200:
            logger.info(f"Successfully sent {filename} via Telegram.")
            return True
        elif response.status_code == 429:
            # Handle rate limiting
            try:
                response_json = response.json()
                retry_after = response_json.get(
                    'parameters', {}).get('retry_after', 30)
                logger.error(f"Rate limit exceeded when sending {filename}. "
                             f"Retrying after {retry_after + 5} seconds.")
                time.sleep(retry_after + 5)
            except ValueError:
                logger.error(f"Rate limit exceeded when sending {filename}, but failed to parse 'retry_after'. "
                             f"Sleeping for 35 seconds.")
                time.sleep(35)  # Fallback sleep duration
            return False
        else:
            logger.error(
                f"Failed to send {filename}. Status Code: {response.status_code}, Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"RequestException while sending {filename}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while sending {filename}: {e}")
    return False


def organize_file(filepath, processed=True):
    """
    Moves the file to the processed or failed directory, organized by year-month.
    """
    timestamp = get_file_timestamp(filepath)
    if not timestamp:
        # Use current time if timestamp retrieval failed
        timestamp = datetime.now()
    year_month = timestamp.strftime('%Y-%m')
    if processed:
        destination_dir = os.path.join(PROCESSED_DIRECTORY, year_month)
    else:
        destination_dir = os.path.join(FAILED_DIRECTORY, year_month)
    os.makedirs(destination_dir, exist_ok=True)
    destination = os.path.join(destination_dir, os.path.basename(filepath))
    try:
        shutil.move(filepath, destination)
        if processed:
            logger.info(
                f"Moved {os.path.basename(filepath)} to {destination_dir}.")
        else:
            logger.info(
                f"Moved {os.path.basename(filepath)} to FAILED directory {destination_dir}.")
    except Exception as e:
        logger.error(f"Error moving file {filepath} to {destination}: {e}")


def process_file(filepath):
    """
    Processes a single file: sends it via Telegram and moves it accordingly.
    """
    filename = os.path.basename(filepath)
    file_type = get_file_type(filename)
    if not file_type:
        logger.warning(f"Unsupported file type for file {filename}. Skipping.")
        return

    retries = 0
    success = False
    while retries < MAX_RETRIES and not success:
        success = send_file(filepath, file_type, filename)
        if not success:
            retries += 1
            logger.warning(
                f"Retrying ({retries}/{MAX_RETRIES}) for file {filename}...")
            time.sleep(2)  # Wait before retrying

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
        files_sorted = sorted(files, key=lambda x: os.path.getmtime(
            os.path.join(FILES_DIRECTORY, x)))

        for file in files_sorted:
            filepath = os.path.join(FILES_DIRECTORY, file)
            if os.path.isfile(filepath):
                logger.info(f"Processing file: {file}")
                process_file(filepath)
    except Exception as e:
        logger.error(f"Error scanning directory {FILES_DIRECTORY}: {e}")
