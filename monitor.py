import os
import sys
import signal
import time
from watchdog.observers.polling import PollingObserver
from log_handler import LogHandler
from config import LOG_FILE_PATH
from utils import logger


def handle_exit(signum, frame):
    """
    Handles graceful shutdown upon receiving termination signals.
    """
    logger.info(f"Received signal {signum}. Shutting down gracefully...")
    sys.exit(0)


# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)
 

def start_log_monitoring(log_file_path):
    """
    Starts monitoring the vsftpd.log file for new upload entries.
    """
    event_handler = LogHandler(log_file_path)
    observer = PollingObserver(timeout=5)
    log_dir = os.path.dirname(log_file_path)
    observer.schedule(event_handler, path=log_dir, recursive=False)
    observer.start()
    logger.info(f"Started monitoring log file: {log_file_path}")
    return observer


def run_monitoring():
    """
    Starts the log monitoring and keeps the process running
    """

    observer = start_log_monitoring(LOG_FILE_PATH)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping application")
        observer.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        observer.stop()

    observer.join()
    logger.info("Application has stopped.")
