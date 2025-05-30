import sys
import ctypes
import time
import threading
import psutil
from typing import Dict, Any, Optional, Callable
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, QPropertyAnimation, QEasingCurve, pyqtSlot
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                           QTextEdit, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
                           QScrollArea, QApplication)
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon

# Windows API constants for screen capture protection
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001

try:
    user32 = ctypes.windll.user32
    HAS_WINDOWS_API = True
except:
    HAS_WINDOWS_API = False

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
    
    # Common screen sharing application process names
    SCREEN_SHARING_APPS = {
        'zoom.exe', 'teams.exe', 'discord.exe', 'obs64.exe', 'obs32.exe', 
        'streamlabs obs.exe', 'xsplit.core.exe', 'skype.exe', 'googlemeet',
        'chrome.exe', 'firefox.exe', 'msedge.exe',  # Browsers (for web meetings)
        'webexmta.exe', 'gotomeeting.exe', 'anydesk.exe', 'teamviewer.exe'
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
                    
                self.msleep(2000)  # Check every 2 seconds
            except Exception as e:
                print(f"❌ Error in screen sharing detection: {e}")
                self.msleep(5000)  # Wait longer on error
    
    def detect_screen_sharing(self) -> bool:
        """Detect if any screen sharing applications are running"""
        try:
            running_processes = {proc.name().lower() for proc in psutil.process_iter(['name'])}
            
            # Check for known screen sharing apps
            for app in self.SCREEN_SHARING_APPS:
                if app.lower() in running_processes:
                    return True
                    
            # Additional check for browser-based meetings (look for specific window titles)
            if self.check_browser_meetings():
                return True
                
            return False
        except Exception as e:
            print(f"❌ Error detecting screen sharing: {e}")
            return False
    
    def check_browser_meetings(self) -> bool:
        """Check for browser-based meeting indicators"""
        try:
            # This is a simplified check - in practice you might want to check window titles
            # or other indicators for browser-based meetings
            return False  # For now, just return False
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
        
        # Get screen resolution for responsive sizing
        screen = QApplication.desktop().screenGeometry()
        self.screen_scale = min(screen.width() / 1920, screen.height() / 1080)
        self.screen_scale = max(0.8, min(2.0, self.screen_scale))  # Clamp between 0.8x and 2.0x
        
        print(f"🖥️ Screen: {screen.width()}x{screen.height()}, Overlay Scale: {self.screen_scale:.2f}x")
        
        # Debug transcript configuration
        print(f"🔍 DEBUG: Overlay config keys: {list(config.keys())}")
        print(f"🔍 DEBUG: show_transcript setting: {self.show_transcript}")
        
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
        
        # Screen sharing detector
        self.screen_sharing_detector = ScreenSharingDetector()
        self.screen_sharing_detector.screen_sharing_changed.connect(self.on_screen_sharing_changed)
        
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
        
    def setup_ui(self):
        """Setup the horizontal bar UI"""
        # Window properties
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool  # Hide from Alt-Tab
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Main layout - vertical to stack bar and expandable content
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top horizontal bar (always visible when shown)
        self.setup_horizontal_bar(main_layout)
        
        # Expandable content area (hidden by default)
        self.setup_expandable_content(main_layout)
        
        self.setLayout(main_layout)
        
        # Set initial size - horizontal bar only
        self.resize(self.scale(1000), self.scale(60))  # Wide horizontal bar
        self.position_window()
        
        # Start hidden
        self.setWindowOpacity(0.0)
        self.hide()
    
    def setup_horizontal_bar(self, parent_layout):
        """Setup the main horizontal bar"""
        # Bar container with improved contrast and sizing
        self.bar_container = QFrame()
        self.bar_container.setObjectName("barContainer")
        self.bar_container.setFixedHeight(self.scale(70))  # Slightly taller for better visibility
        self.bar_container.setStyleSheet(f"""
            QFrame#barContainer {{
                background: rgba(15, 15, 15, 0.95);
                border: 2px solid rgba(255, 255, 255, 0.15);
                border-radius: {self.scale(35)}px;
                backdrop-filter: blur({self.scale(25)}px);
            }}
        """)
        
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
        # Microphone button - larger for better visibility
        self.mic_button = ModernButton("🎤", size_multiplier=self.size_multiplier)
        self.mic_button.setFixedSize(self.scale(50), self.scale(50))
        self.mic_button.clicked.connect(self.toggle_recording)
        self.mic_button.setToolTip("Toggle microphone recording")
        
        # Timer display - larger and more prominent
        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet(f"""
            QLabel {{
                color: #FFD700;
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(16)}px;
                font-weight: 600;
                background: rgba(255, 215, 0, 0.2);
                border: 2px solid rgba(255, 215, 0, 0.4);
                border-radius: {self.scale(18)}px;
                padding: {self.scale(8)}px {self.scale(16)}px;
                min-width: {self.scale(70)}px;
            }}
        """)
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        
        layout.addWidget(self.mic_button)
        layout.addWidget(self.timer_label)
    
    def setup_main_controls(self, layout):
        """Setup main control buttons"""
        # Ask AI button - larger and more prominent
        self.ask_ai_button = ModernButton("🤖 Ask AI", size_multiplier=self.size_multiplier)
        self.ask_ai_button.setFixedSize(self.scale(120), self.scale(50))
        self.ask_ai_button.clicked.connect(self.trigger_ask_ai)
        self.ask_ai_button.setStyleSheet(f"""
            ModernButton {{
                background: rgba(0, 120, 212, 0.3);
                border: 2px solid rgba(0, 120, 212, 0.5);
                color: #87CEEB;
                font-weight: 600;
                font-size: {self.scale_font(14)}px;
                border-radius: {self.scale(25)}px;
            }}
            ModernButton:hover {{
                background: rgba(0, 120, 212, 0.4);
                border: 2px solid rgba(0, 120, 212, 0.7);
            }}
        """)
        
        # Shortcut indicator - larger text
        shortcut_label = QLabel("Ctrl+Space")
        shortcut_label.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.8);
                font-family: 'Segoe UI Variable';
                font-size: {self.scale_font(12)}px;
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: {self.scale(12)}px;
                padding: {self.scale(6)}px {self.scale(12)}px;
            }}
        """)
        
        # Expand/collapse button - larger
        self.expand_button = ModernButton("▼", size_multiplier=self.size_multiplier)
        self.expand_button.setFixedSize(self.scale(50), self.scale(50))
        self.expand_button.clicked.connect(self.toggle_expansion)
        self.expand_button.setToolTip("Expand/collapse details")
        self.expand_button.setStyleSheet(f"""
            ModernButton {{
                background: rgba(255, 255, 255, 0.15);
                border: 2px solid rgba(255, 255, 255, 0.25);
                color: white;
                font-weight: bold;
                font-size: {self.scale_font(16)}px;
                border-radius: {self.scale(25)}px;
            }}
            ModernButton:hover {{
                background: rgba(255, 255, 255, 0.2);
                border: 2px solid rgba(255, 255, 255, 0.35);
            }}
        """)
        
        layout.addWidget(self.ask_ai_button)
        layout.addWidget(shortcut_label)
        layout.addStretch()  # Push remaining items to the right
        layout.addWidget(self.expand_button)
    
    def setup_right_buttons(self, layout):
        """Setup right side control buttons"""
        # Settings button - larger
        settings_button = ModernButton("⚙️", size_multiplier=self.size_multiplier)
        settings_button.setFixedSize(self.scale(50), self.scale(50))
        settings_button.clicked.connect(self.trigger_settings)
        settings_button.setToolTip("Open settings")
        
        # Hide/show button - larger
        self.visibility_button = ModernButton("Hide", size_multiplier=self.size_multiplier)
        self.visibility_button.setFixedSize(self.scale(70), self.scale(50))
        self.visibility_button.clicked.connect(self.toggle_visibility)
        
        # Close button - larger and more prominent
        self.close_button = ModernButton("✕", size_multiplier=self.size_multiplier)
        self.close_button.setFixedSize(self.scale(50), self.scale(50))
        self.close_button.clicked.connect(self.close_application)
        self.close_button.setToolTip("Close application")
        self.close_button.setStyleSheet(f"""
            ModernButton {{
                background: rgba(255, 0, 0, 0.2);
                border: 2px solid rgba(255, 0, 0, 0.4);
                color: #FF6B6B;
                font-weight: bold;
                font-size: {self.scale_font(18)}px;
                border-radius: {self.scale(25)}px;
            }}
            ModernButton:hover {{
                background: rgba(255, 0, 0, 0.3);
                border: 2px solid rgba(255, 0, 0, 0.6);
            }}
        """)
        
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
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Center horizontally, top of screen
        x = (screen.width() - self.width()) // 2
        y = 20  # Small margin from top
        
        self.move(x, y)
    
    @pyqtSlot()
    def show_overlay(self):
        """Show overlay with animation"""
        if self.is_visible:
            return
        
        self.is_visible = True
        self.show()
        self.animate_fade_in()
        self.visibility_button.setText("Hide")
        
        # When showing, always start collapsed
        if self.is_expanded:
            self.collapse_content()
    
    def hide_overlay(self):
        """Hide overlay with animation"""
        if not self.is_visible:
            return
        
        self.is_visible = False
        self.animate_fade_out()
        self.visibility_button.setText("Show")
    
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
    
    def animate_fade_in(self):
        """Animate fade in"""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.OutQuart)
        self.fade_animation.start()
    
    def animate_fade_out(self):
        """Animate fade out"""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.InQuart)
        self.fade_animation.finished.connect(self.hide)
        self.fade_animation.start()
    
    def toggle_recording(self):
        """Toggle microphone recording"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """Start recording"""
        print("🎤 DEBUG: start_recording() called")
        self.is_recording = True
        
        # Start the timer
        print("🎤 DEBUG: Starting mic timer...")
        self.mic_timer.start_recording()
        
        # Update button style
        print("🎤 DEBUG: Updating button style...")
        self.mic_button.setStyleSheet(self.mic_button.styleSheet() + """
            ModernButton {
                background: rgba(255, 0, 0, 0.15);
                border: 1px solid rgba(255, 0, 0, 0.3);
            }
        """)
        
        # Call the callback
        print("🎤 DEBUG: Calling toggle mic callback...")
        if self.on_toggle_mic:
            self.on_toggle_mic(True)
        
        print("✅ Recording started successfully!")
    
    def stop_recording(self):
        """Stop recording"""
        print("🎤 DEBUG: stop_recording() called")
        self.is_recording = False
        
        # Stop the timer
        print("🎤 DEBUG: Stopping mic timer...")
        self.mic_timer.stop_recording()
        
        # Reset button style
        print("🎤 DEBUG: Resetting button style...")
        self.mic_button.setStyleSheet(self.mic_button.styleSheet().replace("""
            ModernButton {
                background: rgba(255, 0, 0, 0.15);
                border: 1px solid rgba(255, 0, 0, 0.3);
            }
        """, ""))
        
        # Call the callback
        print("🎤 DEBUG: Calling toggle mic callback...")
        if self.on_toggle_mic:
            self.on_toggle_mic(False)
        
        print("✅ Recording stopped successfully!")
    
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
        """Update AI response area"""
        self.ai_response_area.setPlainText(text)
        # Auto-expand when AI response is updated
        if not self.is_expanded and text.strip():
            self.expand_content()
    
    @pyqtSlot(str)
    def append_ai_response(self, text: str):
        """Append to AI response area"""
        current_text = self.ai_response_area.toPlainText()
        self.ai_response_area.setPlainText(current_text + text)
        
        # Auto-scroll to bottom
        scrollbar = self.ai_response_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Auto-expand when content is being added
        if not self.is_expanded:
            self.expand_content()
    
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
        """Set callback for close application button"""
        self.on_close_app = callback
    
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
        
        # Stop screen sharing detector
        if hasattr(self, 'screen_sharing_detector'):
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