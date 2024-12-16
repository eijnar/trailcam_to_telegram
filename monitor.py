import sys
import os
import signal
import time
from watchdog.observers.polling import PollingObserver
from log_handler import LogHandler
from config import LOG_FILE_PATH
from utils import logger

def start_log_monitoring(log_file_path):
    """
    Starts monitoring the vsftpd.log file for new upload entries.
    """
    event_handler = LogHandler(log_file_path)
    observer = PollingObserver(timeout=2)  # Polling interval set to 2 seconds
    log_dir = os.path.dirname(log_file_path)
    observer.schedule(event_handler, path=log_dir, recursive=False)
    observer.start()
    logger.info(f"Started monitoring log file: {log_file_path}")
    return observer, event_handler

def handle_exit(signum, frame):
    """
    Handles graceful shutdown upon receiving termination signals.
    """
    logger.info(f"Received signal {signum}. Shutting down gracefully...")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)

def run_monitoring():
    """
    Starts the log monitoring and keeps the process running.
    """
    observer, event_handler = start_log_monitoring(LOG_FILE_PATH)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping File Sender Application.")
        observer.stop()
        event_handler.close()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        observer.stop()
        event_handler.close()

    observer.join()
    logger.info("File Sender Application stopped.")
