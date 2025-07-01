# Video Subtitle Generator - Production Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown appuser:appuser /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Fix permissions
RUN chown -R appuser:appuser /app && \
    chmod +x main.py && \
    chmod +x subtitle-gen

# Create necessary directories
RUN mkdir -p input output temp logs jobs chunks subtitles && \
    chown -R appuser:appuser input output temp logs jobs chunks subtitles

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "from src.health_checker import HealthChecker; hc = HealthChecker(); exit(0 if hc.get_overall_health()['status'] == 'healthy' else 1)"

# Expose port for potential web interface
EXPOSE 8080

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Default command
CMD ["python", "main.py"]