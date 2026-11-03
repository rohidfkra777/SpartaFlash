"""
SpartaFlash - Centralized Application Logger.
Developer: Rohidfkra777
"""

import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from src.config.constants import LOGS_DIR

class CallbackLogHandler(logging.Handler):
    """Custom logging handler to emit log entries to UI widgets."""
    def __init__(self, callback: Optional[Callable[[str, int], None]] = None):
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if self.callback:
                self.callback(msg, record.levelno)
        except Exception:
            self.handleError(record)

_logger: Optional[logging.Logger] = None
_callback_handler: Optional[CallbackLogHandler] = None

def setup_logger(callback: Optional[Callable[[str, int], None]] = None) -> logging.Logger:
    global _logger, _callback_handler
    if _logger is not None:
        if callback and _callback_handler:
            _callback_handler.callback = callback
        return _logger

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"flasher_{datetime.now().strftime('%Y%m%d')}.log"

    _logger = logging.getLogger("AlfaEnergyFlasher")
    _logger.setLevel(logging.DEBUG)
    _logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-5s] %(message)s",
        datefmt="%H:%M:%S"
    )

    # File Handler (5 MB max, 5 backups)
    file_handler = RotatingFileHandler(
        str(log_file), maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    _logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)

    # Callback Handler for UI Terminal
    _callback_handler = CallbackLogHandler(callback)
    _callback_handler.setLevel(logging.INFO)
    _callback_handler.setFormatter(formatter)
    _logger.addHandler(_callback_handler)

    return _logger

def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        return setup_logger()
    return _logger
