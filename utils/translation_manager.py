"""
Translation Manager for MeetMinder
Provides multi-language support for the application UI
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, List
from functools import lru_cache
from utils.app_logger import logger


class TranslationManager:
    """Manages translations for the MeetMinder application"""
    
    # Supported languages with their display names
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'es': 'Español',
        'fr': 'Français',
        'de': 'Deutsch',
        'zh': '中文',
        'ja': '日本語',
        'ko': '한국어',
        'pt': 'Português',
        'it': 'Italiano',
        'ru': 'Русский',
        'ar': 'العربية',
        'hi': 'हिन्दी',
        'nl': 'Nederlands',
        'pl': 'Polski',
        'tr': 'Türkçe'
    }
    
    DEFAULT_LANGUAGE = 'en'
    
    def __init__(self, locale_dir: str = "data/locales", language: str = None):
        """
        Initialize the TranslationManager
        
        Args:
            locale_dir: Directory containing translation JSON files
            language: Language code (e.g., 'en', 'fr', 'es'). If None, uses config or default
        """
        self.locale_dir = Path(locale_dir)
        self.locale_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_language = language or self.DEFAULT_LANGUAGE
        self.translations: Dict[str, Dict[str, str]] = {}
        
        # Load translations
        self._load_translations()
        
        logger.info(f"🌐 TranslationManager initialized (locale_dir: {self.locale_dir})")
    
    def _load_translations(self):
        """Load all available translation files"""
        for lang_code in self.SUPPORTED_LANGUAGES.keys():
            translation_file = self.locale_dir / f"{lang_code}.json"
            if translation_file.exists():
                try:
                    with open(translation_file, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                    logger.info(f"✅ Loaded translations for {lang_code} ({self.SUPPORTED_LANGUAGES[lang_code]})")
                except Exception as e:
                    logger.error(f"❌ Failed to load translations for {lang_code}: {e}")
                    # Load English as fallback
                    if lang_code != self.DEFAULT_LANGUAGE:
                        self.translations[lang_code] = self.translations.get(self.DEFAULT_LANGUAGE, {})
            else:
                # If file doesn't exist, use English as fallback
                if lang_code == self.DEFAULT_LANGUAGE:
                    # Create default English translations if missing
                    self.translations[lang_code] = self._get_default_translations()
                else:
                    # For other languages, use English until file is created
                    if self.DEFAULT_LANGUAGE not in self.translations:
                        self.translations[self.DEFAULT_LANGUAGE] = self._get_default_translations()
                    self.translations[lang_code] = self.translations[self.DEFAULT_LANGUAGE]
    
    def set_language(self, language: str):
        """
        Set the current language
        
        Args:
            language: Language code (e.g., 'en', 'fr', 'es')
        """
        if language not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"⚠️ Unsupported language: {language}, falling back to {self.DEFAULT_LANGUAGE}")
            language = self.DEFAULT_LANGUAGE
        
        self.current_language = language
        logger.info(f"🌐 Language set to: {self.SUPPORTED_LANGUAGES.get(language, language)}")
    
    def get_language(self) -> str:
        """Get the current language code"""
        return self.current_language
    
    def get_language_name(self, language_code: Optional[str] = None) -> str:
        """Get the display name for a language code"""
        code = language_code or self.current_language
        return self.SUPPORTED_LANGUAGES.get(code, code)
    
    def translate(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Translate a key to the current language
        
        Args:
            key: Translation key (supports dot notation, e.g., 'ui.buttons.ask_ai')
            default: Default text if translation not found
            **kwargs: Format arguments for the translation string
        
        Returns:
            Translated string
        """
        # Get translation for current language
        translation = self.translations.get(self.current_language, {})
        
        # Navigate through nested dictionary using dot notation
        keys = key.split('.')
        value = translation
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # Fallback to English if translation not found
                if self.current_language != self.DEFAULT_LANGUAGE:
                    en_translation = self.translations.get(self.DEFAULT_LANGUAGE, {})
                    value = en_translation
                    for k2 in keys:
                        if isinstance(value, dict) and k2 in value:
                            value = value[k2]
                        else:
                            value = default or key
                            break
                else:
                    value = default or key
                break
        
        # If value is still a dict, return the key
        if isinstance(value, dict):
            value = default or key
        
        # Format the string if kwargs provided
        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value
        
        return str(value)
    
    def t(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """Short alias for translate()"""
        return self.translate(key, default, **kwargs)
    
    def get_available_languages(self) -> List[tuple]:
        """
        Get list of available languages as (code, name) tuples
        
        Returns:
            List of (language_code, language_name) tuples
        """
        return [(code, name) for code, name in self.SUPPORTED_LANGUAGES.items()]
    
    def get_available_locale_files(self) -> List[tuple]:
        """
        Get list of languages that have actual locale files (not just supported)
        
        Returns:
            List of (language_code, language_name) tuples for languages with locale files
        """
        available = []
        for lang_code in self.SUPPORTED_LANGUAGES.keys():
            translation_file = self.locale_dir / f"{lang_code}.json"
            if translation_file.exists():
                available.append((lang_code, self.SUPPORTED_LANGUAGES[lang_code]))
        return available
    
    def _get_default_translations(self) -> Dict[str, any]:
        """Get default English translations"""
        return {
            "ui": {
                "overlay": {
                    "title": "MeetMinder",
                    "ask_ai": "🤖 Ask AI",
                    "toggle_mic": "Toggle microphone recording",
                    "settings": "Open settings",
                    "hide": "Hide",
                    "show": "Show",
                    "close": "Close application",
                    "expand": "Expand details",
                    "collapse": "Collapse details",
                    "timer": "00:00",
                    "shortcut": "Ctrl+Space"
                },
                "buttons": {
                    "ask_ai": "🤖 Ask AI",
                    "mic": "🎤",
                    "settings": "⚙️",
                    "hide": "Hide",
                    "show": "Show",
                    "close": "✕",
                    "expand": "▼",
                    "collapse": "▲"
                },
                "sections": {
                    "ai_response": "🤖 AI Response",
                    "live_transcript": "📝 Live Transcript (System Audio)",
                    "topic_analysis": "🧠 Topic Analysis",
                    "guidance": "💡 Guidance",
                    "flow": "🔄 Flow"
                },
                "status": {
                    "no_active_topic": "No active topic",
                    "start_speaking": "Start speaking to get guidance",
                    "waiting": "Waiting",
                    "analyzing": "🤔 Analyzing context...",
                    "processing": "⏳ Processing...",
                    "waiting_audio": "Waiting for system audio...",
                    "transcript_enabled": "Transcript enabled - waiting for system audio...",
                    "screenshot_saved": "📸 Screenshot saved: {path}",
                    "screenshot_taken": "📸 Screenshot taken!",
                    "error": "Error: {error}"
                },
                "tooltips": {
                    "ask_ai": "Trigger AI assistance (Ctrl+Space)",
                    "mic": "Toggle microphone recording (Ctrl+M)",
                    "settings": "Open settings (Ctrl+,)",
                    "hide": "Hide overlay",
                    "show": "Show overlay",
                    "close": "Close application",
                    "expand": "Expand/collapse details"
                }
            },
            "settings": {
                "title": "MeetMinder Settings",
                "tabs": {
                    "ai_provider": "🤖 AI Provider",
                    "audio": "🎤 Audio",
                    "interface": "🖥️ Interface",
                    "assistant": "🧠 Assistant",
                    "prompts": "📝 Prompts",
                    "knowledge": "🧠 Knowledge",
                    "documents": "📚 Documents",
                    "hotkeys": "⌨️ Hotkeys",
                    "debug": "🐛 Debug"
                },
                "buttons": {
                    "save": "💾 Save Settings",
                    "cancel": "❌ Cancel",
                    "reset": "🔄 Reset to Defaults"
                },
                "language": {
                    "label": "Language:",
                    "tooltip": "Select the interface language"
                }
            },
            "messages": {
                "loading": "🚀 Loading MeetMinder...\nPlease wait...",
                "initializing": "Initializing MeetMinder...",
                "ready": "✅ MeetMinder is now running!",
                "error": "Error: {error}",
                "settings_saved": "Settings saved successfully!",
                "settings_reset": "Settings reset to defaults"
            }
        }


# Global translation manager instance
_translation_manager: Optional[TranslationManager] = None


def get_translation_manager(locale_dir: str = "data/locales", language: str = None) -> TranslationManager:
    """Get or create the global translation manager instance"""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager(locale_dir, language)
    elif language is not None:
        _translation_manager.set_language(language)
    return _translation_manager


def t(key: str, default: Optional[str] = None, **kwargs) -> str:
    """Global translation function"""
    manager = get_translation_manager()
    return manager.translate(key, default, **kwargs)


def set_language(language: str):
    """Set the global language"""
    manager = get_translation_manager()
    manager.set_language(language)
    logger.info(f"✅ Language changed to: {language}")

