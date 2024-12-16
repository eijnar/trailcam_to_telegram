import os
import re
from watchdog.events import FileSystemEventHandler
from config import FILES_DIRECTORY
from utils import logger
from file_processor import process_file

class LogHandler(FileSystemEventHandler):
    """
    Handler for monitoring the vsftpd.log file for new upload entries.
    """

    def __init__(self, log_file_path):
        super().__init__()
        self.log_file_path = log_file_path
        self._position = 0
        self.file = None

        # Initialize the file and position
        self._open_log_file()

        # Define the pattern to look for in the log
        self.upload_pattern = re.compile(r'OK UPLOAD:.*?"[^"]+",\s*"([^"]+)"')

    def _open_log_file(self):
        """Opens the log file and initializes the position to the end."""
        if os.path.exists(self.log_file_path):
            try:
                self.file = open(self.log_file_path, 'r')
                self.file.seek(0, os.SEEK_END)
                self._position = self.file.tell()
                logger.info(f"Opened log file: {self.log_file_path}")
            except Exception as e:
                logger.error(f"Error opening log file {self.log_file_path}: {e}")
                self.file = None
        else:
            logger.error(f"Log file {self.log_file_path} does not exist.")

    def on_modified(self, event):
        if event.src_path == self.log_file_path:
            try:
                # If the file was rotated or is not open, reopen it
                if self.file is None:
                    self._open_log_file()
                    if self.file is None:
                        return

                # Read new lines from the file
                self.file.seek(self._position)
                new_lines = self.file.readlines()
                self._position = self.file.tell()

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
                # Close the file on error to trigger reopening on the next modification
                if self.file:
                    self.file.close()
                    self.file = None

    def close(self):
        """Closes the log file when stopping the observer."""
        if self.file:
            self.file.close()
            logger.info("Closed log file.")
