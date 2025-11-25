#!/usr/bin/env python3
"""
Enhanced audio preprocessing to improve Whisper transcription accuracy in noisy environments
Includes spectral subtraction, Wiener filtering, noise profiling, and advanced speech enhancement
"""

import numpy as np
import scipy.signal
from typing import Optional


class AudioPreprocessor:
    """Enhanced audio preprocessor for better Whisper transcription in noisy environments"""
    
    def __init__(
        self, 
        sample_rate: int = 16000,
        enable_spectral_subtraction: bool = True,
        enable_wiener_filter: bool = True,
        enable_pre_emphasis: bool = True,
        enable_multi_band_gate: bool = True,
        noise_reduction_mode: str = "aggressive"
    ):
        """
        Initialize enhanced audio preprocessor
        
        Args:
            sample_rate: Target sample rate for Whisper (16000 Hz)
            enable_spectral_subtraction: Enable spectral subtraction for stationary noise
            enable_wiener_filter: Enable Wiener filtering for adaptive noise reduction
            enable_pre_emphasis: Enable pre-emphasis filter for speech clarity
            enable_multi_band_gate: Enable multi-band noise gating
            noise_reduction_mode: 'mild', 'moderate', or 'aggressive'
        """
        self.sample_rate = sample_rate
        self.enable_spectral_subtraction = enable_spectral_subtraction
        self.enable_wiener_filter = enable_wiener_filter
        self.enable_pre_emphasis = enable_pre_emphasis
        self.enable_multi_band_gate = enable_multi_band_gate
        
        # Noise reduction parameters based on mode
        mode_params = {
            'mild': {'alpha': 1.5, 'beta': 0.02, 'snr_threshold': 2.0},
            'moderate': {'alpha': 2.0, 'beta': 0.01, 'snr_threshold': 3.0},
            'aggressive': {'alpha': 2.5, 'beta': 0.005, 'snr_threshold': 4.0}
        }
        params = mode_params.get(noise_reduction_mode, mode_params['moderate'])
        
        self.spectral_alpha = params['alpha']  # Over-subtraction factor
        self.spectral_beta = params['beta']  # Spectral floor
        self.snr_threshold = params['snr_threshold']  # SNR threshold for Wiener filter
        
        # Noise profile (learned from first few frames)
        self.noise_profile: Optional[np.ndarray] = None
        self.noise_profile_ready = False
        
    def preprocess(
        self, 
        audio_data: np.ndarray, 
        original_sample_rate: int = 44100,
        is_noise_sample: bool = False
    ) -> np.ndarray:
        """
        Enhanced preprocessing pipeline for optimal Whisper transcription
        
        Args:
            audio_data: Raw audio samples as numpy array
            original_sample_rate: Original sample rate of the audio
            is_noise_sample: If True, use this audio to build noise profile
            
        Returns:
            Preprocessed audio ready for Whisper
        """
        # Convert to float32 if needed
        if audio_data.dtype != np.float32:
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            else:
                audio_data = audio_data.astype(np.float32)
        
        # Resample first to target rate
        if original_sample_rate != self.sample_rate:
            audio_data = self._resample(audio_data, original_sample_rate, self.sample_rate)
        
        # If this is a noise sample, build noise profile and return
        if is_noise_sample:
            self._build_noise_profile(audio_data)
            return audio_data
        
        # Apply pre-emphasis to boost high frequencies (speech clarity)
        if self.enable_pre_emphasis:
            audio_data = self._pre_emphasize(audio_data)
        
        # Apply high-pass filter to remove low-frequency noise (AC hum, rumble)
        audio_data = self._high_pass_filter(audio_data, cutoff_freq=80)
        
        # Apply spectral subtraction for stationary noise removal
        if self.enable_spectral_subtraction:
            audio_data = self._spectral_subtract(audio_data)
        
        # Apply Wiener filter for adaptive noise reduction
        if self.enable_wiener_filter:
            audio_data = self._wiener_filter(audio_data)
        
        # Apply multi-band noise gate
        if self.enable_multi_band_gate:
            audio_data = self._multi_band_gate(audio_data)
        
        # Normalize volume to prevent clipping
        audio_data = self._normalize_volume(audio_data)
        
        # Enhance speech using dynamic range compression
        audio_data = self._enhance_speech(audio_data)
        
        # Final normalization
        audio_data = self._normalize_volume(audio_data)
        
        return audio_data
    
    def _build_noise_profile(self, noise_audio: np.ndarray):
        """Build noise profile from noise-only audio sample"""
        # Compute magnitude spectrum of noise
        stft = np.fft.rfft(noise_audio)
        noise_magnitude = np.abs(stft)
        
        # Average with existing profile if available
        if self.noise_profile is None:
            self.noise_profile = noise_magnitude
        else:
            # Exponential moving average
            self.noise_profile = 0.7 * self.noise_profile + 0.3 * noise_magnitude
        
        self.noise_profile_ready = True
        print(f"[AUDIO] Noise profile updated (length: {len(self.noise_profile)})")
    
    def _spectral_subtract(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Spectral subtraction to remove stationary background noise (AC, fan, etc.)
        """
        if not self.noise_profile_ready:
            # No noise profile yet, skip
            return audio_data
        
        # Short-time Fourier transform
        stft = np.fft.rfft(audio_data)
        magnitude = np.abs(stft)
        phase = np.angle(stft)
        
        # Ensure noise profile matches length
        if len(self.noise_profile) != len(magnitude):
            # Build temporary noise profile
            noise_estimate = np.percentile(magnitude, 10)  # Bottom 10% as noise
            noise_profile = np.full_like(magnitude, noise_estimate)
        else:
            noise_profile = self.noise_profile
        
        # Spectral subtraction with over-subtraction
        cleaned_magnitude = magnitude - self.spectral_alpha * noise_profile
        
        # Apply spectral floor to prevent negative values
        cleaned_magnitude = np.maximum(cleaned_magnitude, self.spectral_beta * magnitude)
        
        # Reconstruct signal
        cleaned_stft = cleaned_magnitude * np.exp(1j * phase)
        cleaned_audio = np.fft.irfft(cleaned_stft, n=len(audio_data))
        
        return cleaned_audio.astype(np.float32)
    
    def _wiener_filter(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Wiener filtering for adaptive noise reduction
        """
        # Compute power spectrum
        stft = np.fft.rfft(audio_data)
        power_spectrum = np.abs(stft) ** 2
        
        # Estimate noise power (using bottom 20th percentile)
        noise_power = np.percentile(power_spectrum, 20)
        
        # Compute SNR
        snr = power_spectrum / (noise_power + 1e-10)
        
        # Wiener gain
        wiener_gain = np.maximum(snr / (snr + 1), 0.1)  # Minimum gain of 0.1
        
        # Apply gain
        filtered_stft = stft * wiener_gain
        
        # Inverse FFT
        filtered_audio = np.fft.irfft(filtered_stft, n=len(audio_data))
        
        return filtered_audio.astype(np.float32)
    
    def _pre_emphasize(self, audio_data: np.ndarray, coefficient: float = 0.97) -> np.ndarray:
        """
        Pre-emphasis filter to boost high frequencies (improves consonant recognition)
        """
        emphasized = np.append(audio_data[0], audio_data[1:] - coefficient * audio_data[:-1])
        return emphasized.astype(np.float32)
    
    def _multi_band_gate(self, audio_data: np.ndarray, num_bands: int = 8) -> np.ndarray:
        """
        Multi-band noise gate - different thresholds for different frequency bands
        """
        # Design bandpass filters for each band
        nyquist = self.sample_rate / 2
        band_edges = np.logspace(np.log10(80), np.log10(nyquist * 0.95), num_bands + 1)
        
        # Thresholds for each band (higher frequencies = higher threshold)
        base_thresholds = [0.01, 0.01, 0.015, 0.02, 0.02, 0.025, 0.03, 0.03]
        thresholds = base_thresholds[:num_bands]
        
        filtered_bands = []
        
        for i in range(num_bands):
            low_freq = band_edges[i]
            high_freq = band_edges[i + 1]
            
            # Design bandpass filter
            try:
                sos = scipy.signal.butter(
                    2, 
                    [low_freq / nyquist, high_freq / nyquist], 
                    btype='band', 
                    output='sos'
                )
                band_signal = scipy.signal.sosfiltfilt(sos, audio_data)
                
                # Apply gate
                rms = np.sqrt(np.mean(band_signal ** 2))
                if rms > thresholds[i]:
                    filtered_bands.append(band_signal)
                else:
                    # Gate closed - attenuate by 90%
                    filtered_bands.append(band_signal * 0.1)
            except Exception as e:
                # If filter design fails, use original band
                filtered_bands.append(np.zeros_like(audio_data))
        
        # Sum all bands
        gated_audio = np.sum(filtered_bands, axis=0)
        
        return gated_audio.astype(np.float32)
    
    def _normalize_volume(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio volume to prevent clipping and ensure consistent levels"""
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            # Normalize to 70% of max to prevent clipping
            audio_data = audio_data * (0.7 / max_val)
        return audio_data.astype(np.float32)
    
    def _resample(self, audio_data: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
        """Resample audio to target sample rate using high-quality resampling"""
        if from_rate == to_rate:
            return audio_data
            
        # Calculate resampling ratio
        ratio = to_rate / from_rate
        new_length = int(len(audio_data) * ratio)
        
        # Use scipy for high-quality resampling
        resampled = scipy.signal.resample(audio_data, new_length)
        return resampled.astype(np.float32)
    
    def _high_pass_filter(self, audio_data: np.ndarray, cutoff_freq: int = 80) -> np.ndarray:
        """Apply high-pass filter to remove low-frequency noise (AC hum, rumble)"""
        nyquist = self.sample_rate / 2
        normalized_cutoff = cutoff_freq / nyquist
        
        # Design Butterworth high-pass filter
        b, a = scipy.signal.butter(4, normalized_cutoff, btype='high')
        
        # Apply filter using filtfilt for zero phase distortion
        filtered = scipy.signal.filtfilt(b, a, audio_data)
        return filtered.astype(np.float32)
    
    def _enhance_speech(self, audio_data: np.ndarray) -> np.ndarray:
        """Enhance speech clarity using dynamic range compression"""
        # Calculate RMS for dynamic range compression
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        if rms > 0:
            # Apply light compression to enhance speech (exponent < 1)
            compressed = np.sign(audio_data) * np.power(np.abs(audio_data), 0.8)
            
            # Preserve overall volume
            compressed_rms = np.sqrt(np.mean(compressed ** 2))
            if compressed_rms > 0:
                compressed = compressed * (rms / compressed_rms)
            
            return compressed.astype(np.float32)
        
        return audio_data