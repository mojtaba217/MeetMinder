import yaml
import os
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import json
import hashlib
from functools import lru_cache

@dataclass
class TranscriptionConfig:
    provider: str = "local_whisper"  # local_whisper, google_speech, azure_speech
    whisper_model_size: str = "base"
    google_language: str = "en-US"
    azure_language: str = "en-US"
    google_credentials_path: Optional[str] = None
    azure_subscription_key: Optional[str] = None
    azure_service_region: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.provider not in ["local_whisper", "google_speech", "azure_speech"]:
            raise ValueError(f"Invalid transcription provider: {self.provider}")
        
        if self.whisper_model_size not in ["tiny", "base", "small", "medium", "large"]:
            raise ValueError(f"Invalid Whisper model size: {self.whisper_model_size}")

@dataclass
class AIProviderConfig:
    type: str
    model: str = "gpt-4"
    azure_openai: Optional[Dict[str, str]] = None
    openai: Optional[Dict[str, str]] = None
    google_gemini: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        """Validate AI provider configuration"""
        valid_types = ["azure_openai", "openai", "google_gemini"]
        if self.type not in valid_types:
            raise ValueError(f"Invalid AI provider type: {self.type}")

@dataclass
class AudioConfig:
    mode: str = "dual_stream"
    sample_rate: int = 44100
    chunk_size: int = 1024
    channels: int = 1
    buffer_duration_minutes: int = 5
    transcript_segments_max: int = 50
    silence_threshold_seconds: int = 30
    processing_interval_seconds: float = 1.6
    max_queue_size: int = 100  # Added for memory management
    
    def __post_init__(self):
        """Validate audio configuration"""
        if self.mode not in ["dual_stream", "single_stream"]:
            raise ValueError(f"Invalid audio mode: {self.mode}")
        
        if self.sample_rate not in [22050, 44100, 48000]:
            raise ValueError(f"Unsupported sample rate: {self.sample_rate}")
        
        if self.chunk_size not in [512, 1024, 2048, 4096]:
            raise ValueError(f"Invalid chunk size: {self.chunk_size}")

@dataclass
class DebugConfig:
    enabled: bool = False
    save_audio_chunks: bool = False
    save_transcriptions: bool = False
    verbose_logging: bool = False
    audio_chunk_format: str = "wav"  # wav or raw
    max_debug_files: int = 100  # Limit number of debug files
    performance_monitoring: bool = False  # Added for performance tracking

@dataclass
class AssistantConfig:
    activation_mode: str = "manual"  # auto, manual
    verbosity: str = "standard"  # concise, standard, detailed
    auto_hide_behavior: str = "timer"  # timer, manual, never
    input_prioritization: str = "system_audio"  # mic, system_audio, balanced
    response_style: str = "professional"  # professional, casual, technical

@dataclass
class UIConfig:
    overlay: Dict[str, Any]
    stealth_mode: Dict[str, bool]

@dataclass
class HotkeysConfig:
    trigger_assistance: str = "ctrl+space"
    take_screenshot: str = "ctrl+h"
    toggle_overlay: str = "ctrl+b"
    move_left: str = "alt+left"
    move_right: str = "alt+right"
    move_up: str = "alt+up"
    move_down: str = "alt+down"
    emergency_reset: str = "ctrl+shift+r"

