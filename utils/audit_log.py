import logging
import os
from datetime import datetime

LOG_FILE = "audit.log"

# Configure the logger
logger = logging.getLogger("BloodBankAudit")
logger.setLevel(logging.INFO)

# File handler
handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
handler.setLevel(logging.INFO)

# Format: timestamp - level - message
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)

def log_action(user, action, details=""):
    """Logs a user action to the audit log file."""
    message = f"User: {user} | Action: {action}"
    if details:
        message += f" | Details: {details}"
    logger.info(message)

def log_warning(user, action, details=""):
    """Logs a warning-level event."""
    message = f"User: {user} | Action: {action}"
    if details:
        message += f" | Details: {details}"
    logger.warning(message)
