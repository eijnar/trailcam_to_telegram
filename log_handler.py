import os
import re
from watchdog.events import FileSystemEventHandler
from config import FILES_DIRECTORY
from utils import logger
from file_processor import process_file


class LogHandler(FileSystemEventHandler):
    """
    Handler for monitoring the vsftpd.log file for new upload entries and detecting log rotations.
    """

    def __init__(self, log_file_path):
        super().__init__()
        self.log_file_path = log_file_path
        self._position = 0
        self._inode = None
        self.file = None
        self._upload_pattern = re.compile(r'OK UPLOAD:.*?"[^"]+",\s*"([^"]+)"')
        self._open_log_file()

    def _open_log_file(self):
        """Open the log file and initialize the position and inode."""
        try:
            if os.path.exists(self.log_file_path):
                self.file = open(self.log_file_path, 'r')
                self.file.seek(0, os.SEEK_END)
                self._position = self.file.tell()
                self._inode = os.fstat(self.file.fileno()).st_ino
                logger.info(
                    f"Opened log file: {self.log_file_path} with inode: {self._inode}")
            else:
                logger.error(f"Log file {self.log_file_path} does not exist.")
                self.file = None
        except Exception as e:
            logger.error(f"Error opening log file {self.log_file_path}: {e}")
            self.file = None

    def _check_for_rotation(self):
        """Check if the log file has been rotated by comparing inodes or detecting file deletion."""
        try:
            current_inode = os.stat(self.log_file_path).st_ino
            if self._inode != current_inode:
                logger.info(
                    f"Log rotation detected for {self.log_file_path}. Inode changed from {self._inode} to {current_inode}.")
                self._read_remaining_lines()
                self._reopen_log_file()
        except FileNotFoundError:
            logger.warning(
                f"Log file {self.log_file_path} not found. It may have been rotated. Reopening...")
            self._read_remaining_lines()
            self._reopen_log_file()
        except Exception as e:
            logger.error(
                f"Error checking log rotation for {self.log_file_path}: {e}")

    def _read_remaining_lines(self):
        """Read and process any remaining lines in the current log file before closing it."""
        if self.file:
            try:
                self.file.seek(self._position)
                new_lines = self.file.readlines()
                self._position = self.file.tell()

                for line in new_lines:
                    self._process_upload_line(line)
            except Exception as e:
                logger.error(
                    f"Error reading remaining lines from {self.log_file_path}: {e}")
            finally:
                self.file.close()
                logger.info(
                    "Closed old log file after reading remaining lines.")

    def _reopen_log_file(self):
        """Reopen the new log file and reset position to the beginning."""
        self.file = None
        self._position = 0
        self._open_log_file()
        if self.file:
            # Start reading from the beginning of the new log file
            self.file.seek(0)
            self._position = 0
            logger.info(
                f"Reopened log file {self.log_file_path} and reset position to the beginning.")

    def _process_upload_line(self, line):
        """Process a single line to check for upload entries and handle them."""
        if 'OK UPLOAD:' in line:
            logger.info(f"Detected upload line: {line.strip()}")
            match = self._upload_pattern.search(line)
            if match:
                filepath = match.group(1)
                filename = os.path.basename(filepath)
                uploaded_file_path = os.path.join(FILES_DIRECTORY, filename)

                if os.path.exists(uploaded_file_path):
                    logger.info(f"Newly uploaded file detected: {filename}")
                    process_file(uploaded_file_path)
                else:
                    logger.error(
                        f"Uploaded file {uploaded_file_path} does not exist.")
            else:
                logger.warning(
                    f"Could not extract filename from line: {line.strip()}")

    def on_modified(self, event):
        if event.src_path == self.log_file_path:
            try:
                self._check_for_rotation()

                if self.file is None:
                    return

                self.file.seek(self._position)
                new_lines = self.file.readlines()
                self._position = self.file.tell()

                for line in new_lines:
                    self._process_upload_line(line)
            except Exception as e:
                logger.error(
                    f"Error processing log file {self.log_file_path}: {e}")
                if self.file:
                    self.file.close()
                    self.file = None

    def close(self):
        """Close the log file when stopping the observer."""
        if self.file:
            self.file.close()
            logger.info("Closed log file.")
