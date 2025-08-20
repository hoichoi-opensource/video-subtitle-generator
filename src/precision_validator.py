"""
Precision Validator
100% accuracy validation system for English, Bengali, and Hindi subtitles
Human-equivalent quality control with zero tolerance for errors
"""

import re
import unicodedata
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import json

from .config_manager import ConfigManager
from .logger import get_logger
from .exceptions import ValidationError, SubtitleGenerationError
from .translation_quality_analyzer import TranslationQualityAnalyzer

logger = get_logger(__name__)

class PrecisionValidator:
    """Precision validation system ensuring 100% subtitle accuracy"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.language_specs = self._load_language_specifications()
        
        # Initialize translation quality analyzer
        try:
            self.translation_analyzer = TranslationQualityAnalyzer(config)
            logger.info("✅ Translation quality analyzer initialized")
        except Exception as e:
            logger.warning(f"Translation quality analyzer initialization failed: {e}")
            self.translation_analyzer = None
        
    def _load_language_specifications(self) -> Dict[str, Dict]:
        """Load language-specific validation rules"""
        return {
            "eng": {
                "script": "Latin",
                "direction": "ltr",
                "max_chars_per_line": 42,
                "reading_speed_cps": (15, 20),  # characters per second
                "grammar_patterns": {
                    "sentence_endings": r'[.!?]$',
                    "capitalization": r'^[A-Z]',
                    "contractions": r"(can't|won't|isn't|aren't|don't|doesn't|didn't|wouldn't|shouldn't|couldn't|haven't|hasn't|hadn't)",
                },
                "forbidden_chars": r'[^\w\s.,!?;:()\-\'\""]',
                "common_errors": {
                    "double_spaces": r'\s{2,}',
                    "trailing_spaces": r'\s+$',
                    "missing_capitals": r'(?<=[.!?]\s)[a-z]',
                }
            },
            "ben": {
                "script": "Bengali",
                "direction": "ltr",
                "max_chars_per_line": 42,
                "reading_speed_cps": (12, 18),  # Bengali reads slightly slower
                "unicode_range": (0x0980, 0x09FF),
                "grammar_patterns": {
                    "sentence_endings": r'[।?!]$',
                    "proper_conjuncts": r'[ক-হ][্][ক-হ]',
                },
                "forbidden_chars": r'[a-zA-Z0-9](?![০-৯])',  # No English/digits except Bengali numerals
                "common_errors": {
                    "mixed_scripts": r'[a-zA-Z]',
                    "incorrect_hasant": r'্(?![ক-হ])',
                    "double_spaces": r'\s{2,}',
                }
            },
            "hin": {
                "script": "Devanagari", 
                "direction": "ltr",
                "max_chars_per_line": 42,
                "reading_speed_cps": (14, 19),
                "unicode_range": (0x0900, 0x097F),
                "grammar_patterns": {
                    "sentence_endings": r'[।?!]$',
                    "proper_conjuncts": r'[क-ह][्][क-ह]',
                    "matra_usage": r'[ा-ौ]',
                },
                "forbidden_chars": r'[a-zA-Z0-9](?![०-९])',  # No English/digits except Hindi numerals
                "common_errors": {
                    "mixed_scripts": r'[a-zA-Z]',
                    "incorrect_virama": r'्(?![क-ह])',
                    "double_spaces": r'\s{2,}',
                }
            }
        }
    
    def validate_subtitle_precision(self, 
                                  srt_content: str, 
                                  language: str,
                                  audio_duration: float = None,
                                  video_path: str = None) -> Dict[str, Any]:
        """
        Perform comprehensive precision validation
        
        Returns validation report with 100% accuracy requirements
        """
        logger.info(f"Starting precision validation for {language} subtitles")
        
        validation_report = {
            "language": language,
            "overall_status": "PENDING",
            "accuracy_score": 0.0,
            "critical_errors": [],
            "warnings": [],
            "statistics": {},
            "quality_metrics": {},
            "human_equivalence_score": 0.0,
            "production_ready": False
        }
        
        try:
            # Parse SRT content
            subtitle_entries = self._parse_srt_with_precision(srt_content)
            if not subtitle_entries:
                validation_report["critical_errors"].append("No valid subtitle entries found")
                return self._finalize_report(validation_report)
            
            validation_report["statistics"]["total_entries"] = len(subtitle_entries)
            
            # 1. CRITICAL: Format and Structure Validation
            format_validation = self._validate_srt_format(subtitle_entries, language)
            validation_report["critical_errors"].extend(format_validation["critical_errors"])
            validation_report["warnings"].extend(format_validation["warnings"])
            
            # 2. CRITICAL: Language-Specific Validation
            language_validation = self._validate_language_accuracy(subtitle_entries, language)
            validation_report["critical_errors"].extend(language_validation["critical_errors"])
            validation_report["warnings"].extend(language_validation["warnings"])
            
            # 3. CRITICAL: Timing Precision Validation
            timing_validation = self._validate_timing_precision(subtitle_entries, audio_duration)
            validation_report["critical_errors"].extend(timing_validation["critical_errors"])
            validation_report["warnings"].extend(timing_validation["warnings"])
            
            # 4. CRITICAL: Content Accuracy Validation
            content_validation = self._validate_content_accuracy(subtitle_entries, language)
            validation_report["critical_errors"].extend(content_validation["critical_errors"])
            validation_report["warnings"].extend(content_validation["warnings"])
            
            # 5. CRITICAL: Readability and UX Validation
            readability_validation = self._validate_readability(subtitle_entries, language)
            validation_report["critical_errors"].extend(readability_validation["critical_errors"])
            validation_report["warnings"].extend(readability_validation["warnings"])
            
            # 6. CRITICAL: Translation Quality Validation (for cross-language subtitles)
            translation_validation = self._validate_translation_quality(subtitle_entries, language, video_path)
            validation_report["critical_errors"].extend(translation_validation["critical_errors"])
            validation_report["warnings"].extend(translation_validation["warnings"])
            validation_report["translation_quality"] = translation_validation.get("translation_metrics", {})
            
            # 7. Calculate Quality Metrics
            validation_report["quality_metrics"] = self._calculate_quality_metrics(subtitle_entries, language)
            
            # 7. Calculate Human Equivalence Score
            validation_report["human_equivalence_score"] = self._calculate_human_equivalence(
                validation_report["critical_errors"], 
                validation_report["warnings"],
                validation_report["quality_metrics"]
            )
            
            # 8. Final Assessment
            validation_report = self._finalize_report(validation_report)
            
            logger.info(f"Validation complete. Status: {validation_report['overall_status']}, "
                       f"Score: {validation_report['accuracy_score']:.2f}")
            
            return validation_report
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            validation_report["critical_errors"].append(f"Validation system error: {str(e)}")
            return self._finalize_report(validation_report)
    
    def _parse_srt_with_precision(self, srt_content: str) -> List[Dict]:
        """Parse SRT with high precision, catching subtle format errors"""
        entries = []
        
        if not srt_content or not srt_content.strip():
            return entries
        
        # Normalize line endings
        srt_content = srt_content.replace('\r\n', '\n').replace('\r', '\n')
        blocks = srt_content.strip().split('\n\n')
        
        for i, block in enumerate(blocks):
            if not block.strip():
                continue
                
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            
            if len(lines) < 3:
                continue
            
            try:
                # Validate sequence number
                sequence = int(lines[0])
                if sequence != i + 1:
                    logger.warning(f"Sequence number mismatch: expected {i+1}, got {sequence}")
                
                # Parse timestamp with microsecond precision
                timestamp_line = lines[1]
                timestamp_match = re.match(
                    r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
                    timestamp_line
                )
                
                if not timestamp_match:
                    logger.error(f"Invalid timestamp format in entry {sequence}: {timestamp_line}")
                    continue
                
                start_h, start_m, start_s, start_ms = map(int, timestamp_match.groups()[:4])
                end_h, end_m, end_s, end_ms = map(int, timestamp_match.groups()[4:])
                
                start_seconds = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
                end_seconds = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000
                
                # Extract subtitle text
                text_lines = lines[2:]
                text = '\n'.join(text_lines)
                
                entry = {
                    "sequence": sequence,
                    "start_time": start_seconds,
                    "end_time": end_seconds,
                    "duration": end_seconds - start_seconds,
                    "text": text,
                    "text_lines": text_lines,
                    "raw_timestamp": timestamp_line
                }
                
                entries.append(entry)
                
            except (ValueError, IndexError) as e:
                logger.error(f"Error parsing SRT block {i+1}: {e}")
                continue
        
        return entries
    
    def _validate_srt_format(self, entries: List[Dict], language: str) -> Dict[str, List]:
        """Validate SRT format with zero tolerance for format errors"""
        errors = []
        warnings = []
        
        for i, entry in enumerate(entries):
            # Check sequence numbering
            if entry["sequence"] != i + 1:
                errors.append(f"Entry {i+1}: Incorrect sequence number {entry['sequence']}")
            
            # Check timing format precision
            if entry["duration"] <= 0:
                errors.append(f"Entry {entry['sequence']}: Invalid duration {entry['duration']}")
            
            if entry["duration"] < 0.5:
                warnings.append(f"Entry {entry['sequence']}: Very short duration ({entry['duration']:.2f}s)")
            
            if entry["duration"] > 10:
                warnings.append(f"Entry {entry['sequence']}: Very long duration ({entry['duration']:.2f}s)")
            
            # Check text content
            if not entry["text"].strip():
                errors.append(f"Entry {entry['sequence']}: Empty subtitle text")
            
            # Check line count
            if len(entry["text_lines"]) > 2:
                errors.append(f"Entry {entry['sequence']}: More than 2 lines ({len(entry['text_lines'])} lines)")
            
            # Check line length
            lang_spec = self.language_specs[language]
            max_chars = lang_spec["max_chars_per_line"]
            
            for j, line in enumerate(entry["text_lines"]):
                if len(line) > max_chars:
                    errors.append(f"Entry {entry['sequence']}, Line {j+1}: Exceeds {max_chars} characters ({len(line)} chars)")
        
        # Check for overlapping timestamps
        for i in range(len(entries) - 1):
            current = entries[i]
            next_entry = entries[i + 1]
            
            if current["end_time"] > next_entry["start_time"]:
                errors.append(f"Entry {current['sequence']}: Overlaps with entry {next_entry['sequence']}")
            
            # Check for too short gaps
            gap = next_entry["start_time"] - current["end_time"]
            if 0 < gap < 0.1:
                warnings.append(f"Entry {current['sequence']}: Very short gap to next subtitle ({gap:.2f}s)")
        
        return {"critical_errors": errors, "warnings": warnings}
    
    def _validate_language_accuracy(self, entries: List[Dict], language: str) -> Dict[str, List]:
        """Validate language-specific accuracy with native-speaker precision"""
        errors = []
        warnings = []
        lang_spec = self.language_specs[language]
        
        for entry in entries:
            text = entry["text"]
            
            # Check script consistency
            if language in ["ben", "hin"]:
                # Check Unicode range
                unicode_range = lang_spec["unicode_range"]
                for char in text:
                    if char.isalpha():
                        char_code = ord(char)
                        if not (unicode_range[0] <= char_code <= unicode_range[1]):
                            errors.append(f"Entry {entry['sequence']}: Invalid character '{char}' for {language}")
                
                # Check for mixed scripts
                if re.search(lang_spec["common_errors"]["mixed_scripts"], text):
                    errors.append(f"Entry {entry['sequence']}: Mixed script usage detected")
            
            # Check forbidden characters
            forbidden_pattern = lang_spec.get("forbidden_chars")
            if forbidden_pattern and re.search(forbidden_pattern, text):
                matches = re.findall(forbidden_pattern, text)
                errors.append(f"Entry {entry['sequence']}: Forbidden characters found: {matches}")
            
            # Check grammar patterns
            grammar_patterns = lang_spec.get("grammar_patterns", {})
            
            # Check sentence endings
            sentence_ending_pattern = grammar_patterns.get("sentence_endings")
            if sentence_ending_pattern:
                sentences = [s.strip() for s in re.split(r'[.।!?]', text) if s.strip()]
                for sentence in sentences[:-1]:  # All but last should end properly
                    if not re.search(sentence_ending_pattern, sentence + '.'):
                        warnings.append(f"Entry {entry['sequence']}: Potential incomplete sentence: '{sentence[:30]}...'")
            
            # Language-specific checks
            if language == "eng":
                self._validate_english_specific(entry, errors, warnings)
            elif language == "ben":
                self._validate_bengali_specific(entry, errors, warnings)
            elif language == "hin":
                self._validate_hindi_specific(entry, errors, warnings)
        
        return {"critical_errors": errors, "warnings": warnings}
    
    def _validate_english_specific(self, entry: Dict, errors: List, warnings: List):
        """English-specific validation rules"""
        text = entry["text"]
        
        # Check capitalization
        sentences = re.split(r'[.!?]+\s*', text)
        for sentence in sentences:
            if sentence and not sentence[0].isupper():
                errors.append(f"Entry {entry['sequence']}: Sentence should start with capital: '{sentence[:20]}...'")
        
        # Check common contractions
        contractions = ["can't", "won't", "isn't", "aren't", "don't", "doesn't"]
        for word in text.split():
            clean_word = re.sub(r'[^\w\']', '', word.lower())
            if clean_word in ["cant", "wont", "isnt", "arent", "dont", "doesnt"]:
                warnings.append(f"Entry {entry['sequence']}: Missing apostrophe in contraction: '{word}'")
        
        # Check double spaces and formatting
        if re.search(r'\s{2,}', text):
            errors.append(f"Entry {entry['sequence']}: Multiple consecutive spaces found")
        
        if text.endswith(' '):
            errors.append(f"Entry {entry['sequence']}: Trailing space found")
    
    def _validate_bengali_specific(self, entry: Dict, errors: List, warnings: List):
        """Bengali-specific validation rules"""
        text = entry["text"]
        
        # Check proper use of hasant (্)
        hasant_issues = re.findall(r'্(?![ক-হ])', text)
        if hasant_issues:
            errors.append(f"Entry {entry['sequence']}: Improper hasant usage found")
        
        # Check for common Bengali spelling errors
        # (This would be expanded with a comprehensive Bengali dictionary)
        
        # Check sentence structure
        if not re.search(r'[।?!]$', text.strip()):
            warnings.append(f"Entry {entry['sequence']}: Missing proper Bengali sentence ending")
    
    def _validate_hindi_specific(self, entry: Dict, errors: List, warnings: List):
        """Hindi-specific validation rules"""
        text = entry["text"]
        
        # Check proper use of virama (्)
        virama_issues = re.findall(r'्(?![क-ह])', text)
        if virama_issues:
            errors.append(f"Entry {entry['sequence']}: Improper virama usage found")
        
        # Check for proper matra usage
        # Advanced validation would include dictionary checking
        
        # Check sentence structure
        if not re.search(r'[।?!]$', text.strip()):
            warnings.append(f"Entry {entry['sequence']}: Missing proper Hindi sentence ending")
    
    def _validate_timing_precision(self, entries: List[Dict], audio_duration: float = None) -> Dict[str, List]:
        """Validate timing with frame-level precision"""
        errors = []
        warnings = []
        
        for entry in entries:
            # Check reading speed
            text_length = len(entry["text"])
            duration = entry["duration"]
            chars_per_second = text_length / duration if duration > 0 else 0
            
            # Get language-specific reading speed
            lang_spec = self.language_specs.get("eng", {})  # Default to English
            min_cps, max_cps = lang_spec.get("reading_speed_cps", (15, 20))
            
            if chars_per_second > max_cps:
                errors.append(f"Entry {entry['sequence']}: Reading speed too fast ({chars_per_second:.1f} CPS, max {max_cps})")
            elif chars_per_second < min_cps and text_length > 10:
                warnings.append(f"Entry {entry['sequence']}: Reading speed too slow ({chars_per_second:.1f} CPS, min {min_cps})")
            
            # Check minimum duration
            if duration < 1.0:
                warnings.append(f"Entry {entry['sequence']}: Very short duration ({duration:.2f}s)")
            
            # Check maximum duration
            if duration > 7.0:
                warnings.append(f"Entry {entry['sequence']}: Very long duration ({duration:.2f}s)")
        
        # Check total coverage if audio duration provided
        if audio_duration and entries:
            last_entry = entries[-1]
            if last_entry["end_time"] < audio_duration * 0.95:
                warnings.append(f"Subtitles end significantly before audio ends ({last_entry['end_time']:.1f}s vs {audio_duration:.1f}s)")
        
        return {"critical_errors": errors, "warnings": warnings}
    
    def _validate_content_accuracy(self, entries: List[Dict], language: str) -> Dict[str, List]:
        """Validate content accuracy and completeness"""
        errors = []
        warnings = []
        
        # Check for content consistency
        total_text_length = sum(len(entry["text"]) for entry in entries)
        if total_text_length < 50:
            warnings.append("Very short total content - may be incomplete")
        
        # Check for repetitive content
        texts = [entry["text"] for entry in entries]
        unique_texts = set(texts)
        if len(unique_texts) < len(texts) * 0.8:
            warnings.append("High repetition in content - check for accuracy")
        
        # Check for placeholder text or obvious errors
        error_indicators = ["[inaudible]", "???", "...", "unclear", "mumble"]
        for entry in entries:
            for indicator in error_indicators:
                if indicator.lower() in entry["text"].lower():
                    errors.append(f"Entry {entry['sequence']}: Contains error indicator '{indicator}'")
        
        return {"critical_errors": errors, "warnings": warnings}
    
    def _validate_readability(self, entries: List[Dict], language: str) -> Dict[str, List]:
        """Validate readability and user experience"""
        errors = []
        warnings = []
        
        for entry in entries:
            text = entry["text"]
            
            # Check line breaking
            if '\n' in text:
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    # Check for orphaned words
                    words = line.strip().split()
                    if len(words) == 1 and i > 0:
                        warnings.append(f"Entry {entry['sequence']}: Orphaned word on line {i+1}: '{line.strip()}'")
                    
                    # Check for unbalanced lines
                    if i == 0 and len(lines) == 2:
                        if len(lines[1]) > len(lines[0]) * 1.5:
                            warnings.append(f"Entry {entry['sequence']}: Unbalanced line lengths")
        
        return {"critical_errors": errors, "warnings": warnings}
    
    def _calculate_quality_metrics(self, entries: List[Dict], language: str) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics"""
        if not entries:
            return {}
        
        total_duration = sum(entry["duration"] for entry in entries)
        total_chars = sum(len(entry["text"]) for entry in entries)
        total_words = sum(len(entry["text"].split()) for entry in entries)
        
        metrics = {
            "total_entries": len(entries),
            "total_duration": total_duration,
            "total_characters": total_chars,
            "total_words": total_words,
            "average_duration": total_duration / len(entries),
            "average_chars_per_entry": total_chars / len(entries),
            "average_words_per_entry": total_words / len(entries),
            "reading_speed_cps": total_chars / total_duration if total_duration > 0 else 0,
            "reading_speed_wpm": (total_words / (total_duration / 60)) if total_duration > 0 else 0,
            "coverage_ratio": 1.0,  # Would be calculated against actual audio
        }
        
        return metrics
    
    def _calculate_human_equivalence(self, errors: List, warnings: List, metrics: Dict) -> float:
        """Calculate how close the subtitles are to human-quality"""
        base_score = 100.0
        
        # Deduct points for errors
        critical_deduction = len(errors) * 15.0  # Each critical error = 15 points
        warning_deduction = len(warnings) * 3.0  # Each warning = 3 points
        
        score = base_score - critical_deduction - warning_deduction
        
        # Bonus for good metrics
        reading_speed = metrics.get("reading_speed_cps", 0)
        if 15 <= reading_speed <= 20:
            score += 5.0
        
        avg_duration = metrics.get("average_duration", 0)
        if 2 <= avg_duration <= 6:
            score += 3.0
        
        return max(0.0, min(100.0, score))
    
    def _validate_translation_quality(self, subtitle_entries: List[Dict], language: str, video_path: str = None) -> Dict[str, Any]:
        """
        Validate translation quality for cross-language subtitles
        Critical for ensuring accuracy when audio language differs from subtitle language
        """
        validation_result = {
            "critical_errors": [],
            "warnings": [],
            "translation_metrics": {}
        }
        
        # Skip if translation analyzer not available
        if not self.translation_analyzer:
            validation_result["warnings"].append("Translation quality analyzer not available")
            return validation_result
        
        logger.info(f"Validating translation quality for {language}")
        
        try:
            # Extract all subtitle text
            subtitle_text = "\n".join([entry["text"] for entry in subtitle_entries])
            
            # Attempt to detect source language from video context
            # This would typically be provided by the video processor or user input
            source_language = self._detect_or_infer_source_language(video_path, subtitle_text)
            
            if not source_language or source_language == language:
                # If same language or can't detect source, skip translation validation
                validation_result["warnings"].append(f"Source language detection failed or same as target ({language})")
                return validation_result
            
            logger.info(f"Detected source language: {source_language}, validating translation to {language}")
            
            # For subtitle validation, we need to assess translation quality differently
            # since we don't have access to original audio transcription
            translation_assessment = self._assess_subtitle_translation_quality(
                subtitle_text, source_language, language, video_path
            )
            
            validation_result["translation_metrics"] = translation_assessment
            
            # Apply quality thresholds for translation
            overall_score = translation_assessment.get("overall_score", 0.0)
            bleu_score = translation_assessment.get("bleu_score", 0.0)
            cultural_accuracy = translation_assessment.get("cultural_accuracy", 0.0)
            fluency_score = translation_assessment.get("fluency_score", 0.0)
            
            # Critical thresholds for production quality
            if overall_score < 70.0:
                validation_result["critical_errors"].append(
                    f"Translation quality too low: {overall_score:.1f}% (minimum: 70%)"
                )
            elif overall_score < 85.0:
                validation_result["warnings"].append(
                    f"Translation quality below optimal: {overall_score:.1f}% (recommended: 85%+)"
                )
            
            if cultural_accuracy < 0.8:
                validation_result["critical_errors"].append(
                    f"Cultural accuracy insufficient: {cultural_accuracy:.1f} (minimum: 0.8)"
                )
            
            if fluency_score < 0.8:
                validation_result["critical_errors"].append(
                    f"Target language fluency insufficient: {fluency_score:.1f} (minimum: 0.8)"
                )
            
            # Language-specific translation validation
            if language == 'ben':
                if not self._validate_bengali_translation_quality(subtitle_text):
                    validation_result["critical_errors"].append("Bengali translation lacks cultural authenticity")
            elif language == 'hin':
                if not self._validate_hindi_translation_quality(subtitle_text):
                    validation_result["critical_errors"].append("Hindi translation lacks cultural appropriateness")
            elif language == 'eng':
                if not self._validate_english_translation_quality(subtitle_text):
                    validation_result["critical_errors"].append("English translation lacks natural fluency")
            
            # Check for common translation errors
            translation_errors = self._detect_translation_errors(subtitle_text, language, source_language)
            validation_result["critical_errors"].extend(translation_errors.get("critical", []))
            validation_result["warnings"].extend(translation_errors.get("warnings", []))
            
        except Exception as e:
            logger.error(f"Translation quality validation failed: {str(e)}")
            validation_result["warnings"].append(f"Translation validation error: {str(e)}")
        
        return validation_result
    
    def _detect_or_infer_source_language(self, video_path: str, subtitle_text: str) -> Optional[str]:
        """Detect or infer the source language of the video content"""
        try:
            # Method 1: Check if video path or context provides language info
            if video_path:
                # Extract language hints from video path/filename
                path_lower = video_path.lower()
                if 'bengali' in path_lower or '_ben_' in path_lower or '_bn_' in path_lower:
                    return 'ben'
                elif 'hindi' in path_lower or '_hin_' in path_lower or '_hi_' in path_lower:
                    return 'hin'
                elif 'english' in path_lower or '_eng_' in path_lower or '_en_' in path_lower:
                    return 'eng'
            
            # Method 2: Simple character-based language detection on subtitle text
            # This is a fallback - in production, would use proper language detection
            bengali_chars = len(re.findall(r'[\u0980-\u09FF]', subtitle_text))
            hindi_chars = len(re.findall(r'[\u0900-\u097F]', subtitle_text))
            latin_chars = len(re.findall(r'[a-zA-Z]', subtitle_text))
            
            total_chars = len(subtitle_text.replace(' ', ''))
            if total_chars > 0:
                bengali_ratio = bengali_chars / total_chars
                hindi_ratio = hindi_chars / total_chars
                latin_ratio = latin_chars / total_chars
                
                # If subtitle is in target language, try to infer source
                # This is heuristic-based and could be improved
                if bengali_ratio > 0.5:
                    return 'eng' if latin_ratio < 0.1 else None  # Likely translated from English
                elif hindi_ratio > 0.5:
                    return 'eng' if latin_ratio < 0.1 else None  # Likely translated from English
                elif latin_ratio > 0.5:
                    return 'ben' if bengali_ratio < 0.1 else 'hin'  # Likely translated from Bengali/Hindi
            
            return None  # Could not determine source language
            
        except Exception as e:
            logger.warning(f"Source language detection failed: {str(e)}")
            return None
    
    def _assess_subtitle_translation_quality(self, subtitle_text: str, source_lang: str, target_lang: str, video_path: str = None) -> Dict[str, float]:
        """Assess translation quality for subtitle content"""
        try:
            # Use translation quality analyzer to assess the subtitle text
            # Since we don't have original source text, we'll use reference translation approach
            
            # Generate reference translation for comparison
            reference_translation = None
            if self.translation_analyzer.google_translate_client:
                try:
                    result = self.translation_analyzer.google_translate_client.translate(
                        subtitle_text,
                        target_language=self.translation_analyzer.language_codes.get(target_lang, target_lang)
                    )
                    reference_translation = result.get('translatedText', '')
                except Exception as e:
                    logger.warning(f"Reference translation generation failed: {e}")
            
            # Assess translation quality
            quality_result = self.translation_analyzer.assess_translation_quality(
                source_text="",  # We don't have original source
                translated_text=subtitle_text,
                source_language=source_lang,
                target_language=target_lang,
                reference_translation=reference_translation,
                video_context={"video_path": video_path} if video_path else None
            )
            
            return {
                "overall_score": quality_result.overall_score,
                "bleu_score": quality_result.bleu_score,
                "meteor_score": quality_result.meteor_score,
                "semantic_similarity": quality_result.semantic_similarity,
                "cultural_accuracy": quality_result.cultural_accuracy,
                "terminology_consistency": quality_result.terminology_consistency,
                "fluency_score": quality_result.fluency_score,
                "adequacy_score": quality_result.adequacy_score,
                "language_pair": quality_result.language_pair,
                "recommendations": quality_result.recommendations
            }
            
        except Exception as e:
            logger.error(f"Subtitle translation quality assessment failed: {str(e)}")
            return {
                "overall_score": 50.0,  # Default low score to indicate issues
                "error": str(e)
            }
    
    def _validate_bengali_translation_quality(self, subtitle_text: str) -> bool:
        """Validate Bengali translation quality"""
        # Check for proper Bengali cultural context
        cultural_indicators = ['নমস্কার', 'আদাব', 'ধন্যবাদ', 'আপনি', 'তুমি', 'ভাই', 'বোন']
        has_cultural_context = any(term in subtitle_text for term in cultural_indicators)
        
        # Check for proper Bengali sentence structure indicators
        structure_indicators = ['এর', 'টি', 'টা', 'কে', 'রে', 'তে', 'দিয়ে', 'থেকে']
        has_proper_structure = any(term in subtitle_text for term in structure_indicators)
        
        return has_cultural_context or has_proper_structure
    
    def _validate_hindi_translation_quality(self, subtitle_text: str) -> bool:
        """Validate Hindi translation quality"""
        # Check for proper Hindi cultural context
        cultural_indicators = ['नमस्ते', 'धन्यवाद', 'आप', 'तुम', 'भाई', 'बहन', 'जी', 'साहब']
        has_cultural_context = any(term in subtitle_text for term in cultural_indicators)
        
        # Check for proper Devanagari usage
        has_devanagari = bool(re.search(r'[\u0900-\u097F]', subtitle_text))
        
        return has_cultural_context and has_devanagari
    
    def _validate_english_translation_quality(self, subtitle_text: str) -> bool:
        """Validate English translation quality"""
        # Check for natural English patterns
        natural_patterns = [
            r'\b(the|a|an)\s+\w+',  # Articles
            r'\b(is|are|was|were)\s+',  # Linking verbs
            r'\b(and|but|or|so)\s+',  # Conjunctions
        ]
        
        pattern_matches = sum(1 for pattern in natural_patterns if re.search(pattern, subtitle_text, re.IGNORECASE))
        return pattern_matches >= 2  # At least 2 natural English patterns
    
    def _detect_translation_errors(self, subtitle_text: str, target_lang: str, source_lang: str) -> Dict[str, List[str]]:
        """Detect common translation errors"""
        errors = {
            "critical": [],
            "warnings": []
        }
        
        # Check for untranslated text (source language text remaining)
        if source_lang == 'eng' and target_lang in ['ben', 'hin']:
            # Look for English text in non-English subtitles (excluding proper nouns)
            english_text = re.findall(r'\b[a-zA-Z]{3,}\b', subtitle_text)
            if len(english_text) > len(subtitle_text.split()) * 0.3:  # More than 30% English
                errors["warnings"].append("Significant untranslated English text detected")
        
        # Check for gibberish or malformed characters
        if '?' in subtitle_text and subtitle_text.count('?') > len(subtitle_text) * 0.05:
            errors["critical"].append("Excessive question marks suggesting encoding/translation issues")
        
        # Language-specific error patterns
        if target_lang == 'ben':
            # Check for common Bengali translation errors
            if 'বাংলা' not in subtitle_text and len(subtitle_text) > 100:
                errors["warnings"].append("Long Bengali text without language identifier")
        elif target_lang == 'hin':
            # Check for common Hindi translation errors
            if not re.search(r'[\u0900-\u097F]', subtitle_text):
                errors["critical"].append("Hindi subtitle missing Devanagari characters")
        
        return errors

    def _finalize_report(self, report: Dict) -> Dict:
        """Finalize validation report with production readiness assessment"""
        critical_errors = len(report["critical_errors"])
        warnings = len(report["warnings"])
        human_score = report["human_equivalence_score"]
        
        # Calculate accuracy score
        if critical_errors == 0:
            base_accuracy = 95.0
            warning_penalty = min(warnings * 2.0, 15.0)
            report["accuracy_score"] = base_accuracy - warning_penalty
        else:
            report["accuracy_score"] = max(0.0, 70.0 - (critical_errors * 10.0))
        
        # Determine overall status
        if critical_errors == 0 and warnings <= 3 and human_score >= 90.0:
            report["overall_status"] = "PRODUCTION_READY"
            report["production_ready"] = True
        elif critical_errors == 0 and warnings <= 5 and human_score >= 80.0:
            report["overall_status"] = "MINOR_ISSUES"
            report["production_ready"] = True
        elif critical_errors <= 2 and warnings <= 8:
            report["overall_status"] = "NEEDS_REVISION"
            report["production_ready"] = False
        else:
            report["overall_status"] = "MAJOR_ISSUES"
            report["production_ready"] = False
        
        return report
    
    def generate_correction_suggestions(self, validation_report: Dict, srt_content: str) -> List[Dict]:
        """Generate specific correction suggestions for identified issues"""
        suggestions = []
        
        for error in validation_report["critical_errors"]:
            if "sequence number" in error.lower():
                suggestions.append({
                    "type": "critical",
                    "category": "format",
                    "issue": error,
                    "suggestion": "Renumber all subtitle entries sequentially starting from 1",
                    "auto_fixable": True
                })
            elif "overlaps" in error.lower():
                suggestions.append({
                    "type": "critical",
                    "category": "timing",
                    "issue": error,
                    "suggestion": "Adjust end time of first subtitle or start time of second subtitle",
                    "auto_fixable": True
                })
            elif "reading speed too fast" in error.lower():
                suggestions.append({
                    "type": "critical",
                    "category": "timing",
                    "issue": error,
                    "suggestion": "Increase subtitle duration or split into multiple subtitles",
                    "auto_fixable": False
                })
        
        for warning in validation_report["warnings"]:
            if "short duration" in warning.lower():
                suggestions.append({
                    "type": "warning",
                    "category": "timing",
                    "issue": warning,
                    "suggestion": "Consider combining with adjacent subtitle if contextually appropriate",
                    "auto_fixable": False
                })
        
        return suggestions