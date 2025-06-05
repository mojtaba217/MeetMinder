import pyaudiowpatch as pyaudio
import numpy as np
import threading
import queue
import time
from typing import Callable, Optional

class WASAPISystemAudioCapture:
    """
    System audio capture using PyAudioWPatch WASAPI loopback functionality.
    This handles only the system audio stream, not microphone.
    """
    
    def __init__(self, sample_rate: int = 44100, chunk_size: int = 1024, max_queue_size: int = 100):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.max_queue_size = max_queue_size
        self.is_recording = False
        
        # Audio processing with bounded queue to prevent memory leaks
        self.audio_queue = queue.Queue(maxsize=max_queue_size)
        self.callbacks = []
        
        # PyAudio instance and stream
        self.pyaudio_instance = None
        self.stream = None
        
        # Device info
        self.wasapi_info = None
        self.loopback_device = None
        
        # Performance monitoring
        self.dropped_frames = 0
        self.last_performance_log = time.time()
        
        self._discover_wasapi_loopback()
        
    def _discover_wasapi_loopback(self):
        """Discover WASAPI loopback device using PyAudioWPatch methods"""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Look for WASAPI loopback device using PyAudioWPatch helper methods
            try:
                # Try to get default WASAPI loopback device (new method in PyAudioWPatch)
                self.loopback_device = self.pyaudio_instance.get_default_wasapi_loopback()
                
                if self.loopback_device:
                    print(f"✓ Found default WASAPI loopback device: {self.loopback_device['name']}")
                    print(f"  Sample rate: {self.loopback_device['defaultSampleRate']}")
                    print(f"  Max input channels: {self.loopback_device['maxInputChannels']}")
                    return
                    
            except AttributeError:
                # Fallback for older versions of PyAudioWPatch
                print("Using fallback method to find loopback devices...")
            
            # Alternative approach: iterate through all devices to find loopback devices
            print("Searching for WASAPI loopback devices...")
            
            for i in range(self.pyaudio_instance.get_device_count()):
                device_info = self.pyaudio_instance.get_device_info_by_index(i)
                device_name = device_info['name'].lower()
                
                # Check if this is a loopback device
                # PyAudioWPatch creates loopback devices with specific naming patterns
                if ('loopback' in device_name or 
                    device_info['maxInputChannels'] > 0 and 
                    'wasapi' in str(device_info.get('hostApi', '')).lower()):
                    
                    # Check if this device has WASAPI as host API
                    host_api = self.pyaudio_instance.get_host_api_info_by_index(device_info['hostApi'])
                    if 'wasapi' in host_api['name'].lower():
                        self.loopback_device = device_info
                        print(f"✓ Found WASAPI loopback device: {device_info['name']}")
                        print(f"  Device #{i}: {device_info['name']}")
                        print(f"  Host API: {host_api['name']}")
                        print(f"  Sample rate: {device_info['defaultSampleRate']}")
                        print(f"  Max input channels: {device_info['maxInputChannels']}")
                        return
            
            # If no loopback device found, try to use get_default_output_device and look for its loopback analogue
            try:
                default_output = self.pyaudio_instance.get_default_output_device_info()
                print(f"Default output device: {default_output['name']}")
                
                # Look for a loopback version of the default output device
                for i in range(self.pyaudio_instance.get_device_count()):
                    device_info = self.pyaudio_instance.get_device_info_by_index(i)
                    
                    # Check if this device name contains the output device name (loopback version)
                    if (default_output['name'] in device_info['name'] and 
                        device_info['maxInputChannels'] > 0 and
                        device_info['index'] != default_output['index']):
                        
                        host_api = self.pyaudio_instance.get_host_api_info_by_index(device_info['hostApi'])
                        if 'wasapi' in host_api['name'].lower():
                            self.loopback_device = device_info
                            print(f"✓ Found loopback analogue: {device_info['name']}")
                            return
                            
            except Exception as e:
                print(f"Could not find loopback analogue: {e}")
            
            print("❌ No WASAPI loopback device found")
            print("💡 Make sure PyAudioWPatch is properly installed and WASAPI loopback is supported")
                
        except Exception as e:
            print(f"❌ Error initializing PyAudioWPatch WASAPI: {e}")
    
    def add_callback(self, callback: Callable[[np.ndarray, float], None]):
        """Add callback function that receives (audio_data, timestamp)"""
        self.callbacks.append(callback)
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for WASAPI loopback"""
        if status:
            print(f"WASAPI Status: {status}")
        
        # Convert bytes to numpy array
        try:
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            
            # Reshape to channels if stereo
            if self.loopback_device and self.loopback_device['maxInputChannels'] >= 2:
                audio_data = audio_data.reshape(-1, 2)
                # Convert to mono by averaging channels
                audio_data = np.mean(audio_data, axis=1)
            
            # Queue audio for processing
            if len(audio_data) > 0:
                self.audio_queue.put((audio_data.copy(), time.time()))
                
        except Exception as e:
            print(f"❌ Error in WASAPI callback: {e}")
        
        return (None, pyaudio.paContinue)
    
    def start_capture(self):
        """Start WASAPI loopback capture"""
        if not self.loopback_device or not self.pyaudio_instance:
            print("❌ Cannot start WASAPI capture: loopback device not available")
            return False
        
        try:
            # Determine sample rate
            device_rate = int(self.loopback_device['defaultSampleRate'])
            use_rate = device_rate if device_rate > 0 else self.sample_rate
            
            # Use the loopback device directly (no special parameters needed)
            self.stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=int(self.loopback_device['maxInputChannels']) or 2,
                rate=use_rate,
                input=True,
                input_device_index=self.loopback_device['index'],
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
                # NOTE: No as_loopback parameter needed - the device itself is already a loopback device
            )
            
            self.stream.start_stream()
            self.is_recording = True
            
            # Start processing thread
            threading.Thread(target=self._process_audio, daemon=True).start()
            
            print(f"✓ Started WASAPI loopback capture at {use_rate}Hz")
            print(f"  Device: {self.loopback_device['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start WASAPI capture: {e}")
            return False
    
    def _process_audio(self):
        """Process audio data from queue and trigger callbacks"""
        while self.is_recording:
            try:
                # Get audio data from queue
                audio_data, timestamp = self.audio_queue.get(timeout=0.1)
                
                # Trigger all callbacks
                for callback in self.callbacks:
                    try:
                        callback(audio_data, timestamp)
                    except Exception as e:
                        print(f"❌ Error in WASAPI callback: {e}")
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Error processing WASAPI audio: {e}")
    
    def stop_capture(self):
        """Stop WASAPI loopback capture"""
        self.is_recording = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"❌ Error stopping WASAPI stream: {e}")
        
        print("✓ Stopped WASAPI loopback capture")
    
    def cleanup(self):
        """Clean up PyAudio resources"""
        self.stop_capture()
        
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception as e:
                print(f"❌ Error terminating PyAudio: {e}")
    
    def get_device_info(self) -> Optional[dict]:
        """Get information about the WASAPI loopback device"""
        return self.loopback_device
    
    def is_available(self) -> bool:
        """Check if WASAPI loopback is available"""
        return self.loopback_device is not None and self.pyaudio_instance is not None
    
    def list_all_devices(self):
        """Debug method to list all available devices"""
        if not self.pyaudio_instance:
            print("PyAudio not initialized")
            return
            
        print("\n🔍 All Available Audio Devices:")
        print("=" * 60)
        
        for i in range(self.pyaudio_instance.get_device_count()):
            device_info = self.pyaudio_instance.get_device_info_by_index(i)
            host_api = self.pyaudio_instance.get_host_api_info_by_index(device_info['hostApi'])
            
            device_type = []
            if device_info['maxInputChannels'] > 0:
                device_type.append("input")
            if device_info['maxOutputChannels'] > 0:
                device_type.append("output")
            
            print(f"Device #{i}: {device_info['name']}")
            print(f"  Host API: {host_api['name']}")
            print(f"  Type: {', '.join(device_type) if device_type else 'none'}")
            print(f"  Sample Rate: {device_info['defaultSampleRate']}")
            print(f"  Input Channels: {device_info['maxInputChannels']}")
            print(f"  Output Channels: {device_info['maxOutputChannels']}")
            print("-" * 60) 