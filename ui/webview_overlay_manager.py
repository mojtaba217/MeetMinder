"""
Lightweight Webview-based Overlay Manager
Replaces PyQt5 with native webview for drastically reduced build size
"""

import webview
import threading
import time
import sys
import json
from typing import Dict, Any, Callable, Optional
from pathlib import Path
import win32gui
import win32con
import win32api
from ctypes import windll

# Import translation system
try:
    from utils.translation_manager import get_translation_manager, t
    TRANSLATIONS_AVAILABLE = True
except ImportError:
    TRANSLATIONS_AVAILABLE = False
    def t(key: str, default: str = None, **kwargs) -> str:
        return default or key

DPI_AWARENESS_SET = False


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running as script, use project root (parent of ui folder)
        base_path = Path(__file__).parent.parent
    
    return Path(base_path) / relative_path


class ScreenSharingDetector(threading.Thread):
    """Detect screen sharing and hide overlay automatically"""
    
    def __init__(self, hide_callback, show_callback):
        super().__init__(daemon=True)
        self.hide_callback = hide_callback
        self.show_callback = show_callback
        self.running = True
        self.was_hidden = False
        self.check_interval = 1.0  # Check every second
        
    def run(self):
        """Main detection loop"""
        while self.running:
            try:
                is_sharing = self._detect_screen_sharing()
                
                if is_sharing and not self.was_hidden:
                    print("[SCREEN_SHARE] Screen sharing detected - hiding overlay")
                    self.hide_callback()
                    self.was_hidden = True
                elif not is_sharing and self.was_hidden:
                    print("[SCREEN_SHARE] Screen sharing stopped - showing overlay")
                    self.show_callback()
                    self.was_hidden = False
                    
            except Exception as e:
                print(f"[SCREEN_SHARE] Error detecting screen sharing: {e}")
            
            time.sleep(self.check_interval)
    
    def _detect_screen_sharing(self) -> bool:
        """Detect if screen sharing is active"""
        try:
            # Common screen sharing apps
            sharing_apps = [
                'zoom.exe', 'teams.exe', 'skype.exe', 
                'discord.exe', 'obs64.exe', 'obs32.exe',
                'webexmta.exe', 'slack.exe', 'meet.google.com',
                'CiscoCollabHost.exe', 'lync.exe', 'GoToMeeting.exe'
            ]
            
            def enum_window_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd).lower()
                    # Check for sharing indicators in window titles
                    if any(indicator in window_text for indicator in [
                        'sharing', 'screen share', 'presenting', 
                        'you are presenting', 'screenshare'
                    ]):
                        results.append(True)
                return True
            
            results = []
            win32gui.EnumWindows(enum_window_callback, results)
            
            return len(results) > 0
            
        except Exception as e:
            print(f"[SCREEN_SHARE] Detection error: {e}")
            return False
    
    def stop_detection(self):
        """Stop the detection thread"""
        self.running = False


class WebviewOverlayAPI:
    """API class for JavaScript to Python communication"""
    
    def __init__(self, manager):
        self.manager = manager
    
    def toggle_mic(self, is_recording: bool):
        """Called when microphone button is clicked"""
        print(f"🎤 Microphone {'started' if is_recording else 'stopped'}")
        if self.manager.on_toggle_mic:
            self.manager.on_toggle_mic(is_recording)
    
    def ask_ai(self):
        """Called when Ask AI button is clicked"""
        print("[AI] Ask AI triggered")
        if self.manager.on_ask_ai:
            self.manager.on_ask_ai()
    
    def open_settings(self):
        """Called when settings button is clicked"""
        print("[SETTINGS] Settings opened")
        if self.manager.on_settings:
            self.manager.on_settings()
    
    def close_app(self):
        """Called when close button is clicked"""
        print("[EXIT] Closing application")
        if self.manager.on_close_app:
            self.manager.on_close_app()
    
    def minimize_window(self):
        """Called when minimize button is clicked"""
        print("[MINIMIZE] Minimizing window")
        if self.manager.window:
            self.manager.window.minimize()


