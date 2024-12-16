from utils import logger
from file_processor import scan_and_send
from monitor import run_monitoring

def main():
    """
    Main function to run the file sender application.
    """
    logger.info("Starting Application.")

    # Initial scan and send
    scan_and_send()
    
    # Start log monitoring
    run_monitoring()

if __name__ == "__main__":
    main()
