import re
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
import requests
from dotenv import load_dotenv
from datetime import datetime
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', '/var/log/vsftpd.log')
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
logger = logging.getLogger('FileSender')
logger.setLevel(logging.INFO)

# Create a rotating file handler
handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=5*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

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
        elif file_type == 'video':
            method = 'sendVideo'
            files = {'video': open(filepath, 'rb')}
        else:
            logger.warning(f"Unsupported file type for file {filename}. Skipping.")
            return False

        data = {
            'chat_id': TELEGRAM_CHAT_ID
        }

        response = requests.post(url + method, data=data, files=files, timeout=60)

        # Close the file
        files['photo'].close() if file_type == 'photo' else files['video'].close()

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
            logger.warning(f"Retrying ({retries}/{MAX_RETRIES}) for file {filename}...")
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
        files_sorted = sorted(files, key=lambda x: os.path.getmtime(os.path.join(FILES_DIRECTORY, x)))

        for file in files_sorted:
            filepath = os.path.join(FILES_DIRECTORY, file)
            if os.path.isfile(filepath):
                logger.info(f"Processing file: {file}")
                process_file(filepath)
    except Exception as e:
        logger.error(f"Error scanning directory {FILES_DIRECTORY}: {e}")

class LogHandler(FileSystemEventHandler):
    """
    Handler for monitoring the vsftpd.log file for new upload entries.
    """

    def __init__(self, log_file_path):
        super().__init__()
        self.log_file_path = log_file_path
        self._position = 0
        # Initialize the position to the end of the file
        if os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'r') as f:
                f.seek(0, os.SEEK_END)
                self._position = f.tell()
        else:
            logger.error(f"Log file {self.log_file_path} does not exist.")

        # Define the pattern to look for in the log
        self.upload_pattern = re.compile(r'OK UPLOAD:.*?"([^"]+)"')

    def on_modified(self, event):
        if event.src_path == self.log_file_path:
            try:
                with open(self.log_file_path, 'r') as f:
                    f.seek(self._position)
                    new_lines = f.readlines()
                    self._position = f.tell()

                for line in new_lines:
                    if 'OK UPLOAD:' in line:
                        logger.info(f"Detected upload line: {line.strip()}")
                        match = self.upload_pattern.search(line)
                        if match:
                            filepath = match.group(1)
                            filename = os.path.basename(filepath)
                            uploaded_file_path = os.path.join(FILES_DIRECTORY, filename)
                            if os.path.exists(uploaded_file_path):
                                logger.info(f"Newly uploaded file detected: {filename}")
                                process_file(uploaded_file_path)
                            else:
                                logger.error(f"Uploaded file {uploaded_file_path} does not exist.")
                        else:
                            logger.warning(f"Could not extract filename from line: {line.strip()}")
            except Exception as e:
                logger.error(f"Error processing log file {self.log_file_path}: {e}")

def start_log_monitoring(log_file_path):
    """
    Starts monitoring the vsftpd.log file for new upload entries.
    """
    event_handler = LogHandler(log_file_path)
    observer = Observer()
    log_dir = os.path.dirname(log_file_path)
    observer.schedule(event_handler, path=log_dir, recursive=False)
    observer.start()
    logger.info(f"Started monitoring log file: {log_file_path}")
    return observer

def main():
    """
    Main function to run the file sender application.
    """
    logger.info("Starting File Sender Application.")

    # Initial scan and send
    scan_and_send()

    # Start log monitoring
    observer = start_log_monitoring(LOG_FILE_PATH)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping File Sender Application.")
        observer.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        observer.stop()

    observer.join()
    logger.info("File Sender Application stopped.")

if __name__ == "__main__":
    main()
