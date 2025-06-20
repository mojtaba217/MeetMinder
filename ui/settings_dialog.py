import sys
import os
from typing import Dict, Any, Callable
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QCheckBox, QSpinBox, QComboBox,
                           QGroupBox, QFormLayout, QSlider, QFrame, 
                           QTabWidget, QTextEdit, QLineEdit, QScrollArea,
                           QWidget, QGridLayout, QFileDialog, QMessageBox,
                           QApplication, QDesktopWidget, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import json

class ModernSettingsDialog(QDialog):
    """Modern tabbed settings dialog with organized sections"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, current_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.current_config = current_config.copy()
        
        # Get screen resolution for responsive sizing
        self.screen = QApplication.desktop().screenGeometry()
        self.scale_factor = min(self.screen.width() / 1920, self.screen.height() / 1080)
        self.scale_factor = max(0.8, min(1.5, self.scale_factor))  # Clamp between 0.8x and 1.5x
        
        print(f"🖥️ Screen: {self.screen.width()}x{self.screen.height()}, Scale: {self.scale_factor:.2f}x")
        
        self.setup_ui()
        self.load_current_settings()
    
    def scale(self, value: int) -> int:
        """Scale a value by the screen scale factor"""
        return int(value * self.scale_factor)
    
    def setup_ui(self):
        """Setup the tabbed settings UI"""
        self.setWindowTitle("MeetMinder Settings")
        
        # Set window icon
        if os.path.exists("MeetMinderIcon.ico"):
            self.setWindowIcon(QIcon("MeetMinderIcon.ico"))
        
        # Responsive sizing based on screen resolution
        dialog_width = self.scale(1400)  # Increased width for better content visibility
        dialog_height = self.scale(900)   # Increased height for better content visibility
        self.setFixedSize(dialog_width, dialog_height)
        
        # Center on screen
        screen_center = self.screen.center()
        self.move(screen_center.x() - dialog_width // 2, screen_center.y() - dialog_height // 2)
        
        # Modern dark theme with high contrast
        # Apply theme-based styling - will be updated when theme changes
        self.apply_current_theme()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(self.scale(25), self.scale(25), self.scale(25), self.scale(25))
        layout.setSpacing(self.scale(20))
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumSize(self.scale(1200), self.scale(800))
        
        # Setup all tabs
        self.setup_ai_provider_tab()
        self.setup_audio_tab()
        self.setup_ui_tab()
        self.setup_assistant_tab()
        self.setup_prompts_tab()
        self.setup_knowledge_tab()
        self.setup_hotkeys_tab()
        self.setup_debug_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Setup buttons
        self.setup_buttons(layout)
        
        self.setLayout(layout)
        
        # Load current settings into the dialog
        self.load_current_settings()
        
        # Clear any hardcoded styles that might interfere with theming
        self.clear_hardcoded_styles()
    
    def setup_ai_provider_tab(self):
        """Setup AI Provider configuration tab"""
        tab = QScrollArea()
        content = QWidget()
        
        # Set proper size policy for content to expand
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.setMinimumSize(self.scale(1200), self.scale(700))  # Increased for more providers
        
        layout = QVBoxLayout(content)
        layout.setSpacing(self.scale(25))
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(30))
        
        # Provider Selection
        provider_group = QGroupBox("🤖 AI Provider")
        provider_layout = QFormLayout()
        provider_layout.setSpacing(self.scale(20))
        provider_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.ai_provider_type = QComboBox()
        self.ai_provider_type.addItems(["azure_openai", "openai", "google_gemini", "deepseek", "claude"])
        self.ai_provider_type.setMinimumHeight(self.scale(40))
        self.ai_provider_type.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addRow("Provider:", self.ai_provider_type)
        
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)
        
        # Azure OpenAI Settings
        self.azure_group = QGroupBox("🔷 Azure OpenAI Configuration")
        self.azure_group.setMinimumHeight(self.scale(350))
        azure_layout = QFormLayout()
        azure_layout.setSpacing(self.scale(20))
        azure_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.azure_endpoint = QLineEdit()
        self.azure_endpoint.setPlaceholderText("https://your-resource.openai.azure.com/")
        self.azure_endpoint.setMinimumHeight(self.scale(40))

        azure_layout.addRow("Endpoint:", self.azure_endpoint)
        
        self.azure_api_key = QLineEdit()
        self.azure_api_key.setPlaceholderText("Your Azure OpenAI API key")
        self.azure_api_key.setEchoMode(QLineEdit.Password)
        self.azure_api_key.setMinimumHeight(self.scale(40))

        azure_layout.addRow("API Key:", self.azure_api_key)
        
        self.azure_model = QLineEdit()
        self.azure_model.setPlaceholderText("gpt-4")
        self.azure_model.setMinimumHeight(self.scale(40))

        azure_layout.addRow("Model:", self.azure_model)
        
        self.azure_deployment = QLineEdit()
        self.azure_deployment.setPlaceholderText("your-deployment-name")
        self.azure_deployment.setMinimumHeight(self.scale(40))

        azure_layout.addRow("Deployment:", self.azure_deployment)
        
        self.azure_api_version = QLineEdit()
        self.azure_api_version.setText("2024-06-01")
        self.azure_api_version.setMinimumHeight(self.scale(40))

        azure_layout.addRow("API Version:", self.azure_api_version)
        
        self.azure_group.setLayout(azure_layout)
        layout.addWidget(self.azure_group)
        
        # OpenAI Settings
        self.openai_group = QGroupBox("🟢 OpenAI Configuration")
        self.openai_group.setMinimumHeight(self.scale(200))
        openai_layout = QFormLayout()
        openai_layout.setSpacing(self.scale(20))
        openai_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.openai_api_key = QLineEdit()
        self.openai_api_key.setPlaceholderText("Your OpenAI API key")
        self.openai_api_key.setEchoMode(QLineEdit.Password)
        self.openai_api_key.setMinimumHeight(self.scale(40))
        openai_layout.addRow("API Key:", self.openai_api_key)
        
        self.openai_model = QLineEdit()
        self.openai_model.setPlaceholderText("gpt-4")
        self.openai_model.setMinimumHeight(self.scale(40))
        openai_layout.addRow("Model:", self.openai_model)
        
        self.openai_group.setLayout(openai_layout)
        layout.addWidget(self.openai_group)
        
        # Google Gemini Settings
        self.gemini_group = QGroupBox("🔴 Google Gemini Configuration")
        self.gemini_group.setMinimumHeight(self.scale(250))
        gemini_layout = QFormLayout()
        gemini_layout.setSpacing(self.scale(20))
        gemini_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.gemini_api_key = QLineEdit()
        self.gemini_api_key.setPlaceholderText("Your Gemini API key")
        self.gemini_api_key.setEchoMode(QLineEdit.Password)
        self.gemini_api_key.setMinimumHeight(self.scale(40))
        gemini_layout.addRow("API Key:", self.gemini_api_key)
        
        self.gemini_model = QLineEdit()
        self.gemini_model.setPlaceholderText("gemini-2.0-flash")
        self.gemini_model.setMinimumHeight(self.scale(40))
        gemini_layout.addRow("Model:", self.gemini_model)
        
        self.gemini_project_id = QLineEdit()
        self.gemini_project_id.setPlaceholderText("your-project-id")
        self.gemini_project_id.setMinimumHeight(self.scale(40))
        gemini_layout.addRow("Project ID:", self.gemini_project_id)
        
        self.gemini_group.setLayout(gemini_layout)
        layout.addWidget(self.gemini_group)
        
        # DeepSeek Settings
        self.deepseek_group = QGroupBox("🧠 DeepSeek Configuration")
        self.deepseek_group.setMinimumHeight(self.scale(250))
        deepseek_layout = QFormLayout()
        deepseek_layout.setSpacing(self.scale(20))
        deepseek_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.deepseek_api_key = QLineEdit()
        self.deepseek_api_key.setPlaceholderText("Your DeepSeek API key")
        self.deepseek_api_key.setEchoMode(QLineEdit.Password)
        self.deepseek_api_key.setMinimumHeight(self.scale(40))
        deepseek_layout.addRow("API Key:", self.deepseek_api_key)
        
        self.deepseek_base_url = QLineEdit()
        self.deepseek_base_url.setPlaceholderText("https://api.deepseek.com")
        self.deepseek_base_url.setMinimumHeight(self.scale(40))
        deepseek_layout.addRow("Base URL:", self.deepseek_base_url)
        
        self.deepseek_model = QLineEdit()
        self.deepseek_model.setPlaceholderText("deepseek-coder")
        self.deepseek_model.setMinimumHeight(self.scale(40))
        deepseek_layout.addRow("Model:", self.deepseek_model)
        
        self.deepseek_group.setLayout(deepseek_layout)
        layout.addWidget(self.deepseek_group)
        
        # Claude Settings
        self.claude_group = QGroupBox("🎭 Claude Configuration")
        self.claude_group.setMinimumHeight(self.scale(250))
        claude_layout = QFormLayout()
        claude_layout.setSpacing(self.scale(20))
        claude_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.claude_api_key = QLineEdit()
        self.claude_api_key.setPlaceholderText("Your Anthropic API key")
        self.claude_api_key.setEchoMode(QLineEdit.Password)
        self.claude_api_key.setMinimumHeight(self.scale(40))
        claude_layout.addRow("API Key:", self.claude_api_key)
        
        self.claude_base_url = QLineEdit()
        self.claude_base_url.setPlaceholderText("https://api.anthropic.com")
        self.claude_base_url.setMinimumHeight(self.scale(40))
        claude_layout.addRow("Base URL:", self.claude_base_url)
        
        self.claude_model = QLineEdit()
        self.claude_model.setPlaceholderText("claude-3-sonnet-20240229")
        self.claude_model.setMinimumHeight(self.scale(40))
        claude_layout.addRow("Model:", self.claude_model)
        
        self.claude_group.setLayout(claude_layout)
        layout.addWidget(self.claude_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, "🤖 AI Provider")
    
    def setup_audio_tab(self):
        """Setup Audio settings tab"""
        tab = QScrollArea()
        content = QWidget()
        
        # Set proper size policy for content to expand
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.setMinimumSize(self.scale(1200), self.scale(1100))  # Increased for transcription settings
        
        layout = QVBoxLayout(content)
        layout.setSpacing(self.scale(25))
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(30))
        
        # Audio Mode
        mode_group = QGroupBox("🎤 Audio Configuration")
        mode_group.setMinimumHeight(self.scale(300))
        mode_layout = QFormLayout()
        mode_layout.setSpacing(self.scale(20))
        mode_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.audio_mode = QComboBox()
        self.audio_mode.addItems(["single_stream", "dual_stream"])
        self.audio_mode.setMinimumHeight(self.scale(40))
        mode_layout.addRow("Audio Mode:", self.audio_mode)
        
        self.buffer_duration = QSpinBox()
        self.buffer_duration.setRange(1, 30)
        self.buffer_duration.setSuffix(" minutes")
        self.buffer_duration.setMinimumHeight(self.scale(40))
        mode_layout.addRow("Buffer Duration:", self.buffer_duration)
        
        self.processing_interval = QSlider(Qt.Horizontal)
        self.processing_interval.setRange(5, 50)
        self.processing_interval.setValue(16)
        self.processing_interval.setMinimumHeight(self.scale(40))
        self.processing_label = QLabel("1.6s")
        self.processing_label.setMinimumWidth(self.scale(50))
        self.processing_label.setMinimumHeight(self.scale(28))
        self.processing_interval.valueChanged.connect(
            lambda v: self.processing_label.setText(f"{v/10:.1f}s")
        )
        
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(self.processing_interval)
        interval_layout.addWidget(self.processing_label)
        mode_layout.addRow("Processing Interval:", interval_layout)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # System Audio Monitoring
        system_audio_group = QGroupBox("🔊 System Audio Monitoring")
        system_audio_group.setMinimumHeight(self.scale(400))
        system_audio_layout = QVBoxLayout()
        system_audio_layout.setSpacing(self.scale(15))
        
        # Full system audio monitoring toggle
        self.full_system_audio = QCheckBox("Monitor all system audio (overrides specific app selection)")
        self.full_system_audio.setMinimumHeight(self.scale(32))
        self.full_system_audio.setStyleSheet("font-weight: 600; color: #ffffff;")
        self.full_system_audio.toggled.connect(self.on_full_system_audio_changed)
        self.full_system_audio.toggled.connect(self.update_monitoring_status)
        system_audio_layout.addWidget(self.full_system_audio)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #404040; background-color: #404040;")
        system_audio_layout.addWidget(separator)
        
        # Application selection
        app_selection_label = QLabel("Select specific applications to monitor:")
        app_selection_label.setStyleSheet("color: #e6e6e6; font-style: italic; margin-top: 10px;")
        app_selection_label.setMinimumHeight(self.scale(28))
        system_audio_layout.addWidget(app_selection_label)
        
        # Add status indicator
        self.monitoring_status = QLabel("📊 Currently monitoring: Loading...")
        self.monitoring_status.setStyleSheet("color: #0078d4; font-weight: 600; margin-bottom: 10px; padding: 8px; background: #1a1a1a; border-radius: 4px;")
        self.monitoring_status.setMinimumHeight(self.scale(32))
        self.monitoring_status.setWordWrap(True)
        system_audio_layout.addWidget(self.monitoring_status)
        
        # Create a grid layout for application checkboxes
        apps_widget = QWidget()
        apps_layout = QGridLayout(apps_widget)
        apps_layout.setSpacing(self.scale(15))
        
        # Meeting/Conferencing Applications (default enabled)
        meeting_apps = [
            ("Google Meet", "google_meet", "🟢"),
            ("Zoom", "zoom", "🔵"),
            ("Microsoft Teams", "teams", "🟣"),
            ("Skype", "skype", "🔷"),
            ("Discord", "discord", "🟦"),
            ("Slack", "slack", "🟨"),
            ("WebEx", "webex", "🟧"),
            ("GoToMeeting", "gotomeeting", "🟫")
        ]
        
        # Communication & Productivity Apps
        other_apps = [
            ("Chrome/Edge Browser", "browser", "🌐"),
            ("Firefox", "firefox", "🦊"),
            ("Spotify", "spotify", "🎵"),
            ("YouTube", "youtube", "📺"),
            ("VLC Media Player", "vlc", "🎬"),
            ("OBS Studio", "obs", "📹"),
            ("Custom Application", "custom", "⚙️")
        ]
        
        self.app_checkboxes = {}
        
        # Add meeting apps (left column)
        meeting_label = QLabel("📞 Meeting & Communication Apps (Enabled by Default)")
        meeting_label.setStyleSheet("font-weight: 600; color: #0078d4; margin-bottom: 5px;")
        meeting_label.setMinimumHeight(self.scale(32))
        apps_layout.addWidget(meeting_label, 0, 0, 1, 2)
        
        row = 1
        for app_name, app_key, emoji in meeting_apps:
            checkbox = QCheckBox(f"{emoji} {app_name}")
            checkbox.setMinimumHeight(self.scale(32))
            checkbox.setChecked(True)  # Default to enabled for meeting apps
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #ffffff;
                    font-weight: 500;
                }
                QCheckBox::indicator:checked {
                    background: #0078d4;
                    border: 2px solid #0078d4;
                }
            """)
            checkbox.toggled.connect(self.update_monitoring_status)
            self.app_checkboxes[app_key] = checkbox
            apps_layout.addWidget(checkbox, row, 0)
            row += 1
        
        # Add other apps (right column)
        other_label = QLabel("🖥️ Other Applications (Disabled by Default)")
        other_label.setStyleSheet("font-weight: 600; color: #666666; margin-bottom: 5px;")
        other_label.setMinimumHeight(self.scale(32))
        apps_layout.addWidget(other_label, 0, 2, 1, 2)
        
        row = 1
        for app_name, app_key, emoji in other_apps:
            checkbox = QCheckBox(f"{emoji} {app_name}")
            checkbox.setMinimumHeight(self.scale(32))
            checkbox.setChecked(False)  # Default to disabled for other apps
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #ffffff;
                    font-weight: 500;
                }
                QCheckBox::indicator:checked {
                    background: #0078d4;
                    border: 2px solid #0078d4;
                }
            """)
            checkbox.toggled.connect(self.update_monitoring_status)
            self.app_checkboxes[app_key] = checkbox
            apps_layout.addWidget(checkbox, row, 2)
            row += 1
        
        # Custom application input
        custom_layout = QHBoxLayout()
        self.custom_app_input = QLineEdit()
        self.custom_app_input.setPlaceholderText("Enter custom application name (e.g., MyApp.exe)")
        self.custom_app_input.setMinimumHeight(self.scale(40))
        self.custom_app_input.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        
        add_custom_btn = QPushButton("➕ Add")
        add_custom_btn.setMinimumHeight(self.scale(40))
        add_custom_btn.setMaximumWidth(self.scale(80))
        add_custom_btn.clicked.connect(self.add_custom_application)
        
        custom_layout.addWidget(self.custom_app_input)
        custom_layout.addWidget(add_custom_btn)
        apps_layout.addLayout(custom_layout, row, 2, 1, 2)
        
        system_audio_layout.addWidget(apps_widget)
        
        # Audio filtering options
        filter_label = QLabel("🎛️ Audio Filtering:")
        filter_label.setStyleSheet("font-weight: 600; color: #ffffff; margin-top: 15px;")
        filter_label.setMinimumHeight(self.scale(28))
        system_audio_layout.addWidget(filter_label)
        
        self.filter_music = QCheckBox("🎵 Filter out music and non-speech audio (recommended)")
        self.filter_music.setMinimumHeight(self.scale(32))
        self.filter_music.setChecked(True)
        self.filter_music.setToolTip("Uses AI to detect and ignore music, sound effects, and other non-speech audio")
        system_audio_layout.addWidget(self.filter_music)
        
        self.speech_detection_threshold = QSlider(Qt.Horizontal)
        self.speech_detection_threshold.setRange(10, 90)
        self.speech_detection_threshold.setValue(60)
        self.speech_detection_threshold.setMinimumHeight(self.scale(40))
        self.speech_threshold_label = QLabel("60%")
        self.speech_threshold_label.setMinimumWidth(self.scale(50))
        self.speech_threshold_label.setMinimumHeight(self.scale(28))
        self.speech_detection_threshold.valueChanged.connect(
            lambda v: self.speech_threshold_label.setText(f"{v}%")
        )
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Speech Detection Sensitivity:"))
        threshold_layout.addWidget(self.speech_detection_threshold)
        threshold_layout.addWidget(self.speech_threshold_label)
        system_audio_layout.addLayout(threshold_layout)
        
        system_audio_group.setLayout(system_audio_layout)
        layout.addWidget(system_audio_group)
        
        # Transcription Provider
        transcription_group = QGroupBox("📝 Transcription Settings")
        transcription_group.setMinimumHeight(self.scale(500))  # Increased for more content
        transcription_layout = QVBoxLayout()
        transcription_layout.setSpacing(self.scale(15))
        
        # Provider selection
        provider_form = QFormLayout()
        provider_form.setSpacing(self.scale(20))
        provider_form.setLabelAlignment(Qt.AlignLeft)
        
        self.transcription_provider = QComboBox()
        self.transcription_provider.addItems(["local_whisper", "google_speech", "azure_speech", "openai_whisper"])
        self.transcription_provider.setMinimumHeight(self.scale(40))
        self.transcription_provider.currentTextChanged.connect(self.on_transcription_provider_changed)
        provider_form.addRow("Provider:", self.transcription_provider)
        
        transcription_layout.addLayout(provider_form)
        
        # Local Whisper Settings
        self.whisper_group = QGroupBox("🤖 Local Whisper Configuration")
        self.whisper_group.setMinimumHeight(self.scale(120))
        whisper_layout = QFormLayout()
        whisper_layout.setSpacing(self.scale(15))
        whisper_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.whisper_model = QComboBox()
        self.whisper_model.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_model.setMinimumHeight(self.scale(40))
        whisper_layout.addRow("Model Size:", self.whisper_model)
        
        self.whisper_group.setLayout(whisper_layout)
        transcription_layout.addWidget(self.whisper_group)
        
        # Google Speech Settings
        self.google_speech_group = QGroupBox("🔴 Google Speech-to-Text Configuration")
        self.google_speech_group.setMinimumHeight(self.scale(200))
        google_layout = QVBoxLayout()
        google_layout.setSpacing(self.scale(15))
        
        # JSON config file option
        json_file_layout = QHBoxLayout()
        self.google_json_file = QLineEdit()
        self.google_json_file.setPlaceholderText("Path to Google Cloud service account JSON file")
        self.google_json_file.setMinimumHeight(self.scale(40))
        self.google_json_file.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        
        browse_json_btn = QPushButton("📁 Browse")
        browse_json_btn.setMinimumHeight(self.scale(40))
        browse_json_btn.setMaximumWidth(self.scale(100))
        browse_json_btn.clicked.connect(self.browse_google_json_file)
        
        json_file_layout.addWidget(QLabel("Service Account JSON:"))
        json_file_layout.addWidget(self.google_json_file)
        json_file_layout.addWidget(browse_json_btn)
        google_layout.addLayout(json_file_layout)
        
        # Alternative: Direct JSON input
        google_layout.addWidget(QLabel("Or paste JSON content directly:"))
        self.google_json_content = QTextEdit()
        self.google_json_content.setMinimumHeight(self.scale(100))
        self.google_json_content.setPlaceholderText('{\n  "type": "service_account",\n  "project_id": "your-project",\n  "private_key_id": "...",\n  ...\n}')
        self.google_json_content.setStyleSheet("QTextEdit { color: #ffffff; font-family: 'Consolas', monospace; }")
        google_layout.addWidget(self.google_json_content)
        
        self.google_speech_group.setLayout(google_layout)
        transcription_layout.addWidget(self.google_speech_group)
        
        # Azure Speech Settings
        self.azure_speech_group = QGroupBox("🔷 Azure Speech Services Configuration")
        self.azure_speech_group.setMinimumHeight(self.scale(250))
        azure_speech_layout = QFormLayout()
        azure_speech_layout.setSpacing(self.scale(20))
        azure_speech_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.azure_speech_key = QLineEdit()
        self.azure_speech_key.setPlaceholderText("Your Azure Speech API key")
        self.azure_speech_key.setEchoMode(QLineEdit.Password)
        self.azure_speech_key.setMinimumHeight(self.scale(40))
        self.azure_speech_key.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        azure_speech_layout.addRow("API Key:", self.azure_speech_key)
        
        self.azure_speech_region = QLineEdit()
        self.azure_speech_region.setPlaceholderText("eastus")
        self.azure_speech_region.setMinimumHeight(self.scale(40))
        self.azure_speech_region.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        azure_speech_layout.addRow("Region:", self.azure_speech_region)
        
        self.azure_speech_endpoint = QLineEdit()
        self.azure_speech_endpoint.setPlaceholderText("https://your-region.api.cognitive.microsoft.com/ (optional)")
        self.azure_speech_endpoint.setMinimumHeight(self.scale(40))
        self.azure_speech_endpoint.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        azure_speech_layout.addRow("Custom Endpoint:", self.azure_speech_endpoint)
        
        self.azure_speech_language = QComboBox()
        self.azure_speech_language.addItems(["en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", "zh-CN", "ja-JP", "ko-KR"])
        self.azure_speech_language.setMinimumHeight(self.scale(40))
        azure_speech_layout.addRow("Language:", self.azure_speech_language)
        
        self.azure_speech_group.setLayout(azure_speech_layout)
        transcription_layout.addWidget(self.azure_speech_group)
        
        # OpenAI Whisper API Settings
        self.openai_whisper_group = QGroupBox("🟢 OpenAI Whisper API Configuration")
        self.openai_whisper_group.setMinimumHeight(self.scale(200))
        openai_whisper_layout = QFormLayout()
        openai_whisper_layout.setSpacing(self.scale(20))
        openai_whisper_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.openai_whisper_api_key = QLineEdit()
        self.openai_whisper_api_key.setPlaceholderText("Your OpenAI API key")
        self.openai_whisper_api_key.setEchoMode(QLineEdit.Password)
        self.openai_whisper_api_key.setMinimumHeight(self.scale(40))
        self.openai_whisper_api_key.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        openai_whisper_layout.addRow("API Key:", self.openai_whisper_api_key)
        
        self.openai_whisper_model = QComboBox()
        self.openai_whisper_model.addItems(["whisper-1"])
        self.openai_whisper_model.setMinimumHeight(self.scale(40))
        openai_whisper_layout.addRow("Model:", self.openai_whisper_model)
        
        self.openai_whisper_language = QComboBox()
        self.openai_whisper_language.addItems(["auto-detect", "en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"])
        self.openai_whisper_language.setMinimumHeight(self.scale(40))
        openai_whisper_layout.addRow("Language:", self.openai_whisper_language)
        
        self.openai_whisper_group.setLayout(openai_whisper_layout)
        transcription_layout.addWidget(self.openai_whisper_group)
        
        transcription_group.setLayout(transcription_layout)
        layout.addWidget(transcription_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, "🎤 Audio")
    
    def setup_ui_tab(self):
        """Setup UI settings tab"""
        tab = QScrollArea()
        content = QWidget()
        
        # Set proper size policy for content to expand
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.setMinimumSize(self.scale(1200), self.scale(600))
        
        # Ensure dark background
        content.setStyleSheet(f"""
            QWidget {{
                background: #141414;
            }}
            QSpinBox {{
                background: #1a1a1a;
                color: #ffffff;
                border: 1px solid #404040;
                padding: {self.scale(4)}px {self.scale(8)}px;
            }}
            QSpinBox:hover {{
                background: #262626;
                border: 1px solid #0078d4;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: #262626;
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(content)
        layout.setSpacing(self.scale(25))
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(30))
        
        # Appearance
        appearance_group = QGroupBox("🎨 Appearance")
        appearance_group.setMinimumHeight(self.scale(500))  # Increased height for theme option
        appearance_layout = QFormLayout()
        appearance_layout.setSpacing(self.scale(20))
        appearance_layout.setLabelAlignment(Qt.AlignLeft)
        
        # Ensure consistent styling for the group box
        appearance_group.setStyleSheet(f"""
            QGroupBox {{
                background: #1a1a1a;
                border: 1px solid #404040;
                color: #ffffff;
            }}
        """)
        
        # Theme Selection
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Dark Mode", "Light Mode"])
        self.theme_selector.setMinimumHeight(self.scale(40))
        self.theme_selector.setToolTip("Choose between light and dark theme")
        self.theme_selector.currentTextChanged.connect(self.on_theme_changed)
        appearance_layout.addRow("Theme:", self.theme_selector)
        
        self.size_multiplier = QSlider(Qt.Horizontal)
        self.size_multiplier.setRange(10, 40)
        self.size_multiplier.setValue(10)
        self.size_multiplier.setMinimumHeight(self.scale(40))
        self.size_label = QLabel("1.0x")
        self.size_label.setMinimumWidth(self.scale(60))
        self.size_label.setMinimumHeight(self.scale(28))
        self.size_multiplier.valueChanged.connect(
            lambda v: self.size_label.setText(f"{v/10:.1f}x")
        )
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.size_multiplier)
        size_layout.addWidget(self.size_label)
        appearance_layout.addRow("Size Multiplier:", size_layout)
        
        self.show_transcript = QCheckBox("Show live transcript in expanded view")
        self.show_transcript.setMinimumHeight(self.scale(32))
        appearance_layout.addRow("", self.show_transcript)
        
        self.hide_from_sharing = QCheckBox("Hide from screen sharing")
        self.hide_from_sharing.setMinimumHeight(self.scale(32))
        appearance_layout.addRow("", self.hide_from_sharing)
        
        self.auto_hide_seconds = QSpinBox()
        self.auto_hide_seconds.setRange(0, 60)
        self.auto_hide_seconds.setSuffix(" seconds (0 = disabled)")
        self.auto_hide_seconds.setMinimumHeight(self.scale(40))
        appearance_layout.addRow("Auto-hide Timer:", self.auto_hide_seconds)
        
        # Screen sharing detection
        self.enable_screen_sharing_detection = QCheckBox("Enable screen sharing detection")
        self.enable_screen_sharing_detection.setMinimumHeight(self.scale(32))
        self.enable_screen_sharing_detection.setToolTip("Automatically hide overlay when screen sharing apps are detected")
        appearance_layout.addRow("", self.enable_screen_sharing_detection)
        
        # Hide overlay for screenshots/debugging
        self.hide_overlay_for_screenshots = QCheckBox("Hide overlay for screenshots/debugging")
        self.hide_overlay_for_screenshots.setMinimumHeight(self.scale(32))
        self.hide_overlay_for_screenshots.setToolTip("Temporarily hide the entire overlay for taking clean screenshots or debugging UI issues")
        self.hide_overlay_for_screenshots.toggled.connect(self.on_hide_overlay_toggled)
        appearance_layout.addRow("", self.hide_overlay_for_screenshots)
        
        # Enhanced UI Features Group
        enhanced_group = QGroupBox("🚀 Enhanced Features")
        enhanced_group.setMinimumHeight(self.scale(350))
        enhanced_layout = QFormLayout()
        enhanced_layout.setSpacing(self.scale(20))
        enhanced_layout.setLabelAlignment(Qt.AlignLeft)
        
        # Background opacity slider
        self.background_opacity = QSlider(Qt.Horizontal)
        self.background_opacity.setRange(5, 50)  # 0.05 to 0.5 opacity
        self.background_opacity.setValue(15)  # Default 0.15
        self.background_opacity.setMinimumHeight(self.scale(40))
        self.opacity_label = QLabel("0.15")
        self.opacity_label.setMinimumWidth(self.scale(60))
        self.background_opacity.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v/100:.2f}")
        )
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.background_opacity)
        opacity_layout.addWidget(self.opacity_label)
        enhanced_layout.addRow("Background Opacity:", opacity_layout)
        
        # Blur effects
        self.enable_blur_effects = QCheckBox("Enable blur effects")
        self.enable_blur_effects.setMinimumHeight(self.scale(32))
        self.enable_blur_effects.setToolTip("Apply blur effects to background for professional look")
        enhanced_layout.addRow("", self.enable_blur_effects)
        
        # Smooth animations
        self.enable_smooth_animations = QCheckBox("Enable smooth animations")
        self.enable_smooth_animations.setMinimumHeight(self.scale(32))
        self.enable_smooth_animations.setToolTip("Use smooth animations for transitions and resizing")
        enhanced_layout.addRow("", self.enable_smooth_animations)
        
        # Auto-width adjustment
        self.enable_auto_width = QCheckBox("Enable auto-width adjustment")
        self.enable_auto_width.setMinimumHeight(self.scale(32))
        self.enable_auto_width.setToolTip("Automatically adjust overlay width based on content")
        enhanced_layout.addRow("", self.enable_auto_width)
        
        # Dynamic transparency
        self.enable_dynamic_transparency = QCheckBox("Enable dynamic transparency")
        self.enable_dynamic_transparency.setMinimumHeight(self.scale(32))
        self.enable_dynamic_transparency.setToolTip("Adjust transparency based on activity and context")
        enhanced_layout.addRow("", self.enable_dynamic_transparency)
        
        enhanced_group.setLayout(enhanced_layout)
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        layout.addWidget(enhanced_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, "🖥️ Interface")
    
    def setup_assistant_tab(self):
        """Setup MeetMinder behavior tab"""
        tab = QScrollArea()
        content = QWidget()
        
        # Set proper size policy for content to expand
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.setMinimumSize(self.scale(1200), self.scale(600))  # Set minimum size
        
        layout = QVBoxLayout(content)
        layout.setSpacing(self.scale(25))
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(30))
        
        # Behavior Settings
        behavior_group = QGroupBox("🧠 Assistant Behavior")
        behavior_group.setMinimumHeight(self.scale(400))  # Set minimum height for group
        behavior_layout = QFormLayout()
        behavior_layout.setSpacing(self.scale(20))  # Increased spacing
        behavior_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.activation_mode = QComboBox()
        self.activation_mode.addItems(["manual", "auto"])
        self.activation_mode.setMinimumHeight(self.scale(40))  # Larger height
        behavior_layout.addRow("Activation Mode:", self.activation_mode)
        
        self.verbosity = QComboBox()
        self.verbosity.addItems(["concise", "standard", "detailed"])
        self.verbosity.setMinimumHeight(self.scale(40))
        behavior_layout.addRow("Response Verbosity:", self.verbosity)
        
        self.response_style = QComboBox()
        self.response_style.addItems(["professional", "casual", "technical"])
        self.response_style.setMinimumHeight(self.scale(40))
        behavior_layout.addRow("Response Style:", self.response_style)
        
        self.input_prioritization = QComboBox()
        self.input_prioritization.addItems(["mic", "system_audio", "balanced"])
        self.input_prioritization.setMinimumHeight(self.scale(40))
        behavior_layout.addRow("Input Priority:", self.input_prioritization)
        
        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, "🧠 Assistant")
    
    def setup_prompts_tab(self):
        """Setup prompts configuration tab"""
        tab = QScrollArea()
        content = QWidget()
        
        # Set proper size policy for content to expand
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.setMinimumSize(self.scale(1200), self.scale(600))
        
        layout = QVBoxLayout(content)
        layout.setSpacing(self.scale(25))
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(30))
        
        # System Prompt
        prompt_group = QGroupBox("📝 AI Prompt Configuration")
        prompt_group.setMinimumHeight(self.scale(500))
        prompt_layout = QVBoxLayout()
        prompt_layout.setSpacing(self.scale(15))
        
        prompt_info = QLabel("Customize the MeetMinder assistant's behavior and response style:")
        prompt_info.setStyleSheet("color: #e6e6e6; font-style: italic;")
        prompt_info.setMinimumHeight(self.scale(28))
        prompt_layout.addWidget(prompt_info)
        
        self.system_prompt = QTextEdit()
        self.system_prompt.setMinimumHeight(self.scale(350))
        self.system_prompt.setPlaceholderText("Enter system prompt that defines the MeetMinder assistant's behavior, tone, and expertise...")
        prompt_layout.addWidget(self.system_prompt)
        
        # Load/Save buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(self.scale(15))
        
        load_prompt_btn = QPushButton("📁 Load from File")
        load_prompt_btn.setMinimumHeight(self.scale(40))
        load_prompt_btn.clicked.connect(self.load_prompt_file)
        
        save_prompt_btn = QPushButton("💾 Save to File")
        save_prompt_btn.setMinimumHeight(self.scale(40))
        save_prompt_btn.clicked.connect(self.save_prompt_file)
        
        reset_prompt_btn = QPushButton("🔄 Reset to Default")
        reset_prompt_btn.setMinimumHeight(self.scale(40))
        reset_prompt_btn.clicked.connect(self.reset_prompt_to_default)
        
        button_layout.addWidget(load_prompt_btn)
        button_layout.addWidget(save_prompt_btn)
        button_layout.addWidget(reset_prompt_btn)
        button_layout.addStretch()
        prompt_layout.addLayout(button_layout)
        
        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, "📝 Prompts")
    
    def setup_knowledge_tab(self):
        """Setup knowledge graph management tab"""
        tab = QScrollArea()
        content = QWidget()
        
        # Set proper size policy for content to expand
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.setMinimumSize(self.scale(1200), self.scale(600))
        
        layout = QVBoxLayout(content)
        layout.setSpacing(self.scale(25))
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(30))
        
        # Knowledge Graph Settings
        knowledge_group = QGroupBox("🧠 Knowledge Graph")
        knowledge_group.setMinimumHeight(self.scale(500))
        knowledge_layout = QVBoxLayout()
        knowledge_layout.setSpacing(self.scale(15))
        
        # Enable/disable
        self.enable_topic_graph = QCheckBox("Enable topic analysis and suggestions")
        self.enable_topic_graph.setMinimumHeight(self.scale(32))
        knowledge_layout.addWidget(self.enable_topic_graph)
        
        # Settings
        settings_layout = QFormLayout()
        settings_layout.setSpacing(self.scale(20))
        settings_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.matching_threshold = QSlider(Qt.Horizontal)
        self.matching_threshold.setRange(1, 100)
        self.matching_threshold.setValue(60)
        self.matching_threshold.setMinimumHeight(self.scale(40))
        self.matching_label = QLabel("60%")
        self.matching_label.setMinimumHeight(self.scale(28))
        self.matching_threshold.valueChanged.connect(
            lambda v: self.matching_label.setText(f"{v}%")
        )
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(self.matching_threshold)
        threshold_layout.addWidget(self.matching_label)
        settings_layout.addRow("Matching Threshold:", threshold_layout)
        
        self.max_matches = QSpinBox()
        self.max_matches.setRange(1, 10)
        self.max_matches.setValue(3)
        self.max_matches.setMinimumHeight(self.scale(40))
        settings_layout.addRow("Max Suggestions:", self.max_matches)
        
        knowledge_layout.addLayout(settings_layout)
        
        # Topic definitions
        topic_info = QLabel("Define topics and their relationships (one per line):")
        topic_info.setStyleSheet("color: #e6e6e6; margin-top: 15px;")
        topic_info.setMinimumHeight(self.scale(28))
        knowledge_layout.addWidget(topic_info)
        
        self.topic_definitions = QTextEdit()
        self.topic_definitions.setMinimumHeight(self.scale(250))
        self.topic_definitions.setPlaceholderText("""Example topic definitions:
Programming -> Python (suggestion: "Consider using virtual environments")
Programming -> JavaScript (suggestion: "Don't forget async/await for promises")
Meetings -> Planning (suggestion: "Create action items with deadlines")
Meetings -> Review (suggestion: "Document key decisions and next steps")""")
        knowledge_layout.addWidget(self.topic_definitions)
        
        # Buttons
        topic_button_layout = QHBoxLayout()
        topic_button_layout.setSpacing(self.scale(15))
        
        import_topics_btn = QPushButton("📁 Import Topics")
        import_topics_btn.setMinimumHeight(self.scale(40))
        import_topics_btn.clicked.connect(self.import_topics)
        
        export_topics_btn = QPushButton("💾 Export Topics")
        export_topics_btn.setMinimumHeight(self.scale(40))
        export_topics_btn.clicked.connect(self.export_topics)
        
        clear_topics_btn = QPushButton("🗑️ Clear All")
        clear_topics_btn.setMinimumHeight(self.scale(40))
        clear_topics_btn.clicked.connect(self.clear_topics)
        
        topic_button_layout.addWidget(import_topics_btn)
        topic_button_layout.addWidget(export_topics_btn)
        topic_button_layout.addWidget(clear_topics_btn)
        topic_button_layout.addStretch()
        knowledge_layout.addLayout(topic_button_layout)
        
        knowledge_group.setLayout(knowledge_layout)
        layout.addWidget(knowledge_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, "🧠 Knowledge")
    
    def setup_hotkeys_tab(self):
        """Setup hotkeys configuration tab"""
        tab = QScrollArea()
        content = QWidget()
        
        # Set proper size policy for content to expand
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.setMinimumSize(self.scale(1200), self.scale(600))
        
        layout = QVBoxLayout(content)
        layout.setSpacing(self.scale(25))
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(30))
        
        # Hotkeys
        hotkeys_group = QGroupBox("⌨️ Global Hotkeys")
        hotkeys_group.setMinimumHeight(self.scale(350))
        hotkeys_layout = QFormLayout()
        hotkeys_layout.setSpacing(self.scale(20))
        hotkeys_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.trigger_assistance = QLineEdit()
        self.trigger_assistance.setMinimumHeight(self.scale(40))
        hotkeys_layout.addRow("Trigger AI:", self.trigger_assistance)
        
        self.toggle_overlay = QLineEdit()
        self.toggle_overlay.setMinimumHeight(self.scale(40))
        hotkeys_layout.addRow("Toggle Overlay:", self.toggle_overlay)
        
        self.take_screenshot = QLineEdit()
        self.take_screenshot.setMinimumHeight(self.scale(40))
        hotkeys_layout.addRow("Screenshot:", self.take_screenshot)
        
        self.emergency_reset = QLineEdit()
        self.emergency_reset.setMinimumHeight(self.scale(40))
        hotkeys_layout.addRow("Emergency Reset:", self.emergency_reset)
        
        self.toggle_hide_for_screenshots = QLineEdit()
        self.toggle_hide_for_screenshots.setMinimumHeight(self.scale(40))
        self.toggle_hide_for_screenshots.setPlaceholderText("e.g., Ctrl+H")
        self.toggle_hide_for_screenshots.setToolTip("Hotkey to quickly toggle overlay hiding for screenshots/debugging")
        hotkeys_layout.addRow("Toggle Hide Overlay:", self.toggle_hide_for_screenshots)
        
        hotkeys_group.setLayout(hotkeys_layout)
        layout.addWidget(hotkeys_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, "⌨️ Hotkeys")
    
    def setup_debug_tab(self):
        """Setup debug settings tab"""
        tab = QScrollArea()
        content = QWidget()
        
        # Set proper size policy for content to expand
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.setMinimumSize(self.scale(1200), self.scale(600))
        
        layout = QVBoxLayout(content)
        layout.setSpacing(self.scale(25))
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(30))
        
        # Debug Settings
        debug_group = QGroupBox("🐛 Debug & Logging")
        debug_group.setMinimumHeight(self.scale(400))
        debug_layout = QVBoxLayout()
        debug_layout.setSpacing(self.scale(15))
        
        self.debug_enabled = QCheckBox("Enable debug mode")
        self.debug_enabled.setMinimumHeight(self.scale(32))
        debug_layout.addWidget(self.debug_enabled)
        
        self.verbose_logging = QCheckBox("Verbose logging")
        self.verbose_logging.setMinimumHeight(self.scale(32))
        debug_layout.addWidget(self.verbose_logging)
        
        self.save_transcriptions = QCheckBox("Save transcriptions to files")
        self.save_transcriptions.setMinimumHeight(self.scale(32))
        debug_layout.addWidget(self.save_transcriptions)
        
        self.save_audio_chunks = QCheckBox("Save audio chunks for debugging")
        self.save_audio_chunks.setMinimumHeight(self.scale(32))
        debug_layout.addWidget(self.save_audio_chunks)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(self.scale(20))
        form_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.max_debug_files = QSpinBox()
        self.max_debug_files.setRange(10, 1000)
        self.max_debug_files.setValue(100)
        form_layout.addRow("Max Debug Files:", self.max_debug_files)
        
        debug_layout.addLayout(form_layout)
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, "🐛 Debug")
    
    def on_provider_changed(self, provider):
        """Handle AI provider selection change"""
        self.azure_group.setVisible(provider == "azure_openai")
        self.openai_group.setVisible(provider == "openai")
        self.gemini_group.setVisible(provider == "google_gemini")
        self.deepseek_group.setVisible(provider == "deepseek")
        self.claude_group.setVisible(provider == "claude")
    
    def on_full_system_audio_changed(self, checked):
        """Handle full system audio monitoring toggle"""
        # Disable/enable specific app checkboxes when full monitoring is toggled
        for checkbox in self.app_checkboxes.values():
            checkbox.setEnabled(not checked)
        
        # Update custom app input
        self.custom_app_input.setEnabled(not checked)
        
        # Visual feedback
        if checked:
            for checkbox in self.app_checkboxes.values():
                checkbox.setStyleSheet("color: #666666;")
        else:
            for checkbox in self.app_checkboxes.values():
                checkbox.setStyleSheet("color: #ffffff;")
    
    def on_transcription_provider_changed(self, provider):
        """Handle transcription provider selection change"""
        self.whisper_group.setVisible(provider == "local_whisper")
        self.google_speech_group.setVisible(provider == "google_speech")
        self.azure_speech_group.setVisible(provider == "azure_speech")
        self.openai_whisper_group.setVisible(provider == "openai_whisper")
    
    def on_theme_changed(self, theme_name):
        """Handle theme change"""
        print(f"🎨 Theme changed to: {theme_name}")
        
        # Apply theme immediately to settings dialog
        self.apply_theme_to_dialog(theme_name)
    
    def apply_current_theme(self):
        """Apply the current theme from config to the dialog"""
        try:
            from ui.themes import ThemeManager
            from core.config import ConfigManager
            
            # Get current theme from config
            config = ConfigManager()
            current_theme = config.get_ui_config().get('overlay', {}).get('theme', 'dark')
            
            theme = ThemeManager.get_theme(current_theme)
            
            # Generate and apply stylesheet
            stylesheet = ThemeManager.generate_settings_stylesheet(theme, self.scale_factor)
            self.setStyleSheet(stylesheet)
            
            print(f"✅ Applied {current_theme} theme to settings dialog")
            
        except Exception as e:
            print(f"❌ Error applying theme: {e}")
            # Fallback to basic dark theme
            self.setStyleSheet("QDialog { background: #141414; color: #ffffff; }")

    def apply_theme_to_dialog(self, theme_name):
        """Apply theme to the settings dialog"""
        try:
            from ui.themes import ThemeManager
            
            # Convert display name to internal name
            internal_theme = "light" if "Light" in theme_name else "dark"
            theme = ThemeManager.get_theme(internal_theme)
            
            # Generate and apply stylesheet
            stylesheet = ThemeManager.generate_settings_stylesheet(theme, self.scale_factor)
            self.setStyleSheet(stylesheet)
            
            # Clear any individual widget overrides that might conflict
            self.clear_hardcoded_styles()
            
            print(f"✅ Applied {internal_theme} theme to settings dialog")
            
        except Exception as e:
            print(f"❌ Error applying theme: {e}")
            # Keep current dark theme as fallback
    
    def clear_hardcoded_styles(self):
        """Clear hardcoded color styles from widgets to ensure theme takes precedence"""
        # Clear styles from specific widgets that had hardcoded colors
        widgets_to_clear = [
            # AI Provider fields
            getattr(self, 'azure_endpoint', None),
            getattr(self, 'azure_api_key', None),
            getattr(self, 'azure_model', None),
            getattr(self, 'azure_deployment', None),
            getattr(self, 'azure_api_version', None),
            getattr(self, 'deepseek_api_key', None),
            getattr(self, 'deepseek_base_url', None),
            getattr(self, 'deepseek_model', None),
            getattr(self, 'claude_api_key', None),
            getattr(self, 'claude_base_url', None),
            getattr(self, 'claude_model', None),
            # Audio fields
            getattr(self, 'custom_app_input', None),
            getattr(self, 'google_json_file', None),
            getattr(self, 'google_json_content', None),
            getattr(self, 'azure_speech_key', None),
            getattr(self, 'azure_speech_region', None),
            getattr(self, 'azure_speech_endpoint', None),
            getattr(self, 'openai_whisper_api_key', None),
            # System audio monitoring
            getattr(self, 'full_system_audio', None),
            getattr(self, 'monitoring_status', None),
        ]
        
        for widget in widgets_to_clear:
            if widget:
                widget.setStyleSheet("")
        
        # Also clear any labels or other elements that might have hardcoded colors
        # This covers labels like prompt_info, topic_info, meeting_label, etc.
        for child in self.findChildren(QLabel):
            if child.styleSheet() and 'color:' in child.styleSheet():
                child.setStyleSheet("")
        
        # Clear checkbox styles in audio monitoring section
        for child in self.findChildren(QCheckBox):
            if child.styleSheet() and 'color:' in child.styleSheet():
                child.setStyleSheet("")
    
    def browse_google_json_file(self):
        """Browse for Google Cloud service account JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Google Cloud Service Account JSON", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.google_json_file.setText(file_path)
            # Optionally load and validate the JSON content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_content = f.read()
                    # Basic validation - check if it's valid JSON
                    json.loads(json_content)
                    self.google_json_content.setPlainText(json_content)
                    QMessageBox.information(self, "Success", "JSON file loaded successfully!")
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Invalid JSON", "The selected file does not contain valid JSON.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load file: {e}")
    
    def add_custom_application(self):
        """Add a custom application to monitor"""
        app_name = self.custom_app_input.text().strip()
        if not app_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter an application name.")
            return
        
        # Create a unique key from the app name
        app_key = f"custom_{app_name.lower().replace(' ', '_').replace('.exe', '')}"
        
        # Check if already exists
        if app_key in self.app_checkboxes:
            QMessageBox.information(self, "Already Added", f"'{app_name}' is already in the list.")
            return
        
        # Add the checkbox (find a good position for it)
        checkbox = QCheckBox(f"⚙️ {app_name}")
        checkbox.setMinimumHeight(self.scale(32))
        checkbox.setChecked(True)
        self.app_checkboxes[app_key] = checkbox
        
        # Add to the layout - find the custom application section
        # For now, we'll show a success message and suggest restart
        QMessageBox.information(
            self, "Custom App Added", 
            f"'{app_name}' has been added to the monitoring list.\n\nNote: You may need to restart the application for changes to take effect."
        )
        
        # Clear the input
        self.custom_app_input.clear()
    
    def load_prompt_file(self):
        """Load prompt from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Prompt File", "", "Markdown Files (*.md);;Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.system_prompt.setPlainText(content)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load file: {e}")
    
    def save_prompt_file(self):
        """Save prompt to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Prompt File", "prompt_rules.md", "Markdown Files (*.md);;Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.system_prompt.toPlainText())
                QMessageBox.information(self, "Success", "Prompt saved successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save file: {e}")
    
    def reset_prompt_to_default(self):
        """Reset prompt to default"""
        default_prompt = """You are an intelligent AI meeting assistant designed to provide helpful, contextual responses based on real-time audio transcription and user interactions.

