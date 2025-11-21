#!/usr/bin/env python3
"""
MeetMinder Lightweight - Real-time AI meeting assistant with minimal dependencies
Uses webview instead of PyQt5 for drastically reduced build size (15-30MB vs 150MB+)
"""

import asyncio
import threading
import time
import sys
import os
import warnings
from pathlib import Path
from typing import Optional, Dict, Any
import whisper
from concurrent.futures import ThreadPoolExecutor

# Note: Using ASCII-safe logging messages to avoid encoding issues

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import logging and error handling
from utils.app_logger import logger
from utils.error_handler import handle_errors, MeetMinderError

# Import core components
from core.config import ConfigManager
from profile.user_profile import UserProfileManager
from profile.topic_graph import TopicGraphManager
from ai.ai_helper import AIHelper
from ai.topic_analyzer import LiveTopicAnalyzer
from audio.contextualizer import AudioContextualizer
from audio.dual_stream_contextualizer import DualStreamAudioContextualizer
from audio.transcription_engine import TranscriptionEngineFactory
from screen.capture import ScreenCapture
from utils.hotkeys import AsyncHotkeyManager

# Import lightweight webview overlay instead of PyQt5
from ui.webview_overlay_manager import WebviewOverlay


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running as script, use current directory
        base_path = Path(__file__).parent
    
    return Path(base_path) / relative_path


