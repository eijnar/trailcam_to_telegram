import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from config import APP_LOG_FILE, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS

# Set up logging
logger = logging.getLogger('FileSender')
logger.setLevel(logging.INFO)

# Create handlers
file_handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=5*1024*1024, backupCount=5)
stream_handler = logging.StreamHandler(sys.stdout)

# Create formatters and add them to handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def get_file_type(filename):
    _, ext = os.path.splitext(filename.lower())
    if ext in PHOTO_EXTENSIONS:
        return 'photo'
    elif ext in VIDEO_EXTENSIONS:
        return 'video'
    else:
        return None