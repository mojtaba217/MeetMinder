import numpy as np
import asyncio
import threading
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from core.config import TranscriptionConfig

class TranscriptionEngine(ABC):
    """Abstract base class for transcription engines"""
    
    @abstractmethod
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio data to text"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the transcription engine is available"""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get information about the transcription engine"""
        pass

class WhisperLocalEngine(TranscriptionEngine):
    """Local Whisper transcription engine"""
    
    def __init__(self, config: TranscriptionConfig):
        self.config = config
        self.model = None
        self.language = "en"
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model"""
        try:
            import whisper
            self.model = whisper.load_model(self.config.whisper_model_size)
            print(f"✅ Loaded Whisper model: {self.config.whisper_model_size}")
        except ImportError:
            print("[ERROR] Whisper not installed. Install with: pip install openai-whisper")
            self.model = None
        except Exception as e:
            print(f"[ERROR] Failed to load Whisper model: {e}")
            self.model = None
    
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio using local Whisper"""
        if not self.model:
            return ""
        
        try:
            # Ensure audio is in the right format
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Normalize audio
            if np.max(np.abs(audio_data)) > 1.0:
                audio_data = audio_data / np.max(np.abs(audio_data))
            
            # Resample if needed using librosa
            if sample_rate != 16000:
                try:
                    import librosa
                    audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
                except ImportError:
                    print("⚠️  Librosa not available for resampling")
            
            # Transcribe
            result = self.model.transcribe(audio_data, language=self.language)
            return result['text'].strip()
            
        except Exception as e:
            print(f"[ERROR] Whisper transcription error: {e}")
            return ""
    
    def is_available(self) -> bool:
        """Check if Whisper is available"""
        return self.model is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Get Whisper engine information"""
        return {
            'engine': 'whisper_local',
            'model_size': self.config.whisper_model_size,
            'language': self.language,
            'available': self.is_available()
        }

class GoogleSpeechEngine(TranscriptionEngine):
    """Google Speech-to-Text transcription engine"""
    
    def __init__(self, config: TranscriptionConfig):
        self.config = config
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup Google Speech client"""
        try:
            from google.cloud import speech
            import os
            
            # Set credentials if provided
            if self.config.google_credentials_path:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config.google_credentials_path
            
            self.client = speech.SpeechClient()
            print("✅ Google Speech-to-Text client initialized")
            
        except ImportError:
            print("[ERROR] Google Cloud Speech not installed. Install with: pip install google-cloud-speech")
            self.client = None
        except Exception as e:
            print(f"[ERROR] Failed to setup Google Speech client: {e}")
            self.client = None
    
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio using Google Speech-to-Text"""
        if not self.client:
            return ""
        
        try:
            from google.cloud import speech
            
            # Convert audio to bytes
            if audio_data.dtype != np.int16:
                # Convert float32 to int16
                audio_data = (audio_data * 32767).astype(np.int16)
            
            audio_bytes = audio_data.tobytes()
            
            # Configure recognition
            audio = speech.RecognitionAudio(content=audio_bytes)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code=self.config.google_language,
                enable_automatic_punctuation=True,
                model='latest_short'
            )
            
            # Perform recognition
            response = self.client.recognize(config=config, audio=audio)
            
            # Extract text
            if response.results:
                return response.results[0].alternatives[0].transcript.strip()
            
            return ""
            
        except Exception as e:
            print(f"[ERROR] Google Speech transcription error: {e}")
            return ""
    
    def is_available(self) -> bool:
        """Check if Google Speech is available"""
        return self.client is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Get Google Speech engine information"""
        return {
            'engine': 'google_speech',
            'language': self.config.google_language,
            'credentials_path': self.config.google_credentials_path,
            'available': self.is_available()
        }

class AzureSpeechEngine(TranscriptionEngine):
    """Azure Speech-to-Text transcription engine"""
    
    def __init__(self, config: TranscriptionConfig):
        self.config = config
        self.speech_config = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup Azure Speech client"""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            if not self.config.azure_subscription_key or not self.config.azure_service_region:
                print("[ERROR] Azure Speech credentials not configured")
                return
            
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.config.azure_subscription_key,
                region=self.config.azure_service_region
            )
            self.speech_config.speech_recognition_language = self.config.azure_language
            print("✅ Azure Speech-to-Text client initialized")
            
        except ImportError:
            print("[ERROR] Azure Speech SDK not installed. Install with: pip install azure-cognitiveservices-speech")
            self.speech_config = None
        except Exception as e:
            print(f"[ERROR] Failed to setup Azure Speech client: {e}")
            self.speech_config = None
    
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio using Azure Speech-to-Text"""
        if not self.speech_config:
            return ""
        
        try:
            import azure.cognitiveservices.speech as speechsdk
            import io
            import wave
            
            # Convert audio to WAV format in memory
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            
            wav_buffer.seek(0)
            
            # Create audio input stream
            audio_input = speechsdk.AudioInputStream(wav_buffer)
            audio_config = speechsdk.AudioConfig(stream=audio_input)
            
            # Create recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Perform recognition
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return result.text.strip()
            elif result.reason == speechsdk.ResultReason.NoMatch:
                return ""
            else:
                print(f"[ERROR] Azure Speech recognition failed: {result.reason}")
                return ""
                
        except Exception as e:
            print(f"[ERROR] Azure Speech transcription error: {e}")
            return ""
    
    def is_available(self) -> bool:
        """Check if Azure Speech is available"""
        return self.speech_config is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Get Azure Speech engine information"""
        return {
            'engine': 'azure_speech',
            'language': self.config.azure_language,
            'region': self.config.azure_service_region,
            'available': self.is_available()
        }

class TranscriptionEngineFactory:
    """Factory for creating transcription engines"""
    
    @staticmethod
    def create_engine(config: TranscriptionConfig) -> TranscriptionEngine:
        """Create a transcription engine based on configuration"""
        
        if config.provider == "local_whisper":
            return WhisperLocalEngine(config)
        elif config.provider == "google_speech":
            return GoogleSpeechEngine(config)
        elif config.provider == "azure_whisper":
            return AzureSpeechEngine(config)
        else:
            print(f"⚠️  Unknown transcription provider: {config.provider}, falling back to local Whisper")
            return WhisperLocalEngine(config)
    
    @staticmethod
    def get_available_engines(config: TranscriptionConfig) -> Dict[str, bool]:
        """Get availability status of all engines"""
        engines = {
            'local_whisper': WhisperLocalEngine(config).is_available(),
            'google_speech': GoogleSpeechEngine(config).is_available(),
            'azure_speech': AzureSpeechEngine(config).is_available()
        }
        return engines 