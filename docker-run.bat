@echo off
REM Convenience script to run subtitle generator in Docker (Windows)
REM OS-agnostic through Docker

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop for Windows.
    echo Visit: https://docs.docker.com/desktop/windows/install/
    exit /b 1
)

REM Check for docker compose (prioritize modern syntax)
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    REM Fallback to legacy docker-compose
    docker-compose --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Docker Compose is not installed.
        echo Install Docker Desktop or docker-compose-plugin
        exit /b 1
    )
    set DOCKER_COMPOSE=docker-compose
    echo ⚠️  Using legacy docker-compose. Consider upgrading to 'docker compose'
) else (
    set DOCKER_COMPOSE=docker compose
)

REM Create data directories
echo 📁 Setting up data directories...
if not exist "data\input" mkdir "data\input"
if not exist "data\output" mkdir "data\output"
if not exist "data\logs" mkdir "data\logs"
if not exist "data\config" mkdir "data\config"
if not exist "data\temp" mkdir "data\temp"
if not exist "data\jobs" mkdir "data\jobs"

REM Check for service account
if not exist "data\config\service-account.json" (
    echo ⚠️  No service account found at data\config\service-account.json
    echo    Please copy your Google Cloud service account JSON to this location.
    echo    Example: copy C:\path\to\service-account.json data\config\
    echo.
)

REM Build image if needed
docker images -q video-subtitle-generator:latest >nul 2>&1
if %errorlevel% neq 0 (
    echo 🔨 Building Docker image ^(first time only^)...
    %DOCKER_COMPOSE% build
)

REM Parse command line arguments
if "%~1"=="" (
    REM No arguments - run interactive mode
    echo 🎬 Starting Video Subtitle Generator ^(Interactive Mode^)...
    %DOCKER_COMPOSE% run --rm subtitle-generator
) else if "%~1"=="shell" (
    REM Shell access
    echo 🔧 Opening shell in container...
    %DOCKER_COMPOSE% run --rm subtitle-generator bash
) else if "%~1"=="health" (
    REM Health check
    echo 🏥 Running health check...
    %DOCKER_COMPOSE% run --rm subtitle-generator python -c "from src.health_checker import quick_health_check; import json; print(json.dumps(quick_health_check(), indent=2))"
) else if "%~1"=="daemon" (
    REM Run as daemon
    echo 🚀 Starting as background service...
    %DOCKER_COMPOSE% up -d
    echo ✅ Service started. View logs with: docker compose logs -f
) else if "%~1"=="stop" (
    REM Stop daemon
    echo 🛑 Stopping service...
    %DOCKER_COMPOSE% down
) else if "%~1"=="logs" (
    REM View logs
    %DOCKER_COMPOSE% logs -f
) else if "%~1"=="process" (
    REM Process video with remaining arguments
    echo 🎥 Processing video...
    set args=%*
    call set args=%%args:*%1=%%
    %DOCKER_COMPOSE% run --rm subtitle-generator python main.py %args%
) else (
    REM Pass all arguments to main.py
    echo 🎬 Running with custom arguments...
    %DOCKER_COMPOSE% run --rm subtitle-generator python main.py %*
)