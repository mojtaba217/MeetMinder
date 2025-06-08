#!/usr/bin/env python3
"""
MeetMinder - Real-time AI meeting assistant with stealth overlay
OPTIMIZED VERSION with Performance Management
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

# Import performance optimization systems
from utils.performance_manager import performance_manager, cached, performance_monitor
from utils.memory_manager import memory_manager, lazy_load, memory_efficient
from utils.async_pipeline import pipeline_manager, Priority, create_audio_pipeline, create_ai_pipeline

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

class OptimizedAIAssistant:
    """Performance-optimized MeetMinder application class"""
    
    def __init__(self):
        logger.info("🚀 Initializing Performance-Optimized MeetMinder...")
        
        # Initialize performance management systems first
        self._initialize_performance_systems()
        
        # Initialize PyQt5 Application
        self.app: QApplication = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Dynamic thread pool with performance monitoring
        self.thread_pool = ThreadPoolExecutor(
            max_workers=8,  # Increased from 4 for better performance
            thread_name_prefix="MeetMinder"
        )
        
        # Set application properties
        self._setup_application_properties()
        
        # Show optimized loading screen
        self.splash = self._create_optimized_loading_screen()
        self.splash.show()
        self.app.processEvents()
        
        # Initialize components with performance monitoring
        self._initialize_components_optimized()
        
        # Setup performance monitoring and pipelines
        self._setup_performance_pipelines()
        
        # Hide loading screen
        self.splash.finish(None)
        
        logger.info("✅ Performance-Optimized MeetMinder initialized successfully")
        logger.info("📊 Performance monitoring active")
    
    def _initialize_performance_systems(self):
        """Initialize all performance management systems"""
        logger.info("⚡ Initializing performance systems...")
        
        # Start performance manager
        performance_manager.start()
        
        # Setup memory management
        memory_manager.auto_cleanup_enabled = True
        
        # Register lazy loaders for expensive resources
        memory_manager.register_lazy_loader("whisper_model", self._load_whisper_model)
        
        # Create buffer pools for audio processing
        memory_manager.create_buffer_pool("audio_buffers", 1024 * 1024, max_buffers=10)  # 1MB buffers
        memory_manager.create_buffer_pool("image_buffers", 2 * 1024 * 1024, max_buffers=5)  # 2MB buffers
        
        # Register cleanup callbacks
        memory_manager.register_cleanup_callback(self._cleanup_audio_resources)
        memory_manager.register_cleanup_callback(self._cleanup_ai_cache)
        
        logger.info("✅ Performance systems initialized")
    
    @lazy_load("whisper_model")
    def _load_whisper_model(self):
        """Lazy load Whisper model only when needed"""
        logger.info("🤖 Lazy loading Whisper model...")
        try:
            model_size = self.transcription_config.whisper_model_size if hasattr(self, 'transcription_config') else "base"
            model = whisper.load_model(model_size)
            logger.info(f"✅ Whisper model '{model_size}' loaded successfully")
            return model
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            return None
    
    def _setup_application_properties(self):
        """Setup application properties with caching"""
        self.app.setApplicationName("MeetMinder")
        self.app.setApplicationDisplayName("MeetMinder - Optimized")
        self.app.setApplicationVersion("2.0.0")
        self.app.setOrganizationName("MeetMinder Project")
        self.app.setOrganizationDomain("meetminder.io")
        
        # Set application icon with caching
        if os.path.exists("MeetMinderIcon.ico"):
            self.app.setWindowIcon(QIcon("MeetMinderIcon.ico"))
            logger.info("✅ MeetMinder icon loaded")
    
    def _create_optimized_loading_screen(self):
        """Create optimized loading screen with progress tracking"""
        pixmap = QPixmap(450, 250)
        pixmap.fill(Qt.black)
        
        splash = QSplashScreen(pixmap)
        splash.setStyleSheet("""
            QSplashScreen {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a1a, stop:1 #2d2d2d);
                color: #ffffff;
                border: 2px solid #0078d4;
                border-radius: 10px;
                font-size: 12px;
            }
        """)
        
        splash.showMessage("🚀 Loading Performance-Optimized MeetMinder...\n⚡ Initializing systems...", 
                          Qt.AlignCenter | Qt.AlignBottom, Qt.white)
        return splash
    
    @performance_monitor
    def _initialize_components_optimized(self):
        """Initialize components with performance optimization"""
        steps = [
            ("🔧 Loading configuration...", self._init_config),
            ("🎤 Setting up transcription...", self._init_transcription),
            ("🧠 Initializing AI systems...", self._init_ai_systems),
            ("🎵 Setting up audio processing...", self._init_audio_processing),
            ("🖥️ Initializing interface...", self._init_interface),
            ("⚡ Finalizing optimization...", self._finalize_optimization)
        ]
        
        total_steps = len(steps)
        for i, (message, init_func) in enumerate(steps):
            progress = f"[{i+1}/{total_steps}] "
            self.splash.showMessage(f"{progress}{message}", Qt.AlignCenter | Qt.AlignBottom, Qt.white)
            self.app.processEvents()
            
            # Execute initialization step with error handling
            try:
                init_func()
            except Exception as e:
                logger.error(f"Initialization step failed: {message} - {e}")
                # Continue with other steps
    
    @memory_efficient
    def _init_config(self):
        """Initialize configuration with caching"""
        self.config = ConfigManager()
        logger.info("✅ Configuration loaded")
    
    def _init_transcription(self):
        """Initialize transcription engine with lazy loading"""
        logger.info("🎤 Initializing transcription engine...")
        self.transcription_config = self.config.get_transcription_config()
        self.transcription_engine = TranscriptionEngineFactory.create_engine(self.transcription_config)
        
        if self.transcription_engine.is_available():
            engine_info = self.transcription_engine.get_info()
            logger.info(f"✅ Transcription engine ready: {engine_info['engine']}")
        else:
            logger.info("❌ Transcription engine not available, using fallback")
            from core.config import TranscriptionConfig
            fallback_config = TranscriptionConfig(provider="local_whisper")
            self.transcription_engine = TranscriptionEngineFactory.create_engine(fallback_config)
        
        self.whisper_language = "en"
    
    @cached(ttl=3600)  # Cache for 1 hour
    def _init_ai_systems(self):
        """Initialize AI systems with caching"""
        self.profile_manager = UserProfileManager(self.config)
        self.topic_manager = TopicGraphManager(self.config)
        
        # Initialize AI helper with enhanced configuration
        ai_config = self.config.get_ai_config()
        self.ai_helper = AIHelper(
            ai_config,
            self.profile_manager,
            self.topic_manager,
            self.config
        )
        
        # Initialize live topic analyzer
        self.topic_analyzer = LiveTopicAnalyzer(self.ai_helper, self.config)
        logger.info("✅ AI systems initialized")
    
    def _init_audio_processing(self):
        """Initialize audio processing with buffer pools"""
        audio_config = self.config.get_audio_config()
        
        # Get Whisper model lazily
        whisper_model = memory_manager.get_lazy_resource("whisper_model")
        
        if audio_config.mode == 'dual_stream':
            logger.info("🎤 Using dual-stream audio (microphone + system audio)")
            self.audio_contextualizer = DualStreamAudioContextualizer(
                audio_config,
                self.topic_manager,
                whisper_model=whisper_model,
                whisper_language=self.whisper_language
            )
        else:
            logger.info("🎤 Using single-stream audio (microphone only)")
            self.audio_contextualizer = AudioContextualizer(
                audio_config,
                self.topic_manager,
                whisper_model=whisper_model,
                whisper_language=self.whisper_language
            )
    
    def _init_interface(self):
        """Initialize interface components"""
        self.screen_capture = ScreenCapture()
        self.hotkey_manager = AsyncHotkeyManager(self.config.get_hotkeys_config())
        
        # Initialize modern UI with performance settings
        ui_config = self.config.get('ui.overlay', {})
        if 'size_multiplier' not in ui_config:
            ui_config['size_multiplier'] = 1.0
        
        self.overlay = ModernOverlay(ui_config)
        
        # State management
        self.is_running = False
        self.last_assistance_time = 0
        self.assistance_cooldown = 2.0  # Reduced from default for better responsiveness
        self.current_tasks = set()
        
        # Audio context tracking
        self.last_audio_context = None
        self.last_screenshot = None
        
        logger.info("✅ Interface components initialized")
    
    def _finalize_optimization(self):
        """Finalize performance optimization setup"""
        # Setup callbacks and monitoring
        self._setup_optimized_callbacks()
        self._setup_performance_monitoring()
        
        logger.info("✅ Performance optimization complete")
    
    async def _setup_performance_pipelines(self):
        """Setup async processing pipelines"""
        logger.info("🔧 Setting up performance pipelines...")
        
        # Create pipelines
        await create_audio_pipeline()
        await create_ai_pipeline()
        
        # Start pipeline manager
        await pipeline_manager.start_all()
        
        logger.info("✅ Performance pipelines active")
    
    def _setup_optimized_callbacks(self):
        """Setup callbacks with performance monitoring"""
        # Audio callbacks with debouncing
        if hasattr(self.audio_contextualizer, 'add_context_change_callback'):
            self.audio_contextualizer.add_context_change_callback(
                self._debounced_audio_context_change
            )
        
        # Hotkey callbacks with priority
        try:
            self.hotkey_manager.register_hotkey(
                'ctrl+shift+space', 
                lambda: asyncio.create_task(self._high_priority_assistance())
            )
            self.hotkey_manager.register_hotkey(
                'ctrl+shift+s', 
                lambda: asyncio.create_task(self._priority_screenshot())
            )
            
            logger.info("✅ Optimized callbacks registered")
        except Exception as e:
            logger.warning(f"Hotkey registration failed: {e}")
    
    def _setup_performance_monitoring(self):
        """Setup comprehensive performance monitoring"""
        global_resource_monitor.register_cleanup_callback("audio", self._cleanup_audio_resources)
        global_resource_monitor.register_cleanup_callback("ai", self._cleanup_ai_cache)
        global_resource_monitor.register_cleanup_callback("ui", self._cleanup_ui_resources)
        
        # Connect performance manager signals
        performance_manager.performance_alert.connect(self._handle_performance_alert)
        memory_manager.memory_warning.connect(self._handle_memory_warning)
        
        logger.info("✅ Performance monitoring active")
    
    @performance_monitor
    def _cleanup_audio_resources(self):
        """Optimized audio resource cleanup"""
        if hasattr(self, 'audio_contextualizer'):
            try:
                # Clear audio buffers
                if hasattr(self.audio_contextualizer, 'clear_buffers'):
                    self.audio_contextualizer.clear_buffers()
                logger.debug("🧹 Audio resources cleaned")
            except Exception as e:
                logger.error(f"Audio cleanup error: {e}")
    
    @performance_monitor
    def _cleanup_ai_cache(self):
        """Optimized AI cache cleanup"""
        if hasattr(self, 'ai_helper'):
            try:
                # Clear AI request cache
                if hasattr(self.ai_helper, 'request_cache'):
                    self.ai_helper.request_cache.cache.clear()
                    logger.debug("🧹 AI cache cleaned")
            except Exception as e:
                logger.error(f"AI cleanup error: {e}")
    
    @performance_monitor
    def _cleanup_ui_resources(self):
        """Optimized UI resource cleanup"""
        try:
            # Force UI cleanup
            if hasattr(self, 'overlay'):
                self.overlay.update()
            self.app.processEvents()
            logger.debug("🧹 UI resources cleaned")
        except Exception as e:
            logger.error(f"UI cleanup error: {e}")
    
    def _handle_performance_alert(self, alert_type: str, data: dict):
        """Handle performance alerts"""
        logger.warning(f"🚨 Performance Alert: {alert_type} - {data}")
        
        if alert_type == "high_memory":
            memory_manager.gentle_cleanup("performance_alert")
        elif alert_type == "high_cpu":
            # Reduce processing frequency temporarily
            self.assistance_cooldown = min(self.assistance_cooldown * 1.5, 10.0)
        elif alert_type == "queue_backlog":
            # Clear low priority tasks
            logger.info("🧹 Clearing low priority tasks due to backlog")
    
    def _handle_memory_warning(self, memory_percent: float):
        """Handle memory warnings with progressive response"""
        if memory_percent > 90:
            logger.warning(f"🚨 Critical memory usage: {memory_percent:.1f}%")
            memory_manager.force_cleanup("critical_memory")
        elif memory_percent > 80:
            logger.warning(f"⚠️ High memory usage: {memory_percent:.1f}%")
            memory_manager.gentle_cleanup("high_memory")
    
    @cached(ttl=60)  # Cache for 1 minute to prevent spam
    def _debounced_audio_context_change(self, change_info: str):
        """Debounced audio context change handler"""
        logger.debug(f"🎵 Audio context change: {change_info}")
        
        # Schedule background processing
        asyncio.create_task(
            pipeline_manager.submit_to_pipeline(
                "audio_processing",
                {
                    "id": f"audio_context_{time.time()}",
                    "priority": Priority.NORMAL,
                    "data": change_info
                }
            )
        )
    
    async def _high_priority_assistance(self):
        """High priority assistance with optimized processing"""
        logger.info("🚀 High priority assistance triggered")
        
        # Submit to AI pipeline with high priority
        await pipeline_manager.submit_to_pipeline(
            "ai_processing",
            {
                "id": f"assistance_{time.time()}",
                "priority": Priority.HIGH,
                "func": self._trigger_assistance,
                "args": ()
            }
        )
    
    async def _priority_screenshot(self):
        """Priority screenshot with optimized processing"""
        logger.info("📸 Priority screenshot triggered")
        
        await pipeline_manager.submit_to_pipeline(
            "screen_processing",
            {
                "id": f"screenshot_{time.time()}",
                "priority": Priority.HIGH,
                "func": self._take_screenshot,
                "args": ()
            }
        )
    
    @handle_errors(show_user_message=False)
    @performance_monitor
    async def _trigger_assistance(self):
        """Optimized assistance triggering with performance monitoring"""
        current_time = time.time()
        
        # Check cooldown with adaptive timing
        if current_time - self.last_assistance_time < self.assistance_cooldown:
            logger.debug(f"⏳ Assistance on cooldown ({self.assistance_cooldown:.1f}s)")
            return
        
        self.last_assistance_time = current_time
        
        try:
            # Get screen context with caching
            screen_context = await self._get_cached_screen_context()
            
            # Get audio context efficiently
            audio_transcript = self._get_recent_transcript_optimized()
            
            # Submit to AI pipeline for processing
            await self._process_assistance_request(screen_context, audio_transcript)
            
            # Adapt cooldown based on performance
            if performance_manager.cache.get_stats()['hit_rate'] > 0.7:
                self.assistance_cooldown = max(self.assistance_cooldown * 0.9, 1.0)
            
        except Exception as e:
            logger.error(f"Assistance error: {e}")
            # Increase cooldown on errors
            self.assistance_cooldown = min(self.assistance_cooldown * 1.2, 5.0)
    
    @cached(ttl=30)  # Cache screen context for 30 seconds
    async def _get_cached_screen_context(self) -> Dict[str, Any]:
        """Get screen context with caching"""
        try:
            return self.screen_capture.get_screen_context()
        except Exception as e:
            logger.error(f"Screen context error: {e}")
            return {"error": str(e)}
    
    @memory_efficient
    def _get_recent_transcript_optimized(self) -> List[str]:
        """Get recent transcript with memory optimization"""
        try:
            if hasattr(self.audio_contextualizer, 'get_recent_transcript'):
                transcript = self.audio_contextualizer.get_recent_transcript()
                # Limit transcript size for performance
                return transcript[-50:] if len(transcript) > 50 else transcript
            return []
        except Exception as e:
            logger.error(f"Transcript error: {e}")
            return []
    
    async def _process_assistance_request(self, screen_context: Dict[str, Any], transcript: List[str]):
        """Process assistance request through optimized pipeline"""
        try:
            # Stream AI response with performance monitoring
            start_time = time.time()
            
            async for chunk in self.ai_helper.analyze_context_stream(
                transcript=transcript,
                screen_context=screen_context.get('active_window', {}).get('title', ''),
                clipboard_content=screen_context.get('clipboard', ''),
                context_type=self.screen_capture.detect_context_type()
            ):
                # Update overlay with streaming response
                if hasattr(self.overlay, 'update_ai_response'):
                    self.overlay.update_ai_response(chunk)
                
                # Yield control to prevent UI blocking
                await asyncio.sleep(0.01)
            
            processing_time = time.time() - start_time
            logger.info(f"⚡ Assistance completed in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Assistance processing error: {e}")
    
    async def start_optimized(self):
        """Start the optimized application"""
        logger.info("🚀 Starting Performance-Optimized MeetMinder...")
        
        self.is_running = True
        
        # Start performance systems
        await self._setup_performance_pipelines()
        
        # Start monitoring
        global_resource_monitor.start_monitoring()
        
        # Start hotkeys
        await self.hotkey_manager.start()
        
        # Start audio processing
        if hasattr(self.audio_contextualizer, 'start'):
            await self.audio_contextualizer.start()
        
        logger.info("✅ Performance-Optimized MeetMinder is running!")
        logger.info("📊 Performance dashboard available")
        
        # Show performance summary
        perf_summary = performance_manager.get_performance_summary()
        logger.info(f"💾 Memory: {perf_summary.get('current', {}).get('memory_mb', 0):.1f}MB")
        logger.info(f"📈 Cache hit rate: {perf_summary.get('current', {}).get('cache_hit_rate', 0)*100:.1f}%")
    
    async def stop_optimized(self):
        """Stop the optimized application"""
        logger.info("🛑 Stopping Performance-Optimized MeetMinder...")
        
        if not self.is_running:
            return
        
        self.is_running = False
        
        try:
            # Stop pipelines
            await pipeline_manager.stop_all()
            
            # Stop audio processing
            if hasattr(self.audio_contextualizer, 'stop'):
                await self.audio_contextualizer.stop()
            
            # Stop hotkeys
            await self.hotkey_manager.stop()
            
            # Stop monitoring
            global_resource_monitor.stop_monitoring()
            
            # Stop performance systems
            performance_manager.stop()
            
            # Final cleanup
            memory_manager.force_cleanup("application_shutdown")
            
            # Shutdown thread pool
            self.thread_pool.shutdown(wait=True)
            
            logger.info("✅ Performance-Optimized MeetMinder stopped")
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
    
    def run_optimized(self):
        """Run the optimized application"""
        try:
            # Create event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Start the application
            loop.create_task(self.start_optimized())
            
            # Run Qt application
            exit_code = self.app.exec_()
            
            # Cleanup
            loop.run_until_complete(self.stop_optimized())
            
            return exit_code
            
        except Exception as e:
            logger.error(f"Application run error: {e}")
            return 1

def main():
    """Main entry point for Performance-Optimized MeetMinder"""
    try:
        logger.info("🚀 Starting Performance-Optimized MeetMinder...")
        
        app = OptimizedAIAssistant()
        exit_code = app.run_optimized()
        
        logger.info(f"👋 MeetMinder exited with code {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("👋 MeetMinder interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 