FROM python:3.11-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    mediainfo \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Verify ffmpeg installation
RUN ffmpeg -version

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs temp_chunks output input

# Create entrypoint script
RUN echo '#!/bin/bash\n\
if [ "$1" = "bash" ]; then\n\
    /bin/bash\n\
elif [ -n "$VIDEO_FILE" ] && [ -n "$TARGET_LANG" ]; then\n\
    python main.py --video "$VIDEO_FILE" --lang "$TARGET_LANG" --method "${HINDI_METHOD:-direct}"\n\
else\n\
    python main.py\n\
fi' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Run as non-root user
RUN useradd -m -u 1000 subtitle-user && chown -R subtitle-user:subtitle-user /app
USER subtitle-user

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
