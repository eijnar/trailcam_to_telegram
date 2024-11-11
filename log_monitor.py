# file_sender_async.py

import os
import re
import shutil
import logging
from logging.handlers import RotatingFileHandler
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv
from datetime import datetime
import time

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
FILES_DIRECTORY = os.getenv('FILES_DIRECTORY', '/path/to/files/')
PROCESSED_DIRECTORY = os.getenv('PROCESSED_DIRECTORY', '/path/to/processed/')
FAILED_DIRECTORY = os.getenv('FAILED_DIRECTORY', '/path/to/failed/')
APP_LOG_FILE = os.getenv('APP_LOG_FILE', 'app.log')
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))

# Ensure directories exist
os.makedirs(FILES_DIRECTORY, exist_ok=True)
os.makedirs(PROCESSED_DIRECTORY, exist_ok=True)
os.makedirs(FAILED_DIRECTORY, exist_ok=True)

# Set up logging
logger = logging.getLogger('FileSenderAsync')
logger.setLevel(logging.INFO)

# Create a rotating file handler
handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=5*1024*1024, backupCount=2)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

# Initialize Telegram Bot (Asynchronous)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Define supported file extensions
PHOTO_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv']

def get_file_type(filename):
    _, ext = os.path.splitext(filename.lower())
    if ext in PHOTO_EXTENSIONS:
        return 'photo'
    elif ext in VIDEO_EXTENSIONS:
        return 'video'
    else:
        return None

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

async def send_file(bot, chat_id, filepath, file_type, filename):
    """
    Sends a file via Telegram asynchronously.
    Returns True if successful, False otherwise.
    """
    try:
        with open(filepath, 'rb') as file:
            if file_type == 'photo':
                await bot.send_photo(chat_id=chat_id, photo=file, caption=f"New upload: {filename}")
            elif file_type == 'video':
                await bot.send_video(chat_id=chat_id, video=file, caption=f"New upload: {filename}")
        logger.info(f"Successfully sent {filename} via Telegram.")
        return True
    except TelegramError as te:
        logger.error(f"TelegramError while sending {filename}: {te}")
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
            logger.info(f"Moved {os.path.basename(filepath)} to {destination_dir}.")
        else:
            logger.info(f"Moved {os.path.basename(filepath)} to FAILED directory {destination_dir}.")
    except Exception as e:
        logger.error(f"Error moving file {filepath} to {destination}: {e}")

async def process_file(filepath):
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
        success = await send_file(bot, TELEGRAM_CHAT_ID, filepath, file_type, filename)
        if not success:
            retries += 1
            logger.warning(f"Retrying ({retries}/{MAX_RETRIES}) for file {filename}...")
            await asyncio.sleep(2)  # Wait before retrying

    if success:
        organize_file(filepath, processed=True)
    else:
        organize_file(filepath, processed=False)

async def scan_and_send():
    """
    Scans the FILES_DIRECTORY for files and processes them asynchronously.
    """
    try:
        files = os.listdir(FILES_DIRECTORY)
        if not files:
            logger.info("No files to process.")
            return
        tasks = []
        for file in files:
            filepath = os.path.join(FILES_DIRECTORY, file)
            if os.path.isfile(filepath):
                logger.info(f"Processing file: {file}")
                tasks.append(process_file(filepath))
        if tasks:
            await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Error scanning directory {FILES_DIRECTORY}: {e}")

async def main():
    """
    Main function to run the file sender application asynchronously.
    """
    logger.info("Starting File Sender Async Application.")
    await scan_and_send()
    logger.info("File Sender Async Application finished.")

if __name__ == "__main__":
    asyncio.run(main())
