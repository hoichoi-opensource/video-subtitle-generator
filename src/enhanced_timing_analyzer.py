"""
Enhanced Timing Analyzer
Advanced timing analysis with speech rate detection, pause detection, and audio energy analysis
"""

import numpy as np
import librosa
import scipy.signal
from typing import List, Dict, Tuple, Optional, Any, Union
from pathlib import Path
import json
import math

# Core dependencies
from .config_manager import ConfigManager
from .logger import get_logger
from .exceptions import ValidationError, VideoProcessingError

logger = get_logger(__name__)

class EnhancedTimingAnalyzer:
    """Advanced timing analysis for optimal subtitle segmentation"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.sample_rate = 16000  # Standard rate for speech analysis
        self.hop_length = 512
        self.frame_length = 2048
        self._initialize_audio_processing()
    
    def _initialize_audio_processing(self):
        """Initialize audio processing parameters"""
        try:
            # Verify librosa is available
            import librosa
            logger.info("✅ Enhanced timing analysis initialized with librosa")
        except ImportError:
            logger.warning("librosa not available - install with: pip install librosa")
            raise ImportError("librosa required for enhanced timing analysis")
    
    def analyze_speech_rate(self, audio_path: str, subtitle_segments: List[Dict]) -> Dict[str, Any]:
        """
        Analyze speech rate across subtitle segments
        
        Args:
            audio_path: Path to audio file
            subtitle_segments: List of subtitle segments with timing
        
        Returns:
            Speech rate analysis results
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            analysis = {
                "global_speech_rate": 0.0,
                "segment_rates": [],
                "rate_variability": 0.0,
                "speaking_time_ratio": 0.0,
                "recommended_adjustments": []
            }
            
            segment_rates = []
            total_speaking_time = 0
            total_words = 0
            
            for segment in subtitle_segments:
                start_time = segment.get('start', 0)
                end_time = segment.get('end', 0)
                text = segment.get('text', '').strip()
                
                if not text or end_time <= start_time:
                    continue
                
                # Extract audio segment
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                
                if start_sample >= len(y) or end_sample > len(y):
                    continue
                
                segment_audio = y[start_sample:end_sample]
                duration = end_time - start_time
                
                # Analyze speech activity in segment
                speech_activity = self._detect_speech_activity(segment_audio, sr)
                active_duration = speech_activity['active_duration']
                
                # Calculate speech rate (words per minute)
                word_count = len(text.split())
                if active_duration > 0:
                    rate_wpm = (word_count / active_duration) * 60
                    segment_rates.append(rate_wpm)
                    
                    total_speaking_time += active_duration
                    total_words += word_count
                    
                    # Store segment analysis
                    analysis["segment_rates"].append({
                        "start": start_time,
                        "end": end_time,
                        "speech_rate_wpm": rate_wpm,
                        "word_count": word_count,
                        "active_duration": active_duration,
                        "speech_activity_ratio": active_duration / duration
                    })
                    
                    # Check for problematic rates
                    if rate_wpm > 200:  # Too fast
                        analysis["recommended_adjustments"].append({
                            "segment": f"{start_time:.1f}-{end_time:.1f}s",
                            "issue": "speech_too_fast",
                            "current_rate": rate_wpm,
                            "recommendation": "Consider breaking into shorter segments"
                        })
                    elif rate_wpm < 80:  # Too slow
                        analysis["recommended_adjustments"].append({
                            "segment": f"{start_time:.1f}-{end_time:.1f}s",
                            "issue": "speech_too_slow", 
                            "current_rate": rate_wpm,
                            "recommendation": "Consider combining with adjacent segments"
                        })
            
            # Calculate global metrics
            if segment_rates:
                analysis["global_speech_rate"] = np.mean(segment_rates)
                analysis["rate_variability"] = np.std(segment_rates)
                analysis["median_rate"] = np.median(segment_rates)
                analysis["rate_range"] = [np.min(segment_rates), np.max(segment_rates)]
            
            # Calculate speaking time ratio
            total_audio_duration = len(y) / sr
            if total_audio_duration > 0:
                analysis["speaking_time_ratio"] = total_speaking_time / total_audio_duration
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing speech rate: {e}")
            return {"error": str(e)}
    
    def detect_natural_pauses(self, audio_path: str, min_pause_duration: float = 0.3) -> List[Dict]:
        """
        Detect natural pauses in audio for better segmentation
        
        Args:
            audio_path: Path to audio file
            min_pause_duration: Minimum pause duration to detect (seconds)
        
        Returns:
            List of detected pauses with timing and characteristics
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Compute energy/power
            hop_length = self.hop_length
            frame_length = self.frame_length
            
            # RMS energy
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Convert to time domain
            times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
            
            # Adaptive threshold for silence detection
            rms_threshold = np.percentile(rms[rms > 0], 25)  # 25th percentile of non-zero values
            
            # Detect silence regions
            silence_mask = rms < rms_threshold
            
            # Find continuous silent regions
            pauses = []
            in_pause = False
            pause_start = 0
            
            for i, is_silent in enumerate(silence_mask):
                if is_silent and not in_pause:
                    # Start of pause
                    in_pause = True
                    pause_start = times[i]
                elif not is_silent and in_pause:
                    # End of pause
                    pause_end = times[i]
                    pause_duration = pause_end - pause_start
                    
                    if pause_duration >= min_pause_duration:
                        # Analyze pause characteristics
                        pause_energy = self._analyze_pause_energy(y, sr, pause_start, pause_end)
                        
                        pauses.append({
                            "start": pause_start,
                            "end": pause_end,
                            "duration": pause_duration,
                            "type": self._classify_pause_type(pause_duration, pause_energy),
                            "energy_level": pause_energy["mean_energy"],
                            "confidence": self._calculate_pause_confidence(pause_duration, pause_energy)
                        })
                    
                    in_pause = False
            
            # Sort by confidence and filter high-quality pauses
            high_quality_pauses = [p for p in pauses if p["confidence"] > 0.7]
            high_quality_pauses.sort(key=lambda x: x["confidence"], reverse=True)
            
            logger.info(f"Detected {len(pauses)} total pauses, {len(high_quality_pauses)} high-quality")
            
            return {
                "all_pauses": pauses,
                "high_quality_pauses": high_quality_pauses,
                "pause_statistics": self._calculate_pause_statistics(pauses),
                "segmentation_recommendations": self._generate_segmentation_recommendations(high_quality_pauses)
            }
            
        except Exception as e:
            logger.error(f"Error detecting natural pauses: {e}")
            return {"error": str(e)}
    
    def analyze_audio_energy(self, audio_path: str, window_size: float = 0.1) -> Dict[str, Any]:
        """
        Analyze audio energy patterns for better segmentation
        
        Args:
            audio_path: Path to audio file
            window_size: Analysis window size in seconds
        
        Returns:
            Audio energy analysis results
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Calculate window parameters
            window_samples = int(window_size * sr)
            hop_samples = window_samples // 2
            
            # Compute various energy features
            features = {}
            
            # 1. RMS Energy
            rms = librosa.feature.rms(y=y, frame_length=window_samples, hop_length=hop_samples)[0]
            times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_samples)
            
            # 2. Spectral Centroid (brightness)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_samples)[0]
            
            # 3. Zero Crossing Rate (speech/music discrimination)
            zcr = librosa.feature.zero_crossing_rate(y, frame_length=window_samples, hop_length=hop_samples)[0]
            
            # 4. Spectral Rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_samples)[0]
            
            # 5. Mel-frequency Cepstral Coefficients (MFCCs)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_samples)
            
            analysis = {
                "energy_profile": {
                    "times": times.tolist(),
                    "rms_energy": rms.tolist(),
                    "spectral_centroid": spectral_centroids.tolist(),
                    "zero_crossing_rate": zcr.tolist(),
                    "spectral_rolloff": spectral_rolloff.tolist()
                },
                "energy_statistics": {
                    "mean_rms": float(np.mean(rms)),
                    "std_rms": float(np.std(rms)),
                    "dynamic_range": float(np.max(rms) - np.min(rms[rms > 0])),
                    "energy_variability": float(np.std(rms) / np.mean(rms)) if np.mean(rms) > 0 else 0
                },
                "speech_characteristics": self._analyze_speech_characteristics(mfccs, zcr, spectral_centroids),
                "optimal_breakpoints": self._find_optimal_breakpoints(rms, times),
                "energy_based_segments": self._segment_by_energy(rms, times, y, sr)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing audio energy: {e}")
            return {"error": str(e)}
    
    def optimize_subtitle_timing(self, 
                                audio_path: str, 
                                subtitle_segments: List[Dict],
                                target_reading_speed: float = 200) -> Dict[str, Any]:
        """
        Optimize subtitle timing based on speech analysis
        
        Args:
            audio_path: Path to audio file
            subtitle_segments: Original subtitle segments
            target_reading_speed: Target reading speed in WPM
        
        Returns:
            Optimized timing recommendations
        """
        try:
            # Get speech rate analysis
            speech_analysis = self.analyze_speech_rate(audio_path, subtitle_segments)
            
            # Get pause detection
            pause_analysis = self.detect_natural_pauses(audio_path)
            
            # Get energy analysis
            energy_analysis = self.analyze_audio_energy(audio_path)
            
            optimized_segments = []
            recommendations = []
            
            for segment in subtitle_segments:
                original_start = segment.get('start', 0)
                original_end = segment.get('end', 0)
                text = segment.get('text', '').strip()
                
                if not text:
                    continue
                
                # Calculate optimal timing based on text length and target reading speed
                word_count = len(text.split())
                char_count = len(text)
                
                # Minimum duration based on reading speed (words per minute to seconds)
                min_duration_by_reading = (word_count / target_reading_speed) * 60
                
                # Industry standard: 15-25 characters per second
                min_duration_by_chars = char_count / 20  # 20 CPS target
                
                # Use the longer of the two minimums
                recommended_duration = max(min_duration_by_reading, min_duration_by_chars, 1.0)
                
                # Find optimal start/end times using pause information
                optimal_start, optimal_end = self._find_optimal_segment_boundaries(
                    original_start, original_end, recommended_duration, 
                    pause_analysis.get('high_quality_pauses', []),
                    energy_analysis.get('optimal_breakpoints', [])
                )
                
                # Create optimized segment
                optimized_segment = {
                    "original_start": original_start,
                    "original_end": original_end,
                    "optimized_start": optimal_start,
                    "optimized_end": optimal_end,
                    "text": text,
                    "duration_change": (optimal_end - optimal_start) - (original_end - original_start),
                    "reading_speed_wpm": (word_count / ((optimal_end - optimal_start) / 60)) if optimal_end > optimal_start else 0,
                    "chars_per_second": char_count / (optimal_end - optimal_start) if optimal_end > optimal_start else 0
                }
                
                optimized_segments.append(optimized_segment)
                
                # Generate recommendations for significant changes
                if abs(optimized_segment["duration_change"]) > 0.5:
                    recommendations.append({
                        "segment": f"{original_start:.1f}-{original_end:.1f}s",
                        "change_type": "extend" if optimized_segment["duration_change"] > 0 else "shorten",
                        "duration_change": optimized_segment["duration_change"],
                        "reason": self._explain_timing_change(optimized_segment)
                    })
            
            return {
                "optimized_segments": optimized_segments,
                "recommendations": recommendations,
                "overall_improvements": self._calculate_overall_improvements(subtitle_segments, optimized_segments),
                "timing_quality_score": self._calculate_timing_quality_score(optimized_segments)
            }
            
        except Exception as e:
            logger.error(f"Error optimizing subtitle timing: {e}")
            return {"error": str(e)}
    
    # Helper methods for enhanced timing analysis
    
    def _detect_speech_activity(self, audio_segment: np.ndarray, sr: int) -> Dict[str, Any]:
        """Detect speech activity in audio segment using energy and spectral features"""
        try:
            # Voice Activity Detection (VAD) using multiple features
            
            # 1. Energy-based detection
            frame_length = min(512, len(audio_segment) // 4)
            hop_length = frame_length // 2
            
            if len(audio_segment) < frame_length:
                return {"active_duration": 0, "activity_ratio": 0}
            
            rms = librosa.feature.rms(y=audio_segment, frame_length=frame_length, hop_length=hop_length)[0]
            
            # 2. Zero crossing rate (helps distinguish speech from music/noise)
            zcr = librosa.feature.zero_crossing_rate(audio_segment, frame_length=frame_length, hop_length=hop_length)[0]
            
            # 3. Spectral centroid (frequency content)
            spectral_centroid = librosa.feature.spectral_centroid(y=audio_segment, sr=sr, hop_length=hop_length)[0]
            
            # Adaptive thresholds
            rms_threshold = np.percentile(rms[rms > 0], 30) if len(rms[rms > 0]) > 0 else 0
            zcr_mean = np.mean(zcr)
            centroid_mean = np.mean(spectral_centroid)
            
            # Speech activity mask (combine multiple criteria)
            speech_mask = (
                (rms > rms_threshold) & 
                (zcr > zcr_mean * 0.5) & (zcr < zcr_mean * 2.0) &  # Speech has moderate ZCR
                (spectral_centroid > centroid_mean * 0.3)  # Some frequency content
            )
            
            # Calculate active duration
            frame_duration = hop_length / sr
            active_frames = np.sum(speech_mask)
            active_duration = active_frames * frame_duration
            
            return {
                "active_duration": active_duration,
                "activity_ratio": active_duration / (len(audio_segment) / sr),
                "confidence": np.mean(rms[speech_mask]) / np.mean(rms) if len(rms) > 0 else 0
            }
            
        except Exception as e:
            logger.warning(f"Error in speech activity detection: {e}")
            return {"active_duration": 0, "activity_ratio": 0}
    
    def _analyze_pause_energy(self, audio: np.ndarray, sr: int, start_time: float, end_time: float) -> Dict[str, float]:
        """Analyze energy characteristics of a pause"""
        try:
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            
            if start_sample >= len(audio) or end_sample > len(audio):
                return {"mean_energy": 0, "std_energy": 0}
            
            pause_audio = audio[start_sample:end_sample]
            
            # Calculate RMS energy
            if len(pause_audio) > 0:
                rms = np.sqrt(np.mean(pause_audio ** 2))
                energy_std = np.std(pause_audio)
                
                return {
                    "mean_energy": float(rms),
                    "std_energy": float(energy_std),
                    "max_amplitude": float(np.max(np.abs(pause_audio)))
                }
            
            return {"mean_energy": 0, "std_energy": 0, "max_amplitude": 0}
            
        except Exception:
            return {"mean_energy": 0, "std_energy": 0, "max_amplitude": 0}
    
    def _classify_pause_type(self, duration: float, energy: Dict[str, float]) -> str:
        """Classify pause type based on duration and energy"""
        if duration < 0.5:
            return "short_pause"
        elif duration < 1.0:
            if energy.get("mean_energy", 0) < 0.01:
                return "natural_break"
            else:
                return "speech_pause"
        elif duration < 2.0:
            return "sentence_break"
        else:
            return "long_silence"
    
    def _calculate_pause_confidence(self, duration: float, energy: Dict[str, float]) -> float:
        """Calculate confidence score for pause detection"""
        confidence = 0.5  # Base confidence
        
        # Duration factor
        if 0.3 <= duration <= 2.0:  # Optimal range
            confidence += 0.3
        elif duration > 2.0:
            confidence += 0.1
        
        # Energy factor (lower energy = higher confidence for silence)
        mean_energy = energy.get("mean_energy", 1.0)
        if mean_energy < 0.01:
            confidence += 0.2
        elif mean_energy < 0.05:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _calculate_pause_statistics(self, pauses: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics for detected pauses"""
        if not pauses:
            return {}
        
        durations = [p["duration"] for p in pauses]
        
        return {
            "total_pauses": len(pauses),
            "average_duration": np.mean(durations),
            "median_duration": np.median(durations),
            "duration_std": np.std(durations),
            "shortest_pause": np.min(durations),
            "longest_pause": np.max(durations),
            "pause_types": {ptype: len([p for p in pauses if p["type"] == ptype]) 
                           for ptype in set(p["type"] for p in pauses)}
        }
    
    def _generate_segmentation_recommendations(self, pauses: List[Dict]) -> List[Dict]:
        """Generate recommendations for segment boundaries based on pauses"""
        recommendations = []
        
        for pause in pauses:
            if pause["confidence"] > 0.8 and pause["duration"] > 0.5:
                recommendations.append({
                    "break_point": pause["start"] + pause["duration"] / 2,
                    "confidence": pause["confidence"],
                    "reason": f"Natural {pause['type']} detected",
                    "pause_duration": pause["duration"]
                })
        
        return sorted(recommendations, key=lambda x: x["confidence"], reverse=True)
    
    def _analyze_speech_characteristics(self, mfccs: np.ndarray, zcr: np.ndarray, centroids: np.ndarray) -> Dict[str, Any]:
        """Analyze speech characteristics from audio features"""
        try:
            return {
                "spectral_complexity": float(np.std(centroids)),
                "temporal_stability": float(1.0 / (1.0 + np.std(zcr))),
                "vocal_quality": float(np.mean(mfccs[1:5])),  # Lower MFCCs indicate vocal characteristics
                "speech_consistency": float(1.0 / (1.0 + np.std(mfccs[0])))  # First MFCC stability
            }
        except Exception:
            return {"spectral_complexity": 0, "temporal_stability": 0, "vocal_quality": 0, "speech_consistency": 0}
    
    def _find_optimal_breakpoints(self, rms: np.ndarray, times: np.ndarray) -> List[float]:
        """Find optimal breakpoints based on energy patterns"""
        try:
            # Find local minima in RMS energy (good places for breaks)
            minima_indices = scipy.signal.argrelmin(rms, order=3)[0]
            
            # Filter for significant minima
            threshold = np.percentile(rms, 25)  # Bottom quartile
            significant_minima = [i for i in minima_indices if rms[i] < threshold]
            
            # Convert to time
            breakpoints = [times[i] for i in significant_minima if i < len(times)]
            
            return sorted(breakpoints)
            
        except Exception:
            return []
    
    def _segment_by_energy(self, rms: np.ndarray, times: np.ndarray, audio: np.ndarray, sr: int) -> List[Dict]:
        """Create energy-based segments"""
        try:
            segments = []
            
            # Find high-energy regions
            energy_threshold = np.percentile(rms, 60)  # Upper 40%
            high_energy_mask = rms > energy_threshold
            
            # Find continuous high-energy regions
            in_segment = False
            segment_start = 0
            
            for i, is_high_energy in enumerate(high_energy_mask):
                if is_high_energy and not in_segment:
                    in_segment = True
                    segment_start = times[i]
                elif not is_high_energy and in_segment:
                    segment_end = times[i]
                    duration = segment_end - segment_start
                    
                    if duration > 1.0:  # Minimum 1 second
                        segments.append({
                            "start": segment_start,
                            "end": segment_end,
                            "duration": duration,
                            "type": "high_energy"
                        })
                    
                    in_segment = False
            
            return segments
            
        except Exception:
            return []
    
    def _find_optimal_segment_boundaries(self, 
                                       original_start: float, 
                                       original_end: float,
                                       target_duration: float,
                                       pauses: List[Dict],
                                       breakpoints: List[float]) -> Tuple[float, float]:
        """Find optimal start/end times for a segment"""
        
        # Start with original timing
        optimal_start = original_start
        optimal_end = original_end
        
        # Adjust for target duration
        duration_diff = target_duration - (original_end - original_start)
        
        if abs(duration_diff) > 0.2:  # Significant change needed
            # Try to extend/shrink symmetrically first
            half_diff = duration_diff / 2
            
            # Check for nearby pauses or breakpoints
            nearby_pauses_start = [p for p in pauses if abs(p["start"] - (original_start - half_diff)) < 0.5]
            nearby_pauses_end = [p for p in pauses if abs(p["end"] - (original_end + half_diff)) < 0.5]
            
            # Adjust start time
            if nearby_pauses_start:
                best_pause = max(nearby_pauses_start, key=lambda p: p["confidence"])
                optimal_start = best_pause["end"]
            else:
                # Check breakpoints
                nearby_breaks_start = [b for b in breakpoints if abs(b - (original_start - half_diff)) < 0.5]
                if nearby_breaks_start:
                    optimal_start = min(nearby_breaks_start, key=lambda b: abs(b - (original_start - half_diff)))
                else:
                    optimal_start = max(0, original_start - half_diff)
            
            # Adjust end time
            if nearby_pauses_end:
                best_pause = max(nearby_pauses_end, key=lambda p: p["confidence"])
                optimal_end = best_pause["start"]
            else:
                # Check breakpoints  
                nearby_breaks_end = [b for b in breakpoints if abs(b - (original_end + half_diff)) < 0.5]
                if nearby_breaks_end:
                    optimal_end = min(nearby_breaks_end, key=lambda b: abs(b - (original_end + half_diff)))
                else:
                    optimal_end = original_end + half_diff
        
        # Ensure minimum duration
        if optimal_end - optimal_start < 1.0:
            optimal_end = optimal_start + 1.0
        
        return optimal_start, optimal_end
    
    def _explain_timing_change(self, segment: Dict) -> str:
        """Explain why timing was changed"""
        duration_change = segment["duration_change"]
        reading_speed = segment["reading_speed_wpm"]
        cps = segment["chars_per_second"]
        
        if duration_change > 0.5:
            if reading_speed > 200:
                return "Extended duration due to fast reading speed"
            elif cps > 20:
                return "Extended duration due to high character density"
            else:
                return "Extended for better readability"
        elif duration_change < -0.5:
            if reading_speed < 120:
                return "Shortened duration due to slow reading speed"
            else:
                return "Shortened to improve pacing"
        else:
            return "Minor adjustment for optimal timing"
    
    def _calculate_overall_improvements(self, original: List[Dict], optimized: List[Dict]) -> Dict[str, Any]:
        """Calculate overall improvements from timing optimization"""
        try:
            if not original or not optimized:
                return {}
            
            # Calculate reading speed improvements
            original_speeds = []
            optimized_speeds = []
            
            for orig, opt in zip(original, optimized):
                if 'text' in orig:
                    word_count = len(orig['text'].split())
                    
                    orig_duration = orig.get('end', 0) - orig.get('start', 0)
                    opt_duration = opt['optimized_end'] - opt['optimized_start']
                    
                    if orig_duration > 0:
                        original_speeds.append((word_count / orig_duration) * 60)
                    if opt_duration > 0:
                        optimized_speeds.append((word_count / opt_duration) * 60)
            
            improvements = {
                "average_reading_speed_improvement": 0,
                "timing_consistency_improvement": 0,
                "segments_improved": 0,
                "total_segments": len(optimized)
            }
            
            if original_speeds and optimized_speeds:
                improvements["average_reading_speed_improvement"] = np.mean(optimized_speeds) - np.mean(original_speeds)
                improvements["timing_consistency_improvement"] = np.std(original_speeds) - np.std(optimized_speeds)
                
                # Count improved segments
                improvements["segments_improved"] = sum(1 for opt in optimized if abs(opt["duration_change"]) > 0.2)
            
            return improvements
            
        except Exception:
            return {}
    
    def _calculate_timing_quality_score(self, segments: List[Dict]) -> float:
        """Calculate overall timing quality score"""
        try:
            if not segments:
                return 0.0
            
            total_score = 0
            
            for segment in segments:
                score = 1.0
                
                reading_speed = segment.get("reading_speed_wpm", 150)
                cps = segment.get("chars_per_second", 15)
                
                # Penalize for poor reading speeds
                if reading_speed > 200 or reading_speed < 100:
                    score -= 0.2
                
                # Penalize for poor character rates
                if cps > 25 or cps < 10:
                    score -= 0.2
                
                # Bonus for optimal ranges
                if 120 <= reading_speed <= 180:
                    score += 0.1
                if 15 <= cps <= 20:
                    score += 0.1
                
                total_score += max(0, score)
            
            return total_score / len(segments)
            
        except Exception:
            return 0.0