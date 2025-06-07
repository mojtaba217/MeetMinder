"""
Screen Capture Service abstraction layer for MeetMinder.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import logging
from dataclasses import dataclass
import base64
import io

try:
    import mss
except ImportError:
    mss = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    from PIL import Image
except ImportError:
    Image = None

from utils.error_handler import ScreenCaptureError, handle_errors

logger = logging.getLogger('meetminder.screen_service')


@dataclass
class ScreenConfig:
    """Screen capture configuration."""
    monitor_index: int = 0
    quality: int = 80
    format: str = "PNG"


class ScreenServiceInterface(ABC):
    """Interface for screen capture services."""
    
    @abstractmethod
    def capture_screen(self, config: ScreenConfig) -> Optional[Any]:
        """Capture screen screenshot."""
        pass
    
    @abstractmethod
    def get_monitors(self) -> List[Dict[str, Any]]:
        """Get list of available monitors."""
        pass
    
    @abstractmethod
    def get_active_window_info(self) -> Dict[str, Any]:
        """Get information about active window."""
        pass


class MSSScreenService(ScreenServiceInterface):
    """MSS-based screen capture service."""
    
    def __init__(self):
        if mss is None:
            raise ImportError("MSS library not installed. Install with: pip install mss")
        if Image is None:
            raise ImportError("PIL library not installed. Install with: pip install Pillow")
        self.sct = None
        self.logger = logger
    
    @handle_errors(fallback_return=None)
    def capture_screen(self, config: ScreenConfig) -> Optional[Any]:
        """Capture screen using MSS."""
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                if config.monitor_index >= len(monitors):
                    self.logger.warning(f"Monitor index {config.monitor_index} out of range")
                    config.monitor_index = 0
                
                monitor = monitors[config.monitor_index]
                screenshot = sct.grab(monitor)
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                self.logger.info(f"Captured screen {config.monitor_index}: {img.size}")
                return img
                
        except Exception as e:
            self.logger.error(f"Failed to capture screen: {e}")
            raise ScreenCaptureError(f"Failed to capture screen: {e}")
    
    @handle_errors(fallback_return=[])
    def get_monitors(self) -> List[Dict[str, Any]]:
        """Get available monitors."""
        try:
            with mss.mss() as sct:
                monitors = []
                for i, monitor in enumerate(sct.monitors):
                    if i == 0:  # Skip "All in One" monitor
                        continue
                    monitors.append({
                        "index": i - 1,
                        "left": monitor["left"],
                        "top": monitor["top"],
                        "width": monitor["width"],
                        "height": monitor["height"]
                    })
                
                self.logger.info(f"Found {len(monitors)} monitors")
                return monitors
                
        except Exception as e:
            self.logger.error(f"Failed to get monitors: {e}")
            raise ScreenCaptureError(f"Failed to get monitors: {e}")
    
    @handle_errors(fallback_return={"title": "Unknown", "process": "Unknown"})
    def get_active_window_info(self) -> Dict[str, Any]:
        """Get active window information."""
        try:
            # Use the existing screen capture implementation
            from screen.capture import ScreenCapture
            screen_capture = ScreenCapture()
            return screen_capture.get_active_window_info()
            
        except Exception as e:
            self.logger.error(f"Failed to get active window info: {e}")
            return {"title": "Unknown", "process": "Unknown", "error": str(e)}


class ScreenServiceManager:
    """Manager for screen capture services."""
    
    def __init__(self):
        self.service: Optional[ScreenServiceInterface] = None
        self.logger = logger
    
    def initialize(self, service_type: str = "mss") -> None:
        """Initialize screen capture service."""
        try:
            if service_type.lower() == "mss":
                self.service = MSSScreenService()
            else:
                raise ValueError(f"Unsupported screen service: {service_type}")
            
            self.logger.info(f"Initialized screen service: {service_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize screen service: {e}")
            raise ScreenCaptureError(f"Failed to initialize screen service: {e}")
    
    @handle_errors(fallback_return=None)
    def capture_screen(self, config: Optional[ScreenConfig] = None) -> Optional[Any]:
        """Capture screen with optional configuration."""
        if not self.service:
            raise ScreenCaptureError("Screen service not initialized")
        
        config = config or ScreenConfig()
        return self.service.capture_screen(config)
    
    @handle_errors(fallback_return="")
    def capture_screen_base64(self, config: Optional[ScreenConfig] = None) -> str:
        """Capture screen and return as base64 string."""
        image = self.capture_screen(config)
        if not image:
            return ""
        
        try:
            buffer = io.BytesIO()
            image.save(buffer, format=config.format if config else "PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            self.logger.debug(f"Converted screenshot to base64: {len(img_str)} chars")
            return img_str
            
        except Exception as e:
            self.logger.error(f"Failed to convert image to base64: {e}")
            return ""
    
    @handle_errors(fallback_return=[])
    def get_monitors(self) -> List[Dict[str, Any]]:
        """Get available monitors."""
        if not self.service:
            raise ScreenCaptureError("Screen service not initialized")
        
        return self.service.get_monitors()
    
    @handle_errors(fallback_return={"title": "Unknown", "process": "Unknown"})
    def get_active_window_info(self) -> Dict[str, Any]:
        """Get active window information."""
        if not self.service:
            raise ScreenCaptureError("Screen service not initialized")
        
        return self.service.get_active_window_info()
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about current screen service."""
        return {
            "service": self.service.__class__.__name__ if self.service else None,
            "initialized": self.service is not None
        } 