import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Elasticsearch cluster
ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST')
ELASTICSEARCH_INDEX = os.getenv('ELASTICSEARCH_INDEX')
ELASTICSEARCH_APIKEY_ID = os.getenv('ELASTICSEARCH_APIKEY_ID')
ELASTICSEARCH_APIKEY_VALUE = os.getenv('ELASTICSEARCH_APIKEY_VALUE')

# Log file path
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', '/var/log/vsftpd.log')

# Directory paths
FILES_DIRECTORY = os.getenv('FILES_DIRECTORY', '/path/to/files/')
PROCESSED_DIRECTORY = os.getenv('PROCESSED_DIRECTORY', '/path/to/processed/')
FAILED_DIRECTORY = os.getenv('FAILED_DIRECTORY', '/path/to/failed/')

# Application logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
APP_LOG_FILE = os.getenv('APP_LOG_FILE', 'app.log')

# Retry settings
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))

# Define supported file extensions
PHOTO_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv']

# Ensure directories exist
os.makedirs(FILES_DIRECTORY, exist_ok=True)
os.makedirs(PROCESSED_DIRECTORY, exist_ok=True)
os.makedirs(FAILED_DIRECTORY, exist_ok=True)
