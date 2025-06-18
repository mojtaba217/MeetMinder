#!/usr/bin/env python3
"""
MeetMinder - Real-time AI meeting assistant with stealth overlay
"""

import asyncio
import threading
import time
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import whisper
from concurrent.futures import ThreadPoolExecutor
import functools

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import new logging and error handling
from utils.app_logger import logger
from utils.error_handler import handle_errors, MeetMinderError, AIServiceError, AudioError

from core.config import ConfigManager
from profile.user_profile import UserProfileManager
from profile.topic_graph import TopicGraphManager
from ai.ai_helper import AIHelper
from ai.topic_analyzer import LiveTopicAnalyzer
from audio.contextualizer import AudioContextualizer
from audio.dual_stream_contextualizer import DualStreamAudioContextualizer
from audio.transcription_engine import TranscriptionEngineFactory
from ui.modern_overlay import ModernOverlay
from ui.settings_dialog import ModernSettingsDialog
from screen.capture import ScreenCapture
from utils.hotkeys import AsyncHotkeyManager
from utils.resource_monitor import global_resource_monitor

# PyQt5 imports for the app
from PyQt5.QtWidgets import QApplication, QSplashScreen, QLabel
from PyQt5.QtCore import QTimer, QMetaObject, Qt
from PyQt5.QtGui import QIcon, QPixmap, QFont