class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = None
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            self._create_default_config()
        
        with open(self.config_path, 'r') as file:
            self._config = yaml.safe_load(file)
    
    def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            'ai_provider': {
                'type': 'azure_openai',
                'azure_openai': {
                    'endpoint': 'https://your-resource.openai.azure.com/',
                    'api_key': 'your-azure-openai-api-key-here',
                    'api_version': '2024-02-01',
                    'model': 'gpt-4',
                    'deployment_name': 'gpt-4'
                }
            },
            'transcription': {
                'provider': 'local_whisper',
                'whisper': {
                    'model_size': 'base',
                    'language': 'en'
                }
            },
            'assistant': {
                'activation_mode': 'manual',
                'verbosity': 'standard',
                'auto_hide_behavior': 'timer',
                'input_prioritization': 'system_audio',
                'response_style': 'professional'
            },
            'audio': {
                'mode': 'dual_stream',
                'sample_rate': 44100,
                'processing_interval_seconds': 1.6
            },
            'ui': {
                'overlay': {
                    'size_multiplier': 1.0,
                    'show_transcript': False,
                    'auto_hide_seconds': 5
                }
            }
        }
        
        with open(self.config_path, 'w') as file:
            yaml.dump(default_config, file, default_flow_style=False)
    
    def get_transcription_config(self) -> TranscriptionConfig:
        """Get transcription configuration"""
        transcription_config = self._config.get('transcription', {})
        
        # Get provider from config
        provider = transcription_config.get('provider', 'local_whisper')
        
        # Get Whisper settings
        whisper_config = transcription_config.get('whisper', {})
        whisper_model_size = whisper_config.get('model_size', 'base')
        
        # Get Google Speech settings
        google_config = transcription_config.get('google_speech', {})
        google_language = google_config.get('language', 'en-US')
        google_credentials = google_config.get('credentials_path')
        
        # Get Azure Speech settings
        azure_config = transcription_config.get('azure_speech', {})
        azure_language = azure_config.get('language', 'en-US')
        azure_key = azure_config.get('subscription_key')
        azure_region = azure_config.get('service_region')
        
        return TranscriptionConfig(
            provider=provider,
            whisper_model_size=whisper_model_size,
            google_language=google_language,
            azure_language=azure_language,
            google_credentials_path=google_credentials,
            azure_subscription_key=azure_key,
            azure_service_region=azure_region
        )
    
    def get_assistant_config(self) -> AssistantConfig:
        """Get MeetMinder configuration"""
        assistant_config = self._config.get('assistant', {})
        return AssistantConfig(**assistant_config)
    
    def get_ai_config(self) -> AIProviderConfig:
        """Get AI provider configuration"""
        ai_config = self._config.get('ai_provider', {})
        
        return AIProviderConfig(
            type=ai_config.get('type', 'azure_openai'),
            azure_openai=ai_config.get('azure_openai'),
            openai=ai_config.get('openai'),
            google_gemini=ai_config.get('google_gemini')
        )
    
    def get_audio_config(self) -> AudioConfig:
        """Get audio configuration"""
        audio_config = self._config.get('audio', {})
        
        return AudioConfig(
            mode=audio_config.get('mode', 'dual_stream'),
            sample_rate=audio_config.get('sample_rate', 44100),
            chunk_size=audio_config.get('chunk_size', 1024),
            channels=audio_config.get('channels', 1),
            buffer_duration_minutes=audio_config.get('buffer_duration_minutes', 5),
            transcript_segments_max=audio_config.get('transcript_segments_max', 50),
            silence_threshold_seconds=audio_config.get('silence_threshold_seconds', 30),
            processing_interval_seconds=audio_config.get('processing_interval_seconds', 1.6)
        )
    
    def get_debug_config(self) -> DebugConfig:
        """Get debug configuration"""
        debug_config = self._config.get('debug', {})
        
        return DebugConfig(
            enabled=debug_config.get('enabled', False),
            save_audio_chunks=debug_config.get('save_audio_chunks', False),
            save_transcriptions=debug_config.get('save_transcriptions', False),
            verbose_logging=debug_config.get('verbose_logging', False),
            audio_chunk_format=debug_config.get('audio_chunk_format', 'wav'),
            max_debug_files=debug_config.get('max_debug_files', 100),
            performance_monitoring=debug_config.get('performance_monitoring', False)
        )
    
    def get_hotkeys_config(self) -> HotkeysConfig:
        """Get hotkeys configuration"""
        hotkeys_config = self._config.get('hotkeys', {})
        
        return HotkeysConfig(
            trigger_assistance=hotkeys_config.get('trigger_assistance', 'ctrl+space'),
            take_screenshot=hotkeys_config.get('take_screenshot', 'ctrl+h'),
            toggle_overlay=hotkeys_config.get('toggle_overlay', 'ctrl+b'),
            move_left=hotkeys_config.get('move_left', 'alt+left'),
            move_right=hotkeys_config.get('move_right', 'alt+right'),
            move_up=hotkeys_config.get('move_up', 'alt+up'),
            move_down=hotkeys_config.get('move_down', 'alt+down'),
            emergency_reset=hotkeys_config.get('emergency_reset', 'ctrl+shift+r')
        )
    
    def get(self, key: str, default=None):
        """Get configuration value by key (supports dot notation)"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def load_prompt_rules(self) -> str:
        """Load prompt rules from prompt_rules.md file"""
        try:
            prompt_file = Path("prompt_rules.md")
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                # Return default prompt if file doesn't exist
                return """You are an intelligent AI meeting assistant designed to provide helpful, contextual responses based on real-time audio transcription and user interactions.

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

**Meeting-Specific Expertise:**
- Meeting facilitation and note-taking
- Technical problem-solving
- Project management insights
- Communication enhancement
- General productivity tips"""
        except Exception as e:
            print(f"⚠️ Error loading prompt rules: {e}")
            return "You are a helpful AI meeting assistant."
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update configuration with new values"""
        def deep_merge(base_dict, update_dict):
            """Deep merge two dictionaries"""
            for key, value in update_dict.items():
                if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                    deep_merge(base_dict[key], value)
                else:
                    base_dict[key] = value
        
        deep_merge(self._config, new_config)
    
    def save_config(self):
        """Save current configuration to file"""
        with open(self.config_path, 'w') as file:
            yaml.dump(self._config, file, default_flow_style=False) 