import sounddevice as sd
import numpy as np
import whisper
import threading
import queue
import time
from collections import deque
from typing import List, Callable, Dict, Any
from core.config import AudioConfig
from .wasapi_system_audio import WASAPISystemAudioCapture

class DualStreamAudioContextualizer:
    """
    Dual-stream audio processor that separates:
    - Microphone input (your voice) via sounddevice
    - System audio (meetings, videos, etc.) via PyAudioWPatch WASAPI loopback
    """
    
    def __init__(self, config: AudioConfig, topic_manager=None, whisper_model=None, whisper_language="en"):
        self.config = config
        self.topic_manager = topic_manager
        self.is_recording = False
        
        # Store Whisper model and language (use lazy loading for better performance)
        self.whisper_model = whisper_model
        self.whisper_language = whisper_language
        
        # Debug configuration
        self.debug_config = {
            'enabled': False,
            'save_audio_chunks': False,
            'verbose_logging': False,
            'save_transcriptions': False,
            'audio_chunk_format': 'wav',
            'max_debug_files': 100
        }
        
        # Load debug config from ConfigManager if available
        try:
            from core.config import ConfigManager
            full_config = ConfigManager()
            debug_config = full_config.get_debug_config()
            self.debug_config.update({
                'enabled': debug_config.enabled,
                'save_audio_chunks': debug_config.save_audio_chunks,
                'verbose_logging': debug_config.verbose_logging,
                'save_transcriptions': debug_config.save_transcriptions,
                'audio_chunk_format': debug_config.audio_chunk_format,
                'max_debug_files': debug_config.max_debug_files
            })
            if self.debug_config['enabled']:
                print(f"🐞 Debug mode enabled: chunks={self.debug_config['save_audio_chunks']}, verbose={self.debug_config['verbose_logging']}")
        except Exception as e:
            if self.debug_config['verbose_logging']:
                print(f"⚠️  Could not load debug config: {e}")
        
        # Load thresholds from config (if available) or use defaults
        self.microphone_threshold = getattr(config, 'microphone_threshold', 0.01)
        self.system_audio_threshold = getattr(config, 'system_audio_threshold', 0.001)  # Lowered for YouTube
        
        # Try to get thresholds from config manager if config object doesn't have them
        try:
            from core.config import ConfigManager
            full_config = ConfigManager()
            self.microphone_threshold = full_config.get('audio.dual_stream.microphone_threshold', 0.01)
            self.system_audio_threshold = full_config.get('audio.dual_stream.system_audio_threshold', 0.001)
            print(f"✓ Using thresholds - Mic: {self.microphone_threshold}, System: {self.system_audio_threshold}")
        except:
            print(f"⚠️  Using default thresholds - Mic: {self.microphone_threshold}, System: {self.system_audio_threshold}")
        
        # Separate buffers for each stream
        buffer_size = int(config.buffer_duration_minutes * 60)
        self.microphone_buffer = deque(maxlen=buffer_size)
        self.system_audio_buffer = deque(maxlen=buffer_size)
        
        # Separate transcript buffers
        self.microphone_transcript = deque(maxlen=config.transcript_segments_max)
        self.system_transcript = deque(maxlen=config.transcript_segments_max)
        
        # Audio queues for processing
        self.mic_queue = queue.Queue()
        self.system_queue = queue.Queue()
        
        # Load Whisper model if not provided
        if not self.whisper_model:
            # Use lazy loading to save memory at startup
            self.whisper_model = None
            print(f"✓ Configured for lazy Whisper model loading (saves ~500MB at startup)")
        else:
            print(f"✓ Using pre-loaded Whisper model for dual-stream processing")
        
        # Audio streams
        self.mic_stream = None
        self.system_audio_capture = None
        
        # Timing
        self.last_mic_time = time.time()
        self.last_system_time = time.time()
        
        # Callbacks
        self.context_change_callbacks = []
        
        # Initialize system audio capture
        self._init_system_audio()
    
    def _get_whisper_model(self):
        """Get Whisper model using lazy loading"""
        if self.whisper_model is None:
            try:
                # Try to get from memory manager's lazy loader first
                from utils.memory_manager import memory_manager
                lazy_model = memory_manager.get_lazy_resource("whisper_model")
                if lazy_model:
                    self.whisper_model = lazy_model
                    print(f"✓ Loaded Whisper model via lazy loading for dual-stream")
                else:
                    # Fallback to direct loading
                    try:
                        from core.config import ConfigManager
                        full_config = ConfigManager()
                        model_size = full_config.get('speech_to_text.whisper.model_size', 'small')
                    except:
                        model_size = 'small'  # Default to small for better accuracy
                    
                    import whisper
                    self.whisper_model = whisper.load_model(model_size)
                    print(f"✓ Loaded Whisper model '{model_size}' (fallback)")
            except Exception as e:
                print(f"❌ Error loading Whisper model: {e}")
                return None
        return self.whisper_model
    
    def update_debug_config(self, new_debug_config: Dict[str, Any]):
        """Update debug configuration at runtime"""
        self.debug_config.update(new_debug_config)
        print(f"🐞 Debug config updated: {self.debug_config}")
        
        # Create debug directories if needed
        if self.debug_config['save_audio_chunks'] or self.debug_config['save_transcriptions']:
            import os
            os.makedirs("debug_logs/audio_chunks", exist_ok=True)
            os.makedirs("debug_logs/transcriptions", exist_ok=True)
            print("📁 Created debug directories")
    
    def _save_debug_audio_chunk(self, audio_data: np.ndarray, source: str, volume: float = None):
        """Save audio chunk to debug directory if debug mode is enabled"""
        if not self.debug_config['save_audio_chunks']:
            return
            
        try:
            import os
            import soundfile as sf
            from datetime import datetime
            
            # Create debug directory
            debug_dir = "debug_logs/audio_chunks"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Generate filename with timestamp and volume
            timestamp = datetime.now().strftime("%H%M%S")
            volume_str = f"_vol{volume:.3f}" if volume is not None else ""
            filename = f"{source}_{timestamp}{volume_str}.{self.debug_config['audio_chunk_format']}"
            filepath = os.path.join(debug_dir, filename)
            
            # Save audio file
            if self.debug_config['audio_chunk_format'] == 'wav':
                sf.write(filepath, audio_data, self.config.sample_rate)
            else:
                # Save as raw numpy array
                np.save(filepath.replace('.wav', '.npy'), audio_data)
            
            if self.debug_config['verbose_logging']:
                print(f"💾 DEBUG: Saved audio chunk to {filepath}")
                
            # Clean up old files if we have too many
            self._cleanup_debug_files(debug_dir)
            
        except Exception as e:
            if self.debug_config['verbose_logging']:
                print(f"❌ Error saving debug audio chunk: {e}")
    
    def _cleanup_debug_files(self, debug_dir: str):
        """Clean up old debug files to prevent disk space issues"""
        try:
            import os
            import glob
            
            # Get all debug files
            pattern = os.path.join(debug_dir, "*.*")
            files = glob.glob(pattern)
            
            # If we have too many files, remove the oldest ones
            if len(files) > self.debug_config['max_debug_files']:
                # Sort by modification time
                files.sort(key=os.path.getmtime)
                
                # Remove oldest files
                files_to_remove = files[:-self.debug_config['max_debug_files']]
                for file_path in files_to_remove:
                    os.remove(file_path)
                    
                if self.debug_config['verbose_logging']:
                    print(f"🧹 Cleaned up {len(files_to_remove)} old debug files")
                    
        except Exception as e:
            if self.debug_config['verbose_logging']:
                print(f"❌ Error cleaning up debug files: {e}")
    
    def _init_system_audio(self):
        """Initialize PyAudioWPatch system audio capture"""
        try:
            self.system_audio_capture = WASAPISystemAudioCapture(
                sample_rate=self.config.sample_rate,
                chunk_size=self.config.chunk_size
            )
            
            # Add callback for system audio
            self.system_audio_capture.add_callback(self._system_audio_callback)
            
            if self.system_audio_capture.is_available():
                device_info = self.system_audio_capture.get_device_info()
                print(f"✓ System audio capture ready: {device_info['name']}")
                print(f"🔍 AUDIO DEBUG: Device details:")
                print(f"    📱 Name: {device_info['name']}")
                print(f"    🎵 Sample Rate: {device_info['defaultSampleRate']}Hz")
                print(f"    📊 Max Input Channels: {device_info['maxInputChannels']}")
                print(f"    🎤 This device captures ALL system audio (speakers output)")
                print(f"    💡 Any audio playing through your speakers will be captured")
                
                # Save device info to debug log
                import os
                os.makedirs("debug_logs", exist_ok=True)
                with open("debug_logs/audio_device_info.txt", 'w', encoding='utf-8') as f:
                    f.write(f"Audio Device Information:\n")
                    f.write(f"Name: {device_info['name']}\n")
                    f.write(f"Sample Rate: {device_info['defaultSampleRate']}Hz\n")
                    f.write(f"Max Input Channels: {device_info['maxInputChannels']}\n")
                    f.write(f"Type: WASAPI Loopback (System Audio)\n")
                    f.write(f"Captures: All audio playing through speakers\n")
                
            else:
                print("⚠️  System audio capture not available")
                print("💡 This means no system audio will be captured")
                
        except Exception as e:
            print(f"❌ Error initializing system audio: {e}")
            print(f"🔍 DEBUG: Full error details:")
            import traceback
            traceback.print_exc()
            self.system_audio_capture = None
    
    def _system_audio_callback(self, audio_data: np.ndarray, timestamp: float):
        """Callback for system audio from PyAudioWPatch"""
        # Check for actual audio content using configurable threshold
        max_volume = np.max(np.abs(audio_data))
        
        if self.debug_config['verbose_logging'] and max_volume > 0.0001:
            print(f"🔊 SYSTEM AUDIO: volume={max_volume:.4f}, threshold={self.system_audio_threshold:.4f}")
        
        if max_volume > self.system_audio_threshold:
            self.last_system_time = timestamp
            self.system_queue.put(audio_data.copy())
            
            # Save debug audio chunk
            self._save_debug_audio_chunk(audio_data, "system", max_volume)
            
            if self.debug_config['verbose_logging']:
                print(f"✅ System audio queued: volume={max_volume:.4f}")
        elif max_volume > 0.0001 and self.debug_config['verbose_logging']:
            print(f"📊 System audio detected but below threshold: {max_volume:.4f} < {self.system_audio_threshold:.4f}")
    
    def add_context_change_callback(self, callback: Callable):
        """Add callback for when context changes are detected"""
        self.context_change_callbacks.append(callback)
    
    def start_continuous_capture(self):
        """Start dual-stream audio capture"""
        if not self._get_whisper_model():
            print("Cannot start audio capture: Whisper model not loaded")
            return
            
        self.is_recording = True
        
        # Start microphone capture
        threading.Thread(target=self._start_microphone_capture, daemon=True).start()
        
        # Start system audio capture (PyAudioWPatch)
        if self.system_audio_capture and self.system_audio_capture.is_available():
            if self.system_audio_capture.start_capture():
                print("✓ Started PyAudioWPatch system audio capture")
            else:
                print("❌ Failed to start system audio capture")
        else:
            print("⚠️  System audio capture not available - using microphone only")
        
        # Start processing threads
        threading.Thread(target=self._process_microphone_audio, daemon=True).start()
        threading.Thread(target=self._process_system_audio, daemon=True).start()
        
        # Start analysis threads
        threading.Thread(target=self._audio_analysis_loop, daemon=True).start()
        threading.Thread(target=self._silence_detection_loop, daemon=True).start()
        
        print("✓ Started dual-stream audio capture")
    
    def _mic_callback(self, indata, frames, time_info, status):
        """Callback for microphone audio"""
        if status:
            print(f"🎤 Microphone status: {status}")
        
        audio_data = indata[:, 0] if indata.ndim > 1 else indata
        max_volume = np.max(np.abs(audio_data))
        
        # Debug microphone audio levels
        if self.debug_config['verbose_logging'] and max_volume > 0.0001:  # Show any detectable audio
            print(f"🎤 MIC AUDIO: volume={max_volume:.4f}, threshold={self.microphone_threshold:.4f}")
            if max_volume < self.microphone_threshold:
                print(f"⚠️  Audio below threshold - not processing")

        # Check for actual audio content using configurable threshold
        if max_volume > self.microphone_threshold:
            self.last_mic_time = time.time()
            self.mic_queue.put(audio_data.copy())
            
            # Save debug audio chunk
            self._save_debug_audio_chunk(audio_data, "microphone", max_volume)
            
            if self.debug_config['verbose_logging']:
                print(f"✅ Microphone audio queued: volume={max_volume:.4f}")
        elif max_volume > 0.001 and self.debug_config['verbose_logging']:  # Log near-threshold audio
            print(f"📊 Microphone audio detected but below threshold: {max_volume:.4f} < {self.microphone_threshold:.4f}")
    
    def _start_microphone_capture(self):
        """Start microphone audio capture"""
        try:
            print(f"🎤 Starting microphone with config: rate={self.config.sample_rate}Hz, channels=1, chunk_size={self.config.chunk_size}")
            
            # Check what device will be used
            import sounddevice as sd
            print(f"🎤 Default input device: {sd.default.device[0]}")
            device_info = sd.query_devices(sd.default.device[0])
            print(f"🎤 Device info: {device_info['name']} - Max input channels: {device_info['max_input_channels']}")
            print(f"🎤 Device default sample rate: {device_info['default_samplerate']}Hz")
            
            self.mic_stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=1,
                dtype='float32',
                callback=self._mic_callback,
                blocksize=self.config.chunk_size
            )
            self.mic_stream.start()
            print("✓ Microphone capture started")
            print(f"🎤 Actual stream settings: rate={self.mic_stream.samplerate}Hz, channels={self.mic_stream.channels}")
            
            # Keep the stream alive
            while self.is_recording:
                time.sleep(0.1)
                
        except Exception as e:
            print(f"❌ Failed to start microphone capture: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.mic_stream:
                self.mic_stream.stop()
                self.mic_stream.close()
    
    def _process_microphone_audio(self):
        """Process microphone audio stream"""
        buffer = []
        target_length = int(self.config.processing_interval_seconds * self.config.sample_rate)
        print(f"🎤 Microphone processor started - target length: {target_length} samples ({self.config.processing_interval_seconds}s at {self.config.sample_rate}Hz)")
        
        processing_count = 0
        last_status_time = time.time()
        
        while self.is_recording:
            try:
                # Collect audio data
                while len(buffer) < target_length and self.is_recording:
                    try:
                        data = self.mic_queue.get(timeout=0.1)
                        buffer.extend(data)
                        
                        # More frequent status updates
                        current_time = time.time()
                        if current_time - last_status_time > 2.0:  # Every 2 seconds
                            print(f"🎤 Buffer status: {len(buffer)}/{target_length} samples ({len(buffer)/target_length*100:.1f}%)")
                            print(f"🎤 Queue size: {self.mic_queue.qsize()} chunks pending")
                            last_status_time = current_time
                            
                    except queue.Empty:
                        continue
                
                if len(buffer) >= target_length:
                    processing_count += 1
                    # Process the audio
                    audio_segment = np.array(buffer[:target_length])
                    buffer = buffer[target_length:]
                    
                    max_volume = np.max(np.abs(audio_segment))
                    print(f"🎤 Processing microphone audio segment #{processing_count}: volume={max_volume:.4f}, length={len(audio_segment)}")
                    
                    # Transcribe directly - microphone is already at correct rate
                    transcript = self._transcribe_audio(audio_segment, "microphone")
                    if transcript:
                        print(f"🎤 Microphone transcription: '{transcript}'")
                        self.microphone_transcript.append({
                            'text': transcript,
                            'timestamp': time.time(),
                            'source': 'microphone',
                            'confidence': 0.8
                        })
                        
                        # Trigger callbacks for microphone input
                        self._trigger_context_change(f"user_voice: {transcript}")
                    else:
                        print(f"🎤 No transcript generated from microphone audio (volume: {max_volume:.4f})")
                        
            except Exception as e:
                print(f"❌ Error processing microphone audio: {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(0.1)
    
    def _process_system_audio(self):
        """Process system audio stream"""
        buffer = []
        target_length = int(self.config.processing_interval_seconds * self.config.sample_rate)
        
        while self.is_recording:
            try:
                # Collect audio data
                while len(buffer) < target_length and self.is_recording:
                    try:
                        data = self.system_queue.get(timeout=0.1)
                        buffer.extend(data)
                    except queue.Empty:
                        continue
                
                if len(buffer) >= target_length:
                    # Process the audio
                    audio_segment = np.array(buffer[:target_length])
                    buffer = buffer[target_length:]
                    
                    # NO RESAMPLING HERE - keep native 44100Hz to avoid distortion
                    # Whisper will handle the resampling internally via librosa
                    
                    # Transcribe directly with 44100Hz audio
                    transcript = self._transcribe_audio(audio_segment, "system")
                    if transcript:
                        self.system_transcript.append({
                            'text': transcript,
                            'timestamp': time.time(),
                            'source': 'system',
                            'confidence': 0.8
                        })
                        
                        # Trigger callbacks for system audio
                        self._trigger_context_change(f"system_audio: {transcript}")
                        
            except Exception as e:
                print(f"❌ Error processing system audio: {e}")
            
            time.sleep(0.1)
    
    def _transcribe_audio(self, audio_data: np.ndarray, source: str) -> str:
        """Transcribe audio using Whisper with librosa preprocessing"""
        try:
            # Ensure audio is in the right format for Whisper
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Whisper expects values between -1 and 1
            if np.max(np.abs(audio_data)) > 1.0:
                audio_data = audio_data / np.max(np.abs(audio_data))
            
            # Skip if audio is too quiet (use configurable threshold)
            threshold = self.system_audio_threshold if source == "system" else self.microphone_threshold
            max_volume = np.max(np.abs(audio_data))
            
            if max_volume < threshold:
                return ""
            
            # Debug info for system audio
            if source == "system":
                print(f"🔍 Transcribing {source} audio: volume={max_volume:.4f}, length={len(audio_data)}")
                
                # Save audio chunk for debugging
                import os
                import wave
                from datetime import datetime
                
                os.makedirs("debug_logs/audio_chunks", exist_ok=True)
                timestamp_str = datetime.now().strftime("%H%M%S")
                chunk_file = f"debug_logs/audio_chunks/system_{timestamp_str}_vol{max_volume:.3f}.wav"
                
                try:
                    # Save audio chunk as WAV for manual verification
                    audio_normalized = audio_data / np.max(np.abs(audio_data)) if np.max(np.abs(audio_data)) > 0 else audio_data
                    audio_int16 = (audio_normalized * 32767).astype(np.int16)
                    
                    with wave.open(chunk_file, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(16000)  # Use 16kHz for consistency
                        wav_file.writeframes(audio_int16.tobytes())
                    
                    print(f"💾 DEBUG: Saved audio chunk to {chunk_file}")
                except Exception as e:
                    print(f"⚠️  Failed to save audio chunk: {e}")
            
            # Debug info for microphone audio
            elif source == "microphone":
                print(f"🔍 Transcribing {source} audio: volume={max_volume:.4f}, length={len(audio_data)}")
                
                # Save microphone audio chunk for debugging
                import os
                import wave
                from datetime import datetime
                
                os.makedirs("debug_logs/audio_chunks", exist_ok=True)
                timestamp_str = datetime.now().strftime("%H%M%S")
                chunk_file = f"debug_logs/audio_chunks/microphone_{timestamp_str}_vol{max_volume:.3f}.wav"
                
                try:
                    # Save audio chunk as WAV for manual verification
                    audio_normalized = audio_data / np.max(np.abs(audio_data)) if np.max(np.abs(audio_data)) > 0 else audio_data
                    audio_int16 = (audio_normalized * 32767).astype(np.int16)
                    
                    with wave.open(chunk_file, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(self.config.sample_rate)  # Use configured sample rate for mic
                        wav_file.writeframes(audio_int16.tobytes())
                    
                    print(f"💾 DEBUG: Saved microphone chunk to {chunk_file}")
                except Exception as e:
                    print(f"⚠️  Failed to save microphone audio chunk: {e}")
            
            # Use librosa for audio preprocessing (like our successful tests)
            try:
                import librosa
                
                # Resample to 16kHz using librosa (same as successful debug script method)
                if len(audio_data) > 0:
                    # Librosa expects audio in the right format (float32)
                    # Resample from 44100Hz to 16000Hz exactly like debug script
                    audio_16k = librosa.resample(audio_data, orig_sr=44100, target_sr=16000)
                    
                    # Transcribe the resampled audio with English language setting
                    result = self._get_whisper_model().transcribe(audio_16k, language=self.whisper_language)
                    text = result['text'].strip()
                    
                    # Debug transcription result
                    if source == "system" and text:
                        confidence = result.get('confidence', 'unknown')
                        print(f"🎯 Whisper result ({source}): '{text}' (confidence: {confidence})")
                        
                        # Additional debugging for suspicious transcriptions
                        suspicious_chars = ['醒', 'кра', 'Fugiao', 'forady', '245', 'bruises']
                        if any(char in text for char in suspicious_chars):
                            print(f"🚨 SUSPICIOUS TRANSCRIPTION DETECTED!")
                            print(f"    📝 Text: '{text}'")
                            print(f"    📊 Audio volume: {max_volume:.4f}")
                            print(f"    📏 Audio length: {len(audio_data)} samples")
                            print(f"    🎤 Sample rate: 44100Hz (native WASAPI)")
                            print(f"    💾 Audio saved to: {chunk_file if 'chunk_file' in locals() else 'N/A'}")
                            print(f"    💡 Please check if this audio chunk matches what you're playing!")
                    
                    # Debug transcription result for microphone
                    elif source == "microphone" and text:
                        confidence = result.get('confidence', 'unknown')
                        print(f"🎯 Whisper result ({source}): '{text}' (confidence: {confidence})")
                        print(f"    📊 Audio volume: {max_volume:.4f}")
                        print(f"    📏 Audio length: {len(audio_data)} samples")
                        print(f"    🎤 Sample rate: {self.config.sample_rate}Hz")
                        print(f"    💾 Audio saved to: {chunk_file if 'chunk_file' in locals() else 'N/A'}")
                    
                    # Log when no transcription is generated
                    elif not text:
                        print(f"⚠️  No transcription generated for {source} audio")
                        print(f"    📊 Audio volume: {max_volume:.4f}")
                        print(f"    📏 Audio length: {len(audio_data)} samples")
                        print(f"    🔍 Possible reasons: too quiet, no speech, or background noise")
                    
                    # Filter out very short or nonsensical transcriptions
                    if len(text) > 5 and not text.lower().startswith(('thank you', 'thanks for watching')):
                        return text
                    elif len(text) <= 5 and source == "system":
                        print(f"⚠️  Filtered out short transcript: '{text}'")
                        
                else:
                    print(f"⚠️  Empty audio data for {source}")
                
            except ImportError:
                print(f"❌ Librosa not available, falling back to direct transcription")
                # Fallback to direct transcription without librosa with English language
                result = self._get_whisper_model().transcribe(audio_data, language=self.whisper_language)
                text = result['text'].strip()
                
                if len(text) > 5:
                    return text
                        
        except Exception as e:
            print(f"❌ Transcription error ({source}): {e}")
            import traceback
            traceback.print_exc()
        
        return ""
    
    def _resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Simple resampling for audio data"""
        if orig_sr == target_sr:
            return audio
        
        # Simple decimation/interpolation
        factor = target_sr / orig_sr
        new_length = int(len(audio) * factor)
        
        # Use numpy interpolation for simplicity
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio)
    
    def _audio_analysis_loop(self):
        """Analyze audio patterns and context"""
        while self.is_recording:
            try:
                # Analyze conversation patterns
                self._analyze_conversation_patterns()
                
                # Check for topic matches
                if self.topic_manager:
                    self._analyze_topics()
                
            except Exception as e:
                print(f"❌ Error in audio analysis: {e}")
            
            time.sleep(5)  # Analyze every 5 seconds
    
    def _analyze_conversation_patterns(self):
        """Analyze patterns between microphone and system audio"""
        recent_time = time.time() - 30  # Last 30 seconds
        
        mic_recent = [t for t in self.microphone_transcript if t['timestamp'] > recent_time]
        sys_recent = [t for t in self.system_transcript if t['timestamp'] > recent_time]
        
        # Detect meeting vs solo mode
        if len(sys_recent) > 0 and len(mic_recent) > 0:
            # Active conversation detected
            self._trigger_context_change("meeting_mode_active")
        elif len(sys_recent) > 0 and len(mic_recent) == 0:
            # Listening to content (YouTube, etc.)
            self._trigger_context_change("content_consumption_mode")
        elif len(mic_recent) > 0 and len(sys_recent) == 0:
            # Solo speaking (recording, notes, etc.)
            self._trigger_context_change("solo_recording_mode")
    
    def _analyze_topics(self):
        """Analyze topics from both streams"""
        recent_time = time.time() - 60  # Last minute
        
        all_recent = []
        all_recent.extend([t['text'] for t in self.microphone_transcript if t['timestamp'] > recent_time])
        all_recent.extend([t['text'] for t in self.system_transcript if t['timestamp'] > recent_time])
        
        if all_recent:
            combined_text = " ".join(all_recent)
            matches = self.topic_manager.match_topics(combined_text)
            if matches:
                self._trigger_context_change(f"topics_detected: {[m.topic for m in matches[:3]]}")
    
    def _silence_detection_loop(self):
        """Detect silence periods for context switching"""
        while self.is_recording:
            current_time = time.time()
            mic_silence = current_time - self.last_mic_time
            sys_silence = current_time - self.last_system_time
            
            # Solo mode if both streams are quiet
            if mic_silence > 30 and sys_silence > 30:
                self._trigger_context_change("complete_silence_mode")
                time.sleep(20)  # Wait before checking again
            else:
                time.sleep(5)
    
    def _trigger_context_change(self, context: str):
        """Notify all registered callbacks of context change"""
        for callback in self.context_change_callbacks:
            callback(context)
    
    def get_recent_transcript(self, minutes: int = 5, source: str = "both") -> List[str]:
        """Get transcript from specified source(s)"""
        cutoff_time = time.time() - (minutes * 60)
        
        if source == "microphone":
            return [entry['text'] for entry in self.microphone_transcript 
                   if entry['timestamp'] > cutoff_time]
        elif source == "system":
            return [entry['text'] for entry in self.system_transcript 
                   if entry['timestamp'] > cutoff_time]
        else:  # both
            combined = []
            for entry in self.microphone_transcript:
                if entry['timestamp'] > cutoff_time:
                    combined.append(f"[USER] {entry['text']}")
            for entry in self.system_transcript:
                if entry['timestamp'] > cutoff_time:
                    combined.append(f"[SYSTEM] {entry['text']}")
            
            # Sort by timestamp
            all_entries = list(self.microphone_transcript) + list(self.system_transcript)
            recent_entries = [e for e in all_entries if e['timestamp'] > cutoff_time]
            recent_entries.sort(key=lambda x: x['timestamp'])
            
            return [f"[{entry['source'].upper()}] {entry['text']}" for entry in recent_entries]
    
    def get_recent_transcript_with_topics(self, minutes: int = 5) -> dict:
        """Get combined transcript with topic analysis"""
        transcript = self.get_recent_transcript(minutes, "both")
        result = {
            'transcript': transcript,
            'microphone_transcript': self.get_recent_transcript(minutes, "microphone"),
            'system_transcript': self.get_recent_transcript(minutes, "system"),
            'topic_matches': [],
            'new_topics': [],
            'conversation_mode': self._detect_conversation_mode()
        }
        
        if self.topic_manager and transcript:
            recent_text = " ".join([t.split('] ', 1)[1] for t in transcript if '] ' in t])
            result['topic_matches'] = self.topic_manager.match_topics(recent_text)
            result['new_topics'] = self.topic_manager.detect_new_topics(recent_text)
        
        return result
    
    def _detect_conversation_mode(self) -> str:
        """Detect current conversation mode"""
        recent_time = time.time() - 30
        
        mic_count = len([t for t in self.microphone_transcript if t['timestamp'] > recent_time])
        sys_count = len([t for t in self.system_transcript if t['timestamp'] > recent_time])
        
        if mic_count > 0 and sys_count > 0:
            return "meeting"
        elif mic_count > 0 and sys_count == 0:
            return "solo_speaking"
        elif mic_count == 0 and sys_count > 0:
            return "listening"
        else:
            return "silent"
    
    def stop(self):
        """Stop all audio processing"""
        self.is_recording = False
        
        if self.mic_stream:
            self.mic_stream.stop()
            self.mic_stream.close()
            
        if self.system_audio_capture:
            self.system_audio_capture.cleanup()
            
        print("✓ Stopped dual-stream audio capture") 