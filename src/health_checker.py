"""
Production-grade health check system
Comprehensive monitoring of all system components
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum

from .exceptions import BaseSubtitleError
from .logger import get_logger, logger_manager
from .resource_manager import get_resource_manager
from .validators import SystemValidator

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Health check result"""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: str
    duration_ms: float


class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self.monitoring = False
        self._monitor_thread = None
        self._stop_monitoring = threading.Event()
        
        # Register default health checks
        self._register_default_checks()
    
    def register_check(self, name: str, check_func: Callable[[], Dict[str, Any]]):
        """Register a health check function"""
        self.checks[name] = check_func
        logger.debug(f"Registered health check: {name}")
    
    def _register_default_checks(self):
        """Register default system health checks"""
        self.register_check("system_requirements", self._check_system_requirements)
        self.register_check("disk_space", self._check_disk_space)
        self.register_check("memory_usage", self._check_memory_usage)
        self.register_check("logging_system", self._check_logging_system)
        self.register_check("resource_manager", self._check_resource_manager)
        self.register_check("temp_files", self._check_temp_files)
    
    def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check"""
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found",
                details={},
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_ms=0
            )
        
        start_time = time.time()
        
        try:
            logger.debug(f"Running health check: {name}")
            result = self.checks[name]()
            duration_ms = (time.time() - start_time) * 1000
            
            # Determine status from result
            status = HealthStatus.HEALTHY
            message = "OK"
            
            if 'status' in result:
                status_str = result['status'].lower()
                if status_str == 'warning':
                    status = HealthStatus.WARNING
                elif status_str in ['critical', 'error', 'unhealthy']:
                    status = HealthStatus.CRITICAL
                elif status_str == 'unknown':
                    status = HealthStatus.UNKNOWN
            
            if 'message' in result:
                message = result['message']
            elif 'error' in result:
                message = f"Error: {result['error']}"
                status = HealthStatus.CRITICAL
            elif status == HealthStatus.WARNING and 'warnings' in result:
                message = f"Warnings: {', '.join(result['warnings'])}"
            
            health_result = HealthCheckResult(
                name=name,
                status=status,
                message=message,
                details=result,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms
            )
            
            self.last_results[name] = health_result
            logger.debug(f"Health check {name} completed: {status.value}")
            
            return health_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_result = HealthCheckResult(
                name=name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                details={'error': str(e), 'exception_type': type(e).__name__},
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms
            )
            
            self.last_results[name] = error_result
            logger.error(f"Health check {name} failed: {e}")
            
            return error_result
    
    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        logger.info("Running all health checks")
        results = {}
        
        for name in self.checks:
            results[name] = self.run_check(name)
        
        # Overall system status
        overall_status = self._determine_overall_status(results)
        logger.info(f"Overall system health: {overall_status.value}")
        
        return results
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health summary"""
        results = self.run_all_checks()
        overall_status = self._determine_overall_status(results)
        
        # Count statuses
        status_counts = {status.value: 0 for status in HealthStatus}
        for result in results.values():
            status_counts[result.status.value] += 1
        
        # Get critical and warning issues
        critical_issues = [r for r in results.values() if r.status == HealthStatus.CRITICAL]
        warning_issues = [r for r in results.values() if r.status == HealthStatus.WARNING]
        
        return {
            'overall_status': overall_status.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_checks': len(results),
            'status_counts': status_counts,
            'critical_issues': [{'name': r.name, 'message': r.message} for r in critical_issues],
            'warning_issues': [{'name': r.name, 'message': r.message} for r in warning_issues],
            'details': {name: asdict(result) for name, result in results.items()}
        }
    
    def start_monitoring(self, interval_seconds: int = 300):  # 5 minutes default
        """Start continuous health monitoring"""
        if self.monitoring:
            logger.warning("Health monitoring already running")
            return
        
        self.monitoring = True
        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_health,
            args=(interval_seconds,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info(f"Started health monitoring with {interval_seconds}s interval")
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        self._stop_monitoring.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        logger.info("Stopped health monitoring")
    
    def _monitor_health(self, interval_seconds: int):
        """Health monitoring loop"""
        while not self._stop_monitoring.wait(interval_seconds):
            try:
                health = self.get_system_health()
                
                # Log health status
                if health['overall_status'] == 'critical':
                    logger.error(f"System health critical: {len(health['critical_issues'])} critical issues")
                elif health['overall_status'] == 'warning':
                    logger.warning(f"System health warning: {len(health['warning_issues'])} warnings")
                else:
                    logger.debug("System health OK")
                
                # Log specific issues
                for issue in health['critical_issues']:
                    logger.error(f"Critical health issue - {issue['name']}: {issue['message']}")
                
                for issue in health['warning_issues']:
                    logger.warning(f"Health warning - {issue['name']}: {issue['message']}")
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
    
    def _determine_overall_status(self, results: Dict[str, HealthCheckResult]) -> HealthStatus:
        """Determine overall system health status"""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in results.values()]
        
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif HealthStatus.UNKNOWN in statuses:
            return HealthStatus.WARNING  # Treat unknown as warning
        else:
            return HealthStatus.HEALTHY
    
    # Default health check implementations
    
    def _check_system_requirements(self) -> Dict[str, Any]:
        """Check system requirements"""
        return SystemValidator.validate_system_requirements()
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space"""
        try:
            import shutil
            from pathlib import Path
            
            usage = shutil.disk_usage(Path.cwd())
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            used_percent = ((usage.total - usage.free) / usage.total) * 100
            
            status = 'healthy'
            warnings = []
            
            if free_gb < 1.0:
                status = 'critical'
                warnings.append(f"Critical: Only {free_gb:.1f}GB free")
            elif free_gb < 5.0:
                status = 'warning'
                warnings.append(f"Low disk space: {free_gb:.1f}GB free")
            elif used_percent > 90:
                status = 'warning'
                warnings.append(f"High disk usage: {used_percent:.1f}%")
            
            return {
                'status': status,
                'warnings': warnings,
                'free_gb': free_gb,
                'total_gb': total_gb,
                'used_percent': used_percent
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            resource_manager = get_resource_manager()
            memory_info = resource_manager.memory_manager.get_memory_usage()
            
            if 'error' in memory_info:
                return {'status': 'unknown', 'message': memory_info['error']}
            
            rss_mb = memory_info.get('rss_mb', 0)
            percent = memory_info.get('percent', 0)
            
            status = 'healthy'
            warnings = []
            
            if rss_mb > 6144:  # 6GB
                status = 'critical'
                warnings.append(f"Critical memory usage: {rss_mb:.1f}MB")
            elif rss_mb > 4096:  # 4GB
                status = 'warning'
                warnings.append(f"High memory usage: {rss_mb:.1f}MB")
            elif percent > 80:
                status = 'warning'
                warnings.append(f"High memory percentage: {percent:.1f}%")
            
            return {
                'status': status,
                'warnings': warnings,
                **memory_info
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _check_logging_system(self) -> Dict[str, Any]:
        """Check logging system health"""
        try:
            return logger_manager.health_check()
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _check_resource_manager(self) -> Dict[str, Any]:
        """Check resource manager health"""
        try:
            resource_manager = get_resource_manager()
            return resource_manager.health_check()
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _check_temp_files(self) -> Dict[str, Any]:
        """Check temporary file accumulation"""
        try:
            resource_manager = get_resource_manager()
            temp_usage = resource_manager.temp_manager.get_usage()
            
            file_count = temp_usage['file_count']
            size_mb = temp_usage['total_size_mb']
            
            status = 'healthy'
            warnings = []
            
            if size_mb > 2048:  # 2GB
                status = 'critical'
                warnings.append(f"Critical temp usage: {size_mb:.1f}MB")
            elif size_mb > 1024:  # 1GB
                status = 'warning'
                warnings.append(f"High temp usage: {size_mb:.1f}MB")
            elif file_count > 1000:
                status = 'warning'
                warnings.append(f"Many temp files: {file_count}")
            
            return {
                'status': status,
                'warnings': warnings,
                **temp_usage
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


# Global health checker
health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    return health_checker


def quick_health_check() -> Dict[str, Any]:
    """Quick health check for API endpoints"""
    return health_checker.get_system_health()


def is_system_healthy() -> bool:
    """Check if system is in healthy state"""
    health = health_checker.get_system_health()
    return health['overall_status'] in ['healthy', 'warning']