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

# Import translation system
try:
    from utils.translation_manager import get_translation_manager, t, set_language
    TRANSLATIONS_AVAILABLE = True
except ImportError:
    TRANSLATIONS_AVAILABLE = False
    print("⚠️ Translation system not available in settings")
    def t(key: str, default: str = None, **kwargs) -> str:
        return default or key
    def set_language(lang: str):
        pass

class ModernSettingsDialog(QDialog):
    """Modern tabbed settings dialog with organized sections"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, current_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.current_config = current_config.copy()
        self.overlay_ref = parent  # Store reference to overlay for refreshing
        
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
        self.setWindowTitle(t("settings.title", "MeetMinder Settings"))
        
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
        self.setup_documents_tab()
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
        self.provider_group = QGroupBox(t("settings.ai_provider.title", "🤖 AI Provider"))
        provider_layout = QFormLayout()
        provider_layout.setSpacing(self.scale(20))
        provider_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.ai_provider_type = QComboBox()
        self.ai_provider_type.addItems(["azure_openai", "openai", "google_gemini", "deepseek", "claude"])
        self.ai_provider_type.setMinimumHeight(self.scale(40))
        self.ai_provider_type.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addRow(t("settings.ai_provider.provider_label", "Provider:"), self.ai_provider_type)
        
        self.provider_group.setLayout(provider_layout)
        layout.addWidget(self.provider_group)
        
        # Azure OpenAI Settings
        self.azure_group = QGroupBox(t("settings.ai_provider.azure.title", "🔷 Azure OpenAI Configuration"))
        self.azure_group.setMinimumHeight(self.scale(350))
        azure_layout = QFormLayout()
        azure_layout.setSpacing(self.scale(20))
        azure_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.azure_endpoint = QLineEdit()
        self.azure_endpoint.setPlaceholderText(t("settings.ai_provider.azure.endpoint_placeholder", "https://your-resource.openai.azure.com/"))
        self.azure_endpoint.setMinimumHeight(self.scale(40))

        azure_layout.addRow(t("settings.ai_provider.azure.endpoint", "Endpoint:"), self.azure_endpoint)
        
        self.azure_api_key = QLineEdit()
        self.azure_api_key.setPlaceholderText(t("settings.ai_provider.azure.api_key_placeholder", "Your Azure OpenAI API key"))
        self.azure_api_key.setEchoMode(QLineEdit.Password)
        self.azure_api_key.setMinimumHeight(self.scale(40))

        azure_layout.addRow(t("settings.ai_provider.azure.api_key", "API Key:"), self.azure_api_key)
        
        self.azure_model = QLineEdit()
        self.azure_model.setPlaceholderText(t("settings.ai_provider.azure.model_placeholder", "gpt-4"))
        self.azure_model.setMinimumHeight(self.scale(40))

        azure_layout.addRow(t("settings.ai_provider.azure.model", "Model:"), self.azure_model)
        
        self.azure_deployment = QLineEdit()
        self.azure_deployment.setPlaceholderText(t("settings.ai_provider.azure.deployment_placeholder", "your-deployment-name"))
        self.azure_deployment.setMinimumHeight(self.scale(40))

        azure_layout.addRow(t("settings.ai_provider.azure.deployment", "Deployment:"), self.azure_deployment)
        
        self.azure_api_version = QLineEdit()
        self.azure_api_version.setText("2024-06-01")
        self.azure_api_version.setMinimumHeight(self.scale(40))

        azure_layout.addRow(t("settings.ai_provider.azure.api_version", "API Version:"), self.azure_api_version)
        
        self.azure_group.setLayout(azure_layout)
        layout.addWidget(self.azure_group)
        
        # OpenAI Settings
        self.openai_group = QGroupBox(t("settings.ai_provider.openai.title", "🟢 OpenAI Configuration"))
        self.openai_group.setMinimumHeight(self.scale(200))
        openai_layout = QFormLayout()
        openai_layout.setSpacing(self.scale(20))
        openai_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.openai_api_key = QLineEdit()
        self.openai_api_key.setPlaceholderText(t("settings.ai_provider.openai.api_key_placeholder", "Your OpenAI API key"))
        self.openai_api_key.setEchoMode(QLineEdit.Password)
        self.openai_api_key.setMinimumHeight(self.scale(40))
        openai_layout.addRow(t("settings.ai_provider.openai.api_key", "API Key:"), self.openai_api_key)
        
        self.openai_model = QLineEdit()
        self.openai_model.setPlaceholderText(t("settings.ai_provider.openai.model_placeholder", "gpt-4"))
        self.openai_model.setMinimumHeight(self.scale(40))
        openai_layout.addRow(t("settings.ai_provider.openai.model", "Model:"), self.openai_model)
        
        self.openai_group.setLayout(openai_layout)
        layout.addWidget(self.openai_group)
        
        # Google Gemini Settings
        self.gemini_group = QGroupBox(t("settings.ai_provider.gemini.title", "🔴 Google Gemini Configuration"))
        self.gemini_group.setMinimumHeight(self.scale(250))
        gemini_layout = QFormLayout()
        gemini_layout.setSpacing(self.scale(20))
        gemini_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.gemini_api_key = QLineEdit()
        self.gemini_api_key.setPlaceholderText(t("settings.ai_provider.gemini.api_key_placeholder", "Your Gemini API key"))
        self.gemini_api_key.setEchoMode(QLineEdit.Password)
        self.gemini_api_key.setMinimumHeight(self.scale(40))
        gemini_layout.addRow(t("settings.ai_provider.gemini.api_key", "API Key:"), self.gemini_api_key)
        
        self.gemini_model = QLineEdit()
        self.gemini_model.setPlaceholderText(t("settings.ai_provider.gemini.model_placeholder", "gemini-2.0-flash"))
        self.gemini_model.setMinimumHeight(self.scale(40))
        gemini_layout.addRow(t("settings.ai_provider.gemini.model", "Model:"), self.gemini_model)
        
        self.gemini_project_id = QLineEdit()
        self.gemini_project_id.setPlaceholderText(t("settings.ai_provider.gemini.project_id_placeholder", "your-project-id"))
        self.gemini_project_id.setMinimumHeight(self.scale(40))
        gemini_layout.addRow(t("settings.ai_provider.gemini.project_id", "Project ID:"), self.gemini_project_id)
        
        self.gemini_group.setLayout(gemini_layout)
        layout.addWidget(self.gemini_group)
        
        # DeepSeek Settings
        self.deepseek_group = QGroupBox(t("settings.ai_provider.deepseek.title", "🧠 DeepSeek Configuration"))
        self.deepseek_group.setMinimumHeight(self.scale(250))
        deepseek_layout = QFormLayout()
        deepseek_layout.setSpacing(self.scale(20))
        deepseek_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.deepseek_api_key = QLineEdit()
        self.deepseek_api_key.setPlaceholderText(t("settings.ai_provider.deepseek.api_key_placeholder", "Your DeepSeek API key"))
        self.deepseek_api_key.setEchoMode(QLineEdit.Password)
        self.deepseek_api_key.setMinimumHeight(self.scale(40))
        deepseek_layout.addRow(t("settings.ai_provider.deepseek.api_key", "API Key:"), self.deepseek_api_key)
        
        self.deepseek_base_url = QLineEdit()
        self.deepseek_base_url.setPlaceholderText(t("settings.ai_provider.deepseek.base_url_placeholder", "https://api.deepseek.com"))
        self.deepseek_base_url.setMinimumHeight(self.scale(40))
        deepseek_layout.addRow(t("settings.ai_provider.deepseek.base_url", "Base URL:"), self.deepseek_base_url)
        
        self.deepseek_model = QLineEdit()
        self.deepseek_model.setPlaceholderText(t("settings.ai_provider.deepseek.model_placeholder", "deepseek-coder"))
        self.deepseek_model.setMinimumHeight(self.scale(40))
        deepseek_layout.addRow(t("settings.ai_provider.deepseek.model", "Model:"), self.deepseek_model)
        
        self.deepseek_group.setLayout(deepseek_layout)
        layout.addWidget(self.deepseek_group)
        
        # Claude Settings
        self.claude_group = QGroupBox(t("settings.ai_provider.claude.title", "🎭 Claude Configuration"))
        self.claude_group.setMinimumHeight(self.scale(250))
        claude_layout = QFormLayout()
        claude_layout.setSpacing(self.scale(20))
        claude_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.claude_api_key = QLineEdit()
        self.claude_api_key.setPlaceholderText(t("settings.ai_provider.claude.api_key_placeholder", "Your Anthropic API key"))
        self.claude_api_key.setEchoMode(QLineEdit.Password)
        self.claude_api_key.setMinimumHeight(self.scale(40))
        claude_layout.addRow(t("settings.ai_provider.claude.api_key", "API Key:"), self.claude_api_key)
        
        self.claude_base_url = QLineEdit()
        self.claude_base_url.setPlaceholderText(t("settings.ai_provider.claude.base_url_placeholder", "https://api.anthropic.com"))
        self.claude_base_url.setMinimumHeight(self.scale(40))
        claude_layout.addRow(t("settings.ai_provider.claude.base_url", "Base URL:"), self.claude_base_url)
        
        self.claude_model = QLineEdit()
        self.claude_model.setPlaceholderText(t("settings.ai_provider.claude.model_placeholder", "claude-3-sonnet-20240229"))
        self.claude_model.setMinimumHeight(self.scale(40))
        claude_layout.addRow(t("settings.ai_provider.claude.model", "Model:"), self.claude_model)
        
        self.claude_group.setLayout(claude_layout)
        layout.addWidget(self.claude_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, t("settings.tabs.ai_provider", "🤖 AI Provider"))
    
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
        self.mode_group = QGroupBox(t("settings.audio.title", "🎤 Audio Configuration"))
        self.mode_group.setMinimumHeight(self.scale(300))
        mode_layout = QFormLayout()
        mode_layout.setSpacing(self.scale(20))
        mode_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.audio_mode = QComboBox()
        self.audio_mode.addItems(["single_stream", "dual_stream"])
        self.audio_mode.setMinimumHeight(self.scale(40))
        mode_layout.addRow(t("settings.audio.mode", "Audio Mode:"), self.audio_mode)
        
        self.buffer_duration = QSpinBox()
        self.buffer_duration.setRange(1, 30)
        self.buffer_duration.setSuffix(t("settings.audio.buffer_suffix", " minutes"))
        self.buffer_duration.setMinimumHeight(self.scale(40))
        mode_layout.addRow(t("settings.audio.buffer_duration", "Buffer Duration:"), self.buffer_duration)
        
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
        mode_layout.addRow(t("settings.audio.processing_interval", "Processing Interval:"), interval_layout)
        
        self.mode_group.setLayout(mode_layout)
        layout.addWidget(self.mode_group)
        
        # System Audio Monitoring
        self.system_audio_group = QGroupBox(t("settings.audio.system_audio.title", "🔊 System Audio Monitoring"))
        self.system_audio_group.setMinimumHeight(self.scale(400))
        system_audio_layout = QVBoxLayout()
        system_audio_layout.setSpacing(self.scale(15))
        
        # Full system audio monitoring toggle
        self.full_system_audio = QCheckBox(t("settings.audio.system_audio.full_monitoring", "Monitor all system audio (overrides specific app selection)"))
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
        self.app_selection_label = QLabel(t("settings.audio.system_audio.select_apps", "Select specific applications to monitor:"))
        self.app_selection_label.setStyleSheet("color: #e6e6e6; font-style: italic; margin-top: 10px;")
        self.app_selection_label.setMinimumHeight(self.scale(28))
        system_audio_layout.addWidget(self.app_selection_label)
        
        # Add status indicator
        self.monitoring_status = QLabel(t("settings.audio.system_audio.monitoring_status", "📊 Currently monitoring: Loading..."))
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
        self.meeting_label = QLabel(t("settings.audio.system_audio.meeting_apps", "📞 Meeting & Communication Apps (Enabled by Default)"))
        self.meeting_label.setStyleSheet("font-weight: 600; color: #0078d4; margin-bottom: 5px;")
        self.meeting_label.setMinimumHeight(self.scale(32))
        apps_layout.addWidget(self.meeting_label, 0, 0, 1, 2)
        
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
        self.other_label = QLabel(t("settings.audio.system_audio.other_apps", "🖥️ Other Applications (Disabled by Default)"))
        self.other_label.setStyleSheet("font-weight: 600; color: #666666; margin-bottom: 5px;")
        self.other_label.setMinimumHeight(self.scale(32))
        apps_layout.addWidget(self.other_label, 0, 2, 1, 2)
        
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
        self.custom_app_input.setPlaceholderText(t("settings.audio.system_audio.custom_app", "Enter custom application name (e.g., MyApp.exe)"))
        self.custom_app_input.setMinimumHeight(self.scale(40))
        self.custom_app_input.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        
        self.add_custom_btn = QPushButton(t("settings.audio.system_audio.add_custom", "➕ Add"))
        self.add_custom_btn.setMinimumHeight(self.scale(40))
        self.add_custom_btn.setMaximumWidth(self.scale(80))
        self.add_custom_btn.clicked.connect(self.add_custom_application)
        
        custom_layout.addWidget(self.custom_app_input)
        custom_layout.addWidget(self.add_custom_btn)
        apps_layout.addLayout(custom_layout, row, 2, 1, 2)
        
        system_audio_layout.addWidget(apps_widget)
        
        # Audio filtering options
        self.filter_label = QLabel(t("settings.audio.system_audio.filtering", "🎛️ Audio Filtering:"))
        self.filter_label.setStyleSheet("font-weight: 600; color: #ffffff; margin-top: 15px;")
        self.filter_label.setMinimumHeight(self.scale(28))
        system_audio_layout.addWidget(self.filter_label)
        
        self.filter_music = QCheckBox(t("settings.audio.system_audio.filter_music", "🎵 Filter out music and non-speech audio (recommended)"))
        self.filter_music.setMinimumHeight(self.scale(32))
        self.filter_music.setChecked(True)
        self.filter_music.setToolTip(t("settings.audio.system_audio.filter_music_tooltip", "Uses AI to detect and ignore music, sound effects, and other non-speech audio"))
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
        threshold_layout.addWidget(QLabel(t("settings.audio.system_audio.speech_sensitivity", "Speech Detection Sensitivity:")))
        threshold_layout.addWidget(self.speech_detection_threshold)
        threshold_layout.addWidget(self.speech_threshold_label)
        system_audio_layout.addLayout(threshold_layout)
        
        self.system_audio_group.setLayout(system_audio_layout)
        layout.addWidget(self.system_audio_group)
        
        # Transcription Provider
        self.transcription_group = QGroupBox(t("settings.audio.transcription.title", "📝 Transcription Settings"))
        self.transcription_group.setMinimumHeight(self.scale(500))  # Increased for more content
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
        provider_form.addRow(t("settings.audio.transcription.provider", "Provider:"), self.transcription_provider)
        
        transcription_layout.addLayout(provider_form)
        
        # Local Whisper Settings
        self.whisper_group = QGroupBox(t("settings.audio.transcription.whisper.title", "🤖 Local Whisper Configuration"))
        self.whisper_group.setMinimumHeight(self.scale(120))
        whisper_layout = QFormLayout()
        whisper_layout.setSpacing(self.scale(15))
        whisper_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.whisper_model = QComboBox()
        self.whisper_model.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_model.setMinimumHeight(self.scale(40))
        whisper_layout.addRow(t("settings.audio.transcription.whisper.model_size", "Model Size:"), self.whisper_model)
        
        self.whisper_group.setLayout(whisper_layout)
        transcription_layout.addWidget(self.whisper_group)
        
        # Google Speech Settings
        self.google_speech_group = QGroupBox(t("settings.audio.transcription.google_speech.title", "🔴 Google Speech-to-Text Configuration"))
        self.google_speech_group.setMinimumHeight(self.scale(200))
        google_layout = QVBoxLayout()
        google_layout.setSpacing(self.scale(15))
        
        # JSON config file option
        json_file_layout = QHBoxLayout()
        self.google_json_file = QLineEdit()
        self.google_json_file.setPlaceholderText(t("settings.audio.transcription.google_speech.json_file", "Path to Google Cloud service account JSON file"))
        self.google_json_file.setMinimumHeight(self.scale(40))
        self.google_json_file.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        
        self.browse_json_btn = QPushButton(t("settings.audio.transcription.google_speech.browse", "📁 Browse"))
        self.browse_json_btn.setMinimumHeight(self.scale(40))
        self.browse_json_btn.setMaximumWidth(self.scale(100))
        self.browse_json_btn.clicked.connect(self.browse_google_json_file)
        
        json_file_layout.addWidget(QLabel(t("settings.audio.transcription.google_speech.json_file", "Service Account JSON File:")))
        json_file_layout.addWidget(self.google_json_file)
        json_file_layout.addWidget(self.browse_json_btn)
        google_layout.addLayout(json_file_layout)
        
        # Alternative: Direct JSON input
        google_layout.addWidget(QLabel(t("settings.audio.transcription.google_speech.json_content", "Or paste JSON content:")))
        self.google_json_content = QTextEdit()
        self.google_json_content.setMinimumHeight(self.scale(100))
        self.google_json_content.setPlaceholderText(t("settings.audio.transcription.google_speech.json_placeholder", '{\n  "type": "service_account",\n  "project_id": "your-project",\n  "private_key_id": "...",\n  ...\n}'))
        self.google_json_content.setStyleSheet("QTextEdit { color: #ffffff; font-family: 'Consolas', monospace; }")
        google_layout.addWidget(self.google_json_content)
        
        self.google_speech_group.setLayout(google_layout)
        transcription_layout.addWidget(self.google_speech_group)
        
        # Azure Speech Settings
        self.azure_speech_group = QGroupBox(t("settings.audio.transcription.azure_speech.title", "🔷 Azure Speech Services Configuration"))
        self.azure_speech_group.setMinimumHeight(self.scale(250))
        azure_speech_layout = QFormLayout()
        azure_speech_layout.setSpacing(self.scale(20))
        azure_speech_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.azure_speech_key = QLineEdit()
        self.azure_speech_key.setPlaceholderText(t("settings.audio.transcription.azure_speech.api_key_placeholder", "Your Azure Speech API key"))
        self.azure_speech_key.setEchoMode(QLineEdit.Password)
        self.azure_speech_key.setMinimumHeight(self.scale(40))
        self.azure_speech_key.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        azure_speech_layout.addRow(t("settings.audio.transcription.azure_speech.api_key", "API Key:"), self.azure_speech_key)
        
        self.azure_speech_region = QLineEdit()
        self.azure_speech_region.setPlaceholderText(t("settings.audio.transcription.azure_speech.region_placeholder", "eastus"))
        self.azure_speech_region.setMinimumHeight(self.scale(40))
        self.azure_speech_region.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        azure_speech_layout.addRow(t("settings.audio.transcription.azure_speech.region", "Region:"), self.azure_speech_region)
        
        self.azure_speech_endpoint = QLineEdit()
        self.azure_speech_endpoint.setPlaceholderText(t("settings.audio.transcription.azure_speech.endpoint_placeholder", "https://your-region.api.cognitive.microsoft.com/ (optional)"))
        self.azure_speech_endpoint.setMinimumHeight(self.scale(40))
        self.azure_speech_endpoint.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        azure_speech_layout.addRow(t("settings.audio.transcription.azure_speech.endpoint", "Custom Endpoint:"), self.azure_speech_endpoint)
        
        self.azure_speech_language = QComboBox()
        self.azure_speech_language.addItems(["en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", "zh-CN", "ja-JP", "ko-KR"])
        self.azure_speech_language.setMinimumHeight(self.scale(40))
        azure_speech_layout.addRow(t("settings.audio.transcription.azure_speech.language", "Language:"), self.azure_speech_language)
        
        self.azure_speech_group.setLayout(azure_speech_layout)
        transcription_layout.addWidget(self.azure_speech_group)
        
        # OpenAI Whisper API Settings
        self.openai_whisper_group = QGroupBox(t("settings.audio.transcription.openai_whisper.title", "🟢 OpenAI Whisper API Configuration"))
        self.openai_whisper_group.setMinimumHeight(self.scale(200))
        openai_whisper_layout = QFormLayout()
        openai_whisper_layout.setSpacing(self.scale(20))
        openai_whisper_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.openai_whisper_api_key = QLineEdit()
        self.openai_whisper_api_key.setPlaceholderText(t("settings.audio.transcription.openai_whisper.api_key_placeholder", "Your OpenAI API key"))
        self.openai_whisper_api_key.setEchoMode(QLineEdit.Password)
        self.openai_whisper_api_key.setMinimumHeight(self.scale(40))
        self.openai_whisper_api_key.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        openai_whisper_layout.addRow(t("settings.audio.transcription.openai_whisper.api_key", "API Key:"), self.openai_whisper_api_key)
        
        self.openai_whisper_model = QComboBox()
        self.openai_whisper_model.addItems(["whisper-1"])
        self.openai_whisper_model.setMinimumHeight(self.scale(40))
        openai_whisper_layout.addRow(t("settings.audio.transcription.openai_whisper.model", "Model:"), self.openai_whisper_model)
        
        self.openai_whisper_language = QComboBox()
        self.openai_whisper_language.addItems(["auto-detect", "en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"])
        self.openai_whisper_language.setMinimumHeight(self.scale(40))
        openai_whisper_layout.addRow(t("settings.audio.transcription.openai_whisper.language", "Language:"), self.openai_whisper_language)
        
        self.openai_whisper_group.setLayout(openai_whisper_layout)
        transcription_layout.addWidget(self.openai_whisper_group)
        
        self.transcription_group.setLayout(transcription_layout)
        layout.addWidget(self.transcription_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, t("settings.tabs.audio", "🎤 Audio"))
    
    def setup_ui_tab(self):
        """Setup UI settings tab"""
        tab = QScrollArea()
        content = QWidget()
        
        # Set proper size policy for content to expand
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.setMinimumSize(self.scale(1200), self.scale(600))
        
        layout = QVBoxLayout(content)
        layout.setSpacing(self.scale(25))
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(30))
        
        # Appearance
        self.appearance_group = QGroupBox(t("settings.appearance.title", "🎨 Appearance"))
        self.appearance_group.setMinimumHeight(self.scale(500))  # Increased height for theme option
        appearance_layout = QFormLayout()
        appearance_layout.setSpacing(self.scale(20))
        appearance_layout.setLabelAlignment(Qt.AlignLeft)
        
        # Language Selection
        self.language_selector = QComboBox()
        if TRANSLATIONS_AVAILABLE:
            translation_manager = get_translation_manager()
            languages = translation_manager.get_available_languages()
            for lang_code, lang_name in languages:
                self.language_selector.addItem(f"{lang_name} ({lang_code})", lang_code)
        else:
            self.language_selector.addItem("English (en)", "en")
        self.language_selector.setMinimumHeight(self.scale(40))
        self.language_selector.setToolTip(t("settings.language.tooltip", "Select the interface language"))
        self.language_selector.currentIndexChanged.connect(self.on_language_changed)
        self.language_label = QLabel(t("settings.language.label", "Language:"))
        appearance_layout.addRow(self.language_label, self.language_selector)
        
        # Theme Selection
        self.theme_selector = QComboBox()
        self.theme_selector.addItems([t("settings.theme.dark", "Dark Mode"), t("settings.theme.light", "Light Mode")])
        self.theme_selector.setMinimumHeight(self.scale(40))
        self.theme_selector.setToolTip(t("settings.theme.tooltip", "Choose between light and dark theme"))
        self.theme_selector.currentTextChanged.connect(self.on_theme_changed)
        self.theme_label = QLabel(t("settings.theme.label", "Theme:"))
        appearance_layout.addRow(self.theme_label, self.theme_selector)
        
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
        self.size_multiplier_label = QLabel(t("settings.size_multiplier.label", "Size Multiplier:"))
        appearance_layout.addRow(self.size_multiplier_label, size_layout)
        
        self.show_transcript = QCheckBox(t("settings.show_transcript.label", "Show live transcript in expanded view"))
        self.show_transcript.setMinimumHeight(self.scale(32))
        appearance_layout.addRow("", self.show_transcript)
        
        self.hide_from_sharing = QCheckBox(t("settings.hide_from_sharing.label", "Hide from screen sharing"))
        self.hide_from_sharing.setMinimumHeight(self.scale(32))
        appearance_layout.addRow("", self.hide_from_sharing)
        
        self.auto_hide_seconds = QSpinBox()
        self.auto_hide_seconds.setRange(0, 60)
        self.auto_hide_seconds.setSuffix(t("settings.auto_hide.suffix", " seconds (0 = disabled)"))
        self.auto_hide_seconds.setMinimumHeight(self.scale(40))
        self.auto_hide_label = QLabel(t("settings.auto_hide.label", "Auto-hide Timer:"))
        appearance_layout.addRow(self.auto_hide_label, self.auto_hide_seconds)
        
        # Screen sharing detection
        self.enable_screen_sharing_detection = QCheckBox(t("settings.screen_sharing.label", "Enable screen sharing detection"))
        self.enable_screen_sharing_detection.setMinimumHeight(self.scale(32))
        self.enable_screen_sharing_detection.setToolTip(t("settings.screen_sharing.tooltip", "Automatically hide overlay when screen sharing apps are detected"))
        appearance_layout.addRow("", self.enable_screen_sharing_detection)
        
        # Hide overlay for screenshots/debugging
        self.hide_overlay_for_screenshots = QCheckBox(t("settings.hide_screenshots.label", "Hide overlay for screenshots/debugging"))
        self.hide_overlay_for_screenshots.setMinimumHeight(self.scale(32))
        self.hide_overlay_for_screenshots.setToolTip(t("settings.hide_screenshots.tooltip", "Temporarily hide the entire overlay for taking clean screenshots or debugging UI issues"))
        self.hide_overlay_for_screenshots.toggled.connect(self.on_hide_overlay_toggled)
        appearance_layout.addRow("", self.hide_overlay_for_screenshots)
        
        # Enhanced UI Features Group
        self.enhanced_group = QGroupBox(t("settings.enhanced_features.title", "🚀 Enhanced Features"))
        self.enhanced_group.setMinimumHeight(self.scale(350))
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
        self.background_opacity_label = QLabel(t("settings.background_opacity.label", "Background Opacity:"))
        enhanced_layout.addRow(self.background_opacity_label, opacity_layout)
        
        # Blur effects
        self.enable_blur_effects = QCheckBox(t("settings.blur_effects.label", "Enable blur effects"))
        self.enable_blur_effects.setMinimumHeight(self.scale(32))
        self.enable_blur_effects.setToolTip(t("settings.blur_effects.tooltip", "Apply blur effects to background for professional look"))
        enhanced_layout.addRow("", self.enable_blur_effects)
        
        # Smooth animations
        self.enable_smooth_animations = QCheckBox(t("settings.smooth_animations.label", "Enable smooth animations"))
        self.enable_smooth_animations.setMinimumHeight(self.scale(32))
        self.enable_smooth_animations.setToolTip(t("settings.smooth_animations.tooltip", "Use smooth animations for transitions and resizing"))
        enhanced_layout.addRow("", self.enable_smooth_animations)
        
        # Auto-width adjustment
        self.enable_auto_width = QCheckBox(t("settings.auto_width.label", "Enable auto-width adjustment"))
        self.enable_auto_width.setMinimumHeight(self.scale(32))
        self.enable_auto_width.setToolTip(t("settings.auto_width.tooltip", "Automatically adjust overlay width based on content"))
        enhanced_layout.addRow("", self.enable_auto_width)
        
        # Dynamic transparency
        self.enable_dynamic_transparency = QCheckBox(t("settings.dynamic_transparency.label", "Enable dynamic transparency"))
        self.enable_dynamic_transparency.setMinimumHeight(self.scale(32))
        self.enable_dynamic_transparency.setToolTip(t("settings.dynamic_transparency.tooltip", "Adjust transparency based on activity and context"))
        enhanced_layout.addRow("", self.enable_dynamic_transparency)
        
        self.enhanced_group.setLayout(enhanced_layout)
        
        self.appearance_group.setLayout(appearance_layout)
        layout.addWidget(self.appearance_group)
        layout.addWidget(self.enhanced_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, t("settings.tabs.interface", "🖥️ Interface"))
    
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
        self.behavior_group = QGroupBox(t("settings.assistant.title", "🧠 Assistant Behavior"))
        self.behavior_group.setMinimumHeight(self.scale(400))  # Set minimum height for group
        behavior_layout = QFormLayout()
        behavior_layout.setSpacing(self.scale(20))  # Increased spacing
        behavior_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.activation_mode = QComboBox()
        self.activation_mode.addItems(["manual", "auto"])
        self.activation_mode.setMinimumHeight(self.scale(40))  # Larger height
        behavior_layout.addRow(t("settings.assistant.activation_mode", "Activation Mode:"), self.activation_mode)
        
        self.verbosity = QComboBox()
        self.verbosity.addItems(["concise", "standard", "detailed"])
        self.verbosity.setMinimumHeight(self.scale(40))
        behavior_layout.addRow(t("settings.assistant.verbosity", "Response Verbosity:"), self.verbosity)
        
        self.response_style = QComboBox()
        self.response_style.addItems(["professional", "casual", "technical"])
        self.response_style.setMinimumHeight(self.scale(40))
        behavior_layout.addRow(t("settings.assistant.response_style", "Response Style:"), self.response_style)
        
        self.input_prioritization = QComboBox()
        self.input_prioritization.addItems(["mic", "system_audio", "balanced"])
        self.input_prioritization.setMinimumHeight(self.scale(40))
        behavior_layout.addRow(t("settings.assistant.input_priority", "Input Priority:"), self.input_prioritization)
        
        self.behavior_group.setLayout(behavior_layout)
        layout.addWidget(self.behavior_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, t("settings.tabs.assistant", "🧠 Assistant"))
    
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
        self.prompt_group = QGroupBox(t("settings.prompts.title", "📝 AI Prompt Configuration"))
        self.prompt_group.setMinimumHeight(self.scale(500))
        prompt_layout = QVBoxLayout()
        prompt_layout.setSpacing(self.scale(15))
        
        self.prompt_info = QLabel(t("settings.prompts.info", "Customize the MeetMinder assistant's behavior and response style:"))
        self.prompt_info.setStyleSheet("color: #e6e6e6; font-style: italic;")
        self.prompt_info.setMinimumHeight(self.scale(28))
        prompt_layout.addWidget(self.prompt_info)
        
        self.system_prompt = QTextEdit()
        self.system_prompt.setMinimumHeight(self.scale(350))
        self.system_prompt.setPlaceholderText(t("settings.prompts.placeholder", "Enter system prompt that defines the MeetMinder assistant's behavior, tone, and expertise..."))
        prompt_layout.addWidget(self.system_prompt)
        
        # Load/Save buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(self.scale(15))
        
        self.load_prompt_btn = QPushButton(t("settings.prompts.load_file", "📁 Load from File"))
        self.load_prompt_btn.setMinimumHeight(self.scale(40))
        self.load_prompt_btn.clicked.connect(self.load_prompt_file)
        
        self.save_prompt_btn = QPushButton(t("settings.prompts.save_file", "💾 Save to File"))
        self.save_prompt_btn.setMinimumHeight(self.scale(40))
        self.save_prompt_btn.clicked.connect(self.save_prompt_file)
        
        self.reset_prompt_btn = QPushButton(t("settings.prompts.reset_default", "🔄 Reset to Default"))
        self.reset_prompt_btn.setMinimumHeight(self.scale(40))
        self.reset_prompt_btn.clicked.connect(self.reset_prompt_to_default)
        
        button_layout.addWidget(self.load_prompt_btn)
        button_layout.addWidget(self.save_prompt_btn)
        button_layout.addWidget(self.reset_prompt_btn)
        button_layout.addStretch()
        prompt_layout.addLayout(button_layout)
        
        self.prompt_group.setLayout(prompt_layout)
        layout.addWidget(self.prompt_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, t("settings.tabs.prompts", "📝 Prompts"))
    
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
        self.knowledge_group = QGroupBox(t("settings.knowledge.title", "🧠 Knowledge Graph"))
        self.knowledge_group.setMinimumHeight(self.scale(500))
        knowledge_layout = QVBoxLayout()
        knowledge_layout.setSpacing(self.scale(15))
        
        # Enable/disable
        self.enable_topic_graph = QCheckBox(t("settings.knowledge.enable", "Enable topic analysis and suggestions"))
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
        settings_layout.addRow(t("settings.knowledge.matching_threshold", "Matching Threshold:"), threshold_layout)
        
        self.max_matches = QSpinBox()
        self.max_matches.setRange(1, 10)
        self.max_matches.setValue(3)
        self.max_matches.setMinimumHeight(self.scale(40))
        settings_layout.addRow(t("settings.knowledge.max_matches", "Max Suggestions:"), self.max_matches)
        
        knowledge_layout.addLayout(settings_layout)
        
        # Topic definitions
        self.topic_info = QLabel(t("settings.knowledge.topic_definitions", "Topic Definitions:"))
        self.topic_info.setStyleSheet("color: #e6e6e6; margin-top: 15px;")
        self.topic_info.setMinimumHeight(self.scale(28))
        knowledge_layout.addWidget(self.topic_info)
        
        self.topic_definitions = QTextEdit()
        self.topic_definitions.setMinimumHeight(self.scale(250))
        self.topic_definitions.setPlaceholderText(t("settings.knowledge.topic_definitions_placeholder", "Example topic definitions:\n\nMeeting Management: Strategies for organizing and running effective meetings\nProject Planning: Techniques for project planning and execution\nTechnical Discussions: Handling technical topics and problem-solving\nClient Communication: Best practices for client interactions\n\nEnter one topic per line with format: Topic Name: Description"))
        knowledge_layout.addWidget(self.topic_definitions)
        
        # Buttons
        topic_button_layout = QHBoxLayout()
        topic_button_layout.setSpacing(self.scale(15))
        
        self.import_topics_btn = QPushButton(t("settings.knowledge.import_topics", "📁 Import Topics"))
        self.import_topics_btn.setMinimumHeight(self.scale(40))
        self.import_topics_btn.clicked.connect(self.import_topics)
        
        self.export_topics_btn = QPushButton(t("settings.knowledge.export_topics", "💾 Export Topics"))
        self.export_topics_btn.setMinimumHeight(self.scale(40))
        self.export_topics_btn.clicked.connect(self.export_topics)
        
        self.clear_topics_btn = QPushButton(t("settings.knowledge.clear_all", "🗑️ Clear All"))
        self.clear_topics_btn.setMinimumHeight(self.scale(40))
        self.clear_topics_btn.clicked.connect(self.clear_topics)
        
        topic_button_layout.addWidget(self.import_topics_btn)
        topic_button_layout.addWidget(self.export_topics_btn)
        topic_button_layout.addWidget(self.clear_topics_btn)
        topic_button_layout.addStretch()
        knowledge_layout.addLayout(topic_button_layout)
        
        self.knowledge_group.setLayout(knowledge_layout)
        layout.addWidget(self.knowledge_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, t("settings.tabs.knowledge", "🧠 Knowledge"))

    def setup_documents_tab(self):
        """Setup document management tab"""
        tab = QScrollArea()
        content = QWidget()

        # Set proper size policy for content to expand
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.setMinimumSize(self.scale(1200), self.scale(600))

        layout = QVBoxLayout(content)
        layout.setSpacing(self.scale(25))
        layout.setContentsMargins(self.scale(30), self.scale(30), self.scale(30), self.scale(30))

        # Document Store Settings
        self.doc_settings_group = QGroupBox(t("settings.documents.title", "📚 Document Store Configuration"))
        self.doc_settings_group.setMinimumHeight(self.scale(200))
        doc_settings_layout = QVBoxLayout()
        doc_settings_layout.setSpacing(self.scale(15))

        self.documents_enabled = QCheckBox(t("settings.documents.enabled", "Enable document storage and retrieval"))
        self.documents_enabled.setMinimumHeight(self.scale(32))
        self.documents_enabled.setToolTip(t("settings.documents.enabled", "Enable document storage and retrieval"))
        doc_settings_layout.addWidget(self.documents_enabled)

        # Chunking settings
        chunk_layout = QHBoxLayout()
        chunk_layout.setSpacing(self.scale(15))

        chunk_layout.addWidget(QLabel(t("settings.documents.chunk_size", "Chunk Size:")))
        self.chunk_size = QSpinBox()
        self.chunk_size.setRange(500, 2000)
        self.chunk_size.setValue(1000)
        self.chunk_size.setMinimumHeight(self.scale(35))
        chunk_layout.addWidget(self.chunk_size)

        chunk_layout.addWidget(QLabel(t("settings.documents.chunk_overlap", "Chunk Overlap:")))
        self.chunk_overlap = QSpinBox()
        self.chunk_overlap.setRange(0, 500)
        self.chunk_overlap.setValue(200)
        self.chunk_overlap.setMinimumHeight(self.scale(35))
        chunk_layout.addWidget(self.chunk_overlap)

        chunk_layout.addStretch()
        doc_settings_layout.addLayout(chunk_layout)

        # Max context chunks
        max_chunks_layout = QHBoxLayout()
        max_chunks_layout.addWidget(QLabel(t("settings.documents.max_context", "Max Context Chunks:")))
        self.max_context_chunks = QSpinBox()
        self.max_context_chunks.setRange(1, 10)
        self.max_context_chunks.setValue(5)
        self.max_context_chunks.setMinimumHeight(self.scale(35))
        max_chunks_layout.addWidget(self.max_context_chunks)
        max_chunks_layout.addStretch()
        doc_settings_layout.addLayout(max_chunks_layout)

        self.doc_settings_group.setLayout(doc_settings_layout)
        layout.addWidget(self.doc_settings_group)

        # Embedding Configuration
        self.embedding_group = QGroupBox(t("settings.documents.embedding_provider_title", "🧮 Embedding Provider"))
        self.embedding_group.setMinimumHeight(self.scale(150))
        embedding_layout = QVBoxLayout()
        embedding_layout.setSpacing(self.scale(15))

        # Provider selection
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel(t("settings.documents.embedding_provider", "Embedding Provider:")))
        self.embedding_provider = QComboBox()
        self.embedding_provider.addItems(["local", "openai"])
        self.embedding_provider.setMinimumHeight(self.scale(35))
        provider_layout.addWidget(self.embedding_provider)
        provider_layout.addStretch()
        embedding_layout.addLayout(provider_layout)

        # Model selection (for local)
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel(t("settings.documents.embedding_model", "Embedding Model:")))
        self.embedding_model = QComboBox()
        self.embedding_model.addItems([
            "all-MiniLM-L6-v2",
            "all-mpnet-base-v2",
            "e5-small-v2"
        ])
        self.embedding_model.setMinimumHeight(self.scale(35))
        model_layout.addWidget(self.embedding_model)
        model_layout.addStretch()
        embedding_layout.addLayout(model_layout)

        self.embedding_group.setLayout(embedding_layout)
        layout.addWidget(self.embedding_group)

        # Vector Backend Configuration
        self.vector_group = QGroupBox(t("settings.documents.vector_storage_title", "💾 Vector Storage"))
        self.vector_group.setMinimumHeight(self.scale(100))
        vector_layout = QVBoxLayout()
        vector_layout.setSpacing(self.scale(15))

        backend_layout = QHBoxLayout()
        backend_layout.addWidget(QLabel(t("settings.documents.vector_backend", "Vector Backend:")))
        self.vector_backend = QComboBox()
        self.vector_backend.addItems(["faiss", "pinecone"])
        self.vector_backend.setMinimumHeight(self.scale(35))
        backend_layout.addWidget(self.vector_backend)
        backend_layout.addStretch()
        vector_layout.addLayout(backend_layout)

        self.vector_group.setLayout(vector_layout)
        layout.addWidget(self.vector_group)

        # Document Management
        self.management_group = QGroupBox(t("settings.documents.management_title", "📁 Document Management"))
        self.management_group.setMinimumHeight(self.scale(200))
        management_layout = QVBoxLayout()
        management_layout.setSpacing(self.scale(15))

        # Upload button
        upload_layout = QHBoxLayout()
        self.upload_button = QPushButton(t("settings.documents.upload", "📤 Upload Document"))
        self.upload_button.setMinimumHeight(self.scale(40))
        self.upload_button.clicked.connect(self.upload_document)
        upload_layout.addWidget(self.upload_button)

        self.refresh_button = QPushButton(t("settings.documents.refresh_list", "🔄 Refresh List"))
        self.refresh_button.setMinimumHeight(self.scale(40))
        self.refresh_button.clicked.connect(self.refresh_documents)
        upload_layout.addWidget(self.refresh_button)

        upload_layout.addStretch()
        management_layout.addLayout(upload_layout)

        # Document list placeholder
        self.documents_list = QTextEdit()
        self.documents_list.setMinimumHeight(self.scale(150))
        self.documents_list.setPlaceholderText(t("settings.documents.uploaded_documents", "Uploaded documents will appear here..."))
        self.documents_list.setReadOnly(True)
        management_layout.addWidget(self.documents_list)

        self.management_group.setLayout(management_layout)
        layout.addWidget(self.management_group)

        layout.addStretch()

        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.tab_widget.addTab(tab, t("settings.tabs.documents", "📚 Documents"))

    def upload_document(self):
        """Handle document upload"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Documents (*.pdf *.docx *.doc *.txt *.md *.pptx *.ppt *.xlsx *.xls *.py *.js *.java *.cpp *.c *.html *.css *.json *.xml)")

        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            if hasattr(self.parent(), 'ai_helper') and self.parent().ai_helper:
                try:
                    import asyncio
                    doc_id = asyncio.run(self.parent().ai_helper.add_document_async(file_path))
                    QMessageBox.information(self, 
                                          t("messages.document_uploaded", "Document Uploaded"),
                                          t("messages.document_uploaded_msg", "Document uploaded successfully!\nID: {doc_id}\n\nProcessing in background...").format(doc_id=doc_id))
                    self.refresh_documents()
                except Exception as e:
                    QMessageBox.warning(self, 
                                      t("messages.upload_failed", "Upload Failed"), 
                                      t("messages.upload_failed_msg", "Failed to upload document: {error}").format(error=str(e)))
            else:
                QMessageBox.warning(self, 
                                  t("messages.ai_helper_not_available", "AI Helper Not Available"),
                                  t("messages.ai_helper_not_available_msg", "AI helper is not available. Please check your AI provider configuration."))

    def refresh_documents(self):
        """Refresh the document list"""
        if hasattr(self.parent(), 'ai_helper') and self.parent().ai_helper:
            try:
                documents = self.parent().ai_helper.list_documents()
                stats = self.parent().ai_helper.get_document_store_stats()

                text = t("settings.documents.statistics_title", "📊 Document Store Statistics:") + "\n"
                if stats:
                    text += t("settings.documents.total_documents", "Total Documents:") + f" {stats.get('total_documents', 0)}\n"
                    text += t("settings.documents.completed", "Completed:") + f" {stats.get('completed_documents', 0)}\n"
                    text += t("settings.documents.failed", "Failed:") + f" {stats.get('failed_documents', 0)}\n"
                    text += t("settings.documents.total_chunks", "Total Chunks:") + f" {stats.get('total_chunks', 0)}\n"
                    text += t("settings.documents.embedding", "Embedding:") + f" {stats.get('embedding_provider', 'none')}\n"
                    text += t("settings.documents.vector_backend_label", "Vector Backend:") + f" {stats.get('vector_backend', 'none')}\n\n"

                text += t("settings.documents.documents_list_title", "📁 Documents:") + "\n"
                if documents:
                    for doc in documents:
                        status_emoji = {
                            "pending": "⏳",
                            "processing": "🔄",
                            "completed": "✅",
                            "failed": "❌"
                        }.get(doc.get('status', 'unknown'), "❓")

                        file_name = doc.get('file_name', t("settings.documents.unknown", "Unknown"))
                        text += f"{status_emoji} {file_name} "
                        text += f"(ID: {doc.get('id', 'N/A')[:8]}...)\n"
                        status_label = t("settings.documents.status_label", "Status:")
                        status_value = doc.get('status', t("settings.documents.unknown", "unknown"))
                        text += f"   {status_label} {status_value}\n"
                        if doc.get('error_message'):
                            error_label = t("settings.documents.error_label", "Error:")
                            text += f"   {error_label} {doc.get('error_message')}\n"
                        text += "\n"
                else:
                    text += t("settings.documents.no_documents_uploaded", "No documents uploaded yet.") + "\n"

                self.documents_list.setPlainText(text)
            except Exception as e:
                error_msg = t("settings.documents.error_loading", "Error loading documents: {error}").format(error=str(e))
                self.documents_list.setPlainText(error_msg)
        else:
            self.documents_list.setPlainText(t("messages.ai_helper_not_available_msg", "AI helper is not available. Please check your AI provider configuration."))

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
        self.hotkeys_group = QGroupBox(t("settings.hotkeys.title", "⌨️ Global Hotkeys"))
        self.hotkeys_group.setMinimumHeight(self.scale(350))
        hotkeys_layout = QFormLayout()
        hotkeys_layout.setSpacing(self.scale(20))
        hotkeys_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.trigger_assistance = QLineEdit()
        self.trigger_assistance.setMinimumHeight(self.scale(40))
        hotkeys_layout.addRow(t("settings.hotkeys.trigger_ai", "Trigger AI:"), self.trigger_assistance)
        
        self.toggle_overlay = QLineEdit()
        self.toggle_overlay.setMinimumHeight(self.scale(40))
        hotkeys_layout.addRow(t("settings.hotkeys.toggle_overlay", "Toggle Overlay:"), self.toggle_overlay)
        
        self.take_screenshot = QLineEdit()
        self.take_screenshot.setMinimumHeight(self.scale(40))
        hotkeys_layout.addRow(t("settings.hotkeys.screenshot", "Screenshot:"), self.take_screenshot)
        
        self.emergency_reset = QLineEdit()
        self.emergency_reset.setMinimumHeight(self.scale(40))
        hotkeys_layout.addRow(t("settings.hotkeys.emergency_reset", "Emergency Reset:"), self.emergency_reset)
        
        self.toggle_hide_for_screenshots = QLineEdit()
        self.toggle_hide_for_screenshots.setMinimumHeight(self.scale(40))
        self.toggle_hide_for_screenshots.setPlaceholderText(t("settings.hotkeys.toggle_hide_placeholder", "e.g., Ctrl+H"))
        self.toggle_hide_for_screenshots.setToolTip(t("settings.hotkeys.toggle_hide_placeholder", "e.g., Ctrl+H"))
        hotkeys_layout.addRow(t("settings.hotkeys.toggle_hide", "Toggle Hide Overlay:"), self.toggle_hide_for_screenshots)
        
        self.hotkeys_group.setLayout(hotkeys_layout)
        layout.addWidget(self.hotkeys_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, t("settings.tabs.hotkeys", "⌨️ Hotkeys"))
    
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
        self.debug_group = QGroupBox(t("settings.debug.title", "🐛 Debug & Logging"))
        self.debug_group.setMinimumHeight(self.scale(400))
        debug_layout = QVBoxLayout()
        debug_layout.setSpacing(self.scale(15))
        
        self.debug_enabled = QCheckBox(t("settings.debug.enabled", "Enable debug mode"))
        self.debug_enabled.setMinimumHeight(self.scale(32))
        debug_layout.addWidget(self.debug_enabled)
        
        self.verbose_logging = QCheckBox(t("settings.debug.verbose_logging", "Verbose logging"))
        self.verbose_logging.setMinimumHeight(self.scale(32))
        debug_layout.addWidget(self.verbose_logging)
        
        self.save_transcriptions = QCheckBox(t("settings.debug.save_transcriptions", "Save transcriptions to files"))
        self.save_transcriptions.setMinimumHeight(self.scale(32))
        debug_layout.addWidget(self.save_transcriptions)
        
        self.save_audio_chunks = QCheckBox(t("settings.debug.save_audio", "Save audio chunks to files"))
        self.save_audio_chunks.setMinimumHeight(self.scale(32))
        debug_layout.addWidget(self.save_audio_chunks)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(self.scale(20))
        form_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.max_debug_files = QSpinBox()
        self.max_debug_files.setRange(10, 1000)
        self.max_debug_files.setValue(100)
        form_layout.addRow(t("settings.debug.max_files", "Max Debug Files:"), self.max_debug_files)
        
        debug_layout.addLayout(form_layout)
        self.debug_group.setLayout(debug_layout)
        layout.addWidget(self.debug_group)
        
        layout.addStretch()
        
        # Set the widget to the scroll area and configure scroll area
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tab_widget.addTab(tab, t("settings.tabs.debug", "🐛 Debug"))
    
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
    
    def on_language_changed(self, index):
        """Handle language change"""
        if TRANSLATIONS_AVAILABLE and index >= 0:
            lang_code = self.language_selector.itemData(index)
            if lang_code:
                print(f"🌐 Language changed to: {lang_code}")
                set_language(lang_code)
                # Refresh settings dialog UI
                self.refresh_translations()
                # Refresh overlay if available
                if self.overlay_ref and hasattr(self.overlay_ref, 'refresh_translations'):
                    self.overlay_ref.refresh_translations()
    
    def refresh_translations(self):
        """Refresh all UI text with current translations"""
        if not TRANSLATIONS_AVAILABLE:
            return
        
        try:
            # Update window title
            self.setWindowTitle(t("settings.title", "MeetMinder Settings"))
            
            # Update tab labels
            if hasattr(self, 'tab_widget'):
                for i in range(self.tab_widget.count()):
                    tab_text = self.tab_widget.tabText(i)
                    # Map emoji tabs to translation keys
                    tab_mapping = {
                        "🤖 AI Provider": t("settings.tabs.ai_provider", "🤖 AI Provider"),
                        "🎤 Audio": t("settings.tabs.audio", "🎤 Audio"),
                        "🖥️ Interface": t("settings.tabs.interface", "🖥️ Interface"),
                        "🧠 Assistant": t("settings.tabs.assistant", "🧠 Assistant"),
                        "📝 Prompts": t("settings.tabs.prompts", "📝 Prompts"),
                        "🧠 Knowledge": t("settings.tabs.knowledge", "🧠 Knowledge"),
                        "📚 Documents": t("settings.tabs.documents", "📚 Documents"),
                        "⌨️ Hotkeys": t("settings.tabs.hotkeys", "⌨️ Hotkeys"),
                        "🐛 Debug": t("settings.tabs.debug", "🐛 Debug")
                    }
                    if tab_text in tab_mapping:
                        self.tab_widget.setTabText(i, tab_mapping[tab_text])
            
            # Update button labels
            if hasattr(self, 'save_button'):
                self.save_button.setText(t("settings.buttons.save", "💾 Save Settings"))
            if hasattr(self, 'cancel_button'):
                self.cancel_button.setText(t("settings.buttons.cancel", "❌ Cancel"))
            if hasattr(self, 'reset_button'):
                self.reset_button.setText(t("settings.buttons.reset", "🔄 Reset to Defaults"))
            
            # Update Interface tab labels
            if hasattr(self, 'language_label'):
                self.language_label.setText(t("settings.language.label", "Language:"))
            if hasattr(self, 'theme_label'):
                self.theme_label.setText(t("settings.theme.label", "Theme:"))
            if hasattr(self, 'size_multiplier_label'):
                self.size_multiplier_label.setText(t("settings.size_multiplier.label", "Size Multiplier:"))
            if hasattr(self, 'auto_hide_label'):
                self.auto_hide_label.setText(t("settings.auto_hide.label", "Auto-hide Timer:"))
            if hasattr(self, 'auto_hide_seconds'):
                self.auto_hide_seconds.setSuffix(t("settings.auto_hide.suffix", " seconds (0 = disabled)"))
            if hasattr(self, 'background_opacity_label'):
                self.background_opacity_label.setText(t("settings.background_opacity.label", "Background Opacity:"))
            
            # Update Interface tab checkboxes and labels
            if hasattr(self, 'show_transcript'):
                self.show_transcript.setText(t("settings.show_transcript.label", "Show live transcript in expanded view"))
            if hasattr(self, 'hide_from_sharing'):
                self.hide_from_sharing.setText(t("settings.hide_from_sharing.label", "Hide from screen sharing"))
            if hasattr(self, 'enable_screen_sharing_detection'):
                self.enable_screen_sharing_detection.setText(t("settings.screen_sharing.label", "Enable screen sharing detection"))
                self.enable_screen_sharing_detection.setToolTip(t("settings.screen_sharing.tooltip", "Automatically hide overlay when screen sharing apps are detected"))
            if hasattr(self, 'hide_overlay_for_screenshots'):
                self.hide_overlay_for_screenshots.setText(t("settings.hide_screenshots.label", "Hide overlay for screenshots/debugging"))
                self.hide_overlay_for_screenshots.setToolTip(t("settings.hide_screenshots.tooltip", "Temporarily hide the entire overlay for taking clean screenshots or debugging UI issues"))
            if hasattr(self, 'enable_blur_effects'):
                self.enable_blur_effects.setText(t("settings.blur_effects.label", "Enable blur effects"))
                self.enable_blur_effects.setToolTip(t("settings.blur_effects.tooltip", "Apply blur effects to background for professional look"))
            if hasattr(self, 'enable_smooth_animations'):
                self.enable_smooth_animations.setText(t("settings.smooth_animations.label", "Enable smooth animations"))
                self.enable_smooth_animations.setToolTip(t("settings.smooth_animations.tooltip", "Use smooth animations for transitions and resizing"))
            if hasattr(self, 'enable_auto_width'):
                self.enable_auto_width.setText(t("settings.auto_width.label", "Enable auto-width adjustment"))
                self.enable_auto_width.setToolTip(t("settings.auto_width.tooltip", "Automatically adjust overlay width based on content"))
            if hasattr(self, 'enable_dynamic_transparency'):
                self.enable_dynamic_transparency.setText(t("settings.dynamic_transparency.label", "Enable dynamic transparency"))
                self.enable_dynamic_transparency.setToolTip(t("settings.dynamic_transparency.tooltip", "Adjust transparency based on activity and context"))
            
            # Update group box titles
            if hasattr(self, 'appearance_group'):
                self.appearance_group.setTitle(t("settings.appearance.title", "🎨 Appearance"))
            if hasattr(self, 'enhanced_group'):
                self.enhanced_group.setTitle(t("settings.enhanced_features.title", "🚀 Enhanced Features"))
            if hasattr(self, 'provider_group'):
                self.provider_group.setTitle(t("settings.ai_provider.title", "🤖 AI Provider"))
            if hasattr(self, 'azure_group'):
                self.azure_group.setTitle(t("settings.ai_provider.azure.title", "🔷 Azure OpenAI Configuration"))
            if hasattr(self, 'openai_group'):
                self.openai_group.setTitle(t("settings.ai_provider.openai.title", "🟢 OpenAI Configuration"))
            if hasattr(self, 'gemini_group'):
                self.gemini_group.setTitle(t("settings.ai_provider.gemini.title", "🔴 Google Gemini Configuration"))
            if hasattr(self, 'deepseek_group'):
                self.deepseek_group.setTitle(t("settings.ai_provider.deepseek.title", "🧠 DeepSeek Configuration"))
            if hasattr(self, 'claude_group'):
                self.claude_group.setTitle(t("settings.ai_provider.claude.title", "🎭 Claude Configuration"))
            if hasattr(self, 'mode_group'):
                self.mode_group.setTitle(t("settings.audio.title", "🎤 Audio Configuration"))
            if hasattr(self, 'system_audio_group'):
                self.system_audio_group.setTitle(t("settings.audio.system_audio.title", "🔊 System Audio Monitoring"))
            if hasattr(self, 'transcription_group'):
                self.transcription_group.setTitle(t("settings.audio.transcription.title", "📝 Transcription Settings"))
            if hasattr(self, 'whisper_group'):
                self.whisper_group.setTitle(t("settings.audio.transcription.whisper.title", "🤖 Local Whisper Configuration"))
            if hasattr(self, 'google_speech_group'):
                self.google_speech_group.setTitle(t("settings.audio.transcription.google_speech.title", "🔴 Google Speech-to-Text Configuration"))
            if hasattr(self, 'azure_speech_group'):
                self.azure_speech_group.setTitle(t("settings.audio.transcription.azure_speech.title", "🔷 Azure Speech Services Configuration"))
            if hasattr(self, 'openai_whisper_group'):
                self.openai_whisper_group.setTitle(t("settings.audio.transcription.openai_whisper.title", "🟢 OpenAI Whisper API Configuration"))
            if hasattr(self, 'behavior_group'):
                self.behavior_group.setTitle(t("settings.assistant.title", "🧠 Assistant Behavior"))
            if hasattr(self, 'prompt_group'):
                self.prompt_group.setTitle(t("settings.prompts.title", "📝 AI Prompt Configuration"))
            if hasattr(self, 'knowledge_group'):
                self.knowledge_group.setTitle(t("settings.knowledge.title", "🧠 Knowledge Graph"))
            if hasattr(self, 'doc_settings_group'):
                self.doc_settings_group.setTitle(t("settings.documents.title", "📚 Document Store Configuration"))
            if hasattr(self, 'debug_group'):
                self.debug_group.setTitle(t("settings.debug.title", "🐛 Debug & Logging"))
            
            # Update auto_hide suffix
            if hasattr(self, 'auto_hide_seconds'):
                self.auto_hide_seconds.setSuffix(t("settings.auto_hide.suffix", " seconds (0 = disabled)"))
            
            # Update theme selector items
            if hasattr(self, 'theme_selector'):
                current_theme = self.theme_selector.currentText()
                self.theme_selector.clear()
                self.theme_selector.addItems([t("settings.theme.dark", "Dark Mode"), t("settings.theme.light", "Light Mode")])
                # Restore selection
                if "Light" in current_theme or t("settings.theme.light", "Light Mode") in current_theme:
                    self.theme_selector.setCurrentText(t("settings.theme.light", "Light Mode"))
                else:
                    self.theme_selector.setCurrentText(t("settings.theme.dark", "Dark Mode"))
            
            # Update prompt tab widgets
            if hasattr(self, 'prompt_info'):
                self.prompt_info.setText(t("settings.prompts.info", "Customize the MeetMinder assistant's behavior and response style:"))
            if hasattr(self, 'system_prompt'):
                self.system_prompt.setPlaceholderText(t("settings.prompts.placeholder", "Enter system prompt that defines the MeetMinder assistant's behavior, tone, and expertise..."))
            if hasattr(self, 'load_prompt_btn'):
                self.load_prompt_btn.setText(t("settings.prompts.load_file", "📁 Load from File"))
            if hasattr(self, 'save_prompt_btn'):
                self.save_prompt_btn.setText(t("settings.prompts.save_file", "💾 Save to File"))
            if hasattr(self, 'reset_prompt_btn'):
                self.reset_prompt_btn.setText(t("settings.prompts.reset_default", "🔄 Reset to Default"))
            
            # Update knowledge tab widgets
            if hasattr(self, 'enable_topic_graph'):
                self.enable_topic_graph.setText(t("settings.knowledge.enable", "Enable topic analysis and suggestions"))
            if hasattr(self, 'topic_info'):
                self.topic_info.setText(t("settings.knowledge.topic_definitions", "Topic Definitions:"))
            if hasattr(self, 'topic_definitions'):
                self.topic_definitions.setPlaceholderText(t("settings.knowledge.topic_definitions_placeholder", "Example topic definitions:\n\nMeeting Management: Strategies for organizing and running effective meetings\nProject Planning: Techniques for project planning and execution\nTechnical Discussions: Handling technical topics and problem-solving\nClient Communication: Best practices for client interactions\n\nEnter one topic per line with format: Topic Name: Description"))
            
            # Update documents tab widgets
            if hasattr(self, 'documents_enabled'):
                self.documents_enabled.setText(t("settings.documents.enabled", "Enable document storage and retrieval"))
            if hasattr(self, 'documents_list'):
                self.documents_list.setPlaceholderText(t("settings.documents.uploaded_documents", "Uploaded documents will appear here..."))
            if hasattr(self, 'upload_button'):
                self.upload_button.setText(t("settings.documents.upload", "📤 Upload Document"))
            if hasattr(self, 'refresh_button'):
                self.refresh_button.setText(t("settings.documents.refresh_list", "🔄 Refresh List"))
            if hasattr(self, 'embedding_group'):
                self.embedding_group.setTitle(t("settings.documents.embedding_provider_title", "🧮 Embedding Provider"))
            if hasattr(self, 'vector_group'):
                self.vector_group.setTitle(t("settings.documents.vector_storage_title", "💾 Vector Storage"))
            if hasattr(self, 'management_group'):
                self.management_group.setTitle(t("settings.documents.management_title", "📁 Document Management"))
            
            # Update knowledge tab buttons
            if hasattr(self, 'import_topics_btn'):
                self.import_topics_btn.setText(t("settings.knowledge.import_topics", "📁 Import Topics"))
            if hasattr(self, 'export_topics_btn'):
                self.export_topics_btn.setText(t("settings.knowledge.export_topics", "💾 Export Topics"))
            if hasattr(self, 'clear_topics_btn'):
                self.clear_topics_btn.setText(t("settings.knowledge.clear_all", "🗑️ Clear All"))
            
            # Update hotkeys group title
            if hasattr(self, 'hotkeys_group'):
                self.hotkeys_group.setTitle(t("settings.hotkeys.title", "⌨️ Global Hotkeys"))
            
            # Update debug tab widgets
            if hasattr(self, 'debug_enabled'):
                self.debug_enabled.setText(t("settings.debug.enabled", "Enable debug mode"))
            if hasattr(self, 'verbose_logging'):
                self.verbose_logging.setText(t("settings.debug.verbose_logging", "Verbose logging"))
            if hasattr(self, 'save_transcriptions'):
                self.save_transcriptions.setText(t("settings.debug.save_transcriptions", "Save transcriptions to files"))
            if hasattr(self, 'save_audio_chunks'):
                self.save_audio_chunks.setText(t("settings.debug.save_audio", "Save audio chunks to files"))
            
            # Update audio tab widgets
            if hasattr(self, 'full_system_audio'):
                self.full_system_audio.setText(t("settings.audio.system_audio.full_monitoring", "Monitor all system audio (overrides specific app selection)"))
            if hasattr(self, 'app_selection_label'):
                self.app_selection_label.setText(t("settings.audio.system_audio.select_apps", "Select specific applications to monitor:"))
            if hasattr(self, 'meeting_label'):
                self.meeting_label.setText(t("settings.audio.system_audio.meeting_apps", "📞 Meeting & Communication Apps (Enabled by Default)"))
            if hasattr(self, 'other_label'):
                self.other_label.setText(t("settings.audio.system_audio.other_apps", "🖥️ Other Applications (Disabled by Default)"))
            if hasattr(self, 'custom_app_input'):
                self.custom_app_input.setPlaceholderText(t("settings.audio.system_audio.custom_app", "Enter custom application name (e.g., MyApp.exe)"))
            if hasattr(self, 'add_custom_btn'):
                self.add_custom_btn.setText(t("settings.audio.system_audio.add_custom", "➕ Add"))
            if hasattr(self, 'filter_label'):
                self.filter_label.setText(t("settings.audio.system_audio.filtering", "🎛️ Audio Filtering:"))
            if hasattr(self, 'filter_music'):
                self.filter_music.setText(t("settings.audio.system_audio.filter_music", "🎵 Filter out music and non-speech audio (recommended)"))
                self.filter_music.setToolTip(t("settings.audio.system_audio.filter_music_tooltip", "Uses AI to detect and ignore music, sound effects, and other non-speech audio"))
            if hasattr(self, 'monitoring_status'):
                # Update monitoring status text (will be updated by update_monitoring_status)
                pass
            
            print("✅ Settings dialog translations refreshed")
        except Exception as e:
            print(f"❌ Error refreshing settings translations: {e}")
            import traceback
            traceback.print_exc()
    
    def _refresh_widget_translations(self, widget):
        """Recursively refresh translations in a widget and its children"""
        # This is a helper to refresh form labels and other text
        # For now, we'll update the most critical ones explicitly
        pass
    
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
            QMessageBox.warning(self, t("messages.invalid_input", "Invalid Input"), t("messages.invalid_input_msg", "Please enter an application name."))
            return
        
        # Create a unique key from the app name
        app_key = f"custom_{app_name.lower().replace(' ', '_').replace('.exe', '')}"
        
        # Check if already exists
        if app_key in self.app_checkboxes:
            QMessageBox.information(self, t("messages.already_added", "Already Added"), t("messages.already_added_msg", "'{name}' is already in the list.").format(name=app_name))
            return
        
        # Add the checkbox (find a good position for it)
        checkbox = QCheckBox(f"⚙️ {app_name}")
        checkbox.setMinimumHeight(self.scale(32))
        checkbox.setChecked(True)
        self.app_checkboxes[app_key] = checkbox
        
        # Add to the layout - find the custom application section
        # For now, we'll show a success message and suggest restart
        QMessageBox.information(
            self, t("messages.application_added", "Application Added"), 
            t("messages.application_added_msg", "'{name}' has been added to the monitoring list.\n\nNote: The application will be monitored on the next audio capture restart.").format(name=app_name)
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
            self, t("messages.topics_imported", "Import Topics"), "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.topic_definitions.setPlainText(content)
            except Exception as e:
                QMessageBox.warning(self, t("messages.error_loading_file", "Error"), t("messages.error_loading_file_msg", "Failed to load file: {error}").format(error=str(e)))
    
    def export_topics(self):
        """Export topics to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, t("messages.topics_exported", "Export Topics"), "topics.txt", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.topic_definitions.toPlainText())
                QMessageBox.information(self, t("messages.success", "Success"), t("messages.topics_exported", "Topics exported successfully!"))
            except Exception as e:
                QMessageBox.warning(self, t("messages.error_loading_file", "Error"), t("messages.error_exporting", "Failed to export topics: {error}").format(error=str(e)))
    
    def clear_topics(self):
        """Clear all topics"""
        reply = QMessageBox.question(
            self, t("messages.clear_topics", "Clear Topics"), 
            t("messages.clear_topics_msg", "Are you sure you want to clear all topic definitions?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.topic_definitions.clear()
    
    def setup_buttons(self, layout):
        """Setup dialog buttons"""
        button_layout = QHBoxLayout()
        
        # Save button
        self.save_button = QPushButton(t("settings.buttons.save", "💾 Save Settings"))
        self.save_button.setProperty("class", "primary")
        self.save_button.clicked.connect(self.save_settings)

        # Cancel button
        self.cancel_button = QPushButton(t("settings.buttons.cancel", "❌ Cancel"))
        self.cancel_button.clicked.connect(self.reject)

        # Reset button
        self.reset_button = QPushButton(t("settings.buttons.reset", "🔄 Reset to Defaults"))
        self.reset_button.clicked.connect(self.reset_to_defaults)
        
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
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
        
        # Language selection - get current language from translation manager
        if TRANSLATIONS_AVAILABLE:
            translation_manager = get_translation_manager()
            current_language = translation_manager.get_language()
            for i in range(self.language_selector.count()):
                if self.language_selector.itemData(i) == current_language:
                    self.language_selector.setCurrentIndex(i)
                    break
        else:
            # Fallback to config if translations not available
            current_language = ui.get('language', 'en')
            for i in range(self.language_selector.count()):
                if self.language_selector.itemData(i) == current_language:
                    self.language_selector.setCurrentIndex(i)
                    break
        
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

        # Documents
        documents = self.current_config.get('documents', {})
        self.documents_enabled.setChecked(documents.get('enabled', True))
        self.chunk_size.setValue(documents.get('chunk_size', 1000))
        self.chunk_overlap.setValue(documents.get('chunk_overlap', 200))
        self.max_context_chunks.setValue(documents.get('max_context_chunks', 5))

        embedding = documents.get('embedding', {})
        self.embedding_provider.setCurrentText(embedding.get('provider', 'local'))
        self.embedding_model.setCurrentText(embedding.get('model', 'all-MiniLM-L6-v2'))

        vector = documents.get('vector', {})
        self.vector_backend.setCurrentText(vector.get('backend', 'faiss'))

        # Refresh document list
        self.refresh_documents()
        
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
                'hide_overlay_for_screenshots': self.hide_overlay_for_screenshots.isChecked(),
                'language': self.language_selector.itemData(self.language_selector.currentIndex()) or 'en'
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
            },
            'documents': {
                'enabled': self.documents_enabled.isChecked(),
                'data_dir': 'data/user_documents',
                'chunk_size': self.chunk_size.value(),
                'chunk_overlap': self.chunk_overlap.value(),
                'max_context_chunks': self.max_context_chunks.value(),
                'embedding': {
                    'provider': self.embedding_provider.currentText(),
                    'model': self.embedding_model.currentText(),
                    'device': 'cpu'
                },
                'vector': {
                    'backend': self.vector_backend.currentText(),
                    'dimension': 384,
                    'metric': 'cosine'
                }
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
            QMessageBox.warning(self, t("messages.warning", "Warning"), t("messages.warning_save_topics", "Failed to save topic definitions: {error}").format(error=str(e)))
        
        self.settings_changed.emit(new_config)
        self.accept()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self, t("messages.reset_confirm", "Reset Settings"), 
            t("messages.reset_confirm_msg", "Are you sure you want to reset all settings to defaults?"),
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
    