#!/usr/bin/env python3
"""
MeetMinder Application Core
Refactored main application logic for better maintainability
"""

import asyncio
import threading
import time
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

# PyQt5 imports
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import QTimer, QMetaObject, Qt
from PyQt5.QtGui import QIcon, QPixmap

# Import logging and error handling
from utils.app_logger import logger
from utils.error_handler import handle_errors, MeetMinderError, AIServiceError, AudioError

# Import performance optimization systems
from utils.performance_manager import performance_manager, cached
from utils.memory_manager import memory_manager, lazy_load
from utils.async_pipeline import pipeline_manager, Priority

# Import core components
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

class MeetMinderApplication:
    """Refactored MeetMinder application with improved architecture"""
    
    def __init__(self):
        logger.info("🚀 Initializing MeetMinder Application...")
        
        # Initialize performance management systems first
        self._initialize_performance_systems()
        
        # Initialize PyQt5 Application
        self.app: QApplication = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Enhanced thread pool with performance monitoring
        self.thread_pool = ThreadPoolExecutor(
            max_workers=8,  # Increased from 4 for better performance
            thread_name_prefix="MeetMinder"
        )
        
        # Set application properties
        self._setup_application_properties()
        
        # Initialize core components
        self._initialize_core_components()
        
        # Setup UI and interface
        self._initialize_user_interface()
        
        # Finalize setup
        self._finalize_setup()
        
        logger.info("✅ MeetMinder Application initialized successfully")
    
    def _initialize_performance_systems(self):
        """Initialize all performance management systems"""
        logger.info("⚡ Initializing performance systems...")
        
        # Start performance manager
        performance_manager.start()
        
        # Configure memory management
        memory_manager.auto_cleanup_enabled = True
        memory_manager.warning_threshold = 75.0  # Warning at 75% memory
        memory_manager.critical_threshold = 85.0  # Critical at 85% memory
        
        # Register lazy loaders for expensive resources
        memory_manager.register_lazy_loader("whisper_model", self._load_whisper_model_lazy)
        
        # Create buffer pools for audio and image processing
        memory_manager.create_buffer_pool("audio_buffers", 1024 * 1024, max_buffers=10)  # 1MB buffers
        memory_manager.create_buffer_pool("image_buffers", 2 * 1024 * 1024, max_buffers=5)  # 2MB buffers
        
        # Register cleanup callbacks
        memory_manager.register_cleanup_callback(self._cleanup_audio_resources)
        memory_manager.register_cleanup_callback(self._cleanup_ai_cache)
        
        # Connect performance signals
        performance_manager.performance_alert.connect(self._handle_performance_alert)
        memory_manager.memory_warning.connect(self._handle_memory_warning)
        
        logger.info("✅ Performance systems initialized")
    
    def _setup_application_properties(self):
        """Setup application metadata and properties"""
        self.app.setApplicationName("MeetMinder")
        self.app.setApplicationDisplayName("MeetMinder")
        self.app.setApplicationVersion("2.0.0")  # Updated version for performance improvements
        self.app.setOrganizationName("MeetMinder Project")
        self.app.setOrganizationDomain("meetminder.io")
        
        # Set application icon
        if os.path.exists("MeetMinderIcon.ico"):
            self.app.setWindowIcon(QIcon("MeetMinderIcon.ico"))
            logger.info("✅ MeetMinder icon loaded")
    
    def _initialize_core_components(self):
        """Initialize core application components"""
        logger.info("🔧 Initializing core components...")
        
        # Configuration management
        self.config = ConfigManager()

        # Topic management (doesn't depend on others)
        self.topic_manager = TopicGraphManager(self.config.get_topic_graph_config())

        # AI components with lazy loading (initialize early for document store)
        self.ai_helper = AIHelper(
            self.config.get_ai_provider_config(),
            profile_manager=None,  # Will set later
            topic_manager=self.topic_manager,
            config_manager=self.config
        )

        # Profile management (can now use document store from ai_helper)
        self.profile_manager = UserProfileManager(
            self.config.get_profile_config(),
            document_store=self.ai_helper.document_store
        )

        # Update AI helper with profile manager
        self.ai_helper.profile_manager = self.profile_manager
        
        self.topic_analyzer = LiveTopicAnalyzer(
            topic_manager=self.topic_manager,
            ai_helper=self.ai_helper
        )
        
        # Screen capture with caching
        self.screen_capture = ScreenCapture()
        
        # Hotkey management
        self.hotkey_manager = AsyncHotkeyManager(self.config.get_hotkeys_config())
        
        logger.info("✅ Core components initialized")
    
    def _initialize_user_interface(self):
        """Initialize user interface components"""
        logger.info("🖥️ Initializing user interface...")
        
        # Modern UI with performance optimizations
        ui_config = self.config.get('ui.overlay', {})
        if 'size_multiplier' not in ui_config:
            ui_config['size_multiplier'] = 1.0
        
        self.overlay = ModernOverlay(ui_config)
        
        # State management
        self.is_running = False
        self.current_context_type = "general"
        
        logger.info("✅ User interface initialized")
    
    def _finalize_setup(self):
        """Finalize application setup"""
        logger.info("⚙️ Finalizing setup...")
        
        # Setup callbacks and monitoring
        self._setup_callbacks()
        self._setup_resource_monitoring()
        
        logger.info("✅ Application setup complete")
    
    @lazy_load("whisper_model")
    def _load_whisper_model_lazy(self):
        """Lazy load Whisper model only when needed"""
        logger.info("🤖 Lazy loading Whisper model...")
        try:
            import whisper
            # Use configuration to determine model size
            audio_config = self.config.get_audio_config()
            model_size = getattr(audio_config, 'whisper_model_size', 'base')
            
            model = whisper.load_model(model_size)
            logger.info(f"✅ Whisper model '{model_size}' loaded successfully")
            return model
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            return None
    
    def _cleanup_audio_resources(self):
        """Cleanup audio processing resources"""
        try:
            if hasattr(self, 'audio_contextualizer') and hasattr(self.audio_contextualizer, 'audio_buffer'):
                # Clear audio buffers
                self.audio_contextualizer.audio_buffer.clear()
                if hasattr(self.audio_contextualizer, 'transcript_buffer'):
                    self.audio_contextualizer.transcript_buffer.clear()
            logger.debug("🧹 Audio resources cleaned")
        except Exception as e:
            logger.error(f"❌ Error cleaning audio resources: {e}")
    
    def _cleanup_ai_cache(self):
        """Cleanup AI helper cache"""
        try:
            if hasattr(self, 'ai_helper') and hasattr(self.ai_helper, 'request_cache'):
                # Use performance manager's cache cleanup
                performance_manager.cache.clear_expired()
            logger.debug("🧹 AI cache cleaned")
        except Exception as e:
            logger.error(f"❌ Error cleaning AI cache: {e}")
    
    def _handle_performance_alert(self, alert_type: str, data: dict):
        """Handle performance alerts"""
        logger.warning(f"🚨 Performance Alert: {alert_type} - {data}")
        
        if alert_type == "high_memory":
            memory_manager.gentle_cleanup("performance_alert")
        elif alert_type == "high_cpu":
            # Show alert in overlay if available
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.update_ai_response(f"⚠️ High CPU usage: {data.get('usage', 0):.1f}%")
        elif alert_type == "queue_backlog":
            logger.info("🧹 Clearing low priority tasks due to backlog")
    
    def _handle_memory_warning(self, memory_percent: float):
        """Handle memory warnings with progressive response"""
        if memory_percent > 85:
            logger.warning(f"🚨 Critical memory usage: {memory_percent:.1f}%")
            memory_manager.force_cleanup("critical_memory")
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.update_ai_response(f"🚨 Critical memory usage: {memory_percent:.1f}% - cleaning up...")
        elif memory_percent > 75:
            logger.warning(f"⚠️ High memory usage: {memory_percent:.1f}%")
            memory_manager.gentle_cleanup("high_memory")
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.update_ai_response(f"⚠️ Memory usage: {memory_percent:.1f}% - optimizing...")
    
    def _setup_callbacks(self):
        """Setup callbacks for various components"""
        logger.info("🔗 Setting up component callbacks...")
        
        # Modern UI callbacks
        self.overlay.set_ask_ai_callback(self._trigger_assistance_sync)
        self.overlay.set_background_ai_callback(self._trigger_assistance_background)
        self.overlay.set_toggle_mic_callback(self._on_mic_toggle)
        self.overlay.set_settings_callback(self._open_settings)
        self.overlay.set_close_app_callback(self._close_application)
        
        # Hotkey callbacks - thread-safe
        self.hotkey_manager.register_callback('trigger_assistance', self._trigger_assistance_threadsafe)
        self.hotkey_manager.register_callback('take_screenshot', self._take_screenshot_threadsafe)
        self.hotkey_manager.register_callback('toggle_overlay', self._toggle_overlay_threadsafe)
        self.hotkey_manager.register_callback('emergency_reset', self._emergency_reset_threadsafe)
        self.hotkey_manager.register_callback('toggle_hide_for_screenshots', self._toggle_hide_for_screenshots_threadsafe)
        
        logger.info("✅ Callbacks configured")
    
    def _setup_resource_monitoring(self):
        """Setup resource monitoring and cleanup systems"""
        try:
            logger.info("🔍 Setting up resource monitoring...")
            
            # Connect resource warning signals
            global_resource_monitor.memory_warning.connect(self._handle_memory_warning)
            global_resource_monitor.cpu_warning.connect(self._on_cpu_warning)
            global_resource_monitor.cleanup_triggered.connect(self._on_cleanup_triggered)
            
            # Start monitoring
            global_resource_monitor.start_monitoring()
            logger.info("✅ Resource monitoring active")
            
        except Exception as e:
            logger.info(f"❌ Error setting up resource monitoring: {e}")
    
    def _on_cpu_warning(self, cpu_percent: float):
        """Handle CPU warning"""
        logger.info(f"⚠️ CPU warning: {cpu_percent:.1f}% usage")
    
    def _on_cleanup_triggered(self, reason: str):
        """Handle cleanup trigger"""
        logger.info(f"🧹 Cleanup triggered: {reason}")
        # Force garbage collection
        import gc
        gc.collect()
    
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
    
    def _emergency_reset_threadsafe(self):
        """Thread-safe wrapper for emergency reset"""
        logger.info("🚨 Emergency reset triggered from hotkey!")
        self.app.quit()
    
    def _toggle_hide_for_screenshots_threadsafe(self):
        """Thread-safe wrapper for toggle hide for screenshots"""
        logger.info("📷 Toggle hide for screenshots")
        self.overlay.toggle_hide_for_screenshots()
    
    def _trigger_assistance_sync(self):
        """Synchronous wrapper for UI callback"""
        # Submit to task queue instead of creating threads
        try:
            asyncio.create_task(
                performance_manager.task_queue.submit(
                    Priority.HIGH,
                    self._trigger_assistance_async
                )
            )
        except Exception as e:
            logger.error(f"❌ Error queuing assistance: {e}")
    
    async def _trigger_assistance_async(self):
        """Async AI assistance processing"""
        # This method will be implemented with the AI assistance logic
        logger.info("🤖 Processing AI assistance request...")
        # Implementation will be added in the next step
    
    def _trigger_assistance_background(self):
        """Background AI assistance using performance-optimized approach"""
        # This will be implemented with the background processing logic
        logger.info("🤖 Background AI assistance requested...")
        # Implementation will be added in the next step
    
    def _on_mic_toggle(self, is_recording: bool):
        """Handle microphone toggle from UI"""
        logger.info(f"🎤 Microphone {'started' if is_recording else 'stopped'} recording")
        # Implementation will be added for audio processing
    
    def _open_settings(self):
        """Open settings dialog"""
        logger.info("⚙️ Opening settings dialog...")
        # Implementation will be added for settings management
    
    def _close_application(self):
        """Close the entire application"""
        logger.info("🚪 Closing MeetMinder...")
        self.stop()
        self.app.quit()
    
    def run(self):
        """Run the MeetMinder application"""
        logger.info("🎯 Starting MeetMinder Application...")
        
        try:
            # Show overlay initially
            self.overlay.show_overlay()
            
            logger.info("✅ MeetMinder is now running!")
            logger.info("💡 Press Ctrl+Space to trigger assistance")
            logger.info("💡 Press Ctrl+B to toggle overlay")
            logger.info("💡 Click the ✕ button to close the application")
            
            # Run PyQt5 event loop
            sys.exit(self.app.exec_())
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutting down MeetMinder...")
            self.stop()
        except Exception as e:
            logger.info(f"❌ Error running MeetMinder: {e}")
            self.stop()
    
    def stop(self):
        """Stop MeetMinder application"""
        logger.info("🛑 Stopping MeetMinder Application...")
        
        try:
            # Stop performance systems
            performance_manager.stop()
            memory_manager.cleanup_all()
            
            # Stop resource monitoring
            global_resource_monitor.stop_monitoring()
            
            # Cleanup thread pool
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
            
            logger.info("✅ MeetMinder stopped successfully")
            
        except Exception as e:
            logger.info(f"❌ Error stopping MeetMinder: {e}")
        finally:
            self.app.quit() 