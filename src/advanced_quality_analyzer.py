"""
Advanced Quality Analyzer
Enhanced quality metrics including BLEU scores, confidence analysis, and sentiment preservation
"""

import re
import math
import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Union
from collections import Counter, defaultdict
from pathlib import Path

# Core dependencies
from .config_manager import ConfigManager
from .logger import get_logger
from .exceptions import ValidationError, SubtitleGenerationError

logger = get_logger(__name__)

class AdvancedQualityAnalyzer:
    """Advanced subtitle quality analysis with BLEU scores, confidence metrics, and sentiment analysis"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.sentiment_analyzer = None
        self.language_detector = None
        self._initialize_nlp_models()
    
    def _initialize_nlp_models(self):
        """Initialize NLP models for advanced analysis"""
        try:
            # Import optional dependencies for advanced features
            import nltk
            from textblob import TextBlob
            
            # Download required NLTK data if not present
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                logger.info("Downloading NLTK punkt tokenizer...")
                nltk.download('punkt', quiet=True)
            
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                logger.info("Downloading NLTK stopwords...")
                nltk.download('stopwords', quiet=True)
            
            self.sentiment_analyzer = TextBlob
            logger.info("✅ Advanced NLP models initialized")
            
        except ImportError as e:
            logger.warning(f"Advanced NLP features not available: {e}")
            logger.info("Install with: pip install nltk textblob")
    
    def calculate_bleu_score(self, reference: str, hypothesis: str, max_n: int = 4) -> Dict[str, float]:
        """
        Calculate BLEU score for translation quality assessment
        
        Args:
            reference: Reference (original) text
            hypothesis: Generated (translated) text  
            max_n: Maximum n-gram size (default: 4)
        
        Returns:
            Dict containing BLEU scores and component metrics
        """
        try:
            # Tokenize texts
            ref_tokens = self._tokenize_text(reference.lower())
            hyp_tokens = self._tokenize_text(hypothesis.lower())
            
            if not ref_tokens or not hyp_tokens:
                return {"bleu_score": 0.0, "brevity_penalty": 0.0, "precision_scores": []}
            
            # Calculate precision scores for each n-gram
            precision_scores = []
            
            for n in range(1, max_n + 1):
                ref_ngrams = self._get_ngrams(ref_tokens, n)
                hyp_ngrams = self._get_ngrams(hyp_tokens, n)
                
                if not hyp_ngrams:
                    precision_scores.append(0.0)
                    continue
                
                # Count matching n-grams
                matches = 0
                for ngram in hyp_ngrams:
                    if ngram in ref_ngrams:
                        matches += min(hyp_ngrams[ngram], ref_ngrams[ngram])
                
                precision = matches / sum(hyp_ngrams.values())
                precision_scores.append(precision)
            
            # Calculate brevity penalty
            ref_len = len(ref_tokens)
            hyp_len = len(hyp_tokens)
            
            if hyp_len > ref_len:
                brevity_penalty = 1.0
            else:
                brevity_penalty = math.exp(1 - ref_len / hyp_len) if hyp_len > 0 else 0.0
            
            # Calculate geometric mean of precision scores
            if all(p > 0 for p in precision_scores):
                geometric_mean = math.exp(sum(math.log(p) for p in precision_scores) / len(precision_scores))
            else:
                geometric_mean = 0.0
            
            bleu_score = brevity_penalty * geometric_mean
            
            return {
                "bleu_score": bleu_score,
                "brevity_penalty": brevity_penalty,
                "precision_scores": precision_scores,
                "reference_length": ref_len,
                "hypothesis_length": hyp_len,
                "geometric_mean": geometric_mean
            }
            
        except Exception as e:
            logger.error(f"Error calculating BLEU score: {e}")
            return {"bleu_score": 0.0, "brevity_penalty": 0.0, "precision_scores": []}
    
    def analyze_speech_confidence(self, subtitle_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze speech recognition confidence metrics
        
        Args:
            subtitle_data: List of subtitle entries with timing and text
        
        Returns:
            Confidence analysis metrics
        """
        try:
            metrics = {
                "average_confidence": 0.0,
                "confidence_distribution": {},
                "low_confidence_segments": [],
                "high_confidence_segments": [],
                "confidence_by_duration": {},
                "word_confidence_stats": {}
            }
            
            if not subtitle_data:
                return metrics
            
            confidence_scores = []
            low_threshold = 0.6
            high_threshold = 0.85
            
            for entry in subtitle_data:
                # Extract text and timing
                text = entry.get('text', '')
                duration = entry.get('duration', 0)
                start_time = entry.get('start', 0)
                
                # Calculate confidence based on text characteristics
                confidence = self._estimate_text_confidence(text)
                confidence_scores.append(confidence)
                
                # Categorize segments
                if confidence < low_threshold:
                    metrics["low_confidence_segments"].append({
                        "text": text,
                        "confidence": confidence,
                        "start_time": start_time,
                        "duration": duration
                    })
                elif confidence > high_threshold:
                    metrics["high_confidence_segments"].append({
                        "text": text,
                        "confidence": confidence,
                        "start_time": start_time,
                        "duration": duration
                    })
                
                # Group by duration ranges
                duration_range = self._get_duration_range(duration)
                if duration_range not in metrics["confidence_by_duration"]:
                    metrics["confidence_by_duration"][duration_range] = []
                metrics["confidence_by_duration"][duration_range].append(confidence)
            
            # Calculate overall statistics
            if confidence_scores:
                metrics["average_confidence"] = np.mean(confidence_scores)
                metrics["confidence_std"] = np.std(confidence_scores)
                metrics["median_confidence"] = np.median(confidence_scores)
                
                # Distribution analysis
                for score in confidence_scores:
                    range_key = f"{int(score * 10) / 10:.1f}-{int(score * 10) / 10 + 0.1:.1f}"
                    metrics["confidence_distribution"][range_key] = metrics["confidence_distribution"].get(range_key, 0) + 1
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing speech confidence: {e}")
            return {}
    
    def analyze_sentiment_preservation(self, original_text: str, translated_text: str) -> Dict[str, Any]:
        """
        Analyze sentiment preservation in translation
        
        Args:
            original_text: Original subtitle text
            translated_text: Translated subtitle text
        
        Returns:
            Sentiment analysis results
        """
        try:
            if not self.sentiment_analyzer:
                logger.warning("Sentiment analyzer not available")
                return {"sentiment_preserved": None, "original_sentiment": None, "translated_sentiment": None}
            
            # Analyze original text sentiment
            original_blob = self.sentiment_analyzer(original_text)
            original_sentiment = {
                "polarity": original_blob.sentiment.polarity,
                "subjectivity": original_blob.sentiment.subjectivity,
                "classification": self._classify_sentiment(original_blob.sentiment.polarity)
            }
            
            # Analyze translated text sentiment  
            translated_blob = self.sentiment_analyzer(translated_text)
            translated_sentiment = {
                "polarity": translated_blob.sentiment.polarity,
                "subjectivity": translated_blob.sentiment.subjectivity,
                "classification": self._classify_sentiment(translated_blob.sentiment.polarity)
            }
            
            # Calculate sentiment preservation metrics
            polarity_diff = abs(original_sentiment["polarity"] - translated_sentiment["polarity"])
            subjectivity_diff = abs(original_sentiment["subjectivity"] - translated_sentiment["subjectivity"])
            
            # Determine if sentiment is preserved (threshold: 0.3 for polarity, 0.4 for subjectivity)
            sentiment_preserved = (
                polarity_diff < 0.3 and 
                subjectivity_diff < 0.4 and
                original_sentiment["classification"] == translated_sentiment["classification"]
            )
            
            return {
                "sentiment_preserved": sentiment_preserved,
                "original_sentiment": original_sentiment,
                "translated_sentiment": translated_sentiment,
                "polarity_difference": polarity_diff,
                "subjectivity_difference": subjectivity_diff,
                "preservation_score": 1.0 - (polarity_diff + subjectivity_diff) / 2
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment preservation: {e}")
            return {"sentiment_preserved": None, "error": str(e)}
    
    def comprehensive_quality_assessment(self, 
                                       original_subtitles: str, 
                                       processed_subtitles: str,
                                       language_pair: Tuple[str, str] = None) -> Dict[str, Any]:
        """
        Perform comprehensive quality assessment combining all metrics
        
        Args:
            original_subtitles: Original subtitle content
            processed_subtitles: Processed/translated subtitle content
            language_pair: (source_lang, target_lang) tuple
        
        Returns:
            Comprehensive quality metrics
        """
        try:
            assessment = {
                "overall_score": 0.0,
                "component_scores": {},
                "recommendations": [],
                "quality_grade": "Unknown"
            }
            
            # Parse subtitle entries
            original_entries = self._parse_srt_entries(original_subtitles)
            processed_entries = self._parse_srt_entries(processed_subtitles)
            
            # 1. BLEU Score Analysis (if translation)
            if language_pair and language_pair[0] != language_pair[1]:
                original_text = " ".join([entry.get('text', '') for entry in original_entries])
                processed_text = " ".join([entry.get('text', '') for entry in processed_entries])
                
                bleu_metrics = self.calculate_bleu_score(original_text, processed_text)
                assessment["component_scores"]["bleu"] = bleu_metrics["bleu_score"]
                
                if bleu_metrics["bleu_score"] < 0.3:
                    assessment["recommendations"].append("Translation quality is low - consider reviewing language model")
            
            # 2. Speech Confidence Analysis
            confidence_metrics = self.analyze_speech_confidence(processed_entries)
            assessment["component_scores"]["confidence"] = confidence_metrics.get("average_confidence", 0.0)
            
            if confidence_metrics.get("average_confidence", 0) < 0.7:
                assessment["recommendations"].append("Low confidence detected - consider audio quality improvements")
            
            # 3. Sentiment Preservation (if translation)
            if language_pair and language_pair[0] != language_pair[1]:
                original_text = " ".join([entry.get('text', '') for entry in original_entries])
                processed_text = " ".join([entry.get('text', '') for entry in processed_entries])
                
                sentiment_analysis = self.analyze_sentiment_preservation(original_text, processed_text)
                assessment["component_scores"]["sentiment"] = sentiment_analysis.get("preservation_score", 0.0)
                
                if not sentiment_analysis.get("sentiment_preserved", True):
                    assessment["recommendations"].append("Sentiment not well preserved in translation")
            
            # 4. Timing and Synchronization Quality
            timing_score = self._analyze_timing_quality(processed_entries)
            assessment["component_scores"]["timing"] = timing_score
            
            if timing_score < 0.8:
                assessment["recommendations"].append("Timing synchronization needs improvement")
            
            # 5. Text Quality Metrics
            text_quality = self._analyze_text_quality(processed_entries)
            assessment["component_scores"]["text_quality"] = text_quality
            
            # Calculate overall score (weighted average)
            weights = {
                "bleu": 0.3,
                "confidence": 0.25,
                "sentiment": 0.15,
                "timing": 0.2,
                "text_quality": 0.1
            }
            
            total_weight = 0
            weighted_sum = 0
            
            for metric, score in assessment["component_scores"].items():
                if metric in weights and score is not None:
                    weighted_sum += weights[metric] * score
                    total_weight += weights[metric]
            
            if total_weight > 0:
                assessment["overall_score"] = weighted_sum / total_weight
            
            # Assign quality grade
            score = assessment["overall_score"]
            if score >= 0.9:
                assessment["quality_grade"] = "Excellent"
            elif score >= 0.8:
                assessment["quality_grade"] = "Good"
            elif score >= 0.7:
                assessment["quality_grade"] = "Fair"
            elif score >= 0.6:
                assessment["quality_grade"] = "Poor"
            else:
                assessment["quality_grade"] = "Very Poor"
            
            # Add general recommendations
            if not assessment["recommendations"]:
                assessment["recommendations"].append("Quality meets production standards")
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error in comprehensive quality assessment: {e}")
            return {"overall_score": 0.0, "error": str(e)}
    
    # Helper methods
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text for BLEU score calculation"""
        # Simple tokenization - split on whitespace and punctuation
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def _get_ngrams(self, tokens: List[str], n: int) -> Counter:
        """Extract n-grams from tokenized text"""
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngrams.append(tuple(tokens[i:i + n]))
        return Counter(ngrams)
    
    def _estimate_text_confidence(self, text: str) -> float:
        """Estimate confidence based on text characteristics"""
        if not text or not text.strip():
            return 0.0
        
        # Factors that indicate high confidence
        confidence = 1.0
        
        # Penalize for common OCR/ASR errors
        if re.search(r'[^\w\s\.,!?\-\'\"()]', text):  # Strange characters
            confidence -= 0.1
        
        if len(text.split()) < 2:  # Very short utterances
            confidence -= 0.1
        
        if text.isupper() or text.islower():  # No proper capitalization
            confidence -= 0.05
        
        # Penalize for repeated characters/words
        words = text.split()
        if len(set(words)) < len(words) * 0.7:  # High repetition
            confidence -= 0.1
        
        # Bonus for proper punctuation
        if re.search(r'[.!?]$', text.strip()):
            confidence += 0.05
        
        return max(0.0, min(1.0, confidence))
    
    def _get_duration_range(self, duration: float) -> str:
        """Get duration range category"""
        if duration < 1:
            return "0-1s"
        elif duration < 3:
            return "1-3s"
        elif duration < 5:
            return "3-5s"
        elif duration < 10:
            return "5-10s"
        else:
            return "10s+"
    
    def _classify_sentiment(self, polarity: float) -> str:
        """Classify sentiment based on polarity score"""
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"
    
    def _parse_srt_entries(self, srt_content: str) -> List[Dict]:
        """Parse SRT content into structured entries"""
        entries = []
        if not srt_content:
            return entries
        
        blocks = srt_content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    # Parse timestamp
                    timestamp_match = re.match(
                        r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})',
                        lines[1]
                    )
                    
                    if timestamp_match:
                        start_time = self._timestamp_to_seconds(timestamp_match.group(1))
                        end_time = self._timestamp_to_seconds(timestamp_match.group(2))
                        text = '\n'.join(lines[2:])
                        
                        entries.append({
                            'start': start_time,
                            'end': end_time,
                            'duration': end_time - start_time,
                            'text': text
                        })
                except:
                    continue
        
        return entries
    
    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert timestamp to seconds"""
        try:
            timestamp = timestamp.replace(',', '.')
            parts = timestamp.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except:
            return 0.0
    
    def _analyze_timing_quality(self, entries: List[Dict]) -> float:
        """Analyze timing quality of subtitles"""
        if not entries:
            return 0.0
        
        score = 1.0
        
        for entry in entries:
            duration = entry.get('duration', 0)
            text = entry.get('text', '')
            
            # Check reading speed (industry standard: 20-25 CPS)
            if duration > 0:
                cps = len(text) / duration
                if cps > 25:  # Too fast
                    score -= 0.05
                elif cps < 5:  # Too slow
                    score -= 0.03
            
            # Check minimum duration
            if duration < 0.5:  # Too short
                score -= 0.02
            elif duration > 10:  # Too long
                score -= 0.02
        
        return max(0.0, score)
    
    def _analyze_text_quality(self, entries: List[Dict]) -> float:
        """Analyze text quality of subtitles"""
        if not entries:
            return 0.0
        
        total_chars = 0
        total_words = 0
        quality_score = 1.0
        
        for entry in entries:
            text = entry.get('text', '').strip()
            if not text:
                quality_score -= 0.05
                continue
            
            chars = len(text)
            words = len(text.split())
            total_chars += chars
            total_words += words
            
            # Check for proper capitalization
            if text[0].islower() and text[0].isalpha():
                quality_score -= 0.01
            
            # Check for proper punctuation
            if not re.search(r'[.!?]$', text):
                quality_score -= 0.01
        
        # Check average length
        if total_words > 0:
            avg_words = total_words / len(entries)
            if avg_words < 2:  # Too short
                quality_score -= 0.1
            elif avg_words > 15:  # Too long
                quality_score -= 0.1
        
        return max(0.0, quality_score)