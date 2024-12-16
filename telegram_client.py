# telegram_client.py

import os
import time
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils import logger

def send_file(filepath, file_type, filename):
    """
    Sends a file via Telegram using HTTP requests.
    Returns True if successful, False otherwise.
    """
    
    logger.debug(f"send_file called with: {filename}, file_type: {file_type}")
    
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/'

        if file_type == 'jpg':
            method = 'sendPhoto'
            files = {'photo': open(filepath, 'rb')}
            data = {'chat_id': TELEGRAM_CHAT_ID}
        elif file_type == 'video':
            method = 'sendVideo'
            files = {'video': open(filepath, 'rb')}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'width': 1280,   # Static width for trailcam videos
                'height': 720    # Static height for trailcam videos
            }
        else:
            logger.warning(f"send_file: Unsupported file type for file {filename}. Skipping.")
            return False

        response = requests.post(url + method, data=data, files=files, timeout=60)

        # Close the file
        files['photo'].close() if file_type == 'jpg' else files['video'].close()

        if response.status_code == 200:
            logger.info(f"Successfully sent {filename} via Telegram.")
            return True
        elif response.status_code == 429:
            # Handle rate limiting
            try:
                response_json = response.json()
                retry_after = response_json.get('parameters', {}).get('retry_after', 30)
                logger.error(f"Rate limit exceeded when sending {filename}. "
                             f"Retrying after {retry_after + 5} seconds.")
                time.sleep(retry_after + 5)
            except ValueError:
                logger.error(f"Rate limit exceeded when sending {filename}, but failed to parse 'retry_after'. "
                             f"Sleeping for 35 seconds.")
                time.sleep(35)  # Fallback sleep duration
            return False
        else:
            logger.error(f"Failed to send {filename}. Status Code: {response.status_code}, Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"RequestException while sending {filename}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while sending {filename}: {e}")
    return False
