"""Create a logger object. Writes to /logs/.

Used by all instances
"""
import logging
from logging.handlers import RotatingFileHandler

LOG_PATH = "logs/server.log"

# Create a logger
logger = logging.getLogger("fastapi_app")
logger.setLevel(logging.INFO)  # Change to DEBUG for more details

# Create a rotating file handler (log file max size: 5MB, keeps 3 old logs)
file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
file_handler.setLevel(logging.INFO)

# Create a console handler for logging to stdout
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Define log format
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)