"""
Lightweight Webview-based Overlay Manager
Replaces PyQt5 with native webview for drastically reduced build size
"""

import webview
import threading
import time
from typing import Dict, Any, Callable, Optional
from pathlib import Path


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
        self.api = WebviewOverlayAPI(self)
        self.is_visible = False
        self.is_recording = False
        
        # Callbacks
        self.on_ask_ai = None
        self.on_toggle_mic = None
        self.on_settings = None
        self.on_close_app = None
        
        # Get HTML template path
        html_path = Path(__file__).parent / "webview_overlay.html"
        with open(html_path, 'r', encoding='utf-8') as f:
            self.html_content = f.read()
        
        print("[WEBVIEW] Webview overlay initialized")
    
    def start(self):
        """Start the webview window"""
        # Window configuration - larger size for better UI visibility
        width = self.config.get('width', 1200)
        height = self.config.get('height', 400)
        
        # Create webview window
        self.window = webview.create_window(
            'MeetMinder',
            html=self.html_content,
            js_api=self.api,
            width=width,
            height=height,
            resizable=True,
            frameless=False,  # Show frame for easier debugging
            on_top=False,  # Don't force on top
            transparent=False,  # Disable transparency for stability
            easy_drag=False
        )
        
        self.is_visible = True
        print("[WEBVIEW] Webview window created")
        
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
    
    def destroy(self):
        """Clean up and destroy the overlay"""
        if self.window:
            try:
                self.window.destroy()
            except Exception as e:
                print(f"[WEBVIEW] Error destroying window: {e}")
        print("[WEBVIEW] Webview overlay destroyed")

