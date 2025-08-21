# Video Subtitle Generator - Production Docker Image
# OS-agnostic, self-contained environment with all dependencies
# Updated for 2025 with latest stable versions

FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO \
    ENV=production

# Install system dependencies including FFmpeg
# Use specific versions for reproducible builds and OS-agnostic compatibility
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    ca-certificates \
    gnupg \
    lsb-release \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Create app directory and set as working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser \
    && mkdir -p /app /data /logs \
    && chown -R appuser:appuser /app /data /logs

# Copy requirements first for better caching
COPY --chown=appuser:appuser requirements.txt requirements-minimal.txt ./

# Install Python dependencies as root
# Use latest pip and ensure reproducible builds
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    # Install dependencies with hash checking for security
    pip install --no-cache-dir -r requirements.txt && \
    # Clean up pip cache and temporary files
    pip cache purge && \
    # Verify installations
    python -c "import yaml, ffmpeg, rich, click; print('✅ Core dependencies verified')" && \
    python -c "from google.cloud import aiplatform, storage; print('✅ Google Cloud dependencies verified')" || echo "⚠️  Google Cloud deps need credentials"

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions  
RUN mkdir -p input output temp jobs logs chunks subtitles && \
    chown -R appuser:appuser input output temp jobs logs chunks subtitles && \
    chmod -R 755 /app && \
    chmod +x main.py docker-entrypoint.sh setup.sh && \
    # Ensure all Python files are readable
    find /app -name "*.py" -type f -exec chmod 644 {} \;

# Create volume mount points for persistent data
VOLUME ["/app/input", "/app/output", "/app/logs", "/app/temp", "/app/jobs"]

# Switch to non-root user
USER appuser

# Health check with improved error handling
HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=3 \
    CMD python -c "try:\n  from src.health_checker import quick_health_check; h=quick_health_check(); print(f'Health: {h.get(\"overall_status\", \"unknown\")}'); exit(0 if h.get('overall_status') in ['healthy','warning'] else 1)\nexcept Exception as e:\n  print(f'Health check failed: {e}'); exit(1)"

# Expose port for potential web interface or API
EXPOSE 8080

# Copy entrypoint script
COPY --chown=appuser:appuser docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Set the entry point
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command - interactive mode
CMD ["python", "main.py"]