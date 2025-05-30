import pyautogui
import psutil
import platform
from PIL import Image
import io
import base64
from typing import Optional, Dict, Any
import time

class ScreenCapture:
    def __init__(self):
        # Disable pyautogui failsafe for automated screenshots
        pyautogui.FAILSAFE = False
        
    def take_screenshot(self) -> Optional[Image.Image]:
        """Take a screenshot of the current screen"""
        try:
            screenshot = pyautogui.screenshot()
            return screenshot
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None
    
    def get_active_window_info(self) -> Dict[str, Any]:
        """Get information about the currently active window"""
        try:
            if platform.system() == "Windows":
                return self._get_windows_active_window()
            elif platform.system() == "Darwin":  # macOS
                return self._get_macos_active_window()
            else:  # Linux
                return self._get_linux_active_window()
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