class AIAssistantLightweight:
    """Lightweight MeetMinder application using webview instead of PyQt5"""
    
    def __init__(self):
        logger.info("[INIT] Initializing MeetMinder Lightweight...")
        
        # Thread pool for background tasks
        self.thread_pool = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="MeetMinder"
        )
        
        # Initialize components
        self._initialize_components()
        
        logger.info("[INIT] MeetMinder Lightweight initialized successfully")
        logger.info("[READY] Ready to start!")
    
    def _initialize_components(self):
        """Initialize all application components"""
        try:
            # 1. Configuration
            logger.info("[CONFIG] Loading configuration...")
            try:
                self.config = ConfigManager()
            except ValueError as config_error:
                # Handle configuration errors with user-friendly dialog
                error_msg = str(config_error)
                print("❌ Configuration Error")
                print(f"   {error_msg}")
                print("\n🔧 Quick Fixes:")
                print("   1. Check config.yaml syntax (use colons : not equals =)")
                print("   2. For offline mode: transcription.provider: local_whisper")
                print("   3. Leave ai_provider empty for transcription-only mode")
                print("   4. See OFFLINE_MODE.md for complete offline setup guide")

                # Try to show a dialog if possible, otherwise exit
                try:
                    import tkinter as tk
                    from tkinter import messagebox
                    root = tk.Tk()
                    root.withdraw()  # Hide the main window
                    messagebox.showerror("MeetMinder Configuration Error",
                                       f"{error_msg}\n\nCheck the console for detailed instructions.")
                    root.destroy()
                except ImportError:
                    pass  # Tkinter not available, continue with console message

                sys.exit(1)  # Exit with error code

            # 2. User Profile
            logger.info("[PROFILE] Loading user profile...")
            self.profile_manager = UserProfileManager(self.config.get('user_profile', {}))

            # 3. Topic Graph
            logger.info("[TOPIC] Loading topic graph...")
            self.topic_manager = TopicGraphManager(self.config.get('topic_graph', {}))

            # 4. AI Helper
            logger.info("[AI] Initializing AI helper...")
            ai_config = self.config.get_ai_config()

            if ai_config is None:
                logger.warning("[AI] No AI provider configured - running in transcription-only mode")
                print("🤖 AI responses disabled - transcription only mode active")
                print("   Configure an AI provider in config.yaml for intelligent assistance")
                self.ai_helper = AIHelper(
                    None,  # No AI config
                    self.profile_manager,
                    self.topic_manager,
                    self.config
                )
            else:
                self.ai_helper = AIHelper(
                    ai_config,
                    self.profile_manager,
                    self.topic_manager,
                    self.config
                )
            
            # 5. Topic Analyzer
            logger.info("[ANALYZER] Initializing topic analyzer...")
            # Temporarily disabled to debug
            # self.topic_analyzer = LiveTopicAnalyzer(
            #     self.topic_manager,
            #     self.config.get('topic_analyzer', {})
            # )
            self.topic_analyzer = None  # Placeholder

            # 6. Lightweight Webview Overlay
            logger.info("[UI] Initializing webview overlay...")
            self.overlay = WebviewOverlay(self.config.get('ui', {}).get('overlay', {}))
            
            # Set overlay callbacks
            self.overlay.set_ask_ai_callback(self._handle_ask_ai)
            self.overlay.set_toggle_mic_callback(self._handle_toggle_mic)
            self.overlay.set_settings_callback(self._handle_settings)
            self.overlay.set_close_app_callback(self._handle_close_app)
            
            # 7. Screen Capture
            print("[SCREEN] Initializing screen capture...")
            self.screen_capture = ScreenCapture()

            # 8. Audio Contextualizer
            print("[AUDIO] Initializing audio processing...")
            audio_config = self.config.get_audio_config()
            print(f"[AUDIO] Config mode: {audio_config.mode}")

            # Check if dual stream is enabled
            if audio_config.mode == "dual_stream":
                print("[AUDIO] Using dual-stream audio (microphone + system)")
                # Temporarily use single stream to debug
                print("[DEBUG] Temporarily switching to single-stream for debugging")
                self.audio_contextualizer = AudioContextualizer(
                    audio_config,
                    self.topic_manager,  # Pass topic_manager as second argument
                    None,  # whisper_model
                    "en"  # whisper_language
                )
            else:
                print("[AUDIO] Using single-stream audio (microphone only)")
                self.audio_contextualizer = AudioContextualizer(
                    audio_config,
                    self.topic_manager,  # Pass topic_manager as second argument
                    None,  # whisper_model
                    "en"  # whisper_language
                )

            # 9. Hotkey Manager
            print("[HOTKEY] Setting up hotkeys...")
            self.hotkey_manager = AsyncHotkeyManager(self.config.get_hotkeys_config())
            self._setup_hotkeys()
            
            # State
            self.is_running = True
            self.last_transcription = ""
            self.conversation_history = []
            
            logger.info("[SUCCESS] All components initialized")

        except Exception as e:
            error_msg = str(e)
            print(f"[DEBUG] Raw error message: {repr(error_msg)}")
            try:
                logger.error(f"[ERROR] Error initializing components: {error_msg}")
            except UnicodeEncodeError:
                # Handle Unicode encoding issues in logging
                print(f"[ERROR] Error initializing components: {error_msg}")
            raise
    
    def _setup_hotkeys(self):
        """Setup global hotkeys"""
        # Register callbacks for hotkey actions
        self.hotkey_manager.register_callback('trigger_assistance', self._hotkey_trigger_assistance)
        self.hotkey_manager.register_callback('take_screenshot', self._hotkey_take_screenshot)
        self.hotkey_manager.register_callback('toggle_overlay', self._hotkey_toggle_overlay)
        print("[HOTKEY] Callbacks registered")
    
    def _hotkey_trigger_assistance(self):
        """Hotkey callback for triggering AI assistance"""
        logger.info("[HOTKEY] Trigger AI assistance")
        self.overlay.show_overlay()
        self._handle_ask_ai()

    def _hotkey_toggle_overlay(self):
        """Hotkey callback for toggling overlay"""
        logger.info("[HOTKEY] Toggle overlay visibility")
        self.overlay.toggle_visibility()

    def _hotkey_take_screenshot(self):
        """Hotkey callback for taking screenshot"""
        logger.info("[HOTKEY] Take screenshot")
        self.overlay.update_ai_response("[SCREENSHOT] Screenshot taken!")
    
    def _handle_ask_ai(self):
        """Handle Ask AI button click"""
        logger.info("[AI] Ask AI triggered")

        # Run in background thread to avoid blocking
        self.thread_pool.submit(self._process_ai_request)
    
    def _process_ai_request(self):
        """Process AI request in background thread"""
        try:
            # Get context
            context = self._gather_context()
            
            # Update UI
            self.overlay.update_ai_response("[AI] Analyzing context...")

            # Get AI response
            prompt = self._build_prompt(context)

            # Stream response
            full_response = ""
            for chunk in self.ai_helper.get_streaming_response(prompt):
                full_response += chunk
                self.overlay.append_ai_response(chunk)

            logger.info(f"[AI] Response complete: {len(full_response)} chars")
            
        except Exception as e:
            logger.error(f"[ERROR] Error processing AI request: {e}")
            self.overlay.update_ai_response(f"[ERROR] {str(e)}")
    
    def _gather_context(self) -> Dict[str, Any]:
        """Gather context for AI prompt"""
        # Get user profile summary
        user_summary = ""
        if self.profile_manager and self.profile_manager.profile:
            profile = self.profile_manager.profile
            user_summary = f"{profile.name}"
            if profile.title:
                user_summary += f" - {profile.title}"
            if profile.skills:
                user_summary += f" | Skills: {', '.join(profile.skills[:3])}"
        
        context = {
            'transcription': self.last_transcription,
            'conversation_history': self.conversation_history[-5:],  # Last 5 messages
            'user_profile': user_summary,
            'active_topic': None if not self.topic_analyzer else "General Discussion",
        }
        
        # Get screen context
        try:
            active_window = self.screen_capture.get_active_window_title()
            context['active_window'] = active_window
        except Exception as e:
            logger.warning(f"Could not get active window: {e}")
        
        return context
    
    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build AI prompt from context"""
        prompt_parts = []
        
        # User profile
        if context.get('user_profile'):
            prompt_parts.append(f"User Profile:\n{context['user_profile']}\n")
        
        # Current topic
        if context.get('active_topic'):
            topic = context['active_topic']
            prompt_parts.append(f"Current Topic: {topic.get('name', 'Unknown')}\n")
        
        # Conversation history
        if context.get('conversation_history'):
            prompt_parts.append("Recent Conversation:\n")
            for msg in context['conversation_history']:
                prompt_parts.append(f"- {msg}\n")
        
        # Latest transcription
        if context.get('transcription'):
            prompt_parts.append(f"\nLatest Speech: {context['transcription']}\n")
        
        # Active window
        if context.get('active_window'):
            prompt_parts.append(f"Active Application: {context['active_window']}\n")
        
        prompt_parts.append("\nProvide helpful assistance based on the context above.")
        
        return "".join(prompt_parts)
    
    def _handle_toggle_mic(self, is_recording: bool):
        """Handle microphone toggle"""
        logger.info(f"[AUDIO] Microphone {'started' if is_recording else 'stopped'}")

        if is_recording:
            self.audio_contextualizer.start_continuous_capture()
        else:
            self.audio_contextualizer.stop()

    def _handle_settings(self):
        """Handle settings button click"""
        logger.info("[UI] Settings opened")
        self._open_settings_dialog()

    def _open_settings_dialog(self):
        """Open settings dialog in new webview window"""
        import webview
        import threading
        
        app_ref = self
        settings_window_ref = [None]  # Use list to allow mutation in nested scope

        # Settings API class with no instance attributes to avoid pywebview introspection recursion
        class SettingsAPI:
            __slots__ = ()
            
            def __init__(self, *args, **kwargs):
                """Accept any arguments but ignore them to prevent pywebview errors"""
                pass

            def get_settings(self):
                """Get current settings - returns only simple data types"""
                try:
                    app = app_ref
                    config = app.config
                    overlay_config = config.get('ui', {}).get('overlay', {})
                    profile = app.profile_manager.profile if app.profile_manager.profile else None

                    return {
                        'ai': {
                            'type': config.get('ai_provider.type', 'azure_openai'),
                            'api_key': config.get('ai_provider.azure_openai.api_key', ''),
                            'model': config.get('ai_provider.azure_openai.model', 'gpt-4'),
                            'response_style': config.get('ai_provider.assistant.response_style', 'balanced')
                        },
                        'audio': {
                            'mode': config.get('audio.mode', 'single_stream'),
                            'sample_rate': config.get('audio.sample_rate', 44100),
                            'language': config.get('audio.whisper_language', 'en'),
                            'auto_start': config.get('audio.auto_start', False)
                        },
                        'hotkeys': {
                            'trigger_assistance': config.get('hotkeys.trigger_assistance', 'ctrl+space'),
                            'toggle_overlay': config.get('hotkeys.toggle_overlay', 'ctrl+b'),
                            'take_screenshot': config.get('hotkeys.take_screenshot', 'ctrl+h')
                        },
                        'ui': {
                            'width': overlay_config.get('width', 800),
                            'height': overlay_config.get('height', 380),
                            'position': overlay_config.get('position', 'top_center'),
                            'opacity': overlay_config.get('opacity', 0.9),
                            'auto_hide_seconds': overlay_config.get('auto_hide_seconds', 0),
                            'always_on_top': overlay_config.get('enhanced', {}).get('always_on_top', True),
                            'hide_from_sharing': overlay_config.get('hide_from_sharing', False),
                            'hide_for_screenshots': overlay_config.get('hide_for_screenshots', False),
                            'show_transcript': overlay_config.get('show_transcript', False)
                        },
                        'user_profile': {
                            'name': profile.name if profile else '',
                            'title': profile.title if profile else '',
                            'skills': list(profile.skills) if profile and profile.skills else []
                        },
                        'advanced': {
                            'enable_cache': config.get('advanced.enable_cache', True),
                            'enable_logging': config.get('advanced.enable_logging', False),
                            'max_history': config.get('advanced.max_history', 20)
                        }
                    }
                except Exception as e:
                    logger.error(f"[SETTINGS] Error getting settings: {e}")
                    import traceback
                    traceback.print_exc()
                    return {}

            def save_settings(self, settings):
                """Save settings"""
                try:
                    app = app_ref
                    config_mgr = app.config

                    updates: Dict[str, Any] = {}

                    if 'ai' in settings:
                        ai_settings = settings['ai']
                        ai_updates: Dict[str, Any] = {
                            'type': ai_settings.get('type', config_mgr.get('ai_provider.type', 'azure_openai'))
                        }
                        # Azure OpenAI specific fields (preserve existing)
                        azure_existing = config_mgr.get('ai_provider.azure_openai', {}) or {}
                        azure_updates = {}
                        if ai_settings.get('api_key'):
                            azure_updates['api_key'] = ai_settings['api_key']
                        if ai_settings.get('model'):
                            azure_updates['model'] = ai_settings['model']
                        if azure_updates:
                            ai_updates['azure_openai'] = {**azure_existing, **azure_updates}
                        updates['ai_provider'] = ai_updates
                        # Assistant response style
                        updates.setdefault('assistant', {})['response_style'] = ai_settings.get(
                            'response_style',
                            config_mgr.get('assistant.response_style', 'balanced')
                        )

                    if 'audio' in settings:
                        audio_settings = settings['audio']
                        audio_updates: Dict[str, Any] = {
                            'mode': audio_settings.get('mode', config_mgr.get('audio.mode', 'dual_stream')),
                            'sample_rate': audio_settings.get('sample_rate', config_mgr.get('audio.sample_rate', 44100)),
                            'whisper_language': audio_settings.get(
                                'language',
                                config_mgr.get('audio.whisper_language', 'en')
                            ),
                            'auto_start': audio_settings.get('auto_start', config_mgr.get('audio.auto_start', False))
                        }
                        updates['audio'] = audio_updates

                    if 'hotkeys' in settings:
                        hotkey_settings = settings['hotkeys']
                        updates['hotkeys'] = {
                            'trigger_assistance': hotkey_settings.get(
                                'trigger_assistance', config_mgr.get('hotkeys.trigger_assistance', 'ctrl+space')
                            ),
                            'toggle_overlay': hotkey_settings.get(
                                'toggle_overlay', config_mgr.get('hotkeys.toggle_overlay', 'ctrl+b')
                            ),
                            'take_screenshot': hotkey_settings.get(
                                'take_screenshot', config_mgr.get('hotkeys.take_screenshot', 'ctrl+h')
                            )
                        }

                    if 'ui' in settings:
                        ui_settings = settings['ui']
                        overlay_updates: Dict[str, Any] = {
                            'width': ui_settings.get('width', config_mgr.get('ui.overlay.width', 800)),
                            'height': ui_settings.get('height', config_mgr.get('ui.overlay.height', 380)),
                            'position': ui_settings.get('position', config_mgr.get('ui.overlay.position', 'top_center')),
                            'opacity': ui_settings.get('opacity', config_mgr.get('ui.overlay.opacity', 0.9)),
                            'auto_hide_seconds': ui_settings.get(
                                'auto_hide_seconds', config_mgr.get('ui.overlay.auto_hide_seconds', 0)
                            ),
                            'hide_from_sharing': ui_settings.get(
                                'hide_from_sharing', config_mgr.get('ui.overlay.hide_from_sharing', False)
                            ),
                            'hide_for_screenshots': ui_settings.get(
                                'hide_for_screenshots', config_mgr.get('ui.overlay.hide_for_screenshots', False)
                            ),
                            'show_transcript': ui_settings.get(
                                'show_transcript', config_mgr.get('ui.overlay.show_transcript', False)
                            )
                        }

                        overlay_enhanced = {
                            'always_on_top': ui_settings.get(
                                'always_on_top',
                                config_mgr.get('ui.overlay.enhanced.always_on_top', True)
                            )
                        }

                        overlay_updates['enhanced'] = overlay_enhanced
                        updates.setdefault('ui', {})['overlay'] = overlay_updates

                    if 'advanced' in settings:
                        advanced_settings = settings['advanced']
                        updates['advanced'] = {
                            'enable_cache': advanced_settings.get(
                                'enable_cache', config_mgr.get('advanced.enable_cache', True)
                            ),
                            'enable_logging': advanced_settings.get(
                                'enable_logging', config_mgr.get('advanced.enable_logging', False)
                            ),
                            'max_history': advanced_settings.get(
                                'max_history', config_mgr.get('advanced.max_history', 20)
                            )
                        }

                    if updates:
                        config_mgr.update_config(updates)

                    if 'user_profile' in settings and app.profile_manager.profile:
                        profile = app.profile_manager.profile
                        profile.name = settings['user_profile']['name']
                        profile.title = settings['user_profile']['title']
                        profile.skills = settings['user_profile']['skills']

                    if updates:
                        config_mgr.save_config()
                        logger.info("[SETTINGS] Settings saved successfully")
                        return {'success': True}
                    else:
                        logger.info("[SETTINGS] No configuration changes detected")
                        return {'success': True, 'message': 'No changes'}
                except Exception as e:
                    logger.error(f"[SETTINGS] Error saving settings: {e}")
                    import traceback
                    traceback.print_exc()
                    return {'success': False, 'error': str(e)}

            def reset_settings(self):
                """Reset settings to defaults"""
                try:
                    app = app_ref
                    config_path = str(app.config.config_path)
                    app.config = ConfigManager(config_path)
                    logger.info("[SETTINGS] Settings reset to defaults")
                    return {'success': True}
                except Exception as e:
                    logger.error(f"[SETTINGS] Error resetting settings: {e}")
                    import traceback
                    traceback.print_exc()
                    return {'success': False, 'error': str(e)}

            def close_settings(self):
                """Close settings window"""
                try:
                    logger.info("[SETTINGS] Closing settings dialog")
                    if settings_window_ref[0]:
                        settings_window_ref[0].destroy()
                    return True
                except Exception as e:
                    logger.error(f"[SETTINGS] Error closing: {e}")
                    return False
        
        # Open settings window in new thread
        def open_settings_window():
            try:
                html_path = get_resource_path("ui/settings_dialog.html")
                
                # Create settings window
                settings_window = webview.create_window(
                    'MeetMinder Settings',
                    str(html_path),
                    width=900,
                    height=700,
                    resizable=True,
                    frameless=True,  # Frameless for modern look
                    on_top=True,  # Always on top
                    easy_drag=True,  # Allow dragging
                    js_api=SettingsAPI()
                )
                
                # Store window reference
                settings_window_ref[0] = settings_window
                
                # Apply Windows-specific settings for always on top
                def apply_settings_window_config():
                    import win32gui
                    import win32con
                    time.sleep(1.0)  # Wait for window creation
                    
                    try:
                        # Find settings window
                        def callback(hwnd, windows):
                            if win32gui.IsWindowVisible(hwnd):
                                if 'MeetMinder Settings' in win32gui.GetWindowText(hwnd):
                                    windows.append(hwnd)
                            return True
                        
                        windows = []
                        win32gui.EnumWindows(callback, windows)
                        
                        if windows:
                            hwnd = windows[0]
                            # Set always on top
                            win32gui.SetWindowPos(
                                hwnd, win32con.HWND_TOPMOST,
                                0, 0, 0, 0,
                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                            )
                            print("[SETTINGS] Settings window set to always on top")
                    except Exception as e:
                        print(f"[SETTINGS] Error setting always on top: {e}")
                
                # Apply settings in background
                threading.Thread(target=apply_settings_window_config, daemon=True).start()
                
                webview.start(debug=False)
            except Exception as e:
                logger.error(f"[SETTINGS] Error opening settings: {e}")
        
        # Start in new thread
        settings_thread = threading.Thread(target=open_settings_window, daemon=True)
        settings_thread.start()
    
    def _handle_close_app(self):
        """Handle close application"""
        logger.info("[APP] Closing application...")
        self.cleanup()
        sys.exit(0)
    
    def _on_transcription_complete(self, transcription: str):
        """Callback when transcription is complete"""
        if not transcription.strip():
            return

        logger.info(f"[TRANSCRIPT] {transcription}")
        self.last_transcription = transcription
        self.conversation_history.append(transcription)

        # Analyze topic
        topic_result = self.topic_analyzer.analyze_text(transcription)
        if topic_result:
            topic_path = " > ".join([t['name'] for t in topic_result.get('path', [])])
            self.overlay.update_topic_path(topic_path)

            if topic_result.get('suggestion'):
                self.overlay.update_topic_guidance(topic_result['suggestion'])

    def _on_system_audio_transcription(self, transcription: str):
        """Callback for system audio transcription"""
        if not transcription.strip():
            return

        logger.info(f"[SYSTEM_AUDIO] {transcription}")
        self.overlay.update_transcript(f"[SYSTEM] {transcription}")
    
    def run(self):
        """Run the application"""
        try:
            # Start hotkey manager (async)
            logger.info("[HOTKEY] Starting hotkey manager...")
            # Start hotkey listening in a separate thread
            import threading
            hotkey_thread = threading.Thread(
                target=lambda: asyncio.run(self.hotkey_manager.start_listening()),
                daemon=True
            )
            hotkey_thread.start()

            # Start audio processing
            logger.info("[AUDIO] Starting audio processing...")
            self.audio_contextualizer.start_continuous_capture()

            # Update overlay
            self.overlay.update_ai_response("Ready to assist! Press Ctrl+Space or click 'Ask AI'")

            # Start webview (blocking call)
            logger.info("[UI] Starting webview overlay...")
            self.overlay.start()

        except KeyboardInterrupt:
            logger.info("[APP] Keyboard interrupt received")
        except Exception as e:
            logger.error(f"[ERROR] Error in main loop: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("[CLEANUP] Cleaning up...")

        try:
            self.is_running = False

            # Stop audio
            if hasattr(self, 'audio_contextualizer'):
                self.audio_contextualizer.stop()

            # Stop hotkeys
            if hasattr(self, 'hotkey_manager'):
                # AsyncHotkeyManager uses stop_listening() not stop()
                if hasattr(self.hotkey_manager, 'stop_listening'):
                    self.hotkey_manager.is_active = False
                elif hasattr(self.hotkey_manager, 'stop'):
                    self.hotkey_manager.stop()

            # Close overlay
            if hasattr(self, 'overlay'):
                self.overlay.destroy()

            # Shutdown thread pool
            self.thread_pool.shutdown(wait=False)

            logger.info("[CLEANUP] Cleanup complete")

        except Exception as e:
            logger.error(f"[ERROR] Error during cleanup: {e}")


def main():
    """Main entry point"""
    try:
        app = AIAssistantLightweight()
        app.run()
    except Exception as e:
        try:
            logger.error(f"[FATAL] Fatal error: {e}")
        except UnicodeEncodeError:
            print(f"[FATAL] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

