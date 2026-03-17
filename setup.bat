@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ==============================================
echo TradingMind - Windows One-Click Docker Setup
echo ==============================================

REM Check if Docker CLI is installed and reachable.
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker CLI not found in PATH.
    echo [HINT] Install Docker Desktop and restart your terminal.
    exit /b 1
)

REM Check if Docker Engine is running.
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Engine is not running.
    echo [HINT] Start Docker Desktop and wait until it reports 'Engine running'.
    echo [HINT] In Docker Desktop, ensure WSL2 backend is enabled under Settings ^> General.
    exit /b 1
)

REM Optional check for Docker Compose v2 plugin.
docker compose version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 'docker compose' command is not available.
    echo [HINT] Update Docker Desktop to a version that includes Docker Compose v2.
    exit /b 1
)

REM Pull only works when compose services use images.
echo [INFO] Pulling latest images (if configured)...
docker compose pull
if errorlevel 1 (
    echo [WARN] 'docker compose pull' failed or no pullable image is configured.
    echo [INFO] Continuing with build/start...
)

echo [INFO] Building and starting containers...
docker compose up -d --build
if errorlevel 1 (
    echo [ERROR] Failed to build/start containers.
    exit /b 1
)

echo [INFO] Current container status:
docker compose ps
if errorlevel 1 (
    echo [ERROR] Unable to retrieve container status.
    exit /b 1
)

echo [SUCCESS] Setup complete.
echo [NEXT] To follow logs, run: docker compose logs -f

exit /b 0
