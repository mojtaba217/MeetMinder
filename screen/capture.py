import pyautogui
import psutil
import platform
from PIL import Image
import io
import base64
from typing import Optional, Dict, Any
import time
import hashlib

class ScreenCapture:
    def __init__(self):
        # Disable pyautogui failsafe for automated screenshots
        pyautogui.FAILSAFE = False
        
        # Cache for screen captures to avoid redundant operations
        self.screenshot_cache = {}
        self.window_info_cache = {}
        self.cache_ttl = 30  # 30 seconds cache for screenshots
        self.window_cache_ttl = 5  # 5 seconds cache for window info
        
        # Initialize performance caching if available
        try:
            from utils.performance_manager import performance_manager
            self.use_advanced_cache = True
            self.cache = performance_manager.cache
            print("[SCREEN] Screen capture using advanced performance cache")
        except ImportError:
            self.use_advanced_cache = False
            print("[SCREEN] Screen capture using basic cache")
    
    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operations"""
        key_data = f"{operation}_{kwargs}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: float, ttl: int) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - timestamp < ttl
    
    def take_screenshot(self) -> Optional[Image.Image]:
        """Take a screenshot of the current screen with intelligent caching"""
        cache_key = "screenshot"
        
        if self.use_advanced_cache:
            # Use advanced cache with TTL
            cached_screenshot = self.cache.get(cache_key)
            if cached_screenshot:
                print("📷 Using cached screenshot")
                return cached_screenshot
        else:
            # Use basic cache
            if cache_key in self.screenshot_cache:
                cached_data, timestamp = self.screenshot_cache[cache_key]
                if self._is_cache_valid(timestamp, self.cache_ttl):
                    print("📷 Using cached screenshot")
                    return cached_data
        
        try:
            print("📷 Taking new screenshot")
            screenshot = pyautogui.screenshot()
            
            # Cache the screenshot
            if self.use_advanced_cache:
                self.cache.set(cache_key, screenshot, ttl=self.cache_ttl)
            else:
                self.screenshot_cache[cache_key] = (screenshot, time.time())
            
            return screenshot
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None
    
    def get_active_window_info(self) -> Dict[str, Any]:
        """Get information about the currently active window with caching"""
        cache_key = "active_window"
        
        if self.use_advanced_cache:
            # Use advanced cache with TTL
            cached_info = self.cache.get(cache_key)
            if cached_info:
                return cached_info
        else:
            # Use basic cache
            if cache_key in self.window_info_cache:
                cached_data, timestamp = self.window_info_cache[cache_key]
                if self._is_cache_valid(timestamp, self.window_cache_ttl):
                    return cached_data
        
        try:
            if platform.system() == "Windows":
                window_info = self._get_windows_active_window()
            elif platform.system() == "Darwin":  # macOS
                window_info = self._get_macos_active_window()
            else:  # Linux
                window_info = self._get_linux_active_window()
            
            # Cache the window info
            if self.use_advanced_cache:
                self.cache.set(cache_key, window_info, ttl=self.window_cache_ttl)
            else:
                self.window_info_cache[cache_key] = (window_info, time.time())
            
            return window_info
        except Exception as e:
            print(f"Error getting active window info: {e}")
            return {"title": "Unknown", "process": "Unknown"}
    
    def _get_windows_active_window(self) -> Dict[str, Any]:
        """Get active window info on Windows"""
        try:
            import win32gui
            import win32process
            
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            
            # Get process info
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            
            return {
                "title": window_title,
                "process": process.name(),
                "pid": pid,
                "exe": process.exe() if hasattr(process, 'exe') else "Unknown"
            }
        except Exception as e:
            return {"title": "Unknown", "process": "Unknown", "error": str(e)}
    
    def _get_macos_active_window(self) -> Dict[str, Any]:
        """Get active window info on macOS"""
        try:
            from AppKit import NSWorkspace
            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            return {
                "title": active_app.get('NSApplicationName', 'Unknown'),
                "process": active_app.get('NSApplicationName', 'Unknown'),
                "bundle_id": active_app.get('NSApplicationBundleIdentifier', 'Unknown')
            }
        except Exception as e:
            return {"title": "Unknown", "process": "Unknown", "error": str(e)}
    
    def _get_linux_active_window(self) -> Dict[str, Any]:
        """Get active window info on Linux"""
        try:
            import subprocess
            
            # Try using xdotool
            result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                window_title = result.stdout.strip()
                
                # Get process info
                pid_result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowpid'], 
                                          capture_output=True, text=True)
                if pid_result.returncode == 0:
                    pid = int(pid_result.stdout.strip())
                    process = psutil.Process(pid)
                    return {
                        "title": window_title,
                        "process": process.name(),
                        "pid": pid
                    }
                
                return {"title": window_title, "process": "Unknown"}
            
            return {"title": "Unknown", "process": "Unknown"}
        except Exception as e:
            return {"title": "Unknown", "process": "Unknown", "error": str(e)}
    
    def get_clipboard_content(self) -> str:
        """Get current clipboard content"""
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception as e:
            print(f"Error getting clipboard content: {e}")
            return ""
    
    def screenshot_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        try:
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return img_str
        except Exception as e:
            print(f"Error converting image to base64: {e}")
            return ""
    
    def get_screen_context(self) -> Dict[str, Any]:
        """Get comprehensive screen context"""
        context = {
            "timestamp": time.time(),
            "active_window": self.get_active_window_info(),
            "clipboard": self.get_clipboard_content(),
            "screenshot_available": False
        }
        
        # Optionally include screenshot
        screenshot = self.take_screenshot()
        if screenshot:
            context["screenshot_available"] = True
            context["screenshot_base64"] = self.screenshot_to_base64(screenshot)
        
        return context
    
    def is_coding_context(self, window_info: Dict[str, Any]) -> bool:
        """Determine if current context is coding-related"""
        coding_apps = [
            'code', 'vscode', 'pycharm', 'intellij', 'eclipse', 'atom', 
            'sublime', 'vim', 'emacs', 'notepad++', 'visual studio'
        ]
        
        process_name = window_info.get('process', '').lower()
        window_title = window_info.get('title', '').lower()
        
        return any(app in process_name or app in window_title for app in coding_apps)
    
    def detect_context_type(self) -> str:
        """Detect the type of current context"""
        window_info = self.get_active_window_info()
        
        if self.is_coding_context(window_info):
            return "coding"
        
        # Check for meeting apps
        meeting_apps = ['zoom', 'teams', 'meet', 'skype', 'webex', 'discord']
        process_name = window_info.get('process', '').lower()
        if any(app in process_name for app in meeting_apps):
            return "meeting"
        
        return "general" 