import time
import random
import logging
import os

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure main logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configure dry run logger
dry_run_logger = logging.getLogger("dry_run_logger")
dry_run_logger.setLevel(logging.INFO)
dry_run_handler = logging.FileHandler("logs/dry_run.log")
dry_run_formatter = logging.Formatter("%(asctime)s - %(message)s")
dry_run_handler.setFormatter(dry_run_formatter)
dry_run_logger.addHandler(dry_run_handler)

def log_dry_run(message):
    """Logs a message to the dry run log file."""
    dry_run_logger.info(message)

def random_delay(min_seconds=3, max_seconds=8):
    """Introduces a random delay to simulate human-like behavior."""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay

def log_info(message):
    """Logs an informational message."""
    logging.info(message)

def log_warning(message):
    """Logs a warning message."""
    logging.warning(message)

def log_error(message):
    """Logs an error message."""
    logging.error(message)
