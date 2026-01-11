#!/usr/bin/env python3
"""
MeetMinder Lightweight - Real-time AI meeting assistant with minimal dependencies
Uses webview instead of PyQt5 for drastically reduced build size (15-30MB vs 150MB+)
"""

import os
import sys
from pathlib import Path

# Add bootstrap dependencies directory to path if running from bootstrap launcher
# This must be done BEFORE any other imports
if 'PYTHONPATH' in os.environ:
    # Bootstrap launcher sets PYTHONPATH to deps directory
    deps_dir = os.environ['PYTHONPATH']
    if deps_dir and deps_dir not in sys.path:
        sys.path.insert(0, deps_dir)
        print(f"[BOOTSTRAP] Added deps directory to path: {deps_dir}")
else:
    # Check if we're in a bootstrap installation
    localappdata = os.getenv('LOCALAPPDATA')
    if localappdata:
        deps_dir = Path(localappdata) / 'MeetMinder' / 'deps'
        if deps_dir.exists() and str(deps_dir) not in sys.path:
            sys.path.insert(0, str(deps_dir))
            print(f"[BOOTSTRAP] Added deps directory to path: {deps_dir}")

import asyncio
import threading
import time
import warnings
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
from core.document_store import DocumentStore
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

# Import translation system
try:
    from utils.translation_manager import get_translation_manager, set_language
    TRANSLATIONS_AVAILABLE = True
except ImportError:
    TRANSLATIONS_AVAILABLE = False
    logger.info("[TRANSLATION] Translation system not available")


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
                
                # Initialize translation system
                if TRANSLATIONS_AVAILABLE:
                    try:
                        # Get language from config
                        ui_config = self.config.get('ui', {})
                        language = ui_config.get('language', 'en')
                        
                        # Initialize translation manager
                        translation_manager = get_translation_manager(language=language)
                        logger.info(f"[TRANSLATION] Language initialized: {translation_manager.get_language()}")
                    except Exception as e:
                        logger.info(f"[TRANSLATION] Error initializing translation system: {e}")
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
            
            # Initialize translations in overlay
            if TRANSLATIONS_AVAILABLE:
                try:
                    self.overlay.initialize_translations()
                except Exception as e:
                    logger.info(f"[TRANSLATION] Error initializing overlay translations: {e}")
            
            # 7. Document Store
            print("[DOCS] Initializing document store...")
            self.document_store = DocumentStore(self.config.get('document_store', {}))
            # Initialize async in background
            self.thread_pool.submit(lambda: asyncio.run(self.document_store.initialize()))

            # 8. Screen Capture
            print("[SCREEN] Initializing screen capture...")
            self.screen_capture = ScreenCapture()

            # 9. Audio Contextualizer
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
        if TRANSLATIONS_AVAILABLE:
            try:
                translation_manager = get_translation_manager()
                screenshot_msg = translation_manager.t('ui.status.screenshot_taken', "[SCREENSHOT] Screenshot taken!")
                self.overlay.update_ai_response(screenshot_msg)
            except Exception:
                self.overlay.update_ai_response("[SCREENSHOT] Screenshot taken!")
        else:
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
            
            # Update UI with translated message
            if TRANSLATIONS_AVAILABLE:
                try:
                    translation_manager = get_translation_manager()
                    analyzing_msg = translation_manager.t('ui.status.analyzing', "[AI] Analyzing context...")
                    self.overlay.update_ai_response(analyzing_msg)
                except Exception:
                    self.overlay.update_ai_response("[AI] Analyzing context...")
            else:
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
            if TRANSLATIONS_AVAILABLE:
                try:
                    translation_manager = get_translation_manager()
                    error_msg = translation_manager.t('ui.status.error', "Error: {error}").format(error=str(e))
                    self.overlay.update_ai_response(error_msg)
                except Exception:
                    self.overlay.update_ai_response(f"[ERROR] {str(e)}")
            else:
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
            
            def __getattribute__(self, name):
                """Override to prevent introspection of internal attributes that cause hangs"""
                # Block access to problematic internal attributes that cause pywebview to hang
                blocked_attrs = {
                    '__abstractmethods__', '__dict__', '__weakref__', 
                    '__module__', '__qualname__', '__annotations__',
                    '__orig_bases__', '__parameters__', '__args__',
                    '__mro__', '__bases__', '__subclasses__'
                }
                if name in blocked_attrs:
                    raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
                # Only allow access to our defined methods and essential attributes
                allowed_attrs = {'__class__', '__slots__', '__doc__', '__init__', '__getattribute__', '__dir__'}
                allowed_methods = {'get_settings', 'save_settings', 'close_settings', 
                                 'upload_document', 'delete_document', 'toggle_document'}
                if name.startswith('_') and name not in allowed_attrs and name not in allowed_methods:
                    raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
                try:
                    return super().__getattribute__(name)
                except AttributeError:
                    raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
            
            def __dir__(self):
                """Limit introspection to only our public methods"""
                return ['get_settings', 'save_settings', 'close_settings', 
                        'upload_document', 'delete_document', 'toggle_document']
            
            def __dir__(self):
                """Limit introspection to only our public methods"""
                return ['get_settings', 'save_settings', 'close_settings', 
                        'upload_document', 'delete_document', 'toggle_document']

            def get_settings(self):
                """Get current settings - returns only simple data types"""
                try:
                    app = app_ref
                    config = app.config
                    overlay_config = config.get('ui', {}).get('overlay', {})
                    profile = app.profile_manager.profile if app.profile_manager.profile else None
                    
                    # Get documents
                    documents = []
                    if hasattr(app, 'document_store'):
                        docs = app.document_store.list_documents()
                        documents = [
                            {
                                'id': d.id,
                                'name': d.file_name,
                                'size': d.file_size,
                                'status': d.status,
                                'chunks': d.chunks_count,
                                'active': d.metadata.get('active', True),
                                'type': d.mime_type
                            }
                            for d in docs
                        ]

                    # Get available languages that have actual locale files
                    available_languages = {}
                    ui_translations = {}
                    if TRANSLATIONS_AVAILABLE:
                        try:
                            translation_manager = get_translation_manager()
                            current_lang = translation_manager.get_language()
                            
                            # Only get languages that have locale files
                            for lang_code, lang_name in translation_manager.get_available_locale_files():
                                available_languages[lang_code] = lang_name
                            
                            # Get comprehensive UI translations for all static texts
                            ui_translations = {
                                # Title and navigation
                                'title': translation_manager.t('settings.title', 'MeetMinder Settings'),
                                'nav_general': translation_manager.t('settings.nav.general', 'General'),
                                'nav_ai': translation_manager.t('settings.nav.ai', 'AI & Model'),
                                'nav_audio': translation_manager.t('settings.nav.audio', 'Audio'),
                                'nav_documents': translation_manager.t('settings.nav.documents', 'Documents'),
                                'nav_profile': translation_manager.t('settings.nav.profile', 'Profile'),
                                
                                # General tab
                                'general_title': translation_manager.t('settings.general.title', 'General Settings'),
                                'general_subtitle': translation_manager.t('settings.general.subtitle', 'Configure interface and application behavior'),
                                'always_on_top': translation_manager.t('settings.general.always_on_top', 'Always on Top'),
                                'always_on_top_desc': translation_manager.t('settings.general.always_on_top_desc', 'Keep overlay visible above other windows'),
                                'hide_from_sharing': translation_manager.t('settings.hide_from_sharing.label', 'Hide from screen sharing'),
                                'hide_from_sharing_desc': translation_manager.t('settings.general.hide_from_sharing_desc', 'Invisible to Zoom/Teams/Meet'),
                                'interface_language': translation_manager.t('settings.language.label', 'Interface Language'),
                                'select_language': translation_manager.t('settings.language.tooltip', 'Select the interface language'),
                                'overlay_opacity': translation_manager.t('settings.general.overlay_opacity', 'Overlay Opacity'),
                                'auto_hide_timer': translation_manager.t('settings.general.auto_hide_timer', 'Auto-hide Timer (seconds)'),
                                
                                # AI tab
                                'ai_title': translation_manager.t('settings.ai.title', 'AI Configuration'),
                                'ai_subtitle': translation_manager.t('settings.ai.subtitle', 'Manage your AI provider and model settings'),
                                'ai_provider': translation_manager.t('settings.ai_provider.provider_label', 'AI Provider'),
                                'api_key': translation_manager.t('settings.ai_provider.azure.api_key', 'API Key'),
                                'model_name': translation_manager.t('settings.ai_provider.azure.model', 'Model Name'),
                                'response_style': translation_manager.t('settings.assistant.response_style', 'Response Style'),
                                # AI Provider options
                                'ai_provider_azure': translation_manager.t('settings.ai_provider.azure.title', '🔷 Azure OpenAI').replace('🔷 ', ''),
                                'ai_provider_openai': translation_manager.t('settings.ai_provider.openai.title', '🟢 OpenAI').replace('🟢 ', ''),
                                'ai_provider_gemini': translation_manager.t('settings.ai_provider.gemini.title', '🔴 Google Gemini').replace('🔴 ', ''),
                                # Response Style options
                                'response_concise': translation_manager.t('settings.ai.response_concise', 'Concise'),
                                'response_balanced': translation_manager.t('settings.ai.response_balanced', 'Balanced'),
                                'response_detailed': translation_manager.t('settings.ai.response_detailed', 'Detailed'),
                                # Placeholders
                                'placeholder_api_key': translation_manager.t('settings.ai_provider.azure.api_key_placeholder', 'sk-...'),
                                'placeholder_model': translation_manager.t('settings.ai_provider.azure.model_placeholder', 'gpt-4'),
                                
                                # Audio tab
                                'audio_title': translation_manager.t('settings.audio.title', 'Audio Settings'),
                                'audio_subtitle': translation_manager.t('settings.audio.subtitle', 'Configure microphone and transcription'),
                                'audio_mode': translation_manager.t('settings.audio.mode', 'Audio Input Mode'),
                                'whisper_language': translation_manager.t('settings.audio.whisper_language', 'Whisper Language'),
                                'auto_start': translation_manager.t('settings.audio.auto_start', 'Auto-start Transcription'),
                                'auto_start_desc': translation_manager.t('settings.audio.auto_start_desc', 'Start listening when app launches'),
                                # Audio Mode options
                                'audio_mode_single': translation_manager.t('settings.audio.mode_single', 'Microphone Only'),
                                'audio_mode_dual': translation_manager.t('settings.audio.mode_dual', 'Microphone + System Audio'),
                                # Whisper Language options
                                'language_english': translation_manager.t('settings.audio.language_english', 'English'),
                                'language_auto': translation_manager.t('settings.audio.language_auto', 'Auto-detect'),
                                'language_spanish': translation_manager.t('settings.audio.language_spanish', 'Spanish'),
                                'language_french': translation_manager.t('settings.audio.language_french', 'French'),
                                'language_german': translation_manager.t('settings.audio.language_german', 'German'),
                                
                                # Documents tab
                                'documents_title': translation_manager.t('settings.documents.title_short', 'Knowledge Base'),
                                'documents_subtitle': translation_manager.t('settings.documents.subtitle', 'Manage documents for context-aware answers'),
                                'upload_documents': translation_manager.t('settings.documents.upload_documents', 'Click to Upload Documents'),
                                'support_formats': translation_manager.t('settings.documents.support_formats', 'Support for PDF, TXT, MD, DOCX'),
                                
                                # Profile tab
                                'profile_title': translation_manager.t('settings.profile.title', 'User Profile'),
                                'profile_subtitle': translation_manager.t('settings.profile.subtitle', 'Personalize AI responses for your role'),
                                'full_name': translation_manager.t('settings.profile.full_name', 'Full Name'),
                                'job_title': translation_manager.t('settings.profile.job_title', 'Job Title'),
                                'skills': translation_manager.t('settings.profile.skills', 'Skills & Expertise'),
                                # Profile placeholders
                                'placeholder_name': translation_manager.t('settings.profile.placeholder_name', 'Your name'),
                                'placeholder_title': translation_manager.t('settings.profile.placeholder_title', 'e.g. Software Engineer'),
                                'placeholder_skills': translation_manager.t('settings.profile.placeholder_skills', 'Python, Project Management, etc.'),
                                # Documents
                                'loading_documents': translation_manager.t('settings.documents.loading', 'Loading documents...'),
                                'delete_confirm': translation_manager.t('settings.documents.delete_confirm', 'Are you sure you want to delete this document?'),
                                'upload_failed': translation_manager.t('settings.documents.upload_failed', 'Upload failed: {error}'),
                                'error_saving': translation_manager.t('settings.documents.error_saving', 'Error saving settings: {error}'),
                                'kb': translation_manager.t('settings.documents.kb', 'KB'),
                                'chunks_label': translation_manager.t('settings.documents.chunks', 'chunks'),
                                'status_active': translation_manager.t('settings.documents.status.active', 'Active'),
                                'status_inactive': translation_manager.t('settings.documents.status.inactive', 'Inactive'),
                                'status_processing': translation_manager.t('settings.documents.status.processing', 'Processing'),
                                'status_ready': translation_manager.t('settings.documents.status.ready', 'Ready'),
                                'status_error': translation_manager.t('settings.documents.status.error', 'Error'),
                                'delete_button': translation_manager.t('settings.documents.delete', '🗑️ Delete').replace('🗑️ ', ''),
                                'no_documents': translation_manager.t('settings.documents.no_documents', 'No documents yet. Upload some to get started!'),
                                
                                # Buttons
                                'save': translation_manager.t('settings.buttons.save_changes', 'Save Changes'),
                                'cancel': translation_manager.t('settings.buttons.cancel', '❌ Cancel').replace('❌ ', '')
                            }
                        except Exception as e:
                            logger.info(f"[SETTINGS] Error getting languages: {e}")
                            # Fallback: only include languages with files
                            import os
                            from pathlib import Path
                            locale_dir = Path("data/locales")
                            fallback_map = {
                                'en': 'English',
                                'es': 'Español',
                                'fr': 'Français',
                                'de': 'Deutsch',
                                'zh': '中文',
                                'ja': '日本語',
                                'ko': '한국어',
                                'pt': 'Português',
                                'it': 'Italiano',
                                'ru': 'Русский'
                            }
                            available_languages = {}
                            for lang_code, lang_name in fallback_map.items():
                                if (locale_dir / f"{lang_code}.json").exists():
                                    available_languages[lang_code] = lang_name
                            # Fallback translations (minimal set)
                            ui_translations = {
                                'title': 'MeetMinder Settings',
                                'nav_general': 'General',
                                'nav_ai': 'AI & Model',
                                'nav_audio': 'Audio',
                                'nav_documents': 'Documents',
                                'nav_profile': 'Profile',
                                'general_title': 'General Settings',
                                'general_subtitle': 'Configure interface and application behavior',
                                'always_on_top': 'Always on Top',
                                'always_on_top_desc': 'Keep overlay visible above other windows',
                                'hide_from_sharing': 'Hide from Screen Sharing',
                                'hide_from_sharing_desc': 'Invisible to Zoom/Teams/Meet',
                                'interface_language': 'Interface Language',
                                'select_language': 'Select the interface language',
                                'overlay_opacity': 'Overlay Opacity',
                                'auto_hide_timer': 'Auto-hide Timer (seconds)',
                                'ai_title': 'AI Configuration',
                                'ai_subtitle': 'Manage your AI provider and model settings',
                                'ai_provider': 'AI Provider',
                                'api_key': 'API Key',
                                'model_name': 'Model Name',
                                'response_style': 'Response Style',
                                'ai_provider_azure': 'Azure OpenAI',
                                'ai_provider_openai': 'OpenAI',
                                'ai_provider_gemini': 'Google Gemini',
                                'response_concise': 'Concise',
                                'response_balanced': 'Balanced',
                                'response_detailed': 'Detailed',
                                'placeholder_api_key': 'sk-...',
                                'placeholder_model': 'gpt-4',
                                'audio_title': 'Audio Settings',
                                'audio_subtitle': 'Configure microphone and transcription',
                                'audio_mode': 'Audio Input Mode',
                                'whisper_language': 'Whisper Language',
                                'auto_start': 'Auto-start Transcription',
                                'auto_start_desc': 'Start listening when app launches',
                                'audio_mode_single': 'Microphone Only',
                                'audio_mode_dual': 'Microphone + System Audio',
                                'language_english': 'English',
                                'language_auto': 'Auto-detect',
                                'language_spanish': 'Spanish',
                                'language_french': 'French',
                                'language_german': 'German',
                                'documents_title': 'Knowledge Base',
                                'documents_subtitle': 'Manage documents for context-aware answers',
                                'upload_documents': 'Click to Upload Documents',
                                'support_formats': 'Support for PDF, TXT, MD, DOCX',
                                'loading_documents': 'Loading documents...',
                                'no_documents': 'No documents yet. Upload some to get started!',
                                'profile_title': 'User Profile',
                                'profile_subtitle': 'Personalize AI responses for your role',
                                'full_name': 'Full Name',
                                'job_title': 'Job Title',
                                'skills': 'Skills & Expertise',
                                'placeholder_name': 'Your name',
                                'placeholder_title': 'e.g. Software Engineer',
                                'placeholder_skills': 'Python, Project Management, etc.',
                                'save': 'Save Changes',
                                'cancel': 'Cancel'
                            }
                    else:
                        # Fallback: only include languages with files
                        import os
                        from pathlib import Path
                        locale_dir = Path("data/locales")
                        fallback_map = {
                            'en': 'English',
                            'es': 'Español',
                            'fr': 'Français',
                            'de': 'Deutsch',
                            'zh': '中文',
                            'ja': '日本語',
                            'ko': '한국어',
                            'pt': 'Português',
                            'it': 'Italiano',
                            'ru': 'Русский'
                        }
                        available_languages = {}
                        for lang_code, lang_name in fallback_map.items():
                            if (locale_dir / f"{lang_code}.json").exists():
                                available_languages[lang_code] = lang_name
                        # Fallback translations (minimal set)
                        ui_translations = {
                            'title': 'MeetMinder Settings',
                            'nav_general': 'General',
                            'nav_ai': 'AI & Model',
                            'nav_audio': 'Audio',
                            'nav_documents': 'Documents',
                            'nav_profile': 'Profile',
                            'general_title': 'General Settings',
                            'general_subtitle': 'Configure interface and application behavior',
                            'always_on_top': 'Always on Top',
                            'always_on_top_desc': 'Keep overlay visible above other windows',
                            'hide_from_sharing': 'Hide from Screen Sharing',
                            'hide_from_sharing_desc': 'Invisible to Zoom/Teams/Meet',
                            'interface_language': 'Language:',
                            'select_language': 'Select the interface language',
                            'overlay_opacity': 'Overlay Opacity',
                            'auto_hide_timer': 'Auto-hide Timer (seconds)',
                            'ai_title': 'AI Configuration',
                            'ai_subtitle': 'Manage your AI provider and model settings',
                            'ai_provider': 'AI Provider',
                            'api_key': 'API Key',
                            'model_name': 'Model Name',
                            'response_style': 'Response Style',
                            'ai_provider_azure': 'Azure OpenAI',
                            'ai_provider_openai': 'OpenAI',
                            'ai_provider_gemini': 'Google Gemini',
                            'response_concise': 'Concise',
                            'response_balanced': 'Balanced',
                            'response_detailed': 'Detailed',
                            'placeholder_api_key': 'sk-...',
                            'placeholder_model': 'gpt-4',
                            'audio_title': 'Audio Settings',
                            'audio_subtitle': 'Configure microphone and transcription',
                            'audio_mode': 'Audio Input Mode',
                            'whisper_language': 'Whisper Language',
                            'auto_start': 'Auto-start Transcription',
                            'auto_start_desc': 'Start listening when app launches',
                            'audio_mode_single': 'Microphone Only',
                            'audio_mode_dual': 'Microphone + System Audio',
                            'language_english': 'English',
                            'language_auto': 'Auto-detect',
                            'language_spanish': 'Spanish',
                            'language_french': 'French',
                            'language_german': 'German',
                            'documents_title': 'Knowledge Base',
                            'documents_subtitle': 'Manage documents for context-aware answers',
                            'upload_documents': 'Click to Upload Documents',
                            'support_formats': 'Support for PDF, TXT, MD, DOCX',
                            'loading_documents': 'Loading documents...',
                            'no_documents': 'No documents yet. Upload some to get started!',
                            'profile_title': 'User Profile',
                            'profile_subtitle': 'Personalize AI responses for your role',
                            'full_name': 'Full Name',
                            'job_title': 'Job Title',
                            'skills': 'Skills & Expertise',
                            'placeholder_name': 'Your name',
                            'placeholder_title': 'e.g. Software Engineer',
                            'placeholder_skills': 'Python, Project Management, etc.',
                            'delete_confirm': 'Are you sure you want to delete this document?',
                            'upload_failed': 'Upload failed: {error}',
                            'error_saving': 'Error saving settings: {error}',
                            'kb': 'KB',
                            'chunks_label': 'chunks',
                            'status_active': 'Active',
                            'status_inactive': 'Inactive',
                            'status_processing': 'Processing',
                            'status_ready': 'Ready',
                            'status_error': 'Error',
                            'delete_button': 'Delete',
                            'save': 'Save Changes',
                            'cancel': 'Cancel'
                        }

                    return {
                        'documents': documents,
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
                            'show_transcript': overlay_config.get('show_transcript', False),
                            'language': config.get('ui.language', 'en')
                        },
                        'available_languages': available_languages,
                        'translations': ui_translations,
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
                        
                        # Handle language change
                        ui_language = ui_settings.get('language', None)
                        if ui_language and TRANSLATIONS_AVAILABLE:
                            current_language = get_translation_manager().get_language()
                            if ui_language != current_language:
                                logger.info(f"[TRANSLATION] Language changing from {current_language} to {ui_language}")
                                set_language(ui_language)
                                # Refresh overlay translations
                                if hasattr(app, 'overlay') and hasattr(app.overlay, 'refresh_translations'):
                                    app.overlay.refresh_translations()
                                logger.info(f"[TRANSLATION] Language changed to: {ui_language}")
                        
                        # Store language in config
                        if ui_language:
                            updates.setdefault('ui', {})['language'] = ui_language

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
                        
                        # If language changed, return a flag so frontend knows to reload
                        language_changed = False
                        if 'ui' in updates and 'language' in updates['ui']:
                            language_changed = True
                        
                        return {'success': True, 'language_changed': language_changed}
                    else:
                        logger.info("[SETTINGS] No configuration changes detected")
                        return {'success': True, 'message': 'No changes', 'language_changed': False}
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
                    return False

            def upload_document(self):
                """Handle document upload"""
                try:
                    app = app_ref
                    if not hasattr(app, 'document_store'):
                        return {'success': False, 'error': 'Document store not initialized'}
                    
                    # Open file dialog
                    file_types = ('Document Files (*.pdf;*.txt;*.md;*.docx)', 'All Files (*.*)')
                    result = settings_window_ref[0].create_file_dialog(
                        webview.OPEN_DIALOG, 
                        allow_multiple=True, 
                        file_types=file_types
                    )
                    
                    if not result:
                        return {'success': False, 'message': 'No file selected'}
                    
                    uploaded_docs = []
                    for file_path in result:
                        # Add file to document store
                        # Run async method in thread pool
                        future = app.thread_pool.submit(
                            lambda p=file_path: asyncio.run(app.document_store.add_file(p, {'active': True}))
                        )
                        doc_id = future.result()
                        
                        # Trigger processing
                        app.thread_pool.submit(
                            lambda d=doc_id: asyncio.run(app.document_store.process_document(d))
                        )
                        uploaded_docs.append(doc_id)
                        
                    return {'success': True, 'count': len(uploaded_docs)}
                except Exception as e:
                    logger.error(f"[SETTINGS] Error uploading document: {e}")
                    return {'success': False, 'error': str(e)}

            def toggle_document(self, doc_id, active):
                """Toggle document active status"""
                try:
                    app = app_ref
                    if not hasattr(app, 'document_store'):
                        return {'success': False}
                        
                    doc = app.document_store.get_document_info(doc_id)
                    if doc:
                        doc.metadata['active'] = active
                        app.document_store._save_metadata()
                        return {'success': True}
                    return {'success': False, 'error': 'Document not found'}
                except Exception as e:
                    logger.error(f"[SETTINGS] Error toggling document: {e}")
                    return {'success': False, 'error': str(e)}

            def delete_document(self, doc_id):
                """Delete document"""
                try:
                    app = app_ref
                    if not hasattr(app, 'document_store'):
                        return {'success': False}
                        
                    # Run async delete in thread pool
                    future = app.thread_pool.submit(
                        lambda: asyncio.run(app.document_store.delete_document(doc_id))
                    )
                    success = future.result()
                    return {'success': success}
                except Exception as e:
                    logger.error(f"[SETTINGS] Error deleting document: {e}")
                    return {'success': False, 'error': str(e)}
        
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
                
                # Start webview with minimal introspection to avoid hanging
                try:
                    webview.start(debug=False)
                except Exception as e:
                    logger.error(f"[SETTINGS] Error starting webview: {e}")
                    import traceback
                    traceback.print_exc()
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

            # Update overlay with translated message
            if TRANSLATIONS_AVAILABLE:
                try:
                    translation_manager = get_translation_manager()
                    ready_msg = translation_manager.t('ui.status.waiting', "Ready to assist! Press Ctrl+Space or click 'Ask AI'")
                    self.overlay.update_ai_response(ready_msg)
                except Exception:
                    self.overlay.update_ai_response("Ready to assist! Press Ctrl+Space or click 'Ask AI'")
            else:
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

