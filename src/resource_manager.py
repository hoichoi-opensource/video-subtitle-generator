"""
Production-grade resource management and cleanup
Handles memory, disk space, temporary files, and cloud resources
"""

import os
import gc
import time
import threading
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import weakref
import atexit

from .exceptions import ResourceError, CloudStorageError
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class ResourceUsage:
    """Resource usage metrics"""
    memory_mb: float
    disk_usage_gb: float
    temp_files: int
    temp_size_mb: float
    open_files: int
    timestamp: datetime


class TempFileManager:
    """Manages temporary files with automatic cleanup"""
    
    def __init__(self, base_dir: str = None, max_age_hours: int = 24):
        self.base_dir = Path(base_dir) if base_dir else Path(tempfile.gettempdir()) / "subtitle_generator"
        self.max_age_hours = max_age_hours
        self.tracked_files: Set[Path] = set()
        self.tracked_dirs: Set[Path] = set()
        self._lock = threading.Lock()
        
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Register cleanup on exit
        atexit.register(self.cleanup_all)
    
    @contextmanager
    def temp_file(self, suffix: str = "", prefix: str = "temp_", directory: str = None):
        """Context manager for temporary files"""
        temp_dir = Path(directory) if directory else self.base_dir
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temporary file
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=str(temp_dir))
        temp_path = Path(temp_path)
        
        try:
            os.close(fd)  # Close file descriptor, keep file
            with self._lock:
                self.tracked_files.add(temp_path)
            
            logger.debug(f"Created temporary file: {temp_path}")
            yield temp_path
            
        finally:
            self._safe_remove_file(temp_path)
    
    @contextmanager
    def temp_directory(self, prefix: str = "temp_dir_", parent_dir: str = None):
        """Context manager for temporary directories"""
        parent = Path(parent_dir) if parent_dir else self.base_dir
        parent.mkdir(parents=True, exist_ok=True)
        
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=str(parent)))
        
        try:
            with self._lock:
                self.tracked_dirs.add(temp_dir)
            
            logger.debug(f"Created temporary directory: {temp_dir}")
            yield temp_dir
            
        finally:
            self._safe_remove_directory(temp_dir)
    
    def create_job_directory(self, job_id: str) -> Path:
        """Create job-specific directory"""
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        with self._lock:
            self.tracked_dirs.add(job_dir)
        
        logger.info(f"Created job directory: {job_dir}")
        return job_dir
    
    def cleanup_job(self, job_id: str):
        """Clean up job-specific resources"""
        job_dir = self.base_dir / job_id
        self._safe_remove_directory(job_dir)
    
    def cleanup_old_files(self):
        """Clean up old temporary files"""
        cutoff_time = time.time() - (self.max_age_hours * 3600)
        cleaned_count = 0
        
        try:
            for item in self.base_dir.rglob("*"):
                if item.is_file() and item.stat().st_mtime < cutoff_time:
                    self._safe_remove_file(item)
                    cleaned_count += 1
                elif item.is_dir() and not any(item.iterdir()) and item.stat().st_mtime < cutoff_time:
                    self._safe_remove_directory(item)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old temporary files/directories")
                
        except Exception as e:
            logger.warning(f"Error during old file cleanup: {e}")
    
    def cleanup_all(self):
        """Clean up all tracked resources"""
        with self._lock:
            # Clean up tracked files
            for file_path in list(self.tracked_files):
                self._safe_remove_file(file_path)
            
            # Clean up tracked directories
            for dir_path in list(self.tracked_dirs):
                self._safe_remove_directory(dir_path)
    
    def get_usage(self) -> Dict[str, Any]:
        """Get temporary file usage statistics"""
        total_size = 0
        file_count = 0
        
        try:
            for item in self.base_dir.rglob("*"):
                if item.is_file():
                    file_count += 1
                    total_size += item.stat().st_size
        except Exception as e:
            logger.warning(f"Error calculating temp file usage: {e}")
        
        return {
            'base_directory': str(self.base_dir),
            'file_count': file_count,
            'total_size_mb': total_size / (1024 * 1024),
            'tracked_files': len(self.tracked_files),
            'tracked_dirs': len(self.tracked_dirs)
        }
    
    def _safe_remove_file(self, file_path: Path):
        """Safely remove a file"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Removed temporary file: {file_path}")
            
            with self._lock:
                self.tracked_files.discard(file_path)
                
        except Exception as e:
            logger.warning(f"Failed to remove file {file_path}: {e}")
    
    def _safe_remove_directory(self, dir_path: Path):
        """Safely remove a directory and its contents"""
        try:
            if dir_path.exists() and dir_path.is_dir():
                shutil.rmtree(str(dir_path))
                logger.debug(f"Removed temporary directory: {dir_path}")
            
            with self._lock:
                self.tracked_dirs.discard(dir_path)
                
        except Exception as e:
            logger.warning(f"Failed to remove directory {dir_path}: {e}")


class MemoryManager:
    """Memory usage monitoring and management"""
    
    def __init__(self, warning_threshold_mb: int = 4096, critical_threshold_mb: int = 6144):
        self.warning_threshold_mb = warning_threshold_mb
        self.critical_threshold_mb = critical_threshold_mb
        self.monitoring = False
        self._monitor_thread = None
        self._stop_monitoring = threading.Event()
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / (1024 * 1024),
                'vms_mb': memory_info.vms / (1024 * 1024),
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / (1024 * 1024)
            }
        except ImportError:
            return {'error': 'psutil not available'}
        except Exception as e:
            logger.warning(f"Error getting memory usage: {e}")
            return {'error': str(e)}
    
    def check_memory_pressure(self) -> Optional[str]:
        """Check if memory usage is concerning"""
        usage = self.get_memory_usage()
        
        if 'rss_mb' not in usage:
            return None
        
        rss_mb = usage['rss_mb']
        
        if rss_mb > self.critical_threshold_mb:
            return 'critical'
        elif rss_mb > self.warning_threshold_mb:
            return 'warning'
        
        return None
    
    def force_gc(self):
        """Force garbage collection"""
        logger.debug("Forcing garbage collection")
        collected = gc.collect()
        logger.debug(f"Garbage collection freed {collected} objects")
        return collected
    
    def start_monitoring(self, interval_seconds: int = 30):
        """Start memory monitoring in background thread"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_memory,
            args=(interval_seconds,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Started memory monitoring")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        self._stop_monitoring.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Stopped memory monitoring")
    
    def _monitor_memory(self, interval_seconds: int):
        """Memory monitoring loop"""
        while not self._stop_monitoring.wait(interval_seconds):
            try:
                pressure = self.check_memory_pressure()
                usage = self.get_memory_usage()
                
                if pressure == 'critical':
                    logger.warning(f"Critical memory usage: {usage.get('rss_mb', 0):.1f}MB")
                    self.force_gc()
                elif pressure == 'warning':
                    logger.info(f"High memory usage: {usage.get('rss_mb', 0):.1f}MB")
                
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}")


