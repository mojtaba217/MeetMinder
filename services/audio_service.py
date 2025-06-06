"""
Audio Service abstraction layer for MeetMinder.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import logging
from dataclasses import dataclass

try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    import numpy as np
except ImportError:
    np = None

from utils.error_handler import AudioError, handle_errors

logger = logging.getLogger('meetminder.audio_service')


@dataclass
class AudioConfig:
    """Audio configuration data structure."""
    sample_rate: int = 44100
    channels: int = 1
    chunk_size: int = 1024
    device_index: Optional[int] = None


class AudioServiceInterface(ABC):
    """Interface for audio services."""
    
    @abstractmethod
    def start_recording(self, config: AudioConfig) -> bool:
        """Start audio recording."""
        pass
    
    @abstractmethod
    def stop_recording(self) -> bytes:
        """Stop recording and return audio data."""
        pass
    
    @abstractmethod
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio devices."""
        pass


class PyAudioService(AudioServiceInterface):
    """PyAudio-based audio service implementation."""
    
    def __init__(self):
        if pyaudio is None:
            raise ImportError("PyAudio library not installed. Install with: pip install pyaudio")
        self.audio = None
        self.stream = None
        self.frames = []
        self.is_recording = False
        self.logger = logger
    
    @handle_errors(fallback_return=False)
    def start_recording(self, config: AudioConfig) -> bool:
        """Start audio recording using PyAudio."""
        try:
            if self.is_recording:
                self.logger.warning("Recording already in progress")
                return False
            
            self.audio = pyaudio.PyAudio()
            self.frames = []
            
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=config.channels,
                rate=config.sample_rate,
                input=True,
                input_device_index=config.device_index,
                frames_per_buffer=config.chunk_size
            )
            
            self.is_recording = True
            self.logger.info(f"Started recording with config: {config}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            raise AudioError(f"Failed to start recording: {e}")
    
    @handle_errors(fallback_return=b"")
    def stop_recording(self) -> bytes:
        """Stop recording and return audio data."""
        try:
            if not self.is_recording:
                self.logger.warning("No recording in progress")
                return b""
            
            self.is_recording = False
            
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            
            if self.audio:
                self.audio.terminate()
            
            audio_data = b''.join(self.frames)
            self.frames = []
            
            self.logger.info(f"Stopped recording, captured {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Failed to stop recording: {e}")
            raise AudioError(f"Failed to stop recording: {e}")
    
    @handle_errors(fallback_return=[])
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices."""
        try:
            audio = pyaudio.PyAudio()
            devices = []
            
            for i in range(audio.get_device_count()):
                device_info = audio.get_device_info_by_index(i)
                if device_info["maxInputChannels"] > 0:
                    devices.append({
                        "index": i,
                        "name": device_info["name"],
                        "channels": device_info["maxInputChannels"],
                        "sample_rate": device_info["defaultSampleRate"]
                    })
            
            audio.terminate()
            self.logger.info(f"Found {len(devices)} audio input devices")
            return devices
            
        except Exception as e:
            self.logger.error(f"Failed to get audio devices: {e}")
            raise AudioError(f"Failed to get audio devices: {e}")
