# Production Deployment Guide

This document provides comprehensive instructions for deploying and operating the Video Subtitle Generator in production environments.

## 🏭 Production Features

The system has been enhanced with production-grade features:

### ✅ Error Handling & Resilience
- **Comprehensive Exception Hierarchy**: Custom exceptions with detailed context
- **Retry Mechanisms**: Exponential backoff with circuit breakers
- **Fallback Strategies**: Graceful degradation when components fail
- **Input Validation**: Thorough validation of all inputs and configurations

### 📊 Monitoring & Observability
- **Structured Logging**: JSON-formatted logs with performance metrics
- **Health Checks**: System health monitoring with automatic alerts
- **Resource Monitoring**: Memory, disk, and temp file tracking
- **Performance Metrics**: Detailed timing and usage statistics

### 🔧 Resource Management
- **Memory Management**: Automatic garbage collection and monitoring
- **Temporary File Cleanup**: Automatic cleanup with configurable retention
- **Cloud Resource Management**: Proper cleanup of GCS buckets and objects
- **Graceful Shutdown**: Clean shutdown with resource cleanup

### 🛡️ Security & Validation
- **Configuration Validation**: Comprehensive config and system validation
- **Path Security**: Protection against path traversal attacks
- **Resource Limits**: Configurable limits on file sizes and processing time
- **Authentication Handling**: Proper error handling for auth failures

## 🚀 Quick Start

### 1. System Requirements

```bash
# Check system requirements
python3 test_production.py
```

**Minimum Requirements:**
- Python 3.8+
- FFmpeg and FFprobe
- 10GB free disk space
- 2GB available memory
- Google Cloud credentials

### 2. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "from src.production_processor import ProductionSubtitleProcessor; print('✅ Ready')"
```

### 3. Configuration

Create your configuration file:

```yaml
# config/config.yaml
app:
  output_dir: "output"
  temp_dir: "temp"
  
gcp:
  project_id: "your-project-id"
  location: "us-central1"
  auth_method: "service_account"
  service_account_path: "./service-account.json"

vertex_ai:
  temperature: 0.2
  max_output_tokens: 8192
  safety_settings:
    - category: "HARM_CATEGORY_HATE_SPEECH"
      threshold: "BLOCK_NONE"
```

### 4. Basic Usage

```python
from src.production_processor import process_video_production

# Process video with production handling
result = process_video_production(
    video_path="path/to/video.mp4",
    languages=["eng", "hin"],
    enable_sdh=False
)

print(f"Status: {result['status']}")
print(f"Output files: {result['output_files']}")
```

## 📋 Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 -c "from src.health_checker import quick_health_check; h=quick_health_check(); exit(0 if h['overall_status'] in ['healthy','warning'] else 1)"

# Run application
CMD ["python3", "main.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: subtitle-generator
spec:
  replicas: 2
  selector:
    matchLabels:
      app: subtitle-generator
  template:
    metadata:
      labels:
        app: subtitle-generator
    spec:
      containers:
      - name: subtitle-generator
        image: subtitle-generator:latest
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "8Gi"
            cpu: "4"
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
```

## 🔧 Configuration

### Environment Variables

```bash
# Logging
export LOG_LEVEL=INFO
export LOG_DIR=/var/log/subtitle-generator

# Resources
export TEMP_DIR=/tmp/subtitle-generator
export MAX_MEMORY_MB=6144
export MAX_DISK_GB=50

# Processing
export MAX_VIDEO_SIZE_GB=10
export MAX_DURATION_HOURS=12
export CHUNK_DURATION=60

# Health monitoring
export HEALTH_CHECK_INTERVAL=300
export MEMORY_WARNING_THRESHOLD=4096
export MEMORY_CRITICAL_THRESHOLD=6144
```

### Production Configuration

```yaml
# config/config.production.yaml
app:
  name: "Video Subtitle Generator"
  version: "2.0.0"
  environment: "production"
  output_dir: "/data/output"
  temp_dir: "/tmp/subtitle-generator"
  logs_dir: "/var/log/subtitle-generator"

# Resource limits
limits:
  max_video_size_gb: 10
  max_duration_hours: 12
  max_concurrent_jobs: 5
  temp_file_retention_hours: 24

# Monitoring
monitoring:
  health_check_interval: 300
  memory_warning_threshold: 4096
  memory_critical_threshold: 6144
  log_retention_days: 30

# Retry configuration
retry:
  max_attempts: 3
  base_delay: 1.0
  max_delay: 60.0
  circuit_breaker_threshold: 5
```

## 📊 Monitoring

### Health Check Endpoints

```python
from src.health_checker import quick_health_check

# Basic health check
health = quick_health_check()
print(health['overall_status'])  # healthy, warning, critical

# Detailed system health
from src.production_processor import ProductionSubtitleProcessor
processor = ProductionSubtitleProcessor()
detailed_health = processor.health_check()
```

### Metrics Collection

The system provides comprehensive metrics:

```python
# Performance metrics
{
  "total_duration_ms": 45000,
  "memory_usage": {"rss_mb": 1024, "percent": 15.2},
  "retry_stats": {"total_retries": 3, "circuit_breaker_trips": 0},
  "success_rate": 0.95
}

# Resource usage
{
  "disk_usage_gb": 125.5,
  "temp_files": 45,
  "temp_size_mb": 512.3,
  "memory_mb": 1024.7
}
```

### Log Analysis

Logs are structured JSON for easy analysis:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "module": "ai_generator",
  "job_id": "job_123",
  "message": "Subtitle generation completed",
  "duration_ms": 15000,
  "context": {
    "language": "eng",
    "chunks_processed": 12
  }
}
```

## 🚨 Error Handling

### Error Categories

1. **Retryable Errors**: Network issues, temporary service unavailability
2. **Non-Retryable Errors**: Invalid input, authentication failures
3. **Degradable Errors**: Partial failures that allow continued processing

### Fallback Strategies

```python
# Automatic fallback configuration
{
  "NetworkError": "retry_with_delay",
  "QuotaExceededError": "skip_and_continue", 
  "VertexAIError": "use_alternative_method",
  "AuthenticationError": "fail_fast"
}
```

### Alert Configuration

```yaml
alerts:
  critical:
    - system_health_critical
    - memory_usage_critical
    - disk_space_critical
  warning:
    - high_error_rate
    - quota_approaching
    - long_processing_time
```

## 🔒 Security

### Authentication
- Service account key files should be stored securely
- Use IAM roles in cloud environments
- Rotate credentials regularly

### Network Security
- Restrict outbound connections to required GCP services
- Use VPC endpoints where available
- Monitor network traffic

### Data Security
- Temporary files are automatically cleaned up
- No sensitive data is logged
- Processing directories have restricted permissions

## 📈 Performance Optimization

### Recommended Settings

```yaml
# High-performance configuration
processing:
  chunk_duration: 60  # Optimal for most videos
  concurrent_uploads: 3
  batch_size: 5

vertex_ai:
  temperature: 0.2  # Balanced creativity/consistency
  max_output_tokens: 8192
  timeout_seconds: 300

resource_limits:
  memory_warning_mb: 4096
  memory_critical_mb: 6144
  disk_warning_gb: 10
```

### Scaling Guidelines

- **CPU**: 1-4 cores per concurrent job
- **Memory**: 2-8GB depending on video size
- **Storage**: 10GB + 2x largest video size
- **Network**: Stable connection to GCP regions

## 🧪 Testing

### Production Validation

```bash
# Run all production tests
python3 test_production.py

# Test specific components
python3 -c "from src.health_checker import get_health_checker; hc = get_health_checker(); print(hc.get_system_health())"

# Validate configuration
python3 -c "from src.config_manager import ConfigManager; cm = ConfigManager(); print('✅ Config valid')"
```

### Load Testing

```python
# Simulate production load
import concurrent.futures
from src.production_processor import process_video_production

def process_video_concurrent(video_path):
    return process_video_production(video_path, ["eng"])

# Run multiple jobs concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(process_video_concurrent, path) for path in video_paths]
    results = [f.result() for f in futures]
```

## 🛠️ Troubleshooting

### Common Issues

1. **Memory Issues**
   ```bash
   # Check memory usage
   python3 -c "from src.resource_manager import get_resource_manager; print(get_resource_manager().get_resource_usage())"
   ```

2. **Authentication Issues**
   ```bash
   # Verify credentials
   gcloud auth application-default print-access-token
   ```

3. **Network Issues**
   ```bash
   # Test connectivity
   python3 -c "from google.cloud import storage; print(storage.Client().list_buckets())"
   ```

### Debug Mode

```python
# Enable debug logging
import os
os.environ['LOG_LEVEL'] = 'DEBUG'

from src.production_processor import ProductionSubtitleProcessor
processor = ProductionSubtitleProcessor()
```

## 📞 Support

For production support:

1. **Check Health Status**: Use health check endpoints
2. **Review Logs**: Check structured logs for errors
3. **Monitor Resources**: Verify system resources are available
4. **Validate Configuration**: Ensure all required settings are correct

### Emergency Procedures

1. **Service Degradation**: Check health endpoints and resource usage
2. **High Error Rates**: Review recent changes and network connectivity
3. **Resource Exhaustion**: Scale resources or reduce concurrent jobs
4. **Authentication Failures**: Verify credentials and permissions

---

## 📝 Version History

- **v2.0.0**: Production-grade implementation with comprehensive error handling
- **v1.0.0**: Basic functionality

For the latest updates, see [CHANGELOG.md](CHANGELOG.md).