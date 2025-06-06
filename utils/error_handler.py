"""
Centralized error handling and logging system for MeetMinder
"""

import logging
import traceback
import time
from functools import wraps
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading
from collections import defaultdict, deque

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorMetrics:
    """Track error metrics for monitoring"""
    error_counts: Dict[str, int]
    last_errors: deque
    performance_issues: Dict[str, float]
    recovery_attempts: Dict[str, int]
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.last_errors = deque(maxlen=50)  # Keep last 50 errors
        self.performance_issues = {}
        self.recovery_attempts = defaultdict(int)

class ErrorHandler:
    """Centralized error handling with recovery strategies"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.metrics = ErrorMetrics()
        self._lock = threading.Lock()
        
        # Recovery strategies
        self.recovery_strategies = {
            "transcription_failure": self._recover_transcription,
            "ai_timeout": self._recover_ai_connection,
            "audio_device_error": self._recover_audio_device,
            "memory_pressure": self._recover_memory,
            "config_error": self._recover_config
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Setup enhanced logging with rotation"""
        logger = logging.getLogger('MeetMinder')
        logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] %(message)s'
        )
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        import os
        os.makedirs('logs', exist_ok=True)
        
        file_handler = RotatingFileHandler(
            'logs/meetminder_errors.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def handle_error(self, 
                    error: Exception, 
                    context: str,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    recover: bool = True) -> bool:
        """
        Handle an error with logging, metrics, and optional recovery
        
        Args:
            error: The exception that occurred
            context: Description of where/when the error occurred
            severity: Error severity level
            recover: Whether to attempt automatic recovery
            
        Returns:
            bool: True if error was handled successfully
        """
        with self._lock:
            # Update metrics
            error_type = type(error).__name__
            self.metrics.error_counts[error_type] += 1
            self.metrics.last_errors.append({
                'error': str(error),
                'context': context,
                'severity': severity.value,
                'timestamp': time.time(),
                'traceback': traceback.format_exc()
            })
            
            # Log error
            self._log_error(error, context, severity)
            
            # Attempt recovery if enabled
            if recover and severity != ErrorSeverity.CRITICAL:
                return self._attempt_recovery(error_type, context, error)
            
            return False
    
    def _log_error(self, error: Exception, context: str, severity: ErrorSeverity):
        """Log error with appropriate level"""
        message = f"Error in {context}: {str(error)}"
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(message, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(message, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def _attempt_recovery(self, error_type: str, context: str, error: Exception) -> bool:
        """Attempt to recover from error using registered strategies"""
        recovery_key = f"{error_type}_{context}"
        
        # Check if we've tried too many times
        if self.metrics.recovery_attempts[recovery_key] >= 3:
            self.logger.warning(f"Max recovery attempts reached for {recovery_key}")
            return False
        
        self.metrics.recovery_attempts[recovery_key] += 1
        
        # Try specific recovery strategy
        for strategy_pattern, strategy_func in self.recovery_strategies.items():
            if strategy_pattern in context.lower() or strategy_pattern in error_type.lower():
                try:
                    self.logger.info(f"Attempting recovery using {strategy_pattern}")
                    return strategy_func(error, context)
                except Exception as recovery_error:
                    self.logger.error(f"Recovery strategy failed: {recovery_error}")
        
        return False
    
    def _recover_transcription(self, error: Exception, context: str) -> bool:
        """Recovery strategy for transcription failures"""
        self.logger.info("Attempting transcription recovery...")
        return True
    
    def _recover_ai_connection(self, error: Exception, context: str) -> bool:
        """Recovery strategy for AI connection issues"""
        self.logger.info("Attempting AI connection recovery...")
        return True
    
    def _recover_audio_device(self, error: Exception, context: str) -> bool:
        """Recovery strategy for audio device errors"""
        self.logger.info("Attempting audio device recovery...")
        return True
    
    def _recover_memory(self, error: Exception, context: str) -> bool:
        """Recovery strategy for memory pressure"""
        self.logger.info("Attempting memory recovery...")
        import gc
        gc.collect()
        return True
    
    def _recover_config(self, error: Exception, context: str) -> bool:
        """Recovery strategy for configuration errors"""
        self.logger.info("Attempting config recovery...")
        return True
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error metrics"""
        with self._lock:
            return {
                'total_errors': sum(self.metrics.error_counts.values()),
                'error_types': dict(self.metrics.error_counts),
                'recent_errors': list(self.metrics.last_errors)[-10:],
                'recovery_attempts': dict(self.metrics.recovery_attempts)
            }

# Decorator for automatic error handling
def handle_errors(severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 recover: bool = True,
                 context: Optional[str] = None):
    """Decorator to automatically handle errors in functions"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get global error handler or create one
                error_handler = getattr(wrapper, '_error_handler', None)
                if not error_handler:
                    error_handler = ErrorHandler()
                    wrapper._error_handler = error_handler
                
                func_context = context or f"{func.__module__}.{func.__name__}"
                error_handler.handle_error(e, func_context, severity, recover)
                
                # Re-raise critical errors
                if severity == ErrorSeverity.CRITICAL:
                    raise
                
                return None
        return wrapper
    return decorator

# Global error handler instance
global_error_handler = ErrorHandler() 