#!/usr/bin/env python3
"""
Audio preprocessing to improve Whisper transcription accuracy
"""

import numpy as np
import scipy.signal

class AudioPreprocessor:
    """Preprocesses audio for better Whisper transcription"""
    
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        
    def preprocess(self, audio_data, original_sample_rate=44100):
        """
        Preprocess audio for optimal Whisper transcription
        
        Args:
            audio_data: Raw audio samples as numpy array
            original_sample_rate: Original sample rate of the audio
            
        Returns:
            Preprocessed audio ready for Whisper
        """
        
        # Convert to float32 if needed
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # Normalize volume
        audio_data = self._normalize_volume(audio_data)
        
        # Apply noise reduction
        audio_data = self._reduce_noise(audio_data)
        
        # Resample to 16kHz (Whisper's preferred rate)
        if original_sample_rate != self.sample_rate:
            audio_data = self._resample(audio_data, original_sample_rate, self.sample_rate)
        
        # Apply high-pass filter to remove low-frequency noise
        audio_data = self._high_pass_filter(audio_data)
        
        # Final normalization
        audio_data = self._normalize_volume(audio_data)
        
        return audio_data
    
    def _normalize_volume(self, audio_data):
        """Normalize audio volume to prevent clipping and ensure consistent levels"""
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            # Normalize to 70% of max to prevent clipping
            audio_data = audio_data * (0.7 / max_val)
        return audio_data
    
    def _reduce_noise(self, audio_data, noise_factor=0.1):
        """Simple noise reduction using spectral gating"""
        
        # Calculate noise floor (bottom 10% of samples)
        sorted_samples = np.sort(np.abs(audio_data))
        noise_floor = sorted_samples[int(len(sorted_samples) * noise_factor)]
        
        # Apply soft gating - reduce samples below noise threshold
        mask = np.abs(audio_data) < noise_floor
        audio_data[mask] = audio_data[mask] * 0.1  # Reduce noise by 90%
        
        return audio_data
    
    def _resample(self, audio_data, from_rate, to_rate):
        """Resample audio to target sample rate"""
        if from_rate == to_rate:
            return audio_data
            
        # Calculate resampling ratio
        ratio = to_rate / from_rate
        new_length = int(len(audio_data) * ratio)
        
        # Use scipy for high-quality resampling
        resampled = scipy.signal.resample(audio_data, new_length)
        return resampled.astype(np.float32)
    
    def _high_pass_filter(self, audio_data, cutoff_freq=80):
        """Apply high-pass filter to remove low-frequency noise"""
        nyquist = self.sample_rate / 2
        normalized_cutoff = cutoff_freq / nyquist
        
        # Design Butterworth high-pass filter
        b, a = scipy.signal.butter(4, normalized_cutoff, btype='high')
        
        # Apply filter
        filtered = scipy.signal.filtfilt(b, a, audio_data)
        return filtered.astype(np.float32)
    
    def enhance_speech(self, audio_data):
        """Enhance speech clarity using dynamic range compression"""
        
        # Calculate RMS for dynamic range compression
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        if rms > 0:
            # Apply light compression to enhance speech
            compressed = np.sign(audio_data) * np.power(np.abs(audio_data), 0.8)
            
            # Preserve overall volume
            compressed = compressed * (rms / np.sqrt(np.mean(compressed ** 2)))
            
            return compressed.astype(np.float32)
        
        return audio_data 