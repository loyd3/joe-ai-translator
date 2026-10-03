@echo off
chcp 65001 >nul
setlocal EnableExtensions

rem Joe AI Translator - Windows local Docker entry
rem Ports: MySQL 3308, backend 8002, frontend 8081
rem Usage: deploy.bat [up down logs restart status rebuild prune]

cd /d "%~dp0"
title Joe AI Translator - Docker

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=up"

if "%MYSQL_DATA_PATH%"=="" set "MYSQL_DATA_PATH=F:/docker-data/joe-ai-translator/mysql"

docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not found. Install and start Docker Desktop first.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Start Docker Desktop and retry.
    pause
    exit /b 1
)

if not exist ".env" goto :make_env
goto :after_env

:make_env
if exist ".env.docker" (
    echo [INFO] .env missing, copying from .env.docker ...
    copy /Y ".env.docker" ".env" >nul
    echo [INFO] Edit .env and set DEEPSEEK_API_KEY, then run deploy.bat again.
    notepad ".env"
    pause
    exit /b 0
)
if exist ".env.example" (
    echo [INFO] .env missing, copying from .env.example ...
    copy /Y ".env.example" ".env" >nul
    echo [INFO] Edit .env then run deploy.bat again.
    notepad ".env"
    pause
    exit /b 0
)
echo [ERROR] Missing .env / .env.docker / .env.example
pause
exit /b 1

:after_env
findstr /B /C:"MYSQL_DATA_PATH=" ".env" >nul 2>&1
if errorlevel 1 (
    echo.>>".env"
    echo MYSQL_DATA_PATH=%MYSQL_DATA_PATH%>>".env"
)

for /f "usebackq tokens=1,* delims==" %%A in (`findstr /B /C:"MYSQL_DATA_PATH=" ".env"`) do (
    if not "%%B"=="" set "MYSQL_DATA_PATH=%%B"
)

if not exist "%MYSQL_DATA_PATH%" (
    echo [INFO] Creating MySQL data dir: %MYSQL_DATA_PATH%
    mkdir "%MYSQL_DATA_PATH%" >nul 2>&1
)

if /i "%ACTION%"=="up" goto :up
if /i "%ACTION%"=="down" goto :down
if /i "%ACTION%"=="logs" goto :logs
if /i "%ACTION%"=="restart" goto :restart
if /i "%ACTION%"=="status" goto :status
if /i "%ACTION%"=="rebuild" goto :rebuild
if /i "%ACTION%"=="prune" goto :prune

echo Unknown command: %ACTION%
echo Usage: deploy.bat up ^| down ^| logs ^| restart ^| status ^| rebuild ^| prune
exit /b 1

:up
echo.
echo ========================================
echo   Start Joe AI Translator Docker
echo   MySQL data: %MYSQL_DATA_PATH%
echo ========================================
echo.
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo [ERROR] Start failed. Run: deploy.bat logs
    pause
    exit /b 1
)
goto :success

:rebuild
echo.
echo ========================================
echo   Rebuild without cache and start
echo ========================================
echo.
docker compose build --no-cache
if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)
docker compose up -d
if errorlevel 1 (
    echo [ERROR] Start failed
    pause
    exit /b 1
)
goto :success

:success
echo.
echo ========================================
echo   Deploy OK
echo ========================================
echo   Frontend:  http://localhost:8081
echo   Backend:   http://localhost:8002
echo   API Docs:  http://localhost:8002/docs
echo   MySQL:     localhost:3308
echo.
echo   Data dir:  %MYSQL_DATA_PATH%
echo.
echo   Commands:
echo     deploy.bat logs
echo     deploy.bat status
echo     deploy.bat down
echo     deploy.bat restart
echo     deploy.bat rebuild
echo.
docker compose ps
goto :end

:down
echo Stopping services. Data directory is kept.
docker compose down
goto :end

:logs
docker compose logs -f --tail=200
goto :end

:restart
docker compose restart
docker compose ps
goto :end

:status
docker compose ps
echo.
echo --- docker disk ---
docker system df
echo.
echo --- mysql data dir ---
dir /s /-c "%MYSQL_DATA_PATH%" 2>nul
goto :end

:prune
echo Pruning unused images/build cache. MySQL data is kept.
docker builder prune -f
docker image prune -f
docker system df
goto :end

:end
echo.
pause