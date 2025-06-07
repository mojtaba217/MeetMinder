"""
Logging infrastructure for MeetMinder application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import traceback


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m', 
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
        'RESET': '\033[0m'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Setup application logger with file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    console_formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_exception(logger: logging.Logger, exception: Exception, context: str = "") -> None:
    """Log exception with full traceback."""
    context_msg = f" [{context}]" if context else ""
    logger.error(f"Exception occurred{context_msg}: {str(exception)}")
    logger.debug(f"Full traceback{context_msg}:\n{traceback.format_exc()}")


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module."""
    return logging.getLogger(f"meetminder.{name}")


# Application-wide logger instances
app_logger = setup_logger('meetminder', 'logs/meetminder.log')
ui_logger = get_logger('ui')
ai_logger = get_logger('ai')
audio_logger = get_logger('audio')
screen_logger = get_logger('screen')
config_logger = get_logger('config') 