class AIAssistant:
    """Main MeetMinder application class with enhanced error handling and logging."""
    
    def __init__(self):
        logger.info("🚀 Initializing MeetMinder...")
        
        # Initialize PyQt5 Application first
        self.app: QApplication = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # Keep app running even when window is hidden
        
        # Thread pool for background tasks (improved resource management)
        self.thread_pool = ThreadPoolExecutor(
            max_workers=4, 
            thread_name_prefix="MeetMinder"
        )
        
        # Set application properties
        self.app.setApplicationName("MeetMinder")
        self.app.setApplicationDisplayName("MeetMinder")
        self.app.setApplicationVersion("1.0.0")
        self.app.setOrganizationName("MeetMinder Project")
        self.app.setOrganizationDomain("meetminder.io")
        
        # Set application icon
        if os.path.exists("MeetMinderIcon.ico"):
            self.app.setWindowIcon(QIcon("MeetMinderIcon.ico"))
            logger.info("✅ MeetMinder icon loaded")
        
        # Show loading screen
        self.splash = self._create_loading_screen()
        self.splash.show()
        self.app.processEvents()  # Make sure splash is visible
        
        # Initialize components with progress updates
        self._initialize_components()
        
        # Hide loading screen
        self.splash.finish(None)
        
        logger.info("✓ MeetMinder initialized successfully")
        logger.info("🚀 Ready to start!")
    
    def _create_loading_screen(self):
        """Create a simple loading screen"""
        # Create a simple pixmap for the splash screen
        pixmap = QPixmap(400, 200)
        pixmap.fill(Qt.black)
        
        splash = QSplashScreen(pixmap)
        splash.setStyleSheet("""
            QSplashScreen {
                background: #1a1a1a;
                color: #ffffff;
                border: 2px solid #0078d4;
                border-radius: 8px;
            }
        """)
        
        # Show loading message
        splash.showMessage("🚀 Loading MeetMinder...\nPlease wait...", 
                          Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        return splash
    
    def _initialize_components(self):
        """Initialize all MeetMinder components with progress updates"""
        self.splash.showMessage("🔧 Loading configuration...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        self.app.processEvents()
        
        # Load configuration
        self.config = ConfigManager()
        
        self.splash.showMessage("🎤 Initializing transcription engine...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        self.app.processEvents()
        
        # Initialize transcription engine
        logger.info("🎤 Initializing transcription engine...")
        self.transcription_config = self.config.get_transcription_config()
        self.transcription_engine = TranscriptionEngineFactory.create_engine(self.transcription_config)
        
        if self.transcription_engine.is_available():
            engine_info = self.transcription_engine.get_info()
            logger.info(f"✅ Transcription engine ready: {engine_info['engine']}")
        else:
            logger.info("❌ Transcription engine not available")
            logger.info("   Falling back to local Whisper...")
            # Fallback to local Whisper
            from core.config import TranscriptionConfig
            fallback_config = TranscriptionConfig(provider="local_whisper")
            self.transcription_engine = TranscriptionEngineFactory.create_engine(fallback_config)
        
        self.splash.showMessage("🤖 Loading AI models...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        self.app.processEvents()
        
        # Load Whisper model for backward compatibility (if using local Whisper)
        self.whisper_model = None
        self.whisper_language = "en"
        
        if self.transcription_config.provider == "local_whisper":
            logger.info("📥 Loading Whisper model...")
            try:
                model_size = self.transcription_config.whisper_model_size
                logger.info(f"   Model size: {model_size}")
                
                # Load the model
                self.whisper_model = whisper.load_model(model_size)
                logger.info("✓ Whisper model loaded successfully")
                
                # Set language to English
                self.whisper_language = "en"
                logger.info(f"✓ Language set to: English")
                
            except Exception as e:
                logger.info(f"❌ Failed to load Whisper model: {e}")
                logger.info("   Please ensure Whisper is installed: pip install openai-whisper")
                sys.exit(1)
        
        self.splash.showMessage("🧠 Initializing AI components...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        self.app.processEvents()
        
        # Initialize components
        self.profile_manager = UserProfileManager(self.config)
        self.topic_manager = TopicGraphManager(self.config)
        
        # Initialize AI helper with enhanced configuration
        ai_config = self.config.get_ai_config()
        self.ai_helper = AIHelper(
            ai_config,
            self.profile_manager,
            self.topic_manager,
            self.config  # Pass config manager for assistant settings
        )
        
        # Initialize live topic analyzer
        self.topic_analyzer = LiveTopicAnalyzer(self.ai_helper, self.config)
        
        self.splash.showMessage("🎵 Setting up audio processing...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        self.app.processEvents()
        
        # Choose audio contextualizer based on configuration
        audio_config = self.config.get_audio_config()
        if audio_config.mode == 'dual_stream':
            logger.info("🎤 Using dual-stream audio (microphone + system audio)")
            self.audio_contextualizer = DualStreamAudioContextualizer(
                audio_config,
                self.topic_manager,
                whisper_model=self.whisper_model,  # Pass pre-loaded model
                whisper_language=self.whisper_language
            )
        else:
            logger.info("🎤 Using single-stream audio (microphone only)")
            self.audio_contextualizer = AudioContextualizer(
                audio_config,
                self.topic_manager,
                whisper_model=self.whisper_model,  # Pass pre-loaded model
                whisper_language=self.whisper_language
            )
        
        self.splash.showMessage("🖥️ Initializing interface...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        self.app.processEvents()
        
        self.screen_capture = ScreenCapture()
        self.hotkey_manager = AsyncHotkeyManager(self.config.get_hotkeys_config())
        
        # Initialize modern UI
        ui_config = self.config.get('ui.overlay', {})
        # Add size multiplier with default value
        if 'size_multiplier' not in ui_config:
            ui_config['size_multiplier'] = 1.0
        
        self.overlay = ModernOverlay(ui_config)
        
        # State management
        self.is_running = False
        self.current_context_type = "general"
        
        self.splash.showMessage("🔍 Initializing monitoring systems...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        self.app.processEvents()
        
        # Initialize resource monitoring
        self._setup_resource_monitoring()
        
        self.splash.showMessage("⚙️ Finalizing setup...", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        self.app.processEvents()
        
        # Setup callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Setup callbacks for various components"""
        
        # Audio context change callbacks
        self.audio_contextualizer.add_context_change_callback(
            self._on_audio_context_change
        )
        
        # Modern UI callbacks
        self.overlay.set_ask_ai_callback(self._trigger_assistance_sync)
        self.overlay.set_background_ai_callback(self._trigger_assistance_background)
        self.overlay.set_toggle_mic_callback(self._on_mic_toggle)
        self.overlay.set_settings_callback(self._open_settings)
        self.overlay.set_close_app_callback(self._close_application)  # New close callback
        
        # Hotkey callbacks - these need to be thread-safe
        self.hotkey_manager.register_callback('trigger_assistance', self._trigger_assistance_threadsafe)
        self.hotkey_manager.register_callback('take_screenshot', self._take_screenshot_threadsafe)
        self.hotkey_manager.register_callback('toggle_overlay', self._toggle_overlay_threadsafe)
        self.hotkey_manager.register_callback('move_left', lambda: self._move_overlay_threadsafe('left'))
        self.hotkey_manager.register_callback('move_right', lambda: self._move_overlay_threadsafe('right'))
        self.hotkey_manager.register_callback('move_up', lambda: self._move_overlay_threadsafe('up'))
        self.hotkey_manager.register_callback('move_down', lambda: self._move_overlay_threadsafe('down'))
        self.hotkey_manager.register_callback('emergency_reset', self._emergency_reset_threadsafe)
    
    def _setup_resource_monitoring(self):
        """Setup resource monitoring and cleanup systems"""
        try:
            logger.info("🔍 Setting up resource monitoring...")
            
            # Register cleanup callbacks for our components
            global_resource_monitor.register_cleanup_callback(
                "audio_contextualizer", 
                lambda: self._cleanup_audio_resources()
            )
            
            global_resource_monitor.register_cleanup_callback(
                "ai_helper", 
                lambda: self._cleanup_ai_resources()
            )
            
            global_resource_monitor.register_cleanup_callback(
                "overlay_ui", 
                lambda: self._cleanup_ui_resources()
            )
            
            # Connect resource warning signals
            global_resource_monitor.memory_warning.connect(self._on_memory_warning)
            global_resource_monitor.cpu_warning.connect(self._on_cpu_warning)
            global_resource_monitor.cleanup_triggered.connect(self._on_cleanup_triggered)
            
            # Start monitoring
            global_resource_monitor.start_monitoring()
            logger.info("✅ Resource monitoring active")
            
        except Exception as e:
            logger.info(f"❌ Error setting up resource monitoring: {e}")
    
    def _cleanup_audio_resources(self):
        """Cleanup audio processing resources"""
        try:
            if hasattr(self.audio_contextualizer, 'clear_buffers'):
                self.audio_contextualizer.clear_buffers()
            logger.info("🧹 Audio resources cleaned")
        except Exception as e:
            logger.info(f"❌ Error cleaning audio resources: {e}")
    
    def _cleanup_ai_resources(self):
        """Cleanup AI helper resources"""
        try:
            if hasattr(self.ai_helper, 'request_cache'):
                self.ai_helper.request_cache.cache.clear()
                self.ai_helper.request_cache.timestamps.clear()
            logger.info("🧹 AI resources cleaned")
        except Exception as e:
            logger.info(f"❌ Error cleaning AI resources: {e}")
    
    def _cleanup_ui_resources(self):
        """Cleanup UI resources"""
        try:
            if hasattr(self.overlay, 'clear_all_content'):
                self.overlay.clear_all_content()
            logger.info("🧹 UI resources cleaned")
        except Exception as e:
            logger.info(f"❌ Error cleaning UI resources: {e}")
    
    def _on_memory_warning(self, memory_percent: float):
        """Handle memory warning"""
        logger.info(f"⚠️ Memory warning: {memory_percent:.1f}% usage")
        # Update overlay with warning if needed
        if hasattr(self.overlay, 'show_warning'):
            self.overlay.show_warning(f"High memory usage: {memory_percent:.1f}%")
    
    def _on_cpu_warning(self, cpu_percent: float):
        """Handle CPU warning"""
        logger.info(f"⚠️ CPU warning: {cpu_percent:.1f}% usage")
    
    def _on_cleanup_triggered(self, reason: str):
        """Handle cleanup trigger"""
        logger.info(f"🧹 Cleanup triggered: {reason}")
        # Force garbage collection
        import gc
        gc.collect()
    
    def _close_application(self):
        """Close the entire application"""
        logger.info("🚪 Closing MeetMinder...")
        self.stop()
        self.app.quit()
    
    # Thread-safe wrapper methods for hotkey callbacks
    def _trigger_assistance_threadsafe(self):
        """Thread-safe wrapper for trigger assistance"""
        QMetaObject.invokeMethod(self.overlay, "_queue_trigger_assistance", Qt.QueuedConnection)
    
    def _take_screenshot_threadsafe(self):
        """Thread-safe wrapper for take screenshot"""
        QMetaObject.invokeMethod(self.overlay, "_queue_take_screenshot", Qt.QueuedConnection)
    
    def _toggle_overlay_threadsafe(self):
        """Thread-safe wrapper for toggle overlay"""
        QMetaObject.invokeMethod(self.overlay, "toggle_visibility", Qt.QueuedConnection)
    
    def _move_overlay_threadsafe(self, direction: str):
        """Thread-safe wrapper for move overlay"""
        # For now, just print since moving isn't implemented in modern UI
        logger.info(f"📱 Moving overlay {direction} (not yet implemented in modern UI)")
    
    def _emergency_reset_threadsafe(self):
        """Thread-safe wrapper for emergency reset"""
        logger.info("🚨 Emergency reset triggered from hotkey!")
        # For emergency reset, we can restart the application
        self.app.quit()
    
    async def start(self):
        """Start MeetMinder"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("🎯 Starting MeetMinder...")
        
        try:
            # Start audio processing
            self.audio_contextualizer.start_continuous_capture()
            
            # Start hotkey listening
            await self.hotkey_manager.start_listening()
            
            # Update topic analysis in overlay
            await self._update_overlay_topic_analysis()
            
            logger.info("✅ MeetMinder is now running!")
            logger.info("💡 Press Ctrl+Space to trigger assistance")
            logger.info("💡 Press Ctrl+B to toggle overlay")
            logger.info("💡 Press Ctrl+Shift+R for emergency reset")
            
            # Keep the main loop running
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutting down MeetMinder...")
            await self.stop()
        except Exception as e:
            logger.info(f"❌ Error running MeetMinder: {e}")
            await self.stop()
    
    async def stop(self):
        """Stop MeetMinder"""
        if not self.is_running:
            return
            
        self.is_running = False
        logger.info("🛑 Stopping MeetMinder...")
        
        try:
            # Stop resource monitoring
            global_resource_monitor.stop_monitoring()
            
            # Stop components
            self.audio_contextualizer.stop()
            await self.hotkey_manager.stop_listening()
            
            # Cleanup thread pool
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
            
            logger.info("✅ MeetMinder stopped successfully")
            
        except Exception as e:
            logger.info(f"❌ Error stopping MeetMinder: {e}")
    
    @handle_errors(show_user_message=False)
    async def _trigger_assistance(self):
        """Trigger AI assistance based on current context"""
        try:
            logger.info("🤖 Triggering AI assistance...")
            
            # Get current context
            screen_context = self.screen_capture.get_screen_context()
            self.current_context_type = self.screen_capture.detect_context_type()
            
            # Get recent transcript
            transcript_data = self.audio_contextualizer.get_recent_transcript_with_topics()
            transcript = transcript_data['transcript']
            
            # Update overlay with topic analysis
            await self._update_overlay_topic_analysis(transcript)
            
            # Show overlay
            self.overlay.show_overlay()
            
            # Clear previous AI response
            self.overlay.update_ai_response("🤔 Analyzing context...")
            
            # Stream AI response
            self.overlay.update_ai_response("")  # Clear the analyzing message
            
            async for chunk in self.ai_helper.analyze_context_stream(
                transcript=transcript,
                screen_context=f"{screen_context['active_window']['title']} - {screen_context['active_window']['process']}",
                clipboard_content=screen_context.get('clipboard', ''),
                context_type=self.current_context_type
            ):
                self.overlay.append_ai_response(chunk)
                
        except Exception as e:
            logger.info(f"❌ Error triggering assistance: {e}")
            self.overlay.update_ai_response(f"Error: {e}")
    
    @handle_errors(show_user_message=False)
    def _trigger_assistance_background(self):
        """Background-safe AI assistance that uses signal-based UI updates"""
        try:
            logger.info("🤖 Running AI assistance in background thread...")
            
            # Get current context
            screen_context = self.screen_capture.get_screen_context()
            self.current_context_type = self.screen_capture.detect_context_type()
            
            # Get recent transcript
            transcript_data = self.audio_contextualizer.get_recent_transcript_with_topics()
            transcript = transcript_data['transcript']
            
            # Update topic analysis using thread-safe method
            try:
                threading.Thread(
                    target=lambda: self._update_overlay_topic_analysis_sync(transcript),
                    daemon=True
                ).start()
            except Exception as e:
                logger.info(f"❌ Error updating topic analysis: {e}")
            
            # Clear previous AI response using thread-safe method
            self.overlay.update_ai_response_threadsafe("🤔 Analyzing context...")
            
            # Stream AI response using thread-safe append method
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Clear the analyzing message
                self.overlay.update_ai_response_threadsafe("")
                
                # Stream the response
                async def stream_response():
                    async for chunk in self.ai_helper.analyze_context_stream(
                        transcript=transcript,
                        screen_context=f"{screen_context['active_window']['title']} - {screen_context['active_window']['process']}",
                        clipboard_content=screen_context.get('clipboard', ''),
                        context_type=self.current_context_type
                    ):
                        self.overlay.append_ai_response_threadsafe(chunk)
                
                loop.run_until_complete(stream_response())
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.info(f"❌ Error in background AI assistance: {e}")
            self.overlay.update_ai_response_threadsafe(f"Error: {e}")
    
    def _trigger_assistance_sync(self):
        """Synchronous wrapper for UI callback"""
        # Run the async trigger assistance in a separate thread
        threading.Thread(
            target=lambda: asyncio.run(self._trigger_assistance()),
            daemon=True
        ).start()
    
    def _on_mic_toggle(self, is_recording: bool):
        """Handle microphone toggle from UI"""
        logger.info(f"🎤 Microphone {'started' if is_recording else 'stopped'} recording")
        
        if is_recording:
            # Start audio capture if not already running
            if not hasattr(self.audio_contextualizer, '_is_capturing') or not self.audio_contextualizer._is_capturing:
                logger.info("🎤 Starting audio capture...")
                self.audio_contextualizer.start_continuous_capture()
            
            # Enable transcript display automatically when recording starts
            if hasattr(self.overlay, 'toggle_transcript_visibility'):
                logger.info("📝 Enabling transcript display for recording...")
                self.overlay.toggle_transcript_visibility(True)
                
        else:
            # Optionally stop audio capture when recording is manually stopped
            # (Usually we want to keep it running for background analysis)
            logger.info("🎤 Recording stopped (audio capture continues in background)")
            
        # Update UI to reflect recording state
        try:
            if hasattr(self.overlay, 'is_recording'):
                self.overlay.is_recording = is_recording
        except Exception as e:
            logger.info(f"❌ Error updating recording state: {e}")
    
    def _open_settings(self):
        """Open settings dialog"""
        logger.info("⚙️ Opening settings...")
        try:
            # Get current configuration from the config manager
            current_config = {
                'audio': {
                    'mode': self.config.get('audio.mode', 'dual_stream'),
                    'buffer_duration_minutes': self.config.get('audio.buffer_duration_minutes', 5),
                    'processing_interval_seconds': self.config.get('audio.processing_interval_seconds', 1.6),
                    'whisper': {
                        'model_size': self.config.get('audio.whisper.model_size', 'base')
                    }
                },
                'ui': {
                    'overlay': {
                        'hide_from_sharing': self.config.get('ui.overlay.hide_from_sharing', True),
                        'auto_hide_seconds': self.config.get('ui.overlay.auto_hide_seconds', 5),
                        'size_multiplier': self.config.get('ui.overlay.size_multiplier', 1.0),
                        'position': self.config.get('ui.overlay.position', 'top_right'),
                        'show_transcript': self.config.get('ui.overlay.show_transcript', False)
                    }
                },
                'assistant': {
                    'activation_mode': self.config.get('assistant.activation_mode', 'manual'),
                    'verbosity': self.config.get('assistant.verbosity', 'standard'),
                    'response_style': self.config.get('assistant.response_style', 'professional'),
                    'auto_hide_behavior': self.config.get('assistant.auto_hide_behavior', 'timer'),
                    'input_prioritization': self.config.get('assistant.input_prioritization', 'system_audio')
                },
                'transcription': {
                    'provider': self.config.get('transcription.provider', 'local_whisper'),
                    'whisper': {
                        'model_size': self.config.get('transcription.whisper.model_size', 'base')
                    },
                    'google_speech': {
                        'language': self.config.get('transcription.google_speech.language', 'en-US')
                    },
                    'azure_speech': {
                        'language': self.config.get('transcription.azure_speech.language', 'en-US')
                    }
                },
                'hotkeys': {
                    'trigger_assistance': self.config.get('hotkeys.trigger_assistance', 'ctrl+space'),
                    'toggle_overlay': self.config.get('hotkeys.toggle_overlay', 'ctrl+b'),
                    'take_screenshot': self.config.get('hotkeys.take_screenshot', 'ctrl+h'),
                    'emergency_reset': self.config.get('hotkeys.emergency_reset', 'ctrl+shift+r')
                },
                'debug': {
                    'enabled': self.config.get('debug.enabled', False),
                    'save_audio_chunks': self.config.get('debug.save_audio_chunks', False),
                    'verbose_logging': self.config.get('debug.verbose_logging', False),
                    'save_transcriptions': self.config.get('debug.save_transcriptions', False),
                    'audio_chunk_format': self.config.get('debug.audio_chunk_format', 'wav'),
                    'max_debug_files': self.config.get('debug.max_debug_files', 100)
                }
            }
            
            logger.info(f"🔧 Current UI size multiplier: {current_config['ui']['overlay']['size_multiplier']}x")
            logger.info(f"🤖 Current AI settings: {current_config['assistant']}")
            logger.info(f"🎤 Current transcription: {current_config['transcription']['provider']}")
            
            # Create and show settings dialog
            settings_dialog = ModernSettingsDialog(current_config, self.overlay)
            settings_dialog.settings_changed.connect(self._on_settings_changed)
            settings_dialog.exec_()
            
        except Exception as e:
            logger.info(f"❌ Error opening settings: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_settings_changed(self, new_config):
        """Handle settings changes"""
        logger.info("💾 Applying settings changes...")
        try:
            # Update the configuration manager
            self.config.update_config(new_config)
            
            # Save to file
            self.config.save_config()
            
            # Apply changes that can be applied immediately
            ui_config = new_config.get('ui', {}).get('overlay', {})
            
            # Check if UI size multiplier changed
            current_multiplier = self.overlay.size_multiplier
            new_multiplier = ui_config.get('size_multiplier', current_multiplier)
            
            if new_multiplier != current_multiplier:
                logger.info(f"🎨 UI Size changing from {current_multiplier}x to {new_multiplier}x")
                # Recreate the overlay with new size
                self.overlay.hide()
                self.overlay.screen_sharing_detector.stop_detection()
                self.overlay.screen_sharing_detector.wait()
                
                # Create new overlay with updated config
                updated_ui_config = self.config.get('ui.overlay', {})
                self.overlay = ModernOverlay(updated_ui_config)
                
                # Reconnect callbacks
                self.overlay.set_ask_ai_callback(self._trigger_assistance_sync)
                self.overlay.set_background_ai_callback(self._trigger_assistance_background)
                self.overlay.set_toggle_mic_callback(self._on_mic_toggle)
                self.overlay.set_settings_callback(self._open_settings)
                self.overlay.set_close_app_callback(self._close_application)
                
                # Update with current topic analysis
                self._update_overlay_topic_analysis_sync()
                
                logger.info(f"✅ UI resized to {new_multiplier}x successfully!")
            
            
            # Check if theme changed
            current_theme = getattr(self.overlay, 'current_theme_name', 'dark')
            new_theme = ui_config.get('theme', current_theme)
            
            if new_theme != current_theme:
                logger.info(f"🎨 Theme changing from {current_theme} to {new_theme}")
                # Apply theme without recreating overlay
                self.overlay.apply_theme(new_theme)
                logger.info(f"✅ Theme updated to {new_theme} successfully!")
            
            # Check if transcript visibility changed
            current_transcript = getattr(self.overlay, 'show_transcript', False)
            new_transcript = ui_config.get('show_transcript', current_transcript)
            
            if new_transcript != current_transcript:
                logger.info(f"📝 Transcript visibility changing from {current_transcript} to {new_transcript}")
                # Recreate the overlay with new transcript setting
                self.overlay.hide()
                self.overlay.screen_sharing_detector.stop_detection()
                self.overlay.screen_sharing_detector.wait()
                
                # Create new overlay with updated config
                updated_ui_config = self.config.get('ui.overlay', {})
                self.overlay = ModernOverlay(updated_ui_config)
                
                # Reconnect callbacks
                self.overlay.set_ask_ai_callback(self._trigger_assistance_sync)
                self.overlay.set_background_ai_callback(self._trigger_assistance_background)
                self.overlay.set_toggle_mic_callback(self._on_mic_toggle)
                self.overlay.set_settings_callback(self._open_settings)
                self.overlay.set_close_app_callback(self._close_application)
                
                # Update with current topic analysis
                self._update_overlay_topic_analysis_sync()
                
                logger.info(f"✅ Transcript visibility updated to {'shown' if new_transcript else 'hidden'} successfully!")
            
            # Apply assistant configuration changes
            if 'assistant' in new_config:
                assistant_changes = new_config['assistant']
                logger.info(f"🤖 Assistant settings updated: {list(assistant_changes.keys())}")
                
                # Update AI helper with new assistant config
                assistant_config = self.config.get_assistant_config()
                self.ai_helper.update_assistant_config(assistant_config)
            
            # Apply transcription engine changes
            if 'transcription' in new_config:
                transcription_changes = new_config['transcription']
                logger.info(f"🎤 Transcription settings updated: {list(transcription_changes.keys())}")
                logger.info("⚠️  Transcription changes will take effect after restart")
            
            # Apply other immediate changes
            if 'audio' in new_config:
                audio_changes = new_config['audio']
                logger.info(f"🎤 Audio settings updated: {list(audio_changes.keys())}")
                logger.info("⚠️  Audio changes will take effect after restart")
            
            if 'hotkeys' in new_config:
                hotkey_changes = new_config['hotkeys'] 
                logger.info(f"⌨️  Hotkey settings updated: {list(hotkey_changes.keys())}")
                logger.info("⚠️  Hotkey changes will take effect after restart")
            
            # Apply debug settings immediately
            if 'debug' in new_config:
                debug_changes = new_config['debug']
                logger.info(f"🐞 Debug settings updated: {list(debug_changes.keys())}")
                
                # Update audio contextualizer debug settings
                if hasattr(self.audio_contextualizer, 'update_debug_config'):
                    self.audio_contextualizer.update_debug_config(debug_changes)
                    logger.info("✅ Debug settings applied to audio contextualizer")
                else:
                    logger.info("⚠️  Debug settings will take effect after restart")
            
            logger.info("✅ Settings saved and applied successfully!")
            
        except Exception as e:
            logger.info(f"❌ Error applying settings: {e}")
            import traceback
            traceback.print_exc()
    
    async def _take_screenshot(self):
        """Take a screenshot and provide context"""
        try:
            logger.info("📸 Taking screenshot...")
            screenshot = self.screen_capture.take_screenshot()
            if screenshot:
                # Save screenshot with timestamp
                timestamp = int(time.time())
                screenshot_path = f"logs/screenshot_{timestamp}.png"
                os.makedirs("logs", exist_ok=True)
                screenshot.save(screenshot_path)
                logger.info(f"✅ Screenshot saved: {screenshot_path}")
                
                # Show brief notification in overlay
                self.overlay.show_overlay()
                self.overlay.update_ai_response(f"📸 Screenshot saved: {screenshot_path}")
            else:
                logger.info("❌ Failed to take screenshot")
                
        except Exception as e:
            logger.info(f"❌ Error taking screenshot: {e}")
    
    def _toggle_overlay(self):
        """Toggle overlay visibility"""
        try:
            self.overlay.toggle_visibility()
        except Exception as e:
            logger.info(f"❌ Error toggling overlay: {e}")
    
    def _move_overlay(self, direction: str):
        """Move overlay in specified direction (placeholder for modern UI)"""
        try:
            logger.info(f"📱 Moving overlay {direction}")
            # TODO: Implement overlay positioning for modern UI
        except Exception as e:
            logger.info(f"❌ Error moving overlay: {e}")
    
    async def _emergency_reset(self):
        """Emergency reset - stop and restart"""
        try:
            logger.info("🚨 Emergency reset triggered!")
            await self.stop()
            await asyncio.sleep(2)
            await self.start()
        except Exception as e:
            logger.info(f"❌ Error during emergency reset: {e}")
    
    def _on_audio_context_change(self, change_info: str):
        """Handle audio context changes"""
        try:
            logger.info(f"🎵 Audio context change: {change_info}")
            
            # Update topic analysis when audio context changes
            if "system_audio:" in change_info or "user_voice:" in change_info:
                # Get recent transcript and update topic analysis
                transcript_data = self.audio_contextualizer.get_recent_transcript_with_topics()
                transcript = transcript_data['transcript']
                
                # Run topic analysis in background
                threading.Thread(
                    target=lambda: self._update_overlay_topic_analysis_sync(transcript),
                    daemon=True
                ).start()
            
            # Log audio transcriptions with detailed debugging
            if "system_audio:" in change_info:
                transcript = change_info.split("system_audio: ", 1)[1]
                timestamp = time.strftime("%H:%M:%S")
                
                # Detailed logging for system audio
                logger.info(f"🔊 [SYSTEM] [{timestamp}] {transcript}")
                logger.info(f"🔍 DEBUG: System audio transcription detected")
                logger.info(f"    📝 Text: '{transcript}'")
                logger.info(f"    📏 Length: {len(transcript)} characters")
                logger.info(f"    🎯 Words: {len(transcript.split())} words")
                
                # Save to debug log
                os.makedirs("debug_logs", exist_ok=True)
                debug_log_file = f"debug_logs/system_transcriptions_{time.strftime('%Y%m%d')}.txt"
                with open(debug_log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{timestamp}] SYSTEM: {transcript}\n")
                
                # Check if this looks like real content vs noise
                suspicious_indicators = ['醒', 'кра', 'Fugiao', 'forady']
                if any(indicator in transcript for indicator in suspicious_indicators):
                    logger.info(f"⚠️  SUSPICIOUS: Transcript contains non-English characters or gibberish")
                    logger.info(f"    💡 This suggests audio capture issue or wrong source")
                
                # Update overlay transcript if enabled
                try:
                    self.overlay.update_transcript_threadsafe(f"[SYSTEM] {transcript}")
                except Exception as e:
                    logger.info(f"❌ Error updating overlay transcript: {e}")
                
            elif "user_voice:" in change_info:
                transcript = change_info.split("user_voice: ", 1)[1]
                timestamp = time.strftime("%H:%M:%S")
                
                # Detailed logging for microphone
                logger.info(f"🗣️  [USER] [{timestamp}] {transcript}")
                logger.info(f"🔍 DEBUG: Microphone transcription detected")
                logger.info(f"    📝 Text: '{transcript}'")
                logger.info(f"    📏 Length: {len(transcript)} characters")
                
                # Save to debug log
                debug_log_file = f"debug_logs/mic_transcriptions_{time.strftime('%Y%m%d')}.txt"
                with open(debug_log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{timestamp}] USER: {transcript}\n")
            
            # Log audio device information
            if hasattr(self.audio_contextualizer, 'system_audio_capture'):
                if self.audio_contextualizer.system_audio_capture:
                    device_info = self.audio_contextualizer.system_audio_capture.get_device_info()
                    logger.info(f"🎤 DEVICE INFO: {device_info['name']} at {device_info['defaultSampleRate']}Hz")
            
            if "solo_mode_activated" in change_info:
                self.current_context_type = "general"
                logger.info("🔇 Solo mode activated - switching to screen-only context")
            elif "topic_detected" in change_info:
                topic = change_info.split(": ", 1)[1]
                logger.info(f"🎯 Topic detected: {topic}")
            elif "content_consumption_mode" in change_info:
                self.current_context_type = "learning"
                logger.info("📺 Content consumption mode - you're listening to something")
                logger.info("🔍 DEBUG: System detected audio consumption (YouTube, etc.)")
                self._display_recent_transcript("system")
            elif "meeting_mode_active" in change_info:
                self.current_context_type = "meeting"
                logger.info("🎪 Meeting mode - active conversation detected")
                self._display_recent_transcript("both")
            elif "solo_recording_mode" in change_info:
                self.current_context_type = "dictation"
                logger.info("🎤 Solo recording mode - you're speaking")
                self._display_recent_transcript("microphone")
                
        except Exception as e:
            logger.info(f"❌ Error handling audio context change: {e}")
            import traceback
            traceback.print_exc()
    
    def _display_recent_transcript(self, source: str = "both"):
        """Display recent transcript from specified source"""
        try:
            transcript_data = self.audio_contextualizer.get_recent_transcript_with_topics(minutes=2)
            
            if hasattr(self.audio_contextualizer, 'get_recent_transcript'):
                # For DualStreamAudioContextualizer
                if hasattr(self.audio_contextualizer, 'microphone_transcript'):
                    recent_transcript = self.audio_contextualizer.get_recent_transcript(minutes=2, source=source)
                else:
                    # For regular AudioContextualizer  
                    recent_transcript = transcript_data.get('transcript', [])
            else:
                recent_transcript = transcript_data.get('transcript', [])
            
            if recent_transcript:
                logger.info("📝 Recent transcript:")
                for line in recent_transcript[-3:]:  # Show last 3 lines
                    logger.info(f"   {line}")
            else:
                logger.info("📝 No recent transcript available")
                
        except Exception as e:
            logger.info(f"❌ Error displaying transcript: {e}")
    
    async def _update_overlay_topic_analysis(self, transcript: list = None):
        """Update overlay with current topic analysis"""
        try:
            if not transcript:
                transcript_data = self.audio_contextualizer.get_recent_transcript_with_topics()
                transcript = transcript_data['transcript']
            
            # Get screen context for additional context
            screen_context = self.screen_capture.get_screen_context()
            context_str = f"{screen_context['active_window']['title']} - {screen_context['active_window']['process']}"
            
            # Analyze conversation flow
            analysis = await self.topic_analyzer.analyze_conversation_flow(transcript, context_str)
            
            # Update UI with analysis results
            if analysis['current_path']:
                topic_path = self.topic_analyzer.get_current_topic_display()
                self.overlay.update_topic_path(topic_path)
            else:
                self.overlay.update_topic_path("No active topic")
            
            self.overlay.update_topic_guidance(analysis['guidance'])
            self.overlay.update_conversation_flow(analysis['conversation_flow'])
            
        except Exception as e:
            logger.info(f"❌ Error updating topic analysis: {e}")
    
    def _update_overlay_topic_analysis_sync(self, transcript: list = None):
        """Synchronous wrapper for updating topic analysis"""
        try:
            # Create new event loop for this thread
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._update_overlay_topic_analysis(transcript))
            finally:
                loop.close()
        except Exception as e:
            logger.info(f"❌ Error in sync topic analysis update: {e}")
    
    def run(self):
        """Run MeetMinder with PyQt5 event loop"""
        logger.info("🎯 Starting MeetMinder...")
        
        try:
            # Start audio processing
            self.audio_contextualizer.start_continuous_capture()
            
            # Start hotkeys in background thread
            hotkey_thread = threading.Thread(
                target=lambda: asyncio.run(self.hotkey_manager.start_listening()),
                daemon=True
            )
            hotkey_thread.start()
            
            # Update topic analysis in overlay
            self._update_overlay_topic_analysis_sync()
            
            logger.info("✅ MeetMinder is now running!")
            logger.info("💡 Press Ctrl+Space to trigger assistance")
            logger.info("💡 Press Ctrl+B to toggle overlay")
            logger.info("💡 Press Ctrl+Shift+R for emergency reset")
            logger.info("💡 Click the ✕ button to close the application")
            
            # Show overlay initially
            self.overlay.show_overlay()
            
            # Run PyQt5 event loop
            sys.exit(self.app.exec_())
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutting down MeetMinder...")
            self.stop()
        except Exception as e:
            logger.info(f"❌ Error running MeetMinder: {e}")
            self.stop()
    
    def stop(self):
        """Stop MeetMinder"""
        logger.info("🛑 Stopping MeetMinder...")
        
        try:
            # Stop components
            self.audio_contextualizer.stop()
            
            logger.info("✅ MeetMinder stopped successfully")
            
        except Exception as e:
            logger.info(f"❌ Error stopping MeetMinder: {e}")
        finally:
            self.app.quit()

def main():
    """Main entry point"""
    logger.info("🎯 MeetMinder - Real-time AI Meeting Assistant")
    logger.info("=" * 50)
    
    # Create and run the assistant
    assistant = AIAssistant()
    assistant.run()

if __name__ == "__main__":
    main() 