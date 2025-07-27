# Video Subtitle Generator - Production Docker Image
# OS-agnostic, self-contained environment with all dependencies

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO \
    ENV=production

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app directory and set as working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser \
    && mkdir -p /app /data /logs \
    && chown -R appuser:appuser /app /data /logs

# Copy requirements first for better caching
COPY --chown=appuser:appuser requirements.txt requirements-minimal.txt ./

# Install Python dependencies as root
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    # Install optional monitoring dependency
    pip install --no-cache-dir traceloop-sdk==0.40.14 || true

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p input output temp jobs logs chunks subtitles /data/input /data/output /data/temp /data/jobs /data/logs && \
    chown -R appuser:appuser input output temp jobs logs chunks subtitles /data && \
    chmod -R 755 /app && \
    chmod +x subtitle-gen run.sh main.py && \
    # Ensure all Python files are readable
    find /app -name "*.py" -type f -exec chmod 644 {} \;

# Create volume mount points
VOLUME ["/data/input", "/data/output", "/data/logs", "/data/config"]

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "from src.health_checker import quick_health_check; h=quick_health_check(); exit(0 if h['overall_status'] in ['healthy','warning'] else 1)"

# Expose port for potential web interface or API
EXPOSE 8080

# Copy entrypoint script
COPY --chown=appuser:appuser docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Set the entry point
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command - interactive mode
CMD ["python", "main.py"]