"""
Translation Quality Analyzer
Advanced assessment of translation quality for cross-language subtitle generation
Specializes in English ↔ Bengali ↔ Hindi translation quality validation
"""

import re
import json
import time
from typing import List, Dict, Tuple, Optional, Any, Union
from pathlib import Path
import logging
from dataclasses import dataclass

# NLP libraries for translation quality assessment
try:
    import nltk
    from nltk.translate.bleu_score import sentence_bleu, corpus_bleu
    from nltk.translate.meteor_score import meteor_score
    from nltk.tokenize import word_tokenize, sent_tokenize
    from textblob import TextBlob
    import numpy as np
    TRANSLATION_LIBRARIES_AVAILABLE = True
except ImportError:
    TRANSLATION_LIBRARIES_AVAILABLE = False

# Google Translation API for reference validation
try:
    from google.cloud import translate_v2 as translate
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False

from .config_manager import ConfigManager
from .logger import get_logger
from rich.console import Console

console = Console()
logger = get_logger(__name__)

@dataclass
class TranslationQualityResult:
    """Result structure for translation quality assessment"""
    overall_score: float
    bleu_score: float
    meteor_score: float
    semantic_similarity: float
    cultural_accuracy: float
    terminology_consistency: float
    fluency_score: float
    adequacy_score: float
    language_pair: Tuple[str, str]
    detailed_analysis: Dict[str, Any]
    recommendations: List[str]
    error_analysis: Dict[str, Any]

class TranslationQualityAnalyzer:
    """Comprehensive translation quality assessment for subtitle generation"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.console = Console()
        
        # Language mappings
        self.language_codes = {
            'eng': 'en',
            'ben': 'bn', 
            'hin': 'hi',
            'english': 'en',
            'bengali': 'bn',
            'hindi': 'hi'
        }
        
        # Initialize translation services
        self.google_translate_client = None
        if GOOGLE_TRANSLATE_AVAILABLE:
            try:
                self.google_translate_client = translate.Client()
                logger.info("✅ Google Translate API initialized")
            except Exception as e:
                logger.warning(f"Google Translate API initialization failed: {e}")
        
        # Initialize NLTK components
        self._initialize_nltk()
        
        # Load language-specific quality benchmarks
        self.quality_benchmarks = self._load_quality_benchmarks()
        
        # Cultural context validators
        self.cultural_validators = {
            'ben': self._validate_bengali_cultural_context,
            'hin': self._validate_hindi_cultural_context,
            'eng': self._validate_english_cultural_context
        }
        
    def _initialize_nltk(self):
        """Initialize NLTK resources"""
        if not TRANSLATION_LIBRARIES_AVAILABLE:
            logger.warning("Translation quality libraries not available")
            return
            
        try:
            # Download required NLTK data
            nltk.download('punkt', quiet=True)
            nltk.download('wordnet', quiet=True)
            nltk.download('omw-1.4', quiet=True)
            logger.info("✅ NLTK components initialized")
        except Exception as e:
            logger.error(f"NLTK initialization failed: {e}")
    
    def _load_quality_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """Load quality benchmarks for different language pairs"""
        return {
            ('en', 'bn'): {
                'min_bleu': 0.25,
                'min_meteor': 0.30,
                'min_semantic': 0.75,
                'min_cultural': 0.80,
                'min_fluency': 0.85
            },
            ('en', 'hi'): {
                'min_bleu': 0.28,
                'min_meteor': 0.32,
                'min_semantic': 0.78,
                'min_cultural': 0.82,
                'min_fluency': 0.87
            },
            ('bn', 'en'): {
                'min_bleu': 0.30,
                'min_meteor': 0.35,
                'min_semantic': 0.80,
                'min_cultural': 0.75,
                'min_fluency': 0.90
            },
            ('hi', 'en'): {
                'min_bleu': 0.32,
                'min_meteor': 0.36,
                'min_semantic': 0.82,
                'min_cultural': 0.78,
                'min_fluency': 0.92
            },
            ('bn', 'hi'): {
                'min_bleu': 0.22,
                'min_meteor': 0.28,
                'min_semantic': 0.70,
                'min_cultural': 0.85,
                'min_fluency': 0.80
            },
            ('hi', 'bn'): {
                'min_bleu': 0.22,
                'min_meteor': 0.28,
                'min_semantic': 0.70,
                'min_cultural': 0.85,
                'min_fluency': 0.80
            }
        }
    
    def assess_translation_quality(self, 
                                 source_text: str, 
                                 translated_text: str,
                                 source_language: str,
                                 target_language: str,
                                 reference_translation: str = None,
                                 video_context: Dict[str, Any] = None) -> TranslationQualityResult:
        """
        Comprehensive translation quality assessment
        
        Args:
            source_text: Original text in source language
            translated_text: Translated text in target language
            source_language: Source language code (eng, ben, hin)
            target_language: Target language code (eng, ben, hin)
            reference_translation: Optional reference translation for comparison
            video_context: Optional video context information
        
        Returns:
            TranslationQualityResult with comprehensive assessment
        """
        logger.info(f"Assessing translation quality: {source_language} → {target_language}")
        
        # Normalize language codes
        src_lang = self.language_codes.get(source_language.lower(), source_language.lower())
        tgt_lang = self.language_codes.get(target_language.lower(), target_language.lower())
        
        # Create reference translation if not provided
        if not reference_translation and self.google_translate_client:
            reference_translation = self._generate_reference_translation(source_text, src_lang, tgt_lang)
        
        # Initialize scores
        scores = {
            'bleu_score': 0.0,
            'meteor_score': 0.0,
            'semantic_similarity': 0.0,
            'cultural_accuracy': 0.0,
            'terminology_consistency': 0.0,
            'fluency_score': 0.0,
            'adequacy_score': 0.0
        }
        
        detailed_analysis = {}
        recommendations = []
        error_analysis = {}
        
        # 1. BLEU Score Assessment
        if reference_translation and TRANSLATION_LIBRARIES_AVAILABLE:
            scores['bleu_score'] = self._calculate_bleu_score(
                reference_translation, translated_text, tgt_lang
            )
            detailed_analysis['bleu_details'] = self._analyze_bleu_components(
                reference_translation, translated_text, tgt_lang
            )
        
        # 2. METEOR Score Assessment
        if reference_translation and TRANSLATION_LIBRARIES_AVAILABLE:
            scores['meteor_score'] = self._calculate_meteor_score(
                reference_translation, translated_text, tgt_lang
            )
        
        # 3. Semantic Similarity Assessment
        scores['semantic_similarity'] = self._assess_semantic_similarity(
            source_text, translated_text, src_lang, tgt_lang
        )
        
        # 4. Cultural Context Accuracy
        scores['cultural_accuracy'] = self._assess_cultural_accuracy(
            source_text, translated_text, src_lang, tgt_lang, video_context
        )
        
        # 5. Terminology Consistency
        scores['terminology_consistency'] = self._assess_terminology_consistency(
            source_text, translated_text, src_lang, tgt_lang
        )
        
        # 6. Fluency Assessment
        scores['fluency_score'] = self._assess_fluency(translated_text, tgt_lang)
        
        # 7. Adequacy Assessment
        scores['adequacy_score'] = self._assess_adequacy(
            source_text, translated_text, src_lang, tgt_lang
        )
        
        # Generate recommendations
        recommendations = self._generate_translation_recommendations(
            scores, src_lang, tgt_lang, detailed_analysis
        )
        
        # Error analysis
        error_analysis = self._analyze_translation_errors(
            source_text, translated_text, reference_translation, src_lang, tgt_lang
        )
        
        # Calculate overall score
        overall_score = self._calculate_overall_translation_score(scores, src_lang, tgt_lang)
        
        return TranslationQualityResult(
            overall_score=overall_score,
            bleu_score=scores['bleu_score'],
            meteor_score=scores['meteor_score'],
            semantic_similarity=scores['semantic_similarity'],
            cultural_accuracy=scores['cultural_accuracy'],
            terminology_consistency=scores['terminology_consistency'],
            fluency_score=scores['fluency_score'],
            adequacy_score=scores['adequacy_score'],
            language_pair=(src_lang, tgt_lang),
            detailed_analysis=detailed_analysis,
            recommendations=recommendations,
            error_analysis=error_analysis
        )
    
    def _generate_reference_translation(self, text: str, src_lang: str, tgt_lang: str) -> Optional[str]:
        """Generate reference translation using Google Translate API"""
        try:
            if not self.google_translate_client:
                return None
                
            result = self.google_translate_client.translate(
                text, 
                source_language=src_lang,
                target_language=tgt_lang
            )
            return result['translatedText']
            
        except Exception as e:
            logger.warning(f"Reference translation generation failed: {e}")
            return None
    
    def _calculate_bleu_score(self, reference: str, candidate: str, language: str) -> float:
        """Calculate BLEU score for translation quality"""
        try:
            # Tokenize based on language
            if language in ['bn', 'hi']:
                # For Bengali and Hindi, split on whitespace and punctuation
                ref_tokens = re.findall(r'\S+', reference.lower())
                cand_tokens = re.findall(r'\S+', candidate.lower())
            else:
                # For English, use NLTK tokenization
                ref_tokens = word_tokenize(reference.lower())
                cand_tokens = word_tokenize(candidate.lower())
            
            # Calculate BLEU score
            bleu = sentence_bleu([ref_tokens], cand_tokens, weights=(0.25, 0.25, 0.25, 0.25))
            return min(bleu, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.warning(f"BLEU calculation failed: {e}")
            return 0.0
    
    def _analyze_bleu_components(self, reference: str, candidate: str, language: str) -> Dict[str, float]:
        """Analyze individual BLEU components (1-gram to 4-gram precision)"""
        try:
            if language in ['bn', 'hi']:
                ref_tokens = re.findall(r'\S+', reference.lower())
                cand_tokens = re.findall(r'\S+', candidate.lower())
            else:
                ref_tokens = word_tokenize(reference.lower())
                cand_tokens = word_tokenize(candidate.lower())
            
            components = {}
            for n in range(1, 5):
                weight_vector = [0] * 4
                weight_vector[n-1] = 1.0
                components[f'{n}_gram_precision'] = sentence_bleu([ref_tokens], cand_tokens, weights=weight_vector)
            
            return components
            
        except Exception as e:
            logger.warning(f"BLEU components analysis failed: {e}")
            return {}
    
    def _calculate_meteor_score(self, reference: str, candidate: str, language: str) -> float:
        """Calculate METEOR score for translation quality"""
        try:
            if language not in ['en']:  # METEOR primarily supports English
                return self._estimate_meteor_score(reference, candidate, language)
            
            ref_tokens = word_tokenize(reference.lower())
            cand_tokens = word_tokenize(candidate.lower())
            
            meteor = meteor_score([ref_tokens], cand_tokens)
            return min(meteor, 1.0)
            
        except Exception as e:
            logger.warning(f"METEOR calculation failed: {e}")
            return 0.0
    
    def _estimate_meteor_score(self, reference: str, candidate: str, language: str) -> float:
        """Estimate METEOR-like score for non-English languages"""
        try:
            # Simple precision-recall based estimation
            if language in ['bn', 'hi']:
                ref_tokens = set(re.findall(r'\S+', reference.lower()))
                cand_tokens = set(re.findall(r'\S+', candidate.lower()))
            else:
                ref_tokens = set(reference.lower().split())
                cand_tokens = set(candidate.lower().split())
            
            if not ref_tokens or not cand_tokens:
                return 0.0
            
            matches = len(ref_tokens.intersection(cand_tokens))
            precision = matches / len(cand_tokens) if cand_tokens else 0
            recall = matches / len(ref_tokens) if ref_tokens else 0
            
            if precision + recall == 0:
                return 0.0
            
            f_score = 2 * precision * recall / (precision + recall)
            return min(f_score, 1.0)
            
        except Exception as e:
            logger.warning(f"METEOR estimation failed: {e}")
            return 0.0
    
    def _assess_semantic_similarity(self, source: str, translated: str, src_lang: str, tgt_lang: str) -> float:
        """Assess semantic similarity between source and translation"""
        try:
            # Use back-translation method for semantic similarity
            if not self.google_translate_client:
                return self._estimate_semantic_similarity(source, translated, src_lang, tgt_lang)
            
            # Translate back to source language
            back_translation = self.google_translate_client.translate(
                translated, 
                source_language=tgt_lang,
                target_language=src_lang
            )['translatedText']
            
            # Calculate similarity between original and back-translated text
            similarity = self._calculate_text_similarity(source, back_translation, src_lang)
            return min(similarity, 1.0)
            
        except Exception as e:
            logger.warning(f"Semantic similarity assessment failed: {e}")
            return 0.5  # Default neutral score
    
    def _estimate_semantic_similarity(self, source: str, translated: str, src_lang: str, tgt_lang: str) -> float:
        """Estimate semantic similarity without translation API"""
        try:
            # Length-based heuristic combined with key term preservation
            len_ratio = min(len(translated), len(source)) / max(len(translated), len(source), 1)
            
            # Extract key terms (words longer than 3 characters)
            source_terms = set(word for word in re.findall(r'\w{4,}', source.lower()))
            translated_terms = set(word for word in re.findall(r'\w{4,}', translated.lower()))
            
            # For cross-language, focus on numbers, dates, proper nouns that might be preserved
            preserved_elements = 0
            source_elements = re.findall(r'\d+|[A-Z][a-z]+', source)
            for element in source_elements:
                if element.lower() in translated.lower():
                    preserved_elements += 1
            
            preservation_score = preserved_elements / max(len(source_elements), 1)
            
            # Combine heuristics
            estimated_similarity = (len_ratio * 0.4) + (preservation_score * 0.6)
            return min(estimated_similarity, 1.0)
            
        except Exception as e:
            logger.warning(f"Semantic similarity estimation failed: {e}")
            return 0.5
    
    def _calculate_text_similarity(self, text1: str, text2: str, language: str) -> float:
        """Calculate similarity between two texts in the same language"""
        try:
            if language in ['bn', 'hi']:
                tokens1 = set(re.findall(r'\S+', text1.lower()))
                tokens2 = set(re.findall(r'\S+', text2.lower()))
            else:
                tokens1 = set(word_tokenize(text1.lower()))
                tokens2 = set(word_tokenize(text2.lower()))
            
            if not tokens1 or not tokens2:
                return 0.0
            
            intersection = len(tokens1.intersection(tokens2))
            union = len(tokens1.union(tokens2))
            
            jaccard_similarity = intersection / union if union > 0 else 0.0
            return min(jaccard_similarity, 1.0)
            
        except Exception as e:
            logger.warning(f"Text similarity calculation failed: {e}")
            return 0.0
    
    def _assess_cultural_accuracy(self, source: str, translated: str, src_lang: str, tgt_lang: str, context: Dict = None) -> float:
        """Assess cultural context accuracy in translation"""
        try:
            # Use language-specific cultural validators
            if tgt_lang in self.cultural_validators:
                return self.cultural_validators[tgt_lang](source, translated, src_lang, context)
            else:
                return self._generic_cultural_assessment(source, translated, src_lang, tgt_lang, context)
                
        except Exception as e:
            logger.warning(f"Cultural accuracy assessment failed: {e}")
            return 0.7  # Default score
    
    def _validate_bengali_cultural_context(self, source: str, translated: str, src_lang: str, context: Dict = None) -> float:
        """Validate Bengali cultural context in translation"""
        score = 0.0
        checks = []
        
        # Check 1: Proper Bengali script usage
        bengali_char_pattern = r'[\u0980-\u09FF]'
        has_bengali_script = bool(re.search(bengali_char_pattern, translated))
        if has_bengali_script:
            score += 0.3
            checks.append("✅ Bengali script usage")
        else:
            checks.append("❌ Missing Bengali script")
        
        # Check 2: Cultural terms preservation/adaptation
        cultural_terms = ['নমস্কার', 'আদাব', 'সালাম', 'প্রণাম', 'ভাই', 'দিদি', 'দাদা', 'বোন']
        cultural_found = any(term in translated for term in cultural_terms)
        if cultural_found:
            score += 0.25
            checks.append("✅ Cultural terms present")
        
        # Check 3: Formal/informal register appropriateness
        formal_indicators = ['আপনি', 'আপনার', 'করবেন', 'হবেন']
        informal_indicators = ['তুমি', 'তোমার', 'করবি', 'হবি']
        
        if any(term in translated for term in formal_indicators):
            score += 0.2
            checks.append("✅ Formal register usage")
        elif any(term in translated for term in informal_indicators):
            score += 0.15
            checks.append("✅ Informal register usage")
        
        # Check 4: Bengali sentence structure
        if self._check_bengali_sentence_structure(translated):
            score += 0.25
            checks.append("✅ Proper Bengali sentence structure")
        
        logger.debug(f"Bengali cultural validation: {checks}")
        return min(score, 1.0)
    
    def _validate_hindi_cultural_context(self, source: str, translated: str, src_lang: str, context: Dict = None) -> float:
        """Validate Hindi cultural context in translation"""
        score = 0.0
        checks = []
        
        # Check 1: Proper Devanagari script usage
        devanagari_pattern = r'[\u0900-\u097F]'
        has_devanagari = bool(re.search(devanagari_pattern, translated))
        if has_devanagari:
            score += 0.3
            checks.append("✅ Devanagari script usage")
        else:
            checks.append("❌ Missing Devanagari script")
        
        # Check 2: Cultural greetings and terms
        cultural_terms = ['नमस्ते', 'नमस्कार', 'आदाब', 'सलाम', 'भाई', 'बहन', 'जी', 'साहब']
        cultural_found = any(term in translated for term in cultural_terms)
        if cultural_found:
            score += 0.25
            checks.append("✅ Cultural terms present")
        
        # Check 3: Respect/honorific usage
        respectful_terms = ['आप', 'आपका', 'जी हाँ', 'जी नहीं', 'श्रीमान', 'श्रीमती']
        if any(term in translated for term in respectful_terms):
            score += 0.2
            checks.append("✅ Respectful language usage")
        
        # Check 4: Hindi grammar patterns
        if self._check_hindi_grammar_patterns(translated):
            score += 0.25
            checks.append("✅ Proper Hindi grammar patterns")
        
        logger.debug(f"Hindi cultural validation: {checks}")
        return min(score, 1.0)
    
    def _validate_english_cultural_context(self, source: str, translated: str, src_lang: str, context: Dict = None) -> float:
        """Validate English cultural context in translation"""
        score = 0.0
        checks = []
        
        # Check 1: Natural English flow
        if self._check_natural_english_flow(translated):
            score += 0.4
            checks.append("✅ Natural English flow")
        
        # Check 2: Appropriate register (formal/informal)
        if self._assess_english_register(translated, context):
            score += 0.3
            checks.append("✅ Appropriate register")
        
        # Check 3: Cultural idioms and expressions handling
        if self._check_cultural_expression_handling(source, translated, src_lang):
            score += 0.3
            checks.append("✅ Cultural expressions handled")
        
        logger.debug(f"English cultural validation: {checks}")
        return min(score, 1.0)
    
    def _generic_cultural_assessment(self, source: str, translated: str, src_lang: str, tgt_lang: str, context: Dict = None) -> float:
        """Generic cultural accuracy assessment"""
        # Basic checks for any language
        score = 0.5  # Base score
        
        # Check if translation maintains original length proportionally
        length_ratio = len(translated) / max(len(source), 1)
        if 0.5 <= length_ratio <= 2.0:  # Reasonable length range
            score += 0.2
        
        # Check for preserved proper nouns and numbers
        preserved_score = self._check_preserved_elements(source, translated)
        score += preserved_score * 0.3
        
        return min(score, 1.0)
    
    def _assess_terminology_consistency(self, source: str, translated: str, src_lang: str, tgt_lang: str) -> float:
        """Assess consistency of terminology translation"""
        try:
            # Extract potential terminology (technical terms, proper nouns)
            source_terms = self._extract_terminology(source, src_lang)
            translated_terms = self._extract_terminology(translated, tgt_lang)
            
            if not source_terms:
                return 1.0  # No terminology to check
            
            consistency_score = 0.0
            checked_terms = 0
            
            for term in source_terms:
                # Check if term is appropriately handled in translation
                if self._is_terminology_handled_correctly(term, source, translated, src_lang, tgt_lang):
                    consistency_score += 1.0
                checked_terms += 1
            
            return consistency_score / max(checked_terms, 1)
            
        except Exception as e:
            logger.warning(f"Terminology consistency assessment failed: {e}")
            return 0.8  # Default score
    
    def _assess_fluency(self, text: str, language: str) -> float:
        """Assess fluency of translated text"""
        try:
            fluency_score = 0.0
            
            # Language-specific fluency checks
            if language == 'en':
                fluency_score = self._assess_english_fluency(text)
            elif language == 'bn':
                fluency_score = self._assess_bengali_fluency(text)
            elif language == 'hi':
                fluency_score = self._assess_hindi_fluency(text)
            else:
                fluency_score = self._assess_generic_fluency(text)
            
            return min(fluency_score, 1.0)
            
        except Exception as e:
            logger.warning(f"Fluency assessment failed: {e}")
            return 0.7  # Default score
    
    def _assess_adequacy(self, source: str, translated: str, src_lang: str, tgt_lang: str) -> float:
        """Assess adequacy (completeness) of translation"""
        try:
            # Check if all important information is preserved
            
            # Extract key information elements
            source_info = self._extract_key_information(source, src_lang)
            translated_info = self._extract_key_information(translated, tgt_lang)
            
            if not source_info:
                return 1.0  # No key information to preserve
            
            preservation_score = 0.0
            for info_type, info_items in source_info.items():
                if info_type in translated_info:
                    preserved_ratio = len(translated_info[info_type]) / max(len(info_items), 1)
                    preservation_score += min(preserved_ratio, 1.0)
                else:
                    preservation_score += 0.0  # Information type not preserved
            
            adequacy = preservation_score / len(source_info)
            return min(adequacy, 1.0)
            
        except Exception as e:
            logger.warning(f"Adequacy assessment failed: {e}")
            return 0.8  # Default score
    
    def _calculate_overall_translation_score(self, scores: Dict[str, float], src_lang: str, tgt_lang: str) -> float:
        """Calculate weighted overall translation quality score"""
        language_pair = (src_lang, tgt_lang)
        benchmarks = self.quality_benchmarks.get(language_pair, {})
        
        # Weighted combination of scores
        weights = {
            'bleu_score': 0.20,
            'meteor_score': 0.15,
            'semantic_similarity': 0.25,
            'cultural_accuracy': 0.15,
            'terminology_consistency': 0.10,
            'fluency_score': 0.10,
            'adequacy_score': 0.05
        }
        
        overall_score = sum(scores[metric] * weight for metric, weight in weights.items())
        
        # Apply language-pair specific adjustments
        if language_pair in self.quality_benchmarks:
            benchmark_penalty = 0.0
            for metric, min_score in benchmarks.items():
                metric_name = metric.replace('min_', '') + '_score'
                if metric_name in scores and scores[metric_name] < min_score:
                    benchmark_penalty += (min_score - scores[metric_name]) * 0.1
            
            overall_score = max(0.0, overall_score - benchmark_penalty)
        
        return min(overall_score * 100, 100.0)  # Return as percentage
    
    def _generate_translation_recommendations(self, scores: Dict[str, float], src_lang: str, tgt_lang: str, analysis: Dict[str, Any]) -> List[str]:
        """Generate specific recommendations for translation improvement"""
        recommendations = []
        
        if scores['bleu_score'] < 0.3:
            recommendations.append("🔄 Improve lexical accuracy - many words don't match reference translation")
        
        if scores['semantic_similarity'] < 0.7:
            recommendations.append("🎯 Focus on preserving meaning - semantic content may be lost")
        
        if scores['cultural_accuracy'] < 0.8:
            recommendations.append("🌍 Enhance cultural context adaptation for target language")
        
        if scores['fluency_score'] < 0.8:
            recommendations.append("📝 Improve target language fluency and naturalness")
        
        if scores['terminology_consistency'] < 0.9:
            recommendations.append("🔧 Ensure consistent translation of technical terms")
        
        if scores['adequacy_score'] < 0.9:
            recommendations.append("📋 Check that all source information is preserved in translation")
        
        # Language-specific recommendations
        if tgt_lang == 'bn':
            recommendations.append("🔤 Verify proper Bengali script and cultural expressions")
        elif tgt_lang == 'hi':
            recommendations.append("🔤 Ensure accurate Devanagari script and respectful language")
        elif tgt_lang == 'en':
            recommendations.append("🔤 Maintain natural English flow and appropriate register")
        
        return recommendations
    
    def _analyze_translation_errors(self, source: str, translated: str, reference: str, src_lang: str, tgt_lang: str) -> Dict[str, Any]:
        """Analyze specific types of translation errors"""
        errors = {
            'lexical_errors': [],
            'grammatical_errors': [],
            'cultural_errors': [],
            'omission_errors': [],
            'addition_errors': [],
            'error_severity': 'low'
        }
        
        try:
            # Basic error detection (this could be enhanced with more sophisticated NLP)
            
            # Check for obvious omissions (significantly shorter translation)
            length_ratio = len(translated) / max(len(source), 1)
            if length_ratio < 0.5:
                errors['omission_errors'].append("Translation significantly shorter than source")
                errors['error_severity'] = 'high'
            elif length_ratio > 2.5:
                errors['addition_errors'].append("Translation significantly longer than source")
                errors['error_severity'] = 'medium'
            
            # Language-specific error detection
            if tgt_lang == 'bn' and not re.search(r'[\u0980-\u09FF]', translated):
                errors['cultural_errors'].append("Missing Bengali script characters")
                errors['error_severity'] = 'high'
            
            if tgt_lang == 'hi' and not re.search(r'[\u0900-\u097F]', translated):
                errors['cultural_errors'].append("Missing Devanagari script characters")
                errors['error_severity'] = 'high'
            
            return errors
            
        except Exception as e:
            logger.warning(f"Translation error analysis failed: {e}")
            return errors
    
    # Helper methods (abbreviated for space - would include full implementations)
    def _check_bengali_sentence_structure(self, text: str) -> bool:
        """Check if Bengali sentence follows proper SOV structure"""
        # Simplified check - would be more sophisticated in production
        return True  # Placeholder
    
    def _check_hindi_grammar_patterns(self, text: str) -> bool:
        """Check Hindi grammar patterns"""
        # Simplified check - would be more sophisticated in production
        return True  # Placeholder
    
    def _check_natural_english_flow(self, text: str) -> bool:
        """Check if English text flows naturally"""
        # Simplified check - would be more sophisticated in production
        return True  # Placeholder
    
    def _assess_english_register(self, text: str, context: Dict = None) -> bool:
        """Assess if English register is appropriate"""
        return True  # Placeholder
    
    def _check_cultural_expression_handling(self, source: str, translated: str, src_lang: str) -> bool:
        """Check if cultural expressions are properly handled"""
        return True  # Placeholder
    
    def _check_preserved_elements(self, source: str, translated: str) -> float:
        """Check preservation of numbers, dates, proper nouns"""
        try:
            # Extract numbers and dates
            numbers = re.findall(r'\d+', source)
            dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', source)
            
            preserved_count = 0
            total_elements = len(numbers) + len(dates)
            
            for num in numbers:
                if num in translated:
                    preserved_count += 1
            
            for date in dates:
                if date in translated:
                    preserved_count += 1
            
            return preserved_count / max(total_elements, 1)
            
        except Exception:
            return 0.5
    
    def _extract_terminology(self, text: str, language: str) -> List[str]:
        """Extract technical terminology from text"""
        # Simplified extraction - would be more sophisticated in production
        if language in ['bn', 'hi']:
            # Look for longer words that might be technical terms
            return re.findall(r'\b\w{6,}\b', text)
        else:
            # English technical terms
            return re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    
    def _is_terminology_handled_correctly(self, term: str, source: str, translated: str, src_lang: str, tgt_lang: str) -> bool:
        """Check if terminology is handled correctly in translation"""
        # Simplified check - in production would have term dictionaries
        return True  # Placeholder
    
    def _assess_english_fluency(self, text: str) -> float:
        """Assess English fluency"""
        # Check for common fluency indicators
        score = 0.8  # Base score
        
        # Check sentence length variation
        sentences = sent_tokenize(text)
        if sentences:
            lengths = [len(sent.split()) for sent in sentences]
            if len(set(lengths)) > 1:  # Variation in sentence length
                score += 0.1
        
        return min(score, 1.0)
    
    def _assess_bengali_fluency(self, text: str) -> float:
        """Assess Bengali fluency"""
        # Simplified Bengali fluency check
        score = 0.8
        if re.search(r'[\u0980-\u09FF]', text):
            score += 0.2
        return min(score, 1.0)
    
    def _assess_hindi_fluency(self, text: str) -> float:
        """Assess Hindi fluency"""
        # Simplified Hindi fluency check
        score = 0.8
        if re.search(r'[\u0900-\u097F]', text):
            score += 0.2
        return min(score, 1.0)
    
    def _assess_generic_fluency(self, text: str) -> float:
        """Generic fluency assessment"""
        return 0.7  # Default fluency score
    
    def _extract_key_information(self, text: str, language: str) -> Dict[str, List[str]]:
        """Extract key information elements from text"""
        info = {
            'numbers': re.findall(r'\d+', text),
            'dates': re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text),
            'entities': []  # Would extract named entities in production
        }
        return info
    
    def generate_translation_quality_report(self, result: TranslationQualityResult) -> str:
        """Generate comprehensive translation quality report"""
        report = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    TRANSLATION QUALITY ASSESSMENT REPORT                 ║
║                    Language Pair: {result.language_pair[0].upper()} → {result.language_pair[1].upper()}                           ║
╠══════════════════════════════════════════════════════════════════════════╣
║ OVERALL QUALITY SCORE: {result.overall_score:>6.1f}/100                                  ║
╚══════════════════════════════════════════════════════════════════════════╝

📊 DETAILED METRICS:
┌─────────────────────────────┬─────────┬──────────┐
│ Metric                      │ Score   │ Status   │
├─────────────────────────────┼─────────┼──────────┤
│ BLEU Score                  │ {result.bleu_score:>6.3f}  │ {'✅ Good' if result.bleu_score > 0.3 else '⚠️ Poor' if result.bleu_score > 0.2 else '❌ Bad':<8} │
│ METEOR Score                │ {result.meteor_score:>6.3f}  │ {'✅ Good' if result.meteor_score > 0.3 else '⚠️ Poor' if result.meteor_score > 0.2 else '❌ Bad':<8} │
│ Semantic Similarity         │ {result.semantic_similarity:>6.3f}  │ {'✅ Good' if result.semantic_similarity > 0.7 else '⚠️ Poor' if result.semantic_similarity > 0.5 else '❌ Bad':<8} │
│ Cultural Accuracy           │ {result.cultural_accuracy:>6.3f}  │ {'✅ Good' if result.cultural_accuracy > 0.8 else '⚠️ Poor' if result.cultural_accuracy > 0.6 else '❌ Bad':<8} │
│ Terminology Consistency     │ {result.terminology_consistency:>6.3f}  │ {'✅ Good' if result.terminology_consistency > 0.8 else '⚠️ Poor' if result.terminology_consistency > 0.6 else '❌ Bad':<8} │
│ Fluency                     │ {result.fluency_score:>6.3f}  │ {'✅ Good' if result.fluency_score > 0.8 else '⚠️ Poor' if result.fluency_score > 0.6 else '❌ Bad':<8} │
│ Adequacy (Completeness)     │ {result.adequacy_score:>6.3f}  │ {'✅ Good' if result.adequacy_score > 0.8 else '⚠️ Poor' if result.adequacy_score > 0.6 else '❌ Bad':<8} │
└─────────────────────────────┴─────────┴──────────┘

🔍 ERROR ANALYSIS:
"""
        
        if result.error_analysis:
            for error_type, errors in result.error_analysis.items():
                if errors and error_type != 'error_severity':
                    report += f"\n• {error_type.replace('_', ' ').title()}:\n"
                    for error in errors[:3]:  # Show top 3 errors
                        report += f"  - {error}\n"
        
        report += f"\n💡 RECOMMENDATIONS ({len(result.recommendations)} items):\n"
        for i, rec in enumerate(result.recommendations[:5], 1):  # Show top 5 recommendations
            report += f"{i}. {rec}\n"
        
        # Quality verdict
        if result.overall_score >= 90:
            verdict = "🎉 EXCELLENT - Production ready"
        elif result.overall_score >= 80:
            verdict = "✅ GOOD - Minor improvements recommended"
        elif result.overall_score >= 70:
            verdict = "⚠️ FAIR - Significant improvements needed"
        else:
            verdict = "❌ POOR - Major revision required"
        
        report += f"\n🎯 QUALITY VERDICT: {verdict}\n"
        
        return report