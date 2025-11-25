import pyaudio
import numpy as np
import whisper
import threading
from collections import deque
import time
from typing import List, Callable
from core.config import AudioConfig
from audio.vad_processor import VADProcessor
from audio.audio_preprocessor import AudioPreprocessor

class AudioContextualizer:
    def __init__(self, config: AudioConfig, topic_manager=None, whisper_model=None, whisper_language="en"):
        self.config = config
        self.topic_manager = topic_manager
        self.is_recording = False
        self.whisper_language = whisper_language
        
        # Configurable buffers
        buffer_size = int(config.buffer_duration_minutes * 60)
        self.audio_buffer = deque(maxlen=buffer_size)
        self.transcript_buffer = deque(maxlen=config.transcript_segments_max)
        
        # Load Whisper model based on config or use lazy loading for better performance
        if whisper_model:
            self.whisper_model = whisper_model
            print(f"[AUDIO] Using pre-loaded Whisper model (Language: {self.whisper_language})")
        else:
            # Use lazy loading to save memory at startup
            self.whisper_model = None
            print(f"[AUDIO] Configured for lazy Whisper model loading (saves ~500MB at startup)")
        
        # Initialize enhanced audio preprocessor
        noise_config = getattr(config, 'noise_reduction', {})
        self.preprocessor = AudioPreprocessor(
            sample_rate=16000,
            enable_spectral_subtraction=noise_config.get('spectral_subtraction', {}).get('enabled', True),
            enable_wiener_filter=noise_config.get('wiener_filtering', {}).get('enabled', True),
            enable_pre_emphasis=noise_config.get('pre_emphasis', {}).get('enabled', True),
            enable_multi_band_gate=noise_config.get('multi_band_gate', {}).get('enabled', True),
            noise_reduction_mode=noise_config.get('mode', 'aggressive')
        )
        print(f"[AUDIO] Enhanced audio preprocessor initialized (mode: {noise_config.get('mode', 'aggressive')})")
        
        # Initialize VAD processor
        vad_config = getattr(config, 'vad', {})
        if vad_config.get('enabled', True):
            self.vad_processor = VADProcessor(
                provider=vad_config.get('provider', 'webrtc'),
                aggressiveness=vad_config.get('aggressiveness', 2),
                sample_rate=16000,
                frame_duration_ms=vad_config.get('frame_duration_ms', 30),
                min_speech_duration_ms=vad_config.get('min_speech_duration_ms', 250),
                padding_duration_ms=vad_config.get('padding_duration_ms', 300)
            )
            print(f"[AUDIO] VAD processor initialized ({vad_config.get('provider', 'webrtc')})")
        else:
            self.vad_processor = None
            print("[AUDIO] VAD disabled")
        
        self.last_audio_time = time.time()
        self.context_change_callbacks = []
        self.noise_profile_built = False
    
    def _get_whisper_model(self):
        """Get Whisper model using lazy loading"""
        if self.whisper_model is None:
            try:
                # Try to get from memory manager's lazy loader first
                from utils.memory_manager import memory_manager
                lazy_model = memory_manager.get_lazy_resource("whisper_model")
                if lazy_model:
                    self.whisper_model = lazy_model
                    print(f"[SUCCESS] Loaded Whisper model via lazy loading")
                else:
                    # Fallback to direct loading
                    import whisper
                    self.whisper_model = whisper.load_model("base")
                    print(f"[SUCCESS] Loaded Whisper model (fallback)")
            except Exception as e:
                print(f"[ERROR] Error loading Whisper model: {e}")
                return None
        return self.whisper_model
    
    def add_context_change_callback(self, callback: Callable):
        """Add callback for when context changes are detected"""
        self.context_change_callbacks.append(callback)
    
    def start_continuous_capture(self):
        """Start continuous audio capture with configured parameters"""
        if not self._get_whisper_model():
            print("Cannot start audio capture: Whisper model not loaded")
            return
            
        self.is_recording = True
        
        # Audio capture thread
        threading.Thread(target=self._audio_capture_loop, daemon=True).start()
        
        # Processing thread
        threading.Thread(target=self._audio_processing_loop, daemon=True).start()
        
        # Silence detection thread
        threading.Thread(target=self._silence_detection_loop, daemon=True).start()
        
        print("[SUCCESS] Started audio capture")
        
    def _audio_capture_loop(self):
        """Capture audio using configured parameters"""
        try:
            p = pyaudio.PyAudio()
            
            stream = p.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size
            )
            
            while self.is_recording:
                try:
                    data = stream.read(self.config.chunk_size, exception_on_overflow=False)
                    audio_np = np.frombuffer(data, dtype=np.int16)
                    
                    # Check if there's actual audio (not silence)
                    if np.max(np.abs(audio_np)) > 500:
                        self.last_audio_time = time.time()
                        
                    self.audio_buffer.append(audio_np)
                    time.sleep(0.01)
                    
                except Exception as e:
                    print(f"Audio capture error: {e}")
                    
            stream.stop_stream()
            stream.close()
            p.terminate()
            
        except Exception as e:
            print(f"Failed to initialize audio: {e}")
    
    def _audio_processing_loop(self):
        """Process audio using configured interval with enhanced preprocessing and VAD"""
        processing_chunks = int(self.config.processing_interval_seconds * 
                              self.config.sample_rate / self.config.chunk_size)
        
        while self.is_recording:
            if len(self.audio_buffer) >= processing_chunks:
                # Get recent audio
                recent_audio = np.concatenate(list(self.audio_buffer)[-processing_chunks:])
                
                try:
                    # Convert to float32
                    audio_float = recent_audio.astype(np.float32) / 32768.0
                    
                    # Apply enhanced preprocessing
                    preprocessed_audio = self.preprocessor.preprocess(
                        audio_float,
                        original_sample_rate=self.config.sample_rate
                    )
                    
                    # Apply VAD filtering if enabled
                    if self.vad_processor:
                        filtered_audio, has_speech = self.vad_processor.filter_audio(preprocessed_audio)
                        
                        if not has_speech:
                            # No speech detected, skip transcription
                            time.sleep(self.config.processing_interval_seconds)
                            continue
                        
                        audio_to_transcribe = filtered_audio
                    else:
                        audio_to_transcribe = preprocessed_audio
                    
                    # Skip if audio too short after filtering
                    if len(audio_to_transcribe) < 16000:  # Less than 1 second at 16kHz
                        time.sleep(self.config.processing_interval_seconds)
                        continue
                    
                    # Transcribe using Whisper with language setting
                    result = self._get_whisper_model().transcribe(
                        audio_to_transcribe,
                        language=self.whisper_language
                    )
                    text = result['text'].strip()
                    
                    if text and len(text) > 5:
                        transcript_entry = {
                            'text': text,
                            'timestamp': time.time(),
                            'confidence': result.get('confidence', 0.5)
                        }
                        
                        self.transcript_buffer.append(transcript_entry)
                        
                        # Check for context changes
                        if self._detect_context_change(text):
                            self._trigger_context_change(text)
                        
                        # Check for topic matches
                        if self.topic_manager:
                            matches = self.topic_manager.match_topics(text)
                            if matches:
                                self._trigger_topic_detected(matches)
                            
                except Exception as e:
                    print(f"Transcription error: {e}")
                    
            time.sleep(self.config.processing_interval_seconds)
    
    def _silence_detection_loop(self):
        """Detect silence for solo work mode activation and noise profiling"""
        while self.is_recording:
            time_since_audio = time.time() - self.last_audio_time
            
            # Build noise profile during first silence period
            if not self.noise_profile_built and len(self.audio_buffer) > 10:
                try:
                    # Get a sample of recent audio (likely ambient noise)
                    noise_sample = np.concatenate(list(self.audio_buffer)[-10:])
                    noise_float = noise_sample.astype(np.float32) / 32768.0
                    
                    # Build noise profile
                    self.preprocessor.preprocess(
                        noise_float,
                        original_sample_rate=self.config.sample_rate,
                        is_noise_sample=True
                    )
                    self.noise_profile_built = True
                    print("[AUDIO] Initial noise profile built")
                except Exception as e:
                    print(f"[AUDIO] Error building noise profile: {e}")
            
            if time_since_audio > self.config.silence_threshold_seconds:
                # Trigger solo work mode
                for callback in self.context_change_callbacks:
                    callback("solo_mode_activated")
                    
                # Wait a bit before checking again
                time.sleep(10)
            else:
                time.sleep(5)
    
    def _detect_context_change(self, new_text: str) -> bool:
        """Detect context changes based on configurable indicators"""
        question_indicators = ['?', 'what', 'how', 'why', 'when', 'where', 'who']
        speaker_changes = ['hello', 'hi', 'okay', 'so', 'now', 'next']
        
        text_lower = new_text.lower()
        return any(indicator in text_lower for indicator in question_indicators + speaker_changes)
    
    def _trigger_context_change(self, text: str):
        """Notify all registered callbacks of context change"""
        for callback in self.context_change_callbacks:
            callback(f"context_change: {text}")
    
    def _trigger_topic_detected(self, matches):
        """Notify callbacks of topic detection"""
        for callback in self.context_change_callbacks:
            callback(f"topic_detected: {matches[0].topic}")
    
    def get_recent_transcript(self, minutes: int = 5) -> List[str]:
        """Get transcript from the last N minutes"""
        cutoff_time = time.time() - (minutes * 60)
        recent_entries = [
            entry['text'] for entry in self.transcript_buffer 
            if entry['timestamp'] > cutoff_time
        ]
        return recent_entries
    
    def get_recent_transcript_with_topics(self, minutes: int = 5) -> dict:
        """Get transcript with topic analysis"""
        transcript = self.get_recent_transcript(minutes)
        result = {
            'transcript': transcript,
            'topic_matches': [],
            'new_topics': []
        }
        
        if self.topic_manager and transcript:
            recent_text = " ".join(transcript)
            result['topic_matches'] = self.topic_manager.match_topics(recent_text)
            result['new_topics'] = self.topic_manager.detect_new_topics(recent_text)
        
        return result
    
    def stop(self):
        """Stop all audio processing"""
        self.is_recording = False
        print("[SUCCESS] Stopped audio capture") 