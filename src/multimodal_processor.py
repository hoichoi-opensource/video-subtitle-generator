"""
Multi-Modal Processor
Advanced multi-modal processing with visual context analysis, speaker identification, and noise filtering
"""

import cv2
import numpy as np
import librosa
import scipy.signal
from typing import List, Dict, Tuple, Optional, Any, Union
from pathlib import Path
import json
import pickle
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

# Core dependencies
from .config_manager import ConfigManager
from .logger import get_logger
from .exceptions import ValidationError, VideoProcessingError

logger = get_logger(__name__)

class MultiModalProcessor:
    """Advanced multi-modal processing for enhanced subtitle generation"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.sample_rate = 16000
        self.video_fps = 25
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize computer vision and audio processing models"""
        try:
            # Verify OpenCV is available
            import cv2
            logger.info("✅ OpenCV initialized for visual analysis")
            
            # Initialize cascade classifiers for face detection
            try:
                self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                self.profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
                logger.info("✅ Face detection models loaded")
            except Exception as e:
                logger.warning(f"Face detection models not available: {e}")
                self.face_cascade = None
                self.profile_cascade = None
            
            # Initialize audio processing
            import librosa
            logger.info("✅ Audio processing initialized")
            
        except ImportError as e:
            logger.warning(f"Multi-modal processing not fully available: {e}")
            logger.info("Install with: pip install opencv-python librosa scikit-learn")
    
    def analyze_visual_context(self, video_path: str, subtitle_segments: List[Dict]) -> Dict[str, Any]:
        """
        Analyze visual context including scene detection, face detection, and text overlay
        
        Args:
            video_path: Path to video file
            subtitle_segments: List of subtitle segments with timing
        
        Returns:
            Visual context analysis results
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise VideoProcessingError(f"Cannot open video file: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            analysis = {
                "scene_changes": [],
                "speaker_appearances": [],
                "visual_complexity": [],
                "text_overlays": [],
                "dominant_colors": [],
                "motion_intensity": [],
                "face_detection_results": {}
            }
            
            # Sample frames at regular intervals
            sample_interval = max(1, int(fps / 4))  # 4 samples per second
            frame_count = 0
            prev_frame = None
            
            logger.info(f"Analyzing video: {duration:.1f}s, {fps:.1f} FPS, sampling every {sample_interval} frames")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % sample_interval == 0:
                    current_time = frame_count / fps
                    
                    # 1. Scene change detection
                    if prev_frame is not None:
                        scene_change = self._detect_scene_change(prev_frame, frame, current_time)
                        if scene_change["is_scene_change"]:
                            analysis["scene_changes"].append(scene_change)
                    
                    # 2. Face detection and speaker analysis
                    faces = self._detect_faces(frame, current_time)
                    if faces:
                        analysis["speaker_appearances"].append({
                            "time": current_time,
                            "faces": faces,
                            "dominant_speaker": self._identify_dominant_speaker(faces)
                        })
                    
                    # 3. Visual complexity analysis
                    complexity = self._analyze_visual_complexity(frame, current_time)
                    analysis["visual_complexity"].append(complexity)
                    
                    # 4. Text overlay detection
                    text_regions = self._detect_text_overlay(frame, current_time)
                    if text_regions:
                        analysis["text_overlays"].extend(text_regions)
                    
                    # 5. Color analysis
                    colors = self._analyze_dominant_colors(frame, current_time)
                    analysis["dominant_colors"].append(colors)
                    
                    # 6. Motion analysis
                    if prev_frame is not None:
                        motion = self._analyze_motion_intensity(prev_frame, frame, current_time)
                        analysis["motion_intensity"].append(motion)
                    
                    prev_frame = frame.copy()
                
                frame_count += 1
            
            cap.release()
            
            # Post-process results
            analysis["scene_statistics"] = self._calculate_scene_statistics(analysis["scene_changes"])
            analysis["speaker_timeline"] = self._create_speaker_timeline(analysis["speaker_appearances"])
            analysis["subtitle_alignment"] = self._align_visual_with_subtitles(analysis, subtitle_segments)
            
            logger.info(f"Visual analysis complete: {len(analysis['scene_changes'])} scene changes, "
                       f"{len(analysis['speaker_appearances'])} speaker appearances")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in visual context analysis: {e}")
            return {"error": str(e)}
    
    def identify_speakers(self, audio_path: str, subtitle_segments: List[Dict]) -> Dict[str, Any]:
        """
        Identify and track speakers throughout the audio
        
        Args:
            audio_path: Path to audio file
            subtitle_segments: List of subtitle segments
        
        Returns:
            Speaker identification results
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            analysis = {
                "num_speakers": 0,
                "speaker_segments": [],
                "speaker_profiles": {},
                "speaker_changes": [],
                "confidence_scores": []
            }
            
            # Extract speaker features for each segment
            speaker_features = []
            valid_segments = []
            
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
                
                # Extract speaker characteristics
                features = self._extract_speaker_features(segment_audio, sr)
                if features is not None:
                    speaker_features.append(features)
                    valid_segments.append({
                        "start": start_time,
                        "end": end_time,
                        "text": text,
                        "features": features
                    })
            
            if not speaker_features:
                return analysis
            
            # Cluster speakers using K-means
            features_matrix = np.array(speaker_features)
            
            # Determine optimal number of speakers (2-6 range)
            optimal_k = self._determine_optimal_speakers(features_matrix)
            analysis["num_speakers"] = optimal_k
            
            # Perform clustering
            kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
            speaker_labels = kmeans.fit_predict(features_matrix)
            
            # Create speaker profiles
            for speaker_id in range(optimal_k):
                speaker_mask = speaker_labels == speaker_id
                if np.any(speaker_mask):
                    speaker_segments = [seg for i, seg in enumerate(valid_segments) if speaker_mask[i]]
                    speaker_features_subset = features_matrix[speaker_mask]
                    
                    profile = {
                        "speaker_id": speaker_id,
                        "total_speaking_time": sum(seg["end"] - seg["start"] for seg in speaker_segments),
                        "num_segments": len(speaker_segments),
                        "avg_pitch": float(np.mean(speaker_features_subset[:, 0])),
                        "pitch_variance": float(np.var(speaker_features_subset[:, 0])),
                        "avg_energy": float(np.mean(speaker_features_subset[:, 1])),
                        "spectral_characteristics": {
                            "centroid": float(np.mean(speaker_features_subset[:, 2])),
                            "rolloff": float(np.mean(speaker_features_subset[:, 3])),
                            "mfcc_profile": speaker_features_subset[:, 4:17].mean(axis=0).tolist()
                        }
                    }
                    
                    analysis["speaker_profiles"][f"speaker_{speaker_id}"] = profile
            
            # Assign speaker labels to segments
            for i, segment in enumerate(valid_segments):
                segment["speaker_id"] = int(speaker_labels[i])
                segment["confidence"] = self._calculate_speaker_confidence(
                    segment["features"], kmeans.cluster_centers_[speaker_labels[i]]
                )
                analysis["speaker_segments"].append(segment)
            
            # Detect speaker changes
            analysis["speaker_changes"] = self._detect_speaker_changes(analysis["speaker_segments"])
            
            # Calculate overall confidence
            confidences = [seg["confidence"] for seg in analysis["speaker_segments"]]
            analysis["overall_confidence"] = float(np.mean(confidences)) if confidences else 0.0
            
            logger.info(f"Speaker identification complete: {optimal_k} speakers identified, "
                       f"confidence: {analysis['overall_confidence']:.2f}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in speaker identification: {e}")
            return {"error": str(e)}
    
    def filter_background_noise(self, audio_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Filter background noise to improve speech quality
        
        Args:
            audio_path: Path to input audio file
            output_path: Path for filtered audio output
        
        Returns:
            Noise filtering results
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            analysis = {
                "noise_profile": {},
                "filtering_applied": [],
                "quality_improvement": 0.0,
                "output_path": output_path
            }
            
            # Analyze noise characteristics
            noise_profile = self._analyze_noise_profile(y, sr)
            analysis["noise_profile"] = noise_profile
            
            # Apply noise reduction techniques
            filtered_audio = y.copy()
            
            # 1. Spectral gating (remove low-energy frequencies)
            if noise_profile["low_frequency_noise"] > 0.1:
                filtered_audio = self._apply_high_pass_filter(filtered_audio, sr, cutoff=80)
                analysis["filtering_applied"].append("high_pass_filter")
            
            # 2. Spectral subtraction for stationary noise
            if noise_profile["stationary_noise_level"] > 0.2:
                filtered_audio = self._apply_spectral_subtraction(filtered_audio, sr)
                analysis["filtering_applied"].append("spectral_subtraction")
            
            # 3. Adaptive filtering for non-stationary noise
            if noise_profile["non_stationary_noise"] > 0.15:
                filtered_audio = self._apply_adaptive_filter(filtered_audio, sr)
                analysis["filtering_applied"].append("adaptive_filter")
            
            # 4. Dynamic range compression
            if noise_profile["dynamic_range"] > 40:  # High dynamic range
                filtered_audio = self._apply_compression(filtered_audio)
                analysis["filtering_applied"].append("compression")
            
            # 5. Harmonic enhancement for speech
            filtered_audio = self._enhance_speech_harmonics(filtered_audio, sr)
            analysis["filtering_applied"].append("harmonic_enhancement")
            
            # Calculate quality improvement
            original_snr = self._calculate_snr(y)
            filtered_snr = self._calculate_snr(filtered_audio)
            analysis["quality_improvement"] = filtered_snr - original_snr
            
            # Save filtered audio if output path provided
            if output_path:
                librosa.output.write_wav(output_path, filtered_audio, sr)
                analysis["output_path"] = output_path
                logger.info(f"Filtered audio saved to: {output_path}")
            
            logger.info(f"Noise filtering complete. Quality improvement: {analysis['quality_improvement']:.2f} dB")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in noise filtering: {e}")
            return {"error": str(e)}
    
    def comprehensive_multimodal_analysis(self, 
                                        video_path: str, 
                                        audio_path: str,
                                        subtitle_segments: List[Dict]) -> Dict[str, Any]:
        """
        Perform comprehensive multi-modal analysis
        
        Args:
            video_path: Path to video file
            audio_path: Path to audio file  
            subtitle_segments: List of subtitle segments
        
        Returns:
            Comprehensive multi-modal analysis results
        """
        try:
            comprehensive_analysis = {
                "visual_analysis": {},
                "speaker_analysis": {},
                "audio_quality": {},
                "cross_modal_insights": {},
                "recommendations": []
            }
            
            # 1. Visual Context Analysis
            logger.info("Performing visual context analysis...")
            visual_results = self.analyze_visual_context(video_path, subtitle_segments)
            comprehensive_analysis["visual_analysis"] = visual_results
            
            # 2. Speaker Identification
            logger.info("Performing speaker identification...")
            speaker_results = self.identify_speakers(audio_path, subtitle_segments)
            comprehensive_analysis["speaker_analysis"] = speaker_results
            
            # 3. Audio Quality Assessment
            logger.info("Analyzing audio quality...")
            audio_quality = self._assess_audio_quality(audio_path)
            comprehensive_analysis["audio_quality"] = audio_quality
            
            # 4. Cross-modal correlation analysis
            logger.info("Analyzing cross-modal correlations...")
            cross_modal = self._analyze_cross_modal_correlations(
                visual_results, speaker_results, subtitle_segments
            )
            comprehensive_analysis["cross_modal_insights"] = cross_modal
            
            # 5. Generate actionable recommendations
            recommendations = self._generate_multimodal_recommendations(comprehensive_analysis)
            comprehensive_analysis["recommendations"] = recommendations
            
            logger.info("Comprehensive multi-modal analysis complete")
            return comprehensive_analysis
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            return {"error": str(e)}
    
    # Helper methods for visual analysis
    
    def _detect_scene_change(self, prev_frame: np.ndarray, curr_frame: np.ndarray, timestamp: float) -> Dict[str, Any]:
        """Detect scene changes using histogram comparison"""
        try:
            # Convert to grayscale for faster processing
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate histogram correlation
            prev_hist = cv2.calcHist([prev_gray], [0], None, [256], [0, 256])
            curr_hist = cv2.calcHist([curr_gray], [0], None, [256], [0, 256])
            
            correlation = cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_CORREL)
            
            # Threshold for scene change (lower correlation = more change)
            is_scene_change = correlation < 0.7
            
            return {
                "time": timestamp,
                "is_scene_change": is_scene_change,
                "correlation": float(correlation),
                "change_magnitude": 1.0 - correlation
            }
            
        except Exception:
            return {"time": timestamp, "is_scene_change": False, "correlation": 1.0}
    
    def _detect_faces(self, frame: np.ndarray, timestamp: float) -> List[Dict]:
        """Detect faces in frame"""
        try:
            if self.face_cascade is None:
                return []
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            face_list = []
            for (x, y, w, h) in faces:
                face_info = {
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "center": [int(x + w/2), int(y + h/2)],
                    "area": int(w * h),
                    "aspect_ratio": float(w / h) if h > 0 else 1.0
                }
                face_list.append(face_info)
            
            return face_list
            
        except Exception:
            return []
    
    def _identify_dominant_speaker(self, faces: List[Dict]) -> Optional[Dict]:
        """Identify the dominant speaker based on face size and position"""
        if not faces:
            return None
        
        # Find largest face (closest to camera, likely the speaker)
        dominant_face = max(faces, key=lambda f: f["area"])
        
        # Add speaker confidence based on size and position
        frame_center = [320, 240]  # Assume standard resolution center
        distance_from_center = np.sqrt(
            (dominant_face["center"][0] - frame_center[0]) ** 2 + 
            (dominant_face["center"][1] - frame_center[1]) ** 2
        )
        
        # Higher confidence for larger faces closer to center
        confidence = min(1.0, dominant_face["area"] / 10000) * max(0.1, 1.0 - distance_from_center / 400)
        
        return {
            **dominant_face,
            "speaker_confidence": confidence
        }
    
    def _analyze_visual_complexity(self, frame: np.ndarray, timestamp: float) -> Dict[str, Any]:
        """Analyze visual complexity of frame"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Edge detection for complexity measure
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            
            # Texture analysis using Local Binary Patterns
            # Simplified version using gradient magnitude
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            texture_complexity = np.std(gradient_magnitude)
            
            return {
                "time": timestamp,
                "edge_density": float(edge_density),
                "texture_complexity": float(texture_complexity),
                "overall_complexity": float(edge_density * texture_complexity / 100)
            }
            
        except Exception:
            return {"time": timestamp, "edge_density": 0, "texture_complexity": 0, "overall_complexity": 0}
    
    def _detect_text_overlay(self, frame: np.ndarray, timestamp: float) -> List[Dict]:
        """Detect text overlays in frame"""
        try:
            # Simple text detection using connected components
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to get binary image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Find connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
            
            text_regions = []
            for i in range(1, num_labels):  # Skip background
                x, y, w, h, area = stats[i]
                
                # Filter for text-like regions (aspect ratio and size)
                aspect_ratio = w / h if h > 0 else 0
                if 0.1 < aspect_ratio < 10 and 50 < area < 5000:
                    text_regions.append({
                        "time": timestamp,
                        "bbox": [int(x), int(y), int(w), int(h)],
                        "area": int(area),
                        "aspect_ratio": float(aspect_ratio)
                    })
            
            return text_regions
            
        except Exception:
            return []
    
    def _analyze_dominant_colors(self, frame: np.ndarray, timestamp: float) -> Dict[str, Any]:
        """Analyze dominant colors in frame"""
        try:
            # Reshape frame for K-means clustering
            pixels = frame.reshape(-1, 3)
            
            # Use K-means to find dominant colors
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            colors = kmeans.cluster_centers_.astype(int)
            labels = kmeans.labels_
            
            # Calculate color percentages
            color_percentages = []
            for i, color in enumerate(colors):
                percentage = np.sum(labels == i) / len(labels)
                color_percentages.append({
                    "color": color.tolist(),
                    "percentage": float(percentage)
                })
            
            return {
                "time": timestamp,
                "dominant_colors": color_percentages
            }
            
        except Exception:
            return {"time": timestamp, "dominant_colors": []}
    
    def _analyze_motion_intensity(self, prev_frame: np.ndarray, curr_frame: np.ndarray, timestamp: float) -> Dict[str, Any]:
        """Analyze motion intensity between frames"""
        try:
            # Convert to grayscale
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate optical flow
            flow = cv2.calcOpticalFlowPyrLK(
                prev_gray, curr_gray, 
                np.array([[x, y] for y in range(0, prev_gray.shape[0], 20) 
                         for x in range(0, prev_gray.shape[1], 20)], dtype=np.float32),
                None
            )[0]
            
            if flow is not None:
                # Calculate motion magnitude
                motion_magnitude = np.sqrt(flow[:, 0]**2 + flow[:, 1]**2)
                avg_motion = float(np.mean(motion_magnitude))
                max_motion = float(np.max(motion_magnitude))
            else:
                avg_motion = max_motion = 0.0
            
            return {
                "time": timestamp,
                "average_motion": avg_motion,
                "max_motion": max_motion,
                "motion_intensity": "high" if avg_motion > 5 else "medium" if avg_motion > 2 else "low"
            }
            
        except Exception:
            return {"time": timestamp, "average_motion": 0, "max_motion": 0, "motion_intensity": "low"}
    
    # Helper methods for speaker identification
    
    def _extract_speaker_features(self, audio_segment: np.ndarray, sr: int) -> Optional[np.ndarray]:
        """Extract speaker identification features from audio segment"""
        try:
            if len(audio_segment) < sr * 0.5:  # Too short
                return None
            
            # 1. Fundamental frequency (F0) - pitch
            pitches, magnitudes = librosa.piptrack(y=audio_segment, sr=sr)
            pitch_values = []
            for i in range(pitches.shape[1]):
                index = magnitudes[:, i].argmax()
                pitch = pitches[index, i]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            avg_pitch = np.mean(pitch_values) if pitch_values else 0
            
            # 2. Energy/RMS
            rms = librosa.feature.rms(y=audio_segment)[0]
            avg_energy = np.mean(rms)
            
            # 3. Spectral features
            spectral_centroid = librosa.feature.spectral_centroid(y=audio_segment, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio_segment, sr=sr)[0]
            
            # 4. MFCCs (vocal tract characteristics)
            mfccs = librosa.feature.mfcc(y=audio_segment, sr=sr, n_mfcc=13)
            mfcc_means = np.mean(mfccs, axis=1)
            
            # Combine features
            features = np.concatenate([
                [avg_pitch, avg_energy],
                [np.mean(spectral_centroid), np.mean(spectral_rolloff)],
                mfcc_means
            ])
            
            return features
            
        except Exception:
            return None
    
    def _determine_optimal_speakers(self, features_matrix: np.ndarray) -> int:
        """Determine optimal number of speakers using elbow method"""
        try:
            max_k = min(6, len(features_matrix) // 2)
            if max_k < 2:
                return 2
            
            inertias = []
            k_range = range(2, max_k + 1)
            
            for k in k_range:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans.fit(features_matrix)
                inertias.append(kmeans.inertia_)
            
            # Find elbow point (simplified)
            if len(inertias) >= 2:
                diffs = np.diff(inertias)
                elbow_idx = np.argmax(diffs) + 1  # +1 because diff reduces array size
                optimal_k = k_range[min(elbow_idx, len(k_range) - 1)]
            else:
                optimal_k = 2
            
            return optimal_k
            
        except Exception:
            return 2
    
    def _calculate_speaker_confidence(self, features: np.ndarray, cluster_center: np.ndarray) -> float:
        """Calculate confidence of speaker assignment"""
        try:
            # Use cosine similarity as confidence measure
            similarity = cosine_similarity([features], [cluster_center])[0][0]
            return max(0.0, min(1.0, similarity))
        except Exception:
            return 0.5
    
    def _detect_speaker_changes(self, speaker_segments: List[Dict]) -> List[Dict]:
        """Detect speaker changes in timeline"""
        changes = []
        
        for i in range(1, len(speaker_segments)):
            prev_speaker = speaker_segments[i-1]["speaker_id"]
            curr_speaker = speaker_segments[i]["speaker_id"]
            
            if prev_speaker != curr_speaker:
                changes.append({
                    "time": speaker_segments[i]["start"],
                    "from_speaker": prev_speaker,
                    "to_speaker": curr_speaker,
                    "confidence": min(speaker_segments[i-1]["confidence"], speaker_segments[i]["confidence"])
                })
        
        return changes
    
    # Helper methods for noise filtering
    
    def _analyze_noise_profile(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """Analyze noise characteristics in audio"""
        try:
            # Spectral analysis
            stft = librosa.stft(audio)
            magnitude = np.abs(stft)
            
            # Low frequency content (likely noise)
            low_freq_energy = np.mean(magnitude[:magnitude.shape[0]//8, :])
            total_energy = np.mean(magnitude)
            low_frequency_noise = low_freq_energy / total_energy if total_energy > 0 else 0
            
            # Stationary noise estimation (consistent across time)
            temporal_variance = np.var(np.mean(magnitude, axis=0))
            stationary_noise_level = 1.0 / (1.0 + temporal_variance)
            
            # Non-stationary noise
            non_stationary_noise = temporal_variance / np.mean(magnitude) if np.mean(magnitude) > 0 else 0
            
            # Dynamic range
            dynamic_range = 20 * np.log10(np.max(magnitude) / np.mean(magnitude)) if np.mean(magnitude) > 0 else 0
            
            return {
                "low_frequency_noise": float(low_frequency_noise),
                "stationary_noise_level": float(stationary_noise_level),
                "non_stationary_noise": float(non_stationary_noise),
                "dynamic_range": float(dynamic_range)
            }
            
        except Exception:
            return {"low_frequency_noise": 0, "stationary_noise_level": 0, "non_stationary_noise": 0, "dynamic_range": 0}
    
    def _apply_high_pass_filter(self, audio: np.ndarray, sr: int, cutoff: float = 80) -> np.ndarray:
        """Apply high-pass filter to remove low-frequency noise"""
        try:
            nyquist = sr // 2
            normalized_cutoff = cutoff / nyquist
            b, a = scipy.signal.butter(4, normalized_cutoff, btype='high')
            return scipy.signal.filtfilt(b, a, audio)
        except Exception:
            return audio
    
    def _apply_spectral_subtraction(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Apply spectral subtraction for noise reduction"""
        try:
            # Simplified spectral subtraction
            stft = librosa.stft(audio)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # Estimate noise from first 0.5 seconds (assumed to be quiet)
            noise_frames = min(20, magnitude.shape[1] // 4)
            noise_spectrum = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)
            
            # Subtract noise spectrum with oversubtraction factor
            alpha = 2.0
            enhanced_magnitude = magnitude - alpha * noise_spectrum
            
            # Ensure non-negative values
            enhanced_magnitude = np.maximum(enhanced_magnitude, 0.1 * magnitude)
            
            # Reconstruct audio
            enhanced_stft = enhanced_magnitude * np.exp(1j * phase)
            return librosa.istft(enhanced_stft)
            
        except Exception:
            return audio
    
    def _apply_adaptive_filter(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Apply adaptive filtering for non-stationary noise"""
        try:
            # Simple adaptive filter using moving average
            window_size = sr // 10  # 0.1 second window
            filtered = np.convolve(audio, np.ones(window_size) / window_size, mode='same')
            
            # Blend original and filtered based on local SNR
            local_snr = self._calculate_local_snr(audio, window_size)
            blend_factor = np.clip(local_snr / 10, 0, 1)  # Normalize SNR
            
            return audio * blend_factor + filtered * (1 - blend_factor)
            
        except Exception:
            return audio
    
    def _apply_compression(self, audio: np.ndarray, ratio: float = 4.0, threshold: float = -20) -> np.ndarray:
        """Apply dynamic range compression"""
        try:
            # Convert to dB
            audio_db = 20 * np.log10(np.abs(audio) + 1e-10)
            
            # Apply compression above threshold
            compressed_db = np.where(
                audio_db > threshold,
                threshold + (audio_db - threshold) / ratio,
                audio_db
            )
            
            # Convert back to linear
            gain = 10 ** ((compressed_db - audio_db) / 20)
            return audio * gain
            
        except Exception:
            return audio
    
    def _enhance_speech_harmonics(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Enhance speech harmonics"""
        try:
            # Apply gentle high-frequency boost for speech clarity
            nyquist = sr // 2
            # Boost 1-4 kHz range (important for speech intelligibility)
            b, a = scipy.signal.butter(2, [1000/nyquist, 4000/nyquist], btype='band')
            speech_band = scipy.signal.filtfilt(b, a, audio)
            
            # Blend enhanced band with original
            return audio + 0.3 * speech_band
            
        except Exception:
            return audio
    
    def _calculate_snr(self, audio: np.ndarray) -> float:
        """Calculate signal-to-noise ratio"""
        try:
            # Estimate signal power (top 75% of energy)
            powers = audio ** 2
            signal_power = np.percentile(powers, 75)
            
            # Estimate noise power (bottom 25% of energy)
            noise_power = np.percentile(powers, 25)
            
            if noise_power > 0:
                snr_db = 10 * np.log10(signal_power / noise_power)
            else:
                snr_db = 60  # High SNR if no noise detected
                
            return float(snr_db)
            
        except Exception:
            return 0.0
    
    def _calculate_local_snr(self, audio: np.ndarray, window_size: int) -> np.ndarray:
        """Calculate local SNR across audio"""
        try:
            # Calculate local energy
            local_energy = np.convolve(audio ** 2, np.ones(window_size), mode='same')
            
            # Estimate local noise (minimum energy in neighborhood)
            noise_window = window_size * 3
            local_noise = scipy.ndimage.minimum_filter1d(local_energy, noise_window)
            
            # Calculate SNR
            snr = 10 * np.log10((local_energy + 1e-10) / (local_noise + 1e-10))
            return snr
            
        except Exception:
            return np.zeros(len(audio))
    
    # Cross-modal analysis helpers
    
    def _calculate_scene_statistics(self, scene_changes: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics for scene changes"""
        if not scene_changes:
            return {}
        
        intervals = []
        for i in range(len(scene_changes) - 1):
            interval = scene_changes[i+1]["time"] - scene_changes[i]["time"]
            intervals.append(interval)
        
        return {
            "total_scenes": len(scene_changes),
            "average_scene_length": float(np.mean(intervals)) if intervals else 0,
            "scene_change_frequency": len(scene_changes) / scene_changes[-1]["time"] if scene_changes else 0
        }
    
    def _create_speaker_timeline(self, speaker_appearances: List[Dict]) -> List[Dict]:
        """Create timeline of speaker appearances"""
        timeline = []
        
        for appearance in speaker_appearances:
            if appearance.get("dominant_speaker"):
                timeline.append({
                    "time": appearance["time"],
                    "speaker_info": appearance["dominant_speaker"],
                    "num_faces": len(appearance["faces"])
                })
        
        return timeline
    
    def _align_visual_with_subtitles(self, visual_analysis: Dict, subtitle_segments: List[Dict]) -> List[Dict]:
        """Align visual events with subtitle segments"""
        aligned_data = []
        
        for segment in subtitle_segments:
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            
            # Find visual events within this time range
            segment_data = {
                "subtitle": segment,
                "visual_events": {
                    "scene_changes": [sc for sc in visual_analysis.get("scene_changes", []) 
                                    if start_time <= sc["time"] <= end_time],
                    "speaker_appearances": [sa for sa in visual_analysis.get("speaker_appearances", [])
                                          if start_time <= sa["time"] <= end_time],
                    "motion_intensity": [mi for mi in visual_analysis.get("motion_intensity", [])
                                       if start_time <= mi["time"] <= end_time]
                }
            }
            
            aligned_data.append(segment_data)
        
        return aligned_data
    
    def _assess_audio_quality(self, audio_path: str) -> Dict[str, Any]:
        """Assess overall audio quality"""
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Calculate quality metrics
            snr = self._calculate_snr(y)
            
            # Frequency response analysis
            stft = librosa.stft(y)
            magnitude = np.abs(stft)
            freq_response = np.mean(magnitude, axis=1)
            
            # Speech band energy (300-3400 Hz for telephone quality)
            speech_band_start = int(300 * magnitude.shape[0] / (sr/2))
            speech_band_end = int(3400 * magnitude.shape[0] / (sr/2))
            speech_energy = np.mean(freq_response[speech_band_start:speech_band_end])
            total_energy = np.mean(freq_response)
            
            speech_clarity = speech_energy / total_energy if total_energy > 0 else 0
            
            return {
                "snr_db": float(snr),
                "speech_clarity": float(speech_clarity),
                "dynamic_range": float(20 * np.log10(np.max(y) / np.std(y))),
                "overall_quality": "excellent" if snr > 20 else "good" if snr > 15 else "fair" if snr > 10 else "poor"
            }
            
        except Exception:
            return {"snr_db": 0, "speech_clarity": 0, "dynamic_range": 0, "overall_quality": "unknown"}
    
    def _analyze_cross_modal_correlations(self, visual_results: Dict, speaker_results: Dict, subtitle_segments: List[Dict]) -> Dict[str, Any]:
        """Analyze correlations between visual and audio modalities"""
        correlations = {
            "visual_speaker_alignment": 0.0,
            "scene_speech_correlation": 0.0,
            "motion_energy_correlation": 0.0,
            "multimodal_confidence": 0.0
        }
        
        try:
            # Visual-speaker alignment
            speaker_changes = speaker_results.get("speaker_changes", [])
            scene_changes = visual_results.get("scene_changes", [])
            
            # Count how many speaker changes align with scene changes (within 2 seconds)
            aligned_changes = 0
            for speaker_change in speaker_changes:
                for scene_change in scene_changes:
                    if abs(speaker_change["time"] - scene_change["time"]) < 2.0:
                        aligned_changes += 1
                        break
            
            if speaker_changes:
                correlations["visual_speaker_alignment"] = aligned_changes / len(speaker_changes)
            
            # Overall multimodal confidence
            audio_confidence = speaker_results.get("overall_confidence", 0)
            visual_confidence = len(visual_results.get("speaker_appearances", [])) / max(1, len(subtitle_segments))
            
            correlations["multimodal_confidence"] = (audio_confidence + visual_confidence) / 2
            
        except Exception as e:
            logger.warning(f"Error in cross-modal analysis: {e}")
        
        return correlations
    
    def _generate_multimodal_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate actionable recommendations based on multimodal analysis"""
        recommendations = []
        
        # Audio quality recommendations
        audio_quality = analysis.get("audio_quality", {})
        snr = audio_quality.get("snr_db", 0)
        
        if snr < 15:
            recommendations.append({
                "category": "audio_quality",
                "priority": "high",
                "issue": "Low audio quality detected",
                "recommendation": "Apply noise filtering and audio enhancement",
                "expected_improvement": "Better speech recognition accuracy"
            })
        
        # Speaker identification recommendations  
        speaker_analysis = analysis.get("speaker_analysis", {})
        speaker_confidence = speaker_analysis.get("overall_confidence", 0)
        
        if speaker_confidence < 0.7:
            recommendations.append({
                "category": "speaker_identification", 
                "priority": "medium",
                "issue": "Low speaker identification confidence",
                "recommendation": "Use visual cues to improve speaker tracking",
                "expected_improvement": "Better speaker-specific subtitle formatting"
            })
        
        # Visual context recommendations
        visual_analysis = analysis.get("visual_analysis", {})
        scene_changes = visual_analysis.get("scene_changes", [])
        
        if len(scene_changes) > 0:
            avg_scene_length = visual_analysis.get("scene_statistics", {}).get("average_scene_length", 0)
            
            if avg_scene_length < 5:  # Very short scenes
                recommendations.append({
                    "category": "segmentation",
                    "priority": "low", 
                    "issue": "Frequent scene changes detected",
                    "recommendation": "Consider scene-aware subtitle segmentation",
                    "expected_improvement": "Better subtitle timing alignment with visual content"
                })
        
        # Cross-modal recommendations
        cross_modal = analysis.get("cross_modal_insights", {})
        multimodal_confidence = cross_modal.get("multimodal_confidence", 0)
        
        if multimodal_confidence > 0.8:
            recommendations.append({
                "category": "quality",
                "priority": "info",
                "issue": "High multimodal consistency",
                "recommendation": "Current processing pipeline is well-optimized",
                "expected_improvement": "Maintain current quality standards"
            })
        
        return recommendations