class CloudResourceManager:
    """Manages cloud resources with cleanup"""
    
    def __init__(self):
        self.buckets_to_cleanup: Set[str] = set()
        self.blobs_to_cleanup: Set[tuple] = set()  # (bucket, blob_name)
        self._cleanup_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        
        # Register cleanup on exit
        atexit.register(self.cleanup_all)
    
    def register_bucket_cleanup(self, bucket_name: str):
        """Register bucket for cleanup"""
        with self._lock:
            self.buckets_to_cleanup.add(bucket_name)
        logger.debug(f"Registered bucket for cleanup: {bucket_name}")
    
    def register_blob_cleanup(self, bucket_name: str, blob_name: str):
        """Register blob for cleanup"""
        with self._lock:
            self.blobs_to_cleanup.add((bucket_name, blob_name))
        logger.debug(f"Registered blob for cleanup: {bucket_name}/{blob_name}")
    
    def register_cleanup_callback(self, callback: Callable):
        """Register custom cleanup callback"""
        with self._lock:
            self._cleanup_callbacks.append(callback)
    
    def cleanup_job_resources(self, bucket_name: str, job_id: str, gcs_client=None):
        """Clean up resources for a specific job"""
        if not gcs_client:
            logger.warning("No GCS client provided for cleanup")
            return
        
        try:
            bucket = gcs_client.bucket(bucket_name)
            
            # Clean up job-specific blobs
            blobs_deleted = 0
            for blob in bucket.list_blobs(prefix=f"chunks/"):
                try:
                    blob.delete()
                    blobs_deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete blob {blob.name}: {e}")
            
            for blob in bucket.list_blobs(prefix=f"subtitles/"):
                try:
                    blob.delete()
                    blobs_deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete blob {blob.name}: {e}")
            
            logger.info(f"Cleaned up {blobs_deleted} blobs for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up job resources: {e}")
    
    def cleanup_all(self):
        """Clean up all registered cloud resources"""
        with self._lock:
            # Run custom cleanup callbacks
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in cleanup callback: {e}")
            
            # Note: We don't automatically delete buckets or blobs here
            # as it could be destructive. This would need explicit implementation
            # based on specific requirements
            
            logger.info("Cloud resource cleanup completed")


