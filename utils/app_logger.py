import logging
import sys
import io
from pathlib import Path

def setup_logger(name: str, log_file: str = None, level: int = logging.INFO):
    """Setup application logger with UTF-8 support for emojis."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create console handler with UTF-8 encoding support
    if sys.platform == 'win32':
        # On Windows, create a UTF-8 wrapper for the console handler
        try:
            utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            console_handler = logging.StreamHandler(utf8_stdout)
        except (AttributeError, OSError):
            # Fallback to regular stdout if buffer wrapping fails
            console_handler = logging.StreamHandler(sys.stdout)
    else:
        # On other platforms, use stdout directly
        console_handler = logging.StreamHandler(sys.stdout)

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Main application logger
logger = setup_logger('meetminder', 'logs/meetminder.log') 