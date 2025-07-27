#!/bin/bash
# Docker entrypoint script for Video Subtitle Generator
# Handles initialization and configuration in container

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🐳 Video Subtitle Generator - Docker Container${NC}"
echo "=========================================="

# Create symlinks for data directories
echo -e "${GREEN}📁 Setting up data directories...${NC}"
for dir in input output logs temp jobs; do
    if [ -d "/data/$dir" ]; then
        rm -rf "/app/$dir"
        ln -sf "/data/$dir" "/app/$dir"
        echo "  ✓ Linked /data/$dir → /app/$dir"
    fi
done

# Handle service account
if [ -f "/data/config/service-account.json" ]; then
    ln -sf /data/config/service-account.json /app/service-account.json
    echo -e "${GREEN}✅ Service account linked from /data/config/${NC}"
    
    # Set environment variable if not already set
    if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="/app/service-account.json"
    fi
else
    echo -e "${YELLOW}⚠️  No service account found in /data/config/${NC}"
    echo -e "${YELLOW}   Mount your service-account.json to /data/config/${NC}"
    echo -e "${YELLOW}   Container will use Application Default Credentials if available${NC}"
fi

# Handle custom configuration
if [ -f "/data/config/config.yaml" ]; then
    ln -sf /data/config/config.yaml /app/config/config.yaml
    echo -e "${GREEN}✅ Custom config linked from /data/config/${NC}"
elif [ -f "/data/config/config.production.yaml" ] && [ "$ENV" = "production" ]; then
    ln -sf /data/config/config.production.yaml /app/config/config.yaml
    echo -e "${GREEN}✅ Production config linked from /data/config/${NC}"
fi

# Ensure proper permissions
echo -e "${GREEN}🔒 Setting permissions...${NC}"
for dir in /app /data/input /data/output /data/logs /data/temp /data/jobs; do
    if [ -d "$dir" ] && [ -w "$dir" ]; then
        chmod -R 755 "$dir" 2>/dev/null || true
    fi
done

# Run health check
echo -e "${GREEN}🏥 Running startup health check...${NC}"
python -c "
try:
    from src.health_checker import quick_health_check
    health = quick_health_check()
    status = health.get('overall_status', 'unknown')
    if status in ['healthy', 'warning']:
        print(f'✅ Health check: {status}')
    else:
        print(f'❌ Health check failed: {status}')
except Exception as e:
    print(f'⚠️  Health check error: {e}')
" || true

# Show environment info
echo -e "${GREEN}📊 Environment Information:${NC}"
echo "  • Python: $(python --version 2>&1)"
echo "  • FFmpeg: $(ffmpeg -version 2>&1 | head -n1)"
echo "  • Environment: $ENV"
echo "  • Log Level: $LOG_LEVEL"
echo "  • Working Directory: $(pwd)"

# Check if we're running in interactive mode
if [ -t 0 ] && [ -t 1 ]; then
    echo -e "${GREEN}🎬 Starting in interactive mode...${NC}"
else
    echo -e "${GREEN}🤖 Starting in non-interactive mode...${NC}"
fi

echo "=========================================="
echo ""

# Execute the main command
exec "$@"