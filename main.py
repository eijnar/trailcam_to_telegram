from file_processor import scan_and_send
from monitor import run_monitoring
from elasticsearch_client import create_index
from utils import logger

def main():
    """
    Main function to run the file sender application.
    """
    logger.info("Starting File Sender Application.")

    # Create Elasticsearch index
    create_index()

    # Initial scan and send
    scan_and_send()

    # Start log monitoring
    run_monitoring()

if __name__ == "__main__":
    main()
