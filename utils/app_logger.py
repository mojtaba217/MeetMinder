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
        # On Windows, use a custom handler that replaces emojis to avoid encoding errors
        class SafeConsoleHandler(logging.StreamHandler):
            def emit(self, record):
                try:
                    # Replace emojis with text equivalents for Windows console
                    msg = self.format(record)
                    # Remove or replace common emojis
                    emoji_replacements = {
                        '📥': '[LOAD]',
                        '✅': '[OK]',
                        '❌': '[ERROR]',
                        '⚠️': '[WARN]',
                        '🎯': '[TARGET]',
                        '🚀': '[START]',
                        '🛑': '[STOP]',
                        '🔧': '[CONFIG]',
                        '🎤': '[AUDIO]',
                        '🤖': '[AI]',
                        '🧠': '[BRAIN]',
                        '🎵': '[MUSIC]',
                        '🖥️': '[UI]',
                        '🔍': '[SEARCH]',
                        '⚙️': '[SETUP]',
                        '💡': '[TIP]',
                        '📊': '[STATS]',
                        '💾': '[SAVE]',
                        '📱': '[DEVICE]',
                        '🎵': '[AUDIO]',
                        '🔊': '[SOUND]',
                    }
                    for emoji, replacement in emoji_replacements.items():
                        msg = msg.replace(emoji, replacement)
                    stream = self.stream
                    stream.write(msg + self.terminator)
                    self.flush()
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # If encoding still fails, just write without emojis
                    try:
                        msg = self.format(record)
                        # Remove all non-ASCII characters
                        msg = msg.encode('ascii', errors='ignore').decode('ascii')
                        stream = self.stream
                        stream.write(msg + self.terminator)
                        self.flush()
                    except Exception:
                        pass  # Silently ignore if we can't write at all
        
        console_handler = SafeConsoleHandler(sys.stdout)
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