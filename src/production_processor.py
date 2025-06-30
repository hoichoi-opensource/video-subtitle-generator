"""
Production-grade subtitle processor
Integrates all production features: error handling, monitoring, fallbacks, etc.
"""

import os
import time
import signal
import atexit
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
import threading

# Core components
from .subtitle_processor import SubtitleProcessor as BaseSubtitleProcessor
from .config_manager import ConfigManager
from .state_manager import StateManager

# Production components
from .exceptions import (
    BaseSubtitleError, ValidationError, ConfigurationError,
    ResourceError, NonRetryableError
)
from .validators import VideoValidator, LanguageValidator, SystemValidator
from .resource_manager import get_resource_manager
from .health_checker import get_health_checker, is_system_healthy
from .fallback_handler import get_robust_processor, get_degradation_manager
from .logger import get_logger, logger_manager
from .retry_handler import retry_handler

logger = get_logger(__name__)


class ProductionSubtitleProcessor:
    """Production-grade subtitle processor with comprehensive error handling"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = None
        self.base_processor = None
        self.resource_manager = get_resource_manager()
        self.health_checker = get_health_checker()
        self.robust_processor = get_robust_processor()
        self.degradation_manager = get_degradation_manager()
        
        # Graceful shutdown handling
        self._shutdown_requested = False
        self._shutdown_lock = threading.Lock()
        self._setup_signal_handlers()
        
        # Performance tracking
        self._start_time = None
        self._job_metrics = {}
        
        # Initialize components
        self._initialize()
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        atexit.register(self.cleanup)
    
    def _initialize(self):
        """Initialize all components with comprehensive validation"""
        logger.info("Initializing production subtitle processor")
        
        try:
            # System health check
            if not is_system_healthy():
                health = self.health_checker.get_system_health()
                logger.warning(f"System health issues detected: {health['critical_issues']}")
                
                # Decide whether to continue based on criticality
                critical_count = len(health['critical_issues'])
                if critical_count > 0:
                    raise ResourceError(
                        f"System has {critical_count} critical health issues",
                        context=health
                    )
            
            # Load and validate configuration
            self.config = ConfigManager(self.config_path, validate=True)
            logger.info("Configuration loaded and validated successfully")
            
            # Initialize base processor
            self.base_processor = BaseSubtitleProcessor(self.config)
            logger.info("Base processor initialized")
            
            # Start health monitoring
            self.health_checker.start_monitoring(interval_seconds=300)  # 5 minutes
            
            # Start memory monitoring
            self.resource_manager.memory_manager.start_monitoring()
            
            logger.info("Production processor initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize production processor: {e}")
            raise ConfigurationError(
                f"Production processor initialization failed: {str(e)}",
                context={'config_path': self.config_path}
            )
    
    def process_video(
        self,
        video_path: str,
        languages: List[str],
        enable_sdh: bool = False,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process video with production-grade error handling and monitoring
        """
        self._start_time = time.time()
        
        # Input validation
        try:
            video_info = VideoValidator.validate_video_file(video_path)
            validated_languages = LanguageValidator.validate_language_codes(languages)
            logger.info(f"Input validation passed for {video_path}")
        except ValidationError as e:
            logger.error(f"Input validation failed: {e}")
            raise
        
        # Check system health before processing
        if not is_system_healthy():
            health = self.health_checker.get_system_health()
            if health['overall_status'] == 'critical':
                raise ResourceError(
                    "System is in critical state, cannot process video",
                    context=health
                )
            logger.warning("System has health warnings, proceeding with caution")
        
        # Use resource management
        with self.resource_manager.managed_resources(job_id or "default") as job_dir:
            logger.info(f"Starting video processing with job directory: {job_dir}")
            logger_manager.log_job_start(job_id or "default", video_path, validated_languages)
            
            try:
                # Process with fallback handling
                result = self._process_with_monitoring(
                    video_path=video_path,
                    languages=validated_languages,
                    enable_sdh=enable_sdh,
                    job_id=job_id
                )
                
                # Log successful completion
                duration_ms = (time.time() - self._start_time) * 1000
                output_files = result.get('output_files', [])
                logger_manager.log_job_complete(job_id or "default", output_files, duration_ms)
                
                # Add performance metrics
                result['performance'] = self._get_performance_metrics()
                result['partial_results'] = self.degradation_manager.get_partial_results()
                
                logger.info(f"Video processing completed successfully in {duration_ms:.2f}ms")
                return result
                
            except Exception as e:
                duration_ms = (time.time() - self._start_time) * 1000
                logger_manager.log_error(e, job_id=job_id)
                
                # Check if we can provide partial results
                partial_results = self.degradation_manager.get_partial_results()
                if partial_results.get('partial_successes'):
                    logger.info("Returning partial results due to processing errors")
                    return {
                        'status': 'partial_success',
                        'error': str(e),
                        'partial_results': partial_results,
                        'performance': self._get_performance_metrics()
                    }
                
                # Re-raise if no partial results available
                raise
    
    def _process_with_monitoring(
        self,
        video_path: str,
        languages: List[str],
        enable_sdh: bool,
        job_id: Optional[str]
    ) -> Dict[str, Any]:
        """Process video with comprehensive monitoring and fallback handling"""
        
        # Track progress with fallback handling
        successful_stages = []
        failed_stages = []
        
        # Stage 1: Video Analysis
        analysis_result, success = self.robust_processor.process_with_fallback(
            operation_func=self._analyze_video_robust,
            operation_name="video_analysis",
            context={'video_path': video_path},
            required=True
        )
        
        if success:
            successful_stages.append('analysis')
        else:
            failed_stages.append('analysis')
            raise ResourceError("Video analysis failed and no fallback succeeded")
        
        # Stage 2: Video Chunking
        chunks_result, success = self.robust_processor.process_with_fallback(
            operation_func=self._chunk_video_robust,
            operation_name="video_chunking",
            context={'video_path': video_path, 'job_id': job_id},
            required=True
        )
        
        if success:
            successful_stages.append('chunking')
        else:
            failed_stages.append('chunking')
            raise ResourceError("Video chunking failed")
        
        # Stage 3: Cloud Upload
        upload_result, success = self.robust_processor.process_with_fallback(
            operation_func=self._upload_chunks_robust,
            operation_name="cloud_upload",
            context={'chunks': chunks_result, 'job_id': job_id},
            required=True
        )
        
        if success:
            successful_stages.append('upload')
        else:
            failed_stages.append('upload')
            raise ResourceError("Cloud upload failed")
        
        # Stage 4: Subtitle Generation (with batch fallback handling)
        generation_results, success_rate = self.robust_processor.process_batch_with_fallback(
            items=[(chunk, lang) for chunk in upload_result for lang in languages],
            operation_func=self._generate_subtitle_robust,
            operation_name="subtitle_generation",
            min_success_rate=0.3  # Accept if at least 30% succeed
        )
        
        # Filter successful results
        successful_subtitles = [r for r in generation_results if r is not None]
        
        if success_rate >= 0.3:
            successful_stages.append('generation')
        else:
            failed_stages.append('generation')
            if not successful_subtitles:
                raise ResourceError("Subtitle generation completely failed")
        
        # Stage 5: Download and Merge (best effort)
        final_result, success = self.robust_processor.process_with_fallback(
            operation_func=self._finalize_subtitles_robust,
            operation_name="subtitle_finalization",
            context={
                'subtitles': successful_subtitles,
                'video_path': video_path,
                'job_id': job_id
            },
            required=False
        )
        
        if success:
            successful_stages.append('finalization')
        else:
            failed_stages.append('finalization')
        
        # Compile results
        result = {
            'status': 'success' if len(failed_stages) == 0 else 'partial_success',
            'successful_stages': successful_stages,
            'failed_stages': failed_stages,
            'subtitle_success_rate': success_rate,
            'output_files': final_result.get('output_files', []) if final_result else [],
            'metadata': {
                'video_info': analysis_result,
                'chunks_processed': len(chunks_result) if chunks_result else 0,
                'subtitles_generated': len(successful_subtitles),
                'languages_requested': len(languages),
                'sdh_enabled': enable_sdh
            }
        }
        
        return result
    
    def _analyze_video_robust(self, video_path: str, **kwargs) -> Dict[str, Any]:
        """Robust video analysis with validation"""
        logger.info(f"Analyzing video: {video_path}")
        
        # Use existing base processor functionality
        video_info = self.base_processor.video_chunker.analyze_video(video_path)
        
        # Additional validation
        if video_info['duration'] <= 0:
            raise ValidationError("Invalid video duration")
        
        if video_info['total_chunks'] <= 0:
            raise ValidationError("No chunks would be created")
        
        return video_info
    
    def _chunk_video_robust(self, video_path: str, job_id: str, **kwargs) -> List[str]:
        """Robust video chunking"""
        logger.info(f"Chunking video: {video_path}")
        
        # Create job state for chunking
        job_state = self.base_processor.state_manager.create_job(
            video_path=video_path,
            languages=kwargs.get('languages', ['eng']),
            enable_sdh=kwargs.get('enable_sdh', False),
            job_id=job_id
        )
        
        # Perform chunking
        chunks = self.base_processor.video_chunker.split_video(
            video_path=video_path,
            job_id=job_state.job_id
        )
        
        if not chunks:
            raise ResourceError("No video chunks were created")
        
        return chunks
    
    def _upload_chunks_robust(self, chunks: List[str], job_id: str, **kwargs) -> List[Dict[str, str]]:
        """Robust chunk upload"""
        logger.info(f"Uploading {len(chunks)} chunks to cloud storage")
        
        # Initialize GCS handler
        self.base_processor.gcs_handler.initialize()
        
        # Create bucket
        bucket_name = self.base_processor.gcs_handler.create_job_bucket(job_id)
        
        # Upload chunks
        uploaded_chunks = self.base_processor.gcs_handler.upload_chunks(
            chunks=chunks,
            bucket_name=bucket_name
        )
        
        if not uploaded_chunks:
            raise ResourceError("No chunks were uploaded successfully")
        
        return uploaded_chunks
    
    def _generate_subtitle_robust(self, chunk_lang_tuple: tuple, **kwargs) -> Optional[Dict[str, Any]]:
        """Robust subtitle generation for single chunk/language combination"""
        chunk, language = chunk_lang_tuple
        
        try:
            # Generate subtitle using AI generator
            subtitle_content = self.base_processor.ai_generator._generate_subtitle_for_chunk(
                video_uri=chunk['gcs'],
                language=language,
                is_sdh=kwargs.get('enable_sdh', False)
            )
            
            if subtitle_content:
                return {
                    'chunk': chunk['chunk'],
                    'language': language,
                    'content': subtitle_content,
                    'gcs_uri': chunk['gcs']
                }
            else:
                return None
                
        except Exception as e:
            logger.warning(f"Failed to generate subtitle for {chunk['chunk']} in {language}: {e}")
            return None
    
    def _finalize_subtitles_robust(
        self,
        subtitles: List[Dict[str, Any]],
        video_path: str,
        job_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Robust subtitle finalization"""
        logger.info(f"Finalizing {len(subtitles)} subtitles")
        
        # Group subtitles by language for merging
        grouped_subtitles = {}
        for subtitle in subtitles:
            lang = subtitle['language']
            if lang not in grouped_subtitles:
                grouped_subtitles[lang] = []
            grouped_subtitles[lang].append(subtitle)
        
        # Merge subtitles using base processor
        output_files = []
        for language, lang_subtitles in grouped_subtitles.items():
            try:
                merged_files = self.base_processor.subtitle_merger.merge_subtitles(
                    subtitles=lang_subtitles,
                    job_id=job_id,
                    video_path=video_path
                )
                output_files.extend(merged_files)
            except Exception as e:
                logger.warning(f"Failed to merge subtitles for {language}: {e}")
        
        return {'output_files': output_files}
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the processing job"""
        duration_ms = (time.time() - self._start_time) * 1000 if self._start_time else 0
        
        return {
            'total_duration_ms': duration_ms,
            'memory_usage': self.resource_manager.memory_manager.get_memory_usage(),
            'resource_usage': self.resource_manager.get_resource_usage().__dict__,
            'retry_stats': {
                'circuit_breaker_states': {
                    key: cb.state for key, cb in retry_handler.circuit_breakers.items()
                }
            },
            'logger_metrics': logger_manager.performance.get_metrics()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        return {
            'system_health': self.health_checker.get_system_health(),
            'resource_health': self.resource_manager.health_check(),
            'config_health': self.config.health_check() if self.config else {'status': 'not_loaded'},
            'processor_status': {
                'initialized': self.base_processor is not None,
                'shutdown_requested': self._shutdown_requested
            }
        }
    
    def shutdown(self):
        """Graceful shutdown"""
        with self._shutdown_lock:
            if self._shutdown_requested:
                return
            
            self._shutdown_requested = True
            logger.info("Initiating graceful shutdown...")
            
            try:
                # Stop monitoring
                self.health_checker.stop_monitoring()
                self.resource_manager.memory_manager.stop_monitoring()
                
                # Process any pending retry items
                retry_items = self.degradation_manager.process_retry_queue()
                if retry_items:
                    logger.info(f"Processing {len(retry_items)} retry items during shutdown")
                
                # Clear partial results
                self.degradation_manager.clear_partial_results()
                
                logger.info("Graceful shutdown completed")
                
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
    
    def cleanup(self):
        """Final cleanup on exit"""
        logger.info("Performing final cleanup")
        try:
            self.resource_manager.cleanup_old_resources()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    @contextmanager
    def processing_context(self, job_id: Optional[str] = None):
        """Context manager for safe processing with automatic cleanup"""
        job_id = job_id or f"job_{int(time.time())}"
        
        try:
            # Pre-processing checks
            if self._shutdown_requested:
                raise RuntimeError("Processor is shutting down")
            
            if not is_system_healthy():
                health = self.health_checker.get_system_health()
                if health['overall_status'] == 'critical':
                    raise ResourceError("System health is critical")
            
            logger.info(f"Starting processing context for job {job_id}")
            yield job_id
            
        except Exception as e:
            logger.error(f"Error in processing context for job {job_id}: {e}")
            raise
        finally:
            # Cleanup job resources
            try:
                self.resource_manager.cleanup_old_resources()
                logger.info(f"Completed processing context cleanup for job {job_id}")
            except Exception as e:
                logger.warning(f"Error in context cleanup: {e}")


# Convenience function for one-off processing
def process_video_production(
    video_path: str,
    languages: List[str],
    enable_sdh: bool = False,
    config_path: str = "config/config.yaml"
) -> Dict[str, Any]:
    """
    Process video with production-grade handling
    Convenience function for single video processing
    """
    processor = ProductionSubtitleProcessor(config_path)
    
    try:
        with processor.processing_context() as job_id:
            return processor.process_video(
                video_path=video_path,
                languages=languages,
                enable_sdh=enable_sdh,
                job_id=job_id
            )
    finally:
        processor.shutdown()