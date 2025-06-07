"""
Error handling framework for MeetMinder application.
"""

import logging
import traceback
from typing import Callable, Any, Optional
from functools import wraps
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger('meetminder.error_handler')


class MeetMinderError(Exception):
    """Base exception for MeetMinder application."""
    pass


class AIServiceError(MeetMinderError):
    """Error in AI service operations."""
    pass


class AudioError(MeetMinderError):
    """Error in audio operations."""
    pass


class ScreenCaptureError(MeetMinderError):
    """Error in screen capture operations."""
    pass


class ConfigurationError(MeetMinderError):
    """Error in configuration operations."""
    pass


class UIError(MeetMinderError):
    """Error in UI operations."""
    pass


def handle_errors(
    show_user_message: bool = True, 
    fallback_return: Any = None,
    exception_types: tuple = (Exception,)
):
    """
    Decorator to handle exceptions gracefully.
    
    Args:
        show_user_message: Whether to show error message to user
        fallback_return: Value to return on error
        exception_types: Types of exceptions to catch
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                logger.debug(f"Full traceback: {traceback.format_exc()}")
                
                if show_user_message and isinstance(e, MeetMinderError):
                    show_error_message(str(e), f"Error in {func.__name__}")
                elif show_user_message:
                    show_error_message(
                        f"An unexpected error occurred: {str(e)}", 
                        "Error"
                    )
                
                return fallback_return
        return wrapper
    return decorator


def show_error_message(message: str, title: str = "Error") -> None:
    """
    Show error message to user.
    
    Args:
        message: Error message to display
        title: Dialog title
    """
    try:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
    except Exception as e:
        logger.error(f"Failed to show error message: {e}")


def log_and_ignore(func: Callable) -> Callable:
    """Decorator that logs errors but doesn't raise them."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Ignored error in {func.__name__}: {str(e)}")
            return None
    return wrapper


class ErrorContext:
    """Context manager for error handling."""
    
    def __init__(self, operation: str, show_message: bool = False):
        self.operation = operation
        self.show_message = show_message
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Error in {self.operation}: {exc_val}")
            if self.show_message:
                show_error_message(f"Error in {self.operation}: {exc_val}")
            return True  # Suppress the exception
        return False 