class WebviewOverlay:
    """Lightweight overlay using webview instead of PyQt5"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.window = None
        self.hwnd = None  # Windows handle
        self.api = WebviewOverlayAPI(self)
        self.is_visible = False
        self.is_recording = False
        
        # Enhanced config options
        self.always_on_top = config.get('enhanced', {}).get('always_on_top', True)
        self.hide_from_sharing = config.get('hide_from_sharing', True)
        self.auto_hide_seconds = config.get('auto_hide_seconds', 0)
        self.opacity = config.get('opacity', 0.95)
        self.position = config.get('position', 'top_center')
        self.hide_for_screenshots = config.get('hide_for_screenshots', False)
        
        # Auto-hide timer
        self.auto_hide_timer = None
        self.auto_hide_lock = threading.Lock()
        
        # Screen sharing detector
        self.screen_sharing_detector = None
        if self.hide_from_sharing:
            self.screen_sharing_detector = ScreenSharingDetector(
                self._hide_for_screen_share,
                self._show_after_screen_share
            )
        
        # Initialize DPI awareness once per process
        self._initialize_dpi_awareness()
        
        # Callbacks
        self.on_ask_ai = None
        self.on_toggle_mic = None
        self.on_settings = None
        self.on_close_app = None
        
        # Get HTML template path
        html_path = get_resource_path("ui/webview_overlay.html")
        with open(html_path, 'r', encoding='utf-8') as f:
            self.html_content = f.read()
        
        # Initialize translations
        self.translations = {}
        if TRANSLATIONS_AVAILABLE:
            self._load_translations()
        
        print("[WEBVIEW] Webview overlay initialized")
        print(f"[WEBVIEW] Always on top: {self.always_on_top}")
        print(f"[WEBVIEW] Hide from sharing: {self.hide_from_sharing}")
        print(f"[WEBVIEW] Auto-hide: {self.auto_hide_seconds}s")
        print(f"[WEBVIEW] Position: {self.position}")
    
    def _load_translations(self):
        """Load current translations"""
        if not TRANSLATIONS_AVAILABLE:
            return
        
        try:
            translation_manager = get_translation_manager()
            # Get all UI translations matching the locale structure
            self.translations = {
                # Buttons
                'ui.buttons.ask_ai': translation_manager.t('ui.buttons.ask_ai', '🤖 Ask AI'),
                'ui.buttons.hide': translation_manager.t('ui.buttons.hide', 'Hide'),
                'ui.buttons.show': translation_manager.t('ui.buttons.show', 'Show'),
                'ui.buttons.close': translation_manager.t('ui.buttons.close', '✕'),
                
                # Tooltips
                'ui.tooltips.ask_ai': translation_manager.t('ui.tooltips.ask_ai', 'Trigger AI assistance (Ctrl+Space)'),
                'ui.tooltips.mic': translation_manager.t('ui.tooltips.mic', 'Toggle microphone recording (Ctrl+M)'),
                'ui.tooltips.settings': translation_manager.t('ui.tooltips.settings', 'Open settings (Ctrl+,)'),
                'ui.tooltips.hide': translation_manager.t('ui.tooltips.hide', 'Hide overlay'),
                'ui.tooltips.show': translation_manager.t('ui.tooltips.show', 'Show overlay'),
                'ui.tooltips.close': translation_manager.t('ui.tooltips.close', 'Close application'),
                
                # Overlay
                'ui.overlay.timer': translation_manager.t('ui.overlay.timer', '00:00'),
                'ui.overlay.shortcut': translation_manager.t('ui.overlay.shortcut', 'Ctrl+Space'),
                
                # Status
                'ui.status.waiting': translation_manager.t('ui.status.waiting', 'Ready to assist. Press Ctrl+Space or click \'Ask AI\'.'),
                'ui.status.no_active_topic': translation_manager.t('ui.status.no_active_topic', 'No active topic'),
                'ui.status.start_speaking': translation_manager.t('ui.status.start_speaking', 'Start speaking to get guidance'),
                'ui.status.analyzing': translation_manager.t('ui.status.analyzing', '🤔 Analyzing context...'),
                'ui.status.processing': translation_manager.t('ui.status.processing', '⏳ Processing...'),
            }
        except Exception as e:
            print(f"[WEBVIEW] Error loading translations: {e}")
            # Use defaults
            self.translations = {
                'ui.buttons.ask_ai': '🤖 Ask AI',
                'ui.buttons.hide': 'Hide',
                'ui.buttons.show': 'Show',
                'ui.buttons.close': '✕',
                'ui.tooltips.ask_ai': 'Trigger AI assistance (Ctrl+Space)',
                'ui.tooltips.mic': 'Toggle microphone recording (Ctrl+M)',
                'ui.tooltips.settings': 'Open settings (Ctrl+,)',
                'ui.tooltips.hide': 'Hide overlay',
                'ui.tooltips.show': 'Show overlay',
                'ui.tooltips.close': 'Close application',
                'ui.overlay.timer': '00:00',
                'ui.overlay.shortcut': 'Ctrl+Space',
                'ui.status.waiting': 'Ready to assist. Press Ctrl+Space or click \'Ask AI\'.',
                'ui.status.no_active_topic': 'No active topic',
                'ui.status.start_speaking': 'Start speaking to get guidance',
                'ui.status.analyzing': '🤔 Analyzing context...',
                'ui.status.processing': '⏳ Processing...',
            }
    
    def initialize_translations(self):
        """Initialize translations in the HTML content"""
        self._load_translations()
        self._inject_translations()
    
    def _inject_translations(self):
        """Inject translations into HTML content"""
        if not self.translations:
            return
        
        try:
            # Inject translations as JavaScript object
            translations_js = json.dumps(self.translations, ensure_ascii=False)
            script_tag = f"""
    <script>
        // Translations injected by Python
        window.translations = {translations_js};
        
        // Translation helper function
        window.t = function(key, defaultValue) {{
            return window.translations[key] || defaultValue || key;
        }};
        
        // Apply translations on page load
        document.addEventListener('DOMContentLoaded', function() {{
            updateAllTranslations();
        }});
        
        // Function to update all translations
        function updateAllTranslations() {{
            // Update elements with data-translate attribute
            document.querySelectorAll('[data-translate]').forEach(el => {{
                const key = el.getAttribute('data-translate');
                const translation = window.t(key, '');
                if (translation) {{
                    el.textContent = translation;
                }}
            }});
            
            // Update elements with data-translate-title attribute
            document.querySelectorAll('[data-translate-title]').forEach(el => {{
                const key = el.getAttribute('data-translate-title');
                const translation = window.t(key, '');
                if (translation) {{
                    el.title = translation;
                }}
            }});
        }}
        
        // Expose update function globally
        window.updateAllTranslations = updateAllTranslations;
    </script>
"""
            # Insert before closing </body> tag
            if '</body>' in self.html_content:
                self.html_content = self.html_content.replace('</body>', script_tag + '\n    </body>')
            else:
                # If no body tag, append before closing </html>
                self.html_content = self.html_content.replace('</html>', script_tag + '\n</html>')
        except Exception as e:
            print(f"[WEBVIEW] Error injecting translations: {e}")
    
    def refresh_translations(self):
        """Refresh translations after language change"""
        if not TRANSLATIONS_AVAILABLE:
            return
        
        try:
            self._load_translations()
            if self.window:
                # Update translations in the running window
                translations_js = json.dumps(self.translations, ensure_ascii=False)
                update_script = f"""
                    window.translations = {translations_js};
                    
                    // Update all translations
                    if (window.updateAllTranslations) {{
                        window.updateAllTranslations();
                    }}
                """
                self.window.evaluate_js(update_script)
                print("[WEBVIEW] Translations refreshed")
        except Exception as e:
            print(f"[WEBVIEW] Error refreshing translations: {e}")
    
    def _initialize_dpi_awareness(self):
        global DPI_AWARENESS_SET
        if DPI_AWARENESS_SET:
            return
        try:
            if hasattr(windll, "shcore"):
                # 2 = PROCESS_PER_MONITOR_DPI_AWARE
                windll.shcore.SetProcessDpiAwareness(2)
                DPI_AWARENESS_SET = True
                print("[WEBVIEW] DPI awareness set to PER_MONITOR_AWARE")
            else:
                # Fallback for older versions
                windll.user32.SetProcessDPIAware()
                DPI_AWARENESS_SET = True
                print("[WEBVIEW] DPI awareness set to SYSTEM_AWARE")
        except Exception as e:
            # Ignore error if already set or unsupported
            print(f"[WEBVIEW] DPI awareness setup failed or already applied: {e}")
            DPI_AWARENESS_SET = True

    def _get_dpi_scale(self, hwnd: Optional[int] = None) -> float:
        """Get the DPI scale factor for the given window (defaults to system DPI)"""
        scale = 1.0
        try:
            if hwnd:
                try:
                    dpi = windll.user32.GetDpiForWindow(hwnd)
                except AttributeError:
                    dpi = windll.user32.GetDpiForSystem()
            else:
                dpi = windll.user32.GetDpiForSystem()
            if dpi:
                scale = dpi / 96.0
        except Exception as e:
            print(f"[WEBVIEW] DPI detection failed, using scale 1.0: {e}")
        return scale
    
    def start(self):
        """Start the webview window"""
        # Inject translations before creating window
        if TRANSLATIONS_AVAILABLE:
            self._inject_translations()
        
        # Window configuration
        width = self.config.get('width', 800)
        height = self.config.get('height', 380)
        
        # Get transparency and frameless settings
        use_transparent = True  # Use pywebview's native transparency
        use_frameless = True  # Always use frameless for clean look
        
        # Create webview window
        self.window = webview.create_window(
            'MeetMinder',
            html=self.html_content,
            js_api=self.api,
            width=width,
            height=height,
            resizable=True,
            frameless=use_frameless,
            on_top=self.always_on_top,
            transparent=use_transparent,
            easy_drag=True  # Enable dragging
        )
        
        self.is_visible = True
        print("[WEBVIEW] Webview window created")
        
        # Apply Windows-specific settings after window creation
        def apply_windows_settings():
            time.sleep(2.0)  # Wait even longer for window to be fully initialized
            print("[WEBVIEW] Applying Windows-specific settings...")
            try:
                # First position the window
                self._position_window(width, height)
                time.sleep(0.3)  # Wait after positioning
                
                # Then apply transparency and other settings
                self._apply_window_settings()
                time.sleep(0.2)  # Wait after transparency
                
                # Verify transparency was applied
                hwnd = self._get_window_handle()
                if hwnd:
                    import win32gui
                    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    # With transparent=True, pywebview might handle styles differently
                    # but we can still check if it's working
                    pass
                
                # Start screen sharing detector
                if self.screen_sharing_detector:
                    self.screen_sharing_detector.start()
                    print("[WEBVIEW] Screen sharing detector started")
                    
            except Exception as e:
                print(f"[WEBVIEW] Error applying window settings: {e}")
                import traceback
                traceback.print_exc()
        
        # Apply settings in background
        threading.Thread(target=apply_windows_settings, daemon=True).start()
        
        # Start webview in main thread
        webview.start(debug=False)
    
    def start_in_thread(self):
        """Start webview in a separate thread"""
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        time.sleep(1)  # Give time for window to initialize
        return thread
    
    # Thread-safe UI update methods
    def update_ai_response(self, text: str):
        """Update AI response area"""
        if self.window:
            try:
                self.window.evaluate_js(f'window.updateAIResponse({repr(text)})')
            except Exception as e:
                print(f"[WEBVIEW] Error updating AI response: {e}")
    
    def append_ai_response(self, text: str):
        """Append to AI response area"""
        if self.window:
            try:
                self.window.evaluate_js(f'window.appendAIResponse({repr(text)})')
            except Exception as e:
                print(f"[WEBVIEW] Error appending AI response: {e}")
    
    def update_transcript(self, text: str):
        """Update transcript area"""
        if self.window:
            try:
                # Only show system audio
                if '[SYSTEM]' in text:
                    clean_text = text.replace('[SYSTEM] ', '').strip()
                    self.window.evaluate_js(f'window.updateTranscript({repr(clean_text)})')
            except Exception as e:
                print(f"[WEBVIEW] Error updating transcript: {e}")
    
    def update_topic_path(self, path: str):
        """Update topic analysis display"""
        if self.window:
            try:
                self.window.evaluate_js(f'window.updateTopicPath({repr(path)})')
            except Exception as e:
                print(f"❌ Error updating topic path: {e}")
    
    def update_topic_guidance(self, guidance: str):
        """Update topic guidance display"""
        if self.window:
            try:
                self.window.evaluate_js(f'window.updateTopicGuidance({repr(guidance)})')
            except Exception as e:
                print(f"❌ Error updating guidance: {e}")
    
    def update_conversation_flow(self, flow: str):
        """Update flow status display"""
        if self.window:
            try:
                self.window.evaluate_js(f'window.updateFlowStatus({repr(flow)})')
            except Exception as e:
                print(f"❌ Error updating flow: {e}")
    
    def start_recording(self):
        """Start recording (visual update)"""
        if self.window:
            try:
                self.window.evaluate_js('window.startRecording()')
                self.is_recording = True
            except Exception as e:
                print(f"❌ Error starting recording: {e}")
    
    def stop_recording(self):
        """Stop recording (visual update)"""
        if self.window:
            try:
                self.window.evaluate_js('window.stopRecording()')
                self.is_recording = False
            except Exception as e:
                print(f"❌ Error stopping recording: {e}")
    
    def show_overlay(self):
        """Show the overlay"""
        if self.window:
            try:
                self.window.show()
                self.is_visible = True
            except Exception as e:
                print(f"❌ Error showing overlay: {e}")
    
    def hide_overlay(self):
        """Hide the overlay"""
        if self.window:
            try:
                self.window.hide()
                self.is_visible = False
            except Exception as e:
                print(f"❌ Error hiding overlay: {e}")
    
    def toggle_visibility(self):
        """Toggle overlay visibility"""
        if self.is_visible:
            self.hide_overlay()
        else:
            self.show_overlay()
    
    def clear_all_content(self):
        """Clear all content areas"""
        if self.window:
            try:
                self.window.evaluate_js('window.updateAIResponse("Ready to assist...")')
                self.window.evaluate_js('window.updateTopicPath("No active topic")')
                self.window.evaluate_js('window.updateTopicGuidance("Start speaking to get guidance")')
                self.window.evaluate_js('window.updateFlowStatus("Waiting")')
            except Exception as e:
                print(f"❌ Error clearing content: {e}")
    
    # Callback setters
    def set_ask_ai_callback(self, callback: Callable):
        """Set callback for Ask AI button"""
        self.on_ask_ai = callback
    
    def set_toggle_mic_callback(self, callback: Callable):
        """Set callback for microphone toggle"""
        self.on_toggle_mic = callback
    
    def set_settings_callback(self, callback: Callable):
        """Set callback for settings button"""
        self.on_settings = callback
    
    def set_close_app_callback(self, callback: Callable):
        """Set callback for close application"""
        self.on_close_app = callback
    
    # Backward compatibility methods
    def update_ai_response_threadsafe(self, text: str):
        """Thread-safe version (same as update_ai_response for webview)"""
        self.update_ai_response(text)
    
    def append_ai_response_threadsafe(self, text: str):
        """Thread-safe version (same as append_ai_response for webview)"""
        self.append_ai_response(text)
    
    def update_transcript_threadsafe(self, text: str):
        """Thread-safe version (same as update_transcript for webview)"""
        self.update_transcript(text)
    
    def update_topic_path_threadsafe(self, path: str):
        """Thread-safe version (same as update_topic_path for webview)"""
        self.update_topic_path(path)
    
    def update_topic_guidance_threadsafe(self, guidance: str):
        """Thread-safe version (same as update_topic_guidance for webview)"""
        self.update_topic_guidance(guidance)
    
    def update_profile(self, text: str):
        """Legacy method - redirects to topic path"""
        self.update_topic_path(text)
    
    def update_profile_threadsafe(self, text: str):
        """Legacy thread-safe method - redirects to topic path"""
        self.update_topic_path(text)
    
    def _get_window_handle(self):
        """Get the Windows handle for the webview window"""
        if not self.hwnd and self.window:
            try:
                # Try to find the window by title
                def callback(hwnd, handles):
                    if win32gui.IsWindowVisible(hwnd):
                        if 'MeetMinder' in win32gui.GetWindowText(hwnd):
                            handles.append(hwnd)
                    return True
                
                handles = []
                win32gui.EnumWindows(callback, handles)
                if handles:
                    self.hwnd = handles[0]
                    print(f"[WEBVIEW] Window handle found: {self.hwnd}")
            except Exception as e:
                print(f"[WEBVIEW] Error getting window handle: {e}")
        return self.hwnd
    
    def _apply_window_settings(self):
        """Apply Windows-specific settings like transparency and always-on-top"""
        hwnd = self._get_window_handle()
        if not hwnd:
            print("[WEBVIEW] Warning: Could not get window handle")
            return
        
        try:
            # Get current window styles
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            
            print(f"[WEBVIEW] Current extended style: {ex_style}")
            print(f"[WEBVIEW] Current style: {style}")
            
            # Set always on top
            if self.always_on_top:
                win32gui.SetWindowPos(
                    hwnd, win32con.HWND_TOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                )
                print("[WEBVIEW] ✓ Set to always on top")
            
            # Redraw the window to apply changes
            win32gui.InvalidateRect(hwnd, None, True)
            win32gui.UpdateWindow(hwnd)
            print("[WEBVIEW] Window refreshed")
            
        except Exception as e:
            print(f"[WEBVIEW] ✗ Error applying window settings: {e}")
            import traceback
            traceback.print_exc()
    
    def _position_window(self, width: int, height: int):
        """Position the window based on config"""
        hwnd = self._get_window_handle()
        if not hwnd:
            print("[WEBVIEW] Warning: Could not get window handle for positioning")
            return
        
        try:
            # Get screen dimensions
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
            
            print(f"[WEBVIEW] Screen size: {screen_width}x{screen_height}")
            print(f"[WEBVIEW] Target window size: {width}x{height}")
            
            # Get current window rect to see actual size
            try:
                rect = win32gui.GetWindowRect(hwnd)
                current_width = rect[2] - rect[0]
                current_height = rect[3] - rect[1]
                print(f"[WEBVIEW] Current window size: {current_width}x{current_height}")
            except:
                pass
            
            # Adjust for DPI scaling
            scale = self._get_dpi_scale(hwnd)
            scaled_width = int(width * scale)
            scaled_height = int(height * scale)
            print(f"[WEBVIEW] DPI scale factor: {scale:.2f}")
            print(f"[WEBVIEW] Scaled window size: {scaled_width}x{scaled_height}")
            
            # Calculate position based on config
            if self.position == 'top_center':
                x = (screen_width - scaled_width) // 2
                y = 20
            elif self.position == 'top_right':
                x = screen_width - scaled_width - 20
                y = 20
            elif self.position == 'top_left':
                x = 20
                y = 20
            elif self.position == 'center':
                x = (screen_width - scaled_width) // 2
                y = (screen_height - scaled_height) // 2
            else:
                x = (screen_width - scaled_width) // 2
                y = 20
            
            print(f"[WEBVIEW] Calculated position: ({x}, {y})")
            
            # Set window position AND size
            flags = win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED
            win32gui.SetWindowPos(
                hwnd, 
                win32con.HWND_TOPMOST if self.always_on_top else win32con.HWND_TOP,
                x, y, scaled_width, scaled_height,
                flags
            )
            
            # Verify the new size
            time.sleep(0.1)
            try:
                rect = win32gui.GetWindowRect(hwnd)
                actual_width = rect[2] - rect[0]
                actual_height = rect[3] - rect[1]
                print(f"[WEBVIEW] ✓ Window positioned at ({x}, {y}) with size {actual_width}x{actual_height}")
                if abs(actual_width - scaled_width) > 10 or abs(actual_height - scaled_height) > 10:
                    print(f"[WEBVIEW] ⚠ Warning: Window size differs from scaled target!")
                    print(f"[WEBVIEW]   Target (scaled): {scaled_width}x{scaled_height}")
                    print(f"[WEBVIEW]   Actual        : {actual_width}x{actual_height}")
                else:
                    print("[WEBVIEW] ✓ Window size matches scaled configuration")
            except:
                print(f"[WEBVIEW] ✓ Window positioned at ({x}, {y})")
            
        except Exception as e:
            print(f"[WEBVIEW] ✗ Error positioning window: {e}")
            import traceback
            traceback.print_exc()
    
    def _start_auto_hide_timer(self):
        """Start auto-hide timer"""
        if self.auto_hide_seconds > 0:
            with self.auto_hide_lock:
                # Cancel existing timer
                if self.auto_hide_timer:
                    self.auto_hide_timer.cancel()
                
                # Start new timer
                self.auto_hide_timer = threading.Timer(
                    self.auto_hide_seconds,
                    self._auto_hide_callback
                )
                self.auto_hide_timer.start()
                print(f"[WEBVIEW] Auto-hide timer started ({self.auto_hide_seconds}s)")
    
    def _auto_hide_callback(self):
        """Callback for auto-hide timer"""
        print("[WEBVIEW] Auto-hide timer expired - hiding overlay")
        self.hide_overlay()
    
    def _cancel_auto_hide_timer(self):
        """Cancel auto-hide timer"""
        with self.auto_hide_lock:
            if self.auto_hide_timer:
                self.auto_hide_timer.cancel()
                self.auto_hide_timer = None
                print("[WEBVIEW] Auto-hide timer cancelled")
    
    def _hide_for_screen_share(self):
        """Hide overlay for screen sharing"""
        if self.is_visible:
            self.hide_overlay()
            print("[WEBVIEW] Hidden for screen sharing")
    
    def _show_after_screen_share(self):
        """Show overlay after screen sharing stops"""
        if not self.is_visible:
            self.show_overlay()
            print("[WEBVIEW] Shown after screen sharing")
    
    def show_overlay_with_timer(self):
        """Show overlay and start auto-hide timer"""
        self.show_overlay()
        self._start_auto_hide_timer()
    
    def update_hide_for_screenshots(self, enabled: bool):
        """Update hide for screenshots setting"""
        self.hide_for_screenshots = enabled
        print(f"[WEBVIEW] Hide for screenshots: {enabled}")
    
    def toggle_hide_for_screenshots(self):
        """Toggle hide for screenshots setting"""
        self.hide_for_screenshots = not self.hide_for_screenshots
        print(f"[WEBVIEW] Hide for screenshots toggled: {self.hide_for_screenshots}")
    
    def destroy(self):
        """Clean up and destroy the overlay"""
        # Stop screen sharing detector
        if self.screen_sharing_detector:
            self.screen_sharing_detector.stop_detection()
            print("[WEBVIEW] Screen sharing detector stopped")
        
        # Cancel auto-hide timer
        self._cancel_auto_hide_timer()
        
        # Destroy window
        if self.window:
            try:
                self.window.destroy()
            except Exception as e:
                print(f"[WEBVIEW] Error destroying window: {e}")
        print("[WEBVIEW] Webview overlay destroyed")