class ResourceManager:
    """Main resource manager coordinating all resource management"""
    
    def __init__(self, temp_dir: str = None):
        self.temp_manager = TempFileManager(temp_dir)
        self.memory_manager = MemoryManager()
        self.cloud_manager = CloudResourceManager()
        self._resource_monitors: Dict[str, ResourceUsage] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def managed_resources(self, job_id: str):
        """Context manager for complete resource management"""
        logger.info(f"Starting resource management for job {job_id}")
        
        # Create job directory
        job_dir = self.temp_manager.create_job_directory(job_id)
        
        # Start monitoring
        self.memory_manager.start_monitoring()
        
        try:
            yield job_dir
            
        finally:
            # Cleanup
            logger.info(f"Cleaning up resources for job {job_id}")
            self.temp_manager.cleanup_job(job_id)
            self.memory_manager.stop_monitoring()
            self.memory_manager.force_gc()
    
    def get_resource_usage(self) -> ResourceUsage:
        """Get current resource usage"""
        memory_usage = self.memory_manager.get_memory_usage()
        temp_usage = self.temp_manager.get_usage()
        
        # Get disk usage
        try:
            disk_usage = shutil.disk_usage(self.temp_manager.base_dir)
            disk_free_gb = disk_usage.free / (1024**3)
        except Exception:
            disk_free_gb = 0
        
        return ResourceUsage(
            memory_mb=memory_usage.get('rss_mb', 0),
            disk_usage_gb=disk_free_gb,
            temp_files=temp_usage['file_count'],
            temp_size_mb=temp_usage['total_size_mb'],
            open_files=0,  # Would need psutil for this
            timestamp=datetime.now()
        )
    
    def health_check(self) -> Dict[str, Any]:
        """Resource manager health check"""
        try:
            usage = self.get_resource_usage()
            memory_pressure = self.memory_manager.check_memory_pressure()
            
            # Check disk space
            disk_warning = usage.disk_usage_gb < 5.0  # Less than 5GB free
            
            # Check temp file accumulation
            temp_warning = usage.temp_size_mb > 1024  # More than 1GB temp files
            
            status = 'healthy'
            warnings = []
            
            if memory_pressure:
                warnings.append(f"Memory pressure: {memory_pressure}")
                if memory_pressure == 'critical':
                    status = 'critical'
                elif status == 'healthy':
                    status = 'warning'
            
            if disk_warning:
                warnings.append(f"Low disk space: {usage.disk_usage_gb:.1f}GB free")
                if usage.disk_usage_gb < 1.0:
                    status = 'critical'
                elif status == 'healthy':
                    status = 'warning'
            
            if temp_warning:
                warnings.append(f"High temp usage: {usage.temp_size_mb:.1f}MB")
                if status == 'healthy':
                    status = 'warning'
            
            return {
                'status': status,
                'warnings': warnings,
                'usage': usage.__dict__,
                'memory_monitoring': self.memory_manager.monitoring
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def cleanup_old_resources(self):
        """Clean up old resources across all managers"""
        logger.info("Starting cleanup of old resources")
        
        # Clean old temp files
        self.temp_manager.cleanup_old_files()
        
        # Force garbage collection
        self.memory_manager.force_gc()
        
        logger.info("Old resource cleanup completed")


# Global resource manager
resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance"""
    return resource_manager