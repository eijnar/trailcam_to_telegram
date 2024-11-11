# log_monitor.py (Updated for Async)

import asyncio
import os
import re
import shutil
import logging
from logging.handlers import RotatingFileHandler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', '/var/log/vsftpd.log')
FILES_DIRECTORY = os.getenv('FILES_DIRECTORY', '/path/to/files/')
PROCESSED_DIRECTORY = os.getenv('PROCESSED_DIRECTORY', '/path/to/processed/')
APP_LOG_FILE = os.getenv('APP_LOG_FILE', 'app.log')

# Set up logging
logger = logging.getLogger('LogMonitor')
logger.setLevel(logging.INFO)

# Create a rotating file handler
handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=5*1024*1024, backupCount=2)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

# Define the pattern to look for in the log
# Using 'OK UPLOAD:' as the identifier
UPLOAD_PATTERN = re.compile(r'OK UPLOAD:')

class LogHandler(FileSystemEventHandler):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self._position = 0
        # Initialize the position to the end of the file
        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, 'r') as f:
                f.seek(0, os.SEEK_END)
                self._position = f.tell()
        else:
            logger.error(f"Log file {LOG_FILE_PATH} does not exist.")

    async def on_modified_async(self, event):
        if event.src_path == LOG_FILE_PATH:
            try:
                with open(LOG_FILE_PATH, 'r') as f:
                    f.seek(self._position)
                    new_lines = f.readlines()
                    self._position = f.tell()

                for line in new_lines:
                    if UPLOAD_PATTERN.search(line):
                        logger.info(f"Detected upload line: {line.strip()}")
                        filename = self.extract_filename(line)
                        if filename:
                            await self.process_file(filename)
                        else:
                            logger.warning(f"Could not extract filename from line: {line.strip()}")
            except Exception as e:
                logger.error(f"Error reading log file: {e}")

    def extract_filename(self, log_line):
        """
        Extracts the filename from the log line.
        Example log line:
        Sun Nov 10 16:02:14 2024 [pid 6] [camera] OK UPLOAD: Client "95.197.192.241", "/home/camera/SYDR2547.MP4", 3184198 bytes, 517.68Kbyte/sec
        """
        # Regex to extract the filename between quotes after the client IP
        match = re.search(r'OK UPLOAD: Client ".*?", "([^"]+)",', log_line)
        if match:
            # Extract the base filename
            filepath = match.group(1)
            filename = os.path.basename(filepath)
            return filename
        return None

    async def process_file(self, filename):
        file_path = os.path.join(FILES_DIRECTORY, filename)
        if not os.path.exists(file_path):
            logger.error(f"File {file_path} does not exist.")
            return

        # Determine file type
        _, ext = os.path.splitext(filename.lower())
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            file_type = 'photo'
        elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
            file_type = 'video'
        else:
            logger.warning(f"Unsupported file type for file {filename}.")
            return

        try:
            if file_type == 'photo':
                with open(file_path, 'rb') as photo:
                    await self.bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=photo, caption=f"New upload: {filename}")
            elif file_type == 'video':
                with open(file_path, 'rb') as video:
                    await self.bot.send_video(chat_id=TELEGRAM_CHAT_ID, video=video, caption=f"New upload: {filename}")

            logger.info(f"Successfully sent {filename} via Telegram.")
            # Move the file to the processed directory
            destination = os.path.join(PROCESSED_DIRECTORY, filename)
            shutil.move(file_path, destination)
            logger.info(f"Moved {filename} to processed directory.")

        except TelegramError as e:
            logger.error(f"Failed to send {filename} via Telegram: {e}")
            # Optionally, move to a failed directory
        except Exception as e:
            logger.error(f"Unexpected error processing {filename}: {e}")

async def main():
    # Initialize Telegram Bot
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    event_handler = LogHandler(bot)
    observer = Observer()
    log_dir = os.path.dirname(LOG_FILE_PATH)
    observer.schedule(event_handler, path=log_dir, recursive=False)
    observer.start()
    logger.info(f"Monitoring {LOG_FILE_PATH} for changes...")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Stopping log monitor.")
    except Exception as e:
        logger.error(f"Error in observer: {e}")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    asyncio.run(main())