**Core Behavior:**
- Be concise yet comprehensive in your responses
- Provide actionable insights and suggestions
- Adapt your tone to the context (professional for meetings, casual for general chat)
- Focus on being helpful rather than just informative

**Response Guidelines:**
- Keep responses under 200 words unless detailed explanation is needed
- Use bullet points for lists and actionable items
- Include relevant examples when helpful
- Ask clarifying questions when context is unclear

**Context Awareness:**
- Pay attention to meeting dynamics and conversation flow
- Identify key topics, decisions, and action items
- Provide relevant suggestions based on the current discussion
- Be sensitive to the professional or casual nature of the interaction

**Expertise Areas:**
- Meeting facilitation and note-taking
- Technical problem-solving
- Project management insights
- Communication enhancement
- General productivity tips"""
        
        self.system_prompt.setPlainText(default_prompt)
    
    def import_topics(self):
        """Import topics from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Topics", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.topic_definitions.setPlainText(content)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to import topics: {e}")
    
    def export_topics(self):
        """Export topics to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Topics", "topics.txt", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.topic_definitions.toPlainText())
                QMessageBox.information(self, "Success", "Topics exported successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to export topics: {e}")
    
    def clear_topics(self):
        """Clear all topics"""
        reply = QMessageBox.question(
            self, "Clear Topics", 
            "Are you sure you want to clear all topic definitions?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.topic_definitions.clear()
    
    def setup_buttons(self, layout):
        """Setup dialog buttons"""
        button_layout = QHBoxLayout()
        
        # Save button
        save_button = QPushButton("💾 Save Settings")
        save_button.setProperty("class", "primary")
        save_button.clicked.connect(self.save_settings)
        
        # Cancel button
        cancel_button = QPushButton("❌ Cancel")
        cancel_button.clicked.connect(self.reject)
        
        # Reset button
        reset_button = QPushButton("🔄 Reset to Defaults")
        reset_button.clicked.connect(self.reset_to_defaults)
        
        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
    
    def load_current_settings(self):
        """Load current settings into the UI"""
        # AI Provider
        ai_provider = self.current_config.get('ai_provider', {})
        self.ai_provider_type.setCurrentText(ai_provider.get('type', 'azure_openai'))
        
        # Azure OpenAI (Legacy)
        azure = ai_provider.get('azure_openai', {})
        self.azure_endpoint.setText(azure.get('endpoint', ''))
        self.azure_api_key.setText(azure.get('api_key', ''))
        self.azure_model.setText(azure.get('model', ''))
        self.azure_deployment.setText(azure.get('deployment_name', ''))
        self.azure_api_version.setText(azure.get('api_version', '2024-02-01'))
        
        # OpenAI
        openai = ai_provider.get('openai', {})
        self.openai_api_key.setText(openai.get('api_key', ''))
        self.openai_model.setText(openai.get('model', ''))
        
        # Gemini
        gemini = ai_provider.get('google_gemini', {})
        self.gemini_api_key.setText(gemini.get('api_key', ''))
        self.gemini_model.setText(gemini.get('model', ''))
        self.gemini_project_id.setText(str(gemini.get('project_id', '')))
        
        # DeepSeek
        deepseek = ai_provider.get('deepseek', {})
        self.deepseek_api_key.setText(deepseek.get('api_key', ''))
        self.deepseek_base_url.setText(deepseek.get('base_url', 'https://api.deepseek.com'))
        self.deepseek_model.setText(deepseek.get('model', 'deepseek-coder'))
        
        # Claude
        claude = ai_provider.get('claude', {})
        self.claude_api_key.setText(claude.get('api_key', ''))
        self.claude_base_url.setText(claude.get('base_url', 'https://api.anthropic.com'))
        self.claude_model.setText(claude.get('model', 'claude-3-sonnet-20240229'))
        
        # Audio
        audio = self.current_config.get('audio', {})
        self.audio_mode.setCurrentText(audio.get('mode', 'dual_stream'))
        self.buffer_duration.setValue(audio.get('buffer_duration_minutes', 5))
        processing_interval = audio.get('processing_interval_seconds', 1.6)
        self.processing_interval.setValue(int(processing_interval * 10))
        
        # System Audio Monitoring
        system_audio = audio.get('system_audio_monitoring', {})
        self.full_system_audio.setChecked(system_audio.get('full_monitoring', False))
        
        # Load monitored applications
        monitored_apps = system_audio.get('monitored_applications', {
            # Default to meeting apps enabled
            'google_meet': True, 'zoom': True, 'teams': True, 'skype': True,
            'discord': True, 'slack': True, 'webex': True, 'gotomeeting': True,
            # Other apps disabled by default
            'browser': False, 'firefox': False, 'spotify': False, 'youtube': False,
            'vlc': False, 'obs': False, 'custom': False
        })
        
        for app_key, checkbox in self.app_checkboxes.items():
            checkbox.setChecked(monitored_apps.get(app_key, False))
        
        # Audio filtering settings
        audio_filtering = system_audio.get('audio_filtering', {})
        self.filter_music.setChecked(audio_filtering.get('filter_non_speech', True))
        speech_threshold = int(audio_filtering.get('speech_detection_threshold', 0.6) * 100)
        self.speech_detection_threshold.setValue(speech_threshold)
        
        # Update UI state based on full monitoring setting
        self.on_full_system_audio_changed(self.full_system_audio.isChecked())
        
        # Transcription
        transcription = self.current_config.get('transcription', {})
        self.transcription_provider.setCurrentText(transcription.get('provider', 'local_whisper'))
        
        # Local Whisper config
        whisper_config = transcription.get('whisper', {})
        self.whisper_model.setCurrentText(whisper_config.get('model_size', 'base'))
        
        # Google Speech config
        google_config = transcription.get('google_speech', {})
        self.google_json_file.setText(google_config.get('json_file_path', ''))
        self.google_json_content.setPlainText(google_config.get('json_content', ''))
        
        # Azure Speech config
        azure_speech_config = transcription.get('azure_speech', {})
        self.azure_speech_key.setText(azure_speech_config.get('api_key', ''))
        self.azure_speech_region.setText(azure_speech_config.get('region', 'eastus'))
        self.azure_speech_endpoint.setText(azure_speech_config.get('endpoint', ''))
        self.azure_speech_language.setCurrentText(azure_speech_config.get('language', 'en-US'))
        
        # OpenAI Whisper config
        openai_whisper_config = transcription.get('openai_whisper', {})
        self.openai_whisper_api_key.setText(openai_whisper_config.get('api_key', ''))
        self.openai_whisper_model.setCurrentText(openai_whisper_config.get('model', 'whisper-1'))
        self.openai_whisper_language.setCurrentText(openai_whisper_config.get('language', 'auto-detect'))
        
        # Update transcription provider visibility
        self.on_transcription_provider_changed(self.transcription_provider.currentText())
        
        # UI
        ui = self.current_config.get('ui', {}).get('overlay', {})
        size_mult = ui.get('size_multiplier', 1.0)
        self.size_multiplier.setValue(int(size_mult * 10))
        self.show_transcript.setChecked(ui.get('show_transcript', False))
        self.hide_from_sharing.setChecked(ui.get('hide_from_sharing', True))
        self.auto_hide_seconds.setValue(ui.get('auto_hide_seconds', 5))
        
        # Screen sharing detection
        screen_sharing = self.current_config.get('screen_sharing_detection', {})
        self.enable_screen_sharing_detection.setChecked(screen_sharing.get('enabled', False))
        
        # Enhanced UI Features
        enhanced_ui = ui.get('enhanced', {})
        self.background_opacity.setValue(int(enhanced_ui.get('background_opacity', 0.15) * 100))
        self.enable_blur_effects.setChecked(enhanced_ui.get('blur_enabled', True))
        self.enable_smooth_animations.setChecked(enhanced_ui.get('smooth_animations', True))
        self.enable_auto_width.setChecked(enhanced_ui.get('auto_width', True))
        self.enable_dynamic_transparency.setChecked(enhanced_ui.get('dynamic_transparency', False))
        
        # Hide overlay for screenshots/debugging
        self.hide_overlay_for_screenshots.setChecked(ui.get('hide_overlay_for_screenshots', False))
        
        # Theme selection
        theme = ui.get('theme', 'dark')
        theme_display_name = "Light Mode" if theme == 'light' else "Dark Mode"
        self.theme_selector.setCurrentText(theme_display_name)
        
        # Assistant
        assistant = self.current_config.get('assistant', {})
        self.activation_mode.setCurrentText(assistant.get('activation_mode', 'manual'))
        self.verbosity.setCurrentText(assistant.get('verbosity', 'standard'))
        self.response_style.setCurrentText(assistant.get('response_style', 'professional'))
        self.input_prioritization.setCurrentText(assistant.get('input_prioritization', 'system_audio'))
        
        # Load prompt from file if it exists
        try:
            with open('prompt_rules.md', 'r', encoding='utf-8') as f:
                self.system_prompt.setPlainText(f.read())
        except FileNotFoundError:
            self.reset_prompt_to_default()
        
        # Knowledge Graph
        topic_graph = self.current_config.get('topic_graph', {})
        self.enable_topic_graph.setChecked(topic_graph.get('enabled', True))
        self.matching_threshold.setValue(int(topic_graph.get('matching_threshold', 0.6) * 100))
        self.max_matches.setValue(topic_graph.get('max_matches', 3))
        
        # Hotkeys
        hotkeys = self.current_config.get('hotkeys', {})
        self.trigger_assistance.setText(hotkeys.get('trigger_assistance', 'ctrl+space'))
        self.toggle_overlay.setText(hotkeys.get('toggle_overlay', 'ctrl+b'))
        self.take_screenshot.setText(hotkeys.get('take_screenshot', 'ctrl+h'))
        self.emergency_reset.setText(hotkeys.get('emergency_reset', 'ctrl+shift+r'))
        self.toggle_hide_for_screenshots.setText(hotkeys.get('toggle_hide_for_screenshots', 'ctrl+shift+h'))
        
        # Debug
        debug = self.current_config.get('debug', {})
        self.debug_enabled.setChecked(debug.get('enabled', False))
        self.verbose_logging.setChecked(debug.get('verbose_logging', False))
        self.save_transcriptions.setChecked(debug.get('save_transcriptions', False))
        self.save_audio_chunks.setChecked(debug.get('save_audio_chunks', False))
        self.max_debug_files.setValue(debug.get('max_debug_files', 100))
        
        # Update visibility based on provider
        self.on_provider_changed(self.ai_provider_type.currentText())
        
        # Update monitoring status display
        self.update_monitoring_status()
    
    def save_settings(self):
        """Save all settings and emit signal"""
        new_config = {
            'ai_provider': {
                'type': self.ai_provider_type.currentText(),
                'azure_openai': {
                    'endpoint': self.azure_endpoint.text(),
                    'api_key': self.azure_api_key.text(),
                    'model': self.azure_model.text(),
                    'deployment_name': self.azure_deployment.text(),
                    'api_version': self.azure_api_version.text()
                },
                'openai': {
                    'api_key': self.openai_api_key.text(),
                    'model': self.openai_model.text()
                },
                'google_gemini': {
                    'api_key': self.gemini_api_key.text(),
                    'model': self.gemini_model.text(),
                    'project_id': self.gemini_project_id.text()
                },
                'deepseek': {
                    'api_key': self.deepseek_api_key.text(),
                    'base_url': self.deepseek_base_url.text(),
                    'model': self.deepseek_model.text()
                },
                'claude': {
                    'api_key': self.claude_api_key.text(),
                    'base_url': self.claude_base_url.text(),
                    'model': self.claude_model.text()
                }
            },
            'audio': {
                'mode': self.audio_mode.currentText(),
                'buffer_duration_minutes': self.buffer_duration.value(),
                'processing_interval_seconds': self.processing_interval.value() / 10.0,
                'system_audio_monitoring': {
                    'full_monitoring': self.full_system_audio.isChecked(),
                    'monitored_applications': {app_key: checkbox.isChecked() for app_key, checkbox in self.app_checkboxes.items()},
                    'audio_filtering': {
                        'filter_non_speech': self.filter_music.isChecked(),
                        'speech_detection_threshold': self.speech_detection_threshold.value() / 100.0
                    }
                }
            },
            'transcription': {
                'provider': self.transcription_provider.currentText(),
                'whisper': {
                    'model_size': self.whisper_model.currentText()
                },
                'google_speech': {
                    'json_file_path': self.google_json_file.text(),
                    'json_content': self.google_json_content.toPlainText()
                },
                'azure_speech': {
                    'api_key': self.azure_speech_key.text(),
                    'region': self.azure_speech_region.text(),
                    'endpoint': self.azure_speech_endpoint.text(),
                    'language': self.azure_speech_language.currentText()
                },
                'openai_whisper': {
                    'api_key': self.openai_whisper_api_key.text(),
                    'model': self.openai_whisper_model.currentText(),
                    'language': self.openai_whisper_language.currentText()
                }
            },
            'ui': {
                'overlay': {
                    'theme': 'light' if 'Light' in self.theme_selector.currentText() else 'dark',
                    'size_multiplier': self.size_multiplier.value() / 10.0,
                    'show_transcript': self.show_transcript.isChecked(),
                    'hide_from_sharing': self.hide_from_sharing.isChecked(),
                    'auto_hide_seconds': self.auto_hide_seconds.value(),
                    'enhanced': {
                        'background_opacity': self.background_opacity.value() / 100.0,
                        'blur_enabled': self.enable_blur_effects.isChecked(),
                        'smooth_animations': self.enable_smooth_animations.isChecked(),
                        'auto_width': self.enable_auto_width.isChecked(),
                        'dynamic_transparency': self.enable_dynamic_transparency.isChecked()
                    }
                },
                'hide_overlay_for_screenshots': self.hide_overlay_for_screenshots.isChecked()
            },
            'screen_sharing_detection': {
                'enabled': self.enable_screen_sharing_detection.isChecked(),
                'auto_hide_overlay': True,
                'detection_interval_seconds': 3,
                'verbose_logging': False
            },
            'assistant': {
                'activation_mode': self.activation_mode.currentText(),
                'verbosity': self.verbosity.currentText(),
                'response_style': self.response_style.currentText(),
                'input_prioritization': self.input_prioritization.currentText()
            },
            'topic_graph': {
                'enabled': self.enable_topic_graph.isChecked(),
                'matching_threshold': self.matching_threshold.value() / 100.0,
                'max_matches': self.max_matches.value()
            },
            'hotkeys': {
                'trigger_assistance': self.trigger_assistance.text(),
                'toggle_overlay': self.toggle_overlay.text(),
                'take_screenshot': self.take_screenshot.text(),
                'emergency_reset': self.emergency_reset.text(),
                'toggle_hide_for_screenshots': self.toggle_hide_for_screenshots.text()
            },
            'debug': {
                'enabled': self.debug_enabled.isChecked(),
                'verbose_logging': self.verbose_logging.isChecked(),
                'save_transcriptions': self.save_transcriptions.isChecked(),
                'save_audio_chunks': self.save_audio_chunks.isChecked(),
                'max_debug_files': self.max_debug_files.value()
            }
        }
        
        # Save prompt to file
        try:
            with open('prompt_rules.md', 'w', encoding='utf-8') as f:
                f.write(self.system_prompt.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to save prompt file: {e}")
        
        # Save topic definitions
        try:
            with open('topic_definitions.txt', 'w', encoding='utf-8') as f:
                f.write(self.topic_definitions.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to save topic definitions: {e}")
        
        self.settings_changed.emit(new_config)
        self.accept()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self, "Reset Settings", 
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset to defaults - you could reload from a default config here
            self.reject()  # For now, just close the dialog 

    def update_monitoring_status(self):
        """Update the monitoring status label"""
        if self.full_system_audio.isChecked():
            self.monitoring_status.setText("📊 Currently monitoring: 🌐 ALL SYSTEM AUDIO")
            self.monitoring_status.setStyleSheet("color: #ff6b6b; font-weight: 600; margin-bottom: 10px; padding: 8px; background: #1a1a1a; border-radius: 4px;")
            return
        
        # Get enabled apps
        enabled_apps = []
        app_names = {
            'google_meet': 'Google Meet',
            'zoom': 'Zoom',
            'teams': 'Teams',
            'skype': 'Skype',
            'discord': 'Discord',
            'slack': 'Slack',
            'webex': 'WebEx',
            'gotomeeting': 'GoToMeeting',
            'browser': 'Browser',
            'firefox': 'Firefox',
            'spotify': 'Spotify',
            'youtube': 'YouTube',
            'vlc': 'VLC',
            'obs': 'OBS',
            'custom': 'Custom Apps'
        }
        
        for app_key, checkbox in self.app_checkboxes.items():
            if checkbox.isChecked():
                enabled_apps.append(app_names.get(app_key, app_key))
        
        if enabled_apps:
            if len(enabled_apps) <= 4:
                status_text = f"📊 Currently monitoring: {', '.join(enabled_apps)}"
            else:
                status_text = f"📊 Currently monitoring: {', '.join(enabled_apps[:3])} and {len(enabled_apps)-3} more"
            self.monitoring_status.setStyleSheet("color: #0078d4; font-weight: 600; margin-bottom: 10px; padding: 8px; background: #1a1a1a; border-radius: 4px;")
        else:
            status_text = "📊 Currently monitoring: ⚠️ No applications selected"
            self.monitoring_status.setStyleSheet("color: #ffa500; font-weight: 600; margin-bottom: 10px; padding: 8px; background: #1a1a1a; border-radius: 4px;")
        
        self.monitoring_status.setText(status_text)
    
    def on_hide_overlay_toggled(self, checked):
        """Handle hide overlay for screenshots/debugging toggle"""
        # Add any additional logic you want to execute when this toggle is changed
        print(f"Hide overlay for screenshots/debugging toggled: {'on' if checked else 'off'}")
    