"""
Centralized logging setup with console and rotating file handlers.
"""

import logging
from logging.handlers import RotatingFileHandler


def setup_logger(log_level: str = "INFO", log_file: str = "trading_bot.log") -> logging.Logger:
    """Configure and return the application logger.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).
        log_file: Path to the log file.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("trading_bot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    # Console handler - dashboard-style output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(console_fmt)

    # [SECURE] Rotating file handler - prevents disk exhaustion (Category 3)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    file_handler.setFormatter(file_fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# --------------------------------------------------
# Security Checklist
# Applied:
#   - Rotating file handler: prevents unbounded log growth (Category 3)
#   - Error info exposure prevention: console shows limited info, file gets full details (Category 4)
# Not Applied:
#   - [WARN] SQL Injection: not applicable - no database used
# --------------------------------------------------
