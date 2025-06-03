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
        self.setStyleSheet(f"""
            QDialog {{
                background: #141414;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: {self.scale(14)}px;
            }}
            QWidget {{
                background: #141414;
            }}
            QScrollArea {{
                background: #141414;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: #141414;
            }}
            QTabWidget::pane {{
                border: 1px solid #404040;
                border-radius: {self.scale(8)}px;
                background: #141414;
                margin-top: -1px;
            }}
            QTabWidget QWidget {{
                background: #141414;
            }}
            QTabBar::tab {{
                background: #1a1a1a;
                color: #ffffff;
                border: 1px solid #404040;
                border-bottom: none;
                padding: {self.scale(12)}px {self.scale(24)}px;
                margin-right: 2px;
                border-top-left-radius: {self.scale(8)}px;
                border-top-right-radius: {self.scale(8)}px;
                min-width: {self.scale(120)}px;
                font-weight: 500;
                font-size: {self.scale(13)}px;
            }}
            QTabBar::tab:selected {{
                background: #0078d4;
                color: #ffffff;
                border: 1px solid #0078d4;
            }}
            QTabBar::tab:hover:!selected {{
                background: #262626;
            }}
            QGroupBox {{
                font-size: {self.scale(16)}px;
                font-weight: 600;
                border: 1px solid #404040;
                border-radius: {self.scale(8)}px;
                margin-top: {self.scale(15)}px;
                padding-top: {self.scale(10)}px;
                background: #1a1a1a;
                color: #ffffff;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {self.scale(20)}px;
                padding: 0 {self.scale(10)}px 0 {self.scale(10)}px;
                color: #ffffff;
                font-size: {self.scale(15)}px;
                font-weight: 600;
            }}
            QLabel {{
                color: #ffffff;
                font-size: {self.scale(14)}px;
                min-height: {self.scale(28)}px;
                padding: {self.scale(4)}px;
            }}
            QCheckBox {{
                color: #ffffff;
                font-size: {self.scale(14)}px;
                spacing: {self.scale(12)}px;
                min-height: {self.scale(32)}px;
                padding: {self.scale(6)}px;
            }}
            QCheckBox::indicator {{
                width: {self.scale(20)}px;
                height: {self.scale(20)}px;
                border-radius: {self.scale(4)}px;
                border: 2px solid #666666;
                background: #2d2d2d;
            }}
            QCheckBox::indicator:checked {{
                background: #0078d4;
                border: 2px solid #0078d4;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }}
            QComboBox, QSpinBox, QLineEdit {{
                background: #1a1a1a;
                border: 1px solid #404040;
                border-radius: {self.scale(6)}px;
                color: #ffffff;
                font-size: {self.scale(13)}px;
                padding: {self.scale(8)}px {self.scale(12)}px;
                min-height: {self.scale(30)}px;
            }}
            QComboBox:hover, QSpinBox:hover, QLineEdit:hover {{
                background: #262626;
                border: 1px solid #0078d4;
            }}
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{
                border: 1px solid #0078d4;
                background: #262626;
            }}
            QComboBox::drop-down {{
                border: none;
                width: {self.scale(30)}px;
            }}
            QComboBox::down-arrow {{
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+Cg==);
            }}
            QComboBox QAbstractItemView {{
                background: #1a1a1a;
                border: 1px solid #404040;
                color: #ffffff;
                selection-background-color: #0078d4;
            }}
            QLineEdit::placeholder {{
                color: #808080;
            }}
            QTextEdit {{
                background: #2d2d2d;
                border: 2px solid #404040;
                border-radius: {self.scale(6)}px;
                color: #ffffff;
                font-size: {self.scale(13)}px;
                padding: {self.scale(10)}px;
                font-family: 'Consolas', 'Monaco', monospace;
                line-height: 1.4;
            }}
            QTextEdit:focus {{
                border: 2px solid #0078d4;
            }}
            QPushButton {{
                background: #404040;
                border: 2px solid #666666;
                border-radius: {self.scale(6)}px;
                color: #ffffff;
                font-size: {self.scale(13)}px;
                padding: {self.scale(10)}px {self.scale(20)}px;
                min-height: {self.scale(35)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: #505050;
                border: 2px solid #0078d4;
            }}
            QPushButton:pressed {{
                background: #2d2d2d;
            }}
            QPushButton.primary {{
                background: #0078d4;
                border: 2px solid #0078d4;
                color: #ffffff;
                font-weight: 600;
            }}
            QPushButton.primary:hover {{
                background: #106ebe;
                border: 2px solid #106ebe;
            }}
            QScrollBar:vertical {{
                background: #2d2d2d;
                width: {self.scale(12)}px;
                border-radius: {self.scale(6)}px;
            }}
            QScrollBar::handle:vertical {{
                background: #666666;
                border-radius: {self.scale(6)}px;
                min-height: {self.scale(20)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #808080;
            }}
            QSlider::groove:horizontal {{
                background: #404040;
                height: {self.scale(8)}px;
                border-radius: {self.scale(4)}px;
            }}
            QSlider::handle:horizontal {{
                background: #0078d4;
                border: 2px solid #0078d4;
                width: {self.scale(20)}px;
                height: {self.scale(20)}px;
                border-radius: {self.scale(10)}px;
                margin: -{self.scale(6)}px 0;
            }}
            QSlider::handle:horizontal:hover {{
                background: #106ebe;
                border: 2px solid #106ebe;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(self.scale(25), self.scale(25), self.scale(25), self.scale(25))
        layout.setSpacing(self.scale(20))
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.setup_ai_provider_tab()
        self.setup_audio_tab()
        self.setup_ui_tab()
        self.setup_assistant_tab()
        self.setup_prompts_tab()
        self.setup_knowledge_tab()
        self.setup_hotkeys_tab()
        self.setup_debug_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        self.setup_buttons(layout)
        
        self.setLayout(layout)
    
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
        self.azure_endpoint.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        azure_layout.addRow("Endpoint:", self.azure_endpoint)
        
        self.azure_api_key = QLineEdit()
        self.azure_api_key.setPlaceholderText("Your Azure OpenAI API key")
        self.azure_api_key.setEchoMode(QLineEdit.Password)
        self.azure_api_key.setMinimumHeight(self.scale(40))
        self.azure_api_key.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        azure_layout.addRow("API Key:", self.azure_api_key)
        
        self.azure_model = QLineEdit()
        self.azure_model.setPlaceholderText("gpt-4")
        self.azure_model.setMinimumHeight(self.scale(40))
        self.azure_model.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        azure_layout.addRow("Model:", self.azure_model)
        
        self.azure_deployment = QLineEdit()
        self.azure_deployment.setPlaceholderText("deployment-name")
        self.azure_deployment.setMinimumHeight(self.scale(40))
        self.azure_deployment.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        azure_layout.addRow("Deployment Name:", self.azure_deployment)
        
        self.azure_api_version = QLineEdit()
        self.azure_api_version.setText("2024-02-15-preview")
        self.azure_api_version.setMinimumHeight(self.scale(40))
        self.azure_api_version.setStyleSheet("QLineEdit { color: #ffffff; }")
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
        self.deepseek_api_key.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        deepseek_layout.addRow("API Key:", self.deepseek_api_key)
        
        self.deepseek_base_url = QLineEdit()
        self.deepseek_base_url.setPlaceholderText("https://api.deepseek.com")
        self.deepseek_base_url.setMinimumHeight(self.scale(40))
        self.deepseek_base_url.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        deepseek_layout.addRow("Base URL:", self.deepseek_base_url)
        
        self.deepseek_model = QLineEdit()
        self.deepseek_model.setPlaceholderText("deepseek-coder")
        self.deepseek_model.setMinimumHeight(self.scale(40))
        self.deepseek_model.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
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
        self.claude_api_key.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        claude_layout.addRow("API Key:", self.claude_api_key)
        
        self.claude_base_url = QLineEdit()
        self.claude_base_url.setPlaceholderText("https://api.anthropic.com")
        self.claude_base_url.setMinimumHeight(self.scale(40))
        self.claude_base_url.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
        claude_layout.addRow("Base URL:", self.claude_base_url)
        
        self.claude_model = QLineEdit()
        self.claude_model.setPlaceholderText("claude-3-sonnet-20240229")
        self.claude_model.setMinimumHeight(self.scale(40))
        self.claude_model.setStyleSheet("QLineEdit { color: #ffffff; } QLineEdit::placeholder { color: #a0a0a0; }")
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
        content.setMinimumSize(self.scale(1200), self.scale(600))
        
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
        
        # Transcription Provider
        transcription_group = QGroupBox("📝 Transcription Settings")
        transcription_group.setMinimumHeight(self.scale(200))
        transcription_layout = QFormLayout()
        transcription_layout.setSpacing(self.scale(20))
        transcription_layout.setLabelAlignment(Qt.AlignLeft)
        
        self.transcription_provider = QComboBox()
        self.transcription_provider.addItems(["local_whisper", "google_speech", "azure_speech"])
        self.transcription_provider.setMinimumHeight(self.scale(40))
        transcription_layout.addRow("Provider:", self.transcription_provider)
        
        self.whisper_model = QComboBox()
        self.whisper_model.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_model.setMinimumHeight(self.scale(40))
        transcription_layout.addRow("Whisper Model:", self.whisper_model)
        
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
        appearance_group.setMinimumHeight(self.scale(400))
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
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        
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
        
        # Transcription
        transcription = self.current_config.get('transcription', {})
        self.transcription_provider.setCurrentText(transcription.get('provider', 'local_whisper'))
        whisper_config = transcription.get('whisper', {})
        self.whisper_model.setCurrentText(whisper_config.get('model_size', 'base'))
        
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
        
        # Debug
        debug = self.current_config.get('debug', {})
        self.debug_enabled.setChecked(debug.get('enabled', False))
        self.verbose_logging.setChecked(debug.get('verbose_logging', False))
        self.save_transcriptions.setChecked(debug.get('save_transcriptions', False))
        self.save_audio_chunks.setChecked(debug.get('save_audio_chunks', False))
        self.max_debug_files.setValue(debug.get('max_debug_files', 100))
        
        # Update visibility based on provider
        self.on_provider_changed(self.ai_provider_type.currentText())
    
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
                'processing_interval_seconds': self.processing_interval.value() / 10.0
            },
            'transcription': {
                'provider': self.transcription_provider.currentText(),
                'whisper': {
                    'model_size': self.whisper_model.currentText()
                }
            },
            'ui': {
                'overlay': {
                    'size_multiplier': self.size_multiplier.value() / 10.0,
                    'show_transcript': self.show_transcript.isChecked(),
                    'hide_from_sharing': self.hide_from_sharing.isChecked(),
                    'auto_hide_seconds': self.auto_hide_seconds.value()
                }
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
                'emergency_reset': self.emergency_reset.text()
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