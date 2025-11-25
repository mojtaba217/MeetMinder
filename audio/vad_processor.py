#!/usr/bin/env python3
"""
Voice Activity Detection (VAD) Processor
Filters out non-speech segments to improve transcription accuracy in noisy environments
"""

import numpy as np
from typing import Optional, Tuple
from enum import Enum


class VADProvider(Enum):
    """Available VAD providers"""
    WEBRTC = "webrtc"
    SILERO = "silero"
    ENERGY_BASED = "energy"  # Fallback if libraries unavailable


class VADProcessor:
    """
    Voice Activity Detection processor to filter non-speech audio
    """
    
    def __init__(
        self,
        provider: str = "webrtc",
        aggressiveness: int = 2,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        min_speech_duration_ms: int = 250,
        padding_duration_ms: int = 300
    ):
        """
        Initialize VAD processor
        
        Args:
            provider: VAD provider ('webrtc', 'silero', or 'energy')
            aggressiveness: How aggressive filtering is (0-3, higher = more aggressive)
            sample_rate: Audio sample rate (8000, 16000, 32000, or 48000 for WebRTC)
            frame_duration_ms: Frame duration in ms (10, 20, or 30 for WebRTC)
            min_speech_duration_ms: Minimum speech duration to consider valid
            padding_duration_ms: Padding around speech segments
        """
        self.provider_name = provider
        self.aggressiveness = aggressiveness
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.padding_duration_ms = padding_duration_ms
        
        # Calculate frame size
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.padding_frames = int(padding_duration_ms / frame_duration_ms)
        self.min_speech_frames = int(min_speech_duration_ms / frame_duration_ms)
        
        # Initialize provider
        self.vad = None
        self._init_provider()
        
    def _init_provider(self):
        """Initialize the VAD provider"""
        try:
            if self.provider_name == "webrtc":
                self._init_webrtc()
            elif self.provider_name == "silero":
                self._init_silero()
            else:
                print(f"[VAD] Using energy-based VAD (fallback)")
                self.provider_name = "energy"
        except Exception as e:
            print(f"[VAD] Failed to initialize {self.provider_name} VAD: {e}")
            print(f"[VAD] Falling back to energy-based VAD")
            self.provider_name = "energy"
    
    def _init_webrtc(self):
        """Initialize WebRTC VAD"""
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(self.aggressiveness)
            print(f"[VAD] Initialized WebRTC VAD (aggressiveness={self.aggressiveness})")
        except ImportError:
            print("[VAD] webrtcvad not installed. Install with: pip install webrtcvad")
            raise
    
    def _init_silero(self):
        """Initialize Silero VAD"""
        try:
            import torch
            # Load Silero VAD model
            self.vad, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            self.get_speech_timestamps = utils[0]
            print("[VAD] Initialized Silero VAD")
        except Exception as e:
            print(f"[VAD] Failed to load Silero VAD: {e}")
            raise
    
    def is_speech(self, audio_frame: np.ndarray) -> bool:
        """
        Check if audio frame contains speech
        
        Args:
            audio_frame: Audio data (should be frame_size samples)
            
        Returns:
            True if speech detected, False otherwise
        """
        if self.provider_name == "webrtc":
            return self._is_speech_webrtc(audio_frame)
        elif self.provider_name == "silero":
            return self._is_speech_silero(audio_frame)
        else:
            return self._is_speech_energy(audio_frame)
    
    def _is_speech_webrtc(self, audio_frame: np.ndarray) -> bool:
        """Check speech using WebRTC VAD"""
        try:
            # WebRTC requires int16 PCM
            if audio_frame.dtype != np.int16:
                audio_frame = (audio_frame * 32767).astype(np.int16)
            
            # Ensure correct frame size
            if len(audio_frame) != self.frame_size:
                return False
            
            return self.vad.is_speech(audio_frame.tobytes(), self.sample_rate)
        except Exception as e:
            print(f"[VAD] WebRTC error: {e}")
            return True  # Default to speech on error
    
    def _is_speech_silero(self, audio_frame: np.ndarray) -> bool:
        """Check speech using Silero VAD"""
        try:
            import torch
            
            # Silero requires float32 normalized audio
            if audio_frame.dtype != np.float32:
                audio_frame = audio_frame.astype(np.float32)
            
            # Normalize if needed
            if np.max(np.abs(audio_frame)) > 1.0:
                audio_frame = audio_frame / 32768.0
            
            # Convert to tensor
            audio_tensor = torch.from_numpy(audio_frame)
            
            # Get speech probability
            speech_prob = self.vad(audio_tensor, self.sample_rate).item()
            
            # Threshold based on aggressiveness
            threshold = 0.3 + (self.aggressiveness * 0.1)
            return speech_prob > threshold
            
        except Exception as e:
            print(f"[VAD] Silero error: {e}")
            return True  # Default to speech on error
    
    def _is_speech_energy(self, audio_frame: np.ndarray) -> bool:
        """Check speech using simple energy-based detection"""
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_frame ** 2))
        
        # Adaptive threshold based on aggressiveness
        threshold = 0.01 * (1.0 + self.aggressiveness * 0.5)
        
        return rms > threshold
    
    def filter_audio(self, audio_data: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Filter audio to keep only speech segments
        
        Args:
            audio_data: Input audio data (any length)
            
        Returns:
            Tuple of (filtered_audio, has_speech)
            - filtered_audio: Audio with only speech segments (may be shorter)
            - has_speech: True if any speech was detected
        """
        # Ensure float32
        if audio_data.dtype != np.float32:
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            else:
                audio_data = audio_data.astype(np.float32)
        
        # Split into frames
        num_frames = len(audio_data) // self.frame_size
        if num_frames == 0:
            return audio_data, False
        
        frames = []
        speech_flags = []
        
        for i in range(num_frames):
            start = i * self.frame_size
            end = start + self.frame_size
            frame = audio_data[start:end]
            
            if len(frame) == self.frame_size:
                frames.append(frame)
                speech_flags.append(self.is_speech(frame))
        
        # No frames processed
        if not speech_flags:
            return audio_data, False
        
        # Apply padding around speech segments
        padded_flags = self._apply_padding(speech_flags)
        
        # Check if there's enough continuous speech
        has_speech = self._has_sufficient_speech(padded_flags)
        
        if not has_speech:
            return np.array([], dtype=np.float32), False
        
        # Reconstruct audio with only speech frames
        speech_frames = [frame for frame, is_speech in zip(frames, padded_flags) if is_speech]
        
        if not speech_frames:
            return np.array([], dtype=np.float32), False
        
        filtered_audio = np.concatenate(speech_frames)
        return filtered_audio, True
    
    def _apply_padding(self, speech_flags: list) -> list:
        """Apply padding around speech segments"""
        padded = speech_flags.copy()
        
        # Find speech segments and add padding
        for i in range(len(speech_flags)):
            if speech_flags[i]:
                # Add padding before
                for j in range(max(0, i - self.padding_frames), i):
                    padded[j] = True
                
                # Add padding after
                for j in range(i + 1, min(len(speech_flags), i + self.padding_frames + 1)):
                    padded[j] = True
        
        return padded
    
    def _has_sufficient_speech(self, speech_flags: list) -> bool:
        """Check if there's sufficient continuous speech"""
        max_continuous = 0
        current_continuous = 0
        
        for flag in speech_flags:
            if flag:
                current_continuous += 1
                max_continuous = max(max_continuous, current_continuous)
            else:
                current_continuous = 0
        
        return max_continuous >= self.min_speech_frames
    
    def get_info(self) -> dict:
        """Get VAD processor information"""
        return {
            'provider': self.provider_name,
            'aggressiveness': self.aggressiveness,
            'sample_rate': self.sample_rate,
            'frame_duration_ms': self.frame_duration_ms,
            'min_speech_duration_ms': self.min_speech_duration_ms,
            'padding_duration_ms': self.padding_duration_ms
        }
