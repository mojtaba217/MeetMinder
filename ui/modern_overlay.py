import sys
import ctypes
import time
import threading
import psutil
import os
from typing import Dict, Any, Optional, Callable
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, QPropertyAnimation, QEasingCurve, pyqtSlot, QRect, QPoint, QSize
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                           QTextEdit, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
                           QScrollArea, QApplication, QGraphicsBlurEffect, QDesktopWidget)
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPainter, QBrush, QLinearGradient

# Import theme system
try:
    from ui.themes import ThemeManager, ThemeColors
    THEMES_AVAILABLE = True
except ImportError:
    THEMES_AVAILABLE = False
    print("⚠️ Theme system not available, using default dark theme")

# Windows API constants for screen capture protection
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001

try:
    user32 = ctypes.windll.user32
    HAS_WINDOWS_API = True
except:
    HAS_WINDOWS_API = False

class ResponsiveWidthMonitor(QThread):
    """Monitor screen width changes and content to adjust UI dynamically"""
    width_changed = pyqtSignal(int, int)  # new_width, new_height
    content_changed = pyqtSignal(int)     # content_length
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.current_screen_width = 0
        self.current_screen_height = 0
        self.current_content_length = 0
        self.check_interval = 500  # ms
        
    def run(self):
        """Monitor screen dimensions and content changes"""
        self.is_running = True
        while self.is_running:
            try:
                # Get current screen dimensions
                desktop = QApplication.desktop()
                screen_rect = desktop.screenGeometry()
                width = screen_rect.width()
                height = screen_rect.height()
                
                # Check if screen dimensions changed
                if width != self.current_screen_width or height != self.current_screen_height:
                    print(f"🖥️ Screen dimensions changed: {width}x{height}")
                    self.current_screen_width = width
                    self.current_screen_height = height
                    self.width_changed.emit(width, height)
                
                self.msleep(self.check_interval)
                
            except Exception as e:
                print(f"❌ Error in width monitoring: {e}")
                self.msleep(1000)
    
    def update_content_length(self, length: int):
        """Update content length for adaptive sizing"""
        if length != self.current_content_length:
            self.current_content_length = length
            self.content_changed.emit(length)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False

class BlurredBackgroundWidget(QWidget):
    """Widget with enhanced transparency and blur effects"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.background_opacity = 0.15
        self.blur_radius = 20
        self.gradient_intensity = 0.3
        
    def set_background_opacity(self, opacity: float):
        """Set background opacity (0.0 to 1.0)"""
        self.background_opacity = max(0.0, min(1.0, opacity))
        self.update()
    
    def set_blur_radius(self, radius: int):
        """Set blur radius"""
        self.blur_radius = max(0, radius)
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event for enhanced transparency"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(20, 20, 20, int(255 * self.background_opacity * 0.8)))
        gradient.setColorAt(0.5, QColor(30, 30, 30, int(255 * self.background_opacity)))
        gradient.setColorAt(1, QColor(20, 20, 20, int(255 * self.background_opacity * 0.6)))
        
        # Draw rounded rectangle with gradient
        painter.setBrush(QBrush(gradient))
        painter.setPen(QColor(100, 100, 100, int(255 * self.background_opacity * 2)))
        painter.drawRoundedRect(self.rect(), 12, 12)
        
        super().paintEvent(event)

class SmoothAnimationManager:
    """Manages smooth animations for professional UI transitions"""
    
    def __init__(self, widget):
        self.widget = widget
        self.animations = {}
        
    def fade_in(self, duration=300, target_opacity=1.0):
        """Smooth fade in animation"""
        if 'fade' in self.animations:
            self.animations['fade'].stop()
        
        self.animations['fade'] = QPropertyAnimation(self.widget, b"windowOpacity")
        self.animations['fade'].setDuration(duration)
        self.animations['fade'].setStartValue(0.0)
        self.animations['fade'].setEndValue(target_opacity)
        self.animations['fade'].setEasingCurve(QEasingCurve.OutCubic)
        self.animations['fade'].start()
        
    def fade_out(self, duration=200, target_opacity=0.0):
        """Smooth fade out animation"""
        if 'fade' in self.animations:
            self.animations['fade'].stop()
        
        self.animations['fade'] = QPropertyAnimation(self.widget, b"windowOpacity")
        self.animations['fade'].setDuration(duration)
        self.animations['fade'].setStartValue(self.widget.windowOpacity())
        self.animations['fade'].setEndValue(target_opacity)
        self.animations['fade'].setEasingCurve(QEasingCurve.InCubic)
        self.animations['fade'].start()
    
    def slide_expand(self, duration=400, target_height=None):
        """Smooth height expansion animation"""
        if 'expand' in self.animations:
            self.animations['expand'].stop()
        
        if target_height is None:
            target_height = self.widget.sizeHint().height()
        
        self.animations['expand'] = QPropertyAnimation(self.widget, b"maximumHeight")
        self.animations['expand'].setDuration(duration)
        self.animations['expand'].setStartValue(self.widget.height())
        self.animations['expand'].setEndValue(target_height)
        self.animations['expand'].setEasingCurve(QEasingCurve.OutQuart)
        self.animations['expand'].start()
    
    def slide_collapse(self, duration=300, target_height=60):
        """Smooth height collapse animation"""
        if 'expand' in self.animations:
            self.animations['expand'].stop()
        
        self.animations['expand'] = QPropertyAnimation(self.widget, b"maximumHeight")
        self.animations['expand'].setDuration(duration)
        self.animations['expand'].setStartValue(self.widget.height())
        self.animations['expand'].setEndValue(target_height)
        self.animations['expand'].setEasingCurve(QEasingCurve.InQuart)
        self.animations['expand'].start()

class PerformanceOptimizer:
    """Performance optimization utilities for UI"""
    
    def __init__(self):
        self.update_timers = {}
        self.debounce_delays = {
            'transcript_update': 100,  # ms
            'ai_response_update': 50,
            'metrics_update': 500,
            'width_update': 200
        }
    
    def debounce_update(self, key: str, callback: Callable, delay_ms: int = None):
        """Debounce UI updates to prevent excessive redraws"""
        if delay_ms is None:
            delay_ms = self.debounce_delays.get(key, 100)
        
        # Cancel existing timer
        if key in self.update_timers:
            self.update_timers[key].stop()
        
        # Create new timer
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        timer.start(delay_ms)
        
        self.update_timers[key] = timer

class OptimizedTextEdit(QTextEdit):
    """Optimized text edit with virtual scrolling and limited content"""
    
    def __init__(self, max_lines: int = 100, parent=None):
        super().__init__(parent)
        self.max_lines = max_lines
        self.line_count = 0
        
        # Performance settings
        self.setUndoRedoEnabled(False)
        self.document().setMaximumBlockCount(max_lines)
    
    def append_optimized(self, text: str):
        """Optimized append that manages content size"""
        # Use moveCursor and insertPlainText for better performance
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text + "\n")
        
        # Auto-scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        self.line_count += 1
        
        # Trim if too many lines (handled by document().setMaximumBlockCount)
        if self.line_count > self.max_lines:
            self.line_count = self.max_lines

class MicrophoneTimer(QThread):
    """Background thread for microphone timer"""
    time_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.start_time = None
        self.is_recording = False
        self.is_running = False
    
    def start_recording(self):
        """Start the recording timer"""
        self.start_time = time.time()
        self.is_recording = True
        if not self.is_running:
            self.is_running = True
            self.start()
    
    def stop_recording(self):
        """Stop the recording timer"""
        self.is_recording = False
        self.start_time = None
    
    def stop_timer(self):
        """Stop the timer thread completely"""
        self.is_running = False
        self.is_recording = False
        self.start_time = None
        if self.isRunning():
            self.wait()  # Wait for thread to finish
    
    def run(self):
        """Main timer thread"""
        while self.is_running:
            if self.is_recording and self.start_time:
                elapsed = time.time() - self.start_time
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                self.time_updated.emit(f"{minutes:02d}:{seconds:02d}")
            else:
                self.time_updated.emit("00:00")
            
            self.msleep(1000)  # Update every second

class ScreenSharingDetector(QThread):
    """Detects when screen sharing applications are running"""
    screen_sharing_changed = pyqtSignal(bool)  # True when screen sharing detected
    
    # Only detect dedicated screen sharing/streaming applications
    # Removed browsers as they don't guarantee screen sharing is active
    SCREEN_SHARING_APPS = {
        'zoom.exe', 'teams.exe', 'discord.exe', 'obs64.exe', 'obs32.exe', 
        'streamlabs obs.exe', 'xsplit.core.exe', 'skype.exe',
        'webexmta.exe', 'gotomeeting.exe', 'anydesk.exe', 'teamviewer.exe',
        'loom.exe', 'camtasia.exe', 'bandicam.exe', 'fraps.exe'
    }
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.screen_sharing_active = False
        
    def run(self):
        """Main detection loop"""
        self.is_running = True
        while self.is_running:
            try:
                current_state = self.detect_screen_sharing()
                if current_state != self.screen_sharing_active:
                    self.screen_sharing_active = current_state
                    self.screen_sharing_changed.emit(current_state)
                    print(f"🔍 Screen sharing state changed: {'ACTIVE' if current_state else 'INACTIVE'}")
                    
                self.msleep(3000)  # Check every 3 seconds (less frequent)
            except Exception as e:
                print(f"❌ Error in screen sharing detection: {e}")
                self.msleep(5000)  # Wait longer on error
    
    def detect_screen_sharing(self) -> bool:
        """Detect if any screen sharing applications are running"""
        try:
            running_processes = {proc.name().lower() for proc in psutil.process_iter(['name'])}
            
            # Check for known screen sharing apps
            detected_apps = []
            for app in self.SCREEN_SHARING_APPS:
                if app.lower() in running_processes:
                    detected_apps.append(app)
            
            if detected_apps:
                print(f"🔍 Screen sharing apps detected: {', '.join(detected_apps)}")
                return True
                    
            # Additional check for browser-based meetings (disabled for now to avoid false positives)
            # if self.check_browser_meetings():
            #     return True
                
            return False
        except Exception as e:
            print(f"❌ Error detecting screen sharing: {e}")
            return False
    
    def check_browser_meetings(self) -> bool:
        """Check for browser-based meeting indicators"""
        try:
            # This feature is disabled to prevent false positives
            # In the future, this could check for specific window titles
            # like "Zoom Meeting", "Teams Meeting", etc.
            return False
        except:
            return False
    
    def stop_detection(self):
        """Stop the detection thread"""
        self.is_running = False

class ModernButton(QPushButton):
    """Custom modern button with Windows 11 styling"""
    
    def __init__(self, text="", icon_text="", parent=None, size_multiplier=1.0):
        super().__init__(parent)
        self.setText(text)
        self.size_multiplier = size_multiplier
        self.setFixedHeight(int(44 * size_multiplier))  # Larger buttons
        self.setCursor(QtCore.Qt.PointingHandCursor)
        
        # Windows 11 style - larger text
        self.setStyleSheet(f"""
            ModernButton {{
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: {int(8 * size_multiplier)}px;
                color: white;
                font-family: 'Segoe UI Variable';
                font-size: {int(15 * size_multiplier)}px;
                font-weight: 400;
                padding: {int(8 * size_multiplier)}px {int(20 * size_multiplier)}px;
            }}
            ModernButton:hover {{
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.16);
            }}
            ModernButton:pressed {{
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
            }}
        """)

class ModernOverlay(QWidget):
    """Horizontal bar overlay at top center with expandable content"""
    
    # Qt signals for thread-safe UI updates
    update_ai_response_signal = pyqtSignal(str)
    append_ai_response_signal = pyqtSignal(str)
    update_profile_signal = pyqtSignal(str)
    update_topic_guidance_signal = pyqtSignal(str)
    update_transcript_signal = pyqtSignal(str)
    show_overlay_signal = pyqtSignal()
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.is_visible = False
        self.is_expanded = False  # New: track if content is expanded
        self.is_recording = False
        self.screen_sharing_active = False
        self.was_visible_before_sharing = False
        self.show_transcript = config.get('show_transcript', True)  # Temporarily True for testing
        
        # Theme support
        self.current_theme_name = config.get('theme', 'dark')
        try:
            from ui.themes import ThemeManager
            self.current_theme = ThemeManager.get_theme(self.current_theme_name)
            self.themes_available = True
            print(f"🎨 Using {self.current_theme_name} theme")
        except ImportError:
            self.themes_available = False
            self.current_theme = None
            print("⚠️ Theme system not available, using default styling")
        
        # Get screen resolution for responsive sizing
        screen = QApplication.desktop().screenGeometry()
        self.screen_scale = min(screen.width() / 1920, screen.height() / 1080)
        self.screen_scale = max(0.8, min(2.0, self.screen_scale))  # Clamp between 0.8x and 2.0x
        
        print(f"🖥️ Screen: {screen.width()}x{screen.height()}, Overlay Scale: {self.screen_scale:.2f}x")
        
        # Enhanced features
        self.background_opacity = config.get('background_opacity', 0.15)
        self.blur_enabled = config.get('blur_enabled', True)
        self.smooth_animations = config.get('smooth_animations', True)
        
        # Hide overlay for screenshots/debugging
        self.hide_for_screenshots = config.get('hide_overlay_for_screenshots', False)
        if self.hide_for_screenshots:
            print("📷 Overlay hidden for screenshots/debugging mode")
        
        # Initialize enhanced components
        self.width_monitor = ResponsiveWidthMonitor()
        self.width_monitor.width_changed.connect(self.on_screen_dimensions_changed)
        self.width_monitor.content_changed.connect(self.on_content_length_changed)
        
        self.performance_optimizer = PerformanceOptimizer()
        self.animation_manager = None  # Will be set in setup_ui
        
        # Dynamic sizing based on content
        self.min_width = int(600 * self.screen_scale)
        self.max_width = int(1200 * self.screen_scale)  # Reduced max width to avoid geometry issues
        self.adaptive_width = self.min_width
        
        # Debug transcript configuration
        print(f"🔍 DEBUG: Overlay config keys: {list(config.keys())}")
        print(f"🔍 DEBUG: show_transcript setting: {self.show_transcript}")
        print(f"🎨 Enhanced UI: opacity={self.background_opacity}, blur={self.blur_enabled}, animations={self.smooth_animations}")
        
        # Get size multiplier from config and apply screen scaling
        base_size_multiplier = config.get('size_multiplier', 1.0)
        self.size_multiplier = base_size_multiplier * self.screen_scale
        print(f"🎨 UI Size Multiplier: {base_size_multiplier:.1f} * {self.screen_scale:.2f} = {self.size_multiplier:.2f}x")
        
        # Callbacks
        self.on_ask_ai = None
        self.on_toggle_mic = None
        self.on_settings = None
        
        # Timer
        self.mic_timer = MicrophoneTimer()
        self.mic_timer.time_updated.connect(self.update_timer_display)
        
        # Screen sharing detector (only start if enabled)
        screen_sharing_config = config.get('screen_sharing_detection', {})
        self.screen_sharing_enabled = screen_sharing_config.get('enabled', True)  # Default enabled
        
        if self.screen_sharing_enabled:
            self.screen_sharing_detector = ScreenSharingDetector()
            self.screen_sharing_detector.screen_sharing_changed.connect(self.on_screen_sharing_changed)
            print("🔍 Screen sharing detection enabled")
        else:
            self.screen_sharing_detector = None
            print("🔍 Screen sharing detection disabled by configuration")
        
        # Animation
        self.fade_animation = None
        self.expand_animation = None
        
        # Connect signals to slots
        self.update_ai_response_signal.connect(self.update_ai_response)
        self.append_ai_response_signal.connect(self.append_ai_response)
        self.update_profile_signal.connect(self.update_profile)
        self.update_topic_guidance_signal.connect(self.update_topic_guidance)
        self.update_transcript_signal.connect(self.update_transcript)
        self.show_overlay_signal.connect(self.show_overlay)
        
        self.setup_ui()
        self.apply_screen_protection()
        
        # Start screen sharing detection
        if self.screen_sharing_enabled:
            self.screen_sharing_detector.start()
        
        # Add test transcript after short delay
        if self.show_transcript:
            QTimer.singleShot(2000, self.test_transcript)
            # Also auto-start recording for testing
            QTimer.singleShot(3000, self.force_start_recording_test)
    
    def scale(self, value: int) -> int:
        """Scale a pixel value by the size multiplier"""
        return int(value * self.size_multiplier)
    
    def scale_font(self, size: int) -> int:
        """Scale a font size by the size multiplier"""
        return int(size * self.size_multiplier)
    
    def apply_theme(self, theme_name: str = None):
        """Apply theme to the overlay"""
        if not self.themes_available:
            return
        
        if theme_name:
            self.current_theme_name = theme_name
            
        try:
            from ui.themes import ThemeManager
            self.current_theme = ThemeManager.get_theme(self.current_theme_name)
            
            # Generate and apply stylesheet
            stylesheet = ThemeManager.generate_stylesheet(self.current_theme, self.size_multiplier)
            self.setStyleSheet(stylesheet)
            
            # Update theme-specific styling for the main container
            self.update_container_styling()
            
            print(f"✅ Applied {self.current_theme_name} theme to overlay")
            
        except Exception as e:
            print(f"❌ Error applying theme: {e}")
    
    def update_container_styling(self):
        """Update container styling based on current theme"""
        if not self.themes_available or not hasattr(self, 'bar_container'):
            return
        
        theme = self.current_theme
        
        # Update bar container with theme colors
        if hasattr(self, 'bar_container'):
            container_style = f"""
                QFrame#barContainer {{
                    background: {theme.overlay_background};
                    border: 2px solid {theme.border};
                    border-radius: {self.scale(35)}px;
                    color: {theme.text_primary};
                }}
            """
            self.bar_container.setStyleSheet(container_style)
        
        # Update expanded content container if it exists
        if hasattr(self, 'expanded_container'):
            content_style = f"""
                QFrame#expandedContainer {{
                    background: {theme.background_secondary};
                    border: 1px solid {theme.border_light};
                    border-radius: {self.scale(12)}px;
                    color: {theme.text_primary};
                }}
            """
            self.expanded_container.setStyleSheet(content_style)
    
    def setup_ui(self):
        """Setup the horizontal bar UI with enhanced features"""
        # Window properties
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool  # Hide from Alt-Tab
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Set window title and icon
        self.setWindowTitle("MeetMinder")
        if os.path.exists("MeetMinderIcon.ico"):
            self.setWindowIcon(QtGui.QIcon("MeetMinderIcon.ico"))
        
        # Initialize animation manager
        self.animation_manager = SmoothAnimationManager(self)
        
        # Always use standard layout to avoid conflicts - blur effects will be applied via stylesheets
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Apply enhanced background styling if blur is enabled
        if self.blur_enabled:
            self.setStyleSheet(f"""
                ModernOverlay {{
                    background: rgba({int(20 * self.background_opacity)}, {int(20 * self.background_opacity)}, {int(20 * self.background_opacity)}, {self.background_opacity});
                    border-radius: 16px;
                }}
            """)
        
        # Top horizontal bar (always visible when shown)
        self.setup_horizontal_bar(main_layout)
        
        # Expandable content area (hidden by default)
        self.setup_expandable_content(main_layout)
        
        # Set main layout (always set since we're using standard layout now)
        self.setLayout(main_layout)
        
        # Set initial adaptive size
        self.resize(self.adaptive_width, self.scale(70))
        self.position_window()
        
        # Start width monitoring
        self.width_monitor.start()
        print("🖥️ Width monitoring started")
        
        # Apply theme after UI is fully created
        if self.themes_available:
            self.apply_theme()
        
        # Start visible with smooth animation if enabled
        if self.smooth_animations:
            self.setWindowOpacity(0.0)
            self.show()
            self.animation_manager.fade_in(duration=500, target_opacity=0.9)
        else:
            self.setWindowOpacity(0.9)  # Professional semi-transparency
            self.show()
            
        self.is_visible = True
        print("✅ Enhanced overlay initialized and shown")
    
    def setup_horizontal_bar(self, parent_layout):
        """Setup the main horizontal bar"""
        # Bar container with improved contrast and sizing
        self.bar_container = QFrame()
        self.bar_container.setObjectName("barContainer")
        self.bar_container.setFixedHeight(self.scale(70))  # Slightly taller for better visibility
        # Bar container styling handled by theme system
        
        # Add more prominent drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(self.scale(30))
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, self.scale(6))
        self.bar_container.setGraphicsEffect(shadow)
        
        # Horizontal layout for the bar content with better spacing
        bar_layout = QHBoxLayout(self.bar_container)
        bar_layout.setContentsMargins(
            self.scale(25), self.scale(10), 
            self.scale(25), self.scale(10)
        )
        bar_layout.setSpacing(self.scale(20))
        
        # Recording status indicator
        self.setup_recording_status(bar_layout)
        
        # Main controls
        self.setup_main_controls(bar_layout)
        
        # Right side buttons
        self.setup_right_buttons(bar_layout)
        
        parent_layout.addWidget(self.bar_container)
    
    def setup_recording_status(self, layout):
        """Setup recording status section"""
        # Microphone button - modern style with animation
        self.mic_button = ModernButton("🎤", size_multiplier=self.size_multiplier)
        self.mic_button.setFixedSize(self.scale(50), self.scale(50))
        self.mic_button.clicked.connect(self.toggle_recording)
        self.mic_button.setToolTip("Toggle microphone recording (Ctrl+M)")
        # Mic button styling handled by theme system
        
        # Timer display - modern style
        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("timerLabel")
        # Timer label styling handled by theme system
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        
        layout.addWidget(self.mic_button)
        layout.addWidget(self.timer_label)
    
    def setup_main_controls(self, layout):
        """Setup main control buttons"""
        # Ask AI button - larger and more prominent
        self.ask_ai_button = ModernButton("🤖 Ask AI", size_multiplier=self.size_multiplier)
        self.ask_ai_button.setObjectName("askAiButton")
        self.ask_ai_button.setFixedSize(self.scale(120), self.scale(50))
        self.ask_ai_button.clicked.connect(self.trigger_ask_ai)
        # Ask AI button styling handled by theme system
        
        # Shortcut indicator - larger text
        shortcut_label = QLabel("Ctrl+Space")
        shortcut_label.setObjectName("shortcutLabel")
        # Shortcut label styling handled by theme system
        
        # Expand/collapse button - larger
        self.expand_button = ModernButton("▼", size_multiplier=self.size_multiplier)
        self.expand_button.setFixedSize(self.scale(50), self.scale(50))
        self.expand_button.clicked.connect(self.toggle_expansion)
        self.expand_button.setToolTip("Expand/collapse details")
        # Expand button styling handled by theme system
        
        layout.addWidget(self.ask_ai_button)
        layout.addWidget(shortcut_label)
        layout.addStretch()  # Push remaining items to the right
        layout.addWidget(self.expand_button)
    
    def setup_right_buttons(self, layout):
        """Setup right side control buttons"""
        # Settings button - modern style
        settings_button = ModernButton("⚙️", size_multiplier=self.size_multiplier)
        settings_button.setFixedSize(self.scale(50), self.scale(50))
        settings_button.clicked.connect(self.trigger_settings)
        settings_button.setToolTip("Open settings (Ctrl+,)")
        # Settings button styling handled by theme system
        
        # Hide/show button - modern style
        self.visibility_button = ModernButton("Hide", size_multiplier=self.size_multiplier)
        self.visibility_button.setFixedSize(self.scale(70), self.scale(50))
        self.visibility_button.clicked.connect(self.toggle_visibility)
        # Visibility button styling handled by theme system
        
        # Close button - modern style
        self.close_button = ModernButton("✕", size_multiplier=self.size_multiplier)
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(self.scale(50), self.scale(50))
        self.close_button.clicked.connect(self.close_application)
        self.close_button.setToolTip("Close application")
        # Close button styling handled by theme system
        
        layout.addWidget(settings_button)
        layout.addWidget(self.visibility_button)
        layout.addWidget(self.close_button)
    
    def setup_expandable_content(self, parent_layout):
        """Setup the expandable content area below the bar"""
        # Content container (hidden by default)
        self.content_container = QFrame()
        self.content_container.setObjectName("contentContainer")
        self.content_container.setVisible(False)
        self.content_container.setStyleSheet(f"""
            QFrame#contentContainer {{
                background: rgba(20, 20, 20, 0.90);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: none;
                border-radius: 0 0 {self.scale(16)}px {self.scale(16)}px;
                margin-top: 0px;
            }}
        """)
        
        content_layout = QHBoxLayout(self.content_container)
        content_layout.setContentsMargins(
            self.scale(24), self.scale(16), 
            self.scale(24), self.scale(24)
        )
        content_layout.setSpacing(self.scale(20))
        
        # Left side: AI Response (takes most space)
        self.setup_ai_response_section(content_layout)
        
        # Right side: Info panels
        self.setup_info_panels(content_layout)
        
        parent_layout.addWidget(self.content_container)
    
    def setup_ai_response_section(self, layout):
        """Setup the horizontal AI response area"""
        ai_section = QVBoxLayout()
        ai_section.setSpacing(self.scale(12))
        
        # AI Response header
        ai_header = QLabel("🤖 AI Response")
        ai_header.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(16)}px;
                font-weight: 600;
            }}
        """)
        
        # AI Response text area - horizontal stretch
        self.ai_response_area = QTextEdit()
        self.ai_response_area.setMinimumHeight(self.scale(200))
        self.ai_response_area.setMaximumHeight(self.scale(300))
        self.ai_response_area.setMinimumWidth(self.scale(600))  # Wide for horizontal layout
        self.ai_response_area.setReadOnly(True)
        self.ai_response_area.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: {self.scale(12)}px;
                color: white;
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(14)}px;
                line-height: 1.5;
                padding: {self.scale(16)}px;
            }}
            QScrollBar:vertical {{
                background: rgba(255, 255, 255, 0.03);
                width: {self.scale(8)}px;
                border-radius: {self.scale(4)}px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                border-radius: {self.scale(4)}px;
                min-height: {self.scale(20)}px;
            }}
        """)
        
        # Live transcript area (optional)
        self.setup_transcript_section(ai_section)
        
        ai_section.addWidget(ai_header)
        ai_section.addWidget(self.ai_response_area)
        
        layout.addLayout(ai_section, 3)  # Takes 3/4 of the width
    
    def setup_transcript_section(self, parent_layout):
        """Setup the live transcript section"""
        # Always create transcript elements, but only show them if enabled
        # Transcript header
        self.transcript_header = QLabel("📝 Live Transcript (System Audio)")
        self.transcript_header.setStyleSheet(f"""
            QLabel {{
                color: #98FB98;
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(14)}px;
                font-weight: 500;
                margin-top: {self.scale(8)}px;
            }}
        """)
        
        # Transcript area
        self.transcript_area = QTextEdit()
        self.transcript_area.setMaximumHeight(self.scale(120))
        self.transcript_area.setReadOnly(True)
        self.transcript_area.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(152, 251, 152, 0.05);
                border: 1px solid rgba(152, 251, 152, 0.15);
                border-radius: {self.scale(8)}px;
                color: rgba(255, 255, 255, 0.9);
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(12)}px;
                padding: {self.scale(12)}px;
            }}
        """)
        
        # Add to layout but set visibility based on config
        parent_layout.addWidget(self.transcript_header)
        parent_layout.addWidget(self.transcript_area)
        
        # Set visibility based on show_transcript setting
        self.transcript_header.setVisible(self.show_transcript)
        self.transcript_area.setVisible(self.show_transcript)
        
        # Add some initial text to show it's working
        if self.show_transcript:
            self.transcript_area.setPlainText("Waiting for system audio...")
    
    def setup_info_panels(self, layout):
        """Setup the right side info panels"""
        info_layout = QVBoxLayout()
        info_layout.setSpacing(self.scale(16))
        
        # Topic Analysis section
        topic_header = QLabel("🧠 Topic Analysis")
        topic_header.setStyleSheet(f"""
            QLabel {{
                color: #87CEEB;
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(14)}px;
                font-weight: 500;
            }}
        """)
        
        self.topic_path_label = QLabel("No active topic")
        self.topic_path_label.setWordWrap(True)
        self.topic_path_label.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.9);
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(11)}px;
                line-height: 1.4;
                padding: {self.scale(8)}px {self.scale(10)}px;
                background: rgba(135, 206, 235, 0.1);
                border: 1px solid rgba(135, 206, 235, 0.2);
                border-radius: {self.scale(6)}px;
                max-height: {self.scale(60)}px;
            }}
        """)
        
        # Guidance section
        guidance_header = QLabel("💡 Guidance")
        guidance_header.setStyleSheet(f"""
            QLabel {{
                color: #98FB98;
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(14)}px;
                font-weight: 500;
            }}
        """)
        
        self.topic_guidance_label = QLabel("Start speaking to get guidance")
        self.topic_guidance_label.setWordWrap(True)
        self.topic_guidance_label.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.8);
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(11)}px;
                line-height: 1.3;
                padding: {self.scale(8)}px {self.scale(10)}px;
                background: rgba(152, 251, 152, 0.1);
                border: 1px solid rgba(152, 251, 152, 0.2);
                border-radius: {self.scale(6)}px;
                max-height: {self.scale(60)}px;
            }}
        """)
        
        # Flow indicator
        flow_header = QLabel("🔄 Flow")
        flow_header.setStyleSheet(f"""
            QLabel {{
                color: #FFD700;
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(14)}px;
                font-weight: 500;
            }}
        """)
        
        self.flow_label = QLabel("Waiting")
        self.flow_label.setWordWrap(True)
        self.flow_label.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.7);
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(11)}px;
                padding: {self.scale(6)}px {self.scale(8)}px;
                background: rgba(255, 215, 0, 0.1);
                border: 1px solid rgba(255, 215, 0, 0.2);
                border-radius: {self.scale(4)}px;
                max-height: {self.scale(40)}px;
            }}
        """)
        
        info_layout.addWidget(topic_header)
        info_layout.addWidget(self.topic_path_label)
        info_layout.addWidget(guidance_header)
        info_layout.addWidget(self.topic_guidance_label)
        info_layout.addWidget(flow_header)
        info_layout.addWidget(self.flow_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout, 1)  # Takes 1/4 of the width
    
    def toggle_expansion(self):
        """Toggle the expansion of the content area"""
        if self.is_expanded:
            self.collapse_content()
        else:
            self.expand_content()
    
    def expand_content(self):
        """Expand the content area with animation"""
        if self.is_expanded:
            return
        
        self.is_expanded = True
        self.expand_button.setText("▲")
        self.expand_button.setToolTip("Collapse details")
        
        # Show content container
        self.content_container.setVisible(True)
        
        # Animate height expansion
        self.expand_animation = QPropertyAnimation(self, b"geometry")
        self.expand_animation.setDuration(300)
        
        start_rect = self.geometry()
        end_rect = QtCore.QRect(
            start_rect.x(),
            start_rect.y(),
            start_rect.width(),
            self.scale(400)  # Expanded height
        )
        
        self.expand_animation.setStartValue(start_rect)
        self.expand_animation.setEndValue(end_rect)
        self.expand_animation.setEasingCurve(QEasingCurve.OutQuart)
        self.expand_animation.start()
    
    def collapse_content(self):
        """Collapse the content area with animation"""
        if not self.is_expanded:
            return
        
        self.is_expanded = False
        self.expand_button.setText("▼")
        self.expand_button.setToolTip("Expand details")
        
        # Animate height collapse
        self.expand_animation = QPropertyAnimation(self, b"geometry")
        self.expand_animation.setDuration(250)
        
        start_rect = self.geometry()
        end_rect = QtCore.QRect(
            start_rect.x(),
            start_rect.y(),
            start_rect.width(),
            self.scale(60)  # Collapsed height (bar only)
        )
        
        self.expand_animation.setStartValue(start_rect)
        self.expand_animation.setEndValue(end_rect)
        self.expand_animation.setEasingCurve(QEasingCurve.InQuart)
        self.expand_animation.finished.connect(
            lambda: self.content_container.setVisible(False)
        )
        self.expand_animation.start()
    
    def position_window(self):
        """Position window at top center of screen"""
        if not self.isVisible():
            return
            
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Center horizontally, top of screen
        x = (screen.width() - self.width()) // 2
        y = 20  # Small margin from top
        
        # Ensure coordinates are valid
        x = max(0, min(x, screen.width() - self.width()))
        y = max(0, min(y, screen.height() - self.height()))
        
        self.move(x, y)
    
    def hide_overlay(self):
        """Hide overlay with animation"""
        if not self.is_visible:
            return
        
        # First collapse if expanded
        if self.is_expanded:
            self.collapse_content()
            # Wait for collapse animation to finish
            if self.expand_animation and self.expand_animation.state() == QPropertyAnimation.Running:
                self.expand_animation.finished.connect(self._do_hide_overlay)
                return
        
        self._do_hide_overlay()
    
    def _do_hide_overlay(self):
        """Actually perform the hide animation"""
        self.is_visible = False
        
        # Ensure valid window geometry before animation
        if not self.isVisible():
            return
            
        current_geo = self.geometry()
        if not current_geo.isValid():
            self.resize(self.scale(1000), self.scale(60))
            self.position_window()
        
        self.animate_fade_out()
        self.visibility_button.setText("Show")
    
    def show_overlay(self):
        """Show the overlay with animation if enabled"""
        # Check if overlay should be hidden for screenshots/debugging
        if getattr(self, 'hide_for_screenshots', False):
            print("📷 Overlay hidden due to screenshots/debugging mode")
            return
        
        if self.is_visible:
            return
        
        if self.smooth_animations and self.animation_manager:
            self.animation_manager.fade_in()
        else:
            self._do_show_overlay()
    
    def _do_show_overlay(self):
        """Actually show the overlay without animation"""
        # Check if overlay should be hidden for screenshots/debugging
        if getattr(self, 'hide_for_screenshots', False):
            print("📷 Overlay hidden due to screenshots/debugging mode")
            return
        
        self.is_visible = True
        self.show()
        self.position_window()
        
        # Update window opacity to ensure it's fully opaque when shown
        self.setWindowOpacity(1.0)
    
    def animate_fade_in(self):
        """Animate fade in"""
        if self.fade_animation and self.fade_animation.state() == QPropertyAnimation.Running:
            self.fade_animation.stop()
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.OutQuart)
        self.fade_animation.start()
    
    def animate_fade_out(self):
        """Animate fade out"""
        if self.fade_animation and self.fade_animation.state() == QPropertyAnimation.Running:
            self.fade_animation.stop()
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.InQuart)
        self.fade_animation.finished.connect(self._finish_hide)
        self.fade_animation.start()
    
    def _finish_hide(self):
        """Finish hide animation by actually hiding the window"""
        self.hide()
        # Disconnect to prevent memory leaks
        if self.fade_animation:
            self.fade_animation.finished.disconnect(self._finish_hide)
    
    def toggle_recording(self):
        """Toggle microphone recording"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """Start recording with modern UI updates"""
        print("🎤 DEBUG: start_recording() called")
        self.is_recording = True
        
        # Start the timer
        self.mic_timer.start_recording()
        
        # Update button style for active state
        # Mic button styling handled by theme system
        
        # Update timer label style
        # Timer label styling handled by theme system
        
        # Call the callback
        if self.on_toggle_mic:
            self.on_toggle_mic(True)
    
    def stop_recording(self):
        """Stop recording with modern UI updates"""
        print("🎤 DEBUG: stop_recording() called")
        self.is_recording = False
        
        # Stop the timer
        self.mic_timer.stop_recording()
        
        # Reset button style
        # Mic button styling handled by theme system
        
        # Reset timer label style
        # Timer label styling handled by theme system
        
        # Call the callback
        if self.on_toggle_mic:
            self.on_toggle_mic(False)
    
    def update_timer_display(self, time_str):
        """Update the timer display"""
        print(f"⏱️ DEBUG: Timer update: {time_str}")
        self.timer_label.setText(time_str)
    
    def trigger_ask_ai(self):
        """Trigger AI assistance"""
        if self.on_ask_ai:
            self.on_ask_ai()
        # Auto-expand when AI is triggered
        if not self.is_expanded:
            self.expand_content()
    
    def trigger_settings(self):
        """Trigger settings"""
        if self.on_settings:
            self.on_settings()
    
    def close_application(self):
        """Close the entire application"""
        print("🚪 Closing MeetMinder application...")
        # Emit a signal or call a callback to close the main application
        if hasattr(self, 'on_close_app') and self.on_close_app:
            self.on_close_app()
        else:
            # Fallback - close the overlay and exit
            QApplication.quit()
    
    # Thread-safe queue methods for hotkey callbacks
    @pyqtSlot()
    def _queue_trigger_assistance(self):
        """Queue trigger assistance on main thread"""
        print("🤖 Triggering AI assistance from hotkey...")
        # Show overlay first
        self.show_overlay()
        # Auto-expand when triggered via hotkey
        if not self.is_expanded:
            self.expand_content()
        self.update_ai_response("🤔 Analyzing context...")
        
        # Trigger the assistance callback but don't wait for it
        if self.on_ask_ai:
            # Run the callback in a thread but use signals for UI updates
            threading.Thread(target=self._run_ai_assistance_background, daemon=True).start()
    
    def _run_ai_assistance_background(self):
        """Run AI assistance in background thread with signal-based UI updates"""
        try:
            # This will be set by the main application to a background-safe version
            if hasattr(self, 'background_ai_callback') and self.background_ai_callback:
                self.background_ai_callback()
            else:
                # Fallback - just show a message
                self.update_ai_response_signal.emit("AI assistance triggered! (Configure AI provider to see responses)")
        except Exception as e:
            print(f"❌ Error in background AI assistance: {e}")
            self.update_ai_response_signal.emit(f"Error: {e}")
    
    @pyqtSlot()
    def _queue_take_screenshot(self):
        """Queue take screenshot on main thread"""
        print("📸 Taking screenshot from hotkey...")
        # This would be implemented by the main application
        self.update_ai_response("📸 Screenshot taken!")
    
    # UI update methods - thread-safe slots
    @pyqtSlot(str)
    def update_ai_response(self, text: str):
        """Update AI response area with enhanced content tracking"""
        self.ai_response_area.setPlainText(text)
        # Auto-expand when AI response is updated
        if not self.is_expanded and text.strip():
            self.expand_content()
        
        # Update content metrics for adaptive sizing
        self.performance_optimizer.debounce_update(
            'content_metrics',
            self.update_content_metrics,
            delay_ms=100
        )
    
    @pyqtSlot(str)
    def append_ai_response(self, text: str):
        """Append to AI response area with enhanced content tracking"""
        current_text = self.ai_response_area.toPlainText()
        self.ai_response_area.setPlainText(current_text + text)
        
        # Auto-scroll to bottom
        scrollbar = self.ai_response_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Auto-expand when content is being added
        if not self.is_expanded:
            self.expand_content()
            
        # Update content metrics for adaptive sizing
        self.performance_optimizer.debounce_update(
            'content_metrics',
            self.update_content_metrics,
            delay_ms=100
        )
    
    @pyqtSlot(str)
    def update_topic_path(self, path: str):
        """Update the topic path display"""
        self.topic_path_label.setText(path)
    
    @pyqtSlot(str)
    def update_topic_guidance(self, guidance: str):
        """Update topic guidance display"""
        self.topic_guidance_label.setText(guidance)
    
    @pyqtSlot(str)
    def update_conversation_flow(self, flow: str):
        """Update conversation flow indicator"""
        self.flow_label.setText(flow)
    
    # Legacy method for backward compatibility
    @pyqtSlot(str)
    def update_profile(self, text: str):
        """Legacy method - now updates topic path for backward compatibility"""
        self.update_topic_path(text)
    
    # Thread-safe wrapper methods
    def update_ai_response_threadsafe(self, text: str):
        """Thread-safe version of update_ai_response"""
        self.update_ai_response_signal.emit(text)
    
    def append_ai_response_threadsafe(self, text: str):
        """Thread-safe version of append_ai_response"""
        self.append_ai_response_signal.emit(text)
    
    def update_topic_path_threadsafe(self, path: str):
        """Thread-safe version of update_topic_path"""
        self.update_topic_guidance_signal.emit(path)  # Reuse existing signal
    
    def update_topic_guidance_threadsafe(self, guidance: str):
        """Thread-safe version of update_topic_guidance"""
        self.update_topic_guidance_signal.emit(guidance)
    
    def update_profile_threadsafe(self, text: str):
        """Legacy thread-safe method - now updates topic path"""
        self.update_topic_guidance_signal.emit(text)
    
    def show_overlay_threadsafe(self):
        """Thread-safe version of show_overlay"""
        self.show_overlay_signal.emit()
    
    def on_screen_sharing_changed(self, is_active: bool):
        """Handle screen sharing state change - auto hide during screen sharing"""
        print(f"🔍 Screen sharing {'detected' if is_active else 'stopped'}")
        
        if is_active and not self.screen_sharing_active:
            # Screen sharing just started
            self.screen_sharing_active = True
            if self.is_visible:
                self.was_visible_before_sharing = True
                print("🙈 Auto-hiding overlay during screen sharing")
                self.hide_overlay()
            else:
                self.was_visible_before_sharing = False
                
        elif not is_active and self.screen_sharing_active:
            # Screen sharing just stopped
            self.screen_sharing_active = False
            if self.was_visible_before_sharing:
                print("👀 Restoring overlay visibility after screen sharing")
                self.show_overlay()
            self.was_visible_before_sharing = False
    
    def clear_all_content(self):
        """Clear all content areas"""
        self.ai_response_area.clear()
        self.topic_path_label.setText("No active topic")
        self.topic_guidance_label.setText("Start speaking to get guidance")
        self.flow_label.setText("Waiting")
        if self.show_transcript and hasattr(self, 'transcript_area'):
            self.transcript_area.clear()
    
    # Callback setters
    def set_ask_ai_callback(self, callback: Callable):
        """Set callback for Ask AI button"""
        self.on_ask_ai = callback
    
    def set_background_ai_callback(self, callback: Callable):
        """Set background-safe AI callback that uses signals for UI updates"""
        self.background_ai_callback = callback
    
    def set_toggle_mic_callback(self, callback: Callable):
        """Set callback for microphone toggle"""
        self.on_toggle_mic = callback
    
    def set_settings_callback(self, callback: Callable):
        """Set callback for settings button"""
        self.on_settings = callback
    
    def set_close_app_callback(self, callback: Callable):
        """Set callback for close application"""
        self.on_close_app = callback
    
    def update_hide_for_screenshots(self, hide: bool):
        """Update the hide for screenshots/debugging setting"""
        self.hide_for_screenshots = hide
        if hide:
            print("📷 Overlay will be hidden for screenshots/debugging")
            self.hide_overlay()
        else:
            print("📷 Overlay screenshots/debugging mode disabled")
            # Don't automatically show - let the user control visibility
    
    def toggle_hide_for_screenshots(self):
        """Toggle the hide for screenshots/debugging setting"""
        current_state = getattr(self, 'hide_for_screenshots', False)
        new_state = not current_state
        self.update_hide_for_screenshots(new_state)
        
        # Show feedback to user
        status_msg = "Hidden for screenshots/debugging" if new_state else "Screenshots/debugging mode disabled"
        self.update_ai_response(f"📷 Overlay: {status_msg}")
    
    # Window drag functionality
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if (event.buttons() == QtCore.Qt.LeftButton and 
            hasattr(self, 'drag_position')):
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def closeEvent(self, event):
        """Handle close event"""
        print("🚪 Closing overlay - stopping threads...")
        
        # Stop microphone timer
        if hasattr(self, 'mic_timer'):
            self.mic_timer.stop_timer()
        
        # Stop screen sharing detector (only if enabled)
        if hasattr(self, 'screen_sharing_detector') and self.screen_sharing_detector is not None:
            self.screen_sharing_detector.stop_detection()
            self.screen_sharing_detector.wait()  # Wait for thread to finish
            
        event.accept()
    
    def test_transcript(self):
        """Test function to verify transcript is working"""
        print("🧪 Testing transcript functionality...")
        self.update_transcript_threadsafe("[SYSTEM] This is a test transcript message to verify functionality")
        QTimer.singleShot(3000, lambda: self.update_transcript_threadsafe("[SYSTEM] Second test message with longer content to test scrolling"))
    
    def toggle_transcript_visibility(self, visible: bool):
        """Toggle transcript visibility at runtime"""
        self.show_transcript = visible
        if hasattr(self, 'transcript_header') and hasattr(self, 'transcript_area'):
            self.transcript_header.setVisible(visible)
            self.transcript_area.setVisible(visible)
            print(f"🔍 Transcript visibility set to: {visible}")
            
            if visible:
                self.transcript_area.setPlainText("Transcript enabled - waiting for system audio...")
            else:
                self.transcript_area.clear()
    
    def force_start_recording_test(self):
        """Force start recording for testing purposes"""
        print("🧪 TESTING: Force starting recording...")
        self.start_recording()
        # Auto-enable transcript for testing
        if hasattr(self, 'toggle_transcript_visibility'):
            self.toggle_transcript_visibility(True)
    
    @pyqtSlot()
    def toggle_visibility(self):
        """Toggle overlay visibility"""
        if self.is_visible:
            self.hide_overlay()
        else:
            self.show_overlay()
    
    @pyqtSlot(str)
    def update_transcript(self, text: str):
        """Update the live transcript area"""
        print(f"🔍 DEBUG: update_transcript called with: '{text}'")
        print(f"🔍 DEBUG: show_transcript = {self.show_transcript}")
        print(f"🔍 DEBUG: has transcript_area = {hasattr(self, 'transcript_area')}")
        
        # Always process transcript updates, but only display if enabled and area exists
        if hasattr(self, 'transcript_area') and self.transcript_area is not None:
            print(f"🔍 DEBUG: Transcript area exists, processing...")
            
            # Only show system audio content
            if '[SYSTEM]' in text:
                clean_text = text.replace('[SYSTEM] ', '').strip()
                print(f"🔍 DEBUG: System audio text: '{clean_text}'")
                
                if clean_text:  # Only add non-empty text
                    current_text = self.transcript_area.toPlainText()
                    
                    # Add timestamp
                    import time
                    timestamp = time.strftime("%H:%M:%S")
                    timestamped_text = f"[{timestamp}] {clean_text}"
                    
                    # Keep only last 5 lines
                    if current_text.strip():
                        lines = current_text.split('\n')
                        lines.append(timestamped_text)
                        if len(lines) > 5:
                            lines = lines[-5:]
                        new_text = '\n'.join(lines)
                    else:
                        new_text = timestamped_text
                    
                    print(f"🔍 DEBUG: Setting transcript text: '{new_text}'")
                    self.transcript_area.setPlainText(new_text)
                    
                    # Auto-scroll to bottom
                    scrollbar = self.transcript_area.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())
                    
                    print("✅ Transcript updated successfully")
            else:
                print(f"🔍 DEBUG: Text doesn't contain [SYSTEM]: '{text}'")
        else:
            print(f"❌ DEBUG: No transcript area available")
    
    def update_transcript_threadsafe(self, text: str):
        """Thread-safe version of update_transcript"""
        print(f"🔍 DEBUG: update_transcript_threadsafe called with: '{text}'")
        self.update_transcript_signal.emit(text)
    
    def apply_screen_protection(self):
        """Apply screen capture protection"""
        if HAS_WINDOWS_API:
            try:
                hwnd = int(self.winId())
                user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
                print("✓ Screen capture protection enabled")
            except Exception as e:
                print(f"⚠ Could not enable screen protection: {e}")
        else:
            print("⚠ Screen protection not available (Windows API not found)")
    
    def on_screen_dimensions_changed(self, width: int, height: int):
        """Handle screen dimension changes for responsive design"""
        print(f"🖥️ Screen dimensions changed to: {width}x{height}")
        
        # Recalculate screen scale
        old_scale = self.screen_scale
        self.screen_scale = min(width / 1920, height / 1080)
        self.screen_scale = max(0.8, min(2.0, self.screen_scale))
        
        if abs(old_scale - self.screen_scale) > 0.1:  # Significant change
            print(f"🎨 Scale factor changed: {old_scale:.2f} → {self.screen_scale:.2f}")
            
            # Update size multiplier
            base_size_multiplier = self.config.get('size_multiplier', 1.0)
            self.size_multiplier = base_size_multiplier * self.screen_scale
            
            # Update adaptive width limits
            self.min_width = int(600 * self.screen_scale)
            self.max_width = int(1400 * self.screen_scale)
            
            # Debounce the UI update to avoid excessive redraws
            self.performance_optimizer.debounce_update(
                'scale_update', 
                self.update_ui_scaling,
                delay_ms=300
            )
    
    def on_content_length_changed(self, content_length: int):
        """Handle content length changes for adaptive width"""
        # Calculate optimal width based on content
        base_width = self.min_width
        content_factor = min(content_length / 1000, 1.0)  # Scale factor based on content
        optimal_width = int(base_width + (self.max_width - base_width) * content_factor)
        
        # Update adaptive width if changed significantly
        if abs(optimal_width - self.adaptive_width) > 50:
            print(f"📏 Adaptive width: {self.adaptive_width} → {optimal_width} (content: {content_length})")
            self.adaptive_width = optimal_width
            
            # Debounce the resize operation
            self.performance_optimizer.debounce_update(
                'width_update',
                lambda: self.resize_smoothly(self.adaptive_width),
                delay_ms=200
            )
    
    def update_ui_scaling(self):
        """Update UI scaling after screen changes"""
        try:
            # Resize with new scaling
            current_width = max(self.adaptive_width, self.min_width)
            self.resize(current_width, self.height())
            
            # Reposition on screen
            self.position_window()
            
            print(f"🎨 UI scaling updated: width={current_width}")
            
        except Exception as e:
            print(f"❌ Error updating UI scaling: {e}")
    
    def resize_smoothly(self, target_width: int):
        """Smoothly resize the overlay to target width"""
        try:
            # Get screen dimensions for bounds checking
            screen = QApplication.primaryScreen().availableGeometry()
            max_safe_width = min(self.max_width, screen.width() - 100)  # Leave margin
            
            target_width = max(self.min_width, min(target_width, max_safe_width))
            
            # Don't resize if change is too small to avoid excessive updates
            if abs(target_width - self.width()) < 20:
                return
                
            if self.smooth_animations and hasattr(self, 'animation_manager'):
                # Create smooth width animation
                width_animation = QPropertyAnimation(self, b"size")
                width_animation.setDuration(300)
                width_animation.setStartValue(self.size())
                width_animation.setEndValue(QSize(target_width, self.height()))
                width_animation.setEasingCurve(QEasingCurve.OutCubic)
                width_animation.start()
                
                # Store animation to prevent garbage collection
                if not hasattr(self, '_width_animations'):
                    self._width_animations = []
                self._width_animations.append(width_animation)
                
                # Clean up old animations
                if len(self._width_animations) > 3:
                    self._width_animations.pop(0)
            else:
                # Direct resize
                self.resize(target_width, self.height())
                
            # Reposition to keep centered
            self.position_window()
            
        except Exception as e:
            print(f"❌ Error in smooth resize: {e}")
    
    def update_content_metrics(self):
        """Update content metrics for adaptive sizing"""
        try:
            total_content = 0
            
            # Count AI response content
            if hasattr(self, 'ai_response_area'):
                total_content += len(self.ai_response_area.toPlainText())
            
            # Count transcript content
            if hasattr(self, 'transcript_area'):
                total_content += len(self.transcript_area.toPlainText())
            
            # Update width monitor with new content length
            self.width_monitor.update_content_length(total_content)
            
        except Exception as e:
            print(f"❌ Error updating content metrics: {e}")
    
    def enhanced_closeEvent(self, event):
        """Enhanced cleanup when overlay is closed"""
        try:
            # Stop width monitoring
            if hasattr(self, 'width_monitor'):
                self.width_monitor.stop_monitoring()
                if self.width_monitor.isRunning():
                    self.width_monitor.wait(2000)  # Wait up to 2 seconds
            
            # Stop existing processes
            if hasattr(self, 'mic_timer'):
                self.mic_timer.stop_timer()
            
            if hasattr(self, 'screen_sharing_detector') and self.screen_sharing_detector:
                self.screen_sharing_detector.stop_detection()
                if self.screen_sharing_detector.isRunning():
                    self.screen_sharing_detector.wait(1000)
            
            print("🧹 Enhanced overlay cleanup completed")
            
        except Exception as e:
            print(f"❌ Error in enhanced cleanup: {e}")
        
        # Call original close event
        super().closeEvent